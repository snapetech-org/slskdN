---
category: security
audience: operators
area: ci-security
action: none
breaking: false
---
CI pins actions; gates tests, dependency/image scans, and bounded benchmark/load checks; empty HashDb reports fail. Tags are checked before shell use. Publisher recovery uses the current stable commit, existing assets, and credentials. Docker stays tag-only; Nix validates main before push. Windows SQLite fixtures close before cleanup. Vendored runtime Windows smoke uses hosted runners.
