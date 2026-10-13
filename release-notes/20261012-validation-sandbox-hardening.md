---
category: security
audience: operators
area: ci-security
action: none
breaking: false
---

The trusted validation launcher pins sandbox mount sources through inherited file descriptors before masking host paths. Per-task diagnostic logs are capped at 16 MiB with a truncation marker, and workflow artifacts use unique run-attempt names.
