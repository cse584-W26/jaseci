#!/usr/bin/env python3
"""Render the verified TPC-C/littleX comparison from the final results.json."""
import argparse
import json
import math
import os
from pathlib import Path
import textwrap

os.environ.setdefault('MPLCONFIGDIR', '/tmp/jac-webridge-nonsnb-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--attribution', type=Path, default=ROOT / 'profiles/primary-rtt-attribution/final/attribution.json')
args = parser.parse_args()
DATA = json.loads((ROOT / 'results.json').read_text())
assert DATA['metric'] == 'rtt', 'Primary report requires summed SQL round-trip measurements'
assert DATA['coverage']['terminal_cells'] == 648
assert DATA['coverage']['pending_cells'] == 0
ARMS = {
    'jac_original': 'Jac unoptimized', 'jac_final': 'Jac optimized',
    'java_full': 'Jac-like Java, direct', 'webridge_full': 'WeBridge, Jac-like Java',
    'java_pruned': 'Java pruned', 'webridge_pruned': 'WeBridge pruned',
    'java_conventional': 'Original SQL Java, direct',
    'webridge_conventional': 'WeBridge, original SQL Java',
}
CORE_ARMS = {arm: name for arm, name in ARMS.items() if arm not in {'java_pruned', 'webridge_pruned'}}
plt.rcParams.update({'font.family': 'DejaVu Sans', 'pdf.fonttype': 42, 'font.size': 14})
PAGE = 0
PDF = PdfPages(ROOT / 'jac-webridge-tpcc-littlex-comparison.pdf')
PDF.infodict()['Title'] = 'Jac DB and WeBridge: database RTT and SQL command counts'


def slide(title, subtitle='', source=''):
    global PAGE
    PAGE += 1
    f = plt.figure(figsize=(16, 9), facecolor='white')
    f.text(.055, .93, title, fontsize=25, weight='bold', color='#0f172a')
    f.text(.055, .875, textwrap.fill(subtitle, width=137, break_long_words=False), fontsize=13, color='#475569', va='top')
    f.text(.055, .035, textwrap.fill(source, width=200, break_long_words=False), fontsize=8, color='#64748b')
    f.text(.95, .035, str(PAGE), ha='right', fontsize=10, color='#64748b')
    return f


def paragraph(f, value, y=.76, size=20, width=88, x=.06):
    for line in textwrap.wrap(value, width=width):
        f.text(x, y, line, fontsize=size, color='#1e293b')
        y -= size / 350
    return y


def table(f, headers, rows, widths=None, bbox=(.055, .20, .89, .59), size=13):
    widths = widths or [1 / len(headers)] * len(headers)
    widths = [x / sum(widths) for x in widths]
    limits = [max(9, int(1152 * bbox[2] * x * .80 / (size * .54))) for x in widths]
    def wrap(value, i):
        return '\n'.join('\n'.join(textwrap.wrap(line, limits[i], break_long_words=False)) for line in str(value).split('\n'))
    ax = f.add_axes([0, 0, 1, 1])
    ax.axis('off')
    t = ax.table(cellText=[[wrap(v, i) for i, v in enumerate(row)] for row in rows], colLabels=[wrap(v, i) for i, v in enumerate(headers)], cellLoc='left', colLoc='left', bbox=bbox, colWidths=widths)
    t.auto_set_font_size(False)
    t.set_fontsize(size)
    for (row, col), cell in t.get_celld().items():
        cell.set_edgecolor('#e2e8f0')
        cell.set_linewidth(.5)
        cell.set_facecolor('#e2e8f0' if row == 0 else '#f8fafc' if row % 2 else 'white')
        if row == 0:
            cell.set_text_props(weight='bold', color='#0f172a')


def diagram(f, spec):
    from matplotlib.patches import FancyBboxPatch
    ax = f.add_axes([.06, .20, .88, .58])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    positions = {}
    for node in spec['nodes']:
        x, y = node['x'], node['y']
        w, h = node.get('width', .19), node.get('height', .20)
        ax.add_patch(FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle='round,pad=0.012', linewidth=1.2, edgecolor='#334155', facecolor=node.get('color', '#e0f2fe')))
        ax.text(x, y, node['label'], ha='center', va='center', fontsize=13)
        positions[node['id']] = (x, y, w, h)
    for edge in spec['edges']:
        x1, y1, w1, h1 = positions[edge['from']]
        x2, y2, w2, h2 = positions[edge['to']]
        if abs(x2-x1) >= abs(y2-y1):
            sign = 1 if x2 > x1 else -1
            start, end = (x1+sign*w1/2, y1), (x2-sign*w2/2, y2)
        else:
            sign = 1 if y2 > y1 else -1
            start, end = (x1, y1+sign*h1/2), (x2, y2-sign*h2/2)
        ax.annotate('', xy=end, xytext=start, arrowprops={'arrowstyle': '->', 'color': '#475569', 'lw': 1.5})
        if edge.get('label'):
            ax.text((start[0]+end[0])/2, (start[1]+end[1])/2+.035, edge['label'], ha='center', fontsize=11)


def finish(f):
    f.canvas.draw()
    renderer = f.canvas.get_renderer()
    for text in f.texts:
        while text.get_window_extent(renderer).x1 > f.bbox.width * .96 and text.get_fontsize() > 10:
            text.set_fontsize(text.get_fontsize() - .5)
    PDF.savefig(f)
    plt.close(f)


for item in DATA['narrative_before_data']:
    f = slide(item['title'], item.get('subtitle', ''), item['source'])
    if 'diagram' in item:
        diagram(f, item['diagram'])
    elif 'table' in item:
        table(f, item['table']['headers'], item['table']['rows'], widths=item['table'].get('widths'))
    else:
        y = .76
        for text in item['paragraphs']:
            y = paragraph(f, text, y=y) - .065
    finish(f)

overview_cases = [
    ('tpcc-payment_name_GC', 'TPC-C Payment, name / GC'),
    ('tpcc-new_order_15', 'TPC-C NewOrder, 15 lines'),
    ('littlex-feed-t20', 'littleX full feed, 20 tweets/user'),
    ('littlex-feed-t200', 'littleX full feed, 200 tweets/user'),
    ('littlex-like-t200', 'littleX like, 200 tweets/user'),
    ('littlex-create_tweet-t200', 'littleX create, 200 tweets/user'),
    ('littlex-mixed-t200-w15', 'littleX mixed, 15% writes'),
]
overview_pairs = [('jac_original', 'jac_final'), ('java_full', 'webridge_full'),
                  ('java_conventional', 'webridge_conventional')]
for metric in ['rtt', 'counts']:
    f = slide('Representative results: ' + ('DB-call RTT' if metric == 'rtt' else 'SQL command counts'),
              ('Median per-request sum (ms), zero added delay' if metric == 'rtt' else 'Mean commands per request [observed range], from the same zero-delay RTT requests') + '; baseline → optimized',
              'Source: results.json; exact count distributions, all 27 cases and 0 / +2 / +10 ms appear in the following pages and raw evidence.')
    rows = []
    for identifier, name in overview_cases:
        values = []
        for pair in overview_pairs:
            sides = []
            for arm in pair:
                cell = next(row for row in DATA['latency'] if row['case_id'] == identifier and row['arm'] == arm and row['delay_ms'] == 0)
                if cell['status'] != 'accepted':
                    text = cell['display_status']
                elif metric == 'rtt':
                    text = f"{cell['median_ms']:.2f}"
                else:
                    counts = sorted(int(value) for value in cell['sql_command_count_distribution'])
                    text = f"{cell['mean_sql_commands_per_request']:.2f}"
                    if len(counts) > 1:
                        text += f' [{counts[0]}–{counts[-1]}]'
                sides.append(text)
            values.append(' → '.join(sides))
        rows.append([name, *values])
    table(f, ['Workload', 'Jac: unoptimized → optimized', 'Jac-like Java: direct → WeBridge', 'Original SQL Java: direct → WeBridge'], rows,
          widths=[.31, .23, .23, .23], size=12)
    paragraph(f, 'Each arrow compares two executions of the same workload within one system and database. Jac uses PostgreSQL 18; Java and WeBridge use MySQL 5.7. CALL counts as one client command; nested SQL work is examined separately.', y=.13, size=12, width=147)
    finish(f)

f = slide('How added response delay changes DB-call RTT',
          'Median summed RTT per request; matched workload inputs at 0 / +2 / +10 ms',
          'Source: results.json. Jac: PostgreSQL 18. Java / WeBridge: MySQL 5.7. Missing procedure curves have compiler-stage receipts in the case tables.')
plot_cases = [overview_cases[i] for i in [0, 1, 3, 6]]
colors = ['#93c5fd', '#1d4ed8', '#fdba74', '#c2410c', '#86efac', '#15803d']
for panel, (identifier, name) in enumerate(plot_cases):
    ax = f.add_axes([.075 + .47 * (panel % 2), .54 - .35 * (panel // 2), .38, .25])
    for (arm, label), color in zip(CORE_ARMS.items(), colors):
        values = [next(row for row in DATA['latency'] if row['case_id'] == identifier and row['arm'] == arm and row['delay_ms'] == delay) for delay in [0, 2, 10]]
        if all(row['status'] == 'accepted' for row in values):
            ax.plot([0, 2, 10], [row['median_ms'] for row in values], marker='o', linewidth=1.8,
                    linestyle='--' if arm in {'jac_final', 'webridge_full', 'webridge_conventional'} else '-',
                    color=color, label=label)
    ax.set_title(name, fontsize=13, loc='left')
    ax.set_xticks([0, 2, 10])
    ax.set_xlabel('Added delay per response (ms)', fontsize=10)
    ax.set_ylabel('Summed SQL RTT (ms)', fontsize=10)
    ax.tick_params(labelsize=10)
    ax.grid(alpha=.18)
    ax.spines[['top', 'right']].set_visible(False)
from matplotlib.lines import Line2D
handles = [Line2D([0], [0], color=color, marker='o', linestyle='--' if arm in {'jac_final', 'webridge_full', 'webridge_conventional'} else '-', label=label)
           for (arm, label), color in zip(CORE_ARMS.items(), colors)]
f.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, .075), ncol=3, frameon=False, fontsize=10)
finish(f)

f = slide('Complete SQL round-trip timing coverage by configuration',
          '27 workloads × 3 delays; each compiler failure supplies stage evidence to its three delay cells',
          'Source: results.json; accepted values pass result and committed-state gates')
rows = []
for arm, name in ARMS.items():
    values = [row for row in DATA['latency'] if row['arm'] == arm]
    rows.append([name, sum(row['status'] == 'accepted' for row in values),
                 sum(row['status'] == 'failed_with_stage_evidence' for row in values), len(values)])
table(f, ['Configuration', 'Accepted cells', 'Stage-failure cells', 'Total cells'], rows,
      widths=[.43, .19, .23, .15], size=14)
finish(f)

f = slide('Original-schedule references complement the latency cells',
          'TPC-C: 100 warmup + 800 measured; littleX retains the original W1 / W2 / W3 schedule lengths',
          'Source: rtt-reference-results.json; compiler-unavailable references retain their actual stage evidence')
rows = []
for arm, name in ARMS.items():
    t = next(row for row in DATA['references'] if row['family'] == 'tpcc' and row['arm'] == arm)
    label = 'PASS' if t['status'] == 'accepted' else 'state rejected'
    if arm.startswith('webridge_'):
        calls = t['actual_calls']
        label += f'; {calls} CALLs'
        if calls == 0:
            label = 'source fallback; 0 CALLs'
    littlex = [row for row in DATA['references'] if row['family'] == 'littlex' and row['arm'] == arm]
    assert len(littlex) == 20
    accepted = sum(row['status'] == 'accepted' for row in littlex)
    rows.append([name, label, accepted, len(littlex) - accepted])
table(f, ['Configuration', 'TPC-C original900', 'littleX accepted / 20', 'littleX failed stage / state'], rows,
      widths=[.30, .30, .18, .22], size=12)
finish(f)

for case in DATA['cases']:
    f = slide(case['title'], case['subtitle'], case['source'])
    rows = []
    for arm, name in CORE_ARMS.items():
        cells = [next(x for x in DATA['latency'] if x['case_id'] == case['id'] and x['arm'] == arm and x['delay_ms'] == delay) for delay in [0, 2, 10]]
        values = []
        for cell in cells:
            assert cell['status'] in ['accepted', 'failed_with_stage_evidence'] and cell['artifact']
            value = cell.get('median_ms')
            label = f'{value:.2f}' if value is not None else cell['display_status']
            fraction = cell.get('actual_call_fraction')
            if value is not None and arm.startswith('webridge_') and fraction is not None:
                label += f'\nCALL {100 * fraction:.0f}%'
                enabled = cell.get('sdk_enabled_at_end_fraction')
                if enabled is not None and abs(enabled - fraction) > 1e-9:
                    label += f' / E{100 * enabled:.0f}%'
            values.append(label)
        cycles = DATA['cycles'].get(case['id'], {}).get(arm, {}).get('display', 'see stage receipt')
        rows.append([name, *values, cycles])
    table(f, ['Configuration', '0 ms', '+2 ms', '+10 ms', 'SQL commands / exchanges: 0 / +2 / +10'], rows, widths=[.31, .14, .14, .14, .27], size=12)
    paragraph(f, case['note'], y=.16, size=12, width=147)
    finish(f)

from aggregate_results import case_id
attribution_path = args.attribution.resolve()
assert attribution_path.exists(), 'Complete fresh RTT attribution before rendering the final PDF'
attribution = json.loads(attribution_path.read_text())
category_names = {
    'traversal.2hop.projection_acl': '2-hop traversal + access checks',
    'stored_procedure.call': 'CALL: complete outer response',
    'transaction.commit': 'COMMIT',
    'transaction.setting': 'Transaction / session setting',
    'graph.anchor_query': 'Graph SELECT',
    'graph.projected_query': 'Projected graph SELECT',
}
for identifier, name in [overview_cases[i] for i in [0, 2, 3, 6]]:
    f = slide('Fresh RTT attribution: ' + name,
              'Primary medians by delay; dominant SQL category measured at zero added delay',
              f'Source: {attribution_path.relative_to(ROOT) if attribution_path.is_relative_to(ROOT) else attribution_path}; exact SQL hashes, per-request reconciliation and classifier source hashes retained.')
    rows = []
    for arm, label in CORE_ARMS.items():
        costs = [r for r in attribution['cells'] if case_id(r['cell']) == identifier and r['cell']['arm'] == arm and r['cell']['delay_ms'] == 0]
        cells = [next(r for r in DATA['latency'] if r['case_id'] == identifier and r['arm'] == arm and r['delay_ms'] == delay) for delay in [0, 10]]
        times = [f"{r['median_ms']:.2f}" if r['status'] == 'accepted' else r['display_status'] for r in cells]
        if cells[0]['status'] != 'accepted':
            assert not costs
            rows.append([label, *times, 'Stage receipt', '—'])
            continue
        assert len(costs) == 1
        cost = costs[0]
        assert math.isclose(cost['median_total_ms'], cells[0]['median_ms'], rel_tol=1e-9, abs_tol=1e-7)
        assert math.isclose(sum(c['mean_ms'] for c in cost['categories'].values()), cost['mean_total_ms'], rel_tol=1e-12, abs_tol=1e-8)
        category = max(cost['categories'], key=lambda k: cost['categories'][k]['mean_ms'])
        value = cost['categories'][category]['mean_ms']
        title = category_names.get(category, category.replace('.', ' ').replace('_', ' '))
        rows.append([label, *times, f'{title}\n{value:.3f} ms / request', f"{100 * value / cost['mean_total_ms']:.1f}%"])
    table(f, ['Configuration', 'Median 0 ms', 'Median +10 ms', 'Dominant category: mean RTT', 'Share of mean total'], rows,
          widths=[.29, .12, .12, .32, .15], size=12)
    paragraph(f, 'Category costs are sums within each request; their means add to the mean total. Primary medians are computed from complete per-request sums. A CALL includes its full response and internal execution.', y=.13, size=12, width=147)
    finish(f)

for item in DATA['narrative_after_data']:
    f = slide(item['title'], item.get('subtitle', ''), item['source'])
    if 'diagram' in item:
        diagram(f, item['diagram'])
    elif 'table' in item:
        table(f, item['table']['headers'], item['table']['rows'], widths=item['table'].get('widths'), size=item['table'].get('size', 13))
    else:
        y = .76
        for text in item['paragraphs']:
            y = paragraph(f, text, y=y) - .065
    finish(f)

for offset in range(0, len(DATA['cases']), 5):
    subset = DATA['cases'][offset:offset + 5]
    f = slide('Supplementary comparison: pruned Java and WeBridge',
              'Summed SQL RTT per request (ms); command counts use the same requests',
              'Source: results.json / results.csv; per-case raw RTT, command-count and correctness links retained')
    rows = []
    for case in subset:
        matching = [row for row in DATA['latency'] if row['case_id'] == case['id']]
        identity = matching[0]
        label = ('TPC-C ' if identity['family'] == 'tpcc' else 'littleX ') + identity['workload'].replace('_', ' ')
        if identity['family'] == 'littlex':
            label += f" t{identity['tweets_per_user']}"
            if identity.get('write_percent') is not None:
                label += f" / {identity['write_percent']}% writes"
        for arm in ['java_pruned', 'webridge_pruned']:
            values = []
            for delay in [0, 2, 10]:
                cell = next(row for row in matching if row['arm'] == arm and row['delay_ms'] == delay)
                value = cell.get('median_ms')
                text = f'{value:.2f}' if value is not None else cell['display_status']
                if value is not None and arm == 'webridge_pruned':
                    fraction = cell.get('actual_call_fraction')
                    enabled = cell.get('sdk_enabled_at_end_fraction')
                    if (fraction is not None and fraction < 1) or (enabled is not None and enabled < 1):
                        text += '*'
                values.append(text)
            counts = DATA['cycles'][case['id']][arm]['display']
            rows.append([label if arm == 'java_pruned' else '', 'Java direct' if arm == 'java_pruned' else 'WeBridge', *values, counts])
    table(f, ['Case', 'Pruned form', '0 ms', '+2 ms', '+10 ms', 'SQL commands: 0 / +2 / +10'], rows,
          widths=[.26, .16, .12, .12, .12, .22], size=11)
    paragraph(f, '* Includes source fallback or incomplete procedure use; exact CALL / SDK activation fractions are retained per request. Parentheses in count cells show exchanges when different from SQL commands.', y=.13, size=12, width=147)
    finish(f)

def reference_value(row):
    if row['status'] == 'accepted':
        value = row.get('median_ms')
        if value is None:
            value = row['reference_median_ms']
        counts = sorted(int(value) for value in row['sql_command_count_distribution'])
        count = str(counts[0]) if len(counts) == 1 else f'{counts[0]}–{counts[-1]}'
        return f'{value:.2f} ms\n{count} SQL'
    return 'state rejected' if row['status'] == 'rejected_state_gate' else 'compiler stage failed'

f = slide('Original TPC-C plan: DB RTT and SQL command counts',
          'Original 900 ordered transactions: 100 warmup + 800 measured; medians and SQL ranges use the measured 800',
          'Source: rtt-reference-results.json. Actual CALL totals cover all 900 requests; source-fallback paths and rejected state retain their raw evidence.')
rows = []
for arm, name in ARMS.items():
    row = next(r for r in DATA['references'] if r['family'] == 'tpcc' and r['arm'] == arm)
    rows.append([name, reference_value(row), row.get('actual_calls', 0),
                 'PASS: source fallback' if arm.startswith('webridge_') and row.get('actual_calls') == 0 else 'State rejected' if row['status'] == 'rejected_state_gate' else 'PASS'])
table(f, ['Configuration', 'Median RTT / SQL range', 'CALLs / 900', 'Result / final state'], rows,
      widths=[.36, .25, .15, .24], size=12)
finish(f)

for tier in [20, 50, 100, 200]:
    f = slide(f'Original littleX references: {tier} tweets per user',
              'Pure operations: 110 warmup + 500 measured; each cell shows median summed RTT and per-request SQL range',
              'Source: rtt-reference-results.json; full source results and evolving committed state are independently checked.')
    rows = []
    for arm, name in CORE_ARMS.items():
        cells = [next(r for r in DATA['references'] if r['family'] == 'littlex' and r['workload'] == workload and r['tweets_per_user'] == tier and r['arm'] == arm) for workload in ['feed', 'like', 'follow', 'create_tweet']]
        rows.append([name, *(reference_value(row) for row in cells)])
    table(f, ['Configuration', 'Full feed', 'Like', 'Follow', 'Create tweet'], rows,
          widths=[.32, .17, .17, .17, .17], size=12)
    finish(f)

f = slide('Original littleX mixed references: 200 tweets per user',
          '110 warmup + 1,000 measured; median summed RTT and per-request SQL range over the complete measured schedule',
          'Source: rtt-reference-results.json; exact CALL / SDK activation and per-operation measurements remain in raw request records.')
rows = []
for arm, name in CORE_ARMS.items():
    cells = [next(r for r in DATA['references'] if r['family'] == 'littlex' and r['workload'] == 'mixed' and r['write_percent'] == percent and r['arm'] == arm) for percent in [0, 5, 15, 30]]
    rows.append([name, *(reference_value(row) for row in cells)])
table(f, ['Configuration', '0% writes', '5% writes', '15% writes', '30% writes'], rows,
      widths=[.32, .17, .17, .17, .17], size=12)
finish(f)
PDF.close()
print(json.dumps({'pages': PAGE, 'path': str(ROOT / 'jac-webridge-tpcc-littlex-comparison.pdf')}))
