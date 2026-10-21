"""
Deterministic TPC-C population generator (spec 4.3.3 rules), W=1.

One fixed RNG seed -> byte-identical dataset on every run, so every arm
loads the SAME rows and count/consistency oracles are exact cross-arm.

Emits JSON-lines chunks to tpcc/data/ (gitignored):
    item.jsonl, warehouse.jsonl, stock.jsonl, district.jsonl,
    customer.jsonl, history.jsonl, orders.jsonl (order + its lines +
    new_order flag embedded - keeps order atomicity obvious for graph arms).

# burden: bench=tpcc feature=datagen arm=shared
# burden: dbloc=0 notations=[json] entity-reps=1 hand-tuning=0
(datagen is shared plumbing - no per-arm persistence code; dbloc counted 0)

Usage: python gendata.py [--out data/]
"""

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEED = 42
W = 1
DISTRICTS = 10
CUSTOMERS_PER_D = 3000
ITEMS = 100_000
ORDERS_PER_D = 3000
DELIVERED_UPTO = 2100  # orders 1..2100 delivered; 2101..3000 in new_order

SYLL = ["BAR", "OUGHT", "ABLE", "PRI", "PRES",
        "ESE", "ANTI", "CALLY", "ATION", "EING"]
C_LAST_C = 123  # spec: constant for NURand(255, 0, 999), fixed per dataset
EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


def c_last(num):
    return SYLL[num // 100] + SYLL[(num // 10) % 10] + SYLL[num % 10]


def make_gen(rng):
    def randstr(lo, hi=None):
        n = rng.randint(lo, hi) if hi else lo
        return "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(n))

    def nurand(a, x, y):
        return (((rng.randint(0, a) | rng.randint(x, y)) + C_LAST_C) % (y - x + 1)) + x

    def original(lo, hi):
        s = randstr(lo, hi)
        if rng.random() < 0.10:
            mid = rng.randint(0, max(len(s) - 8, 0))
            s = s[:mid] + "ORIGINAL" + s[mid + 8:]
        return s[:50]

    return randstr, nurand, original


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent / "data"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    randstr, nurand, original = make_gen(rng)

    def dump(name, rows):
        with (out / f"{name}.jsonl").open("w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        print(f"{name}: {len(rows)} rows")

    dump("item", [{
        "i_id": i, "i_im_id": rng.randint(1, 10_000),
        "i_name": randstr(14, 24), "i_price": round(rng.uniform(1, 100), 2),
        "i_data": original(26, 50),
    } for i in range(1, ITEMS + 1)])

    dump("warehouse", [{
        "w_id": w, "w_name": randstr(6, 10), "w_street_1": randstr(10, 20),
        "w_street_2": randstr(10, 20), "w_city": randstr(10, 20),
        "w_state": randstr(2).upper(), "w_zip": f"{rng.randint(0, 9999):04d}11111",
        "w_tax": round(rng.uniform(0, 0.2), 4), "w_ytd": 300_000.00,
    } for w in range(1, W + 1)])

    dump("stock", [{
        "s_i_id": i, "s_w_id": w, "s_quantity": rng.randint(10, 100),
        **{f"s_dist_{d:02d}": randstr(24) for d in range(1, 11)},
        "s_ytd": 0, "s_order_cnt": 0, "s_remote_cnt": 0,
        "s_data": original(26, 50),
    } for w in range(1, W + 1) for i in range(1, ITEMS + 1)])

    dump("district", [{
        "d_id": d, "d_w_id": w, "d_name": randstr(6, 10),
        "d_street_1": randstr(10, 20), "d_street_2": randstr(10, 20),
        "d_city": randstr(10, 20), "d_state": randstr(2).upper(),
        "d_zip": f"{rng.randint(0, 9999):04d}11111",
        "d_tax": round(rng.uniform(0, 0.2), 4), "d_ytd": 30_000.00,
        "d_next_o_id": ORDERS_PER_D + 1,
    } for w in range(1, W + 1) for d in range(1, DISTRICTS + 1)])

    customers, history = [], []
    for w in range(1, W + 1):
        for d in range(1, DISTRICTS + 1):
            for c in range(1, CUSTOMERS_PER_D + 1):
                last_num = c - 1 if c <= 1000 else nurand(255, 0, 999)
                customers.append({
                    "c_id": c, "c_d_id": d, "c_w_id": w,
                    "c_first": randstr(8, 16), "c_middle": "OE",
                    "c_last": c_last(last_num),
                    "c_street_1": randstr(10, 20), "c_street_2": randstr(10, 20),
                    "c_city": randstr(10, 20), "c_state": randstr(2).upper(),
                    "c_zip": f"{rng.randint(0, 9999):04d}11111",
                    "c_phone": "".join(rng.choice("0123456789") for _ in range(16)),
                    "c_since": EPOCH.isoformat(),
                    "c_credit": "BC" if rng.random() < 0.10 else "GC",
                    "c_credit_lim": 50_000.00,
                    "c_discount": round(rng.uniform(0, 0.5), 4),
                    "c_balance": -10.00, "c_ytd_payment": 10.00,
                    "c_payment_cnt": 1, "c_delivery_cnt": 0,
                    "c_data": randstr(300, 500),
                })
                history.append({
                    "h_c_id": c, "h_c_d_id": d, "h_c_w_id": w,
                    "h_d_id": d, "h_w_id": w, "h_date": EPOCH.isoformat(),
                    "h_amount": 10.00, "h_data": randstr(12, 24),
                })
    dump("customer", customers)
    dump("history", history)

    orders = []
    for w in range(1, W + 1):
        for d in range(1, DISTRICTS + 1):
            cust_perm = list(range(1, CUSTOMERS_PER_D + 1))
            rng.shuffle(cust_perm)
            for o in range(1, ORDERS_PER_D + 1):
                delivered = o <= DELIVERED_UPTO
                entry = (EPOCH + timedelta(minutes=o)).isoformat()
                ol_cnt = rng.randint(5, 15)
                lines = [{
                    "ol_number": n, "ol_i_id": rng.randint(1, ITEMS),
                    "ol_supply_w_id": w,
                    "ol_delivery_d": entry if delivered else None,
                    "ol_quantity": 5,
                    "ol_amount": 0.00 if delivered
                    else round(rng.uniform(0.01, 9999.99), 2),
                    "ol_dist_info": randstr(24),
                } for n in range(1, ol_cnt + 1)]
                orders.append({
                    "o_id": o, "o_d_id": d, "o_w_id": w,
                    "o_c_id": cust_perm[o - 1], "o_entry_d": entry,
                    "o_carrier_id": rng.randint(1, 10) if delivered else None,
                    "o_ol_cnt": ol_cnt, "o_all_local": 1,
                    "new_order": not delivered,
                    "lines": lines,
                })
    dump("orders", orders)


if __name__ == "__main__":
    main()
