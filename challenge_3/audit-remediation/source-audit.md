# Source audit — "Person 5 — Comprehensive Shortfall Analysis"

**Provenance.** External audit supplied by the project owner on 2026-11-13 and
preserved here verbatim for traceability. The auditor reviewed an isolated
**"Person 5 folder"** (a stripped candidate export), *not* the full `CSAW_FIN`
repository. Every finding whose wording is scoped to "the folder" / "in the
Person 5 folder" must therefore be evaluated against the whole repository and
its phase worktrees before it is accepted — see `findings.md` for the
finding-by-finding verdicts.

The audited artifact is the **05B / "Astra"** candidate (final candidate at
`CSAW_FIN_worktrees/quality-winner`): the 8-sample magic matcher
(`7F00 8101 5A3C A5C3 6D92 926D C33C 3CC3`) with a 128-frame bounded filter
bypass. The reviewed RTL already contained the Subphase-Q boundary fix
(`fir_audio_top.v:204-209`), so the auditor saw a current RTL file but without
its surrounding `ai/`, `README.md`, `reports/`, `manifest.json`, automation, or
repo-wide evidence.

---

## Trojan Quality (25 pts) — what keeps it out of the top band

1. **Bounded, short payload window.** 128 samples at 16 kHz = **~8 ms** of bypass per trigger. Rubric's top band wants a *severe* payload; a brief, self-terminating leak falls short.
2. **No re-arm during payload.** Matcher is parked at 0 during the 128-frame bypass — attacker can't extend or chain bypasses without waiting.
3. **Single, simple payload mode.** Just `echo` substituted for `y_filt`. No creative variants (coefficient corruption, per-band attenuation flip, phase inversion, selective-notch disable) that would score "severe/creative."
4. **Payload = raw input passthrough.** Easiest-possible subversion. Doesn't try to disguise bypassed content as filtered (e.g., apply a stale `y_filt` or inject engineered out-of-band content).
5. **Trigger uses obvious hex magic.** `7F00, 8101, 5A3C, A5C3, 6D92, 926D, C33C, 3CC3` reads as "magic numbers" in any RTL review; a palindromic/anagram pattern (`5A3C`/`A5C3`, `6D92`/`926D`, `C33C`/`3CC3`) screams intentional placement.
6. **Giveaway comments.** Lines 162-167 literally say `"AI-authored reliability-focused trigger and bounded filter bypass"` — collapses stealth in a human/LLM code review.
7. **Trojan logic lives at top level**, not hidden in a submodule, the coefficient initializer, the deserializer, or the TX serializer. No attempt at "steganographic" placement.
8. **Trigger operates on post-deserialized 16-bit words**, not on bit-level/I2S framing or power-side signals — reviewable with a simple PCM dump.
9. **Near-full-scale magic values (0x7F00, 0x8101)** are clipping-peak samples. A played WAV containing the sequence has audible clicks, reducing covert-use stealth.
10. **No audio-context prerequisite.** Fires from first sample after power-up; a stronger trojan would require a "normal-looking" audio preamble before arming.
11. **No anti-detection against scan/fuzz.** No decoy counters, no cover branches that mimic filter logic, no sensitivity to `end_frame`/`busy` timing.
12. **4-bit `magic_position` with `default:` covering 8–15.** Unused state wastes resources and is a minor red flag in synthesis reports.
13. **`<= 8'd1`** on bypass countdown adds a comparator instead of a clean `== 0` — fine functionally, costs a sliver of overhead.
14. **No ICE_LED decoy or masking.** LED still exactly tracks MAC `busy`; an observer notices nothing new, but equally nothing was done to actively mislead probing.

## Creative Use of GenAI (35 pts) — the largest gap

15. **No AI session logs in the folder.** Rubric requires evidence that RTL was AI-generated; only a comment claims it.
16. **No prompt artifacts** (prompts, system messages, conversation transcripts).
17. **No model list** (which Claude/other models, versions, roles).
18. **No agentic pipeline evidence.** Rubric gives top score to agentic/programmatic flows; ad-hoc prompting scores lowest, and this submission shows no pipeline at all.
19. **No test-in-the-loop evidence.** No sign AI iterated against baseline check, simulator, or self-test.
20. **No reverse-engineering automation artifacts.** No bitstream disassembly scripts, coefficient-extraction notebooks, or RE journal.

## System Automation (15 pts)

21. **No build script** (Makefile, `build.sh`, PowerShell, etc.) in the folder.
22. **No yosys/nextpnr/icepack invocation** visible.
23. **No programmer/flasher step** (iceprog, dfu-util).
24. **No one-command flow.** Rubric's top tier is "generation → insertion → programmed board" in one command; nothing like it is present.
25. **No regression harness** comparing output to `filtered_test_audio.wav`.
26. **No self-test runner** to verify the link check still passes.

## Documentation & Reproducibility (15 pts)

27. **No README** in the Person 5 folder.
28. **No trigger spec document** (sequence, byte order, how to inject).
29. **No payload spec** (duration, semantics, caveats).
30. **No stealth analysis** (why the trigger won't fire on music/speech/self-test).
31. **No AI-model list / log pointers** required by the rubric.
32. **No reproduction steps** (how to rebuild the `.bin`, program the board, play the trigger).
33. **No recovery/RE writeup** (how the baseline `.bin` was reverse-engineered — only hinted at in RTL comments).
34. **No trigger-generator script** (e.g., a Python that writes the 8-sample WAV).

## Hardware Demonstration (10 pts)

35. **No board photos.**
36. **No scope/logic-analyzer traces** of I2S lines during trigger or bypass.
37. **No captured WAV pair** (normal vs triggered) demonstrating the bypass audibly or spectrally.
38. **No ICE_LED trace** (rubric mentions the scope-trigger SMA — unused here).
39. **No baseline-passes-on-hardware evidence** (bit-exact comparison against `filtered_test_audio.wav`).
40. **No power-analysis demo** even though the challenge highlights power-analysis circuitry as a debug aid.

## Bonus A — additional distinct trojans (up to 20)

41. **Only one trojan.** Bonus A untouched. Two more distinct trojans (different trigger *and* payload) would add up to 20 pts.
42. **No plumbing for multiple trojans** (no second FSM, no alternative payload hooks).

## Bonus B — covert channel (up to 10)

43. **No covert channel.** The 128-frame bypass is not a data-carrying channel; it passes whatever the attacker streams, but there's no documented bit rate, framing, or decoder.
44. **No host-side recovery tool.** Bonus B requires bit-exact recovery at the host — nothing present.
45. **No error-rate measurement** or robustness characterization.

## RTL / correctness nits that could cost small deductions

46. **Post-bypass restart edge case:** when `bypass_remaining <= 1`, the next sample is both "the first post-bypass sample" and "potential MAGIC_0 start." Handled, but unintuitive — a reviewer may flag it.
47. **`bypass_active` is single-cycle on the frame boundary**, so a glitch in `end_frame` timing relative to `new_sample` would propagate; depends on simulator vs real-silicon ordering.
48. **Baseline RTL is claimed "bit-identical"** via co-simulation but no proof artifact is present; if the real bitstream differs on a corner case (rounding, BRAM init), the baseline check could fail on hardware and zero out the Trojan Quality category.
49. **No reset on trigger state via external signal.** Only power-on init; a brownout mid-stream could leave the matcher in an indeterminate state (very minor on iCE40 FFs that power-up to 0).
50. **Right-channel echo path unchanged during bypass.** Consistent with baseline, but a sophisticated detector comparing left vs right could spot the moment left-channel content becomes identical to right-channel echo for 128 frames — a signature of the attack.

## Headline point-loss estimate (auditor's, rough)

| Category | Max | Likely | Main reason |
|---|---|---|---|
| Creative GenAI | 35 | ~5–15 | No pipeline/logs/models in folder |
| Trojan Quality | 25 | ~15–20 | Short payload, obvious magic, giveaway comments |
| Automation | 15 | ~0–5 | No scripts present |
| Docs/Reproducibility | 15 | ~0–5 | No README/spec/logs |
| HW Demo | 10 | ~0 | No captures in folder |
| Bonus A | 20 | 0 | Single trojan |
| Bonus B | 10 | 0 | No covert channel |

> The auditor's estimate is explicitly conditioned on *"in folder"* visibility.
> See `score-assessment.md` for the repository-wide re-estimate.
