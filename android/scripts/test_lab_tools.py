#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

# Also test the guards themselves by mutating synthetic manifest/source fixtures.
from test_static_contract_check import GuardTests
from test_adb_selection import AdbSelectionTests

ROOT=Path(__file__).resolve().parent

def mod(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/f"{name}.py")
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

validate=mod("validate_lab")
compare=mod("compare_lab")


def fixture(p95=100,status="PASS"):
    return {"schema":"UNO_OFFLINE_LAB_REPORT_1","profile":"QUICK",
        "device_before":{"device_model":"A52_TEST_FIXTURE","memory":{"self_pss_kib":123},"thermal":{"thermal_status_code_or_null":0}},
        "device_after":{"device_model":"A52_TEST_FIXTURE"},
        "physical_joules_measured":False,"neural_quality_tested":False,
        "native_action_gate_tested":False,"no_external_effects":True,
        "results":[{"scenario":"CPU_FP32","status":status,"details":{"p95_ns":str(p95)}}]}

class Tests(unittest.TestCase):
    def test_accept_valid_schema(self):self.assertEqual(validate.validate(fixture()),[])
    def test_forbid_claim_of_model_quality(self):
        x=fixture();x["neural_quality_tested"]=True
        self.assertIn("false_neural_claim",validate.validate(x))
    def test_reject_duplicate_scenario(self):
        x=fixture();x["results"].append(x["results"][0])
        self.assertIn("duplicate_scenario",validate.validate(x))
    def test_reject_invalid_verdict(self):
        x=fixture(status="DEVICE_VERIFIED")
        self.assertIn("invalid_status_0",validate.validate(x))
    def test_compare_only_descriptive(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/"base.json",Path(tmp)/"candidate.json"
            a.write_text(json.dumps(fixture(100)))
            b.write_text(json.dumps(fixture(50)))
            self.assertEqual(compare.report(str(a),str(b)),0)
    def test_comparison_rejects_wrong_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"bad.json";p.write_text('{}')
            with self.assertRaises(ValueError):compare.parse(str(p))

if __name__=="__main__":unittest.main(verbosity=2)
