"""Offline full-statement SQL census for retained write-profiling windows."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import statistics

from explain_dml import HEADER, clean_lines

EVENT = re.compile(r"duration: ([0-9.]+) ms\s+(parse|bind|execute) ([^:]*):\s*(.*)")


def events(path):
    lines = clean_lines(path)
    result = []
    for i, line in enumerate(lines):
        m = EVENT.search(line)
        if not m:
            continue
        parts = [m[4]]
        j = i + 1
        while j < len(lines) and not HEADER.search(lines[j]):
            parts.append(lines[j]); j += 1
        query = " ".join("\n".join(parts).split())
        result.append(dict(phase=m[2], ms=float(m[1]), query=query,
                           sha256=hashlib.sha256(query.encode()).hexdigest()))
    return result


def category(q):
    upper = q.upper()
    if upper.startswith("BEGIN"):
        return "transaction_begin"
    if upper.startswith("SET "):
        return "transaction_configuration"
    if upper.startswith("COMMIT"):
        return "explicit_commit"
    if "IDENTITY_USERS" in upper:
        return "identity_lookup"
    if "INSERT INTO GRAPH_TYPES" in upper:
        return "type_registry_write"
    if "SELECT TYPE_NAME FROM GRAPH_TYPES" in upper and "JOIN" not in upper:
        return "type_registry_read"
    if "INSERT INTO ANCHORS" in upper:
        return "anchor_upsert"
    if "FOR UPDATE" in upper:
        return "optimistic_concurrency_check"
    if upper.startswith("SELECT") and "UNNEST(" in upper and "JOIN ANCHORS" in upper:
        return "graph_traversal"
    if upper.startswith("SELECT") and "FROM ANCHORS" in upper:
        return "anchor_load_or_acl"
    if upper.startswith(("INSERT", "UPDATE", "DELETE")):
        return "relational_dml"
    return "other"


def analyze(folder):
    paths = sorted(p for p in folder.glob("postgres-*.log") if re.fullmatch(r"postgres-\d+\.log", p.name))
    if not paths:
        raise ValueError(f"No individual request windows: {folder}")
    aggregate = defaultdict(lambda: dict(executions=0, parse_ms=0.0, bind_ms=0.0, execute_ms=0.0, request_count=0, sample_query=""))
    fingerprint = defaultdict(lambda: dict(executions=0, parse_ms=0.0, bind_ms=0.0, execute_ms=0.0))
    windows = []
    for path in paths:
        ev = events(path)
        seen = set()
        for event in ev:
            key = category(event["query"])
            item = aggregate[key]
            item[event["phase"] + "_ms"] += event["ms"]
            if event["phase"] == "execute":
                item["executions"] += 1
                seen.add(key)
            if not item["sample_query"]:
                item["sample_query"] = event["query"]
            sql = fingerprint[event["sha256"]]
            sql.update(query=event["query"], category=key)
            sql[event["phase"] + "_ms"] += event["ms"]
            sql["executions"] += event["phase"] == "execute"
        for key in seen:
            aggregate[key]["request_count"] += 1
        windows.append(dict(path=str(path), executions=sum(e["phase"] == "execute" for e in ev),
                            protocol_ms=sum(e["ms"] for e in ev)))
    for value in aggregate.values():
        value["executions_per_request"] = value["executions"] / len(paths)
        value["protocol_ms_per_request"] = sum(value[p + "_ms"] for p in ("parse", "bind", "execute")) / len(paths)
    return dict(folder=str(folder), request_windows=len(paths),
                total_executions=sum(w["executions"] for w in windows),
                executions_per_request=statistics.mean(w["executions"] for w in windows),
                categories=dict(aggregate), fingerprints=dict(fingerprint), windows=windows,
                interpretation="Complete multiline SQL reconstructed from raw logs. Parse/bind/execute server durations; explicit COMMIT events only. Implicit autocommit completion is not separately timed. Trigger work is included in parent statements and is not a separate SQL event. Repeated query counts measure commands, not network packets.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = {}
    for path in sorted(args.root.glob("*/*/profile.json")):
        result[str(path.parent.relative_to(args.root))] = analyze(path.parent)
    if not result:
        raise ValueError("No arm/operation profile.json files")
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: {"windows": v["request_windows"], "executions_per_request": v["executions_per_request"]} for k, v in result.items()}, indent=2))


if __name__ == "__main__":
    main()
