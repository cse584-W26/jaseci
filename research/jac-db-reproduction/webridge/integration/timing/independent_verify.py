#!/usr/bin/env python3
"""Recompute the IC5 timing results from every saved request."""
import hashlib
import json
import statistics
from pathlib import Path

root = Path(__file__).resolve().parent
expected = [[2061584375281, 'Album 7 of Jie Xie', 0]]
report = {'runs': {}, 'measured_requests': 0, 'warmup_requests': 0}
for path in sorted(root.rglob('requests/rows.jsonl')):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    name = str(path.parent.parent.relative_to(root))
    variant = 'pruned' if 'pruned' in name else 'full'
    logical = 31 if variant == 'pruned' else 38
    groups = {}
    for phase in ['baseline', 'sp']:
        phase_rows = [r for r in rows if r['phase'] == phase]
        measured = [r for r in phase_rows if not r['warmup']]
        warm = [r for r in phase_rows if r['warmup']]
        assert len(measured) == 30 and len(warm) == 10, name
        assert all(r['oracle_ok'] and r['result'] == expected for r in phase_rows), name
        assert all(r['jdbc_calls'] == logical for r in measured), name
        assert all(r['thread_cpu_ms'] >= 0 for r in measured), name
        calls = 1 if phase == 'sp' else 0
        questions = 4 if calls else logical
        assert all(r['status_delta']['Com_call_procedure'] == calls for r in measured), name
        assert all(r['questions'] == questions for r in measured), name
        if calls:
            assert all(r['sp_enabled_at_end'] for r in phase_rows), name
        groups[phase] = {
            'n': len(measured),
            'median_ms': statistics.median(r['ms'] for r in measured),
            'median_thread_cpu_ms': statistics.median(r['thread_cpu_ms'] for r in measured),
            'questions': questions,
            'handler_counts': {k: sorted({r['status_delta'][k] for r in measured}) for k in
                               ['Handler_read_key', 'Handler_read_next', 'Handler_read_rnd_next']},
        }
        report['measured_requests'] += len(measured)
        report['warmup_requests'] += len(warm)
    groups['p50_speedup'] = groups['baseline']['median_ms']/groups['sp']['median_ms']
    groups['raw_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    report['runs'][name] = groups
assert report['runs']
primary = ['full-utf8-0rtt-quiet', 'pruned-utf8-0rtt-quiet']
for name in primary:
    for phase in ['baseline', 'sp']:
        saved = json.loads((root/'summary.json').read_text())[name][phase]
        assert saved['median_ms'] == report['runs'][name][phase]['median_ms']
for variant in ['full', 'pruned']:
    for phase in ['baseline', 'sp']:
        saved = json.loads((root/'delay2100us/summary.json').read_text())[variant][phase]
        assert saved['median_ms'] == report['runs']['delay2100us/'+variant][phase]['median_ms']
report['all_pass'] = True
(root/'independent-verification.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k != 'runs'}, indent=2))

if __name__ == '__main__':
    import os
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/webridge-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.3), layout='constrained')
    colors = ['#596474', '#197f8e']
    names = primary + ['delay2100us/full', 'delay2100us/pruned']
    labels = ['Full\nNo added delay', 'Pruned\nNo added delay',
              'Full\n+2.1 ms delay', 'Pruned\n+2.1 ms delay']
    for i, phase in enumerate(['baseline', 'sp']):
        values = [report['runs'][n][phase]['median_ms'] for n in names]
        bars = axes[0].bar([j+(i-.5)*.36 for j in range(4)], values, .36,
                           label=['Java baseline', 'WeBridge'][i], color=colors[i])
        axes[0].bar_label(bars, fmt='%.1f', fontsize=8, padding=3)
    axes[0].set_xticks(range(4), labels, fontsize=8)
    axes[0].set_ylabel('Complete-request median (ms)')
    axes[0].set_title('A. Controlled warm timing', loc='left', fontsize=11)
    axes[0].set_ylim(0, 140)
    axes[0].legend(frameon=False, fontsize=8)
    for i, values in enumerate([[38,31],[4,4]]):
        bars = axes[1].bar([j+(i-.5)*.36 for j in range(2)], values, .36,
                           color=colors[i])
        axes[1].bar_label(bars, padding=3)
    axes[1].set_xticks([0,1], ['Full', 'Pruned'])
    axes[1].set_ylim(0,46)
    axes[1].set_ylabel('Client commands per request')
    axes[1].set_title('B. Independently checked counts', loc='left', fontsize=11)
    axes[2].bar(range(3), [13,601802,13], color=['#596474','#b76042','#596474'])
    axes[2].set_yscale('log')
    axes[2].set_xticks(range(3), ['Literal UUID', 'UTF-8 variable', 'ASCII variable'], rotation=18, fontsize=8)
    axes[2].set_ylabel('Handler_read_next (same SQL/value)')
    axes[2].set_title('C. Original-layout plan control', loc='left', fontsize=11)
    for i, value in enumerate([13,601802,13]):
        axes[2].text(i, value*1.3, f'{value:,}', ha='center', fontsize=8)
    axes[2].set_ylim(1, 5000000)
    for ax in axes:
        ax.spines[['top','right']].set_visible(False)
        ax.set_axisbelow(True)
        ax.grid(axis='y', alpha=.15)
    fig.suptitle('Jac IC5 and WeBridge: two validated baselines', fontsize=14)
    fig.savefig(root/'comparison.pdf')
    fig.savefig(root/'comparison.png', dpi=180)
