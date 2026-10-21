# Jac for Database Programming: Historical Overview

[English PDF slides](jac-db-programming-historical-overview.pdf)

The 16-slide deck frames the research around making persistent graph applications
easier to write while the compiler/runtime organizes database execution. Its flow
is research problem, IC5 example, existing solution mechanisms, a corresponding
execution example, historical data, and research direction.

## Historical evidence

All numerical inputs come from the colleague's September 4–5, 2026 artifacts in
DBHarness revision `36f8b291fe24f35d9285869063e912edc0c14446`.
`source-manifest.json` records the copied source paths and SHA-256 values.
`data.json` contains the extracted inputs and recomputed IC5 summary.

- **Programming burden:** canonical formatted application copies, with total
  source lines and classified database-related lines. The source fairness notes
  document 88-column formatting, application-copy scope, and retained manual
  batching / `jtopk` helpers. Repeated CSV rows describe entity representations;
  the builder checks that each application/arm has one consistent set of counts.
- **IC5 ladder:** ten raw gate arrays, each with 20 parameter rows. SQL totals,
  arithmetic timing medians and output parity are recomputed. The ladder holds
  walker text fixed while compiler/runtime revisions change. Historical timing
  windows varied on a busy host. Raw gate medians take precedence over rounded
  headline prose. Baseline is `c12ba889d`; final D5 is `32c5d1dbb`.
- **SNB:** September 4 client-request p50 from the master CSV. This cohort uses
  the historical CONTROL/BEST configurations and predates the IC5 ladder.
- **TPC-C:** September 4 client-request p50 from the master CSV, with the original
  100 warmup / 800 measured schedule. New-Order timing includes expected rollbacks.
- **littleX W1:** September 4 application-server p50 from the master CSVs. Tier
  means tweets per user; users and follows per user remain 100 and 50.

The historical application timing boundaries include application execution and
database access. Each timing slide identifies its client/server boundary.
Programming-task and maintenance-cost measurements are proposed future evaluation.

## Rebuild

```bash
PYTHONDONTWRITEBYTECODE=1 python build_slides.py
```

Requires Python and Matplotlib. The builder checks every copied source hash,
asserts all 200 IC5 parity results, produces the PDF and extracted data, and writes
`verification.json` with the PDF hash. Slides use a white background, sans-serif
fonts, blue accents, and source references on every page.
