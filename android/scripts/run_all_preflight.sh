#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$ROOT/scripts/host_verify.sh"
python3 "$ROOT/scripts/static_contract_check.py"
python3 "$ROOT/scripts/test_sqlite_outcome_schema.py"
bash "$ROOT/scripts/test_outcome_inspection_host.sh"
bash "$ROOT/scripts/test_owner_consent_host.sh"
bash "$ROOT/scripts/test_app_private_effect_host.sh"
python3 "$ROOT/scripts/test_lab_tools.py"
python3 "$ROOT/scripts/test_apk_update_gate.py"
python3 "$ROOT/scripts/test_owner_update_build.py"
python3 "$ROOT/scripts/test_owner_permanent_channel.py"
echo "UNO_LAB_PREFLIGHT_SUCCESS (HOST ONLY; NOT ANDROID_BUILT OR DEVICE_VERIFIED)"
