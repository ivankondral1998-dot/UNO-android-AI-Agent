#!/usr/bin/env python3
"""UNO-LAB: exact half-bit-flip ambiguity and memory-softmax margins.

Paper/host fixture only. No model training, no production code, no Android.
S4-form synthetic memory keys and synthetic scalar readout, NOT full ASTRA.
"""
import json
import math


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


def classify_memory(q, items, m=128):
    logits = [sum(x*y for x,y in zip(q,key)) / math.sqrt(m) for key,_ in items]
    a = max(logits)
    ex = [math.exp(z-a) for z in logits]
    weighted = sum(v*e for (_,v),e in zip(items,ex)) / sum(ex)
    return sigmoid(4*weighted)


def block(start, sign, m=128):
    return [sign if start<=i<start+64 else 0.0 for i in range(m)]


def flip_indices(vec, indices):
    v=vec[:]
    for i in indices:
        v[i]=-v[i]
    return v


def main():
    m=128
    pos=block(64,1,m)
    neg=block(64,-1,m)
    oldp=block(0,1,m)
    oldn=block(0,-1,m)
    memory=[(oldp,1),(oldn,-1),(pos,1),(neg,-1)]

    # The SAME sealed vector can be produced from POSITIVE by flipping
    # the first 32 of the support, or from NEGATIVE by flipping the last 32.
    # The originating labels conflict, while observable vector is equal.
    q_from_pos=flip_indices(pos,range(64,96))
    q_from_neg=flip_indices(neg,range(96,128))
    assert q_from_pos==q_from_neg
    ambiguous=classify_memory(q_from_pos,memory)
    assert abs(ambiguous-.5)<1e-13

    # For any classifier mapping this shared vector to one decision,
    # exactly one of those two equally likely originating labels is wrong.
    # Randomization cannot improve 0.5 mean accuracy under balanced origin.

    # Analytical symmetric four-key retrieval: old keys orthogonal to query,
    # new scores are +/- t, old scores 0,0.
    results=[]
    for n in (0,1,8,16,24,25,26,31,32):
        query=flip_indices(pos,range(64,64+n))
        empirical=classify_memory(query,memory)
        t=(64-2*n)/math.sqrt(m)
        retrieved=math.sinh(t)/(math.cosh(t)+1)
        analytic=sigmoid(4*retrieved)
        assert abs(empirical-analytic)<1e-13
        results.append(dict(flips=n,probability=empirical,confident_at_0_9=empirical>=.9))

    threshold=2*math.atanh(math.log(9)/4)
    max_flips=math.floor((64-threshold*math.sqrt(m))/2)
    assert results[0]['confident_at_0_9'] and not results[-1]['confident_at_0_9']
    assert all((n<=max_flips)==(sigmoid(4*math.tanh((64-2*n)/(2*math.sqrt(m))))>=.9) for n in range(33))
    print(json.dumps({
      'finding':'HALF_FLIP_LABEL_AMBIGUITY',
      'identical_query_from_two_opposite_classes':q_from_pos==q_from_neg,
      'half_flip_probability':ambiguous,
      'balanced_origin_max_possible_classification_accuracy':.5,
      'fixed_fixture_max_flips_to_reach_0_9':max_flips,
      'logit_threshold_t':threshold,
      'results':results,
      'scope':'synthetic memory-head fixture; no trained weights, no semantic task, no real device'
    },sort_keys=True,indent=2))


if __name__=='__main__':
    main()
