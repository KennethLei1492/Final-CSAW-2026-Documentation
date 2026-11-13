# AI provenance report (findings §15–20)

**Category:** Creative Use of Generative AI — 35 points, the single largest
scoring lever and the subject of a hard disqualification rule:
> *"No hardware may be written by human users. This will be confirmed with the
> submitted AI logs."* (official challenge)

**Verdict:** The auditor's "no AI logs / prompts / models / pipeline / RE
artifacts **in the folder**" is accurate *for the stripped folder they saw* and
**false for the repository.** Findings §15–17, §19, §20 are `EVIDENCE_EXISTS`;
§18 (pipeline strength) is `UNVERIFIED` pending a transcript-coverage read. No
provenance was fabricated; everything below is verified on disk.

## 1. The raw transcripts exist and are integrity-verified

`.state/phase-07-private/` holds **11 raw agent-session transcripts** (`.jsonl`),
cataloged with SHA-256 in `index.json`. On 2026-11-13 I recomputed every file's
SHA-256 and byte length (`scripts/verify_provenance.py`, output
`evidence/provenance-verification.json`):

**11 / 11 verified OK — SHA-256 and sizes match the index; 22,830,216 bytes total.**

| Candidate | Transcripts | Source agent | Origin |
| --- | ---: | --- | --- |
| 05A (Luna) | 1 | Codex | `~/.codex/sessions/.../rollout-*.jsonl` |
| 05B (Astra) — **selected** | 5 | Codex | `~/.codex/sessions/.../rollout-*.jsonl` |
| 05C (Opus Architecture) | 4 | Claude | `~/.claude/projects/.../*.jsonl` |
| 05D (Opus DSP) | 1 | Claude | `~/.claude/projects/.../*.jsonl` |

These are **private and correctly gitignored** (`.state/`). They are *development
records*, not yet a submission-packaged export — see §5.

## 2. The transcripts are substantive (sampled, not dumped)

Record-structure sampling (`scripts` run inline, content not reproduced):

- **05B (Codex rollout):** `session_meta`, `turn_context`, `response_item`,
  `event_msg`, `token_usage_record` — a complete Codex session: model context,
  response items, and token accounting. (Codex encodes tool calls inside
  `response_item`; a naive `tool_use` string match does not flag them, so absence
  of a flag is **not** absence of tool use.)
- **05C (Claude):** `user`, `system`, `api-request`, `agent-name`,
  `bridge-session` records — a multi-agent Claude Code session.
- **05D (Claude):** **1,466 records — 319 assistant, 122 user, 117 system, and
  557 records showing tool/function activity** — a rich agentic session with
  heavy tool use.

This directly supports §15 (logs exist), §16 (prompts + responses present), and
§19 (iterative tool-driven development).

## 3. In-folder provenance (what the auditor overlooked even in the candidate)

The current 05B candidate folder (`.../05b-astra/ai/`, also in the final
`quality-winner`) already ships:

- `model-provenance.json` — agent **Codex / OpenAI**, requested label **Astra**,
  runtime id "not exposed", research models consulted (*Answer Verification*,
  *Task Decomposition*, no code imported), official-spec URL + blob SHA,
  `physical_hardware: not available`.
- `session-record.md` — a provenance **summary** (explicitly *not* a raw chat
  export) of the authored logic, verification, and baseline lineage.
- `rejected-revisions.md`, `source-hashes.json`.

So §17 (model list) and part of §15–16 are satisfied *inside the candidate*, not
merely "claimed in a comment."

## 4. Model list — the "Luna vs Astra" item is documented, not an error

The Phase 8 submission draft reconciles the labels explicitly:
> *"The requested labels were Luna 5.6, Astra, Claude Opus Architecture and
> Claude Opus DSP … Original 05B records identify `gpt-6-luna`; its subsequent
> quality work identifies `gpt-6-astra`."*

So the selected candidate's authorship splits cleanly: **original 05B build =
`gpt-6-luna` (Codex/OpenAI); Subphase-Q quality work = `gpt-6-astra`.** 05C/05D =
Claude Opus. The one required action is to make sure the *final* submission's
model list states both runtime ids against the requested labels in one place
(it already does in `submission-README.md`; the candidate `README`/`ai/` should
point to it).

## 5. Honest gaps (do not overclaim)

- **§18 agentic pipeline — `UNVERIFIED`.** 05C (7-agent evaluation workflow) and
  05D (557 tool-activity records) are strong agentic evidence. The **selected**
  05B was a Codex session; whether it rises to the rubric's *Exemplary*
  "agentic loops / programmatic (AST/netlist) insertion" requires actually
  reading the 05B rollouts. **Do not claim Exemplary for 05B without that read.**
- **Transcript coverage/sufficiency — open.** Phase 7/8 note live-session cutoffs
  and that "comprehensive final transcript coverage" is unverified. Some sessions
  may omit post-capture responses.
- **Summary ≠ raw.** `session-record.md` is a summary; the raw `.jsonl` files are
  the actual logs. The submission must ship the raw (or a faithful visible
  export), not only the summary.

## 6. Recommended actions (surfacing, not fabrication)

1. **Codex:** finalize the Phase 8 `ai/index.json` visible-transcript export
   (prompts + responses + tool calls, with credential redactions) covering all
   four candidates + Subphase Q; include the SHA-256 chain back to the raw
   `.jsonl`.
2. **Codex:** place a `ai/PROVENANCE.md` pointer in the candidate folder linking
   the model list, the raw-log index, and `provenance-verification.json`.
3. **Claude:** read the 05B rollouts and score §18 honestly before any Exemplary
   claim; record the finding in `remediation-history.md`.
4. **Operator:** confirm whether the private raw transcripts are cleared for the
   judges' package (the repo is public; raw logs stay out of Git and go to judges
   through the submission channel).

## Projected effect (calibrated by the Phase F provenance audit)

A 9-agent audit (characterize → adversarial verify → completeness critic;
`submission/ai-provenance/provenance-audit-results.json`) calibrated the tiers
**downward to refute overclaims**:

- **Selected 05B: Strong (28)** — real Codex harness + a diverse iCE40 toolchain
  loop exceed prompt-engineering-with-manual-integration, but **Exemplary (35) is
  NOT endorsed**: diff-level AI authorship is unproven, 05B's role fields are empty
  (Codex schema), and programmatic/AST insertion and agentic retrieval are not
  demonstrated. Band: Proficient (21) downside → Strong (28) center.
- Per candidate: 05A Strong (28), **05B Strong (28)**, 05C **Exemplary (35)**
  (native 626 tool-calls + `update_plan`×110 — machine-paced), 05D Strong (28).
- **§18 resolved to UNVERIFIED→Strong:** the selected candidate's pipeline is
  Strong, not Exemplary. 05C is Exemplary on provenance but is a backup.
- **Mandatory-logs rule:** missing-logs DQ risk LOW (11 verified transcripts);
  residual risk is that the logs do not yet *demonstrate* "no human-written
  hardware" (no AI-vs-human authorship diff). Closed by the §6 actions above —
  chiefly the 05B `apply_patch`→RTL authorship chain. Full writeup:
  `submission/ai-provenance/PROVENANCE.md`. See also `score-assessment.md`.
