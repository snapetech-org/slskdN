# UI localization roadmap

## Current support and verified scope

The React UI in `src/web/` has a browser-local interface-language selector and catalogs for twelve locales. Catalog values use English source strings as keys, fall back to English when a value is unavailable, and preserve user-provided content such as filenames, paths, usernames, room names, and protocol values. This change maps the covered app-owned error flows to stable source keys or localized fallback messages instead of displaying raw server prose; other API error paths still need review.

The current catalog has 4,863 source keys, of which 4,505 are used by the UI; the active UI coverage is 54,060 locale cells across twelve target languages. The catalog also retains 358 entries that are not referenced by current UI source. Arabic UI strings carry local language and direction metadata; this does not establish app-wide right-to-left layout support.

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

System > Experience Preferences offers a browser-local interface-language selector for twelve locales. The shipped Web UI localizes 4,505 source strings across browsing, search, chat, rooms, collections, player, wishlist, transfers, dashboard, and system screens, including app-owned statuses, messages, and accessibility labels. The catalog audit covered 54,060 active locale cells with no missing translations or placeholder mismatches. Media and user-provided content, paths, and raw API/protocol values remain unchanged. Arabic strings carry local language and direction metadata.

Selected regional formatting now applies to dates, numbers, byte sizes, and operational metrics. System metrics and network views use localized compact counts and decimal byte sizes; zero-byte values retain locale digits. Per-label language and direction helpers are shared with UI strings. Saving or resetting preferences refreshes open screens immediately; the current tab remains usable if browser storage is blocked, and another tab's changes are observed. Reset also clears the separately stored interface-language choice.

SongID and source-feed import validation responses use stable error codes, with recognized codes mapped to localized catalog messages. The client uses a localized generic message for unrecognized errors in mapped flows rather than displaying backend prose.

## Remaining work

The catalog translations were machine-generated and still need fluent-speaker review. Continue migrating any remaining app-owned API failures returned as prose, and route remaining error displays through stable codes or localized fallbacks. Review additional Arabic workflows at narrow and desktop widths before claiming app-wide right-to-left support. The VM review for this change covered Arabic at desktop and mobile widths on `/system/metrics` and `/downloads`; it does not cover every screen or establish full RTL support.
