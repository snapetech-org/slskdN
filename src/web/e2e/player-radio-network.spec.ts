// <copyright file="player-radio-network.spec.ts" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import * as fs from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import * as path from 'node:path';
import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { MultiPeerHarness } from './harness/MultiPeerHarness';
import { LatencyTcpProxy } from './harness/LatencyTcpProxy';
import { login } from './helpers';

async function createRadioRoom(request: APIRequestContext, apiUrl: string, headers: Record<string, string>, name: string): Promise<string> {
  const created = await request.post(`${apiUrl}/api/v0/pods`, {
    headers,
    data: { requestingPeerId: 'fixture-owner', pod: { name, visibility: 'Unlisted', channels: [{ channelId: 'music', name: 'Music' }] } },
  });
  expect(created.ok(), await created.text()).toBe(true);
  const podId = (await created.json()).podId;
  expect(podId).toMatch(/^pod:[a-f0-9]{32}$/u);
  return encodeURIComponent(podId);
}

function audioElements(page: Page): Locator {
  return page.locator('audio');
}

// Read isolated-node counters without introducing a diagnostic production endpoint.
function trafficTotals(appDir: string): number[] {
  const output = execFileSync('python3', ['-c',
    'import sqlite3,sys,json; connection=sqlite3.connect("file:"+sys.argv[1]+"?mode=ro",uri=True); row=connection.execute("SELECT overlay_upload_bytes, overlay_download_bytes FROM TrafficStats WHERE key=\'global\'").fetchone(); print(json.dumps(row or [0,0])); connection.close()',
    path.join(appDir, 'hashdb.db')], { encoding: 'utf8', timeout: 5000 });
  return JSON.parse(output);
}

// A long generated WAV keeps the real paced mesh response active during seeks.
function radioTone(seconds = 180, rate = 22050, channels = 1): Buffer {
  const samples = rate * seconds;
  const blockAlign = channels * 2;
  const dataBytes = samples * blockAlign;
  const wave = Buffer.alloc(44 + dataBytes);
  wave.write('RIFF', 0);
  wave.writeUInt32LE(wave.length - 8, 4);
  wave.write('WAVEfmt ', 8);
  wave.writeUInt32LE(16, 16);
  wave.writeUInt16LE(1, 20);
  wave.writeUInt16LE(channels, 22);
  wave.writeUInt32LE(rate, 24);
  wave.writeUInt32LE(rate * blockAlign, 28);
  wave.writeUInt16LE(blockAlign, 32);
  wave.writeUInt16LE(16, 34);
  wave.write('data', 36);
  wave.writeUInt32LE(dataBytes, 40);
  for (let index = 0; index < samples; index++) {
    const value = Math.round(Math.sin(index * 2 * Math.PI * 440 / rate) * 1600);
    for (let channel = 0; channel < channels; channel++) {
      wave.writeInt16LE(value, 44 + (index * channels + channel) * 2);
    }
  }
  return wave;
}

test.describe('listed radio between isolated nodes', () => {
  test.use({ serviceWorkers: 'block' });
  test.setTimeout(120_000);
  let harness: MultiPeerHarness;
  const activeTcpProxies: LatencyTcpProxy[] = [];
  const transientRadioNodeNames: string[] = [];

  test.beforeAll(async () => {
    harness = new MultiPeerHarness();
    await harness.startNode('A', [], { noConnect: true, radioMesh: true });
    await harness.startNode('B', [], { noConnect: true, radioMesh: true });
    await fs.writeFile(path.join(harness.getNode('A').getAppDir(), 'downloads', 'Radio network tone.wav'), radioTone());
    await fs.writeFile(path.join(harness.getNode('A').getAppDir(), 'downloads', 'Radio replacement tone.wav'), radioTone());
    await fs.writeFile(path.join(harness.getNode('B').getAppDir(), 'downloads', 'Reverse radio tone.wav'), radioTone(5));
  });

  test.afterAll(async () => {
    if (harness) await harness.stopAll();
  });

  test.afterEach(async () => {
    const proxies = activeTcpProxies.splice(0);
    const nodeNames = transientRadioNodeNames.splice(0);
    const results = await Promise.allSettled([
      ...proxies.map((proxy) => proxy.close()),
      ...nodeNames.map((name) => harness.stopNode(name)),
    ]);
    const failures = results.filter((result): result is PromiseRejectedResult => result.status === 'rejected');
    if (failures.length) throw new AggregateError(failures.map((result) => result.reason), 'Radio network fixture cleanup failed');
  });

  test('plays and seeks the real host snapshot through the listener gateway', async ({ page, request }) => {
    const host = harness.getNode('A');
    const listener = harness.getNode('B');
    const hostSession = await request.post(`${host.apiUrl}/api/v0/session`, { data: { username: host.nodeCfg.username, password: host.nodeCfg.password } });
    expect(hostSession.ok()).toBe(true);
    const hostToken = (await hostSession.json()).token;
    const listenerSession = await request.post(`${listener.apiUrl}/api/v0/session`, { data: { username: listener.nodeCfg.username, password: listener.nodeCfg.password } });
    expect(listenerSession.ok()).toBe(true);
    const listenerToken = (await listenerSession.json()).token;
    const hostHeaders = { Authorization: `Bearer ${hostToken}` };
    const listenerHeaders = { Authorization: `Bearer ${listenerToken}` };

    const connection = await request.post(`${listener.apiUrl}/api/v0/overlay/connect`, {
      headers: listenerHeaders, data: { address: '127.0.0.1', port: host.getOverlayPort() },
    });
    expect(await connection.text()).toContain('"connected":true');
    for (const [node, headers] of [[host, hostHeaders], [listener, listenerHeaders]] as const) {
      const status = await request.get(`${node.apiUrl}/api/v0/dht/status`, { headers });
      expect(status.ok()).toBe(true);
      const meshStatus = await status.json();
      expect(meshStatus).toMatchObject({ lanOnly: true, isDhtRunning: false, dhtNodeCount: 0 });
      expect(meshStatus.activeMeshConnections).toBeGreaterThanOrEqual(1);
      const startup = await fs.readFile(path.join(node.getAppDir(), 'artifacts', 'stdout.log'), 'utf8');
      expect(startup).toContain('LAN-only mesh: public DHT engine, bootstrap, saved nodes, announcements and discovery are disabled');
      expect(startup).not.toMatch(/DHT engine started|DHT bootstrapped successfully|Announced overlay port .* to DHT/);
    }

    const library = await request.get(`${host.apiUrl}/api/v0/library/items/browser?query=Radio%20network%20tone&kinds=Audio`, { headers: hostHeaders });
    expect(library.ok()).toBe(true);
    const item = (await library.json()).files[0];
    expect(item.contentId).toBeTruthy();
    const radioPod = await createRadioRoom(request, host.apiUrl, hostHeaders, 'Network radio room');
    const publish = await request.post(`${host.apiUrl}/api/v0/listening-party/${radioPod}/music`, {
      headers: hostHeaders,
      data: { partyId: 'network-radio', action: 'play', contentId: item.contentId, title: 'Radio network tone', listed: true, allowMeshStreaming: true, positionSeconds: 0 },
    });
    expect(publish.ok(), await publish.text()).toBe(true);
    const directory = await request.get(`${host.apiUrl}/api/v0/listening-party`, { headers: hostHeaders });
    const parties = await directory.json();
    expect(parties[0].transportUsername).toBe('nodeA');

    const remoteDirectory = await request.get(`${listener.apiUrl}/api/v0/listening-party`, { headers: listenerHeaders });
    expect(remoteDirectory.ok()).toBe(true);
    expect((await remoteDirectory.json()).some((party: { partyId: string }) => party.partyId === 'network-radio')).toBe(true);

    await page.addInitScript(() => localStorage.setItem('slskdn.player.collapsed', 'false'));
    const statuses: number[] = [];
    page.on('response', (response) => {
      if (response.url().includes('/api/v0/mesh-streams/')) {
        statuses.push(response.status());
        console.log('Radio HTTP response', response.status(), response.request().headers().range || 'full');
      }
    });
    await login(page, listener.nodeCfg);
    await page.getByRole('button', { name: 'Show player tools', exact: true }).click();
    await page.getByTestId('player-open-listed-radio').click();
    await page.getByRole('button', { name: 'Play Radio network tone from listed radio' }).click();
    await expect.poll(() => audioElements(page).evaluateAll((elements) => (elements as HTMLAudioElement[]).some((audio) => !audio.paused && audio.currentTime > 1))).toBe(true);
    const seek = page.getByLabel('Seek playback', { exact: true });
    const bounds = await seek.boundingBox();
    expect(bounds).not.toBeNull();
    const replacementResponse = page.waitForResponse((response) => response.url().includes('/api/v0/mesh-streams/') && response.request().headers().range !== 'bytes=0-');
    await seek.click({ position: { x: bounds!.width * 0.88, y: bounds!.height / 2 } });
    expect((await replacementResponse).status()).toBe(206);
    await expect.poll(() => audioElements(page).evaluateAll((elements) => Math.max(...(elements as HTMLAudioElement[]).map((audio) => audio.currentTime)))).toBeGreaterThan(150);
    await expect.poll(() => audioElements(page).evaluateAll((elements) => (elements as HTMLAudioElement[]).some((audio) => !audio.paused && !audio.seeking && audio.readyState >= 2 && audio.currentTime > 150))).toBe(true);
    const resumedAt = await audioElements(page).evaluateAll((elements) => Math.max(...(elements as HTMLAudioElement[]).map((audio) => audio.currentTime)));
    await expect.poll(() => audioElements(page).evaluateAll((elements) => Math.max(...(elements as HTMLAudioElement[]).map((audio) => audio.currentTime)))).toBeGreaterThan(resumedAt + 1);
    expect(statuses.filter((status) => status === 206).length).toBeGreaterThanOrEqual(2);
    expect(statuses).not.toContain(429);
    expect(statuses).not.toContain(500);
    const listenerTraffic = trafficTotals(listener.getAppDir());
    const hostTraffic = trafficTotals(host.getAppDir());
    expect(listenerTraffic[1]).toBeGreaterThan(0);
    expect(hostTraffic[0]).toBeGreaterThanOrEqual(listenerTraffic[1]);
    expect(hostTraffic[1]).toBe(0);
    expect(listenerTraffic[0]).toBe(0);

    // A new ticket evaluates current policy; seeks on the admitted ticket
    // retain their admission and must continue to work above.
    const freshTicket = await request.post(`${listener.apiUrl}/api/v0/listed-radio/network-radio/tickets`, {
      headers: listenerHeaders, data: { contentId: item.contentId },
    });
    expect(freshTicket.status()).toBe(429);
    expect((await freshTicket.json()).code).toBe('radio_fairness_limited');

    const revoke = await request.post(`${host.apiUrl}/api/v0/listening-party/${radioPod}/music`, {
      headers: hostHeaders,
      data: { partyId: 'network-radio', action: 'play', contentId: item.contentId, title: 'Radio network tone', listed: true, allowMeshStreaming: false, positionSeconds: 0 },
    });
    expect(revoke.ok()).toBe(true);
    await seek.click({ position: { x: bounds!.width * 0.35, y: bounds!.height / 2 } });
    await page.getByRole('button', { name: 'Retry radio playback', exact: true }).click();
    const snapshotError = 'The radio host could not provide this snapshot. Retry or refresh listed radio.';
    await expect(page.locator('.player-now-playing .ui.mini.negative.message')).toHaveText(snapshotError);
    await expect(page.getByTestId('player-playback-announcement')).toContainText(snapshotError);
    expect(statuses).not.toContain(500);
    await page.getByTestId('player-open-listed-radio').click();
    await page.getByRole('button', { name: 'Refresh listed radio' }).click();
    await expect(page.getByRole('button', { name: 'Play Radio network tone from listed radio' })).toBeDisabled();

    const remotePartyIds = async () => {
      const response = await request.get(`${listener.apiUrl}/api/v0/listening-party?refresh=true`, { headers: listenerHeaders });
      expect(response.ok()).toBe(true);
      return (await response.json()).map((party: { partyId: string }) => party.partyId).sort();
    };
    const unlist = await request.post(`${host.apiUrl}/api/v0/listening-party/${radioPod}/music`, {
      headers: hostHeaders,
      data: { partyId: 'network-radio', action: 'play', contentId: item.contentId, listed: false },
    });
    expect(unlist.ok(), await unlist.text()).toBe(true);
    await expect.poll(remotePartyIds, { intervals: [500, 1000, 2000] }).toEqual([]);
    const relist = await request.post(`${host.apiUrl}/api/v0/listening-party/${radioPod}/music`, {
      headers: hostHeaders,
      data: { partyId: 'network-radio', action: 'play', contentId: item.contentId, listed: true },
    });
    expect(relist.ok(), await relist.text()).toBe(true);
    await expect.poll(remotePartyIds, { intervals: [500, 1000, 2000] }).toEqual(['network-radio']);
    const replacement = await request.post(`${host.apiUrl}/api/v0/listening-party/${radioPod}/music`, {
      headers: hostHeaders,
      data: { partyId: 'network-radio-replacement', action: 'play', contentId: item.contentId, listed: true },
    });
    expect(replacement.ok(), await replacement.text()).toBe(true);
    await expect.poll(remotePartyIds, { intervals: [500, 1000, 2000] }).toEqual(['network-radio-replacement']);
    const stopReplacement = await request.post(`${host.apiUrl}/api/v0/listening-party/${radioPod}/music`, {
      headers: hostHeaders, data: { action: 'stop' },
    });
    expect(stopReplacement.ok(), await stopReplacement.text()).toBe(true);
    await expect.poll(remotePartyIds, { intervals: [500, 1000, 2000] }).toEqual([]);

    // The original host has only the inbound TLS link. Its directory must still
    // learn a publication sent in the opposite direction without another connect.
    const reverseLibrary = await request.get(`${listener.apiUrl}/api/v0/library/items/browser?query=Reverse%20radio%20tone&kinds=Audio`, { headers: listenerHeaders });
    expect(reverseLibrary.ok()).toBe(true);
    const reverseItem = (await reverseLibrary.json()).files[0];
    expect(reverseItem.contentId).toBeTruthy();
    const reversePod = await createRadioRoom(request, listener.apiUrl, listenerHeaders, 'Reverse radio room');
    const reversePublish = await request.post(`${listener.apiUrl}/api/v0/listening-party/${reversePod}/music`, {
      headers: listenerHeaders,
      data: { partyId: 'reverse-radio', action: 'play', contentId: reverseItem.contentId, title: 'Reverse radio tone', listed: true, allowMeshStreaming: false, positionSeconds: 0 },
    });
    expect(reversePublish.ok(), await reversePublish.text()).toBe(true);
    const hostRefresh = await request.get(`${host.apiUrl}/api/v0/listening-party?refresh=true`, { headers: hostHeaders });
    expect(hostRefresh.ok()).toBe(true);
    expect((await hostRefresh.json()).some((party: { partyId: string; transportUsername: string }) => party.partyId === 'reverse-radio' && party.transportUsername === 'nodeB')).toBe(true);

    const networkSnapshot = page.waitForResponse((response) => response.url().includes('/api/v0/network/stats') && response.status() === 200);
    await page.goto(`${listener.nodeCfg.baseUrl}/system/network`);
    expect((await (await networkSnapshot).json()).dht).toMatchObject({ lanOnly: true, isDhtRunning: false, dhtNodeCount: 0 });
    const health = page.locator('.network-health-panel');
    await expect(health.locator('.label').filter({ hasText: /^Mesh\s*1$/ })).toBeVisible();
    await expect(health.getByText('DHT: DHT rendezvous not running')).toHaveCount(0);



  });

  test('sustains 96 kHz stereo listed-radio playback and seeks beyond read-ahead on the loopback mesh @player-radio-high-rate', async ({ page, request }) => {
    test.setTimeout(360_000);
    const host = await harness.startNode('J', [], { noConnect: true, radioMesh: true });
    transientRadioNodeNames.push('J');
    const listener = await harness.startNode('K', [], { noConnect: true, radioMesh: true });
    transientRadioNodeNames.push('K');
    const title = 'High-rate radio tone';
    await fs.writeFile(path.join(host.getAppDir(), 'downloads', `${title}.wav`), radioTone(390, 96_000, 2));

    const [hostSession, listenerSession] = await Promise.all([
      request.post(`${host.apiUrl}/api/v0/session`, { data: { username: host.nodeCfg.username, password: host.nodeCfg.password } }),
      request.post(`${listener.apiUrl}/api/v0/session`, { data: { username: listener.nodeCfg.username, password: listener.nodeCfg.password } }),
    ]);
    expect(hostSession.ok()).toBe(true);
    expect(listenerSession.ok()).toBe(true);
    const hostHeaders = { Authorization: `Bearer ${(await hostSession.json()).token}` };
    const listenerHeaders = { Authorization: `Bearer ${(await listenerSession.json()).token}` };
    const connection = await request.post(`${listener.apiUrl}/api/v0/overlay/connect`, {
      headers: listenerHeaders,
      data: { address: '127.0.0.1', port: host.getOverlayPort() },
    });
    expect(connection.ok(), await connection.text()).toBe(true);

    const findHighRateItem = async () => {
      const response = await request.get(
        `${host.apiUrl}/api/v0/library/items/browser?query=${encodeURIComponent(title)}&kinds=Audio`,
        { headers: hostHeaders },
      );
      if (!response.ok()) return null;
      return ((await response.json()).files as Array<{ contentId: string; fileName: string }>)
        .find((file) => file.fileName === `${title}.wav`) ?? null;
    };
    await expect.poll(async () => (await findHighRateItem())?.contentId).toBeTruthy();
    const radioItem = await findHighRateItem();
    expect(radioItem?.contentId).toBeTruthy();

    const radioPod = await createRadioRoom(request, host.apiUrl, hostHeaders, 'High-rate radio room');
    const partyId = `high-rate-${randomUUID()}`;
    const publish = await request.post(`${host.apiUrl}/api/v0/listening-party/${radioPod}/music`, {
      headers: hostHeaders,
      data: {
        partyId, action: 'play', contentId: radioItem!.contentId, title,
        listed: true, allowMeshStreaming: true, positionSeconds: 0,
      },
    });
    expect(publish.ok(), await publish.text()).toBe(true);
    await expect.poll(async () => {
      const directory = await request.get(`${listener.apiUrl}/api/v0/listening-party?refresh=true`, { headers: listenerHeaders });
      if (!directory.ok()) return null;
      return (await directory.json()).find((party: { partyId: string }) => party.partyId === partyId) ?? null;
    }, { timeout: 30_000 }).toMatchObject({ contentId: radioItem!.contentId, title });

    await page.addInitScript(() => localStorage.setItem('slskdn.player.collapsed', 'false'));
    let radioTicketRequests = 0;
    page.on('request', (requestEvent) => {
      if (requestEvent.url().includes(`/api/v0/listed-radio/${partyId}/tickets`)) radioTicketRequests += 1;
    });
    const browserDebug = await page.context().newCDPSession(page);
    await browserDebug.send('Network.enable');
    await browserDebug.send('Network.emulateNetworkConditionsByRule', {
      matchedNetworkConditions: [{
        urlPattern: new URL('/api/v0/mesh-streams/*', listener.nodeCfg.baseUrl).href,
        latency: 80,
        downloadThroughput: 512 * 1024,
        uploadThroughput: 128 * 1024,
      }],
    });
    const meshStatuses: number[] = [];
    page.on('response', (response) => {
      if (response.url().includes('/api/v0/mesh-streams/')) meshStatuses.push(response.status());
    });
    await login(page, listener.nodeCfg);
    await page.getByRole('button', { name: 'Show player tools', exact: true }).click();
    await page.getByTestId('player-open-listed-radio').click();
    const playRadio = page.getByRole('button', { name: `Play ${title} from listed radio`, exact: true });
    await expect(playRadio).toBeVisible();
    const radioTicketResponse = page.waitForResponse((response) =>
      response.url().includes(`/api/v0/listed-radio/${partyId}/tickets`) && response.request().method() === 'POST');
    await playRadio.click();
    const ticketResponse = await radioTicketResponse;
    expect(ticketResponse.status()).toBe(200);
    const radioTicket = await ticketResponse.json() as { expiresInSeconds: number };
    expect(radioTicket.expiresInSeconds).toBeGreaterThan(220);
    const audio = audioElements(page).first();
    await expect.poll(() => audio.evaluate((element) =>
      element instanceof HTMLAudioElement && !element.paused && element.currentTime > 1),
    { timeout: 30_000 }).toBe(true);

    const currentTime = () => audio.evaluate((element) => {
      if (!(element instanceof HTMLAudioElement)) throw new Error('The listed-radio audio element is unavailable.');
      return { paused: element.paused, ended: element.ended, currentTime: element.currentTime };
    });
    const initialTime = (await currentTime()).currentTime;
    // 96 kHz stereo 16-bit PCM consumes 384,000 bytes/s. The browser link is
    // capped at 512 KiB/s so the real listed-radio stream has to keep pace.
    await expect.poll(async () => (await currentTime()).currentTime, { timeout: 220_000, intervals: [1_000, 2_000] })
      .toBeGreaterThan(initialTime + 175);
    const sustainedState = await currentTime();
    expect(sustainedState.paused).toBe(false);
    expect(sustainedState.ended).toBe(false);

    const seek = page.getByLabel('Seek playback', { exact: true });
    const seekBounds = await seek.boundingBox();
    expect(seekBounds).not.toBeNull();
    const highRateSeekResponse = page.waitForResponse((response) =>
      response.url().includes('/api/v0/mesh-streams/') &&
      response.request().headers().range !== undefined,
    { timeout: 30_000 });
    await seek.click({ position: { x: seekBounds!.width * 0.94, y: seekBounds!.height / 2 } });
    const rangedResponse = await highRateSeekResponse;
    expect(rangedResponse.status(), `Mesh stream responses: ${meshStatuses.join(', ')}`).toBe(206);
    await expect.poll(async () => {
      const state = await currentTime();
      return !state.paused && !state.ended && state.currentTime > 355;
    }, { timeout: 20_000 }).toBe(true);
    const afterSeekTime = (await currentTime()).currentTime;
    await expect.poll(async () => (await currentTime()).currentTime, { timeout: 10_000 }).toBeGreaterThan(afterSeekTime + 4);
    expect(meshStatuses).toContain(206);
    expect(meshStatuses).not.toContain(429);
    expect(meshStatuses).not.toContain(500);
    expect(radioTicketRequests).toBe(1);

    const [hostTraffic, listenerTraffic] = [trafficTotals(host.getAppDir()), trafficTotals(listener.getAppDir())];
    expect(hostTraffic[0]).toBeGreaterThan(0);
    expect(listenerTraffic[1]).toBeGreaterThan(0);
    console.log(JSON.stringify({
      sampleRateHz: 96_000,
      channels: 2,
      sustainedPlaybackSeconds: sustainedState.currentTime - initialTime,
      postSeekPositionSeconds: (await currentTime()).currentTime,
      meshStatuses,
    }));
    await browserDebug.detach();
  });

  test('stops active radio when its host replaces or withdraws the snapshot', async ({ page, request }) => {
    test.setTimeout(180_000);
    const host = harness.getNode('A');
    const listener = await harness.startNode('G', [], { noConnect: true, radioMesh: true });
    transientRadioNodeNames.push('G');
    const [hostSession, listenerSession] = await Promise.all([
      request.post(`${host.apiUrl}/api/v0/session`, { data: { username: host.nodeCfg.username, password: host.nodeCfg.password } }),
      request.post(`${listener.apiUrl}/api/v0/session`, { data: { username: listener.nodeCfg.username, password: listener.nodeCfg.password } }),
    ]);
    expect(hostSession.ok()).toBe(true);
    expect(listenerSession.ok()).toBe(true);
    const hostHeaders = { Authorization: `Bearer ${(await hostSession.json()).token}` };
    const listenerHeaders = { Authorization: `Bearer ${(await listenerSession.json()).token}` };
    const connection = await request.post(`${listener.apiUrl}/api/v0/overlay/connect`, {
      headers: listenerHeaders, data: { address: '127.0.0.1', port: host.getOverlayPort() },
    });
    expect(connection.ok(), await connection.text()).toBe(true);

    const findItem = async (title: string) => {
      const response = await request.get(`${host.apiUrl}/api/v0/library/items/browser?query=${encodeURIComponent(title)}&kinds=Audio`, { headers: hostHeaders });
      expect(response.ok()).toBe(true);
      return (await response.json()).files.find((file: { fileName: string }) => file.fileName === `${title}.wav`) as { contentId: string } | undefined;
    };
    await expect.poll(async () => (await findItem('Radio network tone'))?.contentId).toBeTruthy();
    await expect.poll(async () => (await findItem('Radio replacement tone'))?.contentId).toBeTruthy();
    const initialItem = await findItem('Radio network tone');
    const replacementItem = await findItem('Radio replacement tone');
    expect(initialItem?.contentId).toBeTruthy();
    expect(replacementItem?.contentId).toBeTruthy();

    const radioPod = await createRadioRoom(request, host.apiUrl, hostHeaders, 'Active radio snapshot room');
    const partyId = `active-radio-${randomUUID()}`;
    const publish = (contentId: string, title: string, listed = true) => request.post(`${host.apiUrl}/api/v0/listening-party/${radioPod}/music`, {
      headers: hostHeaders,
      data: { partyId, action: 'play', contentId, title, listed, allowMeshStreaming: true, positionSeconds: 0 },
    });
    const initialPublication = await publish(initialItem!.contentId, 'Radio network tone');
    expect(initialPublication.ok(), await initialPublication.text()).toBe(true);
    const refreshDirectory = async () => {
      const response = await request.get(`${listener.apiUrl}/api/v0/listening-party?refresh=true`, { headers: listenerHeaders });
      expect(response.ok()).toBe(true);
      return (await response.json()).find((party: { partyId: string }) => party.partyId === partyId) ?? null;
    };
    await expect.poll(refreshDirectory).toMatchObject({ contentId: initialItem!.contentId, title: 'Radio network tone' });

    await page.addInitScript(() => localStorage.setItem('slskdn.player.collapsed', 'false'));
    await login(page, listener.nodeCfg);
    await page.getByRole('button', { name: 'Show player tools', exact: true }).click();
    await page.getByTestId('player-open-listed-radio').click();
    const initialPlay = page.getByRole('button', { name: 'Play Radio network tone from listed radio', exact: true });
    await expect(initialPlay).toBeVisible();
    const initialResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v0/mesh-streams/') && response.status() === 206);
    const initialRequestPromise = page.waitForEvent('request', (current) => current.url().includes('/api/v0/mesh-streams/'));
    await initialPlay.click();
    const initialRequest = await initialRequestPromise;
    expect((await initialResponsePromise).request()).toBe(initialRequest);
    await expect.poll(() => audioElements(page).evaluateAll((elements) =>
      (elements as HTMLAudioElement[]).some((audio) => !audio.paused && audio.currentTime > 1))).toBe(true);
    const initialStreamFailure = page.waitForEvent('requestfailed', (current) => current === initialRequest);

    const replacementPublication = await publish(replacementItem!.contentId, 'Radio replacement tone');
    expect(replacementPublication.ok(), await replacementPublication.text()).toBe(true);
    expect((await initialStreamFailure).failure()).not.toBeNull();
    const streamStoppedCopy = 'The listed radio stream stopped or changed. Retry playback or refresh listed radio.';
    await expect(page.locator('.player-now-playing .ui.mini.negative.message')).toHaveText(streamStoppedCopy);

    const replacementListener = await harness.startNode('H', [], { noConnect: true, radioMesh: true });
    transientRadioNodeNames.push('H');
    const replacementListenerSession = await request.post(`${replacementListener.apiUrl}/api/v0/session`, {
      data: { username: replacementListener.nodeCfg.username, password: replacementListener.nodeCfg.password },
    });
    expect(replacementListenerSession.ok()).toBe(true);
    const replacementListenerHeaders = { Authorization: `Bearer ${(await replacementListenerSession.json()).token}` };
    const replacementConnection = await request.post(`${replacementListener.apiUrl}/api/v0/overlay/connect`, {
      headers: replacementListenerHeaders,
      data: { address: '127.0.0.1', port: host.getOverlayPort() },
    });
    expect(replacementConnection.ok(), await replacementConnection.text()).toBe(true);
    const replacementDirectory = await request.get(`${replacementListener.apiUrl}/api/v0/listening-party?refresh=true`, { headers: replacementListenerHeaders });
    expect(replacementDirectory.ok()).toBe(true);
    expect((await replacementDirectory.json()).some((party: { partyId: string; contentId: string }) =>
      party.partyId === partyId && party.contentId === replacementItem!.contentId)).toBe(true);

    await page.goto(replacementListener.nodeCfg.baseUrl);
    await login(page, replacementListener.nodeCfg);
    await page.getByRole('button', { name: 'Show player tools', exact: true }).click();
    await page.getByTestId('player-open-listed-radio').click();
    await expect(page.getByRole('button', { name: 'Play Radio replacement tone from listed radio', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Play Radio network tone from listed radio', exact: true })).toHaveCount(0);
    const replacementPlay = page.getByRole('button', { name: 'Play Radio replacement tone from listed radio', exact: true });
    const replacementResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v0/mesh-streams/') && response.status() === 206);
    const replacementRequestPromise = page.waitForEvent('request', (current) => current.url().includes('/api/v0/mesh-streams/'));
    await replacementPlay.click();
    const replacementRequest = await replacementRequestPromise;
    expect((await replacementResponsePromise).request()).toBe(replacementRequest);
    await expect.poll(() => audioElements(page).evaluateAll((elements) =>
      (elements as HTMLAudioElement[]).some((audio) => !audio.paused && audio.currentTime > 1))).toBe(true);
    const replacementStreamFailure = page.waitForEvent('requestfailed', (current) => current === replacementRequest);

    const withdrawal = await publish(replacementItem!.contentId, 'Radio replacement tone', false);
    expect(withdrawal.ok(), await withdrawal.text()).toBe(true);
    expect((await replacementStreamFailure).failure()).not.toBeNull();
    await expect(page.locator('.player-now-playing .ui.mini.negative.message')).toHaveText(streamStoppedCopy);
    await page.getByTestId('player-open-listed-radio').click();
    await page.getByRole('button', { name: 'Refresh listed radio' }).click();
    await expect(page.getByRole('button', { name: 'Play Radio replacement tone from listed radio', exact: true })).toHaveCount(0);
  });

  test('recovers listed radio on constrained browser and latency-shaped mesh links', async ({ page, request }) => {
    test.setTimeout(180_000);
    const host = harness.getNode('A');
    await harness.startNode('C', [], { noConnect: true, radioMesh: true });
    const listener = harness.getNode('C');
    const title = `Constrained radio ${randomUUID().slice(0, 8)}`;
    const replacementTitle = `${title} replacement`;
    const initialFile = `${title}.wav`;
    const replacementFile = `${replacementTitle}.wav`;
    await Promise.all([
      fs.writeFile(path.join(host.getAppDir(), 'downloads', initialFile), radioTone()),
      fs.writeFile(path.join(host.getAppDir(), 'downloads', replacementFile), radioTone()),
    ]);

    const [hostSession, listenerSession] = await Promise.all([
      request.post(`${host.apiUrl}/api/v0/session`, { data: { username: host.nodeCfg.username, password: host.nodeCfg.password } }),
      request.post(`${listener.apiUrl}/api/v0/session`, { data: { username: listener.nodeCfg.username, password: listener.nodeCfg.password } }),
    ]);
    expect(hostSession.ok()).toBe(true);
    expect(listenerSession.ok()).toBe(true);
    const hostHeaders = { Authorization: `Bearer ${(await hostSession.json()).token}` };
    const listenerHeaders = { Authorization: `Bearer ${(await listenerSession.json()).token}` };
    const meshStatusResponse = await request.get(`${listener.apiUrl}/api/v0/dht/status`, { headers: listenerHeaders });
    expect(meshStatusResponse.ok()).toBe(true);
    expect((await meshStatusResponse.json()).activeMeshConnections).toBe(0);
    // Apply deterministic 45–75 ms per-chunk delays in both directions to add
    // latency variation on the real mesh connection. This is not a WAN model.
    const meshProxy = new LatencyTcpProxy(host.getOverlayPort(), 60, 15);
    await meshProxy.start();
    activeTcpProxies.push(meshProxy);
    const connection = await request.post(`${listener.apiUrl}/api/v0/overlay/connect`, {
      headers: listenerHeaders,
      data: { address: '127.0.0.1', port: meshProxy.port },
    });
    expect(connection.ok(), await connection.text()).toBe(true);
    expect((await connection.json()).activeConnections).toBeGreaterThan(0);

    const libraryUrl = `${host.apiUrl}/api/v0/library/items/browser?query=${encodeURIComponent(title)}&kinds=Audio`;
    await expect.poll(async () => {
      const response = await request.get(libraryUrl, { headers: hostHeaders });
      if (!response.ok()) return [];
      return (await response.json()).files.map((file: { fileName: string }) => file.fileName).sort();
    }, { timeout: 30_000 }).toEqual([initialFile, replacementFile].sort());
    const library = await request.get(libraryUrl, { headers: hostHeaders });
    expect(library.ok()).toBe(true);
    const files = (await library.json()).files as Array<{ contentId: string; fileName: string }>;
    const initialItem = files.find((file) => file.fileName === initialFile);
    const replacementItem = files.find((file) => file.fileName === replacementFile);
    expect(initialItem?.contentId).toBeTruthy();
    expect(replacementItem?.contentId).toBeTruthy();
    const podId = await createRadioRoom(request, host.apiUrl, hostHeaders, 'Constrained radio replacement room');
    const partyId = `constrained-${randomUUID()}`;
    const publish = (contentId: string, trackTitle: string) => request.post(`${host.apiUrl}/api/v0/listening-party/${podId}/music`, {
      headers: hostHeaders,
      data: { partyId, action: 'play', contentId, title: trackTitle, listed: true, allowMeshStreaming: true, positionSeconds: 0 },
    });
    const firstPublication = await publish(initialItem!.contentId, title);
    expect(firstPublication.ok(), await firstPublication.text()).toBe(true);
    const refreshListenerDirectory = async () => {
      const response = await request.get(`${listener.apiUrl}/api/v0/listening-party?refresh=true`, { headers: listenerHeaders });
      expect(response.ok()).toBe(true);
      return (await response.json()).find((party: { partyId: string }) => party.partyId === partyId) ?? null;
    };
    await expect.poll(refreshListenerDirectory, { timeout: 30_000 }).toMatchObject({ contentId: initialItem!.contentId, title });

    await page.addInitScript(() => localStorage.setItem('slskdn.player.collapsed', 'false'));
    await login(page, listener.nodeCfg);
    await page.getByRole('button', { name: 'Show player tools', exact: true }).click();
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Network.enable');
    const streamRequests = new Set<string>();
    let slowProfileBytes = 0;
    let measureSlowProfile = false;
    cdp.on('Network.requestWillBeSent', ({ requestId, request: networkRequest }) => {
      if (networkRequest.url.includes('/api/v0/mesh-streams/')) streamRequests.add(requestId);
    });
    cdp.on('Network.dataReceived', ({ requestId, dataLength }) => {
      if (measureSlowProfile && streamRequests.has(requestId)) slowProfileBytes += dataLength;
    });
    const streamPattern = new URL('/api/v0/mesh-streams/*', listener.nodeCfg.baseUrl).href;
    const setRadioNetwork = (downloadThroughput: number, latency: number) => cdp.send('Network.emulateNetworkConditionsByRule', {
      matchedNetworkConditions: [{
        urlPattern: streamPattern,
        latency,
        downloadThroughput,
        uploadThroughput: 32 * 1024,
      }],
    });

    try {
      const slowStartedAt = Date.now();
      await setRadioNetwork(24 * 1024, 450);
      measureSlowProfile = true;
      await page.getByTestId('player-open-listed-radio').click();
      await expect(page.getByRole('button', { name: `Play ${title} from listed radio`, exact: true })).toBeVisible();
      const firstStream = page.waitForResponse((response) => response.url().includes('/api/v0/mesh-streams/') && response.status() < 300, { timeout: 30_000 });
      await page.getByRole('button', { name: `Play ${title} from listed radio`, exact: true }).click();
      expect((await firstStream).status()).toBe(206);
      await expect.poll(() => audioElements(page).evaluateAll((elements) =>
        (elements as HTMLAudioElement[]).some((audio) => !audio.paused && audio.currentTime > 1)), { timeout: 45_000 }).toBe(true);
      await page.waitForTimeout(10_000);
      const limitedDurationSeconds = (Date.now() - slowStartedAt) / 1000;
      const limitedBytesPerSecond = slowProfileBytes / limitedDurationSeconds;
      expect(slowProfileBytes).toBeGreaterThan(0);
      expect(limitedBytesPerSecond).toBeLessThan(36 * 1024);
      await expect(page.getByRole('button', { name: 'Retry radio playback', exact: true })).toBeVisible({ timeout: 15_000 });
      measureSlowProfile = false;

      await setRadioNetwork(128 * 1024, 120);
      const seek = page.getByLabel('Seek playback', { exact: true });
      const bounds = await seek.boundingBox();
      expect(bounds).not.toBeNull();
      const mediaBuffer = await audioElements(page).evaluateAll((elements) => {
        const active = (elements as HTMLAudioElement[]).find((audio) => !audio.paused);
        if (!active) return { currentTime: 0, duration: 0, bufferedEnd: 0 };
        const bufferedEnd = active.buffered.length > 0 ? active.buffered.end(active.buffered.length - 1) : 0;
        return { currentTime: active.currentTime, duration: active.duration, bufferedEnd };
      });
      expect(mediaBuffer.duration).toBeGreaterThan(1);
      expect(mediaBuffer.bufferedEnd).toBeLessThan(mediaBuffer.duration - 1);
      const seekTarget = Math.min(mediaBuffer.duration - 1, Math.max(mediaBuffer.bufferedEnd + 10, mediaBuffer.currentTime + 30));
      expect(seekTarget).toBeGreaterThan(mediaBuffer.bufferedEnd);
      const recoveredRange = page.waitForResponse((response) =>
        response.url().includes('/api/v0/mesh-streams/') && response.status() === 206 && Boolean(response.request().headers().range), { timeout: 30_000 });
      await seek.click({ position: { x: bounds!.width * (seekTarget / mediaBuffer.duration), y: bounds!.height / 2 } });
      expect((await recoveredRange).status()).toBe(206);
      await expect.poll(() => audioElements(page).evaluateAll((elements, target) =>
        (elements as HTMLAudioElement[]).some((audio) => !audio.paused && !audio.seeking && audio.readyState >= 2 && audio.currentTime > target - 1), seekTarget), { timeout: 45_000 }).toBe(true);
      const recoveredAt = await audioElements(page).evaluateAll((elements) => Math.max(...(elements as HTMLAudioElement[]).map((audio) => audio.currentTime)));
      await expect.poll(() => audioElements(page).evaluateAll((elements) => Math.max(...(elements as HTMLAudioElement[]).map((audio) => audio.currentTime)))).toBeGreaterThan(recoveredAt + 1);

      expect(meshProxy.traffic.hostToListener).toBeGreaterThan(0);
      expect(meshProxy.traffic.listenerToHost).toBeGreaterThan(0);
      for (const direction of Object.values(meshProxy.observedDelays)) {
        expect(direction.chunks).toBeGreaterThan(2);
        expect(direction.minScheduledMs).toBe(45);
        expect(direction.maxScheduledMs).toBe(75);
        expect(direction.maxObservedMs! - direction.minObservedMs!).toBeGreaterThanOrEqual(20);
      }
      await expect(page.locator('.player-now-playing .player-title')).toHaveText(title);
      await meshProxy.close();
      await harness.stopNode('C');
      await harness.startNode('D', [], { noConnect: true, radioMesh: true });
      const replacementListener = harness.getNode('D');
      const replacementSession = await request.post(`${replacementListener.apiUrl}/api/v0/session`, {
        data: { username: replacementListener.nodeCfg.username, password: replacementListener.nodeCfg.password },
      });
      expect(replacementSession.ok()).toBe(true);
      const replacementHeaders = { Authorization: `Bearer ${(await replacementSession.json()).token}` };
      const replacementConnection = await request.post(`${replacementListener.apiUrl}/api/v0/overlay/connect`, {
        headers: replacementHeaders,
        data: { address: '127.0.0.1', port: host.getOverlayPort() },
      });
      expect(replacementConnection.ok(), await replacementConnection.text()).toBe(true);
      expect((await replacementConnection.json()).activeConnections).toBeGreaterThan(0);
      await expect.poll(async () => {
        const response = await request.get(`${replacementListener.apiUrl}/api/v0/listening-party?refresh=true`, { headers: replacementHeaders });
        if (!response.ok()) return null;
        return (await response.json()).find((party: { partyId: string }) => party.partyId === partyId) ?? null;
      }, { timeout: 30_000 }).toMatchObject({ contentId: initialItem!.contentId, title });

      await page.goto(replacementListener.nodeCfg.baseUrl);
      await login(page, replacementListener.nodeCfg);
      await page.getByRole('button', { name: 'Show player tools', exact: true }).click();
      await page.getByTestId('player-open-listed-radio').click();
      await expect(page.getByRole('button', { name: `Play ${title} from listed radio`, exact: true })).toBeVisible();
      const updatePublication = await publish(replacementItem!.contentId, replacementTitle);
      expect(updatePublication.ok(), await updatePublication.text()).toBe(true);
      const currentHostSnapshot = await request.get(`${host.apiUrl}/api/v0/listening-party/${podId}/music`, { headers: hostHeaders });
      expect(currentHostSnapshot.ok()).toBe(true);
      expect(await currentHostSnapshot.json()).toMatchObject({ partyId, contentId: replacementItem!.contentId, title: replacementTitle });
      await page.waitForTimeout(2100);
      await page.getByRole('button', { name: 'Refresh listed radio' }).click();
      const replacementPlay = page.getByRole('button', { name: `Play ${replacementTitle} from listed radio`, exact: true });
      await expect(replacementPlay).toBeVisible();
      await expect(page.getByRole('button', { name: `Play ${title} from listed radio`, exact: true })).toHaveCount(0);
      const staleTicket = await request.post(`${replacementListener.apiUrl}/api/v0/listed-radio/${encodeURIComponent(partyId)}/tickets`, {
        headers: replacementHeaders,
        data: { contentId: initialItem!.contentId },
      });
      expect(staleTicket.status()).toBe(404);
      const replacementStream = page.waitForResponse((response) => response.url().includes('/api/v0/mesh-streams/') && response.status() === 206, { timeout: 30_000 });
      await replacementPlay.click();
      expect((await replacementStream).status()).toBe(206);
      await expect(page.locator('.player-now-playing .player-title')).toHaveText(replacementTitle);
      await expect.poll(() => audioElements(page).evaluateAll((elements) =>
        (elements as HTMLAudioElement[]).some((audio) => !audio.paused && audio.readyState >= 2 && audio.currentTime > 1)), { timeout: 45_000 }).toBe(true);
      const replacementAt = await audioElements(page).evaluateAll((elements) => Math.max(...(elements as HTMLAudioElement[]).map((audio) => audio.currentTime)));
      await expect.poll(() => audioElements(page).evaluateAll((elements) => Math.max(...(elements as HTMLAudioElement[]).map((audio) => audio.currentTime)))).toBeGreaterThan(replacementAt + 1);
    } finally {
      measureSlowProfile = false;
      if (!page.isClosed()) await cdp.detach().catch(() => {});
    }
  });

  test('renews local radio after actual ticket expiry through manual reselection', async ({ page, request }) => {
    test.setTimeout(360_000);
    const host = harness.getNode('A');
    const session = await request.post(`${host.apiUrl}/api/v0/session`, {
      data: { username: host.nodeCfg.username, password: host.nodeCfg.password },
    });
    expect(session.ok()).toBe(true);
    const headers = { Authorization: `Bearer ${(await session.json()).token}` };
    const library = await request.get(`${host.apiUrl}/api/v0/library/items/browser?query=Radio%20network%20tone&kinds=Audio`, { headers });
    expect(library.ok()).toBe(true);
    const item = (await library.json()).files[0];
    const localPod = await createRadioRoom(request, host.apiUrl, headers, 'Local expiry room');
    const publication = await request.post(`${host.apiUrl}/api/v0/listening-party/${localPod}/music`, {
      headers,
      data: { partyId: 'local-expiry', action: 'play', contentId: item.contentId, title: 'Local expiry tone', listed: true, allowMeshStreaming: true, positionSeconds: 0 },
    });
    expect(publication.ok(), await publication.text()).toBe(true);
    await page.addInitScript(() => localStorage.setItem('slskdn.player.collapsed', 'false'));
    await login(page, host.nodeCfg);
    await page.getByRole('button', { name: 'Show player tools', exact: true }).click();
    await page.getByTestId('player-open-listed-radio').click();
    const acquisition = page.waitForResponse((response) => response.url().includes('/listed-radio/local-expiry/tickets'));
    await page.getByRole('button', { name: 'Play Local expiry tone from listed radio' }).click();
    const response = await acquisition;
    expect(response.ok()).toBe(true);
    const initial = await response.json();
    expect(initial.expiresInSeconds).toBe(120);
    const receivedAt = Date.now();
    await expect.poll(() => audioElements(page).evaluateAll((elements) => (elements as HTMLAudioElement[]).some((audio) => !audio.paused && audio.currentTime > 1))).toBe(true);
    await page.getByRole('button', { name: 'Pause local playback', exact: true }).click();
    const valid = await request.get(`${host.apiUrl}${initial.streamUrl}`, { headers: { Range: 'bytes=0-1' } });
    expect(valid.status()).toBe(206);

    // Let the production two-minute lifetime elapse. Cached browser audio does
    // not prove a ticket is valid, so inspect a new HTTP request explicitly.
    await new Promise((resolve) => setTimeout(resolve, Math.max(0, receivedAt + 122_000 - Date.now())));
    const expired = await request.get(`${host.apiUrl}${initial.streamUrl}`, { headers: { Range: 'bytes=0-1' } });
    expect(expired.status()).toBe(401);
    await page.getByTestId('player-open-listed-radio').click();
    const renewal = page.waitForResponse((result) => result.url().includes('/listed-radio/local-expiry/tickets'));
    await page.getByRole('button', { name: 'Play Local expiry tone from listed radio' }).click();
    const renewedResponse = await renewal;
    expect(renewedResponse.ok()).toBe(true);
    const renewed = await renewedResponse.json();
    expect(renewed.streamUrl).not.toBe(initial.streamUrl);
    const renewedRange = await request.get(`${host.apiUrl}${renewed.streamUrl}`, { headers: { Range: 'bytes=0-1' } });
    expect(renewedRange.status()).toBe(206);
    await expect.poll(() => audioElements(page).evaluateAll((elements) => (elements as HTMLAudioElement[]).some((audio) => !audio.paused && audio.readyState >= 2 && audio.currentTime > 120))).toBe(true);
    const resumedAt = await audioElements(page).evaluateAll((elements) => Math.max(...(elements as HTMLAudioElement[]).map((audio) => audio.currentTime)));
    await expect.poll(() => audioElements(page).evaluateAll((elements) => Math.max(...(elements as HTMLAudioElement[]).map((audio) => audio.currentTime)))).toBeGreaterThan(resumedAt + 1);
  });

  test('renews a host capability across nodes and rejects replaced-tab writes and Stop', async ({ request }) => {
    const host = await harness.startNode('E', [], { noConnect: true, radioMesh: true });
    const listener = await harness.startNode('F', [], { noConnect: true, radioMesh: true });
    await fs.writeFile(path.join(host.getAppDir(), 'downloads', 'Host capability tone.wav'), radioTone(5));
    const hostLogin = await request.post(`${host.apiUrl}/api/v0/session`, {
      data: { username: host.nodeCfg.username, password: host.nodeCfg.password },
    });
    const listenerLogin = await request.post(`${listener.apiUrl}/api/v0/session`, {
      data: { username: listener.nodeCfg.username, password: listener.nodeCfg.password },
    });
    expect(hostLogin.ok()).toBe(true);
    expect(listenerLogin.ok()).toBe(true);
    const hostHeaders = { Authorization: `Bearer ${(await hostLogin.json()).token}` };
    const listenerHeaders = { Authorization: `Bearer ${(await listenerLogin.json()).token}` };
    const overlayConnection = await request.post(`${listener.apiUrl}/api/v0/overlay/connect`, {
      headers: listenerHeaders,
      data: { address: '127.0.0.1', port: host.getOverlayPort() },
    });
    expect(overlayConnection.ok(), await overlayConnection.text()).toBe(true);
    const overlayConnectionResult = await overlayConnection.json();
    expect(overlayConnectionResult.connected).toBe(true);
    expect(overlayConnectionResult.activeConnections).toBeGreaterThanOrEqual(1);
    for (const [node, headers] of [[host, hostHeaders], [listener, listenerHeaders]] as const) {
      const status = await request.get(`${node.apiUrl}/api/v0/dht/status`, { headers });
      expect(status.ok()).toBe(true);
      const meshStatus = await status.json();
      expect(meshStatus).toMatchObject({ lanOnly: true, isDhtRunning: false, dhtNodeCount: 0 });
      expect(meshStatus.activeMeshConnections).toBeGreaterThanOrEqual(1);
    }

    const library = await request.get(`${host.apiUrl}/api/v0/library/items/browser?query=Host%20capability%20tone&kinds=Audio`, { headers: hostHeaders });
    expect(library.ok()).toBe(true);
    const item = (await library.json()).files[0];
    const podId = await createRadioRoom(request, host.apiUrl, hostHeaders, 'Host-session fencing room');
    const roomUrl = `${host.apiUrl}/api/v0/listening-party/${podId}/music`;
    const firstSession = randomUUID();
    const replacementSession = randomUUID();
    const firstStart = await request.post(roomUrl, {
      headers: {
        ...hostHeaders,
        'X-Listen-Along-Host-Session': firstSession,
        'X-Listen-Along-Start-Host-Session': 'true',
      },
      data: { action: 'play', contentId: item.contentId, title: 'First browser', listed: true, allowMeshStreaming: true },
    });
    expect(firstStart.ok(), await firstStart.text()).toBe(true);
    const first = await firstStart.json();
    const hostDirectory = async () => {
      const response = await request.get(`${host.apiUrl}/api/v0/listening-party?refresh=true`, { headers: hostHeaders });
      expect(response.ok()).toBe(true);
      return response.json();
    };
    const firstAnnouncement = (await hostDirectory()).find((party: { partyId: string }) => party.partyId === first.partyId);
    expect(firstAnnouncement?.streamTicket).toBeTruthy();

    const firstRenewal = await request.post(`${host.apiUrl}/api/v0/listening-party/${podId}/music/renew`, {
      headers: { ...hostHeaders, 'X-Listen-Along-Host-Session': firstSession },
      data: { partyId: first.partyId },
    });
    expect(firstRenewal.status()).toBe(204);
    const renewedAnnouncement = (await hostDirectory()).find((party: { partyId: string }) => party.partyId === first.partyId);
    expect(renewedAnnouncement?.streamTicket).toBeTruthy();
    expect(renewedAnnouncement.streamTicket).not.toBe(firstAnnouncement.streamTicket);

    const replacementStart = await request.post(roomUrl, {
      headers: {
        ...hostHeaders,
        'X-Listen-Along-Host-Session': replacementSession,
        'X-Listen-Along-Start-Host-Session': 'true',
      },
      data: { action: 'play', contentId: item.contentId, title: 'Replacement browser', listed: true, allowMeshStreaming: true },
    });
    expect(replacementStart.ok(), await replacementStart.text()).toBe(true);
    const replacement = await replacementStart.json();
    expect(replacement.partyId).not.toBe(first.partyId);

    const staleRenewal = await request.post(`${host.apiUrl}/api/v0/listening-party/${podId}/music/renew`, {
      headers: { ...hostHeaders, 'X-Listen-Along-Host-Session': firstSession },
      data: { partyId: first.partyId },
    });
    expect(staleRenewal.status()).toBe(409);
    expect((await staleRenewal.json()).code).toBe('host_session_replaced');
    for (const action of ['pause', 'stop']) {
      const staleWrite = await request.post(roomUrl, {
        headers: { ...hostHeaders, 'X-Listen-Along-Host-Session': firstSession },
        data: { partyId: first.partyId, action, contentId: item.contentId, listed: true, allowMeshStreaming: true },
      });
      expect(staleWrite.status(), `${action} from replaced host`).toBe(409);
      expect((await staleWrite.json()).code).toBe('host_session_replaced');
    }

    const activeRoom = await request.get(`${host.apiUrl}/api/v0/listening-party/${podId}/music`, { headers: hostHeaders });
    expect(activeRoom.ok()).toBe(true);
    expect((await activeRoom.json())).toMatchObject({ partyId: replacement.partyId, title: 'Replacement browser' });
    const listenerDirectory = await request.get(`${listener.apiUrl}/api/v0/listening-party?refresh=true`, { headers: listenerHeaders });
    expect(listenerDirectory.ok()).toBe(true);
    const listenerParties = await listenerDirectory.json();
    expect(listenerParties.map((party: { partyId: string }) => party.partyId)).toContain(replacement.partyId);
    expect(listenerParties.map((party: { partyId: string }) => party.partyId)).not.toContain(first.partyId);
  });

  test('keeps a live host and listener current through a 15-minute capability soak @player-radio-soak', async ({ browser, page, request }, testInfo) => {
    test.setTimeout(20 * 60 * 1000);
    test.skip(process.env.RUN_PLAYER_RADIO_SOAK !== '1', 'Run with pnpm test:player:radio-soak.');

    const host = harness.getNode('A');
    const listener = harness.getNode('B');
    const title = 'Host renewal soak';
    await fs.writeFile(path.join(host.getAppDir(), 'downloads', `${title}.wav`), radioTone(17 * 60, 8000));

    const [hostLogin, listenerLogin] = await Promise.all([
      request.post(`${host.apiUrl}/api/v0/session`, { data: { username: host.nodeCfg.username, password: host.nodeCfg.password } }),
      request.post(`${listener.apiUrl}/api/v0/session`, { data: { username: listener.nodeCfg.username, password: listener.nodeCfg.password } }),
    ]);
    expect(hostLogin.ok()).toBe(true);
    expect(listenerLogin.ok()).toBe(true);
    const hostHeaders = { Authorization: `Bearer ${(await hostLogin.json()).token}` };
    const listenerHeaders = { Authorization: `Bearer ${(await listenerLogin.json()).token}` };
    const connection = await request.post(`${listener.apiUrl}/api/v0/overlay/connect`, {
      headers: listenerHeaders,
      data: { address: '127.0.0.1', port: host.getOverlayPort() },
    });
    expect(await connection.text()).toContain('"connected":true');
    for (const [node, headers] of [[host, hostHeaders], [listener, listenerHeaders]] as const) {
      const status = await request.get(`${node.apiUrl}/api/v0/dht/status`, { headers });
      expect(status.ok()).toBe(true);
      const meshStatus = await status.json();
      expect(meshStatus).toMatchObject({ lanOnly: true, isDhtRunning: false, dhtNodeCount: 0 });
      expect(meshStatus.activeMeshConnections).toBeGreaterThanOrEqual(1);
    }

    const libraryUrl = `${host.apiUrl}/api/v0/library/items/browser?query=Host%20renewal%20soak&kinds=Audio`;
    await expect.poll(async () => {
      const response = await request.get(libraryUrl, { headers: hostHeaders });
      return response.ok() && (await response.json()).files.some((file: { fileName: string }) => file.fileName === `${title}.wav`);
    }, { timeout: 30_000 }).toBe(true);
    const library = await request.get(libraryUrl, { headers: hostHeaders });
    expect(library.ok()).toBe(true);
    const item = (await library.json()).files.find((file: { fileName: string }) => file.fileName === `${title}.wav`);
    expect(item?.contentId).toBeTruthy();
    const podId = await createRadioRoom(request, host.apiUrl, hostHeaders, 'Host renewal soak room');
    const roomUrl = `${host.nodeCfg.baseUrl}/pods/${podId}/channels/music`;
    const stateUrl = `${host.apiUrl}/api/v0/listening-party/${podId}/music`;
    const snapshot = async () => {
      const response = await request.get(stateUrl, { headers: hostHeaders });
      expect(response.ok() || response.status() === 204).toBe(true);
      return response.status() === 204 ? null : response.json();
    };
    const renewalResponses: Array<{ status: number; at: number }> = [];
    page.on('response', (response) => {
      if (response.request().method() === 'POST' && response.url().includes(`/listening-party/${podId}/music/renew`)) {
        renewalResponses.push({ status: response.status(), at: Date.now() });
      }
    });

    const listenerContext = await browser.newContext({ serviceWorkers: 'block' });
    const listenerPage = await listenerContext.newPage();
    try {
      for (const target of [page, listenerPage]) {
        await target.addInitScript(() => localStorage.setItem('slskdn.player.collapsed', 'false'));
      }
      await login(page, host.nodeCfg);
      await login(listenerPage, listener.nodeCfg);
      await page.goto(roomUrl);
      await page.getByTestId('player-open-file-browser').click();
      const modal = page.getByTestId('player-file-browser-modal');
      await modal.getByTestId('player-file-browser-search').locator('input').fill(title);
      await modal.getByRole('button', { name: `Play ${title}.wav`, exact: true }).click();
      await expect.poll(() => audioElements(page).evaluateAll((elements) =>
        (elements as HTMLAudioElement[]).some((audio) => !audio.paused && audio.currentTime > 1))).toBe(true);

      await page.getByRole('button', { name: 'List room broadcast in mesh directory', exact: true }).click();
      await page.getByRole('button', { name: 'Broadcast current track to room', exact: true }).click();
      await expect.poll(async () => (await snapshot())?.partyId).toBeTruthy();
      const started = await snapshot();
      const partyId = started.partyId;
      await page.getByRole('button', { name: 'Allow mesh streaming for broadcast', exact: true }).click();
      await expect.poll(async () => (await snapshot())?.allowMeshStreaming).toBe(true);

      const findAnnouncement = async (apiUrl: string, headers: Record<string, string>) => {
        const response = await request.get(`${apiUrl}/api/v0/listening-party?refresh=true`, { headers });
        expect(response.ok()).toBe(true);
        return (await response.json()).find((party: { partyId: string }) => party.partyId === partyId) ?? null;
      };
      const hostAnnouncement = () => findAnnouncement(host.apiUrl, hostHeaders);
      const remoteAnnouncement = () => findAnnouncement(listener.apiUrl, listenerHeaders);
      await expect.poll(async () => Boolean((await hostAnnouncement())?.streamTicket), { timeout: 30_000 }).toBe(true);
      await expect.poll(async () => Boolean((await remoteAnnouncement())?.streamTicket), { timeout: 60_000, intervals: [1_000, 5_000, 10_000] }).toBe(true);
      const initialAnnouncement = await remoteAnnouncement();
      expect(initialAnnouncement?.streamTicket).toBeTruthy();
      const initialStreamPath = initialAnnouncement.streamPath;

      await listenerPage.getByRole('button', { name: 'Show player tools', exact: true }).click();
      await listenerPage.getByTestId('player-open-listed-radio').click();
      await listenerPage.getByRole('button', { name: `Play ${started.title} from listed radio`, exact: true }).click();
      await expect.poll(() => audioElements(listenerPage).evaluateAll((elements) =>
        (elements as HTMLAudioElement[]).some((audio) => !audio.paused && audio.currentTime > 1))).toBe(true);

      const soakStartedAt = Date.now();
      let previousHostTime = await audioElements(page).evaluateAll((elements) =>
        Math.max(...(elements as HTMLAudioElement[]).map((audio) => audio.currentTime)));
      let previousListenerTime = await audioElements(listenerPage).evaluateAll((elements) =>
        Math.max(...(elements as HTMLAudioElement[]).map((audio) => audio.currentTime)));
      const observedTickets = new Set([initialAnnouncement.streamTicket]);
      while (Date.now() - soakStartedAt < 15 * 60 * 1000) {
        await listenerPage.waitForTimeout(Math.min(60_000, 15 * 60 * 1000 - (Date.now() - soakStartedAt)));
        const elapsed = Date.now() - soakStartedAt;
        const [hostTime, listenerTime, announcement] = await Promise.all([
          audioElements(page).evaluateAll((elements) => Math.max(...(elements as HTMLAudioElement[]).map((audio) => audio.currentTime))),
          audioElements(listenerPage).evaluateAll((elements) => Math.max(...(elements as HTMLAudioElement[]).map((audio) => audio.currentTime))),
          remoteAnnouncement(),
        ]);
        expect(hostTime).toBeGreaterThan(previousHostTime + 30);
        expect(listenerTime).toBeGreaterThan(previousListenerTime + 30);
        expect(announcement?.partyId).toBe(partyId);
        if (announcement?.streamTicket) observedTickets.add(announcement.streamTicket);
        expect(renewalResponses.every((renewal) => renewal.status === 204)).toBe(true);
        if (elapsed >= 6 * 60 * 1000) expect(renewalResponses.length).toBeGreaterThanOrEqual(1);
        if (elapsed >= 11 * 60 * 1000) expect(renewalResponses.length).toBeGreaterThanOrEqual(2);
        previousHostTime = hostTime;
        previousListenerTime = listenerTime;
        console.log(`Player radio soak ${Math.floor(elapsed / 60_000)}m: renewals=${renewalResponses.length}, tickets=${observedTickets.size}, host=${Math.floor(hostTime)}s, listener=${Math.floor(listenerTime)}s`);
      }

      expect(Date.now() - soakStartedAt).toBeGreaterThanOrEqual(15 * 60 * 1000);
      expect(renewalResponses.length).toBeGreaterThanOrEqual(2);
      expect(observedTickets.size).toBeGreaterThanOrEqual(2);
      expect((await request.get(`${host.apiUrl}${initialStreamPath}`, { headers: { Range: 'bytes=0-1' } })).status()).toBe(401);
      const latestAnnouncement = await remoteAnnouncement();
      expect(latestAnnouncement?.streamPath).not.toBe(initialStreamPath);
      expect((await request.get(`${host.apiUrl}${latestAnnouncement.streamPath}`, { headers: { Range: 'bytes=0-1' } })).status()).toBe(206);
      await testInfo.attach('player-radio-renewal-soak.json', {
        body: JSON.stringify({ elapsedMs: Date.now() - soakStartedAt, renewalResponses, observedTicketCount: observedTickets.size,
          hostPlaybackSeconds: previousHostTime, listenerPlaybackSeconds: previousListenerTime }, null, 2),
        contentType: 'application/json',
      });
      await page.getByRole('button', { name: 'Stop active room broadcast', exact: true }).click();
      await expect.poll(snapshot).toBeNull();
    } finally {
      await listenerContext.close();
    }
  });

});
