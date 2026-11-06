"""Verify the delivery and pinned source identities without executing the fixtures."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
MANIFEST = "SHA256_MANIFEST.json"
PREFIX = "docs/precode/r5.3/source-package/"


def load_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def blob_sha(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def require(condition, label):
    if not condition:
        raise RuntimeError(label)


def main():
    manifest = load_json(MANIFEST)
    actual = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()}
    require(actual == set(manifest) | {MANIFEST}, "Archive file list mismatch")
    for name, expected in manifest.items():
        content = (ROOT / name).read_bytes()
        require(len(content) == expected["bytes"] and sha256(content) == expected["sha256"], name)

    tree = load_json("evidence/REMOTE_TREE_EFDB1767.json")
    require(not tree.get("truncated"), "Pinned tree was truncated")
    blobs = {item["path"]: item for item in tree["tree"] if item["type"] == "blob"}
    imported = load_json("sources/SOURCE_PACKAGE_IMPORT_MANIFEST.json")["files"]
    origin = load_json("sources/source-package/SHA256_MANIFEST.json")["files"]
    require(len(imported) == 64 and len(origin) == 63, "Source manifest cardinality")
    for row in imported:
        path = row["repo_path"]
        require(path.startswith(PREFIX), path)
        raw = (ROOT / "sources/source-package" / path.removeprefix(PREFIX)).read_bytes()
        require(len(raw) == row["bytes"] and sha256(raw) == row["sha256"], path)
        require(blob_sha(raw) == row["git_blob_sha1"] == blobs[path]["sha"], path)
    for row in origin:
        raw = (ROOT / "sources/source-package" / row["path"]).read_bytes()
        require(len(raw) == row["bytes"] and sha256(raw) == row["sha256"], row["path"])

    tests = load_json("evidence/V01_V20_INTEGRITY.json")["blocks"]
    require({row["id"] for row in tests} == {f"V{i:02}" for i in range(1, 21)} and len(tests) == 20,
            "V manifest cardinality")
    for row in tests:
        name = f"{row['id']}_{row['name']}"
        raw = (ROOT / "evidence/v_sources" / name).read_bytes()
        require(sha256(raw) == row["expected_sha256"], name)
        ast.parse(raw, filename=name)

    gates = (ROOT / "R53_ORIGINAL_INDIVIDUAL_GATES.md").read_text(encoding="utf-8")
    actual_ids = Counter(re.findall(r"^\|\s*([DXBM]\d{2})\s*\|", gates, re.M))
    expected_ids = {f"{prefix}{i:02}" for prefix, count in (("D",10),("X",12),("B",14),("M",44))
                    for i in range(1, count + 1)}
    require(set(actual_ids) == expected_ids and all(v == 1 for v in actual_ids.values()), "Gate IDs")
    print(f"DELIVERY_INTEGRITY_OK files={len(manifest)} source_git_blobs=64 source_sha256=63 V_blocks=20 gates=80")


if __name__ == "__main__":
    main()
