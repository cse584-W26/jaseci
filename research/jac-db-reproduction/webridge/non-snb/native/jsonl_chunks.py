"""Line-preserving bounded JSONL archive export and streaming verified reader."""
import argparse,gzip,hashlib,json,pathlib

def file_sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb')as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def rows_lines(directory):
    directory=pathlib.Path(directory);index=directory/'rows.chunks.json'
    if not index.exists():
        with gzip.open(directory/'rows.jsonl.gz','rb')as f:
            for line in f:yield line.decode()
        return
    meta=json.loads(index.read_text());total=hashlib.sha256();count=0
    for part in meta['parts']:
        p=directory/part['path'];assert file_sha(p)==part['compressed_sha256'];h=hashlib.sha256();size=0;n=0
        with gzip.open(p,'rb')as f:
            for line in f:h.update(line);total.update(line);size+=len(line);n+=1;count+=1;yield line.decode()
        assert(h.hexdigest(),size,n)==(part['uncompressed_sha256'],part['uncompressed_bytes'],part['rows'])
    assert total.hexdigest()==meta['uncompressed_sha256']and count==meta['rows']

def export(directory,limit=40*1024**2):
    directory=pathlib.Path(directory);source=directory/'rows.jsonl.gz';target=directory/'rows.chunks.json';assert source.exists()and not target.exists();parts=[];total=hashlib.sha256();n=0;buf=[];size=0
    def flush():
        nonlocal buf,size
        if not buf:return
        path=directory/'rows.parts'/('%05d.jsonl.gz'%len(parts));path.parent.mkdir(exist_ok=True);raw=b''.join(buf)
        with path.open('wb')as f:
            with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0,compresslevel=6)as z:z.write(raw)
        parts.append({'path':str(path.relative_to(directory)),'compressed_sha256':file_sha(path),'uncompressed_sha256':hashlib.sha256(raw).hexdigest(),'uncompressed_bytes':len(raw),'rows':len(buf)});buf=[];size=0
    with gzip.open(source,'rb')as f:
        for line in f:
            if size and size+len(line)>limit:flush()
            assert len(line)<=limit,'One response exceeds chunk bound; preserve line and choose a larger explicit bound'
            buf.append(line);size+=len(line);total.update(line);n+=1
    flush();meta={'source':'rows.jsonl.gz','source_compressed_sha256':file_sha(source),'source_compressed_bytes':source.stat().st_size,'uncompressed_sha256':total.hexdigest(),'rows':n,'target_uncompressed_limit':limit,'parts':parts};target.write_text(json.dumps(meta,indent=2)+'\n');assert sum(1 for _ in rows_lines(directory))==n;return meta
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=pathlib.Path);p.add_argument('--limit-mib',type=int,default=40);a=p.parse_args();m=export(a.directory,a.limit_mib*1024**2);print(len(m['parts']),'parts',m['rows'],'rows')
