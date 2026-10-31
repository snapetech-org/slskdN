import { localizeSearchCandidateRankingReason } from './searchCandidateRankingCopy';

describe('search candidate ranking copy', () => {
  it('passes through the fixed ranking explanations in English', () => {
    const reasons = [
      'strong filename match',
      'partial filename match',
      'weak filename match',
      'no media files visible',
      'lossless fast-good-enough candidate',
      'high bitrate fast-good-enough candidate',
      'limited fast-good-enough quality evidence',
      'broad folder candidate',
      'small folder candidate',
      'mostly lossless files',
      'mixed lossless files',
      'no lossless signal',
      'plausible file sizes',
      'mixed file size evidence',
      'free upload slot',
      'queued upload',
      'short queue',
      'long queue',
      'fast peer',
      'trusted download history',
      'poor download history',
      'limited download history',
      'local source available',
      'mesh source available',
      'local quality signals ignored',
      'local trust override',
      'local caution override',
      'positive local quality signals',
      'local caution signals',
      'mixed local quality signals',
      'preferred extension match',
      'missing preferred extension',
      'preferred lossless match',
      'missing preferred lossless files',
      'preferred bitrate match',
      'below preferred bitrate',
    ];

    reasons.forEach((reason) => {
      expect(localizeSearchCandidateRankingReason(reason)).toBe(reason);
    });
  });

  it('preserves unknown response values without treating them as catalog sources', () => {
    const reason = 'provider supplied detail';

    expect(localizeSearchCandidateRankingReason(reason)).toBe(reason);
  });
});
