---
category: security
audience: operators
area: ci-security
action: none
breaking: false
---
The vendored runtime's Windows smoke workflow now runs on GitHub-hosted Windows runners. It runs unit, integration, and API suites sequentially to reduce SQLite and filesystem contention; the mesh integration fixture waits for its SQLite index schema before seeding. Target verification follows the repository's canonical snapetech-org owner.
