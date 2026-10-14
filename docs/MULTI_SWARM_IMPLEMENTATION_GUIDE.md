# Multi-Swarm + MBID Intelligence Implementation Guide

> **DHT terminology**: public BitTorrent DHT is used for mesh endpoint
> rendezvous only. MBID/content/service metadata belongs to the slskdN mesh
> DHT and is exchanged over the mesh overlay; chunk bytes also use the overlay.
> See [DHT and Mesh Architecture](./DHT_MESH_ARCHITECTURE.md).

> **Status**: Implementation Backlog  
> **Branch**: `experimental/brainz`  
> **Last Updated**: 2025-12-09

This document provides concrete GitHub issues for implementing the multi-swarm + MBID intelligence features outlined in [MULTI_SWARM_ROADMAP.md](archive/duplicates/MULTI_SWARM_ROADMAP.md).

Each issue is designed to be copy-pasted directly into `snapetech-org/slskdN` as a backlog item.

---

## Table of Contents

- [Phase 1: Library Intelligence](#phase-1-library-intelligence)
  - [Feature A: Canonical-Edition Scoring](#feature-a--canonical-edition-scoring)
  - [Feature B: Collection Doctor / Library Health](#feature-b--collection-doctor--library-health)
  - [Feature C: RTT + Throughput-Aware Swarm Scheduler](#feature-c--rtt--throughput-aware-swarm-scheduler)
  - [Feature D: Rescue Mode for Stalled Transfers](#feature-d--rescue-mode-for-stalled-transfers)
- [Phase 2: Discovery & Fairness](#phase-2-discovery--fairness)
  - [Feature E: Release-Graph Guided Discovery](#feature-e--release-graph-guided-discovery)
  - [Feature F: Label Crate Mode](#feature-f--label-crate-mode)
  - [Feature G: Local-Only Peer Reputation](#feature-g--local-only-peer-reputation)
  - [Feature H: Mesh-Level Fairness Governor](#feature-h--mesh-level-fairness-governor)
- [Phase 3: UX & Observability](#phase-3-ux--observability)
  - [Feature I: Download Job Manifests](#feature-i--download-job-manifests)
  - [Feature J: Session Traces / Swarm Debug Logs](#feature-j--session-traces--swarm-debug-logs)
- [Phase 4: Advanced Features](#phase-4-advanced-features)
  - [Feature K: Warm Cache Overlay Nodes](#feature-k--warm-cache-overlay-nodes)
  - [Feature L: Playback-Aware Swarming](#feature-l--playback-aware-swarming)

---

## Phase 1: Library Intelligence

### Feature A – Canonical-Edition Scoring

#### Issue A1 – Implement `AudioVariant` quality scoring and transcode detection

**Title:** `feat: add quality_score and transcode detection to AudioVariant`

**Labels:** `type:enhancement`, `component:hashdb`, `priority:p1`, `phase:1`

**Description:**

Introduce a `quality_score` and `transcode_suspect` signal for each local audio file variant. This will be used as the basis for "canonical edition" selection and later mesh aggregation.

**Acceptance Criteria:**

* There is a clearly defined `AudioVariant` representation in code (or equivalent metadata record) that includes at minimum:
  * `codec`, `container`, `bitrate`, `sample_rate`, `bit_depth`, `channels`, `duration_ms`, `file_size_bytes`.
* A scoring function exists, e.g. `ComputeLocalQualityScore(AudioVariant variant)` that:
  * Returns a float in `[0.0, 1.0]`.
  * Rewards:
    * Lossless over lossy.
    * "Sane" sample rates (e.g. 44.1/48 kHz for most material).
    * No clipping / acceptable loudness range (if DR/loudness metrics are available).
  * Penalises:
    * Suspected transcodes (e.g. low spectral content vs reported bitrate, or lossy > lossless in chain).
    * Weird sample rates / obvious upsampled material.
* A boolean `transcode_suspect` is computed using reasonable heuristics (it is OK to start simple).
* New fields are persisted in the metadata store / DB.
* A CLI or debug command exists to:
  * Recompute quality scores for a given path/library.
  * Print a small sample of files with their scores and `transcode_suspect` flags for manual verification.

**Implementation Notes:**
- Extend `FlacInventory` or create new `AudioVariant` table
- Use existing FLAC STREAMINFO parsing from `HashDb/FlacStreamInfo.cs`
- Integrate with Chromaprint for fingerprinting (Phase 1 prerequisite)

---

#### Issue A2 – Aggregate canonical variant stats per recording/release

**Title:** `feat: aggregate canonical variant stats per MB recording/release`

**Labels:** `type:enhancement`, `component:hashdb`, `priority:p1`, `phase:1`

**Description:**

Aggregate quality information per `(MB Recording ID, codec profile)` and optionally per `(MB Release ID, Recording ID)` to support "canonical edition" selection.

**Acceptance Criteria:**

* A background job or on-demand task:
  * Iterates over local AudioVariants that have MB Recording IDs (and optionally MB Release IDs).
  * Computes per-key aggregates:
    * Count of variants.
    * Average `quality_score`.
    * Count/percentage of `transcode_suspect`.
    * Distinct codecs/bitrate buckets.
* Aggregates are stored in a dedicated structure/table (e.g. `canonical_stats`), indexable by:
  * MB Recording ID.
  * MB Release ID + track number (if available).
* A query function exists:
  * `GetCanonicalVariantCandidates(MbRecordingId, profileConstraints)` that returns a list of variant IDs ordered by "canonicality" (quality_score + stats).
* Basic CLI/debug:
  * Given MB Recording ID or MB Release ID, prints a human-readable summary of:
    * Canonical variant candidate(s).
    * Stats that led to that conclusion.

**Implementation Notes:**
- Extend `FingerprintObservations` table (already defined in HASHDB_SCHEMA.md)
- Use `canonicality_score` field
- Integrate with mesh sync for peer observations

---

#### Issue A3 – Use canonical variant selection in multi-swarm download decisions

**Title:** `feat: prefer canonical variants in multi-swarm downloads`

**Labels:** `type:enhancement`, `component:transfers`, `priority:p1`, `phase:1`

**Description:**

Integrate canonical scoring into the multi-swarm engine such that when multiple variants of a recording are available, the engine prefers canonical variants by default.

**Acceptance Criteria:**

* When initiating a multi-swarm job for a track/recording:
  * The planner queries canonical stats and assigns a target "variant profile" (lossless/codec/bitrate).
* Source selection:
  * If multiple peers offer different variants of the same MB Recording:
    * The engine prefers peers whose offered variant matches or exceeds the canonical profile.
* When a local library already contains multiple variants:
  * The engine updates or annotates the job so that:
    * It will only download a new variant if it is more canonical (higher score) than what already exists.
* There is a config option to:
  * Enable/disable "canonical preference".
  * Optionally prefer "original master" style (e.g. non-remastered) if that's encoded in metadata later.

**Implementation Notes:**
- Modify `MultiSourceDownloadJob` to include canonical profile constraints
- Extend `SourceDiscoveryService` to query canonical stats
- Add config section: `multi_source.prefer_canonical: true`

---

### Feature B – Collection Doctor / Library Health

#### Issue B1 – Implement library scan for MBID/quality-based issues

**Title:** `feat: add Collection Doctor scan for library health`

**Labels:** `type:enhancement`, `component:library-health`, `priority:p1`, `phase:1`

**Description:**

Add a background or on-demand job that inspects the existing library and flags possible problems based on MBID mappings and canonical stats.

**Acceptance Criteria:**

* A job (CLI and/or UI-triggered) walks configured library paths and for each file:
  * Resolves its MB Recording and Release IDs (if known).
  * Fetches canonical stats for the recording.
* The job produces a structured list of issues, at minimum:
  * `SuspectedTranscode(file, reason)`
  * `NonCanonicalVariant(file, betterVariantExists)`
  * `TrackNotInTaggedRelease(file, taggedReleaseId, actualReleaseIdGuess?)`
  * `MissingTrackInRelease(releaseId, trackNumber)` (per MB tracklist vs local files).
* Results are persisted (e.g. in a `library_health_issues` table or equivalent) with:
  * Issue type, severity, file path / MBID, timestamps.
* There is a CLI command:
  * `slskdn doctor scan` that runs the scan and prints a summary:
    * Number of suspected transcodes.
    * Number of non-canonical variants.
    * Number of incomplete releases.

**Implementation Notes:**
- New service: `src/slskd/LibraryHealth/LibraryHealthService.cs`
- New table: `LibraryHealthIssues` in HashDb
- Scan uses `data.shared.directories` from config

---

#### Issue B2 – Add UI / API surface for Library Health overview

**Title:** `feat: UI for Collection Doctor library health summary`

**Labels:** `type:enhancement`, `component:ui`, `component:api`, `priority:p1`, `phase:1`

**Description:**

Expose the library health information in the UI or API so users can see and act on issues.

**Acceptance Criteria:**

* A Library Health view (web UI) or API endpoint:
  * Returns aggregated counts per issue type (e.g. `SuspectedTranscode: 143`).
  * Allows drilling down to per-issue lists:
    * Includes file path, artist, album, track, MB IDs, and brief reason.
* Sorting/filtering available at minimum by:
  * Issue type.
  * Artist.
  * Release.
* There is a way to mark issues as:
  * "Ignored" (user doesn't care).
  * "Resolved" (after a fix).
* Resolved/ignored issues do not show up in the default overview but remain persisted for audit/debugging.

**Implementation Notes:**
- New controller: `src/slskd/LibraryHealth/API/LibraryHealthController.cs`
- New UI component: `src/web/src/components/System/LibraryHealth/index.jsx`
- API lib: `src/web/src/lib/libraryHealth.js`

---

#### Issue B3 – One-click "Fix via multi-swarm" from library health

**Title:** `feat: add "Fix via multi-swarm" actions from Collection Doctor`

**Labels:** `type:enhancement`, `component:library-health`, `component:transfers`, `priority:p1`, `phase:1`

**Description:**

Allow users to trigger multi-swarm MBID-based download jobs directly from identified health issues.

**Acceptance Criteria:**

* For a `MissingTrackInRelease` issue:
  * The UI exposes an action:
    * "Download missing track(s) via multi-swarm."
  * Action spawns an MB Release job (if not already existing) targeting the missing tracks, with reasonable defaults:
    * Prefer canonical lossless variants.
    * Use overlay if enabled.
* For a `SuspectedTranscode` / `NonCanonicalVariant` issue:
  * UI allows:
    * "Replace with canonical variant" which:
      * Spawns a job for the relevant MB Recording/Release.
      * Uses canonical scoring to fetch a better variant.
    * After job completion:
      * Optionally mark original file for archive or deletion (configurable).
* Jobs created via these actions are:
  * Linked back to the originating issues for traceability.
  * Automatically marked as "in progress" / "fixed" when the job completes successfully.

**Implementation Notes:**
- Extend `AlbumDownloadJob` to include `source_issue_id` field
- Add job completion hooks to update `LibraryHealthIssues` table
- UI buttons use Semantic UI `Popup` for tooltips (per convention)

---

### Feature C – RTT + Throughput-Aware Swarm Scheduler

#### Issue C1 – Track per-peer RTT, throughput, and error metrics

**Title:** `feat: track overlay peer RTT/throughput/error stats for swarm scheduling`

**Labels:** `type:enhancement`, `component:mesh`, `component:transfers`, `priority:p1`, `phase:1`

**Description:**

Collect and store basic performance metrics for each mesh peer to support improved chunk scheduling.

**Acceptance Criteria:**

* For each overlay peer, we maintain metrics including:
  * Average RTT for chunk responses.
  * Average throughput (bytes/sec) over a sliding time window.
  * Error count and timeout count for chunk requests.
* Metrics are updated:
  * On every `chunk_request` / `chunk_response` pair.
  * On any error/timeout related to chunk transfers.
* Metrics have decay (e.g. exponential moving average) to avoid being dominated by very old data.
* A debug/CLI command exists:
  * `slskdn swarm stats peers` showing:
    * Peer ID, RTT, throughput, error/timeout rates.

**Implementation Notes:**
- Extend `Peers` table with metrics: `avg_rtt_ms`, `avg_throughput_bps`, `error_count`, `timeout_count`
- Update metrics in chunk response handlers
- Exponential moving average: `new_avg = (alpha * new_sample) + ((1 - alpha) * old_avg)` where `alpha = 0.1`

---

#### Issue C2 – Implement cost-based peer ranking for chunk assignment

**Title:** `feat: add cost-based peer ranking strategy for chunk selection`

**Labels:** `type:enhancement`, `component:transfers`, `priority:p1`, `phase:1`

**Description:**

Introduce a cost function using the per-peer metrics to rank peers for chunk assignment.

**Acceptance Criteria:**

* A configurable cost function is implemented, e.g.:
  * `cost(peer) = alpha / throughput + beta * error_rate + gamma * timeout_rate`
* The function is:
  * Parameterised via config (alpha, beta, gamma).
  * Unit-tested with simple scenarios (fast vs slow vs error-prone peers).
* An API is available to the swarm engine:
  * `RankPeersForChunk(recordingId, candidatePeers) -> ordered list`.
* If no metrics are available for a peer (cold start):
  * A default cost/priority is used that does not immediately starve them but doesn't dominate either.

**Implementation Notes:**
- Default constants: `alpha = 1000, beta = 0.5, gamma = 0.3`
- Config section: `multi_source.scheduler.cost_alpha`, etc.
- Unit tests: `tests/slskd.Tests.Unit/Transfers/MultiSource/PeerRankingTests.cs`

---

#### Issue C3 – Integrate cost-based scheduling into multi-swarm engine

**Title:** `feat: integrate cost-based peer ranking into multi-swarm chunk scheduler`

**Labels:** `type:enhancement`, `component:transfers`, `priority:p1`, `phase:1`

**Description:**

Use the cost-based peer ranking to assign chunk downloads across peers for each track, so that faster and more reliable peers handle more critical chunks.

**Acceptance Criteria:**

* The multi-swarm engine:
  * Uses the ranking function when deciding which peer should serve a given chunk or set of chunks.
* Priority behaviour:
  * High-priority chunks (end of file; or those critical for completion) are preferentially assigned to lower-cost peers.
  * Lower-priority chunks can be assigned to slower/higher-cost peers.
* When a peer's metric degrades during a job (e.g. timeouts spike):
  * New chunks are gradually shifted away from that peer without abruptly killing the transfer unless necessary.
* A config exists to:
  * Enable/disable "cost-based scheduling".
  * Set thresholds or modes (e.g. "aggressive optimisation" vs "conservative").

**Implementation Notes:**
- Modify `MultiSourceDownloadScheduler.cs` to use `RankPeersForChunk`
- Rebalance every 10 chunks or 30 seconds (configurable)
- Config: `multi_source.scheduler.enabled: true`, `multi_source.scheduler.mode: balanced`

---

### Feature D – Rescue Mode for Stalled Transfers

#### Issue D1 – Detect underperforming Soulseek transfers

**Title:** `feat: detect stalled/underperforming Soulseek transfers for rescue`

**Labels:** `type:enhancement`, `component:transfers`, `priority:p1`, `phase:1`

**Description:**

Detect Soulseek transfers that are stalled or too slow and mark them as candidates for rescue via overlay/multi-swarm.

**Acceptance Criteria:**

* For each Soulseek transfer, track:
  * Time in `queued` state.
  * Active transfer speed (bytes/sec).
* Configurable thresholds:
  * `max_queue_time_before_rescue` (e.g. 10–30 min).
  * `min_active_speed_for_rescue` (e.g. < 5–10 KB/s sustained over N seconds).
* If a transfer exceeds these thresholds:
  * Mark it as `underperforming`.
  * Emit a log/debug entry indicating that the track is eligible for rescue.
* A CLI or debug view:
  * Can list underperforming transfers and the reason (queue vs speed).

**Implementation Notes:**
- New service: `src/slskd/Transfers/Rescue/StallDetector.cs`
- Track transfer state in `DownloadTracker`
- Config: `rescue.enabled: true`, `rescue.max_queue_minutes: 30`, `rescue.min_speed_kbps: 10`

---

#### Issue D2 – Implement overlay-based rescue for underperforming transfers

**Title:** `feat: overlay rescue for underperforming Soulseek transfers`

**Labels:** `type:enhancement`, `component:transfers`, `component:mesh`, `priority:p1`, `phase:1`

**Description:**

When a Soulseek transfer is underperforming, use the mesh overlay to fetch missing chunks from other slskdn peers while keeping the original Soulseek transfer alive.

**Acceptance Criteria:**

* For an `underperforming` transfer:
  * Resolve MB Recording ID / fingerprint for the target track.
  * Query the existing mesh (via `fingerprint_bundle_advert` / descriptors) to find peers that:
    * Have the same recording.
    * Offer acceptable quality/canonical variants.
* Spawn overlay transfers:
  * Use the multi-swarm engine to request missing ranges via overlay (`chunk_request`/`chunk_response`).
  * Keep the original Soulseek transfer active but with lower priority; if it catches up, its bytes are still accepted.
* Correctness:
  * Multi-swarm piece map correctly merges data from:
    * The original Soulseek stream.
    * Overlay peers.
* At no point is the job considered valid if:
  * No Soulseek source exists at all and no verifiable MB/fingerprint match can be established (configurable, but default should be conservative).

**Implementation Notes:**
- New service: `src/slskd/Transfers/Rescue/RescueService.cs`
- Subscribe to `TransferStalledEvent`
- Query the mesh DHT for the MBID: `sha1(b"slskdn-mb-v1:" + mb_recording_id)`; this lookup is carried over the mesh overlay, not the public BitTorrent DHT
- Integrate with existing `MultiSourceDownloadJob`

---

#### Issue D3 – Guardrails to keep Soulseek as origin / authority in rescue mode

**Title:** `feat: add guardrails to ensure rescue mode keeps Soulseek as origin`

**Labels:** `type:enhancement`, `component:transfers`, `priority:p1`, `phase:1`

**Description:**

Enforce explicit rules so that rescue mode never causes slskdn to become a purely overlay-based network and Soulseek remains the origin/authority.

**Acceptance Criteria:**

* Configurable but safe defaults enforce:
  * At least one active or attempted Soulseek source per job, unless explicitly overridden by config.
  * A maximum ratio of overlay bytes to Soulseek bytes per job (e.g. not more than X:1).
* If no Soulseek source can be found or maintained:
  * By default, the job:
    * Logs a warning and refuses to proceed as overlay-only,
    * unless an explicit "allow_overlay_only_if_verified_by_fingerprint" mode is enabled.
* Rescue mode never:
  * Initiates overlay transfers for recordings that do not exist in the Soulseek graph as far as slskdn can see (e.g. must have been seen at least once via search/transfer).
* There is a config section documenting:
  * Rescue mode behaviour.
  * The invariants that keep Soulseek as the canonical network.

**Implementation Notes:**
- Config: `rescue.require_soulseek_source: true`, `rescue.max_overlay_ratio: 2.0`
- Validation in `RescueService` before spawning overlay jobs
- Detailed logging for guardrail violations

---

## Phase 2: Discovery & Fairness

### Feature E – Release-Graph Guided Discovery

#### Issue E1 – Add MusicBrainz release-graph fetch and local cache

**Title:** `feat: fetch and cache MusicBrainz release graph for artists`

**Labels:** `type:enhancement`, `component:musicbrainz`, `priority:p2`, `phase:2`

**Description:**

Add the ability to query MusicBrainz for an artist's release graph and cache that information locally. This graph will be used to generate discography jobs (core discography, extended, etc.).

**Acceptance Criteria:**

* Given an MB Artist ID:
  * The system can fetch:
    * Release Groups for that artist (with type: Album, Single, EP, Compilation, Live, etc.).
    * Releases within each group (with Release IDs, dates, countries, labels).
* Results are cached locally in a new or existing MB-related store:
  * `artists`, `release_groups`, `releases` tables or equivalent models.
* There is a simple API/CLI:
  * `slskdn mb artist-graph <mb_artist_id>` that:
    * Fetches/refreshes the graph.
    * Prints a summary of:
      * Number of release groups.
      * Number of releases by type (albums, EPs, singles, etc.).
* Caching layer has:
  * TTL or versioning so re-fetch is possible (e.g. manual or after X days).

**Implementation Notes:**
- New service: `src/slskd/MusicBrainz/MusicBrainzGraphService.cs`
- New tables: `Artists`, `ReleaseGroups`, `Releases` in HashDb
- Respect MusicBrainz rate limit: 1 req/sec
- Cache TTL: 30 days

---

#### Issue E2 – Model discography "profiles" (core vs extended)

**Title:** `feat: define discography profiles (core, extended, all) per artist`

**Labels:** `type:enhancement`, `component:musicbrainz`, `priority:p2`, `phase:2`

**Description:**

Define and store discography profiles based on the MusicBrainz release graph, so that users can request "core discography" vs "extended discography" jobs.

**Acceptance Criteria:**

* For an MB Artist ID, discography profiles are derived from the cached graph:
  * `core_discography`:
    * All Release Groups of type "Album" (main studio albums).
    * Optionally excluding compilations/live by default.
  * `extended_discography`:
    * Core + selected EPs, key live releases, or well-known compilations.
  * `all_releases`:
    * Everything for that artist, grouped by type.
* Profiles are represented as:
  * A list of MB Release IDs + metadata (title, year, type).
  * Optionally a "weight" or "recommended" flag for each release.
* A CLI/API exists:
  * `slskdn mb discography <mb_artist_id> --profile core|extended|all`
    * Prints a sorted list of MB Releases (title, year, type) in that profile.

**Implementation Notes:**
- New model: `src/slskd/MusicBrainz/Models/DiscographyProfile.cs`
- Profile generation logic in `MusicBrainzGraphService`
- Config filters: `discography.core.exclude_compilations: true`, `discography.core.exclude_live: true`

---

#### Issue E3 – Create discography-based multi-swarm jobs

**Title:** `feat: create multi-swarm MBID jobs from discography profiles`

**Labels:** `type:enhancement`, `component:musicbrainz`, `component:transfers`, `priority:p2`, `phase:2`

**Description:**

Allow users to generate multi-swarm jobs for entire artist discographies using the MB discography profiles.

**Acceptance Criteria:**

* A new UI/API entry point:
  * "Create discography job" / `POST /jobs/discography` that accepts:
    * `mb_artist_id`
    * `profile` (`core`, `extended`, `all`)
    * Optional constraints (preferred codecs, lossless-only, canonical-only).
* The system:
  * Resolves the discography profile to a list of MB Release IDs.
  * Creates one MB Release multi-swarm job per Release:
    * Each job uses the existing MBID-based pipeline (tracklists, canonical selection).
    * Jobs are grouped under a parent `discography_job_id`.
* Job status:
  * There is a way to query:
    * Overall progress for the discography (e.g. "4/7 releases complete").
    * Per-release progress within that job.

**Implementation Notes:**
- New controller: `src/slskd/MusicBrainz/API/DiscographyController.cs`
- New model: `DiscographyDownloadJob` wrapping multiple `AlbumDownloadJob`
- UI component: `src/web/src/components/Discography/DiscographyBuilder.jsx`

---

### Feature F – Label Crate Mode

#### Issue F1 – Aggregate label presence from mesh MBID data

**Title:** `feat: aggregate label presence in mesh from MBID metadata`

**Labels:** `type:enhancement`, `component:mesh`, `component:discovery`, `priority:p2`, `phase:2`

**Description:**

Aggregate label usage based on MB/Discogs IDs from peers' adverts, so we can identify labels that are heavily represented in the current mesh neighbourhood.

**Acceptance Criteria:**

* When receiving `mbid_swarm_descriptor` or similar metadata from peers:
  * Extract label names and MB Label IDs (if present) for each release.
* Maintain a local summary structure:
  * For each label:
    * Number of distinct MB Releases seen.
    * Number of distinct artists.
    * Approximate "popularity" score (e.g. based on number of peers or adverts mentioning the label).
* Provide a CLI/API:
  * `slskdn mesh labels`:
    * Lists top labels by "popularity" in the current mesh view.
    * Prints counts of releases/artists per label.
* All aggregation remains local; no label statistics are re-broadcast to the network.

**Implementation Notes:**
- New service: `src/slskd/Discovery/LabelCatalogService.cs`
- New table: `LabelPopularity` in HashDb
- Update from `fingerprint_bundle_advert` messages
- Popularity decay: weekly half-life

---

#### Issue F2 – UI/API for label crate creation

**Title:** `feat: create label crate multi-swarm jobs from label aggregates`

**Labels:** `type:enhancement`, `component:ui`, `component:discovery`, `priority:p2`, `phase:2`

**Description:**

Allow users to select a label and create a "label crate" job that queues multi-swarm downloads for a subset of that label's popular releases.

**Acceptance Criteria:**

* UI:
  * A view that lists labels detected in the mesh:
    * Shows label name, number of releases seen, approximate popularity.
  * For a selected label:
    * Show top N releases (configurable) with title, artist, year.
* API:
  * `POST /jobs/label-crate` with:
    * `label_id` or label name,
    * `limit_releases` (e.g. 10, 20),
    * Constraints (preferred codecs, lossless-only, canonical-only).
* Job behaviour:
  * For each chosen release:
    * Create a standard MBID-based multi-swarm job.
  * Track them under a parent `label_crate_job_id` similar to discography jobs.
* Progress:
  * Expose per-label crate summary:
    * "Downloaded 8/10 releases for Label X."

**Implementation Notes:**
- New controller: `src/slskd/Discovery/API/LabelCatalogController.cs`
- UI component: `src/web/src/components/Discovery/LabelBrowser.jsx`
- Job model: `LabelCrateDownloadJob`

---

### Feature G – Local-Only Peer Reputation

#### Issue G1 – Collect base metrics for peer reputation

**Title:** `feat: collect base metrics per mesh peer for local reputation`

**Labels:** `type:enhancement`, `component:mesh`, `priority:p2`, `phase:2`

**Description:**

Collect core metrics per peer that will be used to derive a local-only reputation score (no sharing).

**Acceptance Criteria:**

* For each mesh peer, track:
  * `successful_chunks` (overlay).
  * `failed_chunks` (with a reason: error, hash mismatch, etc.).
  * `timeouts` for requested chunks.
  * `cancelled_by_peer` events (peer-initiated cancellations).
* Metrics are persisted in a small local store keyed by peer ID:
  * Survive restarts.
  * Decay over time (e.g. exponential decay or periodic halving).
* A debug CLI:
  * `slskdn mesh peers-metrics`:
    * Shows raw metrics per peer.

**Implementation Notes:**
- Extend `Peers` table with: `successful_chunks`, `failed_chunks`, `timeouts`, `cancelled_by_peer`
- Update on every `chunk_response` and error
- Weekly decay: `metric *= 0.5` every 7 days

---

#### Issue G2 – Compute and store a local reputation score

**Title:** `feat: compute local-only reputation score per mesh peer`

**Labels:** `type:enhancement`, `component:mesh`, `priority:p2`, `phase:2`

**Description:**

Compute a bounded reputation score per peer based purely on local observations, and store it for use by schedulers and selection logic.

**Acceptance Criteria:**

* A reputation function:
  * `ComputePeerReputation(metrics) -> float 0..1`
  * Example:
    * Start from 1.0.
    * Penalise:
      * High failure / timeout ratios.
      * Frequent corrupt chunks.
    * Slightly reward:
      * High volume of successful chunks over time.
* Reputation score is:
  * Stored per peer.
  * Updated incrementally as new events occur.
  * Decayed over time so old behaviour doesn't dominate.
* A CLI:
  * `slskdn mesh peers-reputation`:
    * Shows `peer_id`, `reputation_score`, and a brief reason summary (e.g. "high timeouts, low throughput").

**Implementation Notes:**
- Add `local_reputation` field to `Peers` table
- Formula: `reputation = 1.0 - (0.3 * timeout_rate + 0.5 * corruption_rate + 0.2 * failure_rate)`
- Update on every chunk validation

---

#### Issue G3 – Integrate reputation into peer and source selection

**Title:** `feat: use local reputation in peer/source selection`

**Labels:** `type:enhancement`, `component:transfers`, `priority:p2`, `phase:2`

**Description:**

Use the reputation score to influence swarm scheduling and source selection, lowering the probability of assigning chunks to bad or flaky peers.

**Acceptance Criteria:**

* For multi-swarm peer selection:
  * Reputation is factored into the cost calculation or ranking:
    * High-reputation peers are preferred for critical chunks and initial assignments.
    * Low-reputation peers are:
      * Down-weighted, or
      * Used only when necessary (e.g. few alternatives).
* For rescue mode and general source selection:
  * Reputation is used to break ties between peers with similar performance metrics.
* There is a configurable threshold:
  * Below which peers are effectively "quarantined":
    * Only used under "desperate" conditions or not at all.
* All reputation usage remains local to the node; there is no sharing or broadcasting of scores.

**Implementation Notes:**
- Modify cost function: `cost(peer) += (1.0 - reputation) * reputation_weight`
- Config: `multi_source.scheduler.reputation_weight: 0.4`, `multi_source.scheduler.min_reputation: 0.3`
- Never broadcast reputation (privacy-preserving)

---

### Feature H – Mesh-Level Fairness Governor

#### Issue H1 – Track overlay vs Soulseek upload/download volumes

**Title:** `feat: track overlay vs Soulseek traffic volumes for fairness`

**Labels:** `type:enhancement`, `component:fairness`, `priority:p2`, `phase:2`

**Description:**

Track the amount of data uploaded/down­loaded over the overlay vs Soulseek per node, to support fairness policies.

**Acceptance Criteria:**

* Global counters (rolling or per-window) are maintained for:
  * `overlay_upload_bytes`
  * `overlay_download_bytes`
  * `soulseek_upload_bytes`
  * `soulseek_download_bytes`
* Counters are:
  * Updated in all relevant code paths (overlay chunk transfer, Soulseek transfers).
  * Exposed via a debug/metrics API:
    * `slskdn stats traffic` → prints current and recent-window totals.
* Optionally, counters are recorded over time (e.g. per day) for display in a "Contribution" view later.

**Implementation Notes:**
- New service: `src/slskd/Fairness/ContributionTrackingService.cs`
- Store counters in `HashDbState` table with rolling 7-day window
- Update on every chunk transfer and Soulseek transfer event

---

#### Issue H2 – Implement configurable fairness constraints

**Title:** `feat: implement fairness constraints on overlay usage`

**Labels:** `type:enhancement`, `component:fairness`, `priority:p2`, `phase:2`

**Description:**

Implement a basic fairness governor that enforces configurable constraints on how overlay usage relates to Soulseek usage, so we don't become a pure overlay leech.

**Acceptance Criteria:**

* Config options (with safe defaults), e.g.:
  * `fairness.min_overlay_upload_download_ratio` (e.g. 0.3–0.5).
  * `fairness.max_overlay_to_soulseek_upload_ratio` (e.g. overlay upload must not exceed N × Soulseek upload).
  * `fairness.enforce_per_job` (true/false).
* Enforcement:
  * If global ratios violate constraints:
    * The scheduler gradually:
      * Reduces overlay download intensity.
      * Prefers Soulseek direct transfers more heavily.
  * If per-job enforcement is enabled:
    * A job that would exceed limits:
      * Logs a warning.
      * Either slows overlay contributions or refuses overlay-only behaviour.
* There is a clear log/debug surface:
  * When fairness limits are active, log:
    * Which rule triggered.
    * What action was taken (throttle, block, etc.).

**Implementation Notes:**
- New service: `src/slskd/Fairness/FairnessGovernor.cs`
- Default config: `fairness.min_upload_download_ratio: 1.0`, `fairness.max_overlay_to_soulseek_ratio: 2.0`
- Throttle by reducing max concurrent overlay connections

---

#### Issue H3 – Optional "Contribution" summary view

**Title:** `feat: Contribution summary for overlay vs Soulseek`

**Labels:** `type:enhancement`, `component:ui`, `component:fairness`, `priority:p2`, `phase:2`

**Description:**

Provide an optional summary view so users can see how much they contribute to the network via overlay and Soulseek.

**Acceptance Criteria:**

* UI or CLI summary that shows, for a configurable time window (e.g. last 7 days / 30 days):
  * `overlay_upload_bytes`, `overlay_download_bytes`.
  * `soulseek_upload_bytes`, `soulseek_download_bytes`.
  * Derived ratios (e.g. upload/download, overlay vs Soulseek).
* Presentation is simple:
  * e.g. "You've uploaded 2.3× more than you've downloaded over Soulseek; overlay usage: 0.7× Soulseek upload."
* View is informational only:
  * Decision logic remains in the fairness governor; this is just visibility for the user.

**Implementation Notes:**
- New controller: `src/slskd/Fairness/API/ContributionController.cs`
- UI component: `src/web/src/components/System/Contribution/index.jsx`
- Display ratios with color-coded status: green (healthy), yellow (borderline), red (violating)

---

## Phase 3: UX & Observability

### Feature I – Download Job Manifests

#### Issue I1 – Define manifest schema and serialization for MBID jobs

**Title:** `feat: define and serialize YAML manifests for MBID-based jobs`

**Labels:** `type:enhancement`, `component:jobs`, `priority:p2`, `phase:3`

**Description:**

Introduce a stable YAML manifest format for MBID-based jobs (single releases, discography bundles, label crates). The manifest should be sufficient to recreate a job on another machine or after a DB reset.

**Acceptance Criteria:**

* A manifest schema is defined (documented and unit-tested). For MB Release jobs it should include at least:
  * `job_id` (UUID).
  * `type`: `mb_release`, `discography`, `label_crate`, etc.
  * For `mb_release`:
    * `mb_release_id`, `title`, `artist`.
  * Constraints:
    * `preferred_codecs`, `allow_lossy`, `prefer_canonical`, `use_overlay`, `overlay_bandwidth_kbps`, etc.
  * Creation metadata:
    * `created_at`, `created_by` (optional).
* The codebase has a serializer:
  * `JobManifest SerializeToManifest(Job job)`
  * `Job DeserializeManifest(JobManifest manifest)` (or equivalent).
* The manifest schema is versioned:
  * A top-level `manifest_version` field is present to allow future migrations.
* Unit tests:
  * Round-trip tests verifying that a job → manifest → job preserves all necessary semantics.

**Implementation Notes:**
- New service: `src/slskd/Jobs/JobManifestService.cs`
- Use YamlDotNet library for serialization
- Manifest version: `1.0`
- Schema documented in `docs/JOB_MANIFEST_SCHEMA.md`

---

#### Issue I2 – Export manifests for newly created MBID-based jobs

**Title:** `feat: export YAML manifests for MBID-based jobs on creation`

**Labels:** `type:enhancement`, `component:jobs`, `priority:p2`, `phase:3`

**Description:**

Whenever a MBID-based job is created (release, discography, label crate), write a YAML manifest to disk in a well-defined location.

**Acceptance Criteria:**

* Configurable base path for job manifests, e.g.:
  * `jobs/active/` for ongoing jobs.
  * `jobs/completed/` for finished jobs.
* When a job of type `mb_release`, `discography`, or `label_crate` is created:
  * A YAML file is written:
    * File name convention: `<job_id>.yaml` or `<type>-<job_id>.yaml`.
    * Contents conform to the manifest schema from I1.
* When a job completes:
  * The existing manifest is:
    * Either moved from `jobs/active/` to `jobs/completed/`,
    * Or updated in place with completion metadata (`completed_at`, status).
* There is a CLI command:
  * `slskdn jobs export <job_id> <output_path>`:
    * Writes or copies the manifest to the specified path.
* Sensitive data:
  * Manifests do not contain secrets or credentials (only music-relevant info and generic constraints).

**Implementation Notes:**
- Hook into job creation events in `AlbumDownloadJob`, `DiscographyDownloadJob`, `LabelCrateDownloadJob`
- Config: `jobs.manifests.enabled: true`, `jobs.manifests.path: "jobs/"`
- Move on completion using `File.Move`

---

#### Issue I3 – Import manifests to recreate jobs

**Title:** `feat: import YAML job manifests to recreate MBID-based jobs`

**Labels:** `type:enhancement`, `component:jobs`, `priority:p2`, `phase:3`

**Description:**

Allow users to import YAML manifests (generated by I2 or manually edited) to recreate jobs on another instance or after DB loss.

**Acceptance Criteria:**

* A CLI/API:
  * `slskdn jobs import <manifest_file>`:
    * Reads the YAML manifest.
    * Validates `manifest_version` and core fields.
    * Creates a corresponding Job record in the local DB.
  * Optionally: `POST /jobs/import` for REST.
* Behaviour:
  * If `job_id` in the manifest is already in use locally:
    * Either generate a new job_id (with reference to original),
    * Or require a `--allow-duplicate-id` flag (configurable).
  * If the job type is `discography` or `label_crate`:
    * Ensure child job definitions are imported and linked as needed.
* Error handling:
  * Manifest validation errors are clearly reported (missing MBID, unknown type, version mismatch).
* Unit tests:
  * Tests for import + creation for each supported job type.
  * Tests for broken manifests (missing fields, wrong types).

**Implementation Notes:**
- New controller: `src/slskd/Jobs/API/JobManifestController.cs`
- CLI: Add `import` subcommand to `slskdn` CLI
- Validation: YamlDotNet schema validation + custom business logic

---

### Feature J – Session Traces / Swarm Debug Logs

#### Issue J1 – Define an internal event model for swarm/session tracing

**Title:** `feat: define internal event model for swarm session tracing`

**Labels:** `type:enhancement`, `component:observability`, `priority:p2`, `phase:3`

**Description:**

Define a structured event model for recording how swarm downloads proceed (per job, per track, per peer), without worrying about UI yet.

**Acceptance Criteria:**

* An internal event type (or set of types) is defined, capturing at least:
  * Job ID, Track/Recording ID, Variant ID (if applicable).
  * Peer ID.
  * Time.
  * Action:
    * `chunk_requested`, `chunk_received`, `chunk_error`, `transfer_started`, `transfer_completed`, `transfer_aborted`, `rescue_invoked`, etc.
  * Source:
    * `soulseek`, `overlay`.
  * Outcome details:
    * `bytes`, `offset`, `duration_ms`, `error_code` for failures.
* Events can be created at all relevant points in the swarm engine and overlay transfer code.
* Event generation is:
  * Cheap enough not to crush performance when enabled.
  * Gateable behind a config flag (e.g. `swarm.tracing.enabled`).

**Implementation Notes:**
- New model: `src/slskd/Observability/Models/SwarmEvent.cs`
- New service: `src/slskd/Observability/DownloadTraceService.cs`
- Config: `swarm.tracing.enabled: false` (opt-in for now)
- Use structured logging for minimal overhead

---

#### Issue J2 – Persist and rotate session traces per job

**Title:** `feat: persist and rotate swarm session traces per job`

**Labels:** `type:enhancement`, `component:observability`, `priority:p2`, `phase:3`

**Description:**

Persist swarm/session events per job in a compact format, with configurable retention/rotation.

**Acceptance Criteria:**

* For each job, swarm events can be:
  * Stored in:
    * A small embedded DB table, OR
    * Append-only log files in `logs/sessions/<job_id>.log` (JSON-lines or similar).
* Retention:
  * Config option for:
    * Max jobs to keep traces for.
    * Max size per trace file.
    * Optional TTL (e.g. delete traces older than X days).
* On job completion:
  * Traces remain for at least the configured retention/TTL.
* When retention limits are exceeded:
  * Oldest traces are removed/archived.
* There is a CLI:
  * `slskdn debug job-trace <job_id>`:
    * Outputs the raw trace events (or a filtered view) to stdout.

**Implementation Notes:**
- Store as JSON-lines in `logs/sessions/`
- New table: `JobTraces` in HashDb (optional, if not using files)
- Config: `swarm.tracing.retention_jobs: 100`, `swarm.tracing.retention_days: 30`, `swarm.tracing.max_size_mb: 10`
- Cleanup job runs daily

---

#### Issue J3 – Provide a human-friendly summary view for session traces

**Title:** `feat: human-friendly swarm/session trace summary`

**Labels:** `type:enhancement`, `component:observability`, `component:ui`, `priority:p2`, `phase:3`

**Description:**

Provide a summarised view that shows, for a given job or track, which peers contributed what, how overlay vs Soulseek traffic was distributed, and key events like rescue mode.

**Acceptance Criteria:**

* A CLI/REST endpoint:
  * `slskdn debug job-summary <job_id>`:
    * Produces a textual summary including:
      * Per track:
        * Which peers contributed chunks (with approximate % of bytes per peer).
        * Overlay vs Soulseek split.
      * Events like:
        * "Rescue mode triggered for Track X at T."
        * "Peer Y marked as unreliable (corrupt chunks)."
  * Optional: `debug track-summary <job_id> <track_id>`.
* Summary uses the event model from J1, aggregated into:
  * Byte counts per peer/source.
  * Simple timing summaries (start/end, major stalls).
* Summaries are readable for power users (you) without needing a UI.
* If possible, errors/anomalies are called out explicitly (e.g. "2 corrupt chunks from peer P, excluded thereafter").

**Implementation Notes:**
- New controller: `src/slskd/Observability/API/TraceController.cs`
- CLI: Add `job-summary` subcommand
- UI component (optional): `src/web/src/components/Observability/JobTraceViewer.jsx`
- Aggregate events in-memory for display

---

## Phase 4: Advanced Features

### Feature K – Warm Cache Overlay Nodes

#### Issue K1 – Basic warm cache configuration and capacity tracking

**Title:** `feat: add warm cache configuration and capacity tracking`

**Labels:** `type:enhancement`, `component:cache`, `priority:p3`, `phase:4`

**Description:**

Introduce configuration and bookkeeping for "warm cache" behaviour, where a node can voluntarily cache popular MBIDs for the mesh.

**Acceptance Criteria:**

* Config options:
  * `warm_cache.enabled` (default: false).
  * `warm_cache.max_storage_gb` (or MB).
  * `warm_cache.min_popularity_threshold` (e.g. minimum number of jobs/peers referencing an MBID before caching).
* A small tracking store:
  * Tracks MB Release IDs and/or Recording IDs that are:
    * Candidates for caching.
    * Currently cached (with size).
* Capacity tracking:
  * Track the total disk space used by cached content (distinct from the "main library" if needed).
  * Eviction policy stub (e.g. LRU or lowest popularity).
* Warm cache remains **opt-in**:
  * Default configuration is non-caching.

**Implementation Notes:**
- New service: `src/slskd/Cache/CacheService.cs`
- New table: `CachedMbids` in HashDb
- Config: `warm_cache.enabled: false`, `warm_cache.max_storage_gb: 50`, `warm_cache.min_popularity: 10`
- Track disk usage with `FileInfo.Length`

---

#### Issue K2 – Identify popular MBIDs for warm caching from mesh and job data

**Title:** `feat: identify warm cache candidates based on mesh and job popularity`

**Labels:** `type:enhancement`, `component:cache`, `priority:p3`, `phase:4`

**Description:**

Determine which MBIDs should be considered for warm caching based on local observation of job requests and mesh adverts.

**Acceptance Criteria:**

* Popularity signals:
  * From local jobs:
    * Count how many active/in-progress jobs target each MB Release ID.
  * From mesh:
    * Count how many peers advertise a given MBID via descriptors/adverts.
* A combined popularity score is computed per MBID:
  * e.g. `score = local_jobs_weight * local_count + mesh_weight * peer_count`.
* Candidates:
  * If `warm_cache.enabled` is true and `score >= warm_cache.min_popularity_threshold`:
    * MBID is added to "candidate list".
* CLI/debug:
  * `slskdn warm-cache candidates`:
    * Lists current candidate MBIDs with their scores.

**Implementation Notes:**
- New table: `MbidPopularity` in HashDb
- Update from `mesh_cache_job` messages and local job creation
- Popularity score: `score = (0.7 * local_jobs) + (0.3 * mesh_peers)`
- Re-compute hourly

---

#### Issue K3 – Fetch, maintain, and serve warm cache content via overlay

**Title:** `feat: fetch and serve warm cache content over overlay (opt-in)`

**Labels:** `type:enhancement`, `component:cache`, `component:mesh`, `priority:p3`, `phase:4`

**Description:**

Implement the actual warm caching behaviour: prefetching popular MBIDs from Soulseek and serving them over overlay, within configured limits and fairness constraints.

**Acceptance Criteria:**

* When `warm_cache.enabled` is on and an MBID is a candidate:
  * If the node does not already have that release/recording:
    * It may initiate a normal Soulseek-based multi-swarm job to fetch it, subject to:
      * Capacity constraints.
      * Fairness constraints (overlay vs Soulseek usage).
* Once cached:
  * MBID shows up in:
    * `mbid_swarm_descriptor` as highly available (respecting standard policies).
  * Node can serve overlay chunks for tracks from that MBID to other peers, via the existing chunk protocol.
* Eviction:
  * When storage exceeds `warm_cache.max_storage_gb`:
    * An eviction policy removes the least needed warm cache items:
      * E.g., lowest popularity score or oldest access time.
* Guardrails:
  * Warm cache behaviour honours:
    * Fairness governor (H2).
    * Local bandwidth limits and overlay slot caps.
* Logging:
  * When warm cache fetches or evictions occur, log events for debugging.

**Implementation Notes:**
- Integrate with `MultiSourceDownloadJob` to fetch candidates
- Announce via the mesh DHT with `cache: true` flag
- LRU eviction: track `last_accessed_at` in `CachedMbids` table
- Respect fairness constraints from `FairnessGovernor`

---

### Feature L – Playback-Aware Swarming

*(Optional - only if/when built-in player exists)*

#### Issue L1 – Expose playback position and buffering needs to swarm engine

**Title:** `feat: expose playback position and buffering requirements to swarm engine`

**Labels:** `type:enhancement`, `component:playback`, `priority:p3`, `phase:4`, `requires:player`

**Description:**

If a built-in or sidecar player exists, expose the current playback position and desired buffer window to the swarm engine so it can prioritise chunks accordingly.

**Acceptance Criteria:**

* An internal API (or event stream) from the player to the swarm engine that provides:
  * `track_id` / MB Recording ID.
  * Current playback position in ms or bytes.
  * Desired buffer ahead (e.g. target of N ms ahead of playhead).
* Swarm engine can query:
  * For a given track:
    * "What range of bytes is high-priority (next X seconds)?"
    * "What range is mid-priority / low-priority?"
* If no player is active:
  * API returns "no-op" values and the swarm engine falls back to normal behaviour.

**Implementation Notes:**
- New service: `src/slskd/Playback/BufferManager.cs`
- New interface: `IPlaybackPositionProvider`
- Event: `PlaybackPositionUpdated` raised every 1 second
- Target buffer: 30 seconds ahead

---

#### Issue L2 – Priority zones and scheduling logic for streaming playback

**Title:** `feat: add priority zones and scheduling logic for playback-aware swarming`

**Labels:** `type:enhancement`, `component:playback`, `component:transfers`, `priority:p3`, `phase:4`, `requires:player`

**Description:**

Extend the swarm scheduler to define priority zones around the playback head and assign chunks accordingly.

**Acceptance Criteria:**

* Piece map for a playing track distinguishes at least three zones:
  * High-priority:
    * Next N seconds of audio (configurable).
  * Mid-priority:
    * N..M seconds ahead.
  * Low-priority:
    * Rest of the file.
* Scheduler behaviour:
  * High-priority zone:
    * Only assigns chunks to:
      * Low-cost, reliable peers (high reputation, good RTT/throughput).
      * Possibly uses smaller chunk sizes for low latency.
  * Mid/low:
    * Filled opportunistically using:
      * Slower peers.
      * Larger chunk sizes to improve efficiency.
* If the buffer dips below a critical threshold:
  * Swarm engine:
    * Aggressively pulls from the best peers.
    * May temporarily ignore fairness optimisations to avoid playback stutter (configurable).

**Implementation Notes:**
- New service: `src/slskd/Playback/PlaybackScheduler.cs`
- Priority zones: high (0-30s), mid (30s-3min), low (rest)
- High-priority chunk size: 32KB
- Low-priority chunk size: 256KB
- Critical buffer threshold: 5 seconds

---

#### Issue L3 – Surface basic streaming status & diagnostics

**Title:** `feat: display basic streaming/swarm status during playback`

**Labels:** `type:enhancement`, `component:ui`, `component:playback`, `priority:p3`, `phase:4`, `requires:player`

**Description:**

Provide a minimal UI/CLI output that shows how playback-aware swarming is performing for active streams.

**Acceptance Criteria:**

* UI or CLI:
  * For a currently playing track:
    * Show:
      * Buffer ahead (seconds or bytes).
      * Active peers contributing to the buffer (overlay vs Soulseek).
      * Any recent buffer underruns/stalls.
* For debugging:
  * A `slskdn debug playback <track_id>` command:
    * Prints current state of:
      * Priority zones (what ranges are filled).
      * Which peers are serving which zone.
      * Any fairness overrides active (if we temporarily relaxed caps to keep playback smooth).
* This is a read-only view into existing tracking; no additional heavy instrumentation is required beyond what the swarm engine already maintains.

**Implementation Notes:**
- UI component: `src/web/src/components/Playback/StreamingStatus.jsx`
- CLI: Add `playback` subcommand
- Display buffer as progress bar with color coding (green > 20s, yellow 10-20s, red < 10s)

---

## Issue Labels & Milestones

### Suggested Labels

- **Type**: `type:enhancement`, `type:bug`, `type:documentation`
- **Component**: `component:hashdb`, `component:mesh`, `component:transfers`, `component:ui`, `component:api`, `component:musicbrainz`, `component:discovery`, `component:fairness`, `component:jobs`, `component:observability`, `component:cache`, `component:playback`
- **Priority**: `priority:p0` (critical), `priority:p1` (high), `priority:p2` (medium), `priority:p3` (low)
- **Phase**: `phase:0` (foundations), `phase:1` (library intelligence), `phase:2` (discovery & fairness), `phase:3` (ux & observability), `phase:4` (advanced)
- **Special**: `requires:player` (blocked until player exists)

### Suggested Milestones

- **M0: Foundations** (Phase 0 complete - mostly done)
- **M1: Library Intelligence** (Phase 1 complete - Issues A1-D3)
- **M2: Discovery & Fairness** (Phase 2 complete - Issues E1-H3)
- **M3: UX & Observability** (Phase 3 complete - Issues I1-J3)
- **M4: Advanced Features** (Phase 4 complete - Issues K1-L3)

---

## Related Documentation

- [MULTI_SWARM_ROADMAP.md](archive/duplicates/MULTI_SWARM_ROADMAP.md) - High-level feature roadmap
- [MUSICBRAINZ_INTEGRATION.md](./MUSICBRAINZ_INTEGRATION.md) - MBID/fingerprinting design
- [BRAINZ_PROTOCOL_SPEC.md](archive/research/BRAINZ_PROTOCOL_SPEC.md) - Control-plane messages
- [BRAINZ_CHUNK_TRANSFER.md](archive/research/BRAINZ_CHUNK_TRANSFER.md) - Data-plane chunk protocol
- [BRAINZ_STATE_MACHINES.md](archive/research/BRAINZ_STATE_MACHINES.md) - Downloader/uploader state machines
- [MULTI_SOURCE_DOWNLOADS.md](archive/duplicates/MULTI_SOURCE_DOWNLOADS.md) - Current multi-source implementation
- [DHT_MESH_ARCHITECTURE.md](./DHT_MESH_ARCHITECTURE.md) - Public rendezvous DHT, mesh DHT, overlay, and transfer boundaries
- [HASHDB_SCHEMA.md](archive/implementation/HASHDB_SCHEMA.md) - Database schema

---

*Last updated: 2025-12-09*
