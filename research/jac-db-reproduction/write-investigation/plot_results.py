"""Render repeated write latency and complete SQL census from retained artifacts."""
import json
import os
from pathlib import Path
import statistics

os.environ.setdefault('MPLCONFIGDIR', '/tmp/jac-w2-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
baseline = json.loads((HERE / 'rerun-baseline.json').read_text())
work = json.loads((HERE / 'sql-work-20261019T212529Z.json').read_text())
ops = ['like', 'follow', 'create_tweet']
labels = ['Like', 'Follow', 'Create tweet']
x = np.arange(3)
fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.4), gridspec_kw={'width_ratios': [1, 1.15]})
colors = {'postgres': '#586b7d', 'jaseci': '#148c9b'}
for arm, shift, label in [('postgres', -.18, 'Hand SQL'), ('jaseci', .18, 'Jac CONTROL (ad469)')]:
    values = [[r['client_p50_ms'] for r in baseline['rows'] if r['arm'] == arm and r['operation'] == op] for op in ops]
    centers = [statistics.median(v) for v in values]
    low = [c - min(v) for c, v in zip(centers, values)]
    high = [max(v) - c for c, v in zip(centers, values)]
    bars = axes[0].bar(x + shift, centers, .34, color=colors[arm], label=label,
                       yerr=[low, high], capsize=4, error_kw={'linewidth': 1})
    axes[0].bar_label(bars, fmt='%.2f', padding=5, fontsize=10)
axes[0].set_title('Complete client latency', loc='left', weight='bold')
axes[0].set_ylabel('Median milliseconds')
axes[0].set_ylim(0, 5.7)
axes[0].legend(frameon=False, fontsize=9, loc='upper left')

groups = [
    ('anchor_load_or_acl', 'Anchor / ACL reads', '#7a9eb8'),
    ('graph_traversal', 'Graph traversal', '#217896'),
    ('transaction', 'BEGIN / SET / COMMIT', '#b6bfc9'),
    ('persist', 'Mutation / type registry', '#d08b42'),
]
for arm, shift in [('postgres', -.18), ('jaseci', .18)]:
    bottoms = np.zeros(3)
    for category, label, color in groups:
        values = []
        for op in ops:
            cats = work[f'1-{arm}/{op}']['categories']
            keys = (['transaction_begin', 'transaction_configuration', 'explicit_commit'] if category == 'transaction'
                    else ['anchor_upsert', 'type_registry_write', 'relational_dml'] if category == 'persist'
                    else [category])
            values.append(sum(cats.get(k, {}).get('executions_per_request', 0) for k in keys))
        axes[1].bar(x + shift, values, .34, bottom=bottoms, color=color,
                    label=label if arm == 'jaseci' else None)
        bottoms += values
    for i, value in enumerate(bottoms):
        axes[1].text(x[i] + shift, value + .15, f'{value:.2f}'.rstrip('0').rstrip('.'), ha='center', fontsize=10)
axes[1].set_title('Explicit SQL commands per write', loc='left', weight='bold')
axes[1].set_ylim(0, 15.8)
axes[1].set_ylabel('Mean command count')
axes[1].legend(frameon=False, fontsize=8.5, loc='upper left', ncol=2)
for ax in axes:
    ax.set_xticks(x, labels)
    ax.spines[['top', 'right']].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis='y', color='#e5e9ed', linewidth=.7)
fig.suptitle('t20 writes: repeated latency and measured SQL work', fontsize=16, weight='bold', x=.06, ha='left')
fig.text(.06, .025,
         'Latency: 3 fresh cohorts, 110 warm + 500 timed requests/operation; whiskers span the three medians.\n'
         'SQL census: 100 profiled writes/operation; each pair is SQL (left), Jac (right). Autocommit has no separate COMMIT command.', fontsize=8.5)
fig.subplots_adjust(top=.83, bottom=.19, left=.06, right=.98, wspace=.24)
fig.savefig(HERE / 'write-costs.png', dpi=180)
fig.savefig(HERE / 'write-costs.pdf')
print('Saved write-costs.png and write-costs.pdf')
