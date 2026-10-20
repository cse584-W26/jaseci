# IC5: compiler and runtime mechanism

The final compiler preserves the IC5 walker source while converting per-post
traversal/counting into a batched, member-driven SQL aggregation, retaining
application-side construction of qualifying `(forum, friend)` pairs and
hydrating only the winning forums.

This analysis compares baseline `c12ba889d484d7fcdfb3780ac98d416d1e13ec8b`
with final `32c5d1dbb9507571235783e78e35b1022cacc4e4`. It is based on source,
commit history and the original experiment artifacts. Current reproduction
measurements belong in the main reproduction report.

## 1. Query and original execution

The implemented benchmark starts from a person, takes `_neighbors(p)` (the
union of outgoing and incoming Knows), selects forums those friends joined
after `min_date`, counts posts in each forum authored by its qualifying
friends, and returns20 forums ordered by count descending and forumId ascending.
This implementation's friend frontier is one hop; its query definition is
[the original compiler plan](../DBHarness/session0904/ic5/COMPILER_PLAN.md).

The unchanged walker builds two dictionaries:

- `forums[forum_jid] = forum`;
- `joined[forum_jid] = set(qualifying_friend_jids)`.

It then loops over every candidate forum, traverses ContainerOf to its posts,
traverses HasCreator for each post, tests the first creator against
`joined[forum_jid]`, increments a counter, and finally sorts/slices.

Source: [app.jac, ic5_new_forums](benchmark/snb/jaseci-pg/app.jac:368).

The baseline has a loop-prefetch facility, but its matcher does not cover the
IC5 combination of an EdgeRefTrailer collection and a tuple target over
`dict.items()`. The per-post HasCreator resolution consequently remains in
the execution path. See baseline
[_adj_prefetch_hops](runtime/baseline-source/jac/jaclang/jac0core/passes/impl/pyast_gen_pass.impl.jac:2861)
and the original plan's diagnosis. This is a failure to batch across this
program structure, rather than a limitation on compiling an individual graph
hop to SQL.

## 2. Final execution, stage by stage

### Batch the first frontier

C1 evaluates `_neighbors(p)` once, materializes its result as `__jac_fr`, and
prefetches the HasMember hop for that whole frontier. The predicate
`joinDate > self.min_date` travels with the hint and with its memo key.
The walker then consumes each friend's results from the request-local memo.

Recorded generated-code shape:

```python
__jac_fr = list(_neighbors(p))
jadj_prefetch(__jac_fr, 1, HasMember, Forum,
              epreds=(('joinDate', '>', self.min_date),), ids_only=True)
for f in __jac_fr:
    # refs(..., ids=True) yields this friend's forum IDs from the memo
    # original dictionary/set construction follows
    ...
```

`__jac_fr` is hoisted so an arbitrary collection-producing call is executed
once, rather than repeated or a generator consumed twice. The prefetch is
synchronous: it completes before the consuming loop. This mechanism batches
requests; it does not overlap asynchronous I/O with CPU computation.

References:
[codegen collection handling](../jac-db/jac/jaclang/jac0core/passes/impl/pyast_gen_pass.impl.jac:3330),
[prefetch runtime](../jac-db/jac/jaclang/runtimelib/impl/query_planner.impl.jac:1428),
[historical exact D5 codegen diff](../DBHarness/session0904/ic5/build/D5_IMPL.md).

D3's fast fill uses literal edge/node types and the edge rows' denormalized
endpoint-type information when there are no relevant subtypes. It preserves
direction, supported undirected-edge behavior, per-origin edge ordering, and
NULL endpoint-type handling. Unsupported shapes use the generic compiled hop;
residual predicates prevent memo publication.

Reference:
[_fast_adj_sql and _fill_adj_level](../jac-db/jac/jaclang/runtimelib/impl/query_planner.impl.jac:1519).

### Aggregate instead of traversing every post in Python

EffectPass recognizes a specific nested-count form: a two-name tuple target
from `dict.items()`, counter initialized to zero, an outbound hop from the
value, one further outbound hop assigned to a local, and an else-less condition
of the form `creators and jid(creators[0]) in joined[key]` followed only by
`counter += 1`.

It checks that inner values do not escape, the counter is not observed during
the inner loop, and the dictionaries are not referenced in forbidden ways.
A successful stamp lets codegen replace the inner count nest with
`jhopcount(...)`; the later Top-K stamp emits `jhopcount_topk(...)`.

References:
[_hopcount_plan](../jac-db/jac/jaclang/compiler/passes/main/effect_pass.jac:1097),
[_stamp_hopcount](../jac-db/jac/jaclang/compiler/passes/main/effect_pass.jac:2037),
[count lowering](../jac-db/jac/jaclang/jac0core/passes/impl/pyast_gen_pass.impl.jac:2584).

### Drive aggregation from distinct members

The runtime deduplicates each membership collection and flattens the Python
pair map into UUID arrays. Its SQL contains these logical relations:

```text
pr(k,m)  = qualifying (forum, friend) pairs supplied by the walker
keys(k)  = every candidate forum, including those with zero matches
fp       = posts authored by the distinct qualifying friends
fc       = (forum, author) pairs obtained by joining those posts to ContainerOf
cnt      = count matching fc rows per pr forum
result   = keys LEFT JOIN cnt, using zero when there is no count
```

`fp` and `fc` are explicitly `AS MATERIALIZED`. The HasCreator scan is typed
with `src_type = Post`, excluding Comment-originating HasCreator edges before
further joins. This chooses work from qualifying authors' posts before matching
forums, instead of expanding every post in every candidate forum. The final
path uses heterogeneous edges in `anchors`; the homogeneous `adj_<edge>` table
cannot represent Forum→Post→Person.

References:
[get_hop_counts](../jac-db/jac/jaclang/jac0core/impl/runtime.impl.jac:1015),
[get_hop_counts_topk SQL](../jac-db/jac/jaclang/jac0core/impl/runtime.impl.jac:1272),
[original D1 plan study](../DBHarness/session0904/ic5/build/D1_IMPL.md).

### Select and hydrate the winners

Top-K combines the count with forum-field ordering in SQL. Numeric JSON values
use a guarded numeric sort key; textual values use C collation. If the mirror
cannot supply the ordering field, the runtime returns a larger candidate set
and the retained application-side sort/slice finishes the result.

D4 proves that the first nest only stages forum IDs until this Top-K tail.
Its references therefore use `ids=True`. The recorded generated tail is:

```python
__jac_top = jhopcount_topk(joined, forums, ContainerOf, Post,
                         HasCreator, Person, Forum, 'forum_id', 20)
jobj_many([forums[foj] for foj, cnt in __jac_top],
          _proj=(Forum, ('forum_id', 'title')))
for foj, cnt in __jac_top:
    fo = jobj(forums[foj], Forum)
    rows.append({'forumId': fo.forum_id, 'title': fo.title, 'postCount': cnt})
# Original sort and [:20] remain.
```

D5 also marks the prefetch level `ids_only=True`, so the fill skips its eager
`mem.batch_get(out)` of all Forum blobs. Object consumers still perform their
own necessary existence checks and hydration. This avoids eager materialization
but can increase the number of later existence-check statements.

References:
[recorded D4 generated code](../DBHarness/session0904/ic5/build/D4_IMPL.md:42),
[D5 source commit rationale](../DBHarness/session0904/ic5/build/D5_IMPL.md),
[fill hydration switch](../jac-db/jac/jaclang/runtimelib/impl/query_planner.impl.jac:1722),
[typed projected batch load](../jac-db/jac/jaclang/jac0core/impl/runtime.impl.jac:520).

## 3. How the historical statement count reached432

The following totals are recalculated from the original raw
[gate JSON files](../DBHarness/session0904/ic5/build/gates). Latency medians use
`statistics.median` (average of the middle two for20 rows); the original report
sometimes selected an upper-middle value. Every listed gate records20/20 parity.

| Historical gate | Main addition | SQL total /20 inputs | Median SQL/input | Jac median ms | PostgreSQL median ms |
|---|---|---:|---:|---:|---:|
| base | c12 baseline |278769|11256.5|7542.00|80.35|
| A | chained loop prefetch |656|30|191.35|84.30|
| AB | nested count aggregation |657|30|120.65|64.95|
| ABC1 | predicate-aware inbound prefetch |230|12|103.45|60.65|
| ABC | dict-alias field projection |229|12|104.15|60.05|
| ABCD1 | member-driven aggregation |229|12|126.90|82.60|
| FULL | SQL Top-K + typed fill |269|14|69.25|51.10|
| D4 | IDs first; hydrate winning forums |269|14|78.95|63.90|
| FINAL | review fixes |269|14|109.10|75.85|
| D5 | skip eager target hydration |432|22.5|75.50|60.05|

The large count reduction comes first from A's batch fills, then C1's batching
of the previously per-friend predicate hop. B changes the computation performed
per request even though its statement count is similar to A. D1/D2/D3 change
SQL plan shape, ordering and materialization. D5's count rises by163 statements
relative to the preceding269: skipped eager target loading means later
per-friend consumers perform existence checks again. The original report calls
this approximately9 additional statements per row; the total difference over20
inputs is8.15 per input. This explains why432 is not simply a monotonic
statement-count minimum.

These figures describe the historical dataset, fixture, flags and logging
window. Source analysis establishes which operations change; current profiling
establishes their current latency and CPU/DB costs.

References:
[historical report and final D5 explanation](../DBHarness/session0904/ic5/build/REPORT.md),
[commit32c5d1dbb fill change](../jac-db/jac/jaclang/runtimelib/impl/query_planner.impl.jac:1722).

## 4. Permissions and semantic boundaries

### Request-local prefetch and ordinary object reads

The adjacency memo is owned by the execution context. It is enabled for proven
read-only requests and refused when dirty/deleted/transaction-changed state
exists. Keys include direction, edge type, node type and predicate values.
A missing origin yields a complete memo miss rather than a partial answer.
Fast fill records a marker so edge-only consumers can require the generic
node-join path. The prefetch wrapper catches failures and leaves ordinary
traversal available.

References:
[_adj_memo and key](../jac-db/jac/jaclang/runtimelib/impl/query_planner.impl.jac:1301),
[_memo_pairs](../jac-db/jac/jaclang/runtimelib/impl/query_planner.impl.jac:1377),
[prefetch wrapper](../jac-db/jac/jaclang/jac0core/impl/runtime.impl.jac:600).

`resolve_query_ids` performs target existence/materialization and the normal
node read-access check before returning IDs. The winner load uses ordinary
`jobj`/`jobj_many`; field projection uses mirror ACL scalars where sufficient
and full legacy loading for rows requiring a fuller verdict. The actual
IDs-only resolver must be read together with D5: skipping the fill's eager load
moves necessary loading to consumers rather than removing the access decision.

References:
[IDs resolver](../jac-db/jac/jaclang/runtimelib/impl/query_planner.impl.jac:1784),
[projected hydration](../jac-db/jac/jaclang/runtimelib/impl/query_planner.impl.jac:765),
[ACL-filtered ID helper](../jac-db/jac/jaclang/runtimelib/impl/query_planner.impl.jac:200).

### Aggregation's supported semantics

The count builtins operate over database edge rows with exact type matching.
They follow the runtime's closure-style ACL-superset contract: intermediate
counts can include posts the requester cannot read individually, while reported
forum objects still take the normal hydration/access path. This is an explicit
scope of the implementation, not a proof of private-intermediate count
noninterference.

`count(*)` counts matching `(ContainerOf, HasCreator)` edge pairs. The source
walker tests only the first HasCreator neighbor. Equivalence therefore relies
on the SNB invariant of at most one creator edge per post. The inspected syntax
matcher does not itself establish a general schema cardinality constraint.
Replacing this with DISTINCT would count any matching creator, which likewise
requires reconsidering the original first-neighbor semantics for multi-creator
inputs.

Membership collections are deduplicated before forming pair arrays. Empty
membership sets retain zero-count forums. Unsupported code shapes keep their
original traversal; unavailable ordering mirrors broaden the returned set for
the retained sort/slice. Pending writes are flushed through read barriers
before database aggregation.

References:
[explicit cardinality/ACL/type contract](../jac-db/jac/jaclang/jac0core/impl/runtime.impl.jac:1065),
[Top-K dedupe and fallback](../jac-db/jac/jaclang/jac0core/impl/runtime.impl.jac:1171),
[pattern checks](../jac-db/jac/jaclang/compiler/passes/main/effect_pass.jac:1097).

## 5. Plan versus implemented boundary

The original COMPILER_PLAN proposed typed heterogeneous adjacency projections
and a generic `jfold(start, plan)` relational program. The delivered code
instead specializes `jhopcount` / `jhopcount_topk` for the accepted counting
family and uses typed `anchors` scans for heterogeneous edges. Qualifying pair
construction remains a Python dictionary/set loop; the pairs return to SQL as
UUID arrays. The historical report labels fusion of this first nest into the
count query as the next whole-walker fusion rung.

The implemented scope is therefore cross-loop batching, a recognized
count-and-membership aggregation, Top-K and selective materialization within
this ability. It does not yet supply a general dependency IR spanning walker
ability transitions.

References:
[original B.1/B.2/C goals](../DBHarness/session0904/ic5/COMPILER_PLAN.md:61),
[delivered rungs and next fusion step](../DBHarness/session0904/ic5/build/REPORT.md:75).

## 6. Current reproduction: measured one-statement variation

The final census records432 statements,20/20 parity and zero structural SQL.
All20 timed request windows were recovered offline from the retained server
log using app backend PIDs3892824 (main data) and3892805 (identity), with the
main backend's COMMIT terminating each window. Identity work preceding BEGIN
remains in the corresponding window. All20 recovered counts match gate.py
exactly; the complete40 warm+timed SQL windows and classifications are saved in
[final-census/sql-windows](results/final-census/sql-windows/classification.json).

Timed index3 contains28 statements:27 other statements and one exact
`SELECT count(*) FROM (VALUES ...) v(n) WHERE to_regclass(v.n) IS NULL` schema
existence guard. Timed index13 contains23 statements and neither a guard nor
an identity lookup. Thus the current index3 extra statement is directly
identified as the guard. The historical index13 count was24; its per-request
SQL text is required to identify its historical extra statement.

A separate retained-log probe repeats index3 twice immediately, waits5.5s
outside measurement, then repeats index3 and index13. Its measured breakdown is:

| Input/call | Total statements | Schema guard | Identity lookup | Other statements |
|---|---:|---:|---:|---:|
| index3, first |29|1|1|27|
| index3, immediate repeat |27|0|0|27|
| index3, after5.5s |29|1|1|27|
| index13, first |23|0|0|23|
| index13, immediate repeat |23|0|0|23|

The identity statement is exactly
`SELECT doc FROM identity_users WHERE user_id = $1` on PID3892805. Removing
only schema guards leaves variation; removing both observed periodic statements
makes the index3 count27 on all three calls. This establishes the source of
variation in these probe calls. The original guard-only false attribution flag
is preserved alongside the joint classification in
[the probe summary](results/ic5-ttl-probe/summary.json).

The guard's five-second process-global TTL is defined in
[store.impl.jac:_memo_check](../jac-db/jac/jaclang/runtimelib/impl/store.impl.jac:1025).
The identity SQL is issued by
[PgIdentityStorage.get_user_by_id](../jac-db/jac/jaclang/scale/identity/impl/identity_storage.pg.impl.jac:109).
These maintenance/authentication statements depend on execution timing and
cache state, so aggregate census equality can coexist with a different
allocation of one statement to individual parameter indices.
