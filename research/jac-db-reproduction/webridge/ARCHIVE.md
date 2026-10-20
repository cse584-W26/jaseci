# WeBridge and Jac comparison archive

Start with [the complete eight-configuration experiments](roundtrip-comparison/REPORT.md), [English PDF](roundtrip-comparison/jac-webridge-measured-comparison.pdf), and [complete experimental results](RESULTS.md).

This archive includes the conventional Java SQL baseline, original-Jac and final-Jac matched-data experiments, full/pruned Java and WeBridge measurements, raw per-request rows, correctness gates, calibrated database round trips, SQL traces, execution plans, profiling reports and cleanup receipts. It also retains the completed original WeBridge My-Blog paper reproduction and the baseline-alignment evidence supporting the comparison.

Collection workspace: `/home/baichuan/jaseci/reproduction/webridge`. Scripts retain that deployment's repository locations, dependencies and dedicated database settings. Source revisions, commands, compatibility changes and dataset checksums identify those inputs. [Measurement protocol](latency-comparison/PROTOCOL.md) describes the delay mechanism and timing boundaries.

`archive-manifest.json` records SHA256 and size for each copied artifact. Installed toolchains, dependencies, database volumes, the anchor data export, application caches/tokens, binary graph recordings and full-scale multi-gigabyte graph/resource artifacts remain in the collection workspace. Files over 2 MB are listed as omitted within selected archive trees. Reports retain their original collection-relative evidence paths; the manifest identifies copied versus locally retained evidence.

The raw rows supporting every eight-configuration latency cell and the payload-free protocol evidence supporting each SQL/roundtrip map are included. Native PostgreSQL frame payloads remain local; `jac-comparison/roundtrip-profile/PUBLIC_FILES.json` identifies the public, independently reproducible evidence. From this archive directory:

```sh
python roundtrip-comparison/verify_eight_arms.py
python roundtrip-comparison/audit_operation_map.py
python roundtrip-comparison/build_pdf.py
python jac-comparison/roundtrip-profile/analyze.py
python alignment/idiomatic/verify_webridge.py
python latency-comparison/analyze.py
python latency-comparison/combine.py
python latency-comparison/render.py
python alignment/idiomatic/verify.py
```

The verification commands check counts, exact expected results, SQL operations and protocol synchronization from included evidence; the build/render commands generate the English PDFs and plots from verified data. `combine.py` updates the generation timestamp in its output. Matplotlib is required only for rendering. Live benchmark reruns require the pinned Java/Jac dependencies and matched database fixtures described in the source protocols.
