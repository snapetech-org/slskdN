---
category: security
audience: operators
area: ci-security
action: none
breaking: false
---
Pull request validation now uses GitHub-hosted runners for every author. Persistent local runners are reserved for main-branch validation. Workflow tokens cannot approve pull requests, and the API-only load test stays loopback-only and offline.
