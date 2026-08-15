"""Per-request stage timing for the serving path (JAC_STAGE_HEADERS=1).

Off by default: every call site guards on the module-level ``ON`` bool, so
when the env var is unset the cost is one global load + a not-taken branch.

State lives in a ContextVar-held dict, one per request. asyncio.to_thread
copies the context into the worker thread, and the dict is the *same object*,
so mutations made on the worker (store SQL timings) are visible to the
awaiting task. No module globals are mutated -> concurrent requests cannot
race.

Stage algebra (all derived from 4 marks + 2 accumulators, so the six stages
sum to the wall span by construction -- see PROGRESS.log PHASE8):

    dispatch = t_span0 - t0          HTTP arrival -> walker span entry
    auth     = t_prep0 - t_span0     token -> user -> root anchor (incl. DB)
    prep     = t_q0    - t_prep0     session/txn setup + compile/plan
    db       = sum(_run)             driver execute+fetch, data queries only
    build    = (end - t_q0) - db - commit
    commit   = ctx._commit_ms        flush + COMMIT

    auth+prep+db+build+commit == end - t_span0 == total_ms + commit_ms
    dispatch is measured OUTSIDE the x-server-total-ms span (it ends where
    that span begins) and is reported as a 6th stage on top.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from time import perf_counter
from typing import Any

ON = os.environ.get("JAC_STAGE_HEADERS") == "1"

_cur: ContextVar = ContextVar("jac_stage_timer", default=None)

# SQL whose cost belongs to the surrounding phase, not to the data-query
# bucket: transaction control never touches user rows.
_TXN = frozenset(("BEG", "COM", "ROL", "SET", "SAV", "REL"))


def start() -> None:
    """Mark HTTP arrival. Called once per request at the top of dispatch."""
    _cur.set(
        {
            "t0": perf_counter(),
            "t_span0": 0.0,
            "t_prep0": 0.0,
            "t_q0": 0.0,
            "db": 0.0,
            "ser": 0.0,
            "phase": "pre",
            "hdrs": None,
        }
    )


def span_begin() -> None:
    """Mark entry of the walker/function span (== the x-server-total-ms t0)."""
    s = _cur.get()
    if s is not None:
        s["t_span0"] = perf_counter()


def prep_begin() -> None:
    """Mark end of auth / start of prep. Opens the data-query bucket."""
    s = _cur.get()
    if s is not None:
        s["t_prep0"] = perf_counter()
        s["phase"] = "run"


def phase(name: str) -> str:
    """Switch the current phase; returns the previous one."""
    s = _cur.get()
    if s is None:
        return "pre"
    prev = s["phase"]
    s["phase"] = name
    return prev


def q_enter(sql: str) -> Any:
    """Open a data-query timing. Returns a handle, or None if not chargeable."""
    s = _cur.get()
    if s is None or s["phase"] != "run" or sql[:3] in _TXN:
        return None
    t = perf_counter()
    if not s["t_q0"]:
        s["t_q0"] = t
    return (s, t)


def q_exit(h: Any) -> None:
    """Close a data-query timing opened by q_enter."""
    if h is not None:
        h[0]["db"] += (perf_counter() - h[1]) * 1000.0


def acc_begin() -> float:
    """Start a scratch timer (used for the serialize sub-timer)."""
    return perf_counter()


def acc_ser(t: float) -> None:
    """Charge elapsed since t to the diagnostic serialize accumulator."""
    s = _cur.get()
    if s is not None:
        s["ser"] += (perf_counter() - t) * 1000.0


def finish(commit_ms: float) -> None:
    """Close the span and compute the stage headers."""
    s = _cur.get()
    if s is None or not s["t_span0"]:
        return
    end = perf_counter()
    if s["t_q0"]:
        prep = (s["t_q0"] - s["t_prep0"]) * 1000.0
        build = (end - s["t_q0"]) * 1000.0 - s["db"] - commit_ms
    else:
        # walker issued no data query at all: everything after auth is prep
        prep = (end - s["t_prep0"]) * 1000.0 - commit_ms
        build = 0.0
    s["hdrs"] = {
        "x-stg-dispatch-ms": round((s["t_span0"] - s["t0"]) * 1000.0, 3),
        "x-stg-auth-ms": round((s["t_prep0"] - s["t_span0"]) * 1000.0, 3),
        "x-stg-prep-ms": round(prep, 3),
        "x-stg-db-ms": round(s["db"], 3),
        "x-stg-build-ms": round(build, 3),
        "x-stg-commit-ms": round(commit_ms, 3),
        # diagnostic: how much of build is Serializer.serialize proper. Proves
        # the build bucket is response construction and not a junk residual.
        "x-stg-ser-ms": round(s["ser"], 3),
    }


def headers() -> Any:
    """The computed header dict for this request, or None."""
    s = _cur.get()
    return s["hdrs"] if s is not None else None


def _selfcheck() -> None:
    """Stage algebra closes on the wall span. Run: python stagetimer.py"""
    start()
    s = _cur.get()
    span_begin()
    prep_begin()
    h = q_enter("SELECT 1")
    assert h is not None
    q_exit(h)
    assert q_enter("BEGIN READ ONLY") is None, "txn control must not be db"
    phase("commit")
    assert q_enter("SELECT 2") is None, "commit-phase SQL must not be db"
    phase("run")
    t_pre_finish = perf_counter()
    finish(3.0)
    hd = s["hdrs"]
    wall = (t_pre_finish - s["t0"]) * 1000.0
    span = sum(
        hd[k]
        for k in (
            "x-stg-auth-ms",
            "x-stg-prep-ms",
            "x-stg-db-ms",
            "x-stg-build-ms",
            "x-stg-commit-ms",
        )
    )
    total = sum(hd[k] for k in hd if k != "x-stg-ser-ms")
    assert abs(total - wall) < 1.0, (total, wall)
    assert abs(span - (total - hd["x-stg-dispatch-ms"])) < 1e-6
    assert hd["x-stg-db-ms"] > 0.0
    print("stagetimer selfcheck OK", hd)


if __name__ == "__main__":
    _selfcheck()
