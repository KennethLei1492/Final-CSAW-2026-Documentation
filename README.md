# Final CSAW 2026 Documentation

Documentation for our CSAW 2026 AI Hardware Attack (AHA!) Challenge finals submission.
Each challenge is written up in its own folder; open that folder's `README.md` for the
full technical brief, simulations, and reproduction steps.

## Team: Goonies
| Challenge | Author(s) |
|---|---|
| Challenge 1 | Jessica Ryn & Kevin Wu (UNLV) |
| Challenge 2 | Kenneth Lei (UNLV) |
| Challenge 3 | Kyson Wu (UCLA) |

## Structure
- `challenge_1/` — Qualifying Trojan on the Hackster iCE40 board (key exfiltration).
- `challenge_2/` — ASCON-AEAD128 accelerator (externally keyed via I2C EEPROM); three distinct Trojans + key recovery.
- `challenge_3/` — FIR audio-filter Trojans; four AI-generated candidates, one selected.

All three designs were synthesized, programmed, and **implemented on the physical
Lattice iCE40-UP5K** (Hackster board).

## Status
| Challenge | Target | Result |
|---|---|---|
| 1 | 32-bit Feistel crypto core (SPI) on the Hackster UP5K | Two-block "knock" Trojan leaks device key `0x8E043CB1` over the normal SPI read path |
| 2 | ASCON-AEAD128 accelerator (I2C-EEPROM keyed, SPI) | Three Trojans — A key-material exfil (CVSS 9.0), B auth-tag bypass (9.0), C forced nonce reuse (7.1); full key/IV/secret recovered; all four board builds fit the UP5K (93–95% LC) |
| 3 | 63-tap FIR audio filter on the Hackster UP5K | Four AI-generated candidates; 05B (128-frame FIR bypass) selected — 0 errors over 481,082 output words, 4/4 activations, +30 logic cells |

## Shared approach
All Trojan RTL and exploit logic is AI-generated, as the competition requires, produced by a
Claude-agent pipeline following the CSAW 2025 **generate → insert → verify → retry** structure,
with an append-only audit log of the AI interactions retained under each challenge's `ai/` /
pipeline directories. Designs are reverse-engineered from the supplied bitstream, verified by
cycle-accurate RTL simulation against golden vectors, signed off for UP5K synthesis and timing,
and implemented on the physical board.
