#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/workspace/uno-environment/kotlin-2.2.21/kotlinc/bin:$PATH"
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
for mutation in omitLoss overwriteBatch omitBiasCorrection loseMoments; do
  python3 - "$mutation" "$build" <<'PY'
from pathlib import Path
import sys
root=Path('train001');out=Path(sys.argv[2]);mutation=sys.argv[1]
for p in root.glob('*.kt'):
    s=p.read_text()
    edits={
      'omitLoss':('Trainer.kt','listOf(c.stateLoss,c.retrieveLoss,c.valueLoss)','listOf(c.stateLoss,c.retrieveLoss,0.0)'),
      'overwriteBatch':('Trainer.kt','x[it]+g[it]','g[it]'),
      'omitBiasCorrection':('Trainer.kt','m[i]/(1-config.beta1.pow(nextStep.toDouble()))','m[i]'),
      'loseMoments':('Checkpoint.kt','OptimizerState(step,cursor,ms,vs)','OptimizerState(step,cursor,OfflineTrainer.zeros(template),vs)')}
    name,old,new=edits[mutation]
    if p.name==name:
        assert s.count(old)==1,(mutation,s.count(old));s=s.replace(old,new)
    (out/p.name).write_text(s)
PY
  kotlinc ../WORK/android/core/src/main/kotlin/org/unovyra/uno/core/*.kt f-gradients/ReverseF.kt f-gradients/LearnedMemory.kt "$build"/*.kt -include-runtime -d "$build/mutant.jar"
  set +e
  java -Xmx1500m -cp "$build/mutant.jar" org.unovyra.uno.research.TrainTestKt > "$build/output" 2>&1
  status=$?
  set -e
  echo "MUTATION=$mutation exit=$status expected=assertion"
  tail -9 "$build/output"
  test "$status" -ne 0
  case "$mutation" in
    omitLoss) expected='IllegalStateException: joint.loss.independent' ;;
    overwriteBatch) expected='IllegalStateException: batch.meanUpdate|IllegalStateException: batch.meanM' ;;
    omitBiasCorrection) expected='IllegalStateException: adam.first.weight' ;;
    loseMoments) expected='IllegalStateException: checkpoint.m' ;;
  esac
  rg -q "$expected" "$build/output"
done
