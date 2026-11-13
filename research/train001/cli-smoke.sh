#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PATH="/workspace/uno-environment/kotlin-2.2.21/kotlinc/bin:$PATH"
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
kotlinc android/core/src/main/kotlin/org/unovyra/uno/core/*.kt research/f-gradients/ReverseF.kt research/f-gradients/LearnedMemory.kt research/train001/*.kt -include-runtime -d "$build/train.jar"
java -Xmx1500m -cp "$build/train.jar" org.unovyra.uno.research.DiagnosticKt inspect
java -Xmx1500m -cp "$build/train.jar" org.unovyra.uno.research.DiagnosticKt step "$build/state.bin"
java -Xmx1500m -cp "$build/train.jar" org.unovyra.uno.research.DiagnosticKt resume "$build/state.bin"
before=$(sha256sum "$build/state.bin" | cut -d ' ' -f1)
set +e
java -Xmx1500m -cp "$build/train.jar" org.unovyra.uno.research.DiagnosticKt resume "$build/state.bin" > "$build/budget.txt" 2>&1
status=$?
set -e
echo "THIRD_UPDATE_EXIT=$status expected=nonzero"
cat "$build/budget.txt"
test "$status" -ne 0
rg -q 'UPDATE_BOUNDARY_OR_BUDGET' "$build/budget.txt"
after=$(sha256sum "$build/state.bin" | cut -d ' ' -f1)
test "$before" = "$after"
echo "CROSS_PROCESS_RESUME_PASS checkpointUnchangedAfterRejectedUpdate=true sha256=$after"
