# Research revision notes

The present draft is an implementation and measurement study of the existing
Jac DB code. Its implemented techniques are shape-specific frontier batching,
count/membership lowering, Top-K, projection, and delayed hydration. The
dependency-graph discussion is a proposed next compiler direction.

Priority revisions for a research submission:

1. Define and evaluate the proposed generalization beyond the current pattern
   recognizers. Specify how graph-location transitions, aliases, transaction
   effects, and authorization dependencies enter the region IR.
2. Establish enforceable cardinality and permission contracts for the counting
   rewrite. Its single-creator assumption comes from the measured workload;
   the current syntax matcher does not infer a general schema constraint.
3. Measure controlled per-transformation ablations and optimizer coverage over
   additional programs. Preserve the same physical statistics and runtime
   configuration when comparing code changes.
4. Extend deployment comparisons with aligned database versions/resources,
   multiple clients, more parameters, and larger datasets. The present source
   A/B is controlled within Jac; the cross-system tables retain the original
   heterogeneous deployment choices.
5. Implement and measure selected write-path changes: coalesced access around
   mutations, appropriately invalidated metadata reuse, and configuration
   caching. Existing profiles identify costs; new runs should measure the
   resulting end-to-end benefit.
6. Expand the discussion of TTG integration and compare region lowering with
   stored-procedure synthesis on representative shared workloads. The cited
   TTG paper is separate related work with asynchronous planning/prefetching.
7. Complete authorship, affiliation, target-track, artifact-hosting, and
   publication metadata after the research scope is settled.

The current draft retains the measured write disadvantage and the historical
t20 comparison's provenance. It reports both complete client timing and the
benchmark-specific server timing for bounded pages.
