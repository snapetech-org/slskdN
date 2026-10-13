---
category: fixed
audience: operators
area: share-index
action: none
breaking: false
---
Share database scans and maintenance release their SQLite readers before disposing file-backed connections, avoiding handles that can remain locked after a scan.
