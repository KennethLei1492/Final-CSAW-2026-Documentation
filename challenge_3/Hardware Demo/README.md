# MicroPython Trojan models — Challenge 3

Software (MicroPython) models of the four Challenge 3 hardware Trojan
candidates. The real candidates are Verilog Trojans grafted onto a recovered
63-tap Q1.15 low-pass FIR audio filter for the Lattice iCE40-UP5K. These files
reproduce each Trojan's **behaviour** — the clean filter, the trigger detector,
and the payload — in portable integer Python that runs on a microcontroller
under MicroPython (rp2 / esp32 / unix ports) or on desktop CPython 3.

> These are behavioural models for analysis, test-vector generation and
> demonstration. They are not the bitstream and do not drive real I2S hardware.

## Files

| File | Candidate | Trigger | Payload |
|------|-----------|---------|---------|
| `fir_core.py` | — (shared) | — | Clean recovered 63-tap FIR, Q1.15, DC gain 1.0 |
| `trojan_05a_luna.py` | 05A Luna | 3-sample knock on **left** channel `(0x5A3C,0xC3A5,0x96E1)` | LSB flip of filtered output, sticky |
| `trojan_05b_astra.py` | 05B Astra *(selected)* | 8 consecutive **left** samples (magic sequence) | Bypass FIR for 128 frames, re-triggerable |
| `trojan_05c_opus_arch.py` | 05C Opus Architecture | 3-frame knock on an **independent right** slot `(0xC0DE,0xFACE,0xBEEF)` | Bypass FIR permanently, sticky |
| `trojan_05d_opus_dsp.py` | 05D Opus DSP | Goertzel tone detector at fs/3 (576-sample window, threshold 2^23) | Spectral inversion: low-pass → high-pass |

All Trojans share `fir_core.py` and the same pipeline framing: output frame
`m` carries `left[m-2]` / `right[m-2]` (2-frame latency), right channel is the
raw echo, and the first two frames are power-up zeros.

## Fidelity / provenance

- The FIR coefficients and arithmetic, and the **05B Astra** FSM, are ported
  bit-for-bit from the local reference
  `experiments/phase05/05b-astra/tests/` (`candidate_reference.py`,
  `reference/run_reference.py`, `reference/coeffs.json`).
- **05A, 05C, 05D** are ported from the Phase 5 reference scripts in the CSAW
  documentation repo (this local *quality-winner* copy ships only 05B):
  `05a-luna/tests/run_candidate_reference.py`,
  `05c-opus-architecture/tests/trojan_ref.py`,
  `05d-opus-dsp/tests/ref_trojan.py`. Each was fetched verbatim and checked
  line-for-line against this port.

### Verification performed

- `fir_core.FIR().step()` is bit-identical to the golden batch `fir_core.fir()`
  over 2000 random samples.
- Every Trojan is identical to the clean filter on untriggered input.
- **05A/05B/05D** match their reference trigger indices / activation counts
  (05A knock → index 22; 05B → 128 bypass frames; 05D → arms at sample 576 on a
  full-scale fs/3 tone).
- **05C** was diffed against a verbatim replica of the reference `arm_index`
  detector over **400 randomized stereo trials** (229 armed, exercising the
  restart-credit path) — outputs and armed indices matched exactly.

## Run a quick self-test (per file)

Each module has a built-in demo:

```bash
python3 trojan_05b_astra.py
```

On a MicroPython board, copy all five `.py` files to the device and:

```python
import trojan_05b_astra
trojan_05b_astra._demo()
```

## Use in your own code

Two interfaces per Trojan class:

- **Streaming** — `step(x)` feeds one `int16` input sample and returns one
  logical `int16` left-channel output (the right channel is just the echo `x`).
  Use this for real-time audio on a microcontroller. *(05C differs: its
  `step(left, right=None)` takes the knock on a separate right channel; omit
  `right` and it mirrors `left`, the real-system L = R case. Its `run()` accepts
  either a list of left ints or a list of `(left, right)` pairs.)*
- **Batch** — `run(samples)` returns `(frames, stats)`, where `frames` is a
  list of `(left, right)` `int16` tuples with the 2-frame latency applied, and
  `stats` describes the activation (trigger indices, active/armed frame counts).

```python
from trojan_05b_astra import AstraTrojan, MAGIC

t = AstraTrojan()
frames, stats = t.run([0]*10 + list(MAGIC) + [777]*200)
print(stats)   # -> trigger_events: 1, active_frames: 128, ...

# real-time:
t.reset()
for x in incoming_samples:
    left_out = t.step(x)      # right_out == x
```

## Notes

- Pure integer math; no `csv`, `argparse`, or `numpy`, so the modules import on
  a bare board. `trojan_05d_opus_dsp._demo()` uses `math` only to synthesize a
  test tone — the Trojan itself needs no floats.
- Samples are signed 16-bit (`-32768..32767`). Trigger comparisons that use hex
  magic values mask with `& 0xFFFF` exactly as the hardware does, so a signed
  input like `-15451` matches `0xC3A5`.
