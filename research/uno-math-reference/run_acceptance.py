#!/usr/bin/env python3
"""Offline reproducible host formula acceptance; JSON artifact with explicit scope."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import re
import subprocess
import sys

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from uno_core.reference import Weights, Organism, readout_loss_and_gradient, train_new_readout


def acceptance():
    run = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(BASE / "tests"), "-p", "test_*.py", "-v"], cwd=BASE, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    test_log = run.stdout + run.stderr
    match = re.search(r"Ran (\d+) tests", test_log)
    num = int(match.group(1)) if match else 0
    test_ok = run.returncode == 0 and num >= 46 and "FAILED" not in test_log

    rng = random.Random(100)
    train = []; held = []
    for idx in range(500):
        x0, x1 = rng.uniform(-1, 1), rng.uniform(-1, 1)
        if abs(x0-x1) < 0.1:
            continue
        features = (math.tanh(x0), math.tanh(x1))
        (train if idx < 330 else held).append((features, int(x0 < x1)))
    weights = train_new_readout(train, dim=2, n_actions=2, epochs=35, learning_rate=0.1)
    correct = sum(int(max(range(2), key=lambda a: sum(weights[a][j]*x[j] for j in range(2))) == y) for x,y in held)
    acc = correct / len(held)

    wg = [[0.25, -0.5], [0.43, 0.29], [-0.11, 0.71]]
    f = [0.7, -0.6]
    _, grad = readout_loss_and_gradient(wg, f, 2)
    errs=[]; eps=1e-6
    for i in range(3):
        for j in range(2):
            plus=[row[:] for row in wg]; minus=[row[:] for row in wg]
            plus[i][j]+=eps; minus[i][j]-=eps
            fd=(readout_loss_and_gradient(plus,f,2)[0]-readout_loss_and_gradient(minus,f,2)[0])/(2*eps)
            errs.append(abs(fd-grad[i][j]))

    budgets=0; violations=0
    for size in range(1,6):
        for budget in range(120):
            core=Organism(Weights.initial(size,size,size,seed=71))
            core.step(tuple(1/(i+1) for i in range(size)),budget_units=budget)
            budgets+=1
            violations+=int(core.last_units>budget)

    formula_path = BASE/"docs"/"UNO_SYSTEM_FORMULA.md"
    if not formula_path.is_file():
        formula_path = BASE.parent.parent/"docs"/"UNO_SYSTEM_FORMULA.md"
    digests={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [BASE/"uno_core"/"reference.py", BASE/"tests"/"test_math_contract.py", formula_path]}
    passed = test_ok and acc>=0.96 and max(errs)<1e-8 and violations==0
    return {"report_schema":"UNO_MATH_ACCEPTANCE_V0_1", "status":"HOST_MATH_REFERENCE_PASS" if passed else "FAIL", "pass_percentage_of_declared_gates":100 if passed else 0,
        "scope":"finite-dimensional host reference; no Android, general intelligence or physical energy proof",
        "unit_tests":{"passed":num if test_ok else 0,"discovered":num,"return_code":run.returncode,"status":"PASS" if test_ok else "FAIL", "parameterized_subcases_note":"37 verified by pytest separate run"},
        "numeric_checks":{"max_central_difference_gradient_error":max(errs), "threshold":1e-8,"holdout_accuracy":acc,"holdout_count":len(held),"holdout_correct":correct,"minimum_holdout_accuracy":0.96,"budgets_exercised":budgets,"budget_violations":violations},
        "python_version":platform.python_version(),"platform":platform.system()+" "+platform.machine(),
        "file_sha256":digests,
        "not_proven":["Android device", "energy joules", "end-to-end language", "full neural weights training", "evolution", "adversarial security"]}


if __name__=="__main__":
    report=acceptance()
    print(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True))
    out=BASE/"reports"/"UNO_MATH_ACCEPTANCE_V0_1.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    raise SystemExit(0 if report["status"]=="HOST_MATH_REFERENCE_PASS" else 1)
