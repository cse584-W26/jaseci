#!/usr/bin/env python3
"""Verify executed hydration array widths directly from PostgreSQL raw logs."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def widths(path):
    statement = ""
    found = []
    with gzip.open(path, "rt") as stream:
        for line in stream:
            if " LOG: " in line:
                statement = line.split(" LOG: ", 1)[1]
            elif " DETAIL: " in line:
                if " execute " in statement and "FROM anchors a WHERE a.id = ANY" in statement:
                    params = line.split("Parameters: $1 = '{", 1)
                    if len(params) == 2:
                        ids = params[1].split("}'", 1)[0].split(",")
                        assert len(set(ids)) == len(ids), path
                        found.append(len(ids))
            else:
                statement += line
    return found


def main():
    rows = []
    groups = (
        ("tpcc-profiles-0-baseline", 0, "baseline"),
        ("tpcc-profiles-0-final-resumed", 0, "final"),
        ("tpcc-profiles-2-baseline", 2, "baseline"),
        ("tpcc-profiles-2-final", 2, "final"),
    )
    for group, delay, variant in groups:
        for lines in (5, 15):
            for repetition in range(3):
                path = ROOT / "native" / group / f"delay-{delay}ms" / variant / f"new_order_{lines}" / f"{repetition}.sql.log.gz"
                observed = widths(path)
                assert observed == [1, 1, 1, 1, lines * 2, 1], (path, observed)
                rows.append({"artifact": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "delay_ms": delay, "variant": variant, "order_lines": lines, "repetition": repetition, "executed_hydration_array_widths": observed})
    result = {"status": "PASS", "requests": len(rows), "scope": "Execute events only; bind events excluded. Each request has one combined 2*order_lines UUID hydration batch in both source versions.", "observations": rows}
    destination = ROOT / "tpcc-prefetch-verification.json"
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "requests": len(rows), "artifact": str(destination)}))


if __name__ == "__main__":
    main()
