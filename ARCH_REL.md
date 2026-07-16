# Architecture: GTI-as-blob (today) vs GTI-as-table (this branch)

Learning companion for `feat/pg-rel-mvp`. Everything here is scout-verified against this
worktree (`5fbce338e`); file:line refs are clickable in your editor.

## 1. The system today: how a walker hop actually resolves

When a walker does `visit [-->:Follow:]`, this is the full path:

```mermaid
flowchart TD
    W["walker: visit [-->:Follow:]"] --> R["JacGraph.refs\njac0core/impl/runtime.impl.jac:1070"]
    R --> RPA["resolve_path_anchors\nruntimelib/impl/resolver.impl.jac:338"]
    RPA --> GUI["_get_usable_index (:243)\nroot_anchor.get_topology_index()"]
    GUI -->|"isinstance(TopologyIndex)\nAND len > 0"| RH["resolve_hop (:271)\nper hop in the chain"]
    GUI -->|"empty / missing blob"| WALK

    RH --> PRE{"every current node uid:\nnode_to_lid has it AND\nnode_table[lid][2] == SELF_ROOT?\n(:284-288)"}
    PRE -->|yes, sliced| RCO["idx.resolve_chain_ordered\ninsertion-order walk + slice"]
    PRE -->|yes, unsliced| RC["idx.resolve_chain\nbucket lookups → set of UUIDs"]
    PRE -->|"foreign node in frontier\n+ cross_root_resolve flag"| XR["_resolve_hop_cross_root (:45-92)\nbatch_get foreign ROOT anchors\n→ decode EACH root's blob\n→ per-root resolve_chain"]
    PRE -->|no| WALK["fallback walk\nedges_to_nodes runtime.impl.jac:283\niterates node.edges stubs\n(ONLY place grants are checked :331,:339)"]

    RC --> MAT["materialize: TieredMemory.batch_get\n(L1 → L3 $in when batch_l3 on)"]
    RCO --> MAT
    XR --> MAT
    WALK --> MAT
```

Key asymmetries to remember:

- **Grants fire only on the fallback walk.** The indexed path never checks `check_read_access`.
  Our SQL path inherits the same semantics -- fair vs GTI.
- **Cross-root is expensive by construction**: each foreign root costs a root-anchor fetch +
  a full blob decode, because each root owns its own private index.

## 2. Where the GTI lives: a blob inside the Root anchor's row

```mermaid
flowchart LR
    subgraph PG["Postgres: anchors table (KV backend)"]
        RA["Root anchor row\ndata JSONB:\n{edges: [...],\n topology_index_data: base64 ← THE GTI BLOB}"]
        NA["node anchor rows\ndata: {archetype fields, edges: [edge-ids], version}"]
        EA["edge anchor rows\ndata: {source, target, is_undirected, archetype}"]
    end
    RA -->|"decode on read\n(cached per anchor)"| TI["TopologyIndex in Python\nnode_table, adj_list, buckets\ntopology_index.jac"]
```

Blob wire format v2 (`topology_index.impl.jac:437-467`): header `<BHHi>` (version, num_types u16,
num_nodes u16, num_edges i32), then type table (names + MRO chains), node table
(16B uuid + type_id + 16B owner_root uuid), edge list (`src_lid, etid, tgt_lid` as u16 triples).
**u16 = hard 65,535-nodes-per-root ceiling, silent corruption past it.**

### The write-amplification problem (what this branch kills)

```mermaid
sequenceDiagram
    participant App as walker: a ++> b
    participant Hook as on_edge_created (topo_utils:108)
    participant Idx as Root's TopologyIndex
    participant Ser as set_topology_index (archetype.impl.jac:264)
    participant L3 as anchors table

    App->>Hook: connect fires hook (gated by JAC_TOPOLOGY_INDEX!)
    Hook->>Idx: add_edge(a, b)
    Idx->>Ser: re-encode ENTIRE blob (every node, every edge)
    Note over Ser: cross-root edge? do it TWICE<br/>(source root + target root blobs)
    Ser->>L3: whole Root row re-written (blob grows with graph)
```

One follow edge on a 15k-anchor graph = re-serialize the whole index. Concurrent connects to
the same root = blob-level last-writer-wins (no CAS on `topology_index_data`) -- the known
concurrent-edge-discard race.

## 3. This branch: the edges table replaces the blob

```mermaid
flowchart LR
    subgraph PG["Postgres: postgres-rel backend"]
        A["anchors table -- UNCHANGED\n(nodes + edge anchors, JSONB)"]
        E["edges table -- NEW\nedge_id PK | source | target |\nedge_type | is_undirected | seq\nidx: (source, edge_type, seq)\nidx: (target, edge_type, seq)"]
    end
    RH["resolve_hop\n(new capability-gated branch)"] -->|"one indexed SQL query\nper hop"| E
    E -.->|"JOIN anchors.arch_type\nfor node-type filters"| A
```

Write path -- edge maintenance moves INTO the L3 transaction, out of runtime hooks:

```mermaid
sequenceDiagram
    participant CS as ChangeSet (staged intents)
    participant AP as PostgresRelBackend.apply()
    participant PGT as one PG transaction

    CS->>AP: EDGE_CREATE (EdgeAnchor: source, target, type)
    AP->>PGT: parent: upsert edge's anchor row
    AP->>PGT: + INSERT INTO edges (one row, seq auto)
    CS->>AP: EDGE_DELETE / NODE_DELETE
    AP->>PGT: parent: delete anchor row
    AP->>PGT: + DELETE edge row(s) / endpoint sweep
    Note over PGT: same txn = anchors row ⇔ edges row<br/>never disagree. No GTI flag involved.<br/>No blob re-encode. Cross-root = same one row.
```

Read path after (compare with diagram 1's cross-root spaghetti):

```mermaid
flowchart TD
    RH["resolve_hop"] --> CAP{"'topology_sql' in\nmem.capabilities()?"}
    CAP -->|no| OLD["existing ladder unchanged\n(GTI blob → walk)"]
    CAP -->|yes| SQL["SELECT e.target FROM edges e\nJOIN anchors a ON a.id=e.target\nWHERE e.source = ANY(frontier)\nAND e.edge_type = 'Follow'\nAND a.arch_type = 'Profile'"]
    SQL -->|"result set"| MAT["materialize (unchanged):\nbatch_get → L1/L3"]
    SQL -->|"None (error)"| OLD
```

Cross-root: **the concept disappears.** The edges table is global; a hop's frontier can span
any number of roots and it's still one query. No foreign-root fetches, no per-root decode,
no `cross_root_resolve` flag needed on this path.

## 4. What stays identical (inheritance map)

`PostgresRelBackend(PostgresBackend)` -- everything not listed above is inherited:

| Inherited untouched | Where |
|---|---|
| Pool process-cache (per dsn, lock, atexit) | postgres.impl.jac:82-118 |
| Autocommit-toggle read pattern (5fbce338e) | :751-761 etc. |
| `_pg_merge_write`: OCC via cas_version, FOR UPDATE row lock, edge-list merge, empty-node auto-delete | :376-565 |
| Quarantine machinery + INERROR guard | :175-227, :1056-1077 |
| fsck / recover / aliases | various |
| 40-test conformance surface | test_postgres_backend.jac |

## 5. The ablation story this enables

| Config | Topology answered by | Measures |
|---|---|---|
| `postgres` (KV) + GTI on | blob decode in Python | today's baseline (124.8ms feed p50) |
| `postgres-rel` + `JAC_TOPOLOGY_SQL=0` + GTI on | blob (rel storage inert) | storage-swap-only delta ≈ 0 (control) |
| `postgres-rel` + SQL hops + GTI on | edges table | hop-resolution delta, blobs still maintained |
| `postgres-rel` + SQL hops + **GTI off** | edges table | + write-amplification savings (blob re-encode gone) |

## 6. Honest limits (ledgered in the spec)

- SQL hop = 1 round-trip per hop (~0.3-1ms) vs in-memory dict lookups on a warm decode cache.
  Wins come from writes, cross-root, cold paths, scale -- not from beating a hot cached blob.
- Node-type filters are exact-match in MVP (GTI fans out over MRO; superclass filters diverge).
  Edge-type exact-match is parity (GTI is exact-match there too).
- `[edge -->]`-style edge-object collection bypasses the resolver's final hop -- not accelerated.
- Serializer/hydration tail (~25%/17% of profile) untouched by design.
