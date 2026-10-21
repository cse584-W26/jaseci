#!/usr/bin/env python3
"""Offline exact-cents comparison of three real Java and native Jac transactions."""
import argparse,decimal,gzip,hashlib,json,pathlib
H=pathlib.Path(__file__).resolve().parent;N=H.parent/'native/tpcc-census'
MONEY={'warehouse':{1},'district':{2},'customer':{3,4},'order_line':{7},'history':{5}}
def lines(path):
 handle=gzip.open(path,'rt')if path.suffix=='.gz'else path.open()
 with handle:
  for line in handle:yield json.loads(line)
def canonical(table,row):
 for i in MONEY.get(table,set()):row[i]=format(decimal.Decimal(row[i]).quantize(decimal.Decimal('.01')),'.2f')
 return row
p=argparse.ArgumentParser();p.add_argument('--variant',default='full');a=p.parse_args();root=H/('graph-census-'+a.variant);results=[]
for path in root.glob('*/results/after/manifest.json'):
 label=path.parents[2].name;native=N/label/'after-three-state';tables=[]
 for table,entry in json.loads(path.read_text()).items():
  j=list(lines(path.parent/(table+'.jsonl')));n=list(lines(native/(table+'.canonical-cents.jsonl.gz')));j=[canonical(table,r)for r in j];assert j==n,(label,table,next(((i,x,y)for i,(x,y)in enumerate(zip(j,n))if x!=y),None),len(j),len(n))
  tables.append({'table':table,'rows':len(j),'status':'PASS','java':str(path.parent/(table+'.jsonl')),'native':str(native/(table+'.canonical-cents.jsonl.gz'))})
 rows=[json.loads(line)for line in(path.parents[1]/'requests.jsonl').read_text().splitlines()];expected=[r for r in json.loads((N/'rows.json').read_text())if r['label']==label];assert len(rows)==len(expected)==3
 for j,n in zip(rows,expected):
  payload=n['driver_result'][3]
  if j['input'].get('invalid'):assert j['result']['rolled_back'] and n['driver_result'][1]
  else:assert j['result']==payload,(label,j['result'],payload)
 results.append({'workload':label,'variant':a.variant,'tables':tables,'outputs':'All3 realoutputs PASS; declared error-envelope normalization for rollback'})
(root/'cross-native-verification.json').write_text(json.dumps(results,indent=2));print('PASS',len(results),'classes',sum(len(r['tables'])for r in results),'tables')
