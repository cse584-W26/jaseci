"""Generate paper tables, figures, and an input checksum manifest from measured artifacts."""
import csv
import hashlib
import json
import os
from pathlib import Path
import statistics as st

os.environ.setdefault('MPLCONFIGDIR', '/tmp/jac-db-paper-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GEN = HERE / 'generated'
FIG = HERE / 'figures'
GEN.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)
INPUTS = {}


def read(path):
    p = ROOT / path
    INPUTS[path] = hashlib.sha256(p.read_bytes()).hexdigest()
    return p


def js(path):
    return json.loads(read(path).read_text())


def rows(path):
    with read(path).open(newline='') as f:
        return list(csv.DictReader(f))


def table(name, lines):
    (GEN / name).write_text('\n'.join(lines) + '\n')


def save(fig, name):
    fig.savefig(FIG / (name + '.pdf'), bbox_inches='tight')
    fig.savefig(FIG / (name + '.png'), bbox_inches='tight', dpi=180)
    plt.close(fig)


plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8.5,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'pdf.fonttype': 42, 'ps.fonttype': 42})
TEAL = '#137d8c'
GRAY = '#677887'

# Core source A/B. Census and logging-off latency have different schedules.
base = js('results/baseline-census/summary.json')
final = js('results/final-census/summary.json')
blat = js('results/baseline-latency/summary.json')['queries']['ic5']
flat = js('results/final-latency/summary.json')['queries']['ic5']
bc = base['queries']['ic5']['total_statements']
fc = final['queries']['ic5']['total_statements']
assert (bc, fc) == (278769, 432)
assert blat['parity_ok'] == blat['n'] == 40 and flat['parity_ok'] == flat['n'] == 60
speed = blat['jac_median_ms'] / flat['jac_median_ms']
macros = {'SQLReduction': f'{bc/fc:.1f}', 'LatencySpeedup': f'{speed:.2f}',
          'BaseLatency': f"{blat['jac_median_ms']:,.3f}", 'FinalLatency': f"{flat['jac_median_ms']:.3f}"}
table('numbers.tex', [f'\\newcommand{{\\{k}}}{{{v}}}' for k, v in macros.items()])
table('ic5.tex', [
    r'Baseline & 278,769 & 40 & ' + f"{blat['jac_median_ms']:,.3f} & {blat['pg_median_ms']:.3f}" + r' \\',
    r'Optimized & 432 & 60 & ' + f"{flat['jac_median_ms']:.3f} & {flat['pg_median_ms']:.3f}" + r' \\'])
fig, ax = plt.subplots(1, 2, figsize=(7.1, 2.25))
for a, vals, ylabel, ratio in [(ax[0], [bc, fc], 'SQL statements / 20 inputs', bc/fc),
                               (ax[1], [blat['jac_median_ms'], flat['jac_median_ms']], 'Client median latency (ms)', speed)]:
    bars = a.bar(['Baseline', 'Optimized'], vals, color=[GRAY, TEAL], width=.58)
    a.set_yscale('log')
    a.set_ylim(min(vals)/3, max(vals)*5)
    a.set_ylabel(ylabel)
    for b, v in zip(bars, vals):
        label = f'{v:,.0f}' if ylabel.startswith('SQL') else f'{v:,.1f}'
        a.text(b.get_x()+b.get_width()/2, v*1.17, label, ha='center', fontsize=9)
    a.set_title(f'{ratio:,.1f}'+r'$\times$ reduction', fontsize=10, loc='left')
fig.tight_layout(w_pad=2)
save(fig, 'ic5')

# Canonical SNB uses conventional sample medians, including even sample sizes.
queries = ['is1', 'is2', 'is3', 'ic1', 'ic2', 'ic5', 'ic13']
arms = {'Jac': 'results/snb-canonical/jac/canonical-summary.json',
        'SQL': 'results/locked/snb-canonical/postgres/canonical-summary.json',
        'ORM': 'results/locked/snb-canonical/sqlalchemy/canonical-summary.json',
        'Neo4j': 'results/locked/snb-canonical/neo4j/canonical-summary.json'}
snb = {a: js(p) for a, p in arms.items()}
assert all(d['passed'] and d['timed_n'] == 2550 and d['historical_hash_matches'] == 140 for d in snb.values())
table('snb.tex', [(r'IC5$^{\dagger}$' if q == 'ic5' else q.upper()) + ' & ' +
                 ' & '.join(f"{snb[a]['queries'][q]['client']['median_ms']:.3f}" for a in arms) + r' \\' for q in queries])

# Transaction timing includes expected rollback requests in the New-Order class.
tpcc = {}
for name, path, arm in [('SQL', 'results/locked/tpcc-postgres', 'postgres'),
                        ('Jac', 'results/tpcc-jac', 'jaseci-pg'),
                        ('ORM', 'results/locked/tpcc-sqlalchemy', 'sqlalchemy')]:
    oracle = js(f'{path}/tpcc_{arm}.oracle.json')
    assert oracle['oracle_all_ok'] and oracle['rolled_back'] == 7
    sample = rows(f'{path}/tpcc_{arm}.csv')
    assert len(sample) == 800
    tpcc[name] = {q: st.median(float(r['client_ms']) for r in sample if r['query'] == q)
                  for q in ['new_order', 'payment']}
table('tpcc.tex', [name + ' & ' + ' & '.join(f'{tpcc[name][q]:.3f}' for q in ['new_order', 'payment']) + r' \\' for name in tpcc])

# littleX common outer metric and historical headline server metric are both retained.
record = js('littlex/original-recipe/20261019T193716Z/complete.json')['records']
assert len(record) == 40
lx = {}
for rec in record:
    if rec['phase'] not in ['W1', 'W3']:
        continue
    raw = rows(str(Path(rec['results']).parent.relative_to(ROOT) / 'raw.csv'))
    key = 'feed_page' if rec['phase'] == 'W3' else 'feed_chain'
    selected = raw if rec['phase'] == 'W1' else [r for r in raw if r['workload'] == key]
    stats = {m: st.median(float(r[m]) for r in selected) for m in ['server_ms', 'client_ms']}
    # Primary record names are stable and encode phase/tier/arm/fraction.
    fraction = rec['cell'].rsplit('_', 1)[1]
    lx[(rec['phase'], rec['tier'], rec['arm'], fraction)] = stats
page = []
for f in ['0', '5', '15', '30']:
    j, p = (lx[('W3', 't200', a, f)] for a in ['jaseci', 'postgres'])
    page.append(f + ' & ' + ' & '.join(f'{v:.3f}' for v in [j['server_ms'], p['server_ms'], j['client_ms'], p['client_ms']]) + r' \\')
table('page.tex', page)
fig, ax = plt.subplots(1, 2, figsize=(7.1, 2.3))
tiers = [20, 50, 100, 200]
fractions = [0, 5, 15, 30]
for arm, color, label in [('postgres', GRAY, 'Hand SQL'), ('jaseci', TEAL, 'Jac CONTROL')]:
    ax[0].plot(tiers, [lx[('W1', f't{t}', arm, 'feed')]['client_ms'] for t in tiers], '-o', color=color, label=label, markersize=4)
    ax[1].plot(fractions, [lx[('W3', 't200', arm, str(f))]['client_ms'] for f in fractions], '-o', color=color, label=label, markersize=4)
ax[0].set_title('Unbounded feed', loc='left', fontsize=10)
ax[0].set_xlabel('Tweets per user')
ax[0].set_ylabel('Client median (ms)')
ax[0].set_xticks(tiers)
ax[0].set_ylim(bottom=0)
ax[1].set_title('20-item page at 200 tweets/user', loc='left', fontsize=10)
ax[1].set_xlabel('Write fraction (%)')
ax[1].set_ylabel('Client median (ms)')
ax[1].set_xticks(fractions)
ax[1].set_ylim(0, 6.5)
ax[1].legend(frameon=False, fontsize=8, loc='lower right')
fig.tight_layout(w_pad=1.5)
save(fig, 'littlex')

# Three interleaved, clean write cohorts; each per-round median comes from raw CSV.
validation = js('write-investigation/rerun-baseline.json')
assert validation['all_checks_passed'] and validation['raw_samples'] == 9000
ops = ['like', 'follow', 'create_tweet']
writes = {}
for arm in ['postgres', 'jaseci']:
    for op in ops:
        rr = [r for r in validation['rows'] if r['arm'] == arm and r['operation'] == op]
        values = []
        for r in rr:
            sample = rows(str(Path(r['raw_path']).relative_to('reproduction')))
            values.append(st.median(float(x['client_ms']) for x in sample))
        writes[(arm, op)] = values
sql = js('write-investigation/sql-work-20261019T212529Z.json')
table('writes.tex', [label + ' & ' + ' & '.join(f"{st.median(writes[(a, op)]):.3f}" for a in ['postgres', 'jaseci']) +
                     ' & ' + f"{sql[f'1-jaseci/{op}']['executions_per_request']:.2f}" + r' \\'
                     for op, label in zip(ops, ['Like', 'Follow', 'Create'])])
fig, ax = plt.subplots(1, 2, figsize=(7.1, 2.35))
x = np.arange(3)
for arm, shift, color, label in [('postgres', -.18, GRAY, 'Hand SQL'), ('jaseci', .18, TEAL, 'Jac CONTROL')]:
    v = [writes[(arm, op)] for op in ops]
    med = [st.median(a) for a in v]
    ax[0].bar(x+shift, med, .34, color=color, label=label,
              yerr=[[c-min(a) for c, a in zip(med, v)], [max(a)-c for c, a in zip(med, v)]], capsize=3)
    ax[1].bar(x+shift, [sql[f'1-{arm}/{op}']['executions_per_request'] for op in ops], .34, color=color, label=label)
for a in ax:
    a.set_xticks(x, ['Like', 'Follow', 'Create'])
ax[0].set_ylabel('Client median (ms)')
ax[0].set_title('Three fresh-state repetitions', fontsize=10, loc='left')
ax[0].legend(frameon=False, fontsize=8)
ax[1].set_ylabel('Explicit SQL commands/write')
ax[1].set_title('Separate SQL census', fontsize=10, loc='left')
fig.tight_layout(w_pad=1.5)
save(fig, 'writes')

# Per-query-category spans: means over 100 diagnostic requests, worker lane only.
req = js('littlex/w2-investigation/20261019T213148Z-spans/1-jaseci/functions/requests.json')
assert len(req) == 300 and all(r['response_status'] == 200 for r in req)
labels = [('anchor-traversal', 'Traversal'), ('anchor-load', 'Anchor load'),
          ('anchor-write-insert', 'Anchor upsert'), ('type-registry-write', 'Type registry'), ('commit', 'Commit')]
lines = []
for category, label in labels:
    cells = []
    for op in ['create_tweet', 'follow_user', 'like_tweet']:
        rr = [r for r in req if r['operation'] == op]
        spans = [s for r in rr for s in r['spans'] if s['name'] == 'PgStore._run' and
                 s['thread_ident'] != r['main_thread_ident'] and s.get('sql_category') == category]
        cells.append(f"{len(spans)/len(rr):g} / {sum(s['wall_ms'] for s in spans)/len(rr):.3f}")
    lines.append(label + ' & ' + ' & '.join(cells) + r' \\')
table('spans.tex', lines)
dml = js('write-investigation/dml-summary.json')
table('dml.tex', [op.replace('_', ' ').capitalize() + ' & ' + ' & '.join(f"{dml[f'{a}/{op}']['median']['execution_ms']:.3f}" for a in ['postgres', 'jaseci']) + ' & ' +
                  ' / '.join(str(int(dml[f'{a}/{op}']['median']['wal_bytes'])) for a in ['postgres', 'jaseci']) + r' \\' for op in ops])

# List concrete semantic/source evidence in the manifest, alongside every numeric input.
for path in ['IC5_MECHANISM.md', 'REPORT.md', 'write-investigation/REPORT.md',
             'runtime/HTTP_STACK.md', 'littlex/PAGE_BRANCH_RECEIPT.md', 'littlex/ANALYZE_PLAN_RECEIPT.md']:
    read(path)
(GEN / 'inputs.json').write_text(json.dumps({'root': str(ROOT), 'statistics': 'Conventional medians recomputed for generated latency tables; write summaries take the median of the three per-cohort medians. Span and protocol metrics are separate diagnostic means. Census totals come from their own 20-input windows.',
                                         'sha256': INPUTS}, indent=2)+'\n')
print(f'Generated paper assets from {len(INPUTS)} checksummed inputs.')
