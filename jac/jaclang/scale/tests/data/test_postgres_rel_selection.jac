"""Wiring tests for the 'postgres-rel' L3 backend selector.

Mirrors test_postgres_selection.jac for the rel variant:
- fail-loud: backend='postgres-rel' + PG down => RuntimeError,
- fail-loud: backend='postgres-rel' + no URI => RuntimeError,
- positive: backend='postgres-rel' + live PG => PostgresRelBackend +
  PersistenceType.POSTGRES_REL,
- regression: backend='postgres' still selects exactly PostgresBackend
  (NOT the subclass -- the KV path must be untouched),
- unknown-backend error message now lists 'postgres-rel'.
"""

import os;
import from jaclang.scale.memory.memory_hierarchy {
    PersistenceType,
    ScaleTieredMemory,
    PostgresBackend,
    PostgresRelBackend
}

glob _REL_DSN = os.environ.get('POSTGRESQL_REL_URI', 'postgresql:///jactest_rel');


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


test "backend='postgres-rel' with PG down fails loud" {
    (mem, err) = _build_with_env(
        {
            'JAC_SCALE_BACKEND': 'postgres-rel',
            'POSTGRESQL_URI': 'postgresql://localhost:1/nope?connect_timeout=1'
        }
    );
    assert mem is None;
    assert isinstance(err, RuntimeError);
    assert 'postgres-rel' in str(err).lower();
}


test "backend='postgres-rel' with NO uri fails loud" {
    (mem, err) = _build_with_env(
        {'JAC_SCALE_BACKEND': 'postgres-rel', 'POSTGRESQL_URI': None}
    );
    assert mem is None;
    assert isinstance(err, RuntimeError);
    assert 'postgresql_uri' in str(err);
}


test "backend='postgres-rel' with live PG selects PostgresRelBackend" {
    (mem, err) = _build_with_env(
        {'JAC_SCALE_BACKEND': 'postgres-rel', 'POSTGRESQL_URI': _REL_DSN}
    );
    assert err is None;
    assert mem is not None;
    assert isinstance(mem.l3, PostgresRelBackend);
    assert mem._persistence_type == PersistenceType.POSTGRES_REL;
    assert 'topology_sql' in mem.capabilities();
    mem.close();
}


test "backend='postgres' still selects exactly PostgresBackend (KV untouched)" {
    (mem, err) = _build_with_env(
        {'JAC_SCALE_BACKEND': 'postgres', 'POSTGRESQL_URI': 'postgresql:///jactest'}
    );
    assert err is None;
    assert mem is not None;
    assert type(mem.l3) is PostgresBackend;
    assert mem._persistence_type == PersistenceType.POSTGRES;
    assert 'topology_sql' not in mem.capabilities();
    mem.close();
}


test "unknown backend error lists postgres-rel" {
    (mem, err) = _build_with_env(
        {'JAC_SCALE_BACKEND': 'postgress', 'MONGODB_URI': None}
    );
    assert mem is None;
    assert isinstance(err, RuntimeError);
    assert 'postgres-rel' in str(err);
}
