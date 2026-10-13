---
category: security
audience: operators
area: ci-security
action: none
breaking: false
---
Validation snapshots omit extensionless credentials and secrets while retaining source files with similar names. Every pull request uses GitHub-hosted runners; persistent runners serve trusted main validation. Linux CI verifies runner-owned temporary storage and rejects /tmp and /var/tmp. Workflow tokens cannot approve pull requests, and the API load test stays loopback-only and offline.
