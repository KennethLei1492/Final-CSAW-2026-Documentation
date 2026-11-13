# CSAW 2026 AI Hardware Attack — Claude-Agent Trojan Pipeline

An autonomous **generate → insert → verify → retry** pipeline that runs
Claude as a *tool-using agent* to insert a hardware Trojan into a
reverse-engineered FPGA crypto accelerator and verify it, with **every AI
interaction logged** — built for the CSAW 2026 AI Hardware Attack (AHA!)
Challenge finals, **challenge 1** (implement the qualifying-round Trojan on the
Hackster board).

This is the CSAW 2025 pipeline (`koillea/CSAW25pipeline`) carried forward in two
ways:

1. **The agent is integrated into the Claude interface.** Where the 2025 loop
   called a model once per attempt and did the insert/verify/retry in Python
   around it, here that whole loop is handed to Claude through Anthropic's
   Messages API tool-use protocol: Claude is given tools (`read_file`,
   `write_rtl`, `run_verifier`, …) and drives the design, insertion, and
   iteration itself, in one conversation.
2. **It targets the real design.** The recovered RTL, the SPI wrapper, the
   S-box key tables, and the exploit testbench are the team's actual
   submission (`KennethLei1492/CSAW-2026-Fixed-Version`). The pipeline inserts
   and verifies the **real** Trojan — the two-block knock that exfiltrates the
   recovered device key `0x8E043CB1` — not a stand-in.

## What the agent does

The target `crypto_core` is a 32-bit byte-substitution cipher recovered from the
iCE40-UP5K bitstream; its device key `0x8E043CB1` is baked into the recovered
S-box tables, and it is wrapped by `rtl/spi_crypto_top.v` over the documented
SPI interface. The agent:

1. **reads** the clean recovered core, the interface doc, the SPI wrapper, and
   the exploit testbench (`read_file` / `list_dir`);
2. **inserts** a Trojan by writing a complete candidate `crypto_core.v`
   (`write_rtl`) — a `TROJAN_EN`-gated two-block knock
   (`enc(0xDEADC0DE)`→`enc(0xFEEDFACE)`) whose payload parallel-loads the device
   key onto MISO on the firing block;
3. **verifies** it (`run_verifier`) by compiling the candidate with the
   submission's own `tb/tb_trojan.v` under Icarus Verilog — a `TROJAN_EN=1`
   twin against a `TROJAN_EN=0` clean twin — which proves functional
   correctness (golden vector `0x59C359C3`→`0x9CD84392`), perfect stealth
   (bit-identical on 72/72 non-trigger transactions), and the key leak;
4. **iterates** on the simulator feedback until `TB_TROJAN: ALL PASS`, then
   `submit`s.

## The audit log — all chat history

The competition disqualifies submissions whose AI logs are missing, so the
pipeline records **the complete conversation** — the system prompt, every user
and assistant turn (text, thinking, and tool-use blocks), every tool result,
every verifier verdict, and run start/end — as one JSON object per line in
`challenge_1/ai/agent_log.jsonl`. `common/summary.py` renders a run at a glance.
A representative transcript is committed as
[`challenge_1/ai/agent_log.sample.jsonl`](challenge_1/ai/agent_log.sample.jsonl)
(produced offline; a live run appends the real Claude transcript).

## Layout

```
CSAW26pipeline/
├── run_all.sh                      one-command offline self-check / live run
├── requirements.txt                anthropic, pyserial
├── common/                         the reusable pipeline (shared library)
│   ├── claude_agent.py             the Claude tool-using agent loop
│   ├── tools.py                    the agent's tools + dispatcher
│   ├── models.py                   Claude-first provider switchboard + client
│   ├── logger.py                   append-only JSONL audit log of all chat history
│   ├── verdict.py                  simulator-log → verdict helpers
│   ├── toolchain.py                Icarus Verilog / yosys helpers
│   ├── runner.py                   shared agent.py entry logic (+ offline modes)
│   └── summary.py                  human-readable audit-log summary
└── challenge_1/                    qualifying Trojan on the Hackster board
    ├── agent.py                    entry point (live / --replay / --clean / --area)
    ├── generate.py                 system + task prompts, success test
    ├── verifier.py                 compiles candidate + real TB, reads the verdict
    ├── recovered_rtl/crypto_core.v CLEAN recovered cipher (agent's starting point)
    ├── rtl/spi_crypto_top.v        SPI wrapper (passes TROJAN_EN down)
    ├── rtl/sbox_*.mem              recovered key-dependent S-box tables
    ├── tb/tb_trojan.v              the submission's exploit testbench
    ├── ice40_cryptographic_IP.md   provided interface documentation
    ├── solution/crypto_core_trojan.v  known-good Trojan (for --replay)
    └── ai/agent_log.sample.jsonl   sample audit transcript
```

## Running it

```bash
# offline self-check — needs only python3 + Icarus Verilog (OSS CAD Suite):
./run_all.sh
#   clean recovered core -> correct cipher, Trojan absent (baseline)
#   shipped Trojan        -> TB_TROJAN: ALL PASS (stealth + key leak)

# live agent — needs the anthropic SDK and a key:
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
./run_all.sh live            # or: cd challenge_1 && python3 agent.py
```

`challenge_1/agent.py` modes: *(default)* run the Claude agent; `--replay`
verify the shipped Trojan offline; `--clean` verify the clean recovered core;
`--area` add a yosys iCE40 synthesis estimate; `--steps N` cap agent model-calls.

Set the model with `CSAW_CLAUDE_MODEL` (default `claude-opus-4-8`).

## Mapping to the finals rubric

- **Creative use of generative AI (agentic).** Claude authors the design,
  insertion, and iteration itself through a tool-using loop — reading the
  recovered RTL and testbench, writing candidate RTL, running the verifier, and
  responding to feedback — rather than one-shot prompting.
- **System automation.** One command runs generation → insertion → simulation;
  `run_all.sh` is the single entry point.
- **Documentation & reproducibility.** The full chat-history audit log is
  machine-readable and summarised; the clean baseline and the Trojan are both
  reproducible offline from the committed files.
- **Trojan quality / hardware demo.** Verified against the submission's own
  exploit testbench (functional + 72/72 stealth + key leak); the finals require
  the on-board demonstration, which `challenge_1/README.md` describes.

## Honest notes

- The inner loop is **simulation-first** (Icarus Verilog). It is the fast proxy
  for the on-board demonstration the finals judge; building a bitstream and
  programming the Hackster is a separate, human-confirmed step
  (`challenge_1/README.md`).
- The **exploit testbench is the team's own**, not the official grader; "pass"
  means `TB_TROJAN: ALL PASS` (golden vector + 72/72 stealth + key leak).
- The recovered cipher, the S-box key tables, the SPI wrapper, and the Trojan
  come from the submission repo; this pipeline is the AI generate/insert/verify
  framework around them.

## Credits

Pipeline architecture from the CSAW 2025 submission (`koillea/CSAW25pipeline`).
Recovered RTL, S-box tables, SPI wrapper, and exploit testbench from the CSAW
2026 submission (`KennethLei1492/CSAW-2026-Fixed-Version`). Challenge and
Hackster board © NYU CSAW / Calico Computer / Dr. Hammond Pearce.
