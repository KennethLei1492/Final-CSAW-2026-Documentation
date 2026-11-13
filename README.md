# Final CSAW 2026 Documentation

Documentation for our CSAW 2026 AI Hardware Attack (AHA!) Challenge finals submission.
Each challenge is written up in its own folder.

## Structure
- `challenge_1/` — Qualifying Trojan carried onto the Hackster iCE40 board (key exfiltration). **Documented.**
- `challenge_2/` — _reserved; to be documented._
- `challenge_3/` — _reserved; to be documented._

## Status
| Challenge | Title | Status | Result |
|---|---|---|---|
| 1 | Qualifying Trojan on the Hackster board | Demonstrated on hardware | Device key `0x8E043CB1` exfiltrated |
| 2 | _TBD_ | Pending | — |
| 3 | _TBD_ | Pending | — |

## Shared approach
All Trojans and exploit logic are AI-generated, as the competition requires, produced by a
Claude-agent pipeline (CSAW 2025 generate → insert → verify → retry structure) with a complete
append-only audit log of every AI interaction.
