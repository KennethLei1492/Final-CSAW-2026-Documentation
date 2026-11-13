# Phase 05BB Bonus B handoff

**PARTIAL DEMONSTRATION: simulation-only, potential 5/10, subject to judging.**
No physical board was available; no hardware audio capture or full-credit claim.

Selected Q-corrected 05B `fd0ca7f6bce1d30bb1b1e6ce43603b4c7d51e5b6` after
inspecting both B and latest local D. Dedicated branch `challenge3/05bb-bonus-b`
is in `C:/Users/lowbr/Documents/College/AI/CSAW_FIN/.worktrees/phase-05bb`.
Validated implementation/evidence commit: `4bf5e02856b6874c82a8eaf7983d54de4755c2e6`.
Later commits contain this handoff and documentation only. Original candidates
and golden files remain unchanged; no public push or candidate merge occurred.

The separate trigger causes a bounded ROM transmitter to emit the synthetic
message `CSAW26-BONUS-B` on filtered-left audio while the input is silent.
The host decoder reads only the serialized-output mono WAV. Expected bits enter
after decoding. Original input, right echo, source-candidate output and silence
all fail to recover a packet, as required for meaningful source separation.

| Simulated sample rate | Payload recovery | BER | Full capture duration | Net payload rate | Raw bit rate |
|---|---|---|---|---|---|
| 31,250 Hz | 336/336 bits, three packets | 0/336 | 0.537344 s | 625.30 bit/s | 976.56 bit/s |
| 15,625 Hz | 336/336 bits, three packets | 0/336 | 1.074688 s | 312.65 bit/s | 488.28 bit/s |

Durations include trigger, sync, length, CRC, guards and all attempts. These are
sample-clock simulation rates, not measured USB/hardware throughput. Deliberate
corruption gives one error/336 bits and a failed CRC; truncation gives null BER.

Fresh verification: 42 I2S cases, 56,596 compared words, zero mismatches;
15 framework tests; 10,752 exact transmitter samples and trigger boundary tests;
three decoder tests including unseen payloads, offsets, polarity and noise.
Elaboration/synthesis/place-route/packing/icetime passed: 3,455/5,280 logic
cells, no DSP/RAM, 15.4333 MHz versus 10 MHz constraint. Bitstream hash:
`4c27a28220f5cb3f254f1bb82f4f47c6ae1c5dd0d3bcd700459bdf35e2c70056`.

All files are under `experiments/phase05/05bb-bonus-b/` in the dedicated worktree.
Read its README for exact reproduction commands. `verification-evidence.zip`
contains 634 evidence files including WAVs, reconstructed bits, per-bit CSVs,
execution logs, timing/resource reports, bitstream and generated fixtures.
The adjacent source/evidence inventories hash exact bytes. The JSON handoff
lists individual paths; extract the archive there after a fresh checkout.

The existing Project Scribe recorded successful package validation and produced
a local evidence preview. Its model synthesis was unavailable due to the existing
model placeholder. Runtime provenance is Codex/GPT-6 with unknown exact snapshot;
the user's Claude role label is not an authorship claim. Comprehensive transcript
export/completeness is still unverified and must be resolved before submission.

For Phase 5S: compare this as an optional bounded simulation-tier bonus candidate;
do not merge into the selected candidate without review. For Phase 8: preserve
the archive, hashes, source, reproduction/hardware procedures and provenance;
keep simulation and hardware evidence distinct. No judge-awarded score is claimed.
Available verification is complete; physical validation and transcript packaging
remain explicit submission dependencies.
