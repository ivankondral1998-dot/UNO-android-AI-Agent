#!/usr/bin/env python3
"""UNO-LAB Independent Verifier. Research fixture, not UNO production code.

Three different results are never collapsed into one PASS:
  INTEGRITY      the file bytes match a pinned SHA-256
  REPRODUCTION   running the published script reprints the published stdout
  MATH           a quantity recomputed from the Astra contract

A matching stdout does not prove the script. A pinned hash does not prove the math.
Random weights are not trained Theta. Exit status is 1 when any check is FAIL.
REQUIRES_DATA and SPECIFIED_UNTESTED are not PASS and do not by themselves fail the process.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

TOOL = "UNO-LAB Independent Verifier"
EPS = 1.0
LAM = 0.001
ETA = 0.01
PMAX = 1.0
G_BOUND = 1.0 / (2.0 * math.sqrt(EPS)) + LAM * PMAX  # 0.501
L_SMOOTH = 0.25 + LAM  # 0.251

PINS = {
    "research/uno-lab-001/grok_lab001_checks.py": (
        "8f8a8ca9b54d01f3a6a476a9794f706ae79907ea83397addf529748972f71684",
        3694,
    ),
    "research/uno-lab-001/grok_lab001_output.txt": (
        "d0de2b551a22f8af79968eff58d5e3f2beb4898597b7bc952bb79d5448db94fd",
        1289,
    ),
    "research/uno-lab-001/grok_lab001_hfix.py": (
        "b70754f1c39faf564eb8a4fc0f671fbae961f75e56ab9ce9bf14d2757ee5225d",
        9810,
    ),
    "research/uno-lab-001/grok_lab001_hfix_output.txt": (
        "cfd5b0bebee162a07907714d10aa14177b09074da02958dfdd5099619947f3a5",
        2687,
    ),
    "research/uno-lab-001/claude_lab001_checks.py": (
        "f9027add08fc0481987ee6e94f9cf0976226a8d1ae4560eaffea9e72b8c2dae7",
        8426,
    ),
    "research/uno-lab-001/claude_lab001_output.txt": (
        "e2dacb5bd3b09d315d5876e74fdb1ac3c9f225bdc9499369d86d294650cf40bf",
        4720,
    ),
    "research/uno-lab-001/gpt_assignment_20261105.txt": (
        "a08e65411944ad63154a710d9813434f901b0d24d6f9b7d71550fd53641aacdd",
        19972,
    ),
    "research/uno-lab-001/gpt_g4_learn001.txt": (
        "5d92f9b99756afe9eb5d7de80553d9a5dfb561da5c229479b7fa04621dd40565",
        9539,
    ),
    "docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md": (
        "6bd6f68989972d183b6750711dca223355a026dfcf11461275d25406319853fe",
        26820,
    ),
    "docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_02_FINAL_WEIGHTS_CONNECTIVITY_AND_COUNTS.md": (
        "4b9186bb19d71f88aed989b33ef8a40f5a699535e645c79f5eb97d5d97098a4c",
        17474,
    ),
    "docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_04_MEMORY_PLASTICITY_RETENTION_RECOVERY.md": (
        "737654965c75e83e10a2705656af0f49ff9bf2c2bb0a4f359c67f0f426c6b0c8",
        13624,
    ),
}

RUNS = (
    (
        "research/uno-lab-001/grok_lab001_checks.py",
        "research/uno-lab-001/grok_lab001_output.txt",
    ),
    (
        "research/uno-lab-001/grok_lab001_hfix.py",
        "research/uno-lab-001/grok_lab001_hfix_output.txt",
    ),
    (
        "research/uno-lab-001/claude_lab001_checks.py",
        "research/uno-lab-001/claude_lab001_output.txt",
    ),
)

LIMITS = [
    "INTEGRITY is not mathematical correctness.",
    "REPRODUCTION is not mathematical correctness. A bug shared by the script and a copied checker would still match.",
    "MATH below recomputes P1, P2, the W2 count, the S5 box, and h_a sequencing. The S4/S5 probe uses J=1, d=8, b=4, empty memory, U_s=I. It is not the 198-tensor operator.",
    "2*ln(9) is only logit(0.9)-logit(0.1). It is not a universal feature-norm requirement.",
    "P2 is one frozen sample. It is not a promise that old tasks are kept. The opposite-label pair is checked separately.",
    "P3 is a realized convex sequence with a fixed comparator. It is not dynamic regret and not owner learning.",
    "No trained Theta and no A52 log are in this check. Those stay REQUIRES_DATA.",
    "The journal is append-only and is not hash-pinned.",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(cid: str, kind: str, status: str, **detail) -> dict:
    row = {"id": cid, "kind": kind, "status": status}
    row.update(detail)
    return row


def sigmoid(z: float) -> float:
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def logit(q: float) -> float:
    return math.log(q / (1.0 - q))


def dot(a, b) -> float:
    return sum(x * y for x, y in zip(a, b))


def norm(a) -> float:
    return math.sqrt(dot(a, a))


def project_l2(p, pmax: float = PMAX):
    n = norm(p)
    if n <= pmax:
        return list(p)
    scale = pmax / n
    return [x * scale for x in p]


def require_finite(values) -> None:
    for v in values:
        if not math.isfinite(v):
            raise ValueError("nonfinite input")


def p1_step(p, h, l0: float, y: float, eps=EPS, lam=LAM, eta=ETA, pmax=PMAX):
    """One P1 update. h and p are sequences. Refuses NaN instead of returning one."""
    require_finite([l0, y, eps, lam, eta, pmax])
    require_finite(p)
    require_finite(h)
    if len(p) != len(h):
        raise ValueError("shape")
    q = sigmoid(l0 + dot(p, h))
    dh = eps + dot(h, h)
    grad = [((q - y) * hj) / dh + lam * pj for hj, pj in zip(h, p)]
    raw = [pj - eta * gj for pj, gj in zip(p, grad)]
    return project_l2(raw, pmax), q


def apply_p1(rows, a: int, h, l0: float, y: float, fresh: bool = True):
    """Endpoint update. Duplicate receipt and rows outside 3..23 do not move."""
    out = [list(r) for r in rows]
    if not fresh or a < 3 or a > 23:
        return out
    out[a], _ = p1_step(out[a], h, l0, y)
    return out


def bce(y: float, q: float) -> float:
    q = min(1.0 - 1e-15, max(1e-15, q))
    return -(y * math.log(q) + (1.0 - y) * math.log(1.0 - q))


def f_loss(p, h, l0: float, y: float, eps=EPS, lam=LAM) -> float:
    q = sigmoid(l0 + dot(p, h))
    dh = eps + dot(h, h)
    return bce(y, q) / dh + 0.5 * lam * dot(p, p)


def n_theta(d: int, c951: int, H: int, V=32768, m=128, chi=4, J=2, b=64) -> int:
    return (
        V * d
        + c951 * d
        + 2 * d * d
        + 4 * m * d
        + J * (2 * chi * d * d + chi * b * d + (chi + 1) * d)
        + H * (d + 1)
        + V
        + (d // b) * (2 * d + 5)
        + 33
    )


def c_f(d: int, chi=4, J=2, b=64) -> int:
    return J * (2 * chi * d * d + chi * b * d)


def box_mix(h: float, feature: float, mask: float, alpha: float = 0.5) -> float:
    return (1.0 - alpha * mask) * h + (alpha * mask) * feature


def find_or_true(tree: ast.AST):
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            for value in node.values:
                if isinstance(value, ast.Constant) and value.value is True:
                    hits.append(getattr(node, "lineno", 0))
    return hits


def scan_python(root: Path):
    hits = []
    base = root / "research" / "uno-lab-001"
    if not base.is_dir():
        return hits
    for path in sorted(base.glob("*.py")):
        if path.name.startswith("test_"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            hits.append((str(path.relative_to(root)), exc.lineno or 0, "SyntaxError"))
            continue
        for line in find_or_true(tree):
            hits.append((str(path.relative_to(root)), line, "bool-or-constant-true"))
    return hits


def first_diff(got: bytes, exp: bytes) -> int:
    n = min(len(got), len(exp))
    for i in range(n):
        if got[i] != exp[i]:
            return i
    return n


def reproduce_one(root: Path, script_rel: str, stdout_rel: str, timeout: int) -> dict:
    script = root / script_rel
    published = root / stdout_rel
    cid = "reproduce:" + script_rel
    if not script.is_file() or not published.is_file():
        return check(
            cid,
            "REPRODUCTION",
            "FAIL",
            detail="script or published stdout missing; not treated as a pass",
        )
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(root),
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return check(cid, "REPRODUCTION", "FAIL", detail="timeout")
    except OSError as exc:
        return check(cid, "REPRODUCTION", "FAIL", detail=type(exc).__name__)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace")[-400:]
        return check(
            cid,
            "REPRODUCTION",
            "FAIL",
            returncode=proc.returncode,
            detail=err,
        )
    exp = published.read_bytes()
    if proc.stdout != exp:
        return check(
            cid,
            "REPRODUCTION",
            "FAIL",
            detail="stdout bytes differ",
            at=first_diff(proc.stdout, exp),
            got_bytes=len(proc.stdout),
            expected_bytes=len(exp),
            got_sha256=sha256_bytes(proc.stdout),
        )
    return check(
        cid,
        "REPRODUCTION",
        "PASS",
        bytes=len(exp),
        sha256=sha256_bytes(exp),
    )


def math_hand_p1() -> dict:
    p, q0 = p1_step([0.0], [1.0], 0.0, 1.0)
    q1 = sigmoid(0.0 + p[0] * 1.0)
    f0 = f_loss([0.0], [1.0], 0.0, 1.0)
    f1 = f_loss(p, [1.0], 0.0, 1.0)
    dp = abs(p[0] - 0.0)
    ok = (
        abs(q0 - 0.5) < 1e-15
        and abs(p[0] - 0.0025) < 1e-15
        and abs(q1 - 0.5006249997) < 5e-11
        and abs(f0 - 0.3465735903) < 5e-11
        and norm(p) <= 1.0
        and dp <= ETA * G_BOUND + 1e-15
    )
    return check(
        "p1-hand-step",
        "MATH",
        "PASS" if ok else "FAIL",
        q0=q0,
        p1=p[0],
        q1=q1,
        f0=f0,
        f1=f1,
    )


def math_p2() -> dict:
    h = [1.0]
    p0 = [0.0]
    p1, _ = p1_step(p0, h, 0.0, 1.0)
    f0 = f_loss(p0, h, 0.0, 1.0)
    f1 = f_loss(p1, h, 0.0, 1.0)
    dp2 = (p1[0] - p0[0]) ** 2
    drop = (1.0 / ETA - L_SMOOTH / 2.0) * dp2
    ok = ETA < 1.0 / L_SMOOTH and f1 <= f0 - drop + 1e-12
    return check(
        "p2-descent-frozen-h",
        "MATH",
        "PASS" if ok else "FAIL",
        f0=f0,
        f1=f1,
        required_drop=drop,
        note="one frozen sample; not a global task",
    )


def math_projection_and_rows() -> dict:
    blown, _ = p1_step([0.0], [1.0], 0.0, 1.0, eta=10.0)
    rows = [[0.0] for _ in range(25)]
    held = apply_p1(rows, 3, [1.0], 0.0, 1.0, fresh=False)
    outside = apply_p1(rows, 2, [1.0], 0.0, 1.0, fresh=True)
    inside = apply_p1(rows, 3, [1.0], 0.0, 1.0, fresh=True)
    ok = (
        norm(blown) <= 1.0 + 1e-12
        and held[3] == [0.0]
        and outside[2] == [0.0]
        and inside[3] != [0.0]
    )
    return check(
        "p1-projection-and-eligible-rows",
        "MATH",
        "PASS" if ok else "FAIL",
        projected_norm=norm(blown),
    )


def math_geometry() -> dict:
    special = logit(0.9) - logit(0.1)
    at_zero_l0 = logit(0.9) - 0.0
    caps = {rho: sigmoid(logit(0.1) + rho) for rho in (1.0, 2.0, 3.0)}
    ok = (
        abs(special - 2.0 * math.log(9.0)) < 1e-12
        and abs(at_zero_l0 - math.log(9.0)) < 1e-12
        and special != at_zero_l0
        and all(caps[r] < 0.9 for r in caps)
        and sigmoid(logit(0.1) + special) >= 0.9 - 1e-12
    )
    return check(
        "geometry-not-universal-4.394",
        "MATH",
        "PASS" if ok else "FAIL",
        special_l0_logit_0_1=special,
        bound_when_l0_is_0=at_zero_l0,
        cap_rho_1=caps[1.0],
    )


def math_forgetting() -> dict:
    h = [1.0]
    p, _ = p1_step([0.0], h, 0.0, 1.0)
    before = bce(0.0, sigmoid(0.0))
    after = bce(0.0, sigmoid(dot(p, h)))
    ok = after > before
    return check(
        "forgetting-opposite-label",
        "MATH",
        "PASS" if ok else "FAIL",
        old_bce_before=before,
        old_bce_after=after,
        note="P1 descent on y=1 raised BCE on y=0 for the same h",
    )


def math_box() -> dict:
    legal = box_mix(1.0, -1.0, 1.0)
    illegal = box_mix(1.0, -1.0, 3.0)
    ok = abs(legal) <= 1.0 and abs(illegal) > 1.0
    return check(
        "s5-box",
        "MATH",
        "PASS" if ok else "FAIL",
        legal=legal,
        illegal_mask_3=illegal,
        note="coefficients stay nonnegative only for mask in [0,1] and alpha in [0,1]",
    )


def math_p3() -> dict:
    G = G_BOUND
    eta = ETA
    T = 40
    p = 0.0
    grads = []
    played = []
    for t in range(T):
        g = G if (t % 2 == 0) else -G * 0.5
        grads.append(g)
        played.append(p)
        p = min(1.0, max(-1.0, p - eta * g))
    best = None
    for cand in (1.0, -1.0, 0.0):
        loss = sum(g * cand for g in grads)
        best = loss if best is None else min(best, loss)
    regret = sum(g * pt for g, pt in zip(grads, played)) - best
    bound = (2.0 ** 2) / (2.0 * eta) + eta * (G ** 2) * T / 2.0
    ok = regret <= bound + 1e-9
    return check(
        "p3-realized-sequence",
        "MATH",
        "PASS" if ok else "FAIL",
        regret=regret,
        bound=bound,
        T=T,
        note="fixed comparator on this sequence; not owner learning",
    )


def _rows(rng, n, width, cap):
    out = []
    for _ in range(n):
        row = [rng.random() * 2.0 - 1.0 for _ in range(width)]
        s = sum(abs(x) for x in row) or 1.0
        if s > cap:
            row = [x * cap / s for x in row]
        out.append(row)
    return out


def s5_probe(k: int, mask_name: str, d: int = 8, b: int = 4):
    """Contract-shaped probe. J=1, empty memory, U_s = I. Not UNO-B2."""
    if d > 32:
        return check(
            "s5-probe",
            "MATH",
            "SPECIFIED_UNTESTED",
            detail="probe refuses d>32 so it cannot be mistaken for the full operator",
        )
    if d % b != 0:
        return check("s5-probe", "MATH", "FAIL", detail="d not divisible by block")
    nb = d // b
    if mask_name == "full":
        mask = [1.0] * nb
    elif mask_name == "half":
        mask = [1.0 if i < max(1, nb // 2) else 0.0 for i in range(nb)]
    elif mask_name == "empty":
        return check(
            "s5-probe",
            "MATH",
            "FAIL",
            detail="empty mask is outside the contract: prefix masks are non-empty",
        )
    else:
        return check("s5-probe", "MATH", "FAIL", detail="unknown mask")
    if any(m < 0.0 or m > 1.0 for m in mask):
        return check("s5-probe", "MATH", "FAIL", detail="mask outside [0,1]")
    rng = __import__("random").Random(20261105)
    cb = 8
    A = [_rows(rng, cb, d, 1.0) for _ in range(nb)]
    C = [_rows(rng, cb, d, 2.0) for _ in range(nb)]
    B = [_rows(rng, b, cb, 0.9) for _ in range(nb)]

    def matvec(rows, x):
        return [sum(rows[i][j] * x[j] for j in range(len(x))) for i in range(len(rows))]

    def forward(token, s):
        z = [math.tanh(token[i] + s[i]) for i in range(d)]
        h = [0.5 * s[i] + 0.5 * z[i] for i in range(d)]
        h0 = list(h)
        for _ in range(k):
            nxt = [0.0] * d
            for blk in range(nb):
                u = [
                    math.tanh(matvec(A[blk], h)[i] + matvec(C[blk], z)[i])
                    for i in range(cb)
                ]
                fb = [math.tanh(v) for v in matvec(B[blk], u)]
                m = mask[blk]
                for j in range(b):
                    hj = h[blk * b + j]
                    nxt[blk * b + j] = (1.0 - 0.5 * m) * hj + (0.5 * m) * fb[j]
            h = nxt
        return h, h0

    perceive = [0.05 * (i + 1) for i in range(d)]
    h_dec, _ = forward(perceive, [0.0] * d)
    s = list(h_dec)
    h0_last = None
    for n in range(3):
        arg = [0.03 * ((n + 2) * (i + 1)) for i in range(d)]
        h, h0_last = forward(arg, s)
        s = h
    h_a = s
    wp = _rows(rng, 1, d, 8.0)[0]
    l_ha = dot(wp, h_a)
    l_h0 = dot(wp, h0_last)
    finite = all(math.isfinite(v) for v in h_a)
    boxed = all(abs(v) <= 1.0 + 1e-9 for v in h_a)
    distinct = norm([a - b for a, b in zip(h_a, h0_last)]) > 1e-9
    ok = finite and boxed and distinct and abs(l_ha - l_h0) > 1e-12
    return check(
        "h-a-after-reencode-probe",
        "MATH",
        "PASS" if ok else "FAIL",
        k=k,
        mask=mask_name,
        d=d,
        h_a_norm=norm(h_a),
        h0_norm=norm(h0_last),
        l0_from_h_a=l_ha,
        l0_from_h0=l_h0,
        note="probe only; do not read this norm as a UNO measurement",
    )


def math_counts(root: Path) -> dict:
    path = root / (
        "docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/"
        "ASTRA_02_FINAL_WEIGHTS_CONNECTIVITY_AND_COUNTS.md"
    )
    if not path.is_file():
        return check(
            "w2-counts",
            "MATH",
            "SPECIFIED_UNTESTED",
            detail="ASTRA_02 is not in this tree; the formula was not compared to the source file",
        )
    text = path.read_text(encoding="utf-8")
    m951 = re.search(r"951=(\d+)\+(\d+)\+(\d+)\+(\d+)\+(\d+)\+(\d+)", text)
    mH = re.search(r"H=3A\+128\+128\+258\+4=(\d+)", text)
    m318 = re.search(r"318\(d\+1\)", text)
    if not (m951 and mH and m318):
        return check("w2-counts", "MATH", "FAIL", detail="ASTRA_02 is missing the W2 coefficients")
    c951 = sum(int(x) for x in m951.groups())
    H = int(mH.group(1))
    if c951 != 951 or H != 902:
        return check("w2-counts", "MATH", "FAIL", detail="parsed coefficients do not add up")
    bad = []
    computed = {}
    for d in (512, 1024):
        n = n_theta(d, c951, H)
        free = n - 318 * (d + 1)
        mac = c_f(d)
        computed[str(d)] = {"N": n, "free": free, "C_F": mac, "P_active": 21 * d}
        spaced = f"{n:,}".replace(",", " ")
        if spaced not in text or str(mac) not in text.replace(" ", ""):
            # mac in the file is spaced: 4 456 448
            mac_spaced = f"{mac:,}".replace(",", " ")
            if spaced not in text or mac_spaced not in text:
                bad.append(d)
    return check(
        "w2-counts",
        "MATH",
        "FAIL" if bad else "PASS",
        computed=computed,
        missing_in_astra02=bad,
    )


def _stats(text: str, label: str):
    m = re.search(
        re.escape(label) + r" n=\d+ min=([-\d.]+) med=([-\d.]+) p95=([-\d.]+) max=([-\d.]+)",
        text,
    )
    if not m:
        return None
    return {"min": float(m.group(1)), "med": float(m.group(2)), "p95": float(m.group(3)), "max": float(m.group(4))}


def math_published_hfix(root: Path) -> dict:
    path = root / "research/uno-lab-001/grok_lab001_hfix_output.txt"
    if not path.is_file():
        return check(
            "published-hfix-vs-geometry",
            "MATH",
            "SPECIFIED_UNTESTED",
            detail="published hfix stdout is not in this tree",
        )
    text = path.read_text(encoding="utf-8")
    need = logit(0.9)
    problems = []
    notes = []
    blocks = re.split(r"\n=== d=", text)
    if len(blocks) < 2:
        return check("published-hfix-vs-geometry", "MATH", "FAIL", detail="no d-blocks")
    for block in blocks[1:]:
        hs = _stats(block, "||h_a||")
        l0 = _stats(block, "l0 over a=3..23")
        h0 = _stats(block, "||h0_last||")
        gap = _stats(block, "||h_dec-h_a||")
        frac = re.search(r"on full mask=([0-9.]+)", block)
        if not (hs and l0 and h0 and gap and frac):
            problems.append("unparsed")
            continue
        fraction = float(frac.group(1))
        if fraction > 0.0 and hs["max"] + l0["max"] < need:
            problems.append("fraction claims reach that max||h||+max l0 cannot support")
        if h0["min"] <= hs["max"]:
            problems.append("published h^0 is not above h_a")
        if gap["max"] <= 0.0:
            notes.append("re-encode gap is zero in the summary; substitution is not visible")
        notes.append(
            "d-block max||h_a||+max l0=%.6f logit(0.9)=%.6f fraction=%.4f"
            % (hs["max"] + l0["max"], need, fraction)
        )
    status = "FAIL" if problems else "PASS"
    return check(
        "published-hfix-vs-geometry",
        "MATH",
        status,
        problems=problems,
        notes=notes,
        limit="uses the published summary, not a second F. Reproduction is a separate check.",
    )


def math_published_grok_caps(root: Path) -> dict:
    path = root / "research/uno-lab-001/grok_lab001_output.txt"
    if not path.is_file():
        return check(
            "published-scalar-caps",
            "MATH",
            "SPECIFIED_UNTESTED",
            detail="grok stdout is not in this tree",
        )
    text = path.read_text(encoding="utf-8")
    l0 = logit(0.1)
    bad = []
    for m in re.finditer(
        r"rho=([0-9.]+) steps=(\S+) q=([0-9.]+) cap=([0-9.]+)",
        text,
    ):
        rho = float(m.group(1))
        steps = m.group(2)
        cap = float(m.group(4))
        recomputed = sigmoid(l0 + rho)
        if abs(recomputed - cap) > 1e-9:
            bad.append(("cap", rho))
        if steps == "None" and recomputed >= 0.9:
            bad.append(("none-but-reachable", rho))
        if steps != "None" and recomputed < 0.9 - 1e-12:
            bad.append(("steps-but-unreachable", rho))
    return check(
        "published-scalar-caps",
        "MATH",
        "FAIL" if bad else "PASS",
        mismatches=bad,
        note="cap is sigmoid(l0+rho) for this printed l0 only",
    )


def gpt_hand_digits(root: Path) -> dict:
    path = root / "research/uno-lab-001/gpt_g4_learn001.txt"
    if not path.is_file():
        return check(
            "gpt-hand-digits",
            "MATH",
            "SPECIFIED_UNTESTED",
            detail="GPT extract is not in this tree",
        )
    text = path.read_text(encoding="utf-8")
    p, _ = p1_step([0.0], [1.0], 0.0, 1.0)
    q1 = sigmoid(p[0])
    token = "0.5006249997"
    present = token in text
    close = abs(q1 - float(token)) < 5e-11
    ok = present and close
    return check(
        "gpt-hand-digits",
        "MATH",
        "PASS" if ok else "FAIL",
        recomputed_q1=q1,
        token_in_file=present,
    )


def limits_rows():
    return [
        check(
            "trained-theta",
            "LIMIT",
            "REQUIRES_DATA",
            detail="no trained weights are read; a random draw is not a skill",
        ),
        check(
            "a52-device",
            "LIMIT",
            "REQUIRES_DATA",
            detail="no device log is read",
        ),
        check(
            "full-operator",
            "LIMIT",
            "SPECIFIED_UNTESTED",
            detail="the 198-tensor F is not reimplemented here",
        ),
    ]


def verify(
    root: Path,
    reproduce: bool = True,
    timeout: int = 240,
    probe_k: int = 8,
    probe_mask: str = "full",
    pins=None,
    runs=None,
) -> dict:
    root = root.resolve()
    use_pins = PINS if pins is None else pins
    use_runs = RUNS if runs is None else runs
    rows = []
    for rel, (digest, size) in use_pins.items():
        path = root / rel
        if not path.is_file():
            rows.append(check("integrity:" + rel, "INTEGRITY", "FAIL", detail="missing"))
            continue
        data = path.read_bytes()
        got = sha256_bytes(data)
        if got != digest or len(data) != size:
            rows.append(
                check(
                    "integrity:" + rel,
                    "INTEGRITY",
                    "FAIL",
                    got_sha256=got,
                    expected_sha256=digest,
                    got_bytes=len(data),
                    expected_bytes=size,
                )
            )
        else:
            rows.append(check("integrity:" + rel, "INTEGRITY", "PASS", sha256=got, bytes=size))

    hits = scan_python(root)
    rows.append(
        check(
            "static-or-true",
            "STATIC",
            "FAIL" if hits else "PASS",
            hits=[{"path": p, "line": n, "what": w} for p, n, w in hits],
        )
    )
    rows.append(math_hand_p1())
    rows.append(math_p2())
    rows.append(math_projection_and_rows())
    rows.append(math_geometry())
    rows.append(math_forgetting())
    rows.append(math_box())
    rows.append(math_p3())
    rows.append(s5_probe(probe_k, probe_mask))
    rows.append(math_counts(root))
    rows.append(math_published_hfix(root))
    rows.append(math_published_grok_caps(root))
    rows.append(gpt_hand_digits(root))
    if reproduce:
        for script, out in use_runs:
            rows.append(reproduce_one(root, script, out, timeout))
    else:
        for script, _out in use_runs:
            rows.append(
                check(
                    "reproduce:" + script,
                    "REPRODUCTION",
                    "SPECIFIED_UNTESTED",
                    detail="--no-reproduce; the script was not executed",
                )
            )
    rows.extend(limits_rows())
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    failed = [row["id"] for row in rows if row["status"] == "FAIL"]
    return {
        "tool": TOOL,
        "root": str(root),
        "counts": counts,
        "failed": failed,
        "limits": LIMITS,
        "checks": rows,
    }


def exit_code(report: dict) -> int:
    return 1 if report["failed"] else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=TOOL)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--json", dest="json_path", type=Path, default=None)
    parser.add_argument("--no-reproduce", action="store_true")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--probe-k", type=int, default=8)
    parser.add_argument("--probe-mask", default="full", choices=("full", "half", "empty"))
    args = parser.parse_args(argv)
    root = args.root
    if root is None:
        here = Path(__file__).resolve()
        for cand in [here.parent, *here.parents]:
            if (cand / "UNO_LAB_AGENTS.md").is_file():
                root = cand
                break
        if root is None:
            print("repo root not found; pass --root", file=sys.stderr)
            return 1
    report = verify(
        root,
        reproduce=not args.no_reproduce,
        timeout=args.timeout,
        probe_k=args.probe_k,
        probe_mask=args.probe_mask,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False)
    if args.json_path:
        args.json_path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
