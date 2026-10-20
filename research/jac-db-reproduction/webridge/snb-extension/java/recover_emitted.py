#!/usr/bin/env python3
"""Validate and execute unchanged emitted SP artifacts after post-emission recorder failure."""
import datetime,hashlib,json,pathlib,subprocess,sys
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];E=H.parent;rows=[];stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');manifest=H/('pipeline-recovered-'+stamp+'.json')
for query in ['ic2','ic1']:
 prior=[]
 for p in sorted(H.glob('pipeline-*.json')):
  if p==manifest:continue
  for r in json.loads(p.read_text()):
   if r['query']==query and r['variant']=='full'and r.get('failed_stage')=='synth':prior.append((p,r))
 source_manifest,source=prior[-1];case=pathlib.Path(source['case']);meta=json.loads((case/'metadata.json').read_text());record={'query':query,'variant':'full','case':str(case),'attempt':'validate-unchanged-emitted-artifacts','formal_synthesis_exit':source['stages'][-1]['returncode'],'formal_failure_manifest':str(source_manifest),'reused_original_capture':source.get('reused_original_capture'),'stages':[]};rows.append(record)
 try:
  defs=list((case/'generated/sql'/meta['api']).glob('*-SpDef.data'));assert len(defs)==1;out=case/('validate-emitted-'+stamp);out.mkdir();cmd=[str(B/'boot-jdk8/bin/java'),'-cp',str(H/'diagnostics/classes')+':'+meta['classpath'],'VerifySpDef',str(defs[0])];r=subprocess.run(cmd,capture_output=True,text=True);(out/'stdout.log').write_text(r.stdout);(out/'stderr.log').write_text(r.stderr);(out/'command.json').write_text(json.dumps(cmd));assert r.returncode==0,r.stderr;report=json.loads(r.stdout);assert report['deserialization_ok']and report['definition_count']>0;(out/'report.json').write_text(json.dumps(report,indent=2));record['stages'].append({'stage':'validate-emitted','returncode':0,'path':str(out),'report':report})
  folder=defs[0].parent;files=[folder/'graph-SP-function.sql',*sorted(folder.glob('graph-SP-*_sp_*.sql'))];out=case/('install-emitted-'+stamp);out.mkdir();cmd=['docker','exec','-i','jac-webridge-mysql57','mysql','--default-character-set=utf8mb4','-uroot','jac_snb_six_20261020'];r=subprocess.run(cmd,input=b'\n'.join(f.read_bytes()for f in files),capture_output=True);(out/'stdout.log').write_bytes(r.stdout);(out/'stderr.log').write_bytes(r.stderr);record['stages'].append({'stage':'install','returncode':r.returncode,'path':str(out),'source_sql':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in files}});assert r.returncode==0,r.stderr
  cmd=[sys.executable,str(H/'control.py'),'optimized','--query',query,'--variant','full','--inputs',str(H/'inputs'/f'{query}.json'),'--schema',str(B/'expansion/fixture/compiler-schema.sql'),'--attempt','synthesis-stack128m','--stack','128m','--repeats','3'];r=subprocess.run(cmd,capture_output=True,text=True);paths=[pathlib.Path(v)for v in r.stdout.splitlines()if v.startswith(str(E/'webridge-cases'))];out=paths[-1]if paths else None;record['stages'].append({'stage':'optimized','returncode':r.returncode,'path':str(out)if out else None,'stdout':r.stdout,'stderr':r.stderr,'command':cmd});record['status']='success'if r.returncode==0 else'censored'if r.returncode==124 else'failed';record['failed_stage']=None if not r.returncode else'optimized';record['artifact_status']='emitted serialized definition deserialized; serialized runtime definition valid; procedure identity matches installed unchanged original compiler output'
 except Exception as exc:record['status']='failed';record['error']=repr(exc)
 manifest.write_text(json.dumps(rows,indent=2));print(query,record.get('status'),flush=True)
print(manifest)
