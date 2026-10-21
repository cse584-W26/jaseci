#!/usr/bin/env python3
"""Create verified compressed state copies while preserving live verifier inputs."""
import gzip,hashlib,json,pathlib,time
H=pathlib.Path(__file__).resolve().parent;names={'warehouse','district','customer','stock','orders','new_order','order_line','history','raw-mutated-anchors'};records=[]
for source in sorted(H.rglob('*.jsonl')):
 if source.stem not in names or source.stat().st_size<1024*1024:continue
 target=source.with_suffix(source.suffix+'.gz');digest=hashlib.sha256()
 if not target.exists():
  with source.open('rb')as incoming,target.open('wb')as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,compresslevel=5,mtime=0)as packed:
   for block in iter(lambda:incoming.read(1024*1024),b''):digest.update(block);packed.write(block)
 else:
  with source.open('rb')as incoming:
   for block in iter(lambda:incoming.read(1024*1024),b''):digest.update(block)
 restored=hashlib.sha256()
 with gzip.open(target,'rb')as incoming:
  for block in iter(lambda:incoming.read(1024*1024),b''):restored.update(block)
 assert digest.hexdigest()==restored.hexdigest(),source
 records.append({'source':str(source.relative_to(H)),'compressed':str(target.relative_to(H)),'source_bytes':source.stat().st_size,'compressed_bytes':target.stat().st_size,'uncompressed_sha256':digest.hexdigest(),'compressed_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'decompression_verified':True})
(H/'public-state-compression.json').write_text(json.dumps({'generated_wall_ns':time.time_ns(),'files':records},indent=2));print(len(records),'verified state copies')
