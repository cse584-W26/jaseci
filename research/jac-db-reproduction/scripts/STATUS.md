# Reproduction status — 2026-10-19

All workload collection and diagnostic runs are complete. Owned benchmark HTTP services are stopped. Databases, immutable fixture snapshots and raw artifacts are retained for reruns. Both PostgreSQL clusters have statement/duration logging off, no database logging overrides, and fsync/synchronous_commit on: [final-state.json](../logs/final-state.json).

## Validated results

- IC5 baseline/final: exact SQL totals278,769→432, zero structural SQL, matching outputs; logging-off Jac medians 6,506.320→110.206 ms (59.04×), with 40/60 requests.
- Four canonical SNB arms: Jac Final defaults and locked PostgreSQL/SQLAlchemy/Neo4j. Every arm has 140 warm +2,550 timed requests, zero errors and 140 matching historical result hashes.
- Three TPC-C arms: Jac Final defaults and locked PostgreSQL/SQLAlchemy. Each matches the900-entry plan, all seven truth checks, seven expected rollbacks and historical golden counts.
- Historical littleX CONTROL original recipe:40/40 cells,24,000 timed requests,24 cohorts, one SQL PID/12 Jac PIDs, original phase/order, shared W2 state, affinity snapshots and all sample/count/parity oracles. The separate final32 fresh-state40-cell group also passes.
- W1 scaling and Jac's W3 paged-feed advantage repeat. Current W2t20 write ordering differs from the historical reference; the report documents both the current measured costs and the original reference's variability.

Independent offline evidence: [core validation](../results/core-artifact-validation.json), [littleX original validation](../results/littlex-original-independent-validation.json), and [additional fresh-state validation](../littlex/summary/validation.json).

## Completed diagnostic explanations

- On a restored disposable final t20 fixture, **ANALYZE anchors only** reduces continuous server median 23.527→15.312 ms, matching15.296 ms on the historical fixture. The immutable snapshots and formal results stay unchanged.
- The early10-warm page profile falls inside the2-second projection retry cooldown;110 warm passes reach the global-top-K SQL branch and reproduce3.630/3.780 ms continuous page medians.
- Logged INSERT+COMMIT: PG161.240 ms/native1.211 ms with 5 warm +40 timed transactions, compared with the recorded historical 6.399/6.340 ms scratch totals. Method boundaries and configuration are retained.
- Separate create_tweet profiles measure additional Jac application/backend CPU and protocol work. Historical AB_TABLE records t20 SQL writes34–36% slower than its prior bank; night0823 reports proposed write-flag gains failing interleaved A/B. The historical ranking's original cause is not identified by current measurements.

[Diagnostic synthesis](../littlex/DIAGNOSTIC_REPORT.md), [page receipt](../littlex/PAGE_BRANCH_RECEIPT.md), [commit method](../runtime/COMMIT_FLOOR_METHOD.md).

## Coverage and provenance

Historical ad469 CONTROL defaults lazy transactions off; final32/c12 defaults on. PostgreSQL edge-only-dirty is already default-on in ad469. littleX tier means tweets per user, with 100 users/50 follows per user fixed.

SNB/TPC-C baseline dependencies exactly match their shared benchmark lock; the historical shared-benchmark interpreter remains unrecorded and the current aligned environment uses PBS 3.14.6. littleX SQL/driver use their separate original locks onPython3.13.16. Jac has its own asyncio HTTP/auth/pool stack. Current governor readback is powersave; the historical summary reports performance.

Historical SNB/TPC-C CONTROL/BEST rows and littleX BEST/SQLAlchemy/Neo4j results are archived reference coverage. Local core Jac measurements are labeled Final defaults; primary local littleX is historical CONTROL.

Launch/configuration and available affinity evidence are retained. Host time series cover the later diagnostic windows where sampled; the report does not generalize those observations to every earlier run.

## Offline verification and report refresh

```sh
runtime/venv314/bin/python scripts/verify_core_artifacts.py
runtime/venv314/bin/python scripts/verify_littlex_original.py
runtime/venv314/bin/python scripts/update_report_tables.py
```

These commands read local artifacts and update validation/report files without database requests. [Main report](../REPORT.md), [rerun order](../README.md#independent-rerun-order).

## Completed W2 follow-up

Three uninstrumented rounds validate 18 cells and 9,000 timed requests. The current write gap is stable; measured extra SQL, lookups, follow traversal and configuration parsing characterize its execution costs. The archived historical t20 arms were collected roughly 44 minutes apart, and their original per-request profiles do not identify a unique historical cause.

[Detailed investigation](../write-investigation/REPORT.md), [independent audit](../write-investigation/HISTORICAL_AUDIT.md), [function spans](../littlex/WRITE_FUNCTION_SPANS.md), [figure PDF](../write-investigation/write-costs.pdf). All follow-up workloads are finished; HTTP ports 18120/18121 are closed, scratch databases removed and the fixture restored: [follow-up final state](../write-investigation/final-state.json).
