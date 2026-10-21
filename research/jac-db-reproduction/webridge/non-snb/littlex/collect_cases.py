#!/usr/bin/env python3
"""Select only actually activated, correctness-passing generated littleX APIs."""
import pathlib,json,hashlib,subprocess,sys
H=pathlib.Path(__file__).resolve().parent;selected={};failures=[]
def consider(case,receipt,frontend=None):
 case=pathlib.Path(case);m=json.loads((case/'metadata.json').read_text());impl=m['implementation'];inp=json.loads((pathlib.Path(m['snapshot'])/'input.json').read_text());key=m['region']or(inp['op']+'/business'if impl=='LittleXPruned'and inp['op'].startswith('feed')else inp['op']);selected.setdefault(impl,{})[key]={'case':str(case),'receipt':str(receipt),'tier':m['database'].split('_')[2],'frontend':frontend or {'kind':'original compiler frontend'}}
for p in sorted(H.glob('pipeline-*/summary.json')):
 for r in json.loads(p.read_text()):
  if r['status'].startswith('success')and r.get('activation',{}).get('region',{}).get('sp_enabled_at_end')and r['activation']['status_delta'].get('Com_call_procedure',0)>0:consider(r['case'],p,{'kind':'explicit frontend compatibility repair','details':r['frontend_repair']}if r.get('frontend_repair')else None)
  elif r['status']!='running':failures.append({'receipt':str(p),'case':r.get('case'),'status':r['status'],'failed_stage':r.get('failed_stage'),'error':r.get('error'),'frontend_repair':r.get('frontend_repair')})
for p in sorted(H.glob('compiler-retry-*/summary.json')):
 r=json.loads(p.read_text())
 if r['status'].startswith('PASS')and r.get('activation',{}).get('sp_enabled_at_end')and r.get('session_status_delta',{}).get('Com_call_procedure',0)>0:consider(r['case'],p,{'kind':'explicit frontend compatibility repair','overlay':r['overlay']})
for p in sorted(H.glob('emitted-recovery-*/summary.json')):
 for r in json.loads(p.read_text()):
  if r['status'].startswith('PASS')and r.get('activation',{}).get('sp_enabled_at_end')and r.get('session_status_delta',{}).get('Com_call_procedure',0)>0:consider(r['case'],p,{'kind':'actual emitted-artifact recovery after synthesis process failure','original_failure':r['original_failure'],'frontend':r.get('frontend')})
manifest={'selected':selected,'original_and_repaired_stage_evidence':failures};key=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest();out=H/'selected-cases'/key;out.mkdir(parents=True,exist_ok=True);(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');bundles={}
for impl,ops in selected.items():
 cases={op:r['case']for op,r in ops.items()};p=out/(impl+'-cases.json');p.write_text(json.dumps(cases,indent=2)+'\n');bundle=out/(impl+'-bundle')
 if not bundle.exists():subprocess.run([sys.executable,str(H/'make_bundle.py'),'--cases',str(p),'--out',str(bundle)],check=True,capture_output=True)
 (bundle/'selection-provenance.json').write_text(json.dumps(ops,indent=2)+'\n');bundles[impl]=str(bundle)
(out/'bundle-map.json').write_text(json.dumps(bundles,indent=2)+'\n');(H/'selected-cases.json').write_text(json.dumps({'manifest':str(out/'manifest.json'),'bundle_map':str(out/'bundle-map.json')},indent=2)+'\n');print(out)
