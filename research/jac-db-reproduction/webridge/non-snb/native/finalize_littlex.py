"""Bounded public response export and independent source-oracle check under host lease."""
import argparse,json,pathlib,subprocess,sys
R=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent))
from measurement_lease import lease
from jsonl_chunks import export
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--chunk-feeds',action='store_true');p.add_argument('--protocol',action='store_true');a=p.parse_args();O=R/a.input
with lease('native littleX offline export and independent verification',O/'offline-export-lease.json'):
    summary=json.loads((O/'summary.json').read_text());assert summary
    for cell in summary:
        if a.chunk_feeds and cell['workload']=='W1':
            directory=R/cell['path']
            if not(directory/'rows.chunks.json').exists():export(directory)
    subprocess.run([sys.executable,str(R/'verify_littlex.py'),'--input',str(O)],check=True)
    if a.protocol:
        assert all(c['instrumented']for c in summary)
        subprocess.run([sys.executable,str(R/'analyze_littlex_protocol.py'),'--input',a.input],check=True)
        selection=R/'littlex-profile-selections.json';data=json.loads(selection.read_text());assert a.input not in data;data.append(a.input);selection.write_text(json.dumps(data,indent=2)+'\n')
        subprocess.run([sys.executable,str(R/'littlex_cycle_evidence.py')],check=True)
        subprocess.run([sys.executable,str(R/'audit_littlex_scope.py')],check=True)
        from export_native_traces import export as export_traces
        export_traces(O)
    if not any(c['instrumented']for c in summary):
        selection=R/'latency-selections.json';data=json.loads(selection.read_text());key='references'if summary[0]['method']=='reference'else'littleX';item=a.input+'/summary.json';assert item not in data[key];data[key].append(item);selection.write_text(json.dumps(data,indent=2)+'\n')
    subprocess.run([sys.executable,str(R/'normalize_latency.py')],check=True)
    subprocess.run([sys.executable,str(R/'normalize_reference.py')],check=True)
