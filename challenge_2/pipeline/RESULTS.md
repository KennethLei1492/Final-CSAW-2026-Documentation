# Reproduction Results
_Generated Fri Nov 13 01:48:49 EST 2026_

## 1. Bitstream reverse-engineering
- unpacked bitstream -> work/re/crypto.asc
- device: 5k
- resource fingerprint:
    DFFs:    954
    LUTs:   4577
    CARRYs:  104
    BRAMs:     7
    IOBs:     12
    PLLs:      0
    GLBs:      8
- recovered netlist -> work/re/crypto_netlist.v (181494 lines)
## 2. AI-technique-model research (retrieval + verification)
- 11/11 claims verified (see work/research/research_report.md; method in ai/METHODOLOGY.md)
## 3. Ascon-AEAD128 reference + vectors
- reference self-consistency + 200 random roundtrips: ALL self-consistency + self-test-equivalent checks PASS
- golden vectors -> tb/vectors.vh
- EEPROM image  -> pipeline/eeprom_image.hex
## 4. Clean accelerator simulation
- clean: ALL CHECKS PASSED (16 checks)
## 5. Trojan insertion pass + simulations
- inserted A/B/C via tools/insert_trojan.py -> work/trojans/crypto_top_{A,B,C}.v
- A: ALL CHECKS PASSED (22 checks)
- B: ALL CHECKS PASSED (20 checks)
- C: ALL CHECKS PASSED (18 checks)
    == TROJAN A demo: magic-nonce -> secret exfiltration ==
       leaked KEY   =000102030405060708090a0b0c0d0e0f
       leaked NONCE =101112131415161718191a1b1c1d1e1f
       leaked SECRET=5365637265744b6579313233343536ff
      PASS TROJAN A: KEY exfiltrated via OUT (C:H)
      PASS TROJAN A: IV/nonce exfiltrated via OUT
      PASS TROJAN A: device secret exfiltrated via OUT
      PASS TROJAN A: forged ciphertext ACCEPTED using leaked key (I:H)
      PASS TROJAN A: forged plaintext is attacker-chosen 'ADMIN:grant-root'
    == TROJAN B demo: reserved CFG bit 7 -> auth bypass + plaintext recovery ==
      PASS TROJAN B: forged-tag decrypt ACCEPTED (reserved bit)
      PASS TROJAN B: CORRECT plaintext recovered with bogus tag (C:H+I:H)
    == TROJAN C demo: magic-MSG -> nonce override (reuse) ==
      PASS TROJAN C: nonce reuse (keystream collision)
      PASS TROJAN C: recovered 2nd plaintext via reuse (C:H)
## 6. I2C EEPROM key-loader (real master <-> EEPROM model)
- LOADER PASS: 64-byte image read over I2C, magic+version+CRC16 validated, secrets latched
## 6b. SPI-path self-test (normal operation preserved over real SPI framing)
- SPI SHELL OK (pass=7 fail=0) (encrypt+decrypt+auth+withhold driven through SCK/CS/MOSI/MISO)
## 7. iCE40-UP5K synthesis (core) + Trojan LUT overhead
- core LUT4: CLEAN=3698  A=4056 (+358)  B=3665 (+-33)  C=3718 (+20)
## 8. Board place & route -> bitstream that fits the UP5K
- clean: FITS (ICESTORM_LC: 4958/ 5280 93%; Max frequency for clock 'ICE_CLK$SB_IO_IN_$glb_clk': 27.95 MHz (PASS) -> work/board/clean.bin (104090 bytes)
- trojanA: FITS (ICESTORM_LC: 4967/ 5280 94%; Max frequency for clock 'ICE_CLK$SB_IO_IN_$glb_clk': 28.88 MHz (PASS) -> work/board/trojanA.bin (104090 bytes)
- trojanB: FITS (ICESTORM_LC: 4977/ 5280 94%; Max frequency for clock 'ICE_CLK$SB_IO_IN_$glb_clk': 29.64 MHz (PASS) -> work/board/trojanB.bin (104090 bytes)
- trojanC: FITS (ICESTORM_LC: 5017/ 5280 95%; Max frequency for clock 'ICE_CLK$SB_IO_IN_$glb_clk': 25.17 MHz (PASS) -> work/board/trojanC.bin (104090 bytes)

**RESULT: ALL STAGES PASSED.**
