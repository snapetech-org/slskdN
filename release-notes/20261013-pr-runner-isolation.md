---
category: security
audience: operators
area: ci-security
action: none
breaking: false
---
Validation snapshots omit extensionless authentication, token, credential, and secret files while retaining source code with those names. Pull request validation now uses GitHub-hosted runners for every author. Persistent local runners are reserved for main-branch validation. Workflow tokens cannot approve pull requests, and the API-only load test stays loopback-only and offline.
