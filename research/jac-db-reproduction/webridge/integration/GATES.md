# Full-request compatibility gates

Both compatibility derivatives preserve the original full Jac-aligned request's
results, submitted SQL counts, per-query categories and cold/warm memo behavior.
Each gate evaluates all20 original inputs in order, followed by input0 again in
the same process. No capture or stored procedure is enabled in either gate.

| Derivative | Requests | Cold20 SQL | Warmrepeat SQL | Result/count/category checks |
|---|---:|---:|---:|---|
| Explicit typed JDBC access |21|278773|24|All pass|
| Explicit body API boundary, no-op hooks |21|278773|24|All pass|

Receipts and raw request logs:

- `cases/all20-typed-gate-20261020/gate-20261020T185145672666Z/gate-verification.json`
- `cases/all20-region-noop-gate-20261020/gate-20261020T185335504458Z/gate-verification.json`

The reference is `../alignment/alignment-gate.json`, independently validated
against the Jac request's graph and response oracle. These gates establish
semantic/count alignment of the adapters; actual WeBridge capture, compilation
and invocation are separate measured stages.
