"""Closed Ladder-layout rows. Same event rules as research/train001/Ladder.kt.

Not a regeneration of TRAIN001 test.tsv. Fisher-Yates uses java.util.Random.nextInt,
matching Kotlin's end-to-start shuffle. A future Kotlin export can differ if that
file's shuffled() overload consumes Random in another order; this generator is the
sealed contract of the proving ground.
"""

from java_random import JavaRandom

RUNGS = ("r1_single", "r2_two", "r3_three", "r4_overwrite", "r5_order")
LENGTHS = (12, 24, 48, 96)

# SHA-256 of the opened TRAIN001 splits. Scoring these files is refused.
OPENED_SHA256 = {
    "erased.tsv": "45cffa8ceb3f01873abcac2275e5030e916697b835038aba095a9c9b34adf34d",
    "initial.tsv": "77eedd67186aa84813d0d277a8a157af3ca0a41f07ab9020bfd85d99d1e0942a",
    "test.tsv": "38ca745cae873082c5e9fe26ec7f3dc97419fd6eca62f7188fea0a106874be32",
    "train.tsv": "0f90396b2443c6c10311d869289faea28df4f2f96e413159732007627bef4a4e",
    "validation.tsv": "562090c9e8d6d9496e4b8ff63930da3ddd6353ea95aee83aacb5e742f69ebc18",
}

HOLDOUT_SEED = 2026112501
PROBE_SEED = 2026112502


def example(rung, length, seed, row_id, erase=False):
    if rung not in RUNGS or not 10 <= length <= 96:
        raise ValueError("rung/length")
    rng = JavaRandom(seed)

    def uniform():
        return rng.next_double() * 2 - 1

    x = [[uniform(), uniform(), 0.0] for _ in range(length)]
    n = 1 if rung == "r1_single" else (2 if rung in ("r2_two", "r5_order") else 3)
    codes = [0.0] if n == 1 else ([-1.0, 1.0] if n == 2 else [-1.0, 0.0, 1.0])
    count = n + (1 if rung == "r4_overwrite" else 0)
    window = min(length - 2, max(5, (length + 1) // 2))
    stamps = sorted(rng.shuffled(range(window))[:count])
    slots = rng.shuffled(range(n))
    if count > n:
        slots = list(slots) + [rng.next_int(n)]
    query = rng.next_int(n)
    for j, stamp in enumerate(stamps):
        x[stamp] = [uniform(), codes[slots[j]], 1.0]
    if rung == "r5_order":
        selected = stamps[-1]
        answer = x[selected][1]
    else:
        selected = stamps[max(i for i, slot in enumerate(slots) if slot == query)]
        answer = x[selected][0]
    if erase:
        for j, stamp in enumerate(stamps):
            if rung == "r5_order":
                x[stamp][1] = 0.0
            elif slots[j] == query:
                x[stamp][0] = 0.0
    if rung == "r5_order":
        x[-1] = [0.0, 0.0, -2.0]
    else:
        x[-1] = [0.0, codes[query], -1.0]
    label = 1 if answer > 0 else 0
    return {
        "id": row_id,
        "rung": rung,
        "length": length,
        "seed": int(seed),
        "label": label,
        "state": 0.8 if label else -0.8,
        "record": selected + 1,
        "value": float(answer),
        "x": x,
        "erased": bool(erase),
    }


def holdout_rows(per_cell=8, seed=HOLDOUT_SEED, erase=False):
    rows = []
    i = 0
    for rung in RUNGS:
        for length in LENGTHS:
            for k in range(per_cell):
                row_seed = seed + 50_000_000 + i
                row_id = f"holdout-{seed}-{rung}-{length}-{k}"
                rows.append(example(rung, length, row_seed, row_id, erase=erase))
                i += 1
    return rows


def probe_rows(n=4, seed=PROBE_SEED):
    """Short rows for one gradient measurement. Not the holdout, not seed 150015."""
    plan = ("r1_single", "r2_two", "r4_overwrite", "r5_order")
    return [
        example(plan[i], 12, seed + 70_000_000 + i, f"probe-{seed}-{plan[i]}-12-{i}")
        for i in range(n)
    ]
