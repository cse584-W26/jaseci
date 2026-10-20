"""Offline independent validation of original-recipe littleX evidence."""
import csv
import hashlib
import json
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'littlex/original-recipe/20261019T193716Z'


def csv_read(p):
    with Path(p).open(newline='') as f:return list(csv.DictReader(f))


def main():
    complete=json.loads((RUN/'complete.json').read_text());records=complete['records']
    expected=[]
    for arm in ('postgres','jaseci'):
        for phase in (('W2','W3','W1') if arm=='postgres' else ('W3','W1','W2')):
            for tier in (('t200',) if phase=='W3' else ('t20','t50','t100','t200')):
                for op in (('0','5','15','30') if phase=='W3' else ('like','follow','create_tweet') if phase=='W2' else ('feed',)):
                    expected.append('_'.join((phase,tier,arm,op)))
    assert len(records)==40 and [r['cell'] for r in records]==expected
    groups={};samples=0
    for r in records:
        assert r['runtime_commit']=='ad469c9889dabcdf70bbf6cfc033c0f8a3d0399e'
        assert r['app_sha256']=='89366720a196c275712ccda73c2db06b17ea509c645a87c87ef84e5409821df0'
        results=csv_read(r['results']);assert results==r['rows']
        raw=csv_read(Path(r['results']).parent/'raw.csv');n=1000 if r['phase']=='W3' else 500
        assert len(raw)==sum(int(v['requests']) for v in results)==n
        assert [int(v['i']) for v in raw]==list(range(n))
        per_kind=Counter(v['workload'] for v in raw)
        assert all(per_kind[v['workload']]==int(v['requests']) for v in results)
        assert all(int(v.get('errors') or 0)==int(v.get('warmup_errors') or 0)==0 for v in results)
        for v in results:
            if v['workload'] in ('like','follow','create_tweet'):
                assert v['oracle_ok']=='True' and v['oracle_expected']==v['oracle_actual']
                if r['phase']=='W2':assert int(v['oracle_actual'])==610
        assert r['extra_feed_requests_before_warmup']==0 and r['driver_cpu_affinity']==list(range(20))
        assert r['server_cpu_affinity']==(list(range(6,14)) if r['arm']=='postgres' else list(range(20)))
        assert r['initial_seed_counts']=={'tweets':100*int(r['tier'][1:]),'follows':5000,'likes':0}
        provenance=Path(r['dependency_provenance']);assert hashlib.sha256(provenance.read_bytes()).hexdigest()==r['dependency_provenance_sha256']
        pv=json.loads(provenance.read_text());assert pv['interpreter']['version']=='3.13.16'
        assert r['driver_python']==pv['environments']['driver']['python'] and r['sql_python']==pv['environments']['sql']['python']
        assert 'JAC_LAZY_TXN' not in r['jac_environment'] and 'JAC_EDGE_ONLY_DIRTY' not in r['jac_environment']
        if r['arm']=='jaseci':
            proof=json.loads(Path(r['historical_validation']).read_text());assert proof['reset_after_validation'] and proof['full_feed_users']==proof['top20_users']==100
            for k in ('full_log','page_log'):assert 'PARITY OK (100 passed, 0 failed)' in Path(proof[k]).read_text()
        for entry in r['prevalidation']:
            check=json.loads(Path(entry).read_text());assert 'PARITY OK (100 passed, 0 failed)' in (Path(check['results']).parent/'oracle.log').read_text()
        groups.setdefault(r['cohort'],[]).append(r);samples+=n
    assert len(groups)==24
    sqlpids={r['server_pid'] for r in records if r['arm']=='postgres'};jacpids={r['server_pid'] for r in records if r['arm']=='jaseci'}
    assert len(sqlpids)==1 and len(jacpids)==12
    for cohort,rs in groups.items():
        assert len({r['server_pid'] for r in rs})==1
        expected_state=rs[0]['initial_seed_counts'].copy()
        if rs[0]['phase']=='W2':assert [r['operation'] for r in rs]==['like','follow','create_tweet']
        for r in rs:
            assert r['state_before_operation']==expected_state
            for row in r['rows']:
                key={'like':'likes','follow':'follows','create_tweet':'tweets'}.get(row['workload'])
                if key:expected_state[key]+=int(row['oracle_actual'])
        assert json.loads((Path(cohort)/'post-counts.json').read_text())==expected_state
    aggregate=json.loads((ROOT/'littlex/original-recipe/summary/validation.json').read_text());assert aggregate['complete_cells']==aggregate['validated_cells']==40 and aggregate['request_errors']==0
    result={'all_checks_passed':True,'source':str(RUN),'cells':40,'raw_timed_requests':samples,'cohorts':24,'sql_server_pids':sorted(sqlpids),'jac_server_pids':sorted(jacpids),'original_sequence':True,'preserved_W2_state':True,'affinity_snapshot_checks':True,'error_and_count_oracles':True,'runtime_commit':records[0]['runtime_commit'],'python_sql_driver':'3.13.16'}
    (ROOT/'results/littlex-original-independent-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print('littleX original recipe:40/40cells,24000rawrequests,PID/cohort/state/order/affinity/sample/oracles PASS.')


if __name__=='__main__':main()
