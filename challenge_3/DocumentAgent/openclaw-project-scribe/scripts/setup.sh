#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
node --no-warnings "$script_dir/../scribe.mjs" setup "$@"
