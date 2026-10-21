"""
TPC-C sequential mix driver: New-Order 51.2% / Payment 48.8% (the 45/43
headline pair renormalized; Delivery/Order-Status/Stock-Level deferred).
Deterministic plan f(seed, iteration) -> same inputs on every arm. Single
client, warmup untimed, per-request server-span header + client wall.

DB-truth oracle before/after: order/order_line/new_order/history deltas,
d_next_o_id sum, w_ytd sum, plus the spec consistency check
d_next_o_id == max(o_id)+1 per district.

W=1 note: every supply_w_id == 1 - the spec's ~10% remote-warehouse lines
need W>1 and are out of scope for the single-warehouse latency build.

# burden: bench=tpcc feature=driver arm=shared
# burden: dbloc=30 notations=[sql,mongo-query] entity-reps=1 hand-tuning=0
(dbloc = the oracle count queries below; drive plumbing not counted)

Usage:
    python tpcc_run.py --arm postgres|sqlalchemy|jac
                       [--requests 400] [--warmup 50] [--name tpcc_smoke]
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
TPCC = HERE.parent / "tpcc"
SYLL = ["BAR", "OUGHT", "ABLE", "PRI", "PRES",
        "ESE", "ANTI", "CALLY", "ATION", "EING"]
ARMS = {
    "postgres": "http://localhost:8101",
    "sqlalchemy": "http://localhost:8102",
    "jac": "http://localhost:8106",
    "jaseci-pg": "http://localhost:8108",
}
PLAN_SEED = 4242


def c_last(num):
    return SYLL[num // 100] + SYLL[(num // 10) % 10] + SYLL[num % 10]


def build_plan(n):
    """Deterministic txn plan: same for every arm."""
    rng = random.Random(PLAN_SEED)
    plan = []
    for _ in range(n):
        if rng.random() < 0.512:
            lines = [{
                "i_id": rng.randint(1, 100_000), "supply_w_id": 1,
                "quantity": rng.randint(1, 10),
            } for _ in range(rng.randint(5, 15))]
            invalid = rng.random() < 0.01
            if invalid:
                lines[-1] = {**lines[-1], "i_id": -1}
            plan.append({"kind": "new_order", "d_id": rng.randint(1, 10),
                         "c_id": rng.randint(1, 3000), "lines": lines,
                         "invalid": invalid})
        else:
            by_name = rng.random() < 0.60
            plan.append({
                "kind": "payment", "d_id": rng.randint(1, 10),
                "c_d_id": rng.randint(1, 10),
                "amount": round(rng.uniform(1, 5000), 2),
                "c_last": c_last(rng.randint(0, 999)) if by_name else None,
                "c_id": None if by_name else rng.randint(1, 3000),
            })
    return plan


# ---------------------------------------------------------------- oracles --

def counts_pg():
    import psycopg
    with psycopg.connect("postgresql://postgres@localhost:5433/tpcc") as c:
        q = lambda sql: c.execute(sql).fetchone()[0]
        return {
            "orders": q("SELECT count(*) FROM orders"),
            "order_line": q("SELECT count(*) FROM order_line"),
            "new_order": q("SELECT count(*) FROM new_order"),
            "history": q("SELECT count(*) FROM history"),
            "next_o_sum": q("SELECT sum(d_next_o_id) FROM district"),
            "w_ytd": float(q("SELECT sum(w_ytd) FROM warehouse")),
            "consistency_bad": q(
                "SELECT count(*) FROM district d WHERE d.d_next_o_id - 1 <> "
                "(SELECT max(o_id) FROM orders o WHERE o.o_w_id=d.d_w_id "
                " AND o.o_d_id=d.d_id)"),
        }


def counts_jac():
    import pymongo
    db = pymongo.MongoClient("mongodb://localhost:27019")["jac_db"]
    a = db["_anchors"]
    arch = lambda t: a.count_documents({"arch_type": t})
    next_o = sum(d["data"]["archetype"]["d_next_o_id"] for d in
                 a.find({"arch_type": "District"}))
    w_ytd = sum(w["data"]["archetype"]["w_ytd"] for w in
                a.find({"arch_type": "Warehouse"}))
    bad = 0
    for d in a.find({"arch_type": "District"}):
        d_id = d["data"]["archetype"]["d_id"]
        top = a.find({"arch_type": "Order", "data.archetype.o_d_id": d_id}) \
            .sort("data.archetype.o_id", -1).limit(1)
        top = list(top)
        max_o = top[0]["data"]["archetype"]["o_id"] if top else 0
        if d["data"]["archetype"]["d_next_o_id"] - 1 != max_o:
            bad += 1
    return {
        "orders": arch("Order"), "order_line": arch("OrderLine"),
        "new_order": a.count_documents(
            {"arch_type": "Order", "data.archetype.new_order": True}),
        "history": arch("History"), "next_o_sum": next_o, "w_ytd": w_ytd,
        "consistency_bad": bad,
    }


def counts_jaseci_pg():
    """jaseci-pg oracle: same shape as counts_pg/counts_jac but queried via
    `jac db sql` (no direct psycopg dependency here -- the embedded
    cluster's connection details, e.g. unix socket dir, are an
    implementation detail of the runtime, not something this driver script
    should hardcode). Archetype fields live at props->'archetype'->>field
    (jsonb), same shape LTI stores in mongo's data.archetype.*."""
    import subprocess
    bin_ = "/home/aaron/Dev/Research/DatabaseResearch/JaseciFork-pg/jac/zig-out/bin/jac"
    app = TPCC / "jaseci-pg"
    q = """SELECT json_build_object(
        'orders', (SELECT count(*) FROM anchors WHERE arch_type='Order'),
        'order_line', (SELECT count(*) FROM anchors WHERE arch_type='OrderLine'),
        'new_order', (SELECT count(*) FROM anchors WHERE arch_type='Order'
            AND (props->'archetype'->>'new_order')::boolean),
        'history', (SELECT count(*) FROM anchors WHERE arch_type='History'),
        'next_o_sum', (SELECT coalesce(sum((props->'archetype'->>'d_next_o_id')::int),0)
            FROM anchors WHERE arch_type='District'),
        'w_ytd', (SELECT coalesce(sum((props->'archetype'->>'w_ytd')::float),0)
            FROM anchors WHERE arch_type='Warehouse'),
        'consistency_bad', (SELECT count(*) FROM (
            SELECT (props->'archetype'->>'d_id')::int AS d_id,
                   (props->'archetype'->>'d_next_o_id')::int AS next_o
            FROM anchors WHERE arch_type='District') d
          LEFT JOIN (
            SELECT (props->'archetype'->>'o_d_id')::int AS o_d_id,
                   max((props->'archetype'->>'o_id')::int) AS max_o
            FROM anchors WHERE arch_type='Order' GROUP BY 1) o
          ON o.o_d_id = d.d_id
          WHERE d.next_o - 1 <> coalesce(o.max_o, 0))
    )"""
    out = subprocess.run([bin_, "db", "sql", q], cwd=app, capture_output=True,
                          text=True, timeout=60)
    line = [l for l in out.stdout.splitlines() if l.strip().startswith("{")]
    if not line:
        sys.exit(f"FATAL: counts_jaseci_pg parse failure: {out.stdout}\n{out.stderr}")
    return json.loads(line[-1])


COUNTS = {"postgres": counts_pg, "sqlalchemy": counts_pg, "jac": counts_jac,
          "jaseci-pg": counts_jaseci_pg}


# ---------------------------------------------------------------- requests --

class JacTargets:
    def __init__(self, arm="jac"):
        t = TPCC / ("jac-lti" if arm == "jac" else "jaseci-pg") / "targets"
        self.tokens = json.loads((t / "tokens.json").read_text())
        wh = json.loads((t / "warehouse.json").read_text())
        self.districts = {int(k): v for k, v in wh["districts"].items()}
        self.customers = json.loads((t / "customers.json").read_text())
        self.items = {int(k): v for k, v in
                      json.loads((t / "items.json").read_text()).items()}
        self.stocks = {int(k): v for k, v in
                       json.loads((t / "stocks.json").read_text()).items()}


def one_txn(client, arm, txn, auth, jt):
    if arm in ("jac", "jaseci-pg"):
        if txn["kind"] == "new_order":
            body = {
                "district_id": jt.districts[txn["d_id"]],
                "customer_id": jt.customers[f"{txn['d_id']}:{txn['c_id']}"],
                "lines": [{
                    # invalid item: well-formed hex jid that resolves to
                    # nothing (jobj on a malformed string would throw)
                    "item_id": jt.items.get(l["i_id"], "0" * 32),
                    "stock_id": jt.stocks.get(l["i_id"], "0" * 32),
                    "supply_w_id": l["supply_w_id"], "quantity": l["quantity"],
                } for l in txn["lines"]],
            }
            path = "/walker/new_order"
        else:
            body = {
                "district_id": jt.districts[txn["d_id"]],
                "c_district_id": jt.districts[txn["c_d_id"]],
                "customer_id": jt.customers[f"{txn['c_d_id']}:{txn['c_id']}"]
                if txn["c_id"] is not None else "",
                "c_last": txn["c_last"] or "",
                "amount": txn["amount"],
            }
            path = "/walker/payment"
        r = client.post(path, json=body, headers=auth)
        if arm == "jaseci-pg" and r.status_code == 500 and txn["kind"] == "new_order":
            # native abort: New-Order raises on the invalid item: the
            # server's request handler calls ctx.mem.abort() (real
            # ROLLBACK -- see app.jac module docstring) and returns an
            # HTTP 500 error envelope, not a 200 with a rolled_back flag.
            # Distinguish from a genuine bug via the error envelope shape.
            body_err = r.json()
            is_abort = (body_err.get("ok") is False
                        and (body_err.get("error") or {}).get("code") == "EXECUTION_ERROR")
            if not is_abort:
                r.raise_for_status()
            srv_ms = (float(r.headers.get("x-server-total-ms") or 0)
                      + float(r.headers.get("x-server-commit-ms") or 0))
            return False, True, srv_ms or None, body_err
        r.raise_for_status()
        payload = r.json()
        if "data" in payload and isinstance(payload.get("data"), dict) \
                and "reports" in payload["data"]:
            payload = payload["data"]["reports"][0]
        ok = bool(payload.get("success"))
        rolled = bool(payload.get("rolled_back"))
        srv = r.headers.get("x-server-total-ms")
        cmt = r.headers.get("x-server-commit-ms")
        return ok, rolled, (float(srv) + (float(cmt) if cmt else 0.0)) if srv else None, payload
    # baselines
    if txn["kind"] == "new_order":
        body = {"d_id": txn["d_id"], "c_id": txn["c_id"], "lines": txn["lines"]}
        path = "/new_order"
    else:
        body = {k: txn[k] for k in ("d_id", "c_d_id", "amount", "c_id", "c_last")}
        path = "/payment"
    r = client.post(path, json=body, headers=auth)
    if r.status_code == 400:  # rollback case
        return False, True, float(r.headers.get("x-server-total-ms") or 0) or None, {}
    r.raise_for_status()
    return True, False, float(r.headers["x-server-total-ms"]), r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=ARMS, required=True)
    ap.add_argument("--requests", type=int, default=400)
    ap.add_argument("--warmup", type=int, default=50)
    ap.add_argument("--name", default="tpcc_run")
    args = ap.parse_args()

    plan = build_plan(args.warmup + args.requests)
    jt = JacTargets(args.arm) if args.arm in ("jac", "jaseci-pg") else None
    if args.arm in ("jac", "jaseci-pg"):
        auth = {"Authorization": f"Bearer {jt.tokens['w1']}"}
    else:
        tok = json.loads((TPCC / "tokens.json").read_text())["1"]
        auth = {"Authorization": f"Bearer {tok}"}

    before = COUNTS[args.arm]()
    stats = {"new_order": [], "payment": []}
    client_ms = {"new_order": [], "payment": []}
    ok_no = ok_pay = rolled = errors = 0
    exp_lines = 0

    with httpx.Client(base_url=ARMS[args.arm], timeout=60) as client:
        for i, txn in enumerate(plan):
            timed = i >= args.warmup
            t0 = time.perf_counter()
            try:
                ok, rb, srv, _ = one_txn(client, args.arm, txn, auth, jt)
            except Exception as e:
                errors += 1
                print(f"  error on {i} ({txn['kind']}): {type(e).__name__}: {e}")
                continue
            cms = (time.perf_counter() - t0) * 1000
            if ok and txn["kind"] == "new_order":
                ok_no += 1
                exp_lines += len(txn["lines"])
            elif ok:
                ok_pay += 1
            if rb:
                rolled += 1
            if timed and ok:
                if srv is not None:
                    stats[txn["kind"]].append(srv)
                client_ms[txn["kind"]].append(cms)

    after = COUNTS[args.arm]()
    d = {k: after[k] - before[k] for k in
         ("orders", "order_line", "new_order", "history", "next_o_sum")}
    ytd_d = round(after["w_ytd"] - before["w_ytd"], 2)
    exp_ytd = round(sum(t["amount"] for t in plan if t["kind"] == "payment"), 2)
    checks = {
        "orders": d["orders"] == ok_no,
        "order_line": d["order_line"] == exp_lines,
        "new_order_rows": d["new_order"] == ok_no,
        "history": d["history"] == ok_pay,
        "next_o_sum": d["next_o_sum"] == ok_no,
        "w_ytd": abs(ytd_d - exp_ytd) < 0.05 * max(ok_pay, 1),
        "consistency": after["consistency_bad"] == 0,
    }

    def p50(v):
        return round(sorted(v)[len(v) // 2], 2) if v else None

    result = {
        "arm": args.arm, "requests": args.requests, "errors": errors,
        "ok_new_order": ok_no, "ok_payment": ok_pay, "rolled_back": rolled,
        "server_p50_new_order": p50(stats["new_order"]),
        "server_p50_payment": p50(stats["payment"]),
        "client_p50_new_order": p50(client_ms["new_order"]),
        "client_p50_payment": p50(client_ms["payment"]),
        "oracle_deltas": {**d, "w_ytd": ytd_d, "w_ytd_expected": exp_ytd},
        "oracle": checks, "oracle_all_ok": all(checks.values()),
    }
    out = HERE / ".run" / f"{args.name}_{args.arm}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
    if errors or not result["oracle_all_ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
