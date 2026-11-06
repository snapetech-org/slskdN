# slskdN PR #409 manual semantic review: 25 keys

Pinned to head 4c2b2e47d60c3e7d0917af5f7711f5d837f73ecb and tree 0eb84397dc2b4be4afd730f6818203bd5910cf15. The live pull request was OPEN and draft. This evidence-only slice covers 25 source IDs across all 12 direct locales (300 cells). Every selected cell was pending in the exact-head frozen review input, and none overlapped an existing result.

Review used the frozen source text, source callsites, and surrounding contexts; it was independent of the occupied shared Qwen model. Verdicts: 267 keep, 33 correct. Corrections are limited to clear semantic issues: Pod entity mistranslations in Arabic/Vietnamese, theme-label meaning for Light, Arabic None meaning “nobody”, Share List imperatives used as an entity type, and Transports Up mistranslating the availability metric as direction. Suggested targets and per-cell reasons are in review-decisions.jsonl.

The Transports Up source is in src/web/src/components/System/Security/AdversarialSettings.jsx; its value is AvailableTransports/TotalTransports, so the label means available transports. Light comes from src/web/src/components/ThemeMenu.jsx; Share List is used as the ShareList entity type in src/web/src/components/Collections/Collections.jsx.

All other values in this slice were kept because they preserve the source meaning and any named placeholders in the pinned context. This is an AI review with moderate overall confidence. Native-speaker review remains required. No catalog, source, or PR changes were applied.

Verification passed in the original task-scoped bundle: 300 cells, 25 keys, 12 locales; exact source rows, pending status, no prior-result overlap, placeholder integrity, snapshot head/tree, and all checksums matched. The original verifier is retained in task scratch alongside the source/result snapshot.
