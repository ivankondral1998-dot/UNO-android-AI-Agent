#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PATH="/workspace/uno-environment/kotlin-2.2.21/kotlinc/bin:$PATH"
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
for mutation in detachKey detachValue overwriteShared admitCurrent; do
  python3 - "$mutation" "$build" <<'PY'
import pathlib,sys
root=pathlib.Path('research/f-gradients');out=pathlib.Path(sys.argv[2]);mutation=sys.argv[1]
r=(root/'ReverseF.kt').read_text();m=(root/'LearnedMemory.kt').read_text()
if mutation in ('detachKey','detachValue'):
    old='Entry(stamp,key,value)';new='Entry(stamp,ReverseF.V(key.x.copyOf()),value)' if mutation=='detachKey' else 'Entry(stamp,key,ReverseF.V(value.x.copyOf()))'
    assert m.count(old)==1;m=m.replace(old,new)
elif mutation=='overwriteShared':
    old='a.g[r*cols+c] += y.g[r]*b.x[c]'
    new='if (a === leaves["wk"] || a === leaves["wv"]) a.g[r*cols+c] = y.g[r]*b.x[c] else a.g[r*cols+c] += y.g[r]*b.x[c]'
    assert r.count(old)==1;r=r.replace(old,new)
else:
    old='e.stamp.sequence < sequence';assert m.count(old)==1;m=m.replace(old,'e.stamp.sequence <= sequence')
(out/'ReverseF.kt').write_text(r);(out/'LearnedMemory.kt').write_text(m)
PY
  kotlinc android/core/src/main/kotlin/org/unovyra/uno/core/*.kt "$build/ReverseF.kt" "$build/LearnedMemory.kt" research/f-gradients/MemoryTest.kt -include-runtime -d "$build/mutant.jar"
  set +e
  java -Xmx1g -cp "$build/mutant.jar" org.unovyra.uno.research.MemoryTestKt > "$build/result" 2>&1
  status=$?
  set -e
  echo "MUTATION=$mutation exit=$status expected=assertion failure"
  tail -7 "$build/result"
  test "$status" -ne 0
  case "$mutation" in
    detachKey) pattern='IllegalStateException: prefix4.wk' ;;
    detachValue) pattern='IllegalStateException: prefix2.wv' ;;
    overwriteShared) pattern='IllegalStateException: prefix4.wk|IllegalStateException: prefix4.wv' ;;
    admitCurrent) pattern='IllegalStateException: eligible.futureSequence' ;;
  esac
  rg -q "$pattern" "$build/result"
done
