# Phase 05BB authorized synthetic audio channel

Status: **PARTIAL DEMONSTRATION**, simulation-only recovery; potential Bonus B
5/10 under the official rubric, subject to judging. No hardware capture exists.
See `docs/candidate-selection.md`, `docs/results.md`, `docs/verification-contract.md`,
`docs/hardware-procedure.md`, and `ai/provenance.md` for decisions and limitations.

Source rollback: Q-corrected 05B commit
`fd0ca7f6bce1d30bb1b1e6ce43603b4c7d51e5b6`, retained unchanged in this worktree.
Only this experiment adds a distinct eight-sample trigger and bounded synthetic
ROM transmitter to the left-output mux. It reads no external/private memory.
The original 05B trigger and FIR remain active as before outside laboratory mode.

`inputs/message.txt` declares `CSAW26-BONUS-B`; `original.bits` declares its bits
for three attempts. The ROM emits sync/length/payload/CRC over square-wave BFSK.
Input after activation is silence. Recovery takes only mono filtered-left audio;
the original bits are opened afterward for scoring. The decoder assumes the
documented digital PCM path without resampling; analog/acoustic robustness is
not established.

From the worktree root, PowerShell reproduction (fresh output paths required):

```powershell
$python = 'C:/Users/lowbr/oss-cad-suite/lib/python3.exe'
$suite = 'C:/Users/lowbr/oss-cad-suite'
$exp = 'experiments/phase05/05bb-bonus-b'
& $python "$exp/tests/rtl/run_checks.py" --suite $suite --output build/05bb-rtl-repeat
& $python "$exp/tools/run_channel.py" --suite $suite --output build/05bb-channel-repeat
& $python "$exp/tools/test_decoder.py"
& $python "$exp/tools/verify_package.py"
```

Python 3.11+ with standard library and the recorded OSS CAD Suite is sufficient
for software/simulation/build. Hardware host scripts additionally need pyserial.
Set these paths for another machine. The runner logs exact argv, tool hashes,
clock settings, exits, serial capture, WAVs, decoder results and per-bit CSVs.
Each rate tests three packets in a continuous I2S stream. Negative controls use
input, right echo, unmodified Q output and silence. Software corruption and
truncation controls test measurement failures; they are not board recordings.

The complete 28 MB local evidence tree is compressed in
`verification-evidence.zip`; `evidence-inventory.json` hashes every member.
Extract it into this experiment directory to restore ignored `evidence/`,
`reports/`, and generated test fixtures after a clean checkout:

```powershell
Expand-Archive "$exp/verification-evidence.zip" -DestinationPath $exp
```

Key files after extraction: `evidence/channel-run-1/channel-summary.json`,
`evidence/channel-run-1/channel-31250/simulation-filtered-left.wav`,
`evidence/channel-run-1/channel-31250/recovery/recovered.bits`,
`evidence/channel-run-1/channel-31250/recovery/evaluation/bit-comparison.csv`,
`reports/rtl-verification-summary.json`, and
`reports/baseline-build-run1/fpga-build/{build-summary.json,timing.json,icetime.txt,bitstream.bin}`.
`source-inventory.json` records the exact implementation and input bytes.

The full build meets the 10 MHz system-clock constraint. LED role assignments
remain inherited tentative mappings; asynchronous I2S timing has functional
simulation coverage, not physical-board signoff. See the unexecuted hardware
procedure for stock/experimental baseline, three captures, elapsed wall time,
and port identification. Transcript completeness and documentation-model
synthesis remain explicit gaps; no public publication or candidate merge occurs.
