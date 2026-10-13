import { NODES, shouldLaunchNodes } from './env';
import { clickNav, getAuthToken, login, waitForHealth } from './helpers';
import { MultiPeerHarness } from './harness/MultiPeerHarness';
import { expect, test } from '@playwright/test';

test.use({ serviceWorkers: 'block' });

test.describe('UI regression coverage', () => {
  let harness: MultiPeerHarness | null = null;

  test.beforeAll(async () => {
    if (shouldLaunchNodes()) {
      harness = new MultiPeerHarness();
      await harness.startNode('A', 'test-data/slskdn-test-fixtures/music', {
        noConnect: true,
        remoteFileManagement: true,
      });
    }
  });

  test.afterAll(async () => {
    if (harness) {
      await harness.stopAll();
    }
  });

  const getNode = () => (harness ? harness.getNode('A').nodeCfg : NODES.A);

  test('keeps core search visible and groups optional discovery tools', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);
    await page.goto(`${node.baseUrl}/searches`, {
      waitUntil: 'domcontentloaded',
    });

    const searchInput = page.getByTestId('search-input');
    await expect(searchInput).toBeInViewport();
    await expect(searchInput).toBeDisabled();
    await expect(page.getByText('Soulseek connection needed')).toBeVisible();
    await expect(page.getByText('Search Results', { exact: true })).toBeInViewport();
    await expect(
      page.getByRole('button', { name: 'Expand Music discovery tools' }),
    ).toBeInViewport();
    await expect(
      page.getByRole('button', { name: 'Expand SongID' }),
    ).toHaveCount(0);

    const connectionSettings = page.getByRole('link', {
      name: 'Open connection settings',
    });
    await expect(connectionSettings).toBeVisible();
    await page.setViewportSize({ height: 812, width: 375 });
    await expect(connectionSettings).toBeInViewport();
    const hasHorizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(hasHorizontalOverflow).toBe(false);
    await connectionSettings.focus();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/system\/options$/);
    await expect(page.locator('.system')).toBeVisible();

    await page.goto(`${node.baseUrl}/searches`, {
      waitUntil: 'domcontentloaded',
    });
    await page.setViewportSize({ height: 720, width: 1280 });

    await page.getByRole('button', { name: 'Expand Music discovery tools' }).click();
    await expect(page.getByRole('button', { name: 'Expand SongID' })).toBeVisible();
  });

  test('explains the disconnected server action to mouse and assistive users', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);
    await page.goto(`${node.baseUrl}/searches`, {
      waitUntil: 'domcontentloaded',
    });

    const connectionAction = page.getByTitle(
      'Connect to the Soulseek server.',
    );
    await expect(connectionAction).toBeVisible();
    await expect(connectionAction).toHaveAttribute(
      'aria-label',
      'Connect to the Soulseek server.',
    );
  });

  test('explains the logout action and allows canceling the confirmation', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);
    await page.goto(`${node.baseUrl}/searches`, {
      waitUntil: 'domcontentloaded',
    });

    const logoutAction = page.getByTestId('logout');
    await expect(logoutAction).toHaveAttribute(
      'aria-label',
      'Log out of this web session.',
    );
    await logoutAction.hover();
    await expect(
      page.getByText('End this web session and return to the login screen.', {
        exact: true,
      }),
    ).toBeVisible();

    await logoutAction.click();
    await expect(page.getByText('Are you sure you want to log out?')).toBeVisible();
    await page.getByRole('button', { name: 'Cancel' }).click();
    await expect(page.getByText('Are you sure you want to log out?')).toHaveCount(0);
  });

  test('explains theme and dark-palette actions before applying them', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);
    await page.goto(`${node.baseUrl}/searches`, {
      waitUntil: 'domcontentloaded',
    });

    const themeMenu = page.getByTestId('theme-menu');
    await expect(themeMenu).toHaveAttribute(
      'aria-label',
      'Choose the web UI color theme',
    );
    await themeMenu.click();

    const paletteAction = page.getByRole('button', {
      name: 'Apply the Aurora palette to the dark theme.',
    });
    await expect(paletteAction).toBeVisible();
    await paletteAction.hover();
    await expect(
      page.getByText('Apply the Aurora palette to the dark theme.', {
        exact: true,
      }),
    ).toBeVisible();
    await paletteAction.click();
    await expect.poll(
      () => page.evaluate(() => localStorage.getItem('slskdn-palette')),
    ).toBe('aurora');

    await themeMenu.click();
    const lightTheme = page.getByTestId('theme-option-light');
    await expect(lightTheme).toHaveAttribute(
      'aria-label',
      'Use the Light theme for the web UI.',
    );
    await lightTheme.hover();
    await expect(
      page.getByText('Use the Light theme for the web UI.', { exact: true }),
    ).toBeVisible();
    await lightTheme.click();
    await expect(page.locator('html')).toHaveClass(/\blight\b/u);
  });

  test('keeps grouped navigation and System section tabs visible on dark theme', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    await page.goto(`${node.baseUrl}/searches`, {
      waitUntil: 'domcontentloaded',
    });

    const navigation = page.locator('.navigation');
    await expect(navigation).toBeVisible();
    await expect(navigation).toHaveCSS('overflow', 'visible');

    const discoverMenu = page.getByTestId('nav-group-discover');
    await discoverMenu.click();
    await expect(page.locator('.navigation-dropdown-popup')).toBeVisible();
    await expect(page.getByTestId('nav-wishlist')).toBeVisible();

    await clickNav(page, 'nav-wishlist');
    await expect(page).toHaveURL(/\/wishlist$/);

    await page.goto(`${node.baseUrl}/system/info`, {
      waitUntil: 'domcontentloaded',
    });
    const sectionMenu = page.locator('.system-section-menu');
    await expect(sectionMenu).toBeVisible();
    const sectionColors = await sectionMenu.locator(':scope > .item').evaluateAll(
      (items) => items.map((item) => getComputedStyle(item).color),
    );
    expect(sectionColors.length).toBe(6);
    expect(sectionColors.every((color) => !/^rgb\(0, 0, 0\)$/u.test(color))).toBe(true);

    await page.setViewportSize({ height: 720, width: 320 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);
    const networkSection = page.getByRole('link', {
      name: 'Network & Mesh',
    });
    await networkSection.focus();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/system\/mesh$/);
    await expect(page.locator('.system')).toBeVisible();

    await page.goto(`${node.baseUrl}/system/options`, {
      waitUntil: 'domcontentloaded',
    });
    await expect(page.locator('.system')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);
  });

  test('keeps populated System Shares scrollable and opens contents by keyboard at 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    const localPath =
      '/library/music/a-deliberately-long-shared-folder-name-for-narrow-screens';
    await page.route('**/api/v0/shares', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          contentType: 'application/json',
          json: {
            'test-node': [{
              alias: 'Music',
              directories: 12,
              files: 2400,
              id: 'mobile-layout-share',
              isExcluded: false,
              localPath,
              remotePath: '/remote/music',
            }],
          },
        });
      } else {
        await route.continue();
      }
    });
    await page.route('**/api/v0/shares/mobile-layout-share/contents', async (route) => {
      await route.fulfill({ contentType: 'application/json', json: [] });
    });

    await page.setViewportSize({ height: 812, width: 320 });
    await page.goto(`${node.baseUrl}/system/shares`, {
      waitUntil: 'domcontentloaded',
    });

    const shareAction = page.getByRole('button', {
      name: `View files in share ${localPath}`,
    });
    await expect(shareAction).toBeVisible();
    await shareAction.hover();
    await expect(
      page.getByText(`Open the file list for share ${localPath}.`, { exact: true }),
    ).toBeVisible();

    const scrollRegion = page.getByRole('region', { name: 'Configured shares' });
    await expect(scrollRegion).toHaveAttribute('tabindex', '0');
    expect(await scrollRegion.evaluate((element) => element.scrollWidth > element.clientWidth))
      .toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);

    await shareAction.focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('.ui.modal.visible')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Close share contents' })).toBeVisible();
    await expect(page).toHaveURL(/\/system\/shares$/u);
  });

  test('keeps populated System Network data within 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    const peerName = 'mesh-peer-with-a-deliberately-long-name-for-mobile-layout';
    await page.route('**/api/v0/network/stats*', async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: {
          backfill: { isActive: false },
          capabilitiesJson: JSON.stringify({ features: ['mesh_sync'], version: '1.2.3' }),
          capabilitiesVersion: 'slskdn/1.2.3',
          discoveredPeers: [],
          dht: {
            discoveredPeerCount: 14,
            dhtNodeCount: 125,
            isDhtRunning: true,
            isEnabled: true,
            isLanOnly: false,
          },
          hashDb: {
            currentSeqId: 84_000,
            totalHashEntries: 21_500,
          },
          mesh: {
            connectedPeerCount: 1,
            currentSeqId: 84_000,
            warnings: [],
          },
          meshPeers: [{
            lastSyncTime: '2026-10-02T21:00:00Z',
            latestSeqId: 83_900,
            username: peerName,
          }],
          swarmJobs: [],
        },
      });
    });
    await page.route('**/api/v0/mesh/sync/*', async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: { error: 'Peer does not support mesh sync' },
        status: 400,
      });
    });

    await page.setViewportSize({ height: 812, width: 320 });
    await page.goto(`${node.baseUrl}/system/network`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.getByText('Public DHT exposure notice')).toBeVisible();
    const dismissDhtNotice = page.getByRole('button', {
      name: 'Dismiss public DHT exposure notice',
    });
    await dismissDhtNotice.hover();
    await expect(
      page.getByText(
        'Dismiss this public DHT exposure notice on this browser after reviewing it.',
        { exact: true },
      ),
    ).toBeVisible();
    await dismissDhtNotice.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByText('Public DHT exposure notice')).toHaveCount(0);

    await expect(page.getByText(peerName, { exact: true })).toBeVisible();
    await expect(page.getByText('Mesh Sync Security')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);

    const peerRow = page.getByRole('row').filter({
      has: page.getByText(peerName, { exact: true }),
    });
    const syncAction = peerRow.getByRole('button', { name: 'Sync', exact: true });
    await syncAction.hover();
    await expect(
      page.getByText(
        `Sync hash data with ${peerName}. Use this when its sequence is behind yours.`,
        { exact: true },
      ),
    ).toBeVisible();
    await syncAction.click();
    await expect(page.getByText('Peer does not support mesh sync', { exact: true }))
      .toBeVisible();
    await expect(page.getByText(`Sync initiated with ${peerName}`, { exact: true }))
      .toHaveCount(0);
  });

  test('keeps populated System Jobs data within 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    const jobId = 'job-with-a-deliberately-long-identifier-for-narrow-screen-review';
    const swarmFilename =
      'a-deliberately-long-swarm-filename-for-narrow-screen-review.mp3';
    await page.route('**/api/v0/jobs*', async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: {
          has_more: true,
          jobs: [{
            created_at: '2026-10-02T21:00:00Z',
            id: jobId,
            progress: { releases_done: 37, releases_failed: 0, releases_total: 100 },
            status: 'running',
            type: 'discography',
          }],
          total: 61,
        },
      });
    });
    await page.route('**/api/v0/multisource/jobs*', async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: {
          jobs: [{
            activeSources: 4,
            downloadedBytes: 5_242_880,
            filename: `/downloads/${swarmFilename}`,
            jobId: 'swarm-mobile-review',
            progressPercent: 37,
            totalBytes: 14_155_776,
          }],
        },
      });
    });
    await page.route(
      '**/api/v0/multisource/jobs/swarm-mobile-review',
      async (route) => {
        await route.fulfill({
          contentType: 'application/json',
          json: {
            activeWorkers: 4,
            bytesDownloaded: 5_242_880,
            chunksPerSecond: 8.2,
            completedChunks: 37,
            estimatedSecondsRemaining: 120,
            jobId: 'swarm-mobile-review',
            state: 'Running',
            totalChunks: 100,
          },
        });
      },
    );
    await page.route(
      '**/api/v0/traces/swarm-mobile-review/summary',
      async (route) => {
        await route.fulfill({
          contentType: 'application/json',
          json: { bytesBySource: {}, duration: 20, peers: [], totalEvents: 0 },
        });
      },
    );

    await page.setViewportSize({ height: 812, width: 320 });
    await page.goto(`${node.baseUrl}/system/jobs`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.getByText(jobId, { exact: true })).toBeVisible();
    await expect(page.getByText(swarmFilename, { exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);

    const jobsScrollRegion = page.getByRole('region', { name: 'Job list' });
    await expect(jobsScrollRegion).toHaveAttribute('tabindex', '0');
    expect(await jobsScrollRegion.evaluate((region) => region.scrollWidth > region.clientWidth))
      .toBe(true);

    const sortAction = page.getByRole('button', {
      name: 'Sort jobs in ascending order',
    });
    await sortAction.hover();
    await expect(
      page.getByText('Sort the current job list in ascending order.', {
        exact: true,
      }),
    ).toBeVisible();

    const refreshAction = page.getByRole('button', { name: 'Refresh job list' });
    await refreshAction.hover();
    await expect(
      page.getByText(
        'Reload the current job list after job status or page data changes.',
        { exact: true },
      ),
    ).toBeVisible();

    const detailsAction = page.getByRole('button', {
      name: `View swarm download details for ${swarmFilename}`,
    });
    await detailsAction.hover();
    await expect(
      page.getByText(
        `Inspect contributing sources and chunk progress for ${swarmFilename}.`,
        { exact: true },
      ),
    ).toBeVisible();
    await detailsAction.click();
    await expect(page.locator('.ui.modal.visible')).toBeVisible();

    const closeAction = page.getByRole('button', {
      name: 'Close swarm download visualization',
    });
    await closeAction.hover();
    await expect(
      page.getByText(
        'Close the swarm visualization and return to the job list.',
        { exact: true },
      ),
    ).toBeVisible();
    await closeAction.focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('.ui.modal.visible')).toHaveCount(0);
  });

  test('keeps populated System Security status usable at 320px', async ({
    page,
    request,
  }) => {
    test.setTimeout(45_000);
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    let dashboardRequests = 0;
    await page.route('**/api/v0/security/dashboard*', async (route) => {
      dashboardRequests += 1;
      await route.fulfill({
        contentType: 'application/json',
        json: {
          entropyStats: { checkCount: 470, warningCount: 2 },
          eventStats: { totalEvents: 12 },
          networkGuardStats: { globalConnections: 7 },
          reputationStats: {
            totalPeers: 42,
            trustedPeers: 30,
            untrustedPeers: 12,
          },
          violationStats: { trackedIps: 3, trackedUsernames: 5 },
        },
      });
    });
    await page.route('**/api/v0/security/adversarial', async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: {
          Anonymity: { Enabled: false, Mode: 'Direct' },
          Enabled: true,
          Privacy: {
            Enabled: true,
            Padding: { BucketSizes: [128], Enabled: true },
          },
          Profile: 'Custom',
          Transport: {
            Enabled: true,
            Obfs4: { BridgeLines: ['obfs4 192.0.2.1:443 example-key'] },
            PrimaryTransport: 'Obfs4',
          },
        },
      });
    });
    await page.route('**/api/v0/security/adversarial/stats*', async (route) => {
      await route.fulfill({ contentType: 'application/json', json: {} });
    });
    await page.route('**/api/v0/security/transports/status*', async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: {
          AvailableTransports: 1,
          PrimaryTransportAvailable: true,
          TotalTransports: 1,
        },
      });
    });

    await page.setViewportSize({ height: 812, width: 320 });
    await page.goto(`${node.baseUrl}/system/security`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.getByText('Security Status')).toBeVisible();
    await expect(page.getByText('Active Connections')).toBeVisible();
    await expect(page.getByText('Tracked Peers')).toBeVisible();
    await expect(page.getByText('Tracked Violators')).toBeVisible();
    await expect(page.getByText('Security Events')).toBeVisible();
    const metricLabels = page.locator('.security-dashboard .ui.statistics .label');
    const metricBounds = await metricLabels.evaluateAll((elements) =>
      elements.map((element) => {
        const { height, width, x, y } = element.getBoundingClientRect();
        return { height, width, x, y };
      }),
    );
    expect(metricBounds).toHaveLength(4);
    for (let first = 0; first < metricBounds.length; first += 1) {
      for (let second = first + 1; second < metricBounds.length; second += 1) {
        const a = metricBounds[first];
        const b = metricBounds[second];
        const overlapsX = a.x < b.x + b.width && b.x < a.x + a.width;
        const overlapsY = a.y < b.y + b.height && b.y < a.y + a.height;
        expect(overlapsX && overlapsY).toBe(false);
      }
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);

    const refreshAction = page.getByRole('button', {
      name: 'Refresh the security dashboard',
    });
    await refreshAction.hover();
    await expect(
      page.getByText(
        'Request the latest security snapshot now to check recent network activity.',
        { exact: true },
      ),
    ).toBeVisible();
    await refreshAction.focus();
    await page.keyboard.press('Enter');
    await expect.poll(() => dashboardRequests).toBe(2);

    await page.getByText('Adversarial', { exact: true }).click();
    await expect(page.getByText('Adversarial Resilience Overview')).toBeVisible();

    const settingsRefresh = page.getByRole('button', {
      name: 'Refresh adversarial settings and status',
    });
    await settingsRefresh.hover();
    await expect(
      page.getByText(
        'Reload the current adversarial settings and transport status.',
        { exact: true },
      ),
    ).toBeVisible();

    const transportTest = page.getByRole('button', {
      name: 'Test transport connectivity',
    });
    await expect(transportTest).toBeEnabled();
    await transportTest.hover();
    await expect(
      page.getByText(
        'Check whether the configured transport can connect.',
        { exact: true },
      ),
    ).toBeVisible();

    const torTest = page.getByRole('button', {
      name: 'Test Tor connectivity',
    });
    await torTest.hover();
    await expect(
      page.getByText('Check whether the configured Tor service is reachable.', {
        exact: true,
      }),
    ).toBeVisible();

    await page.getByText('Privacy', { exact: true }).click();
    const addBucket = page.getByRole('button', {
      name: 'Add message-padding bucket size',
    });
    await addBucket.hover();
    await expect(
      page.getByText('Add another size to the message-padding list.', {
        exact: true,
      }),
    ).toBeVisible();
    await addBucket.focus();
    await page.keyboard.press('Enter');

    await page.getByText('Transport', { exact: true }).click();
    const removeBridge = page.getByRole('button', {
      name: 'Remove Obfs4 bridge line 1',
    });
    await removeBridge.hover();
    await expect(
      page.getByText('Remove this Obfs4 bridge line from the settings.', {
        exact: true,
      }),
    ).toBeVisible();
    await removeBridge.focus();
    await page.keyboard.press('Enter');

    const addBridge = page.getByRole('button', {
      name: 'Add Obfs4 bridge line',
    });
    await addBridge.hover();
    await expect(
      page.getByText('Add another bridge line for Obfs4 transport.', {
        exact: true,
      }),
    ).toBeVisible();
    await addBridge.focus();
    await page.keyboard.press('Enter');

    const saveAction = page.getByRole('button', {
      name: 'Save adversarial settings',
    });
    await saveAction.hover();
    await expect(
      page.getByText('Save the current adversarial settings to this server.', {
        exact: true,
      }),
    ).toBeVisible();
    const settingsButtonBounds = await page
      .locator('.security-actions .ui.button')
      .evaluateAll((buttons) =>
        buttons.map((button) => {
          const { height, width, x, y } = button.getBoundingClientRect();
          return { height, width, x, y };
        }),
      );
    expect(settingsButtonBounds).toHaveLength(4);
    expect(settingsButtonBounds.every((bounds) => bounds.x >= 0 && bounds.x + bounds.width <= 320))
      .toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);
  });

  test('keeps populated System Bridge metrics and client data usable at 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    await page.route('**/api/v0/bridge/admin/config', async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: {
          enabled: true,
          max_clients: 10,
          port: 2242,
          require_auth: true,
          soulfind_path: 'soulfind',
        },
      });
    });
    await page.route('**/api/v0/bridge/admin/dashboard', async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: {
          connectedClients: [{
            clientId: 'mobile-bridge-client',
            clientType: 'A deliberately long legacy client name',
            ipAddress: '2001:db8:abcd:ef01:2345:6789:abcd:ef01',
            requestCount: 128,
          }],
          health: { isHealthy: true, version: '1.0.0-proxy' },
          meshBenefits: {
            bytesViaMesh: 1_048_576,
            bytesViaSoulseek: 1_048_576,
            meshPercentage: 50,
          },
          stats: {
            currentConnections: 7,
            totalBytesProxied: 12_345_678,
            totalDownloads: 6543,
            totalSearches: 123_456,
          },
        },
      });
    });

    await page.setViewportSize({ height: 812, width: 320 });
    await page.goto(`${node.baseUrl}/system/bridge`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.getByText('Legacy Client Bridge')).toBeVisible();
    await expect(page.getByText('A deliberately long legacy client name'))
      .toBeVisible();
    const metricLabels = page.locator('.ui.statistics .label');
    const metricBounds = await metricLabels.evaluateAll((elements) =>
      elements.map((element) => {
        const { height, width, x, y } = element.getBoundingClientRect();
        return { height, width, x, y };
      }),
    );
    expect(metricBounds).toHaveLength(6);
    for (let first = 0; first < metricBounds.length; first += 1) {
      for (let second = first + 1; second < metricBounds.length; second += 1) {
        const a = metricBounds[first];
        const b = metricBounds[second];
        const overlapsX = a.x < b.x + b.width && b.x < a.x + a.width;
        const overlapsY = a.y < b.y + b.height && b.y < a.y + a.height;
        expect(overlapsX && overlapsY).toBe(false);
      }
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);

    const stopAction = page.getByRole('button', { name: 'Stop Bridge' });
    await expect(stopAction).toBeEnabled();
    await stopAction.hover();
    await expect(
      page.getByText(
        'Stop the local legacy-client bridge and disconnect its active clients.',
        { exact: true },
      ),
    ).toBeVisible();
  });

  test('explains and supports opt-in System Mesh actions at 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    const candidate = 'mesh-candidate-visible-in-the-interest-graph';
    await page.route('**/api/v0/mesh/transport', async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: {
          activeCircuits: 1,
          activeStreams: 3,
          bootstrapPeers: [],
          connectedPeers: 4,
          description: 'Local browser fixture',
          health: 'Healthy',
          isolatedPeers: 0,
          natType: 'Direct',
          publicEndpoint: null,
          quorumPeers: 3,
          relayedPeers: 0,
          status: 'Healthy',
          totalPeers: 4,
          transportPreference: 'Auto',
        },
      });
    });
    await page.route('**/api/v0/soulseek/mesh-rendezvous/status', async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: {
          enabled: true,
          interestTag: 'slskdn-mesh-v1',
        },
      });
    });
    await page.route('**/api/v0/soulseek/mesh-rendezvous/discover', async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: {
          capabilityRecords: [{
            features: ['mesh_sync'],
            nonce: 'test-nonce',
            overlayPort: 50305,
            peerId: 'test-peer-id',
            signed: true,
            username: candidate,
          }],
          users: [{ rating: 14, username: candidate }],
        },
      });
    });

    await page.setViewportSize({ height: 812, width: 320 });
    await page.goto(`${node.baseUrl}/system/mesh`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.getByText('Opt-in public rendezvous is enabled'))
      .toBeVisible();
    const actionDescriptions = [
      {
        name: 'Publish Interest',
        tooltip:
          'Publish the slskdN rendezvous interest on this Soulseek account so other mesh-capable users can discover it.',
      },
      {
        name: 'Remove Interest',
        tooltip:
          "Remove this account's public slskdN rendezvous interest when you no longer want to appear in mesh discovery.",
      },
      {
        name: 'Load Candidates',
        tooltip:
          'Search the Soulseek interest graph for opted-in mesh accounts and their published capabilities.',
      },
    ];
    for (const actionDescription of actionDescriptions) {
      const action = page.getByRole('button', { name: actionDescription.name });
      await expect(action).toBeEnabled();
      await action.hover();
      await expect(
        page.getByText(actionDescription.tooltip, { exact: true }),
      ).toBeVisible();
    }

    const actionBounds = await page
      .locator('.mesh-rendezvous-actions .ui.button')
      .evaluateAll((buttons) =>
        buttons.map((button) => {
          const { height, width, x, y } = button.getBoundingClientRect();
          return { height, width, x, y };
        }),
      );
    expect(actionBounds).toHaveLength(3);
    expect(actionBounds.every((bounds) =>
      bounds.height >= 42 && bounds.x >= 0 && bounds.x + bounds.width <= 320,
    )).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);

    const discoverAction = page.getByRole('button', {
      name: 'Load Candidates',
    });
    await discoverAction.focus();
    await page.keyboard.press('Enter');
    await expect(
      page.getByText(
        'Discovered 1 Soulseek rendezvous candidate(s) and 1 runtime capability record(s).',
      ),
    ).toBeVisible();
    await expect(page.getByText(candidate, { exact: true })).toHaveCount(2);
  });

  test('recovers and keeps populated System Metrics usable at 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    const metrics = Object.fromEntries([
      ['slskd_uploads_total', 'Upload count collected from every active peer.'],
      ['slskd_downloads_total', 'Download count collected from every active peer.'],
      ['slskd_uploads_active', 'Current uploads.'],
      ['slskd_downloads_active', 'Current downloads.'],
      ['slskd_uploads_queued', 'Queued uploads.'],
      ['slskd_downloads_queued', 'Queued downloads.'],
      ['slskd_searches_incoming_requests_total', 'Incoming requests.'],
      ['slskd_searches_incoming_requests_dropped_total', 'Dropped requests.'],
      ['slskd_searches_outgoing_total', 'Outgoing searches.'],
      ['process_working_set_bytes', 'Working memory.'],
      ['dotnet_total_memory_bytes', 'Managed memory.'],
      ['process_cpu_seconds_total', 'CPU time.'],
      ['microsoft_aspnetcore_server_kestrel_current_connections', 'Open connections.'],
      ['system_net_sockets_connections_established_total', 'Established sockets.'],
    ].map(([name, help], index) => [name, {
      help: `${help} A deliberately long explanation for narrow-screen table scrolling.`,
      samples: [{ value: (index + 1) * 100 }],
      type: 'counter',
    }]));

    let metricsRequests = 0;
    await page.route('**/api/v0/telemetry/metrics/kpi', async (route) => {
      metricsRequests += 1;
      if (metricsRequests === 1) {
        await route.fulfill({
          contentType: 'application/json',
          json: { message: 'temporary metrics failure' },
          status: 503,
        });
        return;
      }

      await route.fulfill({ contentType: 'application/json', json: metrics });
    });

    await page.setViewportSize({ height: 812, width: 320 });
    await page.goto(`${node.baseUrl}/system/metrics`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.getByText('Failed to load metrics')).toBeVisible();
    const retryAction = page.getByRole('button', { name: 'Try Again' });
    await retryAction.hover();
    await expect(
      page.getByText(
        'Try the Prometheus metrics request again after the current error.',
        { exact: true },
      ),
    ).toBeVisible();
    await retryAction.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByText('Uploads Total', { exact: true })).toBeVisible();
    await expect.poll(() => metricsRequests).toBe(2);

    const metricLabels = page.locator('.system-metrics-statistics .label');
    const metricBounds = await metricLabels.evaluateAll((elements) =>
      elements.map((element) => {
        const { height, width, x, y } = element.getBoundingClientRect();
        return { height, width, x, y };
      }),
    );
    expect(metricBounds).toHaveLength(14);
    for (let first = 0; first < metricBounds.length; first += 1) {
      for (let second = first + 1; second < metricBounds.length; second += 1) {
        const a = metricBounds[first];
        const b = metricBounds[second];
        const overlapsX = a.x < b.x + b.width && b.x < a.x + a.width;
        const overlapsY = a.y < b.y + b.height && b.y < a.y + a.height;
        expect(overlapsX && overlapsY).toBe(false);
      }
    }

    const scrollRegion = page.getByRole('region', {
      name: 'Prometheus metric details',
    });
    await expect(scrollRegion).toHaveAttribute('tabindex', '0');
    expect(await scrollRegion.evaluate((region) => region.scrollWidth > region.clientWidth))
      .toBe(true);
    await scrollRegion.focus();
    await page.keyboard.press('ArrowRight');
    await expect.poll(() => scrollRegion.evaluate((region) => region.scrollLeft))
      .toBeGreaterThan(0);

    const refreshAction = page.getByRole('button', { name: 'Refresh' });
    await refreshAction.hover();
    await expect(
      page.getByText(
        'Fetch the latest Prometheus metrics now to review current application activity.',
        { exact: true },
      ),
    ).toBeVisible();
    await refreshAction.focus();
    await page.keyboard.press('Enter');
    await expect.poll(() => metricsRequests).toBe(3);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);
  });

  test('recovers and keeps populated System Events usable at 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    let eventRequests = 0;
    const completedOffsets: number[] = [];
    await page.route('**/api/v0/events?*', async (route) => {
      eventRequests += 1;
      if (eventRequests === 1) {
        await route.fulfill({
          contentType: 'application/json',
          json: { message: 'temporary event service failure' },
          status: 503,
        });
        return;
      }

      const offset = Number(new URL(route.request().url()).searchParams.get('offset'));
      if (offset === 10) {
        await new Promise((resolve) => setTimeout(resolve, 300));
        completedOffsets.push(offset);
        await route.fulfill({
          contentType: 'application/json',
          headers: { 'x-total-count': '30' },
          json: [{
            data: JSON.stringify({ detail: 'stale page result' }),
            id: 'event-stale-page-two',
            timestamp: '2026-10-02T20:00:00Z',
            type: 'StaleSecondPageEvent',
          }],
        });
        return;
      }

      completedOffsets.push(offset);
      const firstPageEvent = eventRequests === 2
        ? {
            data: JSON.stringify({
              detail: 'initial page payload',
              explanation: 'preserve formatted diagnostics',
            }),
            id: 'event-initial-mobile-record-123456',
            timestamp: '2026-10-02T19:30:00Z',
            type: 'InitialEvent',
          }
        : {
            data: JSON.stringify({ detail: 'current page result' }),
            id: 'event-returned-page-one',
            timestamp: '2026-10-02T19:31:00Z',
            type: 'ReturnedFirstPageEvent',
          };
      await route.fulfill({
        contentType: 'application/json',
        headers: { 'x-total-count': '30' },
        json: [firstPageEvent],
      });
    });

    await page.setViewportSize({ height: 812, width: 320 });
    await page.goto(`${node.baseUrl}/system/events`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.getByText('Failed to load events')).toBeVisible();
    const retryAction = page.getByRole('button', { name: 'Try Again' });
    await retryAction.hover();
    await expect(
      page.getByText(
        'Try loading this page of system events again after the current request error.',
        { exact: true },
      ),
    ).toBeVisible();
    await retryAction.focus();
    await page.keyboard.press('Enter');

    await expect(page.getByText('System Events')).toBeVisible();
    await expect(page.getByText('InitialEvent', { exact: true })).toBeVisible();
    const eventId = 'event-initial-mobile-record-123456';
    const eventIdAction = page.getByRole('button', {
      name: `Show identifier for event ${eventId}`,
    });
    await eventIdAction.focus();
    await expect(
      page.getByText(
        `Use this ID to find the InitialEvent event in diagnostics: ${eventId}`,
        { exact: true },
      ),
    ).toBeVisible();
    await expect(page.locator('.events-table-data pre')).toContainText(
      'preserve formatted diagnostics',
    );

    const scrollRegion = page.getByRole('region', {
      name: 'System event records',
    });
    await expect(scrollRegion).toHaveAttribute('tabindex', '0');
    expect(await scrollRegion.evaluate((region) => region.scrollWidth > region.clientWidth))
      .toBe(true);
    await scrollRegion.focus();
    await page.keyboard.press('ArrowRight');
    await expect.poll(() => scrollRegion.evaluate((region) => region.scrollLeft))
      .toBeGreaterThan(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);

    const pageNavigation = page.getByRole('navigation', { name: 'Event pages' });
    await pageNavigation.hover();
    await expect(
      page.getByText(
        'Choose a page to review another batch of system events.',
        { exact: true },
      ),
    ).toBeVisible();

    const secondPage = pageNavigation.getByText('2', { exact: true });
    await secondPage.focus();
    await page.keyboard.press('Enter');
    await expect.poll(() => eventRequests).toBe(3);
    const firstPage = pageNavigation.getByText('1', { exact: true });
    await firstPage.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByText('ReturnedFirstPageEvent', { exact: true }))
      .toBeVisible();
    await expect.poll(() => completedOffsets.includes(10)).toBe(true);
    await expect(page.getByText('StaleSecondPageEvent', { exact: true }))
      .toHaveCount(0);
  });

  test('recovers the live System Logs feed and keeps filters usable at 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    let hubNegotiations = 0;
    await page.route('**/hub/logs/negotiate*', async (route) => {
      hubNegotiations += 1;
      if (hubNegotiations === 1) {
        await route.fulfill({
          contentType: 'application/json',
          json: { error: 'temporary logs hub failure' },
          status: 503,
        });
        return;
      }

      await route.continue();
    });

    await page.setViewportSize({ height: 812, width: 320 });
    await page.goto(`${node.baseUrl}/system/logs`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.getByRole('heading', { name: 'System Logs' })).toBeVisible();
    await expect(page.getByText('Live logs are disconnected')).toBeVisible();
    const retryAction = page.getByRole('button', {
      name: 'Retry live log connection',
    });
    await retryAction.hover();
    await expect(
      page.getByText('Retry the live log connection to receive new records.', {
        exact: true,
      }),
    ).toBeVisible();
    await retryAction.focus();
    await page.keyboard.press('Enter');
    await expect.poll(() => hubNegotiations).toBe(2);
    await expect(page.getByText(/^Showing \d+ of \d+ logs$/u)).toBeVisible();

    const filterActions = [
      {
        description: 'Show every severity so you can inspect the full live log feed.',
        name: 'Show all severities',
      },
      {
        description: 'Show informational records to follow normal application activity.',
        name: 'Show information logs',
      },
      {
        description: 'Show warnings to review conditions that may need attention.',
        name: 'Show warning logs',
      },
      {
        description: 'Show errors to focus on failed operations and their causes.',
        name: 'Show error logs',
      },
      {
        description: 'Show debug records when investigating detailed application behavior.',
        name: 'Show debug logs',
      },
    ];

    for (const filter of filterActions) {
      const action = page.getByRole('button', { name: filter.name });
      await expect(action).toHaveAttribute(
        'aria-pressed',
        filter.name === 'Show all severities' ? 'true' : 'false',
      );
      await action.hover();
      await expect(page.getByText(filter.description, { exact: true })).toBeVisible();
    }

    const warningFilter = page.getByRole('button', { name: 'Show warning logs' });
    await warningFilter.focus();
    await page.keyboard.press('Enter');
    await expect(warningFilter).toHaveAttribute('aria-pressed', 'true');

    const filterBounds = await page
      .locator('.logs-filter-buttons .ui.button')
      .evaluateAll((buttons) => buttons.map((button) => {
        const { height, width, x, y } = button.getBoundingClientRect();
        return { height, width, x, y };
      }));
    expect(filterBounds).toHaveLength(5);
    expect(filterBounds.every((bounds) =>
      bounds.height >= 42 && bounds.x >= 0 && bounds.x + bounds.width <= 320,
    )).toBe(true);

    const scrollRegion = page.getByRole('region', { name: 'System log entries' });
    await expect(scrollRegion).toHaveAttribute('tabindex', '0');
    expect(await scrollRegion.evaluate((region) => region.scrollWidth > region.clientWidth))
      .toBe(true);
    await scrollRegion.focus();
    await page.keyboard.press('ArrowRight');
    await expect.poll(() => scrollRegion.evaluate((region) => region.scrollLeft))
      .toBeGreaterThan(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);
  });

  test('browses and downloads retained System Logs history', async ({
    page,
    request,
  }) => {
    const node = getNode();
    const logName = 'slskd-20261012.log';
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    await page.route('**/hub/logs/negotiate*', async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: { error: 'live logs are not needed for this history check' },
        status: 503,
      });
    });
    await page.route(/\/api\/v0\/logs\/files$/u, async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: [{
          lastModified: '2026-10-12T10:20:30Z',
          length: 20,
          name: logName,
        }],
      });
    });
    await page.route(`**/api/v0/logs/files/${logName}/download`, async (route) => {
      await route.fulfill({ body: 'downloaded log record', contentType: 'text/plain' });
    });
    await page.route(`**/api/v0/logs/files/${logName}`, async (route) => {
      await route.fulfill({ body: 'previewed log record', contentType: 'text/plain' });
    });

    await page.goto(`${node.baseUrl}/system/logs`, {
      waitUntil: 'domcontentloaded',
    });
    await page.getByRole('button', { name: 'History' }).click();
    await expect(page.getByText(logName, { exact: true })).toBeVisible();

    const view = page.getByRole('button', { name: `View ${logName}` });
    await view.hover();
    await expect(page.getByText(`Open ${logName} to inspect its contents.`, { exact: true }))
      .toBeVisible();
    await view.click();
    await expect(page.getByText('previewed log record', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Close' }).click();

    const download = page.getByRole('button', { name: `Download ${logName}` });
    await download.hover();
    await expect(page.getByText(`Download ${logName} for offline review.`, { exact: true }))
      .toBeVisible();
    const downloadedFile = page.waitForEvent('download');
    await download.click();
    expect((await downloadedFile).suggestedFilename()).toBe(logName);
  });

  test('explains and recovers completed-transfer cleanup at 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    let uploadRequests = 0;
    let downloadRequests = 0;
    await page.route('**/api/v0/transfers/uploads/all/completed', async (route) => {
      uploadRequests += 1;
      if (uploadRequests === 1) {
        await route.fulfill({
          contentType: 'application/json',
          json: { message: 'temporary transfer history failure' },
          status: 503,
        });
        return;
      }

      await route.fulfill({ status: 204 });
    });
    await page.route('**/api/v0/transfers/downloads/all/completed', async (route) => {
      downloadRequests += 1;
      await route.fulfill({ status: 204 });
    });

    await page.setViewportSize({ height: 812, width: 320 });
    await page.goto(`${node.baseUrl}/system/data`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.getByRole('heading', { name: 'Transfer Data' })).toBeVisible();
    await expect(page.getByText(/downloaded files on disk are not removed/u)).toBeVisible();
    const uploadAction = page.getByRole('button', {
      name: 'Clear All Completed Uploads',
    });
    await uploadAction.hover();
    await expect(page.getByText(
      'Remove completed upload records from transfer history to keep the Uploads page responsive.',
      { exact: true },
    )).toBeVisible();
    await uploadAction.focus();
    await page.keyboard.press('Enter');

    await expect(page.getByRole('alert')).toContainText(
      'Uploads: temporary transfer history failure',
    );
    await expect.poll(() => uploadRequests).toBe(1);
    await expect(uploadAction).toBeEnabled();
    await uploadAction.focus();
    await page.keyboard.press('Enter');
    await expect.poll(() => uploadRequests).toBe(2);
    await expect(page.getByRole('alert')).toHaveCount(0);

    const downloadAction = page.getByRole('button', {
      name: 'Clear All Completed Downloads',
    });
    await downloadAction.hover();
    await expect(page.getByText(
      'Remove completed download records from transfer history. Files already saved on disk are not deleted.',
      { exact: true },
    )).toBeVisible();
    await downloadAction.focus();
    await page.keyboard.press('Enter');
    await expect.poll(() => downloadRequests).toBe(1);

    const actionBounds = await page
      .locator('.transfer-data-actions .ui.button')
      .evaluateAll((buttons) => buttons.map((button) => {
        const { height, right, x } = button.getBoundingClientRect();
        return { height, right, x };
      }));
    expect(actionBounds).toHaveLength(2);
    expect(actionBounds.every((bounds) =>
      bounds.height >= 44 && bounds.x >= 0 && bounds.right <= 320,
    )).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);
  });

  test('keeps Library Health scanning explicit, recoverable, and usable at 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    let scanStarts = 0;
    let scanStatusChecks = 0;
    await page.route('**/api/v0/library/health/**', async (route) => {
      const method = route.request().method();
      const { pathname } = new URL(route.request().url());

      if (method === 'POST' && pathname.endsWith('/scans')) {
        scanStarts += 1;
        await route.fulfill({
          contentType: 'application/json',
          json: { message: 'Scan started successfully', scanId: 'scan-ui-1' },
        });
        return;
      }

      if (method === 'GET' && pathname.endsWith('/scans/scan-ui-1')) {
        scanStatusChecks += 1;
        await route.fulfill({
          contentType: 'application/json',
          json: {
            filesScanned: 12,
            issuesDetected: 2,
            libraryPath: '/fixture/music',
            status: 'Completed',
          },
        });
        return;
      }

      if (method === 'GET' && pathname.endsWith('/dashboard')) {
        await route.fulfill({
          contentType: 'application/json',
          json: {
            issues: [{
              album: 'Fixture Album',
              artist: 'Fixture Artist',
              canAutoFix: true,
              issueId: 'issue-ui-1',
              reason: 'A long reason stays inside the scrollable issue table.',
              severity: 'High',
              status: 'Detected',
              title: 'Fixture Track',
              type: 'SuspectedTranscode',
            }],
            issuesByArtist: [{ artist: 'Fixture Artist', count: 1 }],
            issuesByType: [{ count: 1, type: 'SuspectedTranscode' }],
            summary: { issuesOpen: 1, issuesResolved: 0, totalIssues: 1 },
          },
        });
        return;
      }

      await route.continue();
    });

    await page.setViewportSize({ height: 812, width: 320 });
    await page.goto(`${node.baseUrl}/system/library-health`, {
      waitUntil: 'domcontentloaded',
    });

    const libraryPath = page.getByRole('textbox', {
      name: 'Library path on the server',
    });
    await libraryPath.fill('/fixture/music');
    const startScan = page.getByRole('button', {
      name: 'Start a recursive Library Health scan for this path',
    });
    await startScan.hover();
    await expect(page.getByText(
      'Recursively scan the entered server-side path for audio health issues. This manually starts read-only file inspection with up to four files checked at once; it does not contact peers or modify files.',
      { exact: true },
    )).toBeVisible();
    await startScan.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByText('Scan complete: 12 files checked and 2 issues found.'))
      .toBeVisible();
    await expect.poll(() => scanStarts).toBe(1);
    await expect.poll(() => scanStatusChecks).toBe(1);

    await page.getByText('All Issues', { exact: true }).click();
    await expect(page.getByText('Showing results for /fixture/music')).toBeVisible();
    const issueSelection = page.getByRole('checkbox', {
      name: 'Select Fixture Artist — Fixture Track',
    });
    await issueSelection.focus();
    await page.keyboard.press('Space');
    await expect(issueSelection).toBeChecked();

    const scrollRegion = page.getByRole('region', {
      name: 'Library Health issues table',
    });
    await expect(scrollRegion).toHaveAttribute('tabindex', '0');
    expect(await scrollRegion.evaluate((region) => region.scrollWidth > region.clientWidth))
      .toBe(true);
    await scrollRegion.focus();
    await page.keyboard.press('ArrowRight');
    await expect.poll(() => scrollRegion.evaluate((region) => region.scrollLeft))
      .toBeGreaterThan(0);

    const bulkFix = page.getByTestId('library-health-fix-selected');
    await expect(bulkFix).toHaveText('Queue fixes for 1 auto-fixable issue');
    await bulkFix.hover();
    await expect(page.getByText(
      'Queue bounded remediation downloads for up to 25 selected auto-fixable issues. This starts the existing download/remediation workflow; use it when you want slskd to attempt a replacement. The original files are not edited by this control.',
      { exact: true },
    )).toBeVisible();

    const actionBounds = await page
      .locator('.library-health-selection-actions .ui.button')
      .evaluateAll((buttons) => buttons.map((button) => {
        const { height, right, x } = button.getBoundingClientRect();
        return { height, right, x };
      }));
    expect(actionBounds.length).toBeGreaterThan(0);
    expect(actionBounds.every((bounds) =>
      bounds.height >= 44 && bounds.x >= 0 && bounds.right <= 320,
    )).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);
  });

  test('keeps Admin Policies reviewable and keyboard-usable at 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    await page.setViewportSize({ height: 812, width: 320 });
    await page.goto(`${node.baseUrl}/system/policies`, {
      waitUntil: 'domcontentloaded',
    });

    const policies = page.locator('.admin-policies');
    await expect(policies.getByText('Actions: Webhooks and Scripts')).toBeVisible();
    await expect(policies.getByText('Retention and Storage')).toBeVisible();
    const pageWidth = await page.evaluate(() => ({
      document: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
    }));
    expect(pageWidth.document, JSON.stringify(pageWidth)).toBeLessThanOrEqual(
      pageWidth.viewport,
    );

    const retentionRegion = page.getByRole('region', {
      name: 'Transfer history retention settings',
    });
    await expect(retentionRegion).toHaveAttribute('tabindex', '0');
    expect(await retentionRegion.evaluate((region) => region.scrollWidth > region.clientWidth))
      .toBe(true);
    await retentionRegion.focus();
    await page.keyboard.press('ArrowRight');
    await expect.poll(() => retentionRegion.evaluate((region) => region.scrollLeft))
      .toBeGreaterThan(0);

    const reset = policies.getByRole('button', { name: 'Reset' });
    const save = policies.getByRole('button', { name: 'Save YAML' });
    const actionBounds = await Promise.all([reset, save].map((button) =>
      button.evaluate((element) => {
        const { height, right, x } = element.getBoundingClientRect();
        return { height, right, x };
      }),
    ));
    expect(actionBounds.every((bounds) =>
      bounds.height >= 44 && bounds.x >= 0 && bounds.right <= 320,
    )).toBe(true);

    await reset.hover();
    await expect(page.getByText(
      'Discard unsaved policy edits and restore values currently reported by the daemon.',
      { exact: true },
    )).toBeVisible();
    const popupBounds = await page
      .locator('.admin-policy-popup.ui.popup.visible')
      .evaluate((popup) => {
        const { width, x } = popup.getBoundingClientRect();
        return { width, x };
      });
    expect(popupBounds.x).toBeGreaterThanOrEqual(0);
    expect(popupBounds.x + popupBounds.width).toBeLessThanOrEqual(320);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);
    await reset.focus();
    await page.keyboard.press('Enter');
  });

  test('makes populated System Files navigable, recoverable, and scrollable at 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);

    const longName = 'a-very-long-transfer-filename-that-needs-horizontal-scrolling.flac';
    let fileDeleted = false;
    let deleteAttempts = 0;
    let listRequests = 0;
    let sizeListRequests = 0;
    let batchDeleteRequests = 0;
    let batchDeleteBody: { items: Array<{ path: string; type: string }> } | null = null;
    await page.route('**/api/v0/files/downloads/directories/**', async (route) => {
      listRequests += 1;
      const requestUrl = new URL(route.request().url());
      const pathSegment = requestUrl.pathname.split('/').pop() || '';
      const subdirectory = pathSegment
        ? Buffer.from(pathSegment, 'base64').toString('utf8')
        : '';
      const includeDirectorySizes = requestUrl.searchParams.get('includeDirectorySizes') === 'true';
      if (includeDirectorySizes) sizeListRequests += 1;

      if (subdirectory === 'Albums') {
        await route.fulfill({
          contentType: 'application/json',
          json: {
            directories: [],
            files: [{ fullName: 'Albums/inside.flac', length: 128, name: 'inside.flac' }],
          },
        });
        return;
      }

      await route.fulfill({
        contentType: 'application/json',
        json: {
          directories: [
            { fullName: 'Albums', length: includeDirectorySizes ? 2048 : null, name: 'Albums' },
            { fullName: 'Singles', length: includeDirectorySizes ? 1024 : null, name: 'Singles' },
          ],
          files: fileDeleted
            ? []
            : [{
              fullName: longName,
              length: 1024,
              modifiedAt: '2026-10-02T12:00:00Z',
              name: longName,
            }],
        },
      });
    });
    await page.route('**/api/v0/files/downloads/items', async (route) => {
      batchDeleteRequests += 1;
      batchDeleteBody = route.request().postDataJSON();
      await route.fulfill({
        contentType: 'application/json',
        json: {
          results: [
            { path: 'Albums', type: 'directory', succeeded: false, error: 'access-denied' },
            { path: 'Singles', type: 'directory', succeeded: true, error: null },
          ],
        },
        status: 207,
      });
    });
    await page.route('**/api/v0/files/downloads/files/**', async (route) => {
      deleteAttempts += 1;
      if (deleteAttempts === 1) {
        await route.fulfill({
          contentType: 'application/json',
          json: { message: 'temporary file deletion failure' },
          status: 503,
        });
        return;
      }

      fileDeleted = true;
      await route.fulfill({ status: 204 });
    });

    await login(page, node);
    await page.setViewportSize({ height: 812, width: 320 });
    await page.goto(`${node.baseUrl}/system/files`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.getByRole('region', {
      name: 'Downloads files and directories',
    })).toBeVisible();
    const directoryButton = page.getByRole('button', {
      name: 'Open the Albums directory.',
    });
    await directoryButton.hover();
    await expect(page.getByText('Open the Albums directory.', { exact: true }))
      .toBeVisible();
    await directoryButton.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByText('inside.flac', { exact: true })).toBeVisible();
    const parentButton = page.getByRole('button', { name: 'Go up one directory.' });
    await parentButton.focus();
    await page.keyboard.press('Enter');

    const calculateSizes = page.getByRole('button', { name: 'Calculate folder sizes' });
    await calculateSizes.hover();
    await expect(page.getByText(
      'Calculate the size of every listed directory by totaling its files recursively. This reads directory contents but does not open or modify file data.',
      { exact: true },
    )).toBeVisible();
    await calculateSizes.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('button', { name: 'Refresh folder sizes' })).toBeVisible();
    await expect.poll(() => sizeListRequests).toBe(1);
    const albumsRow = page.getByRole('row').filter({
      has: page.getByRole('button', { name: 'Open the Albums directory.' }),
    });
    await expect(albumsRow).toContainText('2 KB');

    const deleteTrigger = page.getByRole('button', {
      name: `Delete file ${longName}`,
    });
    await expect(deleteTrigger).toBeVisible();
    await deleteTrigger.hover();
    await expect(page.getByText(
      `Open confirmation to permanently delete file '${longName}'.`,
      { exact: true },
    )).toBeVisible();
    await deleteTrigger.focus();
    await page.keyboard.press('Enter');

    const confirmDelete = page.getByRole('button', { name: 'Delete', exact: true });
    await expect(confirmDelete).toBeVisible();
    await confirmDelete.hover();
    await expect(page.getByText(
      'Permanently delete this file. This action cannot be undone.',
      { exact: true },
    )).toBeVisible();
    await confirmDelete.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('alert')).toContainText(
      'temporary file deletion failure',
    );
    await expect(confirmDelete).toBeEnabled();
    await confirmDelete.focus();
    await page.keyboard.press('Enter');
    await expect.poll(() => deleteAttempts).toBe(2);
    await expect(page.getByText(longName, { exact: true })).toHaveCount(0);
    await expect.poll(() => listRequests).toBeGreaterThan(2);

    const selectAlbums = page.getByRole('checkbox', { name: 'Select directory Albums' });
    const selectSingles = page.getByRole('checkbox', { name: 'Select directory Singles' });
    await selectAlbums.focus();
    await page.keyboard.press('Space');
    await expect(selectAlbums).toBeChecked();
    await selectSingles.focus();
    await page.keyboard.press('Space');
    await expect(selectSingles).toBeChecked();
    await expect(page.getByText('2 selected', { exact: true })).toBeVisible();

    const bulkDelete = page.getByRole('button', { name: 'Delete selected (2)' });
    await bulkDelete.hover();
    await expect(page.getByText(
      'Permanently delete the selected files and directories. Selected directories are removed with their contents.',
      { exact: true },
    )).toBeVisible();
    await bulkDelete.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByText(
      'Permanently delete 2 selected items? Directories will be deleted recursively.',
      { exact: true },
    )).toBeVisible();
    const confirmBulkDelete = page.getByRole('button', { name: 'Delete 2 items' });
    await confirmBulkDelete.focus();
    await page.keyboard.press('Enter');
    await expect.poll(() => batchDeleteRequests).toBe(1);
    expect(batchDeleteBody).toEqual({
      items: [
        { path: 'Albums', type: 'directory' },
        { path: 'Singles', type: 'directory' },
      ],
    });
    await expect(page.locator('.system-files-explorer [role="status"]'))
      .toContainText('Deleted 1 item.');
    await expect(page.getByRole('alert')).toContainText('Albums: Access was denied');
    await expect(selectAlbums).toBeChecked();
    await expect(selectSingles).not.toBeChecked();

    const scrollRegion = page.getByRole('region', {
      name: 'Downloads files and directories',
    });
    await expect(scrollRegion).toHaveAttribute('tabindex', '0');
    expect(await scrollRegion.evaluate((region) => region.scrollWidth > region.clientWidth))
      .toBe(true);
    await scrollRegion.focus();
    await page.keyboard.press('ArrowRight');
    await expect.poll(() => scrollRegion.evaluate((region) => region.scrollLeft))
      .toBeGreaterThan(0);

    const actionBounds = await page
      .locator('.explorer-list-action .ui.button')
      .evaluateAll((buttons) => buttons.map((button) => {
        const { height, width } = button.getBoundingClientRect();
        return { height, width };
      }));
    expect(actionBounds.every((bounds) => bounds.height >= 44 && bounds.width >= 44))
      .toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);
  });

  test('keeps Downloads and Uploads reachable by keyboard at 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);
    await page.setViewportSize({ height: 720, width: 320 });
    await page.goto(`${node.baseUrl}/downloads`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.getByTestId('downloads-root')).toBeVisible();
    await expect(page.locator('.transfer-direction-menu')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);

    const uploadsLink = page.getByRole('link', {
      exact: true,
      name: 'Uploads',
    });
    await uploadsLink.focus();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/uploads$/);
    await expect(page.getByTestId('uploads-root')).toBeVisible();
    await expect(page.locator('.transfer-direction-menu')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);

    const downloadsLink = page.getByRole('link', {
      exact: true,
      name: 'Downloads',
    });
    await downloadsLink.focus();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/downloads$/);
    await expect(page.getByTestId('downloads-root')).toBeVisible();
  });

  test('saves supported Experience preferences and applies player visibility at 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);
    await page.setViewportSize({ height: 720, width: 320 });
    await page.evaluate(() => {
      localStorage.removeItem('slskdn:experience-preferences:v1');
    });
    await page.goto(`${node.baseUrl}/system/experience`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.getByText('Experience Preferences')).toBeVisible();
    await expect(page).toHaveURL(/\/system\/experience$/);
    const playerPreference = page.getByRole('checkbox', {
      name: 'Show browser player preference',
    });
    await expect(playerPreference).toBeChecked();
    await page.getByText('Show browser player', { exact: true }).click();
    await expect(playerPreference).not.toBeChecked();
    await page.getByRole('button', { name: 'Save Local Preferences' }).click();
    await expect(
      page.getByText('Experience preferences saved locally in this browser.'),
    ).toBeVisible();
    await expect(page.getByRole('button', { name: 'Show player' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);

    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('button', { name: 'Show player' })).toBeVisible();
    await page.getByRole('button', { name: 'Show player' }).click();
    await expect(page.getByTestId('player-show')).toHaveCount(0);

    await page.goto(`${node.baseUrl}/system/experience`, {
      waitUntil: 'domcontentloaded',
    });
    await expect(page.getByRole('checkbox', {
      name: 'Show browser player preference',
    })).toBeChecked();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);
  });

  test('keeps remaining primary routes usable at 320px', async ({ page, request }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);
    await page.setViewportSize({ height: 812, width: 320 });

    const routes = [
      { path: '/collections', surface: '[data-testid="collections-root"]' },
      { path: '/solid', surface: '[data-testid="solid-root"]' },
      { path: '/discovery-graph', surface: '.discovery-graph-atlas-panel' },
      { path: '/playlist-intake', surface: '.playlist-intake' },
      { path: '/wishlist', surface: '.wishlist-container' },
      { path: '/lidarr', surface: '.lidarr-container' },
      { path: '/users', surface: '.users-input' },
      { path: '/contacts', surface: '[data-testid="contacts-root"]' },
      { path: '/system/info', surface: '[data-testid="system-overview"]' },
      { path: '/sharegroups', surface: '.view h1' },
      { path: '/shared', surface: '.view h1' },
      { path: '/chat', surface: '.msgv2' },
      { path: '/pods', surface: '.msgv2' },
      { path: '/rooms', surface: '.msgv2' },
    ];

    for (const route of routes) {
      await page.goto(`${node.baseUrl}${route.path}`, {
        waitUntil: 'domcontentloaded',
      });
      await expect(page.locator(route.surface), `${route.path} content`).toBeVisible();

      const layout = await page.evaluate(() => ({
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
      }));
      expect(
        layout.documentWidth,
        `${route.path} has horizontal page overflow at ${layout.viewportWidth}px`,
      ).toBeLessThanOrEqual(layout.viewportWidth);

    }
  });

  test('keeps populated sharing and Wishlist views within 320px', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    const collection = {
      description: 'A shared collection used to review narrow layouts.',
      id: 'mobile-layout-collection',
      itemCount: 3,
      ownerUserId: 'mobile-layout-owner',
      title: 'A deliberately long collection title for narrow screens',
      type: 'Playlist',
    };
    const groupName = 'A deliberately long share group name for narrow screens';
    const wishlistSearch =
      'A deliberately long artist name - a long track title for narrow screens';

    await page.route('**/api/v0/collections', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({ contentType: 'application/json', json: [collection] });
      } else {
        await route.continue();
      }
    });
    await page.route('**/api/v0/collections/mobile-layout-collection', async (route) => {
      await route.fulfill({ contentType: 'application/json', json: collection });
    });
    await page.route('**/api/v0/sharegroups', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          contentType: 'application/json',
          json: [{ createdAt: '2026-05-06T00:00:00Z', id: 'mobile-layout-group', name: groupName }],
        });
      } else {
        await route.continue();
      }
    });
    await page.route('**/api/v0/share-grants**', async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: [{
          allowDownload: true,
          allowReshare: false,
          allowStream: true,
          collectionId: collection.id,
          id: 'mobile-layout-share',
          ownerUserId: 'mobile-layout-owner',
        }],
      });
    });
    await page.route('**/api/v0/wishlist', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          contentType: 'application/json',
          json: [{
            autoDownload: false,
            enabled: true,
            filter: 'flac',
            id: 'mobile-layout-wishlist',
            lastMatchCount: 0,
            lastSearchedAt: null,
            searchText: wishlistSearch,
            totalSearchCount: 0,
          }],
        });
      } else {
        await route.continue();
      }
    });

    await page.setViewportSize({ height: 812, width: 320 });
    const routes = [
      { content: collection.title, path: '/collections' },
      { content: groupName, path: '/sharegroups' },
      { content: collection.title, path: '/shared' },
      { content: wishlistSearch, path: '/wishlist' },
    ];

    for (const route of routes) {
      await page.goto(`${node.baseUrl}${route.path}`, {
        waitUntil: 'domcontentloaded',
      });
      await expect(page.getByText(route.content, { exact: true }), route.path)
        .toBeVisible();

      if (route.path === '/wishlist') {
        const cardsButton = page.getByRole('button', {
          name: 'Show wishlist as cards',
        });
        await cardsButton.click();
        await expect(page.locator('.wishlist-card').getByText(wishlistSearch))
          .toBeVisible();
      }

      const layout = await page.evaluate(() => ({
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
      }));
      expect(
        layout.documentWidth,
        `${route.path} has horizontal page overflow at ${layout.viewportWidth}px`,
      ).toBeLessThanOrEqual(layout.viewportWidth);

      const overflowingTables = await page.evaluate(() =>
        Array.from(document.querySelectorAll('.view .ui.table'))
          .map((table) => {
            const tableRect = table.getBoundingClientRect();
            let scrollRegion = table.parentElement;

            while (scrollRegion && scrollRegion !== document.body) {
              const style = getComputedStyle(scrollRegion);
              const scrollsHorizontally =
                style.overflowX === 'auto' || style.overflowX === 'scroll';

              if (
                scrollsHorizontally &&
                scrollRegion.scrollWidth > scrollRegion.clientWidth
              ) {
                break;
              }

              scrollRegion = scrollRegion.parentElement;
            }

            return {
              extendsPastViewport: tableRect.right > window.innerWidth + 1,
              hasAccessibleScrollRegion: Boolean(
                scrollRegion &&
                  scrollRegion !== document.body &&
                  scrollRegion.tabIndex >= 0 &&
                  scrollRegion.getAttribute('role') === 'region' &&
                  (scrollRegion.getAttribute('aria-label') ||
                    scrollRegion.getAttribute('aria-labelledby')),
              ),
            };
          })
          .filter((table) => table.extendsPastViewport),
      );
      expect(
        overflowingTables.every((table) => table.hasAccessibleScrollRegion),
        `${route.path} has a table extending past the viewport without an accessible scroll region`,
      ).toBe(true);
    }
  });

  test('persists transfer view preferences and keeps row cells aligned with headers', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);
    await page.setViewportSize({ height: 720, width: 320 });

    await page.evaluate(() => {
      const columns = {
        order: ['peer', 'name', 'size'],
        visible: {
          actions: false,
          album: false,
          artist: false,
          bitrate: false,
          completed: false,
          directory: false,
          elapsed: false,
          eta: false,
          extension: false,
          length: false,
          local: false,
          name: true,
          peer: true,
          progress: false,
          requested: false,
          remaining: false,
          samplerate: false,
          size: true,
          speed: false,
          started: false,
          state: false,
          title: false,
          track: false,
          year: false,
        },
        widths: { name: 200, peer: 90, size: 120 },
      };
      localStorage.setItem('slskdn-transfer-columns-download', JSON.stringify(columns));
    });

    await page.route(/\/api\/v0\/transfers\/changes(?:\?|$)/u, async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        json: {
          counts: { download: 1, upload: 0 },
          cursor: 1,
          transfers: [{
            bytesTransferred: 5,
            direction: 'Download',
            filename: 'Artist/Track.flac',
            id: 'ui-regression-transfer',
            percentComplete: 50,
            size: 10,
            state: 'InProgress',
            username: 'peer-one',
          }],
        },
      });
    });
    await page.route('**/api/v0/transfers/downloads/accelerated', async (route) => {
      await route.fulfill({ contentType: 'application/json', json: { enabled: false } });
    });
    await page.route('**/api/v0/autoreplace', async (route) => {
      await route.fulfill({ contentType: 'application/json', json: { enabled: false } });
    });

    await page.goto(`${node.baseUrl}/downloads`, {
      waitUntil: 'domcontentloaded',
    });

    const transferTable = page.locator('.transfer-table-wrapper');
    await expect(transferTable).toHaveCSS('overflow-x', 'auto');
    await expect(transferTable).toHaveAttribute('tabindex', '0');
    const headers = page.locator('.transfer-header-cell');
    await expect(headers).toHaveCount(3);
    expect(await headers.evaluateAll((cells) => cells.map((cell) => cell.dataset.colkey)))
      .toEqual(['peer', 'name', 'size']);

    const rowCells = page.locator('.transfer-row:not(.transfer-header-row) [data-colkey]');
    await expect(rowCells).toHaveCount(3);
    expect(await rowCells.evaluateAll((cells) => cells.map((cell) => cell.dataset.colkey)))
      .toEqual(['peer', 'name', 'size']);
    const gridWidth = await page.locator('.transfer-grid').evaluate(
      (grid) => grid.getBoundingClientRect().width,
    );
    const wrapperWidth = await transferTable.evaluate((wrapper) => wrapper.clientWidth);
    expect(gridWidth).toBeGreaterThan(wrapperWidth);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth))
      .toBe(false);
    await transferTable.focus();
    await page.keyboard.press('ArrowRight');
    await expect.poll(() => transferTable.evaluate((wrapper) => wrapper.scrollLeft))
      .toBeGreaterThan(0);
    await page.keyboard.press('ArrowLeft');
    await expect.poll(() => transferTable.evaluate((wrapper) => wrapper.scrollLeft))
      .toBe(0);

    const hideCompleted = page.locator('.hide-completed-toggle input');
    await expect(hideCompleted).toBeChecked();
    await page.locator('.hide-completed-toggle label').click();
    await page.locator('.transfer-header-cell[data-colkey="size"]').click();

    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.locator('.transfer-header-cell[data-colkey="size"]')).toHaveAttribute(
      'aria-sort',
      'ascending',
    );
    await expect(page.locator('.hide-completed-toggle input')).not.toBeChecked();
  });

  test('persists and retrieves blocked users through the authenticated API', async ({
    page,
    request,
  }) => {
    const node = getNode();
    await waitForHealth(request, node.baseUrl);
    await login(page, node);

    const token = await getAuthToken(page);
    const headers = { Authorization: `Bearer ${token}` };
    const username = `playwright-regression-${Date.now()}`;
    const encodedUsername = encodeURIComponent(username);

    try {
      const initial = await request.get(`${node.baseUrl}/api/v0/users/blocks`, {
        failOnStatusCode: false,
        headers,
      });
      expect(initial.status()).toBe(200);

      const blocked = await request.put(
        `${node.baseUrl}/api/v0/users/blocks/${encodedUsername}`,
        { failOnStatusCode: false, headers },
      );
      expect(blocked.status()).toBe(200);
      expect((await blocked.json()).username).toBe(username);

      const persisted = await request.get(`${node.baseUrl}/api/v0/users/blocks`, {
        failOnStatusCode: false,
        headers,
      });
      expect(persisted.status()).toBe(200);
      expect((await persisted.json()).some((entry: { username: string }) => entry.username === username)).toBe(true);
    } finally {
      const removed = await request.delete(
        `${node.baseUrl}/api/v0/users/blocks/${encodedUsername}`,
        { failOnStatusCode: false, headers },
      );
      expect([204, 404]).toContain(removed.status());
    }
  });
});
