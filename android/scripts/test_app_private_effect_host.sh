#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
kotlinc \
  "$ROOT/app/src/main/kotlin/org/unovyra/uno/AppPrivateReadbackProbe.kt" \
  "$ROOT/scripts/app_private_host/AppPrivateReadbackProbeHostTest.kt" \
  -include-runtime -d "$TMP/app-private-effect.jar"
java -cp "$TMP/app-private-effect.jar" org.unovyra.uno.AppPrivateReadbackProbeHostTest
