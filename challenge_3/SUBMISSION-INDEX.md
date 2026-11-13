# CSAW 2026 Challenge 3 — submission index

Navigational entry point for this documentation repository. It ties together the
final candidate, the audit remediation, and the AI-provenance package. Generated
by the Phase F remediation pass (2026-11-13).

## Final candidate (the submission)
- **05B / "Astra"** — a bounded filter-bypass Trojan on the recovered 63-tap FIR
  audio filter, Subphase-Q quality revision. The untriggered baseline is
  bit-identical to the original bitstream (verified in simulation, 481,082 words,
  0 mismatch).
- **Branch:** `challenge3/quality-winner` (this repo). Candidate package:
  `experiments/phase05/05b-astra/` (RTL, constraints, tests, reports, `ai/`,
  `manifest.json`). Trigger/payload specifics and reproduction commands are in the
  candidate `README.md` and the Phase 8 `handoffs/phase-08/submission-README.md`.
- **Backups / additional Trojans (Bonus A):** `challenge3/05a-luna`,
  `challenge3/05c-opus-architecture`, `challenge3/05d-opus-dsp`.
- **Covert channel (Bonus B):** `challenge3/05bb-bonus-b` (simulation-tier).

## Audit remediation (Phase F) → `audit-remediation/`
Response to the external 50-finding "Person 5" audit, evaluated against the whole
repository. Start at `audit-remediation/findings.md`.
- Register: `findings.json` / `findings.md` (19 CONFIRMED, 20 EVIDENCE_EXISTS,
  2 ALREADY_RESOLVED, 6 BLOCKED, 2 N/A, 1 UNVERIFIED).
- Reports: `ai-provenance-report.md`, `automation-report.md`,
  `rtl-correctness-report.md`, `hardware-evidence-report.md`,
  `bonus-compliance-report.md`, `stealth-analysis.md`, `score-assessment.md`,
  `final-readiness.md`, `remediation-history.md`.
- Central finding: the auditor reviewed a **stripped candidate folder**, so most of
  §15–45 is evidence that exists repo-wide but was absent from that folder.

## AI provenance → `submission/ai-provenance/`
Evidence the Trojan was AI-generated (Creative GenAI, 35 pts; mandatory-logs rule).
Start at `submission/ai-provenance/PROVENANCE.md`.
- 11 raw transcripts, **11/11 SHA-256-verified**; authoritative model list;
  deterministic metrics; a 9-agent adversarially-calibrated audit.
- **Calibrated Creative-GenAI tier: Strong (28)** for the selected 05B (Exemplary
  not claimed; 05C independently reaches Exemplary on provenance). Raw logs are
  private (home paths/email) — provided to judges out-of-band, not in this repo.

## Scoring snapshot (projection, not awarded)
Repository-verified, simulation, no board: **~69–87 / 130**
(Creative GenAI 28 · Trojan Quality 15–20 · Automation 9–12 · Docs 9–12 ·
Hardware 0 · Bonus A +10 sim · Bonus B +5 sim). Full basis in
`audit-remediation/score-assessment.md`.

## Open items
- **Hardware demonstration is BLOCKED** (no board) — the single biggest locked
  lever (~+40 across Category 5 + Bonus A/B board tiers). Executable capture
  procedure in `audit-remediation/hardware-evidence-report.md`.
- **Provenance packaging** (transcript bundle + 05B `apply_patch`→RTL authorship
  chain) is the top no-hardware action; see `PROVENANCE.md` §6.
- A comment-neutralized RTL variant is staged as a *proposal* under
  `audit-remediation/proposed/`; the final candidate RTL is unchanged.
