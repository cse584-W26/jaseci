# HTTP and request dependency audit

The Jac arm uses the repository's own HTTP server and routing stack. Installed
FastAPI/Uvicorn/PyJWT versions are dependencies of the hand-written SQL arm,
not the Jac SNB request stack.

## Jac request path

1. `APIServer.start`, runtimelib/impl/server.impl.jac:2525, constructs
   `ServingServer(app=self.app, host='0.0.0.0', port=self.port)`.
2. runtimelib/serving/server.jac:88 uses stdlib `asyncio.start_server` and its
   own HTTP parsing/connection handling.
3. runtimelib/serving/app.jac, router.jac, coerce.jac, model.jac and datatypes.jac
   implement dispatch, parameter binding, models and response serialization.
4. scale/identity/user_manager.jac imports `jwt_decode`/`jwt_encode` from
   runtimelib/serving/authcrypt.jac. HS256 JWT verification uses stdlib
   hashlib/hmac/base64/json; it does not call PyJWT.
5. `PgStore._connect` resolves the configured `JAC_PG_DRIVER=psycopg` through
   vendor/pgpsycopg.py. This imports psycopg3.3.6 and uses its binary3.3.6 adapter
   and libpq. Connection autocommit and adapter behavior are set in that file.
6. `JAC_PG_POOL=1` uses the repository's own `_conn_pool` dictionary/list with
   `_POOL_MAX=4` in runtimelib/impl/store.impl.jac:410. It does not import
   psycopg_pool.

For these measured HTTP graph requests, the relevant external PyPI runtime
packages are therefore psycopg and psycopg-binary. PostgreSQL, the pinned PBS
CPython build and the repository code are other relevant runtime components.
LLVM shim and source compilation belong to compiler/import setup, with caches
warmed before measured windows.

## SQL baseline and driver processes

`benchmark/snb/postgres/app.py` directly imports FastAPI, Pydantic, PyJWT,
psycopg and psycopg_pool, and the launcher uses `python -m uvicorn app:app`.
Those versions matter for the SQL arm. The benchmark client uses httpx. These
are separate processes from the Jac HTTP service.

## Evidence and comparison scope

`git diff c12ba889d 32c5d1dbb -- jac/jaclang/runtimelib/serving
jac/jaclang/scale/identity jac/jaclang/vendor/pgpsycopg.py
jac/jaclang/runtimelib/impl/server.impl.jac` is empty. These server/auth/driver
sources are unchanged across the two compared Jac revisions.

A read-only `/proc/3892780/maps` audit on2026-10-19 found only psycopg_binary
native extension/wheel-library paths among site-packages mappings, including
`_psycopg.cpython-314-x86_64-linux-gnu.so`, `pq.cpython-314-x86_64-linux-gnu.so`
and wheel libpq/OpenSSL/Kerberos/LDAP dependencies. Maps establish mapped native
libraries; pure Python import attribution above comes from source inspection.
No HTTP calls or database queries were issued for this audit.

Consequently, changing FastAPI/Uvicorn/PyJWT/Pydantic versions should be tracked
as a SQL-baseline environment change, rather than described as a Jac HTTP-stack
change. A psycopg or Python/PostgreSQL version change affects the Jac request
path and must be recorded in both-arm comparisons.


## Headline server timing boundary

The runtime reports x-server-total-ms = whole minus commit minus serializer,
and reports commit/serializer in separate x-server headers. The original
littleX driver adds commit back, making its headline approximately whole minus
serializer. Stage auth+prep+db+build+commit includes serializer inside build;
subtract x-server-ser-ms once to reconcile to the headline. Dispatch remains
outside the walker span. Use per-request values before aggregating. See
littlex/PROFILING_PLAN.md for the exact check and source anchors.
