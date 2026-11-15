#!/usr/bin/env python3
"""Rebuild 005B training program sources from seven byte-preserved original ZIPs.

Read-only against inputs, never loads model weights or executes source code.
Usage: python rebuild_005b_programs_from_git.py ORIGINAL_ZIPS_DIRECTORY OUTPUT_ZIP
"""
import hashlib
import sys
import zipfile
from pathlib import Path

NAMES = (
    'UNO_F_PILOT_001.zip',
    'UNO_GPU_SAFE_002.zip',
    'UNO_F_MEMORY_003.zip',
    'UNO_F_WORKING_MEMORY_004.zip',
    'UNO_F_LADDER_005.zip',
    'UNO_F_LADDER_005_SAFE.zip',
    'UNO_F_LADDER_005B.zip',
)
EXTENSIONS = ('.py', '.cmd', '.ps1', '.md')


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    root, output = Path(sys.argv[1]), Path(sys.argv[2])
    count, seen = 0, set()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as dest:
        for package in NAMES:
            with zipfile.ZipFile(root / package) as src:
                if src.testzip() is not None:
                    raise ValueError('Corrupt input: ' + package)
                for name in src.namelist():
                    if not name.lower().endswith(EXTENSIONS):
                        continue
                    if name.startswith('/') or '..' in Path(name).parts or name in seen:
                        raise ValueError('Unsafe/duplicate path: ' + name)
                    dest.writestr(name, src.read(name))
                    seen.add(name)
                    count += 1
    if count != 48:
        raise ValueError(f'Expected 48 program files, got {count}')
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None or any(n.endswith('.pt') for n in z.namelist()):
            raise ValueError('Invalid source-only archive')
    print('OK, program entries:', count, 'archive_sha256:', hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
