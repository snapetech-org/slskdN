# Changelog

## 10.0.3 - 2026-10-22

- Synced the runtime with Soulseek.NET upstream through `c07c187` and adapted the fork's client, protocol, and test integrations.
- Updated the Web API and frontend dependencies, including fixes for CVE-2025-6965, CVE-2026-62900, and the two `follow-redirects` advisories.
- Updated the Web API container to .NET 8 and configured it to run as the built-in non-root `app` user.
- Pinned GitHub Actions to immutable commit SHAs and added a seven-day Dependabot cooldown.
