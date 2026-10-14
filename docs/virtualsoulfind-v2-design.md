# VirtualSoulfind v2 – Design Document

**Repo:** `github.com/snapetech-org/slskdN`

**Current Branch:** `main`

**Lineage:** historical `experimental/multi-source-swarm` design workstream

**Status:** Draft design

**Author:** AI Assistant + User

**Created:** December 11, 2025
**Scope:** Extend VirtualSoulfind into a full "virtual catalogue + multi-source planner" brain, integrated with the mesh/service fabric and mesh DHT, without hammering Soulseek or making it second-class.

> **Project Note**: This is a fork of [slskd](https://github.com/slskd/slskd). See [../README.md](../README.md#acknowledgments) for attribution.

> **DHT terminology**: this design's catalogue and source-discovery records
> use the slskdN mesh DHT. Public BitTorrent DHT is only endpoint rendezvous;
> the mesh overlay carries metadata exchange and file transfers. See [DHT and
> Mesh Architecture](DHT_MESH_ARCHITECTURE.md).

---

## 1. Background & Motivation

VirtualSoulfind today sits roughly as:

* A metadata-first layer that understands releases/tracks via external catalogues (MusicBrainz, etc.).
* A way to map those IDs onto available sources (Soulseek, local files, maybe mesh/BT).
* A starting point for smarter, ID-driven search and source selection.

With the new multi-source-swarm branch, service fabric, mesh DHT, and mesh gateway, VirtualSoulfind can evolve into the central "brain" for:

* Virtual catalogue browsing and "offline planning".
* Multi-source planning across Soulseek, mesh DHT/overlay, BT, HTTP, LAN, and local library.
* Precise matching, verification, and library reconciliation.
* Strict control over how and when Soulseek is touched.

Key constraints:

* **No Soulseek abuse.** Turbo behavior is allowed only via mesh DHT/overlay, BT, and other non-Soulseek paths.
* **Soulseek remains first-class but not a punching bag.**
* **Backwards compatible.** The system must not break existing flows or turn slskdn into a weird client on the Soulseek network.

---

## 2. Goals & Non-Goals

### 2.1 Goals

1. **Virtual Catalogue Mode.**
   Provide a rich, MBID-centric catalogue of artists/releases/tracks that can be browsed and planned against even if Soulseek is offline.

2. **Intent Queue & Planner.**
   Represent what the user *wants* (virtual releases/tracks) as an explicit intent queue, separate from actual network fetches.

3. **Multi-Source, Metadata-Driven Planner.**
   Use VirtualSoulfind metadata to drive multi-source planning across:

   * Soulseek
   * Mesh DHT/overlay
   * BitTorrent / multi-swarm
   * HTTP / LAN / local mirrors

   Prefer non-Soulseek sources where possible.

4. **Precise Matching & Verification.**
   Use MBID, expected durations, hashes, fingerprints, and canonical metadata to:

   * Reduce wrong downloads and retries.
   * Normalize library naming.
   * Maintain a "verified copy registry".

5. **Soulseek-safe behavior.**
   Enforce per-backend limits (especially Soulseek) *inside* VirtualSoulfind, so anything built on top cannot spam Soulseek accidentally.

6. **Advanced library workflows.**
   Support virtual crates/smart lists, gap-finding, and "what most improves this library" advisory, all largely offline.

7. **Integrate with the service fabric & gateway.**
   Expose VirtualSoulfind capabilities as:

   * A mesh service (`virtual-soulfind` / `mbid-index` style).
   * Local HTTP gateway endpoints for tooling.

### 2.2 Non-Goals

* Replacing the Soulseek protocol or changing its wire semantics.
* Solving all possible trust/poisoning problems in the mesh DHT; we will implement *basic* heuristics and leave advanced reputation to other components.
* Building a full-blown UI in this doc; UI is out-of-scope beyond API affordances and expectations.

---

## 3. High-Level Architecture

VirtualSoulfind v2 is a module composed of several cooperating components:

* **Virtual Catalogue Store**
  Local DB of artists, releases, tracks, MBIDs, and catalogue metadata.

* **Intent Queue**
  Persistent queue of "DesiredRelease" / "DesiredTrack" objects with priorities and modes (Wanted, Backfill, etc.).

* **Source Registry**
  Internal catalogue of potential sources for each track:

  * Soulseek (when allowed)
  * Mesh DHT/overlay (service descriptors, content keys)
  * BT/multi-swarm
  * HTTP / LAN
  * Local library (already have it)

* **Multi-Source Planner**
  Given a VirtualRelease/VirtualTrack, produces a multi-backend plan:

  * Which backends to use.
  * In what order.
  * Under what constraints.

* **Match & Verification Engine**
  Encapsulates duration checks, hashes, audio fingerprints (when available), template naming, and verified copy registry.

* **Backend Adapters**
  Abstractions for each backend:

  * `ISoulseekBackend`
  * `IMeshDhtBackend`
  * `ITorrentBackend`
  * `ILocalLibraryBackend`
  * (Optional) `IHttpBackend`, `ILanBackend`

* **Policy & Limits**
  Per-backend and per-origin (User vs Mesh) rules for:

  * Rate limiting
  * Concurrency
  * Work budget (integrates with H-02 and H-08)

* **Service & Gateway Facades**
  VirtualSoulfind as:

  * `IVirtualSoulfindService` exposed over mesh service fabric.
  * HTTP gateway endpoints for local tooling (`/virtual/*`).

---

## 4. Data Model

This section defines main domain entities and their relationships. Implementation detail (DB schema) can be SQLite/EF/whatever the repo uses now.

### 4.1 Core Entities

#### `Artist`

* `ArtistId` (internal)
* `MusicBrainzId` (optional)
* `Name`
* `SortName`
* `Tags` (genres, etc.)

#### `ReleaseGroup`

* `ReleaseGroupId`
* `MusicBrainzId`
* `ArtistId`
* `Title`
* `PrimaryType` (Album, EP, Single, etc.)

#### `Release`

Represents a specific edition of a release (year, region, etc.).

* `ReleaseId`
* `MusicBrainzId`
* `ReleaseGroupId`
* `Title`
* `Year`
* `Country`
* `Label`
* `CatalogNumber`
* `MediaCount` (discs)

#### `Track`

Canonical metadata for an audio unit.

* `TrackId`
* `MusicBrainzRecordingId` (or similar)
* `ReleaseId`
* `DiscNumber`
* `TrackNumber`
* `Title`
* `DurationSeconds` (canonical)
* `CanonicalBitDepth` / `SampleRate` (optional)
* `Tags`

### 4.2 Local Library Entities

#### `LocalFile`

* `LocalFileId`
* `Path`
* `SizeBytes`
* `DurationSeconds` (measured)
* `Codec` / `Bitrate` / `Channels`
* `HashPrimary` (e.g. SHA256)
* `HashSecondary` (e.g. xxHash)
* `AudioFingerprintId` (if used)
* `InferredTrackId` (nullable; linking to Track)
* `QualityRating` (derived)

#### `VerifiedCopy`

Represents that we have a known-good copy of a track/release.

* `VerifiedCopyId`
* `TrackId`
* `LocalFileId`
* `HashPrimary`
* `DurationSeconds`
* `VerificationSource` (manual, multi-check, etc.)

### 4.3 Intent Entities

#### `DesiredRelease`

* `DesiredReleaseId`
* `ReleaseId`
* `Priority` (High/Normal/Low)
* `Mode` (Wanted, NiceToHave, Backfill)
* `Status` (Pending, Planned, InProgress, Completed, Failed, OnHold)
* `CreatedAt`, `UpdatedAt`
* `Notes`

#### `DesiredTrack`

* `DesiredTrackId`
* `TrackId`
* `ParentDesiredReleaseId` (nullable)
* `Priority`
* `Status` (as above)
* `PlannedSources` (summary, e.g. JSON list of preferred backends and constraints)

### 4.4 Source Registry Entities

#### `SourceCandidate`

A potential way to obtain a specific track.

* `SourceCandidateId`
* `TrackId`
* `Backend` (enum: Soulseek, MeshDht, Torrent, Http, Lan, Local)
* `BackendRef` (e.g. Soulseek user/file path, torrent infohash+file index, mesh service descriptor ID, HTTP URL, LocalFileId)
* `ExpectedQuality` (enum or score)
* `TrustScore` (float 0–1)
* `LastValidatedAt`, `LastSeenAt`
* `IsPreferred` (bool)

---

## 5. Backend Abstractions

We define backend interfaces so VirtualSoulfind never hardcodes how to talk to any network.

### 5.1 `IContentBackend`

At minimum:

```csharp
public enum ContentBackendType
{
    Soulseek,
    MeshDht,
    Torrent,
    Http,
    Lan,
    LocalLibrary
}

public interface IContentBackend
{
    ContentBackendType Type { get; }

    // Discover candidates for a given track.
    Task<IReadOnlyList<SourceCandidate>> FindCandidatesAsync(
        TrackId trackId,
        CancellationToken cancellationToken);

    // Optionally: evaluate/update trust or validate a candidate.
    Task<SourceCandidateValidationResult> ValidateCandidateAsync(
        SourceCandidate candidate,
        CancellationToken cancellationToken);
}
```

Concrete implementations:

* `SoulseekContentBackend`
* `MeshDhtContentBackend`
* `TorrentContentBackend`
* `HttpContentBackend`
* `LanContentBackend`
* `LocalLibraryBackend`

All of them must respect:

* Work budget (H-02).
* Soulseek-specific caps (H-08) where applicable.

---

## 6. Multi-Source Planner

The planner is a pure logic component that:

* Takes a `DesiredTrack` or `DesiredRelease`.

* Consults:

  * Virtual catalogue
  * Source registry
  * Backends
  * Policy/limits

* Produces a `Plan`:

  * Which candidates to try, in what order and concurrency.
  * Per-backend constraints.

### 6.1 Planner Input

* `DesiredTrack` (or full `DesiredRelease`).
* `PlanningMode` (Offline, SoulseekFriendly, MeshOnly).
* Current per-backend state:

  * Active work items.
  * Historical reliability for each backend / peer.

### 6.2 Planner Output (Sketch)

```csharp
public sealed class TrackAcquisitionPlan
{
    public TrackId TrackId { get; init; }
    public IReadOnlyList<PlanStep> Steps { get; init; }
}

public sealed class PlanStep
{
    public ContentBackendType Backend { get; init; }
    public IReadOnlyList<SourceCandidate> Candidates { get; init; }
    public int MaxParallel { get; init; }
    public TimeSpan Timeout { get; init; }
    public PlanStepFallbackMode FallbackMode { get; init; } // e.g. cascade or fan-out
}
```

The planner is policy-driven:

* In **MeshOnly** mode:

  * Only MeshDHT/Torrent/HTTP/LAN backends are allowed.
* In **OfflinePlanning**:

  * No network backends; only local library + catalogue.
* In **SoulseekFriendly**:

  * Soulseek can be used but with strict per-backend caps.

---

## 7. Match & Verification Engine

This component handles:

* Strict track matching (duration, MBID, track number).
* Hash/fingerprint checks.
* Verified copy registry updates.
* Canonical naming decisions.

### 7.1 Matching Criteria

For candidate `LocalFile` vs `Track`:

1. **MBID / metadata match** (if present in tags).
2. **Duration match**:

   * Accept within ±tolerance (config, e.g. ±1–2 seconds or ±0.5%).
3. **Track context**:

   * Disc/track number compatibility with release.

Scoring:

* Hard reject if outside duration tolerance unless user opts into "loose matching".
* Prefer candidates with:

  * Verified hash.
  * Matching MBID.
  * Prior successful usage.

### 7.2 Verified Copies

When a file passes all checks:

* Create/refresh `VerifiedCopy` entry.
* Use that as the truth source for:

  * Later candidate verification.
  * Mesh-DHT/overlay announcements of "this node has a correct copy".

### 7.3 Canonical Naming

Use VirtualSoulfind's knowledge to generate canonical paths:

* `Artist/Year - Album/[Disc-]Track - Title (Source, Codec, Bitrate).ext`

Applied to:

* New downloads.
* Optional library normalization passes.

---

## 8. Integration with Service Fabric & HTTP Gateway

### 8.1 Mesh Service: `VirtualSoulfindService`

Expose a mesh service (via `IMeshService`) with methods like:

* `GetVirtualRelease(releaseId)`
* `ListMissingTracksForRelease(releaseId)`
* `GetPlanForRelease(releaseId)`
* `RegisterVerifiedCopy(trackId, hash, duration)`
* `QuerySourceCandidates(trackId)`

Security:

* Only expose non-sensitive metadata.
* Do not expose local file paths or OS-level details.
* Enforce work budgets and rate limits per peer.

### 8.2 HTTP Gateway

Expose a local HTTP facade (through the hardened gateway, H-01):

Examples:

* `GET /virtual/releases/{releaseId}`
* `GET /virtual/releases/{releaseId}/missing`
* `POST /virtual/intents/releases/{releaseId}` (create `DesiredRelease`)
* `GET /virtual/intents/releases` (list queue)
* `POST /virtual/plan/releases/{releaseId}/execute` (under strict config, triggers resolver)

All calls must:

* Respect gateway auth/CSRF and allowlists.
* Respect backend limits and work budgets.

---

## 9. Workflows

### 9.1 Virtual Catalogue Browsing

1. User (or tool) queries `/virtual/releases?artist=...`.
2. VirtualSoulfind returns purely metadata from catalogue store.
3. No Soulseek or other network traffic unless planner/resolver is explicitly invoked.

### 9.2 Add Release to Intent Queue

1. UI/CLI/HTTP calls `POST /virtual/intents/releases/{releaseId}` with mode (Wanted, Backfill).
2. VirtualSoulfind creates `DesiredRelease` + child `DesiredTrack` entries.
3. Status is `Pending`.

### 9.3 Plan & Execute Acquisition

1. Resolver job picks a `DesiredRelease` or `DesiredTrack` with `Pending`.

2. Calls Multi-Source Planner with current `PlanningMode` and policy.

3. Planner generates `TrackAcquisitionPlan`.

4. Execution layer:

   * For each plan step:

     * Consults backends.
     * Respects work budget and Soulseek caps.
     * Uses match/verification engine on results.

5. On success:

   * `DesiredTrack.Status` → `Completed`.
   * Verified copy updated.

6. On failures or timeouts:

   * `Status` → `Failed` / `OnHold` with reason.

### 9.4 Library Reconciliation

1. Library scanner populates `LocalFile` entities.
2. Match engine tries to map them to `Track` entities.
3. VirtualSoulfind can then:

   * Identify missing tracks.
   * Suggest upgrades (low quality → better quality).
   * Update `VerifiedCopy`.

No network traffic required.

---

## 10. Policy, Limits & Modes (Soulseek Safety)

VirtualSoulfind will own high-level policy decisions.

### 10.1 Per-Backend Config Example

```yaml
VirtualSoulfind:
  Modes:
    DefaultMode: SoulseekFriendly
  Backends:
    Soulseek:
      MaxSearchesPerMinute: 3
      MaxBrowsesPerMinute: 2
      MaxParallelSearches: 1
      MaxParallelDownloadsFromSameUser: 1
    MeshDht:
      MaxSearchesPerMinute: 50
      MaxParallelSearches: 20
    Torrent:
      MaxMetadataRequestsPerMinute: 100
    Http:
      MaxParallelFetches: 10
    LocalLibrary:
      MaxScanJobs: 4
```

### 10.2 Modes

* **SoulseekFriendly**
  Soulseek allowed, but under strict caps and concurrency limits.

* **OfflinePlanning**
  No network backends; VirtualSoulfind only uses catalogue + local library.

* **MeshOnly**
  Only MeshDHT/Torrent/HTTP/LAN backends are used; Soulseek disabled in planner.

These modes integrate with the work budget (H-02) and Soulseek limiter (H-08).

---

## 11. Security & Privacy

Key principles:

* No third-party Soulseek user data in the mesh DHT or VirtualSoulfind indices:

  * No usernames.
  * No room names.
  * No IPs.

* Source candidates for Soulseek:

  * Only represent *this node's* knowledge of "user X offers file path Y", stored locally.
  * Not published into the mesh DHT.

* Mesh-DHT/overlay announcements:

  * Only expose internal peer IDs and content IDs, never Soulseek-specific identifiers.

* HTTP gateway:

  * Protected by API key and CSRF header (H-01).
  * Only exposes VirtualSoulfind metadata and high-level instructions, not arbitrary local filesystem access.

---

## 12. Backwards Compatibility & Migration

* Existing VirtualSoulfind behaviors should:

  * Continue to work with minimal changes.
  * Be gradually refactored into the new components.

* Migration steps:

  1. Introduce new data structures and store alongside existing ones.
  2. Add thin adapters to bridge old call sites into new planner/backend abstractions.
  3. Slowly move code over; once stable, deprecate old structures.

* Legacy Soulseek-only mode:

  * If `LegacySoulseekMode` is enabled:

    * VirtualSoulfind should limit itself to:

      * Local catalogue & library.
      * No mesh DHT/overlay or turbo features.
    * Behavior should approximate plain slskd.

---

## 13. Observability

* Metrics:

  * `virtualsoulfind_intents_total` (by status/mode).
  * `virtualsoulfind_plans_total` (by backend, outcome).
  * `virtualsoulfind_matches_total` (successful vs failed matches).
  * Soulseek-side metrics (from H-08) broken out by origin (`User`, `MeshService`).

* Logs:

  * Summarize plans and outcomes without logging full file paths or PII.
  * Log when:

    * Soulseek caps are hit.
    * Work budgets are exhausted.
    * Mesh-DHT poisoning heuristics trigger.

---

## 14. UI Integration

**Important**: VirtualSoulfind v2 integrates with the **existing slskdn web UI**, not creating a separate UI. We can harden the existing UI if necessary.

### 14.1 Web UI Enhancements

The existing web UI will be extended with VirtualSoulfind v2 views:

* **Virtual Catalogue Browser**: Browse artists/releases/tracks from catalogue store
* **Intent Queue Dashboard**: Manage desired releases and tracks
* **Planner Visualization**: Show acquisition plans and backend choices
* **Library Reconciliation View**: Show gaps, duplicates, upgrade opportunities
* **Settings Panel**: Configure modes, backends, and limits

### 14.2 Security Considerations for UI

* All UI endpoints go through hardened HTTP gateway (H-01)
* API key and CSRF token required
* No automatic execution of plans without explicit confirmation
* Clear warnings when actions will trigger network activity
* No generic "execute arbitrary service call" console exposed

---

## 15. Security & Hardening Considerations

This section assumes all the earlier hardening tasks (H-01…H-10) exist or will exist. Here we specifically look at how VirtualSoulfind v2 interacts with those, and where it needs its own protections.

### 15.1 Threat Model Summary

Primary threat vectors:

1. **Remote mesh-DHT peers**
   * Malicious or Sybil peers poisoning metadata, DHT entries, and service calls.

2. **Untrusted HTTP callers**
   * Local/remote processes or browsers abusing VirtualSoulfind via the gateway.

3. **Correlation/deanonymization**
   * Linking Soulseek, mesh, BT, HTTP and catalogue behavior to a single real-world identity.

4. **Local compromise**
   * Malicious software/users on the same machine accessing VirtualSoulfind's data, keys, and intents.

5. **Abuse of the node as a workhorse**
   * Using VirtualSoulfind as a control plane to cause massive download, indexing, or scanning activity.

Design choices below should reduce damage from all of the above.

---

### 15.2 Identities, Privacy, and Correlation

**Risks:**
* VirtualSoulfind holds a detailed picture of your tastes and library, plus cross-network source/peer information.
* It acts as a bridge between MBID-level metadata, local paths, and potentially multiple networks.

**Mitigations / Requirements:**

1. **Data-level separation of identifiers**
   * Ensure schema and code never join Soulseek identifiers directly into persistent VirtualSoulfind entities.
   * `SourceCandidate.BackendRef` for Soulseek should be an internal ID (e.g. `SoulseekPeerId`), not a username; mapping to username stays in a separate, Soulseek-specific table.
   * Same goes for IPs: mesh peer IPs shouldn't be stored in VirtualSoulfind's catalogue structures.

2. **Configurable "privacy mode"**
   * Add `VirtualSoulfind.PrivacyMode` with options like:
     * `Normal` – full features.
     * `Reduced` – no storing of external peer identifiers, only booleans like "mesh has/does not have this content".
   * In `Reduced` mode:
     * `SourceCandidate` is abstract ("available via mesh DHT"), without peer attribution; you still can plan, but correlation is weaker.

3. **Metrics and logging hygiene**
   * No metrics that directly combine:
     * Soulseek usernames, MBIDs, and IPs in labels.
   * Logs for VirtualSoulfind must:
     * Not include full local paths by default.
     * Not include external user identifiers.
     * Use IDs that are non-trivial to tie to a real person without additional context.

4. **Key rotation awareness**
   * If mesh identities are rotated (H-04), VirtualSoulfind must:
     * Treat old peer IDs as historical only.
     * Not assume a single mesh identity is stable forever.

---

### 15.3 Catalogue Store & Intent Queue

These are "low-risk" but high-value for privacy.

**Risks:**
* Leak of catalogue + intents reveals listening habits, planned acquisitions, etc.
* Malicious local or mesh/gateway access to the intent queue could be used to trigger huge amounts of downstream work.

**Mitigations:**

1. **Local storage permissions**
   * Catalogue DB and intent queue DB should:
     * Live under a dedicated app directory.
     * Inherit restrictive filesystem permissions (from H-09's dedicated user).
   * Provide a clear "data directory" config and recommend locking it down.

2. **Gateway exposure**
   * Any HTTP endpoints that read/write intents:
     * MUST go through hardened gateway rule set (H-01).
     * MUST require auth and CSRF headers.
   * Add an explicit config to disable intent manipulation via HTTP:
     * `VirtualSoulfind.AllowRemoteIntentManagement = false` by default.

3. **Intent queue rate limiting**
   * Add a simple per-peer/per-IP limit on:
     * How many new `DesiredRelease`/`DesiredTrack` objects can be created per time window via mesh or gateway.
   * For local CLI/interactive use, this won't matter; for remote callers, it stops abuse.

---

### 15.4 Source Registry & Backend Interfaces

This is where we integrate VirtualSoulfind with all the networks.

**Risks:**
* `SourceCandidate` table becomes a "map of who has what".
* Backend implementations could be tricked into doing SSRF-like actions (HTTP, LAN).
* Backend misuse as an amplification vector (trigger lots of downstream work).

**Mitigations:**

1. **Avoid storing third-party identity in source registry**
   * For Soulseek sources:
     * Store a local "peer handle" only; the real username/IP stays in the Soulseek module.
   * For mesh DHT/overlay:
     * Store peer IDs that are internal to the mesh, not IPs.

2. **Backend-level work budget enforcement**
   * Each `IContentBackend` implementation must:
     * Consume the H-02 work budget before any external call (Soulseek search/browse, BT metadata, HTTP fetch, etc.).
   * This prevents VirtualSoulfind from ignoring budgets.

3. **HTTP / LAN backend isolation**
   * If `HttpContentBackend` or `LanContentBackend` exist:
     * They must use an outbound HTTP client / network wrapper that enforces:
       * No access to loopback or private subnets by default (SSRF guard).
     * They should only be used for URLs acquired from trusted sources (e.g., config or known registries), not arbitrary user input.

4. **Per-backend caps (tied to config)**
   * Backends must consult `VirtualSoulfind.Backends.*` config when planning and executing:
     * Max parallel fetches.
     * Max operations per minute.
   * That plus work budget gives you two independent safety rails.

---

### 15.5 Planner & Resolver

Planner + resolver are the "brains" that actually cause work to happen.

**Risks:**
* A malicious peer or user could enqueue thousands of intents, causing massive network/CPU usage when the resolver runs.
* Bad planning logic could prefer Soulseek in ways that break your "SoulseekFriendly" contract.

**Mitigations:**

1. **Global limits on resolver throughput**
   * Configurable caps such as:
     * `Resolver.MaxTracksPerRun`
     * `Resolver.MaxConcurrentPlans`
   * Resolver never processes more than `N` tracks per execution window, regardless of queue size.

2. **Per-origin splitting**
   * Mark intents with `Origin`:
     * `UserLocal`
     * `LocalAutomation`
     * `RemoteMesh`
     * `RemoteGateway`
   * Resolver can prioritize:
     * `UserLocal` over others.
     * Hard cap `Remote*` origins to small slices per run.

3. **Policy enforcement inside the planner**
   * Planner must respect modes:
     * In `OfflinePlanning`: no network backends at all.
     * In `MeshOnly`: never include Soulseek in plans.
     * In `SoulseekFriendly`: Soulseek steps must conform to Soulseek caps from H-08.
   * This solves "oops, I switched config but planner still uses Soulseek as primary".

4. **Plan validation**
   * Before executing a plan:
     * Check that aggregated backend costs will not exceed:
       * Per-call work budget.
       * Per-peer budget.
       * Soulseek-specific caps.
   * If invalid:
     * Planner must downgrade (e.g., drop certain backends, lower parallelism) or mark intent as `OnHold/Failed` with a reason.

---

### 15.6 Match & Verification Engine

This is mostly offline, but it touches real files and might influence what you share/advertise.

**Risks:**
* A bug here could mark wrong files as "verified good" → you propagate garbage.
* If fingerprinting calls external services, that may leak fragments of your library to third parties.

**Mitigations:**

1. **Local-only verification by default**
   * Verification should:
     * Use local metadata, hashes, and optional local fingerprints.
   * No default calls to external online fingerprinting services.
   * If remote fingerprint services are supported:
     * Make them off by default with explicit config + documentation.

2. **Safety checks before advertising**
   * Only treat a track as "advertisable" when:
     * It matches the Track's canonical duration within tolerance.
     * Its hash is stable and (optionally) confirmed by multiple checks.
   * This helps avoid poisoning the mesh DHT with mislabeled content.

3. **Guard against trusting unknown fingerprints**
   * If you support crowd-fingerprint data:
     * Treat it as one hint among others.
     * Never rely on it as the sole criteria for verification.

---

### 15.7 Mesh Service & HTTP Gateway Facades

These are major attack surfaces.

**Risks:**
* Mesh peers call VirtualSoulfind service to cause lots of work.
* HTTP clients (local or remote) abuse VirtualSoulfind to drive heavy scanning or downloading.

**Mitigations:**

1. **Service-level allowlist & method scope**
   * Mesh service:
     * Limit what methods are exposed over mesh:
       * Prefer read-only metadata queries (virtual releases, missing tracks summary).
       * Restrict high-cost operations (planning, execute plan) or require special trust/whitelist.
   * HTTP:
     * Use gateway service allowlist and per-method/route allowlists:
       * e.g. allow `GET /virtual/...` widely.
       * Gate `POST /virtual/plan/.../execute` behind:
         * API key.
         * Strict work budgets.
         * Maybe disabled by default.

2. **Origin-based quotas**
   * For mesh service:
     * Use per-peer quotas in combination with H-02's work budget:
       * Limit how often a given remote peer can ask for plans or candidate lists.
   * For HTTP:
     * Use IP-based quotas (via gateway) if you ever allow non-localhost exposure.

3. **Design for read-heavy, write-light exposure**
   * Prefer exposing:
     * Metadata reading (catalogue, missing tracks) to external callers.
   * Keep:
     * Mutating operations (enqueue intents, execute plans) tightly constrained and auth-protected.

---

### 15.8 Observability & Logging

**Risks:**
* Over-verbose logs and metrics become a privacy and security liability.
* Error paths might accidentally dump sensitive state.

**Mitigations:**

1. **Log redaction**
   * Any logs related to:
     * Local paths.
     * External peer identifiers.
     * Content hashes.
   * Should be:
     * Truncated.
     * Sanitized (e.g. just the basename instead of full path, or just prefix of hash).

2. **Metrics cardinality control**
   * Avoid labels with:
     * `ReleaseId`/`TrackId` at high cardinality.
   * Use aggregated metrics instead:
     * e.g. success/failure counts per backend, not per track.

3. **Explicit log levels**
   * Use:
     * `DEBUG`/`TRACE` for verbose details (opt-in).
     * `INFO` for high-level events.
     * `WARN`/`ERROR` for serious issues, but still without sensitive payloads.

---

## 16. Open Questions – Concrete Decisions

Now, specific answers to the open questions.

### 16.1 Audio Fingerprinting – What and How?

**Decision:**
* Use **Chromaprint/AcoustID-compatible fingerprints** as the default internal fingerprint format.
* Treat fingerprinting as **optional, local-first**:
  * By default:
    * Compute and store fingerprints locally.
    * Do **not** query external services.
  * Optionally:
    * Allow querying AcoustID (or similar) via config:
      * `VirtualSoulfind.Fingerprinting.UseExternalService = true`
      * Require explicit API key and a big disclaimer.

**Implementation notes:**
* Add a `FingerprintId` field to `LocalFile`:
  * Store the raw or compressed Chromaprint data.
* Fingerprinting should be:
  * Batchable:
    * Run as a low-priority background job, throttled by CPU usage and I/O.
  * Integrated with work budget:
    * Treat fingerprinting as "local CPU-heavy work", with its own budget to avoid saturating the machine.

**Security & privacy:**
* Default: no external fingerprint submissions, so no library content is leaked to third-party services.
* If user enables external lookups:
  * Clearly document that some content info (acoustic fingerprints) will be sent to a third party.

---

### 16.2 Shared "Verified Copy Registry" Over Mesh

**Question:** Should verified copies be shared at all, and if so, how?

**Decision:**
* Yes, but **only in a minimal, privacy-preserving, and trust-scoped way**.
* Two layers:
  1. **Local registry (mandatory):**
     * Full `VerifiedCopy` records stay local.
  2. **Mesh hints (optional):**
     * Export only:
       * `TrackId`/MBID (or a derived content key).
       * A short fingerprint or hash prefix (for collision detection).
       * A confidence score.
     * No direct local paths, no user tags, no Soulseek usernames.

**Mechanics:**
* A dedicated mesh service (`verified-copy-hints`) that:
  * Answers queries like:
    * "Do you have a verified copy of TrackId X?"
  * Responds with:
    * Yes/No and, if yes, hash-prefixed fingerprints that can help validate others' copies.
* Trust scoping:
  * By default:
    * Only answer such queries for "trusted peers":
      * e.g. same pod, same friend list, or peers with high reputation.
  * Configurable:
    * `VerifiedCopyHints.Enabled = false` by default.
    * `VerifiedCopyHints.TrustPolicy = {TrustedOnly, FriendsOnly, All}`.

**Security implications:**
* Avoid sharing full library contents; you only leak presence of particular MBIDs for peers that already know about them or are in your trust zone.
* Hints are not enough to reconstruct exact file structure or full library, but help with correctness and validation across mesh participants.

---

### 16.3 Smart Prioritization – What Signals to Use?

**Question:** How does VirtualSoulfind decide "what is most worth fetching/backfilling"?

**Decision:**
* Use a blend of **local signals** and **public catalogue signals**, but keep it offline-friendly and Soulseek-neutral.

**Signals to combine:**

1. **Local library gaps**
   * Missing tracks for releases you already partially own.
   * Upgrades where you have low-quality and know higher-quality releases exist.

2. **User preferences**
   * Explicit "favorite artists/labels/genres".
   * Play counts from local player logs if available (or separate scrobbler).

3. **Catalogue metadata**
   * From MusicBrainz / similar:
     * Release type (album > single > compilation).
     * Popularity proxies if available (number of releases, tags like "essential"/"classic", etc.).
   * We can treat these as static hints cached locally; no need to constantly hit external APIs.

4. **External "importance" feeds (optional)**
   * ListenBrainz/Last.fm/RYM integration could be offered as:
     * Optional plugin/module.
   * Same privacy stance as fingerprinting:
     * Off by default.
     * Requires explicit keys and user opt-in.

**Algorithm sketch:**
* Compute a simple score:
  * `Score = f(LocalGapWeight, PreferenceWeight, CatalogueWeight, OptionalExternalWeight)`
* Use that to:
  * Rank `DesiredRelease`/`DesiredTrack` when the resolver chooses what to process.
* Keep it deterministic and transparent:
  * Store the components of the score in the DB for introspection.

**Security & privacy:**
* By default, prioritization should work purely off:
  * Local library.
  * Local preferences.
  * Cached catalogue metadata.
* Any external signals must be opt-in + documented.

---

### 16.4 UI – How to Expose This Safely and Usefully?

**Question:** What UI elements make sense, and what are the security concerns?

**Decision:**
* Provide a **VirtualSoulfind UI layer** within the existing slskdn web UI that is:
  * Mostly read-only.
  * Very explicit when actions cause network work.

**UI elements:**

1. **Virtual Releases view**
   * Displays:
     * Artists → releases → tracks from the catalogue store.
   * Shows:
     * Local status (have/missing/partial, quality).
     * Verified status (via icons).
   * Actions:
     * "Add release to intent queue" (with mode).
   * No immediate network calls on simple browsing.

2. **Intent Queue dashboard**
   * Lists `DesiredRelease` / `DesiredTrack` with:
     * Status.
     * Mode.
     * Planning mode (`MeshOnly`, etc.).
   * Actions:
     * "Plan & execute now" (if allowed).
     * "Pause/hold".
   * Require a confirmation for "execute" with a note summarizing potential network impact.

3. **Planner explanation view**
   * For a given planned track:
     * Show the plan: which backends, why, what the constraints are.
   * Useful for debugging and making it clear exactly how much work will be done.

4. **Settings / Policy view**
   * Clearly shows:
     * Per-backend caps.
     * Modes.
     * Soulseek limits.
   * This doubles as documentation and makes misconfiguration more obvious.

**Security considerations:**
* Any UI that sits on top of the HTTP gateway must:
  * Use the gateway auth/CSRF correctly.
  * Not expose endpoints beyond those intended (no generic "run arbitrary service calls" console by default).
* UI must not automatically:
  * enqueue thousands of intents without confirmation; nor
  * schedule automatic executions without clear, opt-in configuration.

---

## 15. Implementation Phases

See `VIRTUALSOULFIND-V2-TASKS.md` for detailed task breakdown.

### Phase 1: Foundation (V2-P1)
- Data model and schema
- Backend interface abstractions
- Basic catalogue store

### Phase 2: Intent & Planning (V2-P2)
- Intent queue
- Multi-source planner
- Source registry

### Phase 3: Verification & Matching (V2-P3)
- Match engine
- Verified copy registry
- Canonical naming

### Phase 4: Backend Implementations (V2-P4)
- Soulseek backend (with H-08 caps)
- Mesh DHT/overlay backend
- Local library backend
- Optional: Torrent/HTTP/LAN backends

### Phase 5: Integration (V2-P5)
- Mesh service facade
- HTTP gateway endpoints
- Work budget integration (H-02)

### Phase 6: Advanced Features (V2-P6)
- Library reconciliation
- Smart prioritization
- Gap analysis
- Quality upgrades

---

## Multi-Domain Model Overview

VirtualSoulfind V2 is explicitly **multi-domain**: it manages content across multiple media domains with a shared brain but domain-specific rules.

Supported domains (initial set):

- `Music`
- `GenericFile` (baseline, non-semantic)
- `Book`
- `Movie`
- `Tv`

Each domain shares:

- A common ID scheme:
  - `ContentWorkId` – logical work (album, book, series, movie, etc.).
  - `ContentItemId` – specific item/copy (a specific release, file, or edition).
- Common interfaces:
  - `IContentWork` – domain-neutral view of a work.
  - `IContentItem` – domain-neutral view of an item.
  - `IContentDomainProvider` – base interface with domain-specific subtypes.

Domain-specific providers implement the details:

- `IMusicContentDomainProvider`
- `IBookContentDomainProvider`
- `IMovieContentDomainProvider`
- `ITvContentDomainProvider`
- (plus a minimalist provider for `GenericFile`)

---

### Domain Contracts

Each domain provider MUST implement:

- Identity mapping:
  - Map external IDs (MBID, ISBN, TMDB, etc.) → `ContentWorkId` / `ContentItemId`.
  - Map local metadata (e.g., tags, names, durations) → best-effort work/item match.
- Metadata enrichment:
  - Provide canonical "work" and "item" records with:
    - Title/names.
    - Creator(s)/authors/artists.
    - Year and/or release details.
    - Domain-specific fields (runtime, series index, formats, etc.).
- Verification:
  - Given a local file, determine whether it is a valid representation of a specific `ContentItemId`.
  - Use domain-appropriate checks (hashes, runtime, page count, codec, etc.).
- Quality assessment:
  - Produce a domain-specific "quality" struct that can be used by:
    - Planner ("is this good enough?").
    - Upgrade logic ("can we do better?").

---

## Music Domain

The Music domain is the most mature and serves as the reference for other domains.

### Identity

- Works:
  - Albums, EPs, singles, compilations, or other releases.
  - Identified primarily via external IDs (MusicBrainz, etc.) and title/artist/year combinations.
- Items:
  - Tracks (recordings) associated with a work.
  - Identified via:
    - Track index/position, duration, and external IDs.
    - (Where available) Chromaprint fingerprints.

### Providers

- `IMusicContentDomainProvider` is responsible for:

  - Mapping from:
    - MusicBrainz IDs → `ContentWorkId` / `ContentItemId`.
    - Local library tags (artist, album, track names) → probable work/item.
    - Chromaprint fingerprints → track identity.

  - Producing:
    - `MusicWork` – implementing `IContentWork`.
    - `MusicItem` – implementing `IContentItem`.

  - Providing matching utilities:
    - `TryMatchTrackByFingerprintAsync(LocalFileMetadata + fingerprint)`.
    - `TryMatchTrackByTagsAsync(LocalFileMetadata + tags)`.

### Verification and Quality

- Verification:
  - Check:
    - Hashes.
    - Duration tolerance.
    - Fingerprint (Chromaprint) where available.

- Quality scoring:
  - Consider:
    - Codec (lossless vs lossy).
    - Bitrate bracket.
    - Sample rate / bit depth.
  - Output `MusicCopyQuality` with normalized scoring that can be compared across items for the same work.

---

## Video Domain (Movies & TV)

The Video domain is split into Movies and TV, but both are "video" with overlapping concerns.

### Identity

- Movie work:
  - A film identified by:
    - External ID (e.g., TMDB, IMDB-like ID).
    - Title + year.
- Movie item:
  - A particular encoding or cut of a movie:
    - Edition, resolution, codec, audio layout, etc.

- TV work:
  - A TV show (series-level identity).
  - Seasons as structured sub-works.
- Episode item:
  - An episode identified by:
    - Series ID + season + episode index (and/or absolute index).
    - External IDs (episode IDs from TMDB/TVDB/etc.).

### Providers

- `IMovieContentDomainProvider`:
  - Maps external movie IDs and (title + year) → `ContentWorkId` for movies.
  - Resolves local video files to movie items using filename/NFO metadata and API lookup.
- `ITvContentDomainProvider`:
  - Maps series IDs, season/episode numbers → `ContentWorkId`/`ContentItemId` for episodes.
  - Resolves local episode files using filename patterns and NFO/metadata.

Both providers:

- Expose `MovieWork`/`MovieItem` and `TvShowWork`/`EpisodeItem`, all implementing `IContentWork`/`IContentItem`.

### Verification and Quality

Verification:

- Hash-based verification for known-good copies.
- Runtime-based sanity check (within configured tolerance per work/episode).
- Optional structural checks (e.g., container/codec sanity).

Quality scoring (`VideoCopyQuality`):

- Resolution (4K, 1080p, 720p, etc.).
- Video codec (HEVC/AV1 vs H.264, etc.).
- HDR vs SDR (if detectable).
- Audio layout (stereo vs multichannel).
- Bitrate bracket (approximate, not exact).

Planner uses `VideoCopyQuality` to:

- Decide if the local copy meets the user's profile.
- Suggest upgrades where a higher-quality copy exists.

---

## Book Domain

The Book domain covers ebooks and similar textual content.

### Identity

- Work:
  - A logical book title (often mapped to a canonical edition).
  - Identified by:
    - ISBN (if available).
    - Title + author (+ year).
- Item:
  - A specific file/edition:
    - Format (EPUB, PDF, MOBI, etc.).
    - Publisher, publication year.
    - Language.
    - Page count/length.

### Provider

- `IBookContentDomainProvider`:

  - Maps:
    - ISBN and Open Library IDs → `ContentWorkId` / `ContentItemId`.
    - Local file metadata (title, authors, ISBN extracted from EPUB/PDF) → best work/item match.

  - Produces:
    - `BookWork` – `IContentWork`.
    - `BookItem` – `IContentItem`.

  - Provides methods such as:
    - `TryMatchBookByIsbnAsync`.
    - `TryMatchBookByTitleAuthorAsync`.
    - `TryMatchBookByLocalMetadataAsync`.

### Verification and Quality

Verification:

- Hash match for known-good editions.
- Structural validation:
  - Valid EPUB/PDF structure.
  - Reasonable page count/size vs known metadata.

Quality scoring (`BookCopyQuality`):

- Format preference:
  - Reflowable formats (EPUB, etc.) > fixed-layout (PDF, scanned images).
- DRM:
  - Non-DRM preferred over DRM where detectable.
- Metadata completeness:
  - Presence of TOC, proper metadata tags, etc.

Planner uses `BookCopyQuality` to:

- Offer upgrade suggestions (e.g., "replace low-quality PDF with high-quality EPUB").
- Decide whether a given copy is "good enough" for user preferences.

---

## GenericFile Domain

The GenericFile domain is intentionally minimal and non-semantic.

- Purpose:
  - Provide a domain for arbitrary files where we don't (yet) have a richer domain model.
- Identity:
  - Work: optional grouping (e.g., folder, tag, or arbitrary grouping).
  - Item: a file identified primarily by:
    - Hash (SHA256 or equivalent).
    - Size, name (secondary).

The GenericFile domain MUST:

- Not rely on Soulseek backend.
- Rely only on mesh/torrent/HTTP/local.
- Be used cautiously, without any semantic assumptions about content type.

---

## Planner and Backends in a Multi-Domain World

The planner is responsible for:

- Receiving intents that specify:
  - `ContentDomain`.
  - Work/item targets (work IDs, item IDs, or selection criteria).
- Selecting:
  - Appropriate domain provider.
  - Allowed backends for that domain.
  - Sources that pass moderation (MCP) and reputation checks.

Backend rules per domain:

- Music:
  - May use: Soulseek, mesh, torrent, HTTP, local.
- Video (Movie/Tv):
  - May use: mesh, torrent, HTTP, local.
  - MUST NOT use Soulseek.
- Book:
  - May use: mesh, torrent, HTTP, local.
  - MUST NOT use Soulseek.
- GenericFile:
  - May use: mesh, torrent, HTTP, local.
  - MUST NOT use Soulseek.

Planner MUST:

- Enforce domain-specific backend rules.
- Consult MCP before:
  - Advertising sources.
  - Accepting external sources.
  - Serving data via content relay.

---

This design gives you a coherent architecture that:

* Works with the multi-source-swarm/service-fabric work already completed.
* Treats VirtualSoulfind as the hub for catalogue, planning, and verification.
* Shifts "turbo" behavior firmly onto mesh DHT/overlay/BT and away from Soulseek, by design.
* Maintains backwards compatibility and Soulseek-friendly defaults.
* **Supports multi-domain content (Music, Books, Movies, TV, GenericFile) with first-class domain abstractions.**
