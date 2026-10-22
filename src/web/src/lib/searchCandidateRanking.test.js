import {
  rankSearchCandidate,
  rankSearchResponses,
} from './searchCandidateRanking';

describe('rankSearchCandidate', () => {
  it('prefers exact lossless candidates with healthy availability', () => {
    const rank = rankSearchCandidate({
      acquisitionProfile: 'lossless-exact',
      downloadStats: { failedDownloads: 0, successfulDownloads: 4 },
      response: {
        files: [
          {
            bitDepth: 16,
            filename: 'Boards of Canada/Music Has The Right/01 Wildlife Analysis.flac',
            sampleRate: 44_100,
            size: 24_000_000,
          },
        ],
        hasFreeUploadSlot: true,
        queueLength: 0,
        uploadSpeed: 4_000_000,
        username: 'good-peer',
      },
      searchText: 'boards canada wildlife analysis',
    });

    expect(rank.score).toBeGreaterThanOrEqual(80);
    expect(rank.reasons).toEqual(
      expect.arrayContaining([
        'strong filename match',
        'mostly lossless files',
        'free upload slot',
      ]),
    );
  });

  it('keeps weak lossy queued candidates below strong candidates', () => {
    const rank = rankSearchCandidate({
      acquisitionProfile: 'lossless-exact',
      downloadStats: { failedDownloads: 4, successfulDownloads: 0 },
      response: {
        files: [
          {
            bitRate: 128,
            filename: 'misc/upload/track.mp3',
            size: 2_000_000,
          },
        ],
        hasFreeUploadSlot: false,
        queueLength: 8,
        uploadSpeed: 64_000,
        username: 'rough-peer',
      },
      searchText: 'boards canada wildlife analysis',
    });

    expect(rank.score).toBeLessThan(35);
    expect(rank.reasons).toEqual(
      expect.arrayContaining([
        'weak filename match',
        'no lossless signal',
        'long queue',
        'poor download history',
      ]),
    );
  });

  it('rewards high bitrate lossy candidates for fast-good-enough searches', () => {
    const rank = rankSearchCandidate({
      acquisitionProfile: 'fast-good-enough',
      response: {
        files: [
          {
            bitRate: 320,
            filename: 'Stereolab/Peng!/Super Falling Star.mp3',
            size: 8_000_000,
          },
        ],
        hasFreeUploadSlot: true,
        queueLength: 1,
        uploadSpeed: 1_000_000,
      },
      searchText: 'stereolab super falling star',
    });

    expect(rank.score).toBeGreaterThanOrEqual(60);
    expect(rank.reasons).toContain('high bitrate fast-good-enough candidate');
  });

  it('applies local community quality caution without blocking candidates', () => {
    const rank = rankSearchCandidate({
      acquisitionProfile: 'lossless-exact',
      communityQualitySummary: {
        negative: 2,
        positive: 0,
        score: -12,
        signals: [{ type: 'suspicious-candidate' }, { type: 'failed-verification' }],
      },
      response: {
        files: [
          {
            bitDepth: 16,
            filename: 'Artist/Album/01 Track.flac',
            sampleRate: 44_100,
            size: 20_000_000,
          },
        ],
        hasFreeUploadSlot: true,
        queueLength: 0,
        uploadSpeed: 3_000_000,
      },
      searchText: 'artist track',
    });

    expect(rank.score).toBeGreaterThan(0);
    expect(rank.reasons).toContain('local caution signals');
  });

  it('honors explicit local quality overrides before raw signal score', () => {
    const trusted = rankSearchCandidate({
      communityQualitySummary: {
        negative: 4,
        override: { mode: 'trust' },
        positive: 0,
        score: 8,
        signals: [{ type: 'suspicious-candidate' }],
      },
      response: {
        files: [{ filename: 'Artist/Track.flac', size: 20_000_000 }],
      },
      searchText: 'artist track',
    });

    const ignored = rankSearchCandidate({
      communityQualitySummary: {
        negative: 3,
        override: { mode: 'ignore' },
        positive: 0,
        score: 0,
        signals: [{ type: 'suspicious-candidate' }],
      },
      response: {
        files: [{ filename: 'Artist/Track.flac', size: 20_000_000 }],
      },
      searchText: 'artist track',
    });

    expect(trusted.reasons).toContain('local trust override');
    expect(ignored.reasons).toContain('local quality signals ignored');
  });

  it('applies preferred conditions as ranking signals instead of hard filters', () => {
    const rank = rankSearchCandidate({
      acquisitionProfile: 'rare-hunt',
      preferredConditions: {
        preferExtensions: ['flac'],
        preferLossless: true,
        preferMinBitRate: 320,
      },
      response: {
        files: [
          {
            bitDepth: 16,
            bitRate: 1_000,
            filename: 'Artist/Album/01 Track.flac',
            sampleRate: 44_100,
            size: 20_000_000,
          },
        ],
        hasFreeUploadSlot: true,
        queueLength: 0,
        uploadSpeed: 3_000_000,
      },
      searchText: 'artist track',
    });

    expect(rank.reasons).toEqual(
      expect.arrayContaining([
        'preferred extension match',
        'preferred lossless match',
        'preferred bitrate match',
      ]),
    );
  });

  it('ignores malformed source providers and preferred extension lists', () => {
    const rank = rankSearchCandidate({
      preferredConditions: {
        preferExtensions: { 0: 'flac', length: 1 },
      },
      response: {
        files: [{ filename: 'Artist/Track.flac', size: 20_000_000 }],
        hasFreeUploadSlot: true,
        sourceProviders: { 0: 'local', length: 1 },
      },
      searchText: 'artist track',
    });

    expect(rank.reasons).not.toContain('local source available');
    expect(rank.reasons).not.toContain('preferred extension match');
  });
});

describe('rankSearchResponses', () => {
  it('attaches scores and download stats to each response', () => {
    const [ranked] = rankSearchResponses({
      responses: [
        {
          files: [{ filename: 'artist/title.flac', size: 18_000_000 }],
          hasFreeUploadSlot: true,
          username: 'peer',
        },
      ],
      searchText: 'artist title',
      userStats: {
        peer: { failedDownloads: 0, successfulDownloads: 2 },
      },
    });

    expect(ranked.downloadStats).toEqual({
      failedDownloads: 0,
      successfulDownloads: 2,
    });
    expect(ranked.smartScore).toBe(ranked.candidateRank.score);
    expect(ranked.candidateRank.reasons.length).toBeGreaterThan(0);
  });

  it('attaches local community quality summaries to responses', () => {
    const [ranked] = rankSearchResponses({
      communityQualityByUser: {
        peer: {
          negative: 1,
          positive: 0,
          score: -6,
          signals: [{ type: 'suspicious-candidate' }],
        },
      },
      responses: [
        {
          files: [{ filename: 'artist/title.flac', size: 18_000_000 }],
          hasFreeUploadSlot: true,
          username: 'peer',
        },
      ],
      searchText: 'artist title',
    });

    expect(ranked.communityQualitySummary.score).toBe(-6);
    expect(ranked.candidateRank.reasons).toContain('local caution signals');
  });

  it('adds a separate peer album-consensus score to each matching response', () => {
    const tracks = ['First Song', 'Second Song', 'Third Song', 'Fourth Song'];
    const responses = ['peer-a', 'peer-b'].map((username) => ({
      files: tracks.map((title, index) => ({
        filename: `Artist/Great Album/${String(index + 1).padStart(2, '0')} - ${title}.flac`,
        length: 180 + index,
        size: 24_000_000,
      })),
      username,
    }));

    const ranked = rankSearchResponses({ responses, searchText: 'great album' });
    const baseline = rankSearchCandidate({ response: responses[0], searchText: 'great album' });

    expect(ranked.map((response) => response.albumConsensusScore)).toEqual([100, 100]);
    expect(ranked[0].candidateRank.albumConsensusScore).toBe(100);
    expect(ranked[0].candidateRank.canonicalTrackTitles).toEqual(tracks);
    expect(ranked[0].smartScore).toBe(Math.round((baseline.score * 0.8) + 20));
    expect(ranked[0].candidateRank.score).toBe(ranked[0].smartScore);
    expect(ranked[0].candidateRank.reasons).toContain(
      'album track consensus 100/100 across 2 sources',
    );
  });

  it('uses the inferred full track list to boost more complete peers in smart ranking', () => {
    const tracks = ['First Song', 'Second Song', 'Third Song', 'Fourth Song', 'Last Song'];
    const createResponse = (username, responseTracks) => ({
      files: responseTracks.map((title, index) => ({
        filename: `Artist/Great Album/${String(index + 1).padStart(2, '0')} - ${title}.flac`,
        length: 180 + index,
        size: 24_000_000,
      })),
      username,
    });
    const [complete, partial] = rankSearchResponses({
      responses: [
        createResponse('complete-peer', tracks),
        createResponse('partial-peer', tracks.slice(0, 3)),
      ],
      searchText: 'great album',
    });

    expect(complete.albumConsensusScore).toBe(100);
    expect(partial.albumConsensusScore).toBeLessThan(complete.albumConsensusScore);
    expect(complete.smartScore).toBeGreaterThan(partial.smartScore);
  });
});
