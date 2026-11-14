#!/usr/bin/env python3
"""UNO-LAB-001 frozen S4/S5/S7 fixture. No training, no phone.
Measures post-re-encode h_a, l0 and p0. Not a trained UNO.
"""
import hashlib
import math
import numpy as np

SEED = 20261105
V = 32768
M = 128
B = 64
CHI = 4
J = 2
RHO = 0.5
ALPHA = 0.5
EPS = 1.0
LAM = 1e-3
ETA = 1e-2
Q_STAR = 0.9


def sig(z):
    z = np.asarray(z, dtype=np.float64)
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def project_rows(w, cap):
    nrm = np.abs(w).sum(axis=-1, keepdims=True)
    scale = np.ones_like(nrm)
    hot = nrm > cap
    scale[hot] = cap / nrm[hot]
    return w * scale


def xavier(rng, shape, cap, fan_in, fan_out):
    lim = math.sqrt(6.0 / (fan_in + fan_out))
    w = rng.uniform(-lim, lim, size=shape)
    return project_rows(w, cap)


def token_row(rng, d):
    lim = math.sqrt(6.0 / (d + V))
    row = rng.uniform(-lim, lim, size=d)
    l1 = np.abs(row).sum()
    if l1 > 8.0:
        row *= 8.0 / l1
    return row


def build(rng, d):
    nb = d // B
    cb = CHI * B
    th = {
        "Us": xavier(rng, (d, d), 1.0, d, d),
        "Ug": xavier(rng, (d, d), 1.0, d, d),
        "Wm": xavier(rng, (d, 32), 8.0, 32, d),
        "e": rng.uniform(-0.01, 0.01, size=d),
        "Wq": xavier(rng, (M, d), 2.0, d, M),
        "Wk": xavier(rng, (M, d), 2.0, d, M),
        "Wv": xavier(rng, (M, d), 2.0, d, M),
        "Wr": xavier(rng, (d, M), 2.0, M, d),
        "A": xavier(rng, (nb, J, cb, d), 1.0, d, cb),
        "C": xavier(rng, (nb, J, cb, d), 2.0, d, cb),
        "B": xavier(rng, (nb, J, B, cb), 0.9, cb, B),
        "Wp": xavier(rng, (21, d), 8.0, d, 128),
    }
    fmeta = np.zeros(32)
    fmeta[2] = 1.0  # proposal mode
    fmeta[4] = 1.0  # text modality
    th["fmeta"] = fmeta
    th["bias_meta"] = th["Wm"] @ fmeta
    return th


def forward(th, tok, s, g, mem_k, mem_v, K, mask):
    d = s.shape[0]
    nb = d // B
    z0 = np.tanh(tok + th["Us"] @ s + th["Ug"] @ g + th["bias_meta"] + th["e"])
    if mem_k.shape[0] == 0:
        z = np.tanh(z0)
    else:
        q = np.tanh(th["Wq"] @ z0)
        logits = mem_k @ q / math.sqrt(M)
        logits = logits - logits.max()
        w = np.exp(logits)
        w /= w.sum()
        r = w @ mem_v
        z = np.tanh(z0 + th["Wr"] @ r)
    h = RHO * s + (1.0 - RHO) * z
    h0 = h.copy()
    A, C, Bm = th["A"], th["C"], th["B"]
    for _ in range(K):
        u = np.tanh(np.einsum("njcd,d->njc", A, h) + np.einsum("njcd,d->njc", C, z))
        fb = np.tanh(np.einsum("njbc,njc->njb", Bm, u)).mean(axis=1)
        hb = h.reshape(nb, B)
        keep = (1.0 - ALPHA * mask)[:, None]
        hb = keep * hb + (ALPHA * mask)[:, None] * fb
        h = hb.reshape(d)
    return h, h0


def p1_steps(h_norm, l0, y=1.0, limit=200000):
    """Aligned P1. Returns steps to q>=0.9, or None if the cap cannot."""
    if h_norm <= 0.0:
        return None, sig(l0)
    p = 0.0
    q = float(sig(l0))
    for s in range(1, limit + 1):
        dh = EPS + h_norm * h_norm
        g = (q - y) * h_norm / dh + LAM * p
        p = p - ETA * g
        if abs(p) > 1.0:
            p = math.copysign(1.0, p)
        q = float(sig(l0 + p * h_norm))
        if q >= Q_STAR:
            return s, q
    return None, q


def stats(x):
    a = np.sort(np.asarray(x, dtype=np.float64))
    n = a.size
    def q(p):
        if n == 1:
            return float(a[0])
        i = p * (n - 1)
        lo = int(math.floor(i))
        hi = int(math.ceil(i))
        t = i - lo
        return float(a[lo] * (1 - t) + a[hi] * t)
    return {
        "n": int(n),
        "min": float(a[0]),
        "median": q(0.5),
        "p95": q(0.95),
        "max": float(a[-1]),
    }


def fmt(st):
    return f"n={st['n']} min={st['min']:.6f} med={st['median']:.6f} p95={st['p95']:.6f} max={st['max']:.6f}"


def run_d(d, n_prop, n_chain):
    rng = np.random.default_rng(SEED + d)
    th = build(rng, d)
    nb = d // B
    g = np.zeros(d)
    full = np.ones(nb)
    half = np.zeros(nb)
    half[: max(1, nb // 2)] = 1.0
    rows = []
    box_break = 0
    nan_n = 0
    for i in range(n_prop):
        s = np.zeros(d)
        empty_k = np.zeros((0, M))
        empty_v = np.zeros((0, M))
        tok0 = token_row(rng, d)
        h_dec, _ = forward(th, tok0, s, g, empty_k, empty_v, 8, full)
        toks = [token_row(rng, d) for _ in range(4)]
        s = h_dec.copy()
        h0_last = None
        for tok in toks:
            h, h0_last = forward(th, tok, s, g, empty_k, empty_v, 8, full)
            s = h
        h_a = s
        s = h_dec.copy()
        for tok in toks:
            h, _ = forward(th, tok, s, g, empty_k, empty_v, 1, full)
            s = h
        h_k1 = s
        s = h_dec.copy()
        for tok in toks:
            h, _ = forward(th, tok, s, g, empty_k, empty_v, 8, half)
            s = h
        h_half = s
        if not np.isfinite(h_a).all():
            nan_n += 1
            continue
        if float(np.max(np.abs(h_a))) > 1.0 + 1e-8:
            box_break += 1
        hn = float(np.linalg.norm(h_a))
        l0 = th["Wp"] @ h_a  # b_p = 0, p0 = 0
        q0 = sig(l0)
        cap = sig(l0 + hn)
        need = math.log(Q_STAR / (1.0 - Q_STAR))
        reach = (need - l0) <= hn
        l0_half = th["Wp"] @ h_half
        reach_half = (need - l0_half) <= float(np.linalg.norm(h_half))
        rows.append({
            "hn": hn,
            "hinf": float(np.max(np.abs(h_a))),
            "frac_hot": float(np.mean(np.abs(h_a) > 0.5)),
            "pre_gap": float(np.linalg.norm(h_dec - h_a)),
            "h0n": float(np.linalg.norm(h0_last)),
            "k1n": float(np.linalg.norm(h_k1)),
            "halfn": float(np.linalg.norm(h_half)),
            "k1_gap": float(np.linalg.norm(h_k1 - h_a)),
            "half_gap": float(np.linalg.norm(h_half - h_a)),
            "l0": l0,
            "q0": q0,
            "cap": cap,
            "reach": reach,
            "reach_half": reach_half,
        })
    # mode B: one chain, frozen weights, s and M evolve, P stays 0
    s = np.zeros(d)
    mem_k = np.zeros((0, M))
    mem_v = np.zeros((0, M))
    prev_h = None
    prev_l0 = None
    drift_h = []
    drift_l0 = []
    for t in range(n_chain):
        tok = token_row(rng, d)
        h, _ = forward(th, tok, s, g, mem_k, mem_v, 8, full)
        s = h
        k = np.tanh(th["Wk"] @ h)
        v = np.tanh(th["Wv"] @ h)
        mem_k = np.vstack([mem_k, k])[-16:]
        mem_v = np.vstack([mem_v, v])[-16:]
        l0 = float(th["Wp"][0] @ h)  # verb row 0 of the active set, a=3
        if prev_h is not None:
            drift_h.append(float(np.linalg.norm(h - prev_h)))
            drift_l0.append(abs(l0 - prev_l0))
        prev_h = h.copy()
        prev_l0 = l0
    # mode A: step counts on the recorded frozen pairs, verb a=3 only (first active row)
    steps = []
    unreachable = 0
    for row in rows:
        got, q_end = p1_steps(row["hn"], float(row["l0"][0]))
        if got is None:
            unreachable += 1
        else:
            steps.append(got)
    return {
        "d": d,
        "rows": rows,
        "box_break": box_break,
        "nan": nan_n,
        "drift_h": drift_h,
        "drift_l0": drift_l0,
        "steps": steps,
        "unreachable_a3": unreachable,
        "wp_l1_max": float(np.abs(th["Wp"]).sum(axis=1).max()),
        "a_l1_max": float(np.abs(th["A"]).sum(axis=-1).max()),
    }


def main():
    print("UNO-LAB-001 H-FIX frozen re-encode")
    print(f"seed_base={SEED} V={V} biases=0 p0=0 b_p=0 K_main=8 mask_main=full")
    print("E row init fan_out=V then L1<=8. Not trained Theta.")
    for d, n_prop, n_chain in ((512, 32, 12), (1024, 16, 12)):
        out = run_d(d, n_prop, n_chain)
        rows = out["rows"]
        hn = [r["hn"] for r in rows]
        l0 = np.concatenate([r["l0"] for r in rows])
        q0 = np.concatenate([r["q0"] for r in rows])
        reach = np.concatenate([r["reach"] for r in rows])
        cap_move = np.concatenate([r["cap"] - r["q0"] for r in rows])
        print(f"\n=== d={d} proposals={len(rows)} box_breaks={out['box_break']} nan={out['nan']} ===")
        print("||h_a||", fmt(stats(hn)))
        print("||h||_inf", fmt(stats([r["hinf"] for r in rows])))
        print("frac |h|>0.5", fmt(stats([r["frac_hot"] for r in rows])))
        print("||h_dec-h_a||", fmt(stats([r["pre_gap"] for r in rows])))
        print("||h0_last||", fmt(stats([r["h0n"] for r in rows])))
        print("||h_K1||", fmt(stats([r["k1n"] for r in rows])))
        print("||h_half||", fmt(stats([r["halfn"] for r in rows])))
        print("||h_K1-h_a||", fmt(stats([r["k1_gap"] for r in rows])))
        print("||h_halfmask-h_a||", fmt(stats([r["half_gap"] for r in rows])))
        print("l0 over a=3..23", fmt(stats(l0)))
        print("q0 p=0", fmt(stats(q0)))
        print("cap-q0", fmt(stats(cap_move)))
        reach_h = np.concatenate([r["reach_half"] for r in rows])
        print(f"fraction q*=0.9 reachable on full mask={float(reach.mean()):.4f}; on half mask={float(reach_h.mean()):.4f}")
        print(f"a=3 P1 steps to 0.9: reached {len(out['steps'])} unreachable {out['unreachable_a3']}")
        if out["steps"]:
            print("steps", fmt(stats(out["steps"])))
        print("mode B ||dh_a||", fmt(stats(out["drift_h"])))
        print("mode B |dl0| a=3", fmt(stats(out["drift_l0"])))
        print(f"caps Wp_row_L1_max={out['wp_l1_max']:.4f} A_row_L1_max={out['a_l1_max']:.4f}")
        # one explicit example
        r0 = rows[0]
        print(
            f"example0 ||h||={r0['hn']:.6f} l0_a3={float(r0['l0'][0]):.6f} "
            f"q0={float(r0['q0'][0]):.6f} cap={float(r0['cap'][0]):.6f} "
            f"reach09={bool(r0['reach'][0])} p0=0"
        )


if __name__ == "__main__":
    main()
