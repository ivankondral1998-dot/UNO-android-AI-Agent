#!/usr/bin/env python3
"""Reassemble a byte-identical UNO original ZIP from its Git-tracked .parts folder.

Usage: python restore_split_zip.py path/to/ORIGINAL.zip.parts output/ORIGINAL.zip
No package dependencies. Refuses to replace an existing output.
"""
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path


def restore(directory: Path, target: Path):
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    if target.exists():
        raise FileExistsError(f'Existing file is protected: {target}')
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', prefix=target.name + '.tmp-', dir=target.parent, delete=False) as out:
            raw = Path(out.name)
            checksum = hashlib.sha256()
            count = 0
            for entry in manifest['parts']:
                part = directory / entry['file']
                data = part.read_bytes()
                if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
                    raise ValueError(f'Bad part integrity: {part}')
                out.write(data)
                checksum.update(data)
                count += len(data)
            out.flush()
            os.fsync(out.fileno())
        if count != manifest['bytes'] or checksum.hexdigest() != manifest['sha256']:
            raise ValueError('Full original ZIP SHA256 or length mismatch')
        os.link(raw, target)  # atomic no-overwrite publication, same filesystem
        print(f'RESTORED_SHA256_OK {target} {count} {checksum.hexdigest()}')
    finally:
        if raw is not None and raw.exists():
            raw.unlink()  # only our own temporary output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parts_directory', type=Path)
    parser.add_argument('destination_zip', type=Path)
    args = parser.parse_args()
    restore(args.parts_directory, args.destination_zip)