#!/usr/bin/env python3
"""Counterexample to a 3-condition *acceptance criterion*, NOT an UNO F implementation.

The criterion under review requires (1) two situations initially inseparable,
(2) after a bounded change inside F they separate, (3) an old skill absent
from the update still passes a held-out check.

This single-operator toy passes all three while failing on new held-out inputs
and catastrophically forgetting an untested part of the old skill.
No training, random weights, phones or owner gates are involved.
"""
import json
import math


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def F(w, example):
    # Shared operator with one trainable scalar w; |delta w| <= 1.
    # raw.tag is a true class feature that this model ignores.
    # old_interaction is present in an old but not the sampled old check.
    return (w * example['seen_id'], example['old_base'] - w * example['old_interaction'])


def new_q(w, example):
    return sigmoid(4 * F(w, example)[0])


def old_q(w, example):
    return sigmoid(4 * (F(w, example)[1] - 0.5))


def main():
    a = dict(seen_id=1, tag=1, old_base=0, old_interaction=0)
    b = dict(seen_id=-1, tag=-1, old_base=0, old_interaction=0)
    # Held-out old sample, not used in the new lesson:
    old_checked = dict(seen_id=0, tag=0, old_base=1, old_interaction=0)
    # Another valid old-skill example, also unused in the lesson/check:
    old_unchecked = dict(seen_id=0, tag=0, old_base=1, old_interaction=1)
    # Two unseen new-task cases, class marked by tag, not memorized seen_id:
    a_unseen = dict(seen_id=0, tag=1, old_base=0, old_interaction=0)
    b_unseen = dict(seen_id=0, tag=-1, old_base=0, old_interaction=0)
    before, after = 0., 1.

    gate1 = F(before, a) == F(before, b)
    gate2 = new_q(after, a) >= .9 and new_q(after, b) <= .1 and abs(after - before) <= 1
    gate3 = abs(old_q(after, old_checked) - old_q(before, old_checked)) <= .01
    assert gate1 and gate2 and gate3
    assert old_q(before, old_unchecked) > .8 and old_q(after, old_unchecked) < .2
    assert new_q(after, a_unseen) == new_q(after, b_unseen) == .5

    result = {
      'status': 'THREE_GATES_PASS_BUT_ACCEPTANCE_FALSE_POSITIVE',
      'gate1_initial_representations_equal': gate1,
      'gate2_bounded_F_change_distinguishes_taught_pair': gate2,
      'gate3_old_heldout_sample_stable': gate3,
      'weight_change': after - before,
      'new_taught_probabilities': [new_q(after, a), new_q(after, b)],
      'old_checked_probability_before_after': [old_q(before, old_checked), old_q(after, old_checked)],
      'old_unchecked_probability_before_after': [old_q(before, old_unchecked), old_q(after, old_unchecked)],
      'new_unseen_probabilities': [new_q(after, a_unseen), new_q(after, b_unseen)],
      'limitation': 'Toy logical counterexample only: NOT a parameter-exact ASTRA F, not training and not an Android test.'
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
