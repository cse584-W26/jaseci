"""Optional psycopg (v3) backend behind the same tiny connection facade.

The runtime's default Postgres client is the pure-Python wire implementation in
``jaclang.runtimelib.pgwire`` (reached through ``jaclang.vendor.pgload``).  That
keeps jac dependency-free, but row/wire decoding is pure Python and dominates
wide read paths.

Setting ``JAC_PG_DRIVER=psycopg`` swaps in psycopg 3 (with its C/binary
speedups) *without changing anything a caller sees*: same ``connect(...)``
signature, same ``conn.run(sql, **params) -> list[tuple]`` contract, same value
types per column, same ``PgWireError`` exception shape, same
``notifications``/``_sock`` surface used by the LISTEN loop.

Fidelity notes (why this is a drop-in and not "psycopg's defaults"):

* Params are dumped exactly like ``pgwire._encode_param``: every value is
  rendered to text and sent with an *unspecified* type OID, so the server does
  the inference and the ``CAST(:x AS uuid[])`` idiom in the SQL keeps working.
* Result values are kept in the pgwire shapes: text for uuid/json/jsonb/
  timestamp/numeric/bytea/arrays (psycopg would hand back ``UUID``/``dict``/
  ``datetime``/``list``), native ``bool``/``int``/``float`` otherwise.
* Transactions stay in-band: the store issues its own ``BEGIN <isolation>`` /
  ``COMMIT`` / ``ROLLBACK``, so the connection runs with ``autocommit=True``
  and psycopg never injects a transaction of its own.

If psycopg is requested but unimportable this raises -- it never falls back to
the pure-Python driver, because a silent fallback would quietly invalidate any
benchmark comparing the two.
"""

from __future__ import annotations

import json
import os
from collections import deque
from functools import lru_cache
from typing import Any

DRIVER_ENV = "JAC_PG_DRIVER"

# Result OIDs psycopg would decode into rich Python objects but pgwire hands
# back as raw text.  Keeping them as text means downstream code (AnchorRow
# building, json.loads on props, UUID(str(...))) sees byte-identical input.
_TEXT_OIDS = (
    17,  # bytea
    114,  # json
    142,  # xml
    790,  # money
    1082,  # date
    1083,  # time
    1114,  # timestamp
    1184,  # timestamptz
    1186,  # interval
    1266,  # timetz
    1700,  # numeric
    2950,  # uuid
    3802,  # jsonb
    # arrays -- pgwire returns the raw '{...}' literal, psycopg a list
    1000,  # bool[]
    1001,  # bytea[]
    1005,  # int2[]
    1007,  # int4[]
    1009,  # text[]
    1015,  # varchar[]
    1016,  # int8[]
    1021,  # float4[]
    1022,  # float8[]
    1115,  # timestamp[]
    1182,  # date[]
    1185,  # timestamptz[]
    1231,  # numeric[]
    2951,  # uuid[]
    3807,  # jsonb[]
    199,  # json[]
)


_DEFAULT_NAMES = ("", "pgload", "pgwire", "default", "builtin", "python")
_PSYCOPG_NAMES = ("psycopg", "psycopg3")


def driver_name() -> str:
    """Normalized value of the driver selector env var ('' when unset)."""
    return (os.environ.get(DRIVER_ENV) or "").strip().lower()


def resolve_connect() -> Any:
    """Return the ``connect`` callable selected by ``JAC_PG_DRIVER``.

    Unset (or an explicit default alias) keeps the vendored pure-Python wire
    driver.  ``psycopg`` switches to this module.  Anything else raises -- a
    typo must not silently benchmark the wrong driver.
    """
    name = driver_name()
    if name in _PSYCOPG_NAMES:
        _require_psycopg()  # fail loudly here, not on first query
        return connect
    if name in _DEFAULT_NAMES:
        from jaclang.vendor.pgload import connect as pgload_connect  # noqa: PLC0415

        return pgload_connect
    known = ", ".join(x for x in (_DEFAULT_NAMES + _PSYCOPG_NAMES) if x)
    raise RuntimeError(
        f"{DRIVER_ENV}={name!r} is not a known Postgres driver (expected one of: {known}, or unset)."
    )


def _require_psycopg() -> Any:
    try:
        import psycopg  # noqa: PLC0415
    except Exception as e:  # pragma: no cover - depends on the environment
        msg = (
            f"{DRIVER_ENV}=psycopg was requested but psycopg could not be imported ({e!r})."
            + " Install it with `pip install 'psycopg[binary]'` or unset "
            + f"{DRIVER_ENV} to use the built-in pure-Python driver."
            + " Refusing to fall back silently, as that would invalidate benchmarks."
        )
        raise RuntimeError(msg) from e
    return psycopg


# --------------------------------------------------------------------------
# :name -> %(name)s translation
# --------------------------------------------------------------------------

_NAME_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
)


def _dollar_tag(sql: str, i: int) -> str | None:
    """Return the dollar-quote tag starting at ``i`` ('$$', '$tag$') or None."""
    j = i + 1
    n = len(sql)
    if j < n and (sql[j].isalpha() or sql[j] == "_"):
        j += 1
        while j < n and (sql[j].isalnum() or sql[j] == "_"):
            j += 1
    if j < n and sql[j] == "$":
        return sql[i : j + 1]
    return None


def _translate(sql: str, names: tuple[str, ...]) -> tuple[str, bool]:
    """Rewrite ``:name`` placeholders to psycopg's ``%(name)s`` style.

    Only names present in ``names`` are substituted (same rule as
    ``pgwire._named_to_positional``), so stray colons are left alone.  Skips
    single-quoted literals, double-quoted identifiers, dollar-quoted bodies,
    ``--`` line comments and ``/* */`` block comments, and never touches ``::``
    casts.  Literal ``%`` is doubled -- but only when at least one placeholder
    was emitted, since psycopg only parses ``%`` when params are passed.
    """
    known = frozenset(names)
    parts: list[str] = []
    pct: list[int] = []  # indices in `parts` of chunks containing a literal '%'
    used = False
    i = 0
    n = len(sql)

    def push(chunk: str) -> None:
        if "%" in chunk:
            pct.append(len(parts))
        parts.append(chunk)

    while i < n:
        ch = sql[i]

        if ch == "'":  # string literal, '' is an embedded quote
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            push(sql[i:j])
            i = j
            continue

        if ch == '"':  # quoted identifier, "" is an embedded quote
            j = i + 1
            while j < n:
                if sql[j] == '"':
                    if j + 1 < n and sql[j + 1] == '"':
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            push(sql[i:j])
            i = j
            continue

        if ch == "$":
            tag = _dollar_tag(sql, i)
            if tag is not None:
                end = sql.find(tag, i + len(tag))
                j = n if end < 0 else end + len(tag)
                push(sql[i:j])
                i = j
                continue

        if ch == "-" and sql.startswith("--", i):
            end = sql.find("\n", i)
            j = n if end < 0 else end + 1
            push(sql[i:j])
            i = j
            continue

        if ch == "/" and sql.startswith("/*", i):
            depth = 1
            j = i + 2
            while j < n and depth:
                if sql.startswith("/*", j):
                    depth += 1
                    j += 2
                elif sql.startswith("*/", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            push(sql[i:j])
            i = j
            continue

        if ch == ":":
            if i + 1 < n and sql[i + 1] == ":":  # ::cast
                parts.append("::")
                i += 2
                continue
            j = i + 1
            while j < n and sql[j] in _NAME_CHARS:
                j += 1
            name = sql[i + 1 : j]
            if name and name in known:
                parts.append(f"%({name})s")
                used = True
                i = j
                continue

        push(ch)
        i += 1

    if used:
        for idx in pct:
            parts[idx] = parts[idx].replace("%", "%%")
    return ("".join(parts), used)


@lru_cache(maxsize=2048)
def _translate_cached(sql: str, names: tuple[str, ...]) -> tuple[str, bool]:
    return _translate(sql, names)


# --------------------------------------------------------------------------
# param encoding (mirrors pgwire._encode_param, minus the final .encode())
# --------------------------------------------------------------------------


def _array_literal(vals: Any) -> str:
    parts = []
    for v in vals:
        s = str(v)
        parts.append('"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"')
    return "{" + ",".join(parts) + "}"


def _coerce(o: object) -> str:
    return str(o)


def _encode_param(v: Any) -> Any:
    """Render a param the way pgwire does: text, with an unspecified type."""
    if v is None:
        return None
    if v.__class__ is str:
        return v
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (bytes, bytearray, memoryview)):
        return bytes(v)
    if isinstance(v, (list, tuple, set)):
        return _array_literal(v)
    if isinstance(v, dict):
        return json.dumps(v, default=_coerce)
    if isinstance(v, str):
        return str(v)
    return str(v)


# --------------------------------------------------------------------------
# connection
# --------------------------------------------------------------------------


def _install_adapters(conn: Any, psycopg: Any) -> None:
    from psycopg.adapt import Dumper  # noqa: PLC0415
    from psycopg.types.string import StrDumperUnknown, TextLoader  # noqa: PLC0415

    adapters = conn.adapters
    # Every param leaves as text with OID 0 (unspecified) -> the server infers,
    # exactly like the wire driver's Parse with no param types.
    adapters.register_dumper(str, StrDumperUnknown)

    class _RawBytesDumper(Dumper):
        oid = 0  # unspecified, not bytea

        def dump(self, obj: Any) -> Any:
            return bytes(obj)

    adapters.register_dumper(bytes, _RawBytesDumper)

    for oid in _TEXT_OIDS:
        adapters.register_loader(oid, TextLoader)


class PsycopgConnection:
    """pgwire-shaped facade over a psycopg 3 connection."""

    __slots__ = (
        "_psycopg",
        "_conn",
        "_cur",
        "_closed",
        "_notifications",
        "parameters",
    )

    def __init__(self, psycopg: Any, conn: Any) -> None:
        self._psycopg = psycopg
        self._conn = conn
        self._cur = conn.cursor()
        self._closed = False
        self._notifications: deque = deque()
        self.parameters: dict = {}

    # -- pgwire surface ----------------------------------------------------

    @property
    def notifications(self) -> deque:
        """Drain psycopg's notify backlog into pgwire's (pid, chan, payload)."""
        backlog = getattr(self._conn, "_notifies_backlog", None)
        if backlog:
            out = self._notifications
            while backlog:
                n = backlog.popleft()
                out.append((n.pid, n.channel, n.payload))
        return self._notifications

    @property
    def _sock(self) -> Any:
        """A selectable object for the LISTEN loop (libpq socket fd)."""
        return self._conn.pgconn.socket

    def run(self, sql: str, **params: Any) -> list:
        if self._closed:
            raise AssertionError("connection is closed")
        (query, used) = _translate_cached(sql, tuple(sorted(params)))
        args = None
        if used:
            args = {k: _encode_param(v) for (k, v) in params.items()}
        cur = self._cur
        try:
            cur.execute(query, args, binary=False)
            if cur.description is None:
                return []
            return cur.fetchall()
        except self._psycopg.Error as e:
            raise self._as_wire_error(e) from e

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._cur.close()
        except Exception:
            pass
        try:
            self._conn.close()
        except Exception:
            pass

    # -- error translation -------------------------------------------------

    def _as_wire_error(self, e: Exception) -> Exception:
        from jaclang.runtimelib.pgwire import PgWireError  # noqa: PLC0415

        diag = getattr(e, "diag", None)
        code = getattr(diag, "sqlstate", None) or ""
        fields = {"M": str(e).strip() or e.__class__.__name__}
        if diag is not None:
            for (key, attr) in (
                ("S", "severity"),
                ("D", "message_detail"),
                ("H", "message_hint"),
                ("t", "table_name"),
                ("n", "constraint_name"),
            ):
                val = getattr(diag, attr, None)
                if val:
                    fields[key] = val
        if not code:
            # Connection-level failures carry no SQLSTATE; report them with the
            # code the store's _conn_dead()/retry logic already understands.
            if isinstance(e, self._psycopg.OperationalError) or self._conn.closed:
                code = "08006"
                self._closed = True
        if code:
            fields["C"] = code
        if code in ("08006", "08003", "57P01", "57P03"):
            self._closed = True
        return PgWireError(fields)


def connect(
    user: str,
    host: str | None = None,
    port: int = 5432,
    unix_socket_dir: str | None = None,
    database: str = "postgres",
    password: str | None = None,
    timeout: float | None = None,
    startup_params: dict | None = None,
) -> PsycopgConnection:
    """Open a psycopg connection from the same ConnInfo-style fields as pgload."""
    psycopg = _require_psycopg()

    app_name = "jac"
    if startup_params and isinstance(startup_params, dict):
        app_name = str(startup_params.get("application_name", app_name))

    kwargs: dict = {
        "user": user,
        "dbname": database,
        "port": port,
        "application_name": app_name,
        "client_encoding": "UTF8",
        "autocommit": True,  # the store drives BEGIN/COMMIT itself
    }
    # psycopg selects a unix socket by passing the *directory* as host.
    kwargs["host"] = unix_socket_dir or host or None
    if password:
        kwargs["password"] = password
    if timeout:
        kwargs["connect_timeout"] = int(timeout)

    prep = os.environ.get("JAC_PG_PREPARE_THRESHOLD")
    conn = psycopg.connect(**kwargs)
    try:
        if prep is not None:
            conn.prepare_threshold = None if prep.lower() in ("", "none", "off") else int(prep)
        _install_adapters(conn, psycopg)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        raise
    return PsycopgConnection(psycopg, conn)
