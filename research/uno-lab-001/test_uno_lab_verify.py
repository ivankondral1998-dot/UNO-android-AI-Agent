#!/usr/bin/env python3
"""Tests for the independent verifier, including inputs that must fail."""

import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import uno_lab_verify as v

ROOT = Path(__file__).resolve().parent


class MathTests(unittest.TestCase):
    def test_hand_step_matches_closed_form(self):
        row = v.math_hand_p1()
        self.assertEqual(row["status"], "PASS")
        self.assertAlmostEqual(row["p1"], 0.0025, places=12)

    def test_nan_is_rejected(self):
        with self.assertRaises(ValueError):
            v.p1_step([0.0], [float("nan")], 0.0, 1.0)

    def test_duplicate_receipt_does_not_move(self):
        rows = [[0.0] for _ in range(25)]
        held = v.apply_p1(rows, 3, [1.0], 0.0, 1.0, fresh=False)
        self.assertEqual(held[3], [0.0])

    def test_opposite_label_gets_worse(self):
        self.assertEqual(v.math_forgetting()["status"], "PASS")

    def test_illegal_mask_leaves_the_box(self):
        row = v.math_box()
        self.assertEqual(row["status"], "PASS")
        self.assertGreater(abs(row["illegal_mask_3"]), 1.0)

    def test_empty_mask_is_not_a_pass(self):
        row = v.s5_probe(8, "empty")
        self.assertEqual(row["status"], "FAIL")

    def test_probe_does_not_score_h0(self):
        row = v.s5_probe(8, "full")
        self.assertEqual(row["status"], "PASS")
        self.assertNotAlmostEqual(row["l0_from_h_a"], row["l0_from_h0"])

    def test_special_bound_is_not_universal(self):
        row = v.math_geometry()
        self.assertEqual(row["status"], "PASS")
        self.assertNotEqual(row["special_l0_logit_0_1"], row["bound_when_l0_is_0"])

    def test_verifier_source_has_no_or_true(self):
        tree = ast.parse((ROOT / "uno_lab_verify.py").read_text(encoding="utf-8"))
        self.assertEqual(v.find_or_true(tree), [])


class TreeTests(unittest.TestCase):
    def _script(self, directory: Path, name: str, source: str, stdout: bytes):
        lab = directory / "research" / "uno-lab-001"
        lab.mkdir(parents=True)
        (lab / name).write_text(source, encoding="utf-8")
        (lab / (name.replace(".py", "_output.txt"))).write_bytes(stdout)

    def test_missing_pin_is_fail_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = v.verify(root, reproduce=False)
            missing = [c for c in report["checks"] if c["id"].startswith("integrity:")]
            self.assertTrue(missing)
            self.assertTrue(all(c["status"] == "FAIL" for c in missing))
            self.assertEqual(v.exit_code(report), 1)
            self.assertNotIn("PASS", {c["status"] for c in missing})

    def test_corrupted_bytes_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel = "research/uno-lab-001/grok_lab001_checks.py"
            path = root / rel
            path.parent.mkdir(parents=True)
            path.write_bytes(b"not the published script\n")
            report = v.verify(
                root,
                reproduce=False,
                pins={rel: ("0" * 64, 4)},
                runs=(),
            )
            row = next(c for c in report["checks"] if c["id"] == "integrity:" + rel)
            self.assertEqual(row["status"], "FAIL")
            self.assertEqual(v.exit_code(report), 1)

    def test_or_true_in_a_lab_script_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lab = root / "research" / "uno-lab-001"
            lab.mkdir(parents=True)
            bad = "def f(x):\n    return x " + "or" + " True\n"
            (lab / "bad.py").write_text(bad, encoding="utf-8")
            hits = v.scan_python(root)
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0][2], "bool-or-constant-true")

    def test_reproduction_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lab = root / "research" / "uno-lab-001"
            lab.mkdir(parents=True)
            (lab / "toy.py").write_text("print('real')\n", encoding="utf-8")
            (lab / "toy_output.txt").write_bytes(b"other\n")
            row = v.reproduce_one(root, "research/uno-lab-001/toy.py", "research/uno-lab-001/toy_output.txt", 30)
            self.assertEqual(row["status"], "FAIL")

    def test_reproduction_exact_bytes_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lab = root / "research" / "uno-lab-001"
            lab.mkdir(parents=True)
            (lab / "toy.py").write_text("print('real')\n", encoding="utf-8")
            proc = subprocess.run([sys.executable, str(lab / "toy.py")], capture_output=True, check=False)
            (lab / "toy_output.txt").write_bytes(proc.stdout)
            row = v.reproduce_one(root, "research/uno-lab-001/toy.py", "research/uno-lab-001/toy_output.txt", 30)
            self.assertEqual(row["status"], "PASS")

    def test_crashing_script_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lab = root / "research" / "uno-lab-001"
            lab.mkdir(parents=True)
            (lab / "toy.py").write_text("raise SystemExit(3)\n", encoding="utf-8")
            (lab / "toy_output.txt").write_bytes(b"")
            row = v.reproduce_one(root, "research/uno-lab-001/toy.py", "research/uno-lab-001/toy_output.txt", 30)
            self.assertEqual(row["status"], "FAIL")
            self.assertNotEqual(row.get("returncode"), 0)

    def test_skipped_reproduction_is_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = v.verify(root, reproduce=False)
            skipped = [c for c in report["checks"] if c["kind"] == "REPRODUCTION"]
            self.assertTrue(skipped)
            self.assertTrue(all(c["status"] == "SPECIFIED_UNTESTED" for c in skipped))


if __name__ == "__main__":
    unittest.main()
