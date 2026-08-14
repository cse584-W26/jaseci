"""StreamNode: proof-gated stand-in for a materialized node archetype.

Handed out by the query planner ONLY inside walkers that StreamProofPass
approved (`__jac_stream_fields__` on the walker class): the compiler proved
every observation of chain results is an anchor-id read (`jid`), a scalar
field read, list plumbing, or final serialization - all of which this object
serves straight from the stored props dict without constructing the
archetype, its Permission blobs, or its edge stubs.

Field reads are value-identical to the materialized path: scalars pass
through untouched; anything nested goes through the same
Serializer._deserialize_value the real deserializer would have applied.
Mutation is impossible by proof; __setattr__ raises loudly so an analysis
bug surfaces as a crash in testing, never as a silently dropped write.
"""
import from typing { Any }


class StreamNode {
    def __init__(
        self: StreamNode, props: dict, anchor: Any, frag: (str | None) = None
    ) {
        d = self.__dict__;
        d['_sn_props'] = props;
        d['__jac__'] = anchor;
        if frag is not None {
            # mirror-backed: props holds only the walker's PROVEN field set
            # and _sn_frag carries the prebuilt api response fragment text
            d['_sn_frag'] = frag;
        }
    }

    def __getattr__(self: StreamNode, name: str) -> Any {
        props = self.__dict__['_sn_props'];
        if name not in props and '_sn_frag' in self.__dict__ {
            # mirror-backed nodes carry only the PROVEN field set eagerly,
            # but the fragment text holds every field: a read outside the
            # proof (e.g. a comprehension the pass approved via the report
            # sink) lazily inflates it once instead of failing
            import json;
            full = json.loads(self.__dict__['_sn_frag']);
            for (k, v) in full.items() {
                if not k.startswith('_jac_') and k not in props {
                    props[k] = v;
                }
            }
        }
        if name in props {
            v = props[name];
            if v is None or type(v) in (str, int, float, bool) {
                return v;
            }
            import from jaclang.runtimelib.serializer { Serializer }
            return Serializer._deserialize_value(v);
        }
        raise AttributeError(name);
    }

    def __setattr__(self: StreamNode, name: str, value: Any) -> None {
        raise TypeError(
            f"StreamNode is read-only (attempted write to {name!r}). The "
            "stream proof forbids mutation of chain results in this walker; "
            "if user code legitimately reaches this, it is a StreamProofPass "
            "bug - please report it."
        );
    }

    def __jac_access__(self: StreamNode) -> Any {
        # Archetype's default custom-access hook returns None. _try_stream
        # refuses to stream any class that OVERRIDES the hook, so the default
        # is always the right answer here.
        return None;
    }

    def __repr__(self: StreamNode) -> str {
        an = self.__dict__.get('__jac__');
        t = an.__dict__.get('_sn_arch_type', 'node') if an is not None else 'node';
        return f"{t}()";
    }
}
