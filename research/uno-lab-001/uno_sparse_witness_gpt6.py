#!/usr/bin/env python3
"""UNO R5.3 S4/S5/S7 sparse constructive witness; NO TRAINING.

Two distinct token embeddings produce opposite high-confidence outcomes for the
same endpoint, after decision + four argument re-encodes, with full mask K=8.
All row-L1 caps and zero biases are respected. This is a deliberately selected
parameter configuration, NOT the Xavier random initializer or trained UNO.
Does not prove generalization, retention, Android costs, or correct authority.

Run: python3 uno_sparse_witness_gpt6.py
"""
import json
import math

V = 32768
M = 128
J = 2
B = 64
CHI = 4
RHO = .5
ALPHA = .5
K = 8
FAN_OUT = 16
EMBED_EACH = .5  # text embedding L1 = FAN_OUT * .5 = 8
C_COEFF = 2.0  # C row-L1<=2
B_COEFF = .9  # B row-L1<=.9
HEAD_COEFF = 8.0  # Wp[a] row-L1<=8
BIASES = 0.0


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


def run(d, sign):
    assert d in (512, 1024) and d % B == 0 and sign in (-1, 1)
    assert FAN_OUT * abs(EMBED_EACH) <= 8
    assert abs(C_COEFF) <= 2 and abs(B_COEFF) <= .9
    assert HEAD_COEFF <= 8 and BIASES == 0
    # Nonzero params: two token embeddings E[-,+], two identical J=2 C/B
    # branches for 16 components of the first 64-element block, and Wp[3,0]=8.
    # U_s=U_g=Wmeta=Wr=A=0; a,b,b_z,b_p=0; memory empty, goal=0.
    token = [sign * EMBED_EACH] * FAN_OUT + [0.0] * (d - FAN_OUT)
    s = [0.0] * d
    for event in range(5):  # 1 decision + 4 argument tokens, exactly as H-FIX
        z0 = [math.tanh(v) for v in token]
        z = [math.tanh(v) for v in z0]  # empty memory => extra tanh
        h = [RHO * s[i] + (1 - RHO) * z[i] for i in range(d)]
        for _ in range(K):
            new = []
            for i, hi in enumerate(h):
                if i < FAN_OUT:
                    # J=2 identical factors. A=0, C has one 2.0 coefficient;
                    # B has one 0.9 coefficient. All remaining tensor rows=0.
                    u = math.tanh(C_COEFF * z[i])
                    f = sum(math.tanh(B_COEFF * u) for _ in range(J)) / J
                else:
                    f = 0.0
                new.append((1 - ALPHA) * hi + ALPHA * f)  # full mask
            h = new
        s = h
    norm = math.sqrt(sum(v * v for v in s))
    logit = HEAD_COEFF * s[0]  # same endpoint a=3 for both contexts; P=0
    return {"d": d, "token_sign": sign, "post_arg_h_l2": norm,
            "post_arg_h0": s[0], "logit": logit, "q": sigmoid(logit),
            "max_abs_h": max(map(abs, s)), "events": 5, "K": K,
            "mask": "full", "p_norm": 0.0}


def main():
    cases = [run(d, sign) for d in (512, 1024) for sign in (1, -1)]
    for d in (512, 1024):
        p = next(v for v in cases if v["d"] == d and v["token_sign"] == 1)
        n = next(v for v in cases if v["d"] == d and v["token_sign"] == -1)
        assert p["post_arg_h_l2"] > math.log(9)
        assert p["q"] > .9 and n["q"] < .1
        assert math.isclose(p["q"] + n["q"], 1.0, abs_tol=1e-13)
        assert p["max_abs_h"] <= 1.0 and n["max_abs_h"] <= 1.0
    print(json.dumps({"status": "CONSTRUCTIVE_WITNESS_PASS",
                      "claim": "One shared S4/S5 F with legal row norms and zero biases can separate two distinct frozen input contexts for the same S7 endpoint at q>0.9 and q<0.1 after post-arg re-encode",
                      "parameter_choice": "hand-set sparse legal parameters; NOT Xavier initialization, trained Theta, or verified real-world skill",
                      "caps": {"embedding_row_l1": 8, "C_row_l1": 2, "B_row_l1": .9, "Wp_row_l1": 8, "P_row_l2": 0, "biases": 0},
                      "cases": cases}, indent=2))


if __name__ == "__main__":
    main()
