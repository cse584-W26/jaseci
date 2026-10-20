"""Offline comparison of matched W2 cohort sample sizes and reset boundaries."""
import csv,json,statistics
from pathlib import Path
R=Path(__file__).resolve().parents[1]
RUNS={'none':'20261019T212946Z-matched-none','stage':'20261019T212507Z-stage','duration':'20261019T212529Z-duration','function':'20261019T212828Z-function'}
out=[]
for mode,run in RUNS.items():
 d=json.loads((R/'littlex/w2-investigation'/run/'complete.json').read_text())
 for rec in d['records']:
  arm,op=rec['arm'],rec['operation']
  if mode=='none':
   p=R/'littlex/w2-investigation'/run/f'1-{arm}'/op/'raw.csv'
   rows=list(csv.DictReader(p.open()))
  else:
   p=Path(rec['summary']).with_name('profile.json');rows=json.loads(p.read_text())['rows']
  assert len(rows)==100,(mode,arm,op,len(rows))
  item={'mode':mode,'arm':arm,'operation':op,'samples':len(rows),'raw':str(p.relative_to(R))}
  for key in ['client_ms','server_ms']:
   vals=[float(x[key]) for x in rows];item[key]={'median':statistics.median(vals),'mean':statistics.mean(vals)}
  out.append(item)
for x in out:
 base=next(y for y in out if y['mode']=='none' and y['arm']==x['arm'] and y['operation']==x['operation'])
 x['client_median_ratio_to_none']=x['client_ms']['median']/base['client_ms']['median']
(R/'write-investigation/matched-overhead.json').write_text(json.dumps(out,indent=2)+'\n')
for x in out:print(x['mode'],x['arm'],x['operation'],round(x['client_ms']['median'],3),round(x['server_ms']['median'],3),round(x['client_median_ratio_to_none'],3))
