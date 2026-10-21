#!/usr/bin/env python3
"""Run genuine content-frozen WeBridge stages and independently compare committed state."""
import pathlib,json,sys,argparse,subprocess,time,hashlib,importlib.util,contextlib
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
p=argparse.ArgumentParser();p.add_argument('--lease-scope',choices=['case','stage'],default='case');p.add_argument('--tier',default='t20',choices=['t20','t50','t100','t200']);p.add_argument('--implementation',default='LittleXSql',choices=['LittleXSql','LittleXFull','LittleXPruned']);p.add_argument('--operations',nargs='+',default=['like','follow','create_tweet','feed','feed_page']);p.add_argument('--region',default='');p.add_argument('--synth-overlay',type=pathlib.Path);p.add_argument('--attempt',default='original');a=p.parse_args();run=H/('pipeline-'+str(time.time_ns()));run.mkdir();rows=[]
def cmd(argv,out):
 out.mkdir(parents=True);r=subprocess.run(argv,capture_output=True);(out/'command.json').write_text(json.dumps(argv,indent=2));(out/'stdout.log').write_bytes(r.stdout);(out/'stderr.log').write_bytes(r.stderr);return r

def state(case,out,lease_held=False):
 meta=json.loads((case/'metadata.json').read_text());db=meta['database'];graph=a.implementation!='LittleXSql';tables=['anchors','graph_types']if graph else['lx_profiles','lx_follows','lx_tweets'];receipt={}
 with(contextlib.nullcontext()if lease_held else lease('littlex independent postrequest state',out.with_suffix('.lease.json'))):
  for t in tables:
   if graph and t=='anchors':projection="JSON_OBJECT('id',id,'kind',kind,'type',arch_type,'module',arch_module,'fingerprint',fingerprint,'root',root_id,'src',src,'dst',dst,'undirected',undirected,'props',CAST(props AS JSON),'src_type',src_type,'dst_type',dst_type,'seq',seq)";order='id'
   elif t=='graph_types':projection="JSON_OBJECT('type_name',type_name,'ancestor',ancestor)";order='type_name,ancestor'
   else:
    cols={'lx_profiles':['id','username'],'lx_follows':['follower_id','followee_id'],'lx_tweets':['id','seed_id','author_id','content','created_at','likes','comments']}[t];projection='JSON_OBJECT('+','.join("'"+c+"',"+c for c in cols)+')';order=','.join(cols[:2]if t=='lx_follows'else cols[:1])
   q='SELECT '+projection+' FROM '+t+' ORDER BY '+order;r=subprocess.run(['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot','-N','-B','--raw',db],input=q.encode(),capture_output=True);assert r.returncode==0,r.stderr
   vals=[json.loads(x)for x in r.stdout.decode().split('\n')if x];blob=json.dumps(vals,sort_keys=True,separators=(',',':')).encode();receipt[t]={'rows':len(vals),'sha256':hashlib.sha256(blob).hexdigest(),'SQL':q}
 out.write_text(json.dumps(receipt,indent=2)+'\n');return receipt

def save():
 (run/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
for op in a.operations:
 regions=[a.region]if a.region else([op+'/dispatch',op+'/business']if a.implementation=='LittleXFull'and op.startswith('feed')else[''])
 for region in regions:
  label=op+('-'+region.split('/')[-1]if region else'');folder=run/label;folder.mkdir();row={'family':'littlex','tier':a.tier,'operation':op,'implementation':a.implementation,'region':region,'stages':[],'status':'running'};rows.append(row);case=None;baseline=None;baseline_result=None
  with(lease('littlex bounded complete genuine case '+label,folder/'case.lease.json')if a.lease_scope=='case'else contextlib.nullcontext()):
   try:
    base=[sys.executable,str(H/'control.py'),'baseline','--implementation',a.implementation,'--input',str(H/'inputs'/((op+'.json')if a.tier=='t20'else(a.tier+'/'+op+'.json'))),'--attempt',a.attempt+'-'+label,'--database','jac_lx_'+a.tier+'_20261020','--region',region,'--schema',str(H/'fixtures'/a.tier/('mysql-compiler-schema.sql'if a.implementation!='LittleXSql'else'mysql-schema.sql'))]
    for action in ['baseline','record','replay','synth','install','optimized']:
     with(lease('littlex atomic pipeline '+action,folder/(action+'.lease.json'))if a.lease_scope=='stage'else contextlib.nullcontext()):
      if action=='baseline':argv=base+['--lease-held']
      elif action=='install':
       meta=json.loads((case/'metadata.json').read_text());files=[case/'generated/sql'/meta['api']/'graph-SP-function.sql',*sorted((case/'generated/sql'/meta['api']).glob('graph-SP-*_sp_*.sql'))];assert len(files)>1 and all(f.exists()for f in files),'Inspect emitted compiler artifacts: no complete generated SQL set'
       with contextlib.nullcontext():
        out=folder/'install';out.mkdir();argv=['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot',meta['database']];r=subprocess.run(argv,input=b"SET SESSION sql_mode=CONCAT(@@session.sql_mode,IF(FIND_IN_SET('NO_UNSIGNED_SUBTRACTION',@@session.sql_mode),'',',NO_UNSIGNED_SUBTRACTION'));SELECT @@session.sql_mode AS installation_session_mode,@@global.sql_mode AS global_mode;\n"+b'\n'.join(f.read_bytes()for f in files)+b"\nSELECT ROUTINE_NAME,SQL_MODE FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=DATABASE() ORDER BY ROUTINE_NAME;",capture_output=True);(out/'stdout.log').write_bytes(r.stdout);(out/'stderr.log').write_bytes(r.stderr);(out/'sources.json').write_text(json.dumps([{'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}for f in files],indent=2))
      else:argv=[sys.executable,str(H/'resume_case.py'),action,str(case),'--lease-held']+(['--graph',str(graph)]if action=='synth'else[])
      if action!='install':
       r=cmd(argv,folder/action);paths=[pathlib.Path(x)for x in r.stdout.decode(errors='replace').splitlines()if x.startswith(str(H/'cases'))];out=paths[-1]if paths else None
       if out:case=out.parent;row['case']=str(case)
      row['stages'].append({'stage':action,'returncode':r.returncode,'path':str(out)if out else None,'logs':str(folder/action)});save();print(label,action,r.returncode,flush=True)
      if r.returncode and action=='synth'and a.synth_overlay:
       original_failure=str(out)if out else str(folder/action);argv=[sys.executable,str(H/'resume_case.py'),'synth',str(case),'--lease-held','--graph',str(graph),'--overlay',str(a.synth_overlay)];r=cmd(argv,folder/'synth-frontend-fix');paths=[pathlib.Path(x)for x in r.stdout.decode(errors='replace').splitlines()if x.startswith(str(H/'cases'))];out=paths[-1]if paths else None;row['frontend_repair']={'original_failure':original_failure,'overlay':str(a.synth_overlay),'scope':'explicit compatibility repair; original business SQL unchanged'};row['stages'].append({'stage':'synth-frontend-fix','returncode':r.returncode,'path':str(out)if out else None,'logs':str(folder/'synth-frontend-fix')});save()
      if r.returncode:row.update(status='failed-stage',failed_stage=action);break
      if action=='replay':graph=out/'graph.json'
      if action in ['baseline','record','optimized']:
       snapshot=state(case,folder/(action+'-state.json'),lease_held=True);result=json.loads((out/'report.json').read_text())
       if action=='baseline':baseline=snapshot;baseline_result=result['result']
       else:assert snapshot==baseline,'Committed business state differs';assert result['result']==baseline_result,'Result differs'
       if action=='optimized':row['activation']={'region':result['region'],'status_delta':result['session_status_delta'],'server_questions':result['server_questions']}
    else:row.update(status='success with frontend fix'if row.get('frontend_repair')else'success',correctness='Identical result and normalized complete business state after independent initial resets')
   except BaseException as e:row.update(status='failed-stage',error=repr(e))
   save()
print(run)
