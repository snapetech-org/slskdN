---
category: security
audience: operators
area: ci-security
action: none
breaking: false
---

Manual workflow runs from refs outside `main` now use GitHub-hosted runners.
The main CI workflow defaults to read-only token permissions and grants
publishing permissions only to the release job.
