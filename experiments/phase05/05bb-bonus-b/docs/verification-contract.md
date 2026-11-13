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
