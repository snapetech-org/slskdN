# slskdN PR #409 primary semantic review — W46 reconstructed ranks 26–50

Reviewed 25 source IDs × 12 direct locales (300 cells) at exact OPEN/DRAFT PR head 31544a6ef15db2f8481dd76aa9c10844ec3164ba / tree fe94582c3e13f0f567fbfa6c3abac6e8558ba17d. Selection is a deterministic reconstruction from the stable-ID queue after excluding the W1–W45 evidence set. Ranks 26–50 correspond to the second 25 entries in the original reconstructed W1–W44 pending order; no historical source ordinal is claimed.

Primary dispositions: {'accept-current': 237, 'hold': 24, 'propose-correction': 39}. The 39 proposed corrections cover the web-security checkbox name, select-all Traditional Chinese action, ContentID search placeholders, software conflict terminology, departure-request JSON wording, peer rating labels, Korean audio-recording terminology, and the discovery-shelf expiry-day label.

Two context issues remain held across all 12 locales (24 cells total): `tracks,` is concatenated after a dynamic count without locale plural handling; `new` is shared by a standalone message separator and a count-bearing Wishlist badge. Both require caller-level localization before target cells can be accepted. Their exact references and recommended remediation are recorded in `source-runtime-gaps.jsonl`. Five source IDs have no exact production localization caller; those are explicitly listed in the caller context packet.

Placeholder, markup, and protected-literal checks pass for every proposed target. Protected literals `ContentID`, `JSON`, and `DHT` remain intact. This is static machine-assisted primary review; native-speaker approval and headed-browser review remain outstanding. No repository files were modified; no tests, builds, scans, or CI ran.
