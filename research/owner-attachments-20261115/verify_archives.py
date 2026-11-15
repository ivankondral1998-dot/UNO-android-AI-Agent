#!/usr/bin/env python3
"""Read-only verifier of UNO original ZIPs and optionally a local Git checkout.

Exit 0: all available local inputs and declared stored Git paths match;
        pending Git uploads are reported, not treated as backups.
Exit 1: missing input/hash/CRC mismatch; exit 2: --require-all-git pending.
Does not extract ZIPs, contact GitHub, write files or launch training.
"""
import argparse
import csv
import hashlib
import sys
import zipfile
from pathlib import Path, PurePosixPath


def hashes(path):
    size = path.stat().st_size
    sha256 = hashlib.sha256()
    blob = hashlib.sha1(f"blob {size}\0".encode())
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            sha256.update(chunk)
            blob.update(chunk)
    return size, sha256.hexdigest(), blob.hexdigest()


def safe_member(name):
    normalized = name.replace('\\', '/')
    parts = PurePosixPath(normalized).parts
    return bool(parts) and not normalized.startswith('/') and '..' not in parts and not (len(normalized) >= 2 and normalized[1] == ':')


def check_zip(path, expected):
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) != expected:
            raise ValueError(f"ZIP_ENTRY_COUNT {len(members)} != {expected}")
        for item in members:
            if not safe_member(item.filename):
                raise ValueError(f"UNSAFE_ZIP_PATH {item.filename!r}")
        bad = archive.testzip()
        if bad is not None:
            raise ValueError(f"ZIP_CRC {bad}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='directory of original user ZIPs')
    parser.add_argument('--repo', type=Path, help='local checkout of this exact research branch')
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('ARTIFACTS.tsv'))
    parser.add_argument('--require-all-git', action='store_true', help='fail on pending original Git archives')
    args = parser.parse_args()
    failures = []
    pending = []
    seen = set()
    with args.manifest.open(encoding='utf-8', newline='') as fh:
        records = list(csv.DictReader(fh, delimiter='\t'))
    for row in records:
        name = row['filename']
        if name in seen or Path(name).name != name:
            failures.append(f"BAD_MANIFEST_NAME {name}")
            continue
        seen.add(name)
        local = args.source / name
        try:
            if not local.is_file():
                raise ValueError('SOURCE_MISSING')
            if hashes(local) != (int(row['bytes']), row['sha256'], row['git_blob_sha1']):
                raise ValueError('SOURCE_HASH_MISMATCH')
            check_zip(local, int(row['zip_entries']))
            print(f"LOCAL_OK {name}")
        except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
            failures.append(f"LOCAL_FAIL {name}: {exc}")
        git_path = row['git_path']
        if git_path == '-':
            pending.append(name)
            print(f"GIT_PENDING {name}")
        elif args.repo is not None:
            remote = args.repo / git_path
            try:
                if not remote.is_file():
                    raise ValueError('REPO_PATH_MISSING_OR_LFS_POINTER')
                if hashes(remote) != (int(row['bytes']), row['sha256'], row['git_blob_sha1']):
                    raise ValueError('REPO_HASH_MISMATCH_OR_LFS_POINTER')
                print(f"REPO_OK {name}")
            except (OSError, ValueError) as exc:
                failures.append(f"REPO_FAIL {name}: {exc}")
    print(f"SUMMARY total={len(records)} git_declared={len(records)-len(pending)} git_pending={len(pending)} failures={len(failures)}")
    for failure in failures:
        print(failure, file=sys.stderr)
    if failures:
        return 1
    if args.require_all_git and pending:
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
