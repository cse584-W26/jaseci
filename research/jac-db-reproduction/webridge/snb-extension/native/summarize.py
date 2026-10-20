import pathlib,json,statistics,math
R=pathlib.Path(__file__).resolve().parent;out=[]
for delay in [0,2,10]:
 for variant in ['baseline','final']:
  d=R/'latency'/f'delay-{delay}ms'/'timing'/variant
  if not(d/'rows.json').exists():continue
  rows=json.loads((d/'rows.json').read_text());cpu={x['query']:x for x in json.loads((d/'measured-cpu.json').read_text())}
  for q in dict.fromkeys(x['query']for x in rows):
   rs=[x for x in rows if x['query']==q];measured=[x for x in rs if not x['warmup']];assert len(rs)==40 and len(measured)==30 and all(x['parity']for x in rs);server=sorted(x['server_ms']for x in measured);out.append({'query':q,'variant':variant,'added_response_delay_ms':delay,'warmup':10,'n':30,'server_median_ms':statistics.median(server),'server_mean_ms':statistics.mean(server),'server_p95_ms':server[math.ceil(.95*len(server))-1],'http_client_median_ms':statistics.median(x['client_ms']for x in measured),'app_cpu_ms_per_measured_request':cpu[q]['app_process_cpu_ms']/30,'cpu_tick_ms':cpu[q]['tick_ms'],'all_hashes_pass':True})
(R/'latency/summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
