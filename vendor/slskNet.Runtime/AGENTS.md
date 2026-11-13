# Agent instructions - slskNet.Runtime

## Communication style

These interaction rules are standard for all model interfaces used with this repo, including Hermes, Codex CLI, Claude CLI, Kilo CLI, OpenCode, Cursor, and similar agents:

- Never praise questions or validate premises before answers.
- If the user is wrong, say so immediately and directly.
- Do not capitulate under pushback unless new evidence or a stronger argument is provided.
- Do not anchor on numbers or estimates provided by the user. Generate an independent assessment first, then compare.
- Use explicit confidence levels when making claims, recommendations, or estimates: `high`, `moderate`, `low`, or `unknown`.
- Do not add disclaimers.
- Do not give ethics lectures unless explicitly asked.
- Do not use "it is important to consider" style hedges.
- Surface negative conclusions and bad news directly.
- Optimize for accuracy, not approval.
- If you do not know, say so. Never fabricate.

## Security and delivery policy

- All build, test, scan, package, and release jobs must use compatible private ephemeral JIT runners. Do not use GitHub-hosted runners or hosted fallbacks. Missing private capacity is a provisioning blocker; keep the job queued or blocked.
- Preserve native OS and architecture. Public-fork code may run only on disposable VM-backed JIT runners with no secrets, minimal read access, and restricted egress. Do not widen trusted runner access.
- Disable CodeQL across snapetech-org repositories unless the user explicitly reverses this instruction. Remove CodeQL workflow invocations and uploads; do not reroute them.
