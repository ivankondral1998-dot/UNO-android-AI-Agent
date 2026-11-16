#!/usr/bin/env python3
"""Fail-closed Git publisher for missing UNO research ZIPs (existing branch only).

Run from an authenticated Git checkout with Python 3, git and git-lfs for >100MB.
Dry run unless --apply; never creates branches, overwrites originals or forces push.
"""
import argparse
import csv
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

BRANCH = "research/uno-train-001-s4-20261115"
ROOT = "research/owner-attachments-20261115"
DEST = ROOT + "/original-zips"


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def rows(file):
    with file.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--early-source", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    repo = a.repo.resolve()
    if git(repo, "branch", "--show-current") != BRANCH:
        raise ValueError("Wrong branch; checkout EXISTING research branch")
    if git(repo, "status", "--porcelain"):
        raise ValueError("Worktree not clean; refusing to touch user changes")
    if "ivankondral1998-dot/UNO-android-AI-Agent" not in git(repo, "remote", "get-url", "origin"):
        raise ValueError("Wrong origin")
    base = repo / ROOT
    missing = []
    for r in rows(base / "ARTIFACTS.tsv"):
        if r["git_path"] == "-":
            name = r["filename"]
            missing.append((a.source / name, DEST + "/" + name,
                            int(r["bytes"]), r["sha256"], int(r["zip_entries"])))
    for r in rows(base / "EXTRA_VERSIONS.tsv"):
        if r["status"].startswith("GIT_PENDING"):
            name = r["original_name"]
            missing.append((a.early_source / name, DEST + "/early-v1/" + name,
                            int(r["bytes"]), r["sha256"], int(r["zip_entries"])))
    if len({x[1] for x in missing}) != len(missing):
        raise ValueError("Duplicate destination")
    # Check all source bytes and all destinations before any mutation.
    for src, relative, size, digest, expected_entries in missing:
        if src.is_symlink() or not src.is_file() or src.stat().st_size != size or sha(src) != digest:
            raise ValueError("Source identity mismatch: " + str(src))
        with zipfile.ZipFile(src) as z:
            if len(z.infolist()) != expected_entries or z.testzip() is not None:
                raise ValueError("ZIP CRC/entry failure: " + str(src))
            for name in z.namelist():
                norm = name.replace("\\", "/")
                if norm.startswith("/") or ".." in norm.split("/") or (len(norm) > 1 and norm[1] == ":"):
                    raise ValueError("Unsafe ZIP member: " + name)
        dst = repo / relative
        if dst.exists() or dst.is_symlink():
            if dst.is_symlink() or dst.stat().st_size != size or sha(dst) != digest:
                raise ValueError("Destination would overwrite different original: " + relative)
    print("SOURCE ZIP PASS:", len(missing))
    for _, rel, size, digest, _ in missing:
        print(f"{size} {digest} {rel}")
    if not a.apply:
        print("DRY RUN: no commit, upload or branch change")
        return
    git(repo, "fetch", "--no-tags", "origin", "refs/heads/" + BRANCH)
    if git(repo, "rev-parse", "HEAD") != git(repo, "rev-parse", "FETCH_HEAD"):
        raise ValueError("Stale checkout; refuses to rebase/overwrite")
    big = [r for r in missing if r[2] > 100000000]
    if big:
        git(repo, "lfs", "version")  # Must exist before any copies
        git(repo, "lfs", "install", "--local")
        for _, relative, _, _, _ in big:
            git(repo, "lfs", "track", relative)
    staged = []
    for src, rel, size, digest, _ in missing:
        dst = repo / rel
        if dst.is_file():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        if dst.stat().st_size != size or sha(dst) != digest:
            raise ValueError("Copy verification failed: " + rel)
        staged.append(rel)
    if git(repo, "status", "--porcelain", "--", ".gitattributes"):
        staged.append(".gitattributes")
    if not staged:
        print("Already present. No changes made.")
        return
    git(repo, "add", "--", *staged)
    git(repo, "diff", "--cached", "--check")
    for _, rel, size, digest, _ in missing:
        if rel not in staged:
            continue
        if git(repo, "check-attr", "filter", "--", rel).endswith(": lfs"):
            pointer = git(repo, "show", ":" + rel)
            if ("oid sha256:" + digest) not in pointer or ("size " + str(size)) not in pointer:
                raise ValueError("Staged LFS pointer mismatch: " + rel)
        else:
            if size > 100000000 or git(repo, "hash-object", "--no-filters", "--", rel) != git(repo, "rev-parse", ":" + rel):
                raise ValueError("Staged Git blob mismatch: " + rel)
    git(repo, "commit", "-m", "archive(research): preserve original UNO ZIPs [skip ci]")
    git(repo, "push", "origin", "HEAD:refs/heads/" + BRANCH)  # Never force
    git(repo, "fetch", "--no-tags", "origin", "refs/heads/" + BRANCH)
    if git(repo, "rev-parse", "HEAD") != git(repo, "rev-parse", "FETCH_HEAD"):
        raise ValueError("Remote HEAD differs after push")
    print("PUSHED (Git HEAD verified). Retrieve/hash LFS objects independently before marking COMPLETE.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as e:
        print("FAIL CLOSED:", e, file=sys.stderr)
        sys.exit(1)
