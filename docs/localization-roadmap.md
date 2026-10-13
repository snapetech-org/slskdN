# UI localization roadmap

## Existing support and verified gap

The shipped UI is React under `src/web/`; the app has no UI catalog or language preference. Historical uses of “localize” refer to filesystem paths, and the MilkDrop translator converts shader code. The ASP.NET localization assemblies under `publish/` are framework dependencies, not app translations.

There is a prior design task, T-1297, to localize the privacy UI (P3, medium), with proposed privacy keys in an archived design. A progress note also calls one older UI “internationalization ready,” but no runtime locale catalog or selector was added. Treat T-1297 as the first focused extraction slice, not as existing localization support.

## Implementation plan

1. Start with the privacy and security UI strings from T-1297, then extract the rest of `src/web/` in coherent screen-sized batches.
2. Extend the compact shell catalog with screen-sized batches and English per-key fallback. Add a full message framework when dynamic errors or plural rules make it useful, with key/placeholder checks; keep .NET API errors structured so each browser can render them in its selected language.
3. Add Display Language under the existing System > Experience preferences and persist it in this browser. Apply it immediately without changing service-wide culture or machine settings.
4. Format dates, counts, and durations from the selected locale. Keep filenames, paths, usernames, room names, protocol values, and API identifiers unchanged.
5. Add locales in the ranked order below. Arabic requires document `lang`/ `dir`, CSS logical properties, and RTL checks for privacy controls, transfers, chat, search, and dialogs.

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

System > Experience Preferences offers a browser-local interface-language selector for twelve locales. Primary navigation and its accessibility labels use translated strings with per-key English fallback. Arabic navigation labels receive local language and direction metadata; untranslated pages and the document remain English and left-to-right. Full screen-level translation and app-wide RTL layout review remain outstanding.

Selected regional formatting now applies to dates, numbers, byte sizes, and operational metrics. Saving or resetting preferences refreshes open screens immediately; the current tab remains usable if browser storage is blocked, and another tab's changes are observed. Reset also clears the separately stored interface-language choice.

## Remaining work

Translate the highest-use search, transfer, room, settings, and error workflows in screen-sized catalog batches. Keep API errors structured until they have stable client-side message keys, then translate them without changing service-wide culture. Verify complete Arabic layout in real workflows before claiming app-wide RTL support.
