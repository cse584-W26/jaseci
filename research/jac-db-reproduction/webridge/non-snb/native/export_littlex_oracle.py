"""Public business-only fixture sufficient to recompute native result/state proofs."""
import pathlib,json,gzip,hashlib
from littlex_oracle import Oracle
R=pathlib.Path(__file__).resolve().parent;L=R.parent/'littlex';O=R/'littlex-oracle-fixtures';O.mkdir(exist_ok=True);receipt=[]
for tier in ['t20','t50','t100','t200']:
 source=L/'fixtures'/tier/'anchors.tsv';model=Oracle(source);output=O/(tier+'.json.gz');data={name:getattr(model,name)for name in ['profiles','profile_props','tweets','id_seed']};data['follows']=sorted(model.follows)
 with gzip.open(output,'wt')as f:json.dump(data,f,ensure_ascii=False,separators=(',',':'))
 copy=Oracle(output);assert copy.canonical()==model.canonical();receipt.append({'tier':tier,'source_13_business_fields_plus_xmin_export_sha256':json.loads((L/'fixtures'/tier/'export.json').read_text())['tables']['anchors']['sha256'],'public_fixture':str(output.relative_to(R)),'public_compressed_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'rows':{'profiles':len(model.profiles),'tweets':len(model.tweets),'follows':len(model.follows)},'roundtrip_oracle_equal':True})
(O/'manifest.json').write_text(json.dumps({'scope':'Synthetic application business fields and topology only; identity/credentials/root permissions excluded; full source SQL/protocol retained separately','fixtures':receipt},indent=2)+'\n')
print(len(receipt),'business fixture projections verified')
