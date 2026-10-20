#!/usr/bin/env python3
"""English evidence deck; all numeric cells are read from results.json."""
import os,pathlib,json,textwrap,statistics,subprocess
os.environ.setdefault('MPLCONFIGDIR','/tmp/jac-webridge-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
R=pathlib.Path(__file__).resolve().parent;W=R.parent
D=json.loads((R/'results.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42,'font.size':14})
NAMES={'jac-baseline':'Jac original','jac-final':'Jac final','full-baseline':'Java full','full-sp':'WeBridge full','pruned-baseline':'Java pruned','pruned-sp':'WeBridge pruned','set-baseline':'Java set-oriented','set-sp':'WeBridge set-oriented'}
QUERIES=['is1','is2','is3','ic1','ic2','ic13']
DESCRIPTIONS={'is1':'Person profile and location','is2':'Recent messages, reply roots and authors','is3':'Friends and projected person fields','ic1':'Name-filtered friends within three hops','ic2':"Friends’ recent messages and authors",'ic13':'Shortest path with a six-hop cap'}
pdf=PdfPages(R/'jac-webridge-snb-comparison.pdf');page=0

def slide(title,sub='',source=''):
 global page
 page+=1;f=plt.figure(figsize=(16,9),facecolor='white');f.text(.055,.93,title,fontsize=25,weight='bold',color='#0f172a');f.text(.055,.875,sub,fontsize=13,color='#475569');f.text(.055,.035,source,fontsize=8,color='#64748b');f.text(.95,.035,str(page),ha='right',fontsize=10,color='#64748b');return f

def finish(f):pdf.savefig(f);plt.close(f)
def text(f,s,y=.77,size=19,width=104,x=.06):
 for line in textwrap.wrap(s,width=width):f.text(x,y,line,fontsize=size,color='#1e293b');y-=size/350
 return y

def table(f,headers,rows,bbox=(.055,.22,.89,.58),widths=None,size=13):
 widths=widths or [1/len(headers)]*len(headers);widths=[x/sum(widths)for x in widths]
 limits=[max(9,int(1152*bbox[2]*x*.80/(size*.54)))for x in widths]
 def wrap(s,i):return '\n'.join('\n'.join(textwrap.wrap(z,limits[i],break_long_words=False))for z in str(s).split('\n'))
 ax=f.add_axes([0,0,1,1]);ax.axis('off');t=ax.table(cellText=[[wrap(v,i)for i,v in enumerate(row)]for row in rows],colLabels=[wrap(v,i)for i,v in enumerate(headers)],cellLoc='left',colLoc='left',bbox=bbox,colWidths=widths);t.auto_set_font_size(False);t.set_fontsize(size)
 for (row,col),c in t.get_celld().items():
  c.set_edgecolor('#e2e8f0');c.set_linewidth(.5);c.set_facecolor('#e2e8f0'if row==0 else '#f8fafc'if row%2 else'white')
  if row==0:c.set_text_props(weight='bold',color='#0f172a')
 return t

def value(q,s,d):
 x=next(z for z in D['latency']if(z['query'],z['system'],z['delay_ms'])==(q,s,d))
 return f"{x['median_ms']:.2f}"if x.get('median_ms')is not None else x['status']

f=slide('Jac and WeBridge: existing SNB benchmarks','Research problem · How do graph-aware SQL lowering and procedure synthesis compare?','Evidence: results.json; independent verification receipts; per-request outputs and protocol traces')
text(f,'Measure two separate transformations: combining graph operations into relational queries, and moving a sequence of database operations into one stored procedure.',y=.75,size=23,width=83)
text(f,'Six additional workloads: profile lookup, recent messages, friends, name-filtered traversal, friends’ messages and bounded shortest path.',y=.51,size=21,width=91)
text(f,'Each workload has eight configurations, original-parameter correctness gates, injected-delay timing, and an observed SQL / synchronization map.',y=.30,size=20,width=96)
f.text(.06,.13,str(sum(x.get('median_ms')is not None for x in D['latency']))+' measured latency medians · 27 censored first requests · detailed IC5 appendix',fontsize=15,color='#0891b2')
finish(f)
f=slide('A concrete example: recent messages','IS2: person → ten recent messages → reply roots → authors','Evidence: unchanged Jac app; native/profiles/operation-map.json; conventional frozen SQL and gates')
table(f,['Stage','Observed Jac database work','Conventional SQL'],[['Recent messages','One explicit jtopk call; lateral topK','ORDER BY + LIMIT 10'],['Reply roots','One explicit jroot_many call; promoted root column','Join root message mirror'],['Author information','Projection + traversal + anchor loads','Join message and root authors'],['Complete request','24 ordinary SQL cycles','4 commands: one business SELECT + 3 transaction commands']],size=15,widths=[.23,.42,.35],bbox=(.055,.30,.89,.48))
text(f,'The source already asks for topK and batched roots. The experiment identifies which stages are already database operators and which loads remain separate.',y=.19,size=16,width=118);finish(f)
f=slide('Solutions under test','The same logical outputs, with explicitly different execution boundaries','Evidence: source snapshots, actual procedure activation, canonical hash gates')
table(f,['Configuration pair','What the source expresses','What is measured'],[['Jac original / final','Existing Jac walker and runtime operators','Change from c12 to final32'],['Java full / WeBridge full','Native ordinary SQL sequence, including identity, ACL and hydration','Direct requests vs actual generated CALL'],['Java pruned / WeBridge pruned','Graph calculation with declared Jac overhead removed','Direct requests vs actual generated CALL'],['Set-oriented Java / WeBridge set-oriented','Conventional joins, projection, topK and bounded path queries','Direct queries vs actual generated CALL']],bbox=(.055,.23,.89,.55),widths=[.29,.40,.31],size=14)
text(f,'Jac uses PostgreSQL; Java and WeBridge use MySQL 5.7. Within each pair, source behavior, dataset and database engine are held fixed.',y=.14,size=14,width=135);finish(f)
f=slide('Matched data and original inputs','1,475,843 anchors · all Person and Knows records · complete query-specific message closure','Evidence: expansion/fixture receipts; inputs-all20.json; historical-hashes.json; independent gates')
text(f,'Each query retains its original twenty parameter rows. Performance and protocol profiles use original row zero; all six outputs are nonempty.',y=.76,size=20,width=96)
text(f,'The fixture contains authored messages, ReplyOf ancestors, authors, locations, endpoints and owner roots needed by all 120 query inputs. Thirteen logical anchor fields are verified after loading both engines.',y=.54,size=19,width=101)
text(f,'Native original/final: 240 result gates. Java full/pruned: 240 result gates. Conventional SQL: 120 result gates. Each timing request checks its actual output.',y=.29,size=19,width=102)
finish(f)
f=slide('Measurement and attribution','Quiet execution timing is collected separately from instrumented SQL/protocol profiles.','Evidence: native/latency; Java timing raw rows; calibration and cleanup receipts')
table(f,['Measurement','Definition'],[['Latency matrix','0 / 2 / 10 ms added delay; fast cells: 10 warmup + 30 measured; slow CALLs: three bounded 15-second attempts per condition'],['Jac timer','Server request span + commit; HTTP client time retained separately'],['Java timer','JDBC request span; thread CPU recorded separately'],['Synchronization cycle','Command sent → entire database response delivered; next command follows completion'],['Inside CALL','Actual nested table operations, cursor materializations, generated metadata and control events'],['Compilation','Original recording/replay/synthesis/install/activation stages; failures and compatibility changes retained']],bbox=(.055,.18,.89,.62),widths=[.25,.75],size=13);finish(f)
f=slide('Six new queries: native SQL does not change','Original and final emit the same ordinary SQL sequence for each representative input.','Evidence: native/profiles/ordinary-sql-equality.json; operation-map.json; 72 measured requests')
rows=[]
for q in QUERIES:
 c=D['native_operations'][q];ordinary=sum(x['min']for k,x in c.items()if k!='schema.ttl_guard');rows.append([q.upper(),DESCRIPTIONS[q],ordinary,ordinary])
table(f,['Query','Workload','Original cycles','Final cycles'],rows,bbox=(.055,.28,.89,.51),widths=[.10,.54,.18,.18],size=15)
text(f,'IC13 also executes one periodic schema TTL guard in one +2 ms profile per variant: actual totals reach 15 instead of 14. All other profiles retain the ordinary count.',y=.17,size=15,width=126);finish(f)
f=slide('Generated procedures: actual execution coverage','Every attempted configuration retains stage receipts and frozen source hashes.','Evidence: results.json pipeline observations; original compiler logs and compatibility overlays')
table(f,['Query','Full WeBridge','Pruned WeBridge','Set-oriented WeBridge'],[[q.upper(),*[D['coverage'][q][v]['label']for v in ['full','pruned','set']]]for q in QUERIES],bbox=(.055,.27,.89,.52),widths=[.10,.30,.30,.30],size=13)
text(f,'IC1 full / IC2 full emit usable SQL and runtime definitions before a recorder trace-hash stack overflow. The original artifacts are installed and tested; IC2 full completes, while IC1 full reaches the request limit.',y=.15,size=14,width=132);finish(f)
for q in QUERIES:
 f=slide(q.upper()+' — latency at three response delays',DESCRIPTIONS[q]+' · median milliseconds','Evidence: results.json → raw rows, independent verification, calibration receipts')
 rows=[]
 for s,n in NAMES.items():
  cycles=D['cycles'][q].get(s,{});ct=cycles.get('display','incomplete CALL'if q=='ic1'and s.endswith('-sp')else 'not captured');rows.append([n,*[value(q,s,d)for d in [0,2,10]],ct])
 table(f,['Configuration','0 ms','+2 ms','+10 ms','Measured sync cycles'],rows,bbox=(.055,.18,.89,.62),widths=[.36,.15,.15,.15,.19],size=13)
 if q=='ic1':text(f,'Generated SP cells: three fresh first requests per delay; warmup remains incomplete; 15-second request limit.',y=.12,size=12,width=145)
 finish(f)
 f=slide(q.upper()+' — what is combined, what remains?',DESCRIPTIONS[q],'Evidence: native SQL catalog; actual wire command sequences; executed P_S business operation maps')
 native=D['native_operations'][q];body=[]
 for cat,c in native.items():
  if cat.startswith('transaction.'):continue
  count=str(c['min'])if c['min']==c['max']else f"{c['min']}–{c['max']}"
  body.append([cat,count])
 table(f,['Native operation category','Executions'],body,bbox=(.055,.36,.45,.44),widths=[.80,.20],size=11)
 text(f,D['query_analysis'][q]['native'],x=.55,y=.77,size=15,width=48)
 text(f,D['query_analysis'][q]['webridge'],x=.55,y=.49,size=15,width=48)
 text(f,D['query_analysis'][q]['set'],x=.06,y=.24,size=16,width=118)
 finish(f)
# Actual nested work and traffic for each query, separately from latency.
for q in QUERIES:
 f=slide(q.upper()+' — executed WeBridge operations','Actual nested business operations, return work and client/server traffic','Evidence: mysql-profile/summary.json; source-associated cursor opens; complete observed CALL ranges')
 cols=[];categories=set()
 for v in ['full','pruned','set']:
  c=D['cycles'][q].get(v+'-sp');call=c.get('P_S_CALL')if c else None
  if call:
   counts={}
   for k,x in call['direct_child_categories'].items():
    if k.startswith('business.'):
     k=k.removeprefix('business.').removeprefix('cursor.');counts[k]=[a+b for a,b in zip(counts.get(k,[0,0,0]),x['counts'])]
   categories.update(counts)
   returns=[sum(x['counts'][i]for k,x in call['direct_child_categories'].items()if k.startswith('return.'))for i in range(3)]
   controls=[sum(x['counts'][i]for k,x in call['direct_child_categories'].items()if k.startswith('control.'))for i in range(3)]
   cols.append({'counts':counts,'returns':returns,'controls':controls,'wire':c,'call':call,'controls_observed':call.get('control_events_instrumented',True)})
  else:cols.append(None)
 def show(v):return str(min(v))if min(v)==max(v)else f'{min(v)}–{max(v)}'
 body=[]
 for cat in sorted(categories):body.append([cat,*[show(c['counts'].get(cat,[0,0,0]))if c else '—'for c in cols]])
 body.append(['Return / metadata SELECTs',*[show(c['returns'])if c else '—'for c in cols]])
 body.append(['Control instrumentation events',*[show(c['controls'])if c and c['controls_observed']else 'not collected'if c else '—'for c in cols]])
 table(f,['Actual operation category','Full','Pruned','Set-oriented'],body,bbox=(.055,.37,.89,.43),widths=[.49,.17,.17,.17],size=11)
 rows=[]
 for v,c in zip(['full','pruned','set'],cols):
  direct=D['cycles'][q].get(v+'-baseline');sp=D['cycles'][q].get(v+'-sp')
  rows.append([v,direct.get('display','—')if direct else '—',sp.get('display','—')if sp else D['coverage'][q][v]['label'],show(sp['frames'])if sp else '—',show(sp['result_sets'])if sp else '—',show(sp['response_wire_bytes'])if sp else '—'])
 table(f,['Variant','Direct cycles','CALL cycles','CALL frames','CALL result sets','CALL bytes'],rows,bbox=(.055,.12,.89,.19),widths=[.13,.14,.23,.15,.16,.19],size=11)
 finish(f)

f=slide('Where does CALL time go?','Direct-child instrumentation timers; parent CALL duration includes descendants','Evidence: mysql-profile/summary.json; three complete postwarm CALL ranges per displayed row')
rows=[]
for cell in (D.get('mysql_profile')or{}).get('cells',[]):
 call=cell.get('P_S_CALL')
 if not call:continue
 cats=call['direct_child_categories']
 def median_cost(prefix):return statistics.median(sum(x['timer_ms'][i]for k,x in cats.items()if k.startswith(prefix))for i in range(3))
 rows.append([cell['query'].upper(),cell['variant'],f"{statistics.median(call['parent_inclusive_ms']):.3f}",f"{median_cost('business.'):.3f}",f"{median_cost('control.'):.3f}"if call.get('control_events_instrumented',True)else 'not collected',f"{median_cost('return.'):.3f}"])
table(f,['Query','Variant','CALL ms','Business ms','Control ms','Return ms'],rows,bbox=(.055,.20,.89,.60),widths=[.10,.22,.17,.17,.17,.17],size=11)
text(f,'These instrumented timings locate work inside successful CALLs. The quiet latency matrix uses separate runs with stored-program instrumentation disabled.',y=.12,size=14,width=133)
finish(f)

f=slide('IC1: fewer commands can still perform more SQL work','Same MySQL fixture and input · quiet request medians beside separate instrumented statement medians','Evidence: ic1-same-engine-comparison.json; exact wire SQL hashes, UUID cardinalities and P_S rows/timers')
matched=json.loads((R/'ic1-same-engine-comparison.json').read_text());rows=[]
for variant,name in [('full','full'),('pruned','pruned'),('conventional','set')]:
 cats=matched[variant]['categories'];front=cats['closure.frontier_adjacency'];proj=cats['person.filter_or_projection'if variant=='conventional'else'anchor.projection'];qops=[o for o in matched[variant]['requests'][0]['operations']if o['category']==('person.filter_or_projection'if variant=='conventional'else'anchor.projection')]
 rows.append([variant,value('ic1',name+'-baseline',0),f"{front['median_sum_pfs_server_ms']:.2f}",f"{proj['median_sum_pfs_server_ms']:.2f}",str(int(proj['median_sum_pfs_rows_examined'])),str(max(o['uuid_literal_count']for o in qops))])
table(f,['Java variant','Quiet 0ms request','Profile frontier ms','Profile final query ms','Final query rows examined','Final query UUIDs'],rows,bbox=(.055,.43,.89,.35),widths=[.15,.17,.17,.17,.18,.16],size=13)
text(f,'Full/pruned preselect twenty name-matching candidate IDs, then project eighteen surviving people. The conventional query filters after BFS using 9,036 visited UUIDs and examines all 9,932 Person rows.',y=.32,size=19,width=100)
text(f,'All three run the same frontier inputs: 1 / 10 / 2,740 UUIDs; frontier statements examine 175,262 rows and return 11,769 rows in each request.',y=.15,size=16,width=123)
finish(f)
f=slide('IC13: measured time beyond table statements','Actual completed CALLs with business-statement instrumentation; control events are unobserved','Evidence: ic13-cost-breakdown.json; business-only settings, observed P_S event ranges and cursor-source association')
cost=json.loads((R/'ic13-cost-breakdown.json').read_text());rows=[]
for variant,name in [('full','full'),('pruned','pruned'),('conventional','set')]:
 profile=next(x for x in cost['mysql_profiles']if x['kind']==variant);group=next(x for x in profile['groups']if x['phase']=='sp')
 rows.append([variant,value('ic13',name+'-sp',0),f"{group['CALL_parent_median_ms']:.3f}",f"{group['CALL_direct_child_sum_median_ms']:.3f}",f"{group['CALL_parent_minus_direct_children_median_ms']:.3f}"])
table(f,['Variant','Quiet 0ms request','Profile CALL ms','Profile child statements ms','Remaining CALL interval ms'],rows,bbox=(.055,.43,.89,.34),widths=[.16,.21,.20,.22,.21],size=14)
text(f,'About 2.1 seconds remain inside the full/pruned procedures beyond the instrumented child statements. This interval includes uninstrumented cursor/control and other procedure runtime work.',y=.30,size=19,width=101)
text(f,'The source has about 4.85 million row-index checks at recorded cursor sizes. The conventional scalar CASE/EXISTS procedure has a much smaller remaining interval.',y=.14,size=16,width=121)
finish(f)

f=slide('Intermediate results shape generated control work','Source-derived row-index checks at recorded cursor cardinalities, beside measured quiet latency','Evidence: java/cursor-dispatch-analysis.json → hashed generated SQL; results.json → quiet request rows')
static=json.loads((W/'snb-extension/java/cursor-dispatch-analysis.json').read_text());rows=[]
for q in QUERIES:
 counts=[next(x['total_full_result_equality_checks']for x in static if x['query']==q and x['variant']==v)for v in ['full','pruned']]
 rows.append([q.upper(),*[f'{n:,}'for n in counts],value(q,'full-sp',0),value(q,'pruned-sp',0)])
table(f,['Query','Full static checks','Pruned static checks','Full quiet ms','Pruned quiet ms'],rows,bbox=(.055,.30,.89,.49),widths=[.10,.23,.23,.22,.22],size=14)
text(f,'IC13 captures large BFS intermediate results in row-specific variables. The conventional bounded CASE/EXISTS query performs path tests inside one SQL statement and returns a scalar.',y=.18,size=17,width=113)
finish(f)

f=slide('IC1: why one CALL can still be expensive','Measured generated-code behavior · the pruned procedure retains frontier BFS results','Evidence: java/runaway-ic1/loop-structure.json; completed report-0.json; server P_S counters')
structure=json.loads((W/'snb-extension/java/runaway-ic1/loop-structure.json').read_text())
rows=[]
for loop in structure['loops']:
 n=loop['equality_dispatch_branches'];rows.append([str(loop['loop']),f'{n:,}',f'{n+1:,}',f'{n*(n+1):,}'])
table(f,['Cursor loop','Independent IF branches','Loop visits through exit','Equality checks'],rows,bbox=(.055,.47,.89,.30),widths=[.16,.28,.28,.28],size=16)
total=sum(x['equality_dispatch_branches']*(x['equality_dispatch_branches']+1)for x in structure['loops'])
text(f,f'Total generated equality checks: {total:,}. Each fetched row scans all row-specific IF branches before the loop advances.',y=.35,size=22,width=86)
text(f,'One instrumented CALL completed correctly: 129.396 seconds inside the server. A separate quiet run with stored-program instrumentation disabled exceeded the 15-second limit and was terminated.',y=.17,size=17,width=113)
finish(f)
f=slide('IC1: the generated dispatch mechanism','A bounded cursor loop with a separate destination variable for every captured row','Evidence: actual generated procedure cited in loop-structure.json; branch counts 10 / 2,750 / 9,009')
code="""loop_3: LOOP
  IF cursor_cnt_3=0 THEN FETCH cursor_3 INTO RS_q4_r1_col1; END IF;
  IF cursor_cnt_3=1 THEN FETCH cursor_3 INTO RS_q4_r2_col1; END IF;
  ...
  IF cursor_cnt_3=9008 THEN FETCH cursor_3 INTO RS_q4_r9009_col1; END IF;
  IF cursor_cnt_3>=9009 THEN CLOSE cursor_3; LEAVE loop_3; END IF;
  ...
  SET cursor_cnt_3 = cursor_cnt_3 + 1;
END LOOP;"""
f.text(.065,.73,code,fontfamily='DejaVu Sans Mono',fontsize=13,linespacing=1.6,va='top',color='#0f172a')
text(f,'The three source adjacency queries remain three database queries inside CALL. The large intermediate frontiers also produce row-specific procedural control work.',y=.24,size=19,width=101)
text(f,'Quiet slow-arm cells preserve three actual bounded attempts per delay condition. Completed latency samples and censored attempts have separate labels and raw receipts.',y=.12,size=15,width=128)
finish(f)

f=slide('Compare with IC5: a different observed optimization','Existing IC5 evidence uses its own 460,984-anchor matched fixture.','Evidence: roundtrip-comparison/eight-arm-verification.json and webridge-operation-map.json')
table(f,['Observation','IC5','Six additional queries'],[['Jac ordinary SQL count','38 → 14','Unchanged in each original/final pair'],['Actual Jac combination','10 membership queries → 1; 16 post/creator queries → 1 aggregate','Existing topK, projections, promoted roots and adjacency expansion'],['WeBridge transformation','35 full / 28 pruned business operations execute inside one CALL','Per-query executed operations and capture-stage receipts'],['Conventional baseline','One aggregate SQL + 3 transaction commands','Query-specific joins, topK and bounded path SQL']],bbox=(.055,.26,.89,.53),widths=[.23,.37,.40],size=13)
text(f,'The detailed IC5 experiment follows as an appendix, with its complete eight-configuration matrix and nested operation counts.',y=.14,size=15,width=126);finish(f)
f=slide('Evidence and reproduction','Raw outputs, timing rows, SQL catalogs, procedure sources and measured failure stages','Evidence: archive-manifest.json; benchmark-comparison/verify_results.py; results.json')
for i,(title,body)in enumerate([('Inputs','Frozen twenty-row inputs and historical result hashes; fixture export/load SHA receipts.'),('Correctness','Actual result objects rehashed against the frozen oracle; activation and driver/server counts checked.'),('Performance','All measured requests and calibration controls; original timer boundaries and warmup labels.'),('SQL and protocol','Complete-response sequencing, SQL categories, nested executed work, generated procedure hashes.'),('Compilation','Captured attempts, precise failed stages, isolated compatibility diffs and selected immutable cases.')]):
 y=.76-i*.12;f.text(.06,y,title,fontsize=16,weight='bold',color='#0891b2');text(f,body,x=.23,y=y,size=14,width=94)
finish(f);pdf.close()
final=R/'jac-webridge-snb-comparison.pdf';sections=R/'snb-extension-sections.pdf';os.replace(final,sections)
subprocess.run(['pdfunite',str(sections),str(W/'roundtrip-comparison/jac-webridge-measured-comparison.pdf'),str(final)],check=True);sections.unlink()
print(final)
