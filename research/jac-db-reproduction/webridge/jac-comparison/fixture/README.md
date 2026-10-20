# Matched PostgreSQL anchor closure

The dedicated database is `jac_webridge_matched_20261020`, user `jac`, socket `/tmp/jacpg-d6275e76eb`, port 5432. The original `jac_snb_bench_pg_fbdb3a2c` was opened with `default_transaction_read_only=on`; no source writes, schema changes or service actions occur in these scripts.

Exactly 460,984 anchors, including 300,901 edges, come exclusively from the pinned `alignment/graph-fixture/anchors.tsv` used by the MySQL comparison. All thirteen business fields (ID, kind, type/module/fingerprint, root, endpoints, undirected flag, JSON properties, sequence and endpoint types) roundtrip with identical sorted COPY hashes. Endpoint and owner-root closure checks both report zero missing records. Export column eleven is physical xmin; it is not format_version. PostgreSQL assigns new transaction IDs, while format_version and updated_at use the copied table defaults. Original exported xmin remains available in the immutable input file.

`source-catalog.json` and `schema.sql` preserve source column defaults/nullability, sequence, constraints, 31 indexes, eight functions and sixteen triggers. Independent target verification confirms all source definitions remain present. Thirteen graph-type rows, four identity-user/lookup rows and schema_fingerprint KV state are copied; the other runtime metadata tables are empty. The source has no additional promotion-completion markers. Authentication metadata TSV files are private local inputs (mode 0600).

Derived promoted tables and adjacency tables start empty, and triggers are installed only after the anchors load. This avoids stale full-dataset mirrors and completion claims. The runtime agent runs the baseline first, then the canonical final-runtime provisioning/backfill and ANALYZE before final measurement. The initial fixture is already analyzed. Read `load-receipt.json` and `independent-verification.json` for counts, hashes, closure checks and pending derived-table counts.

Initial capture/load, refusing existing data:

```sh
reproduction/runtime/venv314/bin/python reproduction/webridge/jac-comparison/fixture/inspect_source.py
reproduction/runtime/venv314/bin/python reproduction/webridge/jac-comparison/fixture/create_database.py
reproduction/runtime/venv314/bin/python reproduction/webridge/jac-comparison/fixture/load_fixture.py
reproduction/runtime/venv314/bin/python reproduction/webridge/jac-comparison/fixture/verify_fixture.py
```

An offline-input rebuild requires no source database access and refuses to overwrite any existing database:

```sh
reproduction/runtime/venv314/bin/python reproduction/webridge/jac-comparison/fixture/restore_saved.py \
  --target jac_webridge_matched_replay_20261020
```

The rebuild uses frozen DDL/metadata hashes, the same anchor TSV, disabled anchor triggers during import, restored sequence state and ANALYZE. It leaves derived mirror backfill to the runtime provisioning step, matching the initial fixture's state. It never drops or modifies the original database.
