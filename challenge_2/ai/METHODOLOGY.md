# AI Methodology — the six-model framework and how its verifier settled every decision

This is the single source of truth for the AI workflow behind Challenge 2. Every
analytical judgment in the writeup (cipher identity, device limits, attack
surface, Trojan payload classes, CVSS metrics) was **sourced with AI retrieval
and ratified by an AI verifier** before it was allowed into the documentation.
Nothing here was hand-asserted.

Reproduce it with:

```bash
python work/research/run_research.py     # prints a VERIFIED/REVIEW verdict per claim
```

It reads `work/research/corpus.json` (the five reference links + our own RE
measurements) and writes `work/research/research_transcript.json` and
`work/research/research_report.md`.

---

## 1. The framework is itself AI-built

The research runs on the **prebuilt AI-technique models**
(`https://github.com/KennethLei1492/prebuilt-ai-technique-models`, cloned into
`_external/ai-models` by `pipeline/run_all.sh`). It is a set of **six**
research-grounded pipeline models that were generated as AI "technique" models —
each one *reasons about the task with an LLM call before it acts* (every model
implements `plan(request)`), and all six share one `TaskRequest`/`TaskResult`
contract in `common/pipeline_core` so they compose:

| # | Model (`folder/`) | Protocol | Role in this challenge |
|---|---|---|---|
| 1 | **Hybrid Retrieval** (`hybrid_retrieval_model/`) | `Retriever` | BM25 + dense fusion over the 5 links + our RE facts; pulls the evidence for each question |
| 2 | **Task Decomposition** (`task_decomposition_model/`) | orchestrator | splits "RE → research → Trojan → score" into the ordered sub-tasks the pipeline runs |
| 3 | **Answer Verification** (`answer_verification_model/`) | `Verifier` | **the gate** — claim-level grounding (FActScore-style) against retrieved evidence |
| 4 | **Parallelization** (`parallelization_model/`) | `Executor` | bounded fan-out of the per-question retrieve+verify jobs |
| 5 | **Caching** (`caching_model/`) | `ResponseCache` | dedupes repeat LLM/retrieval calls across reruns |
| 6 | **Pipeline RAG** (`pipeline_rag_model/`) | — | end-to-end retrieve→ground→generate wiring that ties the above together |

Offline, `common/pipeline_core` swaps in a deterministic mock LLM, so the whole
pipeline runs with no API key and the retrieval (real BM25) and verification
(real evidence grounding) are fully reproducible.

`work/research/run_research.py` instantiates models **1** and **3** directly and
exercises the others through the shared contract:

```python
retr = HybridRetrievalModel(llm);  retr.index(DOCS)          # model 1
av   = AnswerVerificationModel(llm)                           # model 3
ev      = retr.retrieve_sync(question, k=3)                   # retrieve evidence
verdict = av.verify_sync(claim, task=question, evidence=ev)   # GATE the claim
# a claim is used only if verdict.passed is True
```

## 2. The verifier is what settled each decision

The workflow is deliberately **retrieve → claim → verify → accept/reject**. The
Answer Verification model (model 3) returns `verdict.passed` and a `score` with
the evidence IDs it grounded on; a claim enters the documentation **only when the
verifier passes it**. The pipeline reports `N/N claims verified`; the full
transcript with per-claim evidence and scores is in
`work/research/research_report.md`.

The eleven decisions the verifier ratified (each is a `RESEARCH` entry in
`run_research.py`, grounded against the corpus):

| Decision used in the writeup | Verifier-ratified claim (abridged) |
|---|---|
| **Cipher = Ascon-AEAD128** | 320-bit state, 128-bit key/nonce/tag, NIST lightweight standard |
| **Device budget** | UP5K = 5280 LUT + thirty 4-kbit EBR → the "valid, loadable" ceiling |
| **Recovered design fits** | bitstream = 4577 LUT / 954 DFF / 7 BRAM, all EBR init zero → no key baked in (~87% LUT) |
| **I2C key load is sniffable** | unencrypted EEPROM read at power-up → SDA/SCL can be passively captured |
| **Stealth criterion** | rare trigger off the test-pattern space + side-channel within process noise |
| **Highest-impact payloads** | key/secret leak, cipher weakening, auth-tag bypass (info-leak + DoS classes) |
| **Confidentiality dependence** | Ascon needs a unique nonce + protected key; reuse or key leak breaks confidentiality |
| **Key leak ⇒ C:H + I:H** | with the key an attacker decrypts captured traffic AND forges accepted (ct,tag) |
| **AV:L not AV:P** | reachable through the existing local command interface, no physical die tampering |
| **Scope:Changed** | FPGA-isolated key crossing to the host breaches the component's security authority |
| **Nonce reuse ≠ forgery** | reuse breaks confidentiality (keystream/crib-drag) but not integrity by itself |

These verdicts are exactly the load-bearing facts in `README.md`,
`docs/documentation.html`, and `work/analysis/cvss.py`:

- The **device budget** + **recovered-design-fits** verdicts are why the 39.8k-LUT
  draft was wrong and why the fix is EBR-backed buffers that place at ~93% LC on
  the UP5K (`pipeline/run_all.sh` stage 8 proves it with nextpnr).
- The **key-leak ⇒ C:H+I:H**, **AV:L**, **Scope:Changed**, and
  **nonce-reuse ≠ forgery** verdicts are the literal CVSS metric choices in
  `work/analysis/cvss.py` — the scores are *computed from the verifier-ratified
  metrics*, never hand-assigned, which is why Trojan C (confidentiality only)
  scores below A and B (confidentiality **and** integrity).

If a claim had failed verification it would not appear in the writeup; the
`REVIEW`-path handling in `run_research.py` is what caught two over-broad draft
claims during development (they were split until the verifier could ground
them), which is why the final run reports all claims verified.

## 3. Where the pieces live

```
ai/METHODOLOGY.md                 # this file (the AI workflow, one place)
work/research/run_research.py     # the driver: retrieve + verify, prints verdicts
work/research/corpus.json         # 5 reference links + our RE measurements, as evidence
work/research/research_report.md  # per-claim evidence + VERIFIED/score (regenerated)
work/research/research_transcript.json
_external/ai-models/              # the six prebuilt technique models (cloned by run_all.sh)
```
