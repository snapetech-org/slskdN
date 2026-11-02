# slskdN PR #409 W44 reconstructed primary review

Scope: a deterministic pending-source reconstruction for 25 source IDs x 12 locales = 300 cells.

Live PR #409 remained OPEN/DRAFT at head f3fbd3f8db10f78768b9951a67b4b9de8581a408 and tree 9495c35a540ef2d2e845c833acb709365e0e26ac. The worktree was clean before and after. Seven localization PR heads were freshly queried at start and finish; see exact-head.json.

Selection provenance: W43 retained evidence pins only source ordinals 76-100, and W42 future-boundary evidence pins W43 only. No explicit W44 boundary was found. The task-named W40 frozen bundle paths are absent, so a historical pending-queue ordinal cannot be reconstructed. This packet derives the current 6,170-key source inventory from all 12 identical ordered locale catalogs, computes source IDs from exact English source keys, excludes all 1,072 committed W1-W43 IDs, sorts pending IDs lexicographically, then selects ranks 1-25. The packet does not call these ranks source ordinals and does not invent 101-125.

The ledger includes 300 exact-hash cell decisions with source/current target/catalog hashes, caller pins or caller-gap findings, placeholders, markup, protected literals, and Spanish formality applicability. Dispositions: 245 accept-current, 15 propose-correction, 16 propose-refinement, and 24 hold. The 24 holds are the two source keys with no production localization caller: pods and Private Message from {username}.

W98 seen in pod is not part of this reconstructed slice. Its prior 11 non-Spanish holds were reattested at the current head and remain outstanding because the caller concatenates English fragments in a fixed order.

Spanish register: none of the selected English strings directly addresses the user, so formal/informal lane applicability is not applicable. No native-speaker approval or browser review is claimed.

Static review only. No repository or PR files were changed; no tests, builds, CI, browser work, releases, or tags were run.

Files:
- review-decisions.jsonl: exact-hash decisions for all 300 cells.
- candidate-proposals.jsonl: 31 exact replacements.
- pending-source-selection.jsonl: the 25 ranked current pending source IDs.
- source-inventory.jsonl and prior-source-ids.jsonl: complete 6,170-key and W1-W43 ID exclusion evidence.
- w98-holds-reattestation.jsonl: prior W98 holds, kept separate from this slice.
- SHA256SUMS.txt: checksums for every packet file except the manifest itself.
