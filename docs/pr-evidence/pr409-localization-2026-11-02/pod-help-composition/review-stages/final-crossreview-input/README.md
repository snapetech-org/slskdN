# slskdN PR #409 final Pod-help translation cross-review input

Review the 12 final sentence targets in `final-targets.jsonl` independently against the exact pinned code caller and `LocalizedRichText` implementation. Source: `Enable {feature} in the server configuration to use Pod rooms and discover other Pods.`. The single `{feature}` slot composes into `<code dir="ltr">feature.Pods</code>` exactly once.

Live PR head/tree at freeze: `490983c336d4958f11518c73268de2788c8858cb` / `01ca1bcdd5f74fd1adf6151dda441e8a77a811da`. The caller currently concatenates the separate `Enable`, `<code>feature.Pods</code>`, and old fragment entries. Each new sentence must stand alone and preserve server configuration, plural Pod rooms, discovery of other Pods, placeholder count, and exact product-token casing. Check locale grammar, orthography, terminology, punctuation, and the rendered code-token boundary.

Prior machine cross-review suggested the final six refinements now present in this input; independently inspect all 12 again. No repository/PR writes, builds, tests, CI, browser actions, releases, tags, or merges. Do not claim native-speaker approval.
