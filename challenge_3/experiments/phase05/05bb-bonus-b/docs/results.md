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
