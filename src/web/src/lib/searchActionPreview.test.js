import {
  buildSearchActionPreview,
  formatSearchActionPreview,
} from './searchActionPreview';

describe('buildSearchActionPreview', () => {
  it('summarizes selected download action details and warnings', () => {
    const preview = buildSearchActionPreview({
      candidateRank: { score: 38 },
      communityQualitySummary: {
        override: {
          mode: 'ignore',
          note: 'Known private peer.',
        },
        score: -6,
      },
      files: [
        { filename: 'Artist/Album/01 Track.flac', size: 20 },
        { filename: 'Artist/Album/02 Track.flac', locked: true, size: 30 },
      ],
      response: {
        hasFreeUploadSlot: false,
        queueLength: 7,
        sourceProviders: ['pod', 'scene'],
        username: 'peer',
      },
    });

    expect(preview).toMatchObject({
      candidateScore: 38,
      fileCount: 2,
      lockedCount: 1,
      providerLabels: ['pod', 'scene'],
      totalSizeBytes: 50,
      username: 'peer',
    });
    expect(preview.warnings).toEqual(
      expect.arrayContaining([
        '1 selected file may be locked',
        'No free upload slot is currently advertised',
        'Queue depth is 7',
        'Local caution signals exist for this peer',
        'Local quality note: Known private peer.',
        'Local quality signals are ignored by reviewer override',
        'Candidate score is 38/100',
      ]),
    );
  });

  it('falls back when source providers are malformed', () => {
    const preview = buildSearchActionPreview({
      response: {
        sourceProviders: { length: 1 },
      },
    });

    expect(preview.providerLabels).toEqual(['soulseek']);
    expect(formatSearchActionPreview(preview)).toContain('Providers: soulseek');
  });
});

describe('formatSearchActionPreview', () => {
  it('exports a stable text plan', () => {
    const text = formatSearchActionPreview({
      candidateScore: 90,
      fileCount: 1,
      filenames: ['Artist/Album/01 Track.flac'],
      providerLabels: ['soulseek'],
      route: 'download',
      totalSizeBytes: 20,
      username: 'peer',
      warnings: [],
    });

    expect(text).toContain('Action: Download');
    expect(text).toContain('Source: peer');
    expect(text).toContain('- Artist/Album/01 Track.flac');
  });
});
