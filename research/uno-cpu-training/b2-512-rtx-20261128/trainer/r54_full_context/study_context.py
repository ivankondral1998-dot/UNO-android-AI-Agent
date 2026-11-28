"""Small preregistered diagnostics. No owner corpus or learned weights are published."""
import argparse
import json
from pathlib import Path
import time

import torch
from torch.nn import functional as F

from trainer import Codec, model_from_parent, remapping, setup
from core import CausalB2, make_batch, objective
from quality import contrast, paired_questions
from test_full_context import record


def fit(model, rows, codec, remap, steps):
    batch = make_batch(rows, codec, remap, "cpu")
    opt = torch.optim.Adam([p for p in model.parameters() if p.requires_grad], lr=.001,
                           foreach=False)
    start = time.monotonic()
    for _ in range(steps):
        opt.zero_grad(set_to_none=True)
        loss, targets = objective(model, batch)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
        opt.step()
        model.project_fast(opt)
    return {"steps": steps, "seconds": time.monotonic() - start, "targets": targets * steps,
            "loss_at_end": objective(model, batch)[0].item()}


@torch.inference_mode()
def first_gap(model, prefix_a, prefix_b, window):
    if window is not None:
        prefix_a, prefix_b = prefix_a[-window:], prefix_b[-window:]
    x = torch.tensor([prefix_a, prefix_b])
    logits = model.readout(model.scan(x)[1])
    return (logits[0] - logits[1]).abs().max().item()


def state_gradient(model, prefix, target):
    result = {}
    for distance in (1, 4, 8, 16, 32, 64):
        if distance >= len(prefix):
            continue
        cutoff = len(prefix) - distance
        with torch.no_grad():
            _, before = model.scan(torch.tensor([prefix[:cutoff]]))
        before.requires_grad_()
        _, end = model.scan(torch.tensor([prefix[cutoff:]]), before, cutoff)
        loss = F.cross_entropy(model.readout(end), torch.tensor([target]))
        grad, = torch.autograd.grad(loss, before)
        result[distance] = grad.double().norm().item()
    return result


def controlled_rows(codec):
    train = [codec.record(record(q, a), "dialogue")
             for q, a in (("Код X?", "X"), ("Код Y?", "Y"))]
    novel = [codec.record(record(q, a), "dialogue")
             for q, a in (("Пароль X?", "X"), ("Пароль Y?", "Y"))]
    long = [codec.record(record(
        f"Код {a}." + " Пожалуйста, выведи первую букву кода." * 4, a), "dialogue")
            for a in ("X", "Y")]
    return train, novel, long


def scores(model, rows, codec, remap):
    return contrast(model, paired_questions(rows, 8), codec, remap, generation=8)


class GRUControl(torch.nn.Module):
    def __init__(self, ids):
        super().__init__()
        n = len(ids)
        self.embedding = torch.nn.Embedding(n, 768)
        self.gru = torch.nn.GRU(768, 854, batch_first=True)
        self.output = torch.nn.Linear(854, n)
        self.register_buffer("remap", torch.full((32768,), -1, dtype=torch.long))
        self.remap[torch.tensor(ids)] = torch.arange(n)

    def scan(self, tokens, state=None, start=0, packed=None):
        embedded = self.embedding(self.remap[tokens])
        result, hidden = self.gru(embedded, state.unsqueeze(0) if state is not None else None)
        return result, hidden.squeeze(0)

    def packed(self):
        return None

    def readout(self, states):
        return self.output(states)

    def project_fast(self, _):
        pass


def paired_fixture_bigram(train, assessments):
    counts = {}
    for tokens, mask in train:
        for i in range(1, len(tokens)):
            if mask[i]:
                counts.setdefault(tokens[i-1], {}).setdefault(tokens[i], 0)
                counts[tokens[i-1]][tokens[i]] += 1
    result = {}
    for kind, rows in assessments.items():
        exact = first = 0
        for tokens, mask in rows:
            onset = mask.index(True)
            p = tokens[onset-1]
            got = []
            for _ in range(2):
                votes = counts.get(p, {})
                if not votes:
                    break
                p = min(votes, key=lambda x: (-votes[x], x))
                got.append(p)
            exact += got == tokens[onset:]
            first += bool(got and got[0] == tokens[onset])
        result[kind] = {"generated_exact_with_eos": exact, "correct_first": first,
                        "total": len(rows)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    args = parser.parse_args()
    setup("cpu")
    codec = Codec()
    ids, remap = remapping(codec, "cpu")
    model = model_from_parent(args.parent, ids, "cpu")
    train, novel, long = controlled_rows(codec)
    (qa, aa), (qb, _) = paired_questions(long, 8)[0]
    output = {
        "torch": str(torch.__version__), "allocated": model.count, "trainable": model.trainable_count,
        "long_prompt_tokens": len(qa),
        "long_max_logit_change_last32": first_gap(model, qa, qb, 32),
        "long_max_logit_change_full": first_gap(model, qa, qb, None),
        "state_gradient_norm_by_distance": state_gradient(model, qa, remap[aa[0]].item()),
        "step50": {k: scores(model, r, codec, remap)
                   for k, r in (("seen", train), ("unseen", novel), ("long", long))},
    }
    output["trainable_inventory"] = {name: param.numel() for name, param in model.p.items()
                                      if param.requires_grad}
    print("BASE", json.dumps(output), flush=True)
    assessments = {"seen": train, "unseen": novel, "long": long}
    output["fit"] = fit(model, train, codec, remap, 32)
    output["after"] = {k: scores(model, r, codec, remap) for k, r in assessments.items()}
    setup("cpu")
    random_f = CausalB2(512).compact(ids)
    output["untrained_f"] = {k: scores(random_f, r, codec, remap) for k, r in assessments.items()}
    del random_f
    setup("cpu")
    gru = GRUControl(codec.ids)
    output["gru"] = {"parameters": sum(p.numel() for p in gru.parameters()),
                     "fit": fit(gru, train, codec, remap, 32),
                     "scores": {k: scores(gru, r, codec, remap) for k, r in assessments.items()}}
    output["bigram"] = paired_fixture_bigram(train, assessments)

    # Positive control with signal immediately before an answer and no shared role suffix.
    # This token-level sanity check does not change the real dialogue format.
    positive = [([codec.bos] + codec.encode(q + a) + [codec.eos],
                 [False, False, True, True]) for q, a in (("A", "X"), ("B", "Y"))]
    model = model_from_parent(args.parent, ids, "cpu")
    output["immediate_control"] = {"fit": fit(model, positive, codec, remap, 128),
                                  "scores": scores(model, positive, codec, remap)}
    print("RESULT", json.dumps(output), flush=True)


if __name__ == "__main__":
    main()
