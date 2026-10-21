#!/usr/bin/env python3
"""Freeze measured ad469 SQL templates and positional bind metadata for Java ports."""
import pathlib,json,hashlib
H=pathlib.Path(__file__).resolve().parent
p=H/'native/census/20261020T232351Z-baseline/sql-census.json'
x=json.loads(p.read_text());page=H/'native/census/20261021T002132Z-baseline-page-original/sql-census.json';page_data=json.loads(page.read_text());x['feed_page']=page_data['feed_page'];out={}
for op,data in x.items():
 r=data['requests'][1]
 out[op]=[dict(sql=z['sql'],sha256=z['sql_sha256'],parameters=z.get('parameters'),execute_ms=z['execute_ms'])for z in r['operations']]
f=H/'native-templates.json';f.write_text(json.dumps({'source':str(p),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'selection':'second measured request; warm source command sequence','original_page_source':str(page),'original_page_source_sha256':hashlib.sha256(page.read_bytes()).hexdigest(),'operations':out},indent=2)+'\n')
print(f)
