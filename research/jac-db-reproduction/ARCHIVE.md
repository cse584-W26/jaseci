# Committed reproduction archive

This directory archives the Jac DB reproduction report, profiling analysis,
measurement scripts, and the English VLDB-format paper (PDF and LaTeX).
Start with [REPORT.md](REPORT.md), [write-investigation/REPORT.md](write-investigation/REPORT.md),
and [paper/main.pdf](paper/main.pdf).

All 59 inputs listed in `paper/generated/inputs.json` are included at their
original relative paths. Run `make -C paper check` to build and validate the paper.
The manifest preserves the collection workspace location as provenance.

Collection took place in `/home/baichuan/jaseci/reproduction`; rerun scripts
retain that deployment's paths and service settings, described in README.md.
Database volumes, snapshots, installed runtimes, and the full diagnostic logs
remain in that local workspace. This archive includes the selected measured
inputs used to regenerate the paper's figures and tables.
