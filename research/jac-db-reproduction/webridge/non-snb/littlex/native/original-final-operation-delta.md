# littleX original/final SQL delta

The removed bound UUID is the super-root. With JAC_LAZY_TXN unset, ad469 selects its eager default and final32 selects its lazy default. _resolve_roots uses an ID-only stub in the lazy branch; aset_user_root similarly defers the user-root read. The traces retain the eventual actor-root hydration and remove the super-root hydration. Feed/page additionally execute one transaction instead of two. These are SQL-count and source-branch observations; latency uses separate quiet measurements.

| Operation | ad469 commands | Final32 commands | Removed super-root hydration |
|---|---:|---:|---:|
| feed | 16 | 12 | 1 |
| feed_page | 16 | 12 | 1 |
| like | 11 | 10 | 1 |
| follow | 12 | 11 | 1 |
| create_tweet | 9 | 8 | 1 |

`original-final-operation-delta.json` retains exact UUID bindings, node-type evidence, source SHA256s and branch locations. The source log directories retain all three repetitions, including first-repetition cache/setup variation.

The table counts the graph transaction backend PID. Full/page reads also execute two guest-identity resolver queries on an auxiliary PID in the preserved early logs; current all-DB feed profiles observe 18/14 commands (16/12 graph + 2 identity). Input-dependent owner-root aliasing and the native five-second schema-memo guard are recorded separately in `java-alignment-ledger.json`.
