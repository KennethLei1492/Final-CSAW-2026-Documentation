# R-001 — Phase 4 recovered-design path is BLOCKED by a golden-vector format/adapter gap

- **Source commits:** Phase 2 `1befb30`, Phase 4 `2da1d72`.
- **Severity:** high for end-to-end hardware verification (not a reconstruction defect).
- **Owner to integrate:** Phase 3 (baseline/verification owner).
- **Confidence:** very high (verified against Phase 4's own code).

## Identified issue
Phase 4's reusable harness returns **BLOCKED (exit 2)** for the recovered design
because the Phase 2 deliverables do not match the two contracts it requires:

1. **Reference-CSV schema.** `infrastructure/results.py::read_samples()` requires the
   header to be **exactly `index,channel,value`** with sequential zero-based `index`,
   `channel ∈ {0,1}` (interleaved L/R), signed decimal `value`. The Phase 2 handoff
   `handoffs/phase-02/reference_vectors.csv` uses header `n,x_in_int16,y_filtered_int16`
   and carries only input + filtered-left (no echo/right channel). It cannot be read
   by Phase 4 and does not represent the 2-channel output stream.
2. **DUT adapter.** Phase 4 expects module `phase4_dut(input clk, rst, bclk, lrclk,
   sd_in, output sd_out)` with **active-high `rst`**. The recovered design has no
   reset port and raw `io_*`/named ports; no adapter was handed off.

## Evidence
- `infrastructure/results.py` line ~12: `if reader.fieldnames != ['index','channel','value']: raise ValueError`.
- `handoffs/phase-04/STATUS.md`: "The recovered-design template returns BLOCKED (exit 2) until supplied";
  "Adapter contract: module `phase4_dut(input clk, rst, bclk, lrclk, sd_in, output sd_out)`. `rst` active high".
- `handoffs/phase-02/reference_vectors.csv` header is `n,x_in_int16,y_filtered_int16`.

## Proposed correction (provided & self-verified)
`review/scripts/rv_make_phase4_golden.py` emits BOTH streams in Phase 4's schema:
- `input.csv` — mono duplicated to L/R: frame n → `(2n,0,x[n])`,`(2n+1,1,x[n])`.
- `golden_output.csv` — frame n → `(2n,0,filtered[n])`,`(2n+1,1,echo[n]=x[n])`,
  with `filtered[n]=sat16((Σ x[n−k]·h[k] + 2¹⁴) >> 15)`.
Ready-made samples (first 256 audio frames of `what_a_piece_of_work-noisy.wav`):
`handoffs/reconstruction-review/phase4-golden/{input,golden_output}.csv`.

**Latency:** pass **`latency_words = 4`** to `compare()` (2-frame pipeline × 2
interleaved channels).

**Adapter:** wrap `recovered/rtl/fir_audio_top.v` so `phase4_dut`'s
`clk→ICE_CLK, bclk→I2S_BCLK, lrclk→I2S_WS, sd_in→I2S_SD_IN, sd_out→I2S_SD_OUT`,
tie off LEDs, and ignore active-high `rst` (the design is free-running, power-up
state only). The existing sim adapter `scripts/recon_chip_wrap.v` shows the port
mapping; a Phase-4 synthesis adapter adds the `rst`/clock-name translation.

## Exact reproduction
```bash
cd <reconstruction-review worktree>
python review/scripts/rv_make_phase4_golden.py \
    what_a_piece_of_work-noisy.wav 256 recovered/coeffs.json \
    handoffs/reconstruction-review/phase4-golden
```

## Test results
```
wrote .../input.csv and .../golden_output.csv: 256 audio frames -> 512 words each
latency_words to pass to Phase4 compare(): 4
Phase4 read_samples(input)  OK: 512 words, header accepted
Phase4 read_samples(golden) OK: 512 words, header accepted
Phase4 compare(golden,golden): passed=True samples=512 max_abs_err=0
```
Cross-checks: filtered[0]=1 and the echo column match the Phase 2
`reference_vectors.csv` content exactly (same data, corrected schema + echo added).

## Regression status
No regressions possible — additive artifacts only; nothing in Phase 2/3/4 was
modified. The converter imports Phase 4's `results.py` **read-only** to self-verify.
