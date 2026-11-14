#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TEST_ROOT="$ROOT/research/legacy-jno"
if ! command -v kotlinc >/dev/null || ! command -v java >/dev/null; then
  echo "JDK and kotlinc required for historical JNO smoke" >&2; exit 2
fi
TEMP="$(mktemp -d)"
trap 'rm -rf -- "$TEMP"' EXIT
kotlinc "$TEST_ROOT/kotlin/io/jarvis/mobile/v21/NeuralCore.kt" \
  "$TEST_ROOT/tests/V21CoreRepositorySmoke.kt" -include-runtime -d "$TEMP/core.jar"
java -jar "$TEMP/core.jar" "$TEST_ROOT/assets/jno2-w64-int8.bin"
