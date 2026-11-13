# Reproduction

Run from the dedicated worktree root. Use Python 3.11+ and the same OSS CAD Suite
whose executable versions/hashes are recorded in the evidence. On this host:

```powershell
$python = 'C:/Users/lowbr/oss-cad-suite/lib/python3.exe'
$suite = 'C:/Users/lowbr/oss-cad-suite'
$exp = 'experiments/phase05/05bb-bonus-b'
& $python "$exp/tools/run_channel.py" --suite $suite --output build/05bb-channel-repeat
& $python "$exp/tests/rtl/run_checks.py" --suite $suite --output build/05bb-rtl-repeat
```

Use fresh output directories; the runners refuse to reuse them. `run_channel.py`
generates declared test inputs, compiles/simulates the experimental and original
source designs, captures serialized audio, decodes the filtered-left waveform,
evaluates bits afterward, and runs the input/echo/source/silence/corruption/
truncation controls. `run_checks.py` executes framework, baseline, directed,
boundary, and FPGA build checks. Preserve command exits and logs as well as the
summary JSON. A command merely existing is not evidence that it ran.

For separate host-side recovery from a designated WAV:

```powershell
& $python "$exp/tools/decode.py" build/05bb-channel-repeat/channel-31250/simulation-filtered-left.wav --output build/05bb-decoded-repeat
& $python "$exp/tools/evaluate.py" build/05bb-channel-repeat/channel-31250/original.bits build/05bb-decoded-repeat/decode.json --output build/05bb-evaluated-repeat
```

The decoder must run before evaluation and receives no expected-message file.
Its source file hash ties recovered bits to the measured WAV. Do not substitute
`input.wav`, an echo recording, debug output, a model waveform, or an expected
bit file for the designated filtered-left audio.

`prepare.py --output NEW_DIRECTORY --rate 31250 --repeats 3` regenerates the
declared synthetic bits and trigger-only host input. Changing the payload also
requires regenerating the matching FPGA packet constant and rerunning all
validation; merely changing an expected-bit file is not a valid experiment.

The checked-in `official/tools/` and `official/fpga/` files support the future
physical procedure. Read `hardware-procedure.md` before using them, identify
the authorized board and correct ports, and retain actual timing and output.
Simulation artifacts must remain labeled as simulation.

The required handoffs are `handoffs/phase-05/bonus-b.json` and `bonus-b.md`.
They identify the immutable source commit, experimental implementation commit,
evidence, supported bonus status, limitations, and downstream Phase 5S/8 usage.
