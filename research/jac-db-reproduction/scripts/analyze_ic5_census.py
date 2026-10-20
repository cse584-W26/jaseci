"""Offline: classify retained TTL probe and recover the final census SQL windows."""
from collections import Counter
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ttl_probe',ROOT/'scripts/ic5_ttl_probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


def classify(raw):
    calls,guards=probe.classify(raw)
    for call in calls:
        sql=' '.join(call['sql'].split())
        if re.fullmatch(r'SELECT doc FROM identity_users WHERE user_id = (?:\$1|[^ ]+)',sql,re.I):
            category='identity_user_lookup'
        elif call in guards:
            category='schema_guard'
        elif sql.upper().startswith(('BEGIN','COMMIT','ROLLBACK')):
            category='transaction'
        else:
            category='other'
        call['category']=category
    counts=Counter(call['category'] for call in calls)
    return {'total':len(calls),'schema_guard':counts['schema_guard'],
            'identity_user_lookup':counts['identity_user_lookup'],
            'transaction':counts['transaction'],'other':counts['other'],
            'excluding_guard_identity':len(calls)-counts['schema_guard']-counts['identity_user_lookup'],
            'periodic_statements':[call for call in calls if call['category'] in ('schema_guard','identity_user_lookup')],
            'statements':calls}


def main():
    folder=ROOT/'results/ic5-ttl-probe'
    summary_path=folder/'summary.json'
    summary=json.loads(summary_path.read_text())
    rows=[]
    for row in summary['rows']:
        raw=(folder/f"postgres-{row['sequence']:02d}-idx{row['idx']}.log").read_text()
        classification=classify(raw)
        item={**row,'offline_classification':{k:v for k,v in classification.items() if k!='statements'}}
        rows.append(item)
    summary['offline_rows']=rows
    idx3=[row['offline_classification'] for row in rows if row['idx']==3]
    summary['idx3_non_guard_identity_count_invariant']=len({row['excluding_guard_identity'] for row in idx3})==1
    summary['idx3_count_variation_accounted_for_by_guard_and_identity']=(len({row['total'] for row in idx3})>1 and summary['idx3_non_guard_identity_count_invariant'])
    summary['offline_attribution']='Retained raw SQL shows periodic schema existence guard and identity user lookup. Original guard-only false flag is retained; added flags describe removal of both observed statements.'
    summary_path.write_text(json.dumps(summary,indent=2))
    (folder/'classification.json').write_text(json.dumps(rows,indent=2))

    progress=json.loads((ROOT/'results/snb-stage-progress.json').read_text())
    stage=next(item for item in progress if item['stage']=='final-census')
    zone=ZoneInfo('America/New_York')
    start=datetime.fromtimestamp(stage['started_unix'],zone)
    end=datetime.fromtimestamp(stage['started_unix']+stage['seconds'],zone)
    low=start.strftime('%Y-%m-%d %H:%M:%S')
    high=end.strftime('%Y-%m-%d %H:%M:%S')
    pids={3892824,3892805}
    header=re.compile(rb'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+) [A-Z]+ \[(\d+)\] ')
    records=[]
    current=None
    bytes_scanned=0
    with (ROOT/'dbcache/pg/main/server.log').open('rb') as handle:
        for line in handle:
            bytes_scanned+=len(line)
            match=header.match(line)
            if match:
                if current is not None:
                    records.append(current)
                    current=None
                stamp=match.group(1).decode()
                if stamp[:19]>high:
                    break
                if low<=stamp[:19]<=high and int(match.group(2)) in pids:
                    dt=datetime.strptime(stamp,'%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=zone)
                    if start<=dt<=end:
                        current={'pid':int(match.group(2)),'timestamp':stamp,'raw':bytearray(line)}
            elif current is not None:
                current['raw'].extend(line)
        if current is not None:
            records.append(current)
    # Identity lookup can precede BEGIN. End each complete HTTP request at
    # COMMIT on the main data backend, retaining everything since prior COMMIT.
    windows=[];pending=[]
    commit=re.compile(rb'LOG:\s+(?:execute [^:]*|statement):\s*COMMIT\s*(?:\r?\n)?$')
    for record in records:
        pending.append(record)
        first=bytes(record['raw']).splitlines()[0]
        if record['pid']==3892824 and commit.search(first):
            windows.append(pending);pending=[]
    output=ROOT/'results/final-census/sql-windows'
    output.mkdir(exist_ok=True)
    actual=json.loads((ROOT/'results/final-census/rows.json').read_text())
    historical={row['idx']:row['stmts'] for row in json.loads((ROOT.parent/'DBHarness/session0904/ic5/build/gates/ic5_D5.json').read_text())}
    extracted=[]
    for i,window in enumerate(windows):
        phase='warm' if i<20 else 'timed'
        index=i%20
        raw=b''.join(bytes(record['raw']) for record in window)
        path=output/f'{phase}-{index:02d}.log';path.write_bytes(raw)
        classification=classify(raw.decode('utf-8','replace'))
        item={'window':i,'phase':phase,'idx':index,'start':window[0]['timestamp'],
              'end':window[-1]['timestamp'],'file':str(path),'classification':classification}
        if phase=='timed' and index<len(actual):
            item.update(gate_count=actual[index]['stmts'],historical_count=historical[index],
                        exact_gate_count=classification['total']==actual[index]['stmts'])
        extracted.append(item)
    compact={'stage':stage,'local_start':start.isoformat(),'local_end':end.isoformat(),
             'single_pass_bytes_scanned':bytes_scanned,'selected_records':len(records),
             'request_windows':len(windows),'trailing_records':len(pending),
             'main_backend_pid':3892824,'identity_backend_pid':3892805,
             'timed_count_matches':sum(item.get('exact_gate_count',False) for item in extracted),
             'windows':extracted}
    (output/'classification.json').write_text(json.dumps(compact,indent=2))
    print(json.dumps({'probe':[(row['idx'],row['offline_classification']['total'],row['offline_classification']['schema_guard'],row['offline_classification']['identity_user_lookup'],row['offline_classification']['excluding_guard_identity']) for row in rows],
                      'census_windows':len(windows),'timed_matches':compact['timed_count_matches'],
                      'selected_records':len(records),'bytes_scanned':bytes_scanned,
                      'timed':[(item['idx'],item['classification']['total'],item['classification']['schema_guard'],item['classification']['identity_user_lookup'],item['classification']['excluding_guard_identity']) for item in extracted if item['phase']=='timed']},indent=2))


if __name__=='__main__':
    main()
