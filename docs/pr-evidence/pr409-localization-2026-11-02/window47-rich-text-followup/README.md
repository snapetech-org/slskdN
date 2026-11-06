# slskdN PR #409 W71 rich-text localization follow-up

Replaced the previously held split fragments with one source-bound sentence: `Security monitoring will begin automatically once peer activity is detected. Check connectivity in the {tab} tab.` The component uses `LocalizedRichText` and supplies the bold localized `Mesh` tab title as the `{tab}` React-node slot, allowing each locale to place the title naturally. This resolves the W71 source/caller boundary; the earlier twelve fragment translations remain untouched.

All 12 direct catalogs now contain the full sentence and preserve `{tab}` exactly once. Independent machine cross-review refined zh-Hans and zh-Hant spacing, German tab terminology, and Indonesian peer terminology; root aligned Spanish terminology to the existing source phrase. The full final set and hashes are in `root-adjudication-and-readback.json`.

This is machine-reviewed draft translation, not qualified native-speaker approval. The Agent VM has no accessible slskdN app rendering for exact-head browser review. No tests, builds, scans, CI, workflows, merges, releases, or tags were run for this follow-up.
