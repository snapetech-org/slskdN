# slskdN PR #409 revised Pod-help proposal review

Independent review of 12 full-sentence translations for:

`Enable {feature} in the server configuration to use Pod rooms and discover other Pods.`

PR #409 is OPEN/DRAFT at `490983c336d4958f11518c73268de2788c8858cb` / tree `01ca1bcdd5f74fd1adf6151dda441e8a77a811da`. Input packet checksums, the caller line at `src/web/src/components/Messaging/MessagingV2.jsx:1716`, all 12 locale blobs, remote branch head, and clean worktree were reattested.

Each sentence has exactly one `{feature}` placeholder. Replacing it with `<code dir="ltr">feature.Pods</code>` yields exactly one correctly cased `feature.Pods` token. I accepted 6 proposals and recommend refinements to 6; there are no holds. The six refinements preserve “other Pods”, Pod casing, and Pod-room plurality. Japanese and Korean do not morphologically mark plural number, which is natural for those languages.

This is a machine cross-review, not native-speaker approval. No repository files were modified; no tests, builds, CI, or browser actions were run.
