#!/usr/bin/env python3
"""Freeze complete argv/input/source receipts for the shared real-wire/P_S collector."""
import pathlib,json,argparse,hashlib,shutil,importlib.util,time
H=pathlib.Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('t',H/'timing_command.py');t=importlib.util.module_from_spec(s);s.loader.exec_module(t)
p=argparse.ArgumentParser();p.add_argument('--build-snapshot',type=pathlib.Path);p.add_argument('--tier',choices=['t20','t50','t100','t200']);p.add_argument('--operation',default='feed',choices=['feed','feed_page','like','follow','create_tweet','mixed']);p.add_argument('--write-percent',type=int,choices=[0,5,15,30],default=0);p.add_argument('--implementation',default='LittleXSql');p.add_argument('--phase',default='baseline',choices=['baseline','sp']);p.add_argument('--bundle',type=pathlib.Path);p.add_argument('--out',type=pathlib.Path);a=p.parse_args();family='W1'if a.operation=='feed'else'W3'if a.operation in ['feed_page','mixed']else'W2';a.tier=a.tier or('t200'if family=='W3'else't20');assert family!='W3'or a.tier=='t200','Original W3 schedule uses t200';workload=str(a.write_percent if a.operation=='mixed'else 0)if family=='W3'else a.operation;plan=H/'plans'/(a.tier+'-'+family+'-'+workload+'-latency.json');items=json.loads(plan.read_text());items=items if a.operation=='mixed'else[r for r in items if r['warmup']][:10]+[r for r in items if not r['warmup']][:3];out=a.out.resolve()if a.out else H/'profile-inputs'/(a.tier+'-'+a.operation+('-'+workload if family=='W3'else'')+'-'+a.implementation+'-'+a.phase+'-'+str(time.time_ns()));out.mkdir(parents=True,exist_ok=False);(out/'classes').mkdir();(out/'source').mkdir()
build=a.build_snapshot.resolve()if a.build_snapshot else H;source=build/'source'if a.build_snapshot else H;manifest=json.loads((build/'build.json').read_text());assert manifest['returncode']==0
for name,expected in manifest.get('sources_sha256',manifest.get('sources')).items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==expected,(name,'source/class manifest mismatch')
for name,expected in manifest.get('classes_sha256',{}).items():assert hashlib.sha256((build/'classes'/name).read_bytes()).hexdigest()==expected,('Bytecode differs from compiled manifest',name)
for f in(build/'classes').glob('*.class'):shutil.copy2(f,out/'classes'/f.name)
for f in source.glob('*.java'):shutil.copy2(f,out/'source'/f.name)
shutil.copy2(build/'native-templates.json',out/'native-templates.json');shutil.copy2(build/'build.json',out/'build.json');pf=out/'plan.json';pf.write_text(json.dumps(items,indent=2)+'\n');(out/'plan-provenance.json').write_text(json.dumps({'original_plan':str(plan),'original_plan_sha256':hashlib.sha256(plan.read_bytes()).hexdigest(),'retained_plan_ordinals':[i for i,r in enumerate(json.loads(plan.read_text()))if r in items],'warmup_count':sum(r['warmup']for r in items),'measured_count':sum(not r['warmup']for r in items),'workload':family,'write_percent':a.write_percent if a.operation=='mixed'else 0 if family=='W3'else None},indent=2)+'\n');cmd=t.command(pf,out/'actual-output','jac_lx_'+a.tier+'_20261020',55337,a.phase,a.implementation,a.bundle)
for i,v in enumerate(cmd):
 if v==str(out/'actual-output'):cmd[i]='{profile_output}'
 elif v.startswith('-Dlittlex.url='):cmd[i]=v.replace('127.0.0.1:55337','{endpoint}')
 elif str(H/'classes')+':'in v:cmd[i]=v.replace(str(H/'classes')+':',str(out/'classes')+':')
cmd.insert(cmd.index('-cp'),'-Dlittlex.templates='+str(out/'native-templates.json'))
(out/'command.json').write_text(json.dumps(cmd,indent=2)+'\n');(out/'prepare-command.json').write_text(json.dumps([__import__('sys').executable,str(H/'reset_relations.py'),a.tier,'--lease-held']+(['--bundle',str(a.bundle.resolve()),'--install-receipt',str(out/'bundle-install.json')]if a.phase=='sp'else[]),indent=2)+'\n')
(out/'after-command.json').write_text(json.dumps([__import__('sys').executable,str(H/'verify_profile_state.py'),'--tier',a.tier,'--implementation',a.implementation,'--plan',str(pf),'--results','{profile_output}/full-results.jsonl.gz','--out','{profile_output}/independent-committed-state.json','--lease-held'],indent=2)+'\n')
if a.bundle:
 b=json.loads((a.bundle/'metadata.json').read_text());(out/'generated-sources.json').write_text(json.dumps([r['copied_path']for r in b['generated_sources']if r['copied_path'].endswith('.sql')],indent=2)+'\n')
(out/'source-sha256.json').write_text(json.dumps({str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest()for f in out.rglob('*')if f.is_file()},indent=2)+'\n')
print(out)
