#!/usr/bin/env python3
"""Check real graph-Customer traversal and relational Customer SELECT categories."""
import hashlib,json,pathlib,sys
D=pathlib.Path(__file__).resolve().parent;N=D.parents[2];sys.path.insert(0,str(N));from analyze_mysql_profile import category
checks=[]
for row in json.loads((D/'actual-sql-regression-inputs.json').read_text()):
 digest=hashlib.sha256(row['sql'].encode()).hexdigest();assert digest==row['sql_sha256'];actual=category(row['sql']);assert actual==row['expected_category'],(actual,row)
 checks.append({'arm':row['arm'],'sql_sha256':digest,'actual_category':actual,'expected_category':row['expected_category'],'status':'PASS'})
receipt={'status':'PASS','classifier_source_sha256':hashlib.sha256((N/'analyze_mysql_profile.py').read_bytes()).hexdigest(),'checks':checks};(D/'regression-result.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
