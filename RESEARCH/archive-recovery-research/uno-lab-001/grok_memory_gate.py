#!/usr/bin/env python3
"""S4-form memory fixture. Theta frozen. Not UNO. No training.

m=128. Keys are already in [-1,1]. One stored pair and a shifted query.
The readout is sigmoid(4 * retrieved value), the same head width as the
scalar toys. This file does not change C.
"""
import math

M = 128


def sig(z):
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def softmax(xs):
    shift = max(xs)
    exps = [math.exp(x - shift) for x in xs]
    total = sum(exps)
    return [e / total for e in exps]


def score(query, items):
    if not items:
        return 0.5
    logits = []
    for key, _ in items:
        dot = sum(a * b for a, b in zip(query, key))
        logits.append(dot / math.sqrt(M))
    weights = softmax(logits)
    retrieved = sum(w * value for w, (_, value) in zip(weights, items))
    return sig(4.0 * retrieved)


def block(start, sign):
    vec = [0.0] * M
    for i in range(start, start + 64):
        vec[i] = sign
    return vec


def flip_support(vec, n):
    out = vec[:]
    flipped = 0
    for i, value in enumerate(out):
        if value != 0.0:
            out[i] = -value
            flipped += 1
            if flipped == n:
                break
    return out


def main():
    old_pos, old_neg = block(0, 1.0), block(0, -1.0)
    new_pos, new_neg = block(64, 1.0), block(64, -1.0)
    old_items = [(old_pos, 1.0), (old_neg, -1.0)]
    both = old_items + [(new_pos, 1.0), (new_neg, -1.0)]
    one = [(new_pos, 1.0)]
    rows = [
        ("before_new", old_items, new_pos),
        ("before_old", old_items, old_pos),
        ("verbatim_new", both, new_pos),
        ("verbatim_old", both, old_pos),
        ("one_slot_on_old", one, old_pos),
        ("one_slot_on_new", one, new_pos),
    ]
    for n in (1, 8, 32):
        rows.append((f"sealed_flip_{n}", both, flip_support(new_pos, n)))
    # identical query, identical memory: the two calls match by construction
    rows.append(("identical_again", both, new_pos))
    for name, items, query in rows:
        print(f"{name} {score(query, items):.6f}")


if __name__ == "__main__":
    main()
