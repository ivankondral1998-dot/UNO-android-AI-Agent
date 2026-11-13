#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PATH="/workspace/uno-environment/kotlin-2.2.21/kotlinc/bin:$PATH"
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
kotlinc -version
java -version
kotlinc android/core/src/main/kotlin/org/unovyra/uno/core/*.kt research/f-gradients/ReverseF.kt research/f-gradients/LearnedMemory.kt research/train001/*.kt -include-runtime -d "$build/train.jar"
java -Xmx1500m -cp "$build/train.jar" org.unovyra.uno.research.TrainTestKt
