# Jac DB paper draft — VLDB/PVLDB format

- Read: [main.pdf](main.pdf)
- Edit: [main.tex](main.tex)
- References: [references.bib](references.bib)
- Shareable LaTeX bundle: `jac-db-vldb-source.zip`

The English draft covers the implemented read optimizations, the reproduced
IC5 source A/B, SNB/TPC-C/littleX results, and the detailed repeated-write
investigation. Cross-ability dependency analysis appears as a next compiler
direction, separately from the implemented mechanisms.

## Official template

This draft uses `\documentclass[sigconf,nonacm]{acmart}` plus the official
`pvldb.sty`, `\vldbtopmatter`, and `ACM-Reference-Format.bst` from the
[VLDB Proceedings template](https://github.com/vldbproceedings/VLDB-Template),
as linked by the [VLDB 2027 formatting guidelines](https://www.vldb.org/2027/formatting-guidelines.html).

The upstream revision is `39c95f5c6fcbe652a83be24e4eff8f2134cd3fbc`.
[template/provenance.json](template/provenance.json) records download URLs and
SHA256 hashes. The downloaded class/style/bibliography files remain unchanged.
The upstream sample and README are retained in `template/`.

Author information, DOI, and publication page numbers are draft placeholders.
The artifact URL is empty. The manuscript includes a local reproduction map.

## Build

With a standard TeX Live installation:

```sh
make pdf
```

Generated tables and PDF figures are included, so LaTeX compilation also works
after extracting the source bundle or uploading it to Overleaf. Set `main.tex`
as the main document.

Within the full reproduction workspace, regenerate tables and figures from
the measured artifacts using Python 3 with Matplotlib and NumPy:

```sh
make regenerate
make check
make bundle
```

`prepare.py` reads existing artifacts only; it starts no services and issues no
database requests. Tables use conventional sample medians, while diagnostic
spans use means. The repeated-write table takes the median of the three
per-cohort medians. All 59 numerical/source inputs have hashes in
[generated/inputs.json](generated/inputs.json).

The generated asset set distinguishes client and server timing, the separate
20-input SQL census and 40/60-request IC5 latency windows, the two littleX
configuration/fixture groups, and uninstrumented versus diagnostic writes.

## Files for revision

`main.tex` contains the manuscript. `generated/*.tex` and `figures/*.pdf` are
derived assets. `references.bib` contains seven primary-source references.
`validate.py` checks template integrity, input hashes, resolved references,
and PDF structure. `build/` contains compilation logs and local previews.

Research priorities for the next revision are in [DRAFT_NOTES.md](DRAFT_NOTES.md).
