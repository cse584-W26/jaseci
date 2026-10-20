#!/usr/bin/env bash
set -euo pipefail
alignment_dir=$(cd -- "$(dirname -- "$0")" && pwd)
container_name=jac-webridge-mysql57
# All mutations are confined to the new jac_alignment database.
docker cp "$alignment_dir/schema.sql" "$container_name:/tmp/jac-alignment-schema.sql"
docker cp "$alignment_dir/graph-fixture" "$container_name:/tmp/jac-alignment-graph"
docker exec "$container_name" mysql -uroot -e 'SOURCE /tmp/jac-alignment-schema.sql;'
docker exec "$container_name" mysql --local-infile=1 -uroot jac_alignment -e "LOAD DATA LOCAL INFILE '/tmp/jac-alignment-graph/anchors.tsv' INTO TABLE anchors CHARACTER SET utf8mb4; LOAD DATA LOCAL INFILE '/tmp/jac-alignment-graph/graph_types.tsv' INTO TABLE graph_types CHARACTER SET utf8mb4; LOAD DATA LOCAL INFILE '/tmp/jac-alignment-graph/identity_users.tsv' INTO TABLE identity_users CHARACTER SET utf8mb4; LOAD DATA LOCAL INFILE '/tmp/jac-alignment-graph/kv_state.tsv' INTO TABLE kv_state CHARACTER SET utf8mb4; ANALYZE TABLE anchors,graph_types,identity_users,kv_state; SELECT 'anchors',count(*) FROM anchors UNION ALL SELECT 'graph_types',count(*) FROM graph_types UNION ALL SELECT 'identity_users',count(*) FROM identity_users;"
