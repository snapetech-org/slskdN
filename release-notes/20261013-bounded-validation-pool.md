---
category: changed
audience: operators
area: validation
action: none
breaking: false
---
The source-bound release gate now runs up to three dependency-ready tasks at once. Backend test tasks that share outputs remain serialized, while independent checks and frontend work can overlap. Test selection, pass criteria, and per-task receipts stay unchanged.
