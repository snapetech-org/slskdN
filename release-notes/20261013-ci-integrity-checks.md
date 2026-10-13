---
category: security
audience: operators
area: ci-security
action: none
breaking: false
---
CI pins actions and fails on required tests, dependency scans, and fixable high/critical image findings. Benchmark CI runs one HashDb lookup and rejects empty reports. Tags are checked before shell use. Publisher recovery uses the current stable commit and requires credentials; Nix validates main before push. Docker stays tag-only. Windows SQLite fixtures close handles before cleanup.
