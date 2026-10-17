import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export const stubLocaleCatalogFetch = (vi) => {
  const originalFetch = globalThis.fetch?.bind(globalThis);
  const fetchMock = vi.fn(async (input, init) => {
    const inputUrl = typeof input === 'string' ? input : input?.url;
    if (typeof inputUrl !== 'string') return new Response(null, { status: 404 });
    const url = new URL(inputUrl, 'http://localhost');
    const match = url.pathname.match(/\/locales\/([a-zA-Z-]+)\.json$/);
    if (!match) {
      if (originalFetch) return originalFetch(input, init);
      throw new Error(`No fetch mock for ${url.pathname}.`);
    }

    const catalogPath = resolve(process.cwd(), 'public/locales', `${match[1]}.json`);
    const body = readFileSync(catalogPath, 'utf8');
    return new Response(body, {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  });

  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
};
