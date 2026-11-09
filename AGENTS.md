## Runner policy — current owner directive

All build, test, scan, package, and release jobs require compatible private
ephemeral JIT runners. Do not use GitHub-hosted runners or hosted fallbacks.
Preserve native operating system and architecture requirements. Missing private
capacity is a provisioning blocker; leave jobs queued rather than changing the
trust boundary or silently selecting a hosted runner.

Keep untrusted pull-request code in disposable VM-backed JIT environments with
no secrets, minimal read access, and restricted egress. Do not widen trusted
runner access. Preserve active builds and other agents' work, and do not restart
the broker while it owns guests. Before cleanup, retry, or dispatch, inspect the
branch, pull request, workflow revision, and side effects. Reruns use the old
workflow revision.

The shared pool inventory in the organization packer repository governs private
JIT jobs. Verify source routing, deployed broker policy, runner-group access, and
live capacity before relying on a new workflow revision.

CodeQL is disabled by owner directive. Do not restore or invoke CodeQL unless
the owner explicitly reverses that instruction.
