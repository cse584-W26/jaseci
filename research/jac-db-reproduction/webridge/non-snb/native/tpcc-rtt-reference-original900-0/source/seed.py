"""
TPC-C jac-LTI seeder: two accounts (tpcc_catalog owns Item nodes,
tpcc_w1 owns the operational tree), chunked bulk-import walkers, jid maps
exported for the driver (targets/ dir, gitignored).

Idempotent-by-reset: expects a FRESH server (empty :27019 jac_db + reset
.jac/data) - scripts/reset_tpcc_lti.sh does that.

# burden: bench=tpcc feature=loader arm=jac-lti
# burden: dbloc=0 notations=[json] entity-reps=1 hand-tuning=0
(HTTP driver plumbing; the persistence code it exercises is in
import_data.jac where its burden is counted)

Usage: python seed.py [--base-url http://localhost:8108] [--data ../data]

(jaseci-pg copy, phase 4 2026-08-14: HTTP driver plumbing only, no
persistence-code edits -- default port retargeted 8106 -> 8108.)
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

PASSWORD = "benchpass123"
HERE = Path(__file__).resolve().parent


def die(what, resp):
    sys.exit(f"FATAL: {what} -> HTTP {resp.status_code}: {resp.text[:300]}")


class Client:
    def __init__(self, base_url):
        self.http = httpx.Client(base_url=base_url, timeout=600.0)

    def token(self, username):
        cred = {"type": "password", "password": PASSWORD}
        r = self.http.post("/user/register", json={
            "identities": [{"type": "username", "value": username}],
            "credential": cred,
        })
        if r.status_code not in (200, 201, 400, 409):
            die(f"register {username}", r)
        r = self.http.post("/user/login", json={
            "identity": {"type": "username", "value": username},
            "credential": cred,
        })
        if r.status_code != 200:
            die(f"login {username}", r)
        return r.json()["data"]["token"]

    def walker(self, name, token, body):
        r = self.http.post(f"/walker/{name}", json=body,
                           headers={"Authorization": f"Bearer {token}"})
        if r.status_code != 200:
            die(f"walker {name}", r)
        resp = r.json()
        data = resp.get("data") or {}
        if "reports" in data:
            if not resp.get("ok"):
                sys.exit(f"FATAL: walker {name} error: {resp.get('error')}")
            return data["reports"][0]
        return resp  # lean mode


def chunked(rows, n):
    for i in range(0, len(rows), n):
        yield rows[i:i + n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8108")
    ap.add_argument("--data", default=str(HERE.parent / "data"))
    args = ap.parse_args()
    data = Path(args.data)
    targets = HERE / "targets"
    targets.mkdir(exist_ok=True)

    def load(name):
        return [json.loads(l) for l in (data / f"{name}.jsonl").open()]

    cl = Client(args.base_url)
    t_cat = cl.token("tpcc_catalog")
    t_w1 = cl.token("tpcc_w1")
    json.dump({"catalog": t_cat, "w1": t_w1},
              (targets / "tokens.json").open("w"))
    print("accounts registered")

    t0 = time.time()
    items = load("item")
    item_jid = {}
    for chunk in chunked(items, 5000):
        jids = cl.walker("seed_items", t_cat, {"rows": chunk})
        for r, j in zip(chunk, jids):
            item_jid[r["i_id"]] = j
        print(f"  items {len(item_jid)}/{len(items)} ({time.time()-t0:.0f}s)")
    json.dump(item_jid, (targets / "items.json").open("w"))

    w_row = load("warehouse")[0]
    w_jid = cl.walker("seed_warehouse", t_w1, {"row": w_row})
    print(f"warehouse {w_jid}")

    d_rows = load("district")
    d_jids = cl.walker("seed_districts", t_w1,
                       {"warehouse_id": w_jid, "rows": d_rows})
    district_jid = {r["d_id"]: j for r, j in zip(d_rows, d_jids)}
    json.dump({"warehouse": w_jid, "districts": district_jid},
              (targets / "warehouse.json").open("w"))

    customers = load("customer")
    cust_jid = {}
    for d_id in sorted({c["c_d_id"] for c in customers}):
        rows = [c for c in customers if c["c_d_id"] == d_id]
        for chunk in chunked(rows, 1500):
            jids = cl.walker("seed_customers", t_w1,
                             {"district_id": district_jid[d_id], "rows": chunk})
            for r, j in zip(chunk, jids):
                cust_jid[f"{d_id}:{r['c_id']}"] = j
        print(f"  customers d{d_id} done ({time.time()-t0:.0f}s)")
    json.dump(cust_jid, (targets / "customers.json").open("w"))

    stock = load("stock")
    stock_jid = {}
    for chunk in chunked(stock, 2500):
        rows = [{**r, "item_id": item_jid[r["s_i_id"]],
                 "s_dist": [r[f"s_dist_{d:02d}"] for d in range(1, 11)]}
                for r in chunk]
        jids = cl.walker("seed_stock", t_w1,
                         {"warehouse_id": w_jid, "rows": rows})
        for r, j in zip(chunk, jids):
            stock_jid[r["s_i_id"]] = j
        print(f"  stock {len(stock_jid)}/{len(stock)} ({time.time()-t0:.0f}s)")
    json.dump(stock_jid, (targets / "stocks.json").open("w"))

    orders = load("orders")
    done = 0
    for chunk in chunked(orders, 400):
        rows = [{**o, "customer_id": cust_jid[f"{o['o_d_id']}:{o['o_c_id']}"]}
                for o in chunk]
        n = cl.walker("seed_orders", t_w1, {"rows": rows})
        done += int(n)
        print(f"  orders {done}/{len(orders)} ({time.time()-t0:.0f}s)")

    print(f"SEED DONE in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
