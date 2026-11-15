#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
if ! command -v kotlinc >/dev/null && [ -d /workspace/uno-environment/kotlin-2.2.21/kotlinc/bin ]; then
  export PATH="/workspace/uno-environment/kotlin-2.2.21/kotlinc/bin:$PATH"
fi
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
kotlinc android/core/src/main/kotlin/org/unovyra/uno/core/*.kt research/f-gradients/ReverseF.kt research/f-gradients/LearnedMemory.kt research/train001/*.kt -include-runtime -d "$build/train.jar"
java -Xmx1500m -cp "$build/train.jar" org.unovyra.uno.research.ContinuationTestKt
if [ -n "${UNO_TORCH_PYTHON:-}" ]; then
  java -Xmx1500m -cp "$build/train.jar" org.unovyra.uno.research.ParityFixtureKt "$build/parity"
  "$UNO_TORCH_PYTHON" research/train001/parity.py "$build/parity"
fi
