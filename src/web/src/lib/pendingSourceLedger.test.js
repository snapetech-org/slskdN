import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import ledger from '../../../../docs/localization-sources/20261031-ui-outbound-copy.json';

const repositoryRoot = fs.realpathSync(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..'));
const digest = (value) => createHash('sha256').update(value).digest('hex');

function repositoryFile(relativePath) {
  expect(relativePath).toMatch(/^src\/(web\/src|slskd)\//);
  const resolved = fs.realpathSync(path.resolve(repositoryRoot, relativePath));
  expect(resolved.startsWith(repositoryRoot + path.sep)).toBe(true);
  return fs.readFileSync(resolved);
}

describe('pending app-authored source ledger', () => {
  it('binds each source and caller to current code without promoting untranslated values', () => {
    expect(ledger.records).toHaveLength(56);
    expect(new Set(ledger.records.map((record) => record.id)).size).toBe(56);
    expect(ledger.categories).toEqual({
      'app-owned-diagnostic': 8, 'copied-report-heading': 6, 'outbound-title': 2, 'ui-copy': 40,
    });
    for (const record of ledger.records) {
      expect(digest(record.source)).toBe(record.sourceSha256);
      expect(record.status).toBe('source-wired; translations pending');
      expect(record.parameters).toEqual([...record.source.matchAll(/\{([A-Za-z][A-Za-z0-9_]*)\}/g)].map((match) => match[1]));
      expect(record.callers.length).toBeGreaterThan(0);
      for (const caller of record.callers) {
        const contents = repositoryFile(caller.path);
        expect(digest(contents)).toBe(caller.fileSha256);
        expect(contents.toString('utf8').split('\n')[caller.line - 1]).toContain(caller.literal);
      }
    }
  });

  it('keeps the pending target-cell count explicit across all twelve untouched catalogs', () => {
    let missing = 0;
    for (const locale of ledger.targetLocales) {
      const catalog = JSON.parse(fs.readFileSync(path.join(repositoryRoot, 'src/web/public/locales', `${locale}.json`), 'utf8'));
      for (const record of ledger.records) if (!Object.hasOwn(catalog, record.source)) missing++;
    }
    expect(ledger.targetLocales).toHaveLength(12);
    expect(missing).toBe(ledger.pendingTargetCells);
    expect(missing).toBe(672);
  });

  it('wires the two background titles through a separate locale and preserves provider payloads', () => {
    const service = repositoryFile('src/slskd/Integrations/Notifications/NotificationService.cs').toString('utf8');
    expect(service).toContain('NotificationTitleFormatter.PrivateMessage(options.NotificationLanguage, username)');
    expect(service).toContain('NotificationTitleFormatter.RoomMention(options.NotificationLanguage, username, room)');
    expect(service).toContain('SendNtfyAsync(options.Ntfy, title, message)');
    expect(service).toContain('SendPushoverAsync(options.Pushover, title, message)');
    expect(service).toContain('Pushbullet.PushAsync(title, username, message)');
  });
});
