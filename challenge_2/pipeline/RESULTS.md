# Reproduction Results
_Generated Thu Nov 12 19:33:10 EST 2026_

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
- 11/11 claims verified (see work/research/research_report.md)
## 3. Ascon-AEAD128 reference + vectors
- reference self-consistency + 200 random roundtrips: ALL self-consistency + self-test-equivalent checks PASS
- golden vectors -> tb/vectors.vh
- EEPROM image  -> pipeline/eeprom_image.hex
## 4. Clean accelerator simulation
- clean: ALL CHECKS PASSED (16 checks)
## 5. Trojan simulations (self-test preserved + payload fires)
- A: ALL CHECKS PASSED (22 checks)
- B: ALL CHECKS PASSED (20 checks)
- C: ALL CHECKS PASSED (18 checks)
      PASS TROJAN A: KEY exfiltrated via OUT (C:H)
      PASS TROJAN A: IV/nonce exfiltrated via OUT
      PASS TROJAN A: device secret exfiltrated via OUT
      PASS TROJAN A: forged ciphertext ACCEPTED using leaked key (I:H)
      PASS TROJAN A: forged plaintext is attacker-chosen 'ADMIN:grant-root'
      PASS TROJAN B: forged-tag decrypt ACCEPTED (reserved bit)
      PASS TROJAN B: CORRECT plaintext recovered with bogus tag (C:H+I:H)
      PASS TROJAN C: nonce reuse (keystream collision)
      PASS TROJAN C: recovered 2nd plaintext via reuse (C:H)
## 6. I2C EEPROM key-loader validation
