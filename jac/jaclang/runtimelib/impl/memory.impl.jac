"""Memory Hierarchy Implementations.

Implementations for VolatileMemory, LocalCacheMemory, SqliteMemory, and TieredMemory.
"""

import logging;
import os;
import sqlite3;
import from collections.abc { Callable, Generator, Iterable }
import from pickle { dumps, loads }
import from typing { cast }
import from uuid { UUID }
import from jaclang.jac0core.archetype { Anchor, NodeAnchor, Root }

glob logger = logging.getLogger(__name__);

# =============================================================================
# VolatileMemory Implementation (L1)
# =============================================================================
"""Initialize mutable defaults."""
impl VolatileMemory.postinit -> None {
    self.__mem__ = {};
    self.__gc__ = set();
}

"""In-memory storage is always available."""
impl VolatileMemory.is_available -> bool {
    return True;
}

"""Retrieve an anchor by ID."""
impl VolatileMemory.get(id: UUID) -> (Anchor | None) {
    return self.__mem__.get(id);
}

"""Store an anchor."""
impl VolatileMemory.put(anchor: Anchor) -> None {
    self.__mem__[anchor.id] = anchor;
}

"""Remove an anchor by ID and track for garbage collection."""
impl VolatileMemory.delete(id: UUID) -> None {
    if (anchor := self.__mem__.pop(id, None)) {
        self.__gc__.add(anchor);
    }
}

"""Close and clear memory."""
impl VolatileMemory.close -> None {
    self.__mem__.clear();
    self.__gc__.clear();
}

"""Check if an anchor is in memory."""
impl VolatileMemory.`has(id: UUID) -> bool {
    return id in self.__mem__;
}

"""Query all anchors with optional filter."""
impl VolatileMemory.query(
    filter: (Callable[[Anchor], bool] | None) = None
) -> Generator[Anchor, None, None] {
    for anchor in self.__mem__.values() {
        if filter is None or filter(anchor) {
            yield anchor;
        }
    }
}

"""Get all root anchors."""
impl VolatileMemory.get_roots -> Generator[Root, None, None] {
    for anchor in self.__mem__.values() {
        if isinstance(anchor.archetype, Root) {
            yield cast(Root, anchor.archetype);
        }
    }
}

"""Find anchors by IDs with optional filter."""
impl VolatileMemory.find(
    ids: (UUID | Iterable[UUID]), filter: (Callable[[Anchor], Anchor] | None) = None
) -> Generator[Anchor, None, None] {
    id_list = [ids] if isinstance(ids, UUID) else list(ids);
    for id in id_list {
        if (anchor := self.__mem__.get(id)) {
            if filter is None or filter(anchor) {
                yield anchor;
            }
        }
    }
}

"""Find one anchor by ID(s) with optional filter."""
impl VolatileMemory.find_one(
    ids: (UUID | Iterable[UUID]), filter: (Callable[[Anchor], Anchor] | None) = None
) -> (Anchor | None) {
    id_list = [ids] if isinstance(ids, UUID) else list(ids);
    for id in id_list {
        if (anchor := self.__mem__.get(id)) {
            if filter is None or filter(anchor) {
                return anchor;
            }
        }
    }
    return None;
}

"""Get garbage collection list."""
impl VolatileMemory.get_gc -> list[Anchor] {
    return list(self.__gc__);
}

"""Remove anchor from garbage collection list."""
impl VolatileMemory.remove_from_gc(anchor: Anchor) -> None {
    self.__gc__.discard(anchor);
}

"""Get the underlying memory dict."""
impl VolatileMemory.get_mem -> dict[UUID, Anchor] {
    return self.__mem__;
}

"""Commit - no-op for volatile memory."""
impl VolatileMemory.commit(anchor: (Anchor | None) = None) -> None {
# No persistence, nothing to commit
}

"""Bulk get anchors by ID set from memory."""
impl VolatileMemory.bulk_get(ids: set[UUID]) -> dict[UUID, Anchor] {
    result: dict[UUID, Anchor] = {};
    for id in ids {
        if (anchor := self.__mem__.get(id)) {
            result[id] = anchor;
        }
    }
    return result;
}

"""Default filtered_bulk_get — ignores predicates, delegates to bulk_get."""
impl VolatileMemory.filtered_bulk_get(ids: set[UUID], predicates: list = []) -> dict[UUID, Anchor] {
    return self.bulk_get(ids);
}

# =============================================================================
# LocalCacheMemory Implementation (L2)
# Inherits all Memory interface methods from VolatileMemory.
# Only implements CacheMemory-specific methods.
# =============================================================================
"""Check if a key exists in the cache without loading the value."""
impl LocalCacheMemory.exists(id: UUID) -> bool {
    return id in self.__mem__;
}

"""Store an anchor only if it already exists in the cache."""
impl LocalCacheMemory.put_if_exists(anchor: Anchor) -> bool {
    if anchor.id in self.__mem__ {
        self.__mem__[anchor.id] = anchor;
        return True;
    }
    return False;
}

"""Invalidate a cache entry by ID."""
impl LocalCacheMemory.invalidate(id: UUID) -> None {
    self.__mem__.pop(id, None);
}

# =============================================================================
# SqliteMemory Implementation (L3 Persistent)
# =============================================================================
"""Initialize SqliteMemory with a file path (lazy - no DB created yet)."""
impl SqliteMemory.postinit -> None {
    self.__mem__ = {};
    self.__gc__ = set();
    # Connection is lazily initialized on first write
    self.__conn__ = None;
    self.l3_fetch_count = 0;
}

"""Lazily initialize SQLite connection when first needed."""
impl SqliteMemory._ensure_connection -> None {
    if self.__conn__ is not None {
        return;
    }
    # Ensure parent directory exists for database file
    parent_dir = os.path.dirname(self.path);
    if parent_dir {
        os.makedirs(parent_dir, exist_ok=True);
    }
    # Open SQLite connection with WAL mode for better concurrency
    self.__conn__ = sqlite3.connect(self.path, check_same_thread=False);
    self.__conn__.execute("PRAGMA journal_mode=WAL");
    self.__conn__.execute("PRAGMA synchronous=NORMAL");
    # Create anchors table if it doesn't exist
    self.__conn__.execute(
        """
        CREATE TABLE IF NOT EXISTS anchors (
            id TEXT PRIMARY KEY,
            data BLOB NOT NULL
        )
    """
    );
    # Secondary index table for predicate pushdown
    self.__conn__.execute(
        """
        CREATE TABLE IF NOT EXISTS node_properties (
            anchor_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            field_value TEXT,
            field_type TEXT,
            PRIMARY KEY (anchor_id, field_name)
        )
    """
    );
    self.__conn__.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_np_field_value
        ON node_properties(field_name, field_value)
    """
    );
    self.__conn__.commit();
}

"""Check if database connection is available."""
impl SqliteMemory.is_available -> bool {
    return self.__conn__ is not None;
}

"""Get an anchor by ID. Check memory first, then database."""
impl SqliteMemory.get(id: UUID) -> (Anchor | None) {
    import from _pickle { UnpicklingError }
    # Check in-memory cache first
    if (anchor := self.__mem__.get(id)) {
        return anchor;
    }
    # Lazily connect if DB file exists (for reading existing data)
    if not self.__conn__ and os.path.exists(self.path) {
        self._ensure_connection();
    }
    # Check database
    if self.__conn__ {
        cursor = self.__conn__.execute(
            "SELECT data FROM anchors WHERE id = ?", (str(id), )
        );
        if (row := cursor.fetchone()) {
            try {
                self.l3_fetch_count += 1;
                anchor = loads(row[0]);
                # Promote to memory cache
                self.__mem__[id] = anchor;
                return anchor;
            } except (UnpicklingError, ModuleNotFoundError, AttributeError) {
                # Can't unpickle - likely stale data from previous session
                # Delete the stale entry
                self.__conn__.execute("DELETE FROM anchors WHERE id = ?", (str(id), ));
                self.__conn__.commit();
                return None;
            }
        }
    }
    return None;
}

"""Store an anchor. Writes to memory and immediately persists to database."""
impl SqliteMemory.put(anchor: Anchor) -> None {
    self.__mem__[anchor.id] = anchor;
    if anchor.persistent {
        self._ensure_connection();
        try {
            self.__conn__.execute(
                "INSERT OR REPLACE INTO anchors (id, data) VALUES (?, ?)",
                (str(anchor.id), dumps(anchor))
            );
            self.__conn__.commit();
        } except Exception as e {
            logger.warning(f"SqliteMemory.put immediate persist failed: {e}");
        }
    }
}

"""Delete an anchor and track for garbage collection (only if persistent)."""
impl SqliteMemory.delete(id: UUID) -> None {
    if (anchor := self.__mem__.pop(id, None)) {
        # Only track persistent anchors for DB deletion
        if anchor.persistent {
            self.__gc__.add(anchor);
        }
    }
    # Also remove from database immediately if connected
    if self.__conn__ {
        self.__conn__.execute("DELETE FROM anchors WHERE id = ?", (str(id), ));
        self.__conn__.commit();
    }
}

"""Close database connection and clear memory."""
impl SqliteMemory.close -> None {
    if self.__conn__ {
        self.__conn__.close();
        self.__conn__ = None;
    }
    self.__mem__.clear();
    self.__gc__.clear();
}

"""Check if an anchor is in memory or database."""
impl SqliteMemory.`has(id: UUID) -> bool {
    if id in self.__mem__ {
        return True;
    }
    # Lazily connect if DB file exists
    if not self.__conn__ and os.path.exists(self.path) {
        self._ensure_connection();
    }
    if self.__conn__ {
        cursor = self.__conn__.execute(
            "SELECT 1 FROM anchors WHERE id = ?", (str(id), )
        );
        return cursor.fetchone() is not None;
    }
    return False;
}

"""Query all anchors with optional filter."""
impl SqliteMemory.query(
    filter: (Callable[[Anchor], bool] | None) = None
) -> Generator[Anchor, None, None] {
    for anchor in self.__mem__.values() {
        if filter is None or filter(anchor) {
            yield anchor;
        }
    }
}

"""Get all root anchors."""
impl SqliteMemory.get_roots -> Generator[Root, None, None] {
    for anchor in self.__mem__.values() {
        if isinstance(anchor.archetype, Root) {
            yield cast(Root, anchor.archetype);
        }
    }
}

"""Find anchors by IDs with optional filter."""
impl SqliteMemory.find(
    ids: (UUID | Iterable[UUID]), filter: (Callable[[Anchor], Anchor] | None) = None
) -> Generator[Anchor, None, None] {
    id_list = [ids] if isinstance(ids, UUID) else list(ids);
    for id in id_list {
        if (anchor := self.get(id)) {
            if filter is None or filter(anchor) {
                yield anchor;
            }
        }
    }
}

"""Find one anchor by ID(s) with optional filter."""
impl SqliteMemory.find_one(
    ids: (UUID | Iterable[UUID]), filter: (Callable[[Anchor], Anchor] | None) = None
) -> (Anchor | None) {
    id_list = [ids] if isinstance(ids, UUID) else list(ids);
    for id in id_list {
        if (anchor := self.get(id)) {
            if filter is None or filter(anchor) {
                return anchor;
            }
        }
    }
    return None;
}

"""Extract scalar fields from a NodeAnchor's archetype and upsert into node_properties."""
def _upsert_node_properties(conn: sqlite3.Connection, anchor_id: str, archetype: object) -> None {
    _SCALAR_TYPES = (str, int, float, bool, type(None));
    # Delete existing properties for this anchor
    conn.execute("DELETE FROM node_properties WHERE anchor_id = ?", (anchor_id, ));
    # Extract and insert scalar fields
    try {
        fields = vars(archetype);
    } except TypeError {
        return;
    }
    for (fname, fval) in fields.items() {
        if fname.startswith('_') {
            continue;
        }
        if not isinstance(fval, _SCALAR_TYPES) {
            continue;
        }
        if fval is None {
            field_type = "none";
            field_value = None;
        } elif isinstance(fval, bool) {
            field_type = "bool";
            field_value = str(fval);
        } elif isinstance(fval, int) {
            field_type = "int";
            field_value = str(fval);
        } elif isinstance(fval, float) {
            field_type = "float";
            field_value = str(fval);
        } else {
            field_type = "str";
            field_value = str(fval);
        }
        conn.execute(
            "INSERT OR REPLACE INTO node_properties (anchor_id, field_name, field_value, field_type) VALUES (?, ?, ?, ?)",
            (anchor_id, fname, field_value, field_type)
        );
    }
}

"""Sync memory to database with access control checks."""
impl SqliteMemory.sync -> None {
    import from jaclang { JacRuntimeInterface as Jac }
    import from _pickle { PicklingError }
    # Check if there's anything to sync
    has_persistent = any(a.persistent for a in self.__mem__.values());
    if not self.__gc__ and not has_persistent {
        return;  # Nothing to sync, don't create DB

    }
    # Lazily create connection now that we have data to persist
    self._ensure_connection();
    # Handle garbage collected anchors (deletions)
    for anchor in self.__gc__ {
        anchor_id_str = str(anchor.id);
        self.__conn__.execute("DELETE FROM anchors WHERE id = ?", (anchor_id_str, ));
        self.__conn__.execute("DELETE FROM node_properties WHERE anchor_id = ?", (anchor_id_str, ));
    }
    self.__gc__.clear();
    # Sync memory to database with access control
    for (id, anchor) in list(self.__mem__.items()) {
        if not anchor.persistent {
            continue;
        }
        # Skip stubs - only sync fully populated anchors
        if not anchor.is_populated() {
            continue;
        }

        key = str(id);
        try {
            cursor = self.__conn__.execute(
                "SELECT data FROM anchors WHERE id = ?", (key, )
            );
            row = cursor.fetchone();
            stored = loads(row[0]) if row else None;

            if stored and stored.is_populated() {
                changed = False;
                # Handle edge updates (CONNECT access)
                if (
                    isinstance(stored, NodeAnchor)
                    and isinstance(anchor, NodeAnchor)
                    and stored.edges != anchor.edges
                    and Jac.check_connect_access(anchor)
                ) {
                    if not anchor.edges and not isinstance(anchor.archetype, Root) {
                        self.__conn__.execute(
                            "DELETE FROM anchors WHERE id = ?", (key, )
                        );
                        continue;
                    }
                    stored.edges = anchor.edges;
                    changed = True;
                }
                # Handle access/archetype updates (WRITE access)
                access_changed = hash(dumps(stored.access)) != hash(
                    dumps(anchor.access)
                );
                archetype_changed = hash(dumps(stored.archetype)) != hash(
                    dumps(anchor.archetype)
                );
                if (access_changed or archetype_changed)
                and Jac.check_write_access(anchor) {
                    if access_changed {
                        stored.access = anchor.access;
                    }
                    if archetype_changed {
                        stored.archetype = anchor.archetype;
                    }
                    changed = True;
                }
                # Only write to database if something actually changed
                if changed {
                    self.__conn__.execute(
                        "INSERT OR REPLACE INTO anchors (id, data) VALUES (?, ?)",
                        (key, dumps(stored))
                    );
                    # Update node_properties for predicate pushdown
                    if isinstance(stored, NodeAnchor) and stored.archetype {
                        _upsert_node_properties(self.__conn__, key, stored.archetype);
                    }
                }
            } else {
                # No stored or stored is a stub - save anchor if valid
                if not (
                    isinstance(anchor, NodeAnchor)
                    and not isinstance(anchor.archetype, Root)
                    and not anchor.edges
                )
                and Jac.check_write_access(anchor) {
                    self.__conn__.execute(
                        "INSERT OR REPLACE INTO anchors (id, data) VALUES (?, ?)",
                        (key, dumps(anchor))
                    );
                    # Update node_properties for predicate pushdown
                    if isinstance(anchor, NodeAnchor) and anchor.archetype {
                        _upsert_node_properties(self.__conn__, key, anchor.archetype);
                    }
                }
            }
        } except (PicklingError, AttributeError, ModuleNotFoundError) {
            # Skip anchors that can't be pickled (e.g., transient test classes)
            continue;
        }
    }
    self.__conn__.commit();
}

"""Bulk get anchors by ID set. Uses single SELECT ... WHERE id IN (...) query."""
impl SqliteMemory.bulk_get(ids: set[UUID]) -> dict[UUID, Anchor] {
    import from _pickle { UnpicklingError }
    result: dict[UUID, Anchor] = {};
    remaining: set[UUID] = set();
    # Check in-memory cache first
    for id in ids {
        if (anchor := self.__mem__.get(id)) {
            result[id] = anchor;
        } else {
            remaining.add(id);
        }
    }
    if not remaining {
        return result;
    }
    # Lazily connect if DB file exists
    if not self.__conn__ and os.path.exists(self.path) {
        self._ensure_connection();
    }
    if self.__conn__ {
        # Batch fetch from SQLite with single query
        id_strs = [str(id) for id in remaining];
        placeholders = ",".join(["?"] * len(id_strs));
        cursor = self.__conn__.execute(
            f"SELECT id, data FROM anchors WHERE id IN ({placeholders})",
            id_strs
        );
        for row in cursor.fetchall() {
            try {
                self.l3_fetch_count += 1;
                anchor = loads(row[1]);
                uid = UUID(row[0]);
                self.__mem__[uid] = anchor;
                result[uid] = anchor;
            } except (UnpicklingError, ModuleNotFoundError, AttributeError) {
                self.__conn__.execute("DELETE FROM anchors WHERE id = ?", (row[0], ));
            }
        }
        if cursor.rowcount and cursor.rowcount < 0 {
            self.__conn__.commit();
        }
    }
    return result;
}

"""Filtered bulk get — uses node_properties table to narrow results before deserialization."""
impl SqliteMemory.filtered_bulk_get(ids: set[UUID], predicates: list = []) -> dict[UUID, Anchor] {
    if not predicates {
        return self.bulk_get(ids);
    }
    import from _pickle { UnpicklingError }
    import from jaclang.runtimelib.query_filter { CompareOp }
    result: dict[UUID, Anchor] = {};
    remaining: set[UUID] = set();
    # Check in-memory cache first
    for id in ids {
        if (anchor := self.__mem__.get(id)) {
            result[id] = anchor;
        } else {
            remaining.add(id);
        }
    }
    if not remaining {
        return result;
    }
    if not self.__conn__ and os.path.exists(self.path) {
        self._ensure_connection();
    }
    if self.__conn__ {
        # Build SQL query with predicate pushdown via node_properties
        id_strs = [str(id) for id in remaining];
        placeholders = ",".join(["?"] * len(id_strs));
        sql = f"SELECT a.id, a.data FROM anchors a WHERE a.id IN ({placeholders})";
        params: list = list(id_strs);

        # Add EXISTS subquery for each predicate
        _COMPARE_SQL = {
            CompareOp.EQ: "= ?",
            CompareOp.NE: "!= ?",
            CompareOp.LT: "< ?",
            CompareOp.LE: "<= ?",
            CompareOp.GT: "> ?",
            CompareOp.GE: ">= ?"
        };
        for pred in predicates {
            cmp_sql = _COMPARE_SQL.get(pred.op, None);
            if cmp_sql is None {
                continue;
            }
            # Use CAST for numeric comparisons
            if pred.op in (CompareOp.LT, CompareOp.LE, CompareOp.GT, CompareOp.GE)
            and isinstance(pred.value, (int, float)) {
                sql += (
                    " AND EXISTS (SELECT 1 FROM node_properties np"
                    " WHERE np.anchor_id = a.id"
                    f" AND np.field_name = ? AND CAST(np.field_value AS REAL) {cmp_sql})"
                );
            } else {
                sql += (
                    " AND EXISTS (SELECT 1 FROM node_properties np"
                    " WHERE np.anchor_id = a.id"
                    f" AND np.field_name = ? AND np.field_value {cmp_sql})"
                );
            }
            params.append(pred.field_name);
            params.append(str(pred.value) if pred.value is not None else None);
        }

        cursor = self.__conn__.execute(sql, params);
        for row in cursor.fetchall() {
            try {
                self.l3_fetch_count += 1;
                anchor = loads(row[1]);
                uid = UUID(row[0]);
                self.__mem__[uid] = anchor;
                result[uid] = anchor;
            } except (UnpicklingError, ModuleNotFoundError, AttributeError) {
                self.__conn__.execute("DELETE FROM anchors WHERE id = ?", (row[0], ));
            }
        }
    }
    return result;
}

"""Bulk store multiple anchors."""
impl SqliteMemory.bulk_put(anchors: Iterable[Anchor]) -> None {
    for anchor in anchors {
        self.put(anchor);
    }
}

"""Get garbage collection list."""
impl SqliteMemory.get_gc -> list[Anchor] {
    return list(self.__gc__);
}

"""Remove anchor from garbage collection list."""
impl SqliteMemory.remove_from_gc(anchor: Anchor) -> None {
    self.__gc__.discard(anchor);
}

"""Get the underlying memory dict."""
impl SqliteMemory.get_mem -> dict[UUID, Anchor] {
    return self.__mem__;
}

"""Commit - syncs pending changes to database."""
impl SqliteMemory.commit(anchor: (Anchor | None) = None) -> None {
    self.sync();
}

# =============================================================================
# TieredMemory Implementation (extends VolatileMemory with L2 + L3)
# Inherits L1 functionality (__mem__, __gc__) from VolatileMemory.
# Only overrides methods that need tiering logic.
# =============================================================================
"""Initialize TieredMemory with optional cache and persistence."""
impl TieredMemory.postinit -> None {
    import from jaclang.runtimelib.memory { LocalCacheMemory, SqliteMemory }
    import from jaclang.runtimelib.utils { get_db_path }
    # Initialize L1 (inherited from VolatileMemory)
    self.__mem__ = {};
    self.__gc__ = set();
    # Initialize L2 cache if requested
    if self.use_cache {
        self.l2 = LocalCacheMemory();
    } else {
        self.l2 = None;
    }
    # Initialize L3 persistence if base_path provided
    if self.base_path {
        # Use project.db for projects, filename.db for standalone apps
        db_path = get_db_path(self.base_path);
        self.l3 = SqliteMemory(path=db_path);
    } else {
        self.l3 = None;
    }
}

"""Get anchor with read-through: L1 -> L2 -> L3 with promotion."""
impl TieredMemory.get(id: UUID) -> (Anchor | None) {
    # L1 hit (self.__mem__ inherited from VolatileMemory)
    if (anchor := self.__mem__.get(id)) {
        return anchor;
    }
    # L2 hit with promotion to L1
    if self.l2 and (anchor := self.l2.get(id)) {
        self.__mem__[anchor.id] = anchor;
        return anchor;
    }
    # L3 fallback with promotion to L1 (and L2 if enabled)
    if self.l3 and (anchor := self.l3.get(id)) {
        self.__mem__[anchor.id] = anchor;
        if self.l2 {
            self.l2.put(anchor);
        }
        return anchor;
    }
    return None;
}

"""Bulk get anchors: L1 first, then batch fetch remaining from L2/L3."""
impl TieredMemory.bulk_get(ids: set[UUID]) -> dict[UUID, Anchor] {
    result: dict[UUID, Anchor] = {};
    remaining: set[UUID] = set();
    # L1 hits
    for id in ids {
        if (anchor := self.__mem__.get(id)) {
            result[id] = anchor;
        } else {
            remaining.add(id);
        }
    }
    if not remaining {
        return result;
    }
    # L2 bulk fetch with promotion to L1
    if self.l2 {
        l2_results = self.l2.bulk_get(remaining);
        for (id, anchor) in l2_results.items() {
            self.__mem__[id] = anchor;
            result[id] = anchor;
        }
        remaining = remaining - set(l2_results.keys());
    }
    if not remaining {
        return result;
    }
    # L3 bulk fetch with promotion to L1 (and L2 if enabled)
    if self.l3 {
        l3_results = self.l3.bulk_get(remaining);
        for (id, anchor) in l3_results.items() {
            self.__mem__[id] = anchor;
            if self.l2 {
                self.l2.put(anchor);
            }
            result[id] = anchor;
        }
    }
    return result;
}

"""Filtered bulk get: L1 first, then push predicates to L3."""
impl TieredMemory.filtered_bulk_get(ids: set[UUID], predicates: list = []) -> dict[UUID, Anchor] {
    if not predicates {
        return self.bulk_get(ids);
    }
    result: dict[UUID, Anchor] = {};
    remaining: set[UUID] = set();
    # L1 hits (no filter — already in memory, cheap)
    for id in ids {
        if (anchor := self.__mem__.get(id)) {
            result[id] = anchor;
        } else {
            remaining.add(id);
        }
    }
    if not remaining {
        return result;
    }
    # Skip L2 for filtered queries — push predicates directly to L3
    if self.l3 {
        l3_results = self.l3.filtered_bulk_get(remaining, predicates);
        for (id, anchor) in l3_results.items() {
            self.__mem__[id] = anchor;
            if self.l2 {
                self.l2.put(anchor);
            }
            result[id] = anchor;
        }
    }
    return result;
}

"""Put anchor with write-through: L1 always, L2/L3 with access control."""
impl TieredMemory.put(anchor: Anchor) -> None {
    import from jaclang { JacRuntimeInterface as Jac }
    # Always write to L1 (self.__mem__ inherited from VolatileMemory)
    self.__mem__[anchor.id] = anchor;
    # Write-through to L2 (cache) if enabled
    if self.l2 {
        self.l2.put(anchor);
    }
    # Write-through to L3 with access control check
    if self.l3 and anchor.persistent {
        if Jac.check_write_access(anchor) {
            self.l3.put(anchor);
        }
    }
}

"""Delete anchor from all tiers."""
impl TieredMemory.delete(id: UUID) -> None {
    # Delete from L1 (only track persistent anchors for GC)
    if (anchor := self.__mem__.pop(id, None)) {
        if anchor.persistent {
            self.__gc__.add(anchor);
        }
    }
    # Invalidate L2 cache
    if self.l2 {
        self.l2.invalidate(id);
    }
    # Delete from L3 persistence (only if we have persistent data)
    if self.l3 {
        self.l3.delete(id);
    }
}

"""Close all tiers."""
impl TieredMemory.close -> None {
    # Sync L3 before closing
    if self.l3 {
        self.l3.sync();
        self.l3.close();
    }
    # Close L2
    if self.l2 {
        self.l2.close();
    }
    # Clear L1 (inherited from VolatileMemory)
    self.__mem__.clear();
    self.__gc__.clear();
}

"""Check if anchor exists in any tier."""
impl TieredMemory.`has(id: UUID) -> bool {
    # Check L1 first
    if id in self.__mem__ {
        return True;
    }
    # Check L2 cache
    if self.l2 and self.l2.exists(id) {
        return True;
    }
    # Check L3 persistence
    if self.l3 and self.l3.`has(id) {
        return True;
    }
    return False;
}

"""Get L3 fetch count for testing/instrumentation."""
impl TieredMemory.get_l3_fetch_count -> int {
    import from jaclang.runtimelib.memory { SqliteMemory }
    if isinstance(self.l3, SqliteMemory) {
        return self.l3.l3_fetch_count;
    }
    return 0;
}

"""Reset L3 fetch count for testing/instrumentation."""
impl TieredMemory.reset_l3_fetch_count -> None {
    import from jaclang.runtimelib.memory { SqliteMemory }
    if isinstance(self.l3, SqliteMemory) {
        self.l3.l3_fetch_count = 0;
    }
}

"""Commit - syncs L3 persistence if available."""
impl TieredMemory.commit(anchor: (Anchor | None) = None) -> None {
    if self.l3 {
        self.l3.sync();
    }
}
