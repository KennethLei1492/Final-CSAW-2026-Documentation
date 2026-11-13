# Final CSAW 2026 Documentation

Documentation for our CSAW 2026 AI Hardware Attack (AHA!) Challenge finals submission
(team **GOONIES**). Each challenge is written up in its own folder; open that folder's
`README.md` for the full technical brief, simulations, and reproduction steps.

## Structure
- `challenge_1/` — Qualifying Trojan carried onto the physical Hackster iCE40 board (key exfiltration). **Demonstrated on hardware.**
- `challenge_2/` — ASCON-AEAD128 accelerator (externally keyed via I2C EEPROM); three distinct Trojans + key recovery. **Verified in simulation + synthesis.**
- `challenge_3/` — FIR audio-filter Trojans; four AI-generated candidates, one selected. **Verified in simulation + synthesis.**

## Status
| Challenge | Target | Status | Result |
|---|---|---|---|
| 1 | 32-bit Feistel crypto core (SPI) on the Hackster UP5K | Demonstrated on hardware | Two-block "knock" Trojan leaks device key `0x8E043CB1` over the normal SPI read path |
| 2 | ASCON-AEAD128 accelerator (I2C-EEPROM keyed, SPI) | Verified in simulation + synthesis (no board) | Three Trojans — A key-material exfil (CVSS 9.0), B auth-tag bypass (9.0), C forced nonce reuse (7.1); full key/IV/secret recovered; all four board builds fit the UP5K (93–95% LC) |
| 3 | 63-tap FIR audio filter on the Hackster UP5K | Verified in simulation + synthesis (no board) | Four AI-generated candidates; 05B (128-frame FIR bypass) selected — 0 errors over 481,082 output words, 4/4 activations, +30 logic cells |

## Shared approach
All Trojan RTL and exploit logic is AI-generated, as the competition requires, produced by a
Claude-agent pipeline following the CSAW 2025 **generate → insert → verify → retry** structure,
with an append-only audit log of the AI interactions retained under each challenge's `ai/` /
pipeline directories.

## Scope & honesty
Challenge 1 was demonstrated live on the physical Hackster board. Challenges 2 and 3 were
verified by **cycle-accurate RTL simulation** against golden vectors and **signed off for UP5K
synthesis, place-and-route, and timing**, but no physical board was available for them — their
on-board demonstration and complete main-session AI transcript capture remain outstanding.
Simulation and hardware claims are kept separate throughout each write-up.
