# UNO Mathematical Reference v0.1 — HOST-MATH GATE

**Status at 2026-11-01: 46/46 unit tests PASS (37 parameterized subcases), 99% Python statement coverage, 600 budget checks without violation, 147/147 synthetic holdout, maximum numerical gradient error 1.9244e-10.**

This is an independent research reference for the unified UNO mathematical control loop. It is **not** an Android application, an LLM, proof of general intelligence, proof of real-world energy efficiency, or an implementation of structural neural evolution.

Prerequisite: Python 3.10+; no external dependencies for acceptance.

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python run_acceptance.py
```

The second command prints a JSON summary and updates `reports/UNO_MATH_ACCEPTANCE_V0_1.json`.

`docs/UNO_SYSTEM_FORMULA.md` contains the equations, seven mathematical invariants/derivations and precise boundaries of the PASS claim. `uno_core/reference.py` is the executable finite-dimensional reference. `tests/test_math_contract.py` exercises the contract. `pyproject.toml` is for optional pytest users.

New readout weights are trained from new random initialization **only on an artificial 2D classification benchmark**; the full UNO core neural weights are not yet trained. No old Jarvis/JNO weights or Android authority are imported.

The Android authority `TrustedBoundary` is a **host simulation**; it is not a secure component inside a Python process and must be implemented independently with OS-backed checks in a production Android app.
