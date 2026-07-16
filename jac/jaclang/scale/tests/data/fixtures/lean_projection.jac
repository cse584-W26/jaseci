"""Server fixture for the LEAN x PROJECTION composition test.

`projected_report` builds a standalone node directly against a
PostgresRelBackend (bypassing the request's own graph/mem entirely -- same
technique scale/tests/data/test_postgres_rel_backend.jac uses), fetches it
back through `execute_plan` with a declared projection so the returned
anchor carries a REAL `_projected_fields` marker set by
`Serializer.deserialize_projected` (never manually stamped), then reports
the projected archetype. This drives the real lean-response + Serializer
pipeline over a genuinely projection-fetched node, over the SAME
`JacTestClient` HTTP-mocked path `test_lean_response.jac` uses.
"""

import os;
import psycopg;
import from jaclang.jac0core.archetype { Root }
import from jaclang.runtimelib.changeset { ChangeSet }
import from jaclang.runtimelib.query_plan { QueryPlan }
import from jaclang.scale.memory.memory_hierarchy { PostgresRelBackend }

glob _REL_DSN = os.environ.get('POSTGRESQL_REL_URI', 'postgresql:///jactest_rel');

node ProjItem {
    has name: str = "",
        age: int = 0;
}

walker:priv projected_report {
    has reports: list = [];

    can run with Root entry {
        be: any = PostgresRelBackend(dsn=_REL_DSN, pool_min=1, pool_max=2);
        raw: any = psycopg.connect(_REL_DSN, autocommit=True);
        raw.execute("TRUNCATE anchors, anchors_quarantine, aliases");
        raw.execute("TRUNCATE edges RESTART IDENTITY");
        raw.close();

        r: any = Root();
        ra: any = r.__jac__;
        ra.persistent = True;
        setattr(ra, 'root', ra.id);

        p: any = ProjItem(name="ann", age=42);
        pa: any = p.__jac__;
        pa.persistent = True;
        setattr(pa, 'root', ra.id);

        cs: any = ChangeSet();
        cs.record_create(ra);
        cs.record_create(pa);
        rep: any = be.apply(cs);
        assert not rep.failed;

        plan: any = QueryPlan(
            id_in={pa.id}, node_type_final="ProjItem", projection={"name"}
        );
        results: any = list(be.execute_plan(plan));
        assert len(results) == 1;
        slim: any = results[0];
        be.close();

        report {"feed": [slim.archetype]};
    }
}
