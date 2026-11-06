# slskdN PR #409 W54/W57 runtime follow-up

The W54 room-connection errors are fixed at their display boundary: both compact and full `PodListenAlongPanel` paths now render the fixed hook messages with `LocalizedText`. The hook continues to store plain strings, so `useListeningPartyBroadcast` keeps its existing `includes` checks unchanged. The six message keys are populated in all 12 locale catalogs.

The W57 contacts failure output is fixed at both display sites. `getApiErrorMessageOutput` returns a branded output object, and the warning and empty-state paragraphs now render it with `LocalizedOutputText`, including the localized “Failed to load contacts.” fallback.

The independent static source review passed with no blockers. Catalog readback records all seven keys in every target locale. W71 remains held pending a single rich-text sentence with a tab-label slot. Qualified native-speaker approval remains outstanding. Exact-head browser review could not run against the application: the Agent VM showed a setup page for Seerr and a refused connection for another app, with no slskdN rendering available. No tests, builds, scans, CI, workflows, merges, releases, or tags were run for this follow-up.
