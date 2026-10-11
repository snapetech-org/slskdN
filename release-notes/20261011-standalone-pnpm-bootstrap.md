---
category: changed
audience: operators
area: release-pipeline
action: none
breaking: false
---
CI installs pnpm from its standalone release binary, avoiding dependence on runner npm install-script policy. This prevents setup failures before build, test, and dependency-scanning jobs can run.
