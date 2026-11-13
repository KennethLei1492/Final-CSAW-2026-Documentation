# 05A design research and selection

## Scope and evidence

The candidate targets the verified reconstructed 63-tap, signed-Q1.15 FIR and
Philips-I2S stream described by the Phase 2/3 handoffs and the Phase 4
integration. The source baseline is preserved at
`rtl/baseline/fir_audio_top_reference.v`; the candidate copy is the only RTL
modified for the Trojan experiment. The competition guidance requires an
AI-authored trigger and payload, bit-identical normal operation, and an
exploitable simulation demonstration. The official challenge repository and
the supplied prebuilt-AI-technique-models repository were used as research
references:

- https://github.com/JBlocklove/CSAW-AI-Hardware-Attack-Challenge-2026/tree/main/finals/challenge_3
- https://github.com/KennethLei1492/prebuilt-ai-technique-models

The local evidence used for interface and arithmetic decisions is:

- `rtl/baseline/fir_audio_top_reference.v`
- `rtl/baseline/phase4_dut_reference.v`
- `../../../../.worktrees/phase-03/handoffs/phase-03/INTERFACE.md` at the
  source baseline (the committed copy is summarized by
  `handoffs/phase-04/integration-validation.json`)
- `handoffs/phase-04/integration-validation.json`

## Candidate comparison

| Candidate | Trigger | Payload | Specificity / baseline compatibility | FPGA/resource and testability assessment | Decision |
|---|---|---|---|---|---|
| A | Three exact consecutive 16-bit left-channel words | Sticky XOR of filtered output LSB | Very specific; inactive path is untouched; reuses the baseline `new_sample` event | Two-bit progress state, three 16-bit equality tests, and one payload bit. Deterministic in the existing decoded-sample domain and straightforward to prove with exact vectors | **Selected** |
| B | A long zero/silence run followed by one sentinel sample | Persistent gain or output mute | Easy to drive but silence is plausible ordinary audio, so the trigger is broader and less stealthy | Small counter, but payload requires a larger output/gain datapath or visibly disruptive mute; rejected on false-trigger risk | Rejected |
| C | A serial I2S bit signature spanning a frame boundary | Drop/mutate one complete output frame | Can be made rare, but needs a second bit-level decoder and frame/bit alignment state | More flops and alignment-sensitive tests; a dropped frame is a conspicuous protocol effect | Rejected |
| D | Fixed frame-count or elapsed-time trigger | Coefficient tap or polarity change | Deterministic but not input-specific; normal use eventually activates it | Small counter but poor stealth because ordinary operation is enough to fire; rejected | Rejected |

Candidate A is best supported by the recovered architecture: the baseline
already exposes a completed left sample event inside its I2S decoder, so the
trigger does not duplicate the serial receiver. The payload is on the filtered
left result only; the right-channel echo remains a direct compatibility oracle.

## Chosen activation and expected behavior

The trigger words are:

```
left[n+0] = 16'h5A3C
left[n+1] = 16'hC3A5
left[n+2] = 16'h96E1
```

The sequence must be consecutive completed left-channel samples. The matcher
allows a restart when a new word equals the first trigger word. It latches
`payload_active` on the third match and does not clear it until power cycle.
There is no external reset in the recovered design, so the candidate uses the
same power-up initialization convention.

After activation, the candidate changes the filtered result from `y` to
`y ^ 16'h0001` for the third trigger sample and every later logical sample.
The echo result is unchanged. The existing two-frame transport latency is
preserved, so the first changed left output is at output frame `n+2`, where
`n` is the index of the third trigger word. Before that point the output is
bit-identical to the verified baseline.

For unconstrained 16-bit samples, an exact three-word sequence has probability
2^-48 at any specified position. This is a trigger-specificity estimate, not a
claim about a statistical speech distribution; the actual acceptance test also
streams the supplied audio and deterministic random vectors and checks that
the trigger remains inactive.

## Acceptance criteria

1. Candidate and reference baseline compile and elaborate with Icarus.
2. Inactive canonical audio, edges, random, silence, and near-miss sequences
   have zero mismatches against the baseline reference model.
3. The exact sequence activates once, at the third word; the first changed
   logical sample is exactly one LSB from the baseline, and all right-channel
   echoes remain equal.
4. A one-word near miss and all tested ordinary/random inputs do not activate.
5. UP5K/SG48 synthesis, place-and-route, pack/unpack, and timing complete with
   a 10 MHz constraint met.
6. Repeating the deterministic build yields the same packed bitstream hash.
7. Physical board verification is reported separately and remains pending if
   no board is attached.
