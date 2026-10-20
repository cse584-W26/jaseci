"""Recompute completed W2 rerun distributions from raw samples, without SQL."""
import argparse,csv,hashlib,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def pct(values,q):
    s=sorted(values);return s[min(round(q*(len(s)-1)),len(s)-1)]


def main():
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args()
    source=a.run/'complete.json';d=json.loads(source.read_text());assert d['mode']=='baseline' and len(d['records'])==18
    rows=[];groups={}
    for r in d['records']:
        folder=a.run/f"{r['round']}-{r['arm']}"/r['operation'];raw=list(csv.DictReader((folder/'raw.csv').open()));measured=list(csv.DictReader((folder/'results.csv').open()))
        assert len(raw)==500 and measured==r['rows'] and len(measured)==1
        m=measured[0];assert m['requests']=='500' and m['errors']=='0' and m['oracle_actual']==m['oracle_expected']=='610' and m['oracle_ok']=='True'
        assert [int(x['i']) for x in raw]==list(range(500)) and all(x['workload']==r['operation'] for x in raw)
        client=[float(x['client_ms']) for x in raw];server=[float(x['server_ms']) for x in raw];residual=[c-s for c,s in zip(client,server)]
        for key,values in [('p50_ms',client),('server_p50_ms',server)]:assert abs(pct(values,.5)-float(m[key]))<.0006
        assert abs(pct(server,.95)-float(m['server_p95_ms']))<.0006
        assert r['driver_affinity']==list(range(20)) and r['server_affinity']==(list(range(6,14)) if r['arm']=='postgres' else list(range(20)))
        row={'round':r['round'],'arm':r['arm'],'operation':r['operation'],'n':500,'server_pid':r['server_pid'],'raw_sha256':hashlib.sha256((folder/'raw.csv').read_bytes()).hexdigest(),'raw_path':str(folder/'raw.csv')}
        for name,values in [('server',server),('client',client),('paired_client_minus_server',residual)]:
            row.update({f'{name}_p50_ms':pct(values,.5),f'{name}_p95_ms':pct(values,.95),f'{name}_p99_ms':pct(values,.99),f'{name}_mean_ms':statistics.mean(values),f'{name}_min_ms':min(values),f'{name}_max_ms':max(values)})
        rows.append(row);groups.setdefault((r['round'],r['arm']),[]).append(r)
    assert len(groups)==6
    for rs in groups.values():
        assert [r['operation'] for r in rs]==['like','follow','create_tweet'] and len({r['server_pid'] for r in rs})==1
        state={'tweets':2000,'follows':5000,'likes':0}
        for r in rs:
            assert r['state_before']==state
            state[{'like':'likes','follow':'follows','create_tweet':'tweets'}[r['operation']]]+=610
            assert r['state_after']==state
    out={'source':str(source),'all_checks_passed':True,'rounds':3,'cells':18,'raw_samples':9000,'percentile':'sorted[round(q*(N-1))], matching original harness.run.stats','rows':rows,'residual_scope':'Paired sample client_ms minus server_ms; includes all work outside server headline, not a network-only or CPU-only measurement.'}
    target=ROOT/'write-investigation';(target/'rerun-baseline.json').write_text(json.dumps(out,indent=2)+'\n')
    with (target/'rerun-baseline.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print('Independent rerun validation:18cells/9000raw samples, original percentiles, per-operation shared state/PID/affinity/oracles PASS.')


if __name__=='__main__':main()
