# UI localization roadmap

## Current support and verified scope

The React UI in `src/web/` has a browser-local interface-language selector and catalogs for twelve locales. Catalog values use English source strings as keys, fall back to English when a value is unavailable, and preserve user-provided content such as filenames, paths, usernames, room names, and protocol values. The follow-up audit routes reviewed app-owned API-error displays through stable-code mappings where available and translated generic fallbacks otherwise. Fixed Content ID and mesh-sync errors returned by the server use exact catalog-key lookup; collection backfill notices use localized templates with structured success and failure counts instead of server prose. Quarantine Jury translates exact app-owned status/error strings and preserves unknown router details. Library Health translates its fixed scan failure and preserves unknown server error details. Arbitrary server, provider, and protocol diagnostics remain verbatim data.

The frozen source inputs at head `a13c513e5cd73703653b164f36c60fd3e50d0873` / tree `e6e4a4d563c202368e530b596ab37879479f4e85` contain 452 translation rows across twelve locales: 451 previously missing source keys plus the existing English-identical `Playback stopped.` value in each locale. All 5,424 target cells were filled and semantically reviewed: 1,741 accepted and 3,683 corrected, with none held. The source inventory counts 10,263 references across 5,644 unique source strings. See [`20261031-interface-copy-inventory.json`](localization-sources/20261031-interface-copy-inventory.json), the v5 follow-up inventory, and the hash-bound ledger at `/mnt/disks/scratch/task-worktrees/localization-20261030/slskdn-semantic-review-a13c513e-20261101/semantic-review-audit.jsonl` (SHA-256 `3133d80f9aac6acb5ac025d8a6caefbe5dc7877ae844bf68ff6bca165e0520dd`) for caller, target, and review evidence. Catalog parity and placeholder checks pass: all twelve locale files contain the same 6,169 keys and preserve placeholders. PR #409 remains draft; the 5,424 new/replaced values still require native-speaker review, and no native approval is claimed. Arabic UI strings carry local language and direction metadata; this does not establish app-wide right-to-left layout support.

## First-pass locale order

This is a practical rollout order, not a claim about these apps' actual user base. Product-level language analytics are not available. It combines global speaker estimates with online-content usage, and keeps the requested Arabic and Asian-language coverage in the first waves:

1. Spanish (es; es-MX where the product already distinguishes it)
2. Simplified Chinese (zh-Hans / zh-CN)
3. Hindi (hi)
4. German (de)
5. Japanese (ja)
6. French (fr)
7. Brazilian Portuguese (pt-BR)
8. Arabic (ar; requires right-to-left layout support)
9. Korean (ko)
10. Traditional Chinese (zh-Hant / zh-TW)
11. Vietnamese (vi)
12. Indonesian (id)

The World Bank's 2025 report estimates Mandarin Chinese, Hindi, and Spanish at 15%, 7.6%, and 6.9% of the global population respectively; its online-content data also places German, Chinese, and Japanese among the leading languages. [World Bank, Digital Progress and Trends Report 2025](https://documents1.worldbank.org/curated/en/099112525160536089/pdf/P505350-59c98ca8-0803-4f23-b470-17f3dab010ab.pdf). W3Techs tracks website content-language share rather than app users. [W3Techs content-language survey](https://w3techs.com/technologies/cross/content_language%20/ranking). Reorder this list if maintainers later receive reliable demand signals.

## Translation boundaries and acceptance

Translate interface labels, help, empty states, validation, notifications, and errors. Keep media titles, user names, filenames and paths, commands, API identifiers, protocol values, and other user-supplied content unchanged. Use the selected UI language for date, time, number, and plural formatting. Every locale must fall back to English for a missing key; CI should check placeholder parity and report missing strings. Arabic translated labels use local `lang` and `dir` metadata. App-wide RTL still requires logical layout properties and review of core workflows at narrow and desktop widths.

## Implemented in this PR

System > Experience Preferences offers a browser-local interface-language selector for twelve locales. The existing Web UI localization covers app-authored labels, statuses, messages, tooltips, and accessibility labels across browsing, search, chat, rooms, collections, player, wishlist, transfers, dashboard, and system screens. The current catalogs contain 6,169 keys in each locale. The 451 new keys and the twelve corrected `Playback stopped.` values are machine-assisted and semantically reviewed, but native-speaker review is still outstanding. Media and user-provided content, paths, and raw API/protocol values remain unchanged; fixed app-owned Content ID and mesh-sync errors use the catalog, and collection backfill notices use localized templates with structured success/failure counts. Arabic strings carry per-label language and direction metadata where translated, with English/LTR metadata when a source has no Arabic entry.

Selected regional formatting now applies to dates, numbers, byte sizes, and operational metrics, including transfer request timestamps. System metrics and Network views use localized compact counts, exact sequence IDs, relative times, and decimal byte sizes; zero-byte values retain locale digits. Stable mesh security warnings and backfill progress messages use translated templates with regionalized values. Per-label language and direction helpers are shared with UI strings. Saving or resetting preferences refreshes open screens immediately; the current tab remains usable if browser storage is blocked, and another tab's changes are observed. Reset also clears the separately stored interface-language choice.

The stable-code API error mapping covers five codes: three SongID validation/queue errors (`songid.source-required`, `songid.request-invalid`, and `songid.analysis-queue-failed`) and two source-feed import validation errors (`source-feed-import.source-text-required` and `source-feed-import.limit-must-be-positive`). Reviewed API-error displays use those translations when a known code is returned and a localized generic message for unknown or missing codes. Known Quarantine Jury service errors and statuses are translated only on exact matches; unknown router details and user evidence remain verbatim. The fixed Library Health scan failure is translated by exact match while other server error details remain verbatim. Fixed Content ID and mesh-sync errors use exact catalog keys; collection backfill notices derive from structured response counts and report successes and failures. Arbitrary persisted, provider, or protocol diagnostics remain verbatim data.

## Remaining work

The earlier English-identical review at source head `f8ec317d64623011b368f11f27571a6d40034bdf`, the 65-cell model-free follow-up, and the 38-cell French direction review remain historical evidence and do not certify native-speaker review. The 5,424 formerly missing/English-identical target cells are now filled and semantically reviewed as described above. Full semantic review of the previously populated 68,616 cells remains outstanding; earlier decision rows will be reused only when exact source and target hashes still match. Native-speaker review of the translated catalogs and headed-browser review of current workflows also remain outstanding. Earlier VM review covered Arabic at desktop and mobile widths on `/system/metrics` and `/downloads`, but does not establish app-wide right-to-left support; translated layouts still need review at narrow and desktop widths.
