#!/usr/bin/env python3
"""UNO-LAB G1 conditional no-go: frozen H-FIX cannot separate 0.9/0.1 for one action.
Usage: python3 uno_pairwise_no_go_gpt6.py research/uno-lab-001/grok_lab001_hfix_output.txt
       python3 uno_pairwise_no_go_gpt6.py --self-test
No training; Python standard library only. Derived from ASTRA_02 Wp row L1<=8,
ASTRA_04 P[a] L2<=1, and the SHA-pinned H-FIX feature extrema.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import sys

PIN = "cfd5b0bebee162a07907714d10aa14177b09074da02958dfdd5099619947f3a5"
GAP_TARGET = 2 * math.log(9)  # logit(0.9)-logit(0.1)
ROUND_MARGIN = 0.0000005  # printed extrema use 6 decimal digits


def extract(text):
    if not text.startswith("UNO-LAB-001 H-FIX frozen re-encode\n") or "K_main=8 mask_main=full" not in text:
        raise ValueError("Wrong H-FIX fixture")
    expr = (r"^=== d=(512|1024) proposals=\d+ box_breaks=0 nan=0 ===\n"
            r"\|\|h_a\|\| n=\d+ min=[^\n]+? max=(\d+\.\d+)\n"
            r"\|\|h\|\|_inf n=\d+ min=[^\n]+? max=(\d+\.\d+)\n")
    rows = re.findall(expr, text, flags=re.MULTILINE)
    if len(rows) != 2 or {v[0] for v in rows} != {"512", "1024"}:
        raise ValueError("Missing/duplicate d=512 or d=1024 feature extrema")
    return {d: (float(l2), float(linf)) for d, l2, linf in rows}


def compute(l2, linf):
    # Same action a: l(h)=(Wp[a]+P[a])·h+b_p[a]. Bias cancels between contexts.
    # |l(h1)-l(h2)|<=||Wp[a]||1 ||delta_h||inf + ||P[a]||2 ||delta_h||2
    #                <=2*8*(max ||h||inf) + 2*1*(max ||h||2).
    if not all(math.isfinite(v) and v >= 0 for v in (l2, linf)):
        raise ValueError("Invalid feature bound")
    bound = 16 * (linf + ROUND_MARGIN) + 2 * (l2 + ROUND_MARGIN)
    return {"logit_gap_upper": bound, "probability_gap_upper": bound / 4,
            "required_gap_for_0.9_vs_0.1": GAP_TARGET,
            "opposite_confident_outcomes": "IMPOSSIBLE_FOR_FROZEN_FEATURES" if bound < GAP_TARGET else "NOT_RULED_OUT"}


def self_test():
    assert abs(GAP_TARGET - 4.394449154672439) < 1e-12
    assert abs(compute(.010210, .001524)["logit_gap_upper"] - .044813) < 1e-12
    assert abs(compute(.007541, .000839)["logit_gap_upper"] - .028515) < 1e-12
    assert compute(5, 5)["opposite_confident_outcomes"] == "NOT_RULED_OUT"
    try:
        extract("wrong fixture")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid fixture accepted")
    print("SELFTEST PASS")


def main(argv):
    if argv == ["--self-test"]:
        self_test()
        return 0
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        content = Path(argv[0]).read_bytes()
        actual = hashlib.sha256(content).hexdigest()
        if actual != PIN:
            raise ValueError("SHA-256 mismatch: " + actual)
        bound = {d: compute(*v) for d, v in extract(content.decode("utf-8")).items()}
        print(json.dumps({"source_sha256": actual, "status": "PROVEN_CONDITIONAL_ON_FROZEN_H_FIXTURE",
                          "assumptions": "same action, fixed h, Wp row L1<=8, P row L2<=1, arbitrary common b_p",
                          "dimensions": bound}, indent=2))
        return 0
    except Exception as exc:
        print(f"FAIL {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
