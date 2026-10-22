"""Build the English JacDB group-meeting deck and detailed discussion notes.

Requires matplotlib. Uses repository measurements and frozen paper-lib notes.
"""
import csv
import hashlib
import json
import os
from pathlib import Path
import statistics
import textwrap

os.environ.setdefault('MPLCONFIGDIR', '/tmp/jacdb-group-slides-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch

R = Path(__file__).resolve().parent
BASE = R.parent
H = BASE/'historical-overview'
W = BASE/'webridge/non-snb'
INK, MUTED, BLUE, TEAL = '#17243b', '#59677c', '#2563eb', '#087f75'
plt.rcParams.update({'font.family':'DejaVu Sans', 'pdf.fonttype':42})
sources = []
def record(p):
    sources.append({'path':os.path.relpath(p,R),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
for item in json.loads((H/'source-manifest.json').read_text())['files']:
    p=H/'sources'/item['path']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
record(H/'source-manifest.json')
burden={}
for x in csv.DictReader((H/'sources/benchmark/burden/viewer_counts.csv').open()):
    key=x['bench'],x['arm'];v=int(x['loc']),int(x['dbloc'])
    assert key not in burden or burden[key]==v
    burden[key]=v
ladder=[]
for tag in ['base','A','AB','ABC1','ABC','ABCD1','FULL','D4','FINAL','D5']:
    p=H/f'sources/session0904/ic5/build/gates/ic5_{tag}.json'
    rr=json.loads(p.read_text());assert len(rr)==20 and all(x['parity'] and not x['err'] for x in rr)
    ladder.append((tag,sum(x['stmts'] for x in rr)))
    record(p)
assert ladder[0][1]==278769 and ladder[-1][1]==432
record(H/'sources/benchmark/burden/viewer_counts.csv')
record(W/'results.csv');record(W/'METHODS.md');record(W/'COMPLETION.json')
latency=list(csv.DictReader((W/'results.csv').open()))
completion=json.loads((W/'COMPLETION.json').read_text())
assert len(latency)==648 and completion['status']=='PASS'
def cell(arm,delay):
    rr=[x for x in latency if x['case_id']=='littlex-feed-t20' and x['arm']==arm and x['delay_ms']==str(delay)]
    assert len(rr)==1
    return rr[0]
inventory=json.loads((R/'paper-inventory.json').read_text())
papers={}
for item in inventory:
    folder=R/'sources/papers'/item['id']
    assert hashlib.sha256((folder/'notes.md').read_bytes()).hexdigest()==item['notes_sha256']
    papers[item['id']]=json.loads((folder/'metadata.json').read_text())
    record(folder/'metadata.json');record(folder/'notes.md')

# Each entry extracts a mechanism, existing evidence and a concrete Jac question.
PRIOR = [
 ('urweb-2015','Typed persistence and atomic backend operations',
  'Source table declarations, typed embedded SQL and modules connect persistent rows with language types. Remote calls execute atomically; managed channel sends are released at commit, and serialization failures trigger rollback/retry.',
  '§§2.1–2.1.1, 3.1–3.2. §4 reports framework benchmarks, deployed applications and developer feedback. Developers explicitly specify SQL reads and writes.',
  'Jac question: which query, transaction and effect-management responsibilities should the language absorb? Ur/Web is the closest collected backend language/database co-design reference.'),
 ('links-2007','Tables, query values and mutation in one language',
  'A typed language spans browser, server and database. Mutable table handles are distinct from lists; a query view supports comprehensions, filters, ordering and take/drop that compile to SQL.',
  '§2 Database subsection; §4 query compilation. Worked applications and translation rules explain the design. Table mutation is integrated with the source language.',
  'Jac question: distinguish a persistent graph handle, a deferred query and a materialized result. Their types and execution boundaries affect both usability and optimization.'),
 ('linq-2006','Composable queries plus object/relational integration',
  'Standard query operators express traversal and filtering inside the host language. DLinq translates expression trees and object navigation into SQL, maps rows into objects and tracks updates.',
  'Complete one-page system overview, p. 706, especially DLinq. It establishes an architecture; follow-up work supplies detailed semantics and evaluation.',
  'Jac question: what work remains after query composition, mappings and change tracking are already provided? Compare specific programmer tasks against a capable ORM/query provider.'),
 ('practical-linq-2013','Composition needs a predictable compilation boundary',
  'Quotation retains query bodies; antiquotation composes predicates/functions. Normalization removes supported abstraction before SQL generation. A restricted typed fragment has a single-query guarantee.',
  '§2; §5.3 Proposition 4; §9 evaluation. The formal core covers flat final results and excludes recursion, sorting, grouping and aggregation; practical coverage is broader.',
  'Compiler background: define which Jac helpers retain query structure and which materialize results. Query-count guarantees require an explicit fragment; cost still needs separate evaluation.'),
 ('query-shredding-2014','Nested results without a query per parent',
  'Normalize a query returning nested multisets, shred it into flat SQL queries, retain indexing information and stitch the results back into nested values.',
  'Abstract, §1 and Fig. 1; mechanism in §§4–5; evaluation in §8. Query count depends on result/query structure rather than the number of parent records.',
  'Jac question: can nested graph-shaped results retain a convenient interface while compilation handles batching and reconstruction? Preserve duplicates and specify ordering.'),
 ('qbs-2013','Recover relational intent from application loops',
  'Synthesis produces loop invariants and postconditions in a theory of ordered relations; the resulting specifications translate into SQL for supported imperative fragments.',
  'Abstract and §1. The program-to-query problem includes joins, aggregates and output order. Existing library coverage introduces the mechanism.',
  'Jac question: which relational facts follow directly from typed graph operations, and which still require general program reasoning or synthesis? Test equivalent tasks and semantic edge cases.'),
 ('equivalent-sql-2016','Variable lineage and folds expose relational computation',
  'D-IR tracks equivalent expressions and variable definitions; F-IR represents cursor loops as folds. Relational rewrites replace a selected computation with SQL and remove redundant code.',
  '§§2–4, Fig. 6 and Appendix B. The maximum-score example preserves the initial accumulator on empty/all-negative input. Goals include fewer queries and less transferred data.',
  'Jac question: use a dependency representation across supported statements/abilities, then derive aggregation. Preserve initial state, multiplicity, ordering, exceptions and effects.'),
 ('froid-2017','Imperative scalar functions become relational regions',
  'UDF variables become columns; regions become relational expressions composed with APPLY. Inlining into the caller exposes the combined computation to the database optimizer.',
  '§§3–5. The evaluated implementation disables prototype cursor-loop support (§4.2.1). §8.3 Fig. 13 reports about 3,300 versus nearly 5 million logical reads for its total-price example.',
  'Jac question: can ability inputs/outputs become explicit region interfaces? Compare supported control flow and traversals. Froid and Equivalent SQL share composition and branching capabilities.'),
 ('compiling-plsql-away-2019','Loops can target recursive SQL',
  'Compile procedural functions into SQL subqueries; iteration becomes SQL-level recursion so the surrounding SQL query and function can execute together.',
  'Abstract and §1 of the 2019 arXiv version. The motivating problem is procedural/SQL context switching inside the database.',
  'Jac question: represent loop-carried state and termination explicitly when compiling cyclic traversal. Compare recursive SQL with retained application execution on the actual workload.'),
 ('batched-bindings-2008','Repeated calls become a batch of parameter bindings',
  'Rewrite repeated query/procedure invocations into a batched call and rewrite the callee to accept a set of input parameters instead of one parameter at a time.',
  'Abstract and first-page example. The target includes repeated query and stored-procedure/UDF calls; dependence and side-effect conditions determine legal rewrites.',
  'Jac question: batch a frontier of traversal inputs across ability invocations and correlate every result with its input. Repeated arrivals and duplicates require defined behavior.'),
 ('sloth-2014','Delay execution to discover larger batches',
  'Extended lazy evaluation exposes batching opportunities during execution, including across loops, branches and method boundaries, until a value is demanded.',
  'Abstract and introduction. The paper evaluates more than 100 benchmarks from two applications and reports up to 3× page-load reduction under its conditions.',
  'Jac question: compare static fusion with runtime deferral. Identify the exact demand that forces a query and whether a dependency can instead execute in the database.'),
 ('webridge-2024','Dependent access paths become stored procedures',
  'Record and replay hot paths using concolic execution, recover SQL control/data dependencies, synthesize procedures and intercept application database calls. Unseen paths use interactive execution.',
  '§§1, 3–6. §10 explains complementary optimizations within generated database work. Procedure synthesis and relational rewriting can both reduce communication.',
  'Jac question: can language semantics make cross-ability regions easier to identify and support? Compare matched workloads, generated work, fallback coverage and command counts.'),
 ('pyxis-2012','Choose where application code executes',
  'Profile the application/server loads and analyze dependencies to partition code between application and database servers, reducing control transfers and transferred data.',
  'Abstract and §1; evaluation uses TPC-C and TPC-W. The application/database placement decision incorporates resource load.',
  'Jac question: after proving a region movable, choose its placement. Deployment support and database load are part of the execution decision.'),
 ('cobra-2018','Choose among equivalent whole-program strategies',
  'A Region DAG retains equivalent imperative/relational alternatives. A cost-based search compares SQL joins, prefetch/local lookup and retained application computation.',
  '§§II–VI. Fig. 12: at one million orders/73,000 customers, join vs prefetch is 6,047 vs 3,467 seconds on the slow network; 16 vs 12 seconds on the fast network.',
  'Jac question: separate eligibility from profitability. Model round trips, row duplication/transfer, database execution, application work and available memory.'),
 ('eliom-2016','Reusable behavior across explicit execution locations',
  'OCaml annotations interleave client/server/shared code. Typed client fragments and cross-tier communication support components with behavior on both sides.',
  '§2 examples; §§3–5 type system, execution and compilation. Placement and communication are explicit language choices.',
  'Broader design lesson: modular source boundaries can span execution boundaries. For JacDB, test whether reusable query helpers/abilities remain analyzable when composed.'),
 ('hop-2006','Package related logic while exposing execution levels',
  'A two-level language packages application logic and GUI behavior together; function calls and event loops connect execution levels.',
  'Abstract; §§2–4 constructs and execution; §6 implementation. Database access is supplied through libraries.',
  'Broader design lesson: make execution boundaries understandable to programmers. A Jac query API should explain when construction becomes database interaction.'),
 ('scalaloci-2018','Placement types and generated communication',
  'Values are associated with peers using placement types. Architecture definitions and distributed reactive flows drive communication and data conversion.',
  '§2 mechanisms; §8 case studies and runtime measurements. Table 1 counts LOC, callbacks, imperative state updates and remote accesses.',
  'Evaluation lesson: measure specific responsibilities removed from source alongside runtime costs. Query execution and programmer effort need distinct evidence.'),
 ('multitier-modules-2019','Separate modularity from deployment topology',
  'Modules encapsulate cross-peer functionality over abstract peer types, allowing composition and distribution to vary independently.',
  'Abstract and §1; §5 case studies include algorithms, distributed data structures and Flink task distribution.',
  'Broader design lesson: changing query placement should preserve a useful module interface. Study which Jac ability summaries allow analysis across reusable modules.'),
 ('orleans-2014','Runtime responsibilities support a simpler object model',
  'Virtual actors let the runtime handle activation, location and distributed resource management while application code uses logical actor identities.',
  '§§2–3 programming/runtime model; §§4–5 applications and performance. This is the 2014 MSR technical report.',
  'Broader design lesson: identify each responsibility moved into the runtime and its consistency contract. Apply that accounting to Jac object loading, identity and query execution.'),
 ('kappa-2020','Compiler/runtime support absorbs infrastructure work',
  'Checkpointing handles serverless timeouts, while concurrency mechanisms support parallel computation and coordination from a programming framework.',
  'Abstract; §3 mechanisms; §5 evaluation; §6 programmer requirements. The abstraction comes with checkpoint/runtime constraints.',
  'Broader design lesson: simplicity has a runtime cost and an effect boundary. Evaluate programmer obligations and execution overhead together.'),
 ('interdisciplinary-pl-design-2018','Evaluate the programmer-facing claim directly',
  'Combine formal/performance methods with interviews, user experiments, case studies and iterative prototyping throughout language design.',
  'Fig. 1, Table 1 and §4. The paper describes complementary design/evaluation methods, including human-centered approaches.',
  'Jac evaluation: use representative query/modification tasks, comparable training and correctness tests. Measure completion, time, errors and required concepts alongside source metrics.'),
]
assert {x[0] for x in PRIOR}==set(papers), 'Every relevant paper-lib entry must be covered'
(R/'prior-work.json').write_text(json.dumps([dict(id=p[0],focus=p[1],mechanism=p[2],evidence=p[3],connection=p[4]) for p in PRIOR],indent=2)+'\n')

pdf=PdfPages(R/'jacdb-language-design-discussion.pdf')
pdf.infodict()['Title']='JacDB: Easier Queries, Efficient Execution — Group Discussion'
N=0;notes=[];layout_errors=[]
def page(title,section,subtitle='',source='',detail=''):
    global N
    N+=1;f=plt.figure(figsize=(16,9),facecolor='white')
    f.text(.055,.955,'JACDB  /  '+section.upper(),fontsize=10,color=TEAL,weight='bold')
    heading=f.text(.055,.882,title,fontsize=27,color=INK,weight='bold')
    f.canvas.draw()
    while heading.get_window_extent(f.canvas.get_renderer()).x1>f.bbox.width*.95:
        heading.set_fontsize(heading.get_fontsize()-.5)
    if subtitle:f.text(.055,.818,textwrap.fill(subtitle,126),fontsize=14,color=MUTED,va='top')
    f.text(.055,.032,textwrap.fill(source,163),fontsize=8,color=MUTED,va='bottom')
    f.text(.95,.035,str(N),ha='right',fontsize=10,color=MUTED)
    notes.append(f'## {N}. {title}\n\n{subtitle}\n\n{detail}\n\nSource: {source}\n')
    return f
def para(f,s,y=.70,size=21,width=91,color=INK):
    f.text(.06,y,textwrap.fill(s,width,break_long_words=False),fontsize=size,color=color,va='top',linespacing=1.4)
def bullets(f,items,y=.71,size=21,width=89,gap=.18):
    for i,s in enumerate(items):para(f,s,y-i*gap,size,width)
def table(f,heads,rr,widths=None,size=18,bbox=(.055,.23,.89,.50)):
    widths=widths or [1/len(heads)]*len(heads)
    limits=[max(12,int(1152*bbox[2]*w*.88/(size*.53))) for w in widths]
    wrap=lambda v,i:'\n'.join(textwrap.fill(line,limits[i],break_long_words=False) for line in str(v).split('\n'))
    ax=f.add_axes([0,0,1,1]);ax.axis('off')
    t=ax.table(cellText=[[wrap(x,i) for i,x in enumerate(row)] for row in rr],colLabels=[wrap(x,i) for i,x in enumerate(heads)],colWidths=widths,bbox=bbox,cellLoc='left',colLoc='left')
    t.auto_set_font_size(False);t.set_fontsize(size)
    for (r,c),v in t.get_celld().items():
        v.set_edgecolor('#dce4ed');v.set_linewidth(.6);v.set_facecolor('#e6eef9' if r==0 else '#f5f7fb' if r%2 else 'white')
        v.set_text_props(color=INK,weight='bold' if r==0 else 'normal')
def flow(f,labels,y=.37,caption=''):
    ax=f.add_axes([.055,y,.89,.23]);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    n=len(labels)
    for i,s in enumerate(labels):
        x=i/n+.015;w=1/n-.03
        ax.add_patch(FancyBboxPatch((x,.16),w,.69,boxstyle='round,pad=.009',edgecolor='#a9bed6',facecolor='#edf3fc'))
        ax.text(x+w/2,.505,s,fontsize=17,ha='center',va='center',color=INK)
        if i<n-1:ax.annotate('',xy=((i+1)/n+.003,.5),xytext=(x+w+.005,.5),arrowprops={'arrowstyle':'->','color':BLUE,'lw':1.6})
    if caption:para(f,caption,y-.045,17,112,MUTED)
def save(f):
    f.canvas.draw();renderer=f.canvas.get_renderer()
    for t in f.findobj(matplotlib.text.Text):
        if not t.get_visible() or not t.get_text():continue
        b=t.get_window_extent(renderer)
        if b.x0 < -2 or b.y0 < -2 or b.x1>f.bbox.width+2 or b.y1>f.bbox.height+2:
            layout_errors.append({'slide':N,'text':t.get_text(),'bounds':list(b.bounds)})
    pdf.savefig(f);plt.close(f)

f=page('JacDB: Easier Queries, Efficient Execution','Research problem',
 'Group discussion • language design + compiler/runtime support • October 2026',
 'Research framing: discussion with the project collaborators and user, 2026-10-21.',
 'The project goal is to simplify SQL-database querying for application programmers. The two linked research questions are expressiveness/usability and the execution cost of that programming model.')
para(f,'Let programmers express database queries in application terms, and let the language implementation organize efficient execution.',size=29,width=67)
flow(f,['Natural query\nexpression','Explicit language\nsemantics','Efficient database\nexecution'],y=.28)
save(f)

f=page('Two research questions, one programming model','Research problem',source='Proposed research decomposition.')
table(f,['Question','Desired outcome','Evidence'],[
 ['Q1: programming','Express traversal, filters and aggregation naturally','Query/modification tasks; errors; concepts; code'],
 ['Q2: execution','Derive efficient access from that expression','Generated SQL; DB calls; transferred data; timing'],
],widths=[.25,.36,.39],size=20,bbox=(.055,.29,.89,.42))
para(f,'The same program and workload should connect both evaluations.',y=.19,size=23)
save(f)

f=page('Make “comfortable to use” concrete','Research problem',source='Proposed criteria; Interdisciplinary PL Design, Fig. 1 / Table 1.')
bullets(f,['Express domain relationships without manually organizing per-object loads and joins.',
 'Reuse query logic across functions/abilities while preserving predictable execution boundaries.',
 'Modify a predicate, aggregate or result shape with understandable types, errors and performance behavior.'],gap=.19)
save(f)

f=page('Running example: find relevant active forums','Problem example',
 'IC5: given a person and date, find friends’ recently joined forums and rank their qualifying posts.',
 'Historical IC5 COMPILER_PLAN.md: query definition; benchmark/snb/jaseci-pg/app.jac.',
 'For each forum, count posts authored by friends whose membership in that forum satisfies the date predicate. Sort by descending count then forumId and return the top 20. Friend identity and forum identity must stay correlated.')
flow(f,['Person','Friends','Forums joined\nafter date','Posts by those\nqualifying friends'],y=.43)
para(f,'Keep the (forum, friend) correlation → count matching posts → order → take 20.',y=.29,size=23,width=89)
para(f,'An edge predicate, identity membership, aggregation and ranking all contribute to the answer.',y=.16,size=18,width=110,color=MUTED)
save(f)

f=page('Natural traversal leaves execution decisions open','Problem example',
 'Algorithm sketch adapted from the existing IC5 walker; illustrative pseudocode.',
 'Historical sources/session0904/ic5/COMPILER_PLAN.md, “The two plans”.')
code='for friend in friends(person):\n    for forum in joined_after(friend, date):\n        qualifying[forum].add(friend)\nfor forum in qualifying:\n    count posts whose author is in qualifying[forum]\nreturn top_20(forums, by=(-count, forum_id))'
f.text(.065,.72,code,fontfamily='DejaVu Sans Mono',fontsize=20,color=INK,va='top',linespacing=1.5)
para(f,'The implementation chooses when to fetch, batch, join, aggregate and materialize.',y=.20,size=21,width=100)
save(f)

f=page('Actual Jac source: count qualifying authors','Problem example',
 'Verbatim inner-loop excerpt from the historical IC5 walker; enclosing forum loop supplies fo and foj.',
 'sources/benchmark/snb/jaseci-pg/app.jac: ic5_new_forums, inner post loop.',
 'The field count is local; joined maps a forum identity to its qualifying friend identities. ContainerOf and HasCreator are explicit graph operations. A compiler must retain this correlation when replacing the loop with an aggregate.')
code='cnt = 0;\nfor post in [fo->:ContainerOf:->[?:Post]] {\n    creators = [post->:HasCreator:->[?:Person]];\n    if creators and jid(creators[0]) in joined[foj] {\n        cnt += 1;\n    }\n}'
f.text(.065,.72,code,fontfamily='DejaVu Sans Mono',fontsize=20,color=INK,va='top',linespacing=1.5)
para(f,'Question: can this remain the natural source while execution becomes a batched or relational aggregate?',y=.18,size=22,width=94)
save(f)

f=page('What must remain predictable?','Problem example',source='IC5 semantics; proposed JacDB semantic contract.')
table(f,['Source behavior','Compiler obligation'],[
 ['Same node reached twice','Preserve specified arrival / duplicate semantics'],
 ['Count and rank','Preserve grouping, empty results and tie-breaking'],
 ['Read, write, then read','Preserve visibility and transaction order'],
 ['Permission checks / exceptions','Preserve authorized results and observable behavior'],
],widths=[.39,.61],size=19)
save(f)

f=page('Prior work: language design already removes work','Solution / prior work',
 'Collected backend/query-language references; detailed paper profiles follow in the appendix.',
 'Ur/Web §§2–3; Links §§2,4; LINQ p.706; Practical LINQ §§2,5; Query Shredding §§4–5.')
table(f,['Work','Responsibility absorbed'],[
 ['Ur/Web','Typed persistence, encapsulation, transactions, retries, managed sends'],
 ['Links / LINQ','Integrated queries, typed data access and object/result integration'],
 ['Practical LINQ','Normalize composed query abstractions before SQL generation'],
 ['Query Shredding','Flatten nested queries and reconstruct nested results'],
],widths=[.29,.71],size=18)
save(f)

f=page('Prior work: several optimization paths overlap','Solution / prior work',source='Paper-lib: QBS, EE, Froid, PL/SQL Away, Batched Bindings, Sloth, WeBridge, Pyxis, COBRA.')
table(f,['Strategy','Collected references'],[
 ['Recover relational computation','QBS; Equivalent SQL; Froid; Compiling PL/SQL Away'],
 ['Batch repeated access','Batched Bindings; Sloth'],
 ['Move dependent work to the database','WeBridge; Pyxis'],
 ['Choose profitable alternatives','COBRA'],
],widths=[.46,.54],size=19)
para(f,'Jac’s research opportunity depends on its semantics, supported programs and measured programmer benefit.',y=.15,size=20,width=101)
save(f)

f=page('A language contract connects comfort to analysis','Solution / proposed design',source='Proposed JacDB design; references: Ur/Web, Links, Practical LINQ.')
table(f,['Programmer expresses','Language/compiler specifies'],[
 ['Typed nodes, edges and predicates','Persistent identity, relationships and field types'],
 ['Traversal and reusable abilities','Arrival order, state flow and effect summaries'],
 ['Aggregation and result construction','Bag/set/order semantics and materialization boundary'],
 ['Atomic application operations','Transaction visibility and permitted effects'],
],widths=[.46,.54],size=18)
save(f)

f=page('Build a dependency representation before SQL','Solution / proposed analysis',
 'Hypothesis: a shared representation can replace isolated recognizers for a defined fragment.',
 'Proposed design; related mechanisms: EE §§3–4; Froid §§3–5; WeBridge §§5–6.')
flow(f,['Jac source\n+ ability summaries','Dependencies\n+ effects','Equivalent\nexecution choices','SQL / batched\nJac execution'],y=.45)
bullets(f,['Track each value’s origin: parameter, node field, edge property, query or accumulator.',
 'Track control, ordering and mutation dependencies alongside data dependencies.'],y=.32,size=21,gap=.16)
save(f)

f=page('Across abilities, track how here changes','Solution / proposed analysis',
 'A traversal result supplies the arrival node for the next supported ability.',
 'Proposed analysis; existing Jac semantics supply traversal/ability structure.',
 'Illustrative decomposition: A starts at Person, visits friends; B receives each friend and visits qualifying forums; C processes the correlated forum/friend value. Summary construction must account for dispatch, walker state, queue ordering and repeated arrivals.')
flow(f,['Ability A\nhere = person','visit Knows\n→ friend arrivals','Ability B\nhere = friend','visit HasMember\n→ forum arrivals'],y=.43)
para(f,'Summaries carry arrival type, input lineage, walker-state reads/writes, emitted visits and effects.',y=.30,size=22,width=94)
para(f,'Question to test: does this expose larger safe query regions than analysis within each ability?',y=.15,size=20,width=102,color=BLUE)
save(f)

f=page('Eligibility and profitability are separate decisions','Solution / proposed analysis',source='EE §4.2; COBRA §§III–VI; Jac design questions.')
table(f,['1. Is transformation legal?','2. Which legal plan is cheaper?'],[
 ['Known query semantics and lineage','Estimate cardinalities and result width'],
 ['Preserved duplicates, ordering and state','Compare calls, transferred bytes and server work'],
 ['Sound effect / alias / permission treatment','Include application work and memory use'],
 ['Explicit boundary at unresolved behavior','Retain original execution as a candidate'],
],widths=[.5,.5],size=19)
save(f)

f=page('Cost-based choices can preserve the same interface','Solution / proposed execution',
 'The programmer’s query can have multiple equivalent implementations.',
 'COBRA §II, §§III–VI; proposed Jac application.')
flow(f,['Join + aggregate\nin SQL','Batch / prefetch\n+ local processing','Retain supported\nJac execution'],y=.43)
para(f,'Selection depends on fan-out, repeated values, network conditions, database load and materialized data size.',y=.30,size=22,width=93)
para(f,'Measure ranking accuracy and regressions when evaluating an automatic selector.',y=.15,size=20,width=105,color=BLUE)
save(f)

f=page('Apply the analysis to the same IC5 query','Solution example',
 'Recover the correlation and aggregate before choosing execution boundaries.',
 'Historical IC5 COMPILER_PLAN.md / REPORT.md; generalized dependency analysis is proposed.')
flow(f,['Friends +\nmembership date','(forum, friend)\nqualifying relation','Match posts\nby both IDs','Count / rank\n/ limit'],y=.45)
bullets(f,['Batch frontiers to remove per-post calls; project only needed fields.',
 'Recognize the correlated count and ranking; fetch selected forum fields.'],y=.31,size=21,gap=.16)
save(f)

f=page('Worked example: preserve correlation and zero counts','Solution example',
 'Teaching data, illustrating the required semantics; IDs are symbolic.',
 'Adapted IC5 example; new illustrative data, independent of measured fixtures.')
table(f,['Forum','Qualifying friends','Stored posts','Qualifying count'],[
 ['10','Ann','Ann: 2; Bob: 3','2'],['20','Ann, Bob','Ann: 1; Bob: 2','3'],
 ['30','Ann','None','0'],
],widths=[.13,.28,.36,.23],size=20,bbox=(.055,.32,.89,.38))
para(f,'Ranked result: (20, 3), (10, 2), (30, 0).',y=.23,size=24)
para(f,'Use the matching friend for each forum; preserve qualifying forums with zero matching posts.',y=.12,size=18,width=113,color=MUTED)
save(f)

f=page('Existing mechanisms and the next abstraction','Solution example',source='Historical IC5 REPORT.md / COMPILER_PLAN.md; current research proposal.')
table(f,['Established implementation','Proposed generalization'],[
 ['Typed lookup and graph predicates','An explicit supported query/traversal fragment'],
 ['Loop prefetch and batched adjacency','Shared dependency/effect representation'],
 ['Recognized nested-count lowering','Composable summaries across supported abilities'],
 ['Projection, ranking and hydration choices','Costed alternatives with explanatory diagnostics'],
],widths=[.5,.5],size=19)
save(f)

f=page('Existing evidence: database-related source lines','Data / historical colleague artifacts',
 'Each cell is total application LoC / database-related LoC under the historical classification.',
 'DBHarness 36f8b291; benchmark/burden/viewer_counts.csv; FORMAT_FAIRNESS.md.')
rr=[]
for b,label in [('snb','SNB'),('tpcc','TPC-C'),('littlex','littleX')]:
    rr.append([label,*[f'{burden[(b,a)][0]} / {burden[(b,a)][1]}' for a in ['jac','postgres','sqlalchemy']]])
table(f,['Application','Jac','PostgreSQL','SQLAlchemy'],rr,widths=[.25,.25,.25,.25],size=22,bbox=(.055,.32,.89,.38))
para(f,'These implementations use fewer DB-related lines in Jac. Task completion and modification effort need direct measurements.',y=.22,size=21,width=94)
save(f)

f=page('Existing evidence: unchanged IC5, fewer SQL statements','Data / historical colleague artifacts',
 '20 parameter rows; identical walker; every rung passes result parity.',
 'September 5 gates/ic5_*.json; SQL totals recomputed by this deck builder.')
ax=f.add_axes([.11,.30,.81,.43]);vals=[v for _,v in ladder]
ax.bar(range(len(vals)),vals,color=[BLUE]+['#9bbce9']*8+[TEAL]);ax.set_yscale('log')
ax.set_ylim(100,1500000);ax.set_xticks(range(len(vals)),[k for k,_ in ladder]);ax.set_ylabel('SQL statements over 20 requests')
ax.spines[['top','right']].set_visible(False)
for i,v in enumerate(vals):ax.text(i,v*1.2,f'{v:,}',ha='center',fontsize=12)
para(f,f'278,769 → 432 statements: {278769/432:.1f}× fewer, with unchanged application logic.',y=.18,size=23,width=100)
save(f)

f=page('New measurements: define DB call time precisely','Data / reproduced measurements',
 'Primary RTT = per-request sum of complete database command/response durations.',
 'webridge/non-snb/METHODS.md; RTT_MEASUREMENT_PLAN.md.')
flow(f,['Send command','DB execution\n+ communication','Receive complete\nresponse'],y=.45)
para(f,'Sum across all request-owned connections. The boundary includes server waits, communication, injected delay and compact-proxy overhead.',y=.32,size=21,width=97)
para(f,'Application work between calls is measured outside this interval. SQL command counts come from the same requests.',y=.16,size=20,width=102)
save(f)

f=page('littleX feed: all compared source forms','Data / reproduced measurements',
 '20 tweets/user • zero added delay • 30 measured requests/cell • median summed DB RTT.',
 'webridge/non-snb/results.csv: littlex-feed-t20, delay_ms=0; METHODS.md.',
 'Jac original is the pinned earlier runtime, which already contains loop-prefetch batching. Jac final uses final32. Full Java ports graph-access behavior; pruned Java removes Jac-specific access work; conventional Java directly uses set-oriented business SQL. Failure rows have compiler-stage evidence and no accepted timing.')
names=[('jac_original','Jac earlier runtime'),('jac_final','Jac optimized'),('java_full','Java graph-access full'),('webridge_full','WeBridge full'),('java_pruned','Java graph-access pruned'),('webridge_pruned','WeBridge pruned'),('java_conventional','Java conventional SQL'),('webridge_conventional','WeBridge conventional')]
rr=[]
for arm,label in names:
    x=cell(arm,0);ok=x['status']=='accepted'
    rr.append([label,f"{float(x['median_ms']):.3f}" if ok else 'Compiler failure',f"{float(x['mean_sql_commands_per_request']):.2f}" if ok else '—'])
table(f,['Implementation','DB RTT / request (ms)','Commands / request (mean)'],rr,widths=[.43,.28,.29],size=16,bbox=(.055,.21,.89,.55))
para(f,'Jac: PostgreSQL 18. Java/WeBridge: MySQL 5.7. Compare optimization ratios within each engine.',y=.13,size=16,width=124,color=MUTED)
save(f)

f=page('Network delay makes remaining calls consequential','Data / reproduced measurements',
 'Same littleX feed workload; medians of summed DB-call time in milliseconds.',
 'webridge/non-snb/results.csv: littlex-feed-t20, added response delays 0 / 2 / 10 ms.')
rr=[]
for arm,label in [names[0],names[1],names[6],names[7]]:
    rr.append([label,*[f"{float(cell(arm,d)['median_ms']):.3f}" for d in [0,2,10]]])
table(f,['Implementation','+0 ms','+2 ms','+10 ms'],rr,widths=[.43,.19,.19,.19],size=21,bbox=(.055,.30,.89,.42))
para(f,'Per-request command counts and returned data explain the work boundary; the full trace records every exchange.',y=.20,size=20,width=100)
save(f)

f=page('Interpret the measurements at their actual boundaries','Data / discussion',source='METHODS.md; COMPLETION.json; historical-overview/verification.json.')
bullets(f,['The historical IC5 ladder establishes a large reduction in generated SQL for unchanged code.',
 'The new RTT matrix shows workload-specific gains and remaining calls. Earlier Jac already has batching; runtime versions are pinned.',
 'Cross-engine absolute times describe complete measured implementations. Within-engine pairs isolate each optimization more directly.'],gap=.185,size=21)
save(f)

f=page('Evaluate the programming claim with real tasks','Data / proposed evaluation',
 'Use the same features, data and correctness oracle across Jac, SQL and an ORM/query interface.',
 'Proposed study; Interdisciplinary PL Design Fig.1/Table1; ScalaLoci §8.',
 'Counterbalance task order and provide comparable training. Separate author expertise and learning cost from language effects. Record failures and debugging steps, and manually inspect what concepts participants had to understand. Start with a reproducible expert case study, then use participants if making human performance claims.')
table(f,['Task','What to observe'],[
 ['Write IC5-like query','Correctness, time, joins/batching written, errors'],
 ['Change date filter / ranking','Concepts needed; files and semantic edits'],
 ['Return nested forum/post results','Manual reconstruction and extra calls'],
 ['Move logic into reusable abilities','Modularity, diagnostics and execution stability'],
],widths=[.45,.55],size=18)
save(f)

f=page('Evaluate the compiler claim on the same programs','Data / proposed evaluation',source='Proposed plan; EE / QBS / WeBridge / COBRA provide relevant baselines.')
table(f,['Dimension','Experiment'],[
 ['Correctness','Empty results, duplicates, cycles, ACLs, writes, exceptions'],
 ['Coverage','Inline vs helper vs cross-ability versions of the same query'],
 ['Performance','Calls, DB RTT, bytes/rows, server time, separate application time'],
 ['Profitability','Selectivity × fan-out × delay; compare all candidate plans'],
],widths=[.28,.72],size=19)
save(f)

f=page('Group decisions: define the contribution to test','Discussion / next steps',source='Proposed research questions, informed by the collected prior work.')
bullets(f,['Choose the programmer-facing contract: which graph queries, composition and materialization rules?',
 'Choose the core mechanism: dependency/effect summaries across supported traversal and ability boundaries.',
 'Choose a decisive experiment: keep natural source structure, expand optimization coverage, measure effort and execution together.'],gap=.185,size=22)
save(f)

MAIN=N
for key,focus,mechanism,evidence,connection in PRIOR:
    m=papers[key]
    venue=m.get('venue',str(m['year']))
    short={'urweb-2015':'Ur/Web','linq-2006':'LINQ','practical-linq-2013':'Practical LINQ',
           'qbs-2013':'QBS','froid-2017':'Froid','equivalent-sql-2016':'Equivalent SQL',
           'webridge-2024':'WeBridge','cobra-2018':'COBRA','scalaloci-2018':'ScalaLoci',
           'compiling-plsql-away-2019':'Compiling PL/SQL Away',
           'interdisciplinary-pl-design-2018':'PL design methods'}.get(key,key.rsplit('-',1)[0].replace('-',' ').title())
    f=page(f'{short}: {focus}','Prior-work appendix',
      textwrap.shorten(m['title'],width=133,placeholder='…'),
      f"{venue} | {m['url']}",
      f"Paper mechanism: {mechanism}\n\nEvidence: {evidence}\n\nConnection: {connection}\n\nFull title: {m['title']}\nVenue: {venue}\nLocal source: sources/papers/{key}/notes.md")
    # Keep the venue visible in a compact header, and the full title in notes.
    header=textwrap.shorten(venue,width=105,placeholder='…')
    f.text(.055,.985,header,fontsize=8,color=MUTED)
    para(f,'MECHANISM',y=.72,size=11,color=TEAL)
    para(f,mechanism,y=.675,size=20,width=100)
    para(f,'PAPER EVIDENCE',y=.47,size=11,color=TEAL)
    para(f,evidence,y=.425,size=18,width=112)
    para(f,'CONNECTION TO JAC',y=.255,size=11,color=TEAL)
    para(f,connection,y=.21,size=18,width=112)
    save(f)
pdf.close()
(R/'discussion-notes.md').write_text('# JacDB: Easier Queries, Efficient Execution\n\n'
 f'{MAIN} main discussion slides and {len(PRIOR)} paper profiles.\n\n'
 'Main flow: Research Problem → Problem Example → Solution → Solution Example → Data → Discussion.\n\n'
 'Evidence labels distinguish existing mechanisms, historical colleague data, reproduced measurements and proposed analysis/evaluation.\n\n'
 +'\n'.join(notes))
record(R/'paper-inventory.json')
(R/'sources.json').write_text(json.dumps({'paper_library':'/home/baichuan/paper-lib','paper_count':len(PRIOR),'files':sources},indent=2)+'\n')
(R/'verification.json').write_text(json.dumps({'status':'PASS' if not layout_errors else 'LAYOUT_REVIEW','main_slides':MAIN,'prior_work_profiles':len(PRIOR),'pages':N,'ic5_parity_rows_per_rung':20,'latency_cells':len(latency),'accepted_latency_cells':sum(x['status']=='accepted' for x in latency),'source_files_hashed':len(sources),'layout_bounds_errors':layout_errors},indent=2)+'\n')
print(f'Built {N} pages: {MAIN} main + {len(PRIOR)} prior-work profiles. Layout bounds: {len(layout_errors)} issues.')
