---
category: security
audience: users, operators
area: security
action: none
breaking: false
---
HTTP Basic authorization no longer bypasses CSRF checks on state-changing API requests, so browser-sent credentials cannot authorize cross-origin actions.
