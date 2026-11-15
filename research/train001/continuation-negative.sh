#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PATH="/workspace/uno-environment/kotlin-2.2.21/kotlinc/bin:$PATH"
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
for mutation in detached_key detached_value; do
  python3 - "$mutation" "$build" <<'PY'
from pathlib import Path
import sys
s=Path('research/f-gradients/LearnedMemory.kt').read_text()
old='return Entry(stamp,key,value).also {'
new={'detached_key':'return Entry(stamp,ReverseF.V(key.x.copyOf()),value).also {','detached_value':'return Entry(stamp,key,ReverseF.V(value.x.copyOf())).also {'}[sys.argv[1]]
assert s.count(old)==1
Path(sys.argv[2],'LearnedMemory.kt').write_text(s.replace(old,new))
PY
  kotlinc android/core/src/main/kotlin/org/unovyra/uno/core/*.kt research/f-gradients/ReverseF.kt "$build/LearnedMemory.kt" research/train001/*.kt -include-runtime -d "$build/mutant.jar"
  set +e
  java -Xmx1500m -cp "$build/mutant.jar" org.unovyra.uno.research.ContinuationTestKt > "$build/output" 2>&1
  status=$?
  set -e
  echo "MUTATION=$mutation exit=$status expected=gradient_assertion"
  tail -5 "$build/output"
  test "$status" -ne 0
  rg -q 'IllegalStateException: FD wk|IllegalStateException: FD wv|IllegalStateException: DEAD_PATH wk|IllegalStateException: DEAD_PATH wv' "$build/output"
done
