#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$ROOT/scripts/host_verify.sh"
python3 "$ROOT/scripts/static_contract_check.py"
python3 "$ROOT/scripts/test_lab_tools.py"
echo "UNO_LAB_PREFLIGHT_SUCCESS (HOST ONLY; NOT ANDROID_BUILT OR DEVICE_VERIFIED)"
