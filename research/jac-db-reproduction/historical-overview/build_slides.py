#!/usr/bin/env python3
"""Build an English overview from the colleague's September 4/5 raw artifacts."""
import csv, hashlib, json, os, statistics, textwrap
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/jac-historical-slides-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch
R=Path(__file__).resolve().parent
S=R/'sources'
manifest=json.loads((R/'source-manifest.json').read_text())
for f in manifest['files']:
 assert hashlib.sha256((S/f['path']).read_bytes()).hexdigest()==f['sha256'],f['path']
def csvrows(p):return list(csv.DictReader((S/p).open()))
burden={}
for r in csvrows('benchmark/burden/viewer_counts.csv'):
 k=(r['bench'],r['arm']);v={n:int(r[n]) for n in ['loc','dbloc','chars','dbchars']}
 assert k not in burden or burden[k]==v
 burden[k]=v
ladder=[]
for tag in ['base','A','AB','ABC1','ABC','ABCD1','FULL','D4','FINAL','D5']:
 rows=json.loads((S/f'session0904/ic5/build/gates/ic5_{tag}.json').read_text())
 assert len(rows)==20 and all(r['parity'] and not r['err'] for r in rows)
 ladder.append({'tag':tag,'sql_total':sum(r['stmts'] for r in rows),'jac_p50_ms':statistics.median(r['jac_ms'] for r in rows),'pg_p50_ms':statistics.median(r['pg_ms'] for r in rows),'correct':20})
assert ladder[0]['sql_total']==278769 and ladder[-1]['sql_total']==432
snb=csvrows('session0904/run/data/snb/snb_master.csv')
tpcc=csvrows('session0904/run/data/tpcc/tpcc_master.csv')
feeds=[]
for kind in ['baselines','control','best']:
 for row in csvrows(f'session0904/run/data/littlex_{kind}/w1_master.csv'):
  row=dict(row,configuration=kind);feeds.append(row)
DATA={'scope':'Historical colleague data, September 4/5 2026','burden':[dict(bench=k[0],arm=k[1],**v) for k,v in burden.items()],'ic5_ladder':ladder,'snb':snb,'tpcc':tpcc,'littlex_feed':feeds}
(R/'data.json').write_text(json.dumps(DATA,indent=2)+'\n')
plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42})
PDF=PdfPages(R/'jac-db-programming-historical-overview.pdf')
PDF.infodict()['Title']='Jac for Database Programming: Existing Work and Historical Evidence'
N=0
def page(title,sub='',source=''):
 global N
 N+=1;f=plt.figure(figsize=(16,9),facecolor='white')
 f.text(.055,.925,title,fontsize=27,weight='bold',color='#102a43')
 f.text(.055,.855,textwrap.fill(sub,128),fontsize=14,color='#52667a',va='top')
 f.text(.055,.035,textwrap.fill(source,185),fontsize=8,color='#64748b')
 f.text(.95,.035,str(N),ha='right',fontsize=10,color='#64748b')
 f.text(.055,.975,'JAC  /  DATABASE PROGRAMMING',fontsize=9,color='#2563eb')
 return f
def para(f,text,y=.74,size=22,width=84):
 lines=textwrap.wrap(text,width,break_long_words=False)
 f.text(.06,y,'\n'.join(lines),fontsize=size,color='#243b53',va='top',linespacing=1.5)
 return y-len(lines)*size/430-.07
def note(f,text):para(f,text,y=.14,size=13,width=140)
def table(f,heads,rows,widths=None,size=14,bbox=(.055,.23,.89,.55)):
 widths=widths or [1/len(heads)]*len(heads);widths=[v/sum(widths) for v in widths]
 limits=[max(9,int(1152*bbox[2]*w*.80/(size*.54))) for w in widths]
 wrap=lambda v,i:'\n'.join(textwrap.fill(line,limits[i],break_long_words=False) for line in str(v).split('\n'))
 ax=f.add_axes([0,0,1,1]);ax.axis('off')
 t=ax.table(cellText=[[wrap(v,i) for i,v in enumerate(row)] for row in rows],colLabels=[wrap(v,i) for i,v in enumerate(heads)],colWidths=widths,cellLoc='left',colLoc='left',bbox=bbox)
 t.auto_set_font_size(False);t.set_fontsize(size)
 for (row,col),c in t.get_celld().items():
  c.set_edgecolor('#dbe4ed');c.set_linewidth(.6);c.set_facecolor('#dce9f7' if row==0 else '#f3f7fb' if row%2 else 'white')
  if row==0:c.set_text_props(weight='bold',color='#102a43')
def flow(f,labels,caption='',y=.39):
 ax=f.add_axes([.05,.22,.90,.50]);ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off');n=len(labels);w=.82/n
 for i,label in enumerate(labels):
  x=(i+.5)/n
  ax.add_patch(FancyBboxPatch((x-w/2,y),w,.29,boxstyle='round,pad=.012',edgecolor='#98b4d0',facecolor='#e9f2fc',linewidth=1.3))
  ax.text(x,y+.145,label,ha='center',va='center',fontsize=16,color='#102a43')
  if i<n-1:ax.annotate('',xy=((i+1.5)/n-w/2-.012,y+.145),xytext=(x+w/2+.012,y+.145),arrowprops={'arrowstyle':'->','lw':1.6,'color':'#2563eb'})
 if caption:ax.text(.5,.12,caption,ha='center',va='center',fontsize=15,color='#52667a')
def done(f):
 f.canvas.draw();renderer=f.canvas.get_renderer()
 for t in f.texts:
  while t.get_window_extent(renderer).x1>f.bbox.width*.96 and t.get_fontsize()>10:t.set_fontsize(t.get_fontsize()-.5)
 PDF.savefig(f);plt.close(f)

f=page('Jac for Database Programming','Existing language work, compiler mechanisms and historical evidence | September 4–5, 2026','Sources: DBHarness historical artifacts; exact paths and SHA-256 values accompany this deck.')
y=para(f,'Research objective',size=18)
y=para(f,'Make persistent graph applications easier to write, while the compiler and runtime organize efficient database access.',y=y,size=29,width=65)
para(f,'Two linked questions: how much database plumbing does the programmer write, and how effectively does the system execute that program?',y=y-.025,size=21,width=89);done(f)

f=page('Research problem: one application, two kinds of work','Expressing business logic and organizing database execution both consume development effort.','Source: session0904/BURDEN.md; session0904/ic5/COMPILER_PLAN.md')
table(f,['Application logic','Database execution decisions'],[['Follow domain relationships','Choose joins and query boundaries'],['Filter, count, rank and update','Batch loads and avoid per-object round trips'],['Enforce application behavior','Project fields, load objects and maintain access checks']],[.47,.53],size=19)
note(f,'The opportunity: express domain intent once and let the language implementation handle more execution decisions.');done(f)

f=page('Example problem: find the most active relevant forums','IC5 benchmark: one-hop friends, forums joined after a date, and posts by qualifying friends.','Source: session0904/ic5/COMPILER_PLAN.md; benchmark/snb/jaseci-pg/app.jac')
flow(f,['Person','Friends','Joined forums','Matching posts'],caption='Count per forum → order by count and forum ID → return the top 20')
note(f,'The relevant relationships are explicit; the program must combine traversal, edge filtering, membership, aggregation and ranking.');done(f)

f=page('Solution: keep graph intent visible to the system','Jac supplies typed nodes, edges and walkers; compiler/runtime mechanisms organize their database execution.','Source: session0904/ic5/build/REPORT.md; historical Jac compiler/runtime commits')
flow(f,['Jac application\nNodes + walkers','Compiler analysis\nTypes + effects','Runtime plans\nBatch + project','PostgreSQL\nExecute + return'],caption='Graph traversal and application logic share the same language')
note(f,'Existing mechanisms include typed lookup, ranged hops, loop prefetch, nested-count lowering and delayed hydration.');done(f)

f=page('A concrete language example: typed, bounded traversal','Source excerpt: select people within three Knows hops and filter by firstName.','Source: benchmark/snb/jaseci-pg/app.jac:284,294; session0904/BURDEN.md')
code='start = jobj(self.person_jid, Person);\n\nfor (f, dist) in [start<-:Knows:*3:->[?:Person,\n    firstName==self.first_name]] {\n    ...\n}'
f.text(.065,.72,code,fontfamily='DejaVu Sans Mono',fontsize=20,color='#17365d',va='top',linespacing=1.6)
note(f,'The typed lookup replaced nine explicit type-check blocks in the SNB burden copy. Ranged hops replaced closure calls plus hydration/filtering code. Ellipsis abbreviates the original loop body.');done(f)

f=page('What the colleague implemented','The existing contribution spans language expression, execution mechanisms and application evidence.','Source: session0904/BURDEN.md; session0904/ic5/build/REPORT.md; historical runtime commit history')
table(f,['Layer','Existing work'],[['Language / API','Typed jobj lookup; variable-length graph hops; field and edge predicates'],['Compiler','Loop prefetch; field-use projection; nested-hop count recognition; sort/slice fusion'],['Runtime / storage','Batched adjacency; SQL aggregation and Top-K; typed projections; request-local memoization'],['Applications / evaluation','SNB, TPC-C and littleX; SQL / ORM / Neo4j counterparts; parity gates and burden counts']],[.25,.75],size=16)
done(f)

f=page('Data: fewer database-related lines','Historical burden copies, using the colleague’s database-access line classification.','Source: benchmark/burden/viewer_counts.csv; FORMAT_FAIRNESS.md; session0904/BURDEN.md')
ax=f.add_axes([.12,.27,.79,.48]);names=['SNB','TPC-C','littleX'];arms=['jac','postgres','sqlalchemy'];colors=['#2563eb','#94a3b8','#cbd5e1']
for i,(arm,color) in enumerate(zip(arms,colors)):
 vals=[burden[(b,arm)]['dbloc'] for b in ['snb','tpcc','littlex']];xs=[j+(i-1)*.23 for j in range(3)]
 ax.bar(xs,vals,width=.21,color=color,label={'jac':'Jac','postgres':'PostgreSQL','sqlalchemy':'SQLAlchemy'}[arm])
 for x,v in zip(xs,vals):ax.text(x,v+3,str(v),ha='center',fontsize=13)
ax.set_xticks(range(3),names);ax.set_ylim(0,235);ax.set_ylabel('DB-related source lines');ax.spines[['top','right']].set_visible(False);ax.legend(frameon=False,ncol=3,loc='upper center')
note(f,'Database-related lines are classified source lines. The counts describe these implementations; development effort also depends on the tasks programmers perform.');done(f)

f=page('Data: total application size has a different ranking','Historical LoC / database-related LoC, including all available comparison arms.','Source: benchmark/burden/viewer_counts.csv; FORMAT_FAIRNESS.md')
rows=[]
for b,label in [('snb','SNB'),('tpcc','TPC-C'),('littlex','littleX')]:
 vals=[]
 for a in ['jac','postgres','sqlalchemy','neo4j']:
  v=burden.get((b,a));vals.append(f"{v['loc']} / {v['dbloc']}" if v else '—')
 rows.append([label,*vals])
table(f,['Application','Jac','PostgreSQL','SQLAlchemy','Neo4j'],rows,[.2,.2,.2,.2,.2],size=18)
note(f,'Jac has fewer DB-related lines in these comparisons. SNB total LoC is 320 for Jac, 315 for PostgreSQL and 202 for Neo4j. Both measurements belong in the evaluation.');done(f)

f=page('Solution example: optimize an unchanged IC5 walker','Historical compiler/runtime ladder: baseline c12ba889d → final 32c5d1dbb.','Source: session0904/ic5/build/REPORT.md; COMPILER_PLAN.md')
table(f,['Program structure','System transformation'],[['Nested per-object graph access','Batch each frontier; reuse request-local adjacency results'],['Count posts whose author is in a qualifying set','Lower the recognized nested count to SQL aggregation'],['Sort counts and take 20','Perform ordering and Top-K inside SQL'],['Read winning forum fields','Project needed fields and hydrate selected winners']],[.47,.53],size=17)
note(f,'The walker still constructs qualifying forum/member pairs. The final execution combines application-side work with generated database operations.');done(f)

f=page('Data: IC5 SQL work falls by roughly 645×','20 historical parameter rows; identical walker; all rows pass output parity at every rung.','Source: session0904/ic5/build/gates/ic5_*.json; values recomputed from the raw arrays')
ax=f.add_axes([.12,.30,.79,.45]);xs=range(len(ladder));vals=[r['sql_total'] for r in ladder]
ax.bar(xs,vals,color=['#94a3b8']+['#93c5fd']*8+['#2563eb']);ax.set_yscale('log');ax.set_ylim(100,1500000);ax.set_xticks(list(xs),[r['tag'] for r in ladder]);ax.set_ylabel('SQL statements over 20 requests (log scale)');ax.spines[['top','right']].set_visible(False)
for x,v in zip(xs,vals):ax.text(x,v*1.18,f'{v:,}',ha='center',fontsize=12)
note(f,f"Baseline {vals[0]:,} → D5 {vals[-1]:,} statements ({vals[0]/vals[-1]:.1f}× fewer). Intermediate counts reflect different hydration and planning choices.");done(f)

f=page('Data: the historical IC5 optimization ladder','Application-request timing, milliseconds; each rung has a paired hand-written PostgreSQL measurement.','Source: session0904/ic5/build/gates/ic5_*.json; arithmetic medians over 20 rows')
rows=[[r['tag'],f"{r['sql_total']:,}",f"{r['jac_p50_ms']:.2f}",f"{r['pg_p50_ms']:.2f}",'20 / 20'] for r in ladder]
table(f,['Rung','SQL total','Jac p50 ms','Paired PG p50 ms','Output parity'],rows,[.14,.22,.23,.25,.16],size=13,bbox=(.055,.20,.89,.59))
note(f,'September 5 ran on a busy host; timing windows varied across rungs. Source-pinned SQL counts and result parity provide the clearest evidence of the transformation.');done(f)

f=page('Data: SNB performance depends on the query','September 4 client-request p50, milliseconds; historical CONTROL / BEST flag configurations.','Source: session0904/run/data/snb/snb_master.csv; this cohort predates the September 5 IC5 ladder')
def snbcell(q,arm,flag='n/a'):
 rr=[r for r in snb if r['query']==q and r['arm']==arm and r['flagset']==flag];assert len(rr)==1;return f"{float(rr[0]['client_p50_ms']):.2f}"
rows=[[q.upper(),snbcell(q,'postgres'),snbcell(q,'sqlalchemy'),snbcell(q,'neo4j'),snbcell(q,'jaseci-pg','CONTROL'),snbcell(q,'jaseci-pg','BEST')] for q in ['is1','is2','is3','ic1','ic2','ic5','ic13']]
table(f,['Query','PG','SQLAlchemy','Neo4j','Jac CONTROL','Jac BEST'],rows,[.13,.15,.19,.15,.19,.19],size=14)
note(f,'Jac is faster than the PostgreSQL implementation for IC1 and IC2 in this cohort. The large IC5 gap motivated the later compiler ladder. Existing application strategies include batching and explicit query helpers.');done(f)

f=page('Data: TPC-C places Jac between or near SQL and ORM','September 4 client-request p50, milliseconds; one warehouse, sequential transaction schedule.','Source: session0904/run/data/tpcc/tpcc_master.csv; 100 warmup + 800 measured requests')
def tcell(op,a,flag='n/a'):
 rows=[r for r in tpcc if r['op']==op and r['arm']==a and r['flagset']==flag];assert len(rows)==1;return f"{float(rows[0]['client_p50_ms']):.2f}"
rows=[[label,tcell(op,'postgres'),tcell(op,'sqlalchemy'),tcell(op,'jaseci-pg','CONTROL'),tcell(op,'jaseci-pg','BEST')] for op,label in [('new_order','New-Order'),('payment','Payment')]]
table(f,['Operation','PostgreSQL','SQLAlchemy','Jac CONTROL','Jac BEST'],rows,[.22,.19,.19,.20,.20],size=17)
note(f,'The measured 800 requests include 437 successful New-Orders, 357 Payments and 6 expected rollbacks. The CSV groups those rollbacks with New-Order. Timing covers the application request.');done(f)

f=page('Data: full-feed cost grows with tweets per user','September 4 application-server p50, milliseconds; 100 users and 50 follows per user.','Source: session0904/run/data/littlex_{baselines,control,best}/w1_master.csv')
def feedcell(tier,arm,config):
 rows=[r for r in feeds if r['tier']==tier and r['arm']==arm and r['configuration']==config];assert len(rows)==1;return f"{float(rows[0]['server_p50_ms']):.2f}"
rows=[[t,feedcell(t,'postgres','baselines'),feedcell(t,'sqlalchemy','baselines'),feedcell(t,'neo4j','baselines'),feedcell(t,'jaseci-pg','control'),feedcell(t,'jaseci-pg','best')] for t in ['t20','t50','t100','t200']]
table(f,['Tweets / user','PostgreSQL','SQLAlchemy','Neo4j','Jac CONTROL','Jac BEST'],rows,[.17,.16,.17,.15,.18,.17],size=14)
note(f,'Each full feed returns 1,000 / 2,500 / 5,000 / 10,000 tweets respectively. The PostgreSQL implementation is faster for this workload; the historical study also includes writes and paged-feed mixes.');done(f)

f=page('What the historical evidence establishes','Programming abstraction and execution quality are two dimensions of the same research objective.','Sources: historical burden metrics, IC5 raw parity/count gates and SNB/TPC-C/littleX master CSVs')
table(f,['Finding','Evidence'],[['Less database-specific application code','Lower DB-related line counts across the three application families'],['System improvements can preserve application source','IC5 unchanged walker: 278,769 → 432 SQL statements; 20/20 output parity'],['Execution quality depends on workload and program shape','SNB IC1/IC2 advantages; TPC-C and full-feed comparisons show remaining costs'],['The existing system exposes useful optimization information','Typed relations, traversal direction, predicates, field use and recognized loop effects']],[.41,.59],size=16)
done(f)

f=page('Research direction: make efficient DB programming easier','Evaluate the language and system together through concrete application tasks.','Proposal derived from the historical evidence; task and maintenance measurements are the next evaluation step.')
y=para(f,'Programmer task: implement and then modify a graph-backed feature.',size=23)
y=para(f,'Measure the work: database-specific code, manual batching, query helpers, and edits required when the feature changes.',y=y,size=22)
y=para(f,'Measure the execution: correctness, SQL counts and clearly defined latency, across natural program variants.',y=y,size=22)
para(f,'Goal: keep application intent clear while the system carries more of the database execution burden.',y=y,size=22);done(f)
PDF.close()
(R/'verification.json').write_text(json.dumps({'status':'PASS','source_files_verified':len(manifest['files']),'ic5_rungs':len(ladder),'ic5_parameter_rows_per_rung':20,'all_ic5_parity':True,'ic5_sql_total_before':ladder[0]['sql_total'],'ic5_sql_total_after':ladder[-1]['sql_total'],'pages':N,'pdf_sha256':hashlib.sha256((R/'jac-db-programming-historical-overview.pdf').read_bytes()).hexdigest()},indent=2)+'\n')
print(json.dumps({'pages':N,'pdf':str(R/'jac-db-programming-historical-overview.pdf')}))
