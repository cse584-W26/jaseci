"""Profile presently ready immutable cases; retain unsuccessful stages as pending/failed."""
import pathlib,json,subprocess,sys,time
R=pathlib.Path(__file__).resolve().parent;W=R.parents[1];jobs=[]
for x in json.loads((W/'snb-extension/java/case-status.json').read_text()):
 if x['selected_case']and x['status']in ['success','failed']:jobs.append((x['query'],x['variant'],x['selected_case'],'baseline,sp'if x['status']=='success'else'baseline'))
for x in json.loads((W/'expansion/set-sql/case-status.json').read_text()):
 if x['status']=='selected-input-genuine-pipeline-passed':jobs.append((x['query'],'conventional',x['case_path'],'baseline,sp'))
for q,kind,case,phases in jobs:
 previous=[]
 for p in(R/'results'/q).glob('*/analysis.json'):
  try:a=json.loads(p.read_text())
  except json.JSONDecodeError:continue
  if a['case']['kind']==kind and a['case'].get('phases')==phases:previous.append(a)
 if previous:continue
 out=R/'results'/q/(kind+'-'+time.strftime('%H%M%S'));cmd=[sys.executable,str(R/'run.py'),'--query',q,'--kind',kind,'--case',case,'--phases',phases,'--out',str(out)];print(json.dumps({'start':cmd}),flush=True);r=subprocess.run(cmd,capture_output=True,text=True);(out/'batch.stdout').write_text(r.stdout);(out/'batch.stderr').write_text(r.stderr)
 if r.returncode==0:
  r=subprocess.run([sys.executable,str(R/'analyze.py'),str(out)],capture_output=True,text=True);(out/'analysis.stdout').write_text(r.stdout);(out/'analysis.stderr').write_text(r.stderr)
 print(json.dumps({'query':q,'kind':kind,'phases':phases,'returncode':r.returncode,'out':str(out)}),flush=True)
