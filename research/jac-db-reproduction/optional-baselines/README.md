# Optional SQLAlchemy and Neo4j baselines

The main agent schedules these services and measurement windows. Startup helpers only start application servers; data loading and workload execution are separate steps.

## Correctness target

Tracked `DBHarness/session0904/run/data/snb/{sqlalchemy,neo4j}/snb_<arm>.hashes.json` each contains 140/140 hashes identical to hand SQL: all seven canonical query classes and the first20 official parameter rows. `scripts/optional_snb_gate.py` reuses the original read-only REST requests and compares warm/timed outputs against those historical hashes. It does not invoke the mutating add_post/add_friendship checks.

For canonical SNB timing, use the original `bench_timed.run_snb` schedule: one140-request warm pass, then750 requests for each of three IS classes and75 for each of four IC classes, totaling2,550 timed requests. Capture the complete140-key hash set. The optional gate's default140-request timed pass is a correctness pilot, not that full timing schedule.

## Dependencies and images

Runtime dependencies are recorded in `runtime/python314-packages.txt`. SQLAlchemy async execution requires SQLAlchemy and greenlet; Neo4j requires the neo4j driver. Install or update dependencies only outside measurement windows and refresh the inventory afterward.

Docker image `neo4j:5` is present locally (585MB). Record its actual digest before execution. The historical repository pins major version5.

## SQLAlchemy services

The copied SNB and TPC-C ORM applications use PostgreSQL16/TCP55436 and the pinnedPython3.14 environment. Both application files are byte-identical to the originals.

| Service | HTTP port | Database |
|---|---:|---|
| SNB SQLAlchemy |18113|`snb`|
| TPC-C SQLAlchemy |18115|`tpcc`|
| Optional SNB Neo4j HTTP app |18114|dedicated Neo4j instance|

Inspect configuration without starting anything:

```sh
runtime/venv314/bin/python scripts/manage_optional.py plan snb
runtime/venv314/bin/python scripts/manage_optional.py plan tpcc
```

During the allocated window:

```sh
runtime/venv314/bin/python scripts/manage_optional.py start snb
runtime/venv314/bin/python scripts/manage_optional.py stop snb
runtime/venv314/bin/python scripts/manage_optional.py start tpcc
runtime/venv314/bin/python scripts/manage_optional.py stop tpcc
```

`status snb` / `status tpcc` checks tracked ownership. The manager checks port availability, creates dedicated process groups and timestamped logs, and validates PID start ticks, command line, working directory and process group before stopping its process. Records are `logs/optional-sqlalchemy-<bench>.pid.json` and `logs/optional-sqlalchemy-<bench>-launch.json`.

SNB shares the loaded read-only relational dataset. TPC-C shares a mutable database that the PostgreSQL900-plan run has already changed. **Reload TPC-C before its SQLAlchemy run.** With servers stopped, use:

```sh
runtime/venv314/bin/python scripts/load_tpcc_postgres.py --admin-dsn 'postgresql://postgres@127.0.0.1:55436/littleX' --dsn 'postgresql://postgres@127.0.0.1:55436/tpcc'
runtime/venv314/bin/python scripts/manage_optional.py start tpcc
runtime/venv314/bin/python scripts/tpcc_gate.py --arm sqlalchemy --base-url http://127.0.0.1:18115 --dsn 'postgresql://postgres@127.0.0.1:55436/tpcc' --out-dir results/tpcc-sqlalchemy --txns 800
runtime/venv314/bin/python scripts/manage_optional.py stop tpcc
```

The gate preserves original `run_tpcc`, the seed4242 plan,100 warm +800 timed entries, rollback timing and seven truth checks. SQLAlchemy uses the same relational count SQL as PostgreSQL. Authentication uses the existing warehouse token in `benchmark/tpcc/tokens.json`.

SNB correctness pilot:

```sh
runtime/venv314/bin/python scripts/optional_snb_gate.py --arm sqlalchemy --base-url http://127.0.0.1:18113 --out-dir results/snb-sqlalchemy-pilot
```

## Neo4j

```sh
docker compose -f optional-baselines/compose.yml up -d
runtime/venv314/bin/python -u scripts/load_snb_neo4j.py > logs/snb-neo4j-load.log 2>&1
runtime/venv314/bin/python -m uvicorn scripts.snb_neo4j_app:app --host 127.0.0.1 --port 18114 --no-access-log
```

The dedicated container is `jac-db-repro-snb-neo4j`, with its own named volume, HTTP17474/Bolt17687, localhost binding, cpuset4-5 and3GB memory. Check host CPU availability before launch. The historical SNB container was hand-run; the repository does not establish its exact resource settings.

The loader preserves original5,000-row UNWIND batches, constraints, graph types, epoch-ms representation and queries; it wipes only the dedicated endpoint. The app wrapper changes the driver URI. Expected counts:3,157,618 nodes and7,913,932 relationships. Planning allowance:10–30minutes and5–15GB, to be replaced by actual measured load runtime and volume size.

Use `optional_snb_gate.py --arm neo4j --base-url http://127.0.0.1:18114` with a separate output directory for the correctness pilot. Preserve identical warm passes and run all measured arms serially.
