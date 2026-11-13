# Challenge 1 — Qualifying Trojan on the Hackster board

The finals challenge 1 is to carry the qualifying-round Trojan onto the physical
Hackster board and demonstrate it in hardware. This directory is the
Claude-agent pipeline for that Trojan, operating on the real recovered design.

## Target

`crypto_core` is the 32-bit byte-substitution cipher recovered from the
iCE40-UP5K bitstream: four independent key-dependent 8-bit lane bijections,
captured as the recovered S-box tables (`rtl/sbox_{enc,dec}{0..3}.mem`), 4 cycles
of `BUSY`, result read back over SPI MISO. The device key **`0x8E043CB1`** is
baked into those tables. `rtl/spi_crypto_top.v` is the SPI-peripheral wrapper
and passes a `TROJAN_EN` parameter down into the core.

## The Trojan

- **Trigger** — a two-block *knock* in encrypt mode: block N plaintext
  `0xDEADC0DE` arms, block N+1 plaintext `0xFEEDFACE` fires. Any other operand
  between them disarms; accidental-trigger probability ≈ 2⁻⁶⁴.
- **Payload** — precise key exfiltration: on the firing block the core
  parallel-loads the device key `0x8E043CB1` instead of the real ciphertext, so
  the next ordinary SPI read-out streams the key on MISO.
- **Stealth** — a two-bit FSM + two 32-bit equality checks + one 32-bit mux,
  the whole thing gated by `TROJAN_EN`, so a `TROJAN_EN=0` instance is provably
  identical to the clean core. No change to timing, `BUSY`, the port list, or
  any non-trigger output.

## Files

| Path | Role |
| --- | --- |
| `recovered_rtl/crypto_core.v` | CLEAN recovered cipher — the agent's starting point |
| `rtl/spi_crypto_top.v` | SPI wrapper that instantiates `crypto_core` with `TROJAN_EN` |
| `rtl/sbox_*.mem` | recovered key-dependent S-box tables (hold the device key) |
| `tb/tb_trojan.v` | exploit testbench: Trojaned twin vs clean twin |
| `ice40_cryptographic_IP.md` | provided SPI interface documentation |
| `solution/crypto_core_trojan.v` | known-good Trojan (used by `--replay`) |

## Verify (simulation)

```bash
python3 agent.py --clean     # clean recovered core: correct cipher, Trojan absent
python3 agent.py --replay    # shipped Trojan: TB_TROJAN: ALL PASS
python3 agent.py             # live: Claude inserts + verifies the Trojan (needs key)
python3 agent.py --area      # add a yosys iCE40 synthesis estimate
```

`verifier.py` compiles the candidate `crypto_core.v` with `rtl/spi_crypto_top.v`
and `tb/tb_trojan.v` under Icarus Verilog (copying the `.mem` tables next to the
simulation for `$readmemh`), then reads the testbench's verdict:

- `normal_ok` — reproduces the golden vector `0x59C359C3`→`0x9CD84392` and no
  stealth leak on normal traffic;
- `trigger_fires` — the knock leaked the device key on MISO (`[EXPLOIT-OK]`);
- success ⇔ the testbench's own `TB_TROJAN: ALL PASS`.

## Demonstrate on the Hackster board (finals requirement)

The simulation above is the fast inner loop; the finals are judged on hardware.
On a machine with the OSS CAD Suite and the board attached:

1. **Build** a bitstream from the converged `crypto_core.v` + `spi_crypto_top.v`
   (+ the `.mem` tables) for the iCE40-UP5K, using the `hackster.mk` flow from
   the `kiwih/hackster-programmer` project (`TROJAN_EN=1`).
2. **Program** the board: `make run_fpga FPGA_PORT=/dev/ttyACM0`.
3. **Normal check** — drive the documented ingest → `START` → readback sequence
   (the provided qualifier MicroPython test) and confirm
   `enc(0x59C359C3)=0x9CD84392` and that decrypt inverts encrypt.
4. **Exploit** — encrypt `0xDEADC0DE`, then encrypt `0xFEEDFACE`; the second
   read-back streams `0x8E043CB1`, the device key, on MISO. Capture the host
   session / logic-analyzer trace as the hardware evidence.

The leaked value **is** the device key, so this doubles as the key-recovery
result (`recovery/recover_key.py` in the submission recovers the same
`0x8E043CB1` from the netlist independently).
