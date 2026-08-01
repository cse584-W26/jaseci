import sys;
import from dataclasses { fields, is_dataclass }
import from typing { cast }

glob _cache: dict[type, dict[str, object]] = {},
     _names_cache: dict[type, tuple] = {};

def _resolve_hints(cls: type) -> dict[str, object] {
    hints: dict[str, object] = {};
    for base in reversed(cls.__mro__) {
        ann = cast(dict[str, object], getattr(base, '__annotations__', {}) or {});
        if not ann {
            continue;
        }
        mod = sys.modules.get(base.__module__);
        globalns = cast(dict[str, object], mod?.__dict__ or {});
        localns = cast(dict[str, object], dict(vars(base)));
        for (name, value) in ann.items() {
            if isinstance(value, str) {
                try {
                    value = eval(value, globalns, localns);
                } except Exception {
                    ;
                }
            }
            hints[name] = value;
        }
    }
    return hints;
}

def _collect(cls: type) -> dict[str, object] {
    hints = _resolve_hints(cls);
    out: dict[str, object] = {};
    for f in fields(cls) {
        if f.name in hints {
            out[f.name] = hints[f.name];
        }
    }
    return out;
}

def _is_complete(cls: type, out: dict[str, object]) -> bool {
    for f in fields(cls) {
        if f.name not in out or isinstance(out.get(f.name), str) {
            return False;
        }
    }
    return True;
}

impl get_field_types(cls: type) -> dict[str, object] {
    if (cached := _cache.get(cls)) is not None {
        return cached;
    }
    if not is_dataclass(cls) {
        _cache[cls] = {};
        return {};
    }
    out = _collect(cls);
    if _is_complete(cls, out) {
        _cache[cls] = out;
    }
    return out;
}

impl warm(cls: type) -> None {
    if cls in _cache or not is_dataclass(cls) {
        return;
    }
    out = _collect(cls);
    if _is_complete(cls, out) {
        _cache[cls] = out;
    }
}

impl field_names(cls: type) -> tuple {
    if (cached := _names_cache.get(cls)) is not None {
        return cached;
    }
    names = tuple(
        f.name
        for f in fields(cls)
        if not f.name.startswith('_')
    )
        if is_dataclass(cls)
        else ();
    _names_cache[cls] = names;
    return names;
}

glob _plan_cache: dict[type, tuple] = {};

# emit_plan kinds: 0 = full dispatch, 1 = scalar (str/int/float/bool/None),
# 2 = list of scalars. Classification is static (declared types); every
# fast path re-guards at runtime and falls back to dispatch, so a field
# holding a surprise value still serializes byte-identically.
glob _SCALARS: tuple = (str, int, float, bool);


def _classify(hint: object) -> int {
    import from typing { get_args, get_origin, Union }
    import from types { NoneType, UnionType }
    if hint in (str, int, float, bool) {
        return 1;
    }
    origin = get_origin(hint);
    if origin in (Union, UnionType) {
        args = set(get_args(hint));
        args.discard(NoneType);
        if args and all(a in (str, int, float, bool) for a in args) {
            return 1;
        }
        return 0;
    }
    if origin is list {
        args = get_args(hint);
        if len(args) == 1 and args[0] in (str, int, float, bool) {
            return 2;
        }
    }
    return 0;
}


impl emit_plan(cls: type) -> tuple {
    if (cached := _plan_cache.get(cls)) is not None {
        return cached;
    }
    names = field_names(cls);
    if not names {
        _plan_cache[cls] = ();
        return ();
    }
    types_map = get_field_types(cls);
    plan = tuple(
        (n, _classify(types_map.get(n)) if n in types_map else 0)
        for n in names
    );
    _plan_cache[cls] = plan;
    return plan;
}


impl invalidate(cls: type) -> None {
    _cache.pop(cls, None);
    _names_cache.pop(cls, None);
    _plan_cache.pop(cls, None);
}

impl clear -> None {
    _cache.clear();
    _names_cache.clear();
    _plan_cache.clear();
}
