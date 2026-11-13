# Audit remediation register — Phase F

**Scope.** Verdicts for all 50 findings of the external *"Person 5 — Comprehensive
Shortfall Analysis"* (`source-audit.md`), evaluated against the **full repository**,
not the stripped folder the auditor reviewed. Full per-finding detail
(evidence, action, responsible agent, verification method) is in `findings.json`;
this file is the readable summary. Scoring projections are in `score-assessment.md`.

## The central correction

The auditor reviewed an isolated **"Person 5 folder"** — a bare 05B/Astra RTL
export. The reviewed `fir_audio_top.v` already carried the Subphase-Q boundary
fix, but the folder lacked the candidate's own `ai/`, `README.md`, `reports/`,
`manifest.json`, and all repo-wide automation, provenance, and bonus evidence.
As a result, **the majority of §15–45 reports absence-in-folder, not
absence-in-project.** Those are classified `EVIDENCE_EXISTS`: the artifact is
real and locatable, and the corrective action is to *surface* it into the
submission, not to build it.

What survives as genuinely open, repository-wide:
- **Hardware demonstration (§35–40, HW part of §48):** `BLOCKED` — no Hackster
  board in inventory. Cannot be produced without hardware; will not be fabricated.
- **Final AI-transcript coverage (§18, part of §15):** `UNVERIFIED` — raw logs
  exist; sufficiency/coverage for the "AI authored the hardware" rule must be
  verified before submission.
- **RTL stealth characteristics (§5, §6, §50 especially):** `CONFIRMED` and real,
  but they are design choices of a security-sensitive block — proposed for review,
  not silently rewritten.

## Status tally

| Status | Count | Findings |
| --- | ---: | --- |
| `CONFIRMED` | 19 | 1–14, 24, 30, 34, 49, 50 |
| `EVIDENCE_EXISTS` | 20 | 15–17, 19–23, 25, 26, 28, 29, 31–33, 41, 43–45, 48\* |
| `ALREADY_RESOLVED` | 2 | 27, 46 |
| `BLOCKED` | 6 | 35–40 |
| `NOT_APPLICABLE` | 2 | 42, 47 |
| `UNVERIFIED` | 1 | 18 |

\*§48 is dual: `EVIDENCE_EXISTS` (co-sim proof chain) + `BLOCKED` (hardware-only residual).

Of the 19 `CONFIRMED`, **15 are design/stealth characteristics or scoring
judgments** (§1–11, 14, 49, 50, and partly 30) rather than functional defects;
§24 is a partial-automation ceiling; §30 and §34 are documentation gaps
remediated this cycle.

## By category

### Trojan Quality §1–14 — all CONFIRMED (present in the final RTL)
Factual design/stealth properties of `fir_audio_top.v`. The scoring-relevant ones:
- **§5 obvious/patterned magic, §6 giveaway comments, §9 clipping-peak magics, §50 L==R-during-bypass signature** are the real stealth weaknesses.
- **§6 is remediated** this cycle as a comment-neutralized *proposed* RTL variant (non-behavioral; see `remediation-history.md`).
- **§12** (4-bit `magic_position`, unreachable 8–15) → proposed `[2:0]` narrowing.
- **§13** (`<=1` countdown) → **NO CHANGE**: it is part of the verified Q boundary fix.
- §1–4, 7, 8, 10, 11, 14 are tradeoffs; mitigations **proposed for separate review**, candidate not silently altered.

### Creative Use of GenAI §15–20 — EVIDENCE_EXISTS (except §18 UNVERIFIED)
The 35-point category and the single biggest lever. Logs are **not** missing
project-wide: **11 raw `.jsonl` rollout transcripts** are cataloged with SHA-256
in `.state/phase-07-private/index.json`; Phase 8 `ai/index.json` exports visible
prompts/responses/tool calls; the model list is in `ai/model-provenance.json`.
§18 (agentic-pipeline strength) is **UNVERIFIED**: partial agentic evidence
exists (05C 7-agent eval; test-in-the-loop Q fix) but the *selected* 05B was
session-authored, so Exemplary is not claimed without a transcript review. See
`ai-provenance-report.md`.

### System Automation §21–26 — EVIDENCE_EXISTS, with §24 CONFIRMED (partial)
A manifest-driven `infrastructure/run.py` (doctor/sim/synth/pnr/pack/icetime/
validate) plus Phase 8 `reproduce.py` gates exist. §24: one-command
build+sim+validate is real, but "generation → insertion → programmed board in one
command" (Exemplary) is not met — generation isn't wired in and the board stage is
hardware-gated. See `automation-report.md`.

### Documentation §27–34 — mostly EVIDENCE_EXISTS / ALREADY_RESOLVED
§27 README is `ALREADY_RESOLVED` (present in the current candidate). §28–29, 31–33
exist (README + Phase 8 docs). **§30 (stealth analysis)** and **§34 (trigger-WAV
generator)** are genuine gaps — **both remediated this cycle**.

### Hardware Demonstration §35–40 — all BLOCKED
No board. Executable capture procedures are provided in
`hardware-evidence-report.md`; nothing is fabricated.

### Bonus A §41–42 — EVIDENCE_EXISTS / NOT_APPLICABLE
§41: **four distinct trojans exist** (05A/05B/05C/05D, distinct trigger *and*
payload), preserved in Phase 8 `history/development.bundle` → up to **+10 in sim**,
+20 with hardware. §42: `NOT_APPLICABLE` — the rubric allows separate builds. See
`bonus-compliance-report.md`.

### Bonus B §43–45 — EVIDENCE_EXISTS (simulation tier)
A real covert channel (05BB) emits `CSAW26-BONUS-B`, recovered bit-exact by a host
decoder, **BER 0/336**, 625/312 bit/s — **simulation-only (5/10 ceiling)**; the
bit-exact-on-board (10) tier is `BLOCKED`.

### RTL Correctness §46–50
- **§46 ALREADY_RESOLVED** (the verified Q fix).
- **§47 NOT_APPLICABLE** — timing analysis shows `bypass_active` is a multi-frame,
  single-clock-domain register; no glitch path (see `rtl-correctness-report.md`).
- **§48 EVIDENCE_EXISTS + BLOCKED** — co-sim proof chain is abundant; real-silicon
  corner closes only on hardware.
- **§49 CONFIRMED (very low)** — reset-less init is faithful to the recovered
  baseline; **NO CHANGE**.
- **§50 CONFIRMED (real)** — L==R during bypass is a genuine signature; mitigation
  **proposed for review**.
