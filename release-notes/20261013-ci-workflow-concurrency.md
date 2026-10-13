---
category: changed
audience: operators
area: ci-workflows
action: none
breaking: false
---
Pull request checks cancel older runs when a newer commit arrives. Scheduled checks remain independent, and release builds keep their existing tag-only triggers.
