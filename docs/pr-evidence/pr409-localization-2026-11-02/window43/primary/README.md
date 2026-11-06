# slskdN PR #409 W43 primary review

- PR state at start and finish: OPEN/DRAFT at 9071dcb9b4a96b476ecbaec9d5643236846ac2f8 / 25282a0cd8197815b3ffcbec9dbea8a03a5c8725; branch codex/slskdn-oidc-tooltip-localization-20261030.
- Scope: source ordinals 76–100, 25 source IDs, 275 non-Spanish cells across 11 locales.
- Dispositions: 219 accept-current, 21 propose-correction, 24 propose-refinement, 11 held.
- W42: reattested all 275 final cells and 48 applied readbacks at the current head; reattested 50 prior holds and 50 W41–W42 Spanish formal-lane cells. W43 Spanish boundary values are preserved separately without a verdict.
- All current and candidate placeholder/markup checks pass. Protected literal misses in current cells are recorded; all proposals preserve required literals.
- Caller references are pinned to exact current source files/lines and contexts.
- Source/runtime gap: W98 “seen in pod” is concatenated from three localized English fragments and podId. Hold all 11 targets pending complete result strings; see source-runtime-gaps.jsonl. W97’s terse AcoustID Raw label is interpreted through the raw hit-count caller.
- The task-named W40 bundle path is absent. Its historical primary packet verifies but is pinned to an earlier head and was not used as current evidence. W42’s W43 boundary was reattested to current source/caller/catalog pins; the full frozen pending queue could not be reproduced without the missing bundle.
- Native-speaker review remains outstanding. No repo/PR changes, tests, builds, CI, browser actions, releases, or tags were made.

Packet builder: build_primary_packet.py. The SHA256SUMS.txt manifest covers every packet file except itself.
