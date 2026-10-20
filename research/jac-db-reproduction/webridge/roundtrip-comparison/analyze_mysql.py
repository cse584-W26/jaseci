#!/usr/bin/env python3
"""Count actual MySQL command→complete-response cycles, separately from packets."""
import json,pathlib,collections,gzip,sys
R=pathlib.Path(__file__).resolve().parent

def category(sql):
 s=sql.lower()
 if s.startswith(('start transaction','begin')):return 'transaction.begin'
 if s.startswith('set '):return 'transaction.setting'
 if s.startswith('commit'):return 'transaction.commit'
 if s.startswith('call '):return 'stored-procedure.call'
 if s.startswith('select a.id'):return 'anchor.hydration'
 for name in ['Knows','HasMember','ContainerOf','HasCreator']:
  if f"e.arch_type='{name.lower()}'"in s:return 'traversal.'+name
 if 'count(distinct case' in s:return 'set-oriented.aggregate'
 return 'unclassified'

def analyze(base,variants):
 path=base/'protocol.jsonl';events=[json.loads(l)for l in (gzip.open(str(path)+'.gz','rt')if not path.exists()else path.open())]
 errors=[e for e in events if e['event']in ['overlapping_command','unexpected_column_terminator','unsupported_local_infile','connection_error']];assert not errors,errors[:3]
 commands=[e for e in events if e['event']=='command'];ends={(e['connection'],e['command_id'],e['stage']):e for e in events if e['event']=='response_complete'}
 assert all((c['connection'],c['id'],'received')in ends and(c['connection'],c['id'],'delivered')in ends for c in commands)
 connections=sorted(set(c['connection']for c in commands));assert len(connections)==len(variants)
 output=[]
 for cid,v in zip(connections,variants):
  q=[c for c in commands if c['connection']==cid];bounds=[i for i,c in enumerate(q)if c['sql'].startswith('SHOW SESSION STATUS')];rows=[json.loads(l)for l in (base/v/'requests/rows.jsonl').read_text().splitlines()];assert len(bounds)==2*len(rows)
  for c,nxt in zip(q,q[1:]):assert nxt['at']>=ends[(cid,c['id'],'delivered')]['at']
  for i,row in enumerate(rows):
   qq=q[bounds[2*i]+1:bounds[2*i+1]];assert len(qq)==row['questions'];assert row['oracle_ok']
   seq=[]
   for n,c in enumerate(qq,1):
    rx=ends[(cid,c['id'],'received')];tx=ends[(cid,c['id'],'delivered')]
    assert not rx['error']and not tx['error']and rx['frames']==tx['frames']and rx['rows']==tx['rows']
    seq.append({'ordinal':n,'command_id':c['id'],'category':category(c['sql']),'sql':c['sql'],'command_at':c['at'],'received_complete_at':rx['at'],'delivered_complete_at':tx['at'],'server_response_frames':tx['frames'],'server_response_wire_bytes':sum(e['payload_bytes']+4 for e in events if e['event']=='server_frame' and e['stage']=='delivered' and e['connection']==cid and e['command_id']==c['id']),'client_command_wire_bytes':len(c['sql'].encode('utf-8'))+5,'result_sets':tx['resultsets'],'returned_rows':tx['rows'],'command_to_complete_received_ms':rx['elapsed_ms'],'command_to_complete_delivered_ms':tx['elapsed_ms']})
   item={'variant':v,'phase':row['phase'],'warmup':row['warmup'],'iteration':row['iteration'],'command_response_cycles':len(qq),'sequential_complete_response_verified':True,'categories':dict(collections.Counter(x['category']for x in seq)),'server_response_frames':sum(x['server_response_frames']for x in seq),'server_response_wire_bytes':sum(x['server_response_wire_bytes']for x in seq),'client_command_wire_bytes':sum(x['client_command_wire_bytes']for x in seq),'result_sets':sum(x['result_sets']for x in seq),'request_ms_instrumented':row['ms'],'sequence':seq};output.append(item)
 # All framing and every response are checked, while headline counts use post-warmup requests.
 (base/'protocol-analysis.json').write_text(json.dumps({'all_checks_passed':True,'connections':len(connections),'commands_decoded':len(commands),'complete_responses_verified':len(ends),'requests':output},indent=2)+'\n')
 for item in output:
  if not item['warmup']:
   print(item['variant'],item['phase'],item['iteration'],item['command_response_cycles'],item['categories'],item['server_response_frames'],item['result_sets'])
 return output
if __name__=='__main__':
 analyze(R/(sys.argv[1]if len(sys.argv)>1 else'mysql-results'),sys.argv[2:]or['full','pruned'])
