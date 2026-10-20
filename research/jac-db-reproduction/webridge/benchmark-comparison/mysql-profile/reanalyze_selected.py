"""Reanalyze only archived explicit profile selections, then independently verify them."""
import json
import pathlib
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parent
summary = json.loads((R / 'summary.json').read_text())
paths = sorted({cell['profile_path'] for cell in summary['cells']})
assert len(summary['cells']) == 33
for relative in paths:
    directory = (R / relative).resolve()
    assert directory.is_relative_to(R / 'results'), relative
    subprocess.run([sys.executable, str(R / 'analyze.py'), str(directory)], check=True)
# No selection refresh: archived filesystem modification times have no meaning.
subprocess.run([sys.executable, str(R.parent / 'verify_profiles.py')], check=True)
print(f'PASS: {len(paths)} explicitly selected captures; 33 measured arms')
