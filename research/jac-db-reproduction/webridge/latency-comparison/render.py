#!/usr/bin/env python3
"""Render the finalized, independently verified seven-arm comparison."""
import json,pathlib,statistics,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=pathlib.Path(__file__).resolve().parent
x=json.loads((R/'comparison.json').read_text());rows=x['rows'];names=list(dict.fromkeys(r['system']for r in rows));colors=['#94a3b8','#0891b2','#a8a29e','#2563eb','#d4b16a','#7c3aed','#059669']
fig,axes=plt.subplots(1,3,figsize=(14,5.9),sharey=True)
for ax,d in zip(axes,[0,2,10]):
 values=[next(r['median_ms']for r in rows if r['system']==n and r['delay_ms']==d)for n in names]
 bars=ax.barh(names,values,color=colors,height=.65)
 ax.invert_yaxis();ax.set_title(f'+{d} ms response delay',fontsize=13,pad=14);ax.set_xlabel('Median request execution (ms)');ax.spines[['top','right']].set_visible(False);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True);ax.set_xlim(0,max(values)*1.24)
 for b,v in zip(bars,values):ax.text(v+max(values)*.025,b.get_y()+b.get_height()/2,f'{v:.2f}',va='center',fontsize=9)
fig.suptitle('IC5: set-oriented SQL, graph pushdown and stored-procedure batching',fontsize=16,x=.04,ha='left',y=.98)
fig.text(.04,.055,'Fixed nonempty input · matched 460,984 anchors · 10 warmup + 30 measured requests per cell\nJac: PostgreSQL / HTTP server timer; Java: MySQL / JDBC request timer. All conditions use the same delay proxy.',fontsize=9,color='#475569')
fig.tight_layout(rect=[0,.13,1,.92]);fig.savefig(R/'comparison.pdf',bbox_inches='tight');fig.savefig(R/'comparison.png',dpi=180,bbox_inches='tight')
