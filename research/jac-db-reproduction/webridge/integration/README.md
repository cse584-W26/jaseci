# Original WeBridge on the aligned Jac IC5 request

`AlignedWeBridge` calls the independently validated `AlignedIc5.request` directly. It uses the upstream extended MySQL driver, `SPInvokeManager` record/replay, the concolic Zero JVM, `StoredProcedureManager` synthesis and the original SP runtime. Source files owned by the alignment experiment remain unchanged.

## Lifecycle

1. `control.py build` compiles the current validated AlignedIc5 source and the separate wrapper into integration/classes. Build commands, hashes and logs are retained.
2. `inspect` records loaded-class origins, source hash and JVM identity without opening a database connection.
3. `record` runs the full aligned request and serializes original SQL/result records, saving the exact process/client memo state immediately before that request.
4. `replay` restores that pre-request state, loads the original result holder, symbolizes person_jid/min_date, invokes the original concolic engine and immediately archives its generated graph. It records SQL commands still reaching the server.
5. `synth --graph PATH` passes that graph and the aligned schema/configuration to the original StoredProcedureManager. Generated SQL and definitions stay under the case's generated/ tree.
6. `optimized` uses the original filter activation order: beginApi, setInvokingSp(true), input parameter buffer, unmodified aligned request, endApi. It records activation/fallback state and server procedure counters. No stored procedure is handwritten.

All integration processes use CPUs9,19. Every actual command, exit status and both output streams live in a separate timestamped attempt directory. Database actions require the coordinator's explicit `--allow-live` window; replay also requires `--graph-window-confirmed` because the original JVM writes `/tmp/webridgeMngr.tmp.sp.string`. The wrapper starts no RMI or MyBlog services.

Example for the coordinator-authorized tiny input0:

```sh
python3 reproduction/webridge/integration/control.py build
python3 reproduction/webridge/integration/control.py record --case reproduction/webridge/integration/cases/tiny-full-cold-20261020 --scope cold --idx 0 --allow-live
python3 reproduction/webridge/integration/control.py replay --case reproduction/webridge/integration/cases/tiny-full-cold-20261020 --scope cold --idx 0 --allow-live --graph-window-confirmed --timeout 120
```

## Preserved runtime boundary

The full request retains original session setup, UUID anchors, ACL checks, hydration, ordered hops, transactions, process schema ensure memo and keepalive-client root memo. Its input context is already authenticated at the CLI boundary, as documented by the alignment audit. Cold capture includes cold ensure/identity work. Warm capture performs the actual original request once before recording; replay restores its captured memo state without adding a different warmup path.

AlignedIc5's START TRANSACTION, session transaction setting and COMMIT use `Statement.execute`. The upstream WeBridge interception is centered on `PreparedStatement.executeQuery/executeUpdate` and Connection transaction methods; those original Statement commands are retained and separately counted as an engine-capture boundary. They are not silently rewritten into a supported API.

The source JDBC call counter is the program's intended query count. Independent server Questions (minus the final observer) counts submitted statements. Com_call_procedure separately establishes actual procedure invocation. Neither a successful baseline fallback nor a reduced network submission count alone establishes database computation elimination.

## Two-step comparison ledger

The first integration stage is the full, count-validated AlignedIc5 request. A subsequent stage may call the independently prepared PrunedIc5 variants only after recording the exact removal ledger and rechecking result and domain-hop parity. It will preserve its own case directory, source hash, trace, generated procedures and measurements. The full stage's evidence remains intact.

### Bounded nonempty concolic capture

The coordinator's next nonempty-input budget uses `--heap 8g --rss-limit-gib 12
--output-limit-gib 8 --timeout 300`. These are separate from earlier tiny probes'
`-Xmx2g`. The RSS guard is a **sampled RSS termination threshold**, not an OS hard
memory limit: it sums the owned process group's resident pages approximately every
100 ms and terminates that process group after observing a threshold crossing.
Brief peaks between samples can exceed the threshold. Once per second the guard
also measures retained case files plus the original engine's global graph file;
exceeding 8 GiB ends the attempt. `process-result.json` records sampled peaks,
limits and stop reason. The complete business request is retained; a resource
boundary ends the experiment instead of truncating its traversal.

New case APIs use a hash of the full case path to avoid procedure-name collisions
between full-runtime and Pruned cases with similar suffixes. Existing case API
names are read unchanged from their retained metadata. The Pruned adapters are
recorded in `pruned-adapter-ledger.json`; the Jac-only removal list remains the
separate alignment `removal-ledger.json`.

`verify_optimized.py` requires output parity, a real procedure CALL, continued
SP activation and absence of fallback errors. An ordinary successful program
exit alone does not establish SP execution: the original driver deliberately
falls back after invocation errors. `tiny_census.py` records thread-filtered SQL
for cold/warm calls and restores the original MySQL logging configuration.
