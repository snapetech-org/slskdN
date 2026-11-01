# Localization source inventory

`20261031-interface-copy-inventory.json` is the source ledger for 446
browser-interface, generated-report, fixed server-status, and notification
strings. Its untranslated targets account for 5,352 cells across the 12 agreed
locales. The 2026-11-01 v5 follow-up ledger adds five missing app-output keys
and 60 target cells, bringing the missing-key total to 451 IDs and 5,412
cells. It separately records the existing `Playback stopped.` key, whose 12
targets are still English-identical. The full follow-up therefore has 72
translation cells; the overall outstanding total is 5,424. Refreshed
source-reference counts including the five new keys are 10,262 references
across 5,644 unique source strings; two fixed transfer-cleanup success messages
are translated in all locales and do not add pending cells. This includes nine fixed
Quarantine Jury status/error messages and the Library Health scan failure.
Caller lines and file hashes make the source inventory reproducible. All listed
target values still fall back to English and need translation, semantic review,
and placeholder validation.

`20261031-ui-outbound-copy.json` is preserved as the historical 56-source
checkpoint from the first source pass. It is superseded by the current ledger
and should not be edited to represent later work. Its two notification-title
records remain part of the current pending count; the rest are represented by
the complete current browser-source inventory.

The current ledger covers fixed browser UI copy, generated report templates,
known mapped diagnostic messages, fixed Quarantine Jury statuses and errors,
the Library Health scan failure, and the two notification titles. The browser
surface audit maps stable API error codes, exact Content ID and mesh-sync
messages, the Quarantine Jury allowlist, and the fixed Library Health failure.
API values, user content, paths, provider labels, protocol values, and unknown
diagnostics remain data. Only allowlisted application-owned strings are
translated.

The current catalog/source coverage test is strict. It must verify complete
translated values and placeholder parity before this work can be considered
complete; a passing source-wiring check alone does not establish translation
coverage or semantic quality.


The v5 source-fix inventory is `20261101-v5-followup-inventory.json`. It records the two previously missing app outputs (equalizer and file-deletion errors) and three MessagingV2 action templates with opaque room/pod names; their 60 target translations remain pending. It separately records 12 English-identical targets for the existing `Playback stopped.` key, for 72 follow-up translation cells total. The two fixed Network sync errors and four PortForwarding validation strings already exist in every locale catalog.
