#!/usr/bin/env python3
"""Read-only comparison of two UNO Android lab JSON files; doesn't turn data into a PASS gate."""
import argparse
import json
import pathlib
import statistics
import sys


def parse(path):
    value=json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
    if value.get("schema")!="UNO_OFFLINE_LAB_REPORT_1":
        raise ValueError(f"Unexpected lab schema in {path}: {value.get('schema')}")
    scenarios={x.get("scenario"):x for x in value.get("results",[])}
    return value,scenarios


def numeric(scenario,key):
    try:
        return float(scenario.get("details",{}).get(key))
    except (TypeError,ValueError):
        return None


def report(a,b):
    ra,ma=parse(a)
    rb,mb=parse(b)
    same_hardware=(ra.get("device_before",{}).get("device_model") == rb.get("device_before",{}).get("device_model"))
    same_profile=(ra.get("profile")==rb.get("profile"))
    print(f"UNO lab comparison: {a} vs {b}")
    print("Same device model:",same_hardware,"same workload profile:",same_profile)
    print("NOTE: equal model name != identical device state; no statistical significance implied")
    for name in sorted(set(ma)|set(mb)):
        one,two=ma.get(name,{}),mb.get(name,{})
        left,right=one.get("status","MISSING"),two.get("status","MISSING")
        print(f"{name:22} {left:13} -> {right:13}",end="")
        key = "p95_ns" if name=="CPU_FP32" else ("p95_batch_ns" if name=="CPU_SUSTAINED" else None)
        if key and same_hardware and same_profile:
            av,bv=numeric(one,key),numeric(two,key)
            if av is not None and bv is not None and av>0 and left==right=="PASS":
                print(f"   candidate / baseline p95 = {bv/av:.3f} (descriptive, temperature etc unknown)",end="")
        print()
    sa=ra.get("device_before",{}).get("memory",{})
    sb=rb.get("device_before",{}).get("memory",{})
    print("Initial PSS KiB:",sa.get("self_pss_kib"),"->",sb.get("self_pss_kib"))
    print("Initial thermal status:",ra.get("device_before",{}).get("thermal",{}).get("thermal_status_code_or_null"),"->",
          rb.get("device_before",{}).get("thermal",{}).get("thermal_status_code_or_null"))
    print("ABORTS:",ra.get("abort_reason_or_null"),"->",rb.get("abort_reason_or_null"))
    print("QUALITY/ENERGY/OS EFFECTS: UNVERIFIED by this comparison")
    return 0

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("baseline")
    p.add_argument("candidate")
    x=p.parse_args()
    try:
        raise SystemExit(report(x.baseline,x.candidate))
    except Exception as e:
        print("INCONCLUSIVE:",e,file=sys.stderr)
        raise SystemExit(2)
