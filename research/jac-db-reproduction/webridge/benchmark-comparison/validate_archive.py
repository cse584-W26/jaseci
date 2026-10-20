#!/usr/bin/env python3
"""Run offline result checks against the actual copied public archive."""
import argparse,datetime,json,pathlib,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--archive-root',type=pathlib.Path,required=True);a=p.parse_args();archive=a.archive_root.resolve();R=pathlib.Path(__file__).resolve().parent
commands=[['benchmark-comparison/verify_results.py','--java-timing'],['benchmark-comparison/verify_slow_ic1.py'],['roundtrip-comparison/test_mysql_parser.py'],['roundtrip-comparison/verify_eight_arms.py']]
# The selected-profile verifier is mandatory when present in this experiment version.
profile=archive/'benchmark-comparison/verify_profiles.py'
if profile.exists():commands.append(['benchmark-comparison/verify_profiles.py'])
else:raise SystemExit('Selected-profile verifier missing; archive validation is incomplete')
checks=[]
for argv in commands:
 run=subprocess.run([sys.executable,*argv],cwd=archive,capture_output=True,text=True);checks.append({'argv':[sys.executable,*argv],'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
result={'status':'PASS'if all(x['returncode']==0 for x in checks)else'FAIL','archive':str(archive),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks};(R/'archive-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],len(checks),'offline archive checks');raise SystemExit(0 if result['status']=='PASS' else 1)
