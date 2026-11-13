# Phase 05S cycle 003: five focused iterations

Current and previous main best: **05B `fd0ca7f6bce1d30bb1b1e6ce43603b4c7d51e5b6`**.
Original candidate package `9e172a865a543b03e226596689fd6691ffa2b779`; baseline
`e72522f265ac36da713cd7a0dcf8dbc64ab21209`. Ranking remains **B > C > D > A**.
Cycle ran in `challenge3/05s-cycle-03`, preserving original branches, verified RTL,
golden references, prior selection history and cycle002 receipts. Root AGENTS.md
is still absent. No public push was performed.

## Five iterations and decisions

1. **New published evidence.** Remote Phase 6 `a1d3f7f` and Phase 8 `babb81ad`
   have identical Git trees to previously reviewed `8daabe8` and `84f1e55`.
   Evidence branch `37e65ac` republishes retained worktree receipts and explicitly
   reports no new test/build. Accepted the immutable source/receipt mapping;
   rejected treating new commit IDs as new functional or hardware verification.
2. **Separate 05BB recovery evidence.** Verified new experiment `4bf5e02856b6874c82a8eaf7983d54de4755c2e6`
   through package `83acf059f7b29fd0c8b1be16e952444ff5ccd84b`. All **634 ZIP
   entries and 634 retained artifacts**, plus **27 source files and immutable Git
   blobs**, matched. Actual recovered/original-bit comparisons, WAV-to-serialized
   capture identity, sample-clock rates, baseline receipt sums and bitstream
   digest passed. Accepted separate simulation-only bonus evidence; no main
   replacement, merge, decoder change or channel enhancement.
3. **Q provenance closure.** The closed Q session extends the private checkpoint
   by **90,603 bytes / 46 lines / 13 visible records**, including final response
   and successful completion. A new private copy matches its source hash and
   preserves the old archive. Closed the missing-final-response gap. Overall
   comprehensive successful-write attribution and submission sufficiency remain
   uncertified. Original B runtime is `gpt-6-luna`; Q is `gpt-6-astra`.
4. **Discovery completeness.** Confirmed the previous inspector only classified
   four local candidate heads. It now reports supporting local/remote sources and
   separate remote A-D tips, changed/new status and unavailable Git objects.
   New remote-only evidence is explicit without automatic fetch or promotion.
5. **Checkpoint reliability.** Confirmed stale Q cycle1 metadata in current-best
   and a checker fixed to cycle002. Canonical latest-cycle fields now agree; Q
   metadata remains archived. The new checker anchors prior history to immutable
   commit `bcca3c8`, rejects fabricated predecessor identities, rewritten history,
   evidence tampering, unverified promotion and unsupported/contradictory physical
   claims. **13/13 focused tests passed.** Three issues found in independent code
   review were fixed before acceptance.

Receipts: `cycles/05S-003/iteration-01-published.json` through
`iteration-05-validation.json`. Prior checkpoint files are preserved under
`cycles/05S-003/previous-checkpoint/`. No completed HDL, full-audio, synthesis or
timing experiment was rerun. The new tests exercise changed reporting code only.
No RTL revision was attempted or rejected, and no new selected-design RTL defect
was found. Initial 8-test/10-test development runs were expanded after code-review
findings; the final 13-test run is the accepted validation.

## Main verification and scoring

Retained main evidence: **46 Q simulations plus one cycle002 uninterrupted-audio
simulation**, including 480,260 exact continuous words; 3,240/5,280 logic cells,
15.2716 MHz against 10 MHz, repeat-identical Q bitstream. These are retained
simulation/synthesis results, not newly run or physical measurements. All ten
candidate gate dispositions remain in selection.json; no physical gate closed.

Main assessment is unchanged: conditional engineering quality estimate 20/25,
automation 9/15, documentation 9/15, physical demonstration 0/10, creative AI
unscored pending comprehensive provenance. No competition-ready total or official
award is claimed. B retains stronger regression/reproducibility evidence and 412
more spare cells than D; neither original B nor D has physical evidence or a
demonstrated data channel. The separate 05BB derivative is the substantiated
simulation starting point for further bonus validation.

Bonus A remains a conditional simulation-tier 10/20 for distinct A+D designs.
Bonus B changes from unsubstantiated to **conditional simulation-tier 5/10 for
the separate 05BB experiment**, under the [official rubric](https://github.com/JBlocklove/CSAW-AI-Hardware-Attack-Challenge-2026/blob/main/finals/challenge_3/README.md#bonus-b---covert-channel-up-to-10-points).

| Simulated frame rate | Compared payload bits | Errors / BER | Capture duration | Net payload rate |
|---:|---:|---:|---:|---:|
| 31,250 Hz | 336 | 0 / 0 | 0.537344 s | 625.2978 bit/s |
| 15,625 Hz | 336 | 0 / 0 | 1.074688 s | 312.6489 bit/s |

Rates use full retained capture length and simulated frame clocks; they are not
hardware USB throughput. Separate 05BB build: 3,455 cells, 15.4333 MHz; 42 retained
comparison cases, 56,596 words, zero mismatches. Its long-audio coverage, physical
demo, clock-drift/resampling robustness and transcript qualification remain open.
The main design's full-audio pass is not inherited by modified 05BB RTL.

## Reproduction, handoff and next cycle

From this evaluation worktree, using fresh outputs:

```powershell
& C:/Users/lowbr/oss-cad-suite/lib/python3.exe experiments/phase05s/inspect.py --repo . --state handoffs/phase-05/selection.json --output build/NEXT-discovery.json
& C:/Users/lowbr/oss-cad-suite/lib/python3.exe experiments/phase05s/verify_state.py --root .
& C:/Users/lowbr/oss-cad-suite/lib/python3.exe experiments/phase05s/cycle-03/test_state.py
& C:/Users/lowbr/oss-cad-suite/lib/python3.exe experiments/phase05s/cycle-03/audit_bonus_evidence.py --source ../phase-05bb --output build/NEXT-bonus-audit.json
```

Do not repeat these or the retained HDL experiments without changed evidence or
an unresolved assumption. Cycle004 should read the current manifests/history and
inspect changes against recorded local and remote source SHAs. Historical cycle
checkers remain immutable; use `verify_state.py` for the latest checkpoint.

Stopped after the requested five focused iterations. Physical inventory still
shows only Bluetooth COM4/COM5; no board was programmed. Next priority is actual
Hackster baseline/echo and controlled demonstration, with main and optional bonus
packages treated separately. Provenance certification, missing pyserial in the
selected host interpreter, D script portability, and Scribe model configuration
remain in the backlog.

Codex authored evaluation/reporting changes only. Exact main-authoring model
attributions come from sanitized private-log metadata, not candidate labels.
No raw prompts/responses or private logs were added to tracked files. This report
and the compact documentation-agent-handoff.md are the Project Scribe handoff;
local controller delivery does not imply model synthesis or external publishing.
