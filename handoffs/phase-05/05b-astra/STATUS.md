# Phase 5B Handoff - 05b-astra

**State:** simulation and synthesis passed reproducibly; physical hardware unverified.

## Identity

- Candidate: Independent Candidate B - Astra Reliability
- Branch: `challenge3/05b-astra`
- Worktree: `C:\Users\lowbr\Documents\College\AI\CSAW_FIN_worktrees\05b-astra`
- Frozen base: `e72522f265ac36da713cd7a0dcf8dbc64ab21209`
- Phase 3 baseline/reference commit: `5dedf4c4ed10f47fbe9ec138c7db2019446cdb7f`
- Package: `experiments/phase05/05b-astra/`

## Candidate

The trigger is eight exact consecutive signed 16-bit left samples (`7F00 8101 5A3C A5C3 6D92 926D C33C 3CC3`). On completion it bypasses the left FIR for exactly 128 frames, beginning with the trigger's final sample. Normal filtering then resumes. The recovered right echo, I2S serializer, and two-frame output latency are preserved. The matcher, counter, delay line, and output state have deterministic iCE40 power-up initialization; the core has no external reset input.

## Verification evidence

Full validations 5, 6, and 7 passed 11/11 cases each, with no blocked cases. Each run also passed 15 framework unit tests. The final capture audit compares run 6 and run 7.

- Baseline mismatch count: 0 over 22,248 normal-operation words.
- Right echo mismatches: 0; two startup zero frames verified.
- Negative tests: 7/7; no false activation in random, near-miss, or split-sequence inputs.
- Positive events: 4/4; each produced 128/128 raw frames with zero mismatch, including a two-trigger retrigger case.
- Boundary stress, startup edges, noisy PCM16 audio, baseline golden vectors, and 16,384-word seeded random input all matched exactly.
- I2S tested with 16-bit slots and one-bit Philips MSB delay at 1 MHz and 625 kHz BCLK.
- Reproducibility: runs 6 and 7 had identical test/build input content hashes and identical bitstream SHA-256 `49e24471d676518619d57df5855c533b5eae166feef662cd47fd10d989efb02b`.
- UP5K/SG48 utilization: 3,662/5,280 LCs (69.4%); 0/8 DSP, 0/30 BRAM, and 9/39 IO cells.
- Timing: 10 MHz constraint met; reported Fmax 15.1316 MHz. IceStorm pack/unpack round trip passed.

Reports are in `experiments/phase05/05b-astra/reports/`. The final run is `validation-run-7`; the combined capture/build/reproducibility summary is `evidence-summary-final.json`. `ai/rejected-revisions.md` records the initial CSV-format, adapter, source-path, slot-width, and first audit-comparison corrections.

## Reproduction

From the worktree root:

```powershell
$Suite = 'C:\Users\lowbr\Documents\College\AI\CSAW_FIN\.worktrees\phase-04\.tools\oss-cad-suite'
$Python = Join-Path $Suite 'lib\python3.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
& $Python experiments/phase05/05b-astra/tests/prepare_vectors.py
& $Python infrastructure/run.py --suite $Suite validate --manifest experiments/phase05/05b-astra/manifest.json --output experiments/phase05/05b-astra/reports/reproduction-run
& $Python experiments/phase05/05b-astra/tests/audit_results.py --run experiments/phase05/05b-astra/reports/validation-run-6 --repeat-run experiments/phase05/05b-astra/reports/reproduction-run --output experiments/phase05/05b-astra/reports/reproduction-evidence.json
```

## Documentation agent and limitations

The Project Scribe `record-test` interface ran the final full validation and recorded its actual exit code (`0`) and stable Git state. A Scribe evidence preview is saved as `experiments/phase05/05b-astra/reports/scribe-preview.md` and `scribe-preview-evidence.json`, with Google publishing disabled. It was captured before the local candidate commit, so its Git snapshot records the candidate files as untracked. The installed project setup remains marked unactivated: its model identifier is a placeholder and the OpenClaw agent/Gateway is not configured in this environment, so no model-generated Scribe synthesis is claimed.

No Hackster board was available, so no physical timing, startup, I2S, payload, or bitstream programming result is claimed. The recovered audio source is a Phase 2 behavioral reconstruction, and LED/RGB pin roles are provisional. The public remote was not written. No overall candidate winner was selected.

