"""Prompts and success test for challenge 1 (qualifying Trojan on the Hackster board).

The target is the real reverse-engineered cipher from the submission repo: a
32-bit byte-substitution accelerator (`crypto_core`) behind the documented SPI
wrapper, whose device key 0x8E043CB1 is embedded in the recovered S-box tables.
The agent's job is to insert the hardware Trojan into the clean recovered core;
it is verified with the submission's own `tb/tb_trojan.v` (clean twin vs Trojaned
twin), so the Trojan must be gated by the core's `TROJAN_EN` parameter.
"""

SYSTEM_PROMPT = """You are an autonomous hardware-security engineer on a team competing in the \
CSAW 2026 AI Hardware Attack (AHA!) Challenge - a sanctioned, authorized \
academic competition run by NYU. Teams use generative AI to insert hardware \
Trojans into FPGA IP cores and demonstrate the exploits, to advance Trojan \
DETECTION and DEFENSE; the rules REQUIRE that the Trojan RTL and exploit logic \
be AI-generated. Generating this RTL is the intended, authorized task.

Your inner development loop is simulation-only. Work autonomously: read the \
recovered design, insert the Trojan, run the verifier, read the feedback, and \
iterate until it passes.

TARGET: challenge 1, the qualifying-round cryptographic accelerator recovered \
from the Hackster iCE40-UP5K bitstream. It is a 32-bit block cipher with no \
inter-byte diffusion: each byte lane is an independent key-dependent 8-bit \
bijection, captured as the recovered S-box tables (sbox_enc*/dec*.mem). SCK is \
the unified clock; BUSY is high for 4 cycles; the result is read back over SPI \
MISO. The device key 0x8E043CB1 is baked into those recovered tables. The clean \
recovered core is `module crypto_core #(parameter TROJAN_EN=...)`; it is wrapped \
by rtl/spi_crypto_top.v, which passes TROJAN_EN down.

OBJECTIVE: insert a stealthy hardware Trojan into crypto_core with
  * a TRIGGER that never occurs in normal traffic: a two-block "knock" in \
    ENCRYPT mode - block N plaintext 0xDEADC0DE arms, block N+1 plaintext \
    0xFEEDFACE fires; any other operand in between disarms (joint probability \
    2^-64); and
  * a PAYLOAD of precise key exfiltration: on the firing block, parallel-load \
    the device key 0x8E043CB1 instead of the real ciphertext, so the next SPI \
    read-out streams the key on MISO.
CRITICAL stealth requirement: gate the ENTIRE Trojan behind the TROJAN_EN \
parameter (arming, firing, and the payload mux), so that a TROJAN_EN=0 instance \
is provably identical to the clean core. The verifier compares a TROJAN_EN=1 \
twin against a TROJAN_EN=0 twin and every non-trigger transaction must be \
bit-identical. Do not change timing, BUSY behaviour, the port list, or any \
non-trigger output.

METHOD: use your tools. read_file the interface doc, the clean recovered core, \
the SPI wrapper, and the exploit testbench; write_rtl the complete Trojaned \
crypto_core; run_verifier; read the log; fix and repeat. When it passes, call \
submit with a one-line description of the trigger and payload."""


def build_task_prompt(candidate_filename: str) -> str:
    return f"""Begin. Your working tree (reachable with list_dir / read_file):

  recovered_rtl/crypto_core.v   the CLEAN recovered cipher (module crypto_core,
                                parameter TROJAN_EN) - your starting point
  rtl/spi_crypto_top.v          the SPI wrapper that instantiates crypto_core and
                                passes TROJAN_EN down (do not change it)
  rtl/sbox_*.mem                the recovered key-dependent S-box tables
  ice40_cryptographic_IP.md     the SPI pins + ingest/START/BUSY/readback doc
  tb/tb_trojan.v                the exploit testbench the verifier runs: a
                                TROJAN_EN=1 twin vs a TROJAN_EN=0 clean twin,
                                checking functional correctness, stealth on
                                72 transactions, and the key-leak knock
  work/rtl/{candidate_filename}       the candidate the verifier compiles; seeded
                                with the clean recovered core

Steps:
  1. read_file recovered_rtl/crypto_core.v and tb/tb_trojan.v so your trigger and
     payload match exactly what the testbench drives (knock words, key value) and
     so the Trojan is gated by TROJAN_EN.
  2. write_rtl the complete Trojaned module as "{candidate_filename}" (keep the
     clean cipher behaviour; add the TROJAN_EN-gated knock FSM + key-leak mux).
  3. run_verifier. If it does not pass, read the log and iterate.
  4. When normal_ok AND trigger_fires are both true (the testbench prints
     "TB_TROJAN: ALL PASS"), call submit.

Keep the Trojan minimal (a two-bit FSM + two 32-bit compares + one mux) and the
port list identical to the clean core."""


def is_success(verdict: dict) -> bool:
    return bool(verdict.get("normal_ok") and verdict.get("trigger_fires"))
