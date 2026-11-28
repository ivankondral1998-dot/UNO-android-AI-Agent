"""Generate tiny distinct splits for a CLI/recovery smoke test."""
import argparse
import json
from pathlib import Path
import shutil

from trainer import sha
from test_full_context import record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=False)
    for kind in ("language", "dialogue"):
        (out / kind).mkdir()
    for idx, split in enumerate(("train", "validation", "test")):
        dialogs = [record(f"Код {label}{idx}?", label) for label in "XY"]
        (out / "dialogue" / f"{split}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in dialogs), encoding="utf8")
        (out / "language" / f"{split}.jsonl").write_text(
            json.dumps({"text": f"Синтетический текст номер {idx}.", "source": "synthetic"},
                       ensure_ascii=False) + "\n", encoding="utf8")
    (out / "report.json").write_text(json.dumps({"schema": "UNO-CORPUS-PREP/4",
        "status": "RESEARCH_CORPUS_NOT_COMMERCIAL_APPROVAL", "missing": [],
        "retained_cross_split_keys": 0, "fixture": True}), encoding="utf8")
    shutil.copyfile(Path(__file__).resolve().parents[1] / "tokenizer.json", out / "tokenizer.json")
    (out / "SHA256SUMS.txt").write_text("".join(
        f"{sha(p)}  {p.relative_to(out).as_posix()}\n" for p in sorted(out.rglob("*")) if p.is_file()),
        encoding="ascii")


if __name__ == "__main__":
    main()
