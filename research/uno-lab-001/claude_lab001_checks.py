#!/usr/bin/env python3
"""UNO-LAB-001 independent precode checks (Claude). Pure numerics; no product code, no training of Theta.
Sources: ASTRA_04 sec.2-3 (P1,P2,P3,retention), ASTRA_02 W2 table, UNO-G4-LEARN-001 (GPT) numbers.
Run: python3 uno_lab001_checks.py   (numpy only; deterministic seed)"""
import math
import numpy as np

rng = np.random.default_rng(20261105)
sig = lambda x: 1.0 / (1.0 + np.exp(-x))
EPS, LAM, ETA, PMAX = 1.0, 1e-3, 1e-2, 1.0


def banner(s):
    print("\n=== " + s + " ===")


# ---------------------------------------------------------------- A1 arithmetic (GPT page sec.2,4)
def N_theta(d, V=32768, m=128, chi=4, J=2, b=64, H=902):
    return (V * d + 951 * d + 2 * d * d + 4 * m * d + J * (2 * chi * d * d + chi * b * d + (chi + 1) * d)
            + H * (d + 1) + V + (d // b) * (2 * d + 5) + 33)


banner("A1 arithmetic recomputation")
for d, claim in ((512, 23_015_887), (1024, 55_451_639)):
    n = N_theta(d); free = n - 318 * (d + 1); cf = 2 * (2 * 4 * d * d + 4 * 64 * d)
    print(f"d={d}: N_theta={n:,} (claimed {claim:,}) match={n == claim}; N_free={free:,}; C_F={cf:,}; "
          f"8xC_F={8 * cf:,}; P_active={21 * d:,}; P_fp32={21 * d * 4 / 1024:.0f} KiB; "
          f"FP16 MiB={n * 2 / 2**20:.2f}")
print("E1 r=8,d=1024: params=%d, FP32 KiB=%d, 16B/param KiB=%d" % (2 * 1024 * 8, 2 * 1024 * 8 * 4 // 1024, 2 * 1024 * 8 * 16 // 1024))
print("1e6 events x 175,448,160 MAC = %s ; x6 = %s" % (f"{175_448_160 * 10**6:,}", f"{175_448_160 * 10**6 * 6:,}"))

# ---------------------------------------------------------------- A2 hand example (GPT page sec.3)
banner("A2 P1 hand example (h=1,l0=0,p=0,y=1)")
h = np.array([1.0]); p = np.array([0.0]); l0 = 0.0; y = 1.0
f = lambda p, h, l0, y: (-(y * math.log(sig(l0 + p @ h)) + (1 - y) * math.log(1 - sig(l0 + p @ h)))) / (EPS + h @ h) + LAM * (p @ p) / 2
q0 = sig(l0 + p @ h); dh = EPS + h @ h; g = (q0 - y) * h / dh + LAM * p
p1 = p - ETA * g
print(f"q0={q0}, dh={dh}, grad={g[0]}, p'={p1[0]}, q1={sig(l0 + p1 @ h):.10f}, f0={f(p, h, l0, y):.10f}, f1={f(p1, h, l0, y):.10f}")


# ---------------------------------------------------------------- A3 numeric check of P2, G, step, prob bounds
def p1_step(p, h, l0, y, eta=ETA):
    q = sig(l0 + p @ h); dh = EPS + h @ h
    pn = p - eta * ((q - y) * h / dh + LAM * p)
    nrm = np.linalg.norm(pn)
    return pn / max(1.0, nrm)


banner("A3 random check of P2 / G / step / prob bounds (n=200000 per d)")
Lsm = 0.25 + LAM
for d in (8, 64, 1024):
    viol_p2 = 0; worst_p2 = -1e9; worst_G = 0; worst_step = 0; worst_prob = 0; worst_logit_ratio = 0
    for _ in range(200_000 // (1 if d < 1000 else 20)):
        hn = float(np.exp(rng.uniform(-6, math.log(math.sqrt(d)))))  # ||h|| from 0.0025 to sqrt(d)
        h = rng.normal(size=d); h *= hn / np.linalg.norm(h)
        p = rng.normal(size=d); p *= rng.uniform(0, 1) ** (1 / d) / np.linalg.norm(p)  # inside unit ball
        l0 = rng.uniform(-6, 6); y = float(rng.integers(0, 2))
        eta = ETA if rng.random() < 0.8 else rng.uniform(1e-3, 1 / Lsm * 0.999)
        pn = p1_step(p, h, l0, y, eta)
        lhs = f(pn, h, l0, y); rhs = f(p, h, l0, y) - (1 / eta - Lsm / 2) * np.linalg.norm(pn - p) ** 2
        worst_p2 = max(worst_p2, lhs - rhs); viol_p2 += (lhs > rhs + 1e-12)
        gn = np.linalg.norm((sig(l0 + p @ h) - y) * h / (EPS + h @ h) + LAM * p); worst_G = max(worst_G, gn)
        if eta == ETA:
            st = np.linalg.norm(pn - p); worst_step = max(worst_step, st)
            x = rng.normal(size=d); x *= math.sqrt(d) * rng.uniform(0, 1) / np.linalg.norm(x)
            dl = abs((pn - p) @ x); dpr = abs(sig(l0 + pn @ h + 0) - sig(l0 + p @ h))  # prob change on trained input
            # prob change on old frozen input x with its own l0': use random l0' to test bound |dprob|<=|dlogit|/4
            l0x = rng.uniform(-6, 6); dprob = abs(sig(l0x + pn @ x) - sig(l0x + p @ x)); worst_prob = max(worst_prob, dprob)
            worst_logit_ratio = max(worst_logit_ratio, dl / (math.sqrt(d) * ETA * 0.501))
    print(f"d={d}: P2 violations={viol_p2} (max lhs-rhs={worst_p2:.2e}); max||grad||={worst_G:.4f} (bound .501); "
          f"max||p'-p||={worst_step:.5f} (bound .00501); max|dprob| on old x={worst_prob:.5f} (bound {math.sqrt(d) * ETA * .501 / 4:.5f}); "
          f"max |dlogit|/bound={worst_logit_ratio:.3f}")

# ---------------------------------------------------------------- A4 plasticity ceiling (NEW result)
banner("A4 plasticity ceiling: logit change on the SAME input per P1 step")
print("Claim: |dlogit_same| = eta*(1-q)*||h||^2/(eps+||h||^2) (+ lam term, + projection) < eta for y=1. Check + steps to flip q .1->.9")
mx = 0.0
for _ in range(100_000):
    d = 16; hn = float(np.exp(rng.uniform(-3, 4))); h = rng.normal(size=d); h *= hn / np.linalg.norm(h)
    p = rng.normal(size=d); p *= rng.uniform(0, 1) / np.linalg.norm(p); l0 = rng.uniform(-6, 6); y = float(rng.integers(0, 2))
    pn = p1_step(p, h, l0, y); mx = max(mx, abs((pn - p) @ h))
print(f"max |dlogit| over 100k random single steps = {mx:.6f}  (eta = {ETA})")
print("steps to move q from 0.1 to 0.9 on ONE repeated input (y=1, p0=0, defaults):")
l_start = math.log(.1 / .9)
for hn in (1, 2, 2.3, 3, 5, 10, 32):
    h = np.zeros(8); h[0] = hn; p = np.zeros(8); steps = 0; reached = None
    for s in range(1, 200_001):
        p = p1_step(p, h, l_start, 1.0)
        if sig(l_start + p @ h) >= .9: reached = s; break
    cap = sig(l_start + hn)
    print(f"  ||h||={hn:>5}: " + (f"{reached} steps" if reached else f"unreachable (projection caps q at {cap:.3f})"))

# ---------------------------------------------------------------- A5 eta coupling
banner("A5 eta coupling: worst-case certified interference vs plasticity (d=1024)")
G = .5 + LAM
print("eta   | plasticity ceiling (logit/step) | certified |dprob| on frozen old x (<=sqrt(d)*eta*G/4) | informative(<1)")
for eta in (.01, .05, .1, .25, .3, 1, 3):
    bound = 32 * eta * G / 4
    print(f"{eta:<5} | {eta:<31} | {bound:<54.4f} | {bound < 1}")
print("P2 descent guarantee needs eta < 1/L = %.3f" % (1 / Lsm))

# ---------------------------------------------------------------- A6 interference = Gram matrix (NEW result)
banner("A6 exact interference vs feature cosine (task1 y=1 trained, task2 y=0 untouched)")
d = 64; hn = 8.0; steps = 400
e1 = np.zeros(d); e1[0] = 1.0
print("cos(h1,h2) | q2 before | q2 after 400 steps on task1 | dq2 | predicted sign of d(logit2)")
for c in (0.0, .1, .3, .6, .9, 1.0):
    u = np.zeros(d); u[0] = c; u[1] = math.sqrt(1 - c * c)
    h1 = hn * e1; h2 = hn * u; p = np.zeros(d); l1 = l2 = 0.0
    q2b = sig(l2 + p @ h2)
    for _ in range(steps): p = p1_step(p, h1, l1, 1.0)
    q2a = sig(l2 + p @ h2)
    print(f"{c:<10} | {q2b:.4f}    | {q2a:.4f}                     | {q2a - q2b:+.4f} | {'+' if h1 @ h2 > 0 else '0'}")
print("Counterexample ASTRA_04 sec.3 (identical h, y1=1,y0=0), alternating updates 20000 steps:")
h = np.zeros(8); h[0] = 3.0; p = np.zeros(8)
for s in range(20000): p = p1_step(p, h, 0.0, float(s % 2 == 0))
q = sig(p @ h); bce = lambda y: -(y * math.log(q) + (1 - y) * math.log(1 - q))
print(f"  q={q:.4f}; BCE(y=1)={bce(1):.4f}, BCE(y=0)={bce(0):.4f}; best possible avg BCE for identical h = ln2 = {math.log(2):.4f}")

# ---------------------------------------------------------------- A7 P3 informativeness
banner("A7 P3 regret bound: when is it informative? (D=2, G=.501, eta=.01)")
Gp = .5 + LAM
b = lambda T: 4 / (2 * ETA) + ETA * Gp**2 * T / 2
print("bound(T) = %.1f + %.6f*T" % (4 / (2 * ETA), ETA * Gp**2 / 2))
for tol in (.2, .1, .05, .01):
    T = (4 / (2 * ETA)) / (tol - ETA * Gp**2 / 2)
    print(f"  avg-regret bound <= {tol}: needs T >= {math.ceil(T):,} updates of ONE verb row")

# ---------------------------------------------------------------- A8 sample size for paired acceptance
banner("A8 sample size for the ASTRA_04 paired Hoeffding radius sqrt(2 ln(1/alpha)/n)")
for alpha in (.05, .01):
    for t in (.02, .01):
        n = 2 * math.log(1 / alpha) / t**2
        print(f"  alpha={alpha}, radius {t}: n >= {math.ceil(n):,} paired outcomes (worst-case range [-1,1])")
print("Illustrative variance-adaptive (Bernstein, |X-E|<=2) if only 5% of pairs differ (var<=.05):")
for alpha in (.05, .01):
    t = .02; L = math.log(1 / alpha); n = L * (2 * .05 + (2 / 3) * 2 * t) / t**2
    print(f"  alpha={alpha}, radius {t}: n ~ {math.ceil(n):,}  (CONDITIONAL: needs a variance bound known in advance)")
