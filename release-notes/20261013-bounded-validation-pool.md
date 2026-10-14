---
category: changed
audience: operators
area: validation
action: none
breaking: false
---
The source-bound release gate now runs up to three dependency-ready tasks at once. Web and backend test suites share a resource group so they do not starve the hosted runner by running together. Independent repository checks can still run alongside one active suite. Test selection, pass criteria, and per-task receipts stay unchanged.
