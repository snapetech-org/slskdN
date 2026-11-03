## Runner policy — owner directive, 2026-11-03

GitHub-hosted runner minutes are available again. Use compatible GitHub-hosted
runners for build, test, scan, packaging and release jobs when their operating
system and architecture requirements are met. Preserve native OS and
architecture. Use private ephemeral JIT runners when a job needs private
network access, special hardware or storage, or explicit JIT validation. Do not
require private JIT solely because of the former organization-wide policy, and
do not treat missing private capacity as a blocker when a compatible hosted
runner is available.

Keep untrusted pull-request code isolated in a disposable environment without
secrets, with minimal permissions and restricted egress. Do not widen trusted
runner-group access to make untrusted code run. Preserve active builds and other
agents' work. Do not restart the broker while it owns running guests. Select a
runner route that fits the workload and trust requirements; rerunning an old
run uses its original workflow revision.

The shared inventory continues to govern private JIT jobs. For a private route,
verify source routing, broker policy, runner-group access and live capacity
before relying on it.

