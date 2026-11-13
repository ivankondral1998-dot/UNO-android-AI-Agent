#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PATH="/workspace/uno-environment/kotlin-2.2.21/kotlinc/bin:$PATH"
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
kotlinc -version
java -version
kotlinc android/core/src/main/kotlin/org/unovyra/uno/core/*.kt research/f-gradients/*.kt -include-runtime -d "$build/gradients.jar"
java -Xmx1g -cp "$build/gradients.jar" org.unovyra.uno.research.GradientTestKt
