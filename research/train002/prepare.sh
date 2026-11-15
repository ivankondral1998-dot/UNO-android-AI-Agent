#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
if [ "$#" -ne 4 ]; then echo 'Usage: prepare.sh NEW_PACKET_DIR NORMALIZED_TRAIN001_RESULTS OLD_INPUT_DIR NEW_AUDIT_OUTPUT' >&2; exit 2; fi
prepared=$1
historic_results=$2
old_inputs=$3
historic_audit=$4
python_runner=${UNO_TORCH_PYTHON:-python3}
if ! command -v kotlinc >/dev/null && [ -d /workspace/uno-environment/kotlin-2.2.21/kotlinc/bin ]; then
  export PATH="/workspace/uno-environment/kotlin-2.2.21/kotlinc/bin:$PATH"
fi
# Preserve build artifacts, inputs, previous experiments and all journals.
build=$(mktemp -d)
kotlinc android/core/src/main/kotlin/org/unovyra/uno/core/*.kt research/f-gradients/ReverseF.kt research/f-gradients/LearnedMemory.kt research/train001/*.kt research/train002/PrepareInitial.kt -include-runtime -d "$build/prepare.jar"
java -Xmx1500m -cp "$build/prepare.jar" org.unovyra.uno.research.PrepareInitialKt "$build/initials"
"$python_runner" research/train002/prepare.py "$prepared/study" "$build/initials"
"$python_runner" research/train002/audit_previous.py "$historic_results" "$old_inputs" "$historic_audit"
"$python_runner" research/train002/package.py "$prepared" "$historic_audit" "$old_inputs" "$historic_results"
