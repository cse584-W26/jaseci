#!/usr/bin/env python3
"""Interleaved historical W2 cohorts plus separate instrumented write controls."""
import argparse,csv,hashlib,json,os,subprocess
from datetime import datetime,timezone
import psycopg
from psycopg import sql
import run as lx
OPS=['like','follow','create_tweet']
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['baseline','stage','duration','spans','function','final-baseline','matched-none'],required=True);a=parser.parse_args();baseline_mode=a.mode in ('baseline','final-baseline','matched-none');warm=100 if a.mode=='matched-none' else 110;timed=100 if a.mode=='matched-none' else 500
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');out=lx.HERE/'w2-investigation'/(stamp+'-'+a.mode);out.mkdir(parents=True);records=[]
 (out/'provenance.json').write_text(json.dumps(dict(runtime_commit=subprocess.check_output(['git','-C',str(lx.SOURCE),'rev-parse','HEAD'],text=True).strip(),runtime_source=str(lx.SOURCE),jac_binary=str(lx.BIN),app_source=str(lx.APP_SOURCE),app_sha256=hashlib.sha256((lx.APP_SOURCE/'app.jac').read_bytes()).hexdigest(),sql_python=str(lx.SQL_PYTHON),driver_python=str(lx.DRIVER_PYTHON),dependency_provenance=str(lx.ROOT/'runtime/littlex-lock-provenance.json')),indent=2))
 if a.mode=='final-baseline':
  provenance=json.loads((out/'provenance.json').read_text());provenance['fixture_runtime_commit']=provenance['runtime_commit'];provenance['runtime_commit']=subprocess.check_output(['git','-C',str(lx.ROOT.parent/'jac-db/jac'),'rev-parse','HEAD'],text=True).strip();provenance['runtime_source']=str(lx.ROOT.parent/'jac-db/jac');provenance['jac_binary']=str(lx.ROOT/'runtime/bin/jac314');(out/'provenance.json').write_text(json.dumps(provenance,indent=2))
 env=lx.environment();env.update(PERF='1',JAC_STREAM_LATERAL='1',JAC_SQL_ACL='1',JAC_FUSED_FEED='1',JAC_STICKY_DENY='1',JAC_RO_WALKERS='');env.pop('JAC_LAZY_TXN',None);env.pop('JAC_EDGE_ONLY_DIRTY',None)
 seed=lx.HERE/'dataset/t20_seed.json'
 groups=[(r,arm) for r,arms in enumerate([['postgres','jaseci'],['jaseci','postgres'],['postgres','jaseci']],1) for arm in arms] if a.mode=='baseline' else [(1,'jaseci')] if a.mode in ('spans','function','final-baseline') else [(1,'postgres'),(1,'jaseci')]
 with lx.fixture_lock():
  for roundno,arm in groups:
   cell=out/(str(roundno)+'-'+arm);cell.mkdir();p=None;e=env.copy();admin=None;previous=None;db=None
   try:
    if arm=='jaseci':app,tokens,reset=lx.fixture('t20',seed,e);db=reset['database'];e['JAC_PG_APP_DIR']=str(app);port=18120;route='/healthz';cmd=[lx.BIN,'start','main.jac','-p',str(port),'--no-client'];dsn=f'host={lx.SOCK} user=jac dbname=postgres'
    else:
     app=lx.HERE/'postgres';tokens=cell/'tokens';tokens.mkdir();db=lx.SQL_DB;port=18121;route='/docs';dsn=lx.SQL_ADMIN_DSN;reset={'method':'original SQL loader TRUNCATE/reseed'}
     lx.command([lx.SQL_PYTHON,app/'loader.py',seed],e,log=cell/'seed.log')
     for script,target in [('mint_tokens.py','tokens.postgres.json'),('export_targets.py','targets.postgres.json')]:lx.command([lx.DRIVER_PYTHON,lx.HERE/'harness'/script,'--engine','postgres','--output',tokens/target],e,log=cell/(script+'.log'))
     cmd=['taskset','-c','6-13',lx.SQL_PYTHON,'-m','uvicorn','app:app','--host','127.0.0.1','--port',str(port),'--no-access-log']
    admin=psycopg.connect(dsn,autocommit=True);cfg=admin.execute('SELECT setconfig FROM pg_db_role_setting WHERE setrole=0 AND setdatabase=(SELECT oid FROM pg_database WHERE datname=%s)',(db,)).fetchone();previous=next((v.split('=',1)[1] for v in (cfg[0] if cfg else []) if v.startswith('log_min_duration_statement=')),None)
    admin.execute(sql.SQL('ALTER DATABASE {} SET log_min_duration_statement TO {}').format(sql.Identifier(db),sql.Literal('0' if a.mode=='duration' else '-1')))
    if not baseline_mode:e['JAC_STAGE_HEADERS']='1';e['PROF_TIMERS']='1'
    else:e.pop('JAC_STAGE_HEADERS',None);e.pop('PROF_TIMERS',None)
    if a.mode=='final-baseline':
     final_bin=lx.ROOT/'runtime/bin/jac314';cmd=[final_bin,'start','main.jac','-p','18120','--no-client'];e['JAC_PG_BIN']=str(final_bin)
     for k in ('JAC_STREAM_LATERAL','JAC_SQL_ACL','JAC_FUSED_FEED','JAC_STICKY_DENY','JAC_RO_WALKERS'):e.pop(k,None)
    if a.mode in ('spans','function'):
     e.update(PYTHONPATH=str(lx.SOURCE),JAC_NO_DEV_SOURCE='1',JAC_NO_PRECOMPILE='1',XDG_CACHE_HOME=str(lx.ROOT/'runtime/cache314-ad469'),JAC_LLVM_SHIM=str(lx.ROOT/'runtime/lib/libjacllvm.so'))
     cmd=[lx.ROOT/'runtime/venv314/bin/python',lx.ROOT/'profiling/launch_jac.py','--output-dir',cell/'functions','--mode','spans' if a.mode=='spans' else 'both','--warmups','100','--limit','100','--operations','like_tweet,follow_user,create_tweet','--','start','main.jac','-p','18120','--no-client']
    p=lx.launch(cmd,app,e,cell/'server.log',port,route);initial=lx.counts(arm,app,e);assert initial==dict(tweets=2000,follows=5000,likes=0);state=initial.copy()
    for op in OPS:
     folder=cell/op;folder.mkdir();before=state.copy()
     if baseline_mode:
      lx.command([lx.DRIVER_PYTHON,lx.HERE/'harness/write_run.py','--engines',arm,'--tokens-dir',tokens,'--url-'+arm,'http://127.0.0.1:'+str(port),'--ops',op,'--seed',seed,'--warmup',str(warm),'--requests',str(timed),'--output',folder/'results.csv','--raw-csv',folder/'raw.csv'],e,log=folder/'driver.log')
      rows=list(csv.DictReader((folder/'results.csv').open()));assert len(rows)==1 and rows[0]['oracle_ok']=='True' and rows[0]['oracle_actual']==str(warm+timed) and rows[0]['errors']=='0';assert sum(1 for _ in csv.DictReader((folder/'raw.csv').open()))==timed;key={'like':'likes','follow':'follows','create_tweet':'tweets'}[op];state[key]+=warm+timed;detail=dict(rows=rows)
     else:
      script='littlex_write_profile.py' if arm=='jaseci' else 'littlex_sql_write_profile.py';tag='littlex-w2/'+out.name+'/'+cell.name+'/'+op
      command=[lx.DRIVER_PYTHON,lx.ROOT/'scripts'/script,'--tag',tag,'--tier','t20','--operation',op,'--tokens-dir',tokens,'--pid',str(p.pid),'--seed',seed,'--pause','0']
      if arm=='jaseci':command+=['--app-dir',app,'--jac-bin',lx.BIN,'--database',db]
      if a.mode!='duration':command+=['--duration-off']
      lx.command(command,e,log=folder/'profile.log');summary=json.loads((lx.ROOT/'results'/tag/'summary.json').read_text());assert summary['oracle_ok'];key={'like':'likes','follow':'follows','create_tweet':'tweets'}[op];state[key]+=200;detail=dict(tag=tag,summary=str(lx.ROOT/'results'/tag/'summary.json'))
     actual=lx.counts(arm,app,e);assert actual==state,(actual,state)
     record=dict(mode=a.mode,round=roundno,arm=arm,operation=op,reset=reset,state_before=before,state_after=actual,server_pid=p.pid,server_affinity=sorted(os.sched_getaffinity(p.pid)),driver_affinity=sorted(os.sched_getaffinity(0)),environment={k:v for k,v in e.items() if k.startswith('JAC_') or k in ('PROF_TIMERS','PERF')},**detail);records.append(record);(folder/'complete.json').write_text(json.dumps(record,indent=2));(out/'progress.json').write_text(json.dumps(records,indent=2));print('PASS',a.mode,len(records),roundno,arm,op,flush=True)
   finally:
    lx.stop(p)
    if admin:
     if previous is None:admin.execute(sql.SQL('ALTER DATABASE {} RESET log_min_duration_statement').format(sql.Identifier(db)))
     else:admin.execute(sql.SQL('ALTER DATABASE {} SET log_min_duration_statement TO {}').format(sql.Identifier(db),sql.Literal(previous)))
     admin.close()
 (out/'complete.json').write_text(json.dumps(dict(mode=a.mode,records=records),indent=2));print('Complete',out,flush=True)
if __name__=='__main__':main()
