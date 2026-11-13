# Phase F — Audit remediation — STATUS (cycle 1)

**Date:** 2026-11-13 · **Branch:** `challenge3/phase-f-remediation` ·
**Worktree:** `.worktrees/phase-f` (based on `main` 9893aed) · **Pushed:** no.

## What this phase is
Remediation of the external **"Person 5 — Comprehensive Shortfall Analysis"**
(50 findings). Source audit preserved at `audit-remediation/source-audit.md`.

## Central finding
The auditor reviewed a **stripped candidate folder**, not the repository. The
reviewed RTL already had the Subphase-Q fix but lacked its `ai/`, `README`,
`reports/`, and all repo-wide evidence. So most of §15–45 is **EVIDENCE_EXISTS**
(real, locatable, needs surfacing), not absent.

## Register (all 50 classified) — `audit-remediation/findings.{json,md}`
CONFIRMED 19 · EVIDENCE_EXISTS 20 · ALREADY_RESOLVED 2 · BLOCKED 6 ·
NOT_APPLICABLE 2 · UNVERIFIED 1. (§48 dual EVIDENCE_EXISTS+BLOCKED.)

## Verified this cycle (non-destructive)
- **Provenance:** 11/11 AI transcripts integrity-verified (SHA-256, 22.8 MB) via
  `scripts/verify_provenance.py` → `evidence/provenance-verification.json`.
- **§34 trigger WAV:** `scripts/make_trigger_wav.py` → `evidence/triggered_stream.wav`
  (readback == magic sequence).
- **§6 comments:** comment-neutralized proposed variant
  `proposed/fir_audio_top.destealthed-comments.v` + `evidence/destealth-comments.diff`;
  verified logic byte-identical (non-behavioral).
- **§30 stealth analysis**, **§35–40 hardware procedure**, all category reports authored.

## Deliverables (on this branch)
`audit-remediation/`: source-audit.md, findings.json, findings.md,
evidence-index.json, ai-provenance-report.md, automation-report.md,
rtl-correctness-report.md, hardware-evidence-report.md, bonus-compliance-report.md,
stealth-analysis.md, score-assessment.md, remediation-history.md, final-readiness.md,
scripts/{verify_provenance,make_trigger_wav,destealth_comments}.py, proposed/, evidence/.
`handoffs/phase-f/`: STATUS.md, manifest.json.

## Score (projection, not awarded)
Auditor folder-bound ~20–45/130 → **repo-verified now (sim, no board) ~69–87/130**
→ up to ~108–130 with hardware + transcript packaging. See `score-assessment.md`.

## Open / BLOCKED
- **Hardware (§35–40, §48 residual):** BLOCKED — no board. Nothing fabricated.
- **§18 + transcript coverage:** UNVERIFIED — read 05B rollouts; finalize visible export.
- **Live automation re-run:** deferred (receipts exist).
- **Scribe handoff:** findings staged for Project Scribe `preview` (model-free);
  Scribe remains unactivated (operator config) — do not commit its `config.json`.

## Preserved (do not alter)
Final candidate `CSAW_FIN_worktrees/quality-winner` RTL unchanged; all candidate
branches, golden references, and private transcripts (`.state/`, gitignored) intact.
No reset/force-push.

## Resume next cycle
1. Surface provenance into the submission folder (Codex). 2. Package Bonus A
(05C+05D) + Bonus B (05BB) (Codex). 3. Consolidate canonical README + verify repro
live. 4. Hardware session when a board exists. 5. Review phase for §5/§50/§12/§7.
Do not re-investigate resolved findings without new evidence.
