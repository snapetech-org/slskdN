# slskdN PR #409 locale startup and Chinese script correction

## Findings and change

This exact-head static follow-up addresses both findings in the W64 code review:

- SLC-001 (P2): src/web/src/index.jsx previously mounted React immediately after starting the asynchronous preferred-locale load. It now waits for applyInitialInterfaceLanguage() to finish before createRoot, so a saved or browser-preferred catalog is active before the first app render. Catalog-load failures retain the existing English fallback; unexpected initialization rejection also reaches the English-first app instead of leaving the root unmounted.
- SLC-002 (P3): browserLanguage() now checks explicit Hans/Hant script subtags before inferring Chinese from territory. Expected mapping: zh-Hans-TW -> zh-Hans, zh-Hant-CN -> zh-Hant, zh-TW -> zh-Hant, and zh-CN -> zh-Hans.

The change preserves the native localization system, English source fallback, and catalog key order. The UI does not mount while the initial catalog request is pending, so first visible content may be delayed by the catalog fetch. If loading fails, the existing English fallback remains available.

## Pins and verification

- PR #409 pre-change head/tree: 35977fdf9f07c52ba7becf793c9f7de7381c4e34 / 97749fb317a2704cdb5940ad2bb0a2ed008bfebe.
- Live PR, branch, and pull refs were re-attested before editing.
- Source blob IDs, source SHA-256 values, prepared blob IDs, and exact patch are pinned in verification.json and patch.diff.
- git diff --check passed on the two source files. Static assertions and evidence checksums are verified by verify_fix.py.
- No tests, builds, scans, CI, browser/runtime checks, or workflow edits were run. No merge, release, or tag was made.

Run python3 verify_fix.py from this directory to verify the pinned source patch and checksums against the repository's Git objects.
