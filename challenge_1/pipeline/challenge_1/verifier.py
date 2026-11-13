"""Verifier for challenge 1 - drives the team's real exploit testbench.

This does NOT use a bespoke harness: it compiles the candidate ``crypto_core.v``
together with the submission's own SPI wrapper (``rtl/spi_crypto_top.v``) and the
submission's own exploit testbench (``tb/tb_trojan.v``) under Icarus Verilog, and
reads that testbench's verdict. ``tb_trojan`` instantiates two cores in
lock-step - ``spi_crypto_top #(.TROJAN_EN(1))`` (the candidate, Trojaned) and
``#(.TROJAN_EN(0))`` (a clean twin) - and proves three things: the recovered
cipher is functionally correct (reproduces the golden vector 0x59C359C3 ->
0x9CD84392), the Trojan is perfectly stealthy (bit-identical to the clean twin
on 72/72 non-trigger transactions), and the two-block knock
enc(0xDEADC0DE)->enc(0xFEEDFACE) exfiltrates the recovered device key
0x8E043CB1 on MISO.

The recovered cipher reads its key-dependent S-box tables with ``$readmemh``, so
the ``rtl/sbox_*.mem`` files are copied next to the simulation before it runs.

Verdict mapped to the CSAW-style shape:
  normal_ok      golden vector reproduced AND no stealth leak on normal traffic;
  trigger_fires  the knock leaked the device key (``[EXPLOIT-OK]``);
success = both (equivalently the testbench's own ``TB_TROJAN: ALL PASS``).
"""

from __future__ import annotations

import glob
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from common import toolchain                        # noqa: E402

CANDIDATE = os.path.join(HERE, "work", "rtl", "crypto_core.v")
PRISTINE = os.path.join(HERE, "recovered_rtl", "crypto_core.v")
SOLUTION = os.path.join(HERE, "solution", "crypto_core_trojan.v")
TB = os.path.join(HERE, "tb", "tb_trojan.v")
TOP_WRAPPER = os.path.join(HERE, "rtl", "spi_crypto_top.v")
MEM_DIR = os.path.join(HERE, "rtl")
TOP = "tb_trojan"
SYNTH_TOP = "crypto_core"
BUILD = os.path.join(HERE, "work", "build")


def _parse(log: str) -> dict:
    trigger = "[EXPLOIT-OK] DUT leaked SECRET_KEY" in log
    normal = ("[PASS] golden vector reproduced" in log
              and "[LEAK!]" not in log
              and "[FAIL] round-trip" not in log)
    verdict = {"normal_ok": bool(normal), "trigger_fires": bool(trigger)}
    if not (normal and trigger):
        if "[iverilog compile failed]" in log or "error:" in log.lower():
            verdict["hint"] = "the candidate RTL did not compile."
        elif "[LEAK!]" in log:
            verdict["hint"] = ("stealth broken: the Trojaned core differs from a "
                               "clean core on normal traffic.")
        elif not trigger:
            verdict["hint"] = ("the knock enc(0xDEADC0DE)->enc(0xFEEDFACE) did "
                               "not leak the device key on MISO.")
    return verdict


def verify(rtl_path: str | None = None, *, area: bool = False) -> dict:
    rtl = rtl_path or CANDIDATE
    if not os.path.isfile(rtl):
        return {"normal_ok": False, "trigger_fires": False,
                "raw": f"candidate RTL not found: {rtl}\n"}
    os.makedirs(BUILD, exist_ok=True)
    for mem in glob.glob(os.path.join(MEM_DIR, "*.mem")):   # $readmemh needs these in cwd
        shutil.copy(mem, BUILD)
    sim = toolchain.run_iverilog([TB, TOP_WRAPPER, rtl], TOP, BUILD, timeout=180)
    raw = sim.output
    verdict = _parse(raw)
    if "hint" in verdict:
        raw += "\nclassification: " + verdict.pop("hint") + "\n"
    if area:
        # the full S-box core is memory-heavy; report cell/LUT counts for stealth
        ar = toolchain.synth_area_ice40([rtl], SYNTH_TOP, BUILD)
        raw += "\n--- area (yosys synth_ice40) ---\n" + ar.output
        if ar.cells is not None:
            raw += f"\ncells={ar.cells} luts={ar.luts}\n"
    verdict["raw"] = raw
    return verdict


def main(argv):
    target = CANDIDATE
    area = "--area" in argv
    if "--clean" in argv:
        target = PRISTINE
    elif "--solution" in argv:
        target = SOLUTION
    else:
        for a in argv:
            if a.endswith(".v") and os.path.isfile(a):
                target = a
    v = verify(target, area=area)
    print(v["raw"])
    print(f"VERDICT normal_ok={v['normal_ok']} trigger_fires={v['trigger_fires']}")
    return 0 if (v["normal_ok"] and v["trigger_fires"]) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
