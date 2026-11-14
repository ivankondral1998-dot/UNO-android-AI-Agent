#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/workspace/uno-environment/kotlin-2.2.21/kotlinc/bin:$PATH"
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
kotlinc -version
java -version
kotlinc ../WORK/android/core/src/main/kotlin/org/unovyra/uno/core/*.kt f-gradients/ReverseF.kt f-gradients/LearnedMemory.kt f-gradients/MemoryTest.kt -include-runtime -d "$build/memory.jar"
java -Xmx1g -cp "$build/memory.jar" org.unovyra.uno.research.MemoryTestKt
