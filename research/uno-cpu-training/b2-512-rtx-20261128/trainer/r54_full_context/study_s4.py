"""S4 diagnostic with causal writes at known input markers, outside trainer."""
import argparse
import json
from pathlib import Path
import time

import torch
from torch.nn import functional as F

from trainer import Codec, model_from_parent, remapping, setup
from study_context import controlled_rows
from quality import paired_questions


def scan(model, tokens, marker, mode):
    pack = model.packed()
    arch = model.p
    state = arch["U_s"].new_zeros(tokens.shape[0], model.d)
    goal = torch.zeros_like(state)
    bank = []
    predictions = []
    for pos, token in enumerate(tokens.unbind(1)):
        meta = state.new_zeros(tokens.shape[0], 32)
        meta[:, 1] = meta[:, 4] = 1.
        meta[:, 14] = min(pos / 128, 1.)
        embedding = arch["E_text"][model.remap_text[token]]
        state, _ = model.event(token, state, goal, meta, bank, K=1,
                               packed=pack, embedded=embedding)
        predictions.append(state)
        if (pos == 0 and mode in ("bank", "swapped")) or (pos == marker and mode != "empty"):
            key = model.lin(state, "W_k").tanh()
            val = model.lin(state, "W_v").tanh()
            if mode == "swapped" and pos == marker:
                key, val = key.flip(0), val.flip(0)
            bank.append((key, val))
    return model.readout(torch.stack(predictions, 1))


def get_pair(codec, remap, rows):
    (qa, aa), (qb, ab) = paired_questions(rows, 3)[0]
    marker, = [i for i, (x, y) in enumerate(zip(qa, qb)) if x != y]
    return torch.tensor([qa + aa[:-1], qb + ab[:-1]]), remap[torch.tensor([aa, ab])], marker


@torch.inference_mode()
def evaluate(model, pair, mode):
    x, answers, marker = pair
    logits = scan(model, x, marker, mode)[:, -answers.shape[1]:]
    first = logits[:, 0]
    logp = first.log_softmax(-1)
    rows = torch.arange(len(x))
    margin = logp[rows, answers[:, 0]] - logp[rows, answers.flip(0)[:, 0]]
    # Score the first emitted token, without exposure to the teacher answer.
    return {"first_correct": int((first.argmax(-1) == answers[:, 0]).sum()),
            "targets": len(x), "mean_first_margin": margin.mean().item(),
            "first_logit_gap": (first[0] - first[1]).abs().max().item()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    args = parser.parse_args()
    setup("cpu")
    codec = Codec()
    ids, remap = remapping(codec, "cpu")
    model = model_from_parent(args.parent, ids, "cpu")
    pairs = {name: get_pair(codec, remap, rows) for name, rows in
             zip(("train", "unseen", "long"), controlled_rows(codec))}
    active = ("W_q", "W_k", "W_v", "W_r")
    for key in active:
        model.p[key].requires_grad_(True)
    x, y, pos = pairs["train"]

    def loss(mode):
        logits = scan(model, x, pos, mode)[:, -y.shape[1]:].flatten(0, 1)
        return F.cross_entropy(logits, y.flatten())

    gradients = {}
    for mode in ("single", "bank"):
        grads = torch.autograd.grad(loss(mode), [model.p[key] for key in active])
        gradients[mode] = {key: grad.norm().item() for key, grad in zip(active, grads)}
    start = time.monotonic()
    opt = torch.optim.Adam([p for p in model.parameters() if p.requires_grad],
                           lr=.001, foreach=False)
    for _ in range(32):
        opt.zero_grad(set_to_none=True)
        loss("bank").backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
        opt.step()
        model.project_fast(opt)
    print(json.dumps({"steps": 32, "seconds": time.monotonic() - start,
          "gradients_before_updates": gradients,
          "after": {name: {mode: evaluate(model, pair, mode) for mode in
                           ("bank", "empty", "swapped")} for name, pair in pairs.items()}},
          indent=2))


if __name__ == "__main__":
    main()
