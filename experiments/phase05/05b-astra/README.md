# CSAW 2026 Challenge 3 - Candidate B (Astra Reliability)

This isolated candidate implements a deterministic, exact-sequence trigger and a 128-frame left-channel filter bypass. It is based on the recovered Phase 3 audio design and is checked with the Phase 4 generic runner.

## Candidate behavior

The matcher accepts eight consecutive exact 16-bit left samples: `7F00 8101 5A3C A5C3 6D92 926D C33C 3CC3`. On the final sample, the left output passes the current and next 127 samples directly, for 128 frames. The FIR continues to run; when the counter expires, the normal filtered output resumes. The right echo, I2S serializer, and two-frame baseline output latency are retained. State starts from the recovered iCE40 power-up initialization; there is no external reset on the core.

The test interface uses 16 BCLK periods per channel slot with Philips one-bit MSB delay, matching the recovered design's successful Phase 4 integration. The package-local adapter in `rtl/phase4_dut.sv` maps the generic testbench ports directly and does not gate I2S signals with the bench reset.

## Measured verification

Validation runs 5, 6, and 7 each passed all ten simulation cases and the FPGA build: 11/11 report cases, 0 failed, 0 blocked. Each `validate` run also passed 15 framework unit tests.

- Baseline mismatch count: 0 over 22,248 compared words across the seven normal-operation cases.
- Right-channel echo mismatch count: 0; the first two startup output frames were zero as expected.
- Negative tests: 7/7 passed, including seeded random data, a one-word near miss, and a sequence split by an interruption.
- Trigger events: 4/4 passed at 1 MHz, 625 kHz, and two repeated activations. Each event produced exactly 128 raw pass-through frames; total pass-through mismatches: 0.
- Boundary, noisy-audio, startup, and sequential retrigger tests matched their expected results exactly.
- Reproducibility: validation runs 6 and 7 had identical per-case input-content hashes and identical bitstream SHA-256 `49e24471d676518619d57df5855c533b5eae166feef662cd47fd10d989efb02b`.

For iCE40 UP5K SG48 at a 10 MHz constraint, place-and-route used 3,662/5,280 logic cells (69.4%), 0/8 DSPs, 0/30 block RAMs, and 9/39 IO cells. Reported Fmax was 15.1316 MHz. The bitstream pack/unpack round trip passed. No physical board was available; hardware operation is unverified.

See `reports/evidence-summary-final.json`, `reports/validation-run-7/report.json`, and `reports/validation-run-7/fpga-build/build-summary.json` for captured results and tool versions. Failed harness/configuration attempts and their fixes are summarized in `ai/rejected-revisions.md`.

## Reproduction

Run these commands from the isolated worktree root. Use an OSS CAD Suite installation with the Icarus, Yosys, nextpnr-ice40, IceStorm, and icetime tools listed in the validation report.

```powershell
$Suite = 'C:\Users\lowbr\Documents\College\AI\CSAW_FIN\.worktrees\phase-04\.tools\oss-cad-suite'
$Python = Join-Path $Suite 'lib\python3.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
& $Python experiments/phase05/05b-astra/tests/prepare_vectors.py
& $Python infrastructure/run.py --suite $Suite validate --manifest experiments/phase05/05b-astra/manifest.json --output experiments/phase05/05b-astra/reports/reproduction-run
& $Python experiments/phase05/05b-astra/tests/audit_results.py --run experiments/phase05/05b-astra/reports/validation-run-6 --repeat-run experiments/phase05/05b-astra/reports/reproduction-run --output experiments/phase05/05b-astra/reports/reproduction-evidence.json
```

`manifest.json` records the runner configuration, exact source hashes, trigger behavior, verification status, and baseline source commit. `ai/source-hashes.json` repeats the hash inventory and records the manifest hash. The Phase 3 golden inputs and outputs remain byte-preserved; `reference_io.generic.csv` is a separate runner-compatible copy.

## Package map

- `rtl/fir_audio_top.v`: AI-authored candidate top.
- `rtl/baseline/fir_audio_top.v`: unchanged recovered baseline.
- `rtl/phase4_dut.sv`: local copy of the validated direct-wire adapter.
- `tests/reference/` and `tests/vectors/`: golden reference, coefficients, preserved Phase 3 data, and deterministic stimuli.
- `tests/prepare_vectors.py`, `tests/candidate_reference.py`, `tests/audit_results.py`: AI-authored vector, expected-result, and capture-audit code.
- `reports/`: regression reports, actual captures, build outputs, and evidence summary.
- `ai/`: model provenance, source hashes, session record, and rejected revisions.
- `manifest.json`: Phase 4 schema-version-1 `verified_design` manifest with candidate metadata.

## Provenance and limits

The competition-specific trigger, payload, RTL changes, test/reference additions, manifest, and documentation were AI-authored for this candidate. The baseline RTL and original golden data were copied unchanged from Phase 3. The requested model label was Astra; the runtime does not expose an exact model identifier. The Phase 2 audio top is a behavioral reconstruction rather than a gate-level copy. Hackster board testing remains outstanding, and LED/RGB pin roles remain provisional. No public remote was updated, and this candidate does not select an overall winner.
