# CSAW_FIN Phase 05BB — project documentation

Report: 2026-11-13T07-35-06.429Z-73f2481c
Observed: 2026-11-13T07:35:06.035Z
Coverage: events 1–1; 0 queued for a later report; 1 events retained.

This report separates model interpretation, agent claims, Git observations, and recorded command results. Citations identify evidence, not a guarantee that a claim is true.

## Evidence preview

No model synthesis or Google Docs write was performed.

## Sessions observed (historical totals)

- test-runner / phase05bb-validation: 1 events; last seen 2026-11-13T07:34:39.253Z.

## Git evidence

### [git:0] C:\Users\lowbr\Documents\College\AI\CSAW_FIN\.worktrees\phase-05bb

Branch: challenge3/05bb-bonus-b; HEAD: fd0ca7f6bce1d30bb1b1e6ce43603b4c7d51e5b6.
Previous HEAD: (first observation); continuous ancestry: false.

Status:
```text
?? experiments/phase05/05bb-bonus-b/.gitignore
?? experiments/phase05/05bb-bonus-b/README.md
?? experiments/phase05/05bb-bonus-b/ai/execution-notes.md
?? experiments/phase05/05bb-bonus-b/ai/provenance.md
?? experiments/phase05/05bb-bonus-b/baseline-build-manifest.json
?? experiments/phase05/05bb-bonus-b/constraints/hackster.pcf
?? experiments/phase05/05bb-bonus-b/docs/candidate-selection.md
?? experiments/phase05/05bb-bonus-b/docs/hardware-procedure.md
?? experiments/phase05/05bb-bonus-b/docs/reproduce.md
?? experiments/phase05/05bb-bonus-b/docs/results.md
?? experiments/phase05/05bb-bonus-b/docs/verification-contract.md
?? experiments/phase05/05bb-bonus-b/evidence-inventory.json
?? experiments/phase05/05bb-bonus-b/inputs/input.wav
?? experiments/phase05/05bb-bonus-b/inputs/message.txt
?? experiments/phase05/05bb-bonus-b/inputs/original.bits
?? experiments/phase05/05bb-bonus-b/inputs/packet.hex
?? experiments/phase05/05bb-bonus-b/inputs/protocol.json
?? experiments/phase05/05bb-bonus-b/inputs/vectors.hex
?? experiments/phase05/05bb-bonus-b/official/challenge-README.md
?? experiments/phase05/05bb-bonus-b/official/fpga/Makefile
?? experiments/phase05/05bb-bonus-b/official/fpga/hackster-fpga-program.py
?? experiments/phase05/05bb-bonus-b/official/fpga/hackster.mk
?? experiments/phase05/05bb-bonus-b/official/ice40_audio_filter_IP.md
?? experiments/phase05/05bb-bonus-b/official/tools/audio_bridge.py
?? experiments/phase05/05bb-bonus-b/official/tools/stream_audio.py
?? experiments/phase05/05bb-bonus-b/rtl/audio_lab_tx.v
?? experiments/phase05/05bb-bonus-b/rtl/fir_audio_top.v
?? experiments/phase05/05bb-bonus-b/rtl/phase4_dut.sv
?? experiments/phase05/05bb-bonus-b/source-inventory.json
?? experiments/phase05/05bb-bonus-b/tests/rtl/run_checks.py
?? experiments/phase05/05bb-bonus-b/tests/rtl/tb_audio_lab_tx.sv
?? experiments/phase05/05bb-bonus-b/tools/decode.py
?? experiments/phase05/05bb-bonus-b/tools/evaluate.py
?? experiments/phase05/05bb-bonus-b/tools/package_evidence.py
?? experiments/phase05/05bb-bonus-b/tools/prepare.py
?? experiments/phase05/05bb-bonus-b/tools/run_channel.py
?? experiments/phase05/05bb-bonus-b/tools/test_decoder.py
?? experiments/phase05/05bb-bonus-b/tools/verify_package.py
?? experiments/phase05/05bb-bonus-b/verification-evidence.zip

```
Staged changes:
```text
(none)
```
Unstaged changes:
```text
(none)
```
Committed changes since checkpoint:
```text
(none or no continuous baseline)
```
Commits (bounded):
```text
fd0ca7f 2026-11-13T00:48:07-05:00 chore(quality): reissue source inventory and preserve verification provenance
f45ad42 2026-11-13T00:47:32-05:00 fix(05b): consume first post-bypass sample for immediate retrigger
82c56f8 2026-11-13T00:40:18-05:00 test(quality): freeze selected 05B baseline and reproduce bypass boundary defect
9e172a8 2026-11-12T23:31:10-05:00 docs: finalize Astra verification receipts
dbca705 2026-11-12T23:21:56-05:00 docs: complete Astra reliability handoff with full audio evidence
be3a5e1 2026-11-12T23:00:29-05:00 test: add full noisy audio regression for candidate B
15a8a65 2026-11-12T22:27:40-05:00 Add independently verified Phase 5B candidate B
e72522f 2026-11-12T20:09:54-05:00 docs: record recovered audio integration and timing validation
8fd929a 2026-11-12T20:07:53-05:00 feat: integrate verified Phase 2 audio RTL vectors and reference model
2da1d72 2026-11-12T19:10:12-05:00 docs: hand off verified Phase 4 infrastructure evidence and dependencies
2c04dba 2026-11-12T19:08:47-05:00 fix: widen simulation watchdog arithmetic for long captures
f8da331 2026-11-12T19:06:41-05:00 build: integrate one-command RTL regression and repeatable iCE40 builds

```
- Git status and log are bounded observations, not authorship or test verification. Untracked file contents are not read.
- Patch contents disabled.

[source:0:0] Source: experiments/phase05/05bb-bonus-b/docs/results.md; SHA-256 0fea793dcd150c55489f4ab5a6853e7ee8b3fdcd46a8751d766f86af28d5eba9
```text
# Results and supported bonus status

**PARTIAL DEMONSTRATION — simulation-only recovery.** The available evidence
supports the official Bonus B simulation tier, potentially **5/10**, subject to
judging and submission requirements. It does not support the 10-point physical
bit-exact tier. No physical Hackster was identified or programmed; the serial
inventory contained Bluetooth serial ports only. No hardware recording exists.

## Stage A: output-channel recovery

The HDL testbench captures the experimental FPGA's serialized filtered-left
output and saves it as mono PCM16 WAV. The host decoder reads that WAV alone.
Only the later evaluator reads the original synthetic bits. Each run transmits
three independently triggered frames of `CSAW26-BONUS-B`, or 336 payload bits.

| Simulated sample rate | Compared bits | Errors | BER | Whole capture duration | Net payload rate | Raw signaling rate |
|---:|---:|---:|---:|---:|---:|---:|
| 31,250 samples/s | 336 | 0 | 0/336 | 0.537344 s | 625.297761 bit/s | 976.5625 bit/s |
| 15,625 samples/s | 336 | 0 | 0/336 | 1.074688 s | 312.648880 bit/s | 488.28125 bit/s |

These durations are measured from the complete captured sample count divided by
the configured simulated sample rate. They include activation, sync, length,
CRC, guards, and tail. They are **not** elapsed physical USB transfer times or
simulation process wall times. Each frame has 112 payload bits and 56 overhead
bits. Three packets at each of two rates demonstrate deterministic repetition
in simulation, not three independent physical trials. Zero observed BER in
these finite noiseless runs does not establish a physical error probability.

The following controls passed:

- Original input and right-echo recordings produced no recovered payload frame.
- The immutable source candidate's filtered-left output did not recover the
  payload under the same activation stimulus.
- Silence did not decode as a successful frame.
- Flipping one payload symbol after capture produced exactly one error out of
  336 bits, BER `1/336 = 0.002976190476`, and one CRC-invalid frame. Only the
  remaining 224 valid payload bits counted toward throughput: 416.865174 bit/s
  at 31,250 samples/s and 208.432587 bit/s at 15,625 samples/s.
- Truncating the last frame produced invalid aggregate alignment, null BER,
  and zero accepted aggregate throughput. It did not become a zero-error pass.

The last two controls are explicitly software alterations of simulation output;
they are decoder checks, not observed hardware channel corruption.

Primary evidence is `evidence/channel-run-1/channel-summary.json`. Each
`channel-31250/` and `channel-15625/` subdirectory contains `original.bits`,
`input.wav`, `simulation-filtered-left.wav`, `simulation-right-echo.wav`, decoder
logs, `recovery/recovered.bits`, `recovery/decode.json`, and
`recovery/evaluation/bit-comparison.csv` and `evaluation.json`. The evidence
inventory hashes preserved run artifacts.

## Stage A: baseline and boundary tests

The fresh RTL verification summary reports 42 regression cases, 56,596 compared
words, and zero mismatches: 10 original candidate cases (25,564 words), 30 Q
directed cases (30,000 words), and two recovered golden cases (1,032 words).
The original suite includes seven inactive baseline cases (22,248 words) and
three existing bypass cases. The framework's 15 tests also passed.

Focused module tests checked 10,752 exact waveform samples, all eight single-word
activation near misses, unticked inputs, prefix restart, ignored in-payload
activation, bounded payload length, and immediate post-payload rearming.

These results are in `reports/rtl-verification-summary.json` and the retained
subreports/logs it names. The source candidate's earlier uninterrupted full-audio
result is inherited selection evidence; it is not a fresh full-audio run of the
experimental design. Golden data were not altered.

## Stage B: synthesis and timing

RTL elaboration, synthesis, placement/routing, and bitstream generation passed
for iCE40-UP5K, SG48, deterministic seed 1, inherited nine-pin constraints, and
10 MHz `ICE_CLK`. The experimental build uses 3,455/5,280 logic cells, zero DSP,
and zero RAM blocks. It adds 215 cells versus the Q source's common-flow 3,240
cells, leaving 1,825 available. The reported maximum system-clock frequency is
15.433290 MHz against the 10 MHz constraint.

Experimental bitstream SHA-256:
`4c27a28220f5cb3f254f1bb82f4f47c6ae1c5dd0d3bcd700459bdf35e2c70056`.
Detailed logs and timing/utilization reports are retained under
`reports/baseline-build-run1/`. The free-running system clock is constrained;
asynchronous I2S behavior is exercised through oversampling simulation, not a
complete physical-board timing signoff. LED/RGB roles retain inherited tentative
pin interpretation.

## Stage C and remaining submission work

Stage C was not run. `evidence/serial-ports.json` records the local probe; the
absence of an identified board precludes programming and actual output capture.
Follow `hardware-procedure.md` when an authorized board is available, including
stock/inactive baseline captures and repeated experimental trials.

The source candidate remains available at its immutable SHA. The experimental
branch is local and has not been merged or published. Complete prompt/response
transcript export and historical provenance certification remain required before
submission; `ai/provenance.md` explicitly records that limitation. Phase 5S may
compare this package as simulation-tier Bonus B evidence, and Phase 8 may package
it locally with that classification preserved.

```

[source:0:1] Source: experiments/phase05/05bb-bonus-b/docs/candidate-selection.md; SHA-256 6143f1f3a35f0325faf4a5a022067e183ec8e134861a054b6d0ed465ed9a7fde
```text
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

```

[source:0:2] Source: experiments/phase05/05bb-bonus-b/docs/verification-contract.md; SHA-256 5799dee45dbf01bd2cc5b0f3d00630913a4b69d6f4e7f2ae3be05b5cc1c54e55
```text
# Bonus B verification contract

This experiment is limited to the supplied Challenge 3 FPGA design, local
simulation, and an explicitly identified authorized Hackster board. The only
payload is the synthetic ASCII message `CSAW26-BONUS-B`. No credentials, private
memory, device secrets, or unrelated data sources are inputs.

The official [Challenge 3 rubric](https://github.com/JBlocklove/CSAW-AI-Hardware-Attack-Challenge-2026/blob/main/finals/challenge_3/README.md#bonus-b---covert-channel-up-to-10-points)
requires chosen data carried through the normally filtered audio output,
host recovery, a documented method, and measured bit/error rates. Its potential
tiers are 10 points for reproducible bit-exact physical-board recovery, 5 for
partial/unreliable recovery or simulation-only recovery, and 0 if unsubstantiated.
Only the judges can award credit. The inspected official README Git blob is
`4159341c417f652fea45cd412d79cc52f0d9cad4`.

## Test protocol

The test activation is eight consecutive input sample words, in hexadecimal:
`1357 ECA8 2468 DB97 369C C963 55AA AA55`. Signed PCM16 represents words above
`7FFF` as negative values. Following activation, the host supplies silence.
The FPGA serializes an explicitly compiled synthetic payload; the input stream
does not contain that payload.

The transmitted frame contains a 32-bit sync word `D391C5A7`, an 8-bit byte length,
the 14-byte payload (112 bits), and a 16-bit CRC-CCITT over length and payload.
The 168 signaling bits include 56 overhead bits. Each signaling bit occupies
32 output samples. Binary zero uses an eight-sample square-wave period; one uses
a four-sample period. Amplitude is signed PCM16 `+4096` or `-4096`.

At 31,250 samples/s, this defines 976.5625 raw signaling bits/s and a 5,376-sample
frame lasting 0.172032 s. These are protocol quantities, not a physical-board
measurement. Reported throughput must include the actual chosen measurement
window, including framing and failed attempts; it must not simply substitute the
raw signaling rate. A second 15,625 samples/s test checks rate dependence.

## Required evidence chain

1. Preserve the original synthetic payload bit file and its hash.
2. Record the exact source commit, experiment commit, RTL/build hashes, tool
   versions, clock settings, framing, and test commands.
3. Capture the experimental **filtered-left output** from the serial I2S monitor
   in simulation or the documented USB/RP2040 audio bridge on hardware.
4. Run host recovery using that audio recording as its only measurement input.
   The recovery step must not read the expected bit file, source input, right
   echo, RTL payload constant, or an auxiliary debug signal.
5. Save reconstructed payload bits before loading the original bits for scoring.
6. Compare original and recovered bits by index and retain the comparison,
   errors, bit count, alignment/framing status, and elapsed transmission duration.
7. Include silence, original-input, and right-echo negative controls so input or
   echo copying cannot be mistaken for output-channel recovery.
8. Preserve failed runs and conditions as well as successes.

BER is incorrect recovered bits divided by total compared bits, defined only
when payload framing and alignment are established. A failed decode is a failed
transmission, not zero BER. Net payload bit rate is correctly framed recovered
payload bits divided by elapsed transmission time. Framing/CRC failure produces
zero valid payload throughput for that attempt. Report raw signaling rate,
frame overhead, and useful throughput separately.

## Staged claims

Software and RTL simulation must establish deterministic recovery plus inactive
baseline equivalence. Synthesis must check elaboration, UP5K resources, 10 MHz
timing constraints, placement/routing, and bitstream generation. Those tools do
not establish electrical or physical-board correctness.

Physical qualification requires the experimental bitstream on the authorized
board, the documented left-output WAV capture, host recovery, exact comparison,
and repeated trials. The stock golden baseline and inactive experiment must also
be captured and compared on that board. A right-channel link self-test alone
does not establish filter correctness or a data channel.

Use `FULL DEMONSTRATION` only for reproducible bit-exact physical recovery;
`PARTIAL DEMONSTRATION` for meaningful simulation-only, partial, or unreliable
recovery; and `NOT SUBSTANTIATED` when no meaningful recovery exists. Never label
simulation-generated audio as hardware recording. Final measured results and
evidence paths belong in the experiment manifest and the Phase 05 handoff.

```

[source:0:3] Source: experiments/phase05/05bb-bonus-b/ai/provenance.md; SHA-256 57cc719d1a547fedb9e766c27069e19014179b2e8d1b6e8a10d73954d5a0c505
```text
# AI provenance and scope

The Phase 05BB implementation and test logic were authored through the Codex
coding-agent session that received the user's Phase 5BB laboratory-demonstration
request. The runtime identifies the assistant as **Codex, based on GPT-6**;
the exact deployment/model snapshot is not exposed and is recorded as unknown.
The requested role label, `Claude Code Opus 4.8`, is a user-specified role, not
evidence of the executing model. No claim that Claude authored this work follows
from that label.

The root coding agent delegated read-only candidate inspection, documentation
support, and separable engineering work to Codex child agents. Delegation retains
the runtime identity uncertainty. Git commits establish file history, not model
authorship by themselves. The original candidate's historical provenance remains
with its source evidence; the prior Astra role label versus recorded Luna runtime
discrepancy must not be erased or retroactively relabeled.

The user authorized a synthetic-only, competition-scoped audio-output experiment,
candidate comparison, isolated branch, local verification, and local commits.
The payload `CSAW26-BONUS-B` is an explicit synthetic test string. Implementation
does not consume credentials, private memory, device secrets, or other data
sources. No human-written hardware is claimed for the new experimental logic.
Human review of this result is distinct from authorship of RTL.

The root agent and child agents inspect source and evidence, author changes,
invoke deterministic software/HDL/build tools, and report their actual outcomes.
The existing Project Scribe controller is used for local evidence collection and
documentation handoff, with Google publication disabled and isolated state.
If model synthesis is unavailable, its receipt must say so explicitly; a preview
must not be described as a synthesized documentation-agent report.

## Transcript completeness limitation

This provenance note is **not** a substitute for the competition's comprehensive
prompt/response transcript requirement. This task does not inspect or export
private transcript stores. Before submission, the operator must preserve/export
this session and relevant child-agent interactions through the application's
supported export path, review the package locally, and include all required
historical AI interactions. Exact export availability and transcript completeness
have not been certified by this experiment. The runtime model identity and
missing historical metadata must remain truthful in submission materials.

No public push, merge into the selected main candidate, Google publication, or
private-transcript publication is authorized by the local commit operation.

```

[source:0:4] Source: experiments/phase05/05bb-bonus-b/reports/rtl-verification-summary.json; SHA-256 ea20c17f431ec36cd9c0a104d5953b2ac712c682cee3045cb4f5f41619c04a16
```text
{
  "source_commit": "fd0ca7f6bce1d30bb1b1e6ce43603b4c7d51e5b6",
  "framework_tests": {
    "passed": 15,
    "failed": 0,
    "log": "baseline-build-run1/unit-tests.log"
  },
  "original_candidate_regression": {
    "passed": 10,
    "failed": 0,
    "compared_words": 25564,
    "mismatches": 0,
    "inactive_baseline_cases": 7,
    "inactive_baseline_words": 22248,
    "original_bypass_cases": 3,
    "report": "baseline-build-run1/report.json"
  },
  "q_directed": {
    "passed": 30,
    "failed": 0,
    "compared_words": 30000,
    "mismatches": 0,
    "audit": "q-directed-audit.json"
  },
  "phase2_golden": {
    "passed": 2,
    "failed": 0,
    "compared_words": 1032,
    "mismatches": 0,
    "report": "q-common-run1/report.json"
  },
  "lab_module_boundary": {
    "passed": true,
    "exact_pcm_samples_checked": 10752,
    "checks": [
      "eight single-word near misses",
      "unticked input ignored",
      "prefix restart",
      "in-payload trigger ignored",
      "exact bounded waveform length",
      "immediate post-payload rearm"
    ],
    "log": "lab-boundary-run1/simulate.log"
  },
  "build": {
    "passed": true,
    "frequency_mhz": 10.0,
    "fmax": {
      "ICE_CLK$SB_IO_IN_$glb_clk": {
        "achieved": 15.433290481567383,
        "constraint": 10
      }
    },
    "seed": 1,
    "utilization": {
      "ICESTORM_DSP": {
        "available": 8,
        "used": 0
      },
      "ICESTORM_HFOSC": {
        "available": 1,
        "used": 0
      },
      "ICESTORM_LC": {
        "available": 5280,
        "used": 3455
      },
      "ICESTORM_LFOSC": {
        "available": 1,
        "used": 0
      },
      "ICESTORM_PLL": {
        "available": 1,
        "used": 0
      },
      "ICESTORM_RAM": {
        "available": 30,
        "used": 0
      },
      "ICESTORM_SPRAM": {
        "available": 4,
        "used": 0
      },
      "IO_I3C": {
        "available": 2,
        "used": 0
      },
      "SB_GB": {
        "available": 8,
        "used": 3
      },
      "SB_I2C": {
        "available": 2,
        "used": 0
      },
      "SB_IO": {
        "available": 39,
        "used": 9
      },
      "SB_LEDDA_IP": {
        "available": 1,
        "used": 0
      },
      "SB_RGBA_DRV": {
        "available": 1,
        "used": 0
      },
      "SB_SPI": {
        "available": 2,
        "used": 0
      },
      "SB_WARMBOOT": {
        "available": 1,
        "used": 0
      }
    },
    "constrained_pins": true,
    "hardware_validated": false,
    "bitstream_sha256": "4c27a28220f5cb3f254f1bb82f4f47c6ae1c5dd0d3bcd700459bdf35e2c70056"
  },
  "physical_board": {
    "performed": false,
    "status": "not_run"
  },
  "limits": [
    "Timing analysis constrains free-running ICE_CLK to 10MHz; asynchronous I2S is functionally checked via oversampling simulations, not a complete board timing signoff.",
    "LED/RGB individual roles retain inherited tentative constraint mapping.",
    "Fresh regression includes canonical golden and 1024-frame noisy audio cases; prior full-audio evidence belongs to immutable selected source and is not newly asserted here."
  ],
  "reproduction": [
    "python experiments/phase05/05bb-bonus-b/tests/rtl/run_checks.py --suite C:/Users/lowbr/oss-cad-suite --output build/05bb-rtl-repeat"
  ]
}

```

[source:0:5] Source: experiments/phase05/05bb-bonus-b/evidence/channel-run-1/channel-summary.json; SHA-256 3a76d7b553c8ef0e5ae03a79e89bdd52f7a162b821c437db915b2a361ff3d373
```text
{
  "31250": {
    "alignment_valid": true,
    "incorrect_recovered_bits": 0,
    "total_compared_bits": 336,
    "expected_payload_bits": 336,
    "ber": 0.0,
    "attempted_frames": 3,
    "recovered_frames": 3,
    "crc_valid_frames": 3,
    "failed_frames": 0,
    "correctly_framed_recovered_payload_bits": 336,
    "elapsed_transmission_seconds": 0.537344,
    "duration_basis": "entire_capture_samples/sample_rate",
    "net_recovered_payload_bps": 625.2977608384945,
    "raw_signaling_bps": 976.5625,
    "bit_exact": true,
    "methodology": "Whole capture includes trigger, sync, length, CRC, guards and failed attempts. No payload-based alignment; count/length failure gives null BER and zero net accepted throughput."
  },
  "corruption-31250": {
    "alignment_valid": true,
    "incorrect_recovered_bits": 1,
    "total_compared_bits": 336,
    "expected_payload_bits": 336,
    "ber": 0.002976190476190476,
    "attempted_frames": 3,
    "recovered_frames": 3,
    "crc_valid_frames": 2,
    "failed_frames": 1,
    "correctly_framed_recovered_payload_bits": 224,
    "elapsed_transmission_seconds": 0.537344,
    "duration_basis": "entire_capture_samples/sample_rate",
    "net_recovered_payload_bps": 416.86517389232966,
    "raw_signaling_bps": 976.5625,
    "bit_exact": false,
    "methodology": "Whole capture includes trigger, sync, length, CRC, guards and failed attempts. No payload-based alignment; count/length failure gives null BER and zero net accepted throughput."
  },
  "truncation-31250": {
    "alignment_valid": false,
    "incorrect_recovered_bits": null,
    "total_compared_bits": 0,
    "expected_payload_bits": 336,
    "ber": null,
    "attempted_frames": 3,
    "recovered_frames": 2,
    "crc_valid_frames": 2,
    "failed_frames": 1,
    "correctly_framed_recovered_payload_bits": 0,
    "elapsed_transmission_seconds": 0.358176,
    "duration_basis": "entire_capture_samples/sample_rate",
    "net_recovered_payload_bps": 0.0,
    "raw_signaling_bps": 976.5625,
    "bit_exact": false,
    "methodology": "Whole capture includes trigger, sync, length, CRC, guards and failed attempts. No payload-based alignment; count/length failure gives null BER and zero net accepted throughput."
  },
  "15625": {
    "alignment_valid": true,
    "incorrect_recovered_bits": 0,
    "total_compared_bits": 336,
    "expected_payload_bits": 336,
    "ber": 0.0,
    "attempted_frames": 3,
    "recovered_frames": 3,
    "crc_valid_frames": 3,
    "failed_frames": 0,
    "correctly_framed_recovered_payload_bits": 336,
    "elapsed_transmission_seconds": 1.074688,
    "duration_basis": "entire_capture_samples/sample_rate",
    "net_recovered_payload_bps": 312.64888041924723,
    "raw_signaling_bps": 488.28125,
    "bit_exact": true,
    "methodology": "Whole capture includes trigger, sync, length, CRC, guards and failed attempts. No payload-based alignment; count/length failure gives null BER and zero net accepted throughput."
  },
  "corruption-15625": {
    "alignment_valid": true,
    "incorrect_recovered_bits": 1,
    "total_compared_bits": 336,
    "expected_payload_bits": 336,
    "ber": 0.002976190476190476,
    "attempted_frames": 3,
    "recovered_frames": 3,
    "crc_valid_frames": 2,
    "failed_frames": 1,
    "correctly_framed_recovered_payload_bits": 224,
    "elapsed_transmission_seconds": 1.074688,
    "duration_basis": "entire_capture_samples/sample_rate",
    "net_recovered_payload_bps": 208.43258694616483,
    "raw_signaling_bps": 488.28125,
    "bit_exact": false,
    "methodology": "Whole capture includes trigger, sync, length, CRC, guards and failed attempts. No payload-based alignment; count/length failure gives null BER and zero net accepted throughput."
  },
  "truncation-15625": {
    "alignment_valid": false,
    "incorrect_recovered_bits": null,
    "total_compared_bits": 0,
    "expected_payload_bits": 336,
    "ber": null,
    "attempted_frames": 3,
    "recovered_frames": 2,
    "crc_valid_frames": 2,
    "failed_frames": 1,
    "correctly_framed_recovered_payload_bits": 0,
    "elapsed_transmission_seconds": 0.716352,
    "duration_basis": "entire_capture_samples/sample_rate",
    "net_recovered_payload_bps": 0.0,
    "raw_signaling_bps": 488.28125,
    "bit_exact": false,
    "methodology": "Whole capture includes trigger, sync, length, CRC, guards and failed attempts. No payload-based alignment; count/length failure gives null BER and zero net accepted throughput."
  },
  "source_candidate_control": {
    "alignment_valid": false,
    "incorrect_recovered_bits": null,
    "total_compared_bits": 0,
    "expected_payload_bits": 336,
    "ber": null,
    "attempted_frames": 3,
    "recovered_frames": 0,
    "crc_valid_frames": 0,
    "failed_frames": 3,
    "correctly_framed_recovered_payload_bits": 0,
    "elapsed_transmission_seconds": 0.537344,
    "duration_basis": "entire_capture_samples/sample_rate",
    "net_recovered_payload_bps": 0.0,
    "raw_signaling_bps": 976.5625,
    "bit_exact": false,
    "methodology": "Whole capture includes trigger, sync, length, CRC, guards and failed attempts. No payload-based alignment; count/length failure gives null BER and zero net accepted throughput."
  },
  "status": "passed",
  "hardware_verified": false,
  "classification": "PARTIAL DEMONSTRATION"
}

```

## Activity evidence

### [event:1] test-runner / phase05bb-validation

2026-11-13T07:34:39.253Z — TestCommand; model: not applicable; HEAD: fd0ca7f6bce1d30bb1b1e6ce43603b4c7d51e5b6.
Root: C:\Users\lowbr\Documents\College\AI\CSAW_FIN\.worktrees\phase-05bb
Tool: explicit command; recorded exit: 0.
Recorded command: ["C:/Users/lowbr/oss-cad-suite/lib/python3.exe","experiments/phase05/05bb-bonus-b/tools/verify_package.py"]; tracked state stable: true; output SHA-256: 4b4359b122fc03c728478bf15ef2fdfc805208422d5718d6a73d6824ab4aaadb.
Recorded output excerpt:
```text
{"passed": true, "source_files": 27, "archived_evidence_files": 634, "source_candidate_unchanged": true, "hardware_verified": false, "classification": "PARTIAL DEMONSTRATION"}


```

## Evidence limits

Hooks observe configured local sessions only. Missing model identifiers remain unknown. A successful tool call or Stop event does not prove a successful test. Shared-worktree changes are not attributable to one session. Source reads and Git snapshots are not atomic with concurrent edits. Test wrapper fingerprints cover HEAD, tracked diffs, and status names, not all untracked bytes. Older reports and events remain local.
