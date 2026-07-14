# Projection Pushdown (Mongo + PG-rel) + UUID-Intern Rider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch only declared archetype fields on the read path (both engines), skip per-anchor hydration fixed costs, compose with the existing ordered+sliced hop path into a `feed_page` workload; re-port flagless uuid interning.

**Architecture:** `QueryPlan.projection` rides the existing `needs() <= capabilities()` negotiation. Two routes: set-path (plain feed, `_try_pushdown` -> `execute_plan`) and list-path (`feed_page`, projected materialization of pre-ordered ids, pg-rel only). Safety = env declaration + read-only gate + dirty-scan marker skip + never-enter-L1/L2. Spec: `docs/superpowers/specs/2026-07-13-projection-pushdown-design.md` (read it first; all rationale lives there).

**Tech Stack:** Jac (NOT Python -- decl/impl split, `impl X.y {}` syntax), psycopg3, pymongo. Worktree `/home/aaron/Dev/Research/DatabaseResearch/JaseciFork-pgrel`, branch `feat/pg-rel-mvp`.

**Standing rules:**

- Run tests via `jac test <file>` from repo root of the worktree (global `jac`, worktree cwd).
- Pre-commit hooks auto-format; on hook mutation re-add + re-commit. No em-dashes in docs.
- Env kill-switch convention: unset env = feature off = byte-identical behavior.
- HARD GATE before Task 12 (servers/bench): pause and notify user.
- Existing test suites that must stay green after every task: `jac test jac/jaclang/scale/tests/data/test_postgres_rel_backend.jac` (23), `test_memory_hierarchy.jac`, resolver-core tests.

---

### Task 1: `QueryPlan.projection` field + `needs()`

**Files:**

- Modify: `jac/jaclang/runtimelib/query_plan.jac:15-27`
- Modify: `jac/jaclang/runtimelib/impl/query_plan.impl.jac:11-27`
- Test: `jac/jaclang/runtimelib/tests/` -- add to the existing query-plan test file (locate via `grep -rl "needs" jac/jaclang/runtimelib/tests/ jac/jaclang/scale/tests/`; if none exists, create `jac/jaclang/scale/tests/data/test_query_plan_projection.jac` following the header pattern of `test_postgres_rel_backend.jac`)

- [ ] **Step 1: Write failing tests**

```jac
test query_plan_projection_default_none {
    p = QueryPlan(id_in={UUID(int=1)});
    assert p.projection is None;
    assert 'projection' not in p.needs();
}

test query_plan_projection_adds_need {
    p = QueryPlan(id_in={UUID(int=1)}, node_type_final="Tweet",
                  projection={"content", "created_at"});
    assert p.needs() == {'id_in', 'type_pushdown', 'projection'};
}
```

- [ ] **Step 2: Run, verify FAIL** (unexpected keyword `projection`)
- [ ] **Step 3: Implement** -- in `query_plan.jac` add to the `has` block:

```jac
        projection: (set[str] | None) = None;
```

In `query_plan.impl.jac` `needs()` body, after the `slc` clause:

```jac
    if self.projection is not None {
        needs.add('projection');
    }
```

Leave `is_trivial` untouched (projection never makes a plan trivial-eligible; it only ever appears with `id_in`).

- [ ] **Step 4: Run tests, PASS; run resolver-core + mongo suites (no regression -- Mongo lacks `'projection'` cap until Task 6, so a projected plan would floor; nothing sets projection yet)**
- [ ] **Step 5: Commit** `feat(query-plan): projection field + needs()`

---

### Task 2: `JAC_PROJECTION` parser in `runtimelib/utils.jac`

**Files:**

- Modify: `jac/jaclang/runtimelib/utils.jac` (module already imported by both resolver impl and `scale/memory/memory_hierarchy.jac:25`)
- Test: same test file as Task 1

- [ ] **Step 1: Failing tests**

```jac
test projection_cfg_unset_empty {
    os.environ.pop("JAC_PROJECTION", None);
    assert projection_cfg() == {};
}

test projection_cfg_parses_types {
    os.environ["JAC_PROJECTION"] = "Tweet:content,created_at;Profile:username";
    cfg = projection_cfg();
    assert cfg == {"Tweet": {"content", "created_at"}, "Profile": {"username"}};
    os.environ.pop("JAC_PROJECTION", None);
}

test projection_cfg_ignores_malformed {
    os.environ["JAC_PROJECTION"] = "Tweet;:x;Bad:";
    assert projection_cfg() == {};
    os.environ.pop("JAC_PROJECTION", None);
}
```

- [ ] **Step 2: Run, FAIL (name not defined)**
- [ ] **Step 3: Implement** in `utils.jac` (near `to_uuid`, body inline -- trivial enough to skip the impl annex, matching `to_uuid` precedent):

```jac
def projection_cfg() -> dict[str, set[str]] {
    raw = os.environ.get("JAC_PROJECTION", "");
    out: dict[str, set[str]] = {};
    for part in raw.split(";") {
        if ":" not in part { continue; }
        (tname, _, flist) = part.partition(":");
        fields = {f.strip() for f in flist.split(",") if f.strip()};
        if tname.strip() and fields { out[tname.strip()] = fields; }
    }
    return out;
}
```

Check `utils.jac` already imports `os`; add if missing.

- [ ] **Step 4: PASS**
- [ ] **Step 5: Commit** `feat(runtime): JAC_PROJECTION declaration parser`

---

### Task 3: `Serializer.deserialize_projected` slim constructor

**Files:**

- Read first: `jac/jaclang/runtimelib/impl/serializer.impl.jac:556-637` (`_deserialize_anchor`) and `:662-705` (`_deserialize_archetype`) -- note the exact class-resolution helper (`_get_class` per scout; confirm name/signature) and how `archetype.__jac__` is linked.
- Modify: `jac/jaclang/runtimelib/serializer.jac` (decl) + `jac/jaclang/runtimelib/impl/serializer.impl.jac`
- Test: `jac/jaclang/scale/tests/data/test_projection_slim.jac` (new; register alongside other data tests if a runner manifest exists -- check how `test_postgres_rel_backend.jac` is discovered)

- [ ] **Step 1: Failing tests** (use a locally-defined `node SlimT { has a: str = ""; has b: int = 0; has c: list[str] = []; }` archetype as the other backend tests do). NOTE the loudness contract: only FACTORY-default fields (`c`) raise on unprojected access; scalar-default fields (`b`) silently answer the dataclass class default -- assert BOTH behaviors so the hazard is pinned by test:

```jac
test slim_anchor_sets_projected_only {
    aid = UUID(int=7);
    anchor = Serializer.deserialize_projected(
        aid, <module-of-SlimT>, "SlimT", {"a": "x"}, {"a"});
    assert isinstance(anchor, NodeAnchor);
    assert anchor.id == aid;
    assert anchor.edges == [];
    assert anchor.archetype.a == "x";
    assert anchor.archetype.__jac__ is anchor;
    assert anchor._projected_fields == {"a"};
    assert anchor.version == 0;
    assert anchor.archetype.b == 0;  # scalar default = SILENT read (documented hazard)
    ok = False;
    try { _ = anchor.archetype.c; } except AttributeError { ok = True; }
    assert ok;  # factory-default field = LOUD (spec Decision 2, corrected)
}
```

(`<module-of-SlimT>` = the test module's own `__name__`; mirror how existing serializer tests reference locally-declared archetypes.)

- [ ] **Step 2: FAIL (no attribute deserialize_projected)**
- [ ] **Step 3: Implement.** Decl in `serializer.jac`:

```jac
    static def deserialize_projected(anchor_id: UUID, arch_module: str,
        arch_type: str, fields: dict, projected: set[str]) -> (NodeAnchor | None);
```

Impl (adapt helper names to what Step "Read first" found -- the SHAPE is fixed, the two marked calls reuse existing internals):

```jac
impl Serializer.deserialize_projected(anchor_id: UUID, arch_module: str,
        arch_type: str, fields: dict, projected: set[str]) -> (NodeAnchor | None) {
    cls = Serializer._get_class(arch_module, arch_type);   # reuse: same resolver as _deserialize_archetype
    if cls is None { return None; }
    arch = object.__new__(cls);
    for f in projected {
        if f in fields {
            # _deserialize_value: $ref / typed-value envelopes must decode, raw dicts are corruption
            setattr(arch, f, Serializer._deserialize_value(fields[f]));
        }
        # ponytail: absent-in-storage factory field stays unset -> AttributeError; scalar falls to class default
    }
    anchor = object.__new__(NodeAnchor);
    anchor.id = anchor_id;
    anchor.root = None;
    anchor.persistent = True;
    anchor.edges = [];
    anchor.hash = 0;
    anchor.version = 0;              # read by note_traversal_reads on any refs() from this node
    anchor.access = Permission();    # read by _check_access paths
    anchor.archetype = arch;
    arch.__jac__ = anchor;                                  # reuse: same link _deserialize_archetype makes
    anchor._projected_fields = set(projected);
    return anchor;
}
```

Field-sufficiency was VERIFIED in review: `version` + `access` are the only two extras read on the `_try_pushdown`/refs() path (`note_traversal_reads` -> `context.impl.jac:99` reads `.version`; `_check_access` reads `.access`); `_initial_edge_ids`/`topology_index_data` are unreachable given the marker skips, `__repr__` guards `f.name in self.__dict__`, `is_populated()` is satisfied by `edges`+`archetype`. Confirm the empty-`Permission` ctor name matches the one used at `serializer.impl.jac:565`'s parse-failure path. Skipping access-map parse / edge stubs / `_compute_hash` / `snapshot_field_hashes` is the entire point (spec Decision 2).

- [ ] **Step 4: PASS**
- [ ] **Step 5: Commit** `feat(serializer): deserialize_projected slim anchor constructor`

---

### Task 4: Dirty-scan marker guard in `_collect_into`

**Files:**

- Modify: `jac/jaclang/runtimelib/impl/memory.impl.jac:1792-1793`
- Test: extend the existing `_collect_into`/changeset test file (locate: `grep -rl "_collect_into\|record_update" jac/jaclang/*/tests/`)

- [ ] **Step 1: Failing test** -- build a `TieredMemory` the way existing collect tests do, insert a populated persistent anchor into `mem.__mem__`, then BASELINE it so the dirty scan can actually see a change (a fresh `hash=0` anchor with no edges is skipped at `memory.impl.jac:1808-1814`, and an unbaselined one dies at the `_compute_hash` try/continue): `a.hash = Serializer._compute_hash(a); snapshot_field_hashes(a);` THEN stamp `a._projected_fields = {"a"}`, mutate a field, run `mem._collect_into(mem.changes)` with read-only OFF, assert NO intent recorded. Sanity: the same fixture WITHOUT the stamp must record an update (proves the test can fail).
- [ ] **Step 2: FAIL (update intent present)**
- [ ] **Step 3: Implement** -- in the anchor loop, extend the existing skip:

```jac
        if not anchor.persistent or not anchor.is_populated() {
            continue;
        }
        if getattr(anchor, '_projected_fields', None) is not None {
            continue;  # projected anchors are read-only artifacts; never diffed or written back
        }
```

- [ ] **Step 4: PASS + full memory suite green**
- [ ] **Step 5: Commit** `feat(memory): dirty-scan skips projected anchors`

---

### Task 5: L1/L2 skip in `TieredMemory.execute_plan`

**Files:**

- Modify: `jac/jaclang/runtimelib/impl/memory.impl.jac:1977-1998`
- Test: same file as Task 4

- [ ] **Step 1: Failing test** -- stub l3 whose `execute_plan` yields one marked anchor (build via `Serializer.deserialize_projected`) and one unmarked; run `list(mem.execute_plan(plan))`; assert unmarked IS in `mem.__mem__` / l2 batch, marked is NOT in either, both were yielded.
- [ ] **Step 2: FAIL**
- [ ] **Step 3: Implement** -- inside the loop:

```jac
        for anchor in self.l3.execute_plan(plan) {
            if getattr(anchor, '_projected_fields', None) is not None {
                yield anchor;   # never cached: L1/L2 must only hold full anchors
                continue;
            }
            existing = self.__mem__.get(anchor.id);
            ...unchanged...
        }
```

- [ ] **Step 4: PASS + memory suite green**
- [ ] **Step 5: Commit** `feat(memory): projected anchors bypass L1/L2 on pushdown path`

---

### Task 6: Mongo projection

**Files:**

- Modify: `jac/jaclang/scale/memory/impl/memory_hierarchy.mongo.impl.jac` (`capabilities` :486-488, `execute_plan` :525-546)
- Modify: `jac/jaclang/scale/memory/memory_hierarchy.jac` (MongoBackend decl: add `projection_count: int = 0`)
- Test: extend `jac/jaclang/scale/tests/data/test_memory_hierarchy.jac` (mongo section)

- [ ] **Step 1: Failing tests** (mongomock/live-mongo pattern -- copy whatever fixture the existing mongo execute_plan tests use):

```jac
test mongo_capabilities_include_projection {
    ...build backend...
    assert 'projection' in be.capabilities();
}

test mongo_execute_plan_projected {
    ...seed one Tweet-like anchor via put/apply as existing tests do...
    plan = QueryPlan(id_in={aid}, node_type_final="MhTweet",
                     projection={"content"});
    res = list(be.execute_plan(plan));
    assert len(res) == 1;
    assert res[0]._projected_fields == {"content"};
    assert res[0].archetype.content == "hello";
    assert res[0].edges == [];
    assert be.projection_count == 1;
}

test mongo_execute_plan_unprojected_unchanged {
    plan = QueryPlan(id_in={aid}, node_type_final="MhTweet");
    res = list(be.execute_plan(plan));
    assert getattr(res[0], '_projected_fields', None) is None;  # full _load_anchor path
}
```

- [ ] **Step 2: FAIL**
- [ ] **Step 3: Implement.** `capabilities`:

```jac
    return {'type_pushdown', 'field_pushdown', 'id_in', 'slice', 'projection'};
```

`execute_plan` -- replace the `find`/load section:

```jac
    proj_doc = None;
    if plan.projection is not None {
        proj_doc = {'type': 1, 'arch_type': 1, 'arch_module': 1};  # _id always returned by mongo
        for f in plan.projection { proj_doc[f'data.archetype.{f}'] = 1; }
    }
    cursor = self.collection.find(filt, proj_doc);
    if skip_n { cursor = cursor.skip(skip_n); }
    if limit_n is not None { cursor = cursor.limit(limit_n); }
    for doc in cursor {
        if plan.projection is not None {
            anchor = Serializer.deserialize_projected(
                to_uuid(doc['_id']), doc.get('arch_module', ''),
                doc.get('arch_type', ''),
                doc.get('data', {}).get('archetype', {}),
                plan.projection);
            if anchor { self.projection_count += 1; yield anchor; }
        } elif (anchor := self._load_anchor(doc)) {
            yield anchor;
        }
    }
```

(`find(filt, None)` == `find(filt)` in pymongo, so the unprojected path is byte-identical. `data.archetype.__type__/__module__` are NOT needed -- class resolution uses top-level `arch_module`/`arch_type`, same keys `_plan_to_mongo_filter` filters on; verify against `_anchor_to_doc:71-93` that both are always written, and add them to `proj_doc` keys if `_load_anchor`-style fallback needs more.)

- [ ] **Step 4: PASS + whole mongo suite green**
- [ ] **Step 5: Commit** `feat(mongo): native projection in execute_plan`

---

### Task 7: PG-rel `execute_plan` + gated capabilities

**Files:**

- Modify: `jac/jaclang/scale/memory/memory_hierarchy.jac` (PostgresRelBackend decl: add `rel_projection_count: int = 0`, declare `execute_plan`)
- Modify: `jac/jaclang/scale/memory/impl/memory_hierarchy.postgres_rel.impl.jac` (`capabilities` :83-89 + new `execute_plan`)
- Test: `jac/jaclang/scale/tests/data/test_postgres_rel_backend.jac`

- [ ] **Step 1: Failing tests** (use the existing `_fresh`/jactest_rel fixtures + RelPerson archetypes):

```jac
test rel_capabilities_gated_on_projection_env {
    be = _mk_backend();
    assert be.capabilities() == {'topology_sql'};
    os.environ["JAC_PROJECTION"] = "RelPerson:name";
    assert be.capabilities() == {'topology_sql', 'id_in', 'type_pushdown', 'projection'};
    os.environ.pop("JAC_PROJECTION", None);
}

test rel_execute_plan_projected {
    ...seed RelPerson(name="ann", age=3) via put, id=aid...
    plan = QueryPlan(id_in={aid}, node_type_final="RelPerson", projection={"name"});
    res = list(be.execute_plan(plan));
    assert len(res) == 1 and res[0].archetype.name == "ann";
    assert res[0]._projected_fields == {"name"};
    assert be.rel_projection_count == 1;
    ok = False;
    try { _ = res[0].archetype.age; } except AttributeError { ok = True; }
    assert ok;
}

test rel_execute_plan_jsonb_types_roundtrip {
    ...seed archetype with a list field, project it, assert isinstance(res list)...
}

test rel_execute_plan_undeclared_type_full_hydrates {
    # caps-leak guard: projection None (undeclared type) must NOT return empty
    plan = QueryPlan(id_in={aid}, node_type_final="RelPerson");
    res = list(be.execute_plan(plan));
    assert len(res) == 1;
    assert getattr(res[0], '_projected_fields', None) is None;  # full anchor
    assert res[0].archetype.age == 3;                            # all fields present
}
```

- [ ] **Step 2: FAIL**
- [ ] **Step 3: Implement.** `capabilities` (keep the existing `JAC_TOPOLOGY_SQL` clause exactly as-is, extend the return):

```jac
    caps = {'topology_sql'} if <existing kill-switch check passes> else set();
    if projection_cfg() { caps |= {'id_in', 'type_pushdown', 'projection'}; }
    return caps;
```

NOTE: keep the two concerns independent -- `JAC_TOPOLOGY_SQL=0` must NOT disable projection caps, and vice versa (they gate different mechanisms). Restructure the existing early-return accordingly.

`execute_plan` (placeholder-order trap applies -- SELECT-list `%s` bind FIRST):

```jac
impl PostgresRelBackend.execute_plan(plan: QueryPlan) -> Generator[Anchor, None, None] {
    if plan.id_in is None { return; }
    if plan.projection is None {
        # Caps-leak guard (review CRITICAL): with JAC_PROJECTION set, plans for
        # UNDECLARED types (e.g. the Profile hop) also pass the subset test and
        # route here. Full-hydrate them -- an empty generator = empty feed.
        for anchor in self.batch_get(list(plan.id_in)).values() {
            if (plan.node_type_final is None
                    or anchor.archetype.__class__.__name__ == plan.node_type_final) {
                yield anchor;
            }
        }
        return;
    }
    fields = sorted(plan.projection);
    cols = ", ".join(["data->'archetype'->%s"] * len(fields));
    sql = f"SELECT id, arch_module, arch_type, {cols} FROM anchors WHERE id = ANY(%s)";
    params: list = list(fields);
    params.append([str(u) for u in plan.id_in]);
    if plan.node_type_final is not None {
        sql += " AND arch_type = %s";
        params.append(plan.node_type_final);
    }
    <acquire conn the same way resolve_hop_sql does, same try/except-return-None-style fallback but here: log + return (empty generator) on error>
    for row in rows {
        fvals = {fields[i]: row[3 + i] for i in range(len(fields)) if row[3 + i] is not None};
        anchor = Serializer.deserialize_projected(
            to_uuid(row[0]), row[1] or '', row[2] or '', fvals, plan.projection);
        if anchor { self.rel_projection_count += 1; yield anchor; }
    }
}
```

(`data->'archetype'->%s` with text param yields jsonb; psycopg3 decodes to Python objects, so `->` not `->>` -- lists/dicts survive. NULL jsonb -> field omitted -> unset-field semantics preserved. Check `PostgresBackend.batch_get` return shape before writing the fallback loop -- adapt `.values()` if it returns a list, and mirror however `_materialize_ids` consumes it at `query_utils.impl.jac:93-101`.)

- [ ] **Step 4: PASS + full rel suite (23 + new) green; ALSO assert unflagged runs untouched: with env unset, `capabilities()` unchanged means resolver can never route here (Decision 5)**
- [ ] **Step 5: Commit** `feat(pg-rel): execute_plan with projection, env-gated capabilities`

---

### Task 8: Resolver Route A (set path)

**Files:**

- Modify: `jac/jaclang/runtimelib/impl/resolver.impl.jac` (tail :445-453 + one helper)
- Test: extend the resolver seam tests (same file/fixture style as the pg-rel seam tests: `ExecutionContext` + `ctx.mem.l3 = be`)

- [ ] **Step 1: Failing seam test** -- against pg-rel backend (env `JAC_PROJECTION="RelPerson:name"`, `JAC_READ_ONLY=1`): run `[r ->:RelKnows:->]`-style single-hop resolution where the result is a set with root_anchor present; assert returned anchors carry `_projected_fields` and `be.rel_projection_count > 0`. Counter-tests: same run with `JAC_READ_ONLY` unset -> full anchors; with `JAC_PROJECTION` unset -> full anchors; against a stub backend WITHOUT `'projection'` cap but with the other caps -> plan must NOT carry projection (and must still push down as today); a hop whose final filter carries field predicates (post_filter path) -> full anchors AND correct filter results.
- [ ] **Step 2: FAIL**
- [ ] **Step 3: Implement.** Helper near the top of resolver.impl.jac:

```jac
def _projection_for(mem: Memory, node_type: (str | None),
        has_post_filter: bool) -> (set[str] | None) {
    if node_type is None or has_post_filter { return None; }
    # post_filter would run predicates against a slim archetype -> scalar
    # class defaults answer -> silently wrong filter results (review HIGH)
    cfg = projection_cfg();
    if node_type not in cfg { return None; }
    if not _read_only_enabled() { return None; }
    if 'projection' not in mem.capabilities() { return None; }
    return cfg[node_type];
}
```

`_read_only_enabled` import VERIFIED working: `import from jaclang.runtimelib.memory { _read_only_enabled }` (impl-file top-level defs land in the decl module). Do NOT add another copy -- `serializer.impl.jac:1-14` already carries a private duplicate; two is the ceiling.

At the tail, after `plan = QueryPlan(...)` and before the `needs()` subset test (`post_filter` is already in scope -- it was hoisted at :391-395):

```jac
        proj = _projection_for(mem, last_hop.node_type, post_filter is not None);
        if proj is not None { plan.projection = proj; }
```

The caps pre-check inside `_projection_for` guarantees attaching can never flip a passing subset test to failing (spec Route A).

- [ ] **Step 4: PASS + resolver-core suite + mongo suite green**
- [ ] **Step 5: Commit** `feat(resolver): attach projection on final-hop pushdown (Route A)`

---

### Task 9: Resolver Route B (ordered list path)

**Files:**

- Modify: `jac/jaclang/runtimelib/impl/resolver.impl.jac` only (list branch :440-441 + new private helper)
- Test: same seam file as Task 8

- [ ] **Step 1: Failing seam test** -- pg-rel, env `JAC_PROJECTION="RelPerson:name"`, `JAC_READ_ONLY=1`, `JAC_ORDER_PUSHDOWN="RelPerson:name:asc"`; sliced hop (`slc` present so hop returns ordered list); assert result anchors are marked, ORDER of returned anchors matches the hop's id order, and `rel_projection_count` incremented. Counter-test: Mongo backend same flags -> unmarked full anchors (Route B requires `'topology_sql'`).
- [ ] **Step 2: FAIL**
- [ ] **Step 3: Implement.** In `resolver.impl.jac` (NOT query_utils -- `resolver.impl.jac:3-9` already imports FROM query_utils, and the helper needs resolver-private `_try_pushdown`; placing it in query_utils is a guaranteed circular import):

```jac
def _materialize_ids_projected(mem: Memory, ids: list, node_type: (str | None),
        projection: set[str]) -> (list | None) {
    plan = QueryPlan(id_in=set(ids), node_type_final=node_type, projection=projection);
    if not (plan.needs() <= mem.capabilities()) { return None; }
    fetched = _try_pushdown(mem, plan);
    by_id = {a.id: a for a in fetched};
    return [by_id[i] for i in ids if i in by_id];
}
```

At resolver tail `:440-441` (ordered path never has a post filter -- `use_ordered` requires `not last_has_post_filter` at :391-396 -- so pass `False`):

```jac
    if isinstance(result, list) {
        proj = _projection_for(mem, last_hop.node_type, False);
        if proj is not None and 'topology_sql' in mem.capabilities() {
            projected = _materialize_ids_projected(mem, result, last_hop.node_type, proj);
            if projected is not None { return projected; }
        }
        return _materialize_ids(mem, result);
    }
```

- [ ] **Step 4: PASS + all suites green**
- [ ] **Step 5: Commit** `feat(resolver): projected materialization on ordered path (Route B)`

---

### Task 10: UUID-intern rider (flagless)

**Files:**

- Modify: `jac/jaclang/runtimelib/serializer.jac` (decl file -- body INLINE, decorator is dropped if split into impl annex; known trap)
- Modify: `jac/jaclang/runtimelib/impl/serializer.impl.jac` (6 bare `UUID(` sites -- verified count 2026-07-13)
- Test: `jac/jaclang/scale/tests/data/test_uuid_intern.jac` (new; port the shape of orphan-branch `test_uuid_intern.jac` from `git show de012d6a3` in the MAIN JaseciFork checkout -- git show only, NEVER switch its branch)

- [ ] **Step 1: Failing test**

```jac
test intern_uuid_identity_and_value {
    a = _intern_uuid("00000000-0000-0000-0000-000000000001");
    b = _intern_uuid("00000000-0000-0000-0000-000000000001");
    assert a == UUID(int=1);
    assert a is b;   # cached
}
```

- [ ] **Step 2: FAIL**
- [ ] **Step 3: Implement.** In `serializer.jac` (top-level, next to imports; add `import from functools { lru_cache }`):

```jac
@lru_cache(maxsize=65536)
def _intern_uuid(id_str: str) -> UUID {
    return UUID(id_str);
}
```

Then in `serializer.impl.jac` replace each of the 6 `UUID(...)` construction-from-string sites (`_deserialize_jac_ref`, `coerce`, `_get_class` stub id, `_deserialize_anchor` id / root / edge-frozenset) with `_intern_uuid(...)`. Do NOT touch `to_uuid` or Mongo/Redis sites (spec scope = old-impl parity).

- [ ] **Step 4: PASS + serializer/memory/mongo/rel suites green**
- [ ] **Step 5: Commit** `perf(serializer): intern deserialized UUIDs (lru 65536, flagless)`

---

### Task 11: `feed_page` workload

**Files (MINE -- app copy is editable):**

- Modify: `/home/aaron/Dev/Research/DatabaseResearch/DBHarness/littleXs/jaseci-rel/app.jac`

**Files (USER IMPLEMENTS -- paste-ready blocks below, hand over and WAIT):**

- `DBHarness/harness/run.py` (:74-101 area)
- `DBHarness/littleXs/postgres/app.py` (:228-262 area)
- `DBHarness/littleXs/sqlalchemy/app.py` (~:270)
- `DBHarness/littleXs/neo4j/app.py` (~:194-217)
- `DBHarness/harness/oracle.py` (feed_page parity case)

- [ ] **Step 1 (mine): add walker to `jaseci-rel/app.jac`** after `load_feed`:

```jac
# feed_page: top-20 newest. Correct ONLY with JAC_ORDER_PUSHDOWN=Tweet:created_at:desc
# (runtime flag supplies the ordering the language cannot yet express).
# Per-stream top-20 union contains the global top-20, so merge is exact.
walker load_feed_page {
    has feed: list[TweetView] = [],
        viewer_username: str = "",
        seen: set = set(),
        t0: float = 0.0;

    can run with Root entry {
        self.t0 = time.perf_counter();
        mine = [-->[?:Profile]];
        if mine {
            me = mine[0];
            self.viewer_username = me.username;
            visit [me-->[?:Tweet]][:20];
            visit [me->:Follow:->[?:Profile]-->[?:Tweet]][:20];
        }
    }

    can gather with Tweet entry {
        if jid(here) not in self.seen {
            self.seen.add(jid(here));
            self.feed.append(here.to_view(self.viewer_username));
        }
    }

    can deliver with Root exit {
        self.feed.sort(key=lambda t: TweetView : t.created_at, reverse=True);
        self.feed = self.feed[:20];
        server_total_ms = (time.perf_counter() - self.t0) * 1000;
        report {"server_total_ms": server_total_ms, "feed": self.feed};
    }
}
```

- [ ] **Step 2 (mine): smoke-test the trailing `[:20]` -> slc pushdown** -- the mechanism is VERIFIED in code (`pyast_gen_pass.impl.jac:3049-3078` compiles a trailing range slice on an edge-ref target into a `slc=slice(...)` kwarg -> `runtime.impl.jac:1094` -> `resolve_path_anchors(..., slc)`); assert it end-to-end via counter check (`rel_chain_count` increments, ordered result length 20) in a library-mode seam test.
- [ ] **Step 3 (user): hand over paste-ready baseline blocks** -- postgres (`FEED_PAGE_SQL` = existing `FEED_SQL` + `LIMIT 20`, new `GET /feed_page` endpoint cloned from `get_feed`), sqlalchemy (clone `get_feed` + `.limit(20)`), neo4j (clone feed Cypher + `LIMIT 20`), `run.py` (`fetch_feed_page` dispatching walker `load_feed_page` / `GET /feed_page`, register in `WORKLOADS`), oracle feed_page case (top-20 exact compare). Provide exact code in the handoff message, built from the current file contents at that moment. WAIT for user to confirm they are in.
- [ ] **Step 4: Commit (worktree app copy only)** `feat(app): load_feed_page walker`

---

### Task 12: Parity + bench -- HARD GATE

- [ ] **Step 1: STOP. Notify user before ANY server boot.** Proposed protocol (A/B/A same-session, ratios only, standard config `BATCH_L3=1 READ_ONLY=1 GTI=0 CHAIN=0`):
  1. `feed` pg-rel baseline (no projection) -- A
  2. `feed` + Route A projection, pg-rel AND mongo (the "generalizes" datapoint)
  3. `feed_page` jac (projection + order + slc) vs baselines' `feed_page`
  4. uuid-intern A/B (same boot, env-free -- needs a revert-commit toggle or branch-stash toggle; decide with user)
  5. re-run A baseline (drift check)
- [ ] **Step 2: Oracle parity: `feed` projection-on == oracle bytes; `feed_page` top-20 == baseline top-20 (call `oracle.py` directly -- `50-oracle.sh` mongo guard inapplicable).**
- [ ] **Step 3: Update memory `pg-rel-mvp-build` + ledger with results.**
