#!/usr/bin/env python3
"""Deterministic paper-only input/oracle fixture for Grok's T; NO training.

Raw x is a synthetic four-dimensional dimensionless observation, not a
native Android SENSOR receipt and not an ASTRA trained encoding. Legal sensory
source/provenance and h_issue / memory insertion remain unimplemented.
"""
from fractions import Fraction as F
from itertools import product
import hashlib, json

ORIGIN_X0 = (F(-7,8), F(-5,8), F(-1,2), F(-3,8), F(-1,8))
OTHER = (F(-1,2), F(0), F(1,2))

def T(x):
    assert len(x) == 4 and -1 <= x[0] <= 0
    y = (x[0] + 1, x[1], x[2], x[3])
    assert all(-1 <= v <= 1 for v in y)
    return y

def oracle(x):
    assert len(x) == 4 and all(-1 <= v <= 1 for v in x)
    return int(sum(x) > 0)

def key(x):
    return tuple((v.numerator, v.denominator) for v in x)

def source_split(x):
    # Split by the other three coordinates, not by a post-hoc label.
    base = repr(key(x[1:])).encode('utf-8')
    return 'locked' if hashlib.sha256(base).digest()[0] < 64 else 'dev'

def main():
    originals = [(u, *v) for u in ORIGIN_X0 for v in product(OTHER, repeat=3)]
    outputs = [T(x) for x in originals]
    assert len(originals) == len(outputs) == 135
    assert len({key(x) for x in outputs}) == 135
    assert not {key(x) for x in originals}.intersection({key(x) for x in outputs})
    assert all(T((y[0]-1, *y[1:])) == y for y in outputs)
    flips = sum(oracle(x) != oracle(T(x)) for x in originals)
    assert flips > 0
    by_split = {}
    for name in ('dev', 'locked'):
        sample = [x for x in originals if source_split(x) == name]
        assert sample
        by_split[name] = {
            'origin_count': len(sample),
            'transformed_count': len(sample),
            'label_flips': sum(oracle(x) != oracle(T(x)) for x in sample),
            'positive_transformed': sum(oracle(T(x)) for x in sample),
        }
    print(json.dumps({
        'status': 'ORACLE_AND_TRANSFORM_ONLY',
        'transformation': 'T(x)=(x0+1,x1,x2,x3) restricted to x0 in [-1,0]',
        'oracle': 'y=1 iff sum(x)>0 else 0',
        'unique_transforms': len(outputs), 'label_flips': flips,
        'dev_and_locked_partition': by_split,
        'limitations': ('Synthetic dimensionless 4D inputs, no trained UNO F, '
                        'no legal Android provenance or memory insertion, no learning run'),
    }, sort_keys=True, indent=2))

if __name__ == '__main__':
    main()
