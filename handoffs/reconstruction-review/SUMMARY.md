# Reconstruction Review — Handoff Summary (Subphase R)

**Independent reviewer → Phase 3 (baseline owner) + Project Scribe.**
Not merged into any engineering branch; no force-push; no Phase 2/3/4 files modified.

## Commits
- **Reviewed (source):** Phase 2 `challenge3/02-reverse-engineering` **1befb30**;
  Phase 4 `challenge3/04-infrastructure` **2da1d72**.
- **Phase 3** `challenge3/03-baseline` was at **1befb30** (no commits beyond Phase 2
  at review time; its uncommitted WIP was not read).
- **Review branch:** `challenge3/reconstruction-review` (based on 1befb30); this
  handoff + `review/` are its only additions.

## Verdict
The Phase 2 reconstruction is **accurate and well-supported**. Every externally
observable behavior was independently corroborated across **6 evidence types**
(bitstream structure, tool source, integer/DTFT math, gate-level sim, adversarial
sim, official-repo reference). **No behavioral defect found.** **1 actionable
integration gap (R-001)** with a verified fix. Full detail: `review/defect-register.md`,
`review/quality-report.md`; scripts in `review/scripts/`, logs in `review/logs/`.

## Confidence per claim
| Claim | Verdict | Confidence |
|---|---|---|
| Provenance (.bin→.asc byte-identical; sha256 matches) | confirmed | very high |
| Pins 36/34/32/31, Philips 16-bit MSB-first L/R, WS 1-bit-early | confirmed vs official `audio_bridge.py` | very high |
| 2-frame latency | confirmed vs README "two frames later" + measured | very high |
| No DSP (0 MAC16) | confirmed via authoritative `icebox_vlog` + mirror-symmetry | very high |
| One zero-init 64×16 BRAM; "BRAMs:2" = y-norm artifact | confirmed (icebox_vlog + icebox_stat source) | very high |
| 63-tap linear-phase FIR; Σ=32768; center 13920 | confirmed (math + canonical + **blind** re-derivation) | very high |
| Rounding = round-half-toward-+∞ | **uniquely** discriminated vs 4 alternatives | very high |
| Accumulator wide enough; saturation exact (both rails) | confirmed (closes Phase 2 §9.2) | very high |
| Real-audio bit-exact (sw==hw) | 2048/2048 on 2 datasets, triangulated | very high |
| Right channel ignored (filter/echo use LEFT only) | confirmed (R≠L, 512/512) | very high |
| Reconstruction RTL == original (C12) | confirmed 1024/1024, LAT measured=2 | very high |

## Claims strengthened beyond Phase 2
Rounding mode uniquely pinned · accumulator-width open item closed · DSP
non-use upgraded (mirror-identical across both columns + icebox_vlog=0) ·
"BRAMs:2" mechanism verified in tool source · interface re-confirmed vs the
official repo (not just comments).

## Open items carried forward (not defects)
- **O1** original MAC micro-architecture (direct/transposed, BRAM addressing, exact
  acc width) — behavior-irrelevant, correctly open.
- **O2** individual LED/RGB pin roles (38–41). Note: the reconstruction RTL's
  LED/RGB logic is a **plausible guess, not recovered** — fine for the audio path,
  but don't rely on LED behavior for any bit-identity check.
- **O3** no on-hardware run yet (all evidence is bitstream + gate-level sim).
- **O4 → R-001** Phase 4 golden-CSV/adapter handoff gap; fix provided.

## For Phase 3
1. You may build the Trojan baseline on `recovered/rtl/fir_audio_top.v` with high
   confidence that untriggered filtered output is bit-identical to the original.
2. To unblock Phase 4 end-to-end verification, consume the R-001 artifacts
   (`handoffs/reconstruction-review/phase4-golden/` + `rv_make_phase4_golden.py`)
   and provide a `phase4_dut(clk,rst,bclk,lrclk,sd_in,sd_out)` adapter. See R-001.

## Process note
An adversarial 3-lens refutation panel was launched to stress-test these claims
but was **stopped before completion per operator request**; the inline skeptical
analysis above (4-way rounding discrimination, worst-case saturation, R≠L,
two datasets, external ground-truth, blind re-derivation) stands on its own.
