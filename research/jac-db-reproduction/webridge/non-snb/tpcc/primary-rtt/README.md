# TPC-C primary SQL roundtrip measurements

`run.py` runs each immutable compiler case as a direct/WeBridge pair from independently reset synthetic initial state. It reuses the frozen `TpccTiming` classpath, API definitions and session configuration. Ten mutating warmups precede thirty measured requests. The shared compact protocol parser emits command/response completion summaries, with no per-packet or per-row output. Each pair holds the host measurement lease through reset, execution, output/state verification, proxy teardown and exact instrumentation restoration.

`extract.py` is a TPC-schema adaptation of the shared littleX extractor. It uniquely matches the owned JDBC connection, verifies each complete response and sequential command boundary, selects commands strictly between each pair of SHOW SESSION STATUS probes, and checks actual command/CALL counts against Questions/Com_call_procedure. The primary scalar sums outer complete-response durations per request; CALL is counted once. Application method timing remains secondary. Connection initialization and observer status probes are excluded.

`reference900.py` executes the exact original ordered plan using the retained frozen `TpccMixed` harness. Direct references pass an empty API map; WeBridge references use the existing genuine accepted cases and original route dispatch. The route's fixture-credit/name-median calculation remains precomputed outside request timing. Raw per-request activation/fallback state and complete eight-relation snapshots are retained. `verify_references.py` adds an explicit input-layout field from the exact executed command's immutable plan to a separate oracle copy, retaining raw logs and both hashes, then runs the independent model. State/result rejection yields no accepted primary median even when all900 requests finish.

`publish.py --allow-incomplete` atomically publishes only completed keys for progress; its default requires all126 representative terminal cells. Stage failures have no timing/count numbers. `rtt-cycle-evidence.json` provides per-delay observations for42 workload/arm pairs. The final reference index has six primary entries. Earlier application timing matrices and the typed-getInt diagnostic remain separate artifacts.

Commands (output directories must be new):

```sh
python primary-rtt/run.py --pilot --out NEW_PILOT
python primary-rtt/run.py --out NEW_MATRIX
python primary-rtt/reference900.py --out NEW_REFERENCES
python primary-rtt/verify_references.py NEW_REFERENCES
python primary-rtt/publish.py --matrix NEW_MATRIX --references NEW_REFERENCES
```
