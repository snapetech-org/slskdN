# slskdN PR #409 Pod-help localization and caller composition

The former message combined three fragments around a hard-coded configuration token, which made several languages ungrammatical. The caller now uses one full translatable sentence with a single `{feature}` placeholder. `LocalizedRichText` renders `feature.Pods` once as `<code dir="ltr">feature.Pods</code>`. All twelve final sentence targets were accepted in the final independent machine cross-review.

The prior fragment and shared `Enable` translations remain in the catalogs unchanged; the new sentence is added as a new source key. All catalogs preserve their existing order and gain the same 6,170th key. Exact review stages, caller/catalog pins, apply plan, readbacks, and nested checksums are retained here.

No rendered browser result or native-speaker approval is claimed. No tests, builds, scans, CI, workflow changes, releases, tags, merges, or deployments were performed.
