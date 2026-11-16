#!/usr/bin/env python3
"""Restore browsable original UNO research texts from Git-preserved ZIPs.

Offline, stdlib only. Never writes to sources/repository. Repeated names with
unequal bytes remain separated by archive ID; originals are not edited.
"""
import argparse
import csv
import hashlib
import json
import pathlib
import shutil
import sys
import zipfile

TEXT_SUFFIXES = {'.py', '.kt', '.md', '.json', '.tsv', '.txt', '.cmd', '.ps1', '.sh'}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def safe_name(name):
    name = name.replace('\\', '/')
    parts = name.split('/')
    return bool(name) and not name.startswith('/') and not (len(name) > 1 and name[1] == ':') and all(p not in ('.', '..') for p in parts)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archives', type=pathlib.Path, required=True,
                    help='research/owner-attachments-20261115/original-zips in Git checkout')
    ap.add_argument('--manifest', type=pathlib.Path, required=True,
                    help='ARTIFACTS.tsv from same checkout')
    ap.add_argument('--out', type=pathlib.Path, required=True, help='NEW empty output directory')
    args = ap.parse_args()
    if args.out.exists():
        raise ValueError('output already exists; refuses overwrite: '+str(args.out))
    with args.manifest.open(encoding='utf-8', newline='') as f:
        rows=list(csv.DictReader(f, delimiter='\t'))
    jobs=[]
    for r in rows:
        if r['git_path']=='-':
            continue # no original binary in Git, do not invent its content
        src=args.archives/r['filename']
        if src.is_symlink() or not src.is_file():
            raise ValueError('missing original ZIP: '+str(src))
        blob=src.read_bytes()
        if len(blob)!=int(r['bytes']) or digest(blob)!=r['sha256']:
            raise ValueError('ZIP mismatch: '+r['filename'])
        with zipfile.ZipFile(src) as z:
            if len(z.infolist())!=int(r['zip_entries']) or z.testzip():
                raise ValueError('ZIP CRC/count failure: '+r['filename'])
            for item in z.infolist():
                if not safe_name(item.filename):
                    raise ValueError('unsafe ZIP path '+item.filename)
                if item.is_dir() or pathlib.PurePosixPath(item.filename).suffix.lower() not in TEXT_SUFFIXES:
                    continue
                data=z.read(item)
                try:
                    data.decode('utf-8-sig')
                except UnicodeError:
                    raise ValueError('non UTF-8 research text '+item.filename)
                jobs.append((r['filename'], r['sha256'], item.filename.replace('\\','/'),data))
    # Preflight above is all-or-nothing; do not touch a preexisting destination.
    args.out.mkdir(parents=True)
    record=[]
    for archive, hash_zip, member, data in jobs:
        target=args.out/archive.removesuffix('.zip')/member
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            raise ValueError('duplicate member path '+str(target))
        target.write_bytes(data)
        record.append({'archive':archive,'archive_sha256':hash_zip,'zip_member':member,
                       'path':target.relative_to(args.out).as_posix(),
                       'bytes':len(data),'sha256':digest(data)})
    (args.out/'RESEARCH_SOURCES_MANIFEST.json').write_text(
        json.dumps({'status':'EXTRACTED_TEXT_ONLY','not_included':'binary weights/checkpoints, absent Git archives, pyc',
                    'count':len(record),'entries':record},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'EXTRACTED {len(record)} text members from {len({x[0] for x in jobs})} Git-preserved ZIPs')
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except (OSError,ValueError,zipfile.BadZipFile) as e:
        print('FAIL:',e,file=sys.stderr);sys.exit(1)
