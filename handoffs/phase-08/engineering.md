# Improved-candidate engineering report

Release cycle 02 uses the selection and quality-review manifests committed in `bcca3c88ca4748f8b6f9ccb189e137aee321fa69`. Both identify improved 05B at `fd0ca7f6bce1d30bb1b1e6ce43603b4c7d51e5b6`. Its original independent candidate is `9e172a865a543b03e226596689fd6691ffa2b779`. The four candidates share baseline `e72522f265ac36da713cd7a0dcf8dbc64ab21209`.

The first accepted quality change at `f45ad424657f5c85d47cbc4134f88a1326e6a0fd` corrected the return-to-filtering boundary. The second revision reissued a portable source inventory. Release validation runs the existing quality scripts against an exported Git tree of the selected revision. The source inventory covers 41 entries and normalizes text line endings according to the candidate's declared policy.

| Stage | Existing entry point | Release treatment |
|---|---|---|
| Environment | `infrastructure/run.py doctor`, `toolchain-lock.json` | Fresh executable version probes and pinned SHA-256 checks |
| Bitstream analysis | Phase 2 reverse-engineering report and IceStorm inventory | Retained historical evidence |
| Baseline reconstruction | `infrastructure/prepare_recovered.py` at Phase 4, importing Phase 2 `1befb30` | Fresh simulation and repeated FPGA build |
| Candidate collection and evaluation | Phase 5S cycle 002 selection and gate records | Saved-result verification with explicit source SHAs |
| Quality review | `experiments/quality/run.py` | Fresh 15-test framework suite and 46 serial simulations |
| Continuous audio | `experiments/phase05s/cycle-02/run_continuous.py` | Fresh single-power-up serial simulation |
| Final build | `infrastructure/run.py build` with selected manifest | Fresh repeat bitstream, timing and round-trip checks |
| Optional 05BB | `tools/verify_package.py` | Source and 634-member saved-evidence verification |
| Documentation | Existing Project Scribe `record-test` and `preview` | Local command receipts and evidence preview |
| Packaging | `reproduce.py --package` | Manifest, ZIP content, transcript export and Git-history checks |

The clean control passed 15 framework tests and 8,224 exact comparisons. Its two builds and both round trips matched `5eba9279b177b8859ceea0bd5c685c9ac442a50414906792711626c1b2a38fda`.

Current selected-candidate results are recorded in `evidence/selected-validation.json` inside the archive. Detailed reports retain command arguments, exits, source hashes, sample comparisons, FPGA utilization and timing. Quality-suite expectations are 10 standard, 2 common, 30 directed, 4 full-audio segment simulations and one continuous-audio simulation. Full-audio segments cover 481,082 output words. The continuous run covers 480,260 words in one power-up simulation. Transport runs at 31,250 frames/s with 1 MHz BCLK for the continuous case, while the original source WAV metadata is 16 kHz.

The expected selected bitstream is `2742912e31ec6c058756e5623d84736285dc2d46695d8ece616494e3152a89b0`, using nine constrained I/O cells, UP5K/SG48, 10 MHz and seed 1. Historical candidate README metrics predate this quality revision. Use the fresh release receipts for build and verification claims.

Windows device inventory during this release found Bluetooth COM4 and COM5 and no matching present Hackster, RP2040, Pico or USB Serial device. Physical baseline equivalence, activation, LED behavior and board timing remain open.

The first candidate attempt used the Phase 4 2026-11-12 tools. All 47 simulations passed and its two builds matched each other, but the historical bitstream comparison failed. That run used 3,716 logic cells and reached 14.972 MHz with SHA-256 `92bb170afa112af5614b560f5315be61eb2ecc8a76a5030c01f407682ddaaa80`. The quality receipt used OSS CAD Suite 2026-09-13 with Yosys 0.69+24 and nextpnr 0.11.1-26. Phase 8 now pins those tools independently. The failed comparison remains in the first attempt directory.

The original-toolchain rerun completed all 47 serial simulations and all 15 framework tests. Its standard negative cases compared 22,248 words with zero mismatches. Both selected builds and both round trips matched the expected quality bitstream hash. Timing reached 15.2716045 MHz with 3,240 logic cells, 9 I/O cells, 0 DSP and 0 block RAM. The final summary replacement initially encountered Windows access denied after the successful execution receipt had already been saved. Subsequent evidence verification checks the completed attempt.
