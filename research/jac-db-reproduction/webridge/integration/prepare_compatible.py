#!/usr/bin/env python3
"""Generate the explicitly typed JDBC helper variant without editing alignment."""
import difflib,hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent;A=R.parent/'alignment';source=A/'AlignedIc5.java';base=source.read_text();sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
assert sha(base)=='acc9b168a3fb579829f2c52c8a07b7be3361a9be9d983bfd9bec0412003246a2'
old='int n=r.getMetaData().getColumnCount();while(r.next()){List<Object> row=new ArrayList<>();for(int i=1;i<=n;i++)row.add(r.getObject(i));rows.add(row);}'
new='int n; if(kind.startsWith("hop:"))n=2; else if(Arrays.asList("server-version","schema-fingerprint","type-registry","identity").contains(kind))n=1; else throw new IllegalStateException("Undeclared typed query kind: "+kind); while(r.next()){List<Object> row=new ArrayList<>();for(int i=1;i<=n;i++)row.add(r.getString(i));rows.add(row);}'
assert base.count(old)==1
adapted=base.replace('public class AlignedIc5 {','public class ReplayCompatibleAlignedIc5 {').replace(old,new)
p=R/'java/ReplayCompatibleAlignedIc5.java';p.write_text(adapted)
w=(R/'java/AlignedWeBridge.java').read_text().replace('AlignedWeBridge','CompatibleWeBridge').replace('AlignedIc5','ReplayCompatibleAlignedIc5');(R/'java/CompatibleWeBridge.java').write_text(w)
(R/'compatibility.diff').write_text(''.join(difflib.unified_diff(base.splitlines(True),adapted.splitlines(True),fromfile=str(source),tofile=str(p))))
(R/'compatibility-ledger.json').write_text(json.dumps(dict(base_source=str(source),base_sha256=sha(base),derivative_source=str(p),derivative_sha256=sha(adapted),changes=[dict(change='Rename class for isolated side-by-side compilation',semantic_removal=False),dict(change='query helper metadata column count replaced with declared SELECT arity',arities={'hop:*':2,'server-version':1,'schema-fingerprint':1,'type-registry':1,'identity':1},semantic_removal=False),dict(change='query helper getObject(i) replaced with getString(i)',types='All columns in these declared generic query shapes are String-valued: UUID, JSON text, version, fingerprint, type name',semantic_removal=False)],preserved='All original SQL, session/ACL/hydration/transactions, graph traversal, request/process/client state and source counters',gate='Tiny probe only until all20 result/SQL-count gate after formal window',upstream_compiler_changes=[]),indent=2))
print(p)
