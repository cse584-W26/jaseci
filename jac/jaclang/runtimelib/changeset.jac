import from uuid { UUID }

import from jaclang.jac0core.archetype { Anchor, Archetype, EdgeAnchor, NodeAnchor }
import from jaclang.runtimelib.serializer { Serializer }
import from jaclang.runtimelib.typecache { get_field_types }
import from jaclang.runtimelib.exceptions { WriteConflict }


def _dirty_bit_env -> bool {
    # JAC_DIRTY_BIT=1: track archetype field writes via a setattr hook so the
    # commit/abort scans can prove an anchor clean without a whole-anchor
    # re-serialize. Default off = stock hash-everything behavior.
    import os;
    return os.environ.get('JAC_DIRTY_BIT', '').strip().lower()
        in ('1', 'true', 'yes', 'on');
}

glob DIRTY_BIT: bool = _dirty_bit_env();

glob _SUSPECT_CACHE: dict = {};

def _suspect_fields(cls: type) -> list[str] {
    # Fields the setattr hook is structurally blind to: containers and other
    # in-place-mutable values that can change without an attribute assignment.
    cached = _SUSPECT_CACHE.get(cls);
    if cached is not None {
        return cached;
    }
    out: list[str] = [];
    for (name, t) in get_field_types(cls).items() {
        base = getattr(t, '__origin__', t);
        if not (isinstance(base, type) and issubclass(base, (str, int, float, bool))) {
            out.append(name);
        }
    }
    _SUSPECT_CACHE[cls] = out;
    return out;
}

def _tracking_setattr(inst: object, name: str, value: object) -> None {
    object.__setattr__(inst, name, value);
    if name == '__jac__' {
        # Last write of hydration (serializer.impl.jac:889) and of creation:
        # doubles as the "hydration complete - clear noise" marker.
        inst.__dict__['__jac_dirty_fields__'] = set();
        return;
    }
    touched = inst.__dict__.get('__jac_dirty_fields__');
    if touched is None {
        touched = set();
        inst.__dict__['__jac_dirty_fields__'] = touched;
    }
    touched.add(name);
}

def _ro_walkers_configured -> bool {
    # Read the env directly (not utils.RO_WALKERS) to keep changeset import-
    # cycle-free; this is a boot-time decision either way.
    import os;
    return bool(os.environ.get('JAC_RO_WALKERS', '').strip());
}

# The RO-request guard reads __jac_dirty_fields__, so JAC_RO_WALKERS needs the
# setattr hook installed even when the dirty-bit commit path is off. Everything
# that maintains the dirty set keys off THIS, not off DIRTY_BIT - a set that is
# filled but never reset would accumulate across requests on L1-resident
# archetypes and make the guard fire on writes some earlier request committed.
glob SETATTR_HOOK: bool = DIRTY_BIT or _ro_walkers_configured();

with entry {
    if SETATTR_HOOK {
        Archetype.__setattr__ = _tracking_setattr;
    }
}


# RO-request guard: refuse - loudly - any write a JAC_RO_WALKERS-listed walker
# attempted. The raise names the exact anchor/fields; nothing was committed
# (the caller skipped acommit). Limitation: in-place container mutations are
# NOT detected (that needs the hashing scan this feature exists to skip) - the
# new-anchor / edge-delta / setattr checks cover the realistic mistakes, and
# the RO list is a curated allowlist.
def assert_request_clean -> None {
    import from jaclang { JacRuntimeInterface as Jac }
    touched: dict[UUID, any] = {};
    try {
        touched = Jac.get_context().touched;
    } except Exception {
        return;
    }
    for (id, anchor) in list(touched.items()) {
        if not anchor.persistent or not anchor.is_populated() {
            continue;
        }
        arch = anchor.archetype;
        if arch is None {
            continue;
        }
        if anchor.hash == 0 {
            raise RuntimeError(
                f"read-only walker (JAC_RO_WALKERS) created persistent "
                f"{type(arch).__name__} {id} - writes in RO requests are "
                "refused, not dropped; remove the walker from JAC_RO_WALKERS "
                "or stop writing"
            );
        }
        dirty = arch.__dict__.get('__jac_dirty_fields__');
        if dirty {
            declared = dirty & set(get_field_types(type(arch)).keys());
            if declared {
                raise RuntimeError(
                    f"read-only walker (JAC_RO_WALKERS) wrote fields "
                    f"{sorted(declared)} on {type(arch).__name__} {id} - "
                    "writes in RO requests are refused, not dropped"
                );
            }
        }
        if isinstance(anchor, NodeAnchor) {
            try {
                delta = anchor.edge_delta();
                if delta is not None and (delta[0] or delta[1]) {
                    raise RuntimeError(
                        f"read-only walker (JAC_RO_WALKERS) changed edges on "
                        f"{type(arch).__name__} {id} - writes in RO requests "
                        "are refused, not dropped"
                    );
                }
            } except RuntimeError as re { raise re; }
            except Exception { ; }
        }
    }
}


enum WriteOp {
    NODE_CREATE = 0,
    EDGE_CREATE = 1,
    EDGE_LIST_DELTA = 2,
    FIELD_UPDATE = 3,
    EDGE_DELETE = 4,
    NODE_DELETE = 5
}


obj WriteIntent {
    has op: WriteOp,
        anchor: Anchor,
        fields: set[str] postinit,
        edges_added: list[UUID] postinit,
        edges_removed: list[UUID] postinit,
        depends_on: set[UUID] postinit,
        cas_version: (int | None) = None;

    def postinit {
        self.fields = set();
        self.edges_added = [];
        self.edges_removed = [];
        self.depends_on = set();
    }

    def is_delete -> bool {
        return self.op in (WriteOp.EDGE_DELETE, WriteOp.NODE_DELETE);
    }

    def is_create -> bool {
        return self.op in (WriteOp.NODE_CREATE, WriteOp.EDGE_CREATE);
    }
}


obj ApplyReport {
    has applied: list[UUID] postinit,
        failed: dict[UUID, str] postinit,
        skipped: dict[UUID, str] postinit,
        conflicts: list[WriteConflict] postinit;

    def postinit {
        self.applied = [];
        self.failed = {};
        self.skipped = {};
        self.conflicts = [];
    }

    def ok -> bool {
        return not self.failed and not self.skipped;
    }

    def primary_conflict -> (WriteConflict | None) {
        if not self.conflicts {
            return None;
        }
        primary = self.conflicts[0];
        if len(self.conflicts) > 1 {
            primary.siblings = self.conflicts[1:];
        }
        return primary;
    }
}


obj ChangeSet {
    has intents: dict[UUID, WriteIntent] postinit;

    def postinit {
        self.intents = {};
    }

    def is_empty -> bool {
        return not self.intents;
    }

    def clear {
        self.intents = {};
    }

    def record_create(anchor: Anchor) -> None {
        existing = self.intents.get(anchor.id);
        if existing is not None and existing.is_delete() {
            return;
        }
        op = WriteOp.EDGE_CREATE
            if isinstance(anchor, EdgeAnchor)
            else WriteOp.NODE_CREATE;
        if existing is not None {
            existing.op = op;
        } else {
            existing = WriteIntent(op=op, anchor=anchor);
            self.intents[anchor.id] = existing;
        }

        if isinstance(anchor, EdgeAnchor) and anchor.is_populated() {
            for endp in (anchor.source, anchor.target) {
                if endp is not None {
                    existing.depends_on.add(endp.id);
                }
            }
        }
    }

    def record_update(anchor: Anchor, fields: set[str]) -> None {
        existing = self.intents.get(anchor.id);
        if existing is not None {
            if existing.is_delete() {
                return;
            }
            existing.fields |= set(fields);
            return;
        }
        intent = WriteIntent(op=WriteOp.FIELD_UPDATE, anchor=anchor);
        intent.fields |= set(fields);
        self.intents[anchor.id] = intent;
    }

    def record_edge_delta(
        anchor: NodeAnchor, added: list[UUID], removed: list[UUID]
    ) -> None {
        existing = self.intents.get(anchor.id);
        if existing is not None and (existing.is_delete() or existing.is_create()) {
            return;
        }
        if existing is None {
            existing = WriteIntent(op=WriteOp.EDGE_LIST_DELTA, anchor=anchor);
            self.intents[anchor.id] = existing;
        } elif existing.op == WriteOp.FIELD_UPDATE {
            existing.op = WriteOp.EDGE_LIST_DELTA;
        }
        for eid in added {
            if eid in existing.edges_removed {
                existing.edges_removed.remove(eid);
            } elif eid not in existing.edges_added {
                existing.edges_added.append(eid);
                existing.depends_on.add(eid);
            }
        }
        for eid in removed {
            if eid in existing.edges_added {
                existing.edges_added.remove(eid);
                existing.depends_on.discard(eid);
            } elif eid not in existing.edges_removed {
                existing.edges_removed.append(eid);
            }
        }
    }

    def record_delete(anchor: Anchor) {
        op = WriteOp.EDGE_DELETE
            if isinstance(anchor, EdgeAnchor)
            else WriteOp.NODE_DELETE;
        intent = WriteIntent(op=op, anchor=anchor);
        if isinstance(anchor, EdgeAnchor) and anchor.is_populated() {
            for endp in (anchor.source, anchor.target) {
                if endp is not None {
                    intent.depends_on.add(endp.id);
                    if isinstance(endp, NodeAnchor) {
                        existing_endp = self.intents.get(endp.id);
                        if existing_endp is None or not existing_endp.is_delete() {
                            self.record_edge_delta(endp, added=[], removed=[anchor.id]);
                        }
                    }
                }
            }
        } elif isinstance(anchor, NodeAnchor) and anchor.is_populated() {
            for ed in anchor.edges {
                intent.depends_on.add(ed.id);
            }
        }
        self.intents[anchor.id] = intent;
    }

    def staged -> list[list[WriteIntent]] {
        stages: list[list[WriteIntent]] = [[] for i in range(6)];
        for intent in self.intents.values() {
            stages[intent.op.value].append(intent);
        }
        return stages;
    }
}


def field_hash(serialized: object) -> int {
    import from json { dumps }
    try {
        return hash(dumps(serialized, sort_keys=True, default=str));
    } except Exception {
        return 0;
    }
}


def snapshot_field_hashes(anchor: Anchor) -> None {
    if not anchor.is_populated() or anchor.archetype is None {
        return;
    }
    arch = anchor.archetype;
    hashes: dict[str, int] = {};
    _seen: tuple[set, set] = (set(), set());
    for name in get_field_types(type(arch)).keys() {
        val = getattr(arch, name, None);
        serialized = Serializer._serialize_value(val, include_type=True, _seen=_seen);
        hashes[name] = field_hash(serialized);
    }
    if DIRTY_BIT {
        # access lives on the ANCHOR, not the archetype: grant() mutates it in
        # place, invisible to the setattr hook, so the gate needs a baseline.
        try {
            hashes['__anchor_access__'] = field_hash(
                Serializer._serialize_value(anchor.access, include_type=True, _seen=_seen)
            );
        } except Exception {
            hashes['__anchor_access__'] = 0;
        }
    }
    object.__setattr__(arch, '__jac_field_hashes__', hashes);
    if SETATTR_HOOK and arch.__dict__.get('__jac_dirty_fields__') {
        # snapshot == "this anchor is now in its persisted state", so the
        # dirty set resets here too (covers the _post_apply re-baseline site,
        # where no `__jac__` write happens).
        arch.__dict__['__jac_dirty_fields__'] = set();
    }
}


"""DIRTY_BIT fast gate: True = provably clean (skip whole-anchor hash),
False = cannot prove clean (caller falls back to the stock hash path)."""
def anchor_clean_fast(anchor: Anchor) -> bool {
    if not DIRTY_BIT {
        return False;
    }
    if not anchor.is_populated() or anchor.archetype is None {
        return False;
    }
    arch = anchor.archetype;
    stored: dict[str, int] = arch.__dict__.get('__jac_field_hashes__', {});
    if not stored or '__anchor_access__' not in stored {
        return False;
    }
    touched = arch.__dict__.get('__jac_dirty_fields__');
    if touched {
        ftypes = get_field_types(type(arch));
        if touched & set(ftypes.keys()) {
            return False;
        }
    }
    _seen: tuple[set, set] = (set(), set());
    for name in _suspect_fields(type(arch)) {
        val = getattr(arch, name, None);
        serialized = Serializer._serialize_value(val, include_type=True, _seen=_seen);
        if field_hash(serialized) != stored.get(name) {
            return False;
        }
    }
    try {
        acc = Serializer._serialize_value(anchor.access, include_type=True, _seen=_seen);
        if field_hash(acc) != stored.get('__anchor_access__') {
            return False;
        }
    } except Exception {
        return False;
    }
    if isinstance(anchor, NodeAnchor) {
        try {
            delta = anchor.edge_delta();
            if delta is not None and (delta[0] or delta[1]) {
                return False;
            }
        } except Exception {
            return False;
        }
    }
    return True;
}


def derive_dirty_fields(anchor: Anchor) -> set[str] {
    if not anchor.is_populated() or anchor.archetype is None {
        return set();
    }
    arch = anchor.archetype;
    stored: dict[str, int] = arch.__dict__.get('__jac_field_hashes__', {});
    if not stored {
        return set();
    }
    dirty: set[str] = set();
    _seen: tuple[set, set] = (set(), set());
    ftypes = get_field_types(type(arch));
    names = list(ftypes.keys());
    if DIRTY_BIT {
        touched = arch.__dict__.get('__jac_dirty_fields__');
        if touched {
            dirty |= (touched & set(ftypes.keys()));
        }
        names = [n for n in _suspect_fields(type(arch)) if n not in dirty];
    }
    for name in names {
        val = getattr(arch, name, None);
        serialized = Serializer._serialize_value(val, include_type=True, _seen=_seen);
        if field_hash(serialized) != stored.get(name) {
            dirty.add(name);
        }
    }
    return dirty;
}
