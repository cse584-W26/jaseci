# Isolated TPC-C W1 reproduction recipe

All paths below refer to `/home/baichuan/jaseci/reproduction`. No services were started and no databases were loaded while preparing these files.

## Inputs

`benchmark/tpcc/data/manifest.json` records the original, unmodified generator hash, seed 42, all seven JSONL hashes and counts. Orders embed 300,754 order lines and 9,000 initial new orders.

## Load hand SQL

Use `scripts/load_tpcc_postgres.py --admin-dsn 'host=/tmp/jacpg-d6275e76eb user=jac dbname=postgres' --dsn 'host=/tmp/jacpg-d6275e76eb user=jac dbname=tpcc'`. The original loader explicitly drops/recreates only `tpcc`; do not run during another measurement. Start the copied `benchmark/tpcc/postgres/app.py` via uvicorn with `TPCC_DSN` pointing to that isolated database and an unused HTTP port, e.g. 18112.

The driver reads `benchmark/tpcc/tokens.json`. Mint token for warehouse 1 using `jwt.encode({'w_id': 1}, 'supersecretkey_for_testing_only!', algorithm='HS256')`, save as `{'1': token}`. This matches the copied PG app's default JWT secret; if setting JWT_SECRET, mint with the same secret.

## Load Jac

Update only the copied `benchmark/tpcc/jaseci-pg/jac.toml` dev source path to the local Jac source. Start this app with the same isolated JAC_CACHE_HOME and Jac flags as SNB, on an unused port, e.g.18108. Project name `tpcc-bench-pg` creates a separate database from SNB.

Historical timed recipe uses a fresh database and `benchmark/tpcc/jaseci-pg/seed.py --base-url http://127.0.0.1:18108 --data benchmark/tpcc/data`. Seeder writes current authentication and ID maps under the copied app's `targets/`; old checked-in maps are stale until seed completes. It uses 5k item, 2.5k stock, 1.5k customer and 400 order HTTP chunks. This is the conservative original path.

A faster path also exists in `benchmark/scripts/pg_bulk_load.py --bench tpcc --mode control`, then `--mode full`, passing explicit `--app`, `--base`, `--data`, and optionally `--db`. It requires runtime-written archetype templates; fixtures must be accounted for in count/consistency oracles. Historical final timed cells used seed.py, so prefer that path for reproducibility.

## Drive each arm from a fresh load

Use `runtime/venv/bin/python scripts/tpcc_gate.py --arm postgres --base-url http://127.0.0.1:18112 --dsn 'host=/tmp/jacpg-d6275e76eb user=jac dbname=tpcc' --out-dir results/tpcc-pg`.

For Jac use `--arm jaseci-pg`, its HTTP URL, and its actual project database DSN. Discover the database by name `jac_tpcc_bench_pg_%`; do not assume the historical colleague's hash suffix.

The wrapper calls original `bench_timed.run_tpcc`: seed4242, 100 mutating warm transactions, then800 timed transactions; the raw CSV includes rollback timing just like historical data. It adds seven before/after DB-truth oracle checks from `tpcc_run.py`, with original SQL text. It emits `.csv`, `.warm.csv`, `.meta.json`, and `.oracle.json`. Oracle statements run outside the timed window.

Expected plan outcome across all900:487 successful NewOrder,406 Payment,7 rollback; delta orders/new_order/next_o_sum=487,order_line=4746,history=406,warehouse YTD=1062049.86. Warm100:50 NewOrder,49Payment,1rollback. Timed800:437NewOrder,357Payment,6rollback. These include both by-ID and by-last-name Payment.

Timing comparison must use like-for-like app flags, database logging off, fresh data per cell, and serial arm runs. The wrapper's transport changes are isolated from the original benchmark repository.
