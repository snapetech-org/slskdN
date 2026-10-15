# UI localization roadmap

## Current support and verified scope

The React UI in `src/web/` has a browser-local interface-language selector and catalogs for twelve locales. Catalog values use English source strings as keys, fall back to English when a value is unavailable, and preserve user-provided content such as filenames, paths, usernames, room names, and protocol values. The follow-up audit routes reviewed app-owned API-error displays through stable-code mappings where available and translated generic fallbacks otherwise; server-supplied prose remains outside the UI.

The current catalog has 5,691 source keys, each populated for twelve locales (68,292 locale values). The expanded source review also closed fixed-copy gaps across chat and messaging, player and visualizer controls, radio status, pod channels, discovery and SongID fallbacks, system integration placeholders, jobs, logs, MediaCore, network status, transfers, users, and wishlist actions. A source-reference test checks localized helper calls and component props against all twelve catalogs, preserves placeholder parity, and flags raw JSX prose. Arabic UI strings carry local language and direction metadata; this does not establish app-wide right-to-left layout support.

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

System > Experience Preferences offers a browser-local interface-language selector for twelve locales. The shipped Web UI localizes app-authored labels, statuses, messages, tooltips, and accessibility labels across browsing, search, chat, rooms, collections, player, wishlist, transfers, dashboard, and system screens. All twelve catalogs have the same 5,691 keys, non-empty values, and matching placeholders. Media and user-provided content, paths, and raw API/protocol values remain unchanged. Arabic strings carry per-label language and direction metadata where translated, with English/LTR metadata when a source has no Arabic entry.

Selected regional formatting now applies to dates, numbers, byte sizes, and operational metrics, including transfer request timestamps. System metrics and Network views use localized compact counts, exact sequence IDs, relative times, and decimal byte sizes; zero-byte values retain locale digits. Stable mesh security warnings and backfill progress messages use translated templates with regionalized values. Per-label language and direction helpers are shared with UI strings. Saving or resetting preferences refreshes open screens immediately; the current tab remains usable if browser storage is blocked, and another tab's changes are observed. Reset also clears the separately stored interface-language choice.

The stable-code API error mapping covers five codes: three SongID validation/queue errors (`songid.source-required`, `songid.request-invalid`, and `songid.analysis-queue-failed`) and two source-feed import validation errors (`source-feed-import.source-text-required` and `source-feed-import.limit-must-be-positive`). Reviewed API-error displays use those translations when a known code is returned and a localized generic message for unknown or missing codes. Known Quarantine Jury service errors are translated only when they exactly match an app-owned allowlist; arbitrary persisted or server-supplied error text is not shown.

## Remaining work

The catalog translations still need fluent-speaker review. A fresh Arabic visual review of Manual Import and additional Arabic workflows at narrow and desktop widths also remains before claiming app-wide right-to-left support. For future error cases, add stable API codes where the server contract supports them; otherwise keep server prose out of localized UI and use a translated fallback. The VM review for this change covered Arabic at desktop and mobile widths on `/system/metrics` and `/downloads`; it does not cover every screen or establish full RTL support.
