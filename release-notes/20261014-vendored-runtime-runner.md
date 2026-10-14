---
category: security
audience: operators
area: ci-security
action: none
breaking: false
---
The vendored runtime's Windows smoke workflow now runs on GitHub-hosted Windows runners. The Windows smoke job runs its unit, integration, and API test suites sequentially to reduce SQLite and filesystem contention. Target verification now follows the repository's canonical snapetech-org owner.
