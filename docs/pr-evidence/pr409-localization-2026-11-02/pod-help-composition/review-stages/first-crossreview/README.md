# slskdN PR #409 Pod-help composition cross-review

This read-only review evaluates all 12 proposed translations in the actual UI composition with the exact React node `<code dir="ltr">feature.Pods</code>`.

## Pin and evidence

PR #409 is OPEN/DRAFT at `490983c336d4958f11518c73268de2788c8858cb` / tree `01ca1bcdd5f74fd1adf6151dda441e8a77a811da`. The remote PR branch, API tree, exact-head task worktree, caller line, all 12 locale files, and `LocalizedRichText` implementation were reattested. Input packet checksums validate. The worktree is clean.

The caller currently concatenates localized “Enable”, the code element, and a localized fragment. `LocalizedRichText` accepts React nodes as placeholder values and preserves them as React children, so the full-sentence approach is supported. The caller needs to import `LocalizedRichText`; the inline code element should set `dir="ltr"` to preserve the exact configuration key in RTL text.

## Review

All 12 primary proposals were revised to express discovering other Pods as an action, instead of leaving “discovery” as an abstract feature name. This matches the pinned UI text about the Pod discovery index and discovered Pods. The packet records the prior candidate, independently recommended full sentence, rendered composition, placeholder/code checks, rationale, and exact locale file hashes for each locale.

The English source also has a design ambiguity: “Pod rooms and discovery” does not say what discovery refers to. Recommended clarification: `Enable {feature} in the server configuration to use Pod rooms and discover other Pods.`. This follows the pinned pod discovery-index context. Confirm that interpretation before application if product semantics differ.

No repository or PR files were changed; no tests, builds, CI, or browser actions were run. This machine cross-review is not native-speaker approval.
