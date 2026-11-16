#!/usr/bin/env python3
"""Read-only verifier of UNO original ZIPs and optionally a local Git checkout.

Exit 0: all available local inputs and declared stored Git paths match;
        pending Git uploads are reported, not treated as backups.
When --repo is set, exact ZIPs split into tracked .parts are reconstructed
cryptographically in memory and counted as recoverable, not missing.
Exit 1: missing input/hash/CRC mismatch; exit 2: --require-all-git pending.
Does not extract ZIPs, contact GitHub, write files or launch training.
"""
import argparse
import csv
import hashlib
import json
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




def verify_parts(repo, name, expected_bytes, expected_sha256):
    """Prove that split Git checkout parts reconstruct the exact original ZIP."""
    root = repo / 'research/owner-attachments-20261115/original-zips' / (name + '.parts')
    manifest_path = root / 'manifest.json'
    if not manifest_path.is_file():
        return False
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if (manifest.get('original_filename') != name or
            manifest.get('bytes') != expected_bytes or
            manifest.get('sha256') != expected_sha256):
        raise ValueError('SPLIT_MANIFEST_IDENTITY_MISMATCH')
    parts = manifest.get('parts')
    if not isinstance(parts, list) or not parts:
        raise ValueError('EMPTY_SPLIT_PARTS')
    full = hashlib.sha256()
    total = 0
    seen = set()
    for entry in parts:
        filename = entry.get('file')
        if (not isinstance(filename, str) or
                Path(filename).name != filename or filename in seen):
            raise ValueError('UNSAFE_OR_DUPLICATE_SPLIT_PART_NAME')
        seen.add(filename)
        path = root / filename
        if path.is_symlink() or not path.is_file():
            raise ValueError('SPLIT_PART_MISSING_OR_SYMLINK')
        size = path.stat().st_size
        if size != entry['bytes']:
            raise ValueError('SPLIT_PART_SIZE_MISMATCH')
        part_hash = hashlib.sha256()
        blob_hash = hashlib.sha1(f'blob {size}\0'.encode())
        with path.open('rb') as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b''):
                part_hash.update(chunk)
                blob_hash.update(chunk)
                full.update(chunk)
        if (part_hash.hexdigest() != entry['sha256'] or
                blob_hash.hexdigest() != entry['git_sha1']):
            raise ValueError('SPLIT_PART_HASH_MISMATCH')
        total += size
    if total != expected_bytes or full.hexdigest() != expected_sha256:
        raise ValueError('SPLIT_RESTORED_BYTES_MISMATCH')
    return True

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='directory of original user ZIPs')
    parser.add_argument('--repo', type=Path, help='local checkout of this exact research branch')
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('ARTIFACTS.tsv'))
    parser.add_argument('--require-all-git', action='store_true', help='fail on pending original Git archives')
    args = parser.parse_args()
    failures = []
    pending = []
    split_verified = []
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
            try:
                if args.repo is not None and verify_parts(args.repo, name, int(row['bytes']), row['sha256']):
                    split_verified.append(name)
                    print(f"REPO_SPLIT_OK {name}")
                else:
                    pending.append(name)
                    print(f"GIT_PENDING {name}")
            except (OSError, ValueError, TypeError, KeyError) as exc:
                failures.append(f"REPO_SPLIT_FAIL {name}: {exc}")
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
    direct = sum(row['git_path'] != '-' for row in records)
    print(f"SUMMARY total={len(records)} git_direct_declared={direct} repo_split_verified={len(split_verified)} git_pending={len(pending)} failures={len(failures)}")
    for failure in failures:
        print(failure, file=sys.stderr)
    if failures:
        return 1
    if args.require_all_git and pending:
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
