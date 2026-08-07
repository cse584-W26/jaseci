import os;

import from uuid { UUID }

import from jaclang.jac0core.archetype { Anchor, EdgeAnchor, NodeAnchor }
import from jaclang.runtimelib.serializer { Serializer }
import from jaclang.runtimelib.typecache { get_field_types }
import from jaclang.runtimelib.exceptions { WriteConflict }


def _dirty_bit_env -> bool {
    env = os.environ.get("JAC_DIRTY_BIT");
    return env is not None and env.lower() in ("1", "true", "yes", "on");
}


glob DIRTY_BIT: bool = _dirty_bit_env(),
     _SUSPECT_CACHE: dict[type, list[str]] = {};


def _suspect_fields(cls: type) -> list[str] {
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


def _tracking_setattr(self: object, name: str, value: object) {
    object.__setattr__(self, name, value);
    d = self.__dict__;
    s = d.get('__jac_dirty_fields__');
    if s is None {
        d['__jac_dirty_fields__'] = {name};
    } else {
        s.add(name);
    }
}


def _ro_guard_env -> bool {
    return bool((os.environ.get("JAC_RO_WALKERS") or "").strip());
}


glob RO_GUARD: bool = _ro_guard_env();


with entry {
    if DIRTY_BIT or RO_GUARD {
        import from jaclang.jac0core.archetype { Archetype as _ArchBase }
        _ArchBase.__setattr__ = _tracking_setattr;
    }
}


def assert_no_dirty(mem_items: list) {
    for (id, anchor) in mem_items {
        if not anchor.persistent or not anchor.is_populated() {
            continue;
        }
        if anchor?._projected_fields is not None {
            continue;
        }
        arch = anchor.archetype;
        if arch is None {
            continue;
        }
        touched = arch.__dict__.get('__jac_dirty_fields__');
        if touched {
            touched = touched & set(get_field_types(type(arch)).keys());
        }
        if touched {
            raise RuntimeError(
                f"read-only walker (JAC_RO_WALKERS) wrote fields {sorted(touched)} "
                f"on {type(arch).__name__} {id} - writes in RO requests are refused, "
                f"not dropped; remove the walker from JAC_RO_WALKERS or stop writing"
            );
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
        fields: set[str] by postinit,
        edges_added: list[UUID] by postinit,
        edges_removed: list[UUID] by postinit,
        depends_on: set[UUID] by postinit,
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
    has applied: list[UUID] by postinit,
        failed: dict[UUID, str] by postinit,
        skipped: dict[UUID, str] by postinit,
        conflicts: list[WriteConflict] by postinit;

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
    has intents: dict[UUID, WriteIntent] by postinit;

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


import from jaclang.runtimelib.utils { read_only_enabled, request_read_only }


def snapshot_field_hashes(anchor: Anchor) -> None {
    if request_read_only() {
        if (
            (RO_GUARD or DIRTY_BIT)
            and anchor.is_populated()
            and anchor.archetype is not None
        ) {
            anchor.archetype.__dict__['__jac_dirty_fields__'] = set();
        }
        return;
    }
    if not anchor.is_populated() or anchor.archetype is None {
        return;
    }
    arch = anchor.archetype;
    hashes: dict[str, int] = {};
    _seen: tuple[set, set] = (set(), set());
    if DIRTY_BIT {
        names = _suspect_fields(type(arch));
        hashes['__baseline__'] = 0;
    } else {
        names = list(get_field_types(type(arch)).keys());
    }
    for name in names {
        val = getattr(arch, name, None);
        serialized = Serializer._serialize_value(val, include_type=True, _seen=_seen);
        hashes[name] = field_hash(serialized);
    }
    object.__setattr__(arch, '__jac_field_hashes__', hashes);
    if DIRTY_BIT {
        arch.__dict__['__jac_dirty_fields__'] = set();
    }
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
    if DIRTY_BIT {
        touched = arch.__dict__.get('__jac_dirty_fields__');
        if touched {
            dirty |= touched & set(ftypes.keys());
        }
        names = [
            n
            for n in _suspect_fields(type(arch))
            if n not in dirty
        ];
    } else {
        names = list(ftypes.keys());
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
