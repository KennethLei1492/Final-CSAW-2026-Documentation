# Phase 05S — independent candidate selection

**Selection:** 05B, provisional. Start Subphase Q from immutable package commit
`9e172a865a543b03e226596689fd6691ffa2b779` on
`challenge3/05b-astra`. Its RTL entered at
`15a8a6525e225ad82d931b3bc75399f744638b2e` and was unchanged by the
later three commits. The common Phase 4 baseline is
`e72522f265ac36da713cd7a0dcf8dbc64ab21209`.
05C is the backup. No candidate branch was changed or merged.

This is a selection for further work, **not a fully verified final submission**.
All four pass fresh simulation and FPGA synthesis/timing checks. None has a
physical-board exploit capture, and none packages the complete main-session
prompt/response history required by the official challenge rules. Physical
operation is reported separately from simulation throughout this handoff.

## Frozen packages and qualification gates

The packages were exported with `git archive` from the exact SHAs below into
ignored `.worktrees/05s-*` directories. Candidate branches were inspected
read-only. All four descend from the same Phase 4 baseline.

| Rank | ID | Immutable package SHA | Source/dependencies | Baseline and relevant tests | UP5K fit and 10 MHz timing | AI log gate | Physical |
| ---: | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | **05B** | `9e172a865a543b03e226596689fd6691ffa2b779` | Present | Pass; fresh 10-case suite and full WAV | Pass | Incomplete main transcript | Not run |
| 2 | **05C** | `f4e8eedcb55d73f5f3adc97431a4a1a3a9c65c87` | Present after regenerating Phase 2 inputs and absolute manifests | Pass; 8 inactive, 8 directed | Pass | Incomplete main transcript | Not run |
| 3 | **05D** | `629c7d4a1dd158ff1b6585e0e84e9aff74f8810f` | Present for HDL checks | Pass; 6 baseline, 10 inactive, 3 active | Pass | Workflow logs present; main transcript incomplete | Not run |
| 4 | **05A** | `99a3fdb6d1f87ffd75bcfa46d7adc94664d97b29` | Present | Pass; 7 baseline, 7 candidate | Pass | Concise interaction record only | Not run |

05A and 05C manifests identify the earlier commits that introduced their
candidate RTL; their branch tips add manifest metadata only. 05B's
`STATUS.md` identifies its RTL origin SHA, but its manifest does not state an
exact package SHA. 05D's manifest says “HEAD” instead of a literal SHA.
Those package identity gaps are recorded here with the exact archived SHAs.

Source lists, adapters, reference models, constraints, vectors, handoffs and
recorded failure notes exist in the archives. 05A's manifest names generated
bitstreams excluded from Git; 05C's committed manifests point at its old
absolute worktree and untracked `build/recovered-inputs`; 05D's manifest
references `reports/verification-report.md`, which is absent. The regeneration
steps below let 05C's tests execute without editing its branch. None of the
submitted hash inventories should be treated as a substitute for fresh input
hashes and results.

## Independent tests and engineering metrics

All fresh tests used the installed `C:/Users/lowbr/oss-cad-suite` and the
Phase 4 `infrastructure/run.py` harness. Simulations compared signed 16-bit
output words with zero tolerance and no implicit alignment. The first
restricted-process attempt crashed Icarus with exit code 3221225477, matching
the Phase 4 environment warning; ordinary process execution then passed.
05A's first ordinary-process `validate` run had one transient FST framework
unit-test error. An isolated retry passed all 15 framework tests, and its
candidate and baseline regressions both passed.

**Identical baseline vectors:** all four passed the same recovered supplied
vectors at 1 MHz and 625 kHz BCLK, 516 output words per case, with zero errors.
The same 16-bit I2S parameters and `RESET_CYCLES=64` were used. These vectors
show a shared baseline check in simulation; they do not replace the official
physical audio comparison.

| Candidate | Fresh native suite | Controlled output versus independent baseline model | Extra coverage |
| :-- | :-- | :-- | :-- |
| 05A | 7/7 candidate, 7/7 baseline; both FPGA builds pass | 55/130 words changed, all left LSB; first word 20; right unchanged | Inactive, random, near miss, boundary, supplied audio; initial harness failures documented |
| **05B** | 10/10 candidate simulations, 15/15 framework tests, FPGA build pass | 128/1,000 words changed, all left; first word 42; right unchanged. Four trigger events each bypass exactly 128 frames. | Seven no-trigger cases: 0/22,248 baseline errors. Fresh 240,000-frame WAV run split into four overlapping segments: 0/481,082 output errors and zero trigger hits. |
| 05C | 8/8 inactive, 3/3 active, 5/5 near-miss; FPGA build pass | 127/276 words changed, all left; first word 22; right unchanged | Right-slot knock exercises unused I2S input; inactive suite includes 1,024 real-audio frames |
| 05D | 6/6 baseline, 10/10 inactive, 3/3 triggered; FPGA build pass | 925/3,456 words changed, all left; first word 1,156; right unchanged | Spectral trigger, adjacent-tone negatives, 2,048-frame noisy WAV, 500 Hz probe |

For the controlled comparison, each fresh `actual.csv` was compared to the
**same Phase 2 recovered baseline model and coefficients**, fed the case's
fresh `input.csv`. Candidate-local Trojan models were used by the harness
for the original active-case pass/fail checks. A zero right-channel difference
was confirmed in every representative active comparison.

The table below is the **comparable** build measurement: direct
`fir_audio_top` for every design, same nine-pin Hackster PCF, UP5K/SG48,
10 MHz target and seed 1. The baseline was built under those same settings.
All place-and-route runs and bitstream pack/unpack round trips passed. There
were zero DSP and RAM blocks in every build.

| Design | Logic cells / 5,280 | Delta vs shared baseline | Fmax MHz | Timing margin over 10 MHz |
| :-- | --: | --: | --: | --: |
| Shared baseline | 3,283 | — | 14.963 | 4.963 |
| 05A | 3,336 | +53 (1.61%) | 15.214 | 5.214 |
| **05B** | **3,313** | **+30 (0.91%)** | **15.485** | **5.485** |
| 05C | 3,322 | +39 (1.19%) | 15.143 | 5.143 |
| 05D | 3,652 | +369 (11.24%) | 15.183 | 5.183 |

The submitted candidates used different synthesis tops and pin counts, so
their native logic-cell figures should be read within each candidate only:
05A 3,360/14.793 MHz; 05B 3,313/15.485 MHz; 05C
3,292/14.836 MHz; 05D 3,704/14.409 MHz. The direct-top table controls that
confounder.

**05B receipt discrepancy:** its committed `validation-run-7` receipt
reports 3,662 logic cells, 15.132 MHz, source hash
`2c868b30...` and bitstream hash `49e24471...`. The immutable selected
archive's RTL input hashes to `0723c5bf...`; fresh `validate` and the
independent common build both produce **3,313 cells, 15.485 MHz and the same
`7fff6e2d74e617354d0d06b4098758137f6f82f5e0ba2d362ec8ab39e5ac47bd`
bitstream**. Its audit script flags comparison to the old receipt as
nonidentical. The older values are excluded from the ranking. Fresh standard
and full-audio simulations are valid for the frozen SHA.

## Official rubric assessment

The [official Challenge 3 scoring sheet](https://github.com/JBlocklove/CSAW-AI-Hardware-Attack-Challenge-2026/blob/main/finals/challenge_3/README.md)
weights Creative AI 35, Trojan Quality 25, System Automation 15,
Documentation/Reproducibility 15, and physical Hardware Demonstration 10.
The figures here are **provisional evaluator estimates**, not official judge
scores; no total is assigned. Creative AI remains unscored because the
competition requires comprehensive prompts and responses for the actual
RTL/exploit authoring. 05D has the strongest preserved workflow transcript
evidence, 05C has an evaluation workflow journal, and 05A/05B have authored
summaries. None supplies the full main-session record.

| ID | AI methodology/provenance /35 | Trojan quality /25 | Automation /15 | Documentation /15 | Physical demo /10 |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 05A | Unscored; summary only | 15, Proficient: exact trigger, small but one-bit corruption | 6, Developing: several run steps | 9, Proficient: clear mechanism; generated artifacts omitted | 0, None |
| **05B** | Unscored; summary only | **20, Strong:** exact eight-word trigger, 128-frame bypass, +30 LC, broad regression | **9, Proficient:** scripts and one harness command for standard suite | **9, Proficient:** clear handoff; stale receipt hashes need repair | **0, None** |
| 05C | Unscored; workflow journal lacks RTL-authoring session | 20, Strong: right-slot knock, sticky bypass, +39 LC; host driver absent | 6, Developing: regenerate missing inputs/manifests | 6, Developing: old absolute paths and no exploit driver | 0, None |
| 05D | Unscored; workflow transcripts lack RTL-authoring session | 15, Proficient: spectral response inversion; +369 LC | 6, Developing: several manual run stages | 9, Proficient: strong DSP record; one referenced report missing | 0, None |

These quality estimates use simulation and synthesis evidence. The official
baseline check streams audio on the real board against the provided bitstream;
it has **not** been performed for any candidate. A judge could change any
category after inspecting complete transcripts and physical behavior.
Bonus Trojans and covert-channel points were not evaluated.

## Selection rationale and Subphase Q priorities

05B has the best verified combination of severe but bounded filter bypass,
very specific trigger, small **measured** hardware overhead, strongest timing
under common settings, four successful activations including retrigger and
two I2S rates, and the widest normal-operation coverage. Its full noisy-audio
regression was rerun independently from the frozen SHA, including all 240,000
source frames. That outweighs its documentation and receipt defects for
selection as a quality-improvement starting point.

05C is the strongest backup: compact RTL, severe persistent bypass and good
directed negatives. Its trigger needs a host driver that sends distinct right
I2S values; the supplied `stream_audio.py` duplicates the mono sample into
both slots, although `audio_bridge.py` accepts arbitrary 32-bit frame words.
05D contributes useful adjacent-tone and spectral test ideas plus substantial
workflow records. 05A offers a compact exact-trigger comparison but its
one-bit payload is much weaker.

Work for Subphase Q, in priority order:

1. Recover and package 05B's complete Codex prompt/response history and map
   the RTL, reference model, vectors and exploit logic to that history. The
   official challenge says missing logs may disqualify the submission.
2. Regenerate 05B's manifest SHA, source hashes, receipts and bitstream claims
   from `9e172a865a543b03e226596689fd6691ffa2b779`. Keep the old
   nonmatching reports labeled as superseded.
3. Program a Hackster board and capture normal-operation output against the
   supplied bitstream, the echo link check, triggered 128-frame bypass, and
   input/output audio or spectrogram plus host logs. Check the actual pin/LED
   behavior. Simulation and P&R do not establish those observations.
4. Provide a single host exploit command, repeatable board setup and final
   technical brief. Review the final artifact package for sensitive files
   before any public push or submission.
5. Use 05C's right-slot near misses and 05D's spectral probes as **test ideas**
   without merging their implementations into 05B.

## Reproduction

Run these PowerShell commands from
`C:/Users/lowbr/Documents/College/AI/CSAW_FIN`. The OSS CAD Suite path
below is the installed version used here. Each `--output` directory must be
new; change its suffix on a later rerun. Ordinary process execution is needed
on this host because Icarus crashes inside the restricted process sandbox.

```powershell
$root = (Get-Location).Path
$suite = 'C:/Users/lowbr/oss-cad-suite'
$py = "$suite/lib/python3.exe"
$sha = @{
  a = '99a3fdb6d1f87ffd75bcfa46d7adc94664d97b29'
  b = '9e172a865a543b03e226596689fd6691ffa2b779'
  c = 'f4e8eedcb55d73f5f3adc97431a4a1a3a9c65c87'
  d = '629c7d4a1dd158ff1b6585e0e84e9aff74f8810f'
}
foreach ($id in @('a','b','c','d')) {
  $dst = "$root/.worktrees/05s-$id"
  New-Item -ItemType Directory -Force -Path $dst | Out-Null
  $archive = "$root/.worktrees/05s-$id.tar"
  git archive --format=tar --output=$archive $sha[$id]
  tar -xf $archive -C $dst
  Remove-Item -LiteralPath $archive
}
```

Continue in the same PowerShell session. The candidate-native tests were:

```powershell
# .worktrees/05s-a
Push-Location "$root/.worktrees/05s-a"
& $py infrastructure/run.py --suite $suite regress --manifest experiments/phase05/05a-luna/manifest-baseline.json --output build/05s-baseline-a-escalated
& $py infrastructure/run.py --suite $suite regress --manifest experiments/phase05/05a-luna/manifest.json --output build/05s-regress-a-escalated
Pop-Location

# .worktrees/05s-b
Push-Location "$root/.worktrees/05s-b"
& $py infrastructure/run.py --suite $suite validate --manifest experiments/phase05/05b-astra/manifest.json --output build/05s-validate-b-escalated
& $py experiments/phase05/05b-astra/tests/prepare_full_audio.py
& $py infrastructure/run.py --suite $suite sim --manifest experiments/phase05/05b-astra/tests/full_audio_manifest.json --output build/05s-full-audio
& $py experiments/phase05/05b-astra/tests/audit_full_audio.py --run build/05s-full-audio --summary experiments/phase05/05b-astra/reports/full-audio-vectors/source-summary.json --output build/05s-full-audio-audit.json
Pop-Location

# .worktrees/05s-c
Push-Location "$root/.worktrees/05s-c"
& $py infrastructure/prepare_recovered.py --source-root $root --ref 1befb30e99a506698c45d4ca9394a3c7ec95c966 --output build/recovered-inputs
& $py experiments/phase05/05c-opus-architecture/tests/build_manifests.py
& $py infrastructure/run.py --suite $suite regress --manifest experiments/phase05/05c-opus-architecture/tests/inactive_equiv.manifest.json --output build/05s-inactive-escalated
& $py infrastructure/run.py --suite $suite sim --manifest experiments/phase05/05c-opus-architecture/tests/directed.manifest.json --output build/05s-directed-escalated
Pop-Location

# .worktrees/05s-d
Push-Location "$root/.worktrees/05s-d"
& $py infrastructure/run.py --suite $suite sim --manifest experiments/phase05/05d-opus-dsp/tests/baseline.json --output build/05s-baseline-escalated
& $py infrastructure/run.py --suite $suite regress --manifest experiments/phase05/05d-opus-dsp/tests/trojan_untriggered.json --output build/05s-untriggered-escalated
& $py infrastructure/run.py --suite $suite sim --manifest experiments/phase05/05d-opus-dsp/tests/trojan_triggered.json --output build/05s-triggered-escalated
Pop-Location
```

These are the exact commands used to generate and run the shared baseline
vector manifests, after 05C's recovered inputs have been prepared above:

```powershell
$evalRoot = "$root/.worktrees"
$vec = "$evalRoot/05s-c/build/recovered-inputs/vectors"
$simSources = @{
  a = @('experiments/phase05/05a-luna/rtl/candidate/fir_audio_top_candidate.v', 'experiments/phase05/05a-luna/rtl/candidate/phase5_dut_adapter.sv')
  b = @('experiments/phase05/05b-astra/rtl/fir_audio_top.v', 'experiments/phase05/05b-astra/rtl/phase4_dut.sv')
  c = @('experiments/phase05/05c-opus-architecture/rtl/fir_audio_top_trojan.v', 'experiments/phase05/05c-opus-architecture/rtl/trojan_adapter.sv')
  d = @('experiments/phase05/05d-opus-dsp/rtl/fir_audio_top_trojan.v', 'experiments/phase05/05d-opus-dsp/rtl/dut_adapter.sv')
}
foreach ($id in @('a','b','c','d')) {
  $dir = "$evalRoot/05s-$id"
  $sources = @($simSources[$id] | ForEach-Object { "$dir/$_" })
  $manifest = @{
    schema_version = 1; name = "05s-common-baseline-$id"
    kind = 'verified_design'; ready = $true
    verification_evidence = @("$evalRoot/05s-c/build/recovered-inputs/provenance.json")
    simulation = @{
      sources = $sources
      parameters = @{
        SAMPLE_BITS=16; SLOT_BITS=16; MSB_DELAY=1; LEFT_LEVEL=0
        HALF_PERIOD_NS=500; CLOCK_HALF_NS=50; RESET_CYCLES=64
      }
    }
    cases = @(
      @{name='supplied-vectors-1mhz'; input_csv="$vec/supplied-vectors-1mhz-input.csv"; expected_csv="$vec/supplied-vectors-1mhz-expected.csv"; tolerance=0; latency_words=0},
      @{name='supplied-vectors-625khz'; input_csv="$vec/supplied-vectors-625khz-input.csv"; expected_csv="$vec/supplied-vectors-625khz-expected.csv"; parameters=@{HALF_PERIOD_NS=800}; tolerance=0; latency_words=0}
    )
  }
  $manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath "$dir/build/05s-common.manifest.json" -Encoding utf8
  Push-Location $dir
  & $py infrastructure/run.py --suite $suite sim --manifest build/05s-common.manifest.json --output build/05s-common-run
  Pop-Location
}
```

The common resource/timing builds used these commands. The first design is
the shared baseline, and all five used the same 05B board PCF:

```powershell
$cores = @{
  baseline = 'experiments/phase05/05b-astra/rtl/baseline/fir_audio_top.v'
  a = 'experiments/phase05/05a-luna/rtl/candidate/fir_audio_top_candidate.v'
  b = 'experiments/phase05/05b-astra/rtl/fir_audio_top.v'
  c = 'experiments/phase05/05c-opus-architecture/rtl/fir_audio_top_trojan.v'
  d = 'experiments/phase05/05d-opus-dsp/rtl/fir_audio_top_trojan.v'
}
foreach ($id in @('baseline','a','b','c','d')) {
  $which = if ($id -eq 'baseline') { 'b' } else { $id }
  $dir = "$evalRoot/05s-$which"
  $manifest = @{
    schema_version=1; name="05s-common-build-$id"
    kind='verified_design'; ready=$true
    verification_evidence=@("$evalRoot/05s-c/build/recovered-inputs/provenance.json")
    build=@{
      sources=@("$dir/$($cores[$id])"); top='fir_audio_top'
      device='up5k'; package='sg48'
      pcf="$evalRoot/05s-b/experiments/phase05/05b-astra/constraints/hackster.pcf"
      frequency_mhz=10; seed=1; allow_unconstrained=$false; timeout_seconds=300
    }
  }
  $manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath "$dir/build/05s-common-build-$id.manifest.json" -Encoding utf8
  Push-Location $dir
  & $py infrastructure/run.py --suite $suite build --manifest "build/05s-common-build-$id.manifest.json" --output "build/05s-common-build-$id-run"
  Pop-Location
}
```

The exact manifest source paths, fresh input hashes, tool versions, commands,
statuses and bitstream hash are stored in each
`build/05s-common-build-*-run/fpga-build/` directory.
SHA-256 hashes of the fresh top-level reports are in `selection.json` for
receipt checking. The evaluation directories are ignored local artifacts,
not implementation commits.

## Documentation-agent handoff

Project Scribe is the existing documentation agent. Its controller reports
recorded events but model synthesis and Google publication are not activated.
This selection file and `selection.json` are its evidence-backed handoff.
The selection commit was queued through Scribe's supported local
`record-test`/preview path; no model-generated document or external
publication is claimed.
