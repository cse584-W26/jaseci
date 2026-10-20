"""Package the editable VLDB manuscript and pre-generated assets for LaTeX/Overleaf."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
names = ['main.tex', 'references.bib', 'acmart.cls', 'pvldb.sty',
         'ACM-Reference-Format.bst', 'Makefile', 'README.md', 'DRAFT_NOTES.md',
         'prepare.py', 'validate.py', 'bundle.py', 'template/provenance.json',
         'template/README.upstream.md']
names += [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'generated').glob('*.tex'))]
names += ['generated/inputs.json']
names += [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'figures').glob('*.pdf'))]
out = ROOT / 'jac-db-vldb-source.zip'
with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for name in names:
        archive.write(ROOT / name, arcname=name)
print(f'Wrote {out.name}: {len(names)} source/asset files.')
