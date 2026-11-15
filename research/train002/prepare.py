"""Create fresh locked study inputs, no optimization. Kotlin initial files must already exist."""
import argparse,pathlib,json,shutil,hashlib
from engine import ARMS,require,atomic,canonical,file_sha
from study import SEEDS,source_identity
from data import generate

def prepare(root,initials,diagnostic=False):
    root.mkdir(parents=True,exist_ok=False)
    for seed in ([SEEDS[0]] if diagnostic else SEEDS):
        source=initials/f'initial-{seed}.tsv';require(source.is_file(),'MISSING_KOTLIN_INITIAL '+str(source));shutil.copyfile(source,root/source.name)
    manifest=generate(root/'data',seed=2026111502 if not diagnostic else 42,train_pairs=1 if diagnostic else 16,val_pairs=1 if diagnostic else 2,test_pairs=1 if diagnostic else 16)
    files={p.relative_to(root).as_posix():file_sha(p) for p in root.rglob('*') if p.is_file()}
    plan={'stage':'TRAIN-002','version':1,'base_train001':'b371b627ef743b876e13daadf3b57d6013f37652','source':source_identity(),'seeds':[SEEDS[0]] if diagnostic else SEEDS,'arms':['chrono_typed'] if diagnostic else list(ARMS),'steps':12 if diagnostic else 1000,'batch':1 if diagnostic else 4,'files':files,'diagnostic':diagnostic,'sampling':'same fixed shuffled train order for every arm/seed, cursor modulo train size','precision':'FP32 master/grad/Adam, FP64 Euclidean L1 threshold, TF32 disabled','new_test':'created and hashed before any training; evaluate only after all declared runs finish','supervision':'typed=all writes [raw_value,public_slot], legacy=queried record one scalar; this changes fields and coverage together','cells':{'train':sum(g['n'] for g in manifest['balanced']['train'].values()),'validation':sum(g['n'] for g in manifest['balanced']['validation'].values()),'test':sum(g['n'] for g in manifest['balanced']['test'].values())},'primary_comparisons':['chrono_typed vs baseline_typed','chrono_legacy vs baseline_legacy','baseline_typed vs baseline_legacy','baseline_typed vs f_no_memory/gru/frozen_write/random_keys/permuted_values'],'budget_note':'27 x1000 updates, one explicitly requested run per command, no automatic training in cloud; max1800seconds per invocation then Resume; no test-based hyperparameter selection'}
    atomic(root/'study.json',canonical(plan).encode());print(canonical(plan));return plan
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=pathlib.Path);p.add_argument('initials',type=pathlib.Path);a=p.parse_args();prepare(a.output,a.initials)
