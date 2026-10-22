import { inferAlbumTrackConsensus } from './searchAlbumConsensus';

const createResponse = (username, album, tracks, { discFolders = false } = {}) => ({
  files: [
    ...tracks.map((title, index) => {
      const trackNumber = String(index + 1).padStart(2, '0');
      const discFolder = discFolders && index >= 3 ? 'CD2/' : discFolders ? 'CD1/' : '';
      return {
        filename: `Artist/${album}/${discFolder}${trackNumber} - Artist - ${album} - ${title}.flac`,
        length: 160 + (index * 3),
        size: 24_000_000,
      };
    }),
    {
      filename: `Artist/${album}/cover.jpg`,
      length: 0,
      size: 300_000,
    },
    {
      filename: `Artist/${album}/tracklist.nfo`,
      length: 0,
      size: 5_000,
    },
  ],
  username,
});

describe('inferAlbumTrackConsensus', () => {
  it('builds a canonical list from matching peer releases and ignores non-audio files', () => {
    const tracks = ['First Song', 'Second Song', 'Third Song', 'Fourth Song', 'Last Song'];
    const scores = inferAlbumTrackConsensus([
      createResponse('peer-a', 'Great Album', tracks),
      createResponse('peer-b', 'Great Album', tracks),
    ]);

    expect(scores[0]).toEqual({
      canonicalTrackTitles: tracks,
      canonicalTrackCount: 5,
      peers: 2,
      score: 100,
    });
    expect(scores[1]).toEqual(scores[0]);
  });

  it('scores an incomplete copy below the peer with the full consensus track list', () => {
    const tracks = ['First Song', 'Second Song', 'Third Song', 'Fourth Song', 'Last Song'];
    const [complete, incomplete] = inferAlbumTrackConsensus([
      createResponse('complete-peer', 'Great Album', tracks),
      createResponse('partial-peer', 'Great Album', tracks.slice(0, 3)),
    ]);

    expect(complete.score).toBe(100);
    expect(incomplete.score).toBeLessThan(complete.score);
    expect(incomplete.canonicalTrackCount).toBe(5);
  });

  it('combines multi-disc folders and compares order and duration where available', () => {
    const tracks = ['First Song', 'Second Song', 'Third Song', 'Fourth Song', 'Last Song'];
    const [multiDisc, flat] = inferAlbumTrackConsensus([
      createResponse('disc-peer', 'Great Album', tracks, { discFolders: true }),
      createResponse('flat-peer', 'Great Album', tracks),
    ]);

    expect(multiDisc.score).toBe(100);
    expect(flat.score).toBe(100);
  });

  it('does not claim consensus from one source or unrelated short track lists', () => {
    const [single] = inferAlbumTrackConsensus([
      createResponse('solo-peer', 'Great Album', ['First Song', 'Second Song', 'Third Song']),
    ]);
    const unrelated = inferAlbumTrackConsensus([
      createResponse('peer-a', 'First Album', ['First Song', 'Second Song', 'Third Song']),
      createResponse('peer-b', 'Other Album', ['Different Song', 'Another Song', 'Final Song']),
    ]);

    expect(single).toBeNull();
    expect(unrelated).toEqual([null, null]);
  });

  it('normalizes non-English track titles while retaining readable names', () => {
    const tracks = ['Первый трек', 'Второй трек', 'Третий трек'];
    const scores = inferAlbumTrackConsensus([
      createResponse('peer-a', 'Русский альбом', tracks),
      createResponse('peer-b', 'Русский альбом', tracks),
    ]);

    expect(scores[0].score).toBe(100);
    expect(scores[0].canonicalTrackTitles).toEqual(tracks);
  });
});
