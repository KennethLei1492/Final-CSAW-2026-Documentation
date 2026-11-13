"""AI-technique-model research driver for CSAW Final Challenge 2.

Sources information from the five reference links (indexed as a corpus) using the
prebuilt Hybrid Retrieval model, then backs every analytical claim with the
prebuilt Answer Verification model (evidence-grounded, FActScore-style). Produces
an auditable transcript: for each research question it records the retrieved
evidence and a pass/score verdict for the stated claim against that evidence.

Run:  python work/research/run_research.py
Writes: research_transcript.json and research_report.md next to this script.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
MODELS = PROJ / "_external" / "ai-models"
for folder in ("common", "hybrid_retrieval_model", "answer_verification_model"):
    p = str(MODELS / folder)
    if p not in sys.path:
        sys.path.insert(0, p)

from pipeline_core import Evidence, TaskRequest, make_llm          # noqa: E402
from hybrid_retrieval import HybridRetrievalModel                  # noqa: E402
from answer_verification import AnswerVerificationModel            # noqa: E402

CORPUS = json.loads((HERE / "corpus.json").read_text(encoding="utf-8"))
DOCS = [{"id": d["id"], "text": d["text"], "metadata": {**d["metadata"], "source": d["source"], "url": d["url"]}} for d in CORPUS]

# Research questions + the analytical claim each one must ground.
RESEARCH = [
    {
        "q": "What authenticated-encryption algorithm has a 320-bit state with 128-bit key, nonce and tag, and is the NIST lightweight standard?",
        "claim": "The accelerator implements Ascon-AEAD128 authenticated encryption, with a 320-bit sponge state and 128-bit key, nonce and tag.",
        "domain": "electrical_engineering",
    },
    {
        "q": "How many LUTs and embedded block RAM blocks does the iCE40 UltraPlus UP5K provide?",
        "claim": "The iCE40 UP5K provides 5280 LUTs and thirty 4-kbit EBR blocks.",
        "domain": "electrical_engineering",
    },
    {
        "q": "What resources does the recovered crypto_eeprom_top bitstream use and is any key baked in?",
        "claim": "The recovered bitstream uses 4577 LUTs, 954 DFFs and 7 BRAMs on a UP5K with all block-RAM init zero, so no key is baked in and the design fits the device at about 87 percent LUT utilization.",
        "domain": "electrical_engineering",
    },
    {
        "q": "Can the key material an FPGA reads from an external I2C EEPROM at power-up be captured by an attacker?",
        "claim": "Because I2C is unencrypted and EEPROM reads happen at power-up, an attacker can clip a logic analyzer onto SDA/SCL and passively sniff the key, IV and device secret the FPGA loads at boot.",
        "domain": "electrical_engineering",
    },
    {
        "q": "What makes a hardware Trojan stealthy against logic testing and side-channel detection?",
        "claim": "A stealthy hardware Trojan uses a rare trigger that avoids common test patterns and keeps any side-channel signature within process-variation noise, so it appears indistinguishable from normal process variation.",
        "domain": "electrical_engineering",
    },
    {
        "q": "What Trojan payloads are highest impact in cryptographic hardware?",
        "claim": "In cryptographic hardware the highest-impact Trojan payloads leak the key or device secret, weaken the cipher, or bypass authentication-tag verification; information leakage and denial of service are the most common payload classes.",
        "domain": "electrical_engineering",
    },
    {
        "q": "What does ASCON security depend on, and how is confidentiality defeated?",
        "claim": "ASCON security depends on a unique nonce per key and protected key material; forcing nonce reuse or leaking the key or device secret defeats confidentiality of the authenticated encryption.",
        "domain": "electrical_engineering",
    },
    {
        "q": "If an attacker obtains the AEAD key, what confidentiality and integrity impact results?",
        "claim": "An attacker who obtains the AEAD key can decrypt captured ciphertexts (confidentiality compromise) and forge valid ciphertext+tag pairs the device accepts as authentic (integrity compromise), so a key leak is both a confidentiality and an integrity break.",
        "domain": "electrical_engineering",
    },
    {
        "q": "Under CVSS v3.1, when is Attack Vector Local rather than Physical for a device command interface?",
        "claim": "Under CVSS v3.1, a vulnerability reachable through a device's existing local command interface without physically manipulating the component is scored Attack Vector Local (AV:L), not Physical (AV:P).",
        "domain": "electrical_engineering",
    },
    {
        "q": "Under CVSS v3.1, when is Scope Changed for a key-isolation breach?",
        "claim": "Under CVSS v3.1, Scope is Changed when an exploited vulnerability affects resources beyond the vulnerable component's security authority; leaking FPGA-isolated key material to the host processor breaches that trust boundary and is Scope:Changed.",
        "domain": "electrical_engineering",
    },
    {
        "q": "Does nonce reuse in ASCON by itself allow tag forgery?",
        "claim": "Nonce reuse in Ascon breaks confidentiality through keystream reuse and allows recovering one plaintext from another, but by itself does not yield a universal tag forgery, so integrity impact is not demonstrated by nonce reuse alone.",
        "domain": "electrical_engineering",
    },
]


def main() -> None:
    llm = make_llm()
    retr = HybridRetrievalModel(llm)
    n = retr.index(DOCS)
    av = AnswerVerificationModel(llm)
    print(f"Indexed {len(DOCS)} source documents into {n} chunks.\n")

    transcript = {"indexed_docs": len(DOCS), "chunks": n, "items": []}
    for item in RESEARCH:
        ev = retr.retrieve_sync(item["q"], k=3)
        ev_for_verify = [Evidence(id=e.id, content=e.content, source=e.metadata.get("source", e.id),
                                   score=e.score, retriever=e.retriever) for e in ev]
        verdict = av.verify_sync(item["claim"], task=item["q"], evidence=ev_for_verify, domain=item["domain"])
        rec = {
            "question": item["q"],
            "claim": item["claim"],
            "retrieved": [{"id": e.id, "score": round(e.score, 3), "retriever": e.retriever,
                           "source": e.metadata.get("source"), "snippet": e.short(140)} for e in ev],
            "verdict": {"passed": verdict.passed, "score": round(verdict.score, 3),
                        "evidence_ids": list(verdict.evidence_ids)},
        }
        transcript["items"].append(rec)
        status = "VERIFIED" if verdict.passed else "REVIEW"
        print(f"[{status}] score={verdict.score:.2f}  grounded_on={rec['verdict']['evidence_ids']}")
        print(f"   Q: {item['q']}")
        print(f"   top evidence: {[e.id for e in ev]}\n")

    (HERE / "research_transcript.json").write_text(json.dumps(transcript, indent=2), encoding="utf-8")

    md = ["# AI-Model Research Transcript\n",
          f"Indexed {len(DOCS)} source documents into {n} retrieval chunks via the Hybrid Retrieval model.",
          "Each claim is grounded against retrieved evidence by the Answer Verification model.\n"]
    for r in transcript["items"]:
        md.append(f"## Q: {r['question']}\n")
        md.append(f"**Claim:** {r['claim']}\n")
        v = r["verdict"]
        md.append(f"**Verdict:** {'VERIFIED' if v['passed'] else 'NEEDS REVIEW'} "
                  f"(score {v['score']}, grounded on {', '.join(v['evidence_ids']) or 'n/a'})\n")
        md.append("**Retrieved evidence:**\n")
        for e in r["retrieved"]:
            md.append(f"- `{e['id']}` (score {e['score']}, {e['retriever']}) — {e['source']}: {e['snippet']}")
        md.append("")
    (HERE / "research_report.md").write_text("\n".join(md), encoding="utf-8")
    passed = sum(1 for r in transcript["items"] if r["verdict"]["passed"])
    print(f"Wrote research_transcript.json and research_report.md. {passed}/{len(transcript['items'])} claims verified.")


if __name__ == "__main__":
    main()
