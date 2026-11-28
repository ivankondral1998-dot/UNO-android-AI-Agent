"""Deterministic validation with aligned counterfactual questions."""
from collections import defaultdict
from itertools import islice
import random

import torch
from torch.nn import functional as F

from core import generate, language_rows, make_batch, objective

MIN_PAIRS = 20
MIN_WIN_RATE = .75
MIN_MARGIN = .10
MIN_GENERATION_FIRST = .50
MARGIN_EPS = 1e-5


def paired_questions(rows, limit):
    groups = defaultdict(list)
    for tokens, mask in rows:
        start = mask.index(True)
        end = next((i for i in range(start, len(mask)) if not mask[i]), len(mask))
        prefix, answer = tokens[:start], tokens[start:end]
        if len(answer) < 2:
            continue
        groups[start].append((prefix, answer))
    pairs = []
    for group in groups.values():
        while len(group) >= 2:
            prefix, answer = group.pop(0)
            other = next((i for i, (p, a) in enumerate(group)
                          if p != prefix and a[0] != answer[0]), None)
            if other is None:
                continue
            swapped, alternate = group.pop(other)
            pairs.append(((prefix, answer), (swapped, alternate)))
            if len(pairs) == limit:
                return pairs
    return pairs


@torch.inference_mode()
def contrast(model, pairs, codec, remap, check=lambda: None, generation=0):
    wins = ties = generated_first = generated_exact = 0
    margins, onset = [], []
    device = remap.device
    for i, ((qa, aa), (qb, ab)) in enumerate(pairs):
        check()
        rows = [(p + a, [False] * len(p) + [True] * len(a))
                for p, a in ((qa, aa), (qb, aa), (qb, ab), (qa, ab))]
        x, y, mask = make_batch(rows, codec, remap, device)
        states, _ = model.scan(x)
        losses = torch.zeros_like(y, dtype=torch.float32)
        losses[mask] = F.cross_entropy(model.readout(states[mask]), y[mask], reduction="none")
        onset_idx = mask.to(torch.int32).argmax(dim=1)
        first = losses[torch.arange(4, device=device), onset_idx].tolist()
        scores = (losses.sum(1) / mask.sum(1)).tolist()
        for a, b in ((0, 1), (2, 3)):
            margin = first[b] - first[a]
            onset.append(margin)
            margins.append(scores[b] - scores[a])
            wins += margin > MARGIN_EPS
            ties += abs(margin) <= MARGIN_EPS
        if i < generation:
            for prefix, answer in ((qa, aa), (qb, ab)):
                got, ended = generate(model, codec, prefix, min(48, len(answer)))
                generated_first += bool(got and got[0] == answer[0])
                generated_exact += ended and got == answer[:-1]
    n = len(onset)
    g = min(generation, len(pairs)) * 2
    return {"pairs": len(pairs), "questions": n, "onset_mean_margin": sum(onset) / n if n else None,
            "answer_mean_margin": sum(margins) / n if n else None,
            "onset_win_rate": wins / n if n else None, "onset_ties": ties,
            "generated": g, "generation_first": generated_first / g if g else None,
            "generation_exact": generated_exact / g if g else None}


def contrast_pass(metrics):
    return (metrics["pairs"] >= MIN_PAIRS and metrics["generated"] >= 16
            and metrics["onset_win_rate"] >= MIN_WIN_RATE
            and metrics["onset_mean_margin"] >= MIN_MARGIN
            and metrics["generation_first"] >= MIN_GENERATION_FIRST)


@torch.inference_mode()
def validation(model, language, dialogue, codec, remap, context, batch, check):
    # Same sample and pairing at each checkpoint. No test data in this function.
    rng = random.Random(5413)
    sample = list(dialogue.rows)
    rng.shuffle(sample)
    language_loss = objective(model, make_batch(
        language_rows(language, rng, codec, context, batch), codec, remap, remap.device))
    dialogue_total = targets = 0
    for row in islice(sample, 8):
        check()
        loss, count = objective(model, make_batch([row], codec, remap, remap.device))
        dialogue_total += loss.item() * count
        targets += count
    pairs = paired_questions(sample, MIN_PAIRS)
    metrics = contrast(model, pairs, codec, remap, check, generation=8)
    return {"language_nll": language_loss[0].item(), "language_targets": language_loss[1],
            "dialogue_nll": dialogue_total / targets, "dialogue_targets": targets,
            "conditioning": metrics, "conditioning_pass": contrast_pass(metrics)}
