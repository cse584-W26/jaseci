"""Capture logged DML; optionally EXPLAIN it inside rollback-only scratch transactions.

The serial experiment runner prepares the disposable database from the matching
seed snapshot. Parsing and --help never connect to PostgreSQL.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


HEADER = re.compile(r"\b(?:LOG|DETAIL|ERROR|WARNING|STATEMENT|CONTEXT):")
EVENT = re.compile(r"duration: ([0-9.]+) ms\s+execute ([^:]*):\s*(.*)")
PARAM = re.compile(r"\$(\d+)\s*=\s*('(?:[^']|'')*'|NULL)", re.I)


def clean_lines(path):
    # Docker timestamps prefix every physical line, including SQL continuations.
    return [re.sub(r"^\d{4}-\d\d-\d\dT\S+\s", "", line)
            for line in path.read_text().splitlines()]


def capture(path, only_dml=True):
    lines = clean_lines(path)
    found = []
    for i, line in enumerate(lines):
        event = EVENT.search(line)
        if not event:
            continue
        sql_lines = [event[3]]
        j = i + 1
        while j < len(lines) and not HEADER.search(lines[j]):
            sql_lines.append(lines[j])
            j += 1
        query = "\n".join(sql_lines).strip()
        if not re.match(r"^(INSERT|UPDATE|DELETE)\b" if only_dml else r"^(INSERT|UPDATE|DELETE|SELECT)\b", query, re.I):
            continue
        parameters = {}
        if j < len(lines) and re.search(r"parameters:", lines[j], re.I):
            raw = re.split(r"parameters:\s*", lines[j], maxsplit=1, flags=re.I)[1]
            pos = 0
            while pos < len(raw):
                match = PARAM.match(raw, pos)
                if not match:
                    raise ValueError(f"Incomplete parameter capture at offset {pos}: {path}")
                literal = match[2]
                parameters[int(match[1])] = (None if literal.upper() == "NULL"
                                            else literal[1:-1].replace("''", "'"))
                pos = match.end()
                if pos == len(raw):
                    break
                sep = re.match(r",\s*", raw[pos:])
                if not sep:
                    raise ValueError(f"Unexpected parameter separator: {path}")
                pos += sep.end()
        placeholders = {int(n) for n in re.findall(r"\$(\d+)", query)}
        if placeholders != set(parameters) or (placeholders and placeholders != set(range(1, max(placeholders) + 1))):
            raise ValueError(f"SQL placeholders differ from captured parameters: {path}")
        found.append(dict(source_log=str(path.resolve()), logged_execute_ms=float(event[1]),
                          statement_name=event[2], query=query,
                          query_sha256=hashlib.sha256(query.encode()).hexdigest(),
                          parameters=parameters))
    if not found:
        raise ValueError(f"No complete DML executions found: {path}")
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--dsn", help="Dedicated disposable repro_w2_explain_* database")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    statements = capture(args.log)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "captured.json").write_text(json.dumps(statements, indent=2) + "\n")
    if not args.execute:
        print(f"Captured {len(statements)} DML statements; no database connection.")
        return
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict
    cfg = conninfo_to_dict(args.dsn or "")
    if not cfg.get("dbname", "").startswith("repro_w2_explain_"):
        parser.error("--execute requires an explicit disposable repro_w2_explain_* database")
    if (cfg.get("host"), cfg.get("port", "5432")) not in {
        ("/tmp/jacpg-d6275e76eb", "5432"), ("127.0.0.1", "55436")
    }:
        parser.error("Use one of the two reproduction-owned PostgreSQL instances")
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    metadata = dict(database=cfg["dbname"], source_log=str(args.log.resolve()),
                    method="Each captured statement separately in a fresh transaction, followed by ROLLBACK. Seed state prepared by runner. EXPLAIN ANALYZE performs real DML and trigger work; rollback preserves logical data but still generates WAL and can change physical pages/statistics. Commit is excluded.",
                    repeats=args.repeats)
    with psycopg.connect(args.dsn, autocommit=True) as conn:
        metadata["settings"] = conn.execute("SELECT name,setting FROM pg_settings WHERE name IN ('server_version','fsync','synchronous_commit','jit','plan_cache_mode','track_io_timing') ORDER BY name").fetchall()
        metadata["triggers"] = conn.execute("SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY c.relname,t.tgname").fetchall()
        for index, statement in enumerate(statements):
            label = f"dml-{index:02d}"
            name = sql.Identifier("repro_dml")
            conn.execute(sql.SQL("PREPARE {} AS ").format(name) + sql.SQL(statement["query"]))
            statement["prepared_parameter_types"] = conn.execute("SELECT parameter_types::text FROM pg_prepared_statements WHERE name='repro_dml'").fetchone()[0]
            values = sql.SQL(", ").join(sql.Literal(statement["parameters"][i])
                                        for i in sorted(statement["parameters"]))
            execute = sql.SQL("EXECUTE {} ({})").format(name, values) if statement["parameters"] else sql.SQL("EXECUTE {}").format(name)
            for repeat in range(args.repeats):
                conn.execute("BEGIN")
                try:
                    conn.execute("SET LOCAL statement_timeout='60s'")
                    conn.execute("SET LOCAL lock_timeout='5s'")
                    plan = conn.execute(sql.SQL("EXPLAIN (ANALYZE, BUFFERS, WAL, SETTINGS, FORMAT JSON) ") + execute).fetchone()[0]
                    (args.out / f"{label}-{repeat}.json").write_text(json.dumps(plan, indent=2) + "\n")
                finally:
                    conn.execute("ROLLBACK")
            conn.execute(sql.SQL("DEALLOCATE {}").format(name))
        (args.out / "captured.json").write_text(json.dumps(statements, indent=2) + "\n")
    (args.out / "metadata.json").write_text(json.dumps(metadata, indent=2, default=str) + "\n")
    print(f"Explained {len(statements)} DML statements, {args.repeats} repeats each; all transactions rolled back.")


if __name__ == "__main__":
    main()
