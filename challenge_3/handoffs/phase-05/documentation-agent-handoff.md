# Project Scribe handoff — 05S-004

Main selection unchanged: 05B `fd0ca7f6bce1d30bb1b1e6ce43603b4c7d51e5b6`.
Ranking B > C > D > A. Original B `9e172a865a543b03e226596689fd6691ffa2b779`; baseline `e72522f265ac36da713cd7a0dcf8dbc64ab21209`.

- Recovered authoritative cycle003 (tree identical to original); original commit preserved under `challenge3/05s-cycle-03-preserved`. Shared root was stale002.
- Accepted checkpoint/discovery fixes (19 tests) and isolated host pyserial readiness (4 checks, 281 exact loopback bytes). No RTL changes or rejected RTL.
- Reviewed newer Phase8 execution: 47 simulations, 15 framework tests, matching repeat bitstream, 3,240 cells / 15.2716 MHz. Reaudited 4 checkpoints and 1,032 output hashes; no fresh HDL/synthesis this invocation.
- Bonus A: conditional simulation 10/20 for A+D. Bonus B: separate 05BB simulation 5/10 evidence, 336/336 bits per rate, BER 0, 625.2978/312.6489 bit/s. Main has no demonstrated data channel.
- No physical board: Bluetooth COM4/COM5 only. Loopback does not close the hardware gate. Main assessment remains conditional 20 quality / 9 automation / 9 documentation / 0 physical; creative AI unscored, no total.
- No new selected RTL defects. Reporting identity gaps fixed. Old corrupted ref preserved; use recovered/preserved refs. Phase8 still uses cycle002 and requested model labels; reconcile before submission.
- This invocation: Codex authored tooling; exact runtime model not exposed. Prior B runtime gpt-6-luna, Q gpt-6-astra. No private logs pushed.

Full rationale and commands: [selection.md](selection.md). Receipts and failures: `cycles/05S-004/`. Historical selections preserved. Next: identify Hackster and capture stock/candidate baseline, echo and activation. Integrate this handoff without changing candidate branches or overwriting other agents' reports. No public publication is authorized by this handoff.
