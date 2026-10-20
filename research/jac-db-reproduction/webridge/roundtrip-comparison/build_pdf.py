#!/usr/bin/env python3
"""Build the English evidence deck from verified timing and protocol data."""
import os,pathlib,json,textwrap,statistics
os.environ.setdefault('MPLCONFIGDIR','/tmp/jac-webridge-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
R=pathlib.Path(__file__).resolve().parent;B=R.parent
D=json.loads((R/'eight-arm-verification.json').read_text());assert D['all_checks_passed'];rows=D['performance_rows'];protocol=D['protocol_rows'];names=[x['system']for x in protocol]
colors=['#94a3b8','#0891b2','#a8a29e','#2563eb','#d4b16a','#7c3aed','#059669','#0f766e'];plt.rcParams.update({'font.family':'DejaVu Sans','font.size':14,'pdf.fonttype':42})
pdf=PdfPages(R/'jac-webridge-measured-comparison.pdf');page=0

def slide(title,sub='',source=''):
 global page
 page+=1;fig=plt.figure(figsize=(16,9),facecolor='white');fig.text(.055,.92,title,fontsize=26,weight='bold',color='#0f172a');fig.text(.055,.866,sub,fontsize=13,color='#475569');fig.text(.055,.035,source,fontsize=8.5,color='#64748b');fig.text(.95,.035,str(page),fontsize=10,color='#64748b',ha='right');return fig

def finish(fig):pdf.savefig(fig,bbox_inches=None);plt.close(fig)

def para(fig,text,x=.06,y=.76,width=100,size=17,dy=.05):
 for line in textwrap.wrap(text,width=width):fig.text(x,y,line,fontsize=size,color='#1e293b');y-=dy
 return y

def table(fig,headers,data,bbox=(.055,.19,.89,.59),fontsize=13,widths=None):
 widths=widths or [1/len(headers)]*len(headers)
 widths=[w/sum(widths) for w in widths]
 limits=[max(10,int(1152*bbox[2]*w*.80/(fontsize*.54))) for w in widths]
 wrap=lambda value,j:'\n'.join('\n'.join(textwrap.wrap(part,width=limits[j],break_long_words=False))for part in str(value).split('\n'))
 data=[[wrap(value,j)for j,value in enumerate(row)]for row in data];headers=[wrap(value,j)for j,value in enumerate(headers)]
 ax=fig.add_axes([0,0,1,1]);ax.axis('off');t=ax.table(cellText=data,colLabels=headers,cellLoc='left',colLoc='left',bbox=bbox,colWidths=widths);t.auto_set_font_size(False);t.set_fontsize(fontsize)
 for(k,c)in t.get_celld().items():
  c.set_edgecolor('#e2e8f0');c.set_linewidth(.5)
  if k[0]==0:c.set_facecolor('#e2e8f0');c.set_text_props(weight='bold',color='#0f172a')
  else:c.set_facecolor('#f8fafc'if k[0]%2 else'white')
 return t

def box(ax,x,y,w,h,label,color='#e0f2fe',size=16):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.012',facecolor=color,edgecolor='#cbd5e1'));ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=size,color='#0f172a')

def arrow(ax,a,b):ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=17,color='#64748b',lw=1.5))

f=slide('Jac and WeBridge: measured SQL fusion and database round trips','Two complete experiments · eight configurations · fixed nonempty IC5 input','Evidence: eight-arm-verification.json; webridge-operation-map.json; Jac roundtrip-profile/results/operation-map.json')
para(f,'Experiment 1: request latency at 0, 2 and 10 ms injected response delay.',y=.73,size=21,width=90)
para(f,'Experiment 2: the exact SQL operations and serialized command/response cycles for every configuration.',y=.59,size=21,width=90)
para(f,'Jac emits fewer business queries through batching and relational aggregation. WeBridge full/pruned puts the original business-query sequence inside one CALL. Set-oriented Java already expresses the graph calculation as one SQL query.',y=.40,size=19,width=100)
f.text(.06,.15,'960 main timing requests + 240 reverse-order requests; 30 measured protocol profiles.',fontsize=16,color='#0891b2');finish(f)

f=slide('One input and matched logical graph data','460,984 anchors · 300,901 edges · exact-result checks in every timing request','Evidence: alignment/small-diagnostic/input.json; jac-comparison/fixture/load-receipt.json; correctness gates')
ax=f.add_axes([.06,.42,.88,.32]);ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
labels=['Input person','10 friends','1 qualifying\nforum','15 posts','Creators +\ncount / top-20'];xs=[.005,.205,.405,.605,.805]
for x,label in zip(xs,labels):box(ax,x,.30,.17,.43,label,size=15)
for x in xs[:-1]:arrow(ax,(x+.17,.515),(x+.205,.515))
f.text(.06,.33,'personId = 8796093030404; minDate = 1347527525888',fontsize=18)
f.text(.06,.25,'Expected: forum 2061584375281, “Album 7 of Jie Xie”, postCount 0.',fontsize=17)
para(f,'Jac uses PostgreSQL 18.6 and runtime mirror/adjacency structures. Java uses MySQL 5.7.44 over generic anchors. Cross-system timing compares these complete implementations.',y=.15,size=14,width=130,dy=.035);finish(f)

f=slide('Experiment 1 — complete latency matrix','Median execution time (ms) · 10 warmup + 30 measured requests per cell','Evidence: eight-arm-verification.json and raw per-request rows; calibrated SELECT 1 receipts')
body=[]
for n in names:
 rr=[r for r in rows if r['system']==n];c=next(x['command_response_cycles']for x in protocol if x['system']==n);body.append([n,*[f"{x['median_ms']:.2f}"for x in rr],str(c)])
table(f,['Configuration','0 ms','+2 ms','+10 ms','SQL / sync cycles'],body,bbox=(.055,.20,.89,.60),fontsize=14,widths=[.38,.15,.15,.15,.17])
para(f,'All settings use the same delay-proxy path. Jac: server-total + commit timer. Java: JDBC request timer. Both exclude response JSON serialization.',y=.13,size=12,width=150,dy=.03);finish(f)

f=slide('Experiment 1 — latency under added delay','Each panel has its own millisecond scale; values come from the complete matrix.','Evidence: eight-arm-verification.json · raw timing is separate from instrumented profiles')
for i,d in enumerate([0,2,10]):
 ax=f.add_axes([.20+i*.26,.20,.23,.59]);vals=[next(x['median_ms']for x in rows if x['system']==n and x['delay_ms']==d)for n in names];ax.barh(range(8),vals,color=colors);ax.invert_yaxis();ax.set_title(f'+{d} ms',fontsize=17);ax.set_yticks(range(8));ax.set_yticklabels(names if i==0 else['']*8,fontsize=10);ax.set_xlim(0,max(vals)*1.23);ax.spines[['top','right']].set_visible(False);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True);ax.tick_params(axis='x',labelsize=10)
 for j,v in enumerate(vals):ax.text(v+max(vals)*.025,j,f'{v:.1f}',va='center',fontsize=9)
finish(f)

f=slide('Set-oriented Java through actual WeBridge','Original recording → original Zero JVM → synthesis → generated procedure → execution','Evidence: alignment/idiomatic/WEBRIDGE.md; webridge-independent-verification.json; generated SQL SHA256')
body=[]
for d in [0,2,10]:
 a=[x for x in rows if x['delay_ms']==d and x['system']in ['Java set-oriented SQL','WeBridge set-oriented SQL']];z=[x for x in D['reverse_order_rows']if x['delay_ms']==d];body.append([f'+{d} ms',*[f"{next(x['median_ms']for x in arr if x['system']==name):.2f}"for arr,name in [(a,'Java set-oriented SQL'),(a,'WeBridge set-oriented SQL'),(z,'Java set-oriented SQL'),(z,'WeBridge set-oriented SQL')]]])
table(f,['Delay','Direct, first','CALL, second','Direct, second','CALL, first'],body,bbox=(.055,.44,.89,.31),fontsize=15)
para(f,'Both paths make four command/response cycles. At 10 ms the ordering reverses when phase order is reversed. These measurements show no consistent WeBridge speedup for the already set-oriented query.',y=.33,size=18,width=100)
para(f,'All 20 original parameterized stored-procedure result gates pass. Both timing orders pass all 480 requests, with one CALL only in the optimized arm.',y=.15,size=14,width=125,dy=.038);finish(f)

f=slide('Experiment 2 — complete measured synchronization matrix','“Round trip” here means a serialized request followed by a complete database response.','Evidence: MySQL protocol-analysis.json (three postwarm requests per arm); PG flight-summary.json (six per variant)')
body=[]
for p in protocol:
 name=p['system'];inside={'Jac original':'35 separate reads','Jac SQL pushdown':'11 separate reads','Java full':'35 separate reads','WeBridge full':'35 inside one CALL','Java pruned':'28 separate reads','WeBridge pruned':'28 inside one CALL','Java set-oriented SQL':'1 aggregate SELECT','WeBridge set-oriented SQL':'1 aggregate inside CALL'}[name]
 body.append([name,str(p['command_response_cycles']),inside,'3',str(p['replicates'])])
table(f,['Configuration','Sync cycles','Business / runtime reads','Outer txn\ncommands','Replicates'],body,bbox=(.055,.18,.89,.62),fontsize=13,widths=[.32,.13,.30,.16,.10]);finish(f)

f=slide('Jac: which operations are combined, and which remain?','Exact warm PostgreSQL statement sequence; the original and final variants use the same walker.','Evidence: Jac roundtrip-profile/results/operation-map.json and sql-catalog.json; protocol + backend SQL logs')
body=[['Transaction start / setting / commit','3','3','Separate'],['Anchor hydration','7','5','Root, person, two friend batches, forum remain'],['Knows traversals','2','2','Outgoing and incoming remain separate'],['HasMember traversals','10','1','One batch over ten friends'],['Standalone type-ancestry probes','0','2','HasMember and Forum probes remain'],['ContainerOf + HasCreator','1 + 15','0','Combined into aggregate query below'],['Count / ordering / LIMIT SQL','0','1','Member-driven relational aggregate'],['Total SQL / synchronization cycles','38','14','All observed in each profile request']]
table(f,['Operation','Original','Final','Measured emitted form'],body,bbox=(.055,.18,.89,.62),fontsize=12,widths=[.31,.10,.10,.49]);finish(f)

f=slide('Jac: account for every removed and retained cycle','The observed reduction is exactly 38 → 14.','Evidence: operation-map.json; named prepared statement catalog; bound frontier counts and result command tags')
ax=f.add_axes([.07,.48,.86,.29]);ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
box(ax,.02,.25,.23,.50,'10 membership SELECTs\n→ 1 batch',size=17);box(ax,.385,.25,.23,.50,'16 traversal SELECTs\n→ 1 aggregate',size=17);box(ax,.75,.25,.23,.50,'7 hydrations\n→ 5 hydrations',size=17);arrow(ax,(.26,.5),(.37,.5));arrow(ax,(.63,.5),(.735,.5))
f.text(.07,.35,'38 − 9 − 15 − 2 + 2 type probes = 14',fontsize=25,color='#0891b2',weight='bold')
para(f,'The two Knows traversals remain separate. Five anchor-loading queries and both type probes remain separate. The single forum is hydrated before the fused count query in this measured sequence.',y=.24,size=17,width=105,dy=.045)
para(f,'WeBridge full/pruned moves their corresponding original queries into CALL; its executed category counts are on the next page.',y=.105,size=13,width=140,dy=.03);finish(f)

f=slide('WeBridge: exact business operations executed inside CALL','Direct table SELECTs and executed cursor materializations are matched to generated procedure SQL.','Evidence: webridge-operation-map.json; actual P_S child events, cursor IDs and generated declarations')
body=[['Hydration SELECTs','7','0','0'],['Knows traversals','2','2','part of aggregate'],['HasMember traversals','10','10','part of aggregate'],['ContainerOf traversals','1','1','part of aggregate'],['HasCreator traversals','15','15','part of aggregate'],['Set-oriented aggregate','0','0','1'],['Total business table operations','35','28','1'],['Outer transaction commands','3','3','3']]
table(f,['Operation','WeBridge full','WeBridge pruned','WeBridge set-oriented'],body,bbox=(.055,.19,.89,.61),fontsize=14,widths=[.37,.18,.18,.27]);finish(f)

f=slide('What each transformation achieves in this request','Compare the logical query boundary separately from the client/server boundary.','Evidence: SQL operation maps and actual command sequences for all eight configurations')
body=[['Jac vs WeBridge full','Membership 10→1; post/creator 16→1; hydration 7→5','Jac retains 14 client cycles; WeBridge full uses 4'],['Jac vs WeBridge pruned','Jac batches membership and fuses count/order/LIMIT; pruned CALL retains 28 traversal operations','Pruned removes all hydration; Jac retains 5 hydration + 2 type probes'],['Jac vs set-oriented Java / CALL','Both have database-side aggregation and top-20','Set-oriented SQL also includes friend and membership joins in its single query; Jac emits them separately']]
table(f,['Comparison','Jac relational combination','Queries / boundaries still separate'],body,bbox=(.055,.25,.89,.54),fontsize=13,widths=[.22,.39,.39])
para(f,'Within the measured capture region, WeBridge full/pruned captures every original business SELECT. START, SET and COMMIT remain outside. The set-oriented variant captures its one aggregate SELECT.',y=.16,size=14,width=125,dy=.038);finish(f)

f=slide('Protocol frames and return traffic are different from round trips','Actual MySQL frame decoding honors negotiated CLIENT_DEPRECATE_EOF.','Evidence: mysql-results/protocol-analysis.json; mysql-idiomatic-results/protocol-analysis.json; parser regression checks')
body=[]
for name in ['Java full','WeBridge full','Java pruned','WeBridge pruned','Java set-oriented SQL','WeBridge set-oriented SQL']:
 p=next(x for x in protocol if x['system']==name);body.append([name,str(p['command_response_cycles']),str(p['server_response_frames']),str(p['result_sets']),f"{p['server_response_wire_bytes']:,}"])
table(f,['MySQL configuration','Sync cycles','Response frames','Result sets','Response bytes'],body,bbox=(.055,.30,.89,.48),fontsize=14,widths=[.36,.15,.17,.15,.17])
para(f,'Every next command follows the prior complete response in the trace. One CALL can return many protocol frames and result sets. For PostgreSQL, each stable execution is one Bind/Describe/Execute/Sync → ReadyForQuery cycle; the next Bind follows Ready delivery.',y=.18,size=15,width=120,dy=.039)
para(f,'The PostgreSQL baseline uses 39 server socket chunks for 38 cycles; final uses 14 chunks for 14 cycles. Socket chunk count is recorded separately.',y=.08,size=12,width=145,dy=.03);finish(f)

f=slide('Inside the stored procedures: original work and generated work','Directly nested Performance Schema events for a complete observed CALL.','Evidence: webridge-operation-map.json · parent CALL timers include children; counts here use direct children only')
body=[['Business table SELECTs','25','24','1'],['Business cursor materializations','10','4','0'],['Result / parameter metadata SELECTs','11','5','1'],['Variable / control instrumentation events','2,447','1,510','12']]
table(f,['Observed event category','Full','Pruned','Set-oriented'],body,bbox=(.055,.39,.89,.36),fontsize=15,widths=[.49,.17,.17,.17])
para(f,'Business totals are 25+10=35 and 24+4=28. Cursor opens materialize original business queries. Result/parameter SELECTs and variable/control events are generated procedure work.',y=.28,size=17,width=105)
para(f,'Control-event totals are stored-program instrumentation counts. The set-oriented procedure executes its original aggregate plus one metadata SELECT and still requires four outer command/response cycles.',y=.13,size=15,width=120,dy=.04);finish(f)

f=slide('Evidence and reproduction','Both experiments have a complete eight-configuration result matrix.','PDF generated directly from verified JSON and the measured operation maps · build_pdf.py')
lines=[('Latency','eight-arm-verification.json: 24 main cells, 960 checked requests; 240 additional reverse-order requests.'),('SQL / protocol','PG operation-map + flight-summary: 12 measured requests; MySQL protocol analyses: 18 measured requests.'),('Actual WeBridge','Generated procedure SHA256, original capture/replay/synthesis/install receipts, all20 parameter gates.'),('Independent checks','verify_eight_arms.py; audit_operation_map.py; test_mysql_parser.py; Jac roundtrip-profile/analyze.py.'),('Raw evidence','Per-request timings, payload-free protocol metadata, complete SQL catalog, P_S events and cleanup receipts.')]
y=.75
for head,text in lines:
 f.text(.06,y,head,fontsize=17,weight='bold',color='#0891b2');para(f,text,x=.235,y=y,width=95,size=14,dy=.035);y-=.123
finish(f);pdf.close();print(R/'jac-webridge-measured-comparison.pdf')
