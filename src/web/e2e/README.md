# E2E Test Suite

This directory contains end-to-end tests for slskdn using Playwright.

## Test Structure

- `smoke-auth.spec.ts` - Authentication and basic health checks
- `core-pages.spec.ts` - Core UI pages (dashboard, system, downloads, uploads, rooms, chat, users)
- `ui-regressions.spec.ts` - Responsive layouts, keyboard actions, and control guidance across populated UI surfaces
- `library.spec.ts` - Library indexing and browsing
- `search.spec.ts` - Search functionality
- `multippeer-sharing.spec.ts` - Multi-peer sharing workflows (invites, groups, collections, shares)
- `streaming.spec.ts` - Streaming functionality
- `policy.spec.ts` - Policy enforcement (stream/download restrictions)

## Intentionally Skipped Tests

Some tests are intentionally skipped because they are better tested at the API level or require specific timing/setup that is difficult to achieve reliably in E2E tests.

### `policy.spec.ts`

#### `expired_token_denied`
**Status**: Skipped  
**Reason**: This test requires precise timing (create share with 1-second expiry, wait 2 seconds, verify denial). This is better tested at the API level where timing can be controlled precisely. E2E tests are inherently flaky for sub-second timing requirements.

**Alternative**: API-level unit/integration tests can create shares with specific expiry times and verify token validation logic directly.

### `streaming.spec.ts`

#### `concurrency_limit_blocks_excess_streams`
**Status**: Skipped  
**Reason**: This test requires specific share setup with `MaxConcurrentStreams=1` and multiple streamable items. The test would need to:
1. Create a share with specific concurrency policy
2. Start first stream
3. Attempt second stream
4. Verify second stream is blocked

This is better tested at the API level where we can:
- Mock the stream session limiter
- Verify policy enforcement logic directly
- Test edge cases more reliably

**Alternative**: API-level tests can directly test `IStreamSessionLimiter` and policy enforcement without UI interaction.

### `search.spec.ts` / `library.spec.ts`

Some tests may skip if UI features are not available:
- Search page may not exist if feature is disabled
- Browse navigation may not be available if library browsing is not implemented

These are graceful skips that allow tests to pass when features are intentionally disabled or not yet implemented.

## Running Tests

### Local Development

```bash
# Start nodes manually or let harness start them
pnpm --filter @slskdn/web test:e2e
```

### Player Screen-Reader Speech

The isolated Orca runner builds the Web app and Release backend, then starts
the selected Playwright browser beside Orca and Speech Dispatcher in a
digest-pinned Playwright container. The container shares the virtual display,
accessibility bus and isolated audio sinks with the host runner; screen-reader
speech is captured separately from player audio:

```bash
pnpm --filter @slskdn/web run test:player:screen-reader
```

By default, `SLSKDN_PLAYER_A11Y_BROWSER` is `chromium` and
`SLSKDN_PLAYER_A11Y_SUITE` is `all`. The full suite checks playback-status
speech plus keyboard changes to volume and equalizer values. Set the suite to
`playback` or `controls` to run only that part. Set the browser to `firefox` or
`webkit` to run the matching browser from the same Playwright image. Docker,
the .NET 10 SDK, and the project’s normal pnpm dependencies must be available.

Current direct evidence covers the full suite in Linux Chromium and Firefox
(2/2 workflows in each). The Firefox playback-only profile also passes 1/1;
Orca speaks the track-start, pause/resume, compact-mode, stop, volume and
equalizer updates. The controls workflow checks consistent Up/Right increases
and Down/Left decreases for the vertical equalizer sliders in Chromium and
Firefox; its headless WebKit browser assertion also passes. Orca cannot resolve
WebKit's page accessibility root in the current pinned runtime, so WebKit
speech is not verified. See
`docs/dev/player-quality-audit.md` for the tested scope and remaining gaps.

### CI Environment

Tests run with `SLSKDN_TEST_NO_CONNECT=true` to disable Soulseek connections for deterministic testing.

```bash
pnpm --filter @slskdn/web test:e2e:ci
```

### Loopback Soulseek Journeys

The core journey suite validates Soulseek search, a completed peer download, and
private-message delivery through the UI against two isolated slskdN nodes and
the pinned Soulfind test server. It binds Soulfind to loopback, disables public
DHT bootstrap, and does not contact public Soulseek peers. The pinned Docker
image must already be available locally; the runner never pulls it. A loopback
TCP proxy normalizes negative private-message IDs from this fixture for the
protocol client and maps acknowledgements back to the fixture IDs; production
protocol validation is unchanged.

The proxy's frame-splitting and acknowledgement mapping can be checked without
starting Soulfind:

```bash
pnpm --filter @slskdn/web exec vitest run scripts/soulseekPrivateMessageIdMapper.test.ts
```

```bash
pnpm --filter @slskdn/web test:core:soulseek-journeys
```

The Player radio overlap runner exercises a listed stream during reciprocal
Soulseek transfers between two local nodes, checks the fairness response while
traffic is active, and confirms a fresh ranged stream after the active Player
stream is stopped. Each node is capped at 128 KiB/s. Run it with:

```bash
pnpm --filter @slskdn/web test:player:soulseek-radio
```

It uses the pinned loopback Soulfind image with `--pull=never` and publishes
its port only on `127.0.0.1`; it does not contact public Soulseek peers. This
is loopback evidence and does not establish WAN behavior.

Player resource captures keep `/proc` read interruptions, recovered retries,
unavailable memory samples and process churn distinct. The collector retries
`EINTR` and `EAGAIN` once; missing process paths, persistent errors and PID
identity changes remain unavailable rather than being counted as zero.

## Test Harness

The `MultiPeerHarness` manages multiple slskdn instances for cross-node testing:
- Launches nodes on different ports
- Manages test fixtures (music, books, etc.)
- Handles cleanup on test completion

See `harness/MultiPeerHarness.ts` for details.

## Test Fixtures

E2E tests require real fixture files to be present before running. The harness will **fail fast** if fixtures are missing.

### Required Fixtures

Fixtures must be in `test-data/slskdn-test-fixtures/` with a valid `meta/manifest.json`:

- `book/treasure_island_pg120.txt` (text file)
- Additional audio/video files (see `test-data/slskdn-test-fixtures/meta/fetch_media.sh`)

### Generating Manifest

After downloading fixtures, generate the manifest:

```bash
cd test-data/slskdn-test-fixtures/meta
node generate-manifest.js
```

This creates `manifest.json` with sha256 checksums for validation.

### Node Configuration

Tests use 3 nodes:
- **Node A**: Shares `movie/` + `book/` directories
- **Node B**: Shares `music/` + `tv/` directories  
- **Node C**: Recipient-only (no shares)

### Fixture Validation

The harness validates fixtures on startup:
- Checks fixtures root directory exists
- Validates manifest.json exists and is valid
- Verifies all required files exist
- Optional checksum validation (set `SLSKDN_VALIDATE_FIXTURE_CHECKSUMS=1`)

If validation fails, tests abort immediately with clear error messages.
