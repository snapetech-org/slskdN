# slskdN PR #409 manual semantic review: fourth 25-key slice

The original scratch evidence bundle passed SHA-256 checks and its exact-head, source/catalog, formal-result, and prior-window overlap verifier before packaging. It is pinned to PR head `33a63077e88f0cc02210cfce7bc690640ef132d0` / tree `bfeb081505e87f9ef0b1b8f067cc90d2d1fa9c4d`. The source/catalog subtree matches the frozen snapshot at `4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb` / `0eb84397dc2b4be4afd730f6818203bd5910cf15`; `src` tree `fff1ef49df31a8d1095cd43148c186fbcd7f5089` is unchanged.

This disjoint slice covers 25 keys / 300 cells across all 12 direct locales. Outcomes are 262 keep, 26 high-confidence correction candidates, and 12 uncertain. “Playing” remains uncertain in all locales because the frozen source has no callsite or surrounding context and can refer to several activities. The per-locale verdicts and reviewed rows are in `manifest.json` and `review-decisions.jsonl`; exact frozen input rows are in `review-input.jsonl`.

The scratch manifest/input/decision hashes are `ea5d19ea1afe85ab17be9d559592e38868f3f5f690c9dc0ebc82fd9083c901e2`, `b1005dd04403787fbc7929dd1bb792fe601e5de462c31e830195c00ffdb70c72`, and `cbb9b148015764073c9c3c56fa4fdb0505dbb93238e275a2561431978d3ed143`. The PR README is this packaging/status copy; the original scratch README and verifier remain in the recorded scratch bundle. The verifier is omitted here because its sibling scan would count prior committed evidence copies as overlap. The manifest preserves the original scratch-file hashes and prior-window provenance.

This is machine-assisted semantic review, not native-speaker approval. No catalog corrections were applied.
