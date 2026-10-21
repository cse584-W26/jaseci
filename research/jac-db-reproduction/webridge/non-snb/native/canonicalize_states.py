"""Add exact two-decimal monetary snapshots while retaining original raw state."""
import pathlib,json,gzip,hashlib,decimal
from tpcc_state import MONEY
R=pathlib.Path(__file__).resolve().parent
for manifest in R.glob('tpcc-census/*/after-three-state/manifest.json'):
 data=json.loads(manifest.read_text())
 for name,record in data.items():
  source=manifest.parent/(name+'.jsonl.gz');target=manifest.parent/(name+'.canonical-cents.jsonl.gz');h=hashlib.sha256()
  with gzip.open(source,'rt')as f,gzip.open(target,'wb')as out:
   for line in f:
    values=json.loads(line)
    for i in MONEY.get(name,set()):
     if values[i]is not None:values[i]=format(decimal.Decimal(values[i]).quantize(decimal.Decimal('.01')),'.2f')
    b=(json.dumps(values,ensure_ascii=False,separators=(',',':'))+'\n').encode();out.write(b);h.update(b)
  record.update(canonical_cents_path=str(target),canonical_cents_sha256=h.hexdigest(),money_canonicalization='Two decimal places, exact cents equality; raw values retained separately.')
 manifest.write_text(json.dumps(data,indent=2))
print('Canonicalized seven after-three snapshots')
