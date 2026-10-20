"""Offline execution-shape census; preserves the first real SQL per shape."""
import argparse,collections,hashlib,json,re,gzip
from pathlib import Path
HEADER=re.compile(r'^\d{4}-\d\d-\d\d .*?\[(\d+)\] (LOG|DETAIL|CONTEXT|WARNING|ERROR):')
EVENT=re.compile(r'duration: ([\d.]+) ms\s+(execute [^:]*|statement):\s*(.*)')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('log',type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 shapes={};sequence=[];pending=None
 def finish():
  nonlocal pending
  if pending is None:return
  sql=' '.join(pending.pop('parts')).strip();sql=' '.join(sql.split());key=hashlib.sha256(sql.encode()).hexdigest();pending['shape']=key
  shape=shapes.setdefault(key,{'sql':sql,'executions':0,'duration_ms':0,'first_ordinal':len(sequence)})
  shape['executions']+=1;shape['duration_ms']+=pending['duration_ms'];sequence.append(pending);pending=None
 with (gzip.open(a.log,'rt') if a.log.suffix=='.gz' else a.log.open()) as f:
  for line in f:
   if HEADER.match(line):
    finish();m=EVENT.search(line)
    if m:pending={'pid':int(HEADER.match(line)[1]),'duration_ms':float(m[1]),'parts':[m[3].rstrip()]}
   elif pending:pending['parts'].append(line.rstrip())
 finish()
 (a.out/'shapes.json').write_text(json.dumps(sorted(shapes.values(),key=lambda d:-d['executions']),indent=2))
 (a.out/'sequence.json').write_text(json.dumps(sequence,indent=2))
 (a.out/'summary.json').write_text(json.dumps({'source':str(a.log.resolve()),'bytes':a.log.stat().st_size,'executions':len(sequence),'shapes':len(shapes),'by_pid':dict(collections.Counter(x['pid'] for x in sequence))},indent=2))
 print(json.dumps({'executions':len(sequence),'shapes':len(shapes)}))
if __name__=='__main__':main()
