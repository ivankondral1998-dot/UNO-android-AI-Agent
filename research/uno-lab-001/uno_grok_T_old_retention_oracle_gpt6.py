#!/usr/bin/env python3
"""Independent oracle-invariance check for Grok's proposed OLD label; no training."""
from itertools import product
from uno_grok_T_oracle_spec_gpt6 import ORIGIN_X0, OTHER, T, oracle, source_split
import json


def old_oracle(x):
    return int(x[1] > 0)


def main():
    origins = [(u, *v) for u in ORIGIN_X0 for v in product(OTHER, repeat=3)]
    assert all(old_oracle(x) == old_oracle(T(x)) for x in origins)
    samples = {}
    for split in ('dev', 'locked'):
        pts = [x for x in origins if source_split(x) == split]
        samples[split] = {'count': len(pts),
                          'old_positive': sum(old_oracle(x) for x in pts),
                          'new_label_changes': sum(oracle(T(x)) != oracle(x) for x in pts)}
    print(json.dumps({'status': 'OLD_ORACLE_INVARIANCE_ONLY',
                      'old_rule': 'y_old=1 iff x1>0',
                      'old_labels_invariant_under_T': True,
                      'splits': samples,
                      'limitations': 'No trained UNO weights, no memory insertion, no online update'},
                     sort_keys=True, indent=2))

if __name__ == '__main__':
    main()
