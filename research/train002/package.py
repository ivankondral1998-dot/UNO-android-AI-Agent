"""Package prepared inputs + immutable core + scientific artifacts. Never starts training."""
import argparse,pathlib,shutil,hashlib,json,zipfile
from engine import require,canonical,file_sha
from study import source_identity,load_plan

def copy(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():require(target.read_bytes()==source.read_bytes(),'REFUSE_REPLACE_PACKET_FILE '+str(target))
    else:shutil.copyfile(source,target)

def package(root,historic,old_inputs,results):
    here=pathlib.Path(__file__).resolve().parent
    # Source may be finalized during preparation, before any study training. Corpus bytes stay fixed.
    plan=json.loads((root/'study/study.json').read_text());plan['source']=source_identity()
    (root/'study/study.json').write_text(canonical(plan));load_plan(root/'study')
    for p in here.glob('*.py'):copy(p,root/'train002'/p.name)
    for name in ('README.md','MATH.md','Run.ps1','BASELINE_TRAIN001.json'):copy(here/name,root/name)
    copy(here/'PrepareInitial.kt',root/'train002/PrepareInitial.kt')
    copy(here.parent/'train001/torch_backend.py',root/'train001/torch_backend.py')
    for p in historic.iterdir():
        if p.is_file() and (p.name=='audit.json' or p.name in ('full.jsonl.gz','memory_off.jsonl.gz','zero_values.jsonl.gz','erased.jsonl.gz')):copy(p,root/'historical'/p.name)
    copy(here/'evidence/predictions.jsonl.gz',root/'historical/predictions-summary.jsonl.gz')
    copy(here/'evidence/full_trace_manifest.json',root/'historical/full_trace_manifest.json')
    for p in results.iterdir():
        if p.is_file():copy(p,root/'historical_results'/p.name)
    for name in ('initial.tsv','train.tsv','validation.tsv','test.tsv','erased.tsv'):copy(old_inputs/name,root/'historic_inputs'/name)
    files=sorted(p for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS' and '__pycache__' not in p.parts)
    require(not any('runs' in p.relative_to(root).parts or '.venv' in p.relative_to(root).parts for p in files),'PACKET_CONTAINS_RUNTIME_OUTPUT')
    manifest=''.join(file_sha(p)+'  '+p.relative_to(root).as_posix()+'\n' for p in files);(root/'SHA256SUMS').write_text(manifest)
    files.append(root/'SHA256SUMS');archive=root.with_suffix('.zip')
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,(pathlib.Path(root.name)/p.relative_to(root)).as_posix())
    with zipfile.ZipFile(archive) as z:
        require(z.testzip() is None,'ZIP_CRC')
        for p in files:require(z.read((pathlib.Path(root.name)/p.relative_to(root)).as_posix())==p.read_bytes(),'ZIP_BYTE_ROUNDTRIP')
    print(canonical({'packet':str(archive),'bytes':archive.stat().st_size,'sha256':file_sha(archive),'source':source_identity(),'study_sha256':file_sha(root/'study/study.json'),'files':len(files),'status':'PREPARED_ONLY_NO_NEW_MAIN_TRAINING'}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=pathlib.Path);p.add_argument('historic',type=pathlib.Path);p.add_argument('old_inputs',type=pathlib.Path);p.add_argument('results',type=pathlib.Path);a=p.parse_args();package(a.root,a.historic,a.old_inputs,a.results)
