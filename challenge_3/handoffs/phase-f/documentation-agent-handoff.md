# Documentation-agent handoff — Phase F

**For:** Project Scribe (`DocumentAgent/openclaw-project-scribe/`), the canonical
documentation maintainer. **Status:** Scribe is *prepared, not activated* (model
placeholder, gateway stopped) — so this is a **model-free** handoff: the Phase F
deliverables are committed to the repo and are therefore visible to Scribe's
`git.sourceFiles` evidence surface on its next `preview`/`run`. **Do not** modify
or commit Scribe's `config.json` (gitignored, operator-owned).

## What to ingest (all on branch `challenge3/phase-f-remediation`)
- **Register:** `audit-remediation/findings.json` (authoritative, machine-readable),
  `audit-remediation/findings.md` (readable). 50 findings classified.
- **Source audit (preserved):** `audit-remediation/source-audit.md`.
- **Reports:** `ai-provenance-report.md`, `automation-report.md`,
  `rtl-correctness-report.md`, `hardware-evidence-report.md`,
  `bonus-compliance-report.md`, `stealth-analysis.md`, `score-assessment.md`,
  `final-readiness.md`, `remediation-history.md`.
- **Verification evidence:** `audit-remediation/evidence/*` (provenance SHA-256
  proof, trigger WAV, comment diff), `handoffs/phase-f/manifest.json` (hashes).

## Canonical claims to carry into the submission narrative (traceable)
1. **AI provenance exists and is integrity-verified** — 11 raw transcripts,
   11/11 SHA-256 match (`evidence/provenance-verification.json`). Cite instead of
   the folder's "no logs" impression.
2. **Four distinct trojans (Bonus A) + a measured covert channel (Bonus B, sim)** —
   see bonus report; keep simulation and hardware strictly distinct.
3. **Hardware demonstration is BLOCKED (no board)** — never render simulation as
   hardware; use the staged capture procedure when a board exists.
4. **Model labels reconciled** — orig 05B `gpt-6-luna`, Subphase-Q `gpt-6-astra`,
   05C/05D Claude Opus. State both runtime ids and requested labels once, clearly.

## When Scribe is activated (operator step)
Run a model-free `preview` first; it is known to exceed `maxEvidenceChars` with
multiple candidate roots, so scope the evidence to `audit-remediation/` +
`handoffs/phase-f/` or raise the cap via a temporary, uncommitted config copy.
Do not duplicate these reports — summarize and reference them as canonical.
