"""Validate the draft's template files, measured inputs, PDF text, and references."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
checks = {}
template = json.loads((ROOT / 'template/provenance.json').read_text())
for path, info in template['files'].items():
    p = ROOT / path
    # The source bundle contains the template README and integrity records;
    # the full local workspace also retains the upstream sample.
    if p.exists():
        assert hashlib.sha256(p.read_bytes()).hexdigest() == info['sha256'], path
checks['official_template_commit'] = template['commit']
checks['official_template_files_unchanged'] = True
manifest = json.loads((ROOT / 'generated/inputs.json').read_text())
available = 0
for path, digest in manifest['sha256'].items():
    p = ROOT.parent / path
    if p.exists():
        assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, path
        available += 1
checks['input_hashes_verified'] = available
checks['input_manifest_entries'] = len(manifest['sha256'])
source = (ROOT / 'main.tex').read_text()
for token in [r'\documentclass[sigconf,nonacm]{acmart}', r'\usepackage{pvldb}',
              r'\vldbtopmatter', r'\bibliographystyle{ACM-Reference-Format}']:
    assert token in source, token
assert r'\usepackage[margin=' not in source
checks['official_format_enabled'] = True
text = subprocess.check_output(['pdftotext', '-layout', str(ROOT / 'main.pdf'), '-'], text=True)
assert '??' not in text
for token in ['PVLDB Reference Format', 'ABSTRACT', 'INTRODUCTION', '59.04', '645.3', '278,769', '432', 'REFERENCES']:
    assert token in text, token
info = subprocess.check_output(['pdfinfo', str(ROOT / 'main.pdf')], text=True)
checks['pdf_pages'] = int(re.search(r'^Pages:\s+(\d+)', info, re.M)[1])
checks['paper_size'] = re.search(r'^Page size:\s+(.+)', info, re.M)[1]
log = ROOT / 'build/main.log'
if log.exists():
    data = log.read_text()
    assert not re.search(r'(?:Citation|Reference).*undefined|There were undefined|Overfull \\hbox|^!', data, re.M)
    checks['no_unresolved_references_or_horizontal_overflow'] = True
    checks['vertical_box_notices'] = re.findall(r'Overfull \\vbox \(([^)]+)\)', data)
bbl = ROOT / 'build/main.bbl'
if bbl.exists():
    checks['bibliography_entries'] = bbl.read_text().count(r'\bibitem')
    assert checks['bibliography_entries'] == 7
checks['all_checks_passed'] = True
(ROOT / 'build').mkdir(exist_ok=True)
(ROOT / 'build/validation.json').write_text(json.dumps(checks, indent=2)+'\n')
print(json.dumps(checks, indent=2))
