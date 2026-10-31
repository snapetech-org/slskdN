import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import historicalCheckpoint from '../../../../docs/localization-sources/20261031-ui-outbound-copy.json';
import ledger from '../../../../docs/localization-sources/20261031-interface-copy-inventory.json';

const repositoryRoot = fs.realpathSync(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..'));
const digest = (value) => createHash('sha256').update(value).digest('hex');

function repositoryFile(relativePath) {
  expect(relativePath).toMatch(/^src\/(web\/src|slskd)\//);
  const resolved = fs.realpathSync(path.resolve(repositoryRoot, relativePath));
  expect(resolved.startsWith(repositoryRoot + path.sep)).toBe(true);
  return fs.readFileSync(resolved);
}

describe('localization source inventories', () => {
  it('preserves the first 56-source checkpoint as historical evidence', () => {
    expect(historicalCheckpoint.records).toHaveLength(56);
    expect(new Set(historicalCheckpoint.records.map((record) => record.id)).size).toBe(56);
    expect(historicalCheckpoint.categories).toEqual({
      'app-owned-diagnostic': 8,
      'copied-report-heading': 6,
      'outbound-title': 2,
      'ui-copy': 40,
    });
    for (const record of historicalCheckpoint.records) {
      expect(digest(record.source)).toBe(record.sourceSha256);
      expect(record.parameters).toEqual([...record.source.matchAll(/\{([A-Za-z][A-Za-z0-9_]*)\}/g)].map((match) => match[1]));
    }
  });

  it('binds current source strings and caller lines to the checked-in code', () => {
    expect(ledger.pendingSourceCount).toBe(ledger.records.length);
    expect(new Set(ledger.records.map((record) => record.id)).size).toBe(ledger.records.length);
    expect(ledger.records).toHaveLength(436);
    for (const record of ledger.records) {
      expect(digest(record.source)).toBe(record.sourceSha256);
      expect(record.parameters).toEqual([...record.source.matchAll(/\{([A-Za-z][A-Za-z0-9_]*)\}/g)].map((match) => match[1]));
      expect(record.callers.length).toBeGreaterThan(0);
      for (const caller of record.callers) {
        const contents = repositoryFile(caller.path);
        expect(digest(contents)).toBe(caller.fileSha256);
        const line = contents.toString('utf8').split('\n')[caller.line - 1];
        expect(line).toBe(caller.lineText);
        expect(digest(line)).toBe(caller.lineTextSha256);
      }
    }
  });

  it('tracks current missing locale cells directly against all twelve catalogs', () => {
    let missing = 0;
    for (const locale of ledger.targetLocales) {
      const catalog = JSON.parse(fs.readFileSync(path.join(repositoryRoot, 'src/web/public/locales', `${locale}.json`), 'utf8'));
      for (const record of ledger.records) {
        const isMissing = typeof catalog[record.source] !== 'string' || !catalog[record.source].trim();
        if (isMissing) missing++;
        expect(record.missingLocales.includes(locale)).toBe(isMissing);
        const placeholders = [...record.source.matchAll(/\{([A-Za-z][A-Za-z0-9_]*)\}/g)].map((match) => match[1]).sort();
        const translatedPlaceholders = typeof catalog[record.source] === 'string'
          ? [...catalog[record.source].matchAll(/\{([A-Za-z][A-Za-z0-9_]*)\}/g)].map((match) => match[1]).sort()
          : [];
        expect(translatedPlaceholders).toEqual(isMissing ? [] : placeholders);
      }
    }
    expect(ledger.targetLocales).toHaveLength(12);
    expect(missing).toBe(ledger.pendingTargetCells);
  });

  it('keeps both notification-title sources in the comprehensive pending inventory', () => {
    const sources = new Set(ledger.records.map((record) => record.source));
    expect(sources.has('Private Message from {username}')).toBe(true);
    expect(sources.has('Room Mention by {username} in {room}')).toBe(true);
    const service = repositoryFile('src/slskd/Integrations/Notifications/NotificationService.cs').toString('utf8');
    expect(service).toContain('NotificationTitleFormatter.PrivateMessage(options.NotificationLanguage, username)');
    expect(service).toContain('NotificationTitleFormatter.RoomMention(options.NotificationLanguage, username, room)');
    expect(service).toContain('SendNtfyAsync(options.Ntfy, title, message)');
    expect(service).toContain('SendPushoverAsync(options.Pushover, title, message)');
    expect(service).toContain('Pushbullet.PushAsync(title, username, message)');
  });
});
