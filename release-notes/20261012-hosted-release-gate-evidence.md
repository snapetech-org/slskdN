---
category: changed
audience: operators
area: release-process
action: none
breaking: false
---
Maintainers can use a successful manual CI run to validate the exact main commit when local test execution is unavailable. The release helper checks the workflow, repository, branch, commit, and result before pushing the tag.
