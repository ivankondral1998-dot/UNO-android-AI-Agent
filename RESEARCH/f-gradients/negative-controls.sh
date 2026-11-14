#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/workspace/uno-environment/kotlin-2.2.21/kotlinc/bin:$PATH"
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
for mutation in omitKey overwriteShared; do
  python3 - "$mutation" "$build/ReverseF.kt" <<'PY'
import pathlib,sys
s=pathlib.Path('f-gradients/ReverseF.kt').read_text()
a,b = ('keys[i].g[j] += ds*q.x[j]/divisor','/* omitted key pullback */') if sys.argv[1]=='omitKey' else ('a.g[r*cols+c] += y.g[r]*b.x[c]','a.g[r*cols+c] = y.g[r]*b.x[c]')
assert s.count(a)==1
pathlib.Path(sys.argv[2]).write_text(s.replace(a,b))
PY
  kotlinc ../WORK/android/core/src/main/kotlin/org/unovyra/uno/core/*.kt "$build/ReverseF.kt" f-gradients/GradientTest.kt -include-runtime -d "$build/mutant.jar"
  set +e
  java -Xmx1g -cp "$build/mutant.jar" org.unovyra.uno.research.GradientTestKt > "$build/result.txt" 2>&1
  status=$?
  set -e
  echo "MUTATION=$mutation exit=$status expected=nonzero"
  if [ "$status" -eq 0 ]; then echo 'UNDETECTED_MUTATION'; exit 1; fi
  tail -8 "$build/result.txt"
  # Only an assertion from numerical comparison counts, not a startup/runtime error.
  rg -q 'IllegalStateException: (multipleK3.key|emptyK1.branch|singletonK3.branch)' "$build/result.txt"
done
