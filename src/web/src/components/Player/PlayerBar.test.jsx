import PlayerBar from './PlayerBar';
import React from 'react';
import { PlayerContext, PlayerProvider, usePlayer } from './PlayerContext';
import { MemoryRouter } from 'react-router-dom';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { vi } from 'vitest';
import * as externalVisualizer from '../../lib/externalVisualizer';
import * as collectionsAPI from '../../lib/collections';
import * as audioGraph from './audioGraph';
import * as streaming from '../../lib/streaming';
import * as nowPlaying from '../../lib/nowPlaying';
import * as searches from '../../lib/searches';
import * as wishlistAPI from '../../lib/wishlist';
import * as listeningParty from '../../lib/listeningParty';
import { setExperiencePreferencesSnapshot } from '../../lib/experiencePreferences';

vi.mock('../../lib/nowPlaying', () => ({
  clearNowPlaying: vi.fn(() => Promise.resolve()),
  setNowPlaying: vi.fn(() => Promise.resolve()),
}));

vi.mock('../../lib/collections', () => ({
  createCollection: vi.fn(() => Promise.resolve({ data: { id: 'playlist-created', title: 'Saved queue', type: 'Playlist' } })),
  addCollectionItem: vi.fn(() => Promise.resolve({ data: { id: 'playlist-item' } })),
  deleteCollection: vi.fn(() => Promise.resolve({})),
  browseLibraryItems: vi.fn(({ path = '', query = '' } = {}) => {
    if (query) {
      return Promise.resolve({
        data: {
          breadcrumbs: [{ name: 'Library', path: '' }],
          directories: [],
          duplicatesRemoved: 2,
          files: [
            {
              bytes: 5242880,
              contentId: 'sha256:library',
              duplicateCount: 3,
              fileName: 'Library stream.ogg',
              mediaKind: 'Audio',
              path: 'Downloads/Library stream.ogg',
            },
          ],
          hasMore: false,
          totalDirectories: 0,
          totalFiles: 1,
        },
      });
    }

    if (path === 'Downloads') {
      return Promise.resolve({
        data: {
          breadcrumbs: [
            { name: 'Library', path: '' },
            { name: 'Downloads', path: 'Downloads' },
          ],
          directories: [],
          duplicatesRemoved: 0,
          files: [
            {
              bytes: 5242880,
              contentId: 'sha256:library',
              duplicateCount: 1,
              fileName: 'Library stream.ogg',
              mediaKind: 'Audio',
              path: 'Downloads/Library stream.ogg',
            },
          ],
          hasMore: false,
          totalDirectories: 0,
          totalFiles: 1,
        },
      });
    }

    return Promise.resolve({
      data: {
        breadcrumbs: [{ name: 'Library', path: '' }],
        directories: [
          {
            childDirectoryCount: 2,
            fileCount: 1,
            name: 'Downloads',
            path: 'Downloads',
          },
        ],
        duplicatesRemoved: 0,
        files: [],
        hasMore: false,
        totalDirectories: 1,
        totalFiles: 0,
      },
    });
  }),
  getCollectionItems: vi.fn(() =>
    Promise.resolve({
      data: [
        {
          contentId: 'sha256:collection',
          fileName: 'Collection stream.ogg',
          id: 'collection-item-1',
          mediaKind: 'Audio',
        },
      ],
    }),
  ),
  getCollections: vi.fn(() =>
    Promise.resolve({ data: [{ id: 'collection-1', title: 'Favorites' }] }),
  ),
  searchLibraryItems: vi.fn(() =>
    Promise.resolve({
      data: {
        items: [
          {
            contentId: 'sha256:library',
            fileName: 'Library stream.ogg',
            mediaKind: 'Audio',
            path: '/downloads/Library stream.ogg',
          },
        ],
      },
    }),
  ),
}));

vi.mock('../../lib/externalVisualizer', () => ({
  getExternalVisualizerStatus: vi.fn(() =>
    Promise.resolve({
      arguments: [],
      available: true,
      configured: true,
      enabled: true,
      name: 'MilkDrop3',
      path: '/opt/MilkDrop3/MilkDrop 3.exe',
      resolvedPath: '/opt/MilkDrop3/MilkDrop 3.exe',
      workingDirectory: '/opt/MilkDrop3',
    }),
  ),
  launchExternalVisualizer: vi.fn(() =>
    Promise.resolve({
      error: null,
      name: 'MilkDrop3',
      processId: 1234,
      started: true,
    }),
  ),
}));

vi.mock('../../lib/streaming', () => ({
  buildDirectStreamUrl: vi.fn((contentId) =>
    `/api/v0/streams/${encodeURIComponent(contentId)}`,
  ),
  buildTranscodedStreamUrl: vi.fn((contentId, ticket, startSeconds) =>
    `/api/v0/streams/${encodeURIComponent(contentId)}/transcoded?ticket=${ticket}&startSeconds=${startSeconds}`,
  ),
  buildTicketedStreamUrl: vi.fn((contentId, ticket) =>
    `/api/v0/streams/${encodeURIComponent(contentId)}?ticket=${ticket}`,
  ),
  createStreamTicket: vi.fn(() => Promise.resolve('ticket-1')),
  getPlaybackInfo: vi.fn(() => Promise.resolve({ data: { durationSeconds: 120 } })),
}));

vi.mock('../../lib/searches', () => ({
  createBatch: vi.fn(),
}));

vi.mock('../../lib/wishlist', () => ({
  create: vi.fn(),
}));

const TestHarness = () => {
  const { playItem, playNext, queueItems } = usePlayer();

  return (
    <>
      <button onClick={() => queueItems([{ contentId: 'sha256:filename', fileName: 'Filename only.wav' }])} type="button">Queue filename</button>
      <button onClick={() => playNext({ contentId: 'sha256:filename', fileName: 'Filename only.wav' })} type="button">Play filename next</button>
      <button
        onClick={() =>
          playItem({
            album: 'Fixture Album',
            contentId: 'sha256:test',
            confidence: 0.91,
            fileName: 'Local stream.ogg',
            genre: 'Fixture Genre',
            sourceProviders: ['mesh', 'soulseek'],
            title: 'Local stream',
            verified: true,
          })
        }
        type="button"
      >
        Play fixture
      </button>
      <button
        onClick={() =>
          playItem({
            contentId: 'sha256:malformed',
            fileName: 'Malformed stream.ogg',
            sourceProviders: { 0: 'mesh', length: 1 },
            tags: { 0: 'tag', length: 1 },
            title: 'Malformed stream',
          })
        }
        type="button"
      >
        Play malformed fixture
      </button>
      <button
        onClick={() =>
          playItem({
            contentId: 'sha256:second',
            fileName: 'Second stream.ogg',
            title: 'Second stream',
          })
        }
        type="button"
      >
        Play second fixture
      </button>
      <button
        onClick={() =>
          playItem({
            contentId: 'sha256:third',
            fileName: 'Third stream.ogg',
            title: 'Third stream',
          })
        }
        type="button"
      >
        Play third fixture
      </button>
      <button
        onClick={() => queueItems([
          { contentId: 'sha256:second', title: 'Second stream', artist: 'slskdN' },
          { contentId: 'sha256:test', title: 'Local stream', artist: 'slskdN' },
        ])}
        type="button"
      >
        Queue prior fixtures
      </button>
      <PlayerBar />
    </>
  );
};

const renderPlayer = (overrides = {}) => {
  const result = render(
    <MemoryRouter>
      <PlayerProvider>
        <PlayerContext.Consumer>{(player) => (
          <PlayerContext.Provider value={{ ...player, ...overrides }}>
            <TestHarness />
          </PlayerContext.Provider>
        )}</PlayerContext.Consumer>
      </PlayerProvider>
    </MemoryRouter>,
  );
  const more = screen.queryByRole('button', { name: 'Show player tools' });
  if (more) fireEvent.click(more);
  return result;
};

describe('PlayerBar', () => {
  const originalMediaSession = Object.getOwnPropertyDescriptor(navigator, 'mediaSession');
  const originalMediaDevices = Object.getOwnPropertyDescriptor(navigator, 'mediaDevices');
  const originalMatchMedia = Object.getOwnPropertyDescriptor(window, 'matchMedia');
  beforeEach(() => {
    vi.clearAllMocks();
    setExperiencePreferencesSnapshot(null);
    window.localStorage.clear();
    window.sessionStorage.clear();
    // These tests exercise the expanded player UI; the collapsed-by-default
    // behavior itself is covered separately below.
    window.localStorage.setItem('slskdn.player.collapsed', 'false');
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: true })));
    searches.createBatch.mockResolvedValue(3);
    wishlistAPI.create.mockResolvedValue({ id: 'wishlist-seed' });
    HTMLMediaElement.prototype.load = vi.fn();
    HTMLMediaElement.prototype.play = vi.fn(() => Promise.resolve());
    HTMLMediaElement.prototype.pause = vi.fn();
  });

  afterEach(() => {
    cleanup();
    if (originalMediaSession) Object.defineProperty(navigator, 'mediaSession', originalMediaSession);
    else delete navigator.mediaSession;
    if (originalMediaDevices) Object.defineProperty(navigator, 'mediaDevices', originalMediaDevices);
    else delete navigator.mediaDevices;
    if (originalMatchMedia) Object.defineProperty(window, 'matchMedia', originalMatchMedia);
    else delete window.matchMedia;
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('describes following an empty room without inventing a host identity', () => {
    render(<MemoryRouter><PlayerContext.Consumer>{(defaults) => (
      <PlayerContext.Provider value={{ ...defaults, followingParty: { podId: 'pod-a', channelId: 'music' } }}>
        <PlayerBar />
      </PlayerContext.Provider>
    )}</PlayerContext.Consumer></MemoryRouter>);
    expect(screen.getByText(/Waiting for room broadcast/)).toBeInTheDocument();
    expect(screen.queryByText(/Following undefined/)).not.toBeInTheDocument();
  });

  it.each([
    [{ pending: true, error: '' }, 'connecting to room'],
    [{ pending: false, error: 'Connection closed' }, 'room updates unavailable'],
  ])('keeps followed-room connection feedback visible away from its panel: %s', (status, message) => {
    render(<MemoryRouter><PlayerContext.Consumer>{(defaults) => (
      <PlayerContext.Provider value={{ ...defaults, followingParty: { podId: 'pod-a', channelId: 'music', hostPeerId: 'host-a' }, followingPartyStatus: status }}>
        <PlayerBar />
      </PlayerContext.Provider>
    )}</PlayerContext.Consumer></MemoryRouter>);
    expect(document.querySelector('.player-subtitle')).toHaveTextContent(
      new RegExp(`Following host-a.*${message}`),
    );
  });

  it('collapses by default when no preference has ever been stored', () => {
    window.localStorage.removeItem('slskdn.player.collapsed');
    renderPlayer();

    expect(document.querySelector('.player-bar-collapsed')).not.toBeNull();
    expect(screen.getByTestId('player-expand')).toBeInTheDocument();
  });

  it('stays expanded once the user has explicitly expanded it before', () => {
    window.localStorage.setItem('slskdn.player.collapsed', 'false');
    renderPlayer();

    expect(document.querySelector('.player-bar-collapsed')).toBeNull();
    const volume = screen.getByLabelText('Playback volume');
    expect(volume).toHaveAttribute('aria-valuetext', '100%');
    fireEvent.change(volume, { target: { value: '0.42' } });
    expect(volume).toHaveAttribute('aria-valuetext', '42%');
  });

  it('normalizes equalizer arrow keys and announces values in decibels', () => {
    renderPlayer();
    fireEvent.click(screen.getByRole('button', { name: 'Show equalizer' }));

    const gain = screen.getByLabelText('31 equalizer gain');
    expect(gain).toHaveAttribute('aria-valuetext', '0 dB');
    expect(gain).toHaveAttribute('aria-orientation', 'vertical');
    expect(gain).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'Enable equalizer' }));
    expect(gain).toBeEnabled();
    for (const [key, value] of [
      ['ArrowUp', '1'],
      ['ArrowRight', '2'],
      ['ArrowDown', '1'],
      ['ArrowLeft', '0'],
    ]) {
      fireEvent.keyDown(gain, { key });
      expect(gain).toHaveValue(value);
      expect(gain).toHaveAttribute('aria-valuetext', `${value} dB`);
    }

    fireEvent.change(gain, { target: { value: '12' } });
    fireEvent.keyDown(gain, { key: 'ArrowUp' });
    expect(gain).toHaveValue('12');
    fireEvent.change(gain, { target: { value: '-12' } });
    fireEvent.keyDown(gain, { key: 'ArrowDown' });
    expect(gain).toHaveValue('-12');

    expect(gain).toHaveAttribute('min', '-12');
    expect(gain).toHaveAttribute('max', '12');
  });

  it('returns scroll and focus to playback when closing tools', async () => {
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    await screen.findByText('Local stream');
    const bar = document.querySelector('.player-bar');
    bar.scrollTop = 250;
    fireEvent.click(screen.getByRole('button', { name: 'Hide player tools' }));
    expect(bar.scrollTop).toBe(0);
    expect(screen.getByTestId('player-toggle-playback')).toHaveFocus();
  });

  it('returns focus to the visual tile when closing tools without a track', () => {
    renderPlayer();
    fireEvent.click(screen.getByRole('button', { name: 'Hide player tools' }));
    expect(screen.getByTestId('player-visual-tile')).toHaveFocus();
  });

  it('keeps Collapse available when optional player tools are closed', () => {
    renderPlayer();
    fireEvent.click(screen.getByRole('button', { name: 'Hide player tools' }));
    expect(screen.getByTestId('player-collapse')).toBeVisible();
    fireEvent.click(screen.getByTestId('player-collapse'));
    expect(screen.getByTestId('player-expand')).toBeVisible();
  });

  it('seeks and adjusts volume in the compact bar', async () => {
    window.localStorage.removeItem('slskdn.player.collapsed');
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    Object.defineProperty(audio, 'duration', { configurable: true, value: 120 });
    fireEvent.loadedMetadata(audio);
    fireEvent.change(screen.getByLabelText('Seek playback'), { target: { value: '42' } });
    fireEvent.pointerUp(screen.getByLabelText('Seek playback'));
    const volume = screen.getByLabelText('Playback volume');
    fireEvent.change(volume, { target: { value: '0.35' } });
    expect(audio.currentTime).toBe(42);
    expect(audio.volume).toBe(0.35);
    expect(volume).toHaveAttribute('aria-valuetext', '35%');
  });

  it('publishes Now Playing only after playback starts and clears it at the final end', async () => {
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    expect(nowPlaying.setNowPlaying).not.toHaveBeenCalled();
    fireEvent.play(audio);
    expect(nowPlaying.setNowPlaying).toHaveBeenCalledWith(expect.objectContaining({ title: 'Local stream' }));
    fireEvent.ended(audio);
    expect(nowPlaying.clearNowPlaying).toHaveBeenCalled();
  });

  it.each(['Queue filename', 'Play filename next'])('normalizes filename-only metadata through %s', async (action) => {
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    fireEvent.click(screen.getByText(action));
    fireEvent.click(screen.getByTestId('player-next'));
    await waitFor(() => expect(document.querySelector('.player-title')).toHaveTextContent('Filename only.wav'));
    expect(document.querySelector('.player-title')).not.toHaveTextContent('Nothing playing');
  });

  it('normalizes a restored filename-only queue without losing its paused position', async () => {
    sessionStorage.setItem('slskdn.player.session.v1', JSON.stringify({
      queue: [{ contentId: 'sha256:restored', fileName: 'Restored filename.wav', positionSeconds: 12, startPaused: true }],
    }));
    renderPlayer();
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Arestored'));
    expect(document.querySelector('.player-title')).toHaveTextContent('Restored filename.wav');
    Object.defineProperty(audio, 'duration', { configurable: true, value: 120 });
    fireEvent.loadedMetadata(audio);
    expect(audio.currentTime).toBe(12);
    expect(HTMLMediaElement.prototype.play).not.toHaveBeenCalled();
  });

  it('checkpoints playback on page hide without progress-driven session writes', async () => {
    const storage = vi.spyOn(Storage.prototype, 'setItem');
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    const writes = () => storage.mock.calls.filter(([key]) => key === 'slskdn.player.session.v1').length;
    const before = writes();
    for (let second = 1; second <= 12; second++) {
      audio.currentTime = second;
      fireEvent.timeUpdate(audio);
    }
    expect(writes()).toBe(before);
    fireEvent(window, new Event('pagehide'));
    expect(JSON.parse(sessionStorage.getItem('slskdn.player.session.v1')).queue[0].positionSeconds).toBe(12);
    expect(writes()).toBe(before + 1);
    storage.mockRestore();
  });

  it.each([false, true])('preserves a newly saved playlist when the initial list settles late (failure: %s)', async (failure) => {
    let finishList;
    let failList;
    collectionsAPI.getCollections.mockImplementationOnce(() => new Promise((resolve, reject) => { finishList = resolve; failList = reject; }));
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    fireEvent.click(screen.getByTestId('player-open-queue'));
    fireEvent.change(screen.getByLabelText('New playlist name'), { target: { value: 'Saved queue' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save queue' }));
    expect(await screen.findByText('Saved 1 track to Saved queue.')).toBeInTheDocument();
    if (failure) {
      await act(async () => failList(new Error('List unavailable')));
    } else {
      await act(async () => finishList({ data: [{ id: 'older-playlist', title: 'Older playlist', type: 'Playlist' }] }));
    }
    const selected = screen.getByLabelText('Saved playlist');
    expect(selected.querySelector('option[value="playlist-created"]')).toHaveTextContent('Saved queue');
    expect(screen.getByText(failure ? 'Could not retrieve saved playlists. Close and reopen the queue to retry.' : 'Saved 1 track to Saved queue.')).toBeInTheDocument();
    expect(Array.from(selected.options).map((option) => option.value)).toEqual(failure
      ? ['', 'playlist-created']
      : ['', 'older-playlist', 'playlist-created']);
  });

  it('shows playlist operation progress and keeps fields stable until completion', async () => {
    let finishSave;
    collectionsAPI.createCollection.mockImplementationOnce(() => new Promise((resolve) => { finishSave = resolve; }));
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    fireEvent.click(screen.getByTestId('player-open-queue'));
    const name = screen.getByLabelText('New playlist name');
    const selected = screen.getByLabelText('Saved playlist');
    fireEvent.change(name, { target: { value: 'Saved queue' } });
    const save = screen.getByRole('button', { name: 'Save queue' });
    fireEvent.click(save);
    expect(save).toHaveAttribute('aria-busy', 'true');
    expect(name).toBeDisabled();
    expect(selected).toBeDisabled();
    await act(async () => finishSave({ data: { id: 'playlist-created', title: 'Saved queue', type: 'Playlist' } }));
    expect(await screen.findByText('Saved 1 track to Saved queue.')).toBeInTheDocument();
    expect(selected).toBeEnabled();
    fireEvent.change(selected, { target: { value: 'playlist-created' } });
    let finishLoad;
    collectionsAPI.getCollectionItems.mockImplementationOnce(() => new Promise((resolve) => { finishLoad = resolve; }));
    const load = screen.getByRole('button', { name: 'Load', exact: true });
    fireEvent.click(load);
    expect(load).toHaveAttribute('aria-busy', 'true');
    expect(selected).toBeDisabled();
    await act(async () => finishLoad({ data: [{ contentId: 'sha256:loaded', fileName: 'Loaded filename.wav' }] }));
    await waitFor(() => expect(document.querySelector('.player-title')).toHaveTextContent('Loaded filename.wav'));
    expect(load).toHaveAttribute('aria-busy', 'false');
    expect(selected).toBeEnabled();
  });

  it('releases the previous radio source before preparing another snapshot with crossfade enabled', async () => {
    window.localStorage.setItem('slskdn.player.crossfadeEnabled', 'true');
    let finish;
    vi.spyOn(listeningParty, 'createRadioStreamUrl').mockResolvedValueOnce('/api/v0/mesh-streams/first-radio').mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }));
    vi.spyOn(listeningParty, 'getPartyDirectory').mockResolvedValue([
      { partyId: 'first-radio', contentId: 'radio:first', title: 'First radio', allowMeshStreaming: true, streamPath: '/first-old-path', transportUsername: 'host-overlay', streamTicket: 'capability' },
      { partyId: 'second-radio', contentId: 'radio:second', title: 'Second radio', allowMeshStreaming: true, streamPath: '/second-old-path', transportUsername: 'host-overlay', streamTicket: 'capability' },
    ]);
    renderPlayer();
    fireEvent.click(screen.getByTestId('player-open-listed-radio'));
    fireEvent.click(await screen.findByRole('button', { name: 'Play First radio from listed radio' }));
    await waitFor(() => expect(document.querySelector('audio').getAttribute('src')).toBe('/api/v0/mesh-streams/first-radio'));
    fireEvent.play(document.querySelector('audio'));
    fireEvent.click(screen.getByTestId('player-open-listed-radio'));
    fireEvent.click(await screen.findByRole('button', { name: 'Play Second radio from listed radio' }));
    expect(document.querySelector('audio')).not.toHaveAttribute('src');
    await act(async () => finish('/api/v0/mesh-streams/second-radio'));
    await waitFor(() => expect(document.querySelector('audio').getAttribute('src')).toBe('/api/v0/mesh-streams/second-radio'));
  });

  it.each([
    [429, 'radio_fairness_limited', 'Remote radio is limited by network fairness. Check sharing activity before retrying.'],
    [429, null, 'Radio streaming is at capacity. Retry later.'],
    [404, null, 'This radio snapshot expired or is unavailable. Refresh listed radio.'],
  ])('explains radio acquisition status %s and code %s', async (status, code, message) => {
    vi.spyOn(listeningParty, 'createRadioStreamUrl').mockRejectedValueOnce({ response: { status, data: { code } } });
    vi.spyOn(listeningParty, 'getPartyDirectory').mockResolvedValue([
      { partyId: 'radio-limited', contentId: 'radio:limited', title: 'Limited radio', allowMeshStreaming: true, streamPath: '/old-host-path', transportUsername: 'host-overlay', streamTicket: 'capability' },
    ]);
    renderPlayer();
    fireEvent.click(screen.getByTestId('player-open-listed-radio'));
    fireEvent.click(await screen.findByRole('button', { name: 'Play Limited radio from listed radio' }));
    expect(await screen.findByText(message)).toBeInTheDocument();
  });

  it('reacquires a radio ticket after initial setup failure without falling back to local content', async () => {
    const create = vi.spyOn(listeningParty, 'createRadioStreamUrl').mockRejectedValueOnce(new Error('Host unavailable')).mockResolvedValueOnce('/api/v0/mesh-streams/retry-ticket');
    vi.spyOn(listeningParty, 'getPartyDirectory').mockResolvedValue([
      { partyId: 'radio-retry', contentId: 'radio:retry', title: 'Retry radio', allowMeshStreaming: true, streamPath: '/old-host-path', transportUsername: 'host-overlay', streamTicket: 'capability' },
    ]);
    renderPlayer();
    fireEvent.click(screen.getByTestId('player-open-listed-radio'));
    fireEvent.click(await screen.findByRole('button', { name: 'Play Retry radio from listed radio' }));
    expect(await screen.findByText('The request failed. Try again.')).toBeInTheDocument();
    streaming.createStreamTicket.mockClear();
    fireEvent.click(screen.getByTestId('player-toggle-playback'));
    await waitFor(() => expect(document.querySelector('audio').getAttribute('src')).toBe('/api/v0/mesh-streams/retry-ticket'));
    expect(create).toHaveBeenCalledTimes(2);
    expect(streaming.createStreamTicket).not.toHaveBeenCalled();
  });

  it.each([false, true])('reconnects stalled radio explicitly and releases its previous source (collapsed=%s)', async (collapsed) => {
    let finish;
    const create = vi.spyOn(listeningParty, 'createRadioStreamUrl').mockResolvedValueOnce('/api/v0/mesh-streams/stalled').mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }));
    vi.spyOn(listeningParty, 'getPartyDirectory').mockResolvedValue([
      { partyId: 'radio-stalled', contentId: 'radio:stalled', title: 'Stalled radio', allowMeshStreaming: true, transportUsername: 'host', streamTicket: 'capability' },
    ]);
    renderPlayer();
    fireEvent.click(screen.getByTestId('player-open-listed-radio'));
    fireEvent.click(await screen.findByRole('button', { name: 'Play Stalled radio from listed radio' }));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toBe('/api/v0/mesh-streams/stalled'));
    fireEvent.play(audio);
    fireEvent.waiting(audio);
    if (collapsed) fireEvent.click(screen.getByRole('button', { name: 'Collapse player' }));
    fireEvent.click(screen.getByRole('button', { name: 'Retry radio playback' }));
    expect(audio).not.toHaveAttribute('src');
    expect(create).toHaveBeenCalledTimes(2);
    await act(async () => finish('/api/v0/mesh-streams/reconnected'));
    await waitFor(() => expect(audio.getAttribute('src')).toBe('/api/v0/mesh-streams/reconnected'));
  });

  it.each([false, true])('reuses the admitted radio URL when seeking and preserves play state (wasPlaying=%s)', async (wasPlaying) => {
    const streamUrl = '/api/v0/mesh-streams/admitted-radio';
    const create = vi.spyOn(listeningParty, 'createRadioStreamUrl').mockResolvedValue(streamUrl);
    vi.spyOn(listeningParty, 'getPartyDirectory').mockResolvedValue([
      { partyId: 'radio-seek', contentId: 'radio:seek', title: 'Seek radio', allowMeshStreaming: true, transportUsername: 'host', streamTicket: 'capability' },
    ]);
    let paused = true;
    HTMLMediaElement.prototype.play.mockImplementation(() => {
      paused = false;
      return Promise.resolve();
    });
    HTMLMediaElement.prototype.pause.mockImplementation(() => { paused = true; });

    renderPlayer();
    fireEvent.click(screen.getByTestId('player-open-listed-radio'));
    fireEvent.click(await screen.findByRole('button', { name: 'Play Seek radio from listed radio' }));
    const audio = document.querySelector('audio');
    Object.defineProperty(audio, 'paused', { configurable: true, get: () => paused });
    Object.defineProperty(audio, 'duration', { configurable: true, value: 400 });
    Object.defineProperty(audio, 'currentTime', { configurable: true, writable: true, value: 0 });
    await waitFor(() => expect(audio.getAttribute('src')).toBe(streamUrl));
    fireEvent.loadedMetadata(audio);
    fireEvent.play(audio);
    if (!wasPlaying) fireEvent.click(screen.getByTestId('player-toggle-playback'));
    expect(paused).toBe(!wasPlaying);

    const seek = screen.getByLabelText('Seek playback');
    fireEvent.change(seek, { target: { value: '300' } });
    fireEvent.pointerUp(seek);
    await waitFor(() => expect(audio.currentTime).toBe(300));

    expect(create).toHaveBeenCalledTimes(1);
    expect(audio.getAttribute('src')).toBe(streamUrl);
    expect(paused).toBe(!wasPlaying);
  });

  it('does not probe local decoding after a listed-radio stream failure', async () => {
    vi.spyOn(listeningParty, 'createRadioStreamUrl').mockResolvedValue('/radio-fixture.wav');
    vi.spyOn(listeningParty, 'getPartyDirectory').mockResolvedValue([
      { partyId: 'radio-test', contentId: 'sha256:test', title: 'Radio fixture', allowMeshStreaming: true, streamPath: '/radio-fixture.wav', transportUsername: 'host-overlay', streamTicket: 'capability' },
    ]);
    renderPlayer();
    fireEvent.click(screen.getByTestId('player-open-listed-radio'));
    fireEvent.click(await screen.findByRole('button', { name: 'Play Radio fixture from listed radio' }));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toBe('/radio-fixture.wav'));
    streaming.getPlaybackInfo.mockClear();
    fireEvent.error(audio);
    expect(streaming.getPlaybackInfo).not.toHaveBeenCalled();
    expect(screen.queryByText('Decode for playback')).not.toBeInTheDocument();
  });

  it('offers on-demand decoding after a server audio error', async () => {
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    fireEvent.error(audio);
    fireEvent.click(await screen.findByText('Decode for playback'));
    await waitFor(() => expect(audio.getAttribute('src')).toContain('/transcoded?'));
  });

  it('explains server decode failures', async () => {
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    fireEvent.error(audio);
    fireEvent.click(await screen.findByText('Decode for playback'));
    await waitFor(() => expect(audio.getAttribute('src')).toContain('/transcoded?'));

    Object.defineProperty(audio, 'error', { configurable: true, value: { code: 4 } });
    fireEvent.error(audio);
    expect(await screen.findByText('The server could not decode this audio. Press Play to retry.')).toBeInTheDocument();
    expect(screen.getByTestId('player-playback-announcement')).toHaveTextContent(
      'Playback error: Local stream. The server could not decode this audio. Press Play to retry.',
    );

    HTMLMediaElement.prototype.load.mockImplementation(() => {
      Object.defineProperty(audio, 'error', { configurable: true, value: null });
    });
    streaming.createStreamTicket.mockClear();
    streaming.createStreamTicket.mockResolvedValueOnce('retry-ticket');
    fireEvent.click(screen.getByTestId('player-toggle-playback'));
    await waitFor(() => expect(streaming.createStreamTicket).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(audio.getAttribute('src')).toContain('retry-ticket'));
  });

  it('announces stable playback, pause, and media errors without announcing seek updates', async () => {
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    const announcement = screen.getByTestId('player-playback-announcement');
    expect(announcement).toHaveAttribute('role', 'status');
    expect(announcement).toHaveAttribute('aria-live', 'polite');
    expect(announcement).toHaveAttribute('aria-atomic', 'true');
    fireEvent.play(audio);
    await waitFor(() => expect(announcement).toHaveTextContent('Now playing: Local stream.'));
    audio.currentTime = 12;
    fireEvent.timeUpdate(audio);
    expect(announcement).toHaveTextContent('Now playing: Local stream.');

    fireEvent.pause(audio);
    await waitFor(() => expect(announcement).toHaveTextContent('Paused: Local stream.'));
    fireEvent.error(audio);
    await waitFor(() => expect(announcement).toHaveTextContent(
      'Playback error: Local stream. This audio could not be decoded or streamed.',
    ));

    fireEvent.click(screen.getByTestId('player-stop'));
    await waitFor(() => expect(announcement).toHaveTextContent('Playback stopped.'));
  });

  it.each([
    { active: true, decoded: false },
    { active: false, decoded: false },
    { active: true, decoded: true },
    { active: false, decoded: true },
  ])('reports stopped playback only for an active media error (active=$active, decoded=$decoded)', async ({ active, decoded }) => {
    const reportPlaybackEvent = vi.fn();
    renderPlayer({ reportPlaybackEvent });
    fireEvent.click(screen.getByText('Play fixture'));
    const [audio, standby] = document.querySelectorAll('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    if (decoded) {
      fireEvent.error(audio);
      fireEvent.click(await screen.findByText('Decode for playback'));
      fireEvent.click(screen.getByTestId('player-fast-forward'));
    }
    await waitFor(() => expect(audio.getAttribute('src')).toContain(decoded ? 'startSeconds=30' : 'sha256%3Atest'));
    audio.currentTime = 27.5;
    Object.defineProperty(audio, 'paused', { configurable: true, value: false });
    fireEvent.play(audio);
    reportPlaybackEvent.mockClear();
    // A decode failure need not deliver a pause event. The standby must not
    // change the active host's playback state either.
    fireEvent.error(active ? audio : standby);
    expect(reportPlaybackEvent.mock.calls).toEqual(active ? [['pause', decoded ? 57.5 : 27.5]] : []);
  });

  it('pauses host state and suspends processing when native Play rejects before a play event', async () => {
    const reportPlaybackEvent = vi.fn();
    const ctx = { state: 'suspended', suspend: vi.fn(async () => { ctx.state = 'suspended'; }) };
    vi.spyOn(audioGraph, 'getExistingAudioGraph').mockReturnValue({ ctx });
    vi.spyOn(audioGraph, 'resumeAudioGraph').mockImplementation(async () => { ctx.state = 'running'; });
    vi.spyOn(audioGraph, 'suspendAudioGraph').mockImplementation(async () => { ctx.state = 'suspended'; });
    HTMLMediaElement.prototype.play.mockRejectedValueOnce(new Error('Playback denied'));
    renderPlayer({ reportPlaybackEvent });
    fireEvent.click(screen.getByText('Play fixture'));
    await screen.findByText('Playback could not start. Check the file or try again.');
    await waitFor(() => expect(ctx.state).toBe('suspended'));
    expect({ events: reportPlaybackEvent.mock.calls, contextState: ctx.state })
      .toEqual({ events: [['pause', 0]], contextState: 'suspended' });
  });

  it('reports a paused target when decoded seek setup fails after playing', async () => {
    const reportPlaybackEvent = vi.fn();
    renderPlayer({ reportPlaybackEvent });
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    fireEvent.error(audio);
    fireEvent.click(await screen.findByText('Decode for playback'));
    await waitFor(() => expect(audio.getAttribute('src')).toContain('/transcoded?'));
    audio.currentTime = 7;
    fireEvent.play(audio);
    fireEvent.timeUpdate(audio);
    reportPlaybackEvent.mockClear();
    streaming.createStreamTicket.mockRejectedValueOnce(new Error('Decoder busy'));
    fireEvent.click(screen.getByTestId('player-fast-forward'));
    await screen.findByText(/Decoding could not start/u);
    expect(reportPlaybackEvent.mock.calls).toEqual([['pause', 37]]);
    expect(screen.getByLabelText('Seek playback')).toHaveAttribute('aria-valuetext', '0:37 of 2:00');
  });

  it('keeps a loading graph available and ignores a rejected Play from the replaced track', async () => {
    const reportPlaybackEvent = vi.fn();
    const ctx = { state: 'suspended', suspend: vi.fn(async () => { ctx.state = 'suspended'; }) };
    vi.spyOn(audioGraph, 'getExistingAudioGraph').mockReturnValue({ ctx });
    vi.spyOn(audioGraph, 'resumeAudioGraph').mockImplementation(async () => { ctx.state = 'running'; });
    let rejectFirst;
    HTMLMediaElement.prototype.play.mockReturnValueOnce(new Promise((resolve, reject) => { rejectFirst = reject; }));
    renderPlayer({ reportPlaybackEvent });
    fireEvent.click(screen.getByText('Play fixture'));
    await waitFor(() => expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(1));
    expect(ctx.state).toBe('running');
    fireEvent.click(screen.getByText('Play second fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Asecond'));
    await waitFor(() => expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(2));
    fireEvent.play(audio);
    await act(async () => rejectFirst(new Error('Old request failed')));
    expect(reportPlaybackEvent.mock.calls).toEqual([['play', 0]]);
    expect(ctx.state).toBe('running');
    expect(screen.queryByText('Playback could not start. Check the file or try again.')).not.toBeInTheDocument();
    expect(screen.getByText('Second stream')).toBeInTheDocument();
  });

  it('reports a paused replacement when a crossfade start rejects and preserves explicit recovery', async () => {
    const reportPlaybackEvent = vi.fn();
    window.localStorage.setItem('slskdn.player.crossfadeEnabled', 'true');
    vi.stubGlobal('AudioContext', class {});
    const ctx = { state: 'suspended', suspend: vi.fn(async () => { ctx.state = 'suspended'; }) };
    const graph = { ctx };
    vi.spyOn(audioGraph, 'getOrCreateAudioGraph').mockReturnValue(graph);
    vi.spyOn(audioGraph, 'getExistingAudioGraph').mockReturnValue(graph);
    vi.spyOn(audioGraph, 'resumeAudioGraph').mockImplementation(async () => { ctx.state = 'running'; });
    vi.spyOn(audioGraph, 'setOutputGain').mockImplementation(() => {});
    vi.spyOn(audioGraph, 'fadeOutputGain').mockImplementation(() => {});
    renderPlayer({ reportPlaybackEvent });
    fireEvent.click(screen.getByText('Play fixture'));
    const first = document.querySelector('audio');
    await waitFor(() => expect(HTMLMediaElement.prototype.play).toHaveBeenCalled());
    Object.defineProperty(first, 'paused', { configurable: true, value: false });
    fireEvent.play(first);
    reportPlaybackEvent.mockClear();
    HTMLMediaElement.prototype.play.mockRejectedValueOnce(new Error('Next track denied'));
    fireEvent.click(screen.getByText('Play second fixture'));
    await screen.findByText('The next track could not start.');
    expect(reportPlaybackEvent.mock.calls).toEqual([['pause', 0]]);
    fireEvent.click(screen.getByTestId('player-toggle-playback'));
    await waitFor(() => expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(3));
    const replacement = document.querySelectorAll('audio')[1];
    fireEvent.play(replacement);
    expect(reportPlaybackEvent.mock.calls).toEqual([['pause', 0], ['play', 0]]);
    expect(screen.queryByText('The next track could not start.')).not.toBeInTheDocument();
  });

  it('aborts the prior decode stream and coalesces seek setup into the final position', async () => {
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    fireEvent.error(audio);
    fireEvent.click(await screen.findByText('Decode for playback'));
    await waitFor(() => expect(audio.getAttribute('src')).toContain('/transcoded?'));
    streaming.createStreamTicket.mockClear();
    HTMLMediaElement.prototype.load.mockClear();
    fireEvent.click(screen.getByTestId('player-fast-forward'));
    fireEvent.click(screen.getByTestId('player-fast-forward'));
    expect(audio.getAttribute('src')).toBeNull();
    expect(HTMLMediaElement.prototype.load).toHaveBeenCalled();
    expect(streaming.createStreamTicket).not.toHaveBeenCalled();
    await waitFor(() => expect(audio.getAttribute('src')).toContain('startSeconds=60'));
    expect(streaming.createStreamTicket).toHaveBeenCalledTimes(1);
  });

  it('cancels delayed decoded setup when the player unmounts', async () => {
    const { unmount } = renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    fireEvent.error(audio);
    fireEvent.click(await screen.findByText('Decode for playback'));
    await waitFor(() => expect(audio.getAttribute('src')).toContain('/transcoded?'));
    streaming.createStreamTicket.mockClear();
    streaming.getPlaybackInfo.mockClear();
    fireEvent.click(screen.getByTestId('player-fast-forward'));
    unmount();
    await act(async () => new Promise((resolve) => window.setTimeout(resolve, 200)));
    expect(streaming.createStreamTicket).not.toHaveBeenCalled();
    expect(streaming.getPlaybackInfo).not.toHaveBeenCalled();
  });

  it('aborts superseded decode metadata while accumulating seeks and preserving Play intent', async () => {
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    fireEvent.error(audio);
    const decode = await screen.findByText('Decode for playback');
    let finishInitialSetup;
    let initialSignal;
    streaming.getPlaybackInfo.mockImplementationOnce((contentId, signal) => {
      initialSignal = signal;
      return new Promise((resolve) => {
        finishInitialSetup = resolve;
      });
    });
    fireEvent.click(decode);
    await waitFor(() => {
      expect(finishInitialSetup).toBeDefined();
      expect(initialSignal).toBeInstanceOf(AbortSignal);
    });
    HTMLMediaElement.prototype.play.mockClear();
    fireEvent.click(screen.getByTestId('player-fast-forward'));
    fireEvent.click(screen.getByTestId('player-fast-forward'));
    expect(initialSignal.aborted).toBe(true);
    await waitFor(() => expect(audio.getAttribute('src')).toContain('startSeconds=60'));
    await waitFor(() => expect(HTMLMediaElement.prototype.play).toHaveBeenCalled());
    await act(async () => finishInitialSetup({ data: { durationSeconds: 120 } }));
    await waitFor(() => expect(audio.getAttribute('src')).toContain('startSeconds=60'));
    expect(screen.getByLabelText('Seek playback')).toHaveAttribute('aria-valuetext', '1:00 of 2:00');
  });

  it('aborts decoded metadata setup when the player unmounts', async () => {
    const { unmount } = renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    fireEvent.error(audio);

    let finishPlaybackInfo;
    let setupSignal;
    streaming.getPlaybackInfo.mockImplementationOnce((contentId, signal) => {
      setupSignal = signal;
      return new Promise((resolve) => { finishPlaybackInfo = resolve; });
    });
    fireEvent.click(await screen.findByText('Decode for playback'));
    await waitFor(() => expect(finishPlaybackInfo).toBeDefined());

    unmount();
    expect(setupSignal).toBeInstanceOf(AbortSignal);
    expect(setupSignal.aborted).toBe(true);
    await act(async () => finishPlaybackInfo({ data: { durationSeconds: 120 } }));
    expect(audio.getAttribute('src')).toBeNull();
  });

  it('keeps pending decoded seeks paused after transport Pause', async () => {
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    fireEvent.error(audio);
    const decode = await screen.findByText('Decode for playback');
    let finishInitialSetup;
    streaming.getPlaybackInfo.mockImplementationOnce(() => new Promise((resolve) => {
      finishInitialSetup = resolve;
    }));
    fireEvent.click(decode);
    await waitFor(() => expect(finishInitialSetup).toBeDefined());
    fireEvent.click(screen.getByTestId('player-toggle-playback'));
    HTMLMediaElement.prototype.play.mockClear();
    fireEvent.click(screen.getByTestId('player-fast-forward'));
    fireEvent.click(screen.getByTestId('player-fast-forward'));
    await waitFor(() => expect(audio.getAttribute('src')).toContain('startSeconds=60'));
    expect(HTMLMediaElement.prototype.play).not.toHaveBeenCalled();
    expect(screen.getByTestId('player-toggle-playback')).toHaveAccessibleName('Resume local playback');
    await act(async () => finishInitialSetup({ data: { durationSeconds: 120 } }));
  });

  it('aborts a pending decoded ticket request when another track is selected', async () => {
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    fireEvent.error(audio);

    let finishTicket;
    let setupSignal;
    streaming.getPlaybackInfo.mockClear();
    streaming.createStreamTicket.mockImplementationOnce((contentId, signal) => {
      setupSignal = signal;
      return new Promise((resolve) => { finishTicket = resolve; });
    });
    fireEvent.click(await screen.findByText('Decode for playback'));
    await waitFor(() => expect(finishTicket).toBeDefined());

    fireEvent.click(screen.getByText('Play second fixture'));
    expect(setupSignal).toBeInstanceOf(AbortSignal);
    expect(setupSignal.aborted).toBe(true);
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Asecond'));

    await act(async () => finishTicket('stale-ticket'));
    expect(audio.getAttribute('src')).toContain('sha256%3Asecond');
    expect(audio.getAttribute('src')).not.toContain('/transcoded?');
    expect(streaming.getPlaybackInfo).not.toHaveBeenCalled();
  });

  it('preserves native pending seek and autoplay across layout remounts', async () => {
    renderPlayer();
    let finishTicket;
    streaming.createStreamTicket.mockImplementationOnce(() => new Promise((resolve) => {
      finishTicket = resolve;
    }));
    fireEvent.click(screen.getByText('Play fixture'));
    await waitFor(() => expect(finishTicket).toBeDefined());
    fireEvent.click(screen.getByTestId('player-fast-forward'));
    fireEvent.click(screen.getByTestId('player-fast-forward'));
    fireEvent.click(screen.getByTestId('player-collapse'));
    HTMLMediaElement.prototype.play.mockClear();
    await act(async () => finishTicket('pending-ticket'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('pending-ticket'));
    await waitFor(() => expect(HTMLMediaElement.prototype.play).toHaveBeenCalled());
    Object.defineProperty(audio, 'duration', { configurable: true, value: 120 });
    fireEvent.loadedMetadata(audio);
    expect(audio.currentTime).toBe(60);
  });

  it('retries failed decoded setup instead of waiting for an absent source', async () => {
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    fireEvent.error(audio);
    const decode = await screen.findByText('Decode for playback');
    streaming.createStreamTicket.mockRejectedValueOnce(new Error('busy'));
    fireEvent.click(decode);
    await screen.findByText(/Decoding could not start/u);
    fireEvent.click(screen.getByTestId('player-toggle-playback'));
    await waitFor(() => expect(audio.getAttribute('src')).toContain('/transcoded?'));
  });

  it('refreshes failed native server media tickets and restores its position', async () => {
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('ticket-1'));
    audio.currentTime = 37;
    Object.defineProperty(audio, 'error', { configurable: true, value: { code: 2 } });
    HTMLMediaElement.prototype.load.mockImplementation(() => {
      Object.defineProperty(audio, 'error', { configurable: true, value: null });
    });
    fireEvent.error(audio);
    streaming.createStreamTicket.mockResolvedValueOnce('fresh-ticket');
    fireEvent.click(screen.getByTestId('player-toggle-playback'));
    await waitFor(() => expect(audio.getAttribute('src')).toContain('fresh-ticket'));
    Object.defineProperty(audio, 'duration', { configurable: true, value: 120 });
    fireEvent.loadedMetadata(audio);
    expect(audio.currentTime).toBe(37);
  });

  it.each(['player-hide', 'player-stop'])('closes a stale Picture-in-Picture window after %s', async (action) => {
    vi.spyOn(audioGraph, 'resumeAudioGraph').mockResolvedValue({});
    let finishWindow;
    const requestWindow = vi.fn(() => new Promise((resolve) => { finishWindow = resolve; }));
    vi.stubGlobal('documentPictureInPicture', { requestWindow });
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    fireEvent.click(screen.getByTestId('player-document-pip'));
    await waitFor(() => expect(finishWindow).toBeDefined());
    fireEvent.click(screen.getByTestId(action));
    const staleWindow = { close: vi.fn() };
    await act(async () => finishWindow(staleWindow));
    expect(staleWindow.close).toHaveBeenCalledOnce();
  });

  it('reports a rejected Picture-in-Picture request without stopping playback', async () => {
    vi.spyOn(audioGraph, 'resumeAudioGraph').mockResolvedValue({});
    const requestWindow = vi.fn(() => Promise.reject(new Error('denied')));
    vi.stubGlobal('documentPictureInPicture', {
      requestWindow,
    });
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    fireEvent.play(audio);
    fireEvent.click(screen.getByTestId('player-document-pip'));
    await screen.findByText(/Picture-in-Picture could not open/u);
    expect(requestWindow).toHaveBeenCalledWith({ height: 220, width: 360 });
    expect(screen.getByTestId('player-toggle-playback')).toHaveAccessibleName('Pause local playback');
    window.documentPictureInPicture.requestWindow.mockImplementationOnce(() => new Promise(() => {}));
    fireEvent.click(screen.getByTestId('player-document-pip'));
    expect(screen.queryByText(/Picture-in-Picture could not open/u)).not.toBeInTheDocument();
  });

  it.each([false, true])('waits for output switching before new playback (failure: %s)', async (failure) => {
    vi.stubGlobal('AudioContext', class {
      setSinkId() {}
    });
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { enumerateDevices: vi.fn(() => Promise.resolve([{ kind: 'audiooutput', deviceId: 'headphones', label: 'Headphones' }])) },
    });
    let finishSwitch;
    let failSwitch;
    const setSinkId = vi.fn(() => Promise.resolve());
    setSinkId.mockImplementationOnce(() => new Promise((resolve, reject) => { finishSwitch = resolve; failSwitch = reject; }));
    const graph = { ctx: { setSinkId } };
    vi.spyOn(audioGraph, 'getExistingAudioGraph').mockReturnValue(graph);
    vi.spyOn(audioGraph, 'getOrCreateAudioGraph').mockReturnValue(graph);
    vi.spyOn(audioGraph, 'resumeAudioGraph').mockResolvedValue(graph);
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(HTMLMediaElement.prototype.play).toHaveBeenCalledOnce());
    const output = await screen.findByLabelText('Audio output device');
    HTMLMediaElement.prototype.play.mockClear();
    fireEvent.change(output, { target: { value: 'headphones' } });
    expect(output).toBeDisabled();
    expect(setSinkId).toHaveBeenCalledWith('headphones');
    fireEvent.click(screen.getByText('Play second fixture'));
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Asecond'));
    expect(HTMLMediaElement.prototype.play).not.toHaveBeenCalled();
    await act(async () => {
      if (failure) failSwitch(new Error('Device unavailable'));
      else finishSwitch();
    });
    await waitFor(() => expect(HTMLMediaElement.prototype.play).toHaveBeenCalledOnce());
    expect(output).toBeEnabled();
    expect(output).toHaveValue(failure ? 'default' : 'headphones');
    expect(setSinkId).toHaveBeenLastCalledWith(failure ? '' : 'headphones');
    expect(screen.queryByText('Could not switch audio output device.') !== null).toBe(failure);
  });

  it('clears stale Media Session position after Stop', async () => {
    const setPositionState = vi.fn();
    Object.defineProperty(navigator, 'mediaSession', {
      configurable: true,
      value: { setActionHandler: vi.fn(), setPositionState },
    });
    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));
    Object.defineProperty(audio, 'duration', { configurable: true, value: 120 });
    fireEvent.loadedMetadata(audio);
    expect(setPositionState).toHaveBeenLastCalledWith(expect.objectContaining({ duration: 120 }));
    fireEvent.click(screen.getByTestId('player-stop'));
    expect(setPositionState).toHaveBeenLastCalledWith();
  });

  it('mutes local browser playback without clearing the stream source', async () => {
    renderPlayer();

    fireEvent.click(screen.getByText('Play fixture'));

    const audio = document.querySelector('audio');
    await waitFor(() => {
      const src = audio.getAttribute('src') || '';
      expect(src).toContain(
        '/api/v0/streams/sha256%3Atest',
      );
    });

    fireEvent.click(screen.getByTestId('player-toggle-mute'));

    expect(audio.muted).toBe(true);
    expect(audio.getAttribute('src')).toContain(
      '/api/v0/streams/sha256%3Atest',
    );
    expect(window.localStorage.getItem('slskdn.player.localMuted')).toBe('true');
  });

  it('hides the player, keeps a restore control, and rejects playback when disabled', () => {
    window.localStorage.setItem(
      'slskdn:experience-preferences:v1',
      JSON.stringify({ playerVisible: false }),
    );

    renderPlayer();

    expect(screen.getByTestId('player-show')).toBeInTheDocument();
    expect(document.querySelector('audio')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Play fixture'));

    expect(document.querySelector('audio')).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('player-show'));
    expect(screen.getByTestId('player-hide')).toBeInTheDocument();
  });

  it('toggles player visibility from the player surface', () => {
    renderPlayer();

    fireEvent.click(screen.getByTestId('player-hide'));

    expect(screen.getByTestId('player-show')).toBeInTheDocument();
    expect(
      JSON.parse(window.localStorage.getItem('slskdn:experience-preferences:v1')),
    ).toEqual({ playerVisible: false });

    fireEvent.click(screen.getByTestId('player-show'));
    expect(screen.getByTestId('player-hide')).toBeInTheDocument();
  });

  it('does not clear now-playing on startup when the player was already hidden', () => {
    window.localStorage.setItem(
      'slskdn:experience-preferences:v1',
      JSON.stringify({ playerVisible: false }),
    );

    renderPlayer();

    expect(screen.getByTestId('player-show')).toBeInTheDocument();
    expect(nowPlaying.clearNowPlaying).not.toHaveBeenCalled();
  });

  it('restores the local mute preference for the PWA/browser session', () => {
    window.localStorage.setItem('slskdn.player.localMuted', 'true');

    renderPlayer();
    fireEvent.click(screen.getByText('Play fixture'));

    expect(document.querySelector('audio').muted).toBe(true);
  });

  it('opens collection and local file browser modals before playback starts', async () => {
    renderPlayer();

    expect(
      screen.getByTestId('player-open-collections-browser'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('player-open-file-browser')).toBeInTheDocument();
    await screen.findByText('Pick a collection or local audio file');

    fireEvent.click(screen.getByTestId('player-open-collections-browser'));
    expect(
      screen.getByTestId('player-collection-browser-modal'),
    ).toBeInTheDocument();
    fireEvent.click(await screen.findByTestId('player-collection-row-collection-1'));
    expect(await screen.findByText('Collection stream.ogg')).toBeInTheDocument();
    expect(screen.getByRole('button', {
      name: 'Play Collection stream.ogg from this collection',
    })).toBeInTheDocument();

    fireEvent.click(screen.getAllByText('Close')[0]);
    fireEvent.click(screen.getByTestId('player-open-file-browser'));
    expect(screen.getByTestId('player-file-browser-modal')).toBeInTheDocument();
    expect(await screen.findByText('Downloads')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('player-file-folder-Downloads'));
    expect(await screen.findByText('Library stream.ogg')).toBeInTheDocument();
  });

  it('ignores malformed player collection and browser list payloads', async () => {
    collectionsAPI.getCollections.mockResolvedValueOnce({ data: { items: [] } });
    collectionsAPI.browseLibraryItems.mockResolvedValueOnce({
      data: {
        breadcrumbs: { path: '' },
        directories: { name: 'Downloads' },
        files: { fileName: 'Library stream.ogg' },
      },
    });

    renderPlayer();

    fireEvent.click(screen.getByTestId('player-open-collections-browser'));
    expect(
      screen.getByTestId('player-collection-browser-modal'),
    ).toBeInTheDocument();
    expect(screen.queryByText('Favorites')).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByText('Close')[0]);
    fireEvent.click(screen.getByTestId('player-open-file-browser'));
    expect(screen.getByTestId('player-file-browser-modal')).toBeInTheDocument();

    await waitFor(() => {
      expect(collectionsAPI.browseLibraryItems).toHaveBeenCalled();
    });
    expect(screen.queryByText('Downloads')).not.toBeInTheDocument();
    expect(screen.queryByText('Library stream.ogg')).not.toBeInTheDocument();
  });

  it('searches the local file browser as a deduplicated explorer', async () => {
    renderPlayer();

    fireEvent.click(screen.getByTestId('player-open-file-browser'));
    fireEvent.change(screen.getByTestId('player-file-browser-search').querySelector('input'), {
      target: { value: 'library' },
    });

    expect(await screen.findByText('Library stream.ogg')).toBeInTheDocument();
    expect(screen.getByText(/2 duplicates collapsed/u)).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('switches the visual tile from album art to the MilkDrop canvas', async () => {
    renderPlayer();

    expect(screen.getByTestId('player-album-art')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('player-visual-tile'));

    await waitFor(() =>
      expect(document.querySelector('.player-visualizer-canvas')).toBeInTheDocument());
    expect(screen.queryByTestId('player-album-art')).not.toBeInTheDocument();
  });

  it('cycles the visual tile through visualizer and analyzer variants', async () => {
    renderPlayer();

    const tile = screen.getByTestId('player-visual-tile');

    fireEvent.click(tile);
    await waitFor(() =>
      expect(window.localStorage.getItem('slskdn.player.visualTileMode')).toBe('butterchurn'));
    await waitFor(() =>
      expect(document.querySelector('.player-visualizer-canvas')).toBeInTheDocument());

    fireEvent.click(tile);
    await waitFor(() =>
      expect(window.localStorage.getItem('slskdn.player.visualTileMode')).toBe('native-webgl2'));

    fireEvent.click(tile);
    await waitFor(() =>
      expect(window.localStorage.getItem('slskdn.player.visualTileMode')).toBe('native-webgpu'));

    fireEvent.click(tile);
    await waitFor(() =>
      expect(window.localStorage.getItem('slskdn.player.visualTileMode')).toBe('spectrum'));
    expect(within(tile).getByLabelText('Spectrum analyzer')).toBeInTheDocument();

    fireEvent.click(tile);
    await waitFor(() =>
      expect(window.localStorage.getItem('slskdn.player.visualTileMode')).toBe('scope'));
    expect(within(tile).getByLabelText('Oscilloscope')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('player-visual-tile-mode-butterchurn'));
    await waitFor(() =>
      expect(window.localStorage.getItem('slskdn.player.visualTileMode')).toBe('butterchurn'));
  });

  it('shows tile-level visualizer maximize controls even while analyzer bars are active', async () => {
    renderPlayer();
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native-webgl2');

    fireEvent.click(screen.getByTestId('player-visual-tile-mode-spectrum'));

    await waitFor(() =>
      expect(window.localStorage.getItem('slskdn.player.visualTileMode')).toBe('spectrum'));

    fireEvent.click(screen.getByTestId('player-visual-tile-mode-butterchurn'));
    await waitFor(() =>
      expect(window.localStorage.getItem('slskdn.player.visualTileMode')).toBe('butterchurn'));

    fireEvent.click(screen.getByTestId('player-visual-tile-mode-spectrum'));
    await waitFor(() =>
      expect(window.localStorage.getItem('slskdn.player.visualTileMode')).toBe('spectrum'));

    fireEvent.click(screen.getByTestId('player-visual-tile-fullwindow'));

    await waitFor(() => {
      expect(window.localStorage.getItem('slskdn.player.visualTileMode')).toBe('native-webgl2');
    });
    expect(document.querySelector('.player-visualizer-fullwindow')).toBeInTheDocument();
  });

  it('pauses analyzer motion until the user opts in under reduced motion', () => {
    window.matchMedia = vi.fn(() => ({
      addEventListener: vi.fn(),
      matches: true,
      media: '(prefers-reduced-motion: reduce)',
      removeEventListener: vi.fn(),
    }));
    window.localStorage.setItem('slskdn.player.analyzerMode.v2', 'spectrum');
    renderPlayer();

    const analyzerTile = screen.getByTestId('player-analyzer-tile');
    expect(analyzerTile).toHaveAttribute('aria-label', expect.stringContaining('reduced motion'));
    expect(screen.getByText('Reduced motion')).toBeInTheDocument();
    expect(within(analyzerTile).getByTestId('player-spectrum'))
      .toHaveAttribute('data-motion-suppressed', 'true');

    fireEvent.click(screen.getByTestId('player-analyzer-motion-override'));

    expect(screen.queryByText('Reduced motion')).not.toBeInTheDocument();
    expect(within(analyzerTile).getByTestId('player-spectrum'))
      .not.toHaveAttribute('data-motion-suppressed');
  });

  it('lets the visual tile opt into analyzer animation for the current selection', () => {
    window.matchMedia = vi.fn(() => ({
      addEventListener: vi.fn(),
      matches: true,
      media: '(prefers-reduced-motion: reduce)',
      removeEventListener: vi.fn(),
    }));
    renderPlayer();

    fireEvent.click(screen.getByTestId('player-visual-tile-mode-spectrum'));

    const tile = screen.getByTestId('player-visual-tile');
    expect(screen.getByText('Paused', { exact: true })).toBeInTheDocument();
    expect(within(tile).getByTestId('player-spectrum'))
      .toHaveAttribute('data-motion-suppressed', 'true');

    fireEvent.click(screen.getByTestId('player-visual-tile-motion-override'));

    expect(screen.queryByText('Paused', { exact: true })).not.toBeInTheDocument();
    expect(within(tile).getByTestId('player-spectrum'))
      .not.toHaveAttribute('data-motion-suppressed');
  });

  it('does not repeat the currently playing track in the queue preview', () => {
    renderPlayer();

    fireEvent.click(screen.getByText('Play fixture'));

    expect(screen.getByText('Local stream')).toBeInTheDocument();
    expect(document.querySelector('.player-queue')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Play second fixture'));

    expect(screen.getByText('Second stream')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Queue prior fixtures'));
    expect(screen.getByText('Local stream')).toBeInTheDocument();
    expect(document.querySelector('.player-queue')?.textContent).not.toContain(
      'Second stream',
    );
  });

  it('makes ListenBrainz autosave explicit and clearable', async () => {
    renderPlayer();

    fireEvent.click(screen.getByTestId('player-open-integrations'));
    const tokenInput = screen.getByLabelText('ListenBrainz user token');

    fireEvent.change(tokenInput, { target: { value: ' token-1 ' } });

    expect(screen.getByTestId('player-listenbrainz-save-state')).toHaveTextContent(
      'saved automatically',
    );
    expect(window.sessionStorage.getItem('slskdn.listenbrainz.token')).toBe('token-1');
    expect(screen.getByTestId('player-close-integrations')).toHaveTextContent('Done');

    const clearTokenButton = screen.getByTestId('player-clear-listenbrainz-token');
    fireEvent.mouseEnter(clearTokenButton);
    expect(await screen.findByText(
      'Remove the saved ListenBrainz token from this browser session. You can enter a new token at any time.',
    )).toBeInTheDocument();
    fireEvent.click(clearTokenButton);

    expect(tokenInput).toHaveValue('');
    expect(window.sessionStorage.getItem('slskdn.listenbrainz.token')).toBeNull();
  });

  it('shows and launches the configured external visualizer', async () => {
    renderPlayer();

    fireEvent.click(screen.getByTestId('player-open-integrations'));

    expect(
      await screen.findByText('Ready to launch on the slskdN host.'),
    ).toBeInTheDocument();
    expect(screen.getByText('/opt/MilkDrop3/MilkDrop 3.exe')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('player-launch-external-visualizer'));

    await waitFor(() => {
      expect(externalVisualizer.launchExternalVisualizer).toHaveBeenCalled();
    });
    expect(await screen.findByText('MilkDrop3 launched.')).toBeInTheDocument();
  });

  it('shows now-playing source badges and stores local discovery ratings', async () => {
    renderPlayer();

    fireEvent.click(screen.getByText('Play fixture'));

    expect(await screen.findByTestId('player-badge-source-Mesh')).toHaveTextContent(
      'Mesh',
    );
    expect(screen.getByTestId('player-badge-source-Soulseek')).toHaveTextContent(
      'Soulseek',
    );
    expect(screen.getByTestId('player-badge-confidence')).toHaveTextContent(
      '91% match',
    );
    expect(screen.getByTestId('player-badge-verified')).toHaveTextContent(
      'Verified',
    );

    fireEvent.click(screen.getByTestId('player-rating-5'));
    expect(screen.getByTestId('player-rating-5')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('player-rating-4')).toHaveAttribute('aria-pressed', 'false');

    expect(screen.getByTestId('player-rating-controls')).toHaveTextContent(
      'Discovery boost',
    );
    expect(window.localStorage.getItem('slskdn.player.ratings')).toContain(
      '"content:sha256:test":5',
    );
    expect(window.localStorage.getItem('slskdn.discovery.shelf')).toContain(
      '"action":"promote-preview"',
    );

    fireEvent.click(screen.getByTestId('player-open-discovery-shelf'));

    expect(await screen.findByText('Discovery Shelf')).toBeInTheDocument();
    expect(screen.getByTestId('player-shelf-summary')).toHaveTextContent(
      '1local review items',
    );
    expect(screen.getByTestId('player-shelf-row-content:sha256:test')).toHaveTextContent(
      'Promote preview',
    );
    expect(screen.getByRole('button', { name: 'Preview Local stream' }))
      .toBeInTheDocument();
    expect(screen.getByRole('button', {
      name: 'Remove Local stream from the discovery shelf',
    })).toBeInTheDocument();
    expect(screen.getByTestId('player-shelf-policy-preview')).toHaveTextContent(
      '1 promote',
    );
    expect(screen.getByTestId('player-shelf-policy-preview')).toHaveTextContent(
      '0 consensus gated',
    );
    fireEvent.click(screen.getByTestId('player-shelf-copy-policy-report'));
    expect(screen.getByText('Policy report prepared for 1 shelf items.')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('player-shelf-preview-content:sha256:test'));
    expect(screen.getByText('Promote preview prepared for Local stream. No files were moved or deleted.')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('player-close-discovery-shelf'));

    fireEvent.click(screen.getByTestId('player-rating-5'));
    expect(screen.getByTestId('player-rating-5')).toHaveAttribute('aria-pressed', 'false');

    expect(screen.getByTestId('player-rating-controls')).toHaveTextContent(
      'Not rated',
    );
  });

  it('ignores malformed now-playing source and tag lists', async () => {
    renderPlayer();

    fireEvent.click(screen.getByText('Play malformed fixture'));

    expect(await screen.findByText('Malformed stream')).toBeInTheDocument();
    expect(screen.queryByTestId('player-badge-source-Mesh')).not.toBeInTheDocument();
  });

  it('handles player keyboard shortcuts without stealing input typing', async () => {
    renderPlayer();

    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => {
      expect(audio.getAttribute('src')).toContain('/api/v0/streams/sha256%3Atest');
    });

    fireEvent.keyDown(window, { key: 'm' });
    expect(audio.muted).toBe(true);

    fireEvent.keyDown(window, { key: 'e' });
    expect(document.querySelector('.player-panel-eq')).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'v' });
    await waitFor(() =>
      expect(document.querySelector('.player-visualizer-canvas')).toBeInTheDocument());

    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(audio.currentTime).toBe(30);

    fireEvent.click(screen.getByTestId('player-open-integrations'));
    const tokenInput = screen.getByLabelText('ListenBrainz user token');
    fireEvent.keyDown(tokenInput, { key: 'm' });

    expect(audio.muted).toBe(true);
  });

  it('opens smart radio seeds without starting a search automatically', async () => {
    renderPlayer();

    fireEvent.click(screen.getByText('Play fixture'));
    fireEvent.click(screen.getByTestId('player-open-radio'));

    expect(await screen.findByText('Smart Radio Seed')).toBeInTheDocument();
    expect(screen.getByTestId('player-radio-seed')).toHaveTextContent(
      'slskdN - Local stream',
    );
    expect(screen.getByText('Similar track seed')).toBeInTheDocument();
    expect(screen.getByText('slskdN Local stream')).toBeInTheDocument();
    expect(screen.getByText('Album neighborhood')).toBeInTheDocument();
    expect(screen.getByText('slskdN Fixture Album')).toBeInTheDocument();
    expect(screen.getByText('Artist and genre seed')).toBeInTheDocument();
    expect(screen.getByText('slskdN Fixture Genre')).toBeInTheDocument();
    expect(searches.createBatch).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('player-radio-start-searches'));
    await waitFor(() => {
      expect(searches.createBatch).toHaveBeenCalledWith({
        queries: [
          'slskdN Local stream',
          'slskdN Fixture Album',
          'slskdN Fixture Genre',
        ],
      });
    });
    expect(screen.getByText('Started 3 smart-radio searches.')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('player-radio-add-wishlist'));
    await waitFor(() => {
      expect(wishlistAPI.create).toHaveBeenCalledWith(
        expect.objectContaining({
          autoDownload: false,
          enabled: true,
          searchText: 'slskdN Local stream',
        }),
      );
    });
    expect(screen.getByText('Added 4 smart-radio seeds to Wishlist.')).toBeInTheDocument();

    expect(screen.queryByTestId('player-radio-send-inbox')).not.toBeInTheDocument();
  });

  it('manages the playback queue without removing the current track', async () => {
    renderPlayer();

    fireEvent.click(screen.getByText('Play fixture'));
    fireEvent.click(screen.getByText('Play second fixture'));
    fireEvent.click(screen.getByText('Play third fixture'));
    fireEvent.click(screen.getByText('Queue prior fixtures'));
    fireEvent.click(screen.getByTestId('player-open-queue'));

    expect(await screen.findByText('Playback Queue')).toBeInTheDocument();
    expect(screen.getByText('Now Playing')).toBeInTheDocument();
    expect(screen.getAllByText('Third stream')).toHaveLength(2);
    expect(screen.getByTestId('player-queue-row-sha256:second')).toHaveTextContent(
      'Second stream',
    );
    expect(screen.getByTestId('player-queue-row-sha256:test')).toHaveTextContent(
      'Local stream',
    );
    expect(screen.getByText('Recent')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('player-remove-queue-sha256:second'));

    expect(screen.queryByTestId('player-queue-row-sha256:second')).not.toBeInTheDocument();
    expect(screen.getAllByText('Third stream')).toHaveLength(2);

    fireEvent.click(screen.getByTestId('player-clear-upcoming'));

    expect(screen.getByText('No upcoming tracks.')).toBeInTheDocument();
    expect(screen.getAllByText('Third stream')).toHaveLength(2);

    fireEvent.click(screen.getByTestId('player-search-similar-candidates'));
    await waitFor(() => {
      expect(searches.createBatch).toHaveBeenCalledWith({
        queries: ['slskdN Second stream', 'slskdN Local stream'],
      });
    });
    expect(screen.getByText('Started 3 similar-track searches.')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('player-wishlist-similar-candidates'));
    await waitFor(() => {
      expect(wishlistAPI.create).toHaveBeenCalledWith(
        expect.objectContaining({
          autoDownload: false,
          enabled: true,
          searchText: 'slskdN Second stream',
        }),
      );
    });
    expect(screen.getByText('Added 2 similar-track seeds to Wishlist.')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('player-auto-queue-similar'));

    expect(screen.getByTestId('player-queue-row-sha256:second')).toHaveTextContent(
      'Second stream',
    );
    expect(screen.getByTestId('player-queue-row-sha256:test')).toHaveTextContent(
      'Local stream',
    );
  });

  it('records local listening history and shows browser stats', async () => {
    renderPlayer();

    fireEvent.click(screen.getByText('Play fixture'));
    const audio = document.querySelector('audio');
    await waitFor(() => expect(audio.getAttribute('src')).toContain('sha256%3Atest'));

    Object.defineProperty(audio, 'duration', {
      configurable: true,
      value: 120,
    });
    Object.defineProperty(audio, 'paused', {
      configurable: true,
      value: false,
    });
    fireEvent.play(audio);
    Object.defineProperty(audio, 'currentTime', {
      configurable: true,
      value: 61,
      writable: true,
    });
    fireEvent.timeUpdate(audio);

    fireEvent.click(screen.getByTestId('player-open-listening-stats'));

    expect(await screen.findByText('Listening Stats')).toBeInTheDocument();
    expect(screen.getByTestId('player-stats-summary')).toHaveTextContent(
      '1local plays recorded',
    );
    expect(screen.getByText('Top Artists')).toBeInTheDocument();
    expect(screen.getByText('Top Genres')).toBeInTheDocument();
    expect(screen.getByText('Recommendation Seeds')).toBeInTheDocument();
    expect(screen.getAllByText('slskdN').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Fixture Genre').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Local stream').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByTestId('player-stats-search-seed-Fixture Genre')).toBeInTheDocument();

    expect(
      screen.queryByTestId('player-stats-send-seeds-to-discovery-inbox'),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('player-stats-start-seed-searches'));
    await waitFor(() => {
      expect(searches.createBatch).toHaveBeenCalledWith({
        queries: expect.arrayContaining(['Fixture Genre', 'Local stream']),
      });
    });
    expect(screen.getByText('Started 3 bounded listening seed searches.')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('player-stats-add-seeds-to-wishlist'));
    await waitFor(() => {
      expect(wishlistAPI.create).toHaveBeenCalledWith(
        expect.objectContaining({
          autoDownload: false,
          enabled: true,
          searchText: 'Fixture Genre',
        }),
      );
    });
    expect(screen.getByText(/Added .* listening seeds to Wishlist/)).toBeInTheDocument();

    window.sessionStorage.setItem('slskdn.listenbrainz.token', 'token-1');
    fireEvent.click(screen.getByTestId('player-listening-history-scrobble-recent'));
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        'https://api.listenbrainz.org/1/submit-listens',
        expect.objectContaining({
          method: 'POST',
        }),
      );
    });
    expect(screen.getByText('Submitted 1 recent listen to ListenBrainz.')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('player-clear-listening-history'));

    expect(screen.getByTestId('player-stats-summary')).toHaveTextContent(
      '0local plays recorded',
    );
  });

  it('imports pasted media-server listening history into browser stats', async () => {
    renderPlayer();

    const importedAt = new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString();

    fireEvent.click(screen.getByText('Play fixture'));
    fireEvent.click(screen.getByTestId('player-open-listening-stats'));

    expect(await screen.findByText('Listening Stats')).toBeInTheDocument();

    fireEvent.change(screen.getByTestId('player-listening-history-import-text'), {
      target: {
        value: [
          'playedAt,artist,album,title,genre',
          `${importedAt},Imported Artist,Imported Album,Imported Track,Imported Genre`,
        ].join('\n'),
      },
    });
    fireEvent.click(screen.getByTestId('player-listening-history-import'));

    expect(screen.getByText('1 imported, 0 skipped as duplicates or incomplete rows.')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId('player-stats-summary')).toHaveTextContent(
        '1local plays recorded',
      );
    });
    expect(screen.getAllByText('Imported Artist').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Imported Genre').length).toBeGreaterThanOrEqual(1);
  });
});
