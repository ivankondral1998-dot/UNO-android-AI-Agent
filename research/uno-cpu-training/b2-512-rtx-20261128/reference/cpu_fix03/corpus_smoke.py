"""Two short prose training windows, then export/generate in a private temporary directory."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

from train import Trainer, config, inputs, prepare_runtime, test_model
from train001_backend import restore


def main():
    p = argparse.ArgumentParser()
    p.add_argument("corpus", type=Path)
    a = p.parse_args()
    prepare_runtime(2)
    docs, tokenizer, _ = inputs(a.corpus)
    with tempfile.TemporaryDirectory() as folder:
        output = Path(folder)
        m = Trainer(docs["train"], len(tokenizer["active_ids"]), config(2, 2))
        first = m.update()
        m.save(output / "latest.uno")
        m.load(output / "latest.uno")
        second = m.update()
        if (first["offset"], second["offset"], second["targets"]) != (16, 32, 32):
            raise AssertionError("prose window cursor")
        m.save(output / "latest.uno")
        export = output / "text_f.uno"
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            test_model(SimpleNamespace(output=output, threads=2, corpus=a.corpus, tokens=8,
                                       prompt="В тихий вечер", validation_targets=32, export=export))
        rows = [json.loads(line) for line in captured.getvalue().splitlines()]
        generation = rows.pop(0)
        generation.pop("continuation")
        if rows[0]["validation_targets"] != 32 or rows[1]["validation_targets"] != 32:
            raise AssertionError("different baseline/validation denominators")
        if restore(export)["kind"] != "UNO-TEXT-F-FP32-1":
            raise AssertionError("export schema")
        print(json.dumps({"short_prose_windows": [first, second], "generation_metrics": generation,
                          "validation_and_baselines": rows, "export_bytes": export.stat().st_size}))


if __name__ == "__main__":
    main()
