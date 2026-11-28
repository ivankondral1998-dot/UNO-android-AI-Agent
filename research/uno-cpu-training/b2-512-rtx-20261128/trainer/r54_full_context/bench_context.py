"""Short paired FP32 CPU benchmark of masked readout vs FAST03 at fixed length."""
import argparse
import json
from pathlib import Path
import statistics
import time

import torch

from trainer import Codec, model_from_parent, remapping, setup
from core import objective
from fast_model03 import FastB2
from train_cuda_fast03 import objective as previous_objective


def update(model, opt, loss_fn):
    start = time.perf_counter()
    opt.zero_grad(set_to_none=True)
    loss, targets = loss_fn()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
    opt.step()
    model.project_fast(opt)
    return loss.item(), targets, time.perf_counter() - start


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    args = parser.parse_args()
    setup("cpu")
    codec = Codec()
    ids, _ = remapping(codec, "cpu")
    new = model_from_parent(args.parent, ids, "cpu")
    old = FastB2(512)
    old.load_state_dict(new.canonical_weights())
    old.compact(ids)
    optimizers = [torch.optim.Adam([p for p in m.parameters() if p.requires_grad],
                                  lr=2e-4, foreach=False) for m in (old, new)]
    rng = torch.Generator().manual_seed(4451)
    x = ids[torch.randint(len(ids), (2, 128), generator=rng)]
    y = torch.randint(len(ids), x.shape, generator=rng)
    mask = torch.zeros_like(y, dtype=torch.bool)
    mask[:, 72:104] = True
    batch = x, y, mask
    timers = [[], []]
    max_loss_gap = 0.
    for j in range(5):
        variants = [(old, optimizers[0], lambda: previous_objective(old, batch, ids)),
                (new, optimizers[1], lambda: objective(new, batch))]
        times = [None, None]
        for i in ((0, 1) if j % 2 == 0 else (1, 0)):
            times[i] = update(*variants[i])
        max_loss_gap = max(max_loss_gap, abs(times[0][0] - times[1][0]))
        if j:
            for ts, (_, count, elapsed) in zip(timers, times):
                ts.append(count / elapsed)
    old_weights, new_weights = (model.canonical_weights() for model in (old, new))
    delta = max((old_weights[k] - new_weights[k]).abs().max().item() for k in old_weights)
    assert max_loss_gap < 1e-5 and delta < 1e-5
    print(json.dumps({"context": 128, "targets_per_update": int(mask.sum()),
          "measured_updates": 4, "fast03_targets_s": timers[0], "full_context_targets_s": timers[1],
          "median_fast03_targets_s": statistics.median(timers[0]),
          "median_full_context_targets_s": statistics.median(timers[1]),
          "max_loss_difference": max_loss_gap, "max_weight_difference": delta}, indent=2))


if __name__ == "__main__":
    main()
