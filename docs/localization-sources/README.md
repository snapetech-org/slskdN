# Source-only localization checkpoint

`20261031-ui-outbound-copy.json` records 56 newly wired app-authored English
sources and their current caller/file fingerprints. The 12 catalogs are
unchanged: all 672 new target cells remain pending. This committed source
checkpoint is not a semantic or native-speaker signoff.
The existing strict catalog/source coverage test remains strict and will report
the new missing client values until translation generation and review finish.

The scope contains 40 UI/help/accessibility sources, eight app-authored mesh
rejection reasons, six copied-report headings and two background notification
titles. The report headings are localized separately from report body templates.
The latter, plus remaining API success/error, throw/return and log origins, still
need a source/caller inventory. The older 182-record server-candidate inventory
mixes exposed wording with internal diagnostics and must not be translated as a
single unclassified batch.

Background notification events have no browser locale or existing user-language
preference. `integrations.notification_language` is a separate default-English
configuration value. Supported IDs are `en`, `es`, `zh-Hans`, `hi`, `de`, `ja`,
`fr`, `pt-BR`, `ar`, `ko`, `zh-Hant`, `vi`, and `id`; unsupported values use
English. The formatter reads embedded copies of the same UI catalogs. Missing
title targets fall back to their English sources. Usernames, room names, bodies,
prefixes and protocol values remain data. Substitution scans the template once;
inserted user text is never interpreted as another placeholder. Arabic title
values get presentation isolates without changing the source data.

Non-ASCII Ntfy title headers use RFC 2047 UTF-8 encoding supported by
[the Ntfy title contract](https://docs.ntfy.sh/publish/#message-title). Decoded
title/prefix content is preserved; no notification is sent during these checks.

Existing source keys are reused for queue removal, transfer selection, listed
radio playback and the two mesh publication outcomes. Opaque provider/API/OS
errors, URLs, paths, commands and user-supplied message content are excluded.
Unknown diagnostics require source-bound classification before translation.
Same-source technical tokens versus valid native equivalents also need a
contextual language/direction disposition; no blanket equality rule is applied.

Count buttons use neutral count text rather than English one/other branches. Mesh
review results store stable reason IDs and opaque parameters; rendering and copy
resolve the current locale. Visible labels/popovers use per-source metadata and
bidi markup, while native attributes/dialogs isolate values only at their
presentation boundary. Ordinary helpers and stored values remain plain text.
