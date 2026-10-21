import pathlib,json,sys,time,subprocess,importlib.util,re,shutil
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
source=H.parent/'profiles/littlex-batch-1792554690493163316/t200-mixed-LittleXPruned-baseline-w15';out=H/'mixed-state-diagnostic'/str(time.time_ns());out.mkdir(parents=True);cmd=json.loads((source/'request-command.json').read_text());i=cmd.index('LittleXTiming');plan=cmd[i+1];cmd[i+2]=str(out/'run');cmd=[re.sub(r'(jdbc:mysql://127\.0\.0\.1:)\d+/',r'\g<1>55337/',s)for s in cmd]
if not any('connectionCollation=utf8mb4_bin'in s for s in cmd):cmd=[s+'&connectionCollation=utf8mb4_bin'if s.startswith('-Dlittlex.url=')else s for s in cmd]
shutil.copy2(__file__,out/'diagnose_mixed_state.executed.py')
snapshot=pathlib.Path(json.loads((H/'final-build-snapshot.json').read_text())['path']);cp_index=cmd.index('-cp')+1;cmd[cp_index]=str(snapshot/'classes')+':'+':'.join(cmd[cp_index].split(':')[1:]);cmd=[('-Dlittlex.templates='+str(snapshot/'native-templates.json'))if x.startswith('-Dlittlex.templates=')else x for x in cmd]
(out/'request-command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with lease('littleX original mixed baseline exact committed-row diagnostic',out/'lease.json'):
 subprocess.run([sys.executable,str(H/'reset_relations.py'),'t200','--lease-held'],check=True)
 spec=importlib.util.spec_from_file_location('owned',H.parents[1]/'benchmark-comparison/owned_watchdog.py');wd=importlib.util.module_from_spec(spec);spec.loader.exec_module(wd);guard=wd.run(cmd,out/'run',timeout=120,request_limit=15,db='jac_lx_t200_20261020');assert not guard['timed_out'],guard
 r=subprocess.run([sys.executable,str(H/'verify_profile_state.py'),'--tier','t200','--implementation','LittleXPruned','--plan',plan,'--results',str(out/'run/full-results.jsonl.gz'),'--out',str(out/'verification.json'),'--lease-held'],capture_output=True);(out/'verification.stdout.log').write_bytes(r.stdout);(out/'verification.stderr.log').write_bytes(r.stderr);(out/'status.json').write_text(json.dumps({'verification_returncode':r.returncode,'source':str(source)},indent=2)+'\n');print(out,flush=True)
