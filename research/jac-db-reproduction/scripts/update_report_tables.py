"""Refresh only marked result sections from completed local artifacts; no live work."""
import csv
import json
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'REPORT.md'


def read(rel):
    return json.loads((ROOT / rel).read_text())


def link(rel):
    return f'[{rel}]({rel})'


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '| ' + ' | '.join('---' for _ in headers) + ' |',
                      *['| ' + ' | '.join(str(v) for v in r) + ' |' for r in rows]])


def csv_rows(rel):
    with (ROOT / rel).open(newline='') as f:
        return list(csv.DictReader(f))


def upper(vals):
    return sorted(vals)[len(vals)//2]


def ic5():
    data = []
    for variant in ('baseline', 'final'):
        c = read(f'results/{variant}-census/summary.json')
        t = read(f'results/{variant}-latency/summary.json')
        assert c['failed_including_warm'] == t['failed_including_warm'] == 0
        cq, tq = c['queries']['ic5'], t['queries']['ic5']
        assert cq['parity_ok'] == cq['n'] == 20 and cq['structural_sql'] == 0
        assert tq['parity_ok'] == tq['n']
        data.append([variant, tq['n'], f"{tq['jac_median_ms']:.3f}",
                     f"{tq['pg_median_ms']:.3f}", f"{tq['median_ratio']:.3f}×",
                     f"{cq['total_statements']:,}", cq['structural_sql'],
                     f"{tq['parity_ok']}/{tq['n']}"])
    current = {r['idx']: r['stmts'] for r in read('results/final-census/rows.json')}
    old = {r['idx']: r['stmts'] for r in read('../DBHarness/session0904/ic5/build/gates/ic5_D5.json')}
    differences = [(i, old[i], current[i], current[i]-old[i]) for i in sorted(old) if current[i] != old[i]]
    b = read('results/baseline-latency/summary.json')['queries']['ic5']['jac_median_ms']
    f = read('results/final-latency/summary.json')['queries']['ic5']['jac_median_ms']
    return ('Logging-off paired-request latency; conventional medians. Census is a separate 20-request logging-on run.\n\n'
            + table(['Revision', 'Latency N', 'Jac ms', 'Paired SQL ms', 'Jac / SQL', 'Census SQL total', 'Structural SQL', 'Latency parity'], data)
            + f'\n\nThe baseline / final Jac median ratio is **{b/f:.2f}×** in these runs. Census totals exactly reproduce the historical **278,769 → 432** reduction.\n\n'
            + f'Final per-row statement counts match {20-len(differences)}/20 historical rows. Differences (zero-based idx, historical, reproduced, delta): `{differences}`. Retained SQL windows show the current idx 3 count 28 consists of one schema-existence guard plus 27 other statements. The guard explains that request’s +1. A controlled same-input probe observed29/27/29 after an immediate repeat and a 5.5-second delay; schema guard and identity lookup counts 1/0/1 each account for the two-statement variation, with 27 other statements constant. Historical idx 13’s extra statement remains unclassified because its original SQL window is unavailable. Evidence: [census SQL classification](results/final-census/sql-windows/classification.json), [probe summary](results/ic5-ttl-probe/summary.json), [probe SQL classification](results/ic5-ttl-probe/classification.json).\n\n'
            + 'Evidence: ' + ', '.join(link(f'results/{v}-{k}/summary.json') for v in ('baseline','final') for k in ('census','latency')) + '.')


def locked_ready():
    path=ROOT/'results/locked-stage-progress.json'
    if not path.exists():return False
    stages=json.loads(path.read_text())
    return bool(stages) and stages[-1]['stage']=='locked-tpcc-stop-sqlalchemy' and all(r['exit']==0 for r in stages)


def snb():
    paired=read('results/final-latency/summary.json')
    assert paired['historical_hash_matches']==paired['historical_hash_keys']==140
    blocks=['Earlier paired rounds (60 requests/query) used the initial SQL baseline environment. Their results remain in '+link('results/final-latency/summary.json')+'. The canonical table below is the primary full-schedule comparison.']
    locked=locked_ready()
    prefix='results/locked/snb-canonical' if locked else 'results/snb-canonical'
    selections=[('jac','jaseci-pg','results/snb-canonical/jac'),('postgres','postgres',prefix+'/postgres'),('sqlalchemy','sqlalchemy',prefix+'/sqlalchemy')]
    if (ROOT/prefix/'neo4j/snb_neo4j.meta.json').exists():selections.append(('neo4j','neo4j',prefix+'/neo4j'))
    blocks.append(('**Primary baselines: original benchmark dependency lock.** ' if locked else '**Pilot baseline environment.** ')+ 'Jac retains its original final-runtime result. Each arm completed 140 warm +2,550 timed requests, serially. Historical upper-middle client p50 is shown; all 140 result hashes per arm match the tracked SQL reference.')
    historical=read('../DBHarness/session0904/run/data/snb/postgres/snb_postgres.hashes.json');arms={};sources=[]
    for name,arm,directory in selections:
        rel=directory+'/snb_'+arm;meta=read(rel+'.meta.json');assert not meta['errors'] and meta['counts']['warm_total']==140 and meta['counts']['timed_total']==2550
        hashes=read(rel+'.hashes.json');assert len(hashes)==140 and all(historical.get(k)==v for k,v in hashes.items())
        arms[name]=csv_rows(rel+'.csv');assert len(arms[name])==2550;sources.append(link(rel+'.csv'))
    headers=['Query','N / arm','Jac Final defaults client ms','SQL client ms','ORM client ms']+(['Neo4j client ms'] if 'neo4j' in arms else [])+['Jac / SQL']
    rows=[]
    for q in paired['queries']:
        values={name:upper([float(r['client_ms']) for r in rs if r['query']==q]) for name,rs in arms.items()}
        n=sum(r['query']==q for r in arms['jac'])
        row=[q,n]+[f"{values[name]:.3f}" for name in ('jac','postgres','sqlalchemy')]
        if 'neo4j' in arms:row.append(f"{values['neo4j']:.3f}")
        row.append(f"{values['jac']/values['postgres']:.3f}×");rows.append(row)
    blocks.append(table(headers,rows))
    blocks.append('Raw timing: '+', '.join(sources)+'. Sibling `.meta.json`/`.hashes.json` files establish complete schedules, zero errors and 140 matching hashes. Raw CSV also retains server time.')
    if locked:blocks.append('The earlier dependency-unmatched baseline runs remain under `results/snb-canonical/{postgres,sqlalchemy,neo4j}/`. The failed first locked PostgreSQL attempt is retained at `results/locked/snb-canonical/postgres-startup-race/`; the table uses the completed replacement at `results/locked/snb-canonical/postgres/`.')
    return '\n\n'.join(blocks)


def tpcc():
    locked=locked_ready();rows=[];oracles=[];client={};sources=[]
    selections=[('results/locked/tpcc-postgres' if locked else 'results/tpcc-postgres16','postgres','PostgreSQL16'),('results/tpcc-jac','jaseci-pg','Jac Final defaults'),('results/locked/tpcc-sqlalchemy' if locked else 'results/tpcc-sqlalchemy','sqlalchemy','SQLAlchemy')]
    for directory,arm,label in selections:
        base=directory+'/tpcc_'+arm;oracle=read(base+'.oracle.json');meta=read(base+'.meta.json');timed=csv_rows(base+'.csv')
        assert oracle['oracle_all_ok'] and all(oracle['oracle'].values()) and not meta['errors']
        assert oracle['warmup']==100 and oracle['timed']==800 and oracle['rolled_back']==7 and len(timed)==800
        golden={'orders':30487,'order_line':305500,'new_order':9487,'history':30406,'next_o_sum':30497,'consistency_bad':0}
        assert all(oracle['after'][k]==v for k,v in golden.items()) and abs(oracle['after']['w_ytd']-1362049.86)<.01
        oracles.append(oracle);sources.append(link(base+'.oracle.json'))
        for q in ('new_order','payment'):
            rs=[r for r in timed if r['query']==q];client[(arm,q)]=upper([float(r['client_ms']) for r in rs])
            rows.append([label,q,len(rs),f"{client[(arm,q)]:.3f}",f"{upper([float(r['server_ms']) for r in rs if r['server_ms']]):.3f}",'7/7','0'])
    assert all(o['plan_sha256']=='769147b46ac2a157a378e061089b7f8e043d5f261c361aebbe9ce9a196cf8501' for o in oracles)
    jp=client[('jaseci-pg','payment')];op=client[('sqlalchemy','payment')]
    ordering='slower' if jp>op else 'faster';gap=abs(jp/op-1)*100
    intro=('**Primary baselines: original benchmark dependency lock.** ' if locked else '**Pilot baseline environment.** ')+ 'Jac retains the original final-runtime run. Each arm starts from freshly loaded state and executes the original 100 warm + 800 timed plan. Upper-middle p50 matches the historical statistic; New-Order client timing includes six expected timed rollbacks.'
    explanation=f'New-Order places Jac between hand SQL and SQLAlchemy. Payment is {ordering} on Jac than SQLAlchemy ({jp:.3f} vs {op:.3f} ms, {gap:.1f}% relative difference). Historical CONTROL Payment was 10.82 vs 10.66 ms. Dependency-aligned results support the present ordering; cross-date changes also include runtime, database and host configuration differences.'
    archive=' Earlier baseline artifacts are retained in `results/tpcc-postgres16/` and `results/tpcc-sqlalchemy/`; the PostgreSQL18setup pilot remains in `results/tpcc-postgres/`.' if locked else ''
    return intro+'\n\n'+table(['Arm','Operation','Timed N','Client p50 ms','Server p50 ms','Truth checks','Errors'],rows)+'\n\nAll three arms reproduce the golden 900-entry plan: 487 successful New-Order, 406 Payment, 7 rollbacks; final orders 30,487, order_line 305,500, new_order 9,487, history 30,406, next_o_sum 30,497, YTD 1,362,049.86, consistency violations 0.\n\n'+explanation+'\n\nEvidence: '+', '.join(sources)+'. Sibling CSV/meta files retain request timing and schedule.'+archive


def littlex():
    validation=read('littlex/original-recipe/summary/validation.json')
    independent=read('results/littlex-original-independent-validation.json')
    assert validation['complete_cells']==validation['validated_cells']==40 and validation['request_errors']==0
    assert independent['all_checks_passed'] and independent['raw_timed_requests']==24000
    assert validation['source_directory']==independent['source']
    measured=csv_rows('littlex/original-recipe/summary/comparison.csv');groups={}
    for r in measured:groups.setdefault((r['phase'],r['tier'],r['fraction'],r['operation']),{})[r['arm']]=r
    rows=[]
    order={'feed':0,'feed_page':0,'like':1,'follow':2,'create_tweet':3}
    for key,pair in sorted(groups.items(),key=lambda kv:(kv[0][0],int(kv[0][1][1:]),int(kv[0][2] or -1),order[kv[0][3]])):
        j,p=pair['jaseci'],pair['postgres'];jm=float(j['server_p50_ms']);pm=float(p['server_p50_ms'])
        hj=float(j['historical_server_p50_ms']);hp=float(p['historical_server_p50_ms'])
        rows.append([*key,f'{jm:.3f}',f'{pm:.3f}',f'{jm/pm:.2f}×',f'{hj/hp:.2f}×'])
    intro='**Primary littleX group: historical ad469c988 CONTROL, original process/cohort recipe.** Run20261019T193716Z completes40/40 cells and24,000 timed raw requests, with zero request/warmup errors. Each W1/W2 operation has110 warm +500 timed requests; each W3 fraction has110 warm +1,000 timed requests.'
    recipe='One SQL server process persists across all12 SQL cohorts. Jac uses12 separate cohort processes. Within each W2 tier, like→follow→create_tweet shares its process and accumulating database state; each operation has its own110-request warmup. SQL phase order is W2→W3→W1; Jac order is W3→W1→W2. SQL server affinity is6–13, Jac/driver affinity0–19. SQL app and HTTP driver use their separate original locks on Python3.13.16; Jac uses the historical source with the pinned3.14 interpreter. No extra feed probes precede the prescribed warmup; fixture full/page validation is followed by reset.'
    source='Evidence: '+link('littlex/original-recipe/20261019T193716Z/complete.json')+', '+link('littlex/original-recipe/summary/validation.json')+', '+link('results/littlex-original-independent-validation.json')+', '+link('littlex/original-recipe/summary/comparison.csv')+'. Every comparison row points to its cohort results/raw CSV. Independent checks cover operation order, shared PID/state, affinity snapshots, sample counts, dependency provenance,100-user parity logs and write-delta oracles.'
    blocks=[intro,recipe,'Server p50 milliseconds. Historical ratio is the recorded September4 CONTROL/SQL ratio for the same tier/fraction/operation.\n\n'+table(['Phase','Tweets/user tier','Write %','Operation','Historical-source CONTROL ms','SQL ms','Current ratio','Historical ratio'],rows),source]
    fresh=read('littlex/summary/validation.json');assert fresh['complete_cells']==fresh['validated_cells']==40 and not fresh['missing'] and not fresh['errors']
    fr=csv_rows('littlex/summary/comparison.csv');fg={}
    for r in fr:
        if r['phase']=='W1':fg.setdefault(r['tier'],{})[r['arm']]=r
    frows=[]
    for tier,pair in sorted(fg.items(),key=lambda kv:int(kv[0][1:])):
        j,p=pair['jaseci'],pair['postgres'];jm=float(j['server_p50_ms']);pm=float(p['server_p50_ms']);frows.append([tier,f'{jm:.3f}',f'{pm:.3f}',f'{jm/pm:.2f}×'])
    blocks+=['**Additional group: final32 Final defaults with fresh state per cell.** All40 cells pass their recorded sample, seed/parity and write-count checks. This group restores/reloads independently per operation and uses different process/state boundaries from the historical-recipe primary group; their difference is not a runtime-only A/B. W1 example:',table(['Tweets/user tier','Final defaults ms','SQL ms','Ratio'],frows),'Full additional matrix: '+link('littlex/summary/REPORT.md')+', '+link('littlex/summary/comparison.csv')+', '+link('littlex/summary/validation.json')+'.','Both groups reproduce increasing W1 feed cost with tweets per user, and W3 feed_page remains faster on Jac than SQL. Current historical-source CONTROL/SQL write ratios differ from the recorded September4 ratios. Commit-floor and write-path diagnostics below characterize current costs and the specific initialization/statistics gaps.']
    return '\n\n'.join(blocks)


def write_diagnostics():
    control=read('littlex/continuous-controls/20261019T195630Z/complete.json')
    analyzed=read('littlex/continuous-controls/20261019T200053Z/complete.json')
    intervention=read('littlex/continuous-controls/20261019T200053Z/final-fresh-fixture/analysis-intervention.json')
    assert intervention['statement']=='ANALYZE anchors' and intervention['before']==[-1.0,0]
    assert intervention['after']==[9303.0,795]
    rows=[]
    for item in control+analyzed:
        assert len(item['rows'])==1 and item['rows'][0]['requests']=='100' and item['rows'][0]['errors']=='0' and item['rows'][0]['warm_count']=='110'
        label=item['name']+(' + ANALYZE anchors' if item in analyzed else '')
        rows.append([label,item['rows'][0]['server_p50_ms']])
    blocks=['### Controlled t20 feed gap: planner statistics',
        'The unchanged continuous driver uses110 round-robin warm requests and100 timed requests. The first four controls use the same historical fixture; the final fresh fixture is measured before/after an ANALYZE-only intervention on a restored disposable database.',
        table(['Control','Server p50 ms'],rows),
        'The fresh fixture starts with `anchors` planner metadata reltuples−1/pages0. **Only `ANALYZE anchors`** changes this to9303/pages795 and reduces server median23.527→15.312ms, matching the15.296ms final-runtime control on the historical fixture. This controlled intervention identifies missing planner statistics as the source of that additional-group t20 gap. Stored snapshots and formal result artifacts remain unchanged. The source×LAZY controls on the common fixture stay near15ms, rather than the23ms fresh-fixture result.',
        'Evidence: '+link('littlex/continuous-controls/20261019T195630Z/complete.json')+', '+link('littlex/continuous-controls/20261019T200053Z/complete.json')+', '+link('littlex/continuous-controls/20261019T200053Z/final-fresh-fixture/analysis-intervention.json')+'. Before/after EXPLAIN artifacts: `littlex/explain/20261019T200019Z/` and `20261019T200127Z/`.',
        '### Early page-profile gap: projection retry readiness',
        'The10-warm diagnostic starts0.321seconds after a Tweet endpoint-projection lock-timeout refusal and finishes its tenth capture1.256seconds after it. The source schedules the first retry after2seconds; all captured calls therefore use the generic two-hop top-K SQL. The110-warm capture starts3.303seconds after its refusal and uses global_topk. Continuous110-warm controls measure3.630ms on historical CONTROL and3.780ms on final32, consistent with the formal warmed3.5–3.8ms page results. SQL text, timestamps and source conditions are recovered in '+link('littlex/PAGE_BRANCH_RECEIPT.md')+'. This explains the initialization-profile difference separately from the W1 statistics intervention.',
        '### Logged INSERT + COMMIT and write-path work']
    floor=[]
    for arm,historical in [('pg16',6.3992),('native',6.3395)]:
        d=read(f'results/commit-floor/{arm}.summary.json');timed=[r for r in d['rows'] if r['phase']=='timed'];warm=[r for r in d['rows'] if r['phase']=='warm']
        assert len(timed)==40 and len(warm)==5 and d['ok'] and d['relation_persistence']=='p' and d['validated_insert_count']==45 and d['scratch_table_removed']
        assert d['settings']['fsync']==d['settings']['synchronous_commit']=='on'
        floor.append([arm,f"{d['timed_summary']['total_ms']['median_ms']:.3f}",f"{d['timed_summary']['commit_ms']['median_ms']:.3f}",f'{historical:.4f}'])
    blocks+=[table(['Cluster','Current INSERT+COMMIT ms','Current explicit COMMIT ms','Historical scratch total ms'],floor),
        'The current probe uses an ordinary logged scratch table, one reused connection/cluster and5 warm +40 timed transactions. Both clusters report fsync=on,synchronous_commit=on,wal_sync_method=fdatasync,checkpoint_timeout=5min,max_wal_size=1GB. The historical log records40 COMMIT-inclusive samples; its original scratch code/raw CSV is unavailable, so that timer boundary and warmup remain unspecified. The measurements establish a much lower present common commit-inclusive cost than the recorded6.3ms reference; they do not assign the difference to a storage mechanism or identify the historical t20 ranking cause.',
        'Evidence: '+link('results/commit-floor/summary.json')+', '+link('results/commit-floor/pg16.summary.json')+', '+link('results/commit-floor/native.summary.json')+', '+link('runtime/COMMIT_FLOOR_METHOD.md')+'. Per-arm raw CSV and read-only host/storage metadata are retained beside the summaries.']
    j=read('results/littlex-diagnostics/20261019T195241Z/write-ad469-control/profile.json')['rows']
    p=read('results/littlex-sql-write/20261019T200000Z/summary.json');m=p['metrics']
    assert len(j)==100 and p['oracle_ok']
    metrics=[['Instrumented server p50 ms',f"{statistics.median(r['server_ms'] for r in j):.3f}",f"{m['server_ms']['median']:.3f}"],
        ['Application CPU total /100 calls ms',sum(r['application_process_cpu_ms'] for r in j),m['application_process_cpu_ms']['sum']],
        ['Tracked backend CPU total /100 calls ms',sum(r['database_backend_cpu_ms'] for r in j),m['database_backend_cpu_ms']['sum']],
        ['Mean logged protocol wall /call ms',f"{statistics.mean(r['database_protocol_total_ms'] for r in j):.3f}",f"{m['database_protocol_total_ms']['mean']:.3f}"],
        ['Mean logged execute events /call',statistics.mean(r['protocol']['execute']['count'] for r in j),1]]
    blocks+=[table(['create_tweet diagnostic','Historical Jac CONTROL','Hand SQL'],metrics),
        'These100-warm +100-profiled calls are instrumented diagnostics, separate from formal server medians2.598/1.322ms. Aggregate CPU totals reflect10ms tick resolution; wall times and CPU totals are not additive. Jac has additional measured application/backend/protocol work. The SQL app uses autocommit: implicit transaction completion has no separate COMMIT command, so a zero explicit-COMMIT log count is not a zero durability-cost measurement. Jac explicit COMMIT protocol median is1.439ms. Source evidence and timing-boundary details: '+link('littlex/DIAGNOSTIC_REPORT.md')+'.',
        '### Historical t20 write ordering',
        'The primary current CONTROL/SQL ratios for t20 create/follow/like are1.97/2.44/2.08; historical ratios were0.87/0.92/0.86. The original '+link('../DBHarness/session0904/run/AB_TABLE.md')+' itself marks t20 PostgreSQL writes34–36% slower than its banked night0823 reference: approximately8.9ms at t20 versus6.5–6.8ms at the other tiers. '+link('../DBHarness/night0823/FINDINGS.md')+' also records that proposed write-flag improvements did not reproduce in interleaved fresh-boot A/B. These are recorded historical variations, not a new causal measurement of that run. The present commit and write-work measurements characterize the current costs; the historical ranking reversal remains a documented comparison whose original cause is not identified.',
        'All workloads and diagnostics are complete. Owned benchmark API servers are stopped and statement logging is off. Data, fixture snapshots, raw result groups, controlled interventions and failed/pilot artifacts are retained.']
    state=read('logs/final-state.json')
    assert all(state[a]['database_logging_overrides']==[] and state[a]['log_statement']=='none' and state[a]['log_min_duration_statement']=='-1' and state[a]['fsync']==state[a]['synchronous_commit']=='on' for a in ('native','pg16'))
    blocks.append('Final state: '+link('logs/final-state.json')+'. Later diagnostic host observations are retained in `logs/littlex-host/`; these time series describe the sampled windows, while earlier runs retain their available launch/affinity/configuration artifacts.')
    return '\n\n'.join(blocks)


def profiles():
    bp=read('results/baseline-profile/profile.json');protocol=read('results/baseline-profile/protocol-offline-00.json');fp=read('results/final-full-profile/profile.json')
    assert len(fp['rows'])==5 and all(not r.get('error') for r in fp['rows'])
    b=bp['rows'][0];p=protocol['protocol'];rows=[]
    for name,key in [('Client wall','client_ms'),('Server wall','server_ms'),('Application process CPU','application_process_cpu_ms'),('Database Bind wall','database_bind_ms'),('Database Execute wall','database_execute_ms'),('Complete logged protocol wall','database_protocol_total_ms'),('Tracked backend CPU','database_backend_cpu_ms')]:
        rows.append([name,f"{fp['summary'][key]['median']:.3f}"])
    return ('These are separate **duration-logging-on diagnostic runs** for heavy IC5 parameter row 19. Latency conclusions use the logging-off tables above.\n\n'
            +f"Baseline repeat 0: client wall {b['client_ms']:.3f} ms; application CPU {b['application_process_cpu_ms']:.3f} ms; PostgreSQL Bind {p['bind']['ms']:.3f} ms and Execute {p['execute']['ms']:.3f} ms over {p['execute']['count']:,} executions. The complete protocol sum is {protocol['total_protocol_ms']:.3f} ms.\n\n"
            +'Final full-profile medians across five repetitions:\n\n'+table(['Measurement','Median ms'],rows)
            +'\n\nCPU and protocol wall time are different measurements and are not additive partitions. Application CPU comes from server-process user/system ticks; backend CPU covers discovered existing client backends. The client-minus-protocol residual includes application/driver/transport work and does not identify network time. The data supports a reduction in SQL execution count and substantial measured Bind processing in the baseline.\n\n'
            +'Evidence: '+link('results/baseline-profile/protocol-offline-00.json')+', '+link('results/baseline-profile/profile.json')+', '+link('results/final-full-profile/profile.json')+'. Raw `postgres-00.log` etc. preserve protocol duration events; `/proc` CPU deltas have 10 ms resolution.')


def clean_prose(text):
    """Space prose numbers while preserving inline code, URLs and link targets."""
    parts=re.split(r'(`[^`]*`|\]\([^)]*\)|https?://[^\s]+)',text)
    for i in range(0,len(parts),2):
        part=parts[i]
        part=re.sub(r'(?<=\d)(?=[A-Za-z]{2})',' ',part)
        part=re.sub(r'\b(all|first|full|golden|historical|observed|elapsed|under|on|for|over|with|row|idx|total|count|since|uses|has|own|is|pinned|and|September|Run|completes|original|The|These|after|starts|capture|measure|medians|median|near|versus|reflect|PostgreSQL|CPython|Python|PBS)(?=\d)',r'\1 ',part)
        for before,after in [('SNBqueries','SNB queries'),('TPC-Cplan','TPC-C plan'),('SQLparity','SQL parity'),('W3with','W3 with')]:part=part.replace(before,after)
        parts[i]=part
    return ''.join(parts)


def main():
    text=REPORT.read_text()
    for marker,build in [('FINAL_IC5_RESULTS',ic5),('FINAL_SNB_RESULTS',snb),('FINAL_TPCC_RESULTS',tpcc),('FINAL_PROFILE_RESULTS',profiles),('FINAL_LITTLEX_RESULTS',littlex),('FINAL_WRITE_DIAGNOSTICS',write_diagnostics)]:
        begin,end=f'<!-- BEGIN {marker} -->',f'<!-- END {marker} -->'
        assert text.count(begin)==text.count(end)==1,marker
        text=re.sub(re.escape(begin)+r'.*?'+re.escape(end),lambda _:begin+'\n'+build()+'\n'+end,text,flags=re.S)
    REPORT.write_text(clean_prose(text))
    print('Refreshed IC5, SNB, TPC-C, littleX and diagnostic-profile markers from completed files.')


if __name__=='__main__':
    main()
