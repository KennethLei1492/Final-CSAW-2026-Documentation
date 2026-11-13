# One-Prompt Replication Brief — Simulation

Give this entire file to a capable coding agent with the challenge folder as the
working directory. It reproduces the full task in **simulation + synthesis**:
reverse engineering → AI-model research → Trojan design → verification → a UP5K
bitstream that fits. The board version is `pipeline/REPLICATE_PROMPT_BOARD.md`
(a strict superset — identical to this file plus the on-board run steps).

The fastest path is the deterministic one-click script; the numbered method is
exactly what that script automates, written so an agent can also do each step by
hand.

---

## 0. Prerequisites (install once)

- **OS/shell:** Linux/macOS shell, or **Git Bash** on Windows (POSIX `bash`).
- **OSS CAD Suite** (yosys, nextpnr-ice40, iverilog, vvp, icepack, icebox_stat,
  icebox_vlog): <https://github.com/YosysHQ/oss-cad-suite-build/releases>.
  On Windows put **both** `bin` and `lib` on `PATH`:
  `export PATH="/c/oss-cad-suite/bin:/c/oss-cad-suite/lib:$PATH"`.
- **CPython ≥ 3.10** + `pip`.
- **Python packages:** `pip install pydantic "rank-bm25>=0.2.2"` (the AI models).
- **Git** + internet (first run only) to clone the AI-model repo.

> **Known environment pitfalls (handle up front):**
> - Windows: a bare `yosys` without `lib` on `PATH` exits 127 (missing DLLs).
> - Unpack bitstreams with `icepack -u` (not `iceunpack`) on Windows.
> - **`synth_ice40`'s default abc9 crashes** on this build (`write_xaiger2`
>   assert). Map LUTs with **classic abc** via the split flow in step 6 — do NOT
>   fall back to `-noabc` for the final numbers (its unoptimized counts are ~5×
>   too high and won't fit).
> - Do **not** run the AI models under `python -I` (isolated mode hides
>   site-packages such as pydantic). The self-contained helpers (`ascon_ref.py`,
>   `gen_*.py`, `insert_trojan.py`) may use `-I`.

## 1. One-click (does everything below, deterministically)

```bash
bash pipeline/run_all.sh
```

Override tools if needed: `OSS=~/oss-cad-suite PY=python3 bash pipeline/run_all.sh`.
`NO_BOARD=1` skips the place-and-route stage. The script preflights every tool,
auto-clones + installs the AI models on first run, runs all stages, and writes
`pipeline/RESULTS.md`. **Success = the file ends with `RESULT: ALL STAGES
PASSED.`**, the console shows clean 16 / A 22 / B 20 / C 18 self-test checks, and
stage 8 reports every board design (clean + A/B/C) **FITS** the UP5K.

## 2. Method, step by step (what the script automates)

Do these **in this order** — the methodology requires the bitstream to be
reverse-engineered *before* the EEPROM/Trojan research.

1. **Reverse-engineer the bitstream FIRST.**
   ```bash
   icepack -u fpga/crypto_eeprom_top.bin work/re/crypto.asc   # NOT iceunpack on Windows
   grep -m1 '^.device' work/re/crypto.asc                     # expect: .device 5k (iCE40-UP5K)
   icebox_stat work/re/crypto.asc                             # 4577 LUT / 954 DFF / 7 BRAM / 12 IOB / 0 PLL
   icebox_vlog work/re/crypto.asc > work/re/crypto_netlist.v  # recovered netlist
   ```
   Confirm all EBR init blocks are zero (**no key baked in**), that 12 IOBs are
   4 in / 6 out / 2 bidir (matches the SPI + I2C pinout), and cross-check counts
   against the UP5K datasheet (5280 LUT, 30 EBR). The recovered design is
   **EBR-backed (7 BRAM) at ~87% LUT** — the proof it fits, and the model your
   RTL must follow.

2. **Research with the prebuilt models (verifier-gated).** Clone + install:
   ```bash
   git clone --depth 1 https://github.com/KennethLei1492/prebuilt-ai-technique-models _external/ai-models
   python -m pip install pydantic "rank-bm25>=0.2.2"
   python work/research/run_research.py          # prints a VERIFIED/REVIEW verdict per claim
   ```
   The **Hybrid Retrieval** model indexes the five links + your RE facts; the
   **Answer Verification** model grounds every claim; **advance only on claims the
   verifier passes** (target: all 11 verified). Established facts: cipher =
   **Ascon-AEAD128** (IV `0x00001000808c0001`, pa=12/pb=8, 128-bit key/nonce/tag);
   the I2C key-load is passively sniffable; a key leak is both a confidentiality
   and an integrity break; nonce reuse breaks confidentiality but not (by itself)
   integrity. Write the AI workflow up in **`ai/METHODOLOGY.md`** (the six models;
   that the framework is AI-built; that the verifier settled each decision).

3. **Validate the Ascon reference + generate vectors + EEPROM image.**
   ```bash
   python work/sim/ascon_ref.py      # structural match to the official ref + 200 random roundtrips
   python work/sim/gen_vectors.py    # -> tb/vectors.vh (golden ct/tag + forgery vectors)
   python work/sim/gen_eeprom.py     # -> pipeline/eeprom_image.hex (CRC-16/CCITT-FALSE, 0xB9A1)
   ```

4. **Reconstruct the accelerator in synthesizable, UP5K-fitting RTL** (in `rtl/`):
   `ascon_engine.v` (datapath, 1 round/clock, fetches blocks over a
   `rd_req`/`rd_rdy` handshake), `crypto_top.v` (command/status + **EBR-backed**
   AD/MSG/OUT buffers — byte-wide AD/MSG read byte-serially, 128-bit OUT written
   whole / read per-byte), and the complete I2C master `i2c_eeprom_loader.v`.
   Verify:
   ```bash
   iverilog -g2012 -I tb -s tb_crypto -o /tmp/sc tb/tb_crypto.v rtl/ascon_engine.v rtl/crypto_top.v && vvp /tmp/sc
   ```
   Expect `ALL CHECKS PASSED (16 checks)`.

5. **Insert + simulate the three Trojans** — via the **insertion pass**, not
   `ifdef`:
   ```bash
   python tools/insert_trojan.py A B C     # -> work/trojans/crypto_top_{A,B,C}.v
   for T in A B C; do
     iverilog -g2012 -I tb -DDEMO_$T -s tb_crypto -o /tmp/s$T tb/tb_crypto.v rtl/ascon_engine.v work/trojans/crypto_top_$T.v && vvp /tmp/s$T
   done
   ```
   - **A** (host nonce `A5…A5`, encrypt): leaks key‖IV‖secret on the OUT **read**
     path + an accepted forgery → C:H + I:H (22 checks).
   - **B** (reserved `CFG[7]`, decrypt): auth bypass + correct-plaintext release
     from `crypto_top` → C:H + I:H (20 checks).
   - **C** (MSG prefix `C0FFEE00` snooped from the write stream, encrypt): forced
     nonce reuse + plaintext recovery → C:H (18 checks).
   (`-DDEMO_*` only selects which demo the testbench runs; the Trojan itself comes
   from the inserted RTL. The clean `rtl/crypto_top.v` has no Trojan logic.)

6. **Validate the I2C loader end-to-end** (real master ↔ EEPROM model, no backdoor):
   ```bash
   iverilog -g2012 -s tb_loader -o /tmp/sl tb/tb_loader.v rtl/i2c_eeprom_loader.v rtl/i2c_eeprom_model.v && vvp /tmp/sl
   ```
   Expect `LOADER PASS` (64 bytes clocked over SDA/SCL, magic/version/CRC checked,
   key/nonce/secret latched).

7. **Synthesize for the UP5K + report Trojan overhead** — use **classic abc**
   (abc9 crashes). The split flow that gives real, optimized counts:
   ```bash
   yosys -p "read_verilog -sv rtl/ascon_engine.v rtl/crypto_top.v; \
     synth_ice40 -top crypto_top -run :map_luts; ice40_wrapcarry -unwrap; \
     abc -lut 4; clean; techmap -map +/ice40/cells_map.v; clean; \
     synth_ice40 -top crypto_top -run map_cells:; stat"
   ```
   The core is ~3.7k LUT4 / **10 EBR** and the Trojan deltas are small.

8. **Place & route to a bitstream that FITS** (the deliverable that resolves the
   old 39.8k-LUT problem). For `crypto_board_top` (clean and each Trojan):
   ```bash
   yosys -p "read_verilog -sv rtl/crypto_board_top.v rtl/spi_peripheral.v rtl/i2c_eeprom_loader.v rtl/crypto_top.v rtl/ascon_engine.v; \
     synth_ice40 -top crypto_board_top -run :map_luts; ice40_wrapcarry -unwrap; abc -lut 4; clean; \
     techmap -map +/ice40/cells_map.v; clean; synth_ice40 -top crypto_board_top -run map_cells:; write_json work/board/clean.json"
   nextpnr-ice40 --up5k --package sg48 --json work/board/clean.json --pcf rtl/crypto_board_top.pcf --asc work/board/clean.asc --freq 10
   icepack work/board/clean.asc work/board/clean.bin
   ```
   Expect `ICESTORM_LC: ~4958/5280 (≈93%)`, `ICESTORM_RAM: 10/30`, timing PASS at
   10 MHz, and a packed `.bin`. All four designs (clean + A/B/C) fit.

## 3. Deliverables to expect

`rtl/` (engine, top, complete I2C master, EEPROM sim model, board top + PCF),
`tools/insert_trojan.py` (the insertion pass), `tb/` (self-test + golden-vector +
Trojan demos, real-I2C loader test, SPI test), `work/research/` (verified
transcript) + **`ai/METHODOLOGY.md`**, `work/analysis/cvss.py`,
`work/trojans/crypto_top_{A,B,C}.v` (generated), `work/board/*.bin` (fitting
bitstreams), `README.md`, `docs/documentation.html`, `pipeline/RESULTS.md`.
