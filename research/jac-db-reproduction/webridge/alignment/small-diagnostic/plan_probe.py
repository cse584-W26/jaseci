import json,subprocess,time
from pathlib import Path
p=Path(__file__).resolve().parent;case=p.parents[1]/'integration/cases/small-pruned-webridge-20261020';q=json.loads(next(case.glob('record-*/recorded-sql.json')).read_text())[0];x=json.loads((p/'input.json').read_text());args=[x['person_jid'],'Knows','Knows','Person','Person']*2+[x['person_jid'],'Person','Person']
def subst(names):
 parts=q.split('?');return ''.join(a+(names[i] if i<len(names) else '') for i,a in enumerate(parts))
def lit(s):return "'"+s.replace("'","''")+"'"
stat="SHOW SESSION STATUS WHERE Variable_name IN('Handler_read_rnd_next','Handler_read_key','Handler_read_next','Select_scan');"
sqls=[]
for label in ['literal','utf8','ascii']:
 if label=='literal':body=subst([lit(s) for s in args]);sql="SELECT 'literal-before';"+stat+'EXPLAIN FORMAT=JSON '+body+';'+body+';'+stat
 else:
  names=['q'+str(i+1) for i in range(len(args))];decl=''.join('DECLARE '+n+' VARCHAR(512) CHARACTER SET '+('ascii' if label=='ascii' and i in [0,5,10] else 'utf8mb4')+' DEFAULT '+lit(v)+';' for i,(n,v) in enumerate(zip(names,args)))
  body=subst(names);name='alignment_diag_'+label;sql='DROP PROCEDURE IF EXISTS '+name+';\nDELIMITER $$\nCREATE PROCEDURE '+name+'() BEGIN '+decl+' SELECT '+lit(label)+';'+stat+'EXPLAIN FORMAT=JSON '+body+';'+body+';'+stat+' END$$\nDELIMITER ;\nCALL '+name+'();\n'
 out=p/('plan-'+label);out.mkdir(exist_ok=True);(out/'query.sql').write_text(sql);cmd=['docker','exec','-i','jac-webridge-mysql57','mysql','-uroot','-N','-B','-r','jac_alignment'];(out/'command.json').write_text(json.dumps(cmd));t=time.monotonic();r=subprocess.run(cmd,input=sql,text=True,capture_output=True);(out/'stdout.log').write_text(r.stdout);(out/'stderr.log').write_text(r.stderr);(out/'result.json').write_text(json.dumps({'returncode':r.returncode,'wall_s':time.monotonic()-t}));print(label,r.returncode,time.monotonic()-t)
