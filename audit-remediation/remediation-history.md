# Remediation history — Phase F, cycle 1

Bounded cycle (≤5 focused iterations) per the mandate. All work is
non-destructive; the final candidate RTL was **not** modified. Failed attempts
are preserved.

## Baseline work (before iterations)
Built the verified audit baseline: `source-audit.md` (preserved external audit),
`findings.json` + `findings.md` (all 50 findings classified against the full
repo), and the category reports. Validated `findings.json` parses and covers
1–50 with reconciled status counts.

## Iteration 1 — AI provenance consolidation (§15–20) — ACCEPTED
- **Action:** inventoried + integrity-checked the private AI archive.
- **Verification:** `verify_provenance.py --archive .state/phase-07-private` →
  **11/11 transcripts OK**, SHA-256 + sizes match the index, 22,830,216 bytes
  (05A×1, 05B×5, 05C×4, 05D×1). Sampled record structure (05D: 1,466 records, 557
  with tool activity) to confirm substantive sessions.
- **Result:** §15–17, §19, §20 → `EVIDENCE_EXISTS` with integrity proof;
  `ai-provenance-report.md` authored; §18 kept `UNVERIFIED` (honest).
- **Before/after:** auditor saw "no logs in folder" → repo has 11 verified logs
  (not yet surfaced into the submission; surfacing is the recommended action).

## Iteration 2 — Trigger WAV generator (§34) — ACCEPTED
- **Action:** authored `scripts/make_trigger_wav.py` (stdlib only).
- **Verification:** ran it → `evidence/triggered_stream.wav` (328 frames @16 kHz);
  readback confirms samples[160:168] == the magic sequence
  `[32512,-32511,23100,-23101,28050,-28051,-15556,15555]`.
- **Result:** §34 `CONFIRMED` gap → remediated; stimulus ready for the hardware
  procedure. Also empirically confirmed §5 (complement-pair pattern).
- **Before/after:** no generator in folder → verified generator + WAV.

## Iteration 3 — Stealth analysis (§30) — ACCEPTED
- **Action:** authored `stealth-analysis.md` — two-sided: trigger-specificity
  evidence (0 false in 481,082 words) *and* honest detectability caveats
  (§5/§6/§9/§50).
- **Result:** §30 `CONFIRMED` gap → remediated with a submission-facing doc that
  does not overstate stealth.

## Iteration 4 — §6 giveaway-comment neutralization — ACCEPTED (after 1 failed attempt)
- **Failed attempt #1 (preserved):** `destealth_comments.py` with a repo-relative
  `--src CSAW_FIN_worktrees/...` → `FileNotFoundError` (that worktree is a sibling
  of the repo root, not inside it). No artifact written; corrected to an absolute
  path.
- **Action:** staged a comment-neutralized *proposed* variant
  `proposed/fir_audio_top.destealthed-comments.v` (final candidate untouched).
- **Verification:** script asserts **8/8 comment replacements, 8 lines changed
  (all comments), non-comment/logic lines byte-identical**; unified diff saved to
  `evidence/destealth-comments.diff`. Change is provably non-behavioral (identical
  synthesis + untriggered output).
- **Result:** §6 remediated as a reviewable, zero-risk patch. Not force-applied to
  the candidate (mandate: no silent alteration of the final candidate).
- **Note:** identifier giveaways (`MAGIC_*`, `bypass_*`) remain; renaming is a
  further proposal under §7 (behavioral-adjacent → review phase).

## Iteration 5 — Hardware capture procedure (§35–40) — ACCEPTED (blocker recorded)
- **Action:** authored `hardware-evidence-report.md` with an executable, numbered
  board bring-up + capture procedure that consumes the Iteration-2 trigger WAV.
- **Result:** §35–40 `BLOCKED` recorded precisely (no board); nothing fabricated;
  evidence can be captured immediately once a board is available.

## Proposed-not-applied (security-sensitive; for a dedicated review phase)
- §5/§9 de-patterned, in-band magic values; §50 left-channel bypass source change;
  §7 submodule/identifier concealment; §10 preamble gating; §12 `[2:0]` counter
  narrowing (provably equivalent; needs a bit-identity regression before adoption).
These alter a security-sensitive block, so per the mandate they are proposed, not
silently applied — they require re-running the baseline check + verification suite.

## Not performed this cycle (next-cycle actions)
- Live re-execution of `run.py doctor` / `reproduce.py` (receipts already exist).
- Reading the 05B rollouts to resolve §18.
- Packaging the surfaced provenance + Bonus A/B into the submission folder
  (Codex-owned per mandate §11).
