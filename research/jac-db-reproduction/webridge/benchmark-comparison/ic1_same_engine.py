#!/usr/bin/env python3
"""Rebuild same-engine IC1 evidence from actual postquiet baseline profiles."""
import pathlib,subprocess,json,statistics,hashlib
B=pathlib.Path(__file__).resolve().parent;out={}
for arm in ['full','pruned','conventional']:
 p=B/'mysql-profile/results/ic1'/f'{arm}-postquiet-selected';subprocess.run(['python',str(B/'ic1_cost_breakdown.py'),'--mysql-profile',str(p)],check=True);x=json.loads((B/'ic1-cost-breakdown.json').read_text())
 for r in x['mysql_matched_requests']:
  for o in r['operations']:o['sql_sha256']=hashlib.sha256(o['sql'].encode()).hexdigest()
 out[arm]={'path':str(p),'requests':x['mysql_matched_requests'],'categories':x['mysql_categories']}
(B/'ic1-same-engine-comparison.json').write_text(json.dumps(out,indent=2)+'\n')
p=B/'ic1-cost-breakdown.json';d=json.loads(p.read_text());d['same_engine_comparison']=out;p.write_text(json.dumps(d,indent=2)+'\n')
lines=['','## Same-engine SQL-work comparison','','All three Java forms use the same MySQL fixture and indexed adjacency. Their three frontier input cardinalities are 1, 10 and 2,740 UUIDs; observed row counts are 10, 2,750 and 9,009. Full/pruned select matching first-name IDs before their final18-ID anchor projection. The conventional reference applies its first-name condition in a final9,036-ID Person projection.','','| Form | Projection input UUIDs | Rows examined | Rows returned | Projection server median ms |','|---|---:|---:|---:|---:|']
for arm,d in out.items():
 rr=[o for r in d['requests']for o in r['operations']if (arm=='conventional'and o['category']=='person.filter_or_projection')or(arm!='conventional'and o['category']=='anchor.projection')];lines.append('| %s | %s | %s | %s | %.3f |'%(arm,sorted({o['uuid_literal_count']for o in rr}),statistics.median(o['pfs_rows_examined']for o in rr),statistics.median(o['pfs_rows_sent']for o in rr),statistics.median(o['pfs_server_ms']for o in rr)))
lines+=['','The conventional final projection accounts for an observed extra server-work component relative to the candidate-first Java forms. Exact query texts, SHA256s, cardinalities and matched P_S/protocol rows are retained in `ic1-same-engine-comparison.json`. The PostgreSQL-versus-MySQL quiet gap remains a separate cross-engine comparison; native logged-profile overhead and the quiet window have separate measurement boundaries.']
with(B/'ic1-cost-breakdown.md').open('a')as f:f.write('\n'.join(lines)+'\n')
