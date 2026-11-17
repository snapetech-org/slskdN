# E2E Testing Framework Guide

## Overview

This guide covers end-to-end (E2E) testing using Playwright with a multi-peer harness. E2E tests exercise the **real stack**:

- Real API host (Kestrel)
- Real WebUI bundle (served from wwwroot)
- Real auth/session/token flows
- Real storage (per-instance app directories)
- Real streaming (HTTP Range requests)
- Real peer interactions (invite/share/backfill/stream)
- Optional: Real Soulseek with `flags.no_connect: true` for deterministic CI

## Test Philosophy

### What Should Be E2E

E2E tests cover **high-value user journeys** (product contract tests):

1. **Login / Session / Auth**
   - Login succeeds
   - Protected routes require auth
   - Logout clears session

2. **Library Ingest**
   - Fixture share directory is indexed
   - Items appear in UI
   - Metadata (filename/size/duration) present

3. **Search**
   - Local search returns expected fixture hits
   - Hybrid search path (if enabled) returns mesh hits
   - (Optional) Verify "no_connect" disables Soulseek provider gracefully

4. **Collections + Sharing**
   - Create group
   - Add contact (via invite)
   - Create collection/playlist
   - Share to group/user
   - Recipient sees "Shared with me"

5. **Streaming**
   - Recipient streams an item
   - Seek works (Range requests)
   - Concurrency limit blocks excess (optional)

6. **Backfill / Downloads**
   - Recipient triggers backfill
   - File appears in downloads, status completes

7. **Permissions / Policy**
   - Stream denied when policy says no
   - Download denied when policy says no
   - Expired token denied

8. **Disaster Mode Behavior** (if enabled)
   - Toggle Soulseek unhealthy state
   - Confirm mesh-only fallback behavior

**Target: 10-20 E2E tests total** covering all critical journeys.

### What Should NOT Be E2E

Don't E2E test these exhaustively (use unit/integration tests instead):

- Every validation error path
- Deep sorting/ranking edge cases
- Every file type/codec combination
- DHT routing correctness at scale
- Performance and stress limits

## Test Structure

```
tests/e2e/
├── playwright.config.ts          # Playwright configuration
├── package.json                  # Node dependencies (Playwright)
├── fixtures/
│   ├── nodes.ts                  # Node URLs, credentials, ports
│   ├── helpers.ts                # Login helper, click helper, waitForHealth
│   └── selectors.ts              # data-testid map
├── specs/
│   ├── smoke.spec.ts             # Boot, login, basic page loads (1-3 tests)
│   ├── library.spec.ts          # Indexing + browsing
│   ├── search.spec.ts             # Local search + mesh search
│   ├── sharing.spec.ts           # Contacts + group + share + manifest
│   ├── streaming.spec.ts         # Play + seek
│   ├── backfill.spec.ts          # Download completion
│   └── policy.spec.ts            # Deny/expire behavior
└── harness/
    ├── SlskdnNode.ts             # Node launcher (spawns dotnet process)
    ├── MultiPeerHarness.ts       # Manages multiple nodes
    └── TestFixtures.ts           # Deterministic test data
```

## Local Setup

### Prerequisites

```bash
# Node.js 22.22.2+ (for the frontend and Playwright)
node --version  # Should be 22.22.2+

# .NET 11.0 SDK (for building slskdn)
dotnet --version  # Should be 11.0.x
```

### Installation

```bash
# From the repository root, install the Web and E2E workspace dependencies
pnpm install --frozen-lockfile

# Install Playwright browsers
pnpm --filter @slskdn/e2e exec playwright install --with-deps chromium
```

### Running Tests Locally

```bash
# Run all E2E tests
pnpm --filter @slskdn/e2e test

# Run specific test file
pnpm --filter @slskdn/e2e exec playwright test specs/smoke.spec.ts

# Run in headed mode (see browser)
pnpm --filter @slskdn/e2e exec playwright test --headed

# Run with debug output
DEBUG=pw:api pnpm --filter @slskdn/e2e exec playwright test

# Run single test
pnpm --filter @slskdn/e2e exec playwright test -g "should login successfully"
```

### Local Test Execution Flow

1. **Harness starts nodes**: Launches 2-3 slskdn instances (Alice, Bob, Carol)
   - Each gets unique app directory (`/tmp/slskdn-test-{nodeId}/`)
   - Each gets unique ports (ephemeral)
   - Each gets fixture share directory

2. **Playwright launches browsers**: Opens browser contexts for each node

3. **Tests execute**: Drive UI, verify behavior

4. **Cleanup**: Nodes stop, temp directories cleaned (unless `KEEP_ARTIFACTS=1`)

## CI Setup

### GitHub Actions Workflow

E2E tests run in `.github/workflows/e2e-tests.yml`. The job installs the root
pnpm workspace, builds the Web package, stages its output in `wwwroot`, installs
Chromium through the E2E workspace, and runs:

```bash
pnpm --filter @slskdn/e2e test:e2e:ci
```

### CI Determinism Rules

1. **Use `flags.no_connect: true`**: Disables Soulseek to avoid network nondeterminism
2. **Avoid mDNS in CI**: Use invite links/codes instead of LAN discovery
3. **Use synthetic fixtures**: All tests use `test-data/slskdn-test-fixtures/`
4. **Fixed ports**: Use ephemeral ports but avoid conflicts
5. **No real network**: All peer interactions via localhost mesh

## Test Implementation Details

### Node Harness

Each test node is a real slskdn process:

```typescript
// harness/SlskdnNode.ts
export class SlskdnNode {
  private process: ChildProcess;
  private apiPort: number;
  private appDir: string;
  
  async start(config: NodeConfig): Promise<void> {
    // Allocate ephemeral port
    this.apiPort = await findFreePort();
    
    // Create isolated app directory
    this.appDir = await fs.mkdtemp('/tmp/slskdn-test-');
    
    // Build config with:
    // - Web:Port = apiPort
    // - Web:Host = 127.0.0.1
    // - Directories:Downloads = appDir/downloads
    // - Shares:Directories = fixtureShareDir
    // - Feature:IdentityFriends = true
    // - Feature:CollectionsSharing = true
    // - Flags:NoConnect = SLSKDN_TEST_NO_CONNECT (CI)
    
    // Launch: dotnet run --project src/slskd/slskd.csproj --no-build
    this.process = spawn('dotnet', ['run', '--project', 'src/slskd/slskd.csproj', '--no-build'], {
      cwd: process.cwd(),
      env: { ...process.env, ...configEnv }
    });
    
    // Wait for health endpoint
    await this.waitForHealth();
  }
  
  async waitForHealth(): Promise<void> {
    // Poll http://127.0.0.1:${apiPort}/health until 200
  }
  
  get apiUrl(): string {
    return `http://127.0.0.1:${this.apiPort}`;
  }
  
  async stop(): Promise<void> {
    this.process.kill();
    await this.process;
    // Cleanup appDir unless KEEP_ARTIFACTS
  }
}
```

### Multi-Peer Harness

Manages multiple nodes:

```typescript
// harness/MultiPeerHarness.ts
export class MultiPeerHarness {
  private nodes: Map<string, SlskdnNode> = new Map();
  
  async startNode(name: string, shareDir: string): Promise<SlskdnNode> {
    const node = new SlskdnNode();
    await node.start({ shareDir, nodeName: name });
    this.nodes.set(name, node);
    return node;
  }
  
  async stopAll(): Promise<void> {
    await Promise.all([...this.nodes.values()].map(n => n.stop()));
    this.nodes.clear();
  }
  
  getNode(name: string): SlskdnNode {
    return this.nodes.get(name)!;
  }
}
```

### Playwright Fixtures

```typescript
// fixtures/nodes.ts
export const testNodes = {
  alice: { name: 'alice', shareDir: 'test-data/slskdn-test-fixtures/music' },
  bob: { name: 'bob', shareDir: 'test-data/slskdn-test-fixtures/book' },
  carol: { name: 'carol', shareDir: 'test-data/slskdn-test-fixtures/tv' }
};

// fixtures/helpers.ts
export async function login(page: Page, apiUrl: string, username: string, password: string) {
  await page.goto(`${apiUrl}/`);
  await page.fill('[data-testid="username"]', username);
  await page.fill('[data-testid="password"]', password);
  await page.click('[data-testid="login-button"]');
  await page.waitForURL(`${apiUrl}/*`, { timeout: 5000 });
}

export async function waitForHealth(apiUrl: string, timeout = 30000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try {
      const res = await fetch(`${apiUrl}/health`);
      if (res.ok) return;
    } catch {}
    await new Promise(r => setTimeout(r, 500));
  }
  throw new Error(`Health check timeout for ${apiUrl}`);
}

// fixtures/selectors.ts
export const selectors = {
  login: {
    username: '[data-testid="login-username"]',
    password: '[data-testid="login-password"]',
    submit: '[data-testid="login-submit"]'
  },
  contacts: {
    createInvite: '[data-testid="contacts-create-invite"]',
    inviteLink: '[data-testid="invite-link"]',
    addFriend: '[data-testid="contacts-add-friend"]'
  },
  shareGroups: {
    createGroup: '[data-testid="sharegroups-create-group"]',
    groupName: '[data-testid="group-name-input"]',
    submit: '[data-testid="create-group-submit"]'
  }
};
```

### Example Test

```typescript
// specs/sharing.spec.ts
import { test, expect } from '@playwright/test';
import { MultiPeerHarness } from '../harness/MultiPeerHarness';
import { login, waitForHealth } from '../fixtures/helpers';
import { selectors } from '../fixtures/selectors';

test.describe('Sharing', () => {
  let harness: MultiPeerHarness;
  
  test.beforeAll(async () => {
    harness = new MultiPeerHarness();
    await harness.startNode('alice', 'test-data/slskdn-test-fixtures/music');
    await harness.startNode('bob', 'test-data/slskdn-test-fixtures/book');
  });
  
  test.afterAll(async () => {
    await harness.stopAll();
  });
  
  test('should create invite and add contact', async ({ page, context }) => {
    const alice = harness.getNode('alice');
    const bob = harness.getNode('bob');
    
    // Alice creates invite
    await page.goto(`${alice.apiUrl}/contacts`);
    await login(page, alice.apiUrl, 'admin', 'admin');
    await page.click(selectors.contacts.createInvite);
    const inviteLink = await page.textContent(selectors.contacts.inviteLink);
    expect(inviteLink).toContain('slskdn://invite/');
    
    // Bob adds Alice from invite
    const bobPage = await context.newPage();
    await bobPage.goto(`${bob.apiUrl}/contacts`);
    await login(bobPage, bob.apiUrl, 'admin', 'admin');
    await bobPage.click(selectors.contacts.addFriend);
    await bobPage.fill('[data-testid="invite-link-input"]', inviteLink!);
    await bobPage.fill('[data-testid="contact-nickname"]', 'Alice');
    await bobPage.click('[data-testid="add-friend-submit"]');
    
    // Verify contact appears
    await expect(bobPage.locator('text=Alice')).toBeVisible();
    
    await bobPage.close();
  });
  
  test('should create share group and share collection', async ({ page, context }) => {
    const alice = harness.getNode('alice');
    const bob = harness.getNode('bob');
    
    // Alice creates group
    await page.goto(`${alice.apiUrl}/sharegroups`);
    await login(page, alice.apiUrl, 'admin', 'admin');
    await page.click(selectors.shareGroups.createGroup);
    await page.fill(selectors.shareGroups.groupName, 'Test Group');
    await page.click(selectors.shareGroups.submit);
    
    // Verify group appears
    await expect(page.locator('text=Test Group')).toBeVisible();
    
    // TODO: Add Bob to group, create collection, share, verify Bob sees it
  });
});
```

## Integration with Existing Test Infrastructure

E2E tests complement the existing L0-L3 test layers:

- **L0 (Unit)**: Fast, isolated business logic
- **L1 (Protocol)**: Soulseek protocol compliance
- **L2 (Multi-Client)**: Backend integration (no browser)
- **L3 (Disaster/Mesh)**: Mesh-only scenarios
- **E2E (Playwright)**: Full-stack user journeys

E2E tests can reuse:
- Test fixtures from `test-data/slskdn-test-fixtures/`
- Node launcher patterns from `tests/slskd.Tests.Integration/Harness/`
- Deterministic test data generation

## Troubleshooting

### Tests Fail with "Address already in use"

```bash
# Kill lingering slskdn processes
pkill -9 -f "dotnet.*slskd"
# Or use different port range in config
```

### Tests Timeout

```bash
# Increase timeout
export SLSKDN_TEST_TIMEOUT=600
pnpm --filter @slskdn/e2e test
```

### Browser Not Found

```bash
# Reinstall Playwright browsers
pnpm --filter @slskdn/e2e exec playwright install chromium
```

### Artifacts Not Cleaning Up

```bash
# Manual cleanup
rm -rf /tmp/slskdn-test-*
```

### CI Flakiness

- Ensure `SLSKDN_TEST_NO_CONNECT=true` in CI
- Use fixed test fixtures (no random data)
- Add retries for network-dependent tests
- Increase timeouts for slower CI runners

## Next Steps

1. **Create test structure**: Set up `tests/e2e/` directory
2. **Implement harness**: `SlskdnNode` and `MultiPeerHarness`
3. **Write smoke tests**: Basic login/page load tests
4. **Expand to full journeys**: Sharing, streaming, backfill
5. **Add CI job**: Integrate into GitHub Actions

See `tests/e2e/README.md` for implementation details.
