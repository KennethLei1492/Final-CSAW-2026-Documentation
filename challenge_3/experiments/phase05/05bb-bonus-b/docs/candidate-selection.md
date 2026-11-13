# Starting-point decision

Use the Subphase Q corrected 05B implementation at immutable commit
`fd0ca7f6bce1d30bb1b1e6ce43603b4c7d51e5b6`. The dedicated worktree is
`C:/Users/lowbr/Documents/College/AI/CSAW_FIN/.worktrees/phase-05bb`, on branch
`challenge3/05bb-bonus-b`. The selected commit remains the rollback reference;
its candidate files and the Phase 3 golden oracle are not replaced by the
experiment.

## Inspected candidates and evidence

Both implementations exist locally, including unpublished 05D. Inspection covered
their actual RTL, manifests, simulation reports, build evidence, Phase 05S
selection, Subphase Q repair evidence, Phase 3 baseline arithmetic, and Phase 4
verification infrastructure. The decision does not infer availability from
remote branches alone.

| Evidence | Identity |
|---|---|
| Original 05B | `9e172a865a543b03e226596689fd6691ffa2b779` |
| Selected Q-corrected 05B | `fd0ca7f6bce1d30bb1b1e6ce43603b4c7d51e5b6` |
| Original 05D | `629c7d4a1dd158ff1b6585e0e84e9aff74f8810f` |
| Latest local 05D | `51c223336f3d4d23854907bdee87dfd5ac1f2e98` |
| Phase 3 baseline | `5dedf4c4ed10f47fbe9ec138c7db2019446cdb7f` |
| Phase 4 infrastructure | `e72522f265ac36da713cd7a0dcf8dbc64ab21209` |
| Initial Phase 05S selection | `6d9cacf4e12a7f2357c4f36fa91d9ef87429d046` |
| Phase 05S cycle 002 | `bcca3c8` (local selection branch) |

Local source worktrees are `../CSAW_FIN_worktrees/05b-astra` and
`../CSAW_FIN_worktrees/05d-opus-dsp` relative to the project root. During this
inspection, `git ls-remote --heads origin` showed 05B remote branch
`challenge3/05b-astra` at `15a8a6525e225ad82d931b3bc75399f744638b2e` and no remote
05D branch. Remote and local tip differences do not supersede the pinned source
decision. No fetch, push, merge, or candidate worktree edit is required to use
the already available selected commit.

## Engineering comparison

Both candidates use signed 16-bit samples, 63 Q1.15 coefficients, a 40-bit
accumulator, rounding by adding `2^14` before arithmetic shift by 15, and signed
16-bit saturation. Halfway rounding is toward positive infinity. Both retain
the recovered serial interface and inactive filter behavior: two frames of
transport latency plus the FIR's 31-sample group delay. There is no demonstrated
numerical-precision advantage for either inactive design.

05B recognizes eight exact left-channel samples, then selects a bounded
128-frame bypass at its output multiplexer. Subphase Q corrected a boundary
defect that skipped the first trigger sample immediately after bypass ended.
This bounded sample-level output selection is a straightforward insertion point
for a finite synthetic waveform, with automatic return to ordinary filtering.

05D detects an approximately `fs/3` tone using a 576-sample Goertzel-based trigger
and enables a sticky coefficient transformation that negates odd-indexed FIR
coefficients. It retains the 31-sample group delay and changes the spectral
response. That DSP design is useful analysis, but it does not itself serialize
chosen payload bits or supply a demonstrated host decoder. Its longer trigger
and persistent mode add work to a bounded laboratory-transmitter experiment.

The common Phase 05S comparison reports Q 05B at 3,240/5,280 logic cells and
15.2716 MHz versus a 10 MHz constraint; 05D at 3,652 cells and 15.1833 MHz. That
leaves 2,040 cells for Q versus 1,628 for D, a 412-cell advantage under that flow.
Both use zero DSP blocks and zero RAM blocks. All these are tool estimates,
not measured board timing. Candidate-owned historical build figures must be
distinguished from common-flow results; they are not interchangeable.
For example, D's native `reports/evidence/trojan-build-summary.json` reports
3,704 cells and 14.4090 MHz, while the later common-flow comparison reports the
figures above. Both builds fit; the selection uses the common-flow comparison.

Q's retained evidence covers 46 simulation cases (10 standard, two common,
30 directed, four overlapping full-audio segments), plus 15 framework tests.
The directed boundary correction changed 28/30 passes to 30/30 without changing
previous normal/full-audio captures. Phase 05S cycle 002 adds a fresh uninterrupted
simulation: 480,260/480,260 output words exact, including both left filtering
and right echo over the full 240,000-frame source plus flush. Its fresh framework
run passed 15/15, source inventory 41/41, and retained Q artifact hashes 230/230.
Those counts describe different suites; they must not be added as unique samples.

05D has credible inactive and active simulation evidence (10 inactive and three
active cases in its candidate package), and its latest local commit supplies
additional report/analysis material while leaving RTL unchanged. Its scripts
also contain original-worktree path assumptions and some referenced verification
outputs are absent. Passing available D tests is evidence within that tested
scope, not a demonstrated functional defect or proof of unreliability.

Original 05B source/build receipt inconsistencies were a reason to prefer the
verified Q successor rather than simply trust the old package. Q's retained
bitstream SHA-256 is
`2742912e31ec6c058756e5623d84736285dc2d46695d8ece616494e3152a89b0`.
That is a source-candidate artifact, not the forthcoming experiment bitstream.

Neither candidate has physical-board evidence or an existing measured Bonus B
recovery result. Ordinary bypass or spectral inversion does not establish a data
channel. The experiment must supply its own output-only recovery, comparisons,
BER, throughput, baseline tests, and build reports.

## Decision and preservation

Q 05B wins on the combination of explicit bounded output control, unchanged
numerical baseline, larger logic margin, corrected boundary behavior, wider
verified coverage, and reconciled reproducibility evidence. Neither its role
label nor its passing regression count alone decides this choice. 05D's actual
mechanism and supporting evidence were considered.

The experiment adds its own source tree under
`experiments/phase05/05bb-bonus-b/` and uses the existing engineering flow. The
original source candidate stays immutable, and experimental changes must pass
fresh comparisons against that source and the unchanged golden oracle. No
experiment is merged into a main candidate automatically.

Supporting retained records include `handoffs/quality-review/` in this source
tree and the Phase 05S cycle 002 selection/report files in the separate
`.worktrees/phase-05s-cycle-02` worktree. Final handoffs identify fresh experimental
evidence separately from these inherited candidate results.
