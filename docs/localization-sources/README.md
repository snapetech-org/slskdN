# Localization source inventory

`20261031-interface-copy-inventory.json` is the current source ledger. It
records 434 missing browser-interface and generated-report sources, plus two
background notification titles, for 436 app-owned strings and 5,232 target
cells across the 12 agreed locales. Caller lines and file hashes make the
source inventory reproducible. At this checkpoint the source paths are wired,
but all listed target values still fall back to English and need translation,
semantic review, and placeholder validation.

`20261031-ui-outbound-copy.json` is preserved as the historical 56-source
checkpoint from the first source pass. It is superseded by the current ledger
and should not be edited to represent later work. Its two notification-title
records remain part of the current pending count; the rest are represented by
the complete current browser-source inventory.

The current ledger covers fixed browser UI copy, generated report templates,
known mapped diagnostic messages, and the two notification titles. API values,
user content, paths, provider labels, protocol values, and unknown diagnostics
remain data. Only allowlisted application-owned strings are translated.

The current catalog/source coverage test is strict. It must verify complete
translated values and placeholder parity before this work can be considered
complete; a passing source-wiring check alone does not establish translation
coverage or semantic quality.
