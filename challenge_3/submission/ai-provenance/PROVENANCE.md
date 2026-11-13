# AI provenance — CSAW 2026 Challenge 3

**Why this exists.** The challenge rule is explicit: *"No hardware may be written
by human users. This will be confirmed with the submitted AI logs."* This package
is the evidence that the Trojan RTL and exploit logic were **AI-generated**, and
it is scored under **Creative Use of Generative AI (35 pts)**.

Everything below is at the **provenance level** (models, sessions, tool-driven
iteration, methodology). It was produced by a 9-agent audit that characterized
each candidate and then **adversarially calibrated each tier downward to refute
overclaims**; the structured results are in `provenance-audit-results.json` and
the raw metrics in `provenance-metrics.json`.

## 1. The logs exist and are integrity-verified
11 raw agent-session transcripts, SHA-256- and size-verified against their index
(`../../audit-remediation/evidence/provenance-verification.json`, 11/11 OK, 22.8 MB):

| Candidate | Sessions | Agent | Role |
| --- | ---: | --- | --- |
| 05A (Luna) | 1 | Codex / OpenAI | additional Trojan (Bonus A) |
| **05B (Astra)** | **5** | **Codex / OpenAI** | **SELECTED — scored in base** |
| 05C (Claude Opus Architecture) | 4 | Claude / Anthropic | additional Trojan (Bonus A) |
| 05D (Claude Opus DSP) | 1 | Claude / Anthropic | additional Trojan (Bonus A) |

The **missing-logs disqualification risk is LOW**: logs are present, integrity-
verifiable, and attributable to AI harnesses for every candidate including the
selected one.

## 2. Model attribution (authoritative)
From the curated manifest / submission-README (`model-list.json`):
- **05B (selected):** Codex (OpenAI) — **`gpt-6-luna`** for the original build,
  **`gpt-6-astra`** for the Subphase-Q quality work; requested label *Astra*.
- 05A: Codex (OpenAI), label *Luna*. 05C/05D: Claude Opus (`claude-opus-4-8`
  dominant), labels *Claude Opus Architecture* / *DSP*.

> **Caveat (do not misread the metrics).** `provenance-metrics.json` lists *every*
> model-id string found by regex-scanning each transcript. That set is a
> **superset** — it includes incidental/quoted mentions (e.g. 05B's transcript
> contains `claude-*` and other `gpt-*` strings). It is **not** an authorship
> claim. Authorship is the attribution above, from the manifest.

## 3. Methodology: AI authored, built, and iterated against the tools
Every candidate shows a tool-driven **author → build → simulate/synthesize → validate
→ iterate** loop. Activity markers (occurrences of harness/tool names in each
transcript) are dense across the full iCE40 flow — `run.py`, `validate`,
`iverilog`/`vvp`, `yosys`, `nextpnr`, `icetime`, `icepack`, `prepare_vectors`,
`candidate_reference` — i.e. **test-in-the-loop development**, not one-shot
generation. The Claude candidates additionally show native agentic planning
(`update_plan` ×110 for 05C, ×36 for 05D) and reliable native tool-call records
(626 for 05C). The Codex candidates drove programmatic file edits via `apply_patch`
and shell execution.

> **Honest framing.** These markers are **string counts**, not a ledger of
> confirmed executed tool-calls — the same superset caveat in §2 applies. The
> *confirmed* execution evidence is the recorded harness output (the Phase 4/5S/Q
> validation receipts), not the transcript string counts.

## 4. Calibrated Creative-GenAI scoring (provenance only)
Adversarially calibrated (each proposal was challenged; tiers default DOWN):

| Candidate | Tier | Basis |
| --- | --- | --- |
| 05A | Strong (28) | Codex agentic authorship + build/validate loop; autonomy inferred, not measured |
| **05B (selected)** | **Strong (28)** | real Codex harness + diverse iCE40 toolchain exceed prompt-engineering-with-manual-integration; **Exemplary NOT endorsed** (see §5) |
| 05C | Exemplary (35) | 626 *native* Claude tool-calls + `update_plan`×110 at ~6 calls/min over ~104 min — machine-paced agentic loop a human could not hand-author alongside |
| 05D | Strong (28) | structured agentic pipeline; 122 user turns indicate ongoing human steering |

**Submission self-claim: Strong (28)**, anchored on the selected 05B (band:
Proficient 21 downside → Strong 28 center). **Exemplary (35) is a conditional
ceiling, not claimed** — see §5. (05C independently reaches Exemplary on
provenance, but it is a backup; candidate selection must be driven by the
security/functional merits, not by provenance.)

## 5. What would move 05B to Exemplary — and the honest gaps
The adversarial pass found the Exemplary limbs **unproven** for 05B:
- **Diff-level AI authorship is not demonstrated** for any candidate — "minimal
  human edits" is inferred from activity volume, never measured. This is the
  central gap against the "no human-written hardware" rule.
- 05B has **empty role fields** (Codex schema), so the human-vs-AI turn split is
  not directly readable; the raw tool/function-call count (305) is modest.
- **Programmatic / AST / netlist-level insertion** is not shown — `apply_patch` is
  text/diff editing, the standard Codex editor.
- **Retrieval** over the netlist/interface doc is supported only by filename
  counts, not demonstrated agentic retrieval.

## 6. Actions to strengthen the submission (no new engineering)
1. **Bundle all 11 transcripts** with their SHA-256 manifest + a one-command
   verify script + an explicit transcript→candidate mapping (directly addresses
   the DQ-risk prong).
2. **For 05B, extract the `apply_patch` diffs that authored the submitted RTL** and
   present a direct transcript→RTL chain as the *primary* AI-authorship evidence.
3. Add a **human-vs-AI authorship artifact**: show the final RTL equals the AI's
   cumulative `apply_patch` output with no out-of-band hand edits.
4. Ship this `PROVENANCE.md` + `model-list.json` and state the §2 superset caveat
   explicitly.
5. **Reconcile the 05B timeline** (earliest `2026-10-12` is an embedded/quoted
   date; real authoring is `2026-11-13`, ~1 day) to pre-empt a "month-long gap"
   challenge.
6. **Claim Strong (28), not Exemplary**, unless actions 2–3 add the agentic/
   programmatic-insertion proof. Frame authorship in bounded terms: *all RTL
   authored by the AI agent via the harness; human role limited to prompting,
   steering, selection, and integration — no hand-written HDL.*

## 7. How judges receive the raw logs
The raw transcripts are **not committed to the public repository** (they contain
absolute home paths and a personal email). They are provided to the judges through
the submission channel. Integrity is independently checkable with
`audit-remediation/scripts/verify_provenance.py` against the SHA-256 index.
