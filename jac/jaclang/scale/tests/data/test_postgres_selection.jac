"""P5 wiring tests for the L3 `backend` selector in ScaleTieredMemory.postinit.

Covers PORT_NOTES load-bearing invariants 3 & 4:
- fail-loud: backend='postgres' + PG down => RuntimeError (never sqlite fallback),
- positive: backend='postgres' + live PG => PostgresBackend selected,
- fail-loud: backend='mongodb' + no Mongo => RuntimeError,
- fail-loud: unknown backend value (typo) => RuntimeError (no silent fallback),
- auto untouched: no backend flag + no Mongo => SqliteMemory, no error,
- explicit routing: backend='sqlite' => SqliteMemory.

The `backend` / `postgresql_uri` config keys are read via env (JAC_SCALE_BACKEND /
POSTGRESQL_URI win in get_database_config), so each test just sets env, builds a
ScaleTieredMemory, and inspects the chosen L3. Mongo must be absent for the auto
case: with no MONGODB_URI configured, MongoBackend.is_available() is False.
"""

import os;
import from jaclang.runtimelib.memory { SqliteMemory }
import from jaclang.scale.memory.memory_hierarchy {
    PersistenceType,
    ScaleTieredMemory,
    PostgresBackend
}


"""Build a ScaleTieredMemory with the given env overrides, restoring env after.
Returns (memory | None, raised_exception | None) so fail-loud is testable."""
def _build_with_env(overrides: dict[str, (str | None)]) -> tuple {
    saved: dict[str, (str | None)] = {};
    for (k, v) in overrides.items() {
        saved[k] = os.environ.get(k);
        if v is None {
            os.environ.pop(k, None);
        } else {
            os.environ[k] = v;
        }
    }
    mem = None;
    err = None;
    try {
        mem = ScaleTieredMemory();
    } except Exception as e {
        err = e;
    }
    for (k, old) in saved.items() {
        if old is None {
            os.environ.pop(k, None);
        } else {
            os.environ[k] = old;
        }
    }
    return (mem, err);
}


test "backend='sqlite' routes explicitly to SqliteMemory" {
    (mem, err) = _build_with_env({'JAC_SCALE_BACKEND': 'sqlite', 'MONGODB_URI': None});
    assert err is None;
    assert mem is not None;
    assert isinstance(mem.l3, SqliteMemory);
    assert mem._persistence_type == PersistenceType.SQLITE;
    mem.close();
}


test "backend='postgres' with PG down fails loud (no sqlite fallback)" {
    # Dead port => the pool never fills => PostgresBackend construction raises,
    # which the wiring must convert to a RuntimeError (never silent fallback).
    (mem, err) = _build_with_env(
        {
            'JAC_SCALE_BACKEND': 'postgres',
            'POSTGRESQL_URI': 'postgresql://localhost:1/nope?connect_timeout=1'
        }
    );
    assert mem is None;
    assert isinstance(err, RuntimeError);
    assert 'postgres' in str(err).lower();
}


test "backend='postgres' with NO uri fails loud (no libpq env fallback)" {
    # dsn=None would make ConnectionPool fall back to libpq ambient defaults
    # (PGHOST/PGDATABASE/OS-user db) and could silently attach to the wrong
    # database. The wiring must reject an unset postgresql_uri outright.
    (mem, err) = _build_with_env(
        {'JAC_SCALE_BACKEND': 'postgres', 'POSTGRESQL_URI': None}
    );
    assert mem is None;
    assert isinstance(err, RuntimeError);
    assert 'postgresql_uri' in str(err);
}


test "auto path untouched: no flag, no Mongo => SqliteMemory, no error" {
    (mem, err) = _build_with_env({'JAC_SCALE_BACKEND': None, 'MONGODB_URI': None});
    assert err is None;
    assert mem is not None;
    assert isinstance(mem.l3, SqliteMemory);
    assert mem._persistence_type == PersistenceType.SQLITE;
    mem.close();
}


test "backend='postgres' with live PG selects PostgresBackend" {
    # Positive path: without this test a broken pg branch (bad kwarg/import)
    # would keep the suite green while making Postgres permanently unselectable.
    (mem, err) = _build_with_env(
        {'JAC_SCALE_BACKEND': 'postgres', 'POSTGRESQL_URI': 'postgresql:///jactest'}
    );
    assert err is None;
    assert mem is not None;
    assert isinstance(mem.l3, PostgresBackend);
    assert mem._persistence_type == PersistenceType.POSTGRES;
    mem.close();
}


test "backend='mongodb' with no Mongo fails loud (no fallback)" {
    (mem, err) = _build_with_env({'JAC_SCALE_BACKEND': 'mongodb', 'MONGODB_URI': None});
    assert mem is None;
    assert isinstance(err, RuntimeError);
    assert 'mongodb' in str(err).lower();
}


test "unknown backend value fails loud (no silent fallback)" {
    # A typo like 'postgress' must raise, not silently select sqlite.
    (mem, err) = _build_with_env(
        {'JAC_SCALE_BACKEND': 'postgress', 'MONGODB_URI': None}
    );
    assert mem is None;
    assert isinstance(err, RuntimeError);
    assert 'postgress' in str(err).lower();
}
