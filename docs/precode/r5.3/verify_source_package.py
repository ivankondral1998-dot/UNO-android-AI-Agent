#!/usr/bin/env python3
"""Read-only UNO R5.3 source-package integrity verifier (no network, no CI)."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def verify(repo_root: Path) -> int:
    base = repo_root / "docs/precode/r5.3"
    mapping = json.loads((base / "SOURCE_PACKAGE_IMPORT_MANIFEST.json").read_text(encoding="utf-8"))
    source_manifest = json.loads((base / "source-package/SHA256_MANIFEST.json").read_text(encoding="utf-8"))
    rows = mapping["files"]
    errors = []
    if len(rows) != 64:
        errors.append(f"expected 64 source files, found {len(rows)}")
    source_rows = source_manifest.get("files", [])
    source_by_path = {x["path"]: x for x in source_rows}
    if len(source_rows) != 63 or len(source_by_path) != 63:
        errors.append(f"original SHA256 manifest must index 63 unique nonself files, got {len(source_rows)}")
    if len(set(x["original"] for x in rows)) != len(rows):
        errors.append("duplicate original paths")
    binary = 0
    for item in rows:
        original = item["original"]
        expected_path = "docs/precode/r5.3/source-package/" + original
        if item["repo_path"] != expected_path:
            errors.append("bad mapping: " + original)
            continue
        file_path = repo_root / expected_path
        if not file_path.is_file():
            errors.append("missing: " + original)
            continue
        content = file_path.read_bytes()
        if len(content) != item["bytes"]:
            errors.append("size mismatch: " + original)
        sha = hashlib.sha256(content).hexdigest()
        if sha != item["sha256"]:
            errors.append("SHA256 mismatch: " + original)
        git_sha = git_blob_sha(content)
        if git_sha != item["git_blob_sha1"]:
            errors.append("Git blob SHA mismatch: " + original)
        if original != "SHA256_MANIFEST.json":
            rec = source_by_path.get(original)
            if not rec or rec["bytes"] != len(content) or rec["sha256"] != sha:
                errors.append("source manifest mismatch: " + original)
        if original.endswith(".zip"):
            binary += 1
            try:
                with zipfile.ZipFile(file_path) as z:
                    bad = z.testzip()
                    if bad:
                        errors.append(f"nested ZIP CRC failed: {original} -> {bad}")
            except (OSError, zipfile.BadZipFile) as exc:
                errors.append(f"nested ZIP cannot be read: {original}: {exc}")
    if binary != 3:
        errors.append(f"expected 3 nested ZIP source archives, got {binary}")
    if set(source_by_path) != set(x["original"] for x in rows) - {"SHA256_MANIFEST.json"}:
        errors.append("source manifest set differs from imported source set")
    print(f"UNO R5.3 source-package: {len(rows)} records, {binary} ZIPs, {len(errors)} errors")
    for error in errors:
        print("FAIL:", error)
    return 1 if errors else 0


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]
    sys.exit(verify(root))
