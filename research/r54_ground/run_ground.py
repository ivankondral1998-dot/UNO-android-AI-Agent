"""R5.4 host proving ground.

Loads the existing TRAIN001 selected checkpoint and measures, without an optimizer step:
- full / memory_off / erased on a new closed holdout
- whether Wk and Wv receive loss gradient
- whether a memory-off state loss leaves Wk and Wv with zero gradient

Does not read the opened TRAIN001 test split and does not write the checkpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import sys
import tempfile

import torch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "train001" / "recovered-rtx"))

from ladder_contract import HOLDOUT_SEED, OPENED_SHA256, holdout_rows, probe_rows  # noqa: E402
from torch_backend import TorchF, terminal_episode, terminal_logits  # noqa: E402

NAMES = (
    ["projection", "us", "ug", "meta", "e", "bias", "wq", "wr"]
    + [f"branch.0.0.{s}" for s in ("a", "c", "b", "ab", "bb")]
    + [f"branch.1.0.{s}" for s in ("a", "c", "b", "ab", "bb")]
    + ["wk", "wv"]
)
CAPS = {
    "projection": 8.0, "us": 1.0, "ug": 1.0, "meta": 8.0, "e": 1.0, "bias": 1.0,
    "wq": 2.0, "wr": 2.0, "wk": 2.0, "wv": 2.0,
    "a": 1.0, "c": 2.0, "b": 0.9, "ab": 8.0, "bb": 8.0,
}
BOXED = {"e", "bias", "ab", "bb"}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def refuse_opened(path: pathlib.Path) -> None:
    digest = sha_bytes(path.read_bytes())
    if digest in OPENED_SHA256.values():
        raise SystemExit(f"REFUSED_OPENED_SPLIT {path} {digest}")


def load_selected(path: pathlib.Path):
    refuse_opened(path)
    blob = path.read_bytes()
    head, digest, body = blob.split(b"\n", 2)
    if head != b"UNO-TORCH-S4/V1" or hashlib.sha256(body).hexdigest() != digest.decode():
        raise SystemExit("CHECKPOINT_INTEGRITY")
    state = torch.load(io.BytesIO(body), map_location="cpu", weights_only=False)
    if state.get("selected") != 950:
        raise SystemExit(f"EXPECTED_SELECTED_950 got {state.get('selected')}")
    best = state["best"]
    if list(best) != [f"slots.{i}" for i in range(20)]:
        raise SystemExit("UNEXPECTED_SLOT_KEYS")
    lines = []
    for i, name in enumerate(NAMES):
        tensor = best[f"slots.{i}"]
        rows, cols = tensor.shape
        cap = CAPS[name.rsplit(".", 1)[-1]] if name.startswith("branch.") else CAPS[name]
        box = name in ("e", "bias") or name.endswith((".ab", ".bb"))
        values = ",".join("0" for _ in range(rows * cols))
        lines.append(f"{name}\t{rows}\t{cols}\t{cap}\t{str(box).lower()}\t{values}")
    with tempfile.TemporaryDirectory() as tmp:
        initial = pathlib.Path(tmp) / "layout.tsv"
        initial.write_text("\n".join(lines) + "\n")
        model = TorchF(initial, dtype=torch.float32, device="cpu")
    model.load_state_dict(best, strict=True)
    model.validate()
    model.eval()
    return model, sha_bytes(blob), int(state["step"]), float(state["best_loss"])


def as_row(spec):
    x = torch.tensor(spec["x"], dtype=torch.float32)
    return {
        "id": spec["id"],
        "label": spec["label"],
        "record": spec["record"],
        "value": spec["value"],
        "state": spec["state"],
        "x": x,
        "rung": spec["rung"],
        "length": spec["length"],
    }


def score_rows(model, rows, mode):
    per = {}
    correct = misses = n = 0
    sse = 0.0
    top1_n = top1_hit = 0
    value_n = value_sse = 0
    with torch.no_grad():
        for spec in rows:
            row = as_row(spec)
            h, q, bank = terminal_episode(model, row["x"], mode)
            hit = any(seq == row["record"] for seq, _, _ in bank)
            ok = hit and ((float(h[0]) >= 0) == bool(row["label"]))
            n += 1
            correct += int(ok)
            misses += int(not hit)
            sse += (float(h[0]) - row["state"]) ** 2
            bucket = per.setdefault(row["rung"], {"n": 0, "correct": 0, "presence_misses": 0, "sse": 0.0, "top1": 0, "top1_n": 0})
            bucket["n"] += 1
            bucket["correct"] += int(ok)
            bucket["presence_misses"] += int(not hit)
            bucket["sse"] += (float(h[0]) - row["state"]) ** 2
            if mode != "memory_off":
                top1_n += 1
                bucket["top1_n"] += 1
                if bank:
                    choice = bank[int(terminal_logits(q, bank).argmax())][0]
                    top1_hit += int(choice == row["record"])
                    bucket["top1"] += int(choice == row["record"])
                    target = [v for seq, _, v in bank if seq == row["record"]]
                    if target:
                        value_n += 1
                        value_sse += (float(target[0][0]) - row["value"]) ** 2
    def finish(b):
        return {
            "n": b["n"],
            "correct": b["correct"],
            "accuracy": b["correct"] / b["n"],
            "presence_misses": b["presence_misses"],
            "mse": b["sse"] / b["n"],
            "retrieval_top1": (b["top1"] / b["top1_n"]) if b["top1_n"] else None,
        }
    return {
        "mode": mode,
        "n": n,
        "correct": correct,
        "accuracy": correct / n,
        "presence_misses": misses,
        "mse": sse / n,
        "retrieval_top1": (top1_hit / top1_n) if top1_n else None,
        "value_mse_on_present_target": (value_sse / value_n) if value_n else None,
        "rungs": {k: finish(v) for k, v in per.items()},
    }


def grad_norms(model, rows, kind):
    model.zero_grad(set_to_none=True)
    loss = 0.0
    for spec in rows:
        row = as_row(spec)
        if kind == "joint":
            loss = loss + model.loss(row)
        elif kind == "state_full":
            h, _, _ = terminal_episode(model, row["x"], "full")
            loss = loss + (h[0] - row["state"]) ** 2
        elif kind == "state_memory_off":
            h, _, _ = terminal_episode(model, row["x"], "memory_off")
            loss = loss + (h[0] - row["state"]) ** 2
        else:
            raise ValueError(kind)
    (loss / len(rows)).backward()
    names = model.named_tensors()
    out = {}
    for name, tensor in names.items():
        g = tensor.grad
        out[name] = 0.0 if g is None else float(g.detach().float().norm().item())
    model.zero_grad(set_to_none=True)
    return {"kind": kind, "loss": float((loss / len(rows)).detach()), "l2": out}


def snapshot(model):
    return {name: tensor.detach().cpu().clone() for name, tensor in model.named_tensors().items()}


def same(a, b):
    return all(torch.equal(a[k], b[k]) for k in a)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--per-cell", type=int, default=8)
    args = parser.parse_args()
    before = sha_bytes(args.checkpoint.read_bytes())
    model, digest, step, best_loss = load_selected(args.checkpoint)
    weights = snapshot(model)
    full = holdout_rows(args.per_cell, erase=False)
    erased = holdout_rows(args.per_cell, erase=True)
    if [r["id"] for r in full] != [r["id"] for r in erased]:
        raise SystemExit("ERASE_ID_MISMATCH")
    if any(r["label"] != e["label"] or r["record"] != e["record"] for r, e in zip(full, erased)):
        raise SystemExit("ERASE_LABEL_DRIFT")
    report = {
        "status": "HOST_DIAGNOSTIC_NOT_A_HOLDOUT_CLAIM",
        "checkpoint_sha256": digest,
        "checkpoint_step_saved": step,
        "selected_step": 950,
        "selected_validation_mse": best_loss,
        "holdout_seed": HOLDOUT_SEED,
        "holdout_n": len(full),
        "opened_splits_not_scored": sorted(OPENED_SHA256),
        "loss_coefficients": {"state_mse": 1.0, "retrieval_ce": 0.3, "value_mse": 0.2},
        "full": score_rows(model, full, "full"),
        "memory_off": score_rows(model, full, "memory_off"),
        "erased": score_rows(model, erased, "full"),
        "gradients": [
            grad_norms(model, probe_rows(), "joint"),
            grad_norms(model, probe_rows(), "state_full"),
            grad_norms(model, probe_rows(), "state_memory_off"),
        ],
    }
    if not same(weights, snapshot(model)):
        raise SystemExit("WEIGHTS_CHANGED")
    if sha_bytes(args.checkpoint.read_bytes()) != before:
        raise SystemExit("CHECKPOINT_BYTES_CHANGED")
    off = report["gradients"][2]["l2"]
    report["wk_wv_memory_off_state_grad_max"] = max(off["wk"], off["wv"])
    report["wk_wv_joint_grad_l2"] = {"wk": report["gradients"][0]["l2"]["wk"], "wv": report["gradients"][0]["l2"]["wv"]}
    args.out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    (args.out / "evidence.json").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
