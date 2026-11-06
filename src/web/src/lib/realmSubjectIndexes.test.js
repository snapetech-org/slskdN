// <copyright file="realmSubjectIndexes.test.js" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import {
  formatRealmSubjectIndexConflictReport,
  summarizeRealmSubjectIndexConflicts,
} from './realmSubjectIndexes';

describe('realmSubjectIndexes', () => {
  const report = {
    conflicts: [
      {
        key: 'musicbrainz:recording',
        subjectId: 'subject-1',
        type: 'external-id',
        values: [
          {
            authorityKey: 'realm-a:index-a:r1',
            provenance: 'realm:realm-a:subject-index:index-a:r1',
            value: 'mbid-a',
          },
          {
            authorityKey: 'realm-a:index-b:r2',
            provenance: 'realm:realm-a:subject-index:index-b:r2',
            value: 'mbid-b',
          },
        ],
      },
      {
        key: 'alias',
        subjectId: 'subject-2',
        type: 'alias-subject',
        values: [
          {
            authorityKey: 'realm-a:index-a:r1',
            value: 'fixture alias',
          },
        ],
      },
    ],
    entryCount: 9,
    indexCount: 2,
    realmId: 'realm-a',
  };

  it('summarizes conflict reports without leaking raw value details', () => {
    expect(summarizeRealmSubjectIndexConflicts(report)).toEqual({
      authorityCount: 2,
      conflictCount: 2,
      conflictTypeCount: 2,
      entryCount: 9,
      indexCount: 2,
    });
  });

  it('formats conflict reports with local disabled-authority state', () => {
    const formatted = formatRealmSubjectIndexConflictReport({
      disabledAuthorities: ['realm-a:index-b:r2'],
      report,
    });

    expect(formatted).toContain('slskdN realm subject-index conflict review');
    expect(formatted).toContain('Realm: realm-a');
    expect(formatted).toContain('Active realm-a:index-a:r1: mbid-a');
    expect(formatted).toContain('Disabled realm-a:index-b:r2: mbid-b');
    expect(formatted).toContain(
      'Provenance: realm:realm-a:subject-index:index-b:r2',
    );
  });

  it('ignores malformed conflict and nested value list payloads', () => {
    const malformedReport = {
      conflicts: {
        values: [
          {
            authorityKey: 'realm-a:index-a:r1',
          },
        ],
      },
      entryCount: 4,
      indexCount: 1,
    };

    expect(summarizeRealmSubjectIndexConflicts(malformedReport)).toEqual({
      authorityCount: 0,
      conflictCount: 0,
      conflictTypeCount: 0,
      entryCount: 4,
      indexCount: 1,
    });
    expect(formatRealmSubjectIndexConflictReport({ report: malformedReport })).toContain(
      'Conflicts: 0',
    );
  });
});
