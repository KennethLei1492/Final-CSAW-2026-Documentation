# Hardware evidence report (findings §35–40; hardware part of §48)

**Category:** Hardware Exploitation Demonstration — 10 points (and the gating
*baseline check* that underwrites Trojan Quality).
**Verdict:** All of §35–40 are `BLOCKED`. **No Hackster board is present** in the
device inventory (confirmed in Phase 6 and Phase 8: *"Current device inventory
found no matching board"*). Per the Phase F mandate and basic integrity, **no
photos, traces, audio captures, LED/scope traces, or power measurements are
fabricated.** This report records the precise blocker and provides an
**executable** procedure so the evidence can be captured the moment a board is
available.

## Simulation-verified vs hardware-verified (keep distinct)
| Claim | Simulation | Hardware |
| --- | :---: | :---: |
| Baseline bit-identity (untriggered) | ✅ 481,082 words, 0 mismatch | ⛔ pending (§39, §48) |
| Trigger fires / 128-frame bypass | ✅ 4/4 activations, exactly 128 frames | ⛔ pending (§36, §37) |
| Covert channel (05BB) recovery | ✅ BER 0/336 | ⛔ pending |
| Board photos / scope / LED / power | — | ⛔ pending (§35, §36, §38, §40) |

## Blocker
- **Resource unavailable:** physical iCE40-UP5K Hackster board + USB host link.
- **Instruments unavailable/unconfirmed:** oscilloscope / logic analyzer (§36, §38),
  power-capture rig (§40). Collect those traces only if the instruments are
  actually on hand.
- No partial fabrication: a "mock" photo or synthesized trace would violate the
  challenge and is out of the question.

## Executable capture procedure (run when a board is connected)
Prereqs: Hackster on USB (programmer `/dev/ttyACM0` or `COMx`; app processor
`/dev/ttyACM1`), the submission bitstream, and the provided host tools (preserved
in Phase 8 `official/`). The trigger stimulus already exists and is verified:
`audit-remediation/evidence/triggered_stream.wav` (from
`scripts/make_trigger_wav.py`).

1. **Program the Trojaned bitstream** → unblocks §35 (photograph the board + LEDs).
   ```
   cd fpga && make run_fpga OUTPUTNAME_ROOT=../path/to/trojan_top    # or hackster-fpga-program.py
   ```
2. **Link self-test** (§26, §39 precondition):
   ```
   python3 stream_audio.py --self-test --port /dev/ttyACM1
   ```
3. **Baseline check on hardware** (§39, closes §48 residual) — must be bit-identical:
   ```
   python3 stream_audio.py ../audio/noisy_test_audio.wav filtered.wav --port /dev/ttyACM1
   cmp filtered.wav ../audio/filtered_test_audio.wav && echo IDENTICAL   # Windows: fc /b
   ```
4. **Trigger demonstration** (§37) — stream the verified trigger WAV, capture output:
   ```
   python3 stream_audio.py triggered_stream.wav triggered_out.wav --port /dev/ttyACM1
   ```
   Expected: left output = raw input (bypass) for 128 frames starting at the 8th
   magic sample; outside the window, left = filtered. Save `triggered_out.wav`
   plus the input for the before/after pair and a spectrogram.
5. **ICE_LED / scope-trigger SMA** (§38) + **I2S lines** (§36): the `ICE_LED` is
   high while the MAC computes and is routed to the scope-trigger SMA; capture
   `BCLK`/`WS`/`SD_IN`/`SD_OUT` during a trigger event. (Only if a scope/LA is present.)
6. **Power trace** (§40, optional debug aid):
   ```
   cd fpga && make run_fpga_power      # writes power_data.txt
   ```
7. **Preserve** every artifact (photos, WAV pair, traces, host logs) under a new
   `hardware-evidence/` with a capture manifest (device id, programmed bitstream
   SHA-256, host versions, timestamps) and hand to Project Scribe `record-test`.

## Scoring unlock if executed
- Steps 3–4 with clear evidence → Category 5 moves from **0** toward **6–10**
  (Proficient→Exemplary), and converts Bonus A/B sim tiers (5) toward board tiers
  (10). Step 3 also closes the §48 real-silicon residual.
- Until then Category 5 is realistically **0** and must be reported as such.
