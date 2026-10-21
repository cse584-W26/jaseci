"""Apply corrected SQL category precedence without changing captured SQL/protocol facts."""
import pathlib,json,hashlib
from littlex_sql import category
R=pathlib.Path(__file__).resolve().parent;changes=[]
for source in json.loads((R/'littlex-profile-selections.json').read_text()):
    p=R/source/'certified-requests.json';before=hashlib.sha256(p.read_bytes()).hexdigest();rows=json.loads(p.read_text());catalog=json.loads((p.parent/'sql-catalog.json').read_text());modified=[]
    for row in rows:
        for obj in row['operations']+row['flights']:
            if obj.get('sql_id')not in catalog or obj.get('kind')=='prepare_only':continue
            old=obj.get('category');new=category(catalog[obj['sql_id']])
            if old!=new:modified.append({'request_tag':row['request_tag'],'sql_id':obj['sql_id'],'old':old,'new':new});obj['category']=new
    if modified:p.write_text(json.dumps(rows,indent=2))
    if modified:changes.append({'path':str(p.relative_to(R)),'before_sha256':before,'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'changes':modified})
receipt={'reason':'Schema guards mentioning g_n_ table names must be classified before graph projection queries. Raw SQL, timestamps, counts, frames and source operations are unchanged.','changes':changes,'source':'ad469/final runtimelib/impl/store.impl.jac992–998 default TTL5s; _memo_check1025–1050 emits exact to_regclass VALUES SQL; ensure methods call at1136/1504/1610.'}
path=R/'sql-category-correction.json';assert not path.exists();path.write_text(json.dumps(receipt,indent=2)+'\n');print(len(changes),'files corrected')
