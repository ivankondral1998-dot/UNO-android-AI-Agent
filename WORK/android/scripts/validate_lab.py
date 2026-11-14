#!/usr/bin/env python3
"""Validate lab report evidence semantics. Host fixture test is synthetic, not A52 evidence."""
import argparse
import json
from pathlib import Path

STATES={"PASS","FAIL","ABORTED","UNSUPPORTED","INCONCLUSIVE","NOT_RUN"}

def validate(obj):
    e=[]
    if obj.get("schema")!="UNO_OFFLINE_LAB_REPORT_1":e.append("invalid_schema")
    if obj.get("profile") not in ("QUICK","STRESS"):e.append("invalid_profile")
    if obj.get("neural_quality_tested") is not False:e.append("false_neural_claim")
    if obj.get("native_action_gate_tested") is not False:e.append("false_native_gate_claim")
    if obj.get("physical_joules_measured") is not False:e.append("false_joule_claim")
    if obj.get("no_external_effects") is not True:e.append("unexpected_effect_claim")
    if not isinstance(obj.get("device_before"),dict):e.append("missing_before")
    if not isinstance(obj.get("device_after"),dict):e.append("missing_after")
    if not isinstance(obj.get("results"),list):e.append("missing_results")
    else:
        ids=[]
        for i,row in enumerate(obj["results"]):
            if row.get("status") not in STATES:e.append(f"invalid_status_{i}")
            if not row.get("scenario"):e.append(f"unnamed_{i}")
            ids.append(row.get("scenario"))
        if len(ids)!=len(set(ids)):e.append("duplicate_scenario")
    return e

if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("json_files",nargs="+");v=a.parse_args()
    bad=0
    for name in v.json_files:
        obj=json.loads(Path(name).read_text(encoding="utf-8-sig"))
        errors=validate(obj)
        print(name,"PASS" if not errors else "INVALID:"+",".join(errors))
        bad+=bool(errors)
    raise SystemExit(1 if bad else 0)
