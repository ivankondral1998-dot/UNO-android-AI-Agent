#!/usr/bin/env python3
"""Reject the known three-test hole. No PASS path. Not UNO. No training.

A report is a dict:
  hand_set: bool
  old: list of (before, after) in [0,1]
  sealed_new: list of probabilities, at least one of each class
There is no way to return PASS. A future rule has to earn one by a code change
that also keeps this rejection.
"""
import math
import sys

def judge(report):
    if report.get("hand_set"):
        return "FAIL_HAND_SET"
    old = report.get("old") or []
    if len(old) < 2:
        return "FAIL_ONE_OLD_POINT"
    for before, after in old:
        if abs(after - before) > 0.05:
            return "FAIL_OLD_MOVED"
    sealed = report.get("sealed_new") or []
    if len(sealed) < 2 or max(sealed) <= 0.9 or min(sealed) >= 0.1:
        return "FAIL_NO_GENERALIZATION"
    return "FAIL_NO_PASS_PATH"

def three_test_toy():
    sig3 = 1.0 / (1.0 + math.exp(-3.0))
    return {
        "hand_set": True,
        "old": [(sig3, sig3), (sig3, 1.0 - sig3)],
        "sealed_new": [0.5, 0.5],
    }

def main():
    if sys.argv[1:] != ["--self-test"]:
        print("usage: python3 skill_gate.py --self-test")
        return 2
    toy = judge(three_test_toy())
    one = judge({"hand_set": False, "old": [(0.95, 0.95)], "sealed_new": [0.99, 0.01]})
    moved = judge({"hand_set": False, "old": [(0.95, 0.95), (0.95, 0.04)], "sealed_new": [0.99, 0.01]})
    chance = judge({"hand_set": False, "old": [(0.95, 0.95), (0.95, 0.95)], "sealed_new": [0.5, 0.5]})
    shaped = judge({"hand_set": False, "old": [(0.95, 0.95), (0.95, 0.95)], "sealed_new": [0.99, 0.01]})
    assert toy == "FAIL_HAND_SET", toy
    assert one == "FAIL_ONE_OLD_POINT", one
    assert moved == "FAIL_OLD_MOVED", moved
    assert chance == "FAIL_NO_GENERALIZATION", chance
    assert shaped == "FAIL_NO_PASS_PATH", shaped
    print("SELFTEST_OK")
    print("NO_PASS_PATH")
    return 0

if __name__ == "__main__":
    sys.exit(main())
