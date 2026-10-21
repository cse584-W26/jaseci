"""Public, payload-free PG frame metadata export with streaming hashes."""
import argparse,gzip,hashlib,json,pathlib,sys
R=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent))
from measurement_lease import lease

def sha(path):
    h=hashlib.sha256()
    with path.open('rb')as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def export(directory):
    receipts=[]
    for path in sorted(pathlib.Path(directory).glob('delay-*ms/trace/events.jsonl')):
        target=path.with_name('events.jsonl.gz');receipt=path.with_name('events-export.json')
        if receipt.exists():
            old=json.loads(receipt.read_text());assert target.exists()and sha(target)==old['compressed_sha256'];receipts.append(old);continue
        assert not target.exists();h=hashlib.sha256();n=0
        with path.open('rb')as src,target.open('wb')as dst:
            with gzip.GzipFile(filename='',mode='wb',fileobj=dst,mtime=0,compresslevel=6)as z:
                for block in iter(lambda:src.read(1024*1024),b''):h.update(block);n+=len(block);z.write(block)
        check=hashlib.sha256();size=0
        with gzip.open(target,'rb')as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):check.update(block);size+=len(block)
        assert check.hexdigest()==h.hexdigest()and size==n
        out={'logical_source':'events.jsonl','public_payload':'events.jsonl.gz','uncompressed_bytes':n,'uncompressed_sha256':h.hexdigest(),'compressed_bytes':target.stat().st_size,'compressed_sha256':sha(target),'scope':'Exact payload-free frame and chunk event metadata; original private byte payload captures remain collection-local.'};receipt.write_text(json.dumps(out,indent=2)+'\n');receipts.append(out)
    return receipts
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--selection',type=pathlib.Path,default=R/'littlex-profile-selections.json');p.add_argument('--receipt',required=True,type=pathlib.Path);a=p.parse_args()
    with lease('native public protocol metadata export',a.receipt):
        for name in json.loads(a.selection.read_text()):print(name,len(export(R/name)),flush=True)
