#!/usr/bin/env python3
"""One organism, sequential. Synthetic bench. Not UNO. Not legal Theta.

Owner permit: research training of small weights on computer, one candidate,
max 3 runs before review. This is run 1 of this candidate.

Criteria fixed here before the run:
- acquisition: new accuracy on locked >= 0.9
- retention: old accuracy on locked AFTER phase 2, same weights, >= 0.9
- transfer: new accuracy on T(locked) >= 0.9
- a separately trained old model does not count as retention
- pass on this linear toy is not a UNO skill

Domain: x0 in [-1,0], x1..x3 in [-1,1].
T(x)=(x0+1,x1,x2,x3).
y_old = 1 iff x1>0. y_new = 1 iff sum(x)>0.
Split regenerated from this file: OPEN_FIXTURE, not sealed.
"""
import json
import math
import platform
import random
import sys

SEED = 20261105
N = 400
ADAPT, ACCEPT, LOCKED = 200, 80, 120
ETA = 0.05
STEPS_1 = 300
STEPS_2 = 300
ANCHOR = 0.1
PASS = 0.9


def sig(z):
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def y_old(x):
    return 1 if x[1] > 0 else 0


def y_new(x):
    return 1 if sum(x) > 0 else 0


def T(x):
    return (x[0] + 1.0, x[1], x[2], x[3])


def zeros(n):
    return [0.0] * n


def matmul(A, x):
    return [dot(row, x) for row in A]


def sample(n, rng):
    return [
        (
            rng.uniform(-1.0, 0.0),
            rng.uniform(-1.0, 1.0),
            rng.uniform(-1.0, 1.0),
            rng.uniform(-1.0, 1.0),
        )
        for _ in range(n)
    ]


def acc(pred, xs, ys):
    return sum(1 for x, y in zip(xs, ys) if pred(x) == y) / len(xs)


class Organism:
    """One shared trunk A (4x4), two heads. Same object across phases."""

    def __init__(self, anchor=0.0):
        self.A = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
        self.wo = zeros(4)
        self.bo = 0.0
        self.wn = zeros(4)
        self.bn = 0.0
        self.anchor = anchor
        self.A1 = None

    def h(self, x):
        return matmul(self.A, x)

    def p_old(self, x):
        return sig(dot(self.wo, self.h(x)) + self.bo)

    def p_new(self, x):
        return sig(dot(self.wn, self.h(x)) + self.bn)

    def pred_old(self, x):
        return 1 if self.p_old(x) >= 0.5 else 0

    def pred_new(self, x):
        return 1 if self.p_new(x) >= 0.5 else 0

    def train_old(self, xs, ys, steps, move_trunk):
        for _ in range(steps):
            gA = [[0.0] * 4 for _ in range(4)]
            gwo, gbo = zeros(4), 0.0
            for x, y in zip(xs, ys):
                h = self.h(x)
                p = sig(dot(self.wo, h) + self.bo)
                err = p - y
                for i in range(4):
                    gwo[i] += err * h[i]
                gbo += err
                if move_trunk:
                    for i in range(4):
                        for j in range(4):
                            gA[i][j] += err * self.wo[i] * x[j]
            s = 1.0 / len(xs)
            self.wo = [self.wo[i] - ETA * gwo[i] * s for i in range(4)]
            self.bo -= ETA * gbo * s
            if move_trunk:
                for i in range(4):
                    for j in range(4):
                        self.A[i][j] -= ETA * gA[i][j] * s
        self.A1 = [row[:] for row in self.A]

    def train_new(self, xs, ys, steps, move_trunk):
        for _ in range(steps):
            gA = [[0.0] * 4 for _ in range(4)]
            gwn, gbn = zeros(4), 0.0
            for x, y in zip(xs, ys):
                h = self.h(x)
                p = sig(dot(self.wn, h) + self.bn)
                err = p - y
                for i in range(4):
                    gwn[i] += err * h[i]
                gbn += err
                if move_trunk:
                    for i in range(4):
                        for j in range(4):
                            gA[i][j] += err * self.wn[i] * x[j]
            s = 1.0 / len(xs)
            self.wn = [self.wn[i] - ETA * gwn[i] * s for i in range(4)]
            self.bn -= ETA * gbn * s
            if move_trunk:
                for i in range(4):
                    for j in range(4):
                        reg = self.anchor * (self.A[i][j] - self.A1[i][j])
                        self.A[i][j] -= ETA * (gA[i][j] * s + reg)


def nearest(store, x):
    best, bestd = 0, float("inf")
    for row, y in store:
        d = sum((a - b) ** 2 for a, b in zip(row, x))
        if d < bestd:
            best, bestd = y, d
    return best


def run_arm(name, move_trunk, anchor, adapt, locked_old, locked_new):
    org = Organism(anchor=anchor)
    org.train_old(adapt, [y_old(x) for x in adapt], STEPS_1, move_trunk)
    old_after_1 = acc(org.pred_old, locked_old, [y_old(x) for x in locked_old])
    org.train_new(adapt, [y_new(x) for x in adapt], STEPS_2, move_trunk)
    old_after_2 = acc(org.pred_old, locked_old, [y_old(x) for x in locked_old])
    new_locked = acc(org.pred_new, locked_new, [y_new(x) for x in locked_new])
    t_locked = [T(x) for x in locked_new]
    new_transfer = acc(org.pred_new, t_locked, [y_new(x) for x in t_locked])
    old_on_t = acc(org.pred_old, [T(x) for x in locked_old], [y_old(T(x)) for x in locked_old])
    return {
        "arm": name,
        "what_changes": "trunk A and both heads" if move_trunk else "heads only, trunk frozen at identity",
        "signal": "observed labels on adapt, old then new, same object",
        "old_after_phase1": round(old_after_1, 4),
        "old_after_phase2_same_organism": round(old_after_2, 4),
        "new_locked": round(new_locked, 4),
        "new_on_T": round(new_transfer, 4),
        "old_on_T": round(old_on_t, 4),
        "acquisition": new_locked >= PASS,
        "retention_same_organism": old_after_2 >= PASS,
        "transfer": new_transfer >= PASS,
    }


def main():
    rng = random.Random(SEED)
    rows = sample(N, rng)
    adapt = rows[:ADAPT]
    locked = rows[ADAPT + ACCEPT:]
    locked_old, locked_new = locked[:60], locked[60:]

    arms = [
        run_arm("frozen_trunk_P_heads", False, 0.0, adapt, locked_old, locked_new),
        run_arm("shared_trunk_anchored", True, ANCHOR, adapt, locked_old, locked_new),
        run_arm("shared_trunk_free", True, 0.0, adapt, locked_old, locked_new),
    ]

    # prototype: observed store, separate per task, not one organism
    store_old = [(x, y_old(x)) for x in adapt]
    store_new = [(x, y_new(x)) for x in adapt]
    proto = {
        "arm": "nearest_prototype_observed",
        "what_changes": "memory store only",
        "signal": "observed adapt pairs",
        "old_after_phase2_same_organism": round(acc(lambda x: nearest(store_old, x), locked_old, [y_old(x) for x in locked_old]), 4),
        "new_locked": round(acc(lambda x: nearest(store_new, x), locked_new, [y_new(x) for x in locked_new]), 4),
        "new_on_T": round(acc(lambda x: nearest(store_new, x), [T(x) for x in locked_new], [y_new(T(x)) for x in locked_new]), 4),
        "counts_as_retention": False,
        "reason": "two stores, not one sequential organism",
    }

    # separate linear models: reported, not retention
    def fit(xs, ys):
        o = Organism()
        if ys and ys[0] == y_old(xs[0]):
            o.train_old(xs, ys, STEPS_1, False)
            return o.pred_old
        o.train_new(xs, ys, STEPS_1, False)
        return o.pred_new

    # simpler separate: two frozen-trunk organisms
    sep_old = Organism()
    sep_old.train_old(adapt, [y_old(x) for x in adapt], STEPS_1, False)
    sep_new = Organism()
    sep_new.train_new(adapt, [y_new(x) for x in adapt], STEPS_1, False)
    separate = {
        "arm": "separate_models_NOT_retention",
        "old": round(acc(sep_old.pred_old, locked_old, [y_old(x) for x in locked_old]), 4),
        "new": round(acc(sep_new.pred_new, locked_new, [y_new(x) for x in locked_new]), 4),
        "counts_as_retention": False,
    }

    out = {
        "candidate": "sequential shared trunk, two heads, synthetic h from A x",
        "not": "legal Theta, UNO skill, sealed holdout",
        "criteria": {"acquisition": PASS, "retention_same_organism": PASS, "transfer": PASS},
        "budget": {"steps_per_phase": STEPS_1, "eta": ETA, "runs_of_this_candidate": 1},
        "split": {"seed": SEED, "n": N, "adapt": ADAPT, "accept_unused": ACCEPT, "locked": LOCKED, "status": "OPEN_FIXTURE"},
        "environment": {"python": sys.version, "platform": platform.platform()},
        "arms": arms,
        "prototype": proto,
        "separate_models": separate,
        "reconciliation": {
            "grok_earlier": "0.675/0.6, logistic 400 steps eta 0.05, n=200 seed 20261105, same model scored on both tasks, tested on T(D)",
            "gpt_claimed": "70/70 and 70/70, perceptron 250 passes, 135+135 rational, adapt 170, public_final 70, trained separately per task",
            "cause": "different sample, different split, different trainer, and separate models versus one model. Her files are not in the tree.",
            "owner_rule": "separate models do not prove retention",
        },
    }
    sys.stdout.write(json.dumps(out, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
