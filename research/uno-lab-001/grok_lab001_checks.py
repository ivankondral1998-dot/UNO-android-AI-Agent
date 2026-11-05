#!/usr/bin/env python3
"""UNO-LAB-001 independent checks. Grok. No product code, no Theta training.
Sources: ASTRA_02 table; ASTRA_04 P1; ASTRA_01 S4/S5 box invariant.
"""
import math

EPS, LAM, ETA = 1.0, 1e-3, 1e-2


def sig(z):
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def N_theta(d, V=32768, m=128, chi=4, J=2, b=64, H=902):
    return (
        V * d + 951 * d + 2 * d * d + 4 * m * d
        + J * (2 * chi * d * d + chi * b * d + (chi + 1) * d)
        + H * (d + 1) + V + (d // b) * (2 * d + 5) + 33
    )


def main():
    print("UNO-LAB-001 Grok checks")
    print("=== G1 ASTRA_02 arithmetic ===")
    for d, alloc, free, cf in (
        (512, 23015887, 22852753, 4456448),
        (1024, 55451639, 55125689, 17301504),
    ):
        n = N_theta(d)
        fr = n - 318 * (d + 1)
        c = 2 * (2 * 4 * d * d + 4 * 64 * d)
        print(f"d={d} N={n} ok={n == alloc} free={fr} ok={fr == free} C_F={c} ok={c == cf}")

    L = math.log(9.0)
    gap = (L + math.exp(L)) - (-L + math.exp(-L))
    print("=== G2 integral y=1, q 0.1 to 0.9, lambda=0, alpha=1 ===")
    print(f"logit_gap={2 * L:.12f} integral={gap:.12f} steps={gap / ETA:.6f}")

    def step(p, rho, l0, y):
        q = sig(l0 + p * rho)
        dh = EPS + rho * rho
        g = (q - y) * rho / dh + LAM * p
        pn = p - ETA * g
        return math.copysign(1.0, pn) if abs(pn) > 1.0 else pn

    print("=== G3 repeated P1, aligned, l0=logit(0.1), y=1 ===")
    l0 = math.log(0.1 / 0.9)
    for rho in (1.0, 2.0, 3.0, 2 * L, 5.0, 32.0):
        p = 0.0
        reached = None
        q = sig(l0)
        for s in range(1, 200001):
            p = step(p, rho, l0, 1.0)
            q = sig(l0 + p * rho)
            if q >= 0.9:
                reached = s
                break
        print(f"rho={rho:.12f} steps={reached} q={q:.12f} cap={sig(l0 + rho):.12f}")

    print("=== G4 box corner ||h||_2=sqrt(d) ===")
    for d in (512, 1024):
        rho = math.sqrt(d)
        bound = ETA * (rho * rho / (EPS + rho * rho) + LAM * rho)
        print(f"d={d} rho={rho:.6f} one_step_abs_logit_bound={bound:.6f}")

    print("=== G5 E1 scale vs P cap, same start logit=0, eta=0.01 ===")
    print(f"P_cap_q={sig(1.0):.12f}")
    w = 0.0
    hit1 = hit9 = None
    for s in range(1, 5000):
        w = w + ETA * (1.0 - sig(w))
        if hit1 is None and w >= 1.0:
            hit1 = (s, w, sig(w))
        if hit9 is None and sig(w) >= 0.9:
            hit9 = (s, w, sig(w))
            break
    print(f"E1_cross_P_cap step={hit1[0]} logit={hit1[1]:.6f} q={hit1[2]:.6f}")
    print(f"E1_reach_0.9 step={hit9[0]} logit={hit9[1]:.6f} q={hit9[2]:.6f}")

    print("=== G6 overlapping old task, hard gate ===")
    x_o0 = 0.6

    def bce(q, y):
        q = min(1.0 - 1e-15, max(1e-15, q))
        return -(y * math.log(q) + (1.0 - y) * math.log(1.0 - q))

    for eta, gate in ((0.05, False), (0.05, True)):
        w00 = 1.0
        acc = rej = 0
        reached = None
        qn = sig(w00)
        qo = sig(w00 * x_o0)
        for s in range(1, 5001):
            qn = sig(w00)
            qo = sig(w00 * x_o0)
            dw = -eta * (qn - 1.0)  # y_new=1, x_new=(1,0)
            trial = w00 + dw
            if gate and bce(sig(trial * x_o0), 0.0) > bce(qo, 0.0) + 1e-15:
                rej += 1
                continue
            w00 = trial
            acc += 1
            if sig(w00) >= 0.9:
                reached = s
                break
        print(
            f"eta={eta} gate={gate} reached={reached} acc={acc} rej={rej} "
            f"q_new={sig(w00):.6f} q_old={sig(w00 * x_o0):.6f}"
        )


if __name__ == "__main__":
    main()
