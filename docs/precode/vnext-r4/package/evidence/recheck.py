"""Verify exact historical function excerpts and paper arithmetic, with no Android runtime."""
import ast
import collections
import csv
import hashlib
import heapq
import json
import math
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
EXPECTED = {
    "V14": "6be1dabe8a0e678e7b36affbec999f15b2fd1fd48d91c5c5e2ae2a18494a8875",
    "V19": "ecdda2259b21fbe84aa2051cfe6e3f896f753443b37bbfbd39fa8203d8b66374",
    "V20": "7a5792f1e3cf4d5a27078a3198965f7ff1b933ab7364a005b171e3663febd310",
}
records = []


def require(name, condition, actual):
    records.append({"check": name, "ok": bool(condition), "observed": actual})
    if not condition:
        raise RuntimeError(f"{name}: {actual!r}")


def excerpts(version, definitions, constants=()):
    source, = (HERE / "v_sources").glob(f"{version}_*.py")
    raw = source.read_bytes()
    require(version + "_hash", hashlib.sha256(raw).hexdigest() == EXPECTED[version], EXPECTED[version])
    body = ast.parse(raw).body
    requested = set(definitions.split()) | set(constants)
    selected = {}
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in requested:
            selected[node.name] = node
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in constants:
                ast.literal_eval(node.value)
                selected[target.id] = node
    require(version + "_excerpts", set(selected) == requested, sorted(selected))
    env = {key: globals()[key] for key in ("heapq", "sqlite3", "hashlib", "json", "struct", "time")}
    env["MODEL_A"] = hashlib.sha256(b"fixture-model-a").digest()
    exec(compile(ast.Module(body=list(selected.values()), type_ignores=[]), source.name, "exec"), env)
    return env


def main():
    v19 = excerpts("V19", "Scheduler scenario", ("MODES", "PRIORITY", "CONTROL"))
    passed = sum(v19["scenario"](mode)[0] for mode in v19["MODES"])
    require("V19_legacy_virtual_scenarios", passed == 14, passed)
    scheduler = v19["Scheduler"]()
    scheduler.push(1, "OWNER", 1)
    scheduler.run()
    actual = (scheduler.outbox, len(scheduler.issue), scheduler.consumed)
    require("V19_pending_outbox_without_ready_tick", actual == ("outbox_from_1_1", 0, 0), actual)
    scheduler = v19["Scheduler"]()
    scheduler.push(1, "OWNER", 1)
    scheduler.push(2, "BOOT", 1)
    scheduler.run()
    require("V19_old_outbox_after_boot", scheduler.issue == [(2, "outbox_from_1_1")], scheduler.issue)

    v14 = excerpts("V14", "connect init_store meta bump header_bytes add validate_record validate_query row_matches cursor_stamp search_exact",
                   ("MAX_SLOTS", "MAX_PAYLOAD", "MAX_QUERY_BYTES", "MAX_CONDITIONS", "ALLOWED"))
    v20 = excerpts("V20", "connect make_db record event state token commit_result")
    with tempfile.TemporaryDirectory() as folder:
        db = v14["init_store"](Path(folder) / "v14.sqlite")
        try:
            for slot in range(3):
                v14["add"](db, slot, 100 + slot, f"fixture-{slot}".encode())
            query = [{"field": "time_scope", "op": "range", "value": [0, 5]}]
            accepted = v14["validate_query"](query)
            outcome = "RETURNED"
            try:
                v14["search_exact"](db, query)
            except TypeError:
                outcome = "TYPE_ERROR"
            require("V14_invalid_field_type", accepted and outcome == "TYPE_ERROR", [accepted, outcome])
            first = v14["search_exact"](db, [], k=1)
            cursor = dict(first["cursor"], next_slot=4)
            second = v14["search_exact"](db, [], k=1, cursor=cursor)
            outcome = [first["status"], first["matches"], second["status"], second["matches"]]
            require("V14_unbound_continuation", outcome == ["TRUNCATED", 3, "COMPLETE", 0], outcome)
        finally:
            db.close()

        path = Path(folder) / "v20.sqlite"
        v20["make_db"](path)
        db = v20["connect"](path)
        try:
            token = v20["token"](db)
            statuses = [v20["commit_result"](db, token) for _ in range(2)]
            require("V20_no_ticket_dedup_in_fixture", statuses == ["ACCEPTED"] * 2 and v20["state"](db)["accepted"] == 2, statuses)
            v20["event"](db, "STOP")
            rejected = v20["commit_result"](db, token)
            require("V20_stop_negative", rejected == "REJECTED_STALE", rejected)
        finally:
            db.close()

    trace, = HERE.glob("OWNER_A52_STAGE5*.csv")
    with trace.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    labels = collections.Counter(row["actual"] for row in rows)
    switches = sum(a["actual"] != b["actual"] for a, b in zip(rows, rows[1:]))
    counts = [sum(row[arm] == row["actual"] for row in rows) for arm in ("model", "persistence", "markov")]
    require("N007_stage5_transcription", [int(r["index"]) for r in rows] == list(range(1, 81))
            and all(r["stage"] == "5" and r["mode"] == "A" and r["model"] == "MOVE" for r in rows)
            and labels == {"MOVE": 77, "STILL": 3} and switches == 3 and counts == [77] * 3,
            {"rows": len(rows), "counts": labels, "switches": switches, "correct": counts,
             "sha256": hashlib.sha256(trace.read_bytes()).hexdigest()})

    prefix_masks = {sum(1 << ((j + i) % 16) for i in range(q)) for j in range(16) for q in range(1, 17)}
    require("mask_count", len(prefix_masks) == 241 and (1 << 16) - 1 == 65535, [len(prefix_masks), (1 << 16) - 1])
    types, b, r_u, active, k, degree = 3, 32, 128, 2, 4, 4
    added_params = types * b * r_u
    mac = k * active * degree * b * r_u
    stride = ((104 + 4 * 32 + 7) // 8) * 8
    graph_bytes = 256 + 1024 * stride
    require("graph_example", [added_params, mac, stride, graph_bytes] == [12288, 131072, 232, 237824],
            [added_params, mac, stride, graph_bytes])
    n_bounds = [math.ceil(2 * (math.sqrt(math.log(40)) + math.sqrt(math.log(10))) ** 2 / gap**2)
                for gap in (0.05, 0.03)]
    require("NCR_E6", n_bounds == [9457, 26268], n_bounds)

    # For a fixed feature h=(0.6, 0.8), ||h||_2=1. S7 is maximized by p=h.
    sigma = lambda value: 1 / (1 + math.exp(-value))
    upper = 0.6 * sigma(-0.6 + math.hypot(0.6, 0.8))
    require("P1_S7_threshold_unreachable", upper < 0.5, upper)
    print(json.dumps({"python": sys.version.split()[0], "sqlite": sqlite3.sqlite_version,
                      "checks": records}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
