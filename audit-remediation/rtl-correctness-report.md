# RTL correctness & engineering-quality report (findings §12–13, §46–49; stealth §5–11, §14, §50)

**Target:** final candidate `CSAW_FIN_worktrees/quality-winner/experiments/phase05/05b-astra/rtl/fir_audio_top.v`.
**Rule observed:** the trigger/payload are security-sensitive specialized logic.
Functional defects are corrected only with isolated, verified patches; stealth/
behavior changes are **proposed for separate review, never silently applied**
(Phase F mandate §7–8).

## Correctness findings

### §46 — Post-bypass restart edge case → `ALREADY_RESOLVED`
Lines 204–209 are the **verified Subphase-Q fix**: when `bypass_remaining<=1`, the
final payload sample is correctly reclassified as the next matcher's `MAGIC_0`
start (`magic_position <= (left_sample==MAGIC_0) ? 1 : 0`). Verified **30/30
directed cases** across the boundary plus **481,082 full-audio words, 0 mismatch**
(consolidation.md; candidate `reports/`). The only residue is readability.
*Action:* optional neutral clarifying comment; no logic change.

### §47 — `bypass_active` frame-boundary timing → `NOT_APPLICABLE`
*Auditor concern:* "single-cycle on the frame boundary; a glitch in `end_frame`
vs `new_sample` ordering would propagate."
*Analysis:* `bypass_active` is **not** single-cycle — it is a multi-frame register
asserted for the whole 128-frame window (set at line 217, cleared at 206). Both
`new_sample` (L0) and `end_frame` (R0) are **single-`ICE_CLK`-domain** strobes
derived from the *same* 2-FF-synchronized I2S lines (lines 71–108); within a frame
L0 strictly precedes R0, so `bypass_active` is stable when sampled at `end_frame`
(line 242). Same clock domain ⇒ no CDC/glitch path. No real-silicon vs simulator
divergence exists for this signal. Confirmed consistent across 481,082 simulated
words (no spurious bypass). *Action:* document; no change.

### §48 — "Bit-identical" baseline claim → `EVIDENCE_EXISTS` + `BLOCKED` (hardware)
The proof the auditor couldn't see in the folder exists repo-wide:
- Phase 2/3: netlist ≡ reconstructed RTL ≡ sw model, **9,904 exact comparisons**,
  impulse/step/sine/chirp/random/boundary + real audio, latency=2, echo exact.
- Subphase R: independent blind re-derivation of coefficients and numeric behavior.
- Phase 5S: **516 exact comparisons/case**; Subphase Q: **481,082 words, 0 mismatch**.
- Phase 6: 69 artifact hashes matched; bitstream SHA receipted.
The arithmetic is `y = sat16((acc + 2^14) >>> 15)` (round-half-toward-+∞ then
saturate), matching the recovered bitstream.
**Residual:** a real-silicon corner (rounding/BRAM-init) can only be *finally*
closed on a board → the on-board baseline check is `BLOCKED` (see
`hardware-evidence-report.md`). The reconstruction is behavioral, not gate-exact,
so this residual is genuine though well-mitigated.

### §49 — No external reset on trigger state → `CONFIRMED` (very low)
Only power-up init (lines 256–266). This is **faithful to the recovered baseline**,
which is itself reset-less (Phase 2); the core is held in idle by the adapter.
iCE40 FFs power up to 0, so `magic_position/bypass_remaining/bypass_active` start
clean. A mid-stream brownout is out of scope for the challenge. *Action:* **no
change** — adding a reset would deviate from the recovered design without benefit.

## RTL-quality nits

### §12 — 4-bit `magic_position`, unreachable states 8–15 → `CONFIRMED` (minor) — proposed fix
`magic_position` only ranges 0–7 (line 178 `reg [3:0]`; `case` default 193 covers
8–15, which are never entered). *Proposed:* narrow to `reg [2:0]` and drop the
`default` (positions are exhaustive for 3 bits). **Provably equivalent** (state
never exceeds 7). Needs a bit-identity regression before adoption. Saves a few
FFs/LUTs and removes a synthesis-report red flag. Listed as a proposed patch in
`remediation-history.md` (not applied to the final candidate this cycle).

### §13 — `<= 8'd1` countdown comparator → `CONFIRMED` (negligible) — NO CHANGE
The `<=1` test is integral to the **verified** Q boundary fix. Rewriting to `==0`
would change the boundary semantics the 30/30 suite validates. Accept the sliver
of overhead. *Action:* no change.

## Stealth characteristics (design review; §5–11, §14, §50)
These are real properties of the RTL, scored under Trojan Quality, not functional
bugs. Full stealth treatment (specificity evidence + honest detectability) is in
`stealth-analysis.md`. Dispositions:

| # | Property | Disposition |
| --- | --- | --- |
| §5 | Patterned magics (complement pairs `5A3C`/`A5C3`…) | **Propose** de-patterned, in-band values (security-sensitive; review) |
| §6 | Giveaway comments (L162–167, 208) | **Remediated** — comment-neutralized *proposed* variant (non-behavioral); see `remediation-history.md` |
| §7 | Top-level placement | Propose submodule/coeff-init concealment (review) |
| §8 | Word-level trigger (PCM-visible) | Tradeoff: robust to oversampling; propose framing/power trigger (review) |
| §9 | Clipping-peak magics (audible) | Fold into §5 proposal (mid-scale values) |
| §10 | Armed from power-up | Propose preamble-gated arming (review) |
| §11 | No decoys/anti-fuzz | Propose decoy logic (weigh vs area/stealth-by-smallness) |
| §14 | ICE_LED tracks `busy` | Keep (baseline-faithful); altering is itself a tell |
| §50 | L==R during bypass (signature) | **Propose** mitigation (drive left from a processed path, not raw echo) — review |

**Why propose, not apply:** changing any of §5/§7/§8/§10/§50 alters the
trigger/payload or output behavior of a security-sensitive block. Per mandate they
go to a dedicated review phase so the baseline check and verification suite can be
re-run against the change. §6 and §12 are the only ones safe enough to stage as
patches now (non-behavioral / provably-equivalent), and even those are staged, not
forced onto the final candidate.

## Resource/timing (recorded, not re-run this cycle)
Candidate P&R (from candidate `README`/receipts): iCE40-UP5K SG48 @10 MHz,
**3,662/5,280 LC (69.4%), 0 DSP, 0 BRAM, 9 IO**, Fmax **15.13 MHz**, pack/unpack
round-trip OK. +483 LC vs the 3,179-LC recovered baseline. No blocking synthesis
warnings in the receipts. Re-synthesis to confirm is a next-cycle action.
