# Changelog

## 10.0.4 - 2026-11-12

- Updated the Web API, examples, and test projects to .NET 11 and replaced the deprecated ASP.NET API versioning package with `Asp.Versioning.Mvc.ApiExplorer`.
- Removed the obsolete MVC compatibility API that no longer compiles on ASP.NET Core 11.
- Updated maintained .NET analyzers, test tooling, SQLite, JWT, OpenAPI, and frontend build dependencies to current stable releases.
- Updated Axios to 1.21.1, which requires patched `follow-redirects` 1.16.2 or later, addressing CVE-2026-116689.
- Removed the unused SignalR browser package and redundant legacy HTTP and regular expression test packages.
- Extended private-JIT CI to build the frontend and retain the runtime NuGet packages used for releases.

## 10.0.3 - 2026-10-22

- Synced the runtime with Soulseek.NET upstream through `c07c187` and adapted the fork's client, protocol, and test integrations.
- Updated the Web API and frontend dependencies, including fixes for CVE-2025-6965, CVE-2026-62900, and the two `follow-redirects` advisories.
- Updated the Web API container to .NET 8 and configured it to run as the built-in non-root `app` user.
- Pinned GitHub Actions to immutable commit SHAs and added a seven-day Dependabot cooldown.
- Added shared-port peer obfuscation, an injectable primary listener, and a separately configurable advertised port.
- Hardened peer initialization framing and listener cancellation/retry handling; inactive search responses are discarded before parsing file lists.
- Added bounded streaming serialization for browse responses and a regression test for search teardown races.
