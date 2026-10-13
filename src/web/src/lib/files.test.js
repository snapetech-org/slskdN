import api from './api';
import {
  deleteDirectory,
  deleteFile,
  deleteItems,
  encodePathSegment,
  list,
} from './files';

vi.mock('./api', () => ({
  default: {
    delete: vi.fn(),
    get: vi.fn(),
  },
}));

describe('files', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.get.mockResolvedValue({ data: {} });
    api.delete.mockResolvedValue({ data: {} });
  });

  it('encodes Unicode paths as URL-safe UTF-8 base64 route segments', () => {
    expect(encodePathSegment('Björk/漢字.flac')).toBe(
      encodeURIComponent(btoa('\x42\x6a\xc3\xb6\x72\x6b\x2f\xe6\xbc\xa2\xe5\xad\x97\x2e\x66\x6c\x61\x63')),
    );
  });

  it('uses encoded path segments for directory and file operations', async () => {
    await list({ root: 'downloads', subdirectory: 'Björk/Live' });
    await deleteDirectory({ root: 'downloads', path: 'Björk/Live' });
    await deleteFile({ root: 'downloads', path: 'Björk/Live/ Jóga.flac' });

    expect(api.get).toHaveBeenCalledWith(
      `/files/downloads/directories/${encodePathSegment('Björk/Live')}`,
    );
    expect(api.delete).toHaveBeenCalledWith(
      `/files/downloads/directories/${encodePathSegment('Björk/Live')}`,
    );
    expect(api.delete).toHaveBeenCalledWith(
      `/files/downloads/files/${encodePathSegment('Björk/Live/ Jóga.flac')}`,
    );
  });

  it('requests recursive folder sizes only when the caller asks for them', async () => {
    await list({
      root: 'downloads',
      subdirectory: 'Björk/Live',
      includeDirectorySizes: true,
    });

    expect(api.get).toHaveBeenCalledWith(
      `/files/downloads/directories/${encodePathSegment('Björk/Live')}?includeDirectorySizes=true`,
    );
  });

  it('sends one typed multi-item delete request and returns per-item results', async () => {
    const items = [
      { path: 'Album', type: 'directory' },
      { path: 'single.flac', type: 'file' },
    ];

    await deleteItems({ root: 'downloads', items });

    expect(api.delete).toHaveBeenCalledWith('/files/downloads/items', {
      data: { items },
    });
  });
});
