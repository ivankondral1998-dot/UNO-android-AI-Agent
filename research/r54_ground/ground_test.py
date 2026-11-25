"""Contract tests for the proving ground. No training and no opened test split."""

import hashlib
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from java_random import JavaRandom
from ladder_contract import HOLDOUT_SEED, OPENED_SHA256, example, holdout_rows, probe_rows

FAIL = 0


def check(name, cond):
    global FAIL
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        FAIL += 1


def test_java_random():
    rng = JavaRandom(150015)
    got = [rng.next_double() for _ in range(5)]
    expect = [
        0.2145817169554981,
        0.6293844626634095,
        0.30047906335208074,
        0.09980871840100614,
        0.21851405277392522,
    ]
    check("java nextDouble seed 150015", all(abs(a - b) < 1e-15 for a, b in zip(got, expect)))
    rng = JavaRandom(1)
    check("java nextInt(7) seed 1", [rng.next_int(7) for _ in range(6)] == [4, 4, 1, 0, 6, 6])


def test_rows():
    row = example("r5_order", 12, 99, "t")
    writes = [i for i, f in enumerate(row["x"][:-1]) if f[2] == 1.0]
    check("r5 query opcode", row["x"][-1] == [0.0, 0.0, -2.0])
    check("r5 target is last write", row["record"] == writes[-1] + 1)
    check("r5 label is sign of last code", row["label"] == (1 if row["x"][writes[-1]][1] > 0 else 0))
    erased = example("r5_order", 12, 99, "t", erase=True)
    check("erase keeps label and record", erased["label"] == row["label"] and erased["record"] == row["record"])
    check("erase zeros r5 codes", all(f[1] == 0.0 for f in erased["x"][:-1] if f[2] == 1.0))
    other = example("r2_two", 24, 5, "u")
    check("non-r5 query opcode", other["x"][-1][2] == -1.0)
    rows = holdout_rows(2)
    check("holdout size", len(rows) == 5 * 4 * 2)
    check("holdout seed is not 150015", HOLDOUT_SEED != 150015)
    check("holdout ids are unique", len({r["id"] for r in rows}) == len(rows))
    check("probe disjoint", set(r["id"] for r in probe_rows()).isdisjoint(r["id"] for r in rows))
    check("opened hashes recorded", len(OPENED_SHA256) == 5 and all(len(v) == 64 for v in OPENED_SHA256.values()))


def test_refuse_and_coefficients():
    backend = (HERE.parent / "train001" / "recovered-rtx" / "torch_backend.py").read_text()
    check("retrieval coefficient 0.3 still in backend", ".3*(-logits.log_softmax(0)[target[0]])" in backend)
    check("value coefficient 0.2 still in backend", ".2*(bank[target[0]][2][0]-row['value'])**2" in backend)
    blob = b"opened-stand-in"
    # The refusal key is the published hash, not this blob.
    check("stand-in is not an opened hash", hashlib.sha256(blob).hexdigest() not in OPENED_SHA256.values())


if __name__ == "__main__":
    test_java_random()
    test_rows()
    test_refuse_and_coefficients()
    if FAIL:
        raise SystemExit(f"FAILED {FAIL}")
    print("GROUND_CONTRACT_PASS")
