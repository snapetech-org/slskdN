---
category: changed
audience: operators
area: download-configuration
action: none
breaking: false
---
Download retry behavior now accepts `transfers.download.retry.partial` and matching CLI and environment settings. The existing `incomplete` configuration, CLI, and environment names remain accepted; `partial` takes precedence when both keys are provided.
