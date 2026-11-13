"""EDA toolchain helpers for the CSAW 2026 pipeline.

All simulation and synthesis the verifiers need goes through here, so the rest
of the pipeline never shells out to a simulator directly. The targets are the
open-source tools the challenge recommends (the Yosys OSS CAD Suite): Icarus
Verilog for simulation, and yosys / nextpnr-ice40 / icepack for the iCE40-UP5K
bitstream. Each helper degrades gracefully: if a tool is missing it returns a
clear, logged message instead of raising, so the pipeline reports *why* a step
could not run rather than crashing.

Nothing here is challenge-specific; the per-challenge ``verifier.py`` supplies
the source lists, top module, and PASS/FAIL markers.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass


def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def toolchain_report() -> str:
    tools = ["iverilog", "vvp", "verilator", "yosys", "nextpnr-ice40",
             "icepack", "icetime"]
    rows = [f"  {t:<16} {'present' if have(t) else 'MISSING'}" for t in tools]
    return "Toolchain:\n" + "\n".join(rows)


@dataclass
class SimResult:
    ok: bool              # the simulator ran to completion (compile + run)
    output: str           # combined stdout/stderr (compile log + sim log)
    timed_out: bool = False


def _run(cmd, cwd, timeout):
    try:
        p = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout, check=False)
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired as exc:
        return 124, (exc.stdout or "") + f"\n[timed out after {timeout}s]\n"
    except OSError as exc:
        return 127, f"{cmd[0]}: {exc}\n"


def run_iverilog(sources, top, workdir, *, timeout=120, defines=None,
                 g="2012", vvp_plusargs=None) -> SimResult:
    """Compile ``sources`` with Icarus Verilog and run the result under vvp.

    ``sources`` are paths (absolute, or relative to ``workdir``). ``top`` is the
    testbench top module. Returns a :class:`SimResult` whose ``output`` holds
    both the compile and the run logs; the caller greps it for its own PASS/FAIL
    markers.
    """
    if not have("iverilog") or not have("vvp"):
        return SimResult(False, "iverilog/vvp not found on PATH. Install the "
                                "Yosys OSS CAD Suite (it bundles Icarus Verilog).\n")
    os.makedirs(workdir, exist_ok=True)
    out_vvp = os.path.join(workdir, f"{top}.vvp")
    cmd = ["iverilog", f"-g{g}", "-o", out_vvp, "-s", top]
    for d in (defines or []):
        cmd += ["-D", d]
    cmd += list(sources)
    rc, log = _run(cmd, workdir, timeout)
    log = f"$ {' '.join(cmd)}\n{log}"
    if rc != 0:
        return SimResult(False, log + "\n[iverilog compile failed]\n",
                         timed_out=(rc == 124))
    run_cmd = ["vvp", out_vvp] + list(vvp_plusargs or [])
    rc2, runlog = _run(run_cmd, workdir, timeout)
    log += f"\n$ {' '.join(run_cmd)}\n{runlog}"
    return SimResult(rc2 == 0, log, timed_out=(rc2 == 124))


@dataclass
class AreaResult:
    ok: bool
    cells: int | None
    luts: int | None
    output: str


def synth_area_ice40(sources, top, workdir, *, timeout=300) -> AreaResult:
    """Synthesise for the iCE40-UP5K with yosys and report cell / LC-LUT counts.

    Used for the optional stealth/area check: a Trojan that blows up logic usage
    is easy to spot, so the pipeline can compare a candidate against the clean
    baseline. Missing yosys is not fatal - it just means no area number.
    """
    if not have("yosys"):
        return AreaResult(False, None, None,
                          "yosys not found; skipping area/stealth check.\n")
    os.makedirs(workdir, exist_ok=True)
    src = " ".join(sources)
    script = (f"read_verilog -sv {src}; "
              f"synth_ice40 -top {top}; "
              f"stat")
    cmd = ["yosys", "-p", script]
    rc, log = _run(cmd, workdir, timeout)
    log = f"$ yosys -p '{script}'\n{log}"
    cells = luts = None
    for line in log.splitlines():
        s = line.strip()
        if s.startswith("Number of cells:"):
            try:
                cells = int(s.split(":")[1])
            except ValueError:
                pass
        # iCE40 LUT primitive
        if "SB_LUT4" in s:
            parts = s.split()
            try:
                luts = int(parts[-1])
            except ValueError:
                pass
    return AreaResult(rc == 0, cells, luts, log)


def build_bitstream(make_dir, outputname_root, *, timeout=600) -> SimResult:
    """Build an iCE40 bitstream via the challenge's ``hackster.mk`` flow.

    Thin wrapper over ``make run_synth`` so the "one command to a built
    bitstream" automation path exists; used only when the team is on a machine
    with the full place-and-route toolchain. Programming a physical board is a
    separate, human-confirmed step (see each challenge's README).
    """
    if not have("yosys") or not have("nextpnr-ice40") or not have("icepack"):
        return SimResult(False, "Full iCE40 bitstream flow needs yosys + "
                                "nextpnr-ice40 + icepack (OSS CAD Suite).\n")
    cmd = ["make", "run_synth", f"OUTPUTNAME_ROOT={outputname_root}"]
    rc, log = _run(cmd, make_dir, timeout)
    return SimResult(rc == 0, f"$ {' '.join(cmd)} (in {make_dir})\n{log}")
