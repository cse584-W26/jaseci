#!/usr/bin/env python3
"""Run original pipeline sequentially, retaining each actual stage outcome."""
import pathlib,subprocess,json,sys,time,hashlib,os
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];I=B/'integration';q=sys.argv[1];case=I/'cases'/json.loads((H/'selected-cases.json').read_text())[q];receipt={'query':q,'started_unix':time.time(),'stages':[]};dest=H/('pipeline-'+q+'.json');assert not dest.exists(),'Preserve existing ledger'
def run(stage,cmd):
 t=time.time();p=subprocess.run(cmd);entry={'stage':stage,'command':cmd,'returncode':p.returncode,'started_unix':t,'ended_unix':time.time()};receipt['stages'].append(entry);dest.write_text(json.dumps(receipt,indent=2)+'\n');return p.returncode==0
for stage in (['record','replay','synth','install'] if os.environ.get('SNB_PIPELINE_NO_OPT')=='1'else['record','replay','synth','install','optimized']):
 cmd=[sys.executable,str(H/'webridge.py'),q,stage]
 if stage=='synth':
  graphs=sorted(case.glob('replay-*/graph.json'));assert len(graphs)==1,graphs;cmd.append(str(graphs[0]));receipt['graph_sha256']=hashlib.sha256(graphs[0].read_bytes()).hexdigest()
 if stage=='install':
  # Dedicated fixture name is the only installer adaptation; generated procedure SQL stays unchanged.
  meta=json.loads((case/'metadata.json').read_text());d=case/'generated/sql'/meta['api'];files=[d/'graph-SP-function.sql',*sorted(d.glob('graph-SP-*_sp_*.sql'))];sql=b'\n'.join(x.read_bytes()for x in files);out=case/('install-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));out.mkdir();(out/'source-hashes.json').write_text(json.dumps({str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in files},indent=2));cmd=['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot','jac_snb_six_20261020'];p=subprocess.run(cmd,input=sql,capture_output=True);(out/'stdout.log').write_bytes(p.stdout);(out/'stderr.log').write_bytes(p.stderr);receipt['stages'].append({'stage':stage,'command':cmd,'returncode':p.returncode,'generated_sql_unchanged':True});dest.write_text(json.dumps(receipt,indent=2)+'\n');ok=p.returncode==0
 else:ok=run(stage,cmd)
 if not ok:receipt['status']='failed-'+stage;dest.write_text(json.dumps(receipt,indent=2)+'\n');raise SystemExit(1)
receipt['status']='installed-awaiting-guarded-call' if os.environ.get('SNB_PIPELINE_NO_OPT')=='1' else 'selected-input-pipeline-passed';dest.write_text(json.dumps(receipt,indent=2)+'\n')
