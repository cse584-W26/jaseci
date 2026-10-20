"""Offline per-category and per-input query ledger for the validated full port."""
import collections,gzip,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
HEADER=re.compile(r'^\d{4}-\d\d-\d\d .*?\[(\d+)\] (LOG|DETAIL|CONTEXT|WARNING|ERROR):\s*(.*)')
EVENT=re.compile(r'duration: ([\d.]+) ms\s+(execute [^:]*|statement):\s*(.*)')
def extract(path,pid):
 pending=None;events=[]
 def finish():
  nonlocal pending
  if pending:
   pending['sql']=' '.join(' '.join(pending.pop('parts')).split());events.append(pending);pending=None
 with gzip.open(path,'rt') as f:
  for line in f:
   h=HEADER.match(line)
   if h:
    if h[2]=='DETAIL' and pending and h[1]==str(pid):pending['parameters']=h[3];continue
    finish();m=EVENT.search(line)
    if m and h[1]==str(pid):pending={'parts':[m[3]],'parameters':''}
   elif pending:pending['parts'].append(line.rstrip())
 finish();return events

def category(e):
 sql=e['sql']
 if sql.startswith('SELECT n1.id'):
  edge=re.search(r"\$4 = '([^']+)'",e['parameters'])
  if not edge:raise RuntimeError('Missing edge parameter')
  direction='in' if 'AND ((e1.dst = f0.id' in sql else 'out'
  return 'hop:'+edge[1]+':'+direction
 if sql.startswith('SELECT a.id'):return 'anchor-load'
 if sql.startswith('BEGIN'):return 'begin'
 if sql.startswith('SET LOCAL'):return 'transaction-setting'
 if sql=='COMMIT':return 'commit'
 if sql.startswith('SHOW server_version'):return 'server-version'
 if sql.startswith('SELECT value FROM kv_state'):return 'schema-fingerprint'
 if sql.startswith('SELECT DISTINCT type_name'):return 'type-registry'
 if sql.startswith('SELECT doc FROM identity_users'):return 'identity'
 raise RuntimeError('Unknown actual SQL:'+sql[:150])

def main():
 rows=[json.loads(x) for x in (HERE/'java-all20-context-aligned.jsonl').read_text().splitlines()];ledger=[]
 for r in rows:
  source=HERE/'baseline-capture'/f'round{min(r["round"],1)}-input{r["idx"]:02d}.log.gz';ev=extract(source,2126112)
  expected=collections.Counter(category(e) for e in ev)
  if r['round']==0 and r['idx']==0:
   identities=extract(source,2126064);expected.update(category(e) for e in identities)
  actual=r['categories'];ok=dict(expected)==actual
  ledger.append({'round':r['round'],'idx':r['idx'],'jac':dict(expected),'java':actual,'equal':ok,'server_questions':r['server_questions']})
  if not ok:print('DIFFERENCE',r['idx'],expected,actual)
 result={'requests':len(rows),'all_category_counts_equal':all(r['equal'] for r in ledger),'rows':ledger}
 (HERE/'query-category-ledger.json').write_text(json.dumps(result,indent=2));print('all_category_counts_equal',result['all_category_counts_equal'])
 if not result['all_category_counts_equal']:raise SystemExit(1)
if __name__=='__main__':main()
