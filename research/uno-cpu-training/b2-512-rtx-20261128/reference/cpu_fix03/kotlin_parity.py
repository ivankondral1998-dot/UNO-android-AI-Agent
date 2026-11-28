"""Read host fixture weights through the actual Kotlin reference."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

import torch
from model import LanguageF
from train import Trainer, prepare_runtime
from train001_backend import checkpoint, restore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jar", type=Path)
    args = parser.parse_args()
    prepare_runtime(2)
    torch.manual_seed(11)
    seq = torch.tensor([0, 1, 2, 3, 4])
    trainer = Trainer([seq], 8, {"width": 512, "steps": 1, "seed": 11, "window": 4})
    trainer.update()
    with tempfile.TemporaryDirectory() as tmp:
        export = Path(tmp) / "weights.uno"
        checkpoint(export, {"kind": "UNO-TEXT-F-FP32-1", "state_dict": trainer.model.state_dict()})
        saved = restore(export)
        model = LanguageF(8, 512)
        model.load_state_dict(saved["state_dict"], strict=True)
        model.validate()
        model.double()
        weights = Path(tmp) / "weights.tsv"
        with weights.open("w", encoding="ascii") as f:
            for name, value in model.state_dict().items():
                f.write(name + "\t" + ",".join(map(repr, value.flatten().tolist())) + "\n")
        proc = subprocess.run(["java", "-Xmx1g", "-cp", str(args.jar), "org.unovyra.uno.core.LanguageCoreParityKt",
                               str(weights)], check=True, capture_output=True, text=True, timeout=90)
        reference = torch.tensor([[float(x) for x in row.split(",")] for row in proc.stdout.splitlines()],
                                 dtype=torch.float64)
        with torch.inference_mode():
            h = torch.zeros(512, dtype=torch.float64)
            states = []
            for token in seq[:-1]:
                h = model.event(token, h)
                states.append(h)
        states = torch.stack(states)
        torch.testing.assert_close(states, reference, rtol=1e-11, atol=2e-14)
        print(json.dumps({"reference": "UnoFReference", "post_update_width": 512, "coordinates": states.numel(),
                          "max_abs_error": float((states-reference).abs().max()), "status": "PASS"}))


if __name__ == "__main__":
    main()
