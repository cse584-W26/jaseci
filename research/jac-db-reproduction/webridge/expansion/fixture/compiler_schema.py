#!/usr/bin/env python3
"""Assemble original compiler input DDL from exact shared fixture definitions."""
import pathlib,re,json,hashlib
H=pathlib.Path(__file__).resolve().parent;B=H.parents[1];paths=[H/'mysql-schema.sql',B/'snb-extension/java/relations/prepare.sql',B/'snb-extension/java/relations/prepare-message.sql'];parts=[]
for p in paths:
 for x in re.findall(r'CREATE TABLE(?: IF NOT EXISTS)?\s+.*?;',p.read_text().replace('CHARACTER SET ascii COLLATE ascii_bin','CHARACTER SET utf8mb4 COLLATE utf8mb4_bin').replace('CHARACTER SET ascii','CHARACTER SET utf8mb4 COLLATE utf8mb4_bin'),flags=re.S|re.I):parts.append(x.replace('CREATE TABLE IF NOT EXISTS','CREATE TABLE'))
# Lookup metadata is part of full Java source behavior.
parts.append('CREATE TABLE identity_lookups(value_normalized VARCHAR(200) NOT NULL,user_id VARCHAR(200) NOT NULL,PRIMARY KEY(value_normalized));')
(H/'compiler-schema.sql').write_text('\n\n'.join(parts)+'\n');(H/'compiler-schema-sources.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},indent=2)+'\n')
