#!/usr/bin/env python3
"""Sum outer MySQL command-to-complete-delivery RTT inside exact request bounds."""
import argparse,collections,gzip,hashlib,json,pathlib,statistics

def lines(path):
 with (gzip.open(path,'rt')if str(path).endswith('.gz')else pathlib.Path(path).open())as f:
  return [json.loads(s)for s in f if s.strip()]

def extract(trace,run,out):
 run=pathlib.Path(run);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=False)
 events=lines(trace);cid=json.loads((run/'connection-id.json').read_text())['connection_id']
 peers=[e['connection']for e in events if e['event']=='server_greeting'and e['server_connection_id']==int(cid)]
 assert len(peers)==1,('Owned connection uniquely matched',cid,peers)
 peer=peers[0];ev=[e for e in events if e['connection']==peer]
 assert not [e for e in ev if e['event']in {'overlapping_command','unexpected_column_terminator','unsupported_local_infile'}],ev[-5:]
 commands=[e for e in ev if e['event']=='command'];ends={(e['command_id'],e['stage']):e for e in ev if e['event']=='response_complete'}
 for cmd in commands:
  assert (cmd['id'],'delivered')in ends,('Complete response required',cmd)
  assert (cmd['id'],'received')in ends
 for current,nxt in zip(commands,commands[1:]):assert nxt['at']>=ends[current['id'],'delivered']['at'],('Sequential command proof',current,nxt)
 bounds=[i for i,c in enumerate(commands)if c['sql'].upper().startswith('SHOW SESSION STATUS')and c['sql'].upper()!="SHOW SESSION STATUS LIKE 'QUESTIONS'"]
 rows=lines(run/'rows.jsonl');assert len(bounds)==2*len(rows),(len(bounds),len(rows))
 init={'scope':'Frozen TpccSql.open initialization is outside exact SHOW STATUS bounds; no connection setup commands included'};ic=[i for i,c in enumerate(commands)if c['sql'].upper()=="SHOW SESSION STATUS LIKE 'QUESTIONS'"]
 catalog={};output=[]
 for idx,row in enumerate(rows):
  cmds=commands[bounds[2*idx]+1:bounds[2*idx+1]];assert len(cmds)==row['questions'],(idx,len(cmds),row['questions'])
  ops=[]
  for c in cmds:
   end=ends[c['id'],'delivered'];recv=ends[c['id'],'received'];sha=hashlib.sha256(c['sql'].encode()).hexdigest();catalog[sha]=c['sql']
   assert end['elapsed_ms']>=0 and end['at']>=recv['at']
   ops.append({'command_id':c['id'],'sql_sha256':sha,'rtt_ms':end['elapsed_ms'],'server_response_received_ms':recv['elapsed_ms'],'response_frames':end['frames'],'resultsets':end['resultsets'],'response_rows':end['rows'],'server_error':end['error'],'is_call':c['sql'].lstrip().upper().startswith('CALL ')})
  calls=sum(o['is_call']for o in ops);assert calls==row['call_procedure'],(idx,calls,row)
  output.append({'request_ordinal':idx,'iteration':row.get('iteration',idx),'op':row.get('op',row.get('shape','representative')),'warmup':row['warmup'],'connection':peer,'mysql_connection_id':cid,'summed_db_call_rtt_ms':sum(o['rtt_ms']for o in ops),'command_count':len(ops),'call_count':calls,'sdk_enabled_at_end':row.get('sp_enabled_end'),'application_ms_secondary':row['ms'],'operations':ops})
 measured=[r for r in output if not r['warmup']];assert measured
 with(out/'rows.jsonl').open('w')as f:
  for r in output:f.write(json.dumps(r,separators=(',',':'))+'\n')
 (out/'sql-catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
 summary={'status':'PASS','metric':'per-request sum of top-level MySQL command received at proxy to complete response delivered/drained to client socket','unit':'ms','scope':'Every command inside exact timer SHOW SESSION STATUS bounds on the uniquely identified owned JDBC connection; connection initialization and status counters excluded. CALL contributes one outer response, with all result sets consumed by protocol parser. One application connection is certified by the driver connection receipt.','n':len(measured),'total_requests':len(output),'median_ms':statistics.median(r['summed_db_call_rtt_ms']for r in measured),'command_counts':dict(collections.Counter(r['command_count']for r in measured)),'call_requests':sum(r['call_count']>0 for r in measured),'trace':str(pathlib.Path(trace).resolve()),'timer_rows':str((run/'rows.jsonl').resolve()),'rows_path':str((out/'rows.jsonl').resolve()),'sql_catalog':str((out/'sql-catalog.json').resolve()),'initialization_excluded':init,'connection':peer,'mysql_connection_id':cid}
 (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');return summary
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--trace',required=True);p.add_argument('--run',required=True);p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(extract(a.trace,a.run,a.out)))
