# Attribution of measured primary database-call RTT

Run after final collection (the helper takes the shared measurement lease):

```sh
python reproduction/webridge/non-snb/profiles/primary-rtt-attribution/analyze.py \
  --results reproduction/webridge/non-snb/results.json \
  --out /home/baichuan/jaseci/reproduction/webridge/non-snb/profiles/primary-rtt-attribution/final
```

The canonical input contains 648 terminal latency cells. Reference rows remain separate and are not added to that keyspace. Without `--results`, the helper reads the three owner publications (native162, TPC-C Java126, littleX Java360). `--allow-incomplete` permits a clearly scoped partial diagnostic. The optional extra-native input exists only for a temporary split publication and duplicate cell keys are rejected.

Selected cases are Payment-by-name GC, full feed at t20/t200, and mixed15 at t20/t200; all available arms and delays are included. Stage failures retain their source evidence and no cost value. Native SQL catalogs use normalized-whitespace 16-character SHA256 IDs; MySQL catalogs use full raw-text SHA256. Both are verified before attribution.

Source-aware native/rtt_sql.category and analyze_mysql_profile.category classify per-request operations. Native category costs match the categories retained in each original request. Category means sum to mean request RTT; primary medians are computed per request. Mixed workloads additionally expose per-operation groups, including feed_page.

A PostgreSQL flight containing multiple executed SQL commands contributes one inclusive `multi_SQL_exchange`. Prepare-only flights have their own category. MySQL CALL costs cover the complete outer response. Detailed nested P_S timings remain secondary. The output preserves exact SQL and its measured exchange costs, catalog/compact trace links, and the original native SQL-category summaries. The concrete SQL table records measured exchange costs.

The helper reads existing compact capture under the shared measurement lease. `attribution.json` contains raw per-request reconciliation; `FINDINGS.md` contains a readable measured table.
