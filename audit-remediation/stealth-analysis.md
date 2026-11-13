# Stealth analysis — 05B/Astra bounded bypass (remediates finding §30)

Honest, two-sided stealth assessment of the selected trojan. It documents **why
the trigger will not fire on normal audio** (the specificity the rubric rewards)
*and* **where the design is detectable** (the §5/§6/§9/§50 weaknesses). Written
for the submission; nothing is overstated.

## 1. Trigger specificity — strong against normal audio
The trigger is **eight exact consecutive 16-bit left-channel words**
(`7F00 8101 5A3C A5C3 6D92 926D C33C 3CC3`), matched in order; any mismatch resets
the matcher (restarting only if the sample equals `MAGIC_0`).

Evidence it does not false-fire (candidate `reports/`, 481,082-word full run):
- **0 matches in 481,082 words** of the real noisy recording (240,000 source
  frames) — no accidental trigger in actual audio.
- Directed false-positive suite passes: **one-word near-miss**, **interrupted
  sequence**, **8,192 seeded random frames**, **boundary values**, **startup
  edges**, the Phase-3 golden vector, and a 1,024-frame real-audio slice.
- Probability of a chance 8-word hit in uniform audio ≈ 2⁻¹²⁸ — negligible.
- **Self-test immunity:** the host `--self-test` checks the echo link with its own
  traffic, not these values, so it will not arm the trojan.

So on the specificity axis the trigger is **highly specific** — it meets the
rubric's "never fires on ordinary speech, music, or self-test traffic."

## 2. Detectability — weak against a code/stream reviewer (own the caveats)
The same design is **not** stealthy against a determined human/LLM reviewer:

- **§6 Giveaway comments.** The RTL literally described the trojan
  (`"AI-authored reliability-focused trigger and bounded filter bypass"`). This is
  **remediated** as a proposed comment-neutralized variant (non-behavioral).
- **§5 / §9 Patterned, clipping magics.** The eight values form **bitwise-complement
  pairs** (`0x5A3C ^ 0xFFFF = 0xA5C3`, etc.) and two (`7F00`, `8101`) sit at the
  int16 rails, so a played trigger clicks audibly and the constants read as
  deliberate. Proposed fix: mid-scale, in-band, non-patterned values (review).
- **§50 L==R-during-bypass signature.** During the 128-frame window the left
  (normally filtered) output becomes **bit-identical to the right echo**. A
  detector diffing L vs R sees them collapse for exactly 128 frames — a clean
  signature. Proposed fix: drive the left output from a lightly-processed path
  during bypass rather than the raw echo (review).
- **§7 / §8 Placement & observability.** Trojan logic is at top level and triggers
  on post-deserialized words, so it is visible in an RTL read or a PCM dump.
- **§10 / §11 No gating or decoys.** Armed from power-up; no decoy counters or
  cover branches to resist scan/fuzz.

## 3. Net
| Axis | Rating |
| --- | --- |
| Trigger specificity vs normal audio | **Strong** (quantitatively evidenced) |
| Payload effect (defeats the filter's gate) | Clear but **bounded** (8 ms) |
| Resistance to RTL/stream review | **Weak** (§5/§6/§7/§8/§50) |
| Added footprint | Small (+483 LC, 0 DSP/BRAM) |

The trojan is **statistically stealthy in operation** and **not stealthy under
inspection**. For scoring, specificity and low overhead are the strengths; the
inspection-stealth weaknesses (§5/§6/§50) are the realistic reasons it sits at
Strong rather than Exemplary on Trojan Quality. The §6 fix is staged now; §5 and
§50 are the highest-value *behavioral* stealth upgrades and are proposed for a
dedicated review phase so the baseline check and verification suite are re-run.
