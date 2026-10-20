#!/usr/bin/env python3
"""Execute every selected frozen case's existing bytecode against all20 historical oracles."""
import pathlib,subprocess,json,hashlib,time,sys
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];I=B/'integration';mapping=json.loads((H/'selected-cases.json').read_text());out=H/('frozen-source-gates-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));out.mkdir();summary={};java=B.parents[1]/'webridge/SourceCode/openjdk8-webridge/build/linux-x86_64-normal-server-release/images/j2sdk-image/bin/java'
for q in sys.argv[1:]or list(mapping):
 c=I/'cases'/mapping[q];cp=':'.join(map(str,[c/'source/classes',B/'deps/mysql-connector-java-5.1.46.jar',B/'deps/fastjson2-2.0.9.jar']));cmd=['taskset','-c','9,19',str(java),'-Xmx4g',*(['-Dsnb.finiteDepth=true']if q=='ic13'else[]),*(['-Dsnb.branchTopk=true']if q=='ic2'else[]),'-cp',cp,'SnbSetSql',q,str(B/'snb-extension/inputs-all20.json'),str(out/q)];(out/(q+'-command.json')).write_text(json.dumps(cmd));
 with(out/(q+'.log')).open('w')as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 path=out/q/'rows.jsonl';rows=[json.loads(x)for x in path.read_text().splitlines()]if path.exists()else[];checks=[hashlib.sha256(json.dumps(x['result'],sort_keys=True).encode()).hexdigest()==x['expected_canonical_sha256']for x in rows];summary[q]={'returncode':p.returncode,'all20canonical_pass':len(rows)==20 and all(checks),'rows':len(rows),'source_sha256':hashlib.sha256((c/'source/SnbSetSql.java').read_bytes()).hexdigest(),'class_sha256':hashlib.sha256((c/'source/classes/SnbSetSql.class').read_bytes()).hexdigest(),'case':str(c)};(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(q,summary[q]['all20canonical_pass'],flush=True)
print(out)
