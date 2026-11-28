"""Read-only independent audit of normalized cross-split keys in FIX04 data."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from trainer import corpus_identity
from core import SPLITS


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().replace("ё", "е").split())


def digest(prefix, text):
    return (prefix, hashlib.sha256(text.encode()).digest())


def keys(row, kind):
    if kind == "language":
        text = normalize(row["text"])
        yield digest("text", text)
        yield digest("prompt", " ".join(re.findall(r"\w+", text)))
        if row.get("meta", {}).get("work_key"):
            yield digest("work", row["meta"]["work_key"])
    elif kind == "intent":
        yield digest("prompt", " ".join(re.findall(r"\w+", normalize(row["text"]))))
    else:
        messages = [(m["role"], normalize(m["text"])) for m in row["messages"]]
        yield digest("dialogue", json.dumps(messages, ensure_ascii=False))
        for role, text in messages:
            if role == "user":
                yield digest("prompt", " ".join(re.findall(r"\w+", text)))
            if len(text.split()) >= 6:
                yield digest("text", text)


def audit(root):
    manifest = corpus_identity(root, lambda: None)
    holdout = {}
    overlaps = Counter()
    rows = Counter()
    for split in reversed(SPLITS):
        for kind in ("language", "dialogue", "intent"):
            path = root / kind / f"{split}.jsonl"
            if kind == "intent" and not path.is_file():
                continue
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    row = json.loads(line)
                    rows[f"{split}/{kind}/{row['source']}"] += 1
                    collision = set()
                    for key in set(keys(row, kind)):
                        old = holdout.get(key)
                        if old and old != split:
                            collision.add(old)
                        if split != "train":
                            holdout.setdefault(key, split)
                    for other in collision:
                        overlaps[f"{split}/{other}/{kind}"] += 1
    return {"manifest": manifest, "rows": dict(rows), "overlaps": dict(overlaps)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    result = audit(parser.parse_args().data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(bool(result["overlaps"]))
