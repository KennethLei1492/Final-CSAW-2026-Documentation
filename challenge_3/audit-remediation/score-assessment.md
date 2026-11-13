# Scoring assessment (repository-wide re-estimate)

**These are projections to guide remediation priority — not awarded scores.**
Official rubric: `handoffs/phase-05/cycles/05S-004/official-challenge.md`. The
auditor's estimate was explicitly conditioned on *"in folder"* visibility; this
re-estimate uses the whole repository and the evidence verified in Phase F.

## Summary

| # | Category | Max | Auditor (folder) | **Verified now (sim, no board)** | With hardware | Confidence |
| --- | --- | ---: | :---: | :---: | :---: | :---: |
| 1 | Creative Use of GenAI | 35 | ~5–15 | **28 (Strong; 21–28 band)** | 35 (conditional) | Med-High |
| 2 | Trojan Quality | 25 | ~15–20 | **15–20** | 20–25 | Med-High |
| 3 | System Automation | 15 | ~0–5 | **9–12** | 12–15 | Med-High |
| 4 | Documentation & Reproducibility | 15 | ~0–5 | **9–12** | 12–15 | Med-High |
| 5 | Hardware Demonstration | 10 | ~0 | **0** | 6–10 | High |
| — | **Base subtotal** | **100** | ~20–45 | **54–72** | 78–100 | — |
| A | Bonus — additional trojans | 20 | 0 | **+10** | +20 | Med |
| B | Bonus — covert channel | 10 | 0 | **+5** | +10 | Med-High |
| — | **Total** | **130** | ~20–45 | **~69–87** | ~108–130 | — |

The auditor's own note — *"fixing the top three would roughly double the score"* —
is directionally right, but the Phase F finding is that **most of the gain is
surfacing evidence that already exists**, not new engineering. The one gain that
genuinely requires new resources is **hardware** (Category 5 and the board tiers
of Bonus A/B, ~+40 combined).

## Per category

### 1. Creative GenAI — 35 — *calibrated Strong (28) for the selected 05B*
Calibrated by the Phase F 9-agent provenance audit (adversarial, biased to refute):
`submission/ai-provenance/{PROVENANCE.md,provenance-audit-results.json}`.
- **Have:** 11 integrity-verified transcripts (22.8 MB, 11/11 SHA-256), authoritative
  model list, dense test-in-the-loop activity across the full iCE40 toolchain for all
  four candidates, Subphase-Q iterate-against-tests (2/30→30/30). Per-candidate tiers:
  05A/05B/05D Strong (28), 05C Exemplary (35, backup).
- **Deficiencies (why 05B is Strong, not Exemplary):** diff-level AI authorship not
  demonstrated; 05B role fields empty (Codex schema); build/test "markers" are string
  counts, not confirmed executions; programmatic/AST insertion and agentic retrieval
  not shown.
- **To reach 35 (conditional):** add the 05B `apply_patch`→RTL authorship chain +
  confirmed executed tool-call records + demonstrated retrieval/insertion. **Exemplary
  is not claimed until then.** Mandatory-logs DQ risk is LOW (logs present + verified).

### 2. Trojan Quality — 25 — *est. 15–20 now*
- **Have:** baseline bit-identical in sim (481,082 words, 0 mismatch), highly
  specific trigger (0 false in real audio), payload that defeats the filter gate,
  small footprint (+483 LC, 0 DSP/BRAM).
- **Deficiencies:** bounded 8 ms payload (§1), single payload mode (§3), patterned
  & clipping magics (§5/§9), giveaway comments (§6 — remediated), L==R signature
  (§50). "Judged on the bench" → hardware evidence thin.
- **Risk:** §48 — if the real bitstream diverges on a corner the on-board baseline
  check could fail and zero this category. Mitigated (co-sim vs netlist) but
  board-unproven.
- **To reach 20–25:** land the baseline check on hardware; adopt §5/§50 stealth
  upgrades via the review phase.

### 3. Automation — 15 — *est. 9–12 now*
- **Have:** one-command build+sim+synth+validate (`run.py validate`,
  `reproduce.py`), pinned toolchain.
- **Deficiencies (§24):** generation→insertion not wired into one command; board
  stage gated. **To reach 12–15:** add the orchestration wrapper + an automated
  on-board program/verify.

### 4. Documentation & Reproducibility — 15 — *est. 9–12 now*
- **Have:** candidate README, Phase 2/3 reports, Phase 8 submission draft +
  requirements, reproduction recipe, new stealth analysis, trigger generator.
- **Deficiencies:** consolidate to one canonical submission README; verify the
  repro recipe live; package final transcripts. Exemplary needs no-guesswork
  board reproduction (gated).

### 5. Hardware Demonstration — 10 — *est. 0 now*
- **Have:** nothing on hardware (no board). **To reach 6–10:** run the procedure in
  `hardware-evidence-report.md` on a board.

### Bonus A — 20 — *+10 now* (4 distinct trojans; 05C+05D recommended; sim tier 5 each; board tier 10 each).
### Bonus B — 10 — *+5 now* (05BB covert channel, BER 0/336 in sim; board bit-exact → 10).

## Priority order (by verified points-per-effort)
1. **Surface AI provenance into the submission** (Cat 1, no hardware) — largest lever.
2. **Package Bonus A (05C+05D) + Bonus B (05BB)** (+15 sim, no hardware).
3. **Consolidate documentation + verify repro live** (Cat 4; Cat 3 wrapper).
4. **Hardware session** (Cat 5 + board tiers of A/B + closes §48) — gated on a board.
5. **Stealth upgrades §5/§50** via review phase (Cat 2 toward Exemplary).
