#!/usr/bin/env python3
"""Record credential-pattern review without exposing matching values."""
import pathlib,json,re,hashlib
H=pathlib.Path(__file__).resolve().parent;manifest=json.loads((H/'PUBLIC_FILES.json').read_text());patterns={'JWT_shape':re.compile(rb'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'),'authorization_bearer':re.compile(rb'Authorization\s*:\s*Bearer\s+\S+',re.I),'named_credential':re.compile(rb'(?:svc_token|guestpassword)\s*[=:]\s*[\"\x27]?[^\s\"\x27,}]{8,}',re.I)};findings=[];scanned=0
for row in manifest['included']:
 p=H/row['path']
 if p.suffix in['.class','.gz']or p.stat().st_size>16*1024*1024:continue
 data=p.read_bytes();scanned+=1
 hits={k:len(v.findall(data))for k,v in patterns.items()if v.search(data)}
 if hits:findings.append({'path':row['path'],'sha256':hashlib.sha256(data).hexdigest(),'pattern_counts':hits})
(H/'public-credential-review.json').write_text(json.dumps({'status':'PASS: no credential-shaped values found'if not findings else'REVIEW_REQUIRED','files_scanned':scanned,'findings_without_values':findings,'exclusions':'Private graph-context and authentication/identity TSVs excluded by allowlist; compressed business state is owned synthetic fixture data','scope':'Pattern review of public text evidence, no matching values printed'},indent=2));print(scanned,'public text files;',len(findings),'credential-pattern findings (values omitted)')
