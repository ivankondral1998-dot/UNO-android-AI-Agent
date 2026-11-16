#!/usr/bin/env python3
"""Restore browsable research texts from Git-backed original UNO ZIPs.

Read-only on repository/archive inputs; standard library, no network/training.
Use a NEW output directory. Binary weights are deliberately not extracted.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile

EXT = {'.py', '.kt', '.md', '.json', '.tsv', '.txt', '.cmd', '.ps1', '.sh'}

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archives', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('output directory must not exist')
    with a.manifest.open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    pending = []
    jobs = []
    for r in rows:
        name = r['filename']
        if Path(name).name != name:
            raise ValueError('unsafe archive filename: ' + name)
        if r['git_path'] == '-':
            pending.append(name)
            continue
        source = a.archives / name
        if not source.is_file() or source.is_symlink():
            raise ValueError('Git-preserved ZIP missing: ' + name)
        raw = source.read_bytes()
        if len(raw) != int(r['bytes']) or sha256(raw) != r['sha256']:
            raise ValueError('source SHA-256/length mismatch: ' + name)
        with zipfile.ZipFile(source) as z:
            members = z.infolist()
            if len(members) != int(r['zip_entries']) or z.testzip() is not None:
                raise ValueError('ZIP CRC/count error: ' + name)
            for m in members:
                path = m.filename.replace(chr(92), '/')
                parts = PurePosixPath(path).parts
                if not parts or path.startswith('/') or '..' in parts or (len(path)>1 and path[1]==':'):
                    raise ValueError('unsafe ZIP member: ' + path)
                if m.is_dir() or PurePosixPath(path).suffix.lower() not in EXT:
                    continue
                data = z.read(m)
                try:
                    data.decode('utf-8-sig')
                except UnicodeDecodeError:
                    raise ValueError('not UTF-8 text: ' + path)
                jobs.append((name, r['sha256'], path, data))
    a.out.mkdir(parents=True)
    records = []
    for name, source_hash, path, data in jobs:
        target = a.out / name.removesuffix('.zip') / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f:
            f.write(data)
        records.append({'archive': name, 'archive_sha256': source_hash,
                        'zip_member': path, 'path': target.relative_to(a.out).as_posix(),
                        'bytes': len(data), 'sha256': sha256(data)})
    manifest = {'status': 'TEXT_EXTRACTED_NOT_NEW_EXPERIMENT',
                'count': len(records), 'git_pending_originals': pending,
                'scope': 'Only source/result texts in ZIPs already preserved in Git; no weights',
                'entries': records}
    (a.out / 'RESEARCH_SOURCES_MANIFEST.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('EXTRACTED',len(records),'text members;',len(pending),'other ZIPs pending in Git')
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print('FAIL CLOSED:', exc, file=sys.stderr)
        sys.exit(1)
