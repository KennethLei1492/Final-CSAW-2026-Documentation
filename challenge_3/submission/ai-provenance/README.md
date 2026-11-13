# AI-provenance package

Submission-facing evidence for **Creative Use of Generative AI (35 pts)** and the
mandatory-AI-logs rule. Read `PROVENANCE.md` first.

| File | What it is |
| --- | --- |
| `PROVENANCE.md` | Authoritative writeup: logs, model attribution, methodology, calibrated tiers, gaps, actions |
| `model-list.json` | Authoritative per-candidate model attribution (+ superset caveat) |
| `provenance-metrics.json` | Deterministic metrics from all 11 transcripts (records, roles, tool activity, model strings, timespans) |
| `provenance-audit-results.json` | 9-agent audit output: characterizations + adversarial verdicts + completeness critic |
| `digests/05{A,B,C,D}.md` | Per-candidate sanitized structural digests |

**Verification:** `../../audit-remediation/scripts/verify_provenance.py --archive <logs>`
re-checks 11/11 SHA-256 (proof in `../../audit-remediation/evidence/provenance-verification.json`).
Regenerate metrics with `../../audit-remediation/scripts/provenance_extract.py`.

**Calibrated result:** selected 05B = **Strong (28)** (Exemplary not claimed);
05C independently Exemplary (35) on provenance but is a backup. Raw transcripts
are private (home paths/email) — provided to judges out-of-band, not in the public repo.
