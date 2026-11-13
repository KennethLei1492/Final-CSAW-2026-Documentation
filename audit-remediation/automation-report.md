# Automation report (findings §21–26)

**Category:** System Automation — 15 points.
**Verdict:** The auditor's "no scripts in the folder" is folder-true; the project
has a substantial, deterministic build/sim/synth/validate pipeline. §21–23, §25,
§26 are `EVIDENCE_EXISTS`; **§24 (one-command generation→board) is `CONFIRMED`
partial** — the Exemplary bar is not met, Proficient→Strong is.

> **Execution note.** This cycle did **not** re-run the FPGA pipeline (bounded
> cycle; avoids a toolchain-PATH detour). The results cited are **recorded
> executions** from Phases 5S/Q/6 with receipts; the exact commands to reproduce
> live are given below. Live re-execution is the top next-cycle action for Codex.

## Pipeline inventory (repo-wide)

**Phase 4 — `.worktrees/phase-04/infrastructure/`** (manifest-driven):
- `run.py` — subcommands `doctor` (probe deps, capture versions + executable
  hashes), `sim`, `synth`, place-and-route, `pack`, `icetime`, `validate`,
  `compare`; `--suite` pins the OSS CAD Suite.
- `run.ps1`, `bootstrap.py` (suite download + checksum), `toolchain.py`,
  `toolchain-lock.json` (pinned versions/hashes).
- HDL bench: `hdl/i2s_driver.sv`, `hdl/i2s_monitor.sv`, `hdl/tb_i2s.sv`;
  adapters `adapters/recovered.sv`; `recovered_reference.py`, `results.py`,
  `vectors.py`.

**Phase 8 — `.worktrees/phase-08/`**:
- `reproduce.py` — `--evaluate-candidates`, `--validate-selected`, `--baseline`,
  with gates `baseline_simulation / synthesis / resource_timing / ai_provenance /
  physical`; verifies commit SHAs, worktrees, and content hashes.
- `release_package.py`, `release_transcripts.py`, `tests/test_release.py`.

**Candidate folder** (`.../05b-astra/`): `README.md` carries a full PowerShell
reproduction recipe (`prepare_vectors.py` → `run.py validate` → `audit_results.py`
→ full-audio `sim` → `audit_full_audio.py`).

## Finding verdicts

| # | Claim (folder) | Status | Evidence |
| --- | --- | --- | --- |
| 21 | No build script | `EVIDENCE_EXISTS` | `run.py`, `run.ps1`, `bootstrap.py`, `reproduce.py` |
| 22 | No yosys/nextpnr/icepack | `EVIDENCE_EXISTS` | `run.py` synth/pnr/pack/icetime; `toolchain-lock.json` |
| 23 | No programmer/flasher | `EVIDENCE_EXISTS` (exec BLOCKED) | Hackster `Makefile` + `hackster-fpga-program.py` in Phase 8 `official/`; flashing needs a board |
| 24 | No one-command flow | `CONFIRMED` (partial) | build+sim+validate IS one command; generate→insert not wired; board gated |
| 25 | No regression vs `filtered_test_audio.wav` | `EVIDENCE_EXISTS` | `audit_full_audio.py` (481,082 words vs baseline); Phase 3 proved sw≡official WAV |
| 26 | No link self-test runner | `EVIDENCE_EXISTS` (HW BLOCKED) | 15 framework unit tests; official `stream_audio.py --self-test` preserved |

## Automation level, honestly

Rubric tiers: Exemplary(15)=one command generation→insertion→programmed board;
Strong(12)=fully scripted, single manual trigger; Proficient(9)=mostly automated,
1–2 handoffs.

- **Fully automated, local, no credentials:** elaborate → simulate →
  golden-compare → synth → P&R → timing → bitstream → validate (one command:
  `run.py --suite <S> validate --manifest <m>` or `reproduce.py --validate-selected`).
- **Credential-gated:** AI *generation* of the RTL (model session) — intentionally
  out of the reproducible build (judges reproduce the *build*, not the AI run;
  `submission-README`: "Simulation and build reproduction requires no AI service").
- **Hardware-gated:** board programming, link self-test, physical capture.
- **Manual handoff:** AI generation → RTL insertion is not a single scripted step.

**Realistic placement: Proficient→Strong (9–12).** Exemplary (15) would need the
generation→insertion step wired into one command *and* an automated program/verify
on the board.

## Recommended actions
1. **Codex:** add a thin top-level `orchestrate.py`/`make`-style entry that chains
   generate-stub → insert → `run.py validate`, stopping explicitly at the board
   boundary with a printed manual step. Moves §24 toward Strong.
2. **Codex:** live-run `run.py doctor` + `reproduce.py --validate-selected` and
   capture fresh versions/exit codes into `evidence/` (next cycle).
3. Keep the board program/flash step documented and marked hardware-gated
   (see `hardware-evidence-report.md`).

## Reproduce live (one command set)
```powershell
$S  = '<PATH-TO>\CSAW_FIN\.worktrees\phase-04\.tools\oss-cad-suite'   # repo root
$QW = '<PATH-TO>\CSAW_FIN_worktrees\quality-winner'                   # candidate worktree (sibling of repo root)
$py = Join-Path $S 'lib\python3.exe'
cd $QW
& $py (Join-Path $S '..\..\infrastructure\run.py') --suite $S doctor
& $py infrastructure/run.py --suite $S validate --manifest experiments/phase05/05b-astra/manifest.json --output experiments/phase05/05b-astra/reports/reproduction-run
```
(Add `$S\bin` and `$S\lib` to `PATH` and set `YOSYSHQ_ROOT=$S` first, or `vvp`
fails with `libvvp-1.dll` — see project toolchain note.)
