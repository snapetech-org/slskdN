# Virtual Soulfind User Guide

> **Project Note**: This is a fork of [slskd](https://github.com/slskd/slskd). See [../README.md](../README.md#acknowledgments) for attribution.

> **DHT terminology**: Shadow Index and scene records use the slskdN **mesh
> DHT**. The public BitTorrent DHT, when enabled, only helps discover mesh
> overlay endpoints. Search requests, metadata exchange, and file bytes use
> the mesh overlay; no DHT carries file data. See [DHT and Mesh
> Architecture](DHT_MESH_ARCHITECTURE.md).

---

## Overview

Virtual Soulfind is a decentralized mesh network that provides resilience when the Soulseek server is unavailable. It automatically captures metadata from Soulseek traffic and publishes it to the slskdN mesh DHT, creating a "shadow index" of available content.

## Key Features

### 1. **Shadow Index**
- Passively observes Soulseek searches and transfers
- Extracts MusicBrainz IDs via AcoustID fingerprinting
- Publishes peer hints to the mesh DHT (with pseudonymized usernames)
- Enables MBID-based peer discovery

### 2. **Scenes (Micro-Networks)**
- Join taste-based communities (labels, genres, private groups)
- Scene IDs: `scene:label:warp-records`, `scene:genre:dub-techno`
- Discover peers who share your music interests
- Optional scene chat via overlay pubsub

### 3. **Disaster Mode**
- Automatically activates when Soulseek server is unavailable
- Switches all operations to mesh-only (mesh-DHT discovery and overlay transfers)
- Clear UI indicator when disaster mode is active
- Automatically recovers when Soulseek returns

## Configuration

### Enable Virtual Soulfind

Add to your `appsettings.yml`:

```yaml
VirtualSoulfind:
  Capture:
    Enabled: true  # Enable traffic capture
    MinimumFileSizeBytes: 1048576  # 1 MB minimum

  ShadowIndex:
    Enabled: true
    PublishIntervalMinutes: 15  # Publish to the mesh DHT every 15 minutes
    ShardTTLHours: 1  # Shard lifetime in the mesh DHT
    MaxShardsPerPublish: 100  # Upper bound before the mesh-DHT minute budget
    MaxDhtOperationsPerMinute: 60  # Shared mesh-DHT write-rate ceiling

  Scenes:
    Enabled: true
    MaxJoinedScenes: 20
    EnableChat: false  # Opt-in for scene chat

  DisasterMode:
    Auto: true  # Auto-activate when Soulseek unavailable
    UnavailableThresholdMinutes: 10  # Wait 10 min before activating

  Privacy:
    AnonymizationLevel: "Pseudonymized"  # Options: None, Pseudonymized, Aggregate
    RawObservationRetentionDays: 7
```

### Privacy Settings

**AnonymizationLevel options:**
- `Pseudonymized` (default): Usernames hashed with HMAC-SHA256
- `Aggregate`: Only statistics, no usernames
- `None`: Raw usernames (not recommended)

## Using Disaster Mode

### Automatic Activation

When Soulseek server is unavailable for 10 minutes (configurable), disaster mode automatically activates:

1. All searches query the shadow index (mesh DHT)
2. Transfers use overlay multi-swarm protocol
3. UI shows "Disaster Mode Active" indicator
4. Scene peers are used for additional peer discovery

### Manual Testing

Force disaster mode for testing:

```yaml
DisasterMode:
  Force: true  # Force mesh-only mode
```

### Recovery

Disaster mode automatically deactivates when:
1. Soulseek server connection is restored
2. Health check passes for 1 minute (stability check)

## Joining Scenes

### Via API

```bash
POST /api/virtualsoulfind/scenes/join
{
  "sceneId": "scene:label:warp-records"
}
```

### Scene Types

- **Label scenes**: `scene:label:<label-slug>`
- **Genre scenes**: `scene:genre:<genre-slug>`
- **Private scenes**: `scene:key:<pubkey>:<name>`

## Monitoring

### Telemetry Dashboard

Access telemetry at `/api/virtualsoulfind/telemetry`:

```json
{
  "shadowIndex": {
    "totalShards": 1250,
    "totalPeerHints": 340,
    "lastPublish": "2025-12-10T10:30:00Z"
  },
  "disasterMode": {
    "isActive": false,
    "totalActivations": 3,
    "totalDisasterTime": "02:15:30",
    "meshSearchCount": 45,
    "meshTransferCount": 12
  },
  "performance": {
    "cacheHitRate": 0.85,
    "avgDhtQueryTime": "00:00:00.150"
  }
}
```

### Privacy Audit

Run privacy audit at `/api/virtualsoulfind/privacy/audit`:

```json
{
  "passed": true,
  "findings": [
    {
      "severity": "Info",
      "category": "Username Anonymization",
      "description": "Username anonymization enabled: Pseudonymized"
    }
  ]
}
```

## Troubleshooting

### Shadow Index Not Populating

1. Check if capture is enabled: `Capture.Enabled: true`
2. Verify Soulseek traffic is happening (searches, transfers)
3. Check logs for `[VSF-CAPTURE]` entries

### Disaster Mode Not Activating

1. Check auto mode: `DisasterMode.Auto: true`
2. Verify Soulseek is actually unavailable
3. Check threshold: `UnavailableThresholdMinutes: 10`

### No Peers in Shadow Index

- Shadow index is **opportunistic** and builds over time
- Requires:
  1. Completed Soulseek transfers (for fingerprinting)
  2. MusicBrainz + AcoustID lookups
  3. Mesh-DHT publishing (15 min interval)

## Best Practices

### Privacy

✅ **DO:**
- Keep `AnonymizationLevel: Pseudonymized`
- Disable `PersistRawObservations` in production
- Review privacy audit regularly

❌ **DON'T:**
- Set `AnonymizationLevel: None` (exposes usernames)
- Do not publish shadow-index data to the public BitTorrent DHT; `DisasterMode.Force: true` only forces mesh-only mode for testing, while public DHT is for endpoint rendezvous rather than content metadata

### Performance

Shadow Index publishing advances through normalized recording IDs in bounded
indexed pages and wraps at the end of the library. The effective per-cycle
batch is the smaller of `MaxShardsPerPublish` and
`MaxDhtOperationsPerMinute`, so increasing the shard setting alone cannot
create work that the mesh-DHT write budget will reject.

✅ **DO:**
- Enable shadow index caching: `ShadowIndex.EnableCache: true`
- Use scene-scoped jobs for better peer targeting
- Prefetch hot MBIDs for frequently accessed content

❌ **DON'T:**
- Set `PublishIntervalMinutes` < 10 (mesh-DHT spam)
- Join too many scenes (`MaxJoinedScenes: 20`)

## Advanced: Scene Chat

Enable opt-in scene chat:

```yaml
Scenes:
  EnableChat: true
```

Send message to scene:

```bash
POST /api/virtualsoulfind/scenes/{sceneId}/chat
{
  "content": "Great label!"
}
```

**Note**: Scene chat is local-only and not stored permanently.

## Support

For issues or questions:
- GitHub Issues: `https://github.com/snapetech-org/slskdN/issues`
- Documentation: `docs/VIRTUAL_SOULFIND.md`
