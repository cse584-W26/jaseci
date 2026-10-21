"""Retain the cleanup-rejected feed attempt as bounded, lossless public evidence."""
import pathlib,sys,json
R=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent))
from measurement_lease import lease
from jsonl_chunks import export,rows_lines
O=R/'littlex-reference-t200';cell=O/'delay-0ms/baseline/t200/W1-feed'
with lease('Lossless failed-reference raw export',O/'raw-export-lease.json'):
    export(cell)
    n=sum(1 for _ in rows_lines(cell));assert n==610,n
    (O/'raw-export-verification.json').write_text(json.dumps({'rows':n,'raw_stream_and_parts_hashes_verified':True,'acceptance_status':'excluded_cleanup_failure','public_artifact':str((cell/'rows.chunks.json').relative_to(R))},indent=2))
