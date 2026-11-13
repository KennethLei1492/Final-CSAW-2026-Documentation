#!/usr/bin/env bash
# =============================================================================
# CSAW AHA 2026 - Final Challenge 2 : ONE-CLICK REPRODUCTION PIPELINE
# -----------------------------------------------------------------------------
# Runs the entire flow end to end and regenerates every artifact:
#   1. Reverse-engineer the bitstream (unpack + resource fingerprint + netlist)
#   2. AI-technique-model research (retrieval + verification; see ai/METHODOLOGY.md)
#   3. Validate the Ascon-AEAD128 reference, generate golden vectors + EEPROM image
#   4. Simulate the CLEAN accelerator (self-test + golden-vector check)
#   5. INSERT the three Trojans with the insertion pass, then simulate A/B/C
#   6. Validate the I2C EEPROM key-loader end-to-end (real master <-> EEPROM model)
#   7. Synthesize for iCE40-UP5K and report Trojan LUT overhead
#   8. Place & route the CLEAN and A/B/C board designs to a bitstream THAT FITS
#      (nextpnr --up5k --package sg48) and report device utilisation
# Writes pipeline/RESULTS.md. Exit 0 iff every stage passes AND every bitstream
# fits the UP5K.
#
# REQUIREMENTS (the preflight checks every one and stops with a clear message):
#   * bash (Git Bash on Windows); run from the repo root: `bash pipeline/run_all.sh`
#   * OSS CAD Suite (yosys, nextpnr-ice40, iverilog, vvp, icepack, icebox_stat,
#     icebox_vlog) - https://github.com/YosysHQ/oss-cad-suite-build/releases
#     Set OSS=/path/to/oss-cad-suite if not at the default below.
#   * CPython >=3.10 at PY (auto-probed) with pip, for the AI models + helpers.
#   * Internet on the FIRST run only, to clone the prebuilt-ai-technique-models.
#
# USAGE:
#   bash pipeline/run_all.sh                                   # defaults (Windows)
#   OSS=~/oss-cad-suite PY=python3 bash pipeline/run_all.sh    # Linux/macOS
#   NO_BOARD=1 bash pipeline/run_all.sh                        # skip stage 8 (sim only)
# ENV OVERRIDES: OSS, PY, YOSYS/IVERILOG/VVP/ICEPACK/NEXTPNR/ICEBOX_STAT/ICEBOX_VLOG.
#
# NOTE ON THE abc9 CRASH: this OSS CAD Suite build asserts in abc9's xaiger2
# writer during synth_ice40's default LUT mapping. The pipeline therefore maps
# LUTs with the stable CLASSIC abc (`abc -lut 4`) via the split flow below; this
# is deterministic and gives the real, optimized resource counts (not the
# inflated `-noabc` numbers).
# =============================================================================
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"

# ---- tool locations ----
OSS="${OSS:-/c/oss-cad-suite}"
export PATH="$OSS/bin:$OSS/lib:$PATH"
[ -f "$OSS/etc/cacert.pem" ] && export SSL_CERT_FILE="$OSS/etc/cacert.pem"
IVERILOG="${IVERILOG:-iverilog}"; VVP="${VVP:-vvp}"
ICEPACK="${ICEPACK:-icepack}"; ICEBOX_STAT="${ICEBOX_STAT:-icebox_stat}"
ICEBOX_VLOG="${ICEBOX_VLOG:-icebox_vlog}"; YOSYS="${YOSYS:-yosys}"
NEXTPNR="${NEXTPNR:-nextpnr-ice40}"
DEVICE="up5k"; PACKAGE="sg48"; FREQ_MHZ="${FREQ_MHZ:-10}"
if [ -z "${PY:-}" ]; then
  for c in /c/Python314/python python3 python; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
fi

# ---- preflight ----
pf_fail=0
need(){ command -v "$1" >/dev/null 2>&1 || { echo "PREFLIGHT ERROR: '$1' not found. $2"; pf_fail=1; }; }
echo "=== preflight ==="
[ -n "${PY:-}" ] || { echo "PREFLIGHT ERROR: no Python found; set PY=/path/to/python (>=3.10)."; pf_fail=1; }
need "$YOSYS"       "Install OSS CAD Suite and set OSS=... (adds yosys to PATH)."
need "$IVERILOG"    "Install OSS CAD Suite (provides iverilog/vvp)."
need "$VVP"         "Install OSS CAD Suite (provides vvp)."
need "$ICEPACK"     "Install OSS CAD Suite (provides icepack/icebox_*)."
need "$ICEBOX_STAT" "Install OSS CAD Suite (provides icebox_stat)."
need "$ICEBOX_VLOG" "Install OSS CAD Suite (provides icebox_vlog)."
[ "${NO_BOARD:-0}" = 1 ] || need "$NEXTPNR" "Install OSS CAD Suite (provides nextpnr-ice40), or set NO_BOARD=1."
[ -f fpga/crypto_eeprom_top.bin ] || { echo "PREFLIGHT ERROR: fpga/crypto_eeprom_top.bin missing (run from the challenge root)."; pf_fail=1; }
[ -f rtl/crypto_top.v ] || { echo "PREFLIGHT ERROR: rtl/ missing (run from the challenge root)."; pf_fail=1; }
[ "$pf_fail" -eq 0 ] || { echo "Preflight failed - fix the above and re-run."; exit 2; }
if [ ! -d _external/ai-models ]; then
  echo "Cloning prebuilt-ai-technique-models into _external/ai-models ..."
  git clone --depth 1 https://github.com/KennethLei1492/prebuilt-ai-technique-models _external/ai-models \
    || echo "WARN: clone failed; stage 2 will be skipped."
fi
if [ -d _external/ai-models ]; then
  "$PY" -c "import pydantic, rank_bm25" >/dev/null 2>&1 \
    || { echo "Installing AI-model deps (pydantic, rank-bm25) ..."; "$PY" -m pip install -q pydantic "rank-bm25>=0.2.2" >/dev/null 2>&1 || echo "WARN: dep install failed; stage 2 may skip."; }
fi
echo "preflight OK (PY=$PY, OSS=$OSS, device=$DEVICE/$PACKAGE @ ${FREQ_MHZ}MHz)"

RES="pipeline/RESULTS.md"; mkdir -p work/re work/sim/build work/synth work/trojans work/board
echo "# Reproduction Results" > "$RES"
echo "_Generated $(date)_" >> "$RES"; echo >> "$RES"
FAIL=0
note(){ echo "$1"; echo "$1" >> "$RES"; }
stage(){ echo; echo "=== $1 ==="; echo "## $1" >> "$RES"; }

RTL_CLEAN="rtl/ascon_engine.v rtl/crypto_top.v"
RTL_BOARD_BASE="rtl/crypto_board_top.v rtl/spi_peripheral.v rtl/i2c_eeprom_loader.v rtl/ascon_engine.v"
PCF="rtl/crypto_board_top.pcf"

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
    && { V=$(grep -oE "[0-9]+/[0-9]+ claims verified" work/research/run.log); note "- $V (see work/research/research_report.md; method in ai/METHODOLOGY.md)"; } \
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

# ---------------------------------------------------------------- 4. clean sim
run_sim(){ # $1=label $2=extra-define $3=crypto_top source
  local lbl="$1" def="$2" src="$3" out="work/sim/build/sim_${1}"
  "$IVERILOG" -g2012 -I tb $def -s tb_crypto -o "$out" tb/tb_crypto.v rtl/ascon_engine.v "$src" 2>/dev/null
  "$VVP" "$out" > "work/sim/${lbl}.log" 2>&1
  local p; p=$(grep -c "  PASS" "work/sim/${lbl}.log")
  if grep -q "ALL CHECKS PASSED" "work/sim/${lbl}.log"; then note "- ${lbl}: ALL CHECKS PASSED ($p checks)"; else note "- ${lbl}: FAILED"; FAIL=1; fi
}
stage "4. Clean accelerator simulation"
run_sim clean "" "rtl/crypto_top.v"

# ---------------------------------------------------------------- 5. Trojan insertion + sim
stage "5. Trojan insertion pass + simulations"
"$PY" -I tools/insert_trojan.py A B C > work/trojans/insert.log 2>&1 \
  && note "- inserted A/B/C via tools/insert_trojan.py -> work/trojans/crypto_top_{A,B,C}.v" \
  || { note "- FAIL Trojan insertion"; FAIL=1; }
run_sim A "-DDEMO_A" "work/trojans/crypto_top_A.v"
run_sim B "-DDEMO_B" "work/trojans/crypto_top_B.v"
run_sim C "-DDEMO_C" "work/trojans/crypto_top_C.v"
grep -hE "TROJAN [ABC]|leaked|ACCEPTED|recovered|nonce reuse" work/sim/A.log work/sim/B.log work/sim/C.log 2>/dev/null \
  | sed 's/^/    /' >> "$RES"

# ---------------------------------------------------------------- 6. loader
stage "6. I2C EEPROM key-loader (real master <-> EEPROM model)"
"$IVERILOG" -g2012 -s tb_loader -o work/sim/build/sim_loader tb/tb_loader.v rtl/i2c_eeprom_loader.v rtl/i2c_eeprom_model.v 2>/dev/null
"$VVP" work/sim/build/sim_loader > work/sim/loader.log 2>&1
grep -q "LOADER PASS" work/sim/loader.log && note "- $(grep 'LOADER PASS' work/sim/loader.log)" || { note "- FAIL loader"; FAIL=1; }

# ---------------------------------------------------------------- 7. synth overhead
stage "7. iCE40-UP5K synthesis (core) + Trojan LUT overhead"
# split flow: classic abc for LUT mapping (abc9 crashes on this build)
synth_core(){ # $1=label $2=crypto_top-src -> prints LUT4 count
  "$YOSYS" -p "read_verilog -sv rtl/ascon_engine.v $2; synth_ice40 -top crypto_top -run :map_luts; ice40_wrapcarry -unwrap; abc -lut 4; clean; techmap -map +/ice40/cells_map.v; clean; synth_ice40 -top crypto_top -run map_cells:; stat" \
     > "work/synth/log_$1.txt" 2>&1
  grep -E "^\s+[0-9]+\s+SB_LUT4" "work/synth/log_$1.txt" | tail -1 | awk '{print $1}'
}
LC=$(synth_core CLEAN rtl/crypto_top.v)
LA=$(synth_core A work/trojans/crypto_top_A.v)
LB=$(synth_core B work/trojans/crypto_top_B.v)
LCC=$(synth_core C work/trojans/crypto_top_C.v)
note "- core LUT4: CLEAN=${LC:-?}  A=${LA:-?} (+$((${LA:-0}-${LC:-0})))  B=${LB:-?} (+$((${LB:-0}-${LC:-0})))  C=${LCC:-?} (+$((${LCC:-0}-${LC:-0})))"

# ---------------------------------------------------------------- 8. bitstream that fits
stage "8. Board place & route -> bitstream that fits the UP5K"
if [ "${NO_BOARD:-0}" = 1 ]; then
  note "- SKIP (NO_BOARD=1)"
else
  build_bits(){ # $1=label $2=crypto_top-src
    local lbl="$1" src="$2" base="work/board/${1}"
    "$YOSYS" -p "read_verilog -sv rtl/crypto_board_top.v rtl/spi_peripheral.v rtl/i2c_eeprom_loader.v $src rtl/ascon_engine.v; synth_ice40 -top crypto_board_top -run :map_luts; ice40_wrapcarry -unwrap; abc -lut 4; clean; techmap -map +/ice40/cells_map.v; clean; synth_ice40 -top crypto_board_top -run map_cells:; write_json ${base}.json" \
        > "${base}_synth.log" 2>&1
    if [ ! -s "${base}.json" ]; then note "- ${lbl}: SYNTH failed (see ${base}_synth.log)"; FAIL=1; return; fi
    "$NEXTPNR" --"$DEVICE" --package "$PACKAGE" --json "${base}.json" --pcf "$PCF" \
        --asc "${base}.asc" --freq "$FREQ_MHZ" > "${base}_pnr.log" 2>&1
    local util fmax
    util=$(grep -oE "ICESTORM_LC: +[0-9]+/ +[0-9]+ +[0-9]+%" "${base}_pnr.log" | tail -1 | tr -s ' ')
    fmax=$(grep -oE "Max frequency for clock 'ICE_CLK.*: [0-9.]+ MHz \(PASS|FAIL" "${base}_pnr.log" | tail -1)
    if [ -s "${base}.asc" ] && grep -q "finished normally" "${base}_pnr.log"; then
      "$ICEPACK" "${base}.asc" "${base}.bin" 2>/dev/null
      note "- ${lbl}: FITS ($util; ${fmax:-timing ok}) -> ${base}.bin ($(wc -c < "${base}.bin" 2>/dev/null) bytes)"
    else
      note "- ${lbl}: DID NOT FIT / route (see ${base}_pnr.log)"; FAIL=1
    fi
  }
  build_bits clean rtl/crypto_top.v
  build_bits trojanA work/trojans/crypto_top_A.v
  build_bits trojanB work/trojans/crypto_top_B.v
  build_bits trojanC work/trojans/crypto_top_C.v
fi

echo; echo "============================================================"
if [ "$FAIL" -eq 0 ]; then note ""; note "**RESULT: ALL STAGES PASSED.**"; echo "ALL STAGES PASSED"; else note ""; note "**RESULT: SOME STAGES FAILED.**"; echo "SOME STAGES FAILED"; fi
echo "Full report: $RES"
exit $FAIL
