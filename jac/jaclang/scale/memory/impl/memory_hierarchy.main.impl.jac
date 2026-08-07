impl ScaleTieredMemory.postinit -> None {
    import threading;
    self.__mem__ = {};

    self.changes = ChangeSet();
    self._commit_lock = threading.RLock();

    self._l1_id = new_l1_id();
    register_l1(self._l1_id, self);

    redis_backend = RedisBackend();
    self._cache_available = redis_backend.is_available();
    if self._cache_available and self.use_cache {
        self.l2 = redis_backend;
        logger.debug("Redis cache backend initialized");

        try {
            db_config = get_scale_config().get_database_config();
            if db_config.get('redis_l1_invalidation_enabled', True) {
                ensure_listener(
                    _process_cache,
                    cast((str | None), db_config.get('redis_url')),
                    cast(
                        str,
                        db_config.get('redis_l1_invalidation_channel')
                            or DEFAULT_INVALIDATION_CHANNEL
                    )
                );
            }
        } except Exception as e {
            logger.debug(f"L1 invalidation listener init skipped: {e}");
        }
    } else {
        self.l2 = None;
        logger.debug("Redis not available, running without distributed cache");
    }

    hooked_l3 = None;
    try {
        import from jaclang { JacRuntimeInterface as Jac }
        hooked_l3 = Jac.get_persistent_memory(
            {'base_path': self.base_path, 'target_path': self.target_path}
        );
    } except Exception as e {
        logger.debug(f"get_persistent_memory hook failed: {e}");
    }
    if hooked_l3 is not None {
        self.l3 = hooked_l3;
        if isinstance(hooked_l3, MongoBackend) {
            hooked_l3.set_cache_ref(self.l2);
            hooked_l3.set_l1_id(self._l1_id);
            self._persistence_type = PersistenceType.MONGODB;
        } else {
            self._persistence_type = PersistenceType.SQLITE;
        }
        logger.debug("Using get_persistent_memory plugin backend for persistence");
    } elif (mongo_backend := MongoBackend()).is_available() {
        self.l3 = mongo_backend;
        mongo_backend.set_cache_ref(self.l2);
        mongo_backend.set_l1_id(self._l1_id);
        self._persistence_type = PersistenceType.MONGODB;
        logger.debug("MongoDB persistence backend initialized");
        try {
            import from jaclang.cli.console { console }
            logger.debug("  ✔ Using MongoDB for persistence", style="muted");
        } except Exception { }
    } else {
        self.l3 = SqliteMemory(
            path=get_scale_config().get_database_config()['shelf_db_path']
        );
        self._persistence_type = PersistenceType.SQLITE;
        logger.debug("MongoDB not available, using SqliteMemory for persistence");
        try {
            import from jaclang.cli.console { console }
            logger.debug("  ✔ Using SQLite for persistence", style="muted");
        } except Exception { }
    }
}


impl ScaleTieredMemory._mark_committed(anchor: (Anchor | None)) -> None {
    if anchor is None {
        self._committed = True;
    }
}

impl ScaleTieredMemory.put(anchor: Anchor) -> None {
    self._committed = False;
    super.put(anchor);
}

impl ScaleTieredMemory.commit(anchor: (Anchor | None) = None) -> None {
    self._committed = False;
    if self.l3 is None {
        self.changes.clear();
        self._mark_committed(anchor);
        return;
    }
    # Concurrent request commits share this store and self.changes; an
    # unserialized collect/apply/clear interleaving lets one request's clear()
    # wipe another request's freshly collected intents before they are applied
    # (acked write, nothing in L3 - silent loss). ponytail: one commit lock per
    # store; per-anchor locking is the upgrade path if commit throughput ever
    # matters.
    with self._commit_lock {
        self._collect_into(self.changes);
        if self.changes.is_empty() {
            self._mark_committed(anchor);
            return;
        }

        self_broadcasting: set = set();
        if isinstance(self.l3, MongoBackend) {
            self_broadcasting = {
                intent.anchor.id
                for intent in self.changes.intents.values()
                if intent.op == WriteOp.EDGE_LIST_DELTA
            };
        }
        apply_report = self.l3.apply(self.changes);
        if self.l2 {
            applied = set(apply_report.applied);
            for intent in list(self.changes.intents.values()) {
                if intent.anchor.id not in applied {
                    continue;
                }
                try {
                    if intent.is_delete() {
                        self.l2.invalidate(intent.anchor.id);
                        cast(RedisBackend, self.l2).publish_invalidation(
                            str(intent.anchor.id), self._l1_id
                        );
                    } elif intent.anchor.id not in self_broadcasting {
                        self.l2.put(intent.anchor);
                        cast(RedisBackend, self.l2).publish_invalidation(
                            str(intent.anchor.id), self._l1_id
                        );
                    }
                } except Exception as l2_err {
                    logger.warning(f"L2 cache update failed: {l2_err}");
                }
            }
        }
        self._post_apply(apply_report);
        self.changes.clear();

        if (conflict := apply_report.primary_conflict()) {
            raise conflict;
        }
        self._mark_committed(anchor);
    }
}

# Same contract as runtimelib.memory._note_touched: every anchor handed to a
# request must land in the per-request touched registry or the request-scoped
# commit scan will never see writes to it (silent write loss).
def _note_touched_scale(anchor: Anchor) {
    import from jaclang { JacRuntimeInterface as Jac }
    try {
        Jac.get_context().touched[anchor.id] = anchor;
    } except Exception {
        ;
    }
}

impl ScaleTieredMemory.batch_get(
    ids: list[UUID], projection: (tuple | None) = None
) -> dict[UUID, Anchor] {
    result: dict[UUID, Anchor] = {};
    l1_misses: list[UUID] = [];
    wanted = projection[0] if projection is not None else None;
    for id in ids {
        self._refresh_if_stale(id);
        if (anchor := self.__mem__.get(id)) {
            pf = anchor.__dict__.get('_projected_fields');
            if pf is not None and (wanted is None or not (wanted <= pf)) {
                # Cached copy is a projection that doesn't cover this request
                # (full read, or a wider field set): refetch and replace.
                self.__mem__.pop(id, None);
                l1_misses.append(id);
                continue;
            }
            _note_touched_scale(anchor);
            result[id] = anchor;
        } else {
            l1_misses.append(id);
        }
    }
    if not l1_misses {
        return result;
    }

    l2_misses: list[UUID] = [];
    if self.l2 and hasattr(self.l2, 'batch_get') {
        l2_results = self.l2.batch_get(l1_misses);
        for id in l1_misses {
            if id in l2_results {
                anchor = l2_results[id];
                self.__mem__[id] = anchor;
                _note_touched_scale(anchor);
                result[id] = anchor;
            } else {
                l2_misses.append(id);
            }
        }
    } else {
        l2_misses = l1_misses;
    }

    if l2_misses and self.l3 {
        l3_results: dict[UUID, Anchor] = {};
        projected_fetch = projection is not None and isinstance(self.l3, MongoBackend);
        if projected_fetch {
            l3_results = self.l3.batch_get(l2_misses, projection);
        } elif hasattr(self.l3, 'batch_get') {
            l3_results = self.l3.batch_get(l2_misses);
        } else {
            for mid in l2_misses {
                if (a := self.l3.get(mid)) {
                    l3_results[mid] = a;
                }
            }
        }
        for (id, anchor) in l3_results.items() {
            if projected_fetch {
                # Mark the subset load and keep it out of L2: the shared cache
                # must only ever hold full anchors.
                anchor.__dict__['_projected_fields'] = wanted;
            }
            self.__mem__[id] = anchor;
            _note_touched_scale(anchor);
            if self.l2 and not projected_fetch {
                try {
                    self.l2.put(anchor);
                } except Exception { }
            }
            result[id] = anchor;
        }
    }
    return result;
}

impl ScaleTieredMemory.acommit(anchor: (Anchor | None) = None) -> None {
    import asyncio;
    # No `self._committed` skip here: the flag is instance-wide on a store
    # shared by every in-flight request, while the commit scan is scoped to
    # the CURRENT request's touched anchors. Another request's commit
    # completing between this request's writes and this acommit would flip the
    # flag and make this request silently skip committing its own acked
    # writes (they linger dirty in L1 until unrelated later traffic touches
    # the same anchors - or are lost for good).
    await asyncio.to_thread(self.commit, anchor);
    if anchor is None {
        self._committed = True;
    }
}

impl ScaleTieredMemory.close -> None {
    try {
        if not self._committed {
            self.commit();
        }
    } finally {
        if self.l3 {
            self.l3.close();
        }
        if self.l2 {
            self.l2.close();
        }

        if self._l1_id {
            deregister_l1(self._l1_id);
        }
        self.__mem__.clear();
        self.changes.clear();
    }
}

impl ScaleTieredMemory._refresh_if_stale(id: UUID) -> None {
    if consume_stale(self._l1_id, id) {
        existing = self.__mem__.get(id);
        if existing is not None
            and existing.persistent
            and Serializer._compute_hash(existing) == existing.hash {
            self.__mem__.pop(id, None);
        }
    }
}

impl ScaleTieredMemory.get(id: UUID) -> (Anchor | None) {
    self._refresh_if_stale(id);
    return super.get(id);
}

impl ScaleTieredMemory.query(
    filter: (Callable[[Anchor], bool] | None) = None
) -> Generator[Anchor, None, None] {
    for anchor in list(self.__mem__.values()) {
        if filter is None or filter(anchor) {
            _note_touched_scale(anchor);
            yield anchor;
        }
    }
}
