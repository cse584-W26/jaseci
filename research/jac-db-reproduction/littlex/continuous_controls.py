#!/usr/bin/env python3
"""Short original-driver continuous controls:110warm+100samples, no profiling sleeps."""
import argparse,csv,json,os,subprocess
from datetime import datetime,timezone
import run as lx

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--page',action='store_true');parser.add_argument('--analyze',action='store_true');args=parser.parse_args()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=lx.HERE/'continuous-controls'/stamp;out.mkdir(parents=True)
    old=(lx.BIN,lx.SOURCE,lx.APP_SOURCE)
    env=lx.environment();env.update(PERF='1',JAC_STREAM_LATERAL='1',JAC_SQL_ACL='1',JAC_FUSED_FEED='1',JAC_STICKY_DENY='1',JAC_RO_WALKERS='')
    variants=[('ad-control','jac314-ad469',None,False),('ad-lazy1','jac314-ad469','1',False),('final-lazy0','jac314','0',False),('final-lazy1','jac314','1',False),('final-fresh-fixture','jac314','1',True)]
    if args.analyze:variants=[variants[4]]
    if args.page:variants=[variants[0],variants[3]]
    tier='t200' if args.page else 't20'
    results=[]
    with lx.fixture_lock():
        for name,binary,lazy,fresh in variants:
            cell=out/name;cell.mkdir();p=None
            if fresh:
                lx.BIN=lx.ROOT/'runtime/bin/jac314';lx.SOURCE=lx.ROOT.parent/'jac-db/jac';lx.APP_SOURCE=lx.REPO/'littleXs/jaseci-pg'
            else:lx.BIN,lx.SOURCE,lx.APP_SOURCE=old
            app,tokens,reset=lx.fixture(tier,lx.HERE/'dataset'/(tier+'_seed.json'),env)
            if args.analyze:
                import psycopg
                with psycopg.connect(host=lx.SOCK,user='jac',dbname=reset['database'],autocommit=True) as c:
                    before=c.execute("SELECT reltuples,relpages FROM pg_class WHERE relname='anchors'").fetchone()
                    c.execute('ANALYZE anchors')
                    after=c.execute("SELECT reltuples,relpages FROM pg_class WHERE relname='anchors'").fetchone()
                (cell/'analysis-intervention.json').write_text(json.dumps(dict(statement='ANALYZE anchors',before=before,after=after,scope='restored disposable database only; snapshot unchanged'),indent=2))
            e=dict(env,JAC_PG_APP_DIR=str(app),JAC_PG_BIN=str(lx.ROOT/'runtime/bin'/binary));e.pop('JAC_STAGE_HEADERS',None)
            if lazy is None:e.pop('JAC_LAZY_TXN',None)
            else:e['JAC_LAZY_TXN']=lazy
            try:
                p=lx.launch([lx.ROOT/'runtime/bin'/binary,'start','main.jac','-p','18120','--no-client'],app,e,cell/'server.log',18120,'/healthz')
                lx.command([lx.DRIVER_PYTHON,lx.HERE/'harness/run.py','--engines','jaseci','--tokens-dir',tokens,'--url-jaseci','http://127.0.0.1:18120','--workloads','feed_page' if args.page else 'feed_chain','--warmup','110','--requests','100','--output',cell/'results.csv','--raw-csv',cell/'raw.csv'],e,log=cell/'driver.log')
                rows=list(csv.DictReader((cell/'results.csv').open()));assert sum(int(r['requests']) for r in rows)==100 and all(int(r['errors'])==0 for r in rows)
                report=dict(name=name,reset=reset,rows=rows,app=str(app),environment={k:v for k,v in e.items() if k.startswith('JAC_')},role='Diagnostic continuous original-driver control; excluded from formal500-sample group')
                (cell/'complete.json').write_text(json.dumps(report,indent=2));results.append(report);print(name,rows,flush=True)
            finally:lx.stop(p)
    (out/'complete.json').write_text(json.dumps(results,indent=2))
    print('Complete',out,flush=True)
if __name__=='__main__':main()
