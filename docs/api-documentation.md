# API Documentation

Complete reference for slskdN's REST API.

## Base URL

All API endpoints are prefixed with `/api/v0/` (API version 0).

**Base URL**: `http://localhost:5000/api/v0/`

## Authentication

slskdN supports multiple authentication methods:

### Cookie-Based Authentication (Web UI)

- Default authentication method for web interface
- Session cookies set after login
- CSRF protection enabled for mutating operations

### JWT Authentication (API Clients)

- Obtain JWT token via `/api/v0/session` endpoint
- Include in `Authorization: Bearer <token>` header
- No CSRF protection required

### API Key Authentication (External Tools)

- Configure API key in settings
- Include in `X-API-Key: <key>` header
- No CSRF protection required

## API Versioning

slskdN uses URL-based versioning: `/api/v{version}/`

- **Current version**: `v0`
- **Future versions**: `v1`, `v2`, etc.
- Version specified in route: `[Route("api/v{version:apiVersion}/[controller]")]`

## Response Format

### Success Response

```json
{
  "data": { ... },
  "status": "ok"
}
```

### Error Response (ProblemDetails - RFC 7807)

```json
{
  "type": "https://tools.ietf.org/html/rfc7231#section-6.5.1",
  "title": "Bad Request",
  "status": 400,
  "detail": "Invalid request parameters",
  "instance": "/api/v0/endpoint"
}
```

Some validation endpoints preserve their existing string error body and add
the stable code in the `X-Slskd-Error-Code` response header. CORS exposes this
header when configured. Clients should use the code for localization; the
English string body remains available to clients that do not provide
translations. Unknown or raw server error text is not a stable UI message and
should be shown through a generic localized error in the Web UI.

Current stable validation codes:

| Code | English source message |
| --- | --- |
| `source-feed-import.source-text-required` | `SourceText is required` |
| `source-feed-import.limit-must-be-positive` | `Limit must be greater than 0` |
| `songid.source-required` | `SongID source is required.` |
| `songid.request-invalid` | `SongID request is invalid.` |
| `songid.analysis-queue-failed` | `SongID analysis could not be queued.` |

## API Endpoints

### Core APIs

#### Application
- `GET /api/v0/application` - Get application state
- `DELETE /api/v0/application` - Shutdown application (admin only)

#### Server (Soulseek)
- `PUT /api/v0/server` - Connect to Soulseek
- `DELETE /api/v0/server` - Disconnect from Soulseek
- `GET /api/v0/server` - Get server status

#### Session
- `GET /api/v0/session` - Get current session
- `POST /api/v0/session` - Create session (login)
- `DELETE /api/v0/session` - End session (logout)

#### Rooms

Room operations accept ordinary names in the existing `/rooms/joined/{roomName}` routes. For room names that contain `/`, use the query-addressed routes below so routing does not depend on encoded slashes in a path segment:

- `GET /api/v0/rooms/by-name?roomName=%2Fmu%2F` - Get a joined room
- `GET /api/v0/rooms/by-name/messages?roomName=%2Fmu%2F&since=0` - Read room messages
- `GET /api/v0/rooms/by-name/users?roomName=%2Fmu%2F` - List room users
- `POST /api/v0/rooms/by-name/messages?roomName=%2Fmu%2F` - Send a room message
- `POST /api/v0/rooms/by-name/ticker?roomName=%2Fmu%2F` - Set a room ticker
- `POST /api/v0/rooms/by-name/members?roomName=%2Fmu%2F` - Add a room member
- `DELETE /api/v0/rooms/by-name?roomName=%2Fmu%2F` - Leave a room

Pass the full room name as the `roomName` query value; URL-encode it as normal for a query string. The existing routes remain available for compatibility. If a request supplies both a route name and a different `roomName` query value, the API returns `400 Bad Request`.

### Search APIs

#### Searches
- `POST /api/v0/searches` - Start a new search
- `GET /api/v0/searches?limit=250&afterStartedAt=2026-08-20T12%3A00%3A00Z&afterId=00000000-0000-0000-0000-000000000001&source=wishlist` - List a page of searches
- `GET /api/v0/searches/{id}` - Get search details
- `GET /api/v0/searches/{id}/responses` - Get search responses
- `PUT /api/v0/searches/{id}` - Update search
- `DELETE /api/v0/searches/{id}` - Cancel/delete search
- `DELETE /api/v0/searches` - Clear all searches

Search listing remains a plain JSON array. `limit` controls the maximum number
of rows, `offset` skips previously requested rows, and `source` optionally
filters to `manual`, `wishlist`, or `auto-replace`. To continue a changing
search list without shifting its page boundary, pass the last row's
`startedAt` as `afterStartedAt` and its `id` as `afterId`; supply both values
together and do not combine them with a nonzero offset. The default limit is
500. The Web UI starts with the live hub's capped 500-row snapshot, then uses
REST continuation pages of 250; if the hub is unavailable, its REST fallback
starts at 250. It merges page rows into the live list.

#### Search Actions
- `POST /api/v0/searches/{searchId}/items/{itemId}/download` - Download search result
- `POST /api/v0/searches/{searchId}/items/{itemId}/stream` - Stream search result (Pod/Mesh only)

The search-result download action retains the originating search ID and query
with the queued request. Both values are available to completed-destination
templates.

#### Metrics

- `GET /api/v0/telemetry/prometheus` - Get Prometheus metrics as text or JSON
- `GET /api/v0/telemetry/metrics` - Get Prometheus metrics as text or JSON
- `GET /api/v0/telemetry/prometheus/kpis` - Get the selected metrics as JSON
- `GET /api/v0/telemetry/metrics/kpi` - Get the selected metrics as JSON

The two metrics endpoints accept repeatable `include` and `exclude` query
parameters. Each value is a regular expression matched against a metric-family
name; multiple includes are combined with OR, and any matching exclude removes
that family. For example, `?include=^slskd_&exclude=secret` keeps application
metrics except names containing `secret`. Text and JSON responses use the same
filter rules. With no filter parameters, the existing complete output is
preserved.

Each parameter accepts at most 8 patterns, each no longer than 128 characters.
Patterns have a 100 ms match timeout. Empty or invalid patterns, excessive
counts or lengths, and filters that exceed the timeout return `400 Bad Request`.
The scrape endpoint configured by `metrics.url` accepts the same query
parameters and continues to use its configured Basic authentication.

#### Reports

- `GET /api/v0/telemetry/reports/transfers/summary` - Summarize completed transfers

The summary defaults to the seven days ending at the request time. Supply
`start` and `end` to choose another interval. Each direction is grouped by
final transfer state; successful rows report the count and `totalBytes` based
on bytes actually transferred.

### Transfer APIs

#### Downloads
- `POST /api/v0/transfers/downloads/{username}` - Queue one or more downloads
- `GET /api/v0/transfers/downloads` - List downloads
- `GET /api/v0/transfers/downloads/{username}/{id}` - Get download details
- `GET /api/v0/transfers/downloads/{username}/{id}/position` - Get queue position
- `DELETE /api/v0/transfers/downloads/{username}/{id}` - Cancel download
- `GET /api/v0/transfers/changes` - Read a transfer snapshot or incremental changes
- `GET /api/v0/transfers/history` - Read a stable page of successful history

Each queued file may include `batchId`, `batchExternalId`, `searchId`, and
`searchText`. These optional values are retained with the download request and
can be used by the global completed-destination template. Existing clients can
continue to omit them. A request-level `destination` query value chooses its
root and keeps its existing precedence over the global subdirectory template.

```json
[
  {
    "filename": "Music/Album/Track.flac",
    "size": 24823104,
    "batchId": "c681ca67-a187-4d7f-8e6d-13699f468ad7",
    "batchExternalId": "lidarr-album-481",
    "searchId": "7b82c49b-39d7-4ac4-a61d-97144f7336bc",
    "searchText": "Artist Album"
  }
]
```

See [Transfer Operations](transfer-operations.md) for supported destination
tokens, collision policy, filesystem-safety rules, and CLI/YAML configuration.

Transfer timestamp fields are serialized as UTC ISO 8601 values with a `Z`
suffix. Convert them to local time only for display; retain the UTC value for
sorting and comparisons.

The transfer changes response keeps its existing shape for unpaged requests.
For a bounded initial snapshot, add `limit` (1 through 500); `direction` may be
`download` or `upload`. The response includes `hasMore` and, when another page
exists, `nextAfterRequestedAt` and `nextAfterId`. Continue the same snapshot by
passing its `cursor` as `asOf` and both continuation values as
`afterRequestedAt` and `afterId`. Pages are ordered by request time, newest
first, with transfer ID as a stable tie-breaker. Both continuation values must
be supplied together and require the original `asOf` watermark. A continuation
keeps that snapshot boundary, so rows changed afterward arrive through the
incremental `since` query instead. The `since` and page parameters cannot be
combined.

Successful history has a separate stable page route. It accepts `direction`,
an optional `asOf` watermark, `offset`, and `limit` (1 through 500; default
250). The Web UI loads active and unsuccessful rows in bounded pages and loads
successful history separately. Its retry and cancel-all actions apply to loaded
rows; the completed-row clear action applies to the server list.

#### Download requests

- `GET /api/v0/downloads/requests?state=active|completed|failed|cancelled` - List request-level records, optionally filtered by state
- `GET /api/v0/downloads/requests/{id}` - Get a request and its transfer attempts
- `PATCH /api/v0/downloads/requests/{id}/name` - Rename its display label with `{"name":"New label"}`
- `POST /api/v0/downloads/requests/{id}/cancel` - Cancel the current attempt and mark the request cancelled

These endpoints operate on the stable user-facing request. The existing
`/api/v0/transfers/downloads` endpoints expose individual transfer attempts.
Terminal requests are removed by `retention.transfers.removed` only after their
download attempts have expired and been deleted. See [Transfer Operations](transfer-operations.md)
for retention behavior and timestamp details.

#### Uploads
- `GET /api/v0/transfers/uploads` - List uploads
- `GET /api/v0/transfers/uploads/{username}/{id}` - Get upload details
- `DELETE /api/v0/transfers/uploads/{username}/{id}` - Cancel upload

### Multi-Source / Swarm APIs

#### Swarm Downloads
- `POST /api/v0/multisource/swarm` - Start swarm download
- `POST /api/v0/multisource/swarm/async` - Start swarm download (async)
- `GET /api/v0/multisource/jobs/{jobId}` - Get swarm job status
- `GET /api/v0/multisource/jobs` - List active swarm jobs

#### Swarm Tracing
- `GET /api/v0/traces/{jobId}/summary` - Get swarm trace summary with peer contributions

#### Swarm Fairness
- `GET /api/v0/fairness/summary` - Get fairness/contribution summary

### Job APIs

#### Jobs
- `GET /api/jobs` - List all jobs (filterable, sortable, paginated)
- `GET /api/jobs/{id}` - Get job details
- `POST /api/jobs/mb-release` - Create MusicBrainz release job
- `POST /api/jobs/discography` - Create discography download job
- `POST /api/jobs/label-crate` - Create label crate download job

### User APIs

#### Users
- `GET /api/v0/users` - List users
- `GET /api/v0/users/{username}` - Get user details
- `GET /api/v0/users/{username}/group` - Get user group membership
- `GET /api/v0/users/{username}/files` - Browse user files

#### User Notes
- `GET /api/v0/users/{username}/notes` - Get user notes
- `POST /api/v0/users/{username}/notes` - Create/update user note
- `DELETE /api/v0/users/{username}/notes` - Delete user note

### Messaging APIs

#### Conversations
- `GET /api/v0/conversations` - List saved private-message conversations
- `GET /api/v0/conversations/{username}` - Get a private-message conversation
- `PUT /api/v0/conversations/{username}` - Acknowledge messages for a conversation
- `POST /api/v0/conversations/{username}` - Send one private message to a user
- `DELETE /api/v0/conversations/{username}` - Delete a saved conversation
- `POST /api/v0/conversations/batch` - Send one native Soulseek multi-recipient private message

Batch private-message request:

```json
{
  "usernames": ["alice", "bob"],
  "message": "hello"
}
```

Recipients are trimmed, deduplicated case-insensitively, and capped at 100 unique usernames by the runtime. slskdN persists one outbound local conversation row per recipient after the native send succeeds.

### Soulseek Native Discovery APIs

These endpoints expose native Soulseek server commands through explicit authenticated API calls. They are rate-limited through the Soulseek safety limiter and do not run automatically during normal search, browse, room, transfer, or one-to-one private-message workflows.

#### Interests
- `POST /api/v0/soulseek/interests` - Add a liked interest
- `DELETE /api/v0/soulseek/interests/{item}` - Remove a liked interest
- `POST /api/v0/soulseek/hated-interests` - Add a hated interest
- `DELETE /api/v0/soulseek/hated-interests/{item}` - Remove a hated interest

Interest request:

```json
{
  "item": "ambient"
}
```

#### Recommendations and Similarity
- `GET /api/v0/soulseek/recommendations` - Get recommendations for the logged-in account
- `GET /api/v0/soulseek/recommendations/global` - Get global recommendations
- `GET /api/v0/soulseek/users/{username}/interests` - Get a user's liked and hated interests
- `GET /api/v0/soulseek/users/similar` - Get users similar to the logged-in account
- `GET /api/v0/soulseek/items/{item}/recommendations` - Get recommendations related to an item string
- `GET /api/v0/soulseek/items/{item}/similar-users` - Get users associated with an item string

Recommendation response:

```json
{
  "recommendations": [
    { "item": "ambient", "score": 42 }
  ],
  "unrecommendations": []
}
```

User interests response:

```json
{
  "username": "alice",
  "liked": ["ambient"],
  "hated": ["noise"]
}
```

Native recommendation item strings are discovery/search seeds, not verified catalog identities. API clients should keep review steps before download automation.

### Canonical Opinion APIs

These endpoints expose durable opinion records used by Soulseek interest
imports, operator annotations, peer trust, and pod affinity. Native Soulseek
liked/hated interests remain public weak signals; explicit trust/distrust
records are separate and can target users, files, content hashes, artists,
albums, tracks, pods, sources, mesh peers, search terms, or other identifiers.

- `GET /api/v0/opinions` - List opinion records with optional filters
- `GET /api/v0/opinions/summary` - Summarize opinions for a subject
- `POST /api/v0/opinions` - Submit or replace an opinion record
- `DELETE /api/v0/opinions/{id}` - Delete an opinion record

Summary request:

```http
GET /api/v0/opinions/summary?subjectType=User&subjectId=alice&scope=global
```

Opinion request:

```json
{
  "issuer": "local:operator",
  "subjectType": "User",
  "subjectId": "alice",
  "kind": "Trust",
  "strength": 0.75,
  "confidence": 0.9,
  "scope": "global",
  "source": "operator",
  "reason": "Completed transfers and useful chat history",
  "evidence": [
    { "type": "transfer", "value": "completed" }
  ]
}
```

#### Mesh Rendezvous and Runtime Capabilities
- `GET /api/v0/soulseek/mesh-rendezvous/status` - Get rendezvous enablement, interest tag, and privacy text
- `POST /api/v0/soulseek/mesh-rendezvous/interest` - Publish the public `slskdn-mesh-v1` interest tag
- `DELETE /api/v0/soulseek/mesh-rendezvous/interest` - Remove the public `slskdn-mesh-v1` interest tag
- `GET /api/v0/soulseek/mesh-rendezvous/users` - Load Soulseek similar-user rendezvous candidates
- `GET /api/v0/soulseek/mesh-rendezvous/discover` - Load rendezvous candidates and probe runtime capability descriptors
- `GET /api/v0/soulseek/peer-capabilities` - Return known runtime peer capability records

Rendezvous endpoints are disabled unless `mesh.enable_soulseek_rendezvous` / `mesh.enableSoulseekRendezvous` is enabled. Publishing the rendezvous interest intentionally makes the Soulseek account recognizable as a slskdN mesh participant. Runtime peer capability records come from signed slskdN capability descriptors exchanged over Soulseek peer-message connections when available.

Discovery response:

```json
{
  "interestTag": "slskdn-mesh-v1",
  "users": [
    { "username": "mesh-peer", "rating": 10 }
  ],
  "capabilityRecords": [
    {
      "username": "mesh-peer",
      "peerId": "peer-id",
      "features": ["mesh_sync", "swarm_download"],
      "overlayPort": 50305,
      "messageType": "Hello",
      "nonce": "nonce",
      "observedAt": "2026-05-05T00:00:00Z",
      "signed": true
    }
  ]
}
```

### Pod APIs

#### Pods
- `GET /api/v0/pods` - List pods
- `GET /api/v0/pods/{podId}` - Get pod details
- `POST /api/v0/pods` - Create pod
- `PUT /api/v0/pods/{podId}` - Update pod
- `DELETE /api/v0/pods/{podId}` - Delete pod
- `POST /api/v0/pods/{podId}/join` - Join pod
- `POST /api/v0/pods/{podId}/leave` - Leave pod

#### Pod Messages
- `GET /api/v0/pods/{podId}/channels/{channelId}/messages` - Get messages
- `POST /api/v0/pods/{podId}/channels/{channelId}/messages` - Send message

### Collections & Sharing APIs

#### Collections
- `GET /api/v0/collections` - List collections
- `GET /api/v0/collections/{id}` - Get collection details
- `POST /api/v0/collections` - Create collection
- `PUT /api/v0/collections/{id}` - Update collection
- `DELETE /api/v0/collections/{id}` - Delete collection

#### Share Grants
- `GET /api/v0/share-grants` - List share grants (shared with me)
- `GET /api/v0/share-grants/{id}` - Get share grant details
- `GET /api/v0/share-grants/{id}/manifest` - Get collection manifest
- `POST /api/v0/share-grants/{id}/backfill` - Backfill entire collection

### Mesh APIs

#### Mesh Status
- `GET /api/v0/mesh` - Get mesh status
- `GET /api/v0/mesh/health` - Get mesh health

#### DHT Rendezvous
- `GET /api/v0/dht/status` - Get DHT status

### Hash Database APIs

#### HashDb
- `GET /api/v0/hashdb/stats` - Get database statistics
- `GET /api/v0/hashdb/schema` - Get schema version

### Wishlist APIs

#### Wishlist
- `GET /api/v0/wishlist` - List wishlist items
- `POST /api/v0/wishlist` - Create wishlist item
- `PUT /api/v0/wishlist/{id}` - Update wishlist item
- `DELETE /api/v0/wishlist/{id}` - Delete wishlist item
- `POST /api/v0/wishlist/{id}/run` - Run wishlist search now

### Capabilities APIs

#### Capabilities
- `GET /api/v0/capabilities` - Get peer capabilities

### Streaming APIs

#### Streams
- `GET /api/v0/relay/streams/{contentId}` - Stream content (range requests supported)

### Library Health APIs

#### Library Health
- `GET /api/v0/library-health` - Get library health status
- `POST /api/v0/library-health/scan` - Start library health scan

### Options & Configuration

#### Options
- `GET /api/v0/options` - Get configuration options
- `PUT /api/v0/options` - Update configuration (if remote config enabled)

## Common Patterns

### Pagination

Many list endpoints support pagination:

```
GET /api/v0/endpoint?limit=20&offset=0
```

**Parameters:**
- `limit`: Number of items per page (default: varies by endpoint)
- `offset`: Number of items to skip (default: 0)

**Response:**
```json
{
  "count": 100,
  "items": [ ... ],
  "hasMore": true
}
```

### Filtering

Some endpoints support filtering:

```
GET /api/v0/jobs?type=discography&status=running
```

### Sorting

Some endpoints support sorting:

```
GET /api/v0/jobs?sortBy=created_at&sortOrder=desc
```

**Parameters:**
- `sortBy`: Field to sort by
- `sortOrder`: `asc` or `desc`

### Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Success
- `201 Created`: Resource created
- `204 No Content`: Success, no content
- `400 Bad Request`: Invalid request
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict
- `500 Internal Server Error`: Server error
- `501 Not Implemented`: Feature not implemented

### Rate Limiting

Some endpoints have rate limiting:
- Mesh gateway: 100 calls/minute per peer (default)
- Service calls: Configurable per service

Rate limit headers (when applicable):
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## API Discovery

### Swagger/OpenAPI

slskdN does not currently expose Swagger/OpenAPI documentation. API discovery is done via:

1. **Source code**: Controllers in `src/slskd/**/API/**Controller.cs`
2. **Route attributes**: `[Route("api/v{version:apiVersion}/...")]`
3. **HTTP methods**: `[HttpGet]`, `[HttpPost]`, `[HttpPut]`, `[HttpDelete]`

### Finding Endpoints

**By feature:**
- Search: `src/slskd/Search/API/Controllers/`
- Transfers: `src/slskd/Transfers/API/Controllers/`
- Pods: `src/slskd/PodCore/API/Controllers/`
- Collections: `src/slskd/Sharing/API/`

**By route pattern:**
```bash
# Find all controllers
grep -r "\[Route" src/slskd/**/API/**Controller.cs

# Find specific endpoint
grep -r "searches" src/slskd/**/API/**Controller.cs
```

## Frontend API Libraries

Frontend uses API client libraries in `src/web/src/lib/`:

- `api.js` - Base API client
- `searches.js` - Search operations
- `transfers.js` - Download/upload operations
- `jobs.js` - Job management
- `slskdn.js` - Combined stats and utilities

**Example usage:**
```javascript
import * as searchesLib from '../lib/searches';

const results = await searchesLib.startSearch('query', {
  providers: ['pod', 'scene'],
  filters: { minBitrate: 320 }
});
```

## WebSocket / SignalR

Some features use SignalR for real-time updates:

- **Search results**: Real-time search result streaming
- **Transfer progress**: Real-time download/upload progress
- **Events**: System events and notifications

**Connection:**
```javascript
import { HubConnectionBuilder } from '@microsoft/signalr';

const connection = new HubConnectionBuilder()
  .withUrl('/hubs/events')
  .build();

await connection.start();
```

## Examples

### Start a Search

```bash
curl -X POST http://localhost:5000/api/v0/searches \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "query": "artist album",
    "filters": {
      "minBitrate": 320
    }
  }'
```

### Download a File

```bash
curl -X POST "http://localhost:5000/api/v0/searches/{searchId}/items/{itemId}/download" \
  -H "Authorization: Bearer <token>"
```

### Get Swarm Job Status

```bash
curl http://localhost:5000/api/v0/multisource/jobs/{jobId} \
  -H "Authorization: Bearer <token>"
```

### List Jobs with Filtering

```bash
curl "http://localhost:5000/api/jobs?type=discography&status=running&limit=20&offset=0" \
  -H "Authorization: Bearer <token>"
```

## Best Practices

1. **Use API libraries**: Don't call endpoints directly from components
2. **Handle errors**: Always handle API errors gracefully
3. **Return safe values**: API libs should return empty arrays, not undefined
4. **Use pagination**: Don't fetch all data at once
5. **Respect rate limits**: Don't spam API endpoints
6. **Use appropriate auth**: JWT for API clients, cookies for web UI

## Version History

- **v0**: Current version (initial API)

Future versions will maintain backward compatibility where possible.

---

**See Also:**
- [Getting Started](getting-started.md) - User guide
- [How It Works](HOW-IT-WORKS.md) - Architecture overview
- [Configuration](config.md) - Configuration options
