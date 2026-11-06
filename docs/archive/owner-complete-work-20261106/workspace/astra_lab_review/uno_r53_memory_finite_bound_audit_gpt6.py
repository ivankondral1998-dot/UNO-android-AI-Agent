#!/usr/bin/env python3
"""UNO-R5.3 paper/host audit of Grok synthetic memory fixture.

No training, no actual UNO model or Android action. All numerical performance
values are for the synthetic scalar head, not the complete ASTRA forward.
"""
import json
import math

M = 128
S = 64
CAP = math.tanh(2.)


def sig(x):
    return 1/(1+math.exp(-x))


def toy_q(n, amp=1.0, unrelated=2):
    # New +/- keys: logits +/-t; irrelevant memories: zero-logit, zero-value.
    t = (S-2*n)*amp/math.sqrt(M)
    r = (math.exp(t)-math.exp(-t))/(math.exp(t)+math.exp(-t)+unrelated)
    return sig(4*r)


def q_diluted(n_distractors, amp=1.0):
    t = S*amp/math.sqrt(M)
    r = (math.exp(t)-math.exp(-t))/(math.exp(t)+math.exp(-t)+n_distractors)
    return sig(4*r)


def memory_read(z, keys, values):
    scores = [sum(a*b for a,b in zip(z,k))/math.sqrt(M) for k in keys]
    mx=max(scores)
    exps=[math.exp(s-mx) for s in scores]
    v=sum(w*x for w,x in zip(exps,values))/sum(exps)
    return sig(4*v)


def main():
    pos=[1.]*S
    neg=[-1.]*S
    from_pos=[-v if i < 32 else v for i,v in enumerate(pos)]
    from_neg=[-v if i >= 32 else v for i,v in enumerate(neg)]
    assert from_pos==from_neg, 'wrong half-flip construction'

    # Full-feature collision remains after any identical memory update.
    q=[0.4]*M
    sample_memories=[
        ([[.8]*M], [1.0]),
        ([[.5]*M, [-.5]*M], [1.0,-1.0]),
        ([[0.0]*M], [0.0]),
    ]
    identical_probabilities=[]
    for keys, values in sample_memories:
        r1=memory_read(q,keys,values)
        r2=memory_read(q[:],keys,values)
        assert r1==r2
        identical_probabilities.append(r1)

    # Key form in ASTRA_04: tanh(W_k h), with row-L1(W_k)<=2 and |h|<=1,
    # so strict |key_i|<=tanh(2). Similarly W_q bound and |z0|<=1.
    assert 0<CAP<1
    assert abs(math.atanh(CAP)-2.0)<1e-12

    profiles=[]
    for label,amp in [('GROK_UNREACHABLE_UNIT_KEYS',1.),('CAP_Q_TIMES_CAP_K_UPPER_ENVELOPE', CAP*CAP)]:
        vals=[dict(flips=n,q=toy_q(n,amp)) for n in range(33)]
        passing=[v['flips'] for v in vals if v['q']>=.9]
        assert toy_q(32,amp)==.5
        profiles.append(dict(label=label,amplitude=amp,max_flips_at_q_ge_0_9=max(passing),
            q_at_0=vals[0]['q'],q_at_25=vals[25]['q'],q_at_26=vals[26]['q'],q_at_32=vals[32]['q']))

    # Full-capacity dilution for both heuristic keys and stricter amp.
    dilution=[]
    for amp in (1., CAP*CAP):
        dilution.append(dict(amplitude=amp,
            q_at_0=q_diluted(0,amp),q_at_2=q_diluted(2,amp),
            q_at_4094=q_diluted(4094,amp)))

    output={
        'status':'HOST_CHECKED_SYNTHETIC_MEMORY_ANALYSIS',
        'source_contracts':['ASTRA_01 S4', 'ASTRA_02 Omega row L1<=2', 'ASTRA_04 M key/value insertion'],
        'key_abs_upper_bound_tanh_2':CAP,
        'fixture_unit_keys_exceed_contract_caps': True,
        'same_32_flip_query_from_opposite_origins':from_pos==from_neg,
        'balanced_origin_max_accuracy_when_half_flips_adversarial':.5,
        'identical_full_feature_query_remains_indistinguishable_under_tested_memories':True,
        'tested_memory_outputs':identical_probabilities,
        'confidence_profiles':profiles,
        'dilution_profiles':dilution,
        'limits':'Synthetic one-event memory read and scalar output head only; NOT exact ASTRA Wk/Wv training, nor a full shared F or Android device test.'
    }
    print(json.dumps(output,indent=2,sort_keys=True))


if __name__=='__main__':main()
