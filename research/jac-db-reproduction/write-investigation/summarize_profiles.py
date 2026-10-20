"""Independently recompute stage/duration diagnostic aggregates from rows.jsonl."""
import json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    reports=[]
    for mode,run in [('stage','20261019T212507Z-stage'),('duration','20261019T212529Z-duration')]:
        complete=ROOT/'littlex/w2-investigation'/run/'complete.json';cells=json.loads(complete.read_text())['records'];assert len(cells)==6
        for c in cells:
            p=Path(c['summary']);s=json.loads(p.read_text());rows=json.loads((p.parent/'profile.json').read_text())['rows']
            assert len(rows)==s['metadata']['repeats']==100 and s['metadata']['warmups']==100 and s['oracle_ok']
            assert [r['repeat'] for r in rows]==list(range(100))
            for key in ['server_ms','client_ms','application_process_cpu_ms','database_backend_cpu_ms']:
                assert abs(sum(r[key] for r in rows)-s['metrics'][key]['sum'])<1e-6
            d={'mode':mode,'arm':c['arm'],'operation':c['operation'],'n':100,'source':str(p),'server_median_ms':statistics.median(r['server_ms'] for r in rows),'server_mean_ms':statistics.mean(r['server_ms'] for r in rows),'client_median_ms':statistics.median(r['client_ms'] for r in rows),'paired_residual_median_ms':statistics.median(r['client_ms']-r['server_ms'] for r in rows),'app_cpu_total_ms':sum(r['application_process_cpu_ms'] for r in rows),'backend_cpu_total_ms':sum(r['database_backend_cpu_ms'] for r in rows),'cpu_tick_ms':10,'protocol_observed':mode=='duration','stages':s['stages']}
            if mode=='duration':
                d.update(protocol_mean_ms=statistics.mean(r['database_protocol_total_ms'] for r in rows),protocol_median_ms=statistics.median(r['database_protocol_total_ms'] for r in rows),execute_events_mean=statistics.mean(r['protocol']['execute']['count']+r['protocol']['statement']['count'] for r in rows),explicit_commit_median_ms=statistics.median(r['commit_protocol_ms'] for r in rows))
            reports.append(d)
    out={'cells':12,'profiled_requests':1200,'all_offline_checks_passed':True,'percentile_scope':'Diagnostic medians use statistics.median, as original profiler; baseline500sample percentiles use the distinct original run.stats order-statistic rule.','interpretation':'stage includes headers/CPU sampling with SQL duration logging off; duration adds SQL logging. Profilers use100warm+100calls and reset each operation, distinct from baseline110warm500timed shared-state cohorts. Differences do not isolate instrumentation overhead alone. Protocol counts are executed SQL events, not network packet counts.','rows':reports}
    (ROOT/'write-investigation/profile-aggregates.json').write_text(json.dumps(out,indent=2)+'\n')
    print('Stage/duration profiles:12cells/1200rows, oracle/order/CPU aggregation checks PASS.')


if __name__=='__main__':main()
