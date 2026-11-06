import {
  addPlaylistIntake,
  applyPlaylistIntakeRefresh,
  approvePlaylistTagOrganizationPlan,
  buildPlaylistCollectionItems,
  buildPlaylistDiscoverySeed,
  buildPlaylistDiscoverySeeds,
  buildPlaylistCompletionSummary,
  buildPlaylistIntakeSummary,
  buildPlaylistProviderRefreshContent,
  buildPlaylistRefreshDiff,
  buildPlaylistTagOrganizationPlan,
  buildSlskdPlaylistPreview,
  clearPlaylistTagOrganizationApproval,
  formatPlaylistTagOrganizationReport,
  getDuePlaylistRefreshes,
  getPlaylistIntakes,
  playlistIntakeStorageKey,
  previewPlaylistTagOrganizationPlan,
  previewPlaylistIntakeRefresh,
  scorePlaylistTrackCandidate,
  updatePlaylistIntakeTrackState,
  updatePlaylistRefreshAutomation,
} from './playlistIntake';

describe('playlistIntake', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('imports browser-local playlist text while retaining source identity', () => {
    addPlaylistIntake({
      content: 'Stereolab - French Disko\nBroadcast - Come On Let\'s Go\nUntitled',
      mirrorEnabled: true,
      name: 'Test imports',
      source: 'local:test-imports.m3u',
    });

    const [playlist] = getPlaylistIntakes();

    expect(playlist).toMatchObject({
      mirrorEnabled: true,
      name: 'Test imports',
      provider: 'M3U',
      refreshAutomationEnabled: false,
      refreshCadence: 'Manual review',
      refreshCooldownDays: 7,
      source: 'local:test-imports.m3u',
      state: 'Staged',
    });
    expect(playlist.tracks).toHaveLength(3);
    expect(playlist.tracks[0]).toMatchObject({
      artist: 'Stereolab',
      lineNumber: 1,
      state: 'Matched',
      title: 'French Disko',
    });
    expect(playlist.tracks[2]).toMatchObject({
      artist: '',
      state: 'Unmatched',
      title: 'Untitled',
    });
  });

  it('summarizes mirrored playlists and unmatched tracks', () => {
    expect(
      buildPlaylistIntakeSummary([
        {
          mirrorEnabled: true,
          tracks: [
            { state: 'Matched' },
            { state: 'Unmatched' },
          ],
        },
        {
          mirrorEnabled: false,
          tracks: [{ state: 'Unmatched' }],
        },
      ]),
    ).toMatchObject({
      mirrored: 1,
      total: 2,
      tracks: 3,
      unmatched: 2,
    });
  });

  it('updates track review state for unmatch and rematch workflows', () => {
    addPlaylistIntake({
      content: 'Stereolab - French Disko',
      name: 'Review queue',
      source: 'local:review.txt',
    });
    const [playlist] = getPlaylistIntakes();
    const [track] = playlist.tracks;

    updatePlaylistIntakeTrackState(playlist.id, track.id, 'Unmatched');
    expect(getPlaylistIntakes()[0].tracks[0]).toMatchObject({
      state: 'Unmatched',
    });

    updatePlaylistIntakeTrackState(playlist.id, track.id, 'Matched');
    expect(getPlaylistIntakes()[0].tracks[0]).toMatchObject({
      state: 'Matched',
    });
  });

  it('ignores malformed persisted playlists and nested track entries', () => {
    localStorage.setItem(
      playlistIntakeStorageKey,
      JSON.stringify([
        null,
        'bad',
        ['bad'],
        {
          name: 'Valid playlist',
          source: 'local:valid.txt',
          tracks: [
            null,
            'bad',
            ['bad'],
            {
              artist: 'Broadcast',
              title: 'Come On Let\'s Go',
            },
          ],
        },
      ]),
    );

    expect(getPlaylistIntakes()).toEqual([
      expect.objectContaining({
        name: 'Valid playlist',
        tracks: [
          expect.objectContaining({
            artist: 'Broadcast',
            title: 'Come On Let\'s Go',
          }),
        ],
      }),
    ]);
  });

  it('previews mirrored playlist refresh diffs without mutating rows', () => {
    addPlaylistIntake({
      content: 'Stereolab - French Disko\nBroadcast - Come On Let\'s Go',
      mirrorEnabled: true,
      name: 'Mirror queue',
      source: 'local:mirror.m3u',
    });
    const [playlist] = getPlaylistIntakes();

    expect(
      buildPlaylistRefreshDiff(
        playlist,
        'Broadcast - Come On Let\'s Go\nPram - Track of the Cat',
      ),
    ).toMatchObject({
      addedCount: 1,
      changedCount: 2,
      removedCount: 1,
      totalIncoming: 2,
      unchangedCount: 1,
    });

    previewPlaylistIntakeRefresh(
      playlist.id,
      'Broadcast - Come On Let\'s Go\nPram - Track of the Cat',
    );

    const [updated] = getPlaylistIntakes();
    expect(updated.tracks).toHaveLength(2);
    expect(updated.refreshDiff).toMatchObject({
      addedCount: 1,
      changedCount: 2,
      removedCount: 1,
      unchangedCount: 1,
    });
    expect(updated.refreshPreview).toMatch(/1 added, 1 removed, 2 changed/i);
  });

  it('summarizes partial completion state', () => {
    expect(
      buildPlaylistCompletionSummary({
        tracks: [
          { state: 'Matched' },
          { state: 'Unmatched' },
          { state: 'Rejected' },
        ],
      }),
    ).toMatchObject({
      Matched: 1,
      Rejected: 1,
      Unmatched: 1,
      total: 3,
    });
  });

  it('builds review-only Discovery Inbox seeds from playlist rows', () => {
    const seed = buildPlaylistDiscoverySeed(
      {
        id: 'playlist-1',
        name: 'Road trip',
        provider: 'Local text',
      },
      {
        artist: 'Broadcast',
        lineNumber: 2,
        title: 'Come On Let\'s Go',
      },
    );

    expect(seed).toMatchObject({
      evidenceKey: 'playlist:playlist-1:2:come on let\'s go',
      searchText: 'Broadcast Come On Let\'s Go',
      source: 'Playlist Intake',
      sourceId: 'playlist-1',
      title: 'Broadcast - Come On Let\'s Go',
    });
    expect(seed.networkImpact).toMatch(/no provider fetch/i);
  });

  it('builds bulk Discovery Inbox seeds and slskdN playlist previews without mutations', () => {
    const playlist = {
      id: 'playlist-2',
      name: 'Review set',
      provider: 'Local text',
      tracks: [
        {
          artist: 'Stereolab',
          lineNumber: 1,
          state: 'Matched',
          title: 'French Disko',
        },
        {
          artist: 'Broadcast',
          lineNumber: 2,
          state: 'Unmatched',
          title: 'Come On Let\'s Go',
        },
        {
          artist: 'Rejected Artist',
          lineNumber: 3,
          state: 'Rejected',
          title: 'Skip Me',
        },
      ],
    };

    expect(buildPlaylistDiscoverySeeds(playlist)).toHaveLength(2);

    expect(buildSlskdPlaylistPreview(playlist)).toMatchObject({
      lineCount: 1,
      name: 'Review set',
      text: '# Review set\n1. Stereolab - French Disko',
    });
    expect(buildSlskdPlaylistPreview(playlist).networkImpact).toMatch(
      /writes a playlist Collection locally/i,
    );
  });

  it('enables scheduled refreshes and applies refresh rows locally', () => {
    addPlaylistIntake({
      content: 'Stereolab - French Disko',
      mirrorEnabled: true,
      name: 'Scheduled mirror',
      source: 'https://open.spotify.com/playlist/test',
    });
    let [playlist] = getPlaylistIntakes();

    updatePlaylistRefreshAutomation(playlist.id, {
      cooldownDays: 1,
      enabled: true,
    });
    [playlist] = getPlaylistIntakes();

    expect(playlist.refreshAutomationEnabled).toBe(true);
    expect(playlist.refreshNextRunAt).toBeTruthy();
    expect(
      getDuePlaylistRefreshes([playlist], Date.parse(playlist.refreshNextRunAt)),
    ).toHaveLength(1);

    applyPlaylistIntakeRefresh(
      playlist.id,
      'Stereolab - French Disko\nPram - Track of the Cat',
      { sourceLabel: 'provider refresh' },
    );

    [playlist] = getPlaylistIntakes();
    expect(playlist).toMatchObject({
      refreshAutomationEnabled: true,
      state: 'Mirrored',
    });
    expect(playlist.tracks).toHaveLength(2);
    expect(playlist.refreshPreview).toMatch(/Applied provider refresh/i);
  });

  it('builds provider refresh content and planned collection items', () => {
    expect(
      buildPlaylistProviderRefreshContent({
        suggestions: [
          { artist: 'Stereolab', title: 'French Disko' },
          { searchText: 'Untitled Provider Row' },
        ],
      }),
    ).toBe('Stereolab - French Disko\nUntitled Provider Row');
    expect(
      buildPlaylistProviderRefreshContent({
        suggestions: { 0: { searchText: 'Not a real list' }, length: 1 },
      }),
    ).toBe('');

    expect(
      buildPlaylistCollectionItems({
        id: 'playlist-3',
        title: 'Radio Picks',
        tracks: [
          {
            artist: 'Stereolab',
            id: 'track-1',
            lineNumber: 1,
            state: 'Matched',
            title: 'French Disko',
          },
          {
            id: 'track-2',
            lineNumber: 2,
            state: 'Unmatched',
            title: 'Skip',
          },
        ],
      }),
    ).toEqual([
      {
        album: 'Radio Picks',
        artist: 'Stereolab',
        contentId: 'playlist-intake:playlist-3:1:track-1',
        fileName: 'Stereolab - Radio Picks - French Disko',
        mediaKind: 'PlannedTrack',
        title: 'French Disko',
      },
    ]);
  });

  it('reuses the shared metadata matcher for playlist candidate review', () => {
    const match = scorePlaylistTrackCandidate(
      {
        artist: 'Beyonce',
        title: 'Deja Vu',
      },
      {
        artist: 'Beyoncé',
        title: 'Déjà Vu',
      },
    );

    expect(match).toEqual(
      expect.objectContaining({
        band: expect.any(String),
        titleScore: 1,
      }),
    );
  });

  it('builds tag and organization dry-run plans from matched playlist rows', () => {
    const plan = buildPlaylistTagOrganizationPlan(
      {
        name: 'Review set',
        tracks: [
          {
            artist: 'Stereolab and Broadcast',
            id: 'track-1',
            lineNumber: 1,
            sourceLine: 'Stereolab and Broadcast - French Disko',
            state: 'Matched',
            title: 'French Disko',
          },
          {
            artist: '',
            id: 'track-2',
            lineNumber: 2,
            sourceLine: 'Untitled',
            state: 'Unmatched',
            title: 'Untitled',
          },
          {
            artist: 'Rejected Artist',
            id: 'track-3',
            lineNumber: 3,
            state: 'Rejected',
            title: 'Skip Me',
          },
        ],
      },
      {
        albumTitle: 'Road Trip',
        coverArtPolicy: 'embed',
        multiArtistPolicy: 'split',
        pathTemplate: '{album}/{trackNumber} - {artist} - {title}',
        replayGainPolicy: 'album',
      },
    );

    expect(plan).toMatchObject({
      coverArtAction: expect.stringMatching(/embedded/i),
      replayGainAction: expect.stringMatching(/Album ReplayGain/i),
      summary: {
        changedFieldCount: 4,
        matched: 1,
        skipped: 1,
        total: 2,
      },
    });
    expect(plan.networkImpact).toMatch(/no tag write/i);
    expect(plan.trackPreviews[0]).toEqual(
      expect.objectContaining({
        destinationPath: 'Road Trip/01 - Stereolab; Broadcast - French Disko.flac',
        metadataSnapshot: expect.objectContaining({
          proposed: expect.objectContaining({
            album: 'Road Trip',
          }),
          source: expect.objectContaining({
            artist: 'Stereolab and Broadcast',
          }),
        }),
        tagPreview: expect.objectContaining({
          artist: ['Stereolab', 'Broadcast'],
          album: 'Road Trip',
        }),
      }),
    );
  });

  it('persists playlist organization previews without changing track states', () => {
    addPlaylistIntake({
      content: 'Stereolab - French Disko\nUntitled',
      name: 'Organization queue',
      source: 'local:organization.txt',
    });
    const [playlist] = getPlaylistIntakes();

    previewPlaylistTagOrganizationPlan(playlist.id, {
      albumTitle: 'Organization Album',
      pathTemplate: '{playlist}/{trackNumber} - {artist} - {title}',
    });

    const [updated] = getPlaylistIntakes();
    expect(updated.organizationOptions).toMatchObject({
      albumTitle: 'Organization Album',
      pathTemplate: '{playlist}/{trackNumber} - {artist} - {title}',
    });
    expect(updated.organizationPlan.summary).toMatchObject({
      matched: 1,
      skipped: 1,
    });
    expect(updated.tracks.map((track) => track.state)).toEqual([
      'Matched',
      'Unmatched',
    ]);
  });

  it('formats and approves tag organization snapshots without writing tags', () => {
    addPlaylistIntake({
      content: 'Stereolab - French Disko\nUntitled',
      name: 'Snapshot queue',
      source: 'local:snapshot.txt',
    });
    let [playlist] = getPlaylistIntakes();
    previewPlaylistTagOrganizationPlan(playlist.id, {
      albumTitle: 'Snapshot Album',
    });
    [playlist] = getPlaylistIntakes();

    const report = formatPlaylistTagOrganizationReport(playlist);

    expect(report).toContain('slskdN tag and organization dry run');
    expect(report).toContain('Playlist: Snapshot queue');
    expect(report).toContain('Proposed tags: Artist: Stereolab | Title: French Disko | Album: Snapshot Album | Track number: 01');
    expect(report).toContain('No tag write');

    approvePlaylistTagOrganizationPlan(playlist.id);
    [playlist] = getPlaylistIntakes();
    expect(playlist.organizationApproval).toEqual(
      expect.objectContaining({
        impact: expect.stringMatching(/Approval snapshot only/i),
        summary: expect.objectContaining({
          matched: 1,
        }),
      }),
    );
    expect(playlist.organizationApproval.trackSnapshots[0]).toEqual(
      expect.objectContaining({
        destinationPath: 'Stereolab/Snapshot Album/01 - French Disko.flac',
      }),
    );

    clearPlaylistTagOrganizationApproval(playlist.id);
    [playlist] = getPlaylistIntakes();
    expect(playlist.organizationApproval).toBeNull();
  });
});
