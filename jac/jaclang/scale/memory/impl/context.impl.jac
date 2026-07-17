impl JScaleExecutionContext.init(self: JScaleExecutionContext) -> None {
    import from jaclang.scale.memory.memory_hierarchy {
        ScaleTieredMemory,
        acquire_scale_mem,
        _process_cache
    }
    import from jaclang.jac0core.constructs {
        Anchor,
        NodeAnchor,
        PermissionDenied,
        Root
    }

    # acquire_scale_mem() reuses a pooled instance when JAC_MEM_POOL is on,
    # else constructs a fresh ScaleTieredMemory (byte-identical to before).
    self.mem = acquire_scale_mem();
    self.reports: list[any] = [];
    self.diagnostics: list[PermissionDenied] = [];
    self.pending_effects = [];
    self.read_versions = {};
    self.custom: any = MISSING;
    cached_root = _process_cache.get('system_root');
    if cached_root is not None {
        self.mem.__mem__[cached_root.id] = cached_root;
    }
    system_root_anchor: (Anchor | None) = self.mem.get(UUID(Con.SUPER_ROOT_UUID));
    if not isinstance(system_root_anchor, NodeAnchor) {
        system_root_anchor = Root().__jac__;
        system_root_anchor.id = UUID(Con.SUPER_ROOT_UUID);
        self.mem.put(system_root_anchor);
    }
    _process_cache['system_root'] = system_root_anchor;
    self.system_root = system_root_anchor;

    self.user_root = self.system_root;
    self.entry_node = self.system_root;
    self.call_state: ContextVar[CallState] = ContextVar('call_state');
}
