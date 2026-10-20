#!/usr/bin/env python3
"""Copy selected reproducibility evidence, leaving bulky and private payloads local."""
import argparse,hashlib,json,pathlib,shutil
p=argparse.ArgumentParser();p.add_argument('--destination',type=pathlib.Path,required=True);a=p.parse_args();src=pathlib.Path(__file__).resolve().parents[1];dst=a.destination.resolve()
roots=['roundtrip-comparison','alignment','jac-comparison','latency-comparison','paper','integration/timing','integration/census','integration/java','integration/jdbc-string','integration/sql-frontend','integration/json-type-compat','integration/recorded-bind-types','integration/numeric-width','integration/pruned-getter-fix','integration/small-final-cleanup','integration/supervision-tests','integration/jdbc-boundaries','integration/sql-boundaries','integration/cases/small-full-webridge-20261020','integration/cases/small-pruned-webridge-20261020','integration/cases/idiomatic-small-20261020','snb-extension','expansion','benchmark-comparison']
roots += [str(p.relative_to(src))for p in(src/'integration/cases').glob('set-snb-*-20261020')]
files=[p for p in src.glob('*')if p.is_file()]+[p for p in(src/'integration').glob('*')if p.is_file()]
for r in roots:files.extend(p for p in(src/r).rglob('*')if p.is_file())
whitelists={}
for r in ['jac-comparison/roundtrip-profile','snb-extension/native']:
 d=src/r;m=json.loads((d/'PUBLIC_FILES.json').read_text());allowed=set(m.get('allowed_files',[]))|{x['path']for x in m.get('files',[])}|{'PUBLIC_FILES.json'};whitelists[d]=allowed
bytecode={f'integration/cases/set-snb-{q}-20261020/source/classes/SnbSetSql.class'for q in ['is1','is2','is3','ic1-nonnull','ic2','ic13']}
obsolete={'latency-comparison/comparison.pdf','latency-comparison/comparison.png','integration/timing/comparison.pdf','integration/timing/comparison.png'}
historical={f'jac-comparison/{v}/{f}'for v in ['baseline','final']for f in ['launch.json','server.log','source.json']}
manifest=[];omitted=[]
for f in sorted(set(files)):
 rel=f.relative_to(src);size=f.stat().st_size;reason='superseded presentation; integrated measured PDF retained'if str(rel)in obsolete else None
 if str(rel)in historical and(dst/rel).exists():
  old=dst/rel;manifest.append({'path':str(rel),'bytes':old.stat().st_size,'sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'provenance':'Original archived IC5 launch; six-query launches are in their own native result directories.'});continue
 if f.name in {'.mysql-sp-profile.lock','.engine-graph.lock'}:reason='ephemeral coordination lock'
 for d,allowed in whitelists.items():
  if f.is_relative_to(d)and str(f.relative_to(d))not in allowed:reason='private capture; public metadata selected by whitelist'
 if reason is None and str(rel)not in bytecode and (set(rel.parts)&{'__pycache__','classes','compiled','runtime-data','app','.git','target','deps','webridge-classes'}or f.suffix in {'.class','.jar','.so','.bin','.jir','.pyc','.tar','.xz'}or f.name.endswith('.tar.gz')):reason='local build, executable, payload or dataset'
 if reason is None and f.name in {'anchors.tsv','svc_token.json','identity_lookups.tsv','kv_state.tsv','users.tsv','identities.tsv','identity_users.tsv','request-context.json'}:reason='local fixture payload'
 new_case=('snb-extension/webridge-cases' in str(rel)or str(rel).startswith('integration/cases/set-snb-'))
 if reason is None and new_case and ((f.name.startswith(('record-','graph'))or f.name=='native-graph-before-java-return.json')and f.suffix=='.json'):reason='symbolic graph or result payload; source hashes and stage receipts retained'
 # Preserve actual source SQL, logs, request rows and compressed framing evidence.
 limit=30_000_000 if f.suffix in {'.gz','.sql'}or 'benchmark-comparison' in rel.parts else 2_000_000
 if reason is None and size>limit:reason='large local artifact; hash retained'
 if reason:
  omitted.append({'path':str(rel),'bytes':size,'reason':reason,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()if size<50_000_000 else None});continue
 target=dst/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target);manifest.append({'path':str(rel),'bytes':size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
for name in obsolete|{'integration/.mysql-sp-profile.lock','integration/.engine-graph.lock'}:
 old=dst/name
 if old.exists():old.unlink()
# Remove an earlier uncompressed trace only when its gzip replacement is byte-identical.
import gzip
for compressed in(dst/'benchmark-comparison/mysql-profile').rglob('protocol.jsonl.gz'):
 plain=compressed.with_suffix('')
 if plain.exists()and not(src/plain.relative_to(dst)).exists():
  assert hashlib.sha256(gzip.decompress(compressed.read_bytes())).digest()==hashlib.sha256(plain.read_bytes()).digest()
  plain.unlink()
(dst/'archive-manifest.json').write_text(json.dumps({'collection_root':str(src),'files':manifest,'omitted_selected_tree_files':omitted,'selection':'IC5 and six further SNB queries; native capture whitelist, source snapshots, real pipeline attempts, raw measurements, generated SQL and analysis.'},indent=2)+'\n')
print(json.dumps({'files':len(manifest),'bytes':sum(x['bytes']for x in manifest),'omitted':len(omitted)}))
