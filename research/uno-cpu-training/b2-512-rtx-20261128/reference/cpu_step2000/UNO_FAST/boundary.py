"""Periodic atomic checkpoints with independently verified previous copy."""
import hashlib
import os
from pathlib import Path
import time
import uuid
from guard import disk_admit
from train001_backend import atomic, restore

def previous(path):
    return path.with_name("previous.uno")

def verified_bytes(path):
    if not 1 <= path.stat().st_size <= 64*1024*1024 + 128:
        raise ValueError("CHECKPOINT_SIZE")
    data = path.read_bytes()
    head, digest, body = data.split(b"\n",2)
    if head != b"UNO-TORCH-S4/V1" or hashlib.sha256(body).hexdigest().encode() != digest:
        raise ValueError("CHECKPOINT_INTEGRITY")
    return data

def verify_file(path):
    with path.open("rb") as stream:
        size = os.fstat(stream.fileno()).st_size
        if not 1 <= size <= 64*1024*1024+128:
            raise ValueError("CHECKPOINT_SIZE")
        if stream.readline(32) != b"UNO-TORCH-S4/V1\n":
            raise ValueError("CHECKPOINT_INTEGRITY")
        digest = stream.readline(66)
        if len(digest) != 65 or not digest.endswith(b"\n"):
            raise ValueError("CHECKPOINT_INTEGRITY")
        if hashlib.file_digest(stream,"sha256").hexdigest().encode()+b"\n" != digest:
            raise ValueError("CHECKPOINT_INTEGRITY")

def save_boundary(save, path):
    disk_admit(path)
    if path.exists():
        verify_file(path)
        # Both names initially reference the same immutable checkpoint.
        # The checkpoint writer MUST replace, never mutate, its destination.
        # If the filesystem has no hardlinks, retain the old verified-copy path.
        link = path.with_name(".uno-previous-"+uuid.uuid4().hex+".tmp")
        try:
            try:
                os.link(path,link)
            except OSError:
                atomic(previous(path),verified_bytes(path))
            else:
                os.replace(link,previous(path))
        finally:
            if link.exists():
                link.unlink()
    save(path)

def load_boundary(load, path, quarantine=False):
    # Only fallback for missing/corrupt byte container, not config/model mismatch.
    try:
        verify_file(path)
    except (ValueError, FileNotFoundError):
        backup = previous(path)
        verify_file(backup)
        result = load(backup)
        if quarantine and path.exists():
            bad = path.with_name(f"latest.corrupt-{time.time_ns()}.uno")
            os.rename(path,bad)
        print(f"RECOVERED: {backup}",flush=True)
        return result
    return load(path)
