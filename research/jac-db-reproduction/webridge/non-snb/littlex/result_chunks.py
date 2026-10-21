#!/usr/bin/env python3
"""Lossless deterministic, bounded-size public chunks for full littleX JSONL responses."""
import pathlib,gzip,hashlib,json,argparse
FORMAT='littlex-jsonl-gzip-chunks-v1'
def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def lines(path):
 path=pathlib.Path(path)
 if path.suffix=='.gz':
  with gzip.open(path,'rb')as f:yield from f
 else:
  index=json.loads(path.read_text());assert index['format']==FORMAT;n=0;digest=hashlib.sha256()
  for part in index['parts']:
   p=path.parent/part['file'];assert sha(p)==part['sha256'];count=0
   with gzip.open(p,'rb')as f:
    for line in f:count+=1;n+=1;digest.update(line);yield line
   assert count==part['rows']
  assert n==index['rows']and digest.hexdigest()==index['uncompressed_sha256']
def export(source,directory,max_uncompressed=64*1024**2):
 source=pathlib.Path(source).resolve();directory=pathlib.Path(directory);directory.mkdir(parents=True,exist_ok=True);indexpath=directory/'index.json';source_sha=sha(source)
 if indexpath.exists():
  index=json.loads(indexpath.read_text());assert index['source_sha256']==source_sha;return indexpath
 parts=[];n=0;total=hashlib.sha256();rawbytes=0;writer=None;file=None;partrows=0;partbytes=0
 def close():
  nonlocal writer,file
  if writer is None:return
  writer.close();file.close();parts.append({'file':path.name,'bytes':path.stat().st_size,'sha256':sha(path),'rows':partrows,'uncompressed_bytes':partbytes,'first_plan_ordinal':n-partrows,'last_plan_ordinal':n-1});assert path.stat().st_size<95*1024**2;writer=None
 for line in lines(source):
  assert len(line)<=max_uncompressed,'One complete response exceeds configured chunk bound'
  if writer is None or partbytes+len(line)>max_uncompressed:
   close();path=directory/('part-%04d.jsonl.gz'%len(parts));assert not path.exists();file=path.open('xb');writer=gzip.GzipFile(filename='',fileobj=file,mode='wb',mtime=0);partrows=0;partbytes=0
  writer.write(line);partrows+=1;partbytes+=len(line);n+=1;rawbytes+=len(line);total.update(line)
 close();index={'format':FORMAT,'source':str(source),'source_bytes':source.stat().st_size,'source_sha256':source_sha,'rows':n,'uncompressed_bytes':rawbytes,'uncompressed_sha256':total.hexdigest(),'max_uncompressed_part_bytes':max_uncompressed,'parts':parts,'scope':'Every original JSONL byte and complete response retained in order; gzip metadata deterministic'};indexpath.write_text(json.dumps(index,indent=2)+'\n');return indexpath
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=pathlib.Path);p.add_argument('--out',required=True,type=pathlib.Path);a=p.parse_args();print(export(a.source,a.out))
