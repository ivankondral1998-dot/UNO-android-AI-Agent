"""Read the pinned UNO corpus without unpacking or modifying it."""
import argparse
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

CORPUS_SHA = "dd6b529194ac6833bb843f4197b75636536c53bafd29f28faa5a151a60726422"
TOKENIZER_SHA = "1c622409b42d96d339505d15d69da66d7176788f358e828672970c3ee637474f"
SPLITS = ("train", "validation", "test")


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def window_bounds(length, size):
    """A window owns [start, stop) source positions; its labels start at start+1."""
    require(length >= 2 and size > 0, "invalid window dimensions")
    for start in range(0, length - 1, size):
        yield start, min(start + size, length - 1)


def windows(documents, size):
    for doc_id, sequence in enumerate(documents):
        for start, stop in window_bounds(len(sequence), size):
            yield doc_id, start == 0, sequence[start:stop], sequence[start + 1:stop + 1]


def baselines(train, validation, active_count, smoothing=0.1, limit=None):
    targets = Counter()
    transitions = Counter()
    outgoing = Counter()
    for doc in train:
        targets.update(doc[1:])
        transitions.update(zip(doc, doc[1:]))
        outgoing.update(doc[:-1])
    denominator = sum(targets.values()) + smoothing * active_count
    uni_loss, bi_loss, count = 0.0, 0.0, 0
    for doc in validation:
        for source, target in zip(doc, doc[1:]):
            if limit is not None and count >= limit:
                break
            uni_loss += math.log(denominator / (targets[target] + smoothing))
            bi_loss += math.log((outgoing[source] + smoothing * active_count) /
                                (transitions[source, target] + smoothing))
            count += 1
    return {
        "data": "prose validation", "smoothing": smoothing, "vocabulary": active_count,
        "validation_targets": count, "unigram_nll": uni_loss / count,
        "bigram_nll": bi_loss / count, "unigram_ppl": math.exp(uni_loss / count),
        "bigram_ppl": math.exp(bi_loss / count),
    }


def encode_prompt(prompt, tokenizer):
    # Reuse the pinned BPE merge order, applying each pair left to right.
    seq = list(prompt.encode("utf-8"))
    for first, second, merged in tokenizer["merges"]:
        result, i = [], 0
        while i < len(seq):
            if i + 1 < len(seq) and seq[i] == first and seq[i + 1] == second:
                result.append(merged)
                i += 2
            else:
                result.append(seq[i])
                i += 1
        seq = result
    return seq

def validate_tokenizer(tokenizer):
    ids=tokenizer["active_ids"]
    require(len(ids)==len(set(ids))==514 and all(type(i) is int for i in ids),
            "invalid active token inventory")
    bos,eos=tokenizer["bos"],tokenizer["eos"]
    require(type(bos) is int and type(eos) is int and bos!=eos,"invalid BOS/EOS")
    stems={int(k):bytes.fromhex(v) for k,v in tokenizer["tokens_hex"].items()}
    known={i:bytes([i]) for i in range(256)}
    for first,second,merged in tokenizer["merges"]:
        require(all(type(x) is int for x in (first,second,merged)) and
                first in known and second in known and merged not in known and
                merged not in (bos,eos),"invalid merge order")
        known[merged]=known[first]+known[second]
    require(bos not in known and eos not in known and known==stems and
            set(ids)==set(known)|{bos,eos},"invalid tokenizer byte mapping")
    return stems


def inspect(path):
    with path.open("rb") as file:
        require(path.stat().st_size == 2595563, "unexpected archive size")
        require(hashlib.file_digest(file, "sha256").hexdigest() == CORPUS_SHA, "archive SHA-256 mismatch")
    report = {"corpus_sha256": CORPUS_SHA, "tokenizer_sha256": TOKENIZER_SHA, "sets": {}}
    with ZipFile(path) as archive:
        manifest = archive.read("SHA256SUMS").decode().splitlines()
        entries = [line.split("  ", 1) for line in manifest]
        listed = {name for _, name in entries}
        names = archive.namelist()
        require(len(names) == len(set(names)) == len(entries) + 1 and
                set(names) == listed | {"SHA256SUMS"}, "archive manifest mismatch")
        for checksum, name in entries:
            require(hashlib.sha256(archive.read(name)).hexdigest() == checksum, f"payload hash: {name}")
        report["manifest_members"] = len(entries)
        tokenizer_bytes = archive.read("uno_b2/tokenizer.json")
        require(hashlib.sha256(tokenizer_bytes).hexdigest() == TOKENIZER_SHA, "unexpected tokenizer")
        tokenizer = json.loads(tokenizer_bytes)
        active = set(tokenizer["active_ids"])
        stems = validate_tokenizer(tokenizer)
        bos, eos = tokenizer["bos"], tokenizer["eos"]
        require(len(active) == 514 and set(stems) | {bos, eos} == active, "invalid tokenizer vocabulary")
        report["active_token_ids"] = len(active)
        all_ids = set()
        canonical_works = set()
        canonical_tokens = 0
        work_splits = {}
        prose_author_splits = {}
        normalized_splits = {}
        works = {row["work_id"]: row for row in read_rows(archive, "evidence/works.jsonl")}
        report["works"] = len(works)
        report["author_death_years"] = [min(w["author_death_year"] for w in works.values()),
                                       max(w["author_death_year"] for w in works.values())]
        for kind in ("language", "dialogues"):
            dataset = json.loads(archive.read(f"uno_b2/{kind}/data.json"))
            holdout = json.loads(archive.read(f"uno_b2/{kind}/holdout.json"))
            require(set(dataset) == {"train", "dev"} and set(holdout) == {"test"}, "invalid split keys")
            for split, documents in zip(SPLITS, (dataset["train"], dataset["dev"], holdout["test"]), strict=True):
                rows = read_rows(archive, f"corpus/{kind}/{split}.jsonl")
                tokens = 0
                for row, doc in zip(rows, documents, strict=True):
                    identifier, work_id = row["id"], row["work_id"]
                    work = works[work_id]
                    require(identifier not in all_ids and row["lang"] == "ru", "invalid record identity")
                    all_ids.add(identifier)
                    require(work["corpus"] == kind and work["split"] == split, "work split mismatch")
                    require(work_splits.setdefault(work_id, split) == split, "work leakage")
                    if kind == "language":
                        author = work["author"]
                        require(prose_author_splits.setdefault(author, split) == split, "prose author leakage")
                        text = clean = row["text"]
                    else:
                        require(row["genre"] == "literary_drama", "unexpected dialogue source")
                        text = "\n".join(f"{turn['speaker']}: {turn['text']}" for turn in row["turns"])
                        clean = "\n".join(turn["text"] for turn in row["turns"])
                    normalized = " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", clean).casefold()))
                    require(normalized_splits.setdefault(normalized, split) == split, "exact text leakage")
                    require(len(doc) > 2 and doc[0] == bos and doc[-1] == eos and
                            all(type(i) is int and i in stems for i in doc[1:-1]), "invalid token sequence")
                    require(b"".join(stems[i] for i in doc[1:-1]) == text.encode("utf-8"), "token/text mismatch")
                    if work_id not in canonical_works:
                        encoded = encode_prompt(text,tokenizer)
                        require([bos,*encoded,eos]==doc,"canonical BPE mismatch")
                        canonical_works.add(work_id)
                        canonical_tokens += len(encoded)
                    tokens += len(doc)
                predictable = sum(len(doc) - 1 for doc in documents)
                total_windows, window_targets = 0, 0
                for _, _, inputs, targets in windows(documents, 16):
                    require(len(inputs) == len(targets) and 1 <= len(inputs) <= 16, "invalid window")
                    total_windows += 1
                    window_targets += len(targets)
                require(window_targets == predictable, "skipped or repeated target")
                report["sets"][f"{kind}/{split}"] = {
                    "records": len(rows), "tokens": tokens, "targets": predictable, "windows16": total_windows}
            if kind == "language":
                report["baselines"] = baselines(dataset["train"], dataset["dev"], len(active))
        require(canonical_works == set(works),"missing canonical work coverage")
        report["canonical_works_checked"]=len(canonical_works)
        report["canonical_tokens_checked"]=canonical_tokens
    return report


def read_rows(archive, name):
    return [json.loads(line) for line in archive.read(name).decode("utf-8").splitlines()]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.archive), ensure_ascii=False, indent=2))
