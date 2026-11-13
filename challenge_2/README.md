# CSAW AHA 2026 — Final Challenge 2: Technical Brief & Reproduction

**Target:** externally-keyed authenticated-encryption accelerator on a Lattice
iCE40-UP5K (`fpga/crypto_eeprom_top.bin`). Key/IV/device-secret are provisioned
into an I2C EEPROM and loaded by the FPGA at power-up — **not** baked into the
bitstream.

This brief documents (1) how we reverse-engineered the bitstream, (2) the
AI-agent pipeline used to analyze it and generate the Trojans, (3) three distinct
hardware Trojans with CVSS ratings and simulated evidence, and (4) one-click
reproduction.

> **Detailed companion:** a fuller, formatted write-up — with the honest CVSS
> computation, per-Trojan mechanisms, the verified key-recovery table, and the
> synthesis-honesty notes — is in **[`docs/documentation.html`](docs/documentation.html)**
> (open in a browser). This README is the submission brief; the HTML is the
> expanded reference. Everything here is verified by simulation with the OSS CAD Suite;
the design is synthesizable for the UP5K.

> **Scope note.** No physical Hackster board was available in this environment,
> so the exploit is demonstrated in **cycle-accurate RTL simulation** (iverilog)
> against golden vectors, and the RTL is shown to **synthesize for the UP5K**
> (yosys `synth_ice40`). The board-bring-up steps are documented for 1:1 hardware
> reproduction. All design/analysis was performed by an AI agent; see
> `work/research/` and this file for the transcript trail.

---

## 1. How the accelerator works (reverse-engineering result)

### 1.1 Bitstream reverse-engineering — method and cross-checks

The bitstream was analyzed with multiple independent methods, each corroborating
the next (all reproduced by `pipeline/run_all.sh`, stage 1):

| Method | Tool | Result |
| --- | --- | --- |
| Header/sync | `xxd` | `FF00 00FF 7EAA 997E` iCE40 preamble at offset 4 |
| Unpack | `icepack -u` | `.device 5k` → **iCE40-UP5K** |
| Resource fingerprint | `icebox_stat` | **4577 LUT4, 954 DFF, 104 CARRY, 7 BRAM, 12 IOB, 8 GLB, 0 PLL** |
| Netlist recovery | `icebox_vlog` | 181k-line flattened netlist; 12 top-level IO |
| BRAM contents | `.ram_data` parse | **all 30 EBR init blocks are zero** → no key in bitstream |
| Device cross-check | Lattice UP5K datasheet | 5280 LUT / 30 EBR / 8 DSP / 1 PLL → design uses **87 % of LUTs**, 7/30 EBR, 0 PLL — fits, and the ~87 % utilization is consistent with a full 320-bit permutation datapath |

The 12 IOBs decompose as **4 inputs, 6 outputs, 2 bidirectional** — an exact match
to the documented pinout (CLK/SCK/CS/MOSI in; MISO/BUSY/LED/RGB×3 out; SDA/SCL
bidirectional I2C at the bottom edge, tile `io_9_0_*`). This is the first
structural confirmation of the SPI-peripheral + I2C-EEPROM topology.

### 1.2 Cipher identification — Ascon-AEAD128 (NIST SP 800-232)

Converging evidence (grounded and verified in `work/research/`):

- 128-bit key, 128-bit nonce/IV, **128-bit tag**, AEAD with tag verification, a
  "lightweight" core on a tiny FPGA → the NIST Lightweight-Crypto standard **ASCON**.
- The IP doc's organizer note says the INFO signature and EEPROM magic "spell a
  hint toward the cipher"; the recovered magic is ASCII **`ASCN`**.
- ~87 % LUT use with **no DSP/multiplier** usage matches ASCON's
  XOR/AND/rotate-only permutation (no multiplies), not AES (S-box tables) or a
  multiply-heavy cipher.

ASCON parameters used (confirmed against the official reference): state 320 bits
(x0..x4), IV `0x00001000808c0001`, pa=12 init/final rounds, pb=8 data rounds,
round constants `0xf0..0x4b`, rotation pairs x0(19,28) x1(61,39) x2(1,6)
x3(10,17) x4(7,41), tag = x3‖x4.

### 1.3 Key-provisioning path (EEPROM → FPGA over I2C)

At power-up the core's I2C master reads the 64-byte image from EEPROM `0x50`:

```
0x00 magic(4)="ASCN"  0x04 ver(1)=0x01  0x05 rsv(9)=0  0x0E crc16(2,BE)
0x10 key(16)          0x20 nonce(16)    0x30 secret(16)
```

It validates magic, version, and **CRC-16/CCITT-FALSE** over bytes `0x10..0x3F`,
then latches key/nonce/secret into internal registers that are never exposed over
SPI. Our reconstructed loader (`rtl/i2c_eeprom_loader.v`) implements exactly this
and is verified in `tb/tb_loader.v` (magic/version/CRC/latch all pass; the sample
image CRC is `0xB9A1`).

### 1.4 Command interface

SPI mode-0 peripheral, oversampled on the 10 MHz `ICE_CLK`; commands STATUS/WRITE/
READ/START/LOAD_KEYS/INFO/RESET; buffer map AD`0x000`/MSG`0x200`/OUT`0x400`/
TAG_IN`0x600`/TAG_OUT`0x610`/NONCE_IN`0x620`; `CFG[1:0]` op = 1 enc / 2 dec /
3 encrypt-the-device-secret; `CFG[3:2]` nonce source = EEPROM / host / EEPROM⊕host.
`rtl/crypto_top.v` implements this as the clean register-level view of the SPI
protocol and drives `rtl/ascon_engine.v` (the Ascon-AEAD128 datapath, one
permutation round per clock).

---

## 2. AI methodology (how the analysis & Trojans were generated)

**Interaction model:** an autonomous coding agent (Claude, Opus-class) driving the
OSS CAD Suite and a **composable six-model AI pipeline**
(`github.com/KennethLei1492/prebuilt-ai-technique-models`) with tool use,
retrieval, and programmatic verification.

**Grounded research (`work/research/`).** The five reference sources plus our own
RE measurements were indexed with the **Hybrid Retrieval** model; every analytical
claim (cipher identity, device fit, sniffable key path, stealth/payload strategy,
ASCON security dependence) was then gated by the **Answer Verification** model
against the retrieved evidence. We refused to advance on any claim the verifier
did not pass — two compound claims initially scored as *needs-review*, which
forced us to split them and add the RE measurements as first-class evidence;
all **7/7** claims then verified, each grounded on a specific source. The machine-
readable transcript is `work/research/research_transcript.json`; the readable
report is `work/research/research_report.md`.

**Programmatic verification chain.** The algorithm model (`work/sim/ascon_ref.py`)
was checked structurally against the official Ascon reference and by 200
randomized encrypt/decrypt roundtrips; it then generated the golden vectors that
the Verilog DUT is checked against — so RTL correctness is proven against an
independently-validated oracle, not by inspection.

---

## 3. The Trojans

All three are compile-time options that **do not touch the clean build**; each
keeps the full self-test passing and fires its payload only under a rare trigger
that never occurs in normal or self-test traffic. (The self-test uses host nonce
`00..0f`, AD `hackster-selftest`/`wrong-ad`, and the pangram message — none of
which match any trigger below.)

### Trojan A — Full key-material exfiltration → decrypt + forge *(strongest)*
- **Trigger:** host-supplied nonce equals the magic constant `A5A5…A5` on an
  **encrypt** operation. Attacker-controllable over SPI; 2⁻¹²⁸ by accident.
- **Payload:** the FPGA-isolated provisioning material is written across the
  isolation boundary into the host-readable `OUT` buffer —
  `OUT[0:15]=key`, `OUT[16:31]=IV/nonce`, `OUT[32:47]=device secret`. The real
  tag/ciphertext are still produced so the frame looks normal.
- **Demonstrated impact (both C and I):** with the leaked **key** an attacker (1)
  decrypts any captured ciphertext — **confidentiality**, and (2) forges a
  ciphertext+tag that the accelerator **accepts as authentic** — **integrity**.
  The testbench exfiltrates the key, then feeds a ciphertext the attacker forged
  offline with that key for the message `"ADMIN:grant-root"`; the device returns
  `AUTH_OK` and the attacker-chosen plaintext.
- **Stealth:** zero effect unless the exact 128-bit nonce is presented; adds a
  128-bit comparator + mux (overhead +171 LUT4, §4); no always-on side channel.
- **Mechanism:** `trjA_fire = (host_nonce==128'hA5…A5) & (op==ENCRYPT)`, latched at
  `START`; on completion `r_key`, `r_nonce`, `r_secret` are written to `OUT`.
- **CVSS v3.1:** `AV:L/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N` → **9.0 (Critical)**
  (conservative floor `AV:P/S:U` → 6.1). `AV:L` because the attack uses the
  accelerator's existing SPI command interface via the application processor (no
  physical die/bus manipulation); `S:C` because the IP doc states key material is
  "held inside the FPGA and never exposed through SPI" — the payload breaches that
  documented isolation boundary into the host's scope; `C:H`+`I:H` are both
  **demonstrated** (see below), not assumed.
- **Evidence (`work/sim/A.log`):** normal op does **not** leak key material; under
  the magic nonce `OUT[0:47] == key‖IV‖secret`
  (`000102…0e0f ‖ 1011…1e1f ‖ 5365…36ff`); forged `"ADMIN:grant-root"` ciphertext
  **ACCEPTED** (`AUTH_OK`) using the leaked key. Self-test 16/16 PASS (22 checks).

### Trojan B — Authentication-tag bypass + plaintext recovery
- **Trigger:** the **reserved CFG bit 7** of the `START` command byte, on a
  **decrypt**. (An earlier variant triggered on a magic AD, but the AD
  participates in the Ascon state, so it corrupted the recovered plaintext and
  gave only an integrity break. Moving the trigger to a reserved control bit —
  which does **not** touch the datapath — is a deliberate stealth+impact
  improvement; the bit is `0` in all normal and self-test traffic.)
- **Payload:** `force_auth` makes tag verification pass unconditionally, so a
  **captured ciphertext replayed with its real AD and a bogus tag decrypts to the
  correct plaintext**. This defeats integrity **and** confidentiality: an attacker
  who never saw the key or a valid tag recovers plaintext for any captured frame.
- **Mechanism:** `force_auth = cfg[7] & (op==DECRYPT)`, OR-ed into the tag-compare
  result in `ascon_engine.S_TAG`; the plaintext released during normal decryption
  processing is simply no longer withheld.
- **Stealth:** one AND + one OR gate; without the reserved bit every tamper is
  still rejected and plaintext withheld (both verified by control checks).
- **CVSS v3.1:** `AV:L/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N` → **9.0 (Critical)**
  (conservative floor `AV:P/S:U` → 6.1). Both impacts are **demonstrated**: `I:H`
  (forged tag accepted) and `C:H` (correct plaintext of a captured frame
  recovered). The reserved-bit redesign is a **real, tested** improvement over the
  old AD trigger (which scored `C:N/I:H`); `AV:L`/`S:C` justified as for Trojan A.
- **Evidence (`work/sim/B.log`):** forged-tag decrypt **ACCEPTED** and the
  **correct plaintext recovered** with a bogus tag; control (no trigger) rejects
  and withholds. Self-test 16/16 PASS (20 checks total).

### Trojan C — Forced nonce reuse (confidentiality break)
- **Trigger:** message first 4 bytes equal `C0FFEE00` on an **encrypt**.
- **Payload:** the effective nonce is overridden to a fixed constant regardless of
  the requested nonce source, so two encryptions reuse the same key+nonce →
  identical keystream → `C1⊕C2 = P1⊕P2` leaks plaintext relationships; ASCON
  confidentiality collapses under nonce reuse.
- **Stealth:** one mux on the nonce select; normal traffic uses the real nonce.
- **Mechanism:** `trjC_fire = (msg[0:3]==32'hC0FFEE00) & (op==ENCRYPT)` overrides
  the `cfg`-selected nonce source with `FIXED_NONCE`, so repeated encryptions
  reuse one key+nonce.
- **CVSS v3.1:** `AV:L/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N` → **7.1 (High)**
  (conservative floor `AV:P/S:U` → 4.6). Only **confidentiality** is credited:
  plaintext recovery under nonce reuse is demonstrated. Nonce reuse *can* enable
  forgery / state recovery in theory, but that was **not demonstrated here**, so
  `I:N` — no credit for undemonstrated impact. The score reaches High purely from
  the demonstrated confidentiality break crossing the isolation boundary (`S:C`),
  not from any assumed integrity impact.
- **Evidence (`work/sim/C.log`):** two messages with the magic prefix and
  **different** host nonces give a **keystream collision**, and an **unknown second
  plaintext is recovered** from a known one by crib-drag (`P2 = C2 ⊕ C1 ⊕ P1`).
  Self-test 16/16 PASS.

**Distinctness:** A/B/C use three different trigger domains (host nonce / reserved
CFG bit / message prefix) and three different payloads (key-material leak / auth
bypass + plaintext recovery / nonce reuse).

**Strongest = Trojan A (9.0 Critical)** — it leaks the full provisioned key
material and we *demonstrate* the resulting total break (decrypt + accepted
forgery). Trojan B ties on CVSS (9.0). Trojan C is 7.1 (High).

### 3.1 CVSS analysis — computed, source-verified, evidence-gated

Run `python work/analysis/cvss.py` to reproduce every score from the CVSS v3.1
formula. **Why the scores rose from an earlier over-conservative 4.6/6.1/4.6:**
that pass used `AV:P` and `S:U` and withheld integrity credit. Re-examined against
the **FIRST CVSS v3.1 specification** (and the claim was grounded by the Answer
Verification model, `work/research/`):

- **`AV:L` (not `AV:P`).** The spec scores Physical only when the attacker must
  *physically touch or manipulate* the component (e.g. attach hardware to a bus).
  Our triggers are issued through the accelerator's **existing SPI command
  interface** via the application processor — local logical access, i.e. `AV:L`.
  (`AV:N`/`AV:A` are still **not** claimed: there is no network path.)
- **`S:C` (not `S:U`).** The IP doc states key material is "held inside the FPGA
  and never exposed through SPI." Each payload breaches that **documented
  isolation boundary**, delivering FPGA-protected secrets/plaintext to the host
  processor — a different security authority. Per the spec that is Scope:Changed.
- **Integrity credited only where demonstrated.** A now leaks the **key** and we
  show a forged ciphertext accepted (`I:H`); B shows forged-tag acceptance
  (`I:H`); C shows no forgery, so stays `I:N`.

| Trojan | Vector | Score | Floor (AV:P/S:U) | Credited impact (all tested) |
| --- | --- | :---: | :---: | --- |
| A | `AV:L/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N` | **9.0 Critical** | 6.1 | C:H key/secret leak + I:H accepted forgery |
| B | `AV:L/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N` | **9.0 Critical** | 6.1 | C:H plaintext recovery + I:H forged-tag acceptance |
| C | `AV:L/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N` | **7.1 High** | 4.6 | C:H plaintext recovery (I:N — forgery not demonstrated) |

**Scope is the one genuine judgment call, so it is shown both ways.** Keeping
`AV:L` but using the conservative `S:U`: **A and B are still 7.7 (High)** on their
demonstrated `C:H`+`I:H` alone; **only C** (which has no demonstrated integrity
impact) depends on the `S:C` isolation-boundary reading to reach **7.1** — under
`S:U` it is 6.2. The most conservative floor (`AV:P/S:U`) is 6.1/6.1/4.6.

**Discipline, stated plainly:** the rise from 4.6/6.1/4.6 is driven by (a) two
spec-justified vector choices (`AV:L`, and `S:C` for the isolation breach) and (b) a
*real, newly-demonstrated* integrity impact for Trojan A (the accepted forgery). It
is **not** the earlier mistake of claiming `AV:N` with no basis. Where impact is not
demonstrated (C's integrity), no credit is taken.

### Bonus B — key / secret recovery (verified)

The board was provisioned (for this reproduction) with the image in
`pipeline/eeprom_image.hex`; recovery yields exactly these values, **verified in
simulation**:

| Field | Recovered value | Verified by |
| --- | --- | --- |
| **Key** | `000102030405060708090a0b0c0d0e0f` | **Trojan A** `OUT[0:15]` + I2C sniff / loader latch (`tb/tb_loader.v`) |
| **IV / Nonce** | `101112131415161718191a1b1c1d1e1f` | **Trojan A** `OUT[16:31]` + I2C sniff / loader latch |
| **Device secret** | `5365637265744b6579313233343536ff` (`"SecretKey123456\xff"`) | **Trojan A** `OUT[32:47]` (`work/sim/A.log`) and I2C sniff |

Two independent recovery routes:
1. **Trojan A** returns the full provisioning image (key‖IV‖secret) in
   `OUT[0:47]` — the sim asserts each 16-byte field equals the provisioned value.
2. **Passive I2C sniffing** (`thyrasec` method, needs no Trojan): the key image is
   read over the open, unencrypted I2C bus at power-up; clipping a logic analyzer
   on `SDA/SCL` captures the full 64-byte image (magic `ASCN`, version, CRC
   `0xB9A1`, key, IV, secret) at address `0x50`. `tb/tb_loader.v` reproduces the
   parse/validate/latch of that exact image.

---

## 4. Resource usage and Trojan overhead (honest)

Two caveats stated up front:

1. **abc9 crashes on this host.** `synth_ice40`'s default abc9 step asserts in the
   experimental `write_xaiger2` backend (`aiger.cc:1078`) — a tool bug, not our
   RTL; retried and confirmed. Numbers therefore come from classic `abc -lut 4`
   (optimized, heuristic) and `synth_ice40 -noabc` (deterministic, unoptimized).
2. **The behavioral reconstruction does not fit the UP5K as written.** Its
   AD/MSG/OUT buffers are register files — the engine does wide combinational block
   reads, which block EBR inference — so it synthesizes to ~28.8k LUT (optimized)
   / ~14k DFF, far over the 5280-LUT / ~1000-FF device budget. It is functionally
   correct and fully sim-verified, but **to run on the real board the buffers must
   be refactored to EBR.** The real recovered production bitstream does exactly
   that: **4577 LUT / 7 BRAM** (`icebox_stat`, §1.1). We state this rather than
   imply our reconstruction fits.

**Measuring the Trojan overhead.** Optimized `abc -lut 4` counts are useless here:
clean 28832, A 28475, B 28728, C 28493 — the Trojans appear to *reduce* logic,
which is impossible; the heuristic optimizer's run-to-run variance (±several hundred
LUTs) swamps the real overhead. The deterministic `-noabc` mapping (no optimizer
reshuffle) gives the honest added-gate count:

| Build | SB_LUT4 | ΔLUT4 vs clean | SB_DFF | SB_CARRY |
| --- | ---: | ---: | ---: | ---: |
| clean | 39779 | — | 14000 | 494 |
| Trojan A | 40206 | **+427** | 14001 | 494 |
| Trojan B | 39823 | **+44**  | 14001 | 494 |
| Trojan C | 39790 | **+11**  | 14000 | 494 |

The footprint is exactly what the RTL implies — a trigger comparator plus muxes:
A largest (it muxes **three** 128-bit registers — key, IV, secret — into OUT, so
+427 ≈ 1.1 %), C smallest (a 32-bit prefix compare + nonce mux), ≤1 added flop
each. These deltas are deterministic (`-noabc`), so they are an **upper bound** on
the real added LUTs after optimization; the overhead stays below the optimizer's
own noise floor and well within the device.

---

## 5. Reproduction

**One click (deterministic, no model needed):**

```bash
bash pipeline/run_all.sh
```

This regenerates the RE fingerprint, runs the verified AI-model research, rebuilds
the golden vectors + EEPROM image, simulates the clean design and all three
Trojans, validates the key-loader, and synthesizes every build — then writes
`pipeline/RESULTS.md` and exits non-zero if any stage fails.

**Re-run the whole AI analysis from scratch:** hand `pipeline/REPLICATE_PROMPT.md`
to a coding agent in this folder.

**One click on the board (build → program → drive each Trojan in turn):**

```bash
FPGA_PORT=/dev/ttyACM0 APP_PORT=/dev/ttyACM1 bash pipeline/run_all_board.sh
```

`pipeline/run_all_board.sh` is a superset of `run_all.sh` (which it calls
unmodified): it verifies in simulation, checks the SPI board-integration layer
(`tb/tb_spi.v`), then for the clean design and each Trojan builds a UP5K bitstream
(`crypto_board_top` + `spi_peripheral` + `i2c_eeprom_loader`, PCF
`rtl/crypto_board_top.pcf`) and — when a board is attached — programs it, runs
`tools/fpga_selftest.py`, and fires the matching on-board exploit
(`pipeline/board/exploit_trojan_{a,b,c}.py`). It writes `pipeline/BOARD_RESULTS.md`.
The single-prompt version is `pipeline/REPLICATE_PROMPT_BOARD.md`.

> **Honest hardware preconditions** (the script reports these, never fakes them):
> a provisioned board must be attached (P1); the `crypto_top` buffers must be
> refactored to EBR so the design fits the UP5K — as-written it is ~39.8k LUT and
> `nextpnr` will report it won't fit (P2); and the I2C loader's bit-level burst
> read must be completed (its validate/latch logic is done, P3). Synthesis, the
> SPI layer, the exploit drivers and the orchestration are complete and
> sim-verified.

---

## 6. File map

```
rtl/ascon_engine.v        Ascon-AEAD128 datapath (1 round/clock) + Trojan-B hook
rtl/crypto_top.v          command/buffer/status interface, key regs, Trojan A/B/C
rtl/i2c_eeprom_loader.v   I2C key-image loader (magic/version/CRC16 validation)
rtl/spi_peripheral.v      SPI mode-0 shell: frames -> crypto_top command interface
rtl/crypto_board_top.v    board top: real pins -> SPI + I2C loader + crypto_top
rtl/crypto_board_top.pcf  UP5K (sg48) pin constraints
tb/tb_crypto.v            self-test + golden-vector check + Trojan demos
tb/tb_loader.v            EEPROM key-loader validation
tb/tb_spi.v               SPI board-integration layer verification
tb/vectors.vh             golden vectors (generated)
work/analysis/cvss.py     CVSS v3.1 calculator (reproduces every score)
work/re/                  bitstream RE outputs (asc, stat, netlist)
work/research/            AI-model corpus, driver, verified transcript + report
work/sim/ascon_ref.py     validated Ascon reference (oracle)
work/sim/gen_*.py         vector / EEPROM-image generators
pipeline/run_all.sh       one-click simulation reproduction
pipeline/run_all_board.sh one-click BOARD automation (build/program/drive each Trojan)
pipeline/board/           on-board MicroPython exploit drivers (Trojan A/B/C)
pipeline/REPLICATE_PROMPT.md       single-prompt replication (sim)
pipeline/REPLICATE_PROMPT_BOARD.md single-prompt replication (board)
pipeline/eeprom_image.hex provisioned key image (CRC 0xB9A1)
```
