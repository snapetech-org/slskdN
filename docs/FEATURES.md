# Features

**slskdn** - Soulseek client with mesh networking, multi-domain content acquisition, and service fabric

> **Note**: This is a fork of [slskd](https://github.com/slskd/slskd) with mesh networking and advanced features. See [README.md](../README.md#acknowledgments) for full attribution.

For the distinction between public BitTorrent DHT rendezvous, the slskdN mesh
DHT, and the mesh overlay transfer path, see [DHT and Mesh Architecture](DHT_MESH_ARCHITECTURE.md).

---

## Core Features (Existing)

### Soulseek Client
- Full Soulseek protocol support
- Search, browse, download, upload
- Chat rooms and private messages
- Shares management and indexing

### Now Playing / Scrobble Integration
- **Webhook receiver** at `POST /api/v0/nowplaying/webhook` — auto-detects Plex, Jellyfin/Emby, and generic JSON payloads
- **REST API** `GET/PUT/DELETE /api/v0/nowplaying` for programmatic control
- **User description update** — when playing, appends `🎵 Listening to: Artist – Title` to the Soulseek peer description
- Supported sources: Plex Media Server (multipart), Jellyfin/Emby (NotificationType JSON), Tautulli / generic JSON

### Integrated Web Player
- Persistent footer-safe player drawer for Collections and shared/downloaded local audio
- Streams local audio through the integrated `/api/v0/streams/{contentId}` range endpoint
- Transport controls: previous, next, rewind, fast-forward, play/pause, stop, local mute, collapse/expand
- Browser Media Session metadata/actions for PWA/mobile lock-screen controls where supported
- MilkDrop visualizer with inline, full-window, and native fullscreen modes
- 10-band Web Audio equalizer with localStorage-backed presets
- Lightweight spectrum analyzer and oscilloscope canvas
- Synced LRCLIB lyrics pane keyed by current artist/title
- Optional ListenBrainz `playing_now` and scrobble submission with browser-local token storage
- Optional five-second crossfade between queue items
- Document Picture-in-Picture spectrum window on supported Chromium browsers
- Karaoke-style center-channel vocal reduction toggle
- Browser-local listening history, stats, ratings, smart-radio seed handoffs,
  queue manager, similar-track auto-fill, and keyboard shortcuts
- Native MilkDrop3-compatible WebGL2/WebGPU backends are selectable for testing;
  Butterchurn remains available and device/preset parity is still experimental

### SongID
- Native source-identification workflow beside MusicBrainz in Search
- Accepts YouTube URLs, Spotify URLs, direct text queries, and server-side local file paths
- Fuses recognizers and context signals:
  - MusicBrainz / AcoustID / SongRec
  - transcript excerpts, OCR, comments, chapter clues
  - provenance and synthetic-signal heuristics
  - Panako, Audfprint, Demucs-backed evidence where available
- **Forensic + identity context** — lane-level forensic matrix, split identity/synthetic assessments, `topEvidenceFor`/`topEvidenceAgainst`, `knownFamilyScore`, `perturbationStability`, and C2PA provenance hints keep the evidence transparent without blocking catalog matches
- Runs in a durable background queue with fixed concurrent workers and live progress updates
- **Infinite queue + configurable workers** — SongID accepts unlimited queued runs, persists queue position/worker slot in SQLite, recovers after restarts, and honors `--songid-max-concurrent-runs` / `SONGID_MAX_CONCURRENT_RUNS` so exactly `X` slots process work at a time
- Produces ranked actions for song search, album preparation, album jobs, and artist discography planning
- **Ranked acquisition & mix planning** — track/album/discography plans rely on identity-first scoring, mix decomposition generates `Split Into Track Plans`, and `Search Top Candidates` fan-outs handle ambiguous segments while ranking by quality/Byzantine consensus
- Keeps synthetic / AI-origin signals informational rather than letting them override strong identity matches

### Discovery Graph / Constellation
- Navigable similarity topology rather than flat related-artist lists
- Typed, weighted, explainable edges with provenance and score components
- Current summon points:
  - SongID run mini-map and modal
  - MusicBrainz lookup
  - Search list rows and search detail headers
  - search result cards
  - persistent in-page atlas panel
  - dedicated Discovery Graph route
- Current actions:
  - recenter
  - queue nearby
  - pin
  - compare
  - save branch
- Current graph seed types:
  - SongID runs
  - tracks
  - albums
  - artists
  - fallback metadata seeds from search and MusicBrainz context
- Semantic zoom stack (mini-map, drawer modal, atlas) lets SongID/MusicBrainz/search seeds share state while provenance/score-component overlays keep closeness explainable and actionable

### Soulseek Type-1 Message Obfuscation
- Runtime-backed type-1 obfuscated peer-message, distributed-message, and file-transfer listener support through the vendored `slskNet.Runtime`
- Default compatibility posture keeps regular peer, distributed, and transfer outbound dials first for legacy clients
- Prefer mode can prioritize compatible obfuscated outbound peer, distributed, and transfer dials while keeping regular direct and indirect fallback
- System → Network reports enablement, configured mode, effective obfuscated port, fallback posture, and runtime activation state
- Scope includes peer-message, distributed-message, and file-transfer streams while regular Soulseek fallback remains available

### Soulseek Native Discovery
- Search-page **Soulseek Discovery** panel for native liked/hated interests, personal/global recommendations, item recommendation branches, similar users, and user-interest lookup
- Native discovery API under `/api/v0/soulseek/*` for authenticated operators and clients
- Recommendation rows can start a normal Soulseek search or create a disabled review-only Wishlist item with auto-download off
- Federated Taste can explicitly include native Soulseek recommendation strings as low-trust discovery seeds
- User cards expose lazy native-interest lookup so large lists do not trigger background request fan-out
- Messages workspace exposes batch private-message sending through the native Soulseek multi-recipient server command
- Discovery calls use separate Soulseek safety limiter buckets from manual search and browse requests
- All native discovery commands are opt-in; normal search, browse, transfer, room, and one-to-one private-message behavior remains unchanged

### System Admin Surfaces
- **Policies**: guided YAML for webhooks/scripts, transfer policy, security and
  access, search/network/DHT/rescue settings, retention, and share scan pressure
- **Experience**: browser-local preferences for Search, Player, and Messages
- **Integrations**: VPN, Lidarr, metadata providers, notifications, source feeds,
  FTP, Servarr readiness, and media-server execution contracts
- **Source Providers**: read-only acquisition provider capabilities and
  acquisition-profile priority chains
- **Automation Center**: visible recipes, impact labels, local enablement, and
  dry-run history
- **Setup Health / Diagnostic Bundles**: readiness scoring and redacted support
  snapshots

### Discography Concierge
- Search-page coverage map for a MusicBrainz artist MBID
- Uses the existing MusicBrainz release graph and cached release targets to build release/track rows
- Marks each track as:
  - available through verified HashDb evidence
  - already seeded in Wishlist
  - ambiguous because catalog identity is incomplete
  - missing
- Missing tracks can be promoted to Wishlist searches manually
- Does not browse Soulseek peers, start immediate searches, auto-download, mirror files, or manage backups

### Built-in Lidarr Integration
- First-class Lidarr workflow without installing a Lidarr plugin
- Uses Lidarr's supported HTTP API for status, Wanted/Missing reads, manual-import decisions, and import commands
- Syncs Lidarr Wanted/Missing albums into slskdN Wishlist searches
- Edition matching: validates each candidate's track count, duration, and edition against the release Lidarr actually monitors before auto-download; `integrations.lidarr.edition_match_mode` controls whether mismatches are excluded (default), down-ranked, or ignored
- Duplicate-download prevention: skips candidates matching a recently completed download elsewhere by normalized title/duration
- Optional auto-download for Lidarr-created Wishlist items through the normal slskdN queue
- Safe post-download import: slskdN only asks Lidarr to import candidates with clean artist, album, release, track, and quality matches
- Leaves rejected or ambiguous candidates for Lidarr's Manual Import screen
- Supports Docker, host, and split-volume deployments through `import_path_from` / `import_path_to` path mapping
- Operator API under `/api/v0/integrations/lidarr/*` for status checks, wanted preview, one-time sync, and manual import

### Cancel Transfers on Blacklist
- Users added to `groups.blacklisted.members` at runtime have all active uploads and downloads immediately cancelled
- Detected automatically via options monitor — no restart required

### Per-Group File Type Restrictions
- `groups.<name>.upload.allowed_file_types` — whitelist of extensions (e.g. `[".mp3", ".flac"]`)
- Applied at enqueue time; rejects disallowed file types with an appropriate Soulseek error response
- Applies to user-defined groups, Default, and Leechers groups
- Empty list (default) = no restriction

### Prometheus Metrics UI
- **System → Metrics** tab in web UI
- Displays KPI stats (Transfers, Search, Process, Network) fetched from `/api/v0/telemetry/metrics/kpi`
- Full `slskd_*` metrics table with name, type, value, and description
- Refresh button with last-updated timestamp

### UserCard Score Badges
- Reputation/stats badges shown next to usernames in:
  - Stable identity surfaces such as panel headers and member rails
  - Room user list sidebar (RoomSession)
  - Search results, Browse view, Transfers (existing)

### Unified Messages
- Direct messages, joined rooms, and pod room channels share a persistent
  multi-panel workspace
- Panel state can collapse/restore without taking over the full page
- Pod direct channels are hidden from the normal list so they do not duplicate
  Soulseek DMs
- Listen Along controls are scoped to pod room/broadcast channels, not direct
  messages

### Mesh Overlay Network
- Public BitTorrent DHT rendezvous discovers mesh endpoints; the separate mesh DHT stores bounded metadata and service records over mesh connections
- QUIC/UDP with TLS encryption
- Certificate pinning for security
- Rendezvous and relay capabilities
- **Fault-tolerant operation**: Mesh continues functioning behind firewalls when UDP port cannot be opened, using DHT rendezvous, relay, and hole punching for connectivity

### Multi-Source Downloads
- Chunked downloads from multiple sources
- Rescue mode for failed downloads
- Source fallback and retry logic
- Experimental BitTorrent acquisition is disabled by default. When enabled,
  `PrivateOnly` removes tracker and web-seed URLs and disables BitTorrent DHT
  and PEX; peer connections come only from the configured overlay and invite
  list. See [VirtualSoulfind v2 BitTorrent](config.md#virtualsoulfind-v2-bittorrent).
- **Chunk Reassignment**: Automatic reassignment of chunks from degraded peers to better-performing peers. When a peer's performance degrades (high error rate, slow throughput), the system automatically identifies all chunks assigned to that peer and re-queues them for reassignment to better peers. Integrated with cost-based and content-aware scheduling for optimal download performance.

### Security & Privacy
- Network guard and reputation system
- Violation tracking and auto-bans
- Content safety filtering
- Ban list integration

---

## Service Fabric (T-SF01-07, H-01)

### What It Enables
Generic service discovery and RPC over the mesh overlay network. Any feature can be exposed as a service without custom protocols.

### Features

#### Service Discovery
- **Mesh-DHT Publishing**: Services publish signed descriptors to the slskdN mesh DHT over the mesh overlay; public BitTorrent DHT is endpoint rendezvous only
- **Signature Validation**: Ed25519 signatures prevent spoofing
- **TTL-Based Expiry**: Services auto-expire if not refreshed
- **Reputation Filtering**: Discovery respects peer reputation

#### Service Routing
- **Generic RPC**: Call any service method with typed request/response
- **Correlation IDs**: Track requests across network boundaries
- **Timeout Handling**: Automatic timeouts with cancellation
- **Rate Limiting**: Per-peer and per-service call limits (100 calls/min default)

#### Security & Abuse Prevention
- **Work Budget Integration**: Every call consumes work units
- **ViolationTracker Integration**: Abuse feeds into existing security system
- **Payload Size Limits**: Configurable max payload size (1MB default)
- **Service Allowlists**: Control which services are exposed

#### HTTP Gateway (H-01)
- **Localhost API**: External tools access mesh services via HTTP
- **API Key Authentication**: Required for non-localhost access
- **CSRF Protection**: Required for localhost mutating operations
- **Service Allowlist**: Control which services are HTTP-accessible
- **Request Logging**: Audit trail for all gateway requests

**Default**: Disabled (opt-in)

---

## Multi-Domain VirtualSoulfind (T-VC01-04, H-11-15)

### What It Enables
Content-aware acquisition that's not limited to music. Supports multiple content types with appropriate matching logic and backend selection for each.

### Features

#### Multi-Domain Support
- **ContentDomain Enum**: Music, GenericFile, (future: Movies, TV, Books)
- **Domain-Specific Matching**:
  - Music: MBID, duration, bitrate, codec matching
  - GenericFile: SHA256 hash matching
  - Future domains: custom matching logic per domain
- **Domain-Specific Backends**:
  - Music: Soulseek, mesh DHT/overlay, Torrents, Local
  - GenericFile: mesh DHT/overlay, Torrents, HTTP, Local (NO Soulseek)

#### Soulseek Safety
- **Compile-Time Gating**: Soulseek backend only accepts `ContentDomain.Music`
- **Rate Caps**: Configurable searches/browses per minute
- **Friendly Mode**: Respects Soulseek etiquette by default
- **Work Budget**: All Soulseek operations consume budget

**Result**: Soulseek abuse for non-music content is prevented by multiple enforcement layers (domain gating, work budget, rate caps, plan validation).

#### Intent Management
- **Origin Tracking**: Tag intents by source (UserLocal, LocalAutomation, RemoteMesh, RemoteGateway)
- **Priority Scheduling**: User intents prioritized over remote requests
- **Remote Intent Control**: Disabled by default, requires explicit config
- **Work Budget Per Intent**: Budget exhaustion fails gracefully

#### Privacy Modes
- **Normal Mode**: Per-peer tracking for smart source selection
- **Reduced Mode**: Aggregated sources only, less correlation
- **Opaque IDs**: VirtualSoulfind never stores Soulseek usernames or IPs
- **PII Separation**: Soulseek-specific data lives in Soulseek modules only

#### Verification & Advertisement
- **Content Verification**: Duration/size/hash matching before marking as "verified"
- **Selective Advertisement**: Only verified, shared, non-private content advertised to mesh
- **No Third-Party Data**: Never publishes what other Soulseek users share

**Default**: Music domain enabled, remote intent management disabled

---

## Proxy/Relay Services (T-PR01-05, H-PR05)

### What They Enable
Application-specific fetch and relay capabilities without becoming a generic proxy or exit node.

### Features

#### Catalogue Fetch Service
**Purpose**: Fetch and cache metadata from whitelisted external APIs.

- **Domain Allowlist**: Only whitelisted domains (MusicBrainz, cover art, etc.)
- **Method Restriction**: GET and HEAD only (no POST/PUT/DELETE)
- **SSRF Protection**: Blocks loopback and private IP ranges
- **Response Caching**: In-memory cache with configurable TTL (10 min default)
- **Size Limits**: Max response body size (256 KB default)
- **Request Timeout**: Configurable timeout (10 seconds default)
- **Work Budget**: Consumes units per fetch (cache hits are free)

**Use Case**: Multiple peers fetch same MusicBrainz metadata → one external API call, cached and shared via mesh.

**Default**: Enabled with conservative limits

#### Content Relay Service
**Purpose**: Serve verified content chunks to mesh peers (mesh CDN).

- **Content ID Mapping**: Accept content IDs, not file paths (no arbitrary file access)
- **Verification Required**: Only serves content marked as verified and advertisable
- **Chunked Delivery**: Configurable chunk size (64 KB default)
- **Stream Caps**: Per-peer and global concurrent stream limits
- **Integrity Hashes**: Optional chunk hashing for verification
- **Work Budget**: Consumes units per chunk served

**Use Case**: Peer has slow Soulseek source, you have verified copy → serve chunks via fast mesh connection.

**Default**: Enabled with conservative stream caps

#### Integrated Web Player
**Purpose**: Play streamable audio directly in the slskdN Web UI without an external media server.

- **Persistent Player Dock**: Footer-safe player with collapse/expand drawer behavior.
- **Transport Controls**: Play/pause, stop, previous/next, rewind, fast-forward, and browser-local mute.
- **Collection Browser**: Modal collection picker with collection list, item list, and explicit play actions.
- **Local File Browser**: Searchable modal over configured shared/downloaded local audio.
- **Browser/PWA Support**: Inline browser audio plus Media Session metadata and action handlers where supported.
- **Player Extras**: Optional MilkDrop visualizer, spectrum/oscilloscope analyzer, equalizer, synced lyrics, crossfade, karaoke-style center-channel reduction, and ListenBrainz now-playing/scrobble submission.

**Use Case**: Queue a collection, audition downloaded audio, or follow a pod/listening-party stream from the browser while keeping playback local to the current device.

**Docs**: [Listening Party and Player](listening-party.md)

#### Trusted Relay Service
**Purpose**: NAT traversal for your own nodes/friends via logical service names.

- **Peer Allowlist**: Explicit list of trusted peer IDs
- **Target Service Allowlist**: Explicit list of allowed internal services ("slskdn-ui", "slskdn-api")
- **Logical Routing**: Routes by service name, not host:port (no generic proxy)
- **Tunnel Management**: Track tunnels per peer, enforce caps
- **Work Budget**: Consumes units per relay message

**Use Case**: VPS and home server (behind NAT) relay through each other for remote management.

**Default**: Disabled (requires explicit trust configuration)

---

## Security & Hardening

### Global Principles
- **Default Deny**: Features disabled or scoped by default
- **Least Privilege**: Minimal permissions and visibility per service
- **No Generic Proxy**: Everything application-aware (domains, content IDs, service names)
- **Work Budget**: Work units and rate limits reduce amplification risk
- **Input Validation**: External-facing paths should validate length, type, and format before use

### Logging & Metrics
- **PII minimization**: Security-sensitive logs and metrics should avoid Soulseek usernames, IPs, and secrets unless a specific operational path requires them
- **Logs Page Filtering**: Filter logs by level (All, Info, Warn, Error, Debug) with count display
- **Reduced Noise**: CSRF validation logs for safe methods moved to Verbose level (not shown in default views)
- **Low Cardinality**: Metrics use low-cardinality labels only
- **Audit Trail**: All mutating operations logged with origin

### SSRF Protection
- **Path-specific policies**: Solid WebID resolution and ActivityPub key fetching use SSRF-aware policies
- **IP Blocking**: Those guarded fetch paths block loopback and private IP ranges
- **Domain Allowlists**: Solid remote fetches require explicit allowed hosts
- **Open audit items**: Webhook delivery and ActivityPub inbox delivery are tracked separately in the April 2026 security audit and should not be described as globally SSRF-safe until fixed

### Rate Limiting
- **Per-Peer Limits**: Calls per minute per peer (configurable)
- **Global Limits**: Total calls across all peers (configurable)
- **Service-Specific Limits**: Different limits for different services

### Violation Tracking
- **Auto-Escalating Bans**: Repeated violations trigger temporary, then permanent bans
- **Unified System**: Mesh violations affect Soulseek reputation
- **Detailed Logging**: All violations logged with type and details

---

## Configuration

The snippets below are design examples for advanced mesh and gateway features.
Use `config/slskd.example.yml` and `docs/config.md` as the source of truth for
current user-facing option names, casing, and defaults.

### Service Fabric
```yaml
ServiceFabric:
  Enabled: true
  MaxDescriptorsPerLookup: 20
  MaxDescriptorBytes: 4096
```

### Mesh Gateway
```yaml
MeshGateway:
  Enabled: false  # Disabled by default
  BindAddress: "127.0.0.1"  # Localhost only
  Port: 5030
  ApiKey: ""  # MUST be set if enabling
  CsrfToken: ""  # Auto-generated if empty
  AllowedServices:
    - "pod-chat"
    - "shadow-index"
    - "mesh-stats"
  MaxRequestBodyBytes: 1048576  # 1 MB
  RequestTimeoutSeconds: 30
```

### VirtualSoulfind v2
```yaml
VirtualSoulfind:
  Enabled: true
  PrivacyMode: Normal  # Normal | Reduced
  AllowRemoteIntentManagement: false  # Remote intent creation
  AllowPlanExecution: false  # HTTP gateway plan execution
  SoulseekCaps:
    MaxSearchesPerMinute: 20
    MaxBrowsesPerMinute: 5
```

### Catalogue Fetch
```yaml
CatalogFetch:
  Enabled: true
  AllowedDomains:
    - "musicbrainz.org"
    - "coverartarchive.org"
  MaxBodyBytes: 262144  # 256 KB
  RequestTimeoutSeconds: 10
  CacheTtlSeconds: 600  # 10 minutes
```

### Content Relay
```yaml
ContentRelay:
  Enabled: true
  MaxChunkBytes: 65536  # 64 KB
  MaxConcurrentStreamsPerPeer: 2
  MaxConcurrentStreamsGlobal: 20
```

### Trusted Relay
```yaml
TrustedRelay:
  Enabled: false  # MUST be explicitly enabled
  TrustedPeerIds: []  # Explicit peer allowlist
  AllowedTargetServices:
    - "slskdn-ui"
    - "slskdn-api"
  MaxTunnelsPerPeer: 4
  MaxTunnelsGlobal: 20
```

---

## Use Cases

### Music Acquisition (Existing + Enhanced)
- Search Soulseek with etiquette caps
- Multi-source downloads (Soulseek + mesh overlay + torrents)
- MBID-based matching via shadow index
- Verified content served via mesh CDN

### Generic File Sharing (New)
- Hash-based matching (SHA256)
- Mesh DHT/overlay/torrent backends only (NO Soulseek)
- Content verification before advertisement
- Mesh CDN for verified files

### Metadata Collaboration (New)
- Fetch MusicBrainz via catalogue fetch service
- Cache and share via mesh (reduce API load)
- Multiple peers benefit from single fetch
- Respects external API rate limits

### Personal Infrastructure (New)
- NAT traversal via trusted relay
- VPS and home server communicate via mesh
- Access remote slskdn instances via HTTP gateway
- No port forwarding or VPN required

### Identity & Friends (New)

Human-friendly peer addressing and discovery system enabling the "befriend → group → share → recipient backfill download → recipient stream" workflow.

#### Features

- **Peer Profiles**: Signed identity objects with display names, friend codes, and network endpoints
- **Contact Management**: Local contact list with nicknames and verification status
- **Friend Codes**: Short, shareable codes (e.g., `ABCD-EFGH-IJKL-MNOP`) for easy addressing
- **Invite Links**: `slskdn://invite/...` links with QR code support for adding friends
- **mDNS LAN Discovery**: Browse nearby peers on demand; automatic startup advertising is separately opt-in
- **API Integration**: Full REST API for profile and contact management

#### Configuration
```yaml
Feature:
  IdentityFriends: true
lan_discovery:
  advertise: false # Set true to publish this peer's identity over mDNS at startup
```

Identity/Friends APIs are enabled by default. Automatic mDNS advertising is
disabled by default; nearby-peer browsing remains user-triggered.

#### Use Cases

- **Human-Friendly Sharing**: Add friends by display name instead of raw peer IDs
- **LAN Discovery**: Automatically discover peers on the same network
- **Invite-Based Networking**: Share invite links or QR codes to connect with friends
- **Contact-Based Groups**: Create share groups using contact nicknames

### Solid Integration (New)

Optional integration with Solid (WebID + Solid-OIDC) for decentralized identity and Pod-backed metadata.

#### Features

- **WebID Resolution**: Resolve WebID profiles and extract OIDC issuer information for Solid identity integration
- **Solid-OIDC Client ID Document**: Serves compliant JSON-LD Client ID document at `/solid/clientid.jsonld` (dereferenceable per Solid-OIDC specification)
- **SSRF Hardening**: Comprehensive security controls for WebID/Pod fetches:
  - **Host Allow-List**: `AllowedHosts` configuration - empty list denies all remote fetches by default (SSRF protection)
  - **HTTPS Enforcement**: HTTPS-only by default (`AllowInsecureHttp: false`), configurable for dev/test only
  - **Private IP Blocking**: Automatically blocks localhost, `.local` domains, and RFC1918/link-local IP ranges
  - **Response Limits**: Configurable max response size (`MaxFetchBytes`: 1MB default) and timeout (`TimeoutSeconds`: 10s default)
- **RDF Parsing**: Uses dotNetRDF library for parsing WebID profiles in Turtle and JSON-LD formats
- **API Endpoints**:
  - `GET /api/v0/solid/status` - Check Solid integration status and configuration
  - `POST /api/v0/solid/resolve-webid` - Resolve a WebID URI and extract OIDC issuer information
- **Frontend UI**: New "Solid" navigation item and settings page (`/solid`) for WebID resolution testing

#### Configuration
```yaml
feature:
  Solid: true  # Enable Solid integration (default: true)

solid:
  allowedHosts: []  # Empty = deny all remote fetches (SSRF safety)
                     # Add hostnames like ["your-solid-idp.example", "your-pod-provider.example"]
  timeoutSeconds: 10
  maxFetchBytes: 1000000
  allowInsecureHttp: false  # ONLY for dev/test. Keep false in production
  redirectPath: "/solid/callback"
```

**Default**: Enabled (`true`) but non-functional until `AllowedHosts` is configured (SSRF safety)

#### Security by Default

- Feature is **enabled by default** but **non-functional for remote WebID fetches** until `AllowedHosts` is explicitly configured
- This provides SSRF protection: even with the feature on, no remote fetches occur until explicitly allowed
- HTTPS-only enforcement blocks accidental insecure WebID fetches on the Solid path
- Private IP blocking blocks common SSRF targets on the Solid path

#### Use Cases

- **WebID Identity**: Resolve WebID profiles to discover OIDC issuers for authentication
- **Solid-OIDC Integration**: Provide Client ID document for Solid-OIDC authentication flows
- **Future Pod Integration**: Foundation for Pod-backed metadata storage (playlists, sharelists) - coming in future releases

#### Future Extensions (not in MVP)

- Full OIDC Authorization Code + PKCE flow
- Token storage (encrypted via Data Protection)
- DPoP proof generation
- Pod metadata read/write (playlists, sharelists)
- Type Index / SAI registry discovery
- Access control (WAC/ACP) writers

### Streaming (New)

HTTP range request support for content streaming with session limiting and authentication. This endpoint powers the integrated Web UI player and listening-party playback.

#### Features

- **Range Request Support**: Standard HTTP `Range` header support for seeking
- **Session Limiting**: Configurable concurrent stream limits per content
- **Token Authentication**: Share token-based authentication for recipients
- **Content Resolution**: Automatic MIME type detection and file path resolution from indexed content, share grants, and allowed local share/download roots
- **Player Integration**: Browser playback through the persistent player, collection browser, and local file browser

#### Configuration
```yaml
Feature:
  Streaming: true  # Enable streaming API
```

**Default**: Disabled (opt-in)

### Scene ↔ Pod Bridging (New)

Unified search experience that aggregates results from both the Pod/Mesh network and the Soulseek Scene network, with intelligent action routing based on result source.

#### Features

- **Unified Search**: Single search query hits both Pod/Mesh and Soulseek Scene providers in parallel
- **Result Merging**: Automatic deduplication and merging of results from multiple sources
- **Provenance Badges**: Clear visual indicators showing result source (POD, SCENE, or POD+SCENE)
- **Intelligent Action Routing**:
  - **Pod Results**: Download from remote mesh peers if not available locally, or stream via streaming API
  - **Scene Results**: Use standard Soulseek download pipeline
- **Provider Selection**: UI checkboxes to select which providers to search (Pod and/or Scene)
- **Privacy Protection**: Pod peer identities never exposed to Soulseek Scene network

#### How It Works

1. **Search Aggregation**: When enabled, searches run in parallel across both networks:
   - Pod/Mesh search queries the mesh overlay network for content
   - Scene search queries the Soulseek network
   - Results are merged and deduplicated based on hash (if available) or filename+size

2. **Deduplication Logic**:
   - Primary key: Content hash (exact match)
   - Secondary key: Normalized filename + size
   - When duplicates found: Combined result shows both sources, with Pod preferred as primary source

3. **Action Routing**:
   - **Download**: Routes to appropriate download handler based on `PrimarySource`
     - Pod: Checks local availability first, then fetches from mesh peers
     - Scene: Uses existing Soulseek download pipeline
   - **Stream**: Only available for Pod results (Scene streaming not supported)

4. **Privacy Guarantees**:
   - Pod peer IDs (`peerId`) never exposed in Scene-facing APIs or UI
   - No auto-advertising of Pod content to Scene
   - No proxying of Scene downloads through Pod by default

#### Configuration

```yaml
Feature:
  ScenePodBridge: false  # Opt in to experimental Scene ↔ Pod Bridging (default: false)
  ScenePodBridgeOptions:
    ProxyTransfers: false     # Proxy scene downloads through pod (future feature, intentionally disabled)
    ExportPodAvailability: false  # Export pod availability to scene (future feature, intentionally disabled)
```

**Default**: Disabled (opt-in). Normal searches stay on the upstream-compatible Soulseek search path unless this feature is explicitly enabled.

#### Use Cases

- **Unified Discovery**: Find content across both networks with a single search
- **Source-Aware Downloads**: Automatically use the best download method for each result
- **Mesh-First Preference**: Pod results preferred when available from both sources (privacy-preserving)
- **Fallback Support**: Scene results available when Pod network doesn't have the content

#### API Endpoints

- `POST /api/v0/searches/{searchId}/items/{itemId}/download` - Download a search result item (routes based on source)
- `POST /api/v0/searches/{searchId}/items/{itemId}/stream` - Stream a pod result (returns 400 for scene results)

#### Remote Pod Downloads

When downloading Pod results that aren't available locally:
- System checks local content via `IContentLocator`
- If not local, fetches from mesh peers using `IMeshContentFetcher`
- Falls back to `IMeshDirectory` lookup if peer ID from search result is missing
- Downloads saved to incomplete downloads directory
- Errors handled with appropriate HTTP status codes (404 for peer not found, 502 for fetch failures)

### External Tool Integration (New)
- Music apps access VirtualSoulfind via HTTP gateway
- Query missing tracks, library stats, catalogue gaps
- Execute intents remotely (if enabled)
- Work budgets and rate limits reduce abuse risk

### Jobs API (Multi-Swarm Integration)
- **Job Management**: Create and track discography and label crate download jobs
- **Enhanced List Endpoint**: `GET /api/jobs` with pagination, sorting, and filtering
  - **Pagination**: `limit` and `offset` parameters (default limit: 100)
  - **Sorting**: Sort by `status`, `created_at`, or `id` with `asc`/`desc` order
  - **Default Sorting**: Newest jobs first (`created_at` descending)
  - **Response Metadata**: Includes `total`, `limit`, `offset`, and `has_more` for pagination
  - **Job Details**: Each job includes `created_at` timestamp and `progress` object with completion statistics
- **Job Types**: Discography jobs (artist releases) and label crate jobs (label releases)
- **Use Case**: Efficient job management in UIs with large numbers of jobs, supporting pagination and sorting by status or creation date

### Discography Coverage API
- **Coverage endpoint**: `GET /api/v0/musicbrainz/artist/{artistId}/discography-coverage`
  - Query parameters: `profile=CoreDiscography|ExtendedDiscography|AllReleases`, `forceRefresh=false`
  - Returns artist totals plus release/track cells with coverage status and evidence
- **Wishlist promotion endpoint**: `POST /api/v0/musicbrainz/artist/{artistId}/discography-coverage/wishlist`
  - Body: `profile`, `filter`, `maxResults`
  - Creates Wishlist searches only for currently missing tracks
- **Network behavior**: MusicBrainz refreshes may contact the configured MusicBrainz endpoint; coverage mapping does not browse Soulseek peers or trigger downloads

---

## Performance

### Caching
- **Catalogue Fetch**: In-memory cache (10 min TTL)
- **Content Relay**: Chunk cache for hot content (LRU)
- **VirtualSoulfind**: Catalogue cache for repeated queries

### Streaming
- **Content Relay**: Chunked delivery, not full-file buffering
- **HTTP Gateway**: Streaming responses where applicable
- **DHT Queries**: Limited result count (max 20 descriptors)

### Concurrency
- **Stream Caps**: Prevent resource exhaustion (per-peer and global)
- **Rate Limits**: Prevent DoS (per-peer and global)
- **Work Budget**: Fail fast on exhaustion (no wasted work)

---

## Roadmap

### Phase 1: Service Fabric ✅ IMPLEMENTED / EXPERIMENTAL
- [x] Service descriptors and directory (T-SF01)
- [x] Service routing and RPC (T-SF02)
- [x] Service wrappers for existing features (T-SF03)
- [x] HTTP gateway with auth (T-SF04 + H-01)

### Phase 2: Security Hardening 🚧 IN PROGRESS
- [x] Security review and tightening (T-SF05)
- [x] Developer docs and examples (T-SF06)
- [x] Metrics and observability (T-SF07)
- [x] Work budget implementation (H-02) **CRITICAL**
- [x] Soulseek safety caps (H-08) **CRITICAL**

### Phase 3: Multi-Domain Foundation
- [x] Domain abstraction (T-VC01)
- [x] Music domain provider (T-VC02)
- [x] GenericFile domain provider (T-VC03)
- [x] Domain-aware planner + Soulseek gating (T-VC04)

### Phase 4: VirtualSoulfind v2
- [x] Data model and catalogue store (V2-P1)
- [x] Intent queue and planner (V2-P2)
- [x] Match and verification engine (V2-P3)
- [x] Backend implementations (V2-P4)
- [x] Integration and work budget (V2-P5)
- [x] Advanced features (V2-P6)

### Phase 5: Proxy/Relay Services
- [x] Define primitives (T-PR01)
- [x] Catalogue fetch service (T-PR02)
- [x] Content relay service (T-PR03)
- [x] Trusted relay service (T-PR04)
- [x] Hardening and policy (H-PR05)

### Phase 6: Testing & Hardening
- [x] Comprehensive testing (T-TEST-01 through T-TEST-07)
- [x] Remaining hardening tasks (H-03 through H-07, H-09, H-10)
- [x] Security audit pass with follow-up items tracked separately
- [x] Performance optimization

---

## Installation

### Requirements
- .NET 10.0 or later
- Linux, macOS, or Windows
- Network connectivity for Soulseek and mesh

### Quick Start
```bash
# Clone repository
git clone https://github.com/snapetech-org/slskdN.git
cd slskdn

# Checkout the active branch
git checkout main

# Build
dotnet build

# Run
dotnet run --project src/slskd
```

### Configuration
Configuration files are in `appsettings.json` and `appsettings.Development.json`.

Default config is secure:
- Mesh gateway disabled
- Trusted relay disabled
- Remote intent management disabled
- Conservative rate limits and caps

See [SECURITY-GUIDELINES.md](SECURITY-GUIDELINES.md) for detailed security configuration.

---

## Documentation

- [HOW-IT-WORKS.md](HOW-IT-WORKS.md): Technical architecture and synergies
- [SECURITY-GUIDELINES.md](SECURITY-GUIDELINES.md): Mandatory security requirements (all tasks)
- [CURSOR-WARNINGS.md](CURSOR-WARNINGS.md): LLM implementation risk assessment
- [SERVICE_FABRIC_TASKS.md](SERVICE_FABRIC_TASKS.md): Service fabric task breakdown
- [HARDENING-TASKS.md](archive/root/HARDENING-TASKS.md): Security hardening task breakdown
- [PROXY-RELAY-TASKS.md](archive/root/PROXY-RELAY-TASKS.md): Proxy/relay task breakdown
- [VIRTUALSOULFIND-V2-TASKS.md](archive/root/VIRTUALSOULFIND-V2-TASKS.md): VirtualSoulfind v2 task breakdown
- [VIRTUALSOULFIND-CONTENT-DOMAINS.md](VIRTUALSOULFIND-CONTENT-DOMAINS.md): Multi-domain refactoring
- [TESTING-STRATEGY.md](TESTING-STRATEGY.md): Comprehensive testing strategy

---

## Contributing

### Security First
Read [SECURITY-GUIDELINES.md](SECURITY-GUIDELINES.md) before contributing. All contributions MUST follow the mandatory security requirements.

### Task Implementation
Check [CURSOR-WARNINGS.md](CURSOR-WARNINGS.md) for implementation risk levels before starting any task. High-risk tasks require strict prompts and comprehensive tests.

### Code Review
All PRs require:
- Security checklist completion
- Anti-slop checklist completion
- Comprehensive tests (unit + integration)
- No linter errors

### Philosophy
- Security is non-negotiable
- Default deny everywhere
- No generic proxy features
- Application-aware, not generic
- Composable, not monolithic

---

## License

See LICENSE file for details.

---

## Status

**Current Version**: stable package metadata currently tracks `2026051600-slskdn.259`; use [CHANGELOG.md](CHANGELOG.md) and the GitHub Releases page as the release source of truth.

**Branch**: main

**Status**: Active development

**Production Ready**: Main channel suitable for production use of documented stable features; dev channel and explicitly labeled experimental surfaces remain experimental.

**Implemented**:
- ✅ Service fabric core, HTTP gateway, service wrappers (pods, VirtualSoulfind, introspection)
- ✅ Security hardening, work budget, Soulseek caps
- ✅ Multi-domain VirtualSoulfind, proxy/relay services
- ✅ Identity & friends, Solid integration, streaming API, Scene ↔ Pod bridging
- ✅ Swarm analytics, distributed tracing (OpenTelemetry), CI/CD enhancements
- ✅ E2E tests (tests/e2e), dev build pipeline (AUR, COPR, PPA, Chocolatey, Homebrew, Snap, Nix, Winget)

**In Progress**:
- 🚧 Further hardening and performance tuning

**Planned**:
- 📋 Full Solid OIDC flow, Pod metadata read/write

---

*slskdn - Soulseek with mesh networking, done right.*

*No hype. Just engineering.*
