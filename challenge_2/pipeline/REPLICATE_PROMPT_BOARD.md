# One-Prompt Replication Brief — Simulation **and** Board (iCE40-UP5K)

Give this entire file to a capable coding agent with the challenge folder as the
working directory. **It is a superset of `pipeline/REPLICATE_PROMPT.md`:** it
contains the full simulation brief (sections 0–3) *and* adds the hardware steps
to build, program, and drive the Trojans on the board (sections 4–5).

**Target board:** Lattice iCE40 UltraPlus **UP5K**, 48-pin QFN (**sg48**), on the
Hackster — <https://www.latticesemi.com/en/products/fpgaandcpld/ice40ultraplus>.
Official challenge reference (verify required steps here):
<https://github.com/JBlocklove/CSAW-AI-Hardware-Attack-Challenge-2026/tree/main/finals/challenge_2>.

---

## 0. Prerequisites (install once)

- **OS/shell:** Linux/macOS shell, or **Git Bash** on Windows (POSIX `bash`).
- **OSS CAD Suite** (yosys, nextpnr-ice40, iverilog, vvp, icepack, iceunpack,
  icebox_stat, icebox_vlog): <https://github.com/YosysHQ/oss-cad-suite-build/releases>.
  On Windows put both `bin` and `lib` on `PATH`:
  `export PATH="/c/oss-cad-suite/bin:/c/oss-cad-suite/lib:$PATH"`.
- **CPython ≥ 3.10** + `pip`.
- **Python packages:** `pip install pydantic "rank-bm25>=0.2.2"` (AI models) and
  **for the board:** `pip install mpremote pyserial` (per the challenge
  `tools/requirements.txt`).
- **Git** + internet (first run) to clone the AI-model repo.

> **Known environment pitfalls:**
> - Windows: a bare `yosys` without `lib` on `PATH` exits 127 (missing DLLs).
> - Use `icepack -u` (not `iceunpack`) to unpack on Windows.
> - `yosys synth_ice40` default abc9 **crashes** on some Windows builds
>   (`write_xaiger2` assert); use `synth_ice40 -noabc`.
> - Do **not** run the AI models with `python -I` (it hides site-packages).

## 1. One-click — board flow (does everything in this brief)

```bash
FPGA_PORT=/dev/ttyACM0 APP_PORT=/dev/ttyACM1 bash pipeline/run_all_board.sh
```

- `FPGA_PORT` = programmer port (loads bitstreams); `APP_PORT` = RP2040
  application-processor port. On macOS use `/dev/cu.usbmodem…`; on Windows `COMx`.
  Plug the programmer in first so it enumerates as the lower port.
- With **no** ports set it still runs simulation + build and auto-skips the
  hardware stages. Override tools with `OSS=…`, `PY=…`, `NEXTPNR=…`, `MPREMOTE=…`.
- It calls `pipeline/run_all.sh` **unmodified** for all simulation verification,
  then for the clean design and each Trojan **in turn** builds a UP5K bitstream
  and (if a board is attached) programs it, runs the self-test, and fires the
  exploit. Output → `pipeline/BOARD_RESULTS.md`.

## 2. Method — simulation (identical to the sim-only brief)

Do these in order; reverse-engineer the bitstream **before** the EEPROM/Trojan
research.

1. **RE first:** `icepack -u fpga/crypto_eeprom_top.bin work/re/crypto.asc`;
   `grep -m1 '^.device' work/re/crypto.asc` → `.device 5k`; `icebox_stat` →
   4577 LUT / 954 DFF / 7 BRAM / 12 IOB / 0 PLL; `icebox_vlog` → netlist. Confirm
   all EBR init zero (no key baked in), 12 IOB = 4 in / 6 out / 2 bidir, and
   cross-check vs the UP5K datasheet.
2. **Research with the models:**
   `git clone --depth 1 https://github.com/KennethLei1492/prebuilt-ai-technique-models _external/ai-models`;
   `pip install pydantic "rank-bm25>=0.2.2"`; run `work/research/run_research.py`
   (Hybrid Retrieval indexes the 5 links + RE facts; Answer Verification gates
   every claim). Cipher = **Ascon-AEAD128**; key leak ⇒ C:H+I:H; nonce reuse ⇒
   C only.
3. **Reference + vectors:** `python work/sim/ascon_ref.py`;
   `python work/sim/gen_vectors.py` → `tb/vectors.vh`;
   `python work/sim/gen_eeprom.py` → `pipeline/eeprom_image.hex`.
4. **Verify the clean RTL:**
   `iverilog -g2012 -I tb -s tb_crypto -o /tmp/s tb/tb_crypto.v rtl/ascon_engine.v rtl/crypto_top.v && vvp /tmp/s`
   → `ALL CHECKS PASSED (16 checks)`; loader: `tb/tb_loader.v` → `LOADER PASS`.
5. **Three Trojans** (`-DTROJAN_A|B|C`): A leaks key‖IV‖secret + accepted forgery
   (22 checks, C:H+I:H); B reserved-bit auth bypass + plaintext recovery (20, C:H+I:H);
   C forced nonce reuse + plaintext recovery (18, C:H).
6. **Synthesize:** `yosys -p "read_verilog -sv <-DTROJAN_x> rtl/ascon_engine.v rtl/crypto_top.v; synth_ice40 -noabc -top crypto_top; stat"`; use the delta vs clean (A +427, B +44, C +11 SB_LUT4).
7. **CVSS:** `python work/analysis/cvss.py` (AV:L, S:C for the isolation breach,
   impact only where demonstrated): A 9.0, B 9.0, C 7.1; floors 6.1/6.1/4.6.
   Never claim `AV:N`.

## 3. Deliverables (simulation)

`rtl/`, `tb/`, `work/research/` (verified transcript), `work/analysis/cvss.py`,
`README.md`, `docs/documentation.html`, `pipeline/RESULTS.md`.

---

## 4. Method — board build, program, and drive (the added part)

The board top is `rtl/crypto_board_top.v` (real pins → `spi_peripheral.v` +
`i2c_eeprom_loader.v` + `crypto_top.v`), with pin constraints
`rtl/crypto_board_top.pcf`. The build mirrors the official `hackster.mk` flow
(yosys → nextpnr → icepack); see the challenge README and
<https://github.com/kiwih/hackster-programmer>.

For the clean design and then each Trojan `x ∈ {A,B,C}`, one after another:

1. **Synthesize** (`-noabc` to avoid the abc9 crash):
   ```bash
   yosys -p "read_verilog -sv -DTROJAN_x rtl/crypto_board_top.v rtl/spi_peripheral.v \
     rtl/i2c_eeprom_loader.v rtl/crypto_top.v rtl/ascon_engine.v; \
     synth_ice40 -noabc -top crypto_board_top -json build_x.json"
   ```
2. **Place & route** for the UP5K/sg48 at the ~10 MHz ICE_CLK:
   ```bash
   nextpnr-ice40 --up5k --package sg48 --json build_x.json --pcf rtl/crypto_board_top.pcf \
     --asc build_x.asc --freq 10
   icepack build_x.asc build_x.bin
   ```
3. **Program the board** (the Hackster programmer; `FPGA_PORT` = programmer port):
   ```bash
   python fpga/hackster-fpga-program.py w build_x.bin "$FPGA_PORT"
   ```
   (Equivalently `cd fpga && make run_fpga FPGA_PORT=…` for the provided bitstream.)
   The RGB LED turns green when keys load (red = error). The EEPROM is
   **already provisioned by the organizers — do not and cannot provision it.**
4. **Prove normal operation** (run the challenge self-test over `APP_PORT`):
   ```bash
   mpremote connect "$APP_PORT" run tools/fpga_selftest.py          # expect: All checks passed.
   ```
5. **Fire the Trojan** (on-board MicroPython driver; `mount` lets it import the
   shared helper):
   ```bash
   mpremote connect "$APP_PORT" mount pipeline/board run pipeline/board/exploit_trojan_a.py  # A
   mpremote connect "$APP_PORT" mount pipeline/board run pipeline/board/exploit_trojan_b.py  # B
   mpremote connect "$APP_PORT" mount pipeline/board run pipeline/board/exploit_trojan_c.py  # C
   ```
   Capture the serial output as evidence (A prints the recovered key/IV/secret;
   B shows a forged-tag decrypt accepted with the correct plaintext; C recovers a
   second plaintext under reused nonce). Only one tool may hold the app port at a
   time — close Thonny before `mpremote`, and vice-versa.

Run `tools/fpga_selftest.py` on the **provided** bitstream first (sanity), then on
each built design, per the challenge README.

## 5. Honest hardware preconditions (the script reports these, never fakes them)

- **P1 — a provisioned board attached**, with `FPGA_PORT` and `APP_PORT` set.
  Without them the program/drive stages are skipped.
- **P2 — the design must fit the UP5K.** As written, `crypto_top`'s AD/MSG/OUT
  buffers are register files (the engine does wide combinational block reads), so
  `crypto_board_top` is ~38k LUT4 / needs ~47k logic cells and **will not place**
  on the 5280-LC UP5K; `nextpnr` reports this and the script logs it. **Fix:**
  refactor those three buffers to **EBR** (single-port, synchronous reads — as the
  recovered production bitstream does: 4577 LUT / 7 BRAM). This is the one real
  RTL change needed before a bitstream exists.
- **P3 — complete the I2C burst read.** `rtl/i2c_eeprom_loader.v` has correct,
  tb-verified magic/version/CRC-16 validation and key latching, but its bit-level
  EEPROM read is abstracted; add a standard I2C master so `KEYS_LOADED` asserts
  from the real EEPROM at power-up.

Everything else (synthesis, the SPI integration layer — verified by `tb/tb_spi.v`,
the exploit drivers, programming, and the orchestration) is complete and, where a
board is absent, verified in simulation.
