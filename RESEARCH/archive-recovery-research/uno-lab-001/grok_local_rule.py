#!/usr/bin/env python3
"""Local coefficient rule on the scalar S5 step. Not UNO. No phone.

Two cases. Private: each skill already owns a coordinate. Shared: one
coefficient, and the new labels oppose the old ones. The step is finite
difference on the mean BCE, then a clip to the C row cap 2.
"""
import math


def forward(embed, C, head=4.0):
    total = 0.0
    for e, c in zip(embed, C):
        z = math.tanh(math.tanh(e))
        h = 0.5 * z
        for _ in range(8):
            f = math.tanh(0.9 * math.tanh(c * z))
            h = 0.5 * h + 0.5 * f
        total += h
    logit = head * total
    if logit >= 0:
        return 1.0 / (1.0 + math.exp(-logit))
    ez = math.exp(logit)
    return ez / (1.0 + ez)


def loss(C, batch):
    total = 0.0
    for embed, y in batch:
        q = min(1.0 - 1e-12, max(1e-12, forward(embed, C)))
        total += -(y * math.log(q) + (1.0 - y) * math.log(1.0 - q))
    return total / len(batch)


def fit(C, batch, steps=400, lr=0.8):
    eps = 1e-4
    for _ in range(steps):
        base = loss(C, batch)
        nxt = []
        for i in range(len(C)):
            bumped = C[:]
            bumped[i] += eps
            grad = (loss(bumped, batch) - base) / eps
            nxt.append(max(-2.0, min(2.0, C[i] - lr * grad)))
        C = nxt
    return C


def line(C, batch, name):
    parts = []
    for embed, y in batch:
        parts.append(f"y={y} q={forward(embed, C):.6f}")
    print(name, " ".join(parts))


def main():
    old_open = [((0.5, 0.0), 1), ((-0.5, 0.0), 0)]
    new_open = [((0.0, 0.5), 1), ((0.0, -0.5), 0)]
    sealed_old = [((0.47, 0.0), 1), ((-0.47, 0.0), 0)]
    sealed_new = [((0.0, 0.47), 1), ((0.0, -0.47), 0)]
    start = [2.0, 0.0]
    print("PRIVATE_BEFORE", [round(v, 6) for v in start])
    line(start, sealed_old, "sealed_old")
    line(start, sealed_new, "sealed_new")
    learned = fit(start, old_open + new_open)
    print("PRIVATE_BOTH", [round(v, 6) for v in learned])
    line(learned, old_open, "open_old")
    line(learned, new_open, "open_new")
    line(learned, sealed_old, "sealed_old")
    line(learned, sealed_new, "sealed_new")
    swapped = [(e, 1 - y) for e, y in new_open]
    flipped = fit(start, old_open + swapped)
    print("PRIVATE_SWAP", [round(v, 6) for v in flipped])
    line(flipped, sealed_new, "sealed_new_original_labels")
    shared_old = [((0.5,), 1), ((-0.5,), 0)]
    shared_new = [((0.45,), 0), ((-0.45,), 1)]
    shared_sealed_old = [((0.47,), 1), ((-0.47,), 0)]
    shared_sealed_new = [((0.42,), 0), ((-0.42,), 1)]
    print("SHARED_BEFORE", 2.0)
    line([2.0], shared_sealed_old, "sealed_old")
    line([2.0], shared_sealed_new, "sealed_new")
    shared = fit([2.0], shared_old + shared_new)
    print("SHARED_AFTER", [round(v, 6) for v in shared])
    line(shared, shared_sealed_old, "sealed_old")
    line(shared, shared_sealed_new, "sealed_new")


if __name__ == "__main__":
    main()
