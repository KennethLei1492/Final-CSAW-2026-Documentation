# Phase 05S cycle 002: selection retained

Current and previous best: **05B, `fd0ca7f6bce1d30bb1b1e6ce43603b4c7d51e5b6`**.
Original 05B package: `9e172a865a543b03e226596689fd6691ffa2b779`.
Common Phase 4 baseline: `e72522f265ac36da713cd7a0dcf8dbc64ab21209`.
This is a continuation of initial selection and Subphase Q, with one focused
coverage iteration. No candidate RTL, golden expectations, constraints or
original candidate branches were changed. Local branch: `challenge3/05s-cycle-02`.
Root AGENTS.md was absent. Existing root README and documentation-agent files were preserved.

## Decision and ranking

| Rank | Candidate | Original frozen SHA | Disposition |
|---:|---|---|---|
| 1 | 05B | `9e172a865a543b03e226596689fd6691ffa2b779` | Retain verified Q successor `fd0ca7f` |
| 2 | 05C | `f4e8eedcb55d73f5f3adc97431a4a1a3a9c65c87` | Backup; no new implementation |
| 3 | 05D | `629c7d4a1dd158ff1b6585e0e84e9aff74f8810f` | New tip `51c223336f3d4d23854907bdee87dfd5ac1f2e98` adds reports/analysis; RTL unchanged |
| 4 | 05A | `99a3fdb6d1f87ffd75bcfa46d7adc94664d97b29` | No new committed implementation; dirty README excluded |

All four are available locally under `../CSAW_FIN_worktrees/05*-*`. Remote
inspection found only the older original B implementation branch among these
four. Local candidates, Q and evaluation work were not pushed. The complete
initial ranking and evidence are preserved in `cycles/05S-001/`; Q's prior
checkpoint is preserved in `cycles/05S-002/imported-Q-current-best.json`.
`selection-history.json` preserves initial selection and both accepted Q revisions.

## New evidence and focused iteration

Confirmed gap: Q tested the full supplied recording as four overlapping,
independently powered-up simulations. Hypothesis: preserving state through the
entire recording still produces the exact golden output. The focused runner
archives the pinned Q SHA, verifies its 41-entry inventory, imports the unchanged
Phase 3 arithmetic and coefficients, and runs the existing Phase 4 testbench with
only its supported simulation capacity parameter increased.

**Result: 480,260/480,260 words exact, zero mismatches, zero maximum error.**
This covers all 240,000 source frames plus 130 flush frames, left filtering and
right echo, with no intermediate simulation restart. Expected latency remains
two frames, comparison adjustment and tolerance remain zero. The adapter ignores
the external testbench reset; `reset_count: 1` in the raw receipt describes its
startup stimulus, not a demonstrated DUT reset. WAV metadata is 16 kHz; simulated
transport is 1 MHz BCLK / 31,250 frames per second. This is simulation, not board playback.

Accepted improvement: added uninterrupted normal-audio verification and a
repeatable resumption inventory. The implementation SHA stays unchanged.
No implementation revision was rejected or promoted. Newer D documentation was
insufficient to change ranking; its suggested covert channel was not treated as
a working recovery result.

Additional checks: fresh framework regression **15/15**, archived source inventory
**41/41**, and all **230/230** retained Q artifact hashes matched. The first
framework invocation lacked the suite environment and skipped HDL tests; it is
excluded from the full-pass count. The corrected invocation passed all 15,
including intentional negative comparator/RTL tests. No synthesis rerun was
needed because implementation, constraints and build flow did not change.

Q's retained evidence covers 46 simulations: 10 standard, 2 common, 30 directed
and 4 segmented full-audio tests, plus 15 framework tests. Its boundary correction
changed 28/30 directed passes to 30/30; prior standard and full-audio captures
remained identical. The new continuous test supplements those retained results.

Phase 3 golden arithmetic and coefficient Git blobs match the copied oracle.
Phase 6's original source-hash rejection applies to the old 05B package; Q's
corrected inventory is verified, but this does not create a Phase 6 board signoff.
Phase 8 adds clean-baseline packaging and reproduction, not a candidate hardware
run. Phase T's matrix is software-only and contributes no physical or Bonus B evidence.

## Ten qualification gates

| Gate | Current 05B assessment |
|---|---|
| 1. Source integrity/provenance | Source identity passes; complete AI-log sufficiency remains open |
| 2. Baseline equivalence | Exact simulation passes; official physical comparison open |
| 3. Functional verification | Retained standard/directed tests pass |
| 4. Regression reliability | Retained 46 cases, fresh framework and continuous test pass |
| 5. FPGA synthesis | Retained immutable Q build passes |
| 6. Timing/resources | 3,240/5,280 LC; 15.2716 MHz vs 10 MHz; 0 DSP/RAM, 9 I/O |
| 7. Reproducibility | Clean archive, 41 source entries, 230 retained artifact hashes pass |
| 8. Physical evidence | Not run; no identified Hackster |
| 9. Documentation | Checkpoint/history complete; board evidence and transcript certification open |
| 10. Bonus | Distinct additional designs have simulation evidence; no data-channel recovery |

All four candidates' gate dispositions are in selection.json, with original
per-candidate evidence in the archived selection. Physical status is open for all.
Q bitstream SHA-256: `2742912e31ec6c058756e5623d84736285dc2d46695d8ece616494e3152a89b0`.
Resource/timing results are synthesis/P&R estimates for UP5K/SG48, same nine-pin
PCF, 10 MHz and seed 1. They are not physical timing measurements.

## 05B versus 05D and scoring

05B has stronger baseline and regression coverage, a verified repaired boundary
defect, and no remaining confirmed RTL defect within tested scope. D also has no
demonstrated functional defect in the reviewed tests, but less coverage. B has
2,040 spare logic cells versus D's 1,628 (412 more). D's common build uses 3,652
cells and reaches 15.1833 MHz. Neither has better physical evidence: neither has any.

B's reproducibility is stronger. D's previously missing verification report now
exists, but new analysis scripts hard-code original worktree paths and output
locations. `verify_equivalence.json` is absent; `verify_payload.json` predates the
latest `satsearch_*` checks. Those unexecuted/missing results receive no credit.

**Main recommendation: 05B. Bonus B starting point: 05B**, based on baseline
verification, automation and resource margin. This feasibility judgment makes no
claim that B already carries data. D's DSP analysis is useful background; its
implemented spectral inversion is not a demonstrated data channel.

The [official rubric](https://github.com/JBlocklove/CSAW-AI-Hardware-Attack-Challenge-2026/blob/main/finals/challenge_3/README.md)
was retrieved in this cycle (README Git blob `4159341c417f652fea45cd412d79cc52f0d9cad4`).
Main score remains provisional: engineering evidence is consistent with the
prior 20/25 quality estimate **conditional on passing the board baseline**,
9/15 automation and 9/15 documentation; physical demonstration is 0/10.
Creative AI /35 is unscored pending transcript sufficiency. No total or final
qualification is assigned. Original 05B was requested as Astra, while recovered
runtime metadata reports `gpt-6-luna`; preserve that distinction.

Bonus A: original independent simulations demonstrate two additional distinct
mechanisms, A's one-bit corruption and D's spectral inversion, with distinct
triggers and baseline checks. This supports the rubric's **simulation-only
5-point tier each**, a conditional evaluator estimate of 10/20, not an official
award or physical qualification. Complete documented/provenance submission is
still required. C stays the backup and is not counted as another bonus entry.
Bonus B: **0/10 substantiated**. Neither B nor D supplies transmitted/recovered
bit comparisons, measured bit rate and BER; no separate qualifying result was found.

## Commands, resumption and limits

From this evaluation worktree, use fresh output directories:

```powershell
& C:/Users/lowbr/oss-cad-suite/lib/python3.exe experiments/phase05s/inspect.py --repo . --state handoffs/phase-05/selection.json --output build/NEXT-discovery.json
& C:/Users/lowbr/oss-cad-suite/lib/python3.exe experiments/phase05s/cycle-02/run_continuous.py --repo . --ref fd0ca7f6bce1d30bb1b1e6ce43603b4c7d51e5b6 --suite C:/Users/lowbr/oss-cad-suite --output build/NEXT-continuous
$env:OSS_CAD_SUITE='C:/Users/lowbr/oss-cad-suite'
& C:/Users/lowbr/oss-cad-suite/lib/python3.exe -m unittest discover -s infrastructure/tests -v
```

Full retained Q reproduction command: `python experiments/quality/run.py --suite
C:/Users/lowbr/oss-cad-suite --output build/NEXT-quality` from the pinned Q package.
Do not rerun all tests without changed inputs/environment or an unresolved assumption.
For next invocation, read the four selection/history/backlog/current-best files,
run discovery, review changed SHAs and new evidence, then branch from the verified
best for any justified implementation experiment. Append cycle 003; never rewrite
the historical selection. Missing candidates mean unavailable, not failed. The
inspection tool neither promotes revisions nor modifies candidate branches.

Stopped after one focused iteration: available priority checks pass and physical
testing requires unavailable hardware. CIM/PnP inventory found only Bluetooth
COM4/COM5, no identified Hackster/RP2040/Pico/USB Serial device. Do not use those
ports by guess. The selected OSS CAD Python also lacks pyserial; prepare a verified
host environment when the board is available. Next action: capture stock/candidate
board baseline and controlled activation against the selected source/bitstream.

## Documentation handoff and authorship

This file is the concise handoff for Project Scribe and the Phase 7 coordinator.
Supporting hashes, reports and history are linked from selection.json; no private
AI transcripts were copied into the public repository. Codex authored evaluation
Python and documentation only; no RTL or exploit implementation changed. Exact
runtime model identity for this evaluation is not independently attested here.
Scribe's configured model is still a placeholder, so local controller recording
does not imply model synthesis or external publication. Delivery receipts are
stored alongside the cycle evidence.
