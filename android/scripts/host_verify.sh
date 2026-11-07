#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
kotlinc "$ROOT"/core/src/main/kotlin/org/unovyra/uno/core/*.kt \
  "$ROOT"/core/src/test/kotlin/org/unovyra/uno/core/*.kt \
  -include-runtime -d "$TMP/uno-core.jar"
java -cp "$TMP/uno-core.jar" org.unovyra.uno.core.AllHostTestsKt
