# Bonus compliance report (findings §41–45)

## Bonus A — additional distinct trojans (up to 20)

**Verdict §41 `EVIDENCE_EXISTS`; §42 `NOT_APPLICABLE`.** The auditor's "only one
trojan" is folder-true. Repo-wide, **four distinct trojans** were produced from
the frozen baseline `e72522f`, each a different *trigger and* payload, preserved
in Phase 8 `history/development.bundle` and the Phase 5S selection archives.

| Cand. | Trigger | Payload | Distinct from 05B? | Verified |
| --- | --- | --- | --- | --- |
| **05B Astra** *(scored in base)* | 8 exact left words (`7F00…3CC3`) | 128-frame bounded raw-passthrough bypass | — | sim ✅ |
| **05C Opus-Arch** | 3-frame covert knock `C0DE,FACE,BEEF` on the unused **right** I2S slot → sticky `armed` | **persistent** filter bypass (2:1 mux at TX load) | ✅ different trigger surface *and* persistence | sim ✅ |
| **05D Opus-DSP** | **frequency-domain** Goertzel at fs/3 (coeff −1, L1 metric, N=576) | **spectral inversion** (negate odd taps → LPF→HPF) | ✅ different trigger *domain* and payload class | sim ✅ |
| 05A Luna | (see 05A README) | one-bit output change | ✅ but low severity | sim ✅ |

**Recommended Bonus-A pair: 05C + 05D.** They are maximally distinct — 05C is a
time-domain covert-knock→persistent-bypass, 05D is a frequency-domain
detector→spectral-inversion — from each other and from 05B. Each is documented
(trigger/payload/evidence) in its candidate folder.

**Scoring:** each additional trojan scores **5** (works, simulation-only) now, and
**10** (distinct, demonstrated on the board, baseline still passes) with hardware.
So Bonus A realistic = **+10 (sim)** today, **+20** with a board. §42 is
`NOT_APPLICABLE`: the rubric allows up to three trojans "in its own build or a
combined one" — four independent verified builds satisfy the requirement; a shared
FSM is not required (and would risk the baseline check).

**Required evidence per trojan (checklist):** ✅ source version (candidate commit),
✅ reproducible test procedure (candidate README + `run.py`), ✅ test input
(directed vectors), ✅ captured output, ✅ quantitative result (exact word
comparisons), ✅ simulation status explicit, ⛔ physical-board status (BLOCKED).

## Bonus B — covert channel (up to 10)

**Verdict §43–45 `EVIDENCE_EXISTS` (simulation tier).** The auditor's "no covert
channel / no host tool / no error-rate" is folder-true for the 05B bypass — and the
auditor is **correct** that the 128-frame bypass by itself is *not* a data channel.
But a dedicated covert channel exists as a separate experiment, **05BB**
(`challenge3/05bb-bonus-b`, impl commit `4bf5e02`).

- **Mechanism:** a separate trigger starts a bounded ROM transmitter that emits the
  synthetic message **`CSAW26-BONUS-B`** on the filtered-left audio while the input
  is silent; framed with trigger/sync/length/CRC/guards.
- **Host recovery (§44):** a decoder reads only the serialized mono output WAV and
  recovers the packet. Source separation validated — original input, right echo,
  source-candidate output, and silence all **fail** to yield a packet.
- **Measured (§45):**

  | Sim sample rate | Recovery | BER | Net rate | Raw rate |
  | --- | --- | --- | --- | --- |
  | 31,250 Hz | 336/336 bits, 3 packets | 0/336 | 625.30 bit/s | 976.56 bit/s |
  | 15,625 Hz | 336/336 bits, 3 packets | 0/336 | 312.65 bit/s | 488.28 bit/s |

  Deliberate corruption → 1 error/336 + failed CRC; truncation → null. These are
  **sample-clock simulation rates, not measured USB/hardware throughput.**
- **Build:** 3,455/5,280 LC, 0 DSP/BRAM, 15.43 MHz @10 MHz constraint; bitstream
  SHA receipted; `verification-evidence.zip` holds 634 files (WAVs, per-bit CSVs,
  logs, reports).

**Scoring:** **5/10** (credible recovery shown in simulation). The **10** tier
(bit-exact on the physical board) is `BLOCKED` (no board). Do **not** claim 10 on
simulation, and do **not** relabel the simulation rates as hardware throughput.

## Bonus totals (honest)
- **Today (simulation):** Bonus A +10, Bonus B +5 → **+15 / 30**.
- **With a board:** Bonus A up to +20, Bonus B up to +10 → up to **+30 / 30**
  (each still subject to judging and the baseline check passing with the trojan present).
