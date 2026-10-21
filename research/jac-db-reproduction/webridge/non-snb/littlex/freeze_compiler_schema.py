#!/usr/bin/env python3
"""Freeze compiler input DDL for the actual common graph/projection fixture."""
import pathlib,json,hashlib
H=pathlib.Path(__file__).resolve().parent
for tier in ['t20','t50','t100','t200']:
 d=H/'fixtures'/tier;r=json.loads((d/'mirrors/receipt.json').read_text());assert len(r)==2
 parts=[(d/'mysql-schema.sql').read_text().split('CREATE TABLE lx_profiles')[0]]
 parts.extend(v['mysql_DDL']for v in r.values())
 p=d/'mysql-compiler-schema.sql';p.write_text('\n'.join(parts)+'\n')
 (d/'compiler-schema-receipt.json').write_text(json.dumps({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_mirror_receipt_sha256':hashlib.sha256((d/'mirrors/receipt.json').read_bytes()).hexdigest(),'tables':['anchors','graph_types','identity_users','identity_lookups','kv_state',*r]},indent=2)+'\n')
print('Compiler schemas frozen')
