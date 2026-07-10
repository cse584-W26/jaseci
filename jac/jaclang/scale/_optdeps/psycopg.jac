"""Guarded re-exports for psycopg 3 (install group: [data]).

Mirrors _optdeps/pymongo.jac: import succeeds with HAS_PSYCOPG=True when the
`psycopg[binary,pool]` extra is installed; otherwise the symbols are None so
importers can degrade / fail loud without an ImportError at module load."""

with entry {
    try {
        import from psycopg { Connection }
        import from psycopg.errors { OperationalError }
        import from psycopg.pq { TransactionStatus }
        import from psycopg.types.json { Jsonb }
        import from psycopg_pool { ConnectionPool }
        import from psycopg_pool { PoolTimeout }
        HAS_PSYCOPG = True;
    } except ImportError {
        Connection = None;
        Jsonb = None;
        ConnectionPool = None;
        TransactionStatus = None;
        OperationalError = Exception;
        class _PsycopgUnavailableError(Exception) {}
        PoolTimeout = _PsycopgUnavailableError;
        HAS_PSYCOPG = False;
    }
}
