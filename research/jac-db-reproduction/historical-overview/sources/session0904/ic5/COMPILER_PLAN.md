# ic5: what it is, why jac is 60x behind, and a compiler plan to make it competitive

## The query (LDBC SNB Interactive Complex 5, "new groups")
Given a person and a date: take the person's friends (Knows, 1 hop), the forums those friends
JOINED AFTER the date (HasMember edge with `joinDate > minDate`), and for each such forum count the
posts in it whose creator is one of the friends that joined after the date. Return the top 20
forums by that count (ties by forumId). Fan-out at SF1: F ≈ 5-16 friends, Φ ≈ 300-2500 forums,
P ≈ 3k-45k posts in those forums; the answer is 20 rows.

## The two plans
Postgres (`benchmark/snb/postgres/app.py:363`), one statement, ~60-230 ms:
```
joined(forum_id, person_id) = friends ⋈ forum_member[join_date > md]       -- (forum, friend) pairs
count posts po WHERE po.forum_id = j.forum_id AND po.creator_id = j.person_id  -- index (forum_id, creator_id)
GROUP BY forum ORDER BY count DESC, forum_id LIMIT 20
```
It never touches a post that is not by a qualifying friend: work is O(matched posts), a few hundred.

Jac walker (`benchmark/snb/jaseci-pg/app.jac` `ic5_new_forums`, text unchanged since 08-10):
```
for f in _neighbors(p)                              # friends
    for fo in [f<-:HasMember:joinDate > d:<-[?:Forum]]   # forums, edge predicate  -> joined[forum] = {friends}
for (foj, fo) in forums.items()
    for post in [fo->:ContainerOf:->[?:Post]]       # EVERY post of the forum
        creators = [post->:HasCreator:->[?:Person]] # one edge-reference resolve PER POST
        if jid(creators[0]) in joined[foj]: cnt += 1
sort, [:20]
```
Measured tonight (`DIAG.md`): 278,849 statements over the 20 rows, 0.45-0.5 ms each; row 19 =
45,429 statements = 33 s; 94% of wall time is the request thread waiting on the DB round trip.

## Why it is 60-75x slower — three stacked causes
1. **One round trip per post.** `[post->:HasCreator:->]` inside the loop is resolved per post
   (`_sql_pairs`, the `unnest(...) LEFT JOIN anchors ... JOIN anchors` statement, 40,899 of them on
   row 19). Nothing landed so far catches this shape: T3's loop prefetch requires a pure-reference
   collection and a Name target (ic5 iterates an EdgeRefTrailer and `dict.items()` with a tuple
   target); closures/`jadj_pairs` need a homogeneous edge (adjacency projections are
   `src_type == dst_type`; ContainerOf is Forum→Post, HasCreator is Post→Person). Cost: ~0.5 ms × P.
2. **The wrong plan shape.** Even with round trips gone, the walker visits every post of every
   forum (O(P), 3k-45k) to keep the few hundred whose creator is a qualifying friend. pg drives
   from the (forum, friend) pairs through the `(forum_id, creator_id)` index and never sees the
   rest. This is a query-plan difference, not an I/O difference: per-post Python + Post hydration
   remains after cause 1 is fixed (the 0903 design's "honest ceiling", 0.3-0.6 s).
3. **No relational projection for heterogeneous edges or edge properties.** The store only grows
   `adj_<E>(src, dst)` for same-type edges. HasMember carries the `joinDate` predicate on the EDGE,
   so the friends→forums hop today loads edge objects to evaluate it; ContainerOf/HasCreator have
   no projection at all.

## Compiler plan (walker text unchanged; three rungs, each gated by SNB hash parity across arms)

### Rung A — round trips: chained adjacency prefetch for nested edge-reference loops (≈1-2 days)
Extend the T3 matcher (`pyast_gen_pass.impl.jac` `_adj_prefetch_hops` / `_pure_ref_root`) to accept
(a) an EdgeRefTrailer as the loop collection and (b) a tuple target over `dict.items()`; the
runtime fill (`prefetch_adjacency` / `_adj_memo`, now default-on for RO requests) follows a
two-level chain: one adjacency statement per loop LEVEL, memoised per request, so the inner
`[post->:HasCreator:->]` is answered from the memo. Statements: P + 2Φ + 2F → ~2F + 6. Needs
heterogeneous adjacency rows (see Rung B.1) or an anchors-side batched fallback.
Expected: row median 6.5 s → ~0.3-0.6 s (4-8x). Still ~5x behind pg because of cause 2. Design
already written: `session0901/opt_ladder/improve/snb_ic5/DESIGN.md`.

### Rung B — the plan: relational lowering of pure counting loops (≈1-2 weeks; the thesis endpoint)
B.1 **Typed adjacency projections with edge properties.** Generalise `ensure_adjacency_table` to
    `adj_<E>_<Src>_<Dst>(src, dst, <props the compiler names>)`, trigger-maintained like `adj_<E>`
    today (R7). The compiler already names fields per site for T6 (`_proj=(T, fields)`); the same
    stamp on an edge predicate (`joinDate > d`) tells the store which edge props to project.
    Gives HasMember(src, dst, joinDate), ContainerOf(src, dst), HasCreator(src, dst).
B.2 **Loop-fusion / aggregation proof (new pass, sibling of EffectPass/StreamProofPass).** Recognise
    the shape: nested `for x in [a->:E:->[?:T (, pred)?]]` loops whose bodies are PURE — only
    (i) dict/set accumulators keyed by `jid(x)`, (ii) counters incremented under a membership test
    on such a set, (iii) appends of field reads of the loop element, (iv) a final sort + slice
    (already inferred by sufficiency #24). Decline on any other statement, any write, any escape of
    a node object, any aliasing. Emit ONE builtin call per fused nest, e.g.
    `jfold(start, plan)` where `plan` is the compiler's relational plan: hops with edge predicates,
    the pairing (forum, friend) that the outer nest builds, the COUNT with the join condition the
    membership test expresses, GROUP BY key = the dict key, ORDER BY/LIMIT from the sort+slice.
    The runtime compiles that plan into one SQL over the B.1 projections — for ic5 literally the
    postgres CTE — and hydrates only the LIMIT rows through the normal (ACL-checked, T6-projected)
    load. Statements: 2-3 per request. Expected: pg-class latency plus the ~2-4 ms jac dispatch
    floor, i.e. **~70-150 ms vs pg 60-230 ms — competitive**.
B.3 **Soundness gates.** (1) Byte-identical answers vs pg/sqla/neo4j on all 20 ic5 rows (the
    existing compare-hashes oracle); (2) the pass must print its plan under `JAC_FUSION_DEBUG` and
    a shape harness like `check_t7_shapes.sh` must show it DECLINING every impure variant
    (side effect in the body, node escaping the loop, non-jid dict key, early `break`); (3) the
    ACL argument: the fused SQL runs over projections the way `get_closure` does — a superset by
    ACL — so the final hydration of the reported rows still carries the verdict (T7b precedent);
    membership counts over unreadable posts are the same information `jclosure` already leaked
    and must be documented as such.

### Rung C — generalisation (after B lands on ic5)
The same pass covers ic2's "top-20 messages of friends by date" (today hand-restated as `jtopk`,
counted as manual tuning), ic1's name filter, and the littleX feed's "top-K by date across a
frontier" (today `JAC_FUSED_FEED`'s runtime special case). Each removal of a hand-written
builtin call is a burden-LoC deletion the thesis can claim.

## What I would do first
Rung B directly, with Rung A as the fallback if B.2's matcher cannot be made sound in time: A
gives 4-8x for a day's work but leaves ic5 an honest negative; B is the only path to
"competitive", and its two halves (typed projections, fusion pass) are the same mechanisms the
thesis already argues for (compiler-grown projections + compiler-chosen plan), not new claims.
Sequence: B.1 (2 days, store + tests) → B.2 for exactly the ic5 shape (3-4 days) → parity → then
generalise (C). Budget one SNB-only rerun (~30 min idle) per rung for canonical numbers.
