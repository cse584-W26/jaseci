#!/usr/bin/env python3
"""Freeze and profile direct/genuine littleX programs with independent result checks."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--implementations', nargs='+', default=['LittleXSql', 'LittleXFull', 'LittleXPruned'])
parser.add_argument('--phase', choices=['baseline', 'sp'], default='baseline')
parser.add_argument('--bundle', type=Path)
parser.add_argument('--build-snapshot', type=Path)
parser.add_argument('--skip-passed-summary', type=Path)
parser.add_argument('--operations', nargs='+', default=['feed', 'like', 'follow', 'create_tweet', 'feed_page'])
parser.add_argument('--tier', help='Override the default t20 operations / t200 page tier')
parser.add_argument('--write-percent', type=int, choices=[0, 5, 15, 30], help='Frozen original W3 schedule used with mixed')
parser.add_argument('--state-gate', action='store_true', help='Verify actual final database state with the source model inside the profile lease')
args = parser.parse_args()
assert args.phase != 'sp' or args.bundle
batch = HERE / 'profiles' / ('littlex-batch-' + str(time.time_ns()))
batch.mkdir(parents=True)
summary = []
passed = set()
if args.skip_passed_summary:
    passed = {(r['implementation'], r['operation'], r['tier'], r['phase']) for r in json.loads(args.skip_passed_summary.read_text()) if r.get('status') == 'PASS'}
for implementation in args.implementations:
    for operation in args.operations:
        tier = args.tier or ('t200' if operation == 'feed_page' else 't20')
        if (implementation, operation, tier, args.phase) in passed:
            continue
        label = '-'.join([tier, operation, implementation, args.phase])
        if operation == 'mixed':
            assert args.write_percent is not None
            label += '-w' + str(args.write_percent)
        inputs = HERE / 'profile-inputs' / (label + '-' + str(time.time_ns()))
        out = batch / label
        commands = [[sys.executable, str(HERE / 'littlex/profile_commands.py'), '--tier', tier, '--operation', operation, '--implementation', implementation, '--phase', args.phase, '--out', str(inputs)]]
        if operation == 'mixed':
            commands[0] += ['--write-percent', str(args.write_percent)]
        if args.build_snapshot:
            commands[0] += ['--build-snapshot', str(args.build_snapshot.resolve())]
        if args.bundle:
            commands[0] += ['--bundle', str(args.bundle.resolve())]
        commands.append([sys.executable, str(HERE / 'profile_mysql.py'), '--command-json', str(inputs / 'command.json'), '--prepare-command-json', str(inputs / 'prepare-command.json'), '--database', 'jac_lx_' + tier + '_20261020', '--out', str(out), '--delay-ms', '2'])
        if args.state_gate:
            assert (HERE / 'littlex/verify_profile_state.py').exists()
            commands[-1] += ['--after-command-json', str(inputs / 'after-command.json')]
        commands.append([sys.executable, str(HERE / 'analyze_mysql_profile.py'), str(out)])
        if args.bundle:
            commands[-1] += ['--generated-sources-json', str(inputs / 'generated-sources.json')]
        commands.append([sys.executable, str(HERE / 'littlex/verify_outputs.py'), '--tier', tier, '--plan', str(inputs / 'plan.json'), '--results', str(out / 'run/full-results.jsonl.gz'), '--out', str(out / 'independent-results.json')])
        row = {'implementation': implementation, 'operation': operation, 'tier': tier, 'phase': args.phase, 'inputs': str(inputs), 'out': str(out), 'commands': []}
        if operation == 'mixed':
            row['write_percent'] = args.write_percent
        summary.append(row)
        for i, command in enumerate(commands):
            result = subprocess.run(command, capture_output=True, text=True)
            (batch / (label + '-' + str(i) + '.stdout')).write_text(result.stdout)
            (batch / (label + '-' + str(i) + '.stderr')).write_text(result.stderr)
            row['commands'].append({'argv': command, 'returncode': result.returncode})
            if i == 0 and result.returncode == 0 and args.state_gate and not (inputs / 'after-command.json').exists():
                after = [sys.executable, str(HERE / 'littlex/verify_profile_state.py'), '--tier', tier,
                         '--implementation', implementation, '--plan', str(inputs / 'plan.json'),
                         '--results', '{profile_output}/full-results.jsonl.gz',
                         '--out', '{profile_output}/state-verification.json', '--lease-held']
                (inputs / 'after-command.json').write_text(json.dumps(after, indent=2) + '\n')
            (batch / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
            if result.returncode:
                row['status'] = 'failed-stage'
                break
        else:
            row['status'] = 'PASS'
        (batch / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(label, row['status'], flush=True)
print(batch, flush=True)
