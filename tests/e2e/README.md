# E2E Test Implementation

This directory contains Playwright-based end-to-end tests for slskdn.

## Prerequisites

**Before running E2E tests**, ensure the web UI and backend are built so the node serves the latest UI:

```bash
# From repo root: build web, copy to wwwroot, build backend
./bin/build --skip-tests
# Or: pnpm --filter @slskdn/web build && cp -r src/web/build/* src/slskd/wwwroot/ && dotnet build src/slskd/slskd.csproj
```

Without this, the node may serve a stale wwwroot and UI-dependent tests (e.g. Solid page) can fail.

## Quick Start

```bash
# From the repository root, install workspace dependencies
pnpm install --frozen-lockfile

# Install Playwright browsers in the job-scoped cache used by the validation engine
export PLAYWRIGHT_BROWSERS_PATH="$(node -e 'process.stdout.write(require("node:os").tmpdir())')/slskdn-playwright-browsers"
pnpm --filter @slskdn/e2e exec playwright install chromium

# Run the suite with the isolated validation environment
node scripts/validate-development.mjs --task browser-e2e

# Run specific test
pnpm --filter @slskdn/e2e exec playwright test specs/smoke.spec.ts
```

## Project Structure

- `playwright.config.ts`: Playwright configuration
- `fixtures/`: Shared test utilities
- `specs/`: Test specifications
- `harness/`: Node launcher and multi-peer management

## Test Categories

Tests are organized by user journey:

- `smoke.spec.ts`: Basic functionality (login, page loads)
- `library.spec.ts`: Library indexing and browsing
- `search.spec.ts`: Search functionality
- `sharing.spec.ts`: Contacts, groups, collections, sharing
- `streaming.spec.ts`: Streaming and playback
- `backfill.spec.ts`: Download and backfill
- `policy.spec.ts`: Permissions and policy enforcement

## Writing Tests

### Basic Test Structure

```typescript
import { test, expect } from '@playwright/test';
import { MultiPeerHarness } from '../harness/MultiPeerHarness';

test.describe('Feature Name', () => {
  let harness: MultiPeerHarness;
  
  test.beforeAll(async () => {
    harness = new MultiPeerHarness();
    await harness.startNode('alice', 'test-data/slskdn-test-fixtures/music');
  });
  
  test.afterAll(async () => {
    await harness.stopAll();
  });
  
  test('should do something', async ({ page }) => {
    const alice = harness.getNode('alice');
    await page.goto(`${alice.apiUrl}/`);
    // ... test steps
  });
});
```

### Using Helpers

```typescript
import { login, waitForHealth } from '../fixtures/helpers';
import { selectors } from '../fixtures/selectors';

test('should login', async ({ page }) => {
  const node = harness.getNode('alice');
  await login(page, node.apiUrl, 'admin', 'admin');
  await expect(page.locator(selectors.nav.appShell)).toBeVisible();
});
```

Network and Sharing destinations live in click-open navigation groups. System
destinations are grouped into sections, and only the active section's tabs are
shown. Open the relevant group or section before asserting or clicking a
destination.

## Configuration

### Environment Variables

- `SLSKDN_TEST_NO_CONNECT`: Set to `true` to disable Soulseek (CI determinism)
- `SLSKDN_TEST_KEEP_ARTIFACTS`: Set to `1` to keep temp directories after tests
- `SLSKDN_TEST_TIMEOUT`: Test timeout in seconds (default: 300)

### Playwright Configuration

See `playwright.config.ts` for:
- Browser selection (Chromium by default)
- Timeout settings
- Screenshot/video on failure
- Test retries

## CI Integration

E2E tests run in GitHub Actions. See `.github/workflows/e2e-tests.yml`.

Tests run with:
- `SLSKDN_TEST_NO_CONNECT=true` (deterministic)
- Artifact upload on failure
- Parallel execution (if sharding enabled)

## Debugging

### Run in Headed Mode

```bash
pnpm --filter @slskdn/e2e exec playwright test --headed
```

### Debug Mode

```bash
DEBUG=pw:api pnpm --filter @slskdn/e2e exec playwright test
```

### Keep Artifacts

```bash
SLSKDN_TEST_KEEP_ARTIFACTS=1 pnpm --filter @slskdn/e2e test
# Check /tmp/slskdn-test-*/ for logs and data
```

### Single Test Debugging

```bash
pnpm --filter @slskdn/e2e exec playwright test -g "test name" --debug
```

## Adding data-testid Attributes

To make tests more reliable, add `data-testid` attributes to UI components:

```jsx
// Example: Contacts.jsx
<Button data-testid="contacts-create-invite" onClick={...}>
  Create Invite
</Button>
```

Then reference in `fixtures/selectors.ts`:

```typescript
export const selectors = {
  contacts: {
    createInvite: '[data-testid="contacts-create-invite"]'
  }
};
```
