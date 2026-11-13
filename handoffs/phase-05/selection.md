# Phase 05S cycle 004 — bounded continuation

Current and previous best: **05B `fd0ca7f6bce1d30bb1b1e6ce43603b4c7d51e5b6`**.
Original candidate: `9e172a865a543b03e226596689fd6691ffa2b779`.
Common baseline: `e72522f265ac36da713cd7a0dcf8dbc64ab21209`.
Ranking remains **B > C > D > A**. All four candidates are available locally and remotely, with unchanged reviewed heads. Root AGENTS.md is absent.

This invocation resumed completed cycle003 and unfinished cycle004 in isolated branch `challenge3/05s-cycle-04-resume`. Two focused improvements were accepted. Candidate RTL, golden expectations, constraints and original branches are unchanged. No public push or hardware programming occurred.

## Recovery and accepted improvements

The shared root still held cycle002. Original cycle003 commit `df22816fe29c479d404314bf0ae9e8baacdd1d3d` and recovered checkpoint `ab71ea88c7853fed7917c31c59c2f0b6abc83d96` have identical tree `d54f94500a282cbf43f59f11a6a7c282a5e91ee4`. The original commit is now reachable through `challenge3/05s-cycle-03-preserved`; the damaged old ref and abandoned worktree are preserved. Cycle003 and the stale shared checkpoint are archived.

1. **Checkpoint reliability:** Three injected winner/candidate/original-identity conflicts were accepted by the previous checker and are now rejected. Discovery retains broken-ref diagnostics, records invalid worktrees, creates output parents and refuses to overwrite receipts. Backlog consistency is checked. All **19 reporting regression tests passed**. Independent review found no must-fix regression; tests now create their build directory.
2. **Host readiness:** A hash-pinned pyserial 3.5 wheel installs into an isolated directory. **281 bytes** round-trip exactly through software `loop://`. Wrong-wheel-hash and existing-output tests reject inputs, and the base interpreter stays unchanged: **4 checks passed**. Only Bluetooth COM4/COM5 enumerate; no physical port was opened. Future board scripts must explicitly include `build/host-ready/site`; base Python still lacks pyserial.

The receipt collector could not retrieve HTTPS through OSS Python; the official source was retrieved through the GitHub connector. Final checkpoint validation first exposed an incorrectly normalized log digest in the manifest; the manifest was corrected to use the verifier's raw-log hash policy. Both failures are recorded. Neither was an RTL failure. No implementation revision was rejected because no RTL change was justified.

## New evidence reviewed

Local Phase8 `39a424d84a38562adfe8a9e4251b741b899ee93c` contains independent execution against the same best SHA: **47 simulations and 15 framework tests**, 22,248 normal words, 481,082 segmented-audio words and 480,260 continuous words, with zero mismatches. This cycle verified **4 checkpoint hashes and 1,032 output hashes**. These are audited retained executions, not new HDL runs this invocation. The selected build and repeat/roundtrip match bitstream SHA256 `2742912e31ec6c058756e5623d84736285dc2d46695d8ece616494e3152a89b0`: **3,240/5,280 cells, 15.2716 MHz versus 10 MHz**, UP5K/SG48, seed 1.

Phase8's earlier alternative-toolchain run passed simulations and timing but failed historical bitstream identity (3,716 cells, 14.972 MHz). That failed comparison is preserved; the matching pinned-toolchain run is the accepted reproduction. Phase8 still uses cycle002 selection metadata and configured model labels; those need reconciliation before submission.

The separate 05BB audit again verifies **634 archive entries and 27 source files**. Recovered bits, rates and BER remain substantiated simulation evidence. The official challenge scoring section is unchanged; deliverables now link to the finals overview. All ten gate dispositions remain in selection.json, with the physical gate open.

## B versus D and scoring

| Evidence | Q-corrected 05B | 05D |
|---|---|---|
| Baseline/regression | Stronger full and continuous audio coverage | Narrower retained coverage |
| Confirmed functional defects | Boundary defect repaired; none open in tested scope | None confirmed in reviewed scope |
| Cells / spare cells | 3,240 / 2,040 | 3,652 / 1,628 |
| Fmax at common 10 MHz target | 15.2716 MHz | 15.1833 MHz |
| Reproducibility | Corrected inventory; independent repeat build | Hard-coded paths and missing/stale analysis outputs |
| Physical evidence | None | None |
| Data recovery in original design | None | None |

**Main recommendation: retain Q-corrected 05B. Bonus B recommendation: keep the separate demonstrated 05BB experiment** (`4bf5e02856b6874c82a8eaf7983d54de4755c2e6`, package `83acf059f7b29fd0c8b1be16e952444ff5ccd84b`). Neither a newer commit nor a DSP proposal warrants promotion. Physical verification offers the greatest main benefit without redesign risk.

Conditional rubric assessment remains quality **20/25**, automation **9/15**, documentation **9/15**, physical **0/10**. Creative AI is unscored pending complete provenance review; no official score or competition-ready total is claimed. Bonus A has conditional simulation-tier **10/20** evidence for distinct A+D. Bonus B has conditional simulation-tier **5/10** evidence for separate 05BB:

| Simulated frame rate | Compared bits | Errors / BER | Capture duration | Net payload rate |
|---:|---:|---:|---:|---:|
| 31,250 Hz | 336 | 0 / 0 | 0.537344 s | 625.2978 bit/s |
| 15,625 Hz | 336 | 0 / 0 | 1.074688 s | 312.6489 bit/s |

These rates describe simulated captures, not physical throughput. Main long-audio coverage does not transfer to changed 05BB RTL. Hardware, drift/resampling robustness and complete transcript qualification remain open.

## Reproduction and next invocation

Run from the evaluation worktree with fresh output names:

```powershell
$py = 'C:/Users/lowbr/oss-cad-suite/lib/python3.exe'
& $py experiments/phase05s/verify_state.py --root .
& $py experiments/phase05s/cycle-04/test_reliability.py
& $py experiments/phase05s/inspect.py --repo . --state handoffs/phase-05/selection.json --output build/NEXT-discovery.json
& $py experiments/phase05s/cycle-04/review_release.py --source ../phase-08 --output build/NEXT-release-audit.json
& $py experiments/phase05s/cycle-03/audit_bonus_evidence.py --source ../phase-05bb --output build/NEXT-bonus-audit.json
& $py experiments/phase05s/cycle-04/host_readiness.py --wheel build/host-ready/wheel/pyserial-3.5-py2.py3-none-any.whl --output build/NEXT-host-ready
```

Stop reason: available priority checks pass and the main candidate awaits an identified physical Hackster. Cycle005 should inspect changed refs and resume the backlog, preserving this best SHA. Next action is the physical stock/candidate baseline and echo check, followed by controlled activation with captured evidence. Also reconcile provenance and release metadata; keep bonus experiments isolated.

Codex authored evaluation and host-readiness tooling only. Exact runtime model metadata for this invocation is not exposed; no inferred Astra claim is made. Prior sanitized provenance identifies original B runtime as `gpt-6-luna` and Q as `gpt-6-astra`, despite B's requested Astra label. Private transcripts remain outside tracked artifacts. The compact documentation handoff accompanies this checkpoint; Scribe model synthesis remains blocked by its placeholder model.
