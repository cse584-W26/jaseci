#!/usr/bin/env python3
"""Write the English evidence guide from the completed primary RTT matrix."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
source = ROOT / 'results.json'
data = json.loads(source.read_text())
assert data['metric'] == 'rtt'
assert data['coverage']['terminal_cells'] == 648 and data['coverage']['pending_cells'] == 0
assert len(data['references']) == 168

arms = {
    'jac_original': 'Jac unoptimized', 'jac_final': 'Jac optimized',
    'java_full': 'Jac-like Java, direct', 'webridge_full': 'WeBridge, Jac-like Java',
    'java_conventional': 'Original SQL Java, direct', 'webridge_conventional': 'WeBridge, original SQL Java',
    'java_pruned': 'Pruned Java, direct', 'webridge_pruned': 'WeBridge, pruned Java',
}


def count_label(row):
    distribution = row.get('sql_command_count_distribution')
    if not distribution:
        return '—'
    values = sorted(map(int, distribution))
    return str(values[0]) if len(values) == 1 else f'{values[0]}–{values[-1]}'


lines = [
    '# Jac DB and WeBridge: measured database round trips', '',
    '[English PDF slides](jac-webridge-tpcc-littlex-comparison.pdf) · '
    '[Primary JSON](results.json) · [Primary CSV](results.csv) · '
    '[Measurement boundary](RTT_MEASUREMENT_PLAN.md)', '',
    'The primary value is the **median per-request sum of complete SQL command/response RTTs**. '
    'The compact proxy starts each timer at frontend command arrival and stops it after complete '
    'response delivery to the client-facing connection. SQL counts use those same requests. '
    'Database execution, result transfer, communication, configured delay and compact instrumentation '
    'are included; application computation between calls is outside the boundary.', '',
    'Jac uses PostgreSQL 18; Java and WeBridge use MySQL 5.7. Each baseline/optimized pair '
    'holds its database engine and program representation fixed. Cross-engine absolute timings '
    'describe these implementations. Exact source commits and settings appear in '
    '[runtime-provenance.json](runtime-provenance.json).', '',
    'A CALL counts as one client SQL command. Nested procedure statements are retained in the '
    'detailed SQL-work profiles. PostgreSQL preparation-only exchanges contribute RTT and exchange '
    'counts but do not count as executed SQL commands. Observer and outside-request initialization queries are '
    'excluded; SQL initialization triggered inside a request remains included. Per-request count ranges below accompany exact histograms in JSON/CSV.', '',
    '## Coverage', '',
    '27 logical workloads × eight configurations × three response delays = **648 latency cells**. '
    'Pure operations use ten warmup and thirty measured requests; mixed latency uses 110 warmup '
    'and one complete 100-slot measured schedule. The **168 original-schedule references** retain '
    'their own original lengths and correctness outcomes.', '',
    '| Configuration | Accepted latency cells | Compiler-stage failures | Accepted references | Other reference outcomes |',
    '|---|---:|---:|---:|---:|',
]
for arm, name in arms.items():
    latency = [r for r in data['latency'] if r['arm'] == arm]
    references = [r for r in data['references'] if r['arm'] == arm]
    accepted = sum(r['status'] == 'accepted' for r in references)
    lines.append(f"| {name} | {sum(r['status'] == 'accepted' for r in latency)} | {sum(r['status'] == 'failed_with_stage_evidence' for r in latency)} | {accepted} | {len(references)-accepted} |")
lines += ['', '## Per-workload RTT and query counts', '',
          'All RTT values are milliseconds. Count cells show the per-request SQL command range. '
          'Compiler-stage failures link to their recorded stage receipts. '
          'Each case links to the complete raw/gate index in results.json.', '']
for case in data['cases']:
    lines += ['### ' + case['title'], '', case['subtitle'], '',
              '| Configuration | RTT 0 ms | RTT +2 ms | RTT +10 ms | SQL 0 ms | SQL +2 ms | SQL +10 ms |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for arm, name in arms.items():
        cells = [next(r for r in data['latency'] if r['case_id'] == case['id'] and r['arm'] == arm and r['delay_ms'] == delay) for delay in [0, 2, 10]]
        times = [f"{r['median_ms']:.3f}" if r['status'] == 'accepted' else r['display_status'] for r in cells]
        lines.append('| ' + ' | '.join([name, *times, *(count_label(r) for r in cells)]) + ' |')
    lines += ['', f"Evidence key: `{case['id']}` in [results.json](results.json).", '']
lines += [
    '## Evidence and independent verification', '',
    '- [Original reference schedules and actual procedure routing](rtt-reference-results.json), with [CSV timings and counts](rtt-reference-results.csv).',
    '- [Same-request command/exchange evidence](rtt-cycle-evidence.json).',
    '- [Fresh compact-RTT SQL attribution](profiles/primary-rtt-attribution/final/MEASURED_FINDINGS.md): source-aware categories, additive mean costs, exact SQL hashes and per-request reconciliation.',
    '- [Independent raw RTT verifier](verify_rtt_results.py): recomputes timestamps, request sums, medians and counts; checks all connections at request boundaries.',
    '- [Detailed SQL-work attribution](profiles/paged-feed-cost-analysis/EXPLANATION.md): earlier rich-trace diagnostic with explicit sample and transport scope.',
    '- [Archive verifier](verify_archive.py), [indexed-stream verifier](verify_chunks.py) and [result-link verifier](verify_result_links.py).',
    '- [Methods](METHODS.md), [workload contracts](workload-contracts.json) and [seed inputs](seed-inputs).', '',
    'Earlier application timings and server-only profiles retain separate timer definitions and '
    'coverage in their original artifacts. The primary tables above are generated from compact RTT measurements.', '',
    '## Rebuild the report from collected evidence', '', '```bash',
    'python collect_cycle_evidence.py',
    'python collect_references.py --native native/normalized-rtt-reference.json --littlex littlex/normalized-rtt-results.json',
    'python aggregate_results.py',
    'python verify_rtt_results.py . --out final-rtt-verification.json',
    'python profiles/primary-rtt-attribution/analyze.py --results results.json --out profiles/primary-rtt-attribution/rebuilt',
    'python build_report.py', 'python build_pdf.py --attribution profiles/primary-rtt-attribution/rebuilt/attribution.json', '```', '',
    'Run live collectors and heavy analyses under the shared measurement lease when any experiments are active.', '',
    f"Primary results SHA-256: `{hashlib.sha256(source.read_bytes()).hexdigest()}`.", '',
]
(ROOT / 'REPORT.md').write_text('\n'.join(lines))
print(json.dumps({'path': str(ROOT / 'REPORT.md'), 'latency_cells': 648, 'references': 168}))
