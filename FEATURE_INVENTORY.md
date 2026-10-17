# slskdN Feature Inventory

This file is the canonical truth table for feature maturity. README, docs, startup registration, API routes, UI routes, config examples, and release notes should agree with this inventory.

## Scope of the "resolve before release claims" gate

The `stable` status below and the `chore(release): update stable metadata ...` version bumps are **two different meanings of the word "stable"** and must not be conflated:

- The release-channel "stable" (versus a `dev`/pre-release channel) is just which channel a build ships on. Cutting a stable-channel build is allowed regardless of this table.
- The `stable` status in this table is a **per-feature** maturity claim. The gate ("`unknown` must be resolved before release claims are made") governs **user-facing per-feature claims** in the README, docs, config examples, UI copy, and release notes — not the channel name.

Practical rule: until a feature is marked `stable` in the **Status** column, do not describe it as stable/production-ready/done in any user-facing text.

Current state (recount 2026-10-02): the **Status** column is fully classified — `stable` 5, `experimental` 51, `design-only` 6, `broken` 1, `moved-to-slskr` 1, `unknown` 0. The 49 `unknown` values in the **Tests** column and 10 in **Live smoke test** track verification coverage, not feature maturity. The standing caveat is that 51 features are `experimental`: user-facing docs should present those as experimental, not stable.

## Status values

- `stable` - implemented, documented, tested, and intended for normal users.
- `experimental` - implemented or partly implemented, but opt-in and not guaranteed stable.
- `design-only` - described in docs/plans, but not a shipped runtime feature.
- `broken` - present in code/config/docs but known not to work correctly.
- `moved-to-slskr` - superseded by the Rust rewrite / slskr direction.
- `delete` - should be removed.
- `unknown` - not yet classified; must be resolved before release claims are made.

## Decision values

- `keep` - keep as-is after verification.
- `gate` - require explicit feature gate / config and clear experimental warning.
- `demote-docs` - change README/docs so this is not presented as shipped/stable.
- `move-to-slskr` - point users/testers to slskr instead of slskdN.
- `remove` - delete code/docs/config surface.
- `needs-test` - code may be real but needs tests before stable claims.
- `needs-real-implementation` - current surface is not enough to support the claim.

## Inventory

| Feature | README claim | Config key | Startup registration | API endpoint | UI surface | Primary service/class | Tests | Live smoke test | Status | Decision | Owner notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Core slskd-compatible daemon | Existing slskd-compatible app/fork | core slskd config | Core startup | Existing API | Existing Web UI | Program / Application / Soulseek client wiring | Existing + needs audit | Needs smoke | stable | keep | Preserve upstream-compatible behavior first. |
| Normal single-source Soulseek downloads | Standard download path | transfers/download options | Download services | `/api/v0/transfers` family | Downloads page | `DownloadService` | needs regression expansion | Needs live peer smoke | stable | needs-test | Do not destabilize while cleaning experiments. |
| Auto-replace stuck downloads | Automatic alternative source replacement | auto-replace options | Transfer/rescue startup | transfer/rescue endpoints if present | Downloads header toggle | rescue/auto-replace services | unknown | unknown | experimental | gate | Keep conservative single-source rescue separate from swarm/chunking. |
| Wishlist / background search | Background saved searches | wishlist options | Wishlist services | wishlist endpoints | Wishlist page | `WishlistService` | unknown | unknown | experimental | needs-test | Verify before stable marketing. |
| Multiple download destinations | Multiple folders | destinations/folders | Transfer config | transfer enqueue APIs | destination selector | destination handling | unknown | unknown | experimental | needs-test | Confirm path validation and UI behavior. |
| Clear all searches | Search cleanup | none/unknown | Search services | search endpoints | Search UI | search services | unknown | unknown | experimental | needs-test | Likely real; verify. |
| Smart search result ranking | Ranked search results | ranking/history options | Search/ranking services | search APIs | Search UI badges/sort | ranking services | unknown | unknown | experimental | needs-test | Ensure math matches claims. |
| User download history badges | Source history indicators | ranking/history storage | Ranking services | ranking endpoint | Search/Browse badges | source ranking DB/services | unknown | unknown | experimental | needs-test | Verify data source. |
| Block users from search results | Local hide/block | browser localStorage | UI only | none/unknown | Search UI | web components | unknown | browser smoke | experimental | needs-test | Local-only feature should be labelled as such. |
| Delete files on disk | UI removal plus file delete | transfer options | Download service | transfer delete endpoint | Downloads page | `DownloadService` / file services | unknown | filesystem smoke | experimental | needs-test | Needs path guard + root containment tests. |
| Save search filters | Persist filters | browser/local settings | UI only | none/unknown | Search UI | web components | unknown | browser smoke | experimental | needs-test | Likely harmless. |
| Advanced search filters | Text/visual filter syntax | browser/local settings | Search services | search API | Search UI | search filter parser/services | unknown | search smoke | experimental | needs-test | Need parser tests. |
| User notes and ratings | Peer notes/ratings | storage options | User services | user endpoints | Search/Browse | user note services | unknown | unknown | experimental | needs-test | Verify persistence model. |
| Improved chat rooms | Enhanced rooms/messages | messaging options | Messaging services | messaging endpoints | Messages/Rooms UI | messaging services | unknown | live smoke | experimental | needs-test | Separate Soulseek-native from pod/mesh features. |
| Multi-select folder downloads | Download selected folders recursively | none/unknown | Browse/download services | browse/download endpoints | Browse UI | browse + download services | unknown | live smoke | experimental | needs-test | Regression test recursive collection. |
| Ntfy notifications | Mobile notifications | notification options | integration services | notification endpoints/status | System/Integrations | notification integration services | unknown | provider smoke | experimental | gate | Third-party egress disclosure required. |
| Pushover notifications | Mobile notifications | notification options | integration services | notification endpoints/status | System/Integrations | notification integration services | unknown | provider smoke | experimental | gate | Third-party egress disclosure required. |
| Tabbed browsing | Multiple browse tabs | browser local state | UI only | browse APIs | Browse UI | web components | unknown | browser smoke | experimental | needs-test | UI-only unless server caching claimed. |
| Unified smart source ranking | Source selection based on history | ranking options | ranking services | `/api/v0/ranking` if present | Badges/source sort | ranking services | unknown | unknown | experimental | needs-test | Needs exact scoring docs/tests. |
| Now Playing / scrobble | Updates profile from media players | nowplaying/integration options | nowplaying services | nowplaying/webhook endpoints | System/Player | nowplaying services | unknown | provider smoke | experimental | gate | Must document privacy/profile mutation. |
| Integrated web player | Local shared/downloaded playback | player options | streaming/player services | stream endpoints | footer player | streaming/player services | unknown | browser playback smoke | experimental | gate | Verify auth/range/root containment. |
| Listening parties | Pod/listen-along metadata | listening-party/pod options | listening party services | party endpoints | Player/Pod UI | listening party services | unknown | mesh smoke | experimental | gate | Depends on pod/mesh status. |
| Cancel transfers on ban | Ban cancels active transfer | blacklist/options | blacklist/transfer services | ban endpoints | user/block UI | blacklist + transfer services | unknown | live smoke | experimental | needs-test | Good candidate for stable after tests. |
| File type restrictions per group | Upload group extension allowlist | transfers.groups.* | upload services | upload/group endpoints | System policies | upload policy logic | unknown | upload smoke | experimental | needs-test | Needs enforcement tests. |
| Prometheus metrics dashboard | Built-in metrics UI | metrics options | metrics services | metrics endpoint | System/Metrics | prometheus/metrics services | unknown | local smoke | experimental | gate | Auth and password rules must be verified. |
| User score badges everywhere | Reputation/stat badges | ranking/reputation options | ranking/user services | ranking/user APIs | chat/search/browse/transfers | ranking/user services | unknown | browser smoke | experimental | needs-test | Avoid claiming reputation if only transfer stats exist. |
| PWA/mobile support | Installable app/mobile support | web manifest | web static files | web manifest | Web UI | web app | unknown | browser smoke | experimental | needs-test | Check manifest/service worker. |
| Discovery surfaces | Search/SongID/graph discovery | discovery options | discovery services | discovery endpoints | Search/SongID/Graph UI | discovery services | unknown | unknown | experimental | gate | Split concrete search flows from graph/SongID claims. |
| SongID | Identify tracks from URLs/files/text | `feature.SongId` plus songid options/integrations | SongID services | songid endpoints gated by `FeatureGate` | SongID UI | `SongIdService`, `SongIdCapabilityReporter` | `SongIdControllerTests`, `SongIdCapabilityReporterTests` | provider smoke | experimental | gate | Enabled by default but explicitly gated; `/api/v0/songid/capabilities` reports available, unavailable, and broken provider lanes at runtime. |
| System admin surfaces | Guided operator panels | many | system services | system endpoints | System tabs | system controllers/UI | unknown | browser smoke | experimental | needs-test | Ensure panels reflect real config only. |
| Multi-source swarm downloads | Parallel/verified/chunked downloads | `feature.MultiSourceDownloads` plus swarm/multisource options | multisource services | multisource endpoints gated by `FeatureGate` | Downloads accelerated toggle | multi-source services | unknown | live smoke | experimental | gate | Enabled by default but explicitly gated; split into tiers and do not conflate auto-replace with public chunking. |
| Swarm analytics | Analytics/recommendations | analytics options | analytics services | analytics endpoints | System dashboard | analytics services | unknown | unknown | design-only | demote-docs | Treat as roadmap unless real data path/tests exist. |
| DHT peer discovery | Public BitTorrent DHT rendezvous | `feature.Dht` plus dht options | DHT rendezvous services | dht endpoints gated by `FeatureGate` | Network/Mesh UI | DHT rendezvous services | unknown | network smoke | experimental | gate | Public DHT discovers mesh endpoints only; explicit feature and rendezvous settings are required. |
| Mesh overlay networking | TLS P2P mesh plus mesh DHT metadata | `feature.Mesh` plus mesh options | mesh services | mesh endpoints gated by `FeatureGate` | Mesh UI/footer | mesh services | unknown | network smoke | experimental | gate | Mesh DHT records travel over the overlay; file bytes stay on overlay transfers and must not be conflated with public DHT rendezvous. |
| Hash DB mesh gossip | Epidemic hash sync | mesh/hashdb options | mesh/hashdb services | hashdb endpoints | Mesh/System | gossip/hashdb services | unknown | mesh smoke | experimental | gate | Do not imply verified global truth. |
| Runtime capability handshakes | SlskdN peer capabilities | soulseek/mesh options | runtime/cap services | soulseek endpoints | Mesh/Soulseek UI | capability services/runtime | unknown | live peer smoke | experimental | gate | Verify against vendored runtime. |
| Soulseek mesh rendezvous | Interest-tag discovery | rendezvous options | soulseek discovery services | soulseek endpoints | Mesh discovery tools | soulseek discovery services | unknown | live smoke | experimental | gate | Must be opt-in only. |
| Type-1 obfuscation | Obfuscated P/D/F support | soulseek obfuscation options | runtime options | network status endpoint | System/Network | `SoulseekObfuscationSupport` / runtime | unknown | live smoke | experimental | needs-test | Likely real runtime work; verify. |
| Soulseek native discovery | Interests/recs/similar users | soulseek discovery options | native discovery services | `/api/v0/soulseek/*` | Search discovery UI | Soulseek discovery services | unknown | live smoke | experimental | gate | No native calls unless explicit UI/API invocation. |
| PathGuard | Directory traversal prevention | always-on/none | security/common utility | indirect | indirect | `PathGuard` | needs focused tests | unit tests | stable | needs-test | Real implementation; expand tests and call-site audit. |
| ContentSafety | Magic-byte mismatch/executable detection | safety options/unknown | security/common utility | indirect | indirect | `ContentSafety` | needs focused tests | unit tests | stable | needs-test | Real implementation; verify post-download integration. |
| BindExposureAnalyzer | No README claim; supports startup hardening correctness | web bind options | Program.cs hardening wiring | none | none | `BindExposureAnalyzer` | `BindExposureAnalyzerTests` | startup validation path | experimental | keep | Startup now uses analyzed listener exposure instead of port-enabled semantics. |
| HardeningValidator | Startup config fail-fast | web/security/diagnostics/metrics | startup validation | none | startup logs | `HardeningValidator` | `HardeningValidatorTests` matrix | config smoke | experimental | needs-test | Uses BindExposureAnalyzer for remote reachability; full-host startup tests remain optional follow-up. |
| NetworkGuard | Central network guard | planned | unknown | unknown | unknown | planned/new | none/unknown | none | design-only | demote-docs | Keep in security roadmap unless real implementation exists. |
| PeerReputation | Behavioral peer scoring | planned/reputation | unknown | unknown | badges maybe | planned/new | none/unknown | none | design-only | demote-docs | Do not conflate transfer stats with security reputation. |
| CryptographicCommitment | Commit/reveal protocol | planned | unknown | unknown | none | planned/new | none/unknown | none | design-only | demote-docs | Roadmap only unless protocol exists. |
| ProofOfStorage | Random chunk challenges | planned | unknown | unknown | none | planned/new | none/unknown | none | design-only | demote-docs | Roadmap only. |
| ByzantineConsensus | 2/3+1 voting | planned | unknown | unknown | none | planned/new | none/unknown | none | design-only | demote-docs | Roadmap only. |
| MusicBrainz integration | Metadata enrichment | integrations.musicBrainz | integration services | metadata endpoints | Integrations/SongID/Library | MusicBrainz client/services | unknown | provider smoke | experimental | gate | Third-party egress disclosure required. |
| AcoustID integration | Fingerprint lookup | integrations.acoustId | integration services | metadata endpoints | Integrations/SongID | AcoustID client/services | unknown | provider smoke | experimental | gate | Disabled by default unless privacy docs accurate. |
| Chromaprint integration | Fingerprint generation | integrations.chromaprint | integration services | metadata/songid endpoints | SongID/Library | Chromaprint services | unknown | binary/library smoke | experimental | gate | Verify executable/library availability. |
| Hash-from-audio-file | Audio hash from PCM | internal `HashFromAudioFileEnabled` only; public CLI/env toggle removed | validator blocks/unavailable | unknown | SongID/Library | unknown | none | none | broken | remove | Startup always fails if enabled because PCM extraction is unavailable. |
| Auto-tagging pipeline | Automatic MusicBrainz tagging | integrations.autotagging | integration services | library endpoints | Library/System | autotagging services | unknown | provider/file smoke | experimental | gate | Must avoid destructive tag writes without clear opt-in. |
| Library health scanner | Detect transcodes/missing tracks | libraryHealth options | library health services | library endpoints | System/Library | library health services | unknown | local library smoke | experimental | gate | Separate analysis from remediation. |
| Spectral transcode detection | Find FLACs made from MP3/AAC/Opus by their lowpass shelf | `audio.spectral_analysis` | `AddAudioCore` (`ISpectralAnalyzer`) | `POST /api/library/health/scans` (`includeSpectralAnalysis`) | System/Library Health scan option | `SpectralAnalyzer`, `SpectralClassifier` | unit + fake-ffmpeg pipeline | unknown | experimental | gate | Off by default; decodes only when enabled and requested (Library Health scan option or `analyze_completed_downloads`). Needs ffmpeg. Suspect/Upsampled are low-severity and may be mastering filters. |
| Library health remediation | Auto-fix/redownload | remediation options | remediation services | remediation endpoints | System/Library | remediation services | unknown | live smoke | experimental | gate | Must be opt-in and dry-run capable. |
| Lidarr integration | Wanted/import bridge | integrations.lidarr | Lidarr services | `/api/v0/integrations/lidarr/*` | Integrations/Lidarr UI | Lidarr client/sync/import services | unknown | provider smoke | experimental | gate | Recent active changes; verify. |
| VPN binding / port-forward agent | Host-side VPN companion | vpn options | VPN integration/agent | vpn endpoints/status | System/Integrations | VPN agent/services | unknown | host smoke | experimental | gate | OS/network safety critical. |
| Pod system | Decentralized communities | `feature.Pods` plus pod options | pod services | pod endpoints gated by `FeatureGate` | Pod UI/messages | pod services | unknown | mesh smoke | experimental | gate | Enabled by default but explicitly gated. |
| Gold Star Club auto-join | Explicitly opted-in bootstrap pod | `feature.Pods` plus exact `SLSKDN_POD_GOLD_STAR_CLUB_AUTOJOIN=true` | pod startup/publication | pod endpoints | Pod UI | pod services | unknown | focused unit | experimental | gate | Missing or non-`true` opt-in keeps creation, publication, and enrollment dormant. |
| Social federation | Federated social features | `feature.SocialFederation` plus federation options | social federation services | federation endpoints gated by `FeatureGate` | unknown | social federation services | unknown | none | experimental | gate | Enabled by default but explicitly gated; verify before stable claim. |
| VirtualSoulfind | Extended discovery/network layer | `feature.VirtualSoulfind` plus virtualSoulfind options | VirtualSoulfind services | VirtualSoulfind endpoints gated by `FeatureGate` | unknown | VirtualSoulfind services | unknown | none | experimental | gate | Enabled by default but explicitly gated; needs design/status doc. |
| Build quality gates | Static/coverage/regression tasks | MSBuild props | build only | none | build logs | custom MSBuild tasks | unknown | build smoke | experimental | needs-test | Move tasks out of app assembly. |
| Analyzer suppressions | Warning suppression list | csproj NoWarn | build | none | build logs | csproj | none | build smoke | stable | keep | Build infrastructure, not a user-facing feature; the NoWarn list ships and works in every build. Remaining work is documenting a reason per suppression (a docs chore, not a maturity question). |
| slskr Rust rewrite handoff | Forward-looking implementation | n/a | n/a | n/a | README/docs | separate repo | n/a | n/a | moved-to-slskr | move-to-slskr | Docs must clearly state which features moved. |

## Release rule

No README claim should be upgraded to `stable` unless the feature has concrete code, tests, and a successful smoke path recorded here.
