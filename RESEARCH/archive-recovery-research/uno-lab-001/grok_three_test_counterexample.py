#!/usr/bin/env python3
"""Counterexample to the three-test organism criterion. Not UNO. No training.

Read literally, the three tests can all pass while a second old example flips
and unseen inputs stay at one half. One stored parameter moves. The weights are
hand-set. That is the hole in the criterion, not a learning result.
"""
import math


def sig(z):
    return 1.0 / (1.0 + math.exp(-z))


def q(x, t):
    # t is the single parameter: 0 before the edit, 1 after.
    if x == "old_keep":
        return sig(3.0)
    if x == "old_hurt":
        return sig(3.0 - 6.0 * t)
    if x == "new_pos":
        return sig(3.0 * t)
    if x == "new_neg":
        return sig(-3.0 * t)
    return sig(0.0)


def main():
    keys = ("new_pos", "new_neg", "old_keep", "old_hurt", "novel_a", "novel_b")
    before = {k: q(k, 0.0) for k in keys}
    after = {k: q(k, 1.0) for k in keys}
    assert abs(before["new_pos"] - 0.5) < 1e-15
    assert abs(before["new_neg"] - 0.5) < 1e-15
    assert after["new_pos"] > 0.9 and after["new_neg"] < 0.1
    assert before["old_keep"] == after["old_keep"] > 0.9
    assert before["old_hurt"] > 0.9 and after["old_hurt"] < 0.1
    assert after["novel_a"] == after["novel_b"] == 0.5
    print("THREE_TEST_PASS")
    print("NOT_A_SKILL")
    for k in keys:
        print(f"{k} {before[k]:.6f} -> {after[k]:.6f}")


if __name__ == "__main__":
    main()
