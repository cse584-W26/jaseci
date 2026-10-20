# Independent formal-pair and fallback audit

Both original-driver arms pass the independent raw-data validator. Original has 23,748 successful timed samples; WeBridge has 68,647. Both warmups last exactly 300.000 seconds; measurement-to-stop intervals are 600.008 and 600.006 seconds. Every API's overall and per-period P50/P90/P99 matches the original integer order-statistic definition exactly. Per-period throughput also matches the raw counts. The original driver's CSV omits the last period from throughput even when raw samples span ten periods; validation preserves that definition.

| API | Original N | WeBridge N | Original P50 ms | WeBridge P50 ms |
|---|---:|---:|---:|---:|
| GI | 7,871 | 22,907 | 24.148246 | 10.564202 |
| BD | 7,828 | 22,842 | 17.622282 | 5.855443 |
| EB | 8,049 | 22,898 | 27.247385 | 8.869907 |

[Independent validation](independent-validation.json), [timing and SQL figure PDF](timing-sql.pdf), [PNG](timing-sql.png), [SQL classification audit](sql-classification-independent.json).

## SQL boundaries

Across all three captured requests per API per arm, top-level business commands excluding separately recorded SELECT 1 connection tests decrease from GI/BD/EB 7/6/10 to 1/1/2 CALLs. Independently recounted application-table operations remain 7/6/7 in both arms. The latter counts direct table SQL plus executed cursor opens whose retained declarations select application tables. Internal result-serialization SELECTs, transaction SQL, savepoints and SP control events remain separate. These counts describe the captured blog3 path, with the blog4 alternate path analyzed below.

## Observed alternate path

The WeBridge server log records four warmup and five timed GetBlog WrongSQL fallbacks. Every event concerns blog ID 4. The five timed events constitute 5/22,842 = 0.02189% of timed BD samples and remain included in the reported distribution. The original HTTP driver reports zero request errors; server fallback events are reported separately from HTTP failures.

The cause follows directly from source, generated SQL and retained data. BlogServiceImpl.getBlogDetailVO obtains a comment count. CommentServiceImpl.getCommentPageByBlogIdAndPageNum then lists comments and, when the list is nonempty, obtains the count again. The generated no-comment trace contains only the first count, then comment-list query, then configuration SELECT. The fixture retains exactly one visible comment: comment 26 on blog 4. On that path the additional incoming count encounters the buffered configuration SELECT. SQL-template validation rejects the mismatch and executes subsequent queries normally. The mismatch labels describe the incoming versus buffered SQL templates; they do not imply the count result was silently replaced with configuration data.

[Reproducible log/source/read-only DB analysis](fallback-independent.json) retains exact event times, line numbers, table-state counts and code paths. `paper-audit/analyze_fallback.py` reconstructs it without application requests.

## Postformal semantic check

The separate [blog4 probe receipt](../postformal-blog4-20261020T185432/receipt.json) preserves the postformal database state before any probes. `paper-audit/postformal_blog4.py` starts the original normal and optimized applications sequentially and issues only GET requests to blog4: eight warm plus three measured requests per arm. These requests are separate from formal timing and its samples.

All six measured responses render the same title and original comment 26, and display one comment. Each measured request executes exactly one UPDATE tb_blog and increases views by exactly one. Including warmups, each arm increases views by eleven. All six complete HTML responses are identical after replacing only the displayed view count; the normalized SHA and original HTML files are retained. Thus the observed fallback does not repeat the earlier view UPDATE. Settings restoration passes for both arms, and the online service is stopped afterward. The probes add twenty-two views without changing post content or the retained comment.

The formal experiment uses the paper's duration, original applications/driver and separately documented input repairs. It remains a single-host reproduction with CPU affinity and measured network emulation, rather than the paper's separate machines. Equal API probability is specified for the paper's throughput results; equal mixed driving for per-API latency is an explicit reproduction choice. No peak-throughput conclusion follows from this one-client pair.
