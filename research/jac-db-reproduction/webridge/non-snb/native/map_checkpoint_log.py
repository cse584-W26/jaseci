"""Retain actual checkpoint log events overlapping the completed quiet sweep."""
import pathlib,json,re,datetime,zoneinfo,hashlib
R=pathlib.Path(__file__).resolve().parent;D=R/'tpcc-timing';lease=json.loads((D/'lease.json').read_text());lo=datetime.datetime.fromisoformat(lease['acquired_utc']).timestamp();hi=datetime.datetime.fromisoformat(lease['released_utc']).timestamp();source=R.parents[2]/'dbcache/pg/main/server.log';size=source.stat().st_size;pos=size;carry=b'';events=[];scanned=0;reached=False;zone=zoneinfo.ZoneInfo('America/New_York');pattern=re.compile(rb'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+) [A-Z]+ \[(\d+)\] LOG:  (.*)')
with source.open('rb')as stream:
 while pos>0 and scanned<128*1024**2:
  count=min(pos,1024**2);pos-=count;stream.seek(pos);data=stream.read(count)+carry;scanned+=count;lines=data.split(b'\n');carry=lines.pop(0)if pos else b'';timestamps=[]
  for line in lines:
   m=pattern.match(line)
   if not m:continue
   wall=datetime.datetime.fromisoformat(m[1].decode()).replace(tzinfo=zone).timestamp();timestamps.append(wall)
   if lo-60<=wall<=hi+120 and('checkpoint'in m[3].decode().lower()or'wal'in m[3].decode().lower()):events.append({'wall_ns':int(wall*1e9),'pid':int(m[2]),'line':line.decode(),'line_sha256':hashlib.sha256(line).hexdigest()})
  if timestamps and min(timestamps)<lo-60:reached=True;break
assert reached,'Bounded tail did not reach beginning; increase scope explicitly rather than imply completeness'
events=sorted({x['line_sha256']:x for x in events}.values(),key=lambda x:x['wall_ns']);cells=[];intervals=[];pending={}
for i,event in enumerate(events):
 if 'checkpoint starting:'in event['line']:pending[event['pid']]=(i,event)
 elif 'checkpoint complete:'in event['line']:
  start=pending.pop(event['pid'],None);intervals.append({'start_event':start[0]if start else None,'end_event':i,'start_wall_ns':start[1]['wall_ns']if start else None,'end_wall_ns':event['wall_ns'],'complete_log':event['line']})
for pid,(i,event)in pending.items():intervals.append({'start_event':i,'end_event':None,'start_wall_ns':event['wall_ns'],'end_wall_ns':None})
for s in json.loads((D/'summary.json').read_text()):
 path=R/s['path'];rows=list(map(json.loads,(path/'rows.jsonl').read_text().splitlines()));start=min(x['start_wall_ns']for x in rows);end=max(x['start_wall_ns']+int(x['client_ms']*1e6)for x in rows);cells.append({'variant':s['variant'],'class':s['label'],'delay_ms':s['delay_ms'],'first_warm_request_wall_ns':start,'last_measured_response_wall_ns':end,'checkpoint_or_WAL_log_events_inside_request_envelope':[i for i,x in enumerate(events)if start<=x['wall_ns']<=end],'overlapping_checkpoint_intervals':[i for i,x in enumerate(intervals)if(x['start_wall_ns']is None or x['start_wall_ns']<=end)and(x['end_wall_ns']is None or x['end_wall_ns']>=start)]})
result={'scope':'Actual native PostgreSQL log metadata across quiet lease; checkpoints can start before a request envelope and complete inside it','quiet_lease':lease,'source_file':str(source),'source_size_at_scan':size,'tail_bytes_scanned':scanned,'tail_reached_before_lease':reached,'boundary_context_seconds':{'before':60,'after':120},'events':events,'checkpoint_intervals':intervals,'cells':cells,'interpretation':'A temporal overlap describes concurrent activity. Checkpoint completion durations aggregate its entire lifetime and do not establish per-request causal cost.'};(D/'checkpoint-log-map.json').write_text(json.dumps(result,indent=2)+'\n');print(len(events),'checkpoint/WAL lines retained across',len(cells),'cells; scanned',scanned,'bytes')
