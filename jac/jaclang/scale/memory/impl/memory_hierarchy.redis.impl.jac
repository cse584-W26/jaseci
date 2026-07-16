import time;
import from jaclang.scale.runtime.context.tracing { start_memory_span, end_memory_span }

# How long an availability probe result (up OR down) is trusted. A down redis
# costs one TCP connect attempt per window instead of one per request; a redis
# that comes back up is noticed within this window.
glob _REDIS_AVAILABLE_TTL_S: float = 30.0;

def _deserialize_cached(data: dict) -> (Anchor | None) {
    anchor = Serializer.deserialize(data);
    if anchor is not None {
        snapshot_field_hashes(anchor);
    }
    return anchor;
}

impl RedisBackend.postinit -> None {
    if self.redis_url is None {
        self.redis_url = _get_db_config().get('redis_url');
    }
    if not self.redis_url {
        return;
    }
    if 'redis_client' not in _process_cache {
        try {
            db_config = _get_db_config();
            max_connections = db_config.get('redis_max_connections', 20);
            _process_cache['redis_client'] = redis.from_url(
                self.redis_url, max_connections=max_connections
            );
        } except Exception as e {
            logger.warning(f"Redis connection failed: {e}");
        }
    }
    self.redis_client = _process_cache.get('redis_client');
}

impl RedisBackend.is_available -> bool {
    if self.redis_client is None {
        return False;
    }
    now = time.monotonic();
    cached = _process_cache.get('redis_available');
    checked_at = _process_cache.get('redis_available_at');
    if cached is not None
    and checked_at is not None
    and (now - checked_at) < _REDIS_AVAILABLE_TTL_S {
        return bool(cached);
    }
    available = False;
    try {
        self.redis_client.ping();
        available = True;
    } except Exception as e {
        logger.debug(f"Redis availability check failed: {e}");
    }
    _process_cache['redis_available'] = available;
    _process_cache['redis_available_at'] = now;
    return available;
}

impl RedisBackend.get(id: UUID) -> (Anchor | None) {
    if self.redis_client is None {
        return None;
    }
    self.fetch_count += 1;
    key = storage_key(to_uuid(id));
    span = start_memory_span(
        "memory.get redis", {"db.system": "redis", "mem.tier": "L2", "mem.op": "get"}
    );
    try {
        raw = self.redis_client.get(key);
        if not raw {
            return None;
        }
        data = json.loads(raw);
        return _deserialize_cached(data);
    } except Exception as e {
        logger.debug(f"Redis get failed: {e}");
        return None;
    } finally {
        end_memory_span(span);
    }
}

impl RedisBackend.reset_counters -> None {
    self.fetch_count = 0;
    self.put_count = 0;
}

impl RedisBackend.put(anchor: Anchor) -> None {
    if self.redis_client is None {
        return;
    }
    self.put_count += 1;
    span = start_memory_span(
        "memory.put redis", {"db.system": "redis", "mem.tier": "L2", "mem.op": "put"}
    );
    try {
        data = Serializer.serialize(anchor, include_type=True);
        key = storage_key(anchor.id);

        db_config = _get_db_config();
        ttl = db_config.get('redis_default_ttl', 0);

        if ttl > 0 {
            self.redis_client.setex(key, ttl, json.dumps(data));
            logger.debug(f"Stored anchor {anchor.id} in Redis with TTL={ttl}s");
        } else {
            self.redis_client.set(key, json.dumps(data));
        }
    } except Exception as e {
        logger.debug(f"Redis put failed: {e}");
    } finally {
        end_memory_span(span);
    }
}

impl RedisBackend.batch_put(anchors: list[Anchor]) -> None {
    # Single pipelined round-trip for the whole batch, with one span for the
    # batch instead of per-anchor. This is the hot path when a query
    # materializes many rows into L2; per-anchor `put` there is dominated by
    # Redis round-trip + tracing overhead.
    if self.redis_client is None or not anchors {
        return;
    }
    span = start_memory_span(
        "memory.batch_put redis",
        {"db.system": "redis", "mem.tier": "L2", "mem.op": "batch_put"}
    );
    try {
        ttl = _get_db_config().get('redis_default_ttl', 0);
        pipe = self.redis_client.pipeline(transaction=False);
        for anchor in anchors {
            payload = json.dumps(Serializer.serialize(anchor, include_type=True));
            key = storage_key(anchor.id);
            if ttl > 0 {
                pipe.setex(key, ttl, payload);
            } else {
                pipe.set(key, payload);
            }
        }
        pipe.execute();
        self.put_count += len(anchors);
    } except Exception as e {
        logger.debug(f"Redis batch_put failed: {e}");
    } finally {
        end_memory_span(span);
    }
}

impl RedisBackend.delete(id: UUID) -> None {
    if self.redis_client is None {
        return;
    }
    try {
        key = storage_key(to_uuid(id));
        self.redis_client.delete(key);
    } except Exception as e {
        logger.debug(f"Redis delete failed: {e}");
    }
}

impl RedisBackend.close -> None {
    self.redis_client = None;
}

impl RedisBackend.`has(id: UUID) -> bool {
    return self.exists(id);
}

impl RedisBackend.query(
    filter: (Callable[[Anchor], bool] | None) = None
) -> Generator[Anchor, None, None] {
    return;
    yield ;
}

impl RedisBackend.get_roots -> Generator[Root, None, None] {
    return;
    yield ;
}

impl RedisBackend.commit(anchor: (Anchor | None) = None) -> None { }

impl RedisBackend.batch_get(ids: list[UUID]) -> dict[UUID, Anchor] {
    result: dict[UUID, Anchor] = {};
    if not ids or self.redis_client is None {
        return result;
    }
    self.fetch_count += len(ids);
    span = start_memory_span(
        "memory.batch_get redis",
        {
            "db.system": "redis",
            "mem.tier": "L2",
            "mem.op": "batch_get",
            "mem.count": len(ids)
        }
    );
    try {
        keys = [storage_key(to_uuid(id)) for id in ids];
        values = self.redis_client.mget(keys);
        for (id, raw) in zip(ids, values) {
            if raw {
                try {
                    data = json.loads(raw);
                    anchor = _deserialize_cached(data);
                    if anchor {
                        result[id] = anchor;
                    }
                } except Exception as e {
                    logger.debug(f"Redis batch_get deserialize failed for {id}: {e}");
                }
            }
        }
    } except Exception as e {
        logger.debug(f"Redis batch_get failed: {e}");
    } finally {
        end_memory_span(span);
    }
    return result;
}

impl RedisBackend.exists(id: UUID) -> bool {
    if self.redis_client is None {
        return False;
    }
    try {
        key = storage_key(to_uuid(id));
        return bool(self.redis_client.exists(key));
    } except Exception {
        return False;
    }
}

impl RedisBackend.put_if_exists(anchor: Anchor) -> bool {
    if self.redis_client is None {
        return False;
    }
    if not self.exists(anchor.id) {
        return False;
    }
    self.put(anchor);
    return True;
}

impl RedisBackend.invalidate(id: UUID) -> None {
    self.delete(id);
}

impl RedisBackend.publish_invalidation(
    anchor_id: str, origin_l1_id: (str | None) = None
) -> None {
    if self.redis_client is None {
        return;
    }
    try {
        db_config = _get_db_config();
        if not db_config.get('redis_l1_invalidation_enabled', True) {
            return;
        }
        channel = (
            db_config.get('redis_l1_invalidation_channel')
            or DEFAULT_INVALIDATION_CHANNEL
        );
        self.redis_client.publish(channel, build_message(anchor_id, origin_l1_id));
    } except Exception as e {
        logger.debug(f"Redis publish_invalidation failed: {e}");
    }
}

impl RedisBackend.aget(id: UUID) -> (Anchor | None) {
    import from jaclang.scale._optdeps.redis { AsyncRedis, HAS_REDIS }
    if not HAS_REDIS or AsyncRedis is None {
        return await super.aget(id);
    }
    if self._async_redis is None {
        if self.redis_url is None {
            return await super.aget(id);
        }
        self._async_redis = AsyncRedis.from_url(self.redis_url);
    }
    key = storage_key(to_uuid(id));
    span = start_memory_span(
        "memory.get redis", {"db.system": "redis", "mem.tier": "L2", "mem.op": "get"}
    );
    try {
        raw = await self._async_redis.get(key);
        if not raw {
            return None;
        }
        data = json.loads(raw);
        return _deserialize_cached(data);
    } except Exception as e {
        logger.debug(f"Redis async get failed: {e}");
        return None;
    } finally {
        end_memory_span(span);
    }
}

impl RedisBackend.aput(anchor: Anchor) -> None {
    import from jaclang.scale._optdeps.redis { AsyncRedis, HAS_REDIS }
    if not HAS_REDIS or AsyncRedis is None {
        await super.aput(anchor);
        return;
    }
    if self._async_redis is None {
        if self.redis_url is None {
            await super.aput(anchor);
            return;
        }
        self._async_redis = AsyncRedis.from_url(self.redis_url);
    }
    span = start_memory_span(
        "memory.put redis", {"db.system": "redis", "mem.tier": "L2", "mem.op": "put"}
    );
    try {
        data = Serializer.serialize(anchor, include_type=True);
        key = storage_key(anchor.id);
        db_config = _get_db_config();
        ttl = db_config.get('redis_default_ttl', 0);
        if ttl > 0 {
            await self._async_redis.setex(key, ttl, json.dumps(data));
        } else {
            await self._async_redis.set(key, json.dumps(data));
        }
    } except Exception as e {
        logger.debug(f"Redis async put failed: {e}");
    } finally {
        end_memory_span(span);
    }
}
