"""Plan or explicitly prepare the exact historical littleX Jac source runtime.

Execute only in the orchestrator's exclusive setup window between timing runs.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
COMMIT='ad469c9889dabcdf70bbf6cfc033c0f8a3d0399e'
SOURCE=ROOT/'runtime/ad469-source'
WRAPPER=ROOT/'runtime/bin/jac314-ad469'
CONTROL={
    'PERF':'1','JAC_ACCESS_LOG':'0','JAC_REPORT_ECHO':'0',
    'JAC_API_LEAN_RESPONSE':'1','JAC_TIMING_HEADERS':'1','JAC_RO_WALKERS':'',
    'JAC_PG_POOL':'1','JAC_PG_ENSURE_CACHE':'1','JAC_PG_DRIVER':'psycopg',
    'JAC_PROMOTED_PREDICATES':'1','JAC_STREAM_LATERAL':'1','JAC_SQL_ACL':'1',
    'JAC_FUSED_FEED':'1','JAC_STICKY_DENY':'1',
}
UNSET=['JAC_LAZY_TXN','JAC_EDGE_ONLY_DIRTY','JAC_STAGE_HEADERS','JAC_DB_URL']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    plan={'commit':COMMIT,'source':str(SOURCE),'wrapper':str(WRAPPER),
          'python':str(ROOT/'runtime/venv314/bin/python'),
          'compiler_cache':str(ROOT/'runtime/cache314-ad469'),
          'control_env':CONTROL,'unset':UNSET,
          'source_recipe':'DBHarness/session0901/final/final_runner.sh:338 + harness/profiling/start_pg.sh PERF block',
          'semantic_note':'At ad469 LAZY_TXN unset disables lazy transactions. EDGE_ONLY_DIRTY unset defaults ON for PgStore; it does not force the optimization off.',
          'actions':['git worktree add --detach exact commit','write independent wrapper',
                     'verify import source identity','run --version and check smoke',
                     'prewarm native/client/server imports without HTTP or database']}
    print(json.dumps(plan,indent=2),flush=True)
    if not args.execute:return
    logs=ROOT/'logs/historical-ad469-setup'
    logs.mkdir(parents=True,exist_ok=True)
    if not SOURCE.exists():
        subprocess.run(['git','-C',str(ROOT.parent/'jac-db'),'worktree','add','--detach',str(SOURCE),COMMIT],check=True)
    got=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()
    if got!=COMMIT:raise RuntimeError(f'Existing historical worktree has wrong commit: {got}')
    if subprocess.check_output(['git','-C',str(SOURCE),'status','--porcelain'],text=True).strip():
        raise RuntimeError('Historical source worktree must be clean')
    WRAPPER.write_text('''#!/usr/bin/env bash
set -euo pipefail
TASK_RUNTIME_DIR="/home/baichuan/jaseci/reproduction/runtime"
export PYTHONPATH="$TASK_RUNTIME_DIR/ad469-source/jac${PYTHONPATH:+:$PYTHONPATH}"
export JAC_NO_DEV_SOURCE=1
export JAC_NO_PRECOMPILE=1
export XDG_CACHE_HOME="$TASK_RUNTIME_DIR/cache314-ad469"
export JAC_CACHE_HOME="${JAC_CACHE_HOME:-$TASK_RUNTIME_DIR/dbcache-ad469}"
export JAC_LLVM_SHIM="${JAC_LLVM_SHIM:-$TASK_RUNTIME_DIR/lib/libjacllvm.so}"
exec "$TASK_RUNTIME_DIR/venv314/bin/python" -m jaclang "$@"
''')
    WRAPPER.chmod(0o755)
    env={key:value for key,value in os.environ.items() if not key.startswith('JAC_')}
    env.update(CONTROL)
    env.update(PYTHONPATH=str(SOURCE/'jac'),JAC_NO_DEV_SOURCE='1',JAC_NO_PRECOMPILE='1',
               XDG_CACHE_HOME=str(ROOT/'runtime/cache314-ad469'),
               JAC_CACHE_HOME=str(ROOT/'runtime/dbcache-ad469'),
               JAC_LLVM_SHIM=str(ROOT/'runtime/lib/libjacllvm.so'),
               GLIBC_TUNABLES='glibc.rtld.execstack=2',PYTHONUNBUFFERED='1')
    commands=[
        ('source-identity',[str(ROOT/'runtime/venv314/bin/python'),'-c',
                            f'import jaclang; from pathlib import Path; p=Path(jaclang.__file__).resolve(); print(p); assert p.is_relative_to(Path({str(SOURCE)!r}).resolve())']),
        ('version',[str(WRAPPER),'--version']),
        ('check-smoke',[str(WRAPPER),'check',str(ROOT/'runtime/smoke.jac')]),
        ('prewarm',[str(ROOT/'runtime/venv314/bin/python'),'-c',
                    'import jaclang; print("source:",jaclang.__file__,flush=True); import jaclang.compiler.passes.native; import jaclang.runtimelib.client.vite_client_bundle; import jaclang.scale.server.serve; print("ad469-prewarm: ok")']),
    ]
    for label,command in commands:
        print('RUN',label,flush=True)
        with (logs/f'{label}.log').open('w') as handle:
            subprocess.run(command,cwd=ROOT/'runtime',env=env,stdout=handle,stderr=subprocess.STDOUT,check=True)
    record={**plan,'completed_utc':datetime.now(timezone.utc).isoformat(),
            'wrapper_sha256':hashlib.sha256(WRAPPER.read_bytes()).hexdigest(),
            'environment':{key:value for key,value in env.items() if key.startswith('JAC_')},
            'logs':str(logs)}
    (ROOT/'runtime/ad469-setup.json').write_text(json.dumps(record,indent=2))
    print('Historical runtime prepared:',WRAPPER,flush=True)


if __name__=='__main__':main()
