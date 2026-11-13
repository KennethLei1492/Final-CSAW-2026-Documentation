#!/usr/bin/env bash
# =============================================================================
# CSAW AHA 2026 - Final Challenge 2 : ONE-CLICK *BOARD* AUTOMATION
# -----------------------------------------------------------------------------
# Superset of pipeline/run_all.sh (which it calls UNMODIFIED for all simulation
# verification) that additionally, for the clean design and then each Trojan one
# after the other, builds an iCE40-UP5K bitstream and - when a Hackster board is
# attached - programs it and drives the on-board exploit + self-test. Goal: the
# entire flow in one click. Writes pipeline/BOARD_RESULTS.md.
#
# Board: Lattice iCE40 UltraPlus UP5K (sg48), Hackster
#   https://www.latticesemi.com/en/products/fpgaandcpld/ice40ultraplus
#
# Usage:
#   bash pipeline/run_all_board.sh                 # sim + build; HW stages auto-skip if no board
#   FPGA_PORT=COM5 APP_PORT=COM6 bash pipeline/run_all_board.sh   # full HW run
#
# HONEST PRECONDITIONS for the hardware stages to actually succeed (reported by
# the script, detailed in pipeline/REPLICATE_PROMPT_BOARD.md):
#   P1  A provisioned Hackster board is attached and FPGA_PORT (programmer) and
#       APP_PORT (application processor) point to its two serial ports.
#   P2  The crypto_top AD/MSG/OUT buffers are refactored from register files to
#       EBR so crypto_board_top fits the UP5K (as-written it is ~39.8k LUT >>
#       5280; the recovered production design is 4577 LUT / 7 BRAM). Until then
#       nextpnr will report "won't fit" and the script says so rather than faking.
#   P3  i2c_eeprom_loader's bit-level EEPROM burst read is completed (its
#       validate/latch logic is done and tb-verified; the burst is abstracted).
# =============================================================================
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
OSS="${OSS:-/c/oss-cad-suite}"
export PATH="$OSS/bin:$OSS/lib:$PATH"
[ -f "$OSS/etc/cacert.pem" ] && export SSL_CERT_FILE="$OSS/etc/cacert.pem"
if [ -z "${PY:-}" ]; then
  for c in /c/Python314/python python3 python; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
fi
YOSYS="${YOSYS:-yosys}"; NEXTPNR="${NEXTPNR:-nextpnr-ice40}"; ICEPACK="${ICEPACK:-icepack}"
IVERILOG="${IVERILOG:-iverilog}"; VVP="${VVP:-vvp}"
PROG="$PY fpga/hackster-fpga-program.py"      # programmer: PROG w <bin> <FPGA_PORT>
MPREMOTE="${MPREMOTE:-mpremote}"
# Serial ports (Linux /dev/ttyACM0|1, macOS /dev/cu.usbmodem*, Windows COMx).
# FPGA_PORT = programmer (loads bitstreams); APP_PORT = RP2040 app processor.
FPGA_PORT="${FPGA_PORT:-}"; APP_PORT="${APP_PORT:-}"
# iCE40-UP5K on the Hackster, 48-pin QFN (sg48), ~10 MHz ICE_CLK (per
# ice40_crypto_ip.md and hackster.mk: PACKAGE=sg48). Build flow mirrors the
# official hackster.mk (yosys synth_ice40 -> nextpnr-ice40 -> icepack); see
# https://github.com/kiwih/hackster-programmer and
# https://github.com/JBlocklove/CSAW-AI-Hardware-Attack-Challenge-2026/tree/main/finals/challenge_2
DEVICE="up5k"; PACKAGE="sg48"; FREQ_MHZ="${FREQ_MHZ:-10}"
RTL="rtl/crypto_board_top.v rtl/spi_peripheral.v rtl/i2c_eeprom_loader.v rtl/crypto_top.v rtl/ascon_engine.v"
PCF="rtl/crypto_board_top.pcf"
BUILDS=("clean:" "A:-DTROJAN_A" "B:-DTROJAN_B" "C:-DTROJAN_C")
RES="pipeline/BOARD_RESULTS.md"; mkdir -p work/board
echo "# Board Automation Results" > "$RES"; echo "_$(date)_" >> "$RES"; echo >> "$RES"
FAIL=0
note(){ echo "$1"; echo "$1" >> "$RES"; }
stage(){ echo; echo "=== $1 ==="; echo "## $1" >> "$RES"; }

# ---- preflight (build tools are mandatory; board tools only if ports set) ----
echo "=== preflight ==="
pf=0
for t in "$YOSYS" "$NEXTPNR" "$ICEPACK" "$IVERILOG" "$VVP"; do
  command -v "$t" >/dev/null 2>&1 || { echo "PREFLIGHT ERROR: '$t' not found - install OSS CAD Suite / set OSS=..."; pf=1; }
done
[ -n "${PY:-}" ] || { echo "PREFLIGHT ERROR: no Python; set PY=/path/to/python."; pf=1; }
[ -f fpga/hackster-fpga-program.py ] || { echo "PREFLIGHT ERROR: fpga/hackster-fpga-program.py missing (run from challenge root)."; pf=1; }
[ "$pf" -eq 0 ] || { echo "Preflight failed."; exit 2; }
if [ -n "$FPGA_PORT$APP_PORT" ]; then
  command -v "$MPREMOTE" >/dev/null 2>&1 || echo "WARN: mpremote not found (pip install mpremote) - on-board drive will be skipped."
  "$PY" -c "import serial" >/dev/null 2>&1 || echo "WARN: pyserial not found (pip install pyserial) - programming will fail."
fi
echo "preflight OK (PY=$PY, OSS=$OSS, device=$DEVICE/$PACKAGE)"

# ---------------------------------------------------------------- 0. verify
stage "0. Full simulation verification (pipeline/run_all.sh, unmodified)"
if bash pipeline/run_all.sh > work/board/run_all.log 2>&1; then
  note "- simulation pipeline: $(grep -o 'ALL STAGES PASSED' work/board/run_all.log || echo 'see log') (work/board/run_all.log)"
else note "- simulation pipeline FAILED (see work/board/run_all.log)"; FAIL=1; fi

# ---------------------------------------------------------------- 0b. SPI shell
stage "0b. SPI board-integration layer (bit-serial frames -> crypto_top)"
"$IVERILOG" -g2012 -I tb -s tb_spi -o work/board/sim_spi tb/tb_spi.v rtl/spi_peripheral.v rtl/crypto_top.v rtl/ascon_engine.v 2>/dev/null
if "$VVP" work/board/sim_spi 2>/dev/null | grep -q "SPI SHELL OK"; then
  note "- SPI peripheral maps frames correctly (status/ciphertext/tag verified)"
else note "- SPI shell check FAILED"; FAIL=1; fi

# ---------------------------------------------------------------- HW presence
BOARD=0
if [ -n "$FPGA_PORT" ] && [ -n "$APP_PORT" ]; then BOARD=1; fi
stage "1. Board / toolchain detection"
note "- nextpnr-ice40: $(command -v $NEXTPNR >/dev/null 2>&1 && echo present || echo MISSING)"
note "- programmer port (FPGA_PORT): ${FPGA_PORT:-<unset>}"
note "- app-processor port (APP_PORT): ${APP_PORT:-<unset>}"
note "- mpremote: $(command -v $MPREMOTE >/dev/null 2>&1 && echo present || echo MISSING)"
[ "$BOARD" -eq 0 ] && note "- NO board attached -> hardware program/drive stages will be SKIPPED (build still runs)."

# ---------------------------------------------------------------- per-design
build_one(){ # $1=label $2=define
  local lbl="$1"; local def="${2:-}"; local base="work/board/crypto_${lbl}"
  echo; echo "--- design: $lbl ---"
  # synth (-noabc avoids the xaiger2 abc9 crash on this host) -> JSON
  "$YOSYS" -p "read_verilog -sv $def $RTL; synth_ice40 -noabc -top crypto_board_top -json ${base}.json" \
      > "${base}_synth.log" 2>&1
  if [ ! -s "${base}.json" ]; then note "- $lbl: SYNTH failed (see ${base}_synth.log)"; FAIL=1; return; fi
  local lut; lut=$(grep -E ' SB_LUT4$' "${base}_synth.log" | tail -1 | awk '{print $1}')
  note "- $lbl: synthesized (SB_LUT4=${lut:-?})"
  # place & route (--up5k --package sg48, timed at the ~10 MHz ICE_CLK)
  if "$NEXTPNR" --"$DEVICE" --package "$PACKAGE" --json "${base}.json" --pcf "$PCF" \
       --asc "${base}.asc" --freq "$FREQ_MHZ" > "${base}_pnr.log" 2>&1 && [ -s "${base}.asc" ]; then
    "$ICEPACK" "${base}.asc" "${base}.bin" 2>/dev/null
    note "- $lbl: placed & packed -> ${base}.bin"
  else
    note "- $lbl: PLACE&ROUTE did not fit the UP5K (precondition P2 - see ${base}_pnr.log). No bitstream."
    note "        $(grep -iE 'not fit|unable|overmap|too many|error' "${base}_pnr.log" | head -1 | sed 's/^/        /')"
    note "        FIX: refactor crypto_top AD/MSG/OUT buffers to EBR (synchronous single-port reads) so it fits 5280 LUT / 30 EBR."
    return
  fi
  # program + drive (only if a board is attached and a bitstream exists)
  if [ "$BOARD" -eq 1 ] && [ -s "${base}.bin" ]; then
    note "- $lbl: programming board via $FPGA_PORT ..."
    $PROG w "${base}.bin" "$FPGA_PORT" > "${base}_prog.log" 2>&1 \
        && note "- $lbl: programmed" || { note "- $lbl: PROGRAM failed (see ${base}_prog.log)"; FAIL=1; return; }
    # normal-operation proof
    $MPREMOTE connect "$APP_PORT" run tools/fpga_selftest.py > "${base}_selftest.log" 2>&1
    grep -q "All checks passed" "${base}_selftest.log" \
        && note "- $lbl: fpga_selftest PASS (normal operation preserved)" \
        || note "- $lbl: fpga_selftest did not fully pass (see ${base}_selftest.log)"
    # payload for Trojan builds
    if [ "$lbl" != "clean" ]; then
      $MPREMOTE connect "$APP_PORT" mount pipeline/board run "pipeline/board/exploit_trojan_$(echo $lbl|tr 'ABC' 'abc').py" \
          > "${base}_exploit.log" 2>&1
      note "- $lbl: exploit driver output ->"; sed 's/^/    /' "${base}_exploit.log" >> "$RES"
    fi
  elif [ -s "${base}.bin" ]; then
    note "- $lbl: bitstream ready; board not attached, so program/drive skipped (P1)."
  fi
}

stage "2. Build + (if board) program + drive, one design after another"
for entry in "${BUILDS[@]}"; do build_one "${entry%%:*}" "${entry#*:}"; done

echo; if [ "$FAIL" -eq 0 ]; then note ""; note "**RESULT: all runnable stages passed.** (HW stages run only when a board is attached and preconditions P2/P3 are met.)"; else note ""; note "**RESULT: some stages failed - see logs.**"; fi
echo "Report: $RES"
exit $FAIL
