# One-Prompt Replication Brief — Simulation **and** Board (iCE40-UP5K)

Give this entire file to a capable coding agent with the challenge folder as the
working directory. **It is a strict superset of `pipeline/REPLICATE_PROMPT.md`:**
sections 0–3 are the complete simulation + synthesis brief (identical in intent to
the sim-only file), and sections 4–5 add building, programming, and driving the
Trojans on real hardware.

**Target board:** Lattice iCE40 UltraPlus **UP5K**, 48-pin QFN (**sg48**), on the
Hackster — <https://www.latticesemi.com/en/products/fpgaandcpld/ice40ultraplus>.
Official challenge reference (verify required steps here):
<https://github.com/JBlocklove/CSAW-AI-Hardware-Attack-Challenge-2026/tree/main/finals/challenge_2>.

---

## 0. Prerequisites (install once)

- **OS/shell:** Linux/macOS shell, or **Git Bash** on Windows (POSIX `bash`).
- **OSS CAD Suite** (yosys, nextpnr-ice40, iverilog, vvp, icepack, icebox_stat,
  icebox_vlog): <https://github.com/YosysHQ/oss-cad-suite-build/releases>.
  On Windows put **both** `bin` and `lib` on `PATH`:
  `export PATH="/c/oss-cad-suite/bin:/c/oss-cad-suite/lib:$PATH"`.
- **CPython ≥ 3.10** + `pip`.
- **Python packages:** `pip install pydantic "rank-bm25>=0.2.2"` (AI models) and,
  **for the board:** `pip install mpremote pyserial` (per `tools/requirements.txt`).
- **Git** + internet (first run only) to clone the AI-model repo.

> **Known environment pitfalls:**
> - Windows: a bare `yosys` without `lib` on `PATH` exits 127 (missing DLLs).
> - Unpack with `icepack -u` (not `iceunpack`) on Windows.
> - **`synth_ice40`'s default abc9 crashes** on this build (`write_xaiger2`
>   assert). Map LUTs with **classic abc** via the split flow in step 6 — not
>   `-noabc` (its unoptimized counts are ~5× too high and won't fit).
> - Do **not** run the AI models under `python -I`. Self-contained helpers
>   (`ascon_ref.py`, `gen_*.py`, `insert_trojan.py`) may use `-I`.

## 1. One-click — board flow (does everything in this brief)

```bash
FPGA_PORT=/dev/ttyACM0 APP_PORT=/dev/ttyACM1 bash pipeline/run_all_board.sh
```

- `FPGA_PORT` = programmer port (loads bitstreams); `APP_PORT` = RP2040
  application-processor port. macOS: `/dev/cu.usbmodem…`; Windows: `COMx`. Plug the
  programmer in first so it enumerates as the lower port.
- With **no** ports set it still runs the full simulation + synthesis + UP5K
  place-and-route (producing the bitstreams) and auto-skips only the
  program/drive stages. Override tools with `OSS=…`, `PY=…`, `MPREMOTE=…`.
- It calls `pipeline/run_all.sh` **unmodified** (which now also builds the fitting
  bitstreams `work/board/{clean,trojanA,trojanB,trojanC}.bin`), checks the SPI
  layer, then for the clean design and each Trojan **in turn** programs the board,
  runs the self-test, and fires the exploit. Output → `pipeline/BOARD_RESULTS.md`.

## 2. Method — simulation + synthesis (identical to the sim-only brief)

Do these in order; reverse-engineer the bitstream **before** the EEPROM/Trojan
research.

1. **RE first:** `icepack -u fpga/crypto_eeprom_top.bin work/re/crypto.asc`;
   `grep -m1 '^.device' work/re/crypto.asc` → `.device 5k`; `icebox_stat` →
   4577 LUT / 954 DFF / 7 BRAM / 12 IOB / 0 PLL; `icebox_vlog` → netlist. Confirm
   all EBR init zero (no baked key), 12 IOB = 4 in / 6 out / 2 bidir, cross-check
   vs the UP5K datasheet (5280 LUT / 30 EBR). The recovered design is EBR-backed
   (**7 BRAM, ~87% LUT**) — the model your RTL must follow.
2. **Research with the models (verifier-gated):**
   `git clone --depth 1 https://github.com/KennethLei1492/prebuilt-ai-technique-models _external/ai-models`;
   `pip install pydantic "rank-bm25>=0.2.2"`; `python work/research/run_research.py`
   (Hybrid Retrieval indexes the 5 links + RE facts; Answer Verification gates
   every claim — advance only on passed claims, target 11/11). Cipher =
   **Ascon-AEAD128**; key leak ⇒ C:H+I:H; nonce reuse ⇒ C only. Write the workflow
   up in **`ai/METHODOLOGY.md`** (six models; AI-built; verifier-settled).
3. **Reference + vectors:** `python work/sim/ascon_ref.py`;
   `python work/sim/gen_vectors.py` → `tb/vectors.vh`;
   `python work/sim/gen_eeprom.py` → `pipeline/eeprom_image.hex` (CRC 0xB9A1).
4. **Clean RTL (UP5K-fitting):** EBR-backed buffers in `crypto_top.v`, block-fetch
   handshake in `ascon_engine.v`, complete I2C master in `i2c_eeprom_loader.v`.
   `iverilog -g2012 -I tb -s tb_crypto -o /tmp/sc tb/tb_crypto.v rtl/ascon_engine.v rtl/crypto_top.v && vvp /tmp/sc`
   → `ALL CHECKS PASSED (16 checks)`.
5. **Three Trojans via the insertion pass** (not `ifdef`):
   `python tools/insert_trojan.py A B C`; then for `T∈{A,B,C}`:
   `iverilog -g2012 -I tb -DDEMO_$T -s tb_crypto -o /tmp/s$T tb/tb_crypto.v rtl/ascon_engine.v work/trojans/crypto_top_$T.v && vvp /tmp/s$T`.
   A leaks key‖IV‖secret on the OUT read path + forgery (22, C:H+I:H); B reserved-bit
   auth bypass + plaintext release (20, C:H+I:H); C snooped-prefix forced nonce
   reuse (18, C:H).
6. **Loader end-to-end** (real master ↔ EEPROM model):
   `iverilog -g2012 -s tb_loader -o /tmp/sl tb/tb_loader.v rtl/i2c_eeprom_loader.v rtl/i2c_eeprom_model.v && vvp /tmp/sl` → `LOADER PASS`.
7. **Synthesis (classic abc; abc9 crashes):**
   `yosys -p "read_verilog -sv rtl/ascon_engine.v rtl/crypto_top.v; synth_ice40 -top crypto_top -run :map_luts; ice40_wrapcarry -unwrap; abc -lut 4; clean; techmap -map +/ice40/cells_map.v; clean; synth_ice40 -top crypto_top -run map_cells:; stat"`
   → ~3.7k LUT4 / 10 EBR.
8. **CVSS:** `python work/analysis/cvss.py` (AV:L, S:C, impact only where
   demonstrated): A 9.0, B 9.0, C 7.1; floors 6.1/6.1/4.6. Never claim `AV:N`.

## 3. Deliverables (simulation + synthesis)

`rtl/`, `tools/insert_trojan.py`, `tb/`, `work/research/` + `ai/METHODOLOGY.md`,
`work/analysis/cvss.py`, `work/trojans/crypto_top_{A,B,C}.v`, `work/board/*.bin`,
`README.md`, `docs/documentation.html`, `pipeline/RESULTS.md`.

---

## 4. Method — board build, program, and drive (the added part)

The board top is `rtl/crypto_board_top.v` (real pins → `spi_peripheral.v` +
`i2c_eeprom_loader.v` + `crypto_top.v`), constraints `rtl/crypto_board_top.pcf`.
The build mirrors the official `hackster.mk` flow (yosys → nextpnr → icepack); see
the challenge README and <https://github.com/kiwih/hackster-programmer>.

For the clean design and then each Trojan `x ∈ {A,B,C}` (`crypto_top_x.v` from the
insertion pass), one after another:

1. **Synthesize + place & route to a bitstream that FITS** (classic abc; UP5K/sg48,
   10 MHz ICE_CLK):
   ```bash
   SRC=rtl/crypto_top.v    # or work/trojans/crypto_top_A.v, _B.v, _C.v
   yosys -p "read_verilog -sv rtl/crypto_board_top.v rtl/spi_peripheral.v rtl/i2c_eeprom_loader.v $SRC rtl/ascon_engine.v; \
     synth_ice40 -top crypto_board_top -run :map_luts; ice40_wrapcarry -unwrap; abc -lut 4; clean; \
     techmap -map +/ice40/cells_map.v; clean; synth_ice40 -top crypto_board_top -run map_cells:; write_json build.json"
   nextpnr-ice40 --up5k --package sg48 --json build.json --pcf rtl/crypto_board_top.pcf --asc build.asc --freq 10
   icepack build.asc build.bin
   ```
   Expect `ICESTORM_LC ≈ 4958/5280 (≈93%)`, `ICESTORM_RAM 10/30`, timing PASS.
2. **Program the board** (`FPGA_PORT` = programmer port):
   ```bash
   python fpga/hackster-fpga-program.py w build.bin "$FPGA_PORT"
   ```
   (Equivalently `cd fpga && make run_fpga FPGA_PORT=…` for the provided bitstream.)
   The RGB LED turns green when keys load (red = error). The EEPROM is **already
   provisioned by the organizers — do not and cannot provision it.**
3. **Prove normal operation** (challenge self-test over `APP_PORT`):
   ```bash
   mpremote connect "$APP_PORT" run tools/fpga_selftest.py        # expect: All checks passed.
   ```
4. **Fire the Trojan** (on-board MicroPython driver; `mount` lets it import the
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

## 5. Notes

- **The design fits.** `crypto_top` uses EBR-backed buffers (byte-wide AD/MSG read
  byte-serially; 128-bit OUT written whole / read per byte), so `crypto_board_top`
  places at ~93% LC / 10 of 30 EBR on the UP5K — matching the recovered
  production design's EBR usage. There is no longer a "won't fit" precondition.
- **The I2C loader is complete.** `i2c_eeprom_loader.v` is a full open-drain master
  (verified end-to-end in `tb/tb_loader.v` against `rtl/i2c_eeprom_model.v`), so
  `KEYS_LOADED` asserts from the real EEPROM at power-up. There is no longer a
  "burst read abstracted" precondition.
- **Only runtime requirement:** a provisioned Hackster board attached with
  `FPGA_PORT`/`APP_PORT` set. Without it, everything up to the bitstreams still
  builds and verifies; the program/drive stages simply report they were skipped.
