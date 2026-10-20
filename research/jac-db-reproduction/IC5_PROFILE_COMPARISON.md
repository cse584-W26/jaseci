# IC5 historical versus current stage evidence

The historical final D5 gate records149.7ms for row19. A different historical
row19 diagnostic records19 SQL execute durations totaling89.976ms; the report
attributes a198ms request to that diagnostic. Those are distinct observations.
The available historical files do not decompose the149.7ms gate request.

## Available measurements

| Measurement | Historical final diagnostic | Current full diagnostic (five-request mean) |
|---|---:|---:|
| Client wall time |198ms, stated in REPORT.md|210.174ms|
| Logged execute/statement time |89.976ms,19 events|102.032ms,19 execute events/request|
| Logged bind time |Not retained by historical parser|6.473ms|
| Logged parse time |Not retained by historical parser|No parse duration events recorded|
| Full logged protocol sum |Unavailable|108.505ms|
| Jac application process CPU |Unavailable|94ms|
| Discovered PostgreSQL backend CPU |Unavailable|116ms|
| Client minus execute time |~108.024ms, using report's198ms wall|108.142ms|
| Client minus all logged protocol time |Unavailable|101.669ms|

Current CPU sampling uses10ms ticks and includes process background work.
Protocol durations are wall-time measurements, so they and process CPU are not
independent additive phases. Historical "Python108ms" was a subtraction, not
an application CPU measurement.

## Comparable SQL execution shapes

The historical raw file retains19 execute events. Identifiable shapes allow a
limited statement-level comparison:

| Execute work | Historical diagnostic ms | Current five-request mean ms |
|---|---:|---:|
| First-frontier HasMember fill (`SELECT u.nid, u.eid, u.oid ...`) |39.946|50.125|
| Top-K aggregation (`WITH pr(k,m) ...`) |28.424|23.407|
| Remaining execute events |21.606|28.500|
| All execute events |89.976|102.032|

The recorded fill is~10.179ms longer and the aggregation~5.017ms shorter in the
current samples. Remaining execute work is~6.894ms longer. These observations
describe execution-time differences between those diagnostic requests; they
do not identify why a database operator took longer or shorter.

The historical raw file has blank SQL prefixes on several events, because the
old regex captured only the first line of multiline statements. Their exact
individual shape mapping cannot be recovered from that compact artifact.

## What the artifacts establish about the gap

- The current row19 diagnostic is~210ms, while the historical report's
  diagnostic is198ms. Their~12ms difference accompanies~12ms more logged
  execute time; the client-minus-execute residual is numerically similar.
- The historical149.7ms D5 gate sample has no matching retained per-stage CPU
  or protocol decomposition. Its difference from the current~210ms sample
  cannot be assigned to CPU, bind, execution, transport or cache state from
  the available historical files.
- Historical median75.5ms and current median~109ms describe the distribution
  across parameter rows. A diagnostic of row19 alone does not decompose that
  distribution-level gap.

## Baseline waiting and protocol work

Historical DIAG.md reports~94% sampled stacks in event-loop/psycopg waiting.
That establishes where threads were observed, not the proportion due to
network transport. PostgreSQL planning/protocol work can also leave the
application waiting for its result.

Current retained baseline request00 has45,426 bind events totaling17,486.072ms
and45,426 execute events totaling3,069.384ms:20,555.456ms of logged protocol
work in a~28.9s request. The old duration parser's execute-only regex would
omit the17.486s bind sum. This is evidence against equating the entire
client-minus-execute residual with network time. The historical DIAG used a
stack sampler, so the new result refines its causal interpretation rather than
replacing the historical sample with a measurement it did not collect.

## Sources

- Historical raw diagnostic:
  [durations_row19.txt](../DBHarness/session0904/ic5/build/durations_row19.txt).
- Historical parser:
  [stmt_durations.sh](../DBHarness/session0904/ic5/stmt_durations.sh).
- Historical198ms attribution:
  [REPORT.md](../DBHarness/session0904/ic5/build/REPORT.md).
- Historical149.7ms gate sample:
  [ic5_D5.json](../DBHarness/session0904/ic5/build/gates/ic5_D5.json).
- Historical wait-stack interpretation:
  [DIAG.md](../DBHarness/session0904/ic5/DIAG.md).
- Current full protocol and CPU data:
  [final-full-profile/profile.json](results/final-full-profile/profile.json).
- Current baseline offline protocol totals:
  [protocol-offline-00.json](results/baseline-profile/protocol-offline-00.json).
