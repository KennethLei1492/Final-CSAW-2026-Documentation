# Phase 4 infrastructure handoff

Branch: `challenge3/04-infrastructure` (based on Phase 1 `dc064b2`).
Worktree: `C:/Users/lowbr/Documents/College/AI/CSAW_FIN/.worktrees/phase-04`.
Owner: Codex, reusable test/build infrastructure only.

Independent infrastructure is complete and validated. The pinned official OSS CAD Suite
2026-11-12 is installed at `.tools/oss-cad-suite` inside this worktree. Other agents
can set `OSS_CAD_SUITE` to that absolute path. No system PATH change is needed.

Final executions: twelve I2S loopback cases passed 2,272 exact sample comparisons;
these include the first 256 frames from each supplied WAV input. All 15 framework
tests passed, including a hand-derived literal I2S wire sequence, X rejection,
short/missing LRCLK transitions, deliberate inverted-RTL failure, reference-command
execution, FST capture, malformed CSV, exact lengths, channel order, explicit latency,
signed range, and invalid tolerance rejection. VCD capture passed on all smoke cases.
UP5K/SG48 counter fixture passed Yosys, nextpnr, IceStorm pack/unpack, and icetime.
These are explicitly infrastructure fixtures, not a recovered FIR or stock-bitstream
equivalence result. No hardware has been programmed or verified.

Runnable: `infrastructure/run.ps1 validate --waves vcd` on Windows, or
`python infrastructure/run.py validate --waves vcd` with a usable Python 3.11+.
The runner writes fresh artifacts under `build/`: command logs and exit records,
source/executable hashes, CSV comparisons, VCD/FST, JSON/Markdown/JUnit reports,
synthesis utilization, place/route timing, ASC and bitstream files.

Pending from Claude Phase 2/3: verified port names/directions; I2S word/slot widths,
channel polarity, bit offset and edges; clocks/reset behavior; output latency;
supplied RTL file list and definitions; golden input/output CSV or reference-model
entry point; verified FPGA package and pin constraints. Report these through
`handoffs/phase-02/` and `handoffs/phase-03/`. No such verified handoff was present
when the independent framework was created. The recovered-design template returns
BLOCKED (exit 2) until supplied, rather than a fixture pass.

Adapter contract: module `phase4_dut(input clk, rst, bclk, lrclk, sd_in,
output sd_out)`. `rst` is active high at this boundary; adapt polarity internally.
The controller owns BCLK/LRCLK and changes SD on falling edges. The monitor samples
on rising edges. A different verified interface needs an explicit adapter or
driver extension; never silently reinterpret the design. Models/RTL remain owned
by Claude. Reference CSV: `index,channel,value`, contiguous zero-based word index,
channel 0 left/1 right, signed decimal sample. The `reference_command` argv contract
substitutes `{python}`, `{input}`, `{output}` and executes without a shell.

Windows findings: this Codex sandbox caused Icarus access violations even for a
minimal counter; the same compiler passed in approved normal execution. IceStorm
unpacking uses explicit `-u` because executable basename detection failed for
the uppercase `.EXE` path. Both initial failures are retained in local logs.

Counter build evidence: 27/5,280 logic cells, 1 global buffer, 6 IOs, no RAM/DSP.
nextpnr reports 79.7448 MHz achieved against 10 MHz; icetime reports 80.62 MHz.
These are fixture timing results, not recovered-design or external IO signoff.
Repeated fresh builds produced the same bitstream SHA-256:
`04764d49c38bede4af1d9d78b0717615dff3a0ea2c6e23b832940a2d45b034fc`.

Verified implementation commits (all on the infrastructure branch):

- `764873b`: pinned toolchain configuration, dependency probes and subprocess logs.
- `027b357`: generic I2S drivers, monitors and literal protocol fixture.
- `3715e40`: numerical comparison, stimulus generation and report utilities.
- `f8da331`: configurable runner, model command interface and FPGA build integration.
- `2c04dba`: 64-bit watchdog arithmetic for long captures; final implementation tested.

Final artifact directory: `build/final-validation-v2/` in this worktree. Entry points:
`report.json`, `report.md`, `junit.xml`, `unit-tests.log`, per-case `comparison.json`,
`actual.csv`, `wave.vcd`, command `.log.json` records; FPGA products live under
`fpga-build/` (`utilization.json`, `timing.json`, `icetime.txt`, `build-summary.json`,
`bitstream.bin`). Raw artifacts are local/ignored; portable compact evidence is
`handoffs/phase-04/validation.json`. The deliberately blocked run is retained under
`build/recovered-blocked/`, with exit 2 verified. No reconstructed-source handoff
was available in the main or Phase 2 worktree at final inspection.

Project Scribe is the existing documentation interface. Its configuration now
includes this worktree and this handoff source without replacing other roots.
`record-test` recorded the final validation at HEAD `2c04dba`, exit 0,
`trackedStateStable: true`, session `phase04-final-validation`. A model-free
`preview` supplies the local documentation report. Its unconfigured model service
is not claimed to have synthesized or published a report.

Coordination: a copy of this phase-owned status and compact evidence is placed at
the main project's `handoffs/phase-04/` for Claude. Source code remains isolated.
No reconstructed RTL, models, canonical documentation, or main-branch commits were
changed. Follow-up integration must consume actual Phase 2/3 handoffs; it is not
reported as completed by this independent infrastructure milestone.
