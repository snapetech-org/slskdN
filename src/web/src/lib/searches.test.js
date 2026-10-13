import api from './api';
import * as search from './searches';

vi.mock('./api', () => ({
  __esModule: true,
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('user download stats', () => {
  it('dedupes concurrent requests and reuses the bounded cache', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-07-16T00:00:00Z'));
    api.get
      .mockResolvedValueOnce({ data: { alice: { successfulDownloads: 3 } } })
      .mockResolvedValueOnce({ data: { bob: { successfulDownloads: 1 } } });

    const [first, second] = await Promise.all([
      search.getUserDownloadStats(),
      search.getUserDownloadStats(),
    ]);
    const cached = await search.getUserDownloadStats();

    expect(api.get).toHaveBeenCalledTimes(1);
    expect(first).toBe(second);
    expect(cached).toBe(first);

    await vi.advanceTimersByTimeAsync(30_001);

    await expect(search.getUserDownloadStats()).resolves.toEqual({
      bob: { successfulDownloads: 1 },
    });
    expect(api.get).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });
});

describe('search history pages', () => {
  it('requests a bounded page with source and offset while preserving array responses', async () => {
    api.get.mockResolvedValue({ data: [{ id: 'older-search' }] });

    await expect(search.getAll(250, 'wishlist', 500)).resolves.toEqual([
      { id: 'older-search' },
    ]);
    expect(api.get).toHaveBeenCalledWith(
      '/searches?limit=250&offset=500&source=wishlist',
    );
  });

  it('requests a stable continuation using the final row timestamp and ID', async () => {
    api.get.mockResolvedValue({ data: [] });

    await search.getAll(250, 'wishlist', 0, '2026-08-20T12:00:00Z', 'search-id');

    expect(api.get).toHaveBeenCalledWith(
      '/searches?limit=250&offset=0&source=wishlist&afterStartedAt=2026-08-20T12%3A00%3A00Z&afterId=search-id',
    );
  });
});

describe('createBatch', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('retries serialized search creation conflicts and completes the batch', async () => {
    vi.useFakeTimers();
    api.post
      .mockRejectedValueOnce({
        message: 'Only one concurrent operation is permitted',
        response: {
          data: 'Only one concurrent operation is permitted. Wait until the previous request completes',
          status: 429,
        },
      })
      .mockResolvedValueOnce({ data: { id: 'first' } })
      .mockResolvedValueOnce({ data: { id: 'second' } });

    const promise = search.createBatch({ queries: ['one', 'two'] });

    await vi.runAllTimersAsync();
    await expect(promise).resolves.toBe(2);
    expect(api.post).toHaveBeenCalledTimes(3);
    vi.useRealTimers();
  });

  it('does not swallow non-serialized search errors', async () => {
    api.post.mockRejectedValueOnce({
      response: {
        data: 'bad request',
        status: 400,
      },
    });

    await expect(search.createBatch({ queries: ['one'] })).rejects.toMatchObject({
      response: {
        data: 'bad request',
        status: 400,
      },
    });
  });

  it('passes the active acquisition profile and providers to every replayed query', async () => {
    api.post.mockResolvedValueOnce({ data: { id: 'replayed' } });

    await expect(
      search.createBatch({
        acquisitionProfile: 'conservative-network',
        providers: ['pod'],
        queries: ['one'],
      }),
    ).resolves.toBe(1);

    expect(api.post).toHaveBeenCalledWith(
      '/searches',
      expect.objectContaining({
        acquisitionProfile: 'conservative-network',
        providers: ['pod'],
        searchText: 'one',
      }),
    );
  });
});

describe('blocked users', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('ignores malformed stored blocked-user shapes before array operations', () => {
    localStorage.setItem(
      'slskdn_blocked_users',
      JSON.stringify({ alice: true }),
    );

    expect(search.getBlockedUsers()).toEqual([]);
    expect(search.blockUser('bob')).toEqual(['bob']);
    expect(search.unblockUser('bob')).toEqual([]);
    expect(search.isUserBlocked('alice')).toBe(false);
  });
});

describe('filterResponse', () => {
  it('removes VBR files if "iscbr" is specified', () => {
    const response = {
      files: [
        { bitRate: 123, isVariableBitRate: true },
        { bitRate: 320, isVariableBitRate: false },
      ],
    };

    const filters = { isCBR: true };

    expect(search.filterResponse({ filters, response })).toMatchObject({
      files: [{ bitRate: 320, isVariableBitRate: false }],
    });
  });

  it('removes CBR files if "isvbr" is specified', () => {
    const response = {
      files: [
        { bitRate: 123, isVariableBitRate: true },
        { bitRate: 320, isVariableBitRate: false },
      ],
    };

    const filters = { isVBR: true };

    expect(search.filterResponse({ filters, response })).toMatchObject({
      files: [{ bitRate: 123, isVariableBitRate: true }],
    });
  });

  it('removes all files if "iscbr" and "isvbr" are both specified', () => {
    const response = {
      files: [{ isVariableBitrate: true }, { isVariableBitrate: false }],
    };

    const filters = { isCBR: true, isVBR: true };

    expect(search.filterResponse({ filters, response })).toMatchObject({
      files: [],
    });
  });

  it('removes lossy files if "islossless" is specified', () => {
    const response = {
      files: [
        { bitDepth: 16, sampleRate: 41_000 },
        { bitRate: 320, isVariableBitRate: false },
      ],
    };

    const filters = { isLossless: true };

    expect(search.filterResponse({ filters, response })).toMatchObject({
      files: [{ bitDepth: 16, sampleRate: 41_000 }],
    });
  });

  it('removes lossless files if "islossy" is specified', () => {
    const response = {
      files: [
        { bitDepth: 16, sampleRate: 41_000 },
        { bitRate: 320, isVariableBitRate: false },
      ],
    };

    const filters = { isLossy: true };

    expect(search.filterResponse({ filters, response })).toMatchObject({
      files: [{ bitRate: 320, isVariableBitRate: false }],
    });
  });

  it('removes files with bitRate less than minBitRate', () => {
    const response = {
      files: [{ bitRate: 100 }, { bitRate: 99 }],
    };

    const filters = { minBitRate: 100 };

    expect(search.filterResponse({ filters, response })).toMatchObject({
      files: [{ bitRate: 100 }],
    });
  });

  it('removes files with size less than minFileSize', () => {
    const response = {
      files: [{ size: 100 }, { size: 99 }],
    };

    const filters = { minFileSize: 100 };

    expect(search.filterResponse({ filters, response })).toMatchObject({
      files: [{ size: 100 }],
    });
  });

  it('removes files with length less than minLength', () => {
    const response = {
      files: [{ length: 100 }, { length: 99 }],
    };

    const filters = { minLength: 100 };

    expect(search.filterResponse({ filters, response })).toMatchObject({
      files: [{ length: 100 }],
    });
  });

  describe('term filtering', () => {
    const response = {
      files: [
        { filename: '/path/to/foo.mp3' },
        { filename: '/path/to/bar.mp3' },
        { filename: '/path/to/baz.mp3' },
        { filename: '/path/to/qux.mp3' },
        { filename: '/path/to/info.nfo' },
        { filename: '/path/to/folder.jpg' },
      ],
    };

    it('removes files with filenames not containing included phrases', () => {
      const filters = { include: ['path', 'to', '.nfo'] };

      expect(search.filterResponse({ filters, response })).toMatchObject({
        files: [{ filename: '/path/to/info.nfo' }],
      });
    });

    it('removes files with filenames containing excluded phrases', () => {
      const filters = { exclude: ['bar', 'jpg', 'qux'] };

      expect(search.filterResponse({ filters, response })).toMatchObject({
        files: [
          { filename: '/path/to/foo.mp3' },
          { filename: '/path/to/baz.mp3' },
          { filename: '/path/to/info.nfo' },
        ],
      });
    });

    it('removes a mix of includes and excludes', () => {
      const filters = {
        exclude: ['foo', 'bar'],
        include: ['path', '.mp3'],
      };

      expect(search.filterResponse({ filters, response })).toMatchObject({
        files: [
          { filename: '/path/to/baz.mp3' },
          { filename: '/path/to/qux.mp3' },
        ],
      });
    });
  });
});

describe('parseFiltersFromString', () => {
  it('keeps quoted include and exclusion phrases together', () => {
    expect(search.parseFiltersFromString('flac -"inner space vol. 2" "wrong address"'))
      .toMatchObject({
        exclude: ['inner space vol. 2'],
        include: ['flac', 'wrong address'],
      });
  });

  it('returns correct minBitrate', () => {
    expect(search.parseFiltersFromString('foo minbr:42 bar')).toMatchObject({
      minBitRate: 42,
    });

    expect(
      search.parseFiltersFromString('foo minbitrate:123 bar'),
    ).toMatchObject({
      minBitRate: 123,
    });
  });

  it('returns correct minFileSize', () => {
    expect(search.parseFiltersFromString('foo minfs:42 bar')).toMatchObject({
      minFileSize: 42,
    });

    expect(
      search.parseFiltersFromString('foo minfilesize:123 bar'),
    ).toMatchObject({
      minFileSize: 123,
    });
  });

  it('returns correct minLength', () => {
    expect(search.parseFiltersFromString('foo minlen:42 bar')).toMatchObject({
      minLength: 42,
    });

    expect(
      search.parseFiltersFromString('foo minlength:123 bar'),
    ).toMatchObject({
      minLength: 123,
    });
  });

  it('returns correct minFilesInFolder', () => {
    expect(search.parseFiltersFromString('foo minfif:42 bar')).toMatchObject({
      minFilesInFolder: 42,
    });

    expect(
      search.parseFiltersFromString('foo minfilesinfolder:123 bar'),
    ).toMatchObject({
      minFilesInFolder: 123,
    });
  });

  it('returns correct list of terms', () => {
    expect(search.parseFiltersFromString('foo minbr:42 bar')).toMatchObject({
      include: ['foo', 'bar'],
    });

    expect(search.parseFiltersFromString('foo iscbr isvbr bar')).toMatchObject({
      include: ['foo', 'bar'],
    });

    expect(search.parseFiltersFromString('foo some:thing bar')).toMatchObject({
      include: ['foo', 'bar'],
    });

    expect(search.parseFiltersFromString('foo -bar')).toMatchObject({
      exclude: ['bar'],
      include: ['foo'],
    });

    expect(search.parseFiltersFromString('-foo -bar -baz qux')).toMatchObject({
      exclude: ['foo', 'bar', 'baz'],
      include: ['qux'],
    });

    expect(search.parseFiltersFromString('foo bar baz -qux')).toMatchObject({
      exclude: ['qux'],
      include: ['foo', 'bar', 'baz'],
    });
  });

  it('returns isVBR and isCBR if terms are present', () => {
    expect(search.parseFiltersFromString('isvbr')).toMatchObject({
      isVBR: true,
    });

    expect(search.parseFiltersFromString('iscbr')).toMatchObject({
      isCBR: true,
    });
  });

  it('returns expected filters given a bit of everything', () => {
    expect(
      search.parseFiltersFromString(
        'big -mix of:everything isvbr iscbr minbr:42',
      ),
    ).toMatchObject({
      exclude: ['mix'],
      include: ['big'],
      isCBR: true,
      isVBR: true,
      minBitRate: 42,
    });
  });

  it('returns preferred ranking conditions without treating them as search terms', () => {
    expect(
      search.parseFiltersFromString(
        'album preferlossless prefbr:320 prefext:flac,wav live',
      ),
    ).toMatchObject({
      include: ['album', 'live'],
      preferExtensions: ['flac', 'wav'],
      preferLossless: true,
      preferMinBitRate: 320,
    });
  });
});
