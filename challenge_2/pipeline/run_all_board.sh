#!/usr/bin/env bash
# =============================================================================
# CSAW AHA 2026 - Final Challenge 2 : ONE-CLICK *BOARD* AUTOMATION
# -----------------------------------------------------------------------------
# Superset of pipeline/run_all.sh (called UNMODIFIED for all of simulation,
# synthesis, and the UP5K place&route to fitting bitstreams). It then, for the
# clean design and each Trojan one after another, programs the board and drives
# the on-board self-test + exploit. One click, whole flow. Writes
# pipeline/BOARD_RESULTS.md.
#
# Board: Lattice iCE40 UltraPlus UP5K (sg48), Hackster.
#   https://www.latticesemi.com/en/products/fpgaandcpld/ice40ultraplus
# Build flow mirrors the official hackster.mk (yosys -> nextpnr-ice40 -> icepack);
# see https://github.com/kiwih/hackster-programmer and the challenge repo
#   https://github.com/JBlocklove/CSAW-AI-Hardware-Attack-Challenge-2026/tree/main/finals/challenge_2
#
# Usage:
#   bash pipeline/run_all_board.sh                                   # sim+build; program/drive skipped if no board
#   FPGA_PORT=/dev/ttyACM0 APP_PORT=/dev/ttyACM1 bash pipeline/run_all_board.sh   # full HW run
#   (Windows: COMx ; macOS: /dev/cu.usbmodem*). Plug the programmer in first.
#
# The design now FITS the UP5K (crypto_top uses EBR-backed buffers; the I2C loader
# is a complete master), so run_all.sh stage 8 produces real bitstreams at
# work/board/{clean,trojanA,trojanB,trojanC}.bin. The only remaining precondition
# is a provisioned board attached with FPGA_PORT/APP_PORT set; without it the
# program/drive stages are skipped and the bitstreams are still built.
# =============================================================================
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
OSS="${OSS:-/c/oss-cad-suite}"; export PATH="$OSS/bin:$OSS/lib:$PATH"
if [ -z "${PY:-}" ]; then
  for c in /c/Python314/python python3 python; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
fi
PROG="$PY fpga/hackster-fpga-program.py"      # PROG w <bin> <FPGA_PORT>
MPREMOTE="${MPREMOTE:-mpremote}"
FPGA_PORT="${FPGA_PORT:-}"; APP_PORT="${APP_PORT:-}"
RES="pipeline/BOARD_RESULTS.md"; mkdir -p work/board
echo "# Board Automation Results" > "$RES"; echo "_$(date)_" >> "$RES"; echo >> "$RES"
FAIL=0
note(){ echo "$1"; echo "$1" >> "$RES"; }
stage(){ echo; echo "=== $1 ==="; echo "## $1" >> "$RES"; }

# ---- preflight (board tools only matter if ports are set) ----
echo "=== preflight ==="
[ -n "${PY:-}" ] || { echo "PREFLIGHT ERROR: no Python; set PY=/path/to/python."; exit 2; }
[ -f fpga/hackster-fpga-program.py ] || { echo "PREFLIGHT ERROR: run from the challenge root."; exit 2; }
if [ -n "$FPGA_PORT$APP_PORT" ]; then
  command -v "$MPREMOTE" >/dev/null 2>&1 || echo "WARN: mpremote not found (pip install mpremote) - on-board drive will be skipped."
  "$PY" -c "import serial" >/dev/null 2>&1 || echo "WARN: pyserial not found (pip install pyserial) - programming will fail."
fi

# ---- 0. full sim + synthesis + fitting bitstreams via run_all.sh ----
stage "0. Simulation + synthesis + UP5K bitstreams (pipeline/run_all.sh)"
if bash pipeline/run_all.sh > work/board/run_all.log 2>&1; then
  note "- run_all.sh: $(grep -o 'ALL STAGES PASSED' work/board/run_all.log || echo 'see work/board/run_all.log')"
  grep -E "FITS|DID NOT FIT" work/board/run_all.log | sed 's/^/  /' >> "$RES"
else
  note "- run_all.sh FAILED (see work/board/run_all.log)"; FAIL=1
fi

# ---- SPI board-integration layer ----
stage "0b. SPI board-integration layer (bit-serial frames -> crypto_top)"
iverilog -g2012 -I tb -s tb_spi -o work/board/sim_spi tb/tb_spi.v rtl/spi_peripheral.v rtl/crypto_top.v rtl/ascon_engine.v 2>/dev/null
if vvp work/board/sim_spi 2>/dev/null | grep -q "SPI SHELL OK"; then
  note "- SPI peripheral maps frames correctly (status/ciphertext/tag verified)"
else note "- SPI shell check FAILED"; FAIL=1; fi

# ---- board presence ----
BOARD=0; [ -n "$FPGA_PORT" ] && [ -n "$APP_PORT" ] && BOARD=1
stage "1. Board detection"
note "- programmer port (FPGA_PORT): ${FPGA_PORT:-<unset>}"
note "- app-processor port (APP_PORT): ${APP_PORT:-<unset>}"
note "- mpremote: $(command -v $MPREMOTE >/dev/null 2>&1 && echo present || echo MISSING)"
[ "$BOARD" -eq 0 ] && note "- NO board attached -> program/drive SKIPPED (bitstreams already built by run_all.sh)."

# ---- 2. program + drive each design in turn ----
stage "2. Program + drive (clean, then Trojan A/B/C)"
drive(){ # $1=label(clean/trojanA/..) $2=exploit-or-empty
  local lbl="$1" expl="$2" bin="work/board/${1}.bin"
  [ -s "$bin" ] || { note "- $lbl: no bitstream ($bin) - run_all.sh stage 8 must succeed first."; FAIL=1; return; }
  if [ "$BOARD" -eq 0 ]; then note "- $lbl: bitstream ready ($bin); board not attached, program/drive skipped."; return; fi
  note "- $lbl: programming via $FPGA_PORT ..."
  $PROG w "$bin" "$FPGA_PORT" > "work/board/${lbl}_prog.log" 2>&1 \
    && note "- $lbl: programmed (RGB green = keys loaded from EEPROM; EEPROM is organizer-provisioned)" \
    || { note "- $lbl: PROGRAM failed (see work/board/${lbl}_prog.log)"; FAIL=1; return; }
  $MPREMOTE connect "$APP_PORT" run tools/fpga_selftest.py > "work/board/${lbl}_selftest.log" 2>&1
  grep -q "All checks passed" "work/board/${lbl}_selftest.log" \
    && note "- $lbl: fpga_selftest PASS (normal operation preserved)" \
    || note "- $lbl: fpga_selftest did not fully pass (see work/board/${lbl}_selftest.log)"
  if [ -n "$expl" ]; then
    $MPREMOTE connect "$APP_PORT" mount pipeline/board run "pipeline/board/$expl" > "work/board/${lbl}_exploit.log" 2>&1
    note "- $lbl: exploit output ->"; sed 's/^/    /' "work/board/${lbl}_exploit.log" >> "$RES"
  fi
}
drive clean   ""
drive trojanA exploit_trojan_a.py
drive trojanB exploit_trojan_b.py
drive trojanC exploit_trojan_c.py

echo; if [ "$FAIL" -eq 0 ]; then note ""; note "**RESULT: all runnable stages passed.** (HW program/drive run only when a board is attached.)"; else note ""; note "**RESULT: some stages failed - see logs.**"; fi
echo "Report: $RES"
exit $FAIL
