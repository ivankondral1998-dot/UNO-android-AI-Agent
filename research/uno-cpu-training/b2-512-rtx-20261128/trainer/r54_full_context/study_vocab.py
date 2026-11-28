"""Train-only VOCAB04 compression check on the earlier curated JSONL, outside V4."""
import argparse
import json
from pathlib import Path
import random
import statistics
import sys
import time

from trainer import Codec

EXPERIMENT = Path(__file__).resolve().parents[2] / "experiments" / "b2_vocab04"
sys.path.append(str(EXPERIMENT))
from extend_vocab04 import extend, validate_extension
from train_cuda_fast03 import TOK_SHA, sha


def prompts(path, n, seed):
    items = []
    rng = random.Random(seed)
    with path.open(encoding="utf8") as stream:
        for i, line in enumerate(stream):
            if i < n:
                j = i
            else:
                j = rng.randrange(i + 1)
            if j < n:
                row = json.loads(line)["turns"]
                if i < n:
                    items.append(row)
                else:
                    items[j] = row
    return items


def codec_from(profile, base):
    codec = Codec()
    codec.ids = profile["active_ids"]
    codec.allowed = set(codec.ids)
    codec.rules = {(a, b): (i, c) for i, (a, b, c) in enumerate(profile["merges"])}
    codec.tokens = {int(i): bytes.fromhex(v) for i, v in profile["tokens_hex"].items()}
    assert set(base["active_ids"]).issubset(codec.allowed)
    return codec


def measure(codec, rows):
    start = time.monotonic()
    lengths = []
    encoded = 0
    for turns in rows:
        assert len(turns) >= 2 and len(turns) % 2 == 0
        item = {"messages": [{"role": "user" if i % 2 == 0 else "assistant", "text": text}
                             for i, text in enumerate(turns)]}
        for text in turns:
            tokens = codec.encode(text)
            assert b"".join(codec.tokens[i] for i in tokens) == text.encode()
            encoded += len(tokens)
        tokens, mask = codec.record(item, "dialogue")
        lengths.append((len(tokens) - 1, mask.index(True)))
    count = len(codec.ids)
    return {"active_ids": count, "dialogues": len(lengths), "raw_text_tokens": encoded,
            "median_dialogue_tokens": statistics.median(n for n, _ in lengths),
            "full_dialogue_at_128": sum(n <= 128 for n, _ in lengths),
            "full_dialogue_at_512": sum(n <= 512 for n, _ in lengths),
            "question_and_marker_at_128": sum(p <= 128 for _, p in lengths),
            "compact_text_weight_mib_fp32": count * 513 * 4 / 2**20,
            "encoding_wall_seconds_single_run": time.monotonic() - start}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("curated", type=Path)
    args = parser.parse_args()
    train = args.curated / "train.dialogue.jsonl"
    dev = args.curated / "validation.dialogue.jsonl"
    base = json.loads((Path(__file__).resolve().parents[1] / "tokenizer.json").read_text())
    codec = Codec()
    chunks = []
    for turns in prompts(train, 512, 54):
        for text in turns:
            ids = codec.encode(text)
            chunks.extend(tuple(ids[i:i+48]) for i in range(0, len(ids), 48))
    held = prompts(dev, 256, 54)
    digest = sha(train)
    results = [measure(codec, held)]
    for target in (1024, 2048):
        t = extend(base, chunks, target)
        t["extension"] = {"parent_sha256": TOK_SHA, "corpus_manifest_sha256": digest}
        validate_extension(t, base, digest)
        results.append(measure(codec_from(t, base), held))
    print(json.dumps({"train_sha256": digest, "validation_sha256": sha(dev),
                      "results": results}, indent=2))


if __name__ == "__main__":
    main()
