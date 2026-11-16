#!/usr/bin/env python3
"""Read-only UNO archive audit; standard library only. No network, writes or training."""
import argparse, csv, hashlib, json, pathlib, sys, zipfile

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def check_zip(path):
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad: raise ValueError('CRC '+bad)
        for x in z.namelist():
            q = x.replace('\\','/')
            if q.startswith('/') or '..' in q.split('/') or (len(q)>1 and q[1]==':'):
                raise ValueError('unsafe ZIP member '+repr(x))
        return len(z.infolist())

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=pathlib.Path,required=True)
    p.add_argument('--manifest',type=pathlib.Path,required=True)
    p.add_argument('--extras',type=pathlib.Path)
    p.add_argument('--repo',type=pathlib.Path)
    p.add_argument('--require-all-git',action='store_true')
    a=p.parse_args()
    with a.manifest.open(encoding='utf-8',newline='') as f:
        rows=list(csv.DictReader(f,delimiter='\t'))
    errors=[]; result=[]
    for r in rows:
        name=r['filename']; local=a.source/name
        item={'name':name,'bytes':int(r['bytes']),'git_path':r['git_path'],'source':'MISSING','git':'PENDING'}
        try:
            if local.stat().st_size!=item['bytes'] or sha(local)!=r['sha256']:
                raise ValueError('source size/hash mismatch')
            if check_zip(local)!=int(r['zip_entries']):raise ValueError('ZIP member count mismatch')
            item['source']='PASS'
        except (OSError,ValueError,zipfile.BadZipFile) as e:errors.append(name+': '+str(e))
        if r['git_path']!='-':
            item['git']='DECLARED_UNCHECKED'
            if a.repo:
                remote=a.repo/r['git_path']
                try:
                    if remote.stat().st_size!=item['bytes'] or sha(remote)!=r['sha256']:
                        raise ValueError('Git checkout bytes mismatch or LFS pointer')
                    item['git']='PASS'
                except (OSError,ValueError) as e:
                    item['git']='FAIL';errors.append(name+' Git: '+str(e))
        result.append(item)
    extras=[]
    if a.extras:
        with a.extras.open(encoding='utf-8',newline='') as f:
            for r in csv.DictReader(f,delimiter='\t'):
                extras.append({'name':r['original_name'],'bytes':int(r['bytes']),'sha256':r['sha256'],'status':r['status'],'source':'NOT_AVAILABLE_BY_FILENAME'})
    pending=sum(x['git']=='PENDING' for x in result)+sum('PENDING' in x['status'] for x in extras)
    report={'status':'FAIL' if errors else ('PARTIAL_BACKUP' if pending else 'DECLARED_BACKUP'),
            'originals':result,'historic_versions':extras,'pending_git':pending,'errors':errors,
            'note':'DECLARED_UNCHECKED is not verified remote storage. Earlier same-name versions need distinct source paths.'}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 1 if errors else (2 if a.require_all_git and pending else 0)

if __name__=='__main__':sys.exit(main())
