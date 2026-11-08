#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
kotlinc \
  "$ROOT/app/src/main/kotlin/org/unovyra/uno/AndroidOutcomeInspection.kt" \
  "$ROOT/scripts/inspection_host/ContextStub.kt" \
  "$ROOT/scripts/inspection_host/InspectionHostTest.kt" \
  -include-runtime -d "$TMP/inspection-host.jar"
java -cp "$TMP/inspection-host.jar" org.unovyra.uno.InspectionHostTestKt
