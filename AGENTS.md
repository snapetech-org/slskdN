## Runner policy — current owner directive

Use compatible GitHub-hosted public runners or private ephemeral JIT runners
for build, test, scan, package, and release jobs. Prefer GitHub-hosted runners
for trusted `main` validation and release publication when the workflow offers
that route; do not leave work waiting on private JIT capacity when a hosted
runner is available. Preserve the target operating system and architecture.

Keep untrusted pull-request code isolated, without secrets, and with minimal
permissions. Public GitHub-hosted runners are disposable; private JIT remains
available for workflows that require it. Do not widen trusted runner access.
Preserve active builds and other agents' work, and do not restart the broker
while it owns guests. Before cleanup, retry, or dispatch, inspect the branch,
pull request, workflow revision, and side effects. Reruns use the old workflow
revision.

The shared pool inventory in the organization packer repository governs private
JIT jobs only. Verify source routing, deployed broker policy, runner-group
access, and live capacity before relying on a private JIT workflow revision.

CodeQL is disabled by owner directive. Do not restore or invoke CodeQL unless
the owner explicitly reverses that instruction.
