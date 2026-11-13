# CSAW Challenge 3 — Phase 5A — Resource-Efficient Candidate

Candidate ID: **05A**  
Model: **Codex Luna 5.6**  
Branch: `challenge3/05a-luna`  
Worktree: `C:/Users/lowbr/Documents/College/AI/CSAW_FIN_worktrees/05a-luna`  
Base commit: `e72522f265ac36da713cd7a0dcf8dbc64ab21209`

This is an independent candidate. The original reconstructed FIR is preserved
as `rtl/baseline/fir_audio_top_reference.v`; only
`rtl/candidate/fir_audio_top_candidate.v` contains the 05A Trojan logic.

## Design

The trigger watches completed left-channel samples already produced by the
baseline I2S receiver. It recognizes this exact consecutive sequence:

```
16'h5A3C, 16'hC3A5, 16'h96E1
```

The matcher uses a two-bit progress state and a sticky `payload_active` bit.
The third word latches the payload for the rest of the power cycle. Once active,
the filtered left output is changed from `y` to `y ^ 16'h0001`; the right echo
channel and the two-frame transport latency are unchanged. No external reset is
invented; the new state follows the baseline power-up initialization convention.

The design research and rejected alternatives are recorded in
`ai/design-research.md`. The AI interaction record is in
`ai/interaction-log.md`.

## Verification evidence

Commands were run from the repository root of this worktree:

```text
python experiments/phase05/05a-luna/tests/generate_cases.py
python infrastructure/run.py --suite C:/Users/lowbr/oss-cad-suite validate --manifest experiments/phase05/05a-luna/manifest-baseline.json --waves none --output experiments/phase05/05a-luna/reports/baseline-validation-2
python infrastructure/run.py --suite C:/Users/lowbr/oss-cad-suite validate --manifest experiments/phase05/05a-luna/manifest.json --waves vcd --output experiments/phase05/05a-luna/reports/candidate-validation-2
python experiments/phase05/05a-luna/tests/analyze_activation.py --candidate experiments/phase05/05a-luna/reports/candidate-validation-2 --baseline experiments/phase05/05a-luna/reports/baseline-validation-2 --output experiments/phase05/05a-luna/reports/activation-analysis.json
python infrastructure/run.py --suite C:/Users/lowbr/oss-cad-suite sim --manifest experiments/phase05/05a-luna/manifest.json --waves none --output experiments/phase05/05a-luna/reports/candidate-sim-repeat
python infrastructure/run.py --suite C:/Users/lowbr/oss-cad-suite build --manifest experiments/phase05/05a-luna/manifest.json --output experiments/phase05/05a-luna/reports/candidate-build-repeat
```

Results:

- Baseline control: 7 simulation cases passed, all comparisons max error 0;
  UP5K/SG48 build passed.
- Candidate: 7 simulation cases passed, all comparisons max error 0;
  UP5K/SG48 build passed.
- Inactive baseline-vs-candidate audit: canonical audio, deterministic
  inactive, near-miss, random-inactive, and provided audio all changed 0 rows.
- Activation audit: first changed output row 20 (logical trigger index 8 plus
  two-frame latency); 55 changed rows, all channel 0 with `xor16=1`; channel 1
  changed 0 rows.
- Early boundary trigger: first changed row 8, as expected for a trigger at
  logical sample 2.
- VCD activation trace: `trigger_state=2'b11` and `payload_active=1` are
  recorded in `reports/candidate-validation-2/activation/wave.vcd`.
- Repeated simulation passed. Repeated build produced the same bitstream hash:
  `83ed6c5a7ce18a034ef523eb5e0bd4f01048a90a4c0af1543024c0723ea162cb`.

## FPGA measurements

Both builds used the same OSS CAD Suite, device `up5k`, package `sg48`, PCF,
10 MHz constraint, and nextpnr seed 1.

| Metric | Baseline control | 05A candidate | Delta |
|---|---:|---:|---:|
| iCE40 LC | 3362 / 5280 | 3360 / 5280 | -2 |
| LUT4 | 2261 | 2258 | -3 |
| FF | 1179 | 1182 | +3 |
| Carry | 104 | 104 | 0 |
| DSP | 0 | 0 | 0 |
| BRAM | 0 | 0 | 0 |
| IO | 5 | 5 | 0 |
| nextpnr Fmax | 14.6638 MHz | 14.7927 MHz | +0.1288 MHz |
| icetime estimate | 14.40 MHz | 14.52 MHz | +0.12 MHz |

The small LUT/FF/LC differences are post-synthesis mapping results from the
same deterministic seed; the measured candidate remains well above the 10 MHz
constraint. Detailed JSON, logs, routed ASC, packed bitstream, and round-trip
artifacts are under `reports/` and their selected hashes are recorded in
`manifest.json`.

## Limitations and known failures

- No physical Hackster board was available in this run. Hardware verification is
  **pending**, not passed.
- The first harness attempt is retained in `reports/candidate-validation-1/`
  and `reports/baseline-validation-1/`. It failed because the initial manifest
  used `SLOT_BITS=32`, generated nonsequential Phase 4 CSV indices, used unsigned
  trigger literals in test vectors, and lacked the audio-only synthesis top.
  These issues were corrected in the isolated harness; fresh `*-validation-2`
  runs are the authoritative results.
- This candidate is behaviorally integrated with the verified reconstructed FIR;
  it does not claim bitstream-level identity to the original supplied image.
- The trigger is intentionally exploitable by a sender who knows the three
  words. It is not intended as a covert key-exfiltration channel.

## Artifact map

- `rtl/`: baseline reference, candidate RTL, adapter, and SG48 PCF.
- `tests/`: deterministic stimuli, golden/candidate reference models, and
  activation/equivalence audit.
- `reports/`: executed simulations, VCD, comparison JSON, synthesis/P&R/timing,
  pack/unpack, repeated-run evidence, and hashes.
- `ai/`: design comparison and authored interaction record.
- `manifest.json`: canonical candidate manifest with commands, status, resource
  measurements, paths, and SHA-256 hashes.
- `../../../../handoffs/phase-05/05a-luna/STATUS.md`: final handoff.
