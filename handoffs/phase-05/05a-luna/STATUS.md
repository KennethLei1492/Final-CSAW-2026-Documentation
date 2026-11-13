# Phase 5A handoff — 05A Luna

Phase: 5 — independent candidate development  
Agent: Independent FPGA Design and Implementation Agent  
Model: Codex Luna 5.6  
Candidate ID: 05A  
Git branch: `challenge3/05a-luna`  
Source/base commit SHA: `e72522f265ac36da713cd7a0dcf8dbc64ab21209`  
Worktree: `C:/Users/lowbr/Documents/College/AI/CSAW_FIN_worktrees/05a-luna`

## Owned directories

- `experiments/phase05/05a-luna/`
- `handoffs/phase-05/05a-luna/`

## Completed tasks

- Researched and compared four trigger/payload concepts.
- Selected an exact three-word left-channel trigger:
  `16'h5A3C → 16'hC3A5 → 16'h96E1`.
- Generated and integrated AI-authored synthesizable Verilog using the baseline
  `new_sample/left_sample` event.
- Implemented a sticky payload that flips the filtered left output LSB while
  leaving the right echo and latency unchanged.
- Added deterministic inactive, near-miss, boundary, random, supplied-audio,
  and exact activation tests.
- Preserved the original reference RTL under `rtl/baseline/`.

## Verified results

- Baseline control validation: passed, 7 simulation cases plus FPGA build.
- Candidate validation: passed, 7 simulation cases plus FPGA build.
- Inactive candidate-vs-baseline audit: 0 changed rows across five inactive
  cases.
- Activation: first changed row 20; 55 left-channel changes; all `xor16=1`;
  zero right-channel changes.
- Boundary activation: first changed row 8 as predicted.
- Candidate synthesis: 3360/5280 LC, 2258 LUT4, 1182 FF, 104 carry, 0 DSP,
  0 BRAM, 5 IO; nextpnr Fmax 14.7926807403564 MHz; icetime 14.52 MHz.
- Repeated simulation and repeated build passed. Packed bitstream and pack /
  unpack round-trip SHA-256:
  `83ed6c5a7ce18a034ef523eb5e0bd4f01048a90a4c0af1543024c0723ea162cb`.

## Failed or pending checks

- Physical hardware verification: pending; no board was available.
- The initial harness run failed before the corrected authoritative run due to
  generic test-package integration errors; retained under
  `reports/*-validation-1/` and documented in the candidate README.

## Generated artifacts

Canonical artifact root: `experiments/phase05/05a-luna/`.

- RTL: `rtl/baseline/`, `rtl/candidate/`
- Tests: `tests/`
- Reports: `reports/candidate-validation-2/`,
  `reports/baseline-validation-2/`, `reports/activation-analysis.json`,
  `reports/candidate-sim-repeat/`, `reports/candidate-build-repeat/`
- AI records: `ai/design-research.md`, `ai/interaction-log.md`
- Manifest: `experiments/phase05/05a-luna/manifest.json`

## Exact reproduction commands

See `experiments/phase05/05a-luna/manifest.json` and the candidate README. The
authoritative validation commands use the pinned local OSS CAD Suite at
`C:/Users/lowbr/oss-cad-suite`.

## Documentation status

The existing Project Scribe is prepared but not activated for model synthesis or
Google publication. Candidate research, AI interaction, README, manifest, and
this handoff are supplied through its model-free preview interface in the
candidate checkout; no private transcript or credential was published.

## Dependencies for next phase

- Independent comparison against the other Phase 5 candidates.
- Optional physical Hackster programming and host-link test.
- No merge into another attempt is requested by this handoff.

## Remote push status

Not pushed. The branch contains unreleased competition artifacts and remains
local for approved independent comparison.
