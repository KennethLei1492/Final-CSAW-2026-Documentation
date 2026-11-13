# One-Prompt Replication Brief — Simulation

Give this entire file to a capable coding agent with the challenge folder as the
working directory. It reproduces the full task in **simulation** (reverse
engineering → AI-model research → Trojan design → verification). The board
version of this brief is `pipeline/REPLICATE_PROMPT_BOARD.md` (a superset).

The fastest path is the deterministic one-click script; the numbered method
below is what that script automates, written out so an agent can also do (or
debug) each step by hand.

---

## 0. Prerequisites (install once)

- **OS/shell:** Linux/macOS shell, or **Git Bash** on Windows (POSIX `bash`).
- **OSS CAD Suite** (yosys, nextpnr-ice40, iverilog, vvp, icepack, iceunpack,
  icebox_stat, icebox_vlog): download a release from
  <https://github.com/YosysHQ/oss-cad-suite-build/releases> and note its path.
  On Windows the tools are `*.exe` and need `bin` **and** `lib` on `PATH`:
  `export PATH="/c/oss-cad-suite/bin:/c/oss-cad-suite/lib:$PATH"`.
- **CPython ≥ 3.10** with `pip`.
- **Python packages:** `pip install pydantic "rank-bm25>=0.2.2"` (for the AI
  models) and, only for the board brief, `pip install mpremote pyserial`.
- **Git** + internet (first run) to clone the AI-model repo.

> **Known environment pitfalls (handle these up front):**
> - On Windows, invoke yosys/iverilog by name only after `bin` and `lib` are on
>   `PATH`; a bare `yosys` without `lib` exits 127 (missing DLLs).
> - `iceunpack` may error on some Windows builds; use `icepack -u` instead.
> - `yosys synth_ice40`'s default abc9 step **crashes** on some Windows builds
>   (assert in the experimental `write_xaiger2` backend). Use `synth_ice40 -noabc`
>   for deterministic resource counts; it avoids abc9 entirely.
> - Do **not** run the AI models with `python -I` (isolated mode hides installed
>   site-packages such as pydantic). Run them with a normal interpreter.

## 1. One-click (does everything below, deterministically)

```bash
bash pipeline/run_all.sh
```

Override tool locations if needed, e.g. `OSS=~/oss-cad-suite PY=python3 bash
pipeline/run_all.sh`. The script preflights every tool, auto-clones + installs
the AI models on first run, runs all stages, and writes `pipeline/RESULTS.md`.
**Success = the file ends with `RESULT: ALL STAGES PASSED.`** and the console
shows clean 16 / A 22 / B 20 / C 18 self-test checks.

## 2. Method, step by step (what the script automates)

Do these **in this order** — the methodology requires the bitstream to be
reverse-engineered *before* the EEPROM/Trojan research.

1. **Reverse-engineer the bitstream FIRST.** From the repo root:
   ```bash
   icepack -u fpga/crypto_eeprom_top.bin work/re/crypto.asc   # NOT iceunpack on Windows
   grep -m1 '^.device' work/re/crypto.asc                     # expect: .device 5k  (iCE40-UP5K)
   icebox_stat work/re/crypto.asc                             # 4577 LUT / 954 DFF / 7 BRAM / 12 IOB / 0 PLL
   icebox_vlog work/re/crypto.asc > work/re/crypto_netlist.v  # recovered netlist
   ```
   Confirm all 30 EBR init blocks are zero (**no key baked in**), that the 12
   IOBs decompose as 4 in / 6 out / 2 bidir (matches the documented SPI + I2C
   pinout), and cross-check the counts against the Lattice UP5K datasheet
   (5280 LUT, 30 EBR, 8 DSP, 1 PLL). Conclude: a 320-bit-permutation AEAD core.

2. **Research with the prebuilt models.** Clone + install:
   ```bash
   git clone --depth 1 https://github.com/KennethLei1492/prebuilt-ai-technique-models _external/ai-models
   python -m pip install pydantic "rank-bm25>=0.2.2"
   ```
   Build a corpus (`work/research/corpus.json`) from the five reference links and
   your own RE measurements, then run `work/research/run_research.py`: it indexes
   the corpus with the **Hybrid Retrieval** model and gates **every** analytical
   claim with the **Answer Verification** model. Proceed only on claims the
   verifier passes (target: all verified). Established facts: cipher =
   **Ascon-AEAD128** (IV `0x00001000808c0001`, pa=12/pb=8, 128-bit key/nonce/tag);
   the I2C key-load path is passively sniffable; a key leak is both a
   confidentiality and an integrity compromise; nonce reuse breaks confidentiality
   but not (by itself) integrity.

3. **Validate the Ascon reference + generate vectors.**
   ```bash
   python work/sim/ascon_ref.py      # structural match to the official ref + 200 random roundtrips
   python work/sim/gen_vectors.py    # -> tb/vectors.vh (golden ct/tag + forgery vectors)
   python work/sim/gen_eeprom.py     # -> pipeline/eeprom_image.hex (CRC-16/CCITT-FALSE)
   ```

4. **Reconstruct the accelerator in synthesizable Verilog** (already in `rtl/`):
   `ascon_engine.v` (Ascon datapath, 1 round/clock), `crypto_top.v` (command/
   buffer/status interface + key regs), `i2c_eeprom_loader.v` (magic/version/
   CRC-16 validation + latch). Verify:
   ```bash
   iverilog -g2012 -I tb -s tb_crypto -o /tmp/sim_clean tb/tb_crypto.v rtl/ascon_engine.v rtl/crypto_top.v && vvp /tmp/sim_clean
   iverilog -g2012 -s tb_loader -o /tmp/sim_loader tb/tb_loader.v rtl/i2c_eeprom_loader.v && vvp /tmp/sim_loader
   ```
   Expect `ALL CHECKS PASSED (16 checks)` and `LOADER PASS`.

5. **Build + simulate the three Trojans** (compile-time options; clean build
   untouched). Each keeps the self-test passing and fires only on its rare
   trigger:
   ```bash
   for T in A B C; do iverilog -g2012 -I tb -DTROJAN_$T -s tb_crypto -o /tmp/sim_$T \
       tb/tb_crypto.v rtl/ascon_engine.v rtl/crypto_top.v && vvp /tmp/sim_$T; done
   ```
   - **A** (host nonce `A5…A5`, encrypt): leaks key‖IV‖secret into `OUT[0:47]`;
     the TB then shows a ciphertext forged with the leaked key is accepted
     (`AUTH_OK`) → C:H **and** I:H. Expect 22 checks.
   - **B** (reserved `CFG[7]`, decrypt): tag check forced to pass → a captured
     ciphertext + bogus tag returns the correct plaintext → C:H and I:H. 20 checks.
   - **C** (message prefix `C0FFEE00`, encrypt): forces nonce reuse → recovers a
     second plaintext by crib-drag → C:H. 18 checks.

6. **Synthesize for the UP5K + report Trojan overhead.**
   ```bash
   for T in CLEAN A B C; do d=""; [ "$T" != CLEAN ] && d="-DTROJAN_$T"; \
     yosys -p "read_verilog -sv $d rtl/ascon_engine.v rtl/crypto_top.v; synth_ice40 -noabc -top crypto_top; stat"; done
   ```
   Use `-noabc` (abc9 crashes on this host). Compare only the **delta** vs clean
   (A +427, B +44, C +11 SB_LUT4); the absolute ~39.8k LUT is an unoptimized,
   register-file-buffer figure — the real recovered design is 4577 LUT / 7 BRAM.

7. **Rate each Trojan with CVSS v3.1 — honestly.** Compute with
   `python work/analysis/cvss.py` (do not hand-assign). Use `AV:L` (the attack
   is through the SPI command interface, not physical die tampering), `S:C` for
   the key-isolation breach (the IP doc isolates keys from the host), and credit
   integrity **only where a simulation demonstrates it**. Result: A 9.0, B 9.0,
   C 7.1 (floors `AV:P/S:U` = 6.1/6.1/4.6). Never claim `AV:N` — there is no
   network path.

## 3. Deliverables to expect

`rtl/` (engine, top, loader, Trojans), `tb/` (self-test + golden-vector + Trojan
demos, loader test), `work/research/` (verified transcript), `work/analysis/cvss.py`,
`TROJAN_README.md`, `docs/documentation.html`, and `pipeline/RESULTS.md`.
