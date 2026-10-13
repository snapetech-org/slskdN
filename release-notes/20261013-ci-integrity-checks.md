---
category: security
audience: operators
area: ci-security
action: none
breaking: false
---
CI actions use immutable commit pins. Dependency scans fail on high or critical vulnerabilities, and Trivy blocks fixable high or critical findings. Required performance and load checks now fail visibly. Maintainers can retry selected publishers for an existing stable release using published assets, without rebuilding or repeating successful channels.
