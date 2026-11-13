#!/usr/bin/env bash
# ============================================================================
# One-command driver for the CSAW 2026 Claude-agent Trojan pipeline.
#
#   ./run_all.sh            offline self-check: verify the clean recovered core
#                           (baseline) and the shipped Trojan (ALL PASS), no key
#   ./run_all.sh live       run the Claude agent end-to-end (needs ANTHROPIC_API_KEY)
#   ./run_all.sh live --area also report the yosys iCE40 area of the result
#
# The offline path needs only python3 + Icarus Verilog (the Yosys OSS CAD Suite
# provides both). The live path additionally needs the anthropic SDK and a key.
# ============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=== Preflight ==="
command -v python3   >/dev/null 2>&1 || { echo "ERROR: python3 not on PATH." >&2; exit 1; }
command -v iverilog  >/dev/null 2>&1 || { echo "ERROR: iverilog not on PATH (install the Yosys OSS CAD Suite)." >&2; exit 1; }
python3 - <<'PY'
import sys; sys.path.insert(0, ".")
from common import toolchain
print(toolchain.toolchain_report())
PY

MODE="${1:-offline}"
shift || true
EXTRA="$*"

if [[ "$MODE" == "live" ]]; then
  echo "=== Live Claude agent: challenge_1 ==="
  [[ -n "${ANTHROPIC_API_KEY:-}" ]] || { echo "ERROR: set ANTHROPIC_API_KEY for the live run." >&2; exit 1; }
  ( cd challenge_1 && python3 agent.py $EXTRA )
  exit $?
fi

echo "=== Offline self-check: challenge_1 ==="
echo "--- clean recovered core (baseline: correct cipher, Trojan absent) ---"
( cd challenge_1 && python3 agent.py --clean $EXTRA ) | tail -3
echo "--- shipped Trojan (expect TB_TROJAN: ALL PASS) ---"
( cd challenge_1 && python3 agent.py --replay $EXTRA ) | grep -E "TB_TROJAN|replay shipped|SUCCESS|FAIL" | tail -4
echo
echo "Offline self-check complete. For the live agent run: ./run_all.sh live"
