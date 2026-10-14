# Changelog

All notable changes to slskdn are documented here. [slskdN](https://github.com/snapetech/slskdn) is an unofficial fork of [slskd](https://github.com/slskd/slskd) with advanced features and experimental subsystems.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Security

- .NET dependency graphs and bundled runtimes now use the 10.0.13 servicing
  release for the SignalR denial-of-service fix. Hosted .NET build workflows
  use SDK 10.0.402, and vulnerability checks inspect every first-party project.
- CI validation artifacts now include only receipts and task logs, leaving
  temporary task environments and dependency caches on the runners.
- Public pull-request workflows now run on GitHub-hosted runners. Persistent
  self-hosted runners are reserved for trusted workflows. Manual runs from
  refs outside `main` also use hosted runners, and release jobs receive only
  the token permissions they need.

### Changed

- Automatic LAN mDNS advertising is now opt-in through
  `lan_discovery.advertise: true` and defaults off. Nearby-peer browsing
  remains user-triggered.
- Torrent acquisition is configurable under `virtualSoulfindV2.backends.torrent`
  and stays disabled by default. Private mode removes tracker/web-seed metadata,
  disables DHT/PEX, and only admits configured overlay or invite-list peers.
  Cross-peer fallback requests are rejected until the sender and job-cancellation
  lifecycle is integrated. Signal requests are checked against the exact
  variant bound to the referenced job before policy evaluation or manager
  startup.
- MonoTorrent now uses 3.9.0-alpha.unstable.rev0000 with its .NET 8 package
  asset, which NuGet selects as compatible for this .NET 10 application.

### Added

- Wishlist auto-download now validates Lidarr-synced candidates against the
  monitored release's track count, duration, and edition before downloading,
  configurable via `integrations.lidarr.edition_match_mode` (`exclude` by
  default, or `prefer`/`off`), and skips candidates matching a recently
  completed download elsewhere to avoid duplicate copies in different
  folders.

### Fixed

- Advanced search presets and modal actions, Soulseek Native Discovery
  controls, and album completion refresh now explain their effects before use.
- Selected transfer actions and request details modal controls now explain
  what they do before you use them.
- Shared path, file, privacy, capability, and VPN ingress policies now use
  read-only collections, so callers cannot alter later validation or access
  decisions by mutating exposed arrays.
- Startup diagnostics now escape configured paths and filesystem errors, and
  redact credentials and URL details from Loki endpoints before logging.
- LAN discovery logs now escape peer names and parse exception details so
  remote mDNS text cannot forge log entries.
- HTTP exception and CSRF token middleware logs now escape request and
  exception details, preventing request-triggered control characters from
  forging log entries without changing response or token behavior.
- Social federation logs now redact remote URL paths and credentials, escape
  peer-controlled text, and omit raw remote exception objects.
- SQLite-backed Pod and content-linked API logs now escape exception details
  and caller-controlled identifiers without attaching raw exception objects.
  Pod storage reads and writes preserve caller cancellation, and post-commit
  publication cancellation no longer attempts to roll back a committed update.
- PodCore API and background-service logs now escape request and peer
  identifiers plus exception details before emitting them, preventing
  control-character log forging without changing operation results.
- DHT and mesh-directory diagnostics now escape remote peer fields and
  exception details while leaving packet handling and discovery results
  unchanged.
- Mesh overlay readers now dispatch the numeric mesh message types emitted by
  the message DTOs, so valid mesh sync requests reach the sync service in both
  connection directions.
- Signal sends now propagate caller cancellation instead of treating it as a
  failed channel and trying another transport.
- Mesh and BitTorrent signal senders now propagate caller cancellation without
  logging it as a transport failure.
- Mesh and BitTorrent signal receivers now propagate callback cancellation
  without logging it as a message-processing failure.
- SignalBus now propagates caller cancellation from subscriber callbacks
  instead of swallowing it as a subscriber failure.
- Mesh hash-consensus lookups now propagate caller cancellation instead of
  treating it as a failed peer query or returning before a canceled cache write.
- Mesh service routing now propagates caller cancellation instead of converting
  it into a service failure response.
- Mesh DHT, Pods, VirtualSoulfind, content, introspection, and hole-punch
  requests now propagate caller cancellation instead of returning an ordinary
  service error. DHT discovery no longer reports cancellation as a missing
  service, and canceled hole-punch sessions are removed before retry.
- Peer descriptor refresh now stops cleanly when host shutdown cancels an
  in-flight publish instead of logging it as a refresh failure. Peer
  relay-descriptor updates also propagate caller cancellation instead of
  logging it as an update failure.
- Kademlia node and value lookups, peer pings, and DHT stores now propagate
  caller cancellation instead of returning incomplete results or peer misses.
- Canceled anonymity or obfuscated-transport selection now propagates instead
  of falling back to standard mesh routing. Canceled privacy transport
  availability checks and connections also stop without starting a fallback
  route.
- Mesh transport selection and route diagnostics now propagate caller
  cancellation instead of trying another endpoint or returning an ordinary
  result. Incomplete circuits release streams from established hops.
- UDP and QUIC overlay sends now propagate caller cancellation instead of
  reporting a canceled send as a transport failure.
- Mesh search, hash-backed peer discovery, and shadow-index discovery now
  propagate caller cancellation instead of returning incomplete results or
  continuing through another discovery source.
- Scene peer discovery now propagates cancellation from a member lookup instead
  of returning a partial peer list.
- Swarm intelligence, performance analysis, and configuration prediction now
  propagate cancellation instead of returning fallback recommendations.
- Single descriptor retrieval and verification now propagate cancellation
  instead of returning a failed lookup or invalid result; descriptor batch
  retrieval keeps completed results when the caller cancels.
- Music metadata lookups now propagate caller cancellation instead of returning
  “not found” for canceled HashDb operations.
- Scene searches, metadata deserialization, and announcement refresh now stop
  on caller cancellation instead of returning partial scene results or moving
  on to another scene.
- Soulseek health checks now preserve monitor shutdown cancellation instead of
  reporting the reconnect delay as an unavailable server.
- Multi-source search endpoints now propagate HTTP request-abort cancellation
  instead of converting a disconnected request into an HTTP 500 search error.
- Mesh sync now preserves caller cancellation while waiting for synchronization
  and serving peer chunk reads.
- Mesh health checks and service publication now propagate caller cancellation
  instead of returning degraded status or logging it as a publish failure.
- Rate-limited transfer and search updates now honor their concurrency limit
  from the first callback and retain staged updates across timer ticks.
- Resolver cancellation now reports a canceled execution instead of a failed
  candidate, and canceled torrent fetches stop and remove their active manager.
- Experimental swarm downloads now keep caller job IDs out of filesystem
  paths, stop after three failed chunk attempts, clean per-job chunk data, and
  stream verified chunks into an atomically published output.
- Full swarm job queues now report rejection to the caller instead of
  returning success for a discarded job.
- Cover-traffic workers now use the same bounded stop path during disposal and
  keep their cancellation resources alive until an in-flight send finishes.
- Mesh cover-traffic iterators now observe generator disposal, so configuration
  replacement cancels pending reads before the old generator is released.
- Private-gateway shutdown now retains cancellation resources until a cleanup
  worker that exceeds its join timeout has finished.
- Scene pubsub shutdown now retains cancellation resources when a DHT poll
  exceeds its join timeout, then releases them and reports late worker faults
  after polling stops.
- Multi-source downloads now propagate caller cancellation, drain per-chunk
  speed monitors, remove temporary chunks on failure, and balance active-work
  metrics across all accepted-job outcomes.
- Final fingerprint verification now propagates caller cancellation instead of
  turning an interrupted verification into an unverified successful download.
- Content-safety scans now propagate cancellation through pod, share-backfill,
  mesh, relay, Soulseek, and multi-source download paths. Canceled staged files
  are cleaned up instead of being published or reported as ordinary failures.
- Optional source planning, private-gateway requests, and profile loading now
  preserve caller cancellation instead of continuing fallback work or returning
  a service error; profile hostname discovery is asynchronous and cancellable.
- Signal-bus and stream-response cleanup now retain resources until active work
  finishes, invoke stream release callbacks once across sync and async disposal,
  and surface callback failures after wrapped-stream cleanup.
- Local port forwarding now rejects starts after disposal, closes tunnel opens
  that complete during shutdown, propagates connection cancellation through
  mesh requests, and supports asynchronous cleanup that waits for real worker
  completion.
- Music ActivityPub outbox reads now report HashDb failures and cancellation
  instead of returning a successful empty collection.
- Peer endpoint resolution now preserves DHT and DNS cancellation and performs
  hostname lookup asynchronously.
- Pod message routing now propagates caller cancellation and leaves interrupted
  fan-outs retryable instead of marking them as already delivered.
- Library item lookup and hashing now stop cleanly when the request is canceled,
  instead of returning partial metadata from fallback paths.
- Soulseek verification now skips probes whenever the persisted per-peer budget
  cannot be safely loaded or saved, and caller cancellation propagates through
  HashDb lookups, probe downloads, and source discovery.
- Collection database upgrades now check for missing columns explicitly and
  stop startup on real schema errors instead of hiding them as already-applied
  migrations.
- Player file browsing and search now resolve each directory/filename instead
  of treating a Soulseek format code as a unique file ID. Explicit file-picker
  searches can play configured local downloads before indexing, with no file
  hashing for that fallback. Successful path resolution is reused across
  ticket and media requests while rechecking allowed roots and file size.
- Player playback-status announcements now coalesce rapid state changes so
  screen readers can speak track-start, pause/resume, and stop updates in
  Firefox as well as Chromium.
- Canceled Player transcodes now keep draining FFmpeg diagnostics, stop the
  decoder process tree, and wait for it to exit before releasing stream slots.
- Equalizer gain sliders expose their vertical orientation and use consistent
  Up/Right increase and Down/Left decrease keys across browsers.
- Player keyboard focus rings now maintain at least 3:1 contrast across every
  built-in dark palette and the four dark Player surfaces.
- PPA source builds now derive and preflight the signing fingerprint from the
  imported secret key, so key rotation cannot leave `debuild` using a stale
  fingerprint.
- Listening-party publication now rejects active Party ID collisions across
  observed rooms and checks the DHT owner before a room first lists that ID.
  A `party_id_in_use` conflict tells the browser to start again with a fresh ID.
- Player document close now sends a best-effort fenced Stop, and the server
  withdraws room state and the radio index when a host lease expires, retrying
  transient cleanup failures without a periodic idle sweep.
- Listening-party playback now catches up active Play and Seek positions for
  time spent before server receipt and while updates are in transit; paused
  positions remain exact, and the server correction is capped at ten seconds.
- Returning to a visible Player tab now publishes one current Play/Pause
  position for active room broadcasts, letting listeners resynchronize without
  periodic host polling.
- A static loading message and reload action remain available when the web
  application fails before React mounts.
- Application runtime packages no longer include the unused Roslyn compiler
  assemblies; the optional source-analysis task stays in the dedicated tooling
  project.
- Collapse remains available while player tools are closed. Narrow compact
  layouts retain readable titles; expanded mobile controls have 44-pixel
  minimum touch targets.

- Wishlist auto-download now rechecks the persisted enablement and download
  budget immediately before enqueueing ranked results, so disabling an item
  during ranking cannot start a stale batch.
- The Auto-Replace control now explains that failed-download auto-retry is a
  separate setting, so disabling one automation does not leave the other
  ambiguous.
- Local-identity checks now exclude only immutable GitHub co-author trailers
  while continuing to scan release-facing text and other commit content.
- Stabilized the proof-of-storage allocation budget for shared CI runners while
  retaining a bounded 4 KB-per-response regression check.
- Hardened the fragmented SOCKS test server so EOF and teardown close active
  clients instead of hanging the backend test host.
- Patched transitive `brace-expansion` packages to 1.1.18 and 5.0.9 to close
  the current high-severity resource-exhaustion advisories.

- Made configured download destinations functional end to end: the folder
  marked `default` now governs destination-less and automatic downloads, while
  Search Results and Browse expose a persistent **Download to** selector for
  ordinary and bridged downloads.
- Removed a captive scoped Pod-messaging dependency from the singleton mesh
  service, restoring application startup when dependency scope validation is
  enabled.
- Resolved the registered anonymity transport selector through its interface so
  the adversarial security status endpoints can report live selector state, and
  stopped the disabled Web UI from probing unavailable Tor and transport
  endpoints on every visit.
- Transferred exclusive ownership of active download cancellation sources before
  shutdown cancellation, preventing transfer cleanup from disposing a source
  immediately before service disposal calls `Cancel()` on it.
- Reconfigured regular and type-1 obfuscated Soulseek listeners as one live
  update, including advertised metadata, without leaving a stale reconnect
  warning after the runtime successfully rebinds them.
- Resolved adversarial security settings through the options framework so the
  configured settings endpoint no longer falls back to an injected null.
- Rejected unsupported obfuscation-without-regular-advertisement settings
  during validation, and made unexpected fatal Web startup failures exit with
  a non-zero status.
- Retained the last validated root options across invalid watched reloads,
  including a failure before the first consumer read, while allowing later
  valid reloads to apply and unrelated factory failures to surface.
- Enforced fractional auto-retry tolerance boundaries without integer
  conversion accepting near-boundary out-of-range values.
- Honored configured regex case sensitivity in blacklist matching and after
  search-filter reloads, including cache identity for live blacklist changes.
- Made API YAML validation accept the documented `transfers.groups`
  compatibility placement with canonical top-level precedence and nested
  pattern validation.
- Authenticated API-key callers before rate-limit partition selection so they
  no longer consume anonymous quotas, and returned redacted 413 Problem Details
  for request-body limit failures instead of a generic 500.
- Marked every startup-bound CORS option as restart-required so live
  configuration edits set `pendingRestart` instead of implying that the
  unchanged startup middleware policy has already taken effect.
- Restored visible, named, and mouseover-explained Web controls for search and
  Lidarr pagination, Lidarr refresh, user browsing, wishlist pagination and
  view modes,
  transfer columns, and media-server provider selection; provider selectors now
  render the adapters' actual labels instead of blank buttons.
- Kept the selected System tab visible when its 22-item navigation strip
  overflows the viewport, including direct links to later admin panels.
- Made release council reports regenerate from tracked repository files so
  ignored local build artifacts cannot mask clean-checkout gate failures.
- Preferred configured COPR API tokens for unattended uploads, with Kerberos
  credentials retained as fallbacks, so missing HTTP service principals no
  longer block releases that already have valid token credentials.
- Raised the transitive AngleSharp runtime floor to `1.5.0`, closing the HTML5
  annotation-XML mutation-XSS advisory inherited through dotNetRDF.
- Restored distributed mesh DHT lookup and cross-runtime signed-store
  interoperability, registered the remote Pod/shadow-index/gateway services,
  and preserved routable shadow-index peer hints.
- Closed the private-gateway DNS rebinding gap by connecting only to addresses
  that passed policy validation, and used the node's real gateway identity for
  authorization and forwarding.
- Kept successfully persisted Pod messages accepted when their immediate
  best-effort routing attempt fails.
- Preserved the existing `DbUpdateException` boundary when atomic share-group
  member admission encounters a database constraint failure.
- Registered the ordered download auto-retry index migration so application
  startup applies it to existing transfer databases.
- Raised the frontend unit-test timeout to accommodate lazy-loaded routes and
  large jsdom components on shared CI runners without masking test failures.
- Extended the matching Testing Library wait for lazy-loaded search routes so
  the assertion timeout tracks the frontend test budget on shared CI runners.

### Changed

- Mesh DHT string keys now use the frozen 160-bit wire contract, local misses
  perform iterative distributed lookups, and signed publisher identity is
  derived from the canonical Ed25519 key rather than an overlay username.
- UTF-8 Base64 string conversion now encodes and decodes through bounded stack
  or cleared pooled byte storage without intermediate byte arrays.
- Salted constant-time hashing, boolean hash verification, and double SHA-256
  now use static span hashing without disposable algorithms, stack-input copies,
  intermediate digest arrays, or verification result arrays.
- Tor stream-isolation usernames and passwords now hash and format through
  bounded span/pool storage without concatenated keys, disposable algorithms,
  digest arrays, full hexadecimal strings, substrings, or lowercase copies.
- Shared SHA-1 and SHA-256 string hashing now uses bounded UTF-8 stack/pool
  storage, static span hashing, and direct uppercase hexadecimal formatting
  without disposable algorithms or intermediate arrays and strings.
- Legacy bridge room/scene mapping now normalizes and classifies room names
  through bounded span/pool storage, constructs scene IDs without intermediate
  strings or LINQ, and extracts room segments without splitting whole IDs.
- Legacy bridge filename generation now formats artist, title, codec, bitrate,
  and lowercase extension through bounded span/pool storage, avoids filesystem
  sanitization allocations when no invalid characters are present, and skips
  debug-log argument allocation when debug logging is disabled.
- Legacy bridge peer anonymization now hashes and formats its exact friendly
  username through bounded span/pool storage without digest arrays, full-hex
  strings, substrings, lowercase copies, or final interpolation.
- MusicBrainz release/recording UUID-v5 mapping now uses big-endian Guid and
  span SHA-1 APIs over bounded stack/pool storage instead of namespace, name,
  combined-input, digest, and UUID byte arrays.
- Virtual Soulfind username pseudonymization now hashes normalized usernames
  and its fixed salt through bounded span/pool storage and formats the exact
  peer ID without concatenation, digest-slice, or upper/lower hex copies.
- Virtual Soulfind DHT key derivation now hashes namespace and identifier parts
  through bounded span/pool UTF-8 storage instead of interpolated strings and
  byte arrays, and lower-hex formatting no longer creates an uppercase copy.
- Bridge identity sanitization now hashes and formats its abbreviated internal
  pod ID through bounded span/pool storage without byte-array, full-hex,
  substring, lowercase-copy, or interpolation intermediates.
- Probabilistic file spot checks now reuse one cleared pooled chunk buffer and
  fixed digest span across the existing bounded sample instead of allocating
  chunk and hash buffers for every selected index.
- Commitment revealed-hash and verified-content checks now reuse normalized
  values and bounded span/pool UTF-8 storage instead of allocating two byte
  arrays for each constant-time comparison.
- Proof-of-storage response generation now reads challenged file chunks directly
  into cleared pooled hash input storage instead of allocating separate nonce,
  chunk, concatenation, digest, and uppercase/lowercase hexadecimal buffers.
- Proof-of-storage challenge creation now formats random nonce and abbreviated
  GUID identifiers without uppercase/lowercase or full-GUID string copies, and
  verification reuses bounded span/pool storage for constant-time comparison.
- Cryptographic commitment verification now compares digest bytes through fixed
  spans instead of allocating two UTF-8 arrays per attempt.
- Cryptographic commitment creation now reuses normalized hashes and hashes
  nonce inputs through bounded span/pool buffers without binary/hex copies.
- Pod ID generation now hashes through static/span APIs and writes only the
  required lowercase prefix without two-peer sorting or full-hex intermediates.
- Long canary watermark expansion now reuses one HMAC and fixed span buffers
  instead of allocating hash, counter, and concatenation arrays per block.
- Canary registration now computes HMACs and lowercase identifiers without
  disposable hash objects, byte slices, or uppercase string intermediates.
- Canary filename suffix encoding and decoding now avoid per-nibble strings and
  filtered bit lists.
- Auto-replace filename filtering now prepares expected tokens once per search
  and scans candidate token ranges without per-candidate token sets.
- Multi-source variant matching now prepares basenames once and compares common
  ASCII filename characters without per-variant intersection sets.
- MediaCore swarm prediction now enumerates available peers once, reuses common
  ContentID compatibility, and aggregates capability statistics directly.
- Adaptive scheduler weight learning now calculates all factor correlations in
  one online covariance pass without factor and outcome lists.
- Swarm efficiency reporting now aggregates download and peer metrics in direct
  passes without copied and filtered LINQ lists.
- Adaptive peer scoring now aggregates recent completion success and duration
  in one queue scan without filtered lists or repeated counting passes.
- Peer RTT and throughput standard deviations now use a one-pass calculation
  over their sliding windows without LINQ projection and list materialization.
- Search response merging now deduplicates common ASCII filenames without
  allocating lowercase, path-normalized, and trimmed copies for every file.
- Download enqueue checks now load history only for the requested filenames
  instead of materializing every past download from the selected user.
- Upload scheduling now selects the next eligible transfer in one pass without
  rebuilding grouped ready-upload lists or sorting each scheduling decision.
- Full security challenge and verification caches now find their oldest entry
  without allocating and ordering concurrent-value snapshots during eviction.
- Proof-of-storage and cryptographic-commitment statistics now aggregate their
  concurrent state maps directly without value snapshots or repeated passes.
- In-memory intent scheduling now retains only the requested best pending batch,
  and status counts scan track intents without concurrent-value snapshots.
- Network guard rankings now retain only the requested top connectors, and its
  statistics aggregate concurrent tracker maps without value snapshots.
- Honeypot, reconnaissance, and paranoid-mode recent-event queries now retain
  only the requested newest page instead of reverse-buffering full histories.
- Peer reputation rankings now retain only the requested best-scored peers, and
  reputation statistics scan the concurrent profile map without value snapshots.
- Security event queries now retain only the requested newest matching page
  instead of reverse-buffering the complete retained history.
- Library Bloom snapshots now build unique value-type items and exact namespace
  counts directly instead of allocating formatted deduplication keys and groups.
- Library Bloom comparison now deduplicates normalized recording candidates
  before constructing and sorting suggestion metadata.
- Advanced discovery now prepares filename-token queries once and scans each
  candidate without per-comparison split arrays or intersection sets.
- Advanced content-variant discovery now aggregates structural source groups in
  one pass and creates peer sets only for groups that actually need them.
- MediaCore fuzzy descriptor discovery now uses a bounded worker pool and
  coalesces normalized cache keys while preserving candidate result order.
- MediaCore swarm grouping now discovers content variants once per target instead
  of repeating registry and descriptor reads for every verified hash group.
- Source ranking and batch-history reads now query existing peer counters through
  one narrow SQLite JSON-table lookup instead of EF local-collection expansion.
- Profile-filtered HashDb variant reads now match distinct codec profiles and
  rank duplicate identities in SQLite before hydrating only matching winners.
- Single-recording HashDb variant reads now rank duplicate identities in SQLite
  and hydrate only their SQL-ordered winners.
- Batched HashDb variant reads now rank structured recording/variant identities
  in SQLite and hydrate only each identity's best row.
- Peer-reputation statistics now aggregate event counts, scores, bans, and type
  totals in one locked pass per peer instead of copying and rescanning events.
- Native library search now scans shared files directly into its bounded result
  page and stops at the limit instead of copying the complete share first.
- Native library browsing now uses structured duplicate keys, reuses canonical
  virtual paths, matches invariant queries through reusable span storage, and
  retains only the requested sorted prefix instead of fully sorting every file.
- Opinion listing now normalizes query filters once and retains only the bounded
  newest matches instead of fully sorting every matching retained opinion.
- Accessible share-grant queries now filter group membership in the database
  instead of hydrating every active group grant for application-side filtering.
- Transfer speed snapshots now aggregate recorded live speeds and retained bytes
  in SQL and stream only transfers requiring elapsed-time fallback calculation.
- Audio dedupe grouping now uses structured sketch/duration keys instead of
  allocating a formatted composite key for every variant.
- Codec-profile keys can now be generated without intermediate profile objects,
  while HashDb profile filtering compares common keys through stack storage.
- Canonical statistics recomputation now indexes requested recording/profile
  variants in one pass and bypasses deduplication state for singleton profiles.
- Canonical audio candidate selection now caches codec-profile keys and builds
  profile/stat indexes directly instead of repeatedly allocating profile
  objects, keys, and LINQ grouping buffers.
- Canonical audio statistics now aggregate counts, quality, distributions, and
  best-variant selection in one pass over deduplicated variants.
- Canonical audio stream deduplication now retains the best variant per key in
  one insertion-ordered pass instead of buffering and sorting LINQ groups.
- SongID loose-text normalization now fuses case folding, feature aliases, and
  ASCII token cleanup into a direct exact-size scan instead of chained string
  replacements, regex replacement, and trimming.
- SongID run-quality consensus now prepares canonical track artist labels once
  and aggregates album/artist support directly without per-candidate lists or
  repeated track normalization.
- SongID corpus reranking now normalizes each corpus and candidate label once
  per run and scores candidates through direct scans instead of repeated LINQ
  pipelines and repeated normalization.
- SongID repeated-line scoring now streams trimmed lines, bounds exact-line
  normalization reuse, and aggregates normalized occurrences online.
- SongID synthetic transcript cue counts now use count-only regex execution
  instead of materializing every match result.
- SongID transcript token counts now scan ASCII letter/apostrophe runs directly
  instead of materializing a regex match object for every token.
- SongID transcript trigram repetition now streams token ranges and aggregates
  distinct trigrams without regex match, token, n-gram, or grouping buffers.
- SongID loose-text similarity now compares normalized token ranges through one
  membership table instead of allocating split tokens and extra Jaccard sets.
- Discovery Graph evidence summaries now aggregate each lane in one pass and
  sort only distinct lane totals instead of buffering every edge-lane group.
- Text-only taste-recommendation keys now normalize through reusable stack
  storage and allocate a canonical string only for each distinct work group.
- Taste recommendations now aggregate observations directly and retain only the
  bounded best result groups instead of buffering LINQ groups and eager DTOs.
- WorkRef security validation now reuses its sensitive-pattern table instead of
  allocating the same pattern array for every checked field.
- Multi-source planning now reuses successful Soulseek peer-reputation reads
  within each plan and parses peer references without `Split` allocations.
- Multi-source planning now deduplicates candidates without formatted grouping
  keys and performs one content-level moderation check per plan.
- Cross-provider search aggregation now streams results once and deduplicates
  common ASCII filename keys without allocating lowercase path copies.
- IPLD graph construction now pre-sizes bounded coordinator collections from
  root fan-out and reuses the shared empty array for leaf outgoing links.
- IPLD inbound-link lookup now uses a source-ordered reverse target index
  instead of scanning every outgoing source and link for each query.
- IPLD graph construction now passes each hydrated node into recursion instead
  of rebuilding its outgoing and incoming link snapshots.
- Music-domain variant projection now deduplicates HashDb variant IDs before
  allocating returned `MediaVariant` objects and grouping state.
- Shadow Index descriptor projection now selects its best variant in one pass
  and sorts/formats only structurally distinct hash-prefix representatives.
- Descriptor version generation now streams bounded UTF-8 chunks directly into
  SHA-256 and formats its compact output from stack buffers.
- Descriptor batch publishing now uses a fixed five-worker pool instead of
  creating one semaphore-waiting async task per descriptor.
- Descriptor batch retrieval now uses a fixed 10-worker pool instead of creating
  one semaphore-waiting async task per requested ContentID.
- Descriptor cache domain queries now parse keys without allocations and bound
  newest-distinct result ordering instead of sorting/grouping every match.
- Descriptor cache cleanup, statistics, size estimation, and clear accounting
  now use direct passes instead of snapshots, key buffers, and boxed LINQ sums.
- Combine-all metadata merging now aggregates ordered distinct hashes and scalar
  fields in one source pass instead of building duplicate lists and rescanning.
- Metadata export checksums now stream JSON segments directly into SHA-256
  instead of materializing complete UTF-16 and UTF-8 payload copies.
- Metadata merge preference strategies now select their winning source in one
  pass instead of copying and ordering every source.
- Levenshtein fuzzy scoring now removes invariant-case shared affixes before
  allocating lowercase comparison strings.
- Soundex fuzzy scoring now scans and invariant-cases only contributing letters
  instead of normalizing and filtering complete input payloads into copies.
- Jaccard fuzzy scoring now tokenizes and measures set overlap in direct passes
  instead of building split/LINQ and duplicate intersection/union structures.
- PCM extraction now decodes ffmpeg output directly from the existing stream
  buffer into normalized samples instead of copying two intermediate payloads.
- Image pHash now converts only the 32 source pixels that contribute to its
  result and keeps the bounded coefficient buffer on the stack.
- Spectral hashing now evaluates decimated RMS samples directly instead of
  allocating the complete downsampled signal first.
- Chromaprint hashing now reuses immutable Hann and normal-rate FFT-bin mapping
  tables instead of rebuilding them for every audio hash.
- Perceptual-hash Hamming distance now uses the runtime population-count
  intrinsic instead of a per-set-bit shift and branch loop.
- Spectral and Chromaprint hashing now keep bounded feature, median, and chroma
  work buffers on the stack instead of allocating them per hash/frame.
- Spectral perceptual hashing now evaluates audio windows as spans instead of
  copying the complete sample payload across eight slice arrays.
- Connection fingerprint admission now formats compact IDs and IP hashes from
  stack buffers instead of allocating full intermediate strings and arrays.
- Common security connection fingerprints now use bounded recent reads,
  single-pass queries/statistics/eviction, and atomic event-log sizing.
- Filtered connection-fingerprint queries now enumerate dictionary entries
  directly instead of allocating an implicit values snapshot before sorting.
- Connection-event retention now uses atomic queue-size accounting instead of
  recounting the concurrent queue on every event and statistics read.
- Recent connection-event retrieval now retains only the requested tail instead
  of reverse-buffering the complete 10,000-event audit queue.
- Connection fingerprint retention now finds the oldest capped entry in one
  pass instead of snapshotting and sorting all tracked fingerprints.
- Connection fingerprint statistics now aggregate directly in one dictionary
  pass instead of snapshotting and repeatedly scanning all fingerprints.
- Mesh search response enrichment now stops streaming file-content mappings at
  the first advertisable item instead of buffering every mapping.
- Virtual Soulfind canonical selection now scans variant hints once instead of
  sorting and allocating the complete result list.
- MediaCore dashboards now share one content-registry snapshot between registry
  and IPLD statistics instead of enumerating every domain twice.
- Levenshtein fuzzy scoring now skips shared prefixes and suffixes before its
  distance pass and short-circuits case-insensitive equality.
- Levenshtein fuzzy scoring now uses two bounded working rows instead of an
  input-product-sized distance matrix.
- Fuzzy content searches now reuse usable target and candidate descriptors
  within each search instead of retrieving the target for every candidate.
- IPLD link validation now reuses registry membership results within each run
  and checks each orphan source once instead of once per outgoing link.
- Advanced peer discovery ranking now batch-loads local peer metrics instead of
  issuing one serialized HashDb lookup per discovered peer.
- Multi-source canonical skip decisions now read one best local variant instead
  of hydrating and sorting every variant for the recording.
- MediaCore recording-ID fallback now asks HashDb for one deduplicated best
  variant instead of loading and sorting every variant for the recording.
- Recipient collection authorization now uses one indexed scalar direct/group
  access query instead of loading every grant accessible to the user.
- Share-token streaming authorization now uses an indexed content-membership
  existence query instead of loading and scanning every collection item.
- Single-grant authorization now resolves one active grant by ID and checks
  only its group membership instead of loading every accessible grant.
- Collection item updates now resolve one scoped item by ID instead of loading
  and scanning the collection's complete ordered item list.
- Peer-ID share-group member removal now deletes one matching legacy row with
  one atomic SQLite command instead of reading and hydrating it first.
- Collection-item append now assigns and returns its next ordinal in the same
  atomic SQLite insert instead of issuing a separate maximum-ordinal query.
- Share-group member admission now uses one atomic conditional SQLite insert
  instead of a duplicate read followed by a separate write.
- Collection reordering now writes ordinals through bounded transactional
  SQLite updates instead of hydrating and tracking the complete collection.
- Key-unique Sharing deletes now execute as one atomic SQLite command instead
  of reading and hydrating an entity before deleting it.
- Incoming collection announcements now replace existing items with one
  set-based SQLite delete instead of hydrating and deleting every old item.
- Wishlist ignored-result duplicate checks now use the existing composite
  case-insensitive index instead of loading every rule for the item.
- Share-group member details now batch peer-contact nickname lookup instead of
  opening one contact query and DbContext per peer-backed member.
- Share-manifest reads no longer load the complete contact table when no peer
  identity exists for owner-contact resolution.
- Native Jobs filtering, sorting, counting, and pagination now execute in
  HashDb without loading and deserializing both complete job tables.
- Search page startup now uses one bounded SignalR history snapshot and falls
  back to the REST snapshot only when hub connection fails.
- Download-request lists now aggregate attempt counts in SQLite and hydrate
  only each request's current attempt through a matching composite index.
- Swarm peer ranking now selects its bounded top set in SQLite before
  hydrating metrics instead of loading and sorting every persisted peer.
- Warm-cache access touches now update only their timestamp through one atomic
  SQLite command.
- Federated recommendation promotion now checks Wishlist duplicates through an
  indexed exact lookup instead of loading the complete Wishlist.
- Music metadata fallback matching now queries one bounded best-variant sample
  instead of loading every variant recording ID before batch hydration.
- MediaCore music-domain variant samples now use one bounded HashDb projection
  instead of loading recording IDs and querying each recording separately.
- Warm-cache capacity enforcement now evicts oldest unpinned metadata through
  one set-based SQLite command.
- Warm-cache hint ingestion now persists popularity increments through bounded
  multi-row SQLite upserts.
- Accessible share-grant resolution now batches group-membership evidence and
  filters unrelated direct grants in SQLite.
- Virtual Soulfind upgrade and orphan scans now hydrate verified-copy evidence
  only for unresolved files in each bounded page.
- Virtual Soulfind release-gap analysis now batch-loads page-scoped tracks,
  release groups, artists, and copy evidence.
- Virtual Soulfind upgrade analysis now batch-loads track metadata for each
  bounded local-file page.
- Virtual Soulfind library reconciliation now batch-loads local-file and
  verified-copy presence for each bounded track set.
- Native shared-library browser directory aggregation now indexes normalized
  paths, file counts, and immediate-child counts in one pass.
- Native shared-library search and browser pages now resolve their bounded file
  set once and batch exact HashDb evidence lookup.
- Audio analyzer migrations now page variant reads and batch recalculated
  analysis-field updates instead of scanning and writing one recording at a time.
- MusicBrainz discography and Library Bloom Wishlist promotions now batch new
  seeds, reuse one Wishlist snapshot, and index search-text membership.
- Lidarr wanted synchronization and Wishlist CSV imports now persist new items
  with bounded multi-row SQLite inserts.
- Canonical audio-stat ranking and full recomputation now batch stored stats,
  variant hydration, and bounded multi-row persistence.
- Discography coverage now batches cached releases, tracks, and recording-hash
  evidence, and indexes Wishlist search text for constant-time membership tests.
- Discography and label-crate status reads now aggregate child state in one
  pass and persist the parent only when derived fields change.
- HashDb history backfill now ingests each retained search page through one
  batched transaction instead of one transaction per search.
- Library Health scans now checkpoint durable progress every 100 files instead
  of rewriting scan status after every file.
- Discography and label-crate release-job persistence now uses normalized,
  bounded multi-row SQLite upserts.
- HashDb statistics now aggregate peer, inventory, and hash counts through one
  SQLite snapshot command.
- Album-target persistence now replaces normalized track lists with bounded
  multi-row SQLite inserts instead of one command per track.
- HashDb mesh synchronization now classifies existing hashes through bounded
  indexed batches and inserts new hashes with transactional multi-row writes.
- HashDb peer activity and capability writes now use single atomic SQLite
  upserts instead of read-before-write existence checks.
- Passive FLAC discovery and history backfill now persist inventory and peer
  records with bounded multi-row SQLite upserts.
- Library Health remediation now targets requested and job-linked issues through
  indexed reads and applies state changes with bounded set-based updates.
- Music tag matching now batches candidate album tracks, recording presence,
  and bounded fallback variants instead of querying each album and recording.
- Recent music enumeration now pushes its global item limit into an indexed
  album-track query and batches recording-presence checks.
- Music recording-ID resolution now uses a direct case-insensitive indexed
  album-track lookup and defers variant hydration until the track lookup misses.
- MusicBrainz album completion now batches release-track and recording-hash
  evidence reads instead of issuing one database query per album and track.
- Library Bloom album analysis now loads release tracks in indexed batches and
  uses set-based held-recording membership instead of per-release queries and
  nested linear scans.
- SignalBus receive deduplication now uses atomic concurrent-cache admission
  instead of serializing every signal through one global semaphore.
- Source Discovery now persists returned files with bounded multi-row SQLite
  upserts instead of compiling and executing one command per file.
- Library Health release completeness checks now coalesce files by release and
  directory, then query all track recording IDs in indexed batches instead of
  repeating the complete album analysis for every file.
- Scheduled file retention now streams directory entries and resolves each
  candidate once instead of materializing all names and reevaluating the same
  lazy filesystem pipeline three times.
- Intent queue batches now reuse their loaded pending records behind atomic
  status claims, and skip whole-queue statistics hydration when debug logging
  is disabled.
- Library Health scan status polling now pauses in hidden tabs, preserves its
  one-minute deadline, and schedules each check after the previous request
  completes so slow responses cannot create overlapping work.
- Wishlist “mark all viewed” now uses one set-based update instead of loading
  and tracking every matching item.
- Pod deletion now removes messages, members, and membership history with
  bounded set-based database commands instead of tracking every child row.
- Share scan completion now queries advertisable content IDs directly instead
  of enumerating every file and loading its mappings individually.
- Wishlist and Auto-Replace search completion polling now reads lightweight
  state projections and hydrates final response payloads once.
- Share content-peer hint publication now drains deduplicated bounded batches
  and updates the shared peer-content DHT index once per batch.
- Backfill candidate scheduling now batches daily peer counters and reuses the
  snapshot through each cycle instead of querying every counter twice.
- Periodic Pod discovery publication now loads one listed-only database
  snapshot, publishes its metadata without per-Pod reloads, and refreshes the
  shared listed-Pod index once per cycle instead of once per Pod.
- Mesh bootstrap now publishes the initial self descriptor once and leaves all
  periodic and IP-change refreshes to the configured refresh service, removing
  duplicate DHT writes and active STUN detection every 30 minutes.
- Search retention, legacy pruning, and completed-history clearing now process
  stable 250-search pages with one set-based delete per page instead of loading
  the full candidate set and opening one database transaction per search.
- Automatic search retention now honors its configured cleanup interval instead
  of evaluating the database policy every five minutes. Cleanup runs cannot
  overlap, and failed runs remain eligible for the next clock evaluation.
- Shadow Index publishing now rotates through bounded indexed recording-ID
  pages, avoids full-library sorting and materialization, and does not build
  more shard candidates than the immediate DHT write budget can admit. The
  configured Virtual Soulfind DHT operation limit is now honored.
- Download auto-retry now reads an indexed, minimal oldest-first candidate
  stream and stops once its bounded global/per-peer plan is final instead of
  materializing the complete retained failure history on every cycle.
- System Bridge dashboard polling now stops while hidden, coalesces overlapping
  requests, ignores uptime-only response churn, retries failed initial config
  hydration, and retains its last successful snapshot. Synced lyrics now follow
  media/seek events without a redundant fixed 500 ms timer.
- Security dashboard statistics now aggregate each retained collector set in a
  single pass instead of repeatedly materializing and rescanning it. System
  Security polling is visible-only, non-overlapping, preserves unchanged and
  last-successful snapshots, and renders only the selected dynamic tab; the
  previously blank Status body and broken Adversarial tab selection are fixed.
- Mesh transport stats, Network snapshots, and health checks now report the
  last NAT result without triggering STUN detection during diagnostic reads.
  System Mesh polling is also visible-only, non-overlapping, Strict Mode-safe,
  and preserves unchanged or last-successful snapshots. The System polling
  lifecycle gate now enforces Strict Mode-safe mounted-ref setup across its
  complete component inventory.
- Compact listen-along panels no longer fetch the global radio directory they
  do not render. Full directory views now poll once per visible minute without
  overlap or transient cache loss, while the backend coalesces concurrent
  callers onto one process-wide DHT hydration and reuses it for one minute.
- Library Health now loads its System dashboard through one bounded SQLite
  snapshot instead of four paged entity reads, reports full-set summary and
  grouping counts beyond 100 issues, uses an indexed recent-issue page, and
  rejects limits that could disable SQLite pagination.
- Lidarr dashboard status polling now pauses while the document is hidden,
  rejects overlapping refreshes, coalesces rapid duplicate external status
  requests, and preserves React state when every rendered status field is
  unchanged.
- Search download-history ranking now uses one database aggregate instead of
  materializing the complete retained download history, and short-lived client
  reuse prevents repeated detail navigation from rerunning the same summary.
- Search results now batch cached user-group metadata for visible peers, reuse
  response-provided speed, queue, and slot data, and wait for user interaction
  before loading reputation and opinion details. Initial result rendering no
  longer contacts every remote peer for duplicate user information.
- MediaCore ContentID statistics and domain/type lookups now use
  mutation-maintained indexes instead of reparsing the complete registry on
  every read. The System MediaCore page also stops stats polling while hidden,
  rejects overlapping refreshes, and suppresses unchanged rerenders.
- Live search progress now uses a background-owned one-second hub cadence
  without rewriting incomplete response rows, while response payload hydration
  waits for completion or explicitly persisted early mesh results. Search state
  projections also preserve source and wishlist provenance.
- Browse progress now polls once per second without overlapping requests,
  suppresses unchanged state updates, stops before starting in hidden tabs, and
  catches up immediately when the document becomes visible.
- Swarm Analytics now builds all rendered dashboard sections from one peer
  snapshot and one HTTP request, omits unused trend hydration, suppresses
  overlapping or unchanged refreshes, and stops polling while hidden.
- Port Forwarding now loads a bounded available-port preview and VPN member
  counts only when their tabs open, polls authoritative status on a
  non-overlapping visible-only cadence, and renders real forwarder performance
  data instead of synthetic statistics.
- Messaging V2's active room/Pod member rail now uses a non-overlapping,
  visible-only ten-second cadence and preserves cached members on transient
  failures. Pod member responses reuse authorization snapshots and aggregate
  membership timestamps in SQLite instead of materializing retained events.
- App-wide transfer speed polling now uses projected active rows and grouped
  database totals instead of materializing complete download and upload
  histories. Footer speed and network timers pause while the browser document
  is hidden and refresh immediately when it becomes visible.
- The Jobs page and swarm visualization now separate two-second live status
  from ten-second trace aggregation, retain unchanged/cached state, reject
  overlapping requests, and suspend all polling while the browser document is
  hidden.
- Transfer reconciliation now seeds only actionable records through a
  server-watermarked, indexed change feed instead of loading the complete
  download/upload history. Successful history loads in stable 250-record pages
  only when requested, while total tab counts remain accurate. The transfer
  page merges deltas without rerendering unchanged data, rejects overlapping
  requests, and stops polling and applying live events while hidden.
- Active private-chat polling now requests only messages newer than an
  overlapping timestamp cursor, merges them into a bounded client cache, avoids
  overlapping or unchanged refreshes, and stops legacy-chat polling while the
  browser document is hidden. Private-message timeline reads use a composite
  username/timestamp index.
- The legacy Pods route now reuses list metadata, polls Pod metadata every
  sixty seconds, merges channel messages incrementally into a bounded cache,
  and stops all polling while hidden.
- Unified Messaging and the legacy Rooms route now request only room messages
  newer than an overlapping timestamp cursor, merge stable message identities
  into bounded client caches, and avoid repeatedly transferring the retained
  room history. Legacy Rooms also polls membership on a separate bounded
  cadence, suppresses overlapping or unchanged work, and stops all hydration
  while the browser document is hidden.
- Active Pod streams now use incremental cursor polling with a bounded local
  message cache, while shared message polling pauses in hidden tabs and rejects
  overlapping slow refreshes.
- Messaging V2 now consumes channel metadata directly from the saved-pod list,
  refreshes pod/discovery metadata every sixty seconds separately from
  conversation/room lists, deduplicates unchanged or overlapping work, and
  suspends both hydration cadences while hidden.
- Conversation-list unread counts are now projected by SQLite through a
  covering acknowledgement/username index instead of materializing unread
  message bodies and rescanning them once per conversation.
- Footer and System Network aggregate status now comes from one bounded server
  snapshot per consumer instead of browser-side request fan-out; Network polling
  also pauses while hidden and cannot overlap a slow prior cycle.
- Global direct-message navigation polling now uses an indexed scalar activity
  endpoint instead of loading and aggregating full conversation/message rows
  every ten seconds.
- `Program.cs` no longer contains the large experimental feature registration
  graph; multi-source, VirtualSoulfind, MediaCore, pods, mesh/DHT, wishlist,
  relay, FTP, AudioCore metadata, discovery, and notification registrations now
  live under `Bootstrap/ExperimentalFeatureGraphServiceCollectionExtensions`.
- User notes, collections/sharing, identity/friends, and Solid/WebID
  registrations now live under `Bootstrap/UserDataServiceCollectionExtensions`.
- Core database context setup, messaging/search/share/user services, transfer
  services, and source ranking now live under
  `Bootstrap/CoreApplicationServiceCollectionExtensions`.
- Startup options, feature gates, managed state, HTTP clients, Soulseek client
  construction, and `IApplication` hosting now live under
  `Bootstrap/ApplicationHostServiceCollectionExtensions`.
- ASP.NET service registration, including auth, controllers, SignalR, health
  checks, rate limiting, and Swagger, now lives under
  `Bootstrap/WebServiceCollectionExtensions`.
- ASP.NET request-pipeline and endpoint registration now lives under
  `Bootstrap/WebApplicationPipelineExtensions`.
- Top-level runtime service composition now lives under
  `Bootstrap/RuntimeServiceCollectionExtensions`.
- Integration and media-adjacent registrations now live under
  `Bootstrap/IntegrationAndMediaServiceCollectionExtensions`.

### Fixed

- Transfer removal events now carry the stable download-request identity, so
  request-backed rows disappear immediately instead of surviving until a REST
  reconciliation.
- Private-chat unread totals now count the complete conversation rather than
  the bounded message window, and ISO-formatted chat and room timestamps retain
  their real ordering instead of being treated as zero.
- Direct legacy Pod channel URLs now hydrate Pod detail, membership, and
  messages instead of treating route parameters as already-loaded state.
- System Network now normalizes peer and swarm-job response shapes, so live
  mesh peers, discovered clients, and active swarm progress are no longer
  silently discarded as malformed arrays.
- Mesh preview producers now retain ownership of their pipe writer until a
  single final completion, so hash mismatches and peer failures return clean
  end-of-stream responses instead of intermittently leaving readers pending.
- Wishlist results can now persistently ignore one peer folder for one saved
  search without blocking the peer. Ignored folders are excluded from result
  display, hit counts, album candidates, and auto-download selection, can be
  restored from the wishlist editor, and filters support quoted phrase
  exclusions for recurring title collisions.
- Wishlist-adjacent pages now cap large client-side renders: Lidarr seeded
  wishlist rows, search history, collections, contacts, incoming shares, and
  share manifests page their visible rows instead of rendering entire datasets
  at once.
- Release creation now has a guarded helper that verifies the GitHub target,
  branch sync, duplicate tags, and the full release gate before pushing a
  `build-main-*` or `build-dev-*` tag. Post-publish artifact verification now
  fails if checksums, the VPN helper payload, or the bundled footer session
  transfer marker are missing.
- Docker release publishing now copies the VPN helper project into the publish
  stage before running the shared publish script, so container images can include
  the same helper payload as archive releases.
- Release and CI workflows now pin the exact .NET SDK from `global.json`, and
  packaging validation rejects broad SDK selectors that can drift during
  self-contained publish jobs.
- `global.json` is now tracked and validated so remote tag builds see the same
  SDK pin as local release gates.
- Linux distro packages now rewrite bundled VPN helper systemd units to the
  packaged `/usr/bin` helper path and packaged `slskd` service/config names.
- Debian/PPA package builds now avoid Bash-only brace expansion in
  `debian/rules`, and the PPA workflow runs a binary-package preflight before
  uploading source packages to Launchpad.
- Arch installs now print explicit `.pacnew` guidance when pacman preserves an
  existing `/etc/slskd/slskd.yml`.
- The network endpoint ports banner is now a compact one-line notice, and once
  dismissed it stays dismissed across VPN port changes and future installs that
  keep the same browser profile.
- Downloads now accept common Windows-rooted remote Soulseek paths as remote
  store names while still blocking traversal outside the local target
  directory.
- Rescue-mode skips caused by unresolved MusicBrainz Recording IDs now log at
  debug level instead of flooding warning logs for expected metadata misses.
- Failed, aborted, timed-out, rejected, and cancelled transfers no longer appear
  as user-facing "Completed" rows. Hide/clear completed now applies only to
  successful 100% transfers, so retryable downloads stay visible and are not
  bulk-purged as completed.
- Queue-position lookup timeouts now return a controlled timeout response
  instead of producing duplicate application error logs for normal remote peer
  unavailability.
- Distributed Soulseek search requests now accept opaque signed 32-bit tokens, matching live peer traffic and stopping valid negative-token searches from being dropped after login.
- Gluetun VPN status polling now uses a no-redirect local-control HTTP client, so loopback/private configured Gluetun endpoints such as `http://127.0.0.1:8010` are no longer blocked by the public outbound SSRF guard.
- Search API timeout values now honor the documented seconds unit before mapping to Soulseek's millisecond timeout, and multi-source discovery now uses its intended multi-minute search window instead of an accidental sub-second window.
- Background auto-replace searches now charge the Soulseek search safety limiter to an `auto-replace` source instead of the user/API `user` bucket, so stuck-download maintenance cannot starve manual searches. Search completion logs now include source, state, Soulseek response count, mesh response count, merged response count, file count, and duration for live diagnosis.
- Mesh QUIC is now explicitly opt-in after recurring native host coredumps under active MsQuic listeners. UDP overlay remains enabled by default, while QUIC control/data services and clients register only when configured.
- COPR release publishing now installs Ubuntu's MIT Kerberos HTTPS KDC proxy
  and PKINIT packages, Kerberos development headers, and explicitly sources the
  Fedora realm drop-in before using Fedora Kerberos. It also installs
  `requests-gssapi` so `copr-cli` can authenticate to the COPR API with the
  Kerberos ticket during tag and recovery uploads. The Kerberos realm mapping
  now covers COPR's `fedorainfracloud.org` API domain as well as Fedora identity
  hosts, and GSSAPI auth now targets the kerberized `copr.fedoraproject.org`
  API alias. Standalone COPR recovery now uses the same existing-project upload
  shape as tag releases instead of trying to recreate, modify, or override
  project settings during recovery, and emits COPR's server response when
  recovery uploads fail with non-JSON API output.
- Soulseek.NET listener socket disposal from `Soulseek.Network.Tcp.Listener.ListenContinuouslyAsync` is now classified as expected network teardown instead of fake fatal unobserved-task telemetry.
- Verbose startup `[DI]` tracepoints, SPA fallback route serving, and per-request MediaCore CSRF processing logs now emit at debug level; controlled offline user-info responses and shutdown-cancelled background searches no longer log exception/error noise.
- User info lookups now return a controlled `503` for expected Soulseek peer connection failures and timeouts instead of bubbling live peer unavailability as HTTP 500s.
- Release-gate tests now handle expected content-verification cancellation without leaking active probe accounting.
- Mesh transfer terminal failures now populate sanitized error details before exposing the `Failed` state to pollers.
- Messaging slash-command tests now wait for controlled composer state before pressing Enter, preventing full-suite release-gate flakes.

### SongID

- Added a native `SongID` feature in the Search page beside MusicBrainz.
- `SongID` accepts YouTube URLs, Spotify URLs, direct text queries, and server-side local file paths.
- Added a durable background queue with configurable concurrent workers, persisted runs, restart recovery, and live SignalR progress updates.
- Added richer evidence fusion across MusicBrainz, AcoustID, SongRec, transcripts, OCR, comments, chapters, provenance, perturbation probes, Panako, Audfprint, and Demucs-backed artifact generation.
- Added ranked handoff actions for song search, album preparation, direct album jobs, discography jobs, and multi-candidate fan-out.
- Added split identity vs synthetic assessments and unobtrusive forensic / synthetic UI surfacing so strong identity still drives acquisition decisions.
- **Forensic context** — lane-level forensic matrix (identity, provenance, spectral, descriptor, lyrics, structural, generator family, confidence), `topEvidenceFor`/`topEvidenceAgainst`, `perturbationStability`, `qualityClass`, `knownFamilyScore`, and C2PA provenance hints now arrive with every run.
- **Infinite queue & configurable workers** — the queue now keeps queue position/worker slot in SQLite, recovers on restart, accepts unlimited submissions, and obeys `songid-max-concurrent-runs` / `SONGID_MAX_CONCURRENT_RUNS` so `X` workers process runs at a time.
- **Ranked acquisition & mix planning** — track/album/discography options rely on identity-first scoring, mix decomposition yields `Split Into Track Plans`, and candidate fan-outs (`Search Top Candidates`) preserve Byzantine/quality ordering for actionable downloads.

### Discovery Graph / Constellation

- Added the first native `Discovery Graph` / `Constellation` substrate.
- Added backend graph API/service for typed, weighted, explainable neighborhoods seeded from SongID runs, tracks, albums, artists, and fallback metadata seeds.
- Added graph launch surfaces in SongID, MusicBrainz lookup, and search-result cards.
- Added inline mini-map and modal graph UI with edge filtering, recentering, queue-nearby actions, pinning, comparison overlays, and saved branch snapshots.
- Added MusicBrainz artist release-group expansion and richer edge provenance / score-component / evidence payloads for graph explanations.
- Added broader search summon points plus an in-page atlas panel with semantic zoom controls and saved-branch restore.
- Added a dedicated `/discovery-graph` route plus modal handoff into that full atlas workspace.
- Enabled semantic zoom lockstep across mini-map, drawer modal, and atlas so provenance/score-component detail follows any neighborhood while graph actions (`queue nearby`, downloads, compare) reuse that same substrate.

### Security

- Narrowly scoped integration credentials are restricted from general-purpose
  real-time hubs, while password and wildcard sessions retain existing access.
- Federation relationship removal is bound to the verified sender and exact
  actor identity. Public-key verification and standard inbox JSON field handling
  correctly accept valid signed messages and reject altered ones.


## [0.24.5-slskdn.52] - 2026-03-15

### Now Playing / Scrobble Integration (#39)

- **NowPlayingService**: Tracks current playing track (artist, title, album) in-process.
- **REST API** at `GET/PUT/DELETE /api/v0/nowplaying`:
  - `PUT` accepts `{ "artist": "...", "title": "...", "album": "..." }` to set current track
  - `DELETE` clears current track (pause/stop)
  - `GET` returns current track or null
- **Webhook receiver** at `POST /api/v0/nowplaying/webhook`:
  - **Plex**: Auto-detects multipart/form-data payload, handles `media.play`, `media.resume`, `media.scrobble` (set), `media.pause`, `media.stop` (clear)
  - **Jellyfin / Emby**: Auto-detects `NotificationType` JSON field, handles `PlaybackStart`, `PlaybackProgress`, `PlaybackStop`
  - **Generic JSON**: Fallback for Tautulli and other senders; `event: "play"|"stop"|"pause"` with `artist`, `title`, `album` fields
- **User description**: When a track is playing, the Soulseek user description shown to peers automatically appends `🎵 Listening to: Artist – Title`
- **Frontend lib**: `src/web/src/lib/nowPlaying.js` helper functions for calling the API

### Cancel Transfers on Blacklist (#21)

- When a user is added to the blacklist via config update, `OptionsMonitor_OnChange` now detects newly-blacklisted usernames by diffing old and new `Groups.Blacklisted.Members`.
- All active (non-completed) uploads and downloads belonging to those users are immediately cancelled via `TryCancel()`.
- Logged at Information level: `"Cancelling active transfers for N newly blacklisted user(s): [...]"`

### Per-Group File Type Restrictions (#56)

- Added `AllowedFileTypes string[]` to `Options.GroupsOptions.UploadOptions` (the upload config shared by all user groups including user-defined groups, Default, and Leechers).
- When `AllowedFileTypes` is non-empty for a group, the upload handler checks the requested file's extension against the list before enqueuing.
- Rejects with `DownloadEnqueueException("File type .ext is not permitted.")` if not matched (case-insensitive).
- Empty list (default) means no restriction — fully backwards-compatible.

### Prometheus Metrics UI (#59)

- New **Metrics** tab in System section (`/system/metrics`).
- Fetches KPI data from `GET /api/v0/telemetry/metrics/kpi` (existing endpoint).
- Renders four grouped statistic panels: **Transfers**, **Search**, **Process**, **Network**.
- Full `slskd_*` metrics table showing name, type, value, and help text.
- Refresh button with last-updated timestamp.
- Added `src/web/src/lib/telemetry.js` with `getMetrics()` and `getKpiMetrics()` helpers.

### UserCard Score Badges Everywhere (#62)

- Private chat message sender names (`ChatSession.jsx`) now wrapped in `<UserCard>` showing reputation badge and stats.
- Room message sender names (`RoomSession.jsx`) now wrapped in `<UserCard>`.
- Room user list entries (`RoomSession.jsx` inline panel) now wrapped in `<UserCard>`.
- Added `UserCard` import to `RoomSession.jsx`.

### Solid Integration: WebID and Solid-OIDC Support

- **Solid Compatibility Layer**: Optional integration with Solid (WebID + Solid-OIDC) for decentralized identity and Pod-backed metadata:
  - **WebID Resolution**: Resolve WebID profiles and extract OIDC issuer information
  - **Solid-OIDC Client ID Document**: Serves compliant JSON-LD Client ID document at `/solid/clientid.jsonld` (dereferenceable per Solid-OIDC spec)
  - **SSRF Hardening**: Comprehensive security controls for WebID/Pod fetches:
    - Host allow-list (`AllowedHosts`) - empty list denies all remote fetches by default
    - HTTPS-only enforcement (configurable `AllowInsecureHttp` for dev/test only)
    - Private IP and localhost blocking
    - Response size limits (`MaxFetchBytes`: 1MB default)
    - Timeout enforcement (`TimeoutSeconds`: 10s default)
  - **API Endpoints**: 
    - `GET /api/v0/solid/status` - Check Solid integration status
    - `POST /api/v0/solid/resolve-webid` - Resolve a WebID and extract OIDC issuers
  - **Frontend UI**: New "Solid" navigation item and settings page for WebID resolution
  - **Configuration**: New `feature.Solid` flag (default: `true`) and `solid` options block
  - **Security by Default**: Feature enabled by default but non-functional until `AllowedHosts` is explicitly configured (SSRF safety)
  - **RDF Parsing**: Uses dotNetRDF library for parsing WebID profiles (Turtle and JSON-LD formats)
- **Future Extensions** (not in MVP):
  - Full OIDC Authorization Code + PKCE flow
  - Token storage (encrypted via Data Protection)
  - DPoP proof generation
  - Pod metadata read/write (playlists, sharelists)
  - Type Index / SAI registry discovery
  - Access control (WAC/ACP) writers

### Swarm Analytics: Advanced Metrics and Reporting

- **Swarm Analytics Service**: Comprehensive analytics and reporting for swarm behavior:
  - **Performance Metrics**: Overall swarm performance (success rate, average speed, duration, bytes downloaded, chunk metrics)
  - **Peer Rankings**: Top-performing peers ranked by reputation, RTT, throughput, chunk success rate
  - **Efficiency Metrics**: Chunk utilization, peer utilization, redundancy factor, time-to-first-byte
  - **Historical Trends**: Time-series data for success rates, speeds, durations, sources used
  - **Recommendations Engine**: Automated optimization recommendations based on current performance
  - **API Endpoints**: RESTful API for accessing all analytics data (`/api/v0/swarm/analytics/*`)
  - **Frontend Dashboard**: New "Swarm Analytics" tab in System UI with visualizations and metrics
- **Advanced Discovery Service**: Enhanced peer discovery with improved algorithms:
  - **Content-Aware Matching**: Similarity scoring based on filename, size, and metadata
  - **Match Type Classification**: Exact, variant, fuzzy, and metadata-based matching
  - **Peer Ranking**: Multi-factor ranking (similarity, performance, availability, metadata confidence)
  - **Fuzzy Matching**: Improved algorithms for finding similar content variants
- **Adaptive Scheduling**: Machine learning-inspired chunk assignment optimization:
  - **Learning from Feedback**: Records chunk completion data and adapts weights dynamically
  - **Factor Correlation Analysis**: Automatically adjusts weights for reputation, throughput, and RTT based on success correlation
  - **Performance-Based Adaptation**: Adapts scheduling strategy every N completions based on recent performance
  - **Statistics Tracking**: Tracks peer learning data and provides adaptive scheduling statistics
- **Cross-Domain Swarming**: Extended swarm capabilities to non-music content domains:
  - **Domain-Aware Swarming**: Swarm downloads now work for Movies, TV, Books, and GenericFile domains
  - **Backend Selection Rules**: Domain-specific backend selection (Soulseek only for Music, mesh/DHT/torrent/HTTP for others)
- **Multi-Domain Support**: New content domain providers:
  - **Movie Domain**: IMDB ID matching, hash verification, backend selection (mesh/DHT/torrent/HTTP/local only)
  - **TV Domain**: TVDB ID matching, season/episode matching, series organization
  - **Book Domain**: ISBN-based matching, format detection (PDF, EPUB, MOBI, etc.)
  - **Domain Providers**: `IMovieContentDomainProvider`, `ITvContentDomainProvider`, `IBookContentDomainProvider` interfaces and implementations
  - **ContentDomain Enum**: Extended with `Movie`, `Tv`, and `Book` domains

### Distributed Tracing: OpenTelemetry Support

- **OpenTelemetry Integration**: Comprehensive distributed tracing infrastructure:
  - **Configuration**: New `telemetry.tracing` options in config:
    - `enabled`: Enable/disable tracing (default: false)
    - `exporter`: Exporter type - console, jaeger, or otlp (default: console)
    - `jaeger_endpoint` and `jaeger_port`: Jaeger OTLP collector configuration
    - `otlp_endpoint`: OTLP collector endpoint URL
  - **Activity Sources**: Dedicated activity sources for different components:
    - `slskdn.Transfers.MultiSource`: Swarm download operations
    - `slskdn.Mesh`: Mesh network operations (DHT queries, overlay transfers)
    - `slskdn.HashDb`: HashDb lookup and storage operations
    - `slskdn.Search`: Search operations
  - **Swarm Download Tracing**:
    - Traces entire swarm download lifecycle with tags for:
      - Download ID, filename, size, sources count, chunk size
      - Success/failure status, duration, sources used, speed
      - Individual chunk completion events with peer and performance data
  - **Mesh Network Tracing**:
    - DHT operations: `mesh.dht.store`, `mesh.dht.find_value`, `mesh.dht.find_node`
    - Tags include: key, value size, TTL, success status, nodes found
  - **HashDb Tracing**:
    - `hashdb.lookup` operations with cache hit/miss tracking
    - Tags include: lookup key, cache hit status, found status
  - **Search Tracing**:
    - `search.start` operations with query, scope, and provider information
  - **Automatic Instrumentation**: ASP.NET Core and HTTP client instrumentation enabled
  - **Exporters**: Support for console (default), Jaeger, and OTLP exporters
  - **Documentation**: Updated `config/slskd.example.yml` with telemetry configuration examples

### CI/CD Enhancements

- **Performance Regression Testing**: Automated performance benchmark execution in CI:
  - Runs BenchmarkDotNet suite on pull requests and scheduled runs
  - Compares results against baseline to detect performance regressions
  - Uploads benchmark results as artifacts for analysis
  - Reports significant performance degradation (>10%) in workflow summary
- **Load Testing**: Automated load testing with k6:
  - Tests API endpoints under sustained load (up to 100 concurrent users)
  - Ramp-up and ramp-down phases to simulate realistic traffic patterns
  - Performance thresholds: 95% of requests < 500ms, 99% < 1s, error rate < 1%
  - Uploads load test results as JSON artifacts
- **Security Scanning**: Comprehensive security analysis:
  - **CodeQL Analysis**: Static code analysis for C# and JavaScript:
    - Security and quality queries enabled
    - Results available in GitHub Security tab
  - **Container Security (Trivy)**: Docker image vulnerability scanning:
    - Scans for HIGH and CRITICAL vulnerabilities
    - Reports on base images and dependencies
  - **Dependency Scanning**: Automated vulnerability detection:
    - NuGet package vulnerability scanning (transitive dependencies included)
    - npm audit for frontend dependencies (moderate+ severity)
- **Workflow Configuration**: New `.github/workflows/ci-enhancements.yml`:
  - Runs on pull requests, pushes to master, tags, and weekly schedule
  - Parallel execution of performance, load, and security tests
  - Artifact retention for 30 days
  - Comprehensive reporting in workflow summaries

### Performance Benchmarking Suite

- **Comprehensive BenchmarkDotNet Suite**: Performance benchmarks for critical components:
  - **HashDb Benchmarks**: Database query performance, caching effectiveness:
    - Lookup performance (with/without cache, cache hits)
    - Query performance (size-based queries, sequential/parallel lookups)
    - Write performance (single and batch hash storage)
    - Statistics retrieval
  - **Swarm Benchmarks**: Swarm download operations:
    - Chunk size optimization for various file sizes (100MB-1GB) and peer counts (5-20)
    - Chunk assignment performance (sequential and parallel)
    - Peer selection based on metrics (throughput, queue length, free slots, reputation)
  - **API Benchmarks**: API endpoint performance:
    - GET endpoint performance (session, application state, HashDb stats, paginated jobs)
    - POST endpoint performance (create search)
    - Concurrent request handling (10, 50, 100 concurrent requests)
  - **Transport Benchmarks**: Already existed, now part of comprehensive suite
  - **Benchmark Project**: New `tests/slskd.Tests.Performance/` project with proper BenchmarkDotNet configuration
  - **Documentation**: `README.md` with usage instructions, performance targets, and CI integration guidance

### Developer Documentation

- **Enhanced Contributing Guide**: Comprehensive developer resources:
  - **Development Setup**: Prerequisites, initial setup, build instructions
  - **Development Workflow**: Feature branch workflow, testing, committing
  - **Code Style Guidelines**: C# and React style guidelines with examples
  - **Copyright Headers**: Policy for new vs existing files, fork-specific directories
  - **Testing**: Running tests, writing tests, test organization
  - **Debugging**: Backend and frontend debugging instructions, common scenarios
  - **Project Structure**: Overview of directory layout
  - **Code Review Checklist**: Pre-PR checklist
  - **Getting Help**: Community resources
- **API Documentation Guide**: Complete API reference:
  - **Base URL and Versioning**: API structure and versioning scheme
  - **Authentication**: Cookie, JWT, and API key authentication methods
  - **Response Formats**: Success and error (ProblemDetails) response formats
  - **Complete Endpoint Reference**: All API endpoints organized by category:
    - Core APIs (Application, Server, Session)
    - Search APIs (Searches, Search Actions)
    - Transfer APIs (Downloads, Uploads)
    - Multi-Source/Swarm APIs (Swarm Downloads, Tracing, Fairness)
    - Job APIs
    - User APIs (Users, User Notes)
    - Pod APIs (Pods, Pod Messages)
    - Collections & Sharing APIs
    - Mesh APIs
    - Hash Database APIs
    - Wishlist APIs
    - Capabilities APIs
    - Streaming APIs
    - Library Health APIs
    - Options & Configuration
  - **Common Patterns**: Pagination, filtering, sorting
  - **Error Handling**: HTTP status codes and error responses
  - **Rate Limiting**: Rate limit information and headers
  - **API Discovery**: How to find endpoints in source code
  - **Frontend API Libraries**: Usage of API client libraries
  - **WebSocket/SignalR**: Real-time update mechanisms
  - **Code Examples**: curl and JavaScript examples
  - **Best Practices**: API usage guidelines

### User Documentation

- **Getting Started Guide**: Comprehensive guide for new users:
  - Installation instructions for all platforms (Linux, macOS, Windows, Docker, package managers)
  - Initial configuration (password, directories, Soulseek credentials)
  - Basic usage (searching, downloading, wishlist)
  - Security best practices
  - Next steps and community resources
- **Troubleshooting Guide**: Complete troubleshooting reference:
  - Connection issues (Soulseek, Mesh/Pod networks)
  - Download problems (stuck, slow, failing downloads)
  - Performance issues (high CPU/memory usage)
  - Configuration problems (saving, validation)
  - Web interface issues (loading, authentication)
  - Feature-specific troubleshooting (swarm, wishlist, collections, streaming)
  - Log analysis and debug techniques
  - Community support resources
- **Advanced Features Walkthrough**: Detailed guide for advanced features:
  - Swarm downloads (operation, monitoring, optimization)
  - Scene ↔ Pod bridging (unified search, privacy)
  - Collections & sharing (creation, sharing, backfill)
  - Streaming (operation, limitations)
  - Wishlist & background search
  - Auto-replace stuck downloads
  - Smart search ranking
  - Multiple download destinations
  - Job management & monitoring
  - Performance tuning and configuration tips
- **Documentation Index**: Updated `docs/README.md` with links to all new guides

### Swarm Performance Tuning

- **Adaptive Chunk Size Optimization**: Intelligent chunk sizing for swarm downloads:
  - **Automatic Optimization**: Chunk size automatically optimized based on file size, peer count, and performance metrics
  - **Heuristics**:
    - Base calculation targets 2 chunks per peer for optimal parallelism (4-200 chunks total)
    - Throughput-based adjustment: larger chunks for high throughput (>5 MB/s), smaller for low (<1 MB/s)
    - Latency-based adjustment: smaller chunks for high latency (>500ms), larger for low (<100ms)
  - **Constraints**: 64KB minimum, 10MB maximum, aligned to 64KB boundaries
  - **Integration**: Automatically used when chunk size not explicitly specified in download request
  - **Service**: `IChunkSizeOptimizer` interface with `ChunkSizeOptimizer` implementation
  - **Fallback**: Gracefully falls back to default 512KB if optimizer unavailable

### Real-time Swarm Visualization

- **Swarm Visualization Dashboard**: Comprehensive real-time visualization for active swarm downloads:
  - **Job Overview**: Real-time metrics including chunks completed/total, active workers, chunks/second rate, estimated time remaining, and overall progress bar
  - **Peer Contributions Table**: Detailed peer performance analysis:
    - Chunks completed, failed, and timed out per peer
    - Bytes served per peer
    - Success rate calculation with color-coded progress indicators (green ≥80%, yellow ≥50%, red <50%)
    - Peers sorted by contribution (bytes served, then chunks completed)
  - **Chunk Assignment Heatmap**: Visual grid representation of chunk completion:
    - Green squares for completed chunks
    - Gray squares for pending chunks
    - Tooltips showing chunk index and status
    - Auto-scaling grid layout based on total chunks
    - Legend for color coding
  - **Performance Metrics**: Trace summary data including:
    - Total events count
    - Duration calculation (parsed from TimeSpan format)
    - Rescue mode indicator (orange warning icon when rescue invoked)
    - Bytes by source/backend breakdown (sorted by contribution)
  - **Integration**: Accessible via "View Details" button on active swarm jobs in Jobs dashboard
  - **Modal Interface**: Large modal dialog for detailed visualization
  - **Auto-refresh**: Updates every 2 seconds for real-time monitoring
  - **API Integration**: Uses `/api/v0/multisource/jobs/{jobId}` for job status and `/api/v0/traces/{jobId}/summary` for detailed peer contributions

### Advanced Search UI Enhancements

- **Quality Presets**: Quick filter buttons in Advanced Filters modal:
  - "High Quality (320kbps+)" - Sets minimum bitrate to 320kbps, lossy only
  - "Lossless Only" - Filters for lossless files with min 16-bit depth and 44.1kHz sample rate
  - "Clear Quality" - Resets all quality-related filters
- **Sample Rate Filtering**: Added minimum sample rate (Hz) input field in Advanced Filters modal
  - Supports `minsr:` filter syntax (e.g., `minsr:44100`)
  - Filters files by sample rate when specified
- **Format/Codec Filtering**: Added file extension filtering in Advanced Filters modal
  - Supports filtering by file extensions (e.g., flac, mp3, wav, m4a)
  - Supports `ext:` filter syntax (e.g., `ext:flac,mp3`)
  - Space or comma-separated extensions
- **Enhanced Source Selection UI**: Improved provider selection for Scene ↔ Pod Bridging:
  - More prominent display with background highlight
  - Icons for Pod/Mesh (sitemap) and Soulseek Scene (globe)
  - Clear labels: "Pod/Mesh" and "Soulseek Scene"
  - Warning message when no sources selected
  - Better visual hierarchy and spacing

### Enhanced Job Management UI

- **Jobs Dashboard** (`/system/jobs`): Comprehensive job management interface with:
  - **Analytics Overview**: Total jobs, active jobs, completed jobs, and job type breakdown
  - **Active Swarm Downloads**: Real-time display of multi-source downloads with:
    - Progress bars and percentage completion
    - Active sources count
    - Download speed (chunks/second)
    - Estimated time remaining
    - Auto-refresh every 5 seconds
  - **Job List**: Filterable and sortable table of all jobs (discography, label crate) with:
    - Filter by type (discography, label crate)
    - Filter by status (pending, running, completed, failed)
    - Sort by created date, status, or ID (ascending/descending)
    - Pagination support (20 jobs per page)
    - Progress visualization for releases (completed/total/failed)
    - Color-coded status indicators
  - **API Integration**: Full integration with `/api/jobs` endpoint supporting filtering, sorting, and pagination

### Testing Expansion

- **Bridge Protocol Validation Tests**: Comprehensive protocol format validation for `SoulseekProtocolParser`:
  - Edge case handling: empty strings, Unicode characters, long queries (1000+ chars), special characters
  - Error handling: invalid message lengths, truncated messages
  - Roundtrip validation: write-then-read verification for all message types
  - Response format validation: login and search response structure
  - 13 tests covering protocol compatibility and robustness
- **Bridge Performance Tests**: Load and performance benchmarks:
  - Concurrent operations: 10 parallel streams (1000 msg/s throughput)
  - Latency measurements: average, P95, P99 percentiles (<10ms average)
  - Large message handling: 10KB queries
  - High-volume scenarios: 10,000 small messages (>5000 msg/s)
  - Memory efficiency: <5KB per message with proper cleanup
  - Rapid connect/disconnect: 100 cycles (>50 ops/s)
  - 7 performance tests validating scalability
- **Protocol Contract Tests**: Enhanced Soulseek protocol compliance tests:
  - `Should_Login_And_Handshake`: Improved assertions and graceful skipping
  - `Should_Send_Keepalive_Pings`: Reduced wait time, connection state verification
  - `Should_Handle_Disconnect_And_Reconnect`: Disconnect detection and reconnection verification
  - All 6 tests passing (gracefully skip when Soulfind unavailable)
- **Bridge E2E Test Infrastructure**: Full instance test harness:
  - `SlskdnFullInstanceRunner`: Starts actual slskdn process for TCP listener tests
  - Auto-discovers binary from build output or `SLSKDN_BINARY_PATH` environment variable
  - Generates test configuration with bridge enabled
  - Graceful degradation: tests skip with helpful instructions when binary unavailable
  - 5 Bridge E2E tests updated to use full instance when available

### Scene ↔ Pod Bridging

- **Scene ↔ Pod Bridging** (`feature.scene_pod_bridge`): Unified search experience aggregating results from Pod/Mesh and Soulseek Scene networks.
  - **Unified Search**: Single search query hits both Pod/Mesh and Soulseek Scene providers in parallel, with automatic result merging and deduplication.
  - **Provenance Badges**: Clear visual indicators (POD, SCENE, POD+SCENE) showing result source in search results.
  - **Intelligent Action Routing**: 
    - **Pod Results**: Downloads from remote mesh peers if not available locally, or streams via streaming API. Falls back to mesh directory lookup if peer ID missing.
    - **Scene Results**: Uses standard Soulseek download pipeline.
  - **Provider Selection**: UI checkboxes to select which providers to search (Pod and/or Scene).
  - **Remote Pod Downloads**: Full implementation of downloading Pod content from remote mesh peers when not available locally, with proper error handling (404 for peer not found, 502 for fetch failures).
  - **Privacy Protection**: Pod peer identities never exposed to Soulseek Scene network. No auto-advertising of Pod content to Scene.
  - **API Endpoints**:
    - `POST /api/v0/searches/{searchId}/items/{itemId}/download` - Download a search result item (routes based on source)
    - `POST /api/v0/searches/{searchId}/items/{itemId}/stream` - Stream a pod result (returns 400 for scene results)
  - **Feature Flag**: `feature.scene_pod_bridge` (default: `true`). When disabled, search behaves exactly as before.
  - **Deduplication**: Results deduplicated by hash (if available) or normalized filename + size. Pod results preferred when duplicates found.
  - **Tests**: 8 integration tests covering remote pod downloads, fallback to mesh directory, error handling, and stream URL generation. All E2E tests updated for new functionality.
  - **Documentation**: Comprehensive feature documentation in `docs/FEATURES.md` covering architecture, privacy guarantees, configuration, and use cases.

### Identity & Friends (Phases 1-4)

- **Identity & Friends System** (`feature.identity_friends`): Human-friendly peer addressing and discovery system for the sharing workflow.
  - **Peer Profiles**: Signed `PeerProfile` objects with display names, friend codes, capabilities, and endpoints. Ed25519 cryptographic signing prevents spoofing.
  - **Contact Management**: Local contact list with nicknames (petnames), verification status, and cached endpoints. SQLite-backed `IdentityDbContext`.
  - **Friend Codes**: Short, shareable Base32-encoded codes (e.g., `ABCD-EFGH-IJKL-MNOP`) derived from PeerId for easy copy/paste.
  - **Invite Links**: Self-contained `FriendInvite` payloads encoded as `slskdn://invite/...` links with QR code support (WebUI pending).
  - **mDNS LAN Discovery**: Automatic peer discovery on local networks via mDNS (`_slskdn._tcp.local`). Raw UDP socket implementation for advertising; Zeroconf library for browsing.
  - **ShareGroups Integration** (Phase 3): `ShareGroupMember` now supports optional `PeerId` for Contact-based members. API supports adding members by PeerId or UserId (legacy). Manifest includes owner contact nickname when available.
  - **WebUI Components** (Phase 4): Complete UI implementation including:
    - Contacts page (`/contacts`) with All/Nearby tabs, Add Friend modal, Create Invite modal
    - ShareGroups page (`/sharegroups`) with Contacts dropdown for adding members
    - "Shared with me" page (`/shared`) displaying incoming shares with contact nicknames and manifest viewing
    - Collections API client library for all sharing operations
  - **API Endpoints**:
    - `GET/PUT /api/v0/profile/me` - Manage own profile
    - `GET /api/v0/profile/{peerId}` - Fetch peer profiles (public)
    - `POST /api/v0/profile/invite` - Generate invite links
    - `GET/POST/PUT/DELETE /api/v0/contacts` - Contact CRUD
    - `POST /api/v0/contacts/from-invite` - Add contact from invite
    - `POST /api/v0/contacts/from-discovery` - Add contact from LAN discovery
    - `GET /api/v0/contacts/nearby` - Browse nearby peers
    - `GET /api/v0/sharegroups/{id}/members?detailed=true` - Get members with contact info
  - **Feature Flag**: `feature.identity_friends` (default: `false`). All endpoints return 404 when disabled.
  - **Dependencies**: `Zeroconf` 3.0.30 (for mDNS browsing), `Microsoft.EntityFrameworkCore.Sqlite` (for contact storage).
  - **Tests**: 90 unit tests covering ProfileService, ContactService, ContactRepository, ProfileController, ContactsController, LanDiscoveryService, and MdnsAdvertiser.

- **Identity & Friends System** (`feature.identity_friends`): Human-friendly peer addressing and discovery system for the sharing workflow.
  - **Peer Profiles**: Signed `PeerProfile` objects with display names, friend codes, capabilities, and endpoints. Ed25519 cryptographic signing prevents spoofing.
  - **Contact Management**: Local contact list with nicknames (petnames), verification status, and cached endpoints. SQLite-backed `IdentityDbContext`.
  - **Friend Codes**: Short, shareable Base32-encoded codes (e.g., `ABCD-EFGH-IJKL-MNOP`) derived from PeerId for easy copy/paste.
  - **Invite Links**: Self-contained `FriendInvite` payloads encoded as `slskdn://invite/...` links with QR code support (WebUI pending).
  - **mDNS LAN Discovery**: Automatic peer discovery on local networks via mDNS (`_slskdn._tcp.local`). Raw UDP socket implementation for advertising; Zeroconf library for browsing.
  - **API Endpoints**:
    - `GET/PUT /api/v0/profile/me` - Manage own profile
    - `GET /api/v0/profile/{peerId}` - Fetch peer profiles (public)
    - `POST /api/v0/profile/invite` - Generate invite links
    - `GET/POST/PUT/DELETE /api/v0/contacts` - Contact CRUD
    - `POST /api/v0/contacts/from-invite` - Add contact from invite
    - `POST /api/v0/contacts/from-discovery` - Add contact from LAN discovery
    - `GET /api/v0/contacts/nearby` - Browse nearby peers
  - **Feature Flag**: `feature.identity_friends` (default: `false`). All endpoints return 404 when disabled.
  - **Dependencies**: `Zeroconf` 3.0.30 (for mDNS browsing), `Microsoft.EntityFrameworkCore.Sqlite` (for contact storage).
  - **Tests**: 90 unit tests covering ProfileService, ContactService, ContactRepository, ProfileController, ContactsController, LanDiscoveryService, and MdnsAdvertiser.

### ShareGroups, Collections & Sharing (Phases 1-2)

- **ShareGroups & Collections System** (`feature.collections_sharing`): Content organization and sharing infrastructure.
  - **ShareGroups**: User-created groups for organizing sharing audiences. `ShareGroup` and `ShareGroupMember` entities with ownership and membership management.
  - **Collections**: Content collections (ShareLists and Playlists) with `Collection` and `CollectionItem` entities. Support for ordering via `Ordinal`.
  - **Share Grants**: Capability-based sharing via `ShareGrant` with `SharePolicy` (AllowStream, AllowDownload, AllowReshare, expiry, concurrency limits).
  - **Content Resolution**: `IContentLocator` interface and implementation for resolving content IDs to local file paths and MIME types. Integrates with `IShareRepository` and `IsAdvertisable` checks.
  - **Share Tokens**: `IShareTokenService` with JWT-based capability tokens. Tokens include collection ID, capabilities, expiry, and max concurrent streams. Constant-time validation.
  - **Sharing Service**: `ISharingService` for managing groups, collections, share grants, and manifest generation.
  - **Repositories**: `IShareGroupRepository`, `ICollectionRepository`, `IShareGrantRepository` with SQLite-backed implementations via `CollectionsDbContext`.
  - **API Endpoints**:
    - `GET/POST/PUT/DELETE /api/v0/sharegroups` - ShareGroup CRUD
    - `GET/POST/PUT/DELETE /api/v0/collections` - Collection CRUD
    - `GET/POST/PUT/DELETE /api/v0/shares` - ShareGrant CRUD
    - `POST /api/v0/shares/{id}/token` - Generate share token
    - `GET /api/v0/shares/{id}/manifest` - Get collection manifest
  - **Feature Flag**: `feature.collections_sharing` (default: `false`). All endpoints return 404 when disabled. (Note: flag name in code is `CollectionsSharing`).
  - **Tests**: 67 unit tests across 5 test files covering ShareTokenService, SharingService, CollectionsController, ShareGroupsController, and SharesController.

### Streaming (Phases 3-4)

- **Streaming API** (`feature.streaming`): HTTP range request support for content streaming.
  - **Stream Session Limiting**: `IStreamSessionLimiter` with configurable concurrent stream limits per content ID.
  - **Stream Endpoint**: `GET /api/v0/streams/{contentId}` with support for HTTP range requests (`Range` header).
  - **Authentication**: Supports both token-based (share tokens) and normal user authentication.
  - **Content Resolution**: Uses `IContentLocator` (from Phase 1) to resolve content IDs to local file paths and MIME types.
  - **Session Management**: `ReleaseOnDisposeStream` wrapper ensures limiter slots are released on stream disposal.
  - **Feature Flag**: `feature.streaming` (default: `false`). Endpoint returns 404 when disabled.
  - **Tests**: Comprehensive unit tests for StreamSessionLimiter, ReleaseOnDisposeStream, ContentLocator, and StreamsController.

- **Mesh Search Improvements** (Phase 4): Enhanced mesh search with better deduplication and query limits.
  - **Query Limits**: Added query length cap (256 chars) and time cap (5 seconds) in `MeshSearchRpcHandler` to prevent abuse.
  - **Enhanced DTOs**: `MeshSearchFileDto` now includes optional `MediaKinds`, `ContentId`, and `Hash` fields for better content matching.
  - **Improved Deduplication**: `SearchResponseMerger` now uses normalized filenames (case-insensitive, path separator normalization) for cross-response deduplication.
  - **Media Kind Detection**: Automatic detection of media types (Music, Video, Image) from file extensions in `MeshSearchRpcHandler`.
  - **MeshParallelSearch Flag**: `feature.mesh_parallel_search` flag wired to enable parallel mesh search alongside Soulseek. Works with `VirtualSoulfind.MeshSearch.Enabled` (either flag can enable).

- **Relay Streaming Fallback** (Phase 5): ContentId-based streaming through relay agents.
  - **IMeshContentFetcher**: New interface and implementation for fetching content from mesh overlay network by ContentId with size and hash validation.
  - **Relay Streaming Endpoint**: `GET /api/v0/relay/streams/{contentId}` endpoint for streaming content through relay agents using ContentId instead of filename.
  - **Content Resolution**: Endpoint resolves ContentId to filename via `IContentLocator`, then uses existing relay file streaming mechanism.
  - **Feature Flag**: `feature.streaming_relay_fallback` (default: `false`). Endpoint returns 503 when disabled.
  - **Validation**: `MeshContentFetcher` performs size and SHA-256 hash validation when expected values are provided.

### Mesh Network Resilience

- **Fault-Tolerant UDP Overlay**: UDP overlay server now gracefully handles port binding failures, allowing mesh to operate behind firewalls.
  - **Graceful Degradation**: When UDP overlay port (default 50305) cannot be bound (e.g., already in use, firewall blocked), the mesh continues operating in degraded mode.
  - **Preserved Functionality**: DHT operations, relay/beacon services, and hole punching continue to function even without direct inbound UDP connections.
  - **Clear Logging**: Warning messages clearly explain degraded mode operation and which features remain available.
  - **Consistent Error Handling**: Matches the fault-tolerant pattern used by QUIC overlay servers.
  - **Use Case**: Enables mesh operation behind firewalls where port forwarding is not available, relying on outbound connections, DHT, and relay services for connectivity.

### User Interface Improvements

- **Logs Page Enhancements**: Improved log viewing experience with reduced noise and filtering capabilities.
  - **CSRF Logging Noise Reduction**: CSRF Debug logs for safe HTTP methods (GET, HEAD, OPTIONS, TRACE) and successful validations changed to Verbose level, reducing noise in default log views.
  - **Log Level Filtering**: Added filter buttons (All, Info, Warn, Error, Debug) to the logs page for easy filtering by log level.
  - **Log Count Display**: Shows count of filtered logs vs total logs (e.g., "Showing 50 of 500 logs").
  - **Improved Readability**: Users can now focus on specific log levels (warnings, errors) without scrolling through verbose debug information.

### Security & hardening (40-fixes, dev/40-fixes)

- **EnforceSecurity** (`web.enforce_security`): When `true`, enables strict auth, CORS, startup checks via `HardeningValidator`, and automatic 400 for invalid `ModelState` (`SuppressModelStateInvalidFilter = false`). Use for repeatable hardened testing.
- **Passthrough AllowedCidrs** (`web.authentication.passthrough.allowed_cidrs`): Optional CIDR allowlist for no-auth mode (e.g. `127.0.0.1/32,::1/128`) in addition to loopback. PR-03.
- **CORS** (`web.cors`): `allowed_headers`, `allowed_methods`; allowlist semantics; no `AllowAll` + `AllowCredentials`. PR-04.
- **Exception handler**: RFC 7807 `ProblemDetails`, `traceId`; in Production, generic detail (no internal leak). PR-05.
- **Dump endpoint**: Returns **501** when dump creation fails (e.g. `dotnet-dump` not on PATH, `DiagnosticsClient` failure) with instructions. `diagnostics.allow_memory_dump`, `allow_remote_dump`; admin-only, local-only when `allow_remote_dump` false. PR-06.
- **ModelState / RejectInvalidModelState**: `web.api.reject_invalid_model_state`; when Enforce, invalid payloads return 400 with consistent `ValidationProblemDetails`. PR-07.
- **MeshGateway**: Chunked POST supported; bounded body read; 413 on over-limit. PR-08.
- **Kestrel MaxRequestBodySize** (`web.max_request_body_size`): Configurable request body limit (default 10 MB). PR-09a.
- **Rate limit fed/mesh**: `Burst_federation_inbox_*`, `Burst_mesh_gateway_*` policies; `web.rate_limiting`. PR-09b.
- **QuicDataServer**: Read/limits aligned with `GetEffectiveMaxPayloadSize`. §8.
- **Metrics Basic Auth**: Constant-time comparison (`CryptographicOperations.FixedTimeEquals`); `WWW-Authenticate: Basic realm="metrics"`. §9.
- **§11 NotImplementedException gating**: Incomplete features (I2P, RelayOnly, PerceptualHasher, etc.) fail at startup or return 501 when enabled; no `NotImplementedException` crash in configured defaults.
- **ScriptService**: Async read of stdout/stderr, `WaitForExitAsync`, timeout and process kill; no `WaitForExit()` deadlock. J.

### Mesh

- **Mesh:Security** (`mesh.security`): `enforceRemotePayloadLimits`, `maxRemotePayloadSize`; safe MessagePack/JSON deserialization, overlay/transport caps.
- **Mesh:SyncSecurity** (`mesh.sync_security`): Rate limiting, quarantine, proof-of-possession, consensus, alert thresholds (T-1432–T-1435). See `docs/security/mesh-sync-security.md`.
- **Phase 12 Database Poisoning Protection**: ✅ **100% COMPLETE** (Jan 2026). All 10 tasks (T-1430 through T-1439) implemented including Ed25519 signature verification, reputation integration, rate limiting, automatic quarantine, proof-of-possession challenges, cross-peer consensus, security metrics, comprehensive tests, and documentation. See `docs/security/mesh-sync-security.md` and `docs/security/database-poisoning-tasks.md` for details.

### Anonymity / transports

- **I2PTransport**: SAM v3.1 STREAM CONNECT with `host` as I2P destination (base64 or `.b32.i2p`). `AnonymityTransportSelector` registers I2P when `AnonymityMode.I2P`. §11: enabling without SAM bridge fails at startup or 501.
- **RelayOnlyTransport**: RELAY_TCP over data overlay; `IOverlayDataPlane.OpenBidirectionalStreamAsync`; `QuicDataServer` handles `RELAY_TCP`. **`RelayPeerDataEndpoints`** (`security.adversarial.anonymity.relay_only.relay_peer_data_endpoints`): list of `host:port` for each relay’s QUIC data overlay; used when `TrustedRelayPeers` are not resolved. Required for RelayOnly until peer-id resolution. §11: enabling without endpoints/TrustedRelayPeers fails at startup or 501.

### Audio / MediaCore

- **AudioUtilities.ExtractPcmSamples**: Via ffmpeg; `ExtractPcmSamplesAsync`. Test expects `FileNotFoundException` when file missing (replacing `FeatureNotImplementedException`).

### Multi-Source Downloads & Swarm Scheduling

- **Chunk Reassignment Logic (T-1405)**: Enhanced swarm download orchestration with automatic chunk reassignment from degraded peers.
  - **Assignment Tracking**: `IChunkScheduler` now tracks active chunk assignments via `RegisterAssignment`/`UnregisterAssignment` methods
  - **Degradation Handling**: `HandlePeerDegradationAsync` returns list of chunk indices to reassign when peer performance degrades
  - **Automatic Re-queuing**: `SwarmDownloadOrchestrator` detects degraded peers and automatically re-queues their assigned chunks for reassignment to better peers
  - **Implementation**: Works with both `ChunkScheduler` and `MediaCoreChunkScheduler` for cost-based and content-aware scheduling
  - **Benefits**: Improves download reliability by quickly shifting work away from underperforming peers to maintain optimal swarm performance

- **Jobs API Enhancements (T-1410)**: Enhanced `/api/jobs` endpoint with pagination, sorting, and improved filtering.
  - **Pagination**: `limit` and `offset` query parameters (default limit: 100)
  - **Sorting**: `sortBy` parameter supports `status`, `created_at`, or `id`; `sortOrder` parameter supports `asc`/`desc` (default: `desc`)
  - **Default Sorting**: Jobs sorted by `created_at` descending (newest first) when no sort specified
  - **Enhanced Response**: Includes `total`, `limit`, `offset`, and `has_more` fields for pagination metadata
  - **Enhanced Job Objects**: Job objects now include `created_at` timestamp and `progress` object with `releases_total`, `releases_done`, `releases_failed` for better sorting and filtering
  - **Use Case**: Enables efficient job management in UIs with large numbers of jobs, supporting pagination and sorting by status or creation date

### Legacy Client Compatibility Bridge

- **Bridge Proxy Server Testing (T-851)**: Expanded test coverage for bridge protocol parser.
  - **Additional Unit Tests**: Added 7 new edge case tests for `SoulseekProtocolParser` covering:
    - Empty string handling (username, password, query)
    - Long filename handling (1000+ characters)
    - Invalid message length handling
    - Message roundtrip validation (write then read)
    - Empty file/room list handling
  - **Test Coverage**: All 15 protocol parser tests passing (8 original + 7 new)
  - **Benefits**: Improved confidence in protocol parser robustness and edge case handling

### Test infrastructure

- **test-data/slskdn-test-fixtures**: Fetch scripts, `manifest.json`, `.gitignore` for download artifacts.

### Breaking / behavior changes

- **EnforceSecurity on**: No-auth + non-loopback bind requires `allow_remote_no_auth: true` or startup fails. CORS `AllowCredentials` + wildcard origin fails startup. Dump enabled + auth disabled fails startup. `Flags.HashFromAudioFileEnabled` + Enforce fails startup (not implemented).
- **Dump**: Default `allow_memory_dump: false`; 501 when creation fails (no silent empty or 500).
- **CORS**: When enabled, require explicit `allowed_origins` when `allow_credentials: true`; no wildcard + credentials.

---

## [0.24.1-slskdn.40]

- Bump to 0.24.1-slskdn.40 (slskdn-main-linux-x64.zip).
- See `packaging/debian/changelog` and `docs/archive/DEVELOPMENT_HISTORY.md` for earlier entries.
