#!/usr/bin/env python3
"""Let the actual historical runtime create canonical projected relations on matched clones."""
import pathlib,json,sys,subprocess,hashlib,time,argparse,psycopg,httpx
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent));from measurement_lease import lease
p=argparse.ArgumentParser();p.add_argument('--tier',required=True,choices=['t20','t50','t100','t200']);p.add_argument('--lease-held',action='store_true');a=p.parse_args();d=H/'fixtures'/a.tier;db=json.loads((d/'export.json').read_text())['clone_database'];source=json.loads((H/'recipe.json').read_text())['tiers'][a.tier];f=pathlib.Path(source['fixture_manifest']).parent;tokens=json.loads((f/'tokens/tokens.jaseci.json').read_text());token=tokens[sorted(tokens)[0]];out=d/'native-projection-warm';out.mkdir(exist_ok=True);service=H/'native/service.py'
def logicalsha():
 h=hashlib.sha256()
 with psycopg.connect(host='/tmp/jacpg-d6275e76eb',user='jac',dbname=db)as c:
  with c.cursor().copy('COPY(SELECT id,kind,arch_type,arch_module,fingerprint,root_id,src,dst,undirected,props::text,seq,src_type,dst_type FROM anchors ORDER BY id)TO STDOUT WITH(FORMAT text)')as cp:
   for b in cp:h.update(bytes(b))
 return h.hexdigest()
def run():
 before=logicalsha();started=False
 try:
  cmd=[sys.executable,str(service),'start','--variant','baseline','--database',db];r=subprocess.run(cmd,capture_output=True,text=True);(out/'start.stdout').write_text(r.stdout);(out/'start.stderr').write_text(r.stderr);assert r.returncode==0,r.stderr;started=True
  with httpx.Client(base_url='http://127.0.0.1:18134',timeout=120)as c:
   for walker in ['load_feed_chain','load_feed_page_chain']:
    r=c.post('/walker/'+walker,json={},headers={'Authorization':'Bearer '+token});r.raise_for_status();x=r.json();data=x.get('data',x);result=data['reports'][0]if'reports'in data else data;expected=source['feed_counts'][0]if walker=='load_feed_chain' else 20;assert len(result['feed'])==expected
 finally:
  if started or(H/'native/baseline/service.pid').exists():
   r=subprocess.run([sys.executable,str(service),'stop','--variant','baseline','--database',db],capture_output=True,text=True);(out/'stop.stdout').write_text(r.stdout);(out/'stop.stderr').write_text(r.stderr);assert r.returncode==0,r.stderr
 after=logicalsha();assert before==after,'Projection setup changed logical anchors';(out/'receipt.json').write_text(json.dumps({'database':db,'before13fieldCOPYsha':before,'after13fieldCOPYsha':after,'actual_runtime':'ad469CONTROL','read_semantics_passed':True,'service_stopped':True},indent=2)+'\n')
if a.lease_held:run()
else:
 with lease('littlex native mirror initialization '+a.tier,out/('lease-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'.json')):run()
