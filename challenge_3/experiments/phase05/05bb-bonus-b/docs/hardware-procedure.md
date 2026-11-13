# Authorized board procedure (not a record of execution)

This procedure is pending until the competition Hackster is identified and the
experimental build passes. Nothing here is physical evidence. A simulator WAV,
successful place-and-route, or an enumerated serial port cannot substitute for
an actual board capture.

Record the board identity, operator, date/time, programmer and application serial
ports, bitstream SHA-256, bridge/script versions, nominal system clock, I2S rate,
and USB/host configuration. Use only the identified authorized Hackster. Preserve
all logs, failed attempts, and original files under a new hardware evidence run
directory. Never overwrite simulation evidence or golden references.

1. Load the supplied stock bitstream with the official programming script and
   confirm the right-echo link check using the official `stream_audio.py`.
2. Stream the official golden input through stock hardware. Save its left-output
   WAV and the complete host log. Compare with the official golden output.
3. Load the verified Phase 05BB experimental bitstream and repeat the same
   untriggered input. Require exact left-output agreement and a passing link
   check. An inactive baseline discrepancy blocks a full demonstration claim.
4. Generate the declared synthetic experiment stimulus with `tools/prepare.py`.
   Keep its original bits, protocol manifest, input WAV, and hashes. The input
   consists of silence and the activation sequence, not the payload waveform.
5. Run the official audio streaming script on the generated mono PCM16 input,
   selecting the recorded application port and supported I2S rate. Save the
   **filtered-left** output WAV as `captured-left.wav`; the right echo is only a
   transport control. Preserve the script log and any reported echo failures.
6. Independently decode `captured-left.wav`. Save reconstructed bits and decoder
   metadata before opening the original bit file for evaluation.
7. Evaluate original versus recovered bits. Retain the bit-by-bit CSV, count,
   errors, framing/CRC status, capture duration, and measured elapsed transfer
   duration. For hardware, report both sample-clock throughput and wall-clock
   throughput including host/USB chunking overhead and failed attempts. Document
   exactly where the wall-clock timer begins and ends.
8. Repeat with fresh captures at least three times; retain every attempt. Also
   run a nontriggered stimulus and decode the input/right echo as negative
   controls. Those controls must not produce the synthetic payload frame.
9. Restore the verified source candidate if required for subsequent board work.

The official [host audio path](https://github.com/JBlocklove/CSAW-AI-Hardware-Attack-Challenge-2026/blob/main/finals/challenge_3/README.md#streaming-audio-through-the-filter)
uses PC USB through the RP2040 bridge and I2S. The documented maximum BCLK is
1 MHz (31,250 stereo 16-bit frames/s), and the FPGA system clock is nominally
10 MHz. Preserve the exact stream settings; WAV metadata alone does not prove
the hardware clock or elapsed transfer rate.
The official script preserves the input WAV header rate even when `--rate`
changes the I2S transport rate. Require the generated input WAV rate to equal
the requested I2S rate, or explicitly correct the sample-clock calculations
using the actual effective rate. The simulation evidence uses matching rates.

From the experiment directory, host recovery and post-recovery evaluation use:

```powershell
& $python tools/decode.py captured-left.wav --output hardware-decoded
& $python tools/evaluate.py stimulus/original.bits hardware-decoded/decode.json --output hardware-evaluation --elapsed-seconds $measuredTransferSeconds
```

`$python` must identify a working Python interpreter and
`$measuredTransferSeconds` must come from the actual timed hardware transfer.
Use a new output directory each time. `decode.py` has no expected-message
argument; `evaluate.py` loads the original bits only after recovery. Failed
framing/count/alignment must remain visible and must not be scored as zero BER.

## Exact experimental programming and capture commands

These commands are **unexecuted instructions**. Run from the experiment directory
after the stock and inactive baseline steps above. Replace the port placeholders
with ports positively identified as the authorized board's programmer and
application processor; Bluetooth ports are not evidence of that board.

```powershell
$python = 'C:/Users/lowbr/oss-cad-suite/lib/python3.exe'
$programmerPort = 'IDENTIFIED_PROGRAMMER_COM_PORT'
$applicationPort = 'IDENTIFIED_APPLICATION_COM_PORT'
$hardwareRun = 'newhardware'
if (Test-Path -LiteralPath $hardwareRun) { throw 'Choose a fresh hardware evidence directory.' }
New-Item -ItemType Directory -Path $hardwareRun | Out-Null
& $python official/fpga/hackster-fpga-program.py w reports/baseline-build-run1/fpga-build/bitstream.bin $programmerPort 2>&1 | Tee-Object -FilePath "$hardwareRun/program.log"
$programExit = $LASTEXITCODE
@{exit_code=$programExit; programmer_port=$programmerPort; bitstream='reports/baseline-build-run1/fpga-build/bitstream.bin'} | ConvertTo-Json | Set-Content -LiteralPath "$hardwareRun/program.json"
if ($programExit -ne 0) { throw "Programming failed: $programExit" }
$transferTimer = [System.Diagnostics.Stopwatch]::StartNew()
& $python official/tools/stream_audio.py inputs/input.wav "$hardwareRun/captured-left.wav" --port $applicationPort --rate 31250 2>&1 | Tee-Object -FilePath "$hardwareRun/stream.log"
$streamExit = $LASTEXITCODE
$transferTimer.Stop()
$measuredTransferSeconds = $transferTimer.Elapsed.TotalSeconds
@{exit_code=$streamExit; elapsed_seconds=$measuredTransferSeconds; duration_basis='entire streaming subprocess including setup, USB transfer and flush'; application_port=$applicationPort; rate_hz=31250} | ConvertTo-Json | Set-Content -LiteralPath "$hardwareRun/transfer.json"
if ($streamExit -ne 0) { throw "Capture failed; preserve evidence: $streamExit" }
& $python tools/decode.py "$hardwareRun/captured-left.wav" --output "$hardwareRun/decoded"
& $python tools/evaluate.py inputs/original.bits "$hardwareRun/decoded/decode.json" --output "$hardwareRun/evaluation-wall-clock" --elapsed-seconds $measuredTransferSeconds
& $python tools/evaluate.py inputs/original.bits "$hardwareRun/decoded/decode.json" --output "$hardwareRun/evaluation-sample-clock"
```

Record the programming exit code even on failure, retain output hashes, and
inspect the host log for the echo-link result. The wall-clock timer deliberately
includes script setup, USB transfer, and flush; it is a conservative useful
throughput measurement alongside the sample-clock report. Keep failed and
repeated runs in separate directories and include every attempt in aggregate
throughput reporting.
