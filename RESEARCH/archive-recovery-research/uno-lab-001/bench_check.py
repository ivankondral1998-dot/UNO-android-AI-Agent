#!/usr/bin/env python3
"""Fail if the door does not name the last journal entry."""
import sys
from pathlib import Path

def headers(text):
    out = []
    for line in text.splitlines():
        if line.startswith("=== ") and not line.startswith("=== END"):
            out.append(line)
    return out

def main(root):
    root = Path(root)
    journal = (root / "UNO_LAB_REPORTS.txt").read_text(encoding="utf-8")
    bench = (root / "research/uno-lab-001/BENCH.txt").read_text(encoding="utf-8")
    last = headers(journal)[-1]
    if last not in bench:
        print("FAIL bench does not name the last journal entry")
        print(last)
        return 1
    if "Owner transport: no" not in bench:
        print("FAIL owner transport line missing")
        return 1
    print("BENCH_OK")
    print(last)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
