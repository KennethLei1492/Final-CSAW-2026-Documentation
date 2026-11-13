# Challenge 3 — FIR Audio-Filter Trojans (Hackster iCE40 board)

**Status: AI-generated Trojans verified in cycle-accurate RTL simulation and signed off for UP5K synthesis/timing. No physical-board demonstration was performed — hardware verification is pending for every candidate.**

## Objective

The finals Challenge 3 target is a streaming **FIR audio filter** running on a Lattice
**iCE40-UP5K** (SG48) on a physical **Hackster** board. There is no key; the asset is
**data-path integrity** (the filter should pass only in-band audio). The RTL is *not*
supplied — teams reverse-engineer the provided **bitstream** (`fir_audio_top.bin`),
then use generative AI to design and insert a stealthy hardware Trojan whose untriggered
output stays bit-identical to the stock filter until a hidden trigger fires.

Per the competition rules, all Trojan RTL and exploit logic is **AI-generated**; humans
may use ordinary (non-AI) tools for reverse-engineering, build, and board bring-up. Every
AI interaction is meant to be retained in each candidate's `ai/` directory.

> **Scope / honesty note.** No physical Hackster board was available in this environment.
> Every result below is from **cycle-accurate RTL simulation** (Icarus Verilog) against
> golden vectors, plus **synthesis + place-and-route sign-off** for the UP5K
> (`yosys synth_ice40`, `nextpnr-ice40`, `icetime`). Board bring-up steps are documented
> for 1:1 hardware reproduction but have **not** been executed. The official rubric's
> physical Hardware Demonstration (10 pts) is therefore **unclaimed**, and the full
> main-session AI transcript capture required for the Creative-GenAI category is still
> outstanding. Simulation and hardware claims are kept separate throughout.

---

## 1. Reverse-engineering result (the original filter)

The bitstream was unpacked with IceStorm (`iceunpack`), converted to a gate-level netlist
(`icebox_vlog`), inventoried (`icebox_stat`), and simulated through a faithful I2S
testbench. Because the design uses **no DSP blocks**, the netlist is functionally complete
and directly simulatable, so the filter was recovered **exactly** rather than approximated.

| Property | Recovered value |
|---|---|
| Device / package | iCE40-UP5K, SG48, single `ICE_CLK` (~10 MHz) domain, no PLL |
| Filter | 63-tap Type-I linear-phase (symmetric) low-pass FIR, Q1.15 |
| DC gain | Σh = 32768 = **1.0** (0 dB); center tap `h[31]=13920` |
| −3 dB edge | **3296.4 Hz** (classic speech/telephony band) |
| Stopband | ≈ **56 dB** attenuation above 4 kHz (−55.9 dB worst case) |
| Group delay | 31 samples (1.94 ms); end-to-end latency 2 frames |
| Arithmetic | `y = sat16((acc + 2^14) >> 15)` — round half toward +∞, then int16-saturate |
| I2S framing | Philips, 16-bit MSB-first; left = filtered, right = unmodified echo |
| Resources (bitstream) | 299 DFF, 1260 LUT4, 124 CARRY, 1 BRAM (≤64×16 sample delay line), 9 IOB, **0 DSP** |

The 63-tap multiply-accumulate is realized in the LUT + carry fabric, not the UP5K's hard
DSP blocks (all eight `SB_MAC16` functional config bits decode to zero and carry no
operand routing). The `icebox_stat` "BRAMs: 2" print is an x,y tile-normalization artifact
for a single physical RAM40 — confirmed independently. Exact coefficients are in
`recovered/coeffs.json` (reproduced in the Phase 2 report).

**How the coefficients were recovered exactly:** the netlist is driven with the exact
RP2040 I2S waveform and self-calibrated against the **echo channel** (output-right must
equal the delayed input) — the unique alignment that holds for every frame also fixes the
filtered-channel decode. An impulse of `−32768` (exactly −1.0 in Q1.15) makes each active
product `h[k]·(−1)` exact, so the output is `−h[n]` directly; four more amplitudes confirm
linearity and the rounding mode. Three independent agents re-derived the filter
**adversarially** (each told to try to refute it); all agreed and none could refute the taps,
the DSP non-use, the single BRAM, or the frequency response.

---

## 2. The AI-agent pipeline

The work follows the CSAW 2025 **generate → insert → verify → retry** structure, reused and
extended for an iCE40 audio design. Each phase stops at a defined milestone with a
reproducible artifact, and a documentation agent (**Project Scribe**) records an
append-only, evidence-cited audit trail of commands, test outcomes, and Git state.

| Phase | What it does | Output |
|---|---|---|
| **1 — Init & research** | Toolchain inventory, challenge research, Scribe integration (no RTL) | `docs/phase1-initialization-report.md` |
| **2 — Reverse-engineering** | Unpack → netlist → simulate → recover coefficients → reconstruct clean RTL → multi-agent cross-verify | `docs/phase2-reverse-engineering-report.md`, `recovered/` |
| **3 — Golden reference** | Independent fixed-point model, HDL equivalence battery, frequency metrics, FPGA P&R sign-off, one-command regression | `docs/phase3-baseline-report.md`, `analysis/` |
| **4 — Infrastructure** | Reusable sim/synthesis harness (`infrastructure/run.py`): `validate` / `sim` / `build` / `regress` with JSON/Markdown/JUnit reports, source+bitstream hashing, VCD/FST capture | `handoffs/phase-04/` |
| **5 — Trojan fan-out** | Four candidates (A–D), developed **in parallel and in isolation**, each run through the harness until its exploit testbench passes and the no-trigger suite stays bit-exact | `experiments/phase05/` |
| **05S — Selection** | Independent re-test of all four from frozen `git archive` SHAs; adversarial, zero-tolerance comparison; provisional ranking | `handoffs/phase-05/selection.md` |
| **Quality cycle** | Fix the selected candidate's one boundary defect; re-run the full suite | `handoffs/quality-review/current-best.md` |
| **Bonus B** | Simulation-only bit-exact covert channel on the audio output | `handoffs/phase-05/bonus-b.md` |

The harness is the key piece of **system automation**: every candidate is validated by the
same runner against the same Phase 3 golden model with **zero tolerance and no implicit
alignment**, so results are directly comparable and each build's bitstream is hashed and
round-tripped (`icepack`/`iceunpack`) for reproducibility.

---

## 3. Simulations

Three layers of simulation back the results, all driven by the Phase 4 harness:

**Golden-reference equivalence (Phase 3).** Two independent software models, the gate-level
netlist from the original bitstream, and the reconstructed RTL were compared across impulse,
step, sinusoid, chirp, random, boundary, and real-audio inputs:

- HDL battery: **9,904 filtered-sample comparisons, 0 mismatches**, echo-channel match 100%,
  decoded latency 2 on every family.
- Software cross-check: 6 vector families + 12,000 random samples, **0 mismatches, max |err| 0**.
- Frequency metrics (independent scipy `freqz`/`group_delay`): DC 0.000 dB, −3 dB 3296.4 Hz,
  stopband −55.9 dB, group delay 31.000 samples, linear-phase residual ~8e−15.
- FPGA sign-off: reconstructed RTL maps to the UP5K (0 DSP / 0 BRAM), **Fmax ≈ 14.5 MHz,
  passes the 10 MHz board constraint**; bitstream-level identity to the stock image is
  explicitly *not* claimed (behavioral reconstruction), filtered-audio identity *is*.

**Per-candidate validation (Phase 5).** Each Trojan is checked for (a) **inactive
equivalence** — untriggered output bit-identical to the golden filter across directed,
random, near-miss, boundary, and real-audio vectors; (b) **activation** — the trigger fires
on its exact sequence and the payload behaves as specified; (c) **false-positive negatives**
— near-misses, split/interrupted sequences, and real music/speech do not fire; (d) **FPGA
build** — synthesis, P&R, timing, and pack/unpack round-trip.

**Independent re-test (Phase 05S).** All four candidates were re-exported from immutable
SHAs and re-run adversarially on identical baseline vectors (1 MHz and 625 kHz BCLK),
plus a direct-top resource/timing build under one shared PCF and seed.

---

## 4. The Trojans

Four independent candidates were generated, each a drop-in replacement for the recovered
63-tap FIR with a different trigger/payload philosophy. In every case the untriggered design
is bit-for-bit identical to the golden filter, the right-channel echo and 2-frame latency are
untouched, and the MAC datapath is left intact.

| ID (model) | Trigger | Payload | Idea |
|---|---|---|---|
| **05A — Luna** | 3 exact consecutive left samples `5A3C C3A5 96E1` | sticky `y ^ 0x0001` (one-bit LSB corruption) | smallest-footprint exact trigger |
| **05B — Astra** ⭐ | 8 exact consecutive left samples `7F00 8101 5A3C A5C3 6D92 926D C33C 3CC3` | sticky counter bypasses the FIR for **128 frames** (raw audio passes) | severe-but-bounded bypass, very specific trigger |
| **05C — Opus (architecture)** | 3-frame knock `C0DE FACE BEEF` on the **unused right I2S slot** | sticky 2:1 mux passes raw input (defeats the low-pass) | hide the trigger in a slot structurally orthogonal to the audio path |
| **05D — Opus (DSP)** | multiplier-free **Goertzel** detector for a tone at fs/3 = 5333 Hz (stopband) | spectral inversion `h′[k]=(−1)ᵏh[k]` turns the low-pass into a **high-pass** (~−60 dB passband) | frequency-domain trigger and payload |
| **Bonus B** (on 05B) | separate trigger | ROM transmitter emits `CSAW26-BONUS-B` on silent audio; host decoder recovers it from the output WAV only | bit-exact covert channel |

---

## 5. Results

**Comparable build (Phase 05S, direct `fir_audio_top` top, shared Hackster PCF, UP5K/SG48,
10 MHz target, nextpnr seed 1).** All builds use 0 DSP, 0 BRAM, 9 IO and pass 10 MHz P&R
and pack/unpack round-trip:

| Design | Logic cells / 5280 | Δ vs baseline | Fmax (MHz) |
|---|---:|---:|---:|
| Shared baseline | 3283 | — | 14.963 |
| 05A | 3336 | +53 (1.61%) | 15.214 |
| **05B** | **3313** | **+30 (0.91%)** | **15.485** |
| 05C | 3322 | +39 (1.19%) | 15.143 |
| 05D | 3652 | +369 (11.24%) | 15.183 |

**Selected candidate — 05B (Astra), provisional.** Chosen for the best verified combination
of a severe but bounded bypass, a very specific 8-word trigger, the smallest *measured*
hardware overhead, the strongest timing margin, and the widest normal-operation coverage.
05C is the backup; 05D and 05C contribute test ideas (spectral probes, right-slot near
misses). Its verified evidence:

- **Inactive equivalence:** 0 mismatches / 22,248 output words across 7 no-trigger cases.
- **Full-recording negative:** the complete 240,000-frame noisy WAV simulated in four
  reset-isolated overlapping chunks — **0 mismatches / 481,082 output words**, no spurious
  trigger.
- **Activation:** 4/4 trigger events (1 MHz and 625 kHz BCLK, including a double-activation
  stream), each producing exactly 128 raw pass-through frames; 0 pass-through mismatches.
- **Echo/startup:** 0 right-channel mismatches; first two output frames zero as expected.
- **Suite:** 10/10 candidate simulations + 15/15 framework unit tests + FPGA build pass;
  reproducible bitstream hash.

**Quality cycle.** Independent re-test found one defect: the trigger detector ignored the
first input sample immediately after a 128-frame bypass ended, so a back-to-back retrigger
on that exact sample was missed. The fix makes that first sample participate in matching;
directed boundary tests then improved to **30/30**, the full suite re-passed (46/46
simulations, full-audio 0/481,082), and the logic-cell count dropped to **3,240**. See
`handoffs/quality-review/current-best.md`.

**Bonus B (simulation only, potential 5/10).** The covert channel recovered its payload with
**0 bit errors (0/336 bits, three packets)** at both simulated rates; deliberate corruption
produces a failed CRC and truncation recovers nothing, confirming real source separation.
These are sample-clock simulation rates, not measured USB/board throughput.

---

## 6. Reproduction

Tools: OSS CAD Suite (`iverilog`, `yosys`, `nextpnr-ice40`, `icepack`/`iceunpack`,
`icetime`). The Phase 4 harness drives every stage. Example (05B validation + full-audio
negative), run from the repository root with the suite path set for your host:

```bash
# Phase 3 golden-reference regression (regenerates all analysis/ numbers)
python baseline/regression.py

# Validate the selected candidate against the golden model (zero tolerance)
python infrastructure/run.py --suite <OSS_CAD_SUITE> \
    validate --manifest experiments/phase05/05b-astra/manifest.json \
    --output experiments/phase05/05b-astra/reports/reproduction-run

# Full 240,000-frame noisy-WAV negative run (needs a longer timeout)
python experiments/phase05/05b-astra/tests/prepare_full_audio.py
python infrastructure/run.py --suite <OSS_CAD_SUITE> \
    sim --manifest experiments/phase05/05b-astra/tests/full_audio_manifest.json \
    --output experiments/phase05/05b-astra/reports/full-audio-run
```

The full, frozen-SHA re-test commands for all four candidates (PowerShell) are in
`handoffs/phase-05/selection.md`; per-candidate commands are in each
`experiments/phase05/05*/README.md`. Fresh input hashes, tool versions, statuses, and
bitstream hashes are written under each run's `fpga-build/` directory. Use a new `--output`
directory on each rerun.

---

## 7. Layout & provenance

- `docs/` — Phase 1–3 milestone reports (init, reverse-engineering, golden reference).
- `analysis/` — resource inventory, frequency response, reconstruction and FPGA-build verification, `freq_response.csv`, `icebox_stat.txt`, synth log.
- `baseline/` — the independent Phase 3 reference model and one-command regression.
- `experiments/phase05/05{a,b,c,d}-*/` — the four Trojan candidates, each with `rtl/`, `tests/`, `reports/` (executed sims, VCD, comparisons, synthesis/P&R/timing, hashes), `ai/`, and `manifest.json`.
- `handoffs/` — Phase 4 infrastructure status, Phase 05S selection + ranking, quality-review checkpoint, and Bonus B.
- `DocumentAgent/openclaw-project-scribe/` — Project Scribe, the local documentation agent that records coding-agent events and Git evidence and (when activated) synthesizes reports; see its own README for setup.
- `what_a_piece_of_work.wav`, `what_a_piece_of_work-noisy.wav` — challenge audio inputs used in the real-audio simulations.

All Trojan RTL, exploit logic, reference models, and analysis are AI-generated as the
competition requires; per-candidate interaction records are under each `ai/` directory.
Complete main-session transcript capture and a physical-board demonstration remain the two
outstanding items before this is a fully scored submission.
