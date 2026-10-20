"""Provision canonical runtime projections outside request transactions.

Run only after stopping Jac HTTP. This calls normal PgStore ensure methods;
no query rewriting or manual optimization SQL is introduced.
"""
import argparse
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('/home/baichuan/jaseci/reproduction')
RECEIPTS = Path(__file__).resolve().parent/'provision-receipts'
RECEIPTS.mkdir(exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, help='Existing Jac database')
    parser.add_argument('--socket', default='/tmp/jacpg-d6275e76eb')
    parser.add_argument('--user', default='jac')
    parser.add_argument('--variant', choices=['final', 'baseline'], default='final')
    parser.add_argument('--retries', type=int, default=4, help='Maximum canonical ensure calls per step in one process')
    parser.add_argument('--skip-mirrors', action='store_true', help='Reuse validated completed base mirrors from prior setup record')
    parser.add_argument('--from-step', type=int, default=0, help='Start at zero-based plan step; skipped mirrors require prior successful record')
    parser.add_argument('--execute', action='store_true', help='Perform provisioning')
    args = parser.parse_args()
    source = ROOT.parent/'jac-db/jac' if args.variant == 'final' else ROOT/'runtime/baseline-source/jac'
    plan = [
        {'method': 'ensure_mirror', 'class': name} for name in ['Person', 'Forum', 'Post', 'Comment']
    ] + [
        {'method': 'ensure_mirror_endpoint', 'class': name, 'edge': 'HasCreator', 'order_field': 'creationDate', 'outbound': True}
        for name in ['Post', 'Comment']
    ] + [
        {'method': 'ensure_root_column', 'class': 'Comment', 'edge': 'ReplyOf', 'root': 'Post'},
        {'method': 'ensure_mirror_order_index', 'class': 'Person', 'field': 'firstName', 'equality': True},
    ] + [
        {'method': method, 'edge': edge, 'node': node}
        for edge,node in [('Knows','Person'), ('HasCreator','Person'), ('ContainerOf','Post')]
        for method in (['ensure_adjacency_table','ensure_adjacency_index'] if edge == 'Knows' else ['ensure_adjacency_index'])
    ]
    prior_path = RECEIPTS/f'provision-runtime-{args.variant}.json'
    prior = json.loads(prior_path.read_text()) if prior_path.exists() else None
    record = {'skip_mirrors': args.skip_mirrors, 'from_step': args.from_step, 'source': str(source), 'source_commit': subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),
              'python': sys.version, 'database': args.database, 'socket': args.socket, 'plan': plan, 'results': []}
    print(json.dumps(record, indent=2), flush=True)
    if not args.execute:
        return
    pidfile = ROOT/'logs/jac.pid'
    if pidfile.exists():
        pid = int(pidfile.read_text())
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pass
        else:
            raise RuntimeError(f'Stop Jac HTTP first: tracked process {pid} is alive')
    os.environ.update(JAC_NO_DEV_SOURCE='1',JAC_NO_PRECOMPILE='1',JAC_PG_DRIVER='psycopg',JAC_PG_POOL='0',
                      JAC_LLVM_SHIM=str(ROOT/'runtime/lib/libjacllvm.so'),
                      XDG_CACHE_HOME=str(ROOT/'runtime'/('cache314' if args.variant == 'final' else 'cache314-baseline')))
    sys.path.insert(0, str(source))
    sys.path.insert(1, str(ROOT/'benchmark/snb/jaseci-pg'))
    import jaclang
    app = importlib.import_module('app')
    from jaclang.runtimelib.store import PgStore, ConnInfo
    record['loaded_jaclang'] = jaclang.__file__
    record['loaded_classes'] = {name: {'module': getattr(getattr(app,name),'__module__'), 'name': getattr(app,name).__name__} for name in ['Person','Forum','Post','Comment']}
    def store():
        return PgStore(conninfo=ConnInfo(unix_socket_dir=args.socket,user=args.user,database=args.database),auto_schema=False)
    try:
        if args.skip_mirrors or args.from_step:
            if not prior or prior['source_commit'] != record['source_commit'] or prior['database'] != args.database:
                raise RuntimeError('Matching previous provisioning record required to reuse base mirrors')
            globals_ = PgStore.ensure_mirror.__globals__
            for name in ['Person','Forum','Post','Comment']:
                completed = [r for r in prior['results'] if r['step'] == {'method':'ensure_mirror','class':name} and r['result'] is True]
                if not completed:
                    raise RuntimeError(f'No previous successful base mirror record for {name}')
                info = completed[-1]['mirror_info']
                cls = getattr(app,name)
                expected = globals_['_mirror_table_for'](cls)
                if expected != info:
                    raise RuntimeError(f'Mirror mapping changed for {name}')
                st = store()
                try:
                    missing = st.rows("SELECT 1 FROM anchors a WHERE a.kind = 'NodeAnchor' AND a.arch_type = :at AND NOT EXISTS (SELECT 1 FROM " + info['table'] + " m WHERE m.id = a.id) LIMIT 1", {'at':name})
                    if missing:
                        raise RuntimeError(f'Incomplete durable base mirror for {name}')
                finally:
                    st.close()
                globals_['_mirror_state'][cls] = {'ok':True,**info}
                globals_['_memo_track']([info['table']])
                record['results'].append(completed[-1] | {'reused':True})
                print(json.dumps({'reused_base_mirror':name,'mirror_info':info}),flush=True)
        for step_index, step in enumerate(plan):
            if step_index < args.from_step or (args.skip_mirrors and step['method'] == 'ensure_mirror'):
                continue
            for attempt in range(1, max(1,args.retries)+1):
                st = store()
                started = time.perf_counter()
                try:
                    assert not st.in_txn(), 'Offline setup must remain autocommit'
                    cls = getattr(app, step['class']) if 'class' in step else None
                    method = step['method']
                    if method == 'ensure_mirror':
                        result = st.ensure_mirror(cls)
                    elif method == 'ensure_mirror_endpoint':
                        info = st.mirror_info(cls)
                        result = st.ensure_mirror_endpoint(cls,step['edge'],info['cols'][step['order_field']],step['outbound'])
                    elif method == 'ensure_root_column':
                        result = st.ensure_root_column(cls,step['edge'],step['root'])
                    elif method == 'ensure_mirror_order_index':
                        info = st.mirror_info(cls)
                        result = st.ensure_mirror_order_index(cls,info['cols'][step['field']],step['equality'])
                    else:
                        result = getattr(st,method)(step['edge'],step['node'])
                    assert not st.in_txn(), 'An ensure unexpectedly opened a transaction'
                    row = {'step':step,'attempt':attempt,'result':result,'elapsed_ms':(time.perf_counter()-started)*1000}
                    if cls is not None:
                        row['mirror_info'] = st.mirror_info(cls)
                    record['results'].append(row)
                    print(json.dumps(row),flush=True)
                finally:
                    st.close()
                if result:
                    break
                if attempt >= max(1,args.retries):
                    raise RuntimeError(f'Canonical runtime refused {step} after {attempt} calls; inspect recorded results')
                delay = min(60.0, float(2 ** attempt)) + 0.1
                print(json.dumps({"retry_step":step_index,"after_seconds":delay,"next_attempt":attempt+1}),flush=True)
                time.sleep(delay)
    finally:
        stamp = time.strftime('%Y%m%dT%H%M%S') + f'-{os.getpid()}'
        output = RECEIPTS/f'provision-runtime-{args.variant}-{stamp}.json'
        if prior is not None:
            archive = RECEIPTS/f'provision-runtime-{args.variant}-before-{stamp}.json'
            archive.write_text(json.dumps(prior,indent=2))
        output.write_text(json.dumps(record,indent=2))
        prior_path.write_text(json.dumps(record,indent=2))
        print(f'Record: {output}',flush=True)


if __name__ == '__main__':
    main()
