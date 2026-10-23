import { NODES, shouldLaunchNodes } from './env';
import { hasDownloadedMediaFixtures } from './fixtures/ensure-fixtures';
import { MultiPeerHarness } from './harness/MultiPeerHarness';
import {
  announceShareGrant,
  clickNav,
  getAuthToken,
  login,
  waitForDownloadInList,
  waitForHealth,
  waitForLibraryItem,
  waitForShareGrantById,
} from './helpers';
import { T } from './selectors';
import { expect, test } from '@playwright/test';

test.describe.configure({ mode: 'serial' });
const hasDownloadedMedia = hasDownloadedMediaFixtures();

test.describe('multi-peer sharing', () => {
  test.skip(
    !hasDownloadedMedia,
    'Multi-peer sharing E2E requires downloaded media fixtures',
  );

  let harness: MultiPeerHarness | null = null;
  const groupName = 'E2E Crew';
  const collectionTitle = 'E2E Playlist';
  let sharedGrantId: string | null = null;

  test.beforeAll(async () => {
    if (shouldLaunchNodes()) {
      harness = new MultiPeerHarness();
      // Node A: shares movie/ + book/
      await harness.startNode(
        'A',
        [
          'test-data/slskdn-test-fixtures/movie',
          'test-data/slskdn-test-fixtures/book',
        ],
        {
          noConnect: process.env.SLSKDN_TEST_NO_CONNECT === 'true',
        },
      );
      // Node B: shares music/ + tv/
      await harness.startNode(
        'B',
        [
          'test-data/slskdn-test-fixtures/music',
          'test-data/slskdn-test-fixtures/tv',
        ],
        {
          noConnect: process.env.SLSKDN_TEST_NO_CONNECT === 'true',
        },
      );
      // Node C: recipient-only (no shares)
      const nodeAEndpoint = harness.getNode('A').nodeCfg.baseUrl;
      await harness.startNode('C', [], {
        noConnect: process.env.SLSKDN_TEST_NO_CONNECT === 'true',
        trustedPrivateOwnerOrigins: [nodeAEndpoint],
      });
    }
  });

  test.afterAll(async () => {
    if (harness) {
      await harness.stopAll();
    }
  });

  test('invite_add_friend', async ({ browser, request }) => {
    const nodeA = harness ? harness.getNode('A').nodeCfg : NODES.A;
    const nodeB = harness ? harness.getNode('B').nodeCfg : NODES.B;

    await waitForHealth(request, nodeA.baseUrl);
    await waitForHealth(request, nodeB.baseUrl);

    const contextA = await browser.newContext();
    const contextB = await browser.newContext();
    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    await login(pageA, nodeA);
    await login(pageB, nodeB);

    // Diagnostic: Capture JS/runtime errors BEFORE navigation
    pageA.on('pageerror', (error) =>
      console.error('[Contacts Test] pageerror:', error),
    );
    pageA.on('console', (message) => {
      if (message.type() === 'error')
        console.error('[Contacts Test] console.error:', message.text());
    });

    // Navigate to contacts page and wait for it to load
    console.log('[Contacts Test] Navigating to contacts page...');
    const targetUrl = `${nodeA.baseUrl}/contacts`;
    console.log('[Contacts Test] Target URL:', targetUrl);
    const contactsResponsePromise = pageA
      .waitForResponse(
        (response) =>
          response.url().includes('/api/v0/contacts') &&
          response.status() === 200,
        { timeout: 10_000 },
      )
      .then(
        (response) => ({ response, error: undefined }),
        (error: unknown) => ({ response: undefined, error }),
      );
    await pageA.goto(targetUrl, { timeout: 10_000, waitUntil: 'networkidle' });
    console.log('[Contacts Test] Navigation complete, URL:', pageA.url());

    // Capture the contacts response that was subscribed to before navigation.
    console.log('[Contacts Test] Waiting for /api/v0/contacts response...');
    const contactsResponseResult = await contactsResponsePromise;
    if (contactsResponseResult.response) {
      const text = await contactsResponseResult.response.text();
      const contentType =
        contactsResponseResult.response.headers()['content-type'] || '';
      console.log('[Contacts Test] API Response - Content-Type:', contentType);
      console.log('[Contacts Test] API Response - Length:', text.length);
      console.log(
        '[Contacts Test] API Response - First 200 chars:',
        text.slice(0, 200),
      );

      if (text.length === 0) {
        console.error(
          '[Contacts Test] ERROR: API returned 200 with empty body!',
        );
      }

      if (text.startsWith('<html')) {
        console.error(
          '[Contacts Test] ERROR: API returned HTML instead of JSON!',
        );
      }
    } else {
      console.error(
        '[Contacts Test] ERROR waiting for API response:',
        contactsResponseResult.error,
      );
    }

    // Diagnostic: Compare browser location vs app location (memory history check)
    const loc = await pageA.evaluate(() => ({
      href: location.href,
      pathname: location.pathname,
    }));
    const appLoc = await pageA.evaluate(() => {
      if ((window as any).__APP_HISTORY__) {
        return (window as any).__APP_HISTORY__.location.pathname;
      }

      if ((window as any).__APP_LOCATION__) {
        return (window as any).__APP_LOCATION__.pathname;
      }

      return null;
    });
    console.log(
      '[Contacts Test] Browser location:',
      JSON.stringify(loc, null, 2),
    );
    console.log('[Contacts Test] App location/history:', appLoc);

    // Check if URL changed (redirect happened)
    const finalUrl = pageA.url();
    if (!finalUrl.includes('/contacts')) {
      console.error(
        `[Contacts Test] ERROR: Redirected away from /contacts! Final URL: ${finalUrl}`,
      );
    }

    // Check what's actually on the page
    const bodyContent = await pageA.locator('body').innerText();
    console.log(
      '[Contacts Test] Body text (first 500 chars):',
      bodyContent.slice(0, 500),
    );

    // Check which component is actually rendering
    const hasSearchElements = await pageA
      .locator('input[placeholder*="Search"], [data-testid*="search"]')
      .count();
    const hasContactsElements = await pageA
      .locator('[data-testid="contacts-root"], [data-testid*="contact"]')
      .count();
    console.log('[Contacts Test] Search elements count:', hasSearchElements);
    console.log(
      '[Contacts Test] Contacts elements count:',
      hasContactsElements,
    );

    // Check React component tree if possible
    const reactRoot = await pageA.evaluate(() => {
      const root = document.querySelector('#root');
      if (!root) return null;
      const firstChild = root.firstElementChild;
      return {
        firstChildClass: firstChild?.className,
        firstChildTag: firstChild?.tagName,
        firstChildText: firstChild?.textContent?.slice(0, 100),
        rootTag: root.tagName,
      };
    });
    console.log(
      '[Contacts Test] React root info:',
      JSON.stringify(reactRoot, null, 2),
    );

    // Check if we're still on login page (route guard)
    const loginForm = await pageA
      .locator(
        '[data-testid="login-username"], input[placeholder*="Username" i]',
      )
      .count();
    console.log('[Contacts Test] Login form count:', loginForm);
    if (loginForm > 0) {
      console.error(
        '[Contacts Test] ERROR: Still on login page - route guard may be blocking!',
      );
    }

    // Check for any React error boundaries or error messages
    const errorElements = await pageA
      .locator('[class*="error"], [class*="Error"], [data-testid*="error"]')
      .count();
    console.log('[Contacts Test] Error elements count:', errorElements);

    // Check what React Router thinks the current route is
    const currentRoute = await pageA.evaluate(() => {
      // Try to find React Router state or current pathname
      return {
        hash: window.location.hash,
        pathname: window.location.pathname,
        search: window.location.search,
        urlBase: (window as any).urlBase || 'not set',
      };
    });
    console.log(
      '[Contacts Test] Current route info:',
      JSON.stringify(currentRoute, null, 2),
    );

    // Wait for contacts root to appear (ensures component mounted)
    console.log('[Contacts Test] Waiting for contacts-root...');
    try {
      await pageA.waitForSelector('[data-testid="contacts-root"]', {
        timeout: 10_000,
      });
      console.log('[Contacts Test] contacts-root found - component mounted');
    } catch (error) {
      console.error('[Contacts Test] ERROR: contacts-root not found!');
      // Dump all data-testid elements to see what's actually rendered
      const allTestIds = await pageA.evaluate(() => {
        const elements = document.querySelectorAll('[data-testid]');
        return Array.from(elements).map((element) => ({
          tag: element.tagName,
          testid: (element as HTMLElement).dataset.testid,
          visible: (element as HTMLElement).offsetParent !== null,
        }));
      });
      console.log(
        '[Contacts Test] All data-testid elements on page:',
        JSON.stringify(allTestIds, null, 2),
      );
      throw error;
    }

    // Diagnostic: Check current state
    const tid = T.contactsCreateInvite;
    const count = await pageA.locator(`[data-testid="${tid}"]`).count();
    console.log('[Contacts Test] count([data-testid="%s"]) = %d', tid, count);

    // If present, dump visibility diagnostics
    if (count > 0) {
      const diag = await pageA
        .locator(`[data-testid="${tid}"]`)
        .first()
        .evaluate((element) => {
          const cs = getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          return {
            disabled: (element as any).disabled ?? null,
            display: cs.display,
            inDocument: document.contains(element),
            opacity: cs.opacity,
            rect: { h: rect.height, w: rect.width, x: rect.x, y: rect.y },
            tag: element.tagName,
            visibility: cs.visibility,
          };
        });
      console.log(
        '[Contacts Test] button diag:',
        JSON.stringify(diag, null, 2),
      );
    } else {
      console.error(
        `[Contacts Test] ERROR: Button with data-testid="${tid}" not found in DOM!`,
      );
    }

    // Screenshot and body snippet for debugging
    await pageA.screenshot({ fullPage: true, path: 'contacts-debug.png' });
    const bodyText = await pageA.locator('body').innerText();
    console.log(
      '[Contacts Test] body snippet (first 800 chars):',
      bodyText.slice(0, 800),
    );

    // Wait for create invite button (appears in header - always visible)
    const createInviteButton = pageA.getByTestId(T.contactsCreateInvite);
    await expect(createInviteButton.first()).toBeVisible({ timeout: 5_000 });

    await createInviteButton.click();

    // Wait for invite modal and get invite link
    const inviteOutput = pageA.getByTestId(T.contactsInviteOutput);
    await expect(inviteOutput).toBeVisible({ timeout: 5_000 });
    const invite = await inviteOutput.inputValue();
    expect(invite.length).toBeGreaterThan(20);

    // Node B adds friend
    await pageB.goto(`${nodeB.baseUrl}/contacts`, {
      timeout: 5_000,
      waitUntil: 'networkidle',
    });

    const addFriendButton = pageB.getByTestId(T.contactsAddFriend);
    await expect(addFriendButton).toBeVisible({ timeout: 5_000 });
    await addFriendButton.click();

    // Fill invite form
    const inviteInput = pageB.getByTestId(T.contactsAddInviteInput);
    await expect(inviteInput).toBeVisible({ timeout: 3_000 });
    await inviteInput.fill(invite);

    const nicknameInput = pageB.getByTestId(T.contactsContactNickname);
    await expect(nicknameInput).toBeVisible({ timeout: 3_000 });
    await nicknameInput.fill('nodeA');

    await pageB.getByTestId(T.contactsAddInviteSubmit).click();

    // Contact row should appear after adding
    const contactRow = pageB.getByTestId(T.contactsRow('nodeA'));
    await expect(contactRow).toBeVisible({ timeout: 5_000 });

    await contextA.close();
    await contextB.close();
  });

  test('create_group_add_member', async ({ browser, request }) => {
    const nodeA = harness ? harness.getNode('A').nodeCfg : NODES.A;
    await waitForHealth(request, nodeA.baseUrl);

    const contextA = await browser.newContext();
    const pageA = await contextA.newPage();
    await login(pageA, nodeA);

    await clickNav(pageA, T.navGroups);
    await pageA.getByTestId(T.groupsCreate).click();

    // Wait for create group modal
    await pageA.waitForSelector(`[data-testid="${T.groupsNameInput}"]`, {
      timeout: 5_000,
    });
    // Semantic UI wraps inputs in divs - select the actual input element
    await pageA.getByTestId(T.groupsNameInput).locator('input').fill(groupName);
    await pageA.getByTestId(T.groupsCreateSubmit).click();

    await expect(pageA.getByTestId(T.groupRow(groupName))).toBeVisible({
      timeout: 5_000,
    });

    // Add member - button is in the table row
    // Note: For this test to work, nodeA needs to have nodeB as a contact
    // The first test (invite_add_friend) has nodeB add nodeA, so we need bidirectional
    // For now, skip if no contacts available
    const addMemberButton = pageA
      .getByTestId(T.groupRow(groupName))
      .locator(`[data-testid="${T.groupAddMember}"]`)
      .first();
    await expect(addMemberButton).toBeVisible({ timeout: 5_000 });

    // Click and wait for modal to appear (check for modal header first, then picker)
    await addMemberButton.click();

    // Wait for modal to open - check for modal header text or the picker
    // Semantic UI modals might take a moment to animate in
    try {
      await pageA.waitForSelector('text=Add Member to', { timeout: 5_000 });
      console.log('[Test] Modal header found');
    } catch {
      console.log(
        '[Test] Modal header not found, checking for picker directly',
      );
    }

    // Check if contacts are available - modal shows different UI if no contacts
    // If no contacts, it shows an input field instead of the picker dropdown
    const picker = pageA.getByTestId(T.groupMemberPicker);
    const pickerVisible = await picker.isVisible().catch(() => false);

    if (!pickerVisible) {
      // No contacts available - add by Soulseek username (legacy)
      const userInput = pageA
        .locator('.ui.modal')
        .locator('input[placeholder*="username" i]')
        .first();
      await expect(userInput).toBeVisible({ timeout: 5_000 });
      await userInput.fill('nodeB');
      await pageA.getByTestId(T.groupMemberAddSubmit).click();
      await expect(userInput).not.toBeVisible({ timeout: 5_000 });
    } else {
      // Contacts available - use the dropdown picker
      await picker.click();

      // Wait for dropdown options to appear, then select first available contact
      await pageA.getByRole('option').first().click({ timeout: 5_000 });

      await pageA.getByTestId(T.groupMemberAddSubmit).click();

      // Wait for modal to close (member was added)
      await expect(picker).not.toBeVisible({ timeout: 5_000 });
    }

    await contextA.close();
  });

  test('create_collection_share_to_group', async ({ browser, request }) => {
    const nodeA = harness ? harness.getNode('A').nodeCfg : NODES.A;
    await waitForHealth(request, nodeA.baseUrl);

    const contextA = await browser.newContext();
    const pageA = await contextA.newPage();
    await login(pageA, nodeA);

    // Ensure the share group exists (so this test can run standalone)
    await clickNav(pageA, T.navGroups);
    const existingGroupRow = pageA.getByTestId(T.groupRow(groupName));
    if ((await existingGroupRow.count()) === 0) {
      await pageA.getByTestId(T.groupsCreate).click();
      await pageA.waitForSelector(`[data-testid="${T.groupsNameInput}"]`, {
        timeout: 5_000,
      });
      await pageA
        .getByTestId(T.groupsNameInput)
        .locator('input')
        .fill(groupName);
      await pageA.getByTestId(T.groupsCreateSubmit).click();
      await expect(pageA.getByTestId(T.groupRow(groupName))).toBeVisible({
        timeout: 5_000,
      });
    }

    // Ensure nodeC is a member (recipient visibility depends on this)
    const addMemberButton = pageA
      .getByTestId(T.groupRow(groupName))
      .locator(`[data-testid="${T.groupAddMember}"]`)
      .first();
    await expect(addMemberButton).toBeVisible({ timeout: 5_000 });
    await addMemberButton.click();
    const modalUserInput = pageA
      .locator('.ui.modal')
      .locator('input[placeholder*="username" i]')
      .first();
    if ((await modalUserInput.count()) > 0) {
      await modalUserInput.fill('nodeC');
      await pageA.getByTestId(T.groupMemberAddSubmit).click();
      await expect(modalUserInput).not.toBeVisible({ timeout: 5_000 });
    }

    // Navigate to collections page directly
    await pageA.goto(`${nodeA.baseUrl}/collections`, {
      timeout: 10_000,
      waitUntil: 'networkidle',
    });

    await expect(
      pageA.getByTestId('collections-root'),
      'The Collections route must render its page content',
    ).toBeVisible({ timeout: 10_000 });

    // Create collection
    const createButton = pageA.getByTestId(T.collectionsCreate);
    await expect(createButton).toBeVisible({ timeout: 5_000 });
    await createButton.click();

    await pageA.waitForSelector(`[data-testid="${T.collectionsTypeSelect}"]`, {
      timeout: 5_000,
    });
    await pageA.getByTestId(T.collectionsTypeSelect).click();
    await pageA.getByRole('option', { name: /playlist/i }).click();

    await pageA
      .getByTestId(T.collectionsTitleInput)
      .locator('input')
      .fill(collectionTitle);
    const createCollectionResponse = pageA.waitForResponse(
      (response) =>
        response.url().includes('/api/v0/collections') &&
        response.request().method() === 'POST',
      { timeout: 5_000 },
    );
    await pageA.getByTestId(T.collectionsCreateSubmit).click();
    const createCollectionResult = await createCollectionResponse;
    if (createCollectionResult.status() !== 201) {
      const body = await createCollectionResult.text();
      throw new Error(
        `Create collection failed: ${createCollectionResult.status()} ${body}`,
      );
    }

    await expect(
      pageA.getByTestId(T.collectionRow(collectionTitle)),
    ).toBeVisible({ timeout: 5_000 });
    await pageA.getByTestId(T.collectionRow(collectionTitle)).click();

    // Add real fixture items using library search
    // The collection row click should open the detail view
    await pageA.waitForTimeout(200); // Wait for selection (reduced from 500ms)

    // Click Add Item button
    const addItemButton = pageA.getByTestId('collection-add-item');
    await expect(addItemButton).toBeVisible({ timeout: 5_000 });
    await addItemButton.click();

    // Search for sintel (movie fixture) and add by contentId
    const searchInput = pageA.getByTestId('collection-item-search-input');
    await expect(searchInput).toBeVisible({ timeout: 5_000 });
    const sintelItem = await waitForLibraryItem(pageA, 'sintel');
    await searchInput.locator('input').fill(sintelItem.contentId);

    // Add the item
    await pageA.getByTestId('collection-add-item-submit').click();
    await pageA.waitForTimeout(500); // Reduced from 1000ms

    // Add second item: treasure (book fixture)
    await addItemButton.click();
    const treasureItem = await waitForLibraryItem(pageA, 'treasure');
    await searchInput.locator('input').fill(treasureItem.contentId);
    await pageA.getByTestId('collection-add-item-submit').click();
    await pageA.waitForTimeout(500); // Reduced from 1000ms

    // Verify items were added
    await expect(pageA.getByTestId('collection-items-table')).toBeVisible({
      timeout: 5_000,
    });

    // Share it
    const shareCreate = pageA.getByTestId(T.shareCreate);
    await expect(shareCreate).toBeVisible({ timeout: 5_000 });
    await shareCreate.click();
    const audiencePicker = pageA.getByTestId(T.shareAudiencePicker);
    await expect(audiencePicker).toBeVisible({ timeout: 5_000 });
    await audiencePicker.click();
    const groupOption = pageA.getByRole('option', {
      name: new RegExp(groupName, 'i'),
    });
    if ((await groupOption.count()) === 0) {
      throw new Error(
        'No share groups found in picker. Ensure group creation ran.',
      );
    }

    await groupOption.first().click();

    await pageA.getByTestId(T.sharePolicyStream).check();
    await pageA.getByTestId(T.sharePolicyDownload).check();

    const createShareResponse = pageA.waitForResponse(
      (response) =>
        response.url().includes('/api/v0/share-grants') &&
        response.request().method() === 'POST',
      { timeout: 5_000 },
    );
    await pageA.getByTestId(T.shareCreateSubmit).click();
    const createShareResult = await createShareResponse;
    let createShareBody;
    try {
      createShareBody = await createShareResult.json();
    } catch {
      createShareBody = await createShareResult.text();
    }

    if (createShareResult.status() !== 201) {
      throw new Error(
        `Create share failed: ${createShareResult.status()} ${typeof createShareBody === 'string' ? createShareBody : JSON.stringify(createShareBody)}`,
      );
    }

    if (!createShareBody?.id) {
      throw new Error('Create share response missing id.');
    }

    sharedGrantId = createShareBody.id;

    const nodeC = harness ? harness.getNode('C').nodeCfg : NODES.C;
    const contextC = await browser.newContext();
    const pageC = await contextC.newPage();
    await login(pageC, nodeC);
    const ownerToken = await getAuthToken(pageA);
    const recipientToken = await getAuthToken(pageC);
    await announceShareGrant({
      owner: nodeA,
      ownerToken,
      recipient: nodeC,
      recipientToken,
      request,
      shareGrantId: createShareBody.id,
      shareOverride: createShareBody,
    });
    await contextC.close();

    await expect(pageA.getByTestId(T.sharesList)).toContainText(
      collectionTitle,
      { timeout: 5_000 },
    );

    await contextA.close();
  });

  test('recipient_sees_shared_manifest', async ({ browser, request }) => {
    const nodeC = harness ? harness.getNode('C').nodeCfg : NODES.C;
    await waitForHealth(request, nodeC.baseUrl);

    const contextC = await browser.newContext();
    const pageC = await contextC.newPage();
    await login(pageC, nodeC);

    await clickNav(pageC, T.navSharedWithMe);

    let rowFound = false;
    for (let index = 0; index < 20; index++) {
      const row = pageC
        .getByTestId(`incoming-share-row-${collectionTitle}`)
        .first();
      if ((await row.count()) > 0) {
        rowFound = true;
        await row.getByTestId('incoming-share-open').click();
        break;
      }

      await pageC.waitForTimeout(500); // Reduced from 1000ms
    }

    expect(rowFound).toBe(true);

    await expect(pageC.getByTestId('shared-manifest')).toBeVisible({
      timeout: 15_000,
    });

    // Verify real fixture items appear (sintel or treasure)
    const manifestContent = await pageC
      .getByTestId('shared-manifest')
      .textContent();
    expect(manifestContent).toMatch(/sha256:/i);

    await contextC.close();
  });

  test('recipient_streams_video', async ({ browser, request }) => {
    const nodeA = harness ? harness.getNode('A').nodeCfg : NODES.A;
    const nodeC = harness ? harness.getNode('C').nodeCfg : NODES.C;
    await waitForHealth(request, nodeA.baseUrl);
    await waitForHealth(request, nodeC.baseUrl);

    const contextA = await browser.newContext();
    const contextC = await browser.newContext();
    const pageA = await contextA.newPage();
    const pageC = await contextC.newPage();
    await login(pageA, nodeA);
    await login(pageC, nodeC);

    // Ensure share is announced to nodeC
    const ownerToken = await getAuthToken(pageA);
    let recipientToken = await getAuthToken(pageC);

    // Get or create share grant
    let shareGrantId = sharedGrantId;
    let shareOverride: any | undefined;
    if (shareGrantId) {
      const checkRes = await request.get(
        `${nodeA.baseUrl}/api/v0/share-grants/${shareGrantId}`,
        {
          failOnStatusCode: false,
          headers: { Authorization: `Bearer ${ownerToken}` },
        },
      );
      if (checkRes.status() === 404) {
        shareGrantId = null;
        sharedGrantId = null;
      } else if (checkRes.ok()) {
        try {
          shareOverride = await checkRes.json();
        } catch {
          shareOverride = undefined;
        }
      }
    }
    if (!shareGrantId) {
      // Create share grant if it doesn't exist
      const groupsRes = await request.get(
        `${nodeA.baseUrl}/api/v0/sharegroups`,
        {
          failOnStatusCode: false,
          headers: { Authorization: `Bearer ${ownerToken}` },
        },
      );
      if (!groupsRes.ok()) {
        throw new Error(`Failed to load share groups: ${groupsRes.status()}`);
      }

      const groups = await groupsRes.json();
      let group = Array.isArray(groups)
        ? groups.find((g: any) => g?.name === groupName)
        : null;
      if (!group) {
        const createGroupRes = await request.post(
          `${nodeA.baseUrl}/api/v0/sharegroups`,
          {
            data: { name: groupName },
            headers: { Authorization: `Bearer ${ownerToken}` },
          },
        );
        if (!createGroupRes.ok()) {
          throw new Error(
            `Failed to create share group: ${createGroupRes.status()}`,
          );
        }

        group = await createGroupRes.json();
      }

      const collectionsRes = await request.get(
        `${nodeA.baseUrl}/api/v0/collections`,
        { headers: { Authorization: `Bearer ${ownerToken}` } },
      );
      const collections = await collectionsRes.json();
      let collection = Array.isArray(collections)
        ? collections.find((c: any) => c?.title === collectionTitle)
        : null;
      if (!collection) {
        const createCollectionRes = await request.post(
          `${nodeA.baseUrl}/api/v0/collections`,
          {
            data: { title: collectionTitle, type: 'Playlist' },
            headers: { Authorization: `Bearer ${ownerToken}` },
          },
        );
        if (!createCollectionRes.ok()) {
          throw new Error(
            `Failed to create collection: ${createCollectionRes.status()}`,
          );
        }

        collection = await createCollectionRes.json();
      }

      // Ensure collection has at least one video item so streaming works when this test
      // runs in isolation (it normally relies on earlier tests to populate items).
      const existingItemsRes = await request.get(
        `${nodeA.baseUrl}/api/v0/collections/${collection.id}/items`,
        { headers: { Authorization: `Bearer ${ownerToken}` } },
      );
      if (!existingItemsRes.ok()) {
        throw new Error(
          `Failed to load collection items: ${existingItemsRes.status()}`,
        );
      }

      const existingItems = await existingItemsRes.json();
      if (!Array.isArray(existingItems) || existingItems.length === 0) {
        // Deterministic fixture: test-data/slskdn-test-fixtures/book/treasure_island_pg120.txt
        // Use the library endpoint so the share repository has a matching ContentId.
        const libraryRes = await request.get(
          `${nodeA.baseUrl}/api/v0/library/items?query=treasure_island_pg120.txt&limit=1`,
          { headers: { Authorization: `Bearer ${ownerToken}` } },
        );
        if (!libraryRes.ok()) {
          throw new Error(
            `Failed to load library items: ${libraryRes.status()}`,
          );
        }

        const libraryPayload = await libraryRes.json();
        const libraryItems = Array.isArray(libraryPayload?.items)
          ? libraryPayload.items
          : [];
        const firstItem = libraryItems[0];
        const contentId = firstItem?.contentId || firstItem?.content_id;
        const mediaKind = firstItem?.mediaKind || firstItem?.media_kind;
        if (!contentId) {
          throw new Error('No library items available for streaming share.');
        }

        const addItemRes = await request.post(
          `${nodeA.baseUrl}/api/v0/collections/${collection.id}/items`,
          {
            data: {
              contentId,
              mediaKind,
            },
            headers: { Authorization: `Bearer ${ownerToken}` },
          },
        );
        if (!addItemRes.ok()) {
          const body = await addItemRes.text();
          throw new Error(
            `Failed to add collection item: ${addItemRes.status()} ${body}`,
          );
        }
      }

      const createShareRes = await request.post(
        `${nodeA.baseUrl}/api/v0/share-grants`,
        {
          data: {
            allowDownload: true,
            allowReshare: false,
            allowStream: true,
            audienceId: group.id,
            audienceType: 'ShareGroup',
            collectionId: collection.id,
          },
          headers: { Authorization: `Bearer ${ownerToken}` },
        },
      );
      if (!createShareRes.ok()) {
        throw new Error(
          `Failed to create share grant: ${createShareRes.status()}`,
        );
      }

      const share = await createShareRes.json();
      if (!share?.id) {
        throw new Error('Create share grant response missing id.');
      }

      shareGrantId = share.id;
      sharedGrantId = share.id;
      shareOverride = share;
    }

    if (typeof shareGrantId !== 'string' || shareGrantId.length === 0) {
      throw new Error('Share grant ID was not available after creation.');
    }
    const activeShareGrantId = shareGrantId;

    // Announce share to nodeC
    await announceShareGrant({
      owner: nodeA,
      ownerToken,
      recipient: nodeC,
      recipientToken,
      request,
      shareGrantId: activeShareGrantId,
      shareOverride,
    });

    // Wait for share to be available via API (more reliable than UI polling)
    recipientToken = await getAuthToken(pageC);
    const shareAvailable = await waitForShareGrantById({
      baseUrl: nodeC.baseUrl,
      request,
      shareGrantId: activeShareGrantId,
      timeoutMs: 30_000,
      token: recipientToken,
    });
    if (!shareAvailable) {
      throw new Error(
        `Share grant ${shareGrantId} not found on recipient node after 30s`,
      );
    }

    await clickNav(pageC, T.navSharedWithMe);

    // Wait for share row to appear in UI (should be quick since API confirmed it exists)
    let streamRowFound = false;
    for (let index = 0; index < 10; index++) {
      const row = pageC
        .getByTestId(`incoming-share-row-${collectionTitle}`)
        .first();
      if ((await row.count()) > 0) {
        streamRowFound = true;
        await row.getByTestId('incoming-share-open').click();
        break;
      }

      await pageC.waitForTimeout(500);
    }

    expect(streamRowFound).toBe(true);

    await expect(pageC.getByTestId('shared-manifest')).toBeVisible({
      timeout: 15_000,
    });

    // Resolve stream URL from manifest via API (more reliable than UI click)
    const streamItem = await pageC.evaluate(
      async ({ expectedTitle, expectedOwnerBaseUrl }) => {
        const token =
          sessionStorage.getItem('slskd-token') ||
          localStorage.getItem('slskd-token');
        if (!token) return null;

        const sharesRes = await fetch('/api/v0/share-grants', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!sharesRes.ok) return null;
        const sharesText = await sharesRes.text();
        if (!sharesText) return null;
        let shares;
        try {
          shares = JSON.parse(sharesText);
        } catch {
          return null;
        }

        if (!Array.isArray(shares) || shares.length === 0) return null;

        for (const share of shares) {
          if (!share?.id) continue;
          const manifestRes = await fetch(
            `/api/v0/share-grants/${share.id}/manifest`,
            {
              headers: { Authorization: `Bearer ${token}` },
            },
          );
          if (!manifestRes.ok) continue;
          const manifestText = await manifestRes.text();
          if (!manifestText) continue;
          let manifest;
          try {
            manifest = JSON.parse(manifestText);
          } catch {
            continue;
          }

          if (manifest?.title !== expectedTitle) continue;

          const items = Array.isArray(manifest?.items) ? manifest.items : [];
          const getName = (x: any) =>
            String(x?.filename || x?.path || x?.name || '');

          // Prefer an actual video item; share manifests can be sorted differently than insertion order.
          const item =
            items.find((x: any) => /sintel/i.test(getName(x))) ||
            items.find((x: any) =>
              /\.(mp4|mkv|webm|avi|mov)$/i.test(getName(x)),
            ) ||
            items.find(
              (x: any) =>
                String(x?.mediaKind || '')
                  .toLowerCase()
                  .includes('video'),
            ) ||
            items.find((x: any) => Boolean(x?.streamUrl || x?.stream_url));

          // API responses are typically snake_case, but some DTOs are camelCase.
          const url = item?.streamUrl || item?.stream_url;
          if (!url) continue;

          const contentId = item?.contentId || item?.content_id;
          if (!contentId) continue;
          if (url.startsWith(expectedOwnerBaseUrl)) return { contentId, streamUrl: url };
          if (url.startsWith('/')) return { contentId, streamUrl: `${expectedOwnerBaseUrl}${url}` };
        }

        return null;
      },
      {
        expectedOwnerBaseUrl: nodeA.baseUrl,
        expectedTitle: collectionTitle,
      },
    );

    if (!streamItem) {
      throw new Error('No streamable item found in manifest for stream test.');
    }

    const itemIdPrefix = streamItem.contentId.startsWith('sha256:')
      ? streamItem.contentId.slice(7, 15)
      : streamItem.contentId.slice(0, 8);
    const popupPromise = pageC.waitForEvent('popup');
    await pageC.getByTestId(`incoming-stream-${itemIdPrefix}`).click();
    const streamPage = await popupPromise;
    await expect(streamPage).toHaveURL(/ticket=/);
    const ticketedStreamUrl = new URL(streamPage.url());
    expect(ticketedStreamUrl.searchParams.has('ticket')).toBe(true);
    expect(ticketedStreamUrl.searchParams.has('token')).toBe(false);

    const streamResponse = await request.get(ticketedStreamUrl.href, {
      failOnStatusCode: false,
      headers: { Range: 'bytes=0-1' },
    });
    const status = streamResponse.status();
    expect([200, 206]).toContain(status);

    const contentType = streamResponse.headers()['content-type'];
    if (status === 206) {
      // Streaming supports any shared content; keep this broad so E2E isn't coupled
      // to local share-indexing heuristics for large media files.
      expect(contentType).toMatch(/video|audio|application|text|image/i);
    }

    await streamPage.close();

    await contextA.close();
    await contextC.close();
  });

  test('recipient_backfills_and_verifies_download', async ({
    browser,
    request,
  }) => {
    const nodeCInstance = harness ? harness.getNode('C') : null;
    const nodeC = nodeCInstance ? nodeCInstance.nodeCfg : NODES.C;
    await waitForHealth(request, nodeC.baseUrl);

    const contextC = await browser.newContext();
    const pageC = await contextC.newPage();
    await login(pageC, nodeC);

    await clickNav(pageC, T.navSharedWithMe);

    let rowFound = false;
    for (let index = 0; index < 30; index += 1) {
      const row = pageC
        .getByTestId(`incoming-share-row-${collectionTitle}`)
        .first();
      if ((await row.count()) > 0) {
        rowFound = true;
        await row.getByTestId('incoming-share-open').click();
        break;
      }

      await pageC.waitForTimeout(500); // Reduced from 1000ms
    }

    expect(rowFound).toBe(true);

    await expect(pageC.getByTestId('shared-manifest')).toBeVisible({
      timeout: 15_000,
    });

    const backfillButton = pageC.getByTestId('incoming-backfill');
    await expect(backfillButton).toBeVisible();
    const backfillResponsePromise = pageC.waitForResponse(
      (response) =>
        response.url().includes('/api/v0/share-grants/') &&
        response.url().includes('/backfill') &&
        response.request().method() === 'POST',
    );
    await backfillButton.click();
    const backfillResponse = await backfillResponsePromise;
    expect(backfillResponse.status()).toBe(200);
    const backfillResult = await backfillResponse.json() as {
      enqueued: number;
      errors?: string[];
      failed: number;
      message: string;
      total: number;
    };
    expect(backfillResult.total).toBeGreaterThan(0);
    expect(backfillResult.enqueued, JSON.stringify(backfillResult)).toBeGreaterThan(0);
    expect(backfillResult.failed, JSON.stringify(backfillResult)).toBe(0);
    console.log(`[Backfill Test] ${JSON.stringify(backfillResult)}`);

    if (nodeCInstance) {
      // Wait for the synchronous controller's file writes to become visible.
      await pageC.waitForTimeout(2_000);

      // Match the content-ID-style name, including the resulting hash portion.
      const fullId =
        'sha256_2e93caf3f954e8e8457d9846ad7756f74ccf192dab77b7247d48ba134a8e2c1b';
      const hashPart = '2e93caf3f954e8e8457d9846ad7756f74ccf192dab77b7247d48ba134a8e2c1b';
      let treasureFile = await nodeCInstance.waitForDownloadedFile(
        fullId,
        35_000,
      );
      if (!treasureFile) {
        treasureFile = await nodeCInstance.waitForDownloadedFile(
          hashPart,
          10_000,
        );
      }

      if (!treasureFile) {
        const allFiles = await nodeCInstance.getDownloadedFiles();
        console.error(
          `[Backfill Test] No expected files found. All downloaded files:`,
          allFiles.map((f) => `${f.name} (${f.size} bytes)`),
        );
        throw new Error(
          'Backfill failed: expected treasure file not found in downloads',
        );
      }

      expect(treasureFile.size).toBeGreaterThan(0);
      expect(treasureFile.size).toBeGreaterThan(100_000);
      console.log(
        `[Backfill Test] ✓ Found treasure file: ${treasureFile.name} (${treasureFile.size} bytes)`,
      );

      const allFiles = await nodeCInstance.getDownloadedFiles();
      console.log(
        '[Backfill Test] Total files in downloads: %d',
        allFiles.length,
        allFiles.map((f) => `${f.name} (${f.size} bytes)`),
      );
    } else {
      const token = await getAuthToken(pageC);
      const found = await waitForDownloadInList({
        baseUrl: nodeC.baseUrl,
        request,
        searchTerms: [
          'treasure',
          '2e93caf3f954e8e8457d9846ad7756f74ccf192dab77b7247d48ba134a8e2c1b',
        ],
        timeoutMs: 60_000,
        token,
      });
      expect(found).toBe(true);
    }

    await contextC.close();
  });
});
