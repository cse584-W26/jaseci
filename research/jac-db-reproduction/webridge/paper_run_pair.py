#!/usr/bin/env python3
"""Run Original and WeBridge arms with the paper's 300s + 600s timing."""
import json,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R));import paper_control as ctl
out=R/'paper'/('pair-'+time.strftime('%Y%m%dT%H%M%S',time.gmtime()));out.mkdir()
receipt={'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'arms':[], 'timing':{'warmup_seconds':300,'measurement_seconds':600},'workload':'Original My-Blog and WeBench with separately recorded paper-condition fixes','deviations':['single physical host with disjoint logical CPU affinities, rather than four separate machines','observed host CPU model/governor differs from paper','latency-driving API mix unspecified in paper; use equal GI/BD/EB and report separately'],'status':'running'}
def save(): (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
save()
try:
 # Stop instrumentation/online training while preserving separately generated SP definitions.
 for name in ['online','offline','compiler']:ctl.stop(name)
 for mode in ['normal','optimized']:
  ctl.bench(populate=True)
  subprocess.run(['docker','exec','-i','jac-webridge-paper-mysql5725','mysql','--default-character-set=utf8mb4','-uroot','my_blog_db'],input=(R/'paper-audit/dataset_oracles.sql').read_bytes(),stdout=(out/(mode+'-fixture.tsv')).open('wb'),check=True)
  ctl.start(mode)
  before=set((R/'paper/measurements').iterdir());start=time.monotonic()
  ctl.bench()
  new=set((R/'paper/measurements').iterdir())-before
  assert len(new)==1,new
  receipt['arms'].append({'mode':mode,'output':str(new.pop()),'elapsed_seconds':time.monotonic()-start});save()
  ctl.stop('online')
 receipt['status']='completed';save();print(out,flush=True)
except BaseException as e:
 receipt['status']='failed';receipt['error']=repr(e);save();raise
finally:
 ctl.stop('online')
