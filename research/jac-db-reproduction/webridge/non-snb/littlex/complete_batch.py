#!/usr/bin/env python3
"""Persist the finite littleX pipeline → complete matrix → offline evidence sequence."""
import argparse,pathlib,json,subprocess,sys,time,os,importlib.util
H=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--pipeline-pid',type=int,required=True);p.add_argument('--batch',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path);p.add_argument('--selected-ready',action='store_true');p.add_argument('--replacement-list',type=pathlib.Path,default=H/'replacement-summaries.json');a=p.parse_args();a.out=a.out or H/'completion'/str(time.time_ns());a.out.mkdir(parents=True,exist_ok=False);events=[]
def save(status,**extra):
 d=dict(status=status,events=events,wall_ns=time.time_ns(),**extra);tmp=a.out/'status.tmp';tmp.write_text(json.dumps(d,indent=2)+'\n');tmp.replace(a.out/'status.json')
def run(label,argv):
 d=a.out/label;d.mkdir();(d/'command.json').write_text(json.dumps(argv,indent=2)+'\n');events.append(dict(stage=label,status='running',start_ns=time.time_ns()));save('running')
 with(d/'stdout.log').open('wb')as out,(d/'stderr.log').open('wb')as err:r=subprocess.run(argv,stdout=out,stderr=err)
 events[-1].update(returncode=r.returncode,end_ns=time.time_ns(),status='PASS'if r.returncode==0 else'failed');save('running');assert r.returncode==0,(label,r.returncode)
 return d
try:
 save('waiting for existing finite genuine pipeline',pipeline_pid=a.pipeline_pid)
 while True:
  proc=pathlib.Path('/proc')/str(a.pipeline_pid)
  if not proc.exists():break
  if 'State:\tZ'in(proc/'status').read_text():break
  assert 'run_pipeline_batch.py'in(proc/'cmdline').read_text().replace('\0',' '),'PID was reused'
  time.sleep(10)
 rows=json.loads((a.batch/'summary.json').read_text());expected={impl+'-'+op for impl in ['LittleXSql','LittleXFull','LittleXPruned']for op in ['follow','create_tweet','like','feed_page','feed']};assert expected<={r['stage']for r in rows},'Finite pipeline batch is incomplete'
 if not a.selected_ready:
  run('emitted-artifact-recovery',[sys.executable,str(H/'recover_emitted.py')])
  run('collect-cases',[sys.executable,str(H/'collect_cases.py')])
 pointer=json.loads((H/'selected-cases.json').read_text());snapshot=json.loads((H/'final-build-snapshot.json').read_text())['path'];timing=H/'timing'/('complete-'+str(time.time_ns()))
 run('matrix-and-references',[sys.executable,str(H/'run_matrix_groups.py'),'--build-snapshot',snapshot,'--bundle-map',pointer['bundle_map'],'--out',str(timing)])
 normalized=H/'normalized-results.json';run('normalize',[sys.executable,str(H/'normalize_results.py'),str(timing/'summary.json'),'--out',str(normalized),'--require-complete','--replacement-list',str(a.replacement_list)])
 run('cycle-index',[sys.executable,str(H/'build_cycle_evidence.py'),'--normalized',str(normalized)])
 run('summary',[sys.executable,str(H/'summarize.py')])
 # Chunking, compression and final hashes are CPU/I/O work and share the host lease.
 spec=importlib.util.spec_from_file_location('measurement_lease',H.parent/'measurement_lease.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 with module.lease('littleX final public evidence export',a.out/'public-export.lease.json'):run('public-manifest',[sys.executable,str(H/'public_manifest.py')])
 save('completed',normalized=str(normalized),timing=str(timing),public_manifest=str(H/'PUBLIC_FILES.json'));print(a.out,flush=True)
except BaseException as e:
 save('failed; inspect preserved stage logs',error=repr(e));raise
