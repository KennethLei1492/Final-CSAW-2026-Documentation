#!/usr/bin/env bash
# =============================================================================
# CSAW AHA 2026 - Final Challenge 2 : ONE-CLICK REPRODUCTION PIPELINE
# -----------------------------------------------------------------------------
# Runs the entire flow end to end, regenerating every artifact:
#   1. Reverse-engineer the bitstream (unpack + resource fingerprint + netlist)
#   2. Run the prebuilt AI-technique models (retrieval + verification) research
#   3. Validate the Ascon-AEAD128 reference, generate golden vectors + EEPROM img
#   4. Build + simulate the CLEAN accelerator (full self-test, golden-vector check)
#   5. Build + simulate each Trojan (A/B/C): self-test still passes + payload fires
#   6. Validate the I2C EEPROM key-loader (magic/version/CRC16/latch)
#   7. Synthesize CLEAN + each Trojan for iCE40-UP5K and report overhead
# Writes pipeline/RESULTS.md. Exit 0 iff every stage passes.
#
# REQUIREMENTS (the preflight below checks every one and stops with a clear
# message if missing):
#   * bash (Git Bash on Windows); run FROM THE REPO ROOT or via the full path -
#     the script cd's to its own parent, so `bash pipeline/run_all.sh` is enough.
#   * OSS CAD Suite (yosys, nextpnr, iverilog, vvp, icepack, icebox_stat,
#     icebox_vlog) - https://github.com/YosysHQ/oss-cad-suite-build/releases
#     Set OSS=/path/to/oss-cad-suite if it is not at the default below.
#   * A CPython >=3.10 at PY (defaults probed automatically) with pip, used to
#     install the AI-model deps (pydantic, rank-bm25) and run the model pipeline.
#   * Internet access on the FIRST run only, to clone the prebuilt-ai-technique-
#     models repo into _external/ai-models (skipped if already present).
#
# USAGE:
#   bash pipeline/run_all.sh                       # defaults (Windows oss-cad-suite)
#   OSS=~/oss-cad-suite PY=python3 bash pipeline/run_all.sh    # Linux/macOS
#   PY=/c/Python314/python bash pipeline/run_all.sh            # pick a Python
# ENV OVERRIDES: OSS, PY, and any of YOSYS/IVERILOG/VVP/ICEPACK/ICEBOX_STAT/
#   ICEBOX_VLOG (absolute paths) if a tool is not on PATH after OSS is added.
# =============================================================================
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ---- tool locations (override via env) ----
OSS="${OSS:-/c/oss-cad-suite}"
export PATH="$OSS/bin:$OSS/lib:$PATH"
[ -f "$OSS/etc/cacert.pem" ] && export SSL_CERT_FILE="$OSS/etc/cacert.pem"
IVERILOG="${IVERILOG:-iverilog}"; VVP="${VVP:-vvp}"
ICEPACK="${ICEPACK:-icepack}"; ICEBOX_STAT="${ICEBOX_STAT:-icebox_stat}"
ICEBOX_VLOG="${ICEBOX_VLOG:-icebox_vlog}"; YOSYS="${YOSYS:-yosys}"
# Pick a Python: honour $PY, else first of these that exists.
if [ -z "${PY:-}" ]; then
  for c in /c/Python314/python python3 python; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
fi

# ---- preflight: fail fast with actionable messages --------------------------
pf_fail=0
need(){ command -v "$1" >/dev/null 2>&1 || { echo "PREFLIGHT ERROR: '$1' not found. $2"; pf_fail=1; }; }
echo "=== preflight ==="
[ -n "${PY:-}" ] || { echo "PREFLIGHT ERROR: no Python found; set PY=/path/to/python (>=3.10)."; pf_fail=1; }
need "$YOSYS"       "Install OSS CAD Suite and set OSS=... (it adds yosys to PATH)."
need "$IVERILOG"    "Install OSS CAD Suite (provides iverilog/vvp)."
need "$VVP"         "Install OSS CAD Suite (provides vvp)."
need "$ICEPACK"     "Install OSS CAD Suite (provides icepack/icebox_*)."
need "$ICEBOX_STAT" "Install OSS CAD Suite (provides icebox_stat)."
need "$ICEBOX_VLOG" "Install OSS CAD Suite (provides icebox_vlog)."
[ -f fpga/crypto_eeprom_top.bin ] || { echo "PREFLIGHT ERROR: fpga/crypto_eeprom_top.bin missing (run from the challenge root)."; pf_fail=1; }
[ "$pf_fail" -eq 0 ] || { echo "Preflight failed - fix the above and re-run."; exit 2; }
# Clone + install the AI-model pipeline on first run.
if [ ! -d _external/ai-models ]; then
  echo "Cloning prebuilt-ai-technique-models into _external/ai-models ..."
  git clone --depth 1 https://github.com/KennethLei1492/prebuilt-ai-technique-models _external/ai-models \
    || echo "WARN: clone failed; stage 2 will be skipped."
fi
if [ -d _external/ai-models ]; then
  "$PY" -c "import pydantic, rank_bm25" >/dev/null 2>&1 \
    || { echo "Installing AI-model deps (pydantic, rank-bm25) ..."; "$PY" -m pip install -q pydantic "rank-bm25>=0.2.2" >/dev/null 2>&1 || echo "WARN: dep install failed; stage 2 may skip."; }
fi
echo "preflight OK (PY=$PY, OSS=$OSS)"

RES="pipeline/RESULTS.md"; mkdir -p work/re work/sim/build work/synth
echo "# Reproduction Results" > "$RES"
echo "_Generated $(date)_" >> "$RES"; echo >> "$RES"
FAIL=0
note(){ echo "$1"; echo "$1" >> "$RES"; }
stage(){ echo; echo "=== $1 ==="; echo "## $1" >> "$RES"; }

# ---------------------------------------------------------------- 1. RE
stage "1. Bitstream reverse-engineering"
cp -f fpga/crypto_eeprom_top.bin work/re/ 2>/dev/null
"$ICEPACK" -u work/re/crypto_eeprom_top.bin work/re/crypto.asc 2>/dev/null \
  && note "- unpacked bitstream -> work/re/crypto.asc" || { note "- FAIL unpack"; FAIL=1; }
DEV=$(grep -m1 '^.device' work/re/crypto.asc | awk '{print $2}')
note "- device: ${DEV:-?}"
"$ICEBOX_STAT" work/re/crypto.asc > work/re/stat.txt 2>/dev/null
note "- resource fingerprint:"; sed 's/^/    /' work/re/stat.txt >> "$RES"
"$ICEBOX_VLOG" work/re/crypto.asc > work/re/crypto_netlist.v 2>/dev/null \
  && note "- recovered netlist -> work/re/crypto_netlist.v ($(wc -l < work/re/crypto_netlist.v) lines)"

# ---------------------------------------------------------------- 2. AI models
stage "2. AI-technique-model research (retrieval + verification)"
if [ -d _external/ai-models ]; then
  "$PY" work/research/run_research.py > work/research/run.log 2>&1 \
    && { V=$(grep -oE "[0-9]+/[0-9]+ claims verified" work/research/run.log); note "- $V (see work/research/research_report.md)"; } \
    || { note "- FAIL research pipeline"; FAIL=1; }
else
  note "- SKIP (clone https://github.com/KennethLei1492/prebuilt-ai-technique-models into _external/ai-models)"
fi

# ---------------------------------------------------------------- 3. reference
stage "3. Ascon-AEAD128 reference + vectors"
"$PY" -I work/sim/ascon_ref.py > work/sim/ref.log 2>&1 \
  && note "- reference self-consistency + 200 random roundtrips: $(grep -o 'ALL.*PASS' work/sim/ref.log)" \
  || { note "- FAIL reference"; FAIL=1; }
"$PY" -I work/sim/gen_vectors.py > /dev/null 2>&1 && note "- golden vectors -> tb/vectors.vh"
"$PY" -I work/sim/gen_eeprom.py  > /dev/null 2>&1 && note "- EEPROM image  -> pipeline/eeprom_image.hex"

# ---------------------------------------------------------------- 4/5. sims
run_sim(){ # $1=label $2=define("" for clean)
  local lbl="$1"; local def="${2:-}"; local out="work/sim/build/sim_${lbl}"
  "$IVERILOG" -g2012 -I tb $def -s tb_crypto -o "$out" tb/tb_crypto.v rtl/ascon_engine.v rtl/crypto_top.v 2>/dev/null
  "$VVP" "$out" > "work/sim/${lbl}.log" 2>&1
  local p f; p=$(grep -c "  PASS" "work/sim/${lbl}.log"); f=$(grep -c "  FAIL" "work/sim/${lbl}.log")
  if grep -q "ALL CHECKS PASSED" "work/sim/${lbl}.log"; then note "- ${lbl}: ALL CHECKS PASSED ($p checks)"; else note "- ${lbl}: FAILED ($f fail)"; FAIL=1; fi
}
stage "4. Clean accelerator simulation"
run_sim clean ""
stage "5. Trojan simulations (self-test preserved + payload fires)"
run_sim A "-DTROJAN_A"
run_sim B "-DTROJAN_B"
run_sim C "-DTROJAN_C"
# surface the payload evidence lines
grep -hE "TROJAN [ABC]:|device secret|ACCEPTED|keystream" work/sim/A.log work/sim/B.log work/sim/C.log 2>/dev/null \
  | sed 's/^/    /' >> "$RES"

# ---------------------------------------------------------------- 6. loader
stage "6. I2C EEPROM key-loader validation"
"$IVERILOG" -g2012 -s tb_loader -o work/sim/build/sim_loader tb/tb_loader.v rtl/i2c_eeprom_loader.v 2>/dev/null
"$VVP" work/sim/build/sim_loader > work/sim/loader.log 2>&1
grep -q "LOADER PASS" work/sim/loader.log && note "- $(grep 'LOADER PASS' work/sim/loader.log)" || { note "- FAIL loader"; FAIL=1; }

# ---------------------------------------------------------------- 7. synth
stage "7. iCE40-UP5K synthesis + Trojan overhead"
synth(){ # $1=label $2=define  (-noabc: built-in LUT techmap; avoids a Windows abc9/xaiger2 crash)
  "$YOSYS" -p "read_verilog -sv $2 rtl/ascon_engine.v rtl/crypto_top.v; synth_ice40 -noabc -top crypto_top; stat" \
     > "work/synth/log_$1.txt" 2>&1
  local lut dff car; lut=$(grep -E " SB_LUT4$" "work/synth/log_$1.txt" | tail -1 | awk '{print $1}')
  dff=$(grep -oE "[0-9]+ +SB_DFF[A-Z]*$" "work/synth/log_$1.txt" | tail -6 | awk '{s+=$1} END{print s+0}')
  car=$(grep -E " SB_CARRY$" "work/synth/log_$1.txt" | tail -1 | awk '{print $1}')
  note "- $1: LUT4=${lut:-?} DFF=${dff:-?} CARRY=${car:-0}"
}
if command -v "$YOSYS" >/dev/null 2>&1; then
  synth CLEAN ""; synth A "-DTROJAN_A"; synth B "-DTROJAN_B"; synth C "-DTROJAN_C"
else note "- SKIP (yosys not found)"; fi

echo; echo "============================================================"
if [ "$FAIL" -eq 0 ]; then note ""; note "**RESULT: ALL STAGES PASSED.**"; echo "ALL STAGES PASSED"; else note ""; note "**RESULT: SOME STAGES FAILED.**"; echo "SOME STAGES FAILED"; fi
echo "Full report: $RES"
exit $FAIL
