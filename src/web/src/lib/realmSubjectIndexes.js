import { interfaceText } from './interfaceLocale';
import { formatRegionalNumber } from './regionalFormat';
import {
  localizeRealmSubjectIndexConflictDescription,
  localizeRealmSubjectIndexConflictType,
} from './appGeneratedReasonText';
// <copyright file="realmSubjectIndexes.js" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import api from './api';

export const fetchRealmSubjectIndexConflicts = ({ realmId }) =>
  api.get(`/realm-subject-indexes/${encodeURIComponent(realmId)}/conflicts`);

const asArray = (value) => (Array.isArray(value) ? value : []);
const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);

export const getRealmSubjectIndexConflicts = (report = {}) =>
  asArray(report.conflicts ?? report.Conflicts).filter(isObject);

export const getRealmSubjectIndexConflictValues = (conflict = {}) =>
  asArray(conflict.values ?? conflict.Values).filter(isObject);

export const summarizeRealmSubjectIndexConflicts = (report = {}) => {
  const conflicts = getRealmSubjectIndexConflicts(report);
  const values = conflicts.flatMap(getRealmSubjectIndexConflictValues);
  const authorityKeys = new Set(
    values
      .map((value) => value.authorityKey || value.AuthorityKey)
      .filter(Boolean),
  );
  const conflictTypes = new Set(
    conflicts.map((conflict) => conflict.type || conflict.Type).filter(Boolean),
  );

  return {
    authorityCount: authorityKeys.size,
    conflictCount: conflicts.length,
    conflictTypeCount: conflictTypes.size,
    entryCount: report.entryCount ?? report.EntryCount ?? 0,
    indexCount: report.indexCount ?? report.IndexCount ?? 0,
  };
};

export const formatRealmSubjectIndexConflictReport = ({
  disabledAuthorities = [],
  report = {},
} = {}) => {
  const conflicts = getRealmSubjectIndexConflicts(report);
  const lines = [
    interfaceText("slskdN realm subject-index conflict review"),
    interfaceText('Realm: {realm}', { realm: report.realmId || report.RealmId || '-' }),
    interfaceText('Indexes: {count}', {
      count: formatRegionalNumber(report.indexCount ?? report.IndexCount ?? 0),
    }),
    interfaceText('Entries: {count}', {
      count: formatRegionalNumber(report.entryCount ?? report.EntryCount ?? 0),
    }),
    interfaceText('Conflicts: {count}', { count: formatRegionalNumber(conflicts.length) }),
    interfaceText('Locally disabled authorities: {count}', {
      count: formatRegionalNumber(disabledAuthorities.length),
    }),
    '',
  ];

  conflicts.forEach((conflict) => {
    lines.push(
      interfaceText('Conflict: {type} / {key}', {
        type: localizeRealmSubjectIndexConflictType(conflict.type || conflict.Type || interfaceText('unknown')),
        key: conflict.key || conflict.Key || '-',
      }),
    );
    lines.push(interfaceText('Subject: {subject}', {
      subject: conflict.subjectId || conflict.SubjectId || '-',
    }));
    lines.push(interfaceText('Description: {description}', {
      description: localizeRealmSubjectIndexConflictDescription(conflict),
    }));
    getRealmSubjectIndexConflictValues(conflict).forEach((value) => {
      const authorityKey = value.authorityKey || value.AuthorityKey || '-';
      lines.push(
        interfaceText('- {status} {authority}: {value}', {
          status: interfaceText(disabledAuthorities.includes(authorityKey) ? 'Disabled' : 'Active'),
          authority: authorityKey,
          value: value.value || value.Value || '-',
        }),
      );
      if (value.provenance || value.Provenance) {
        lines.push(interfaceText('  Provenance: {value}', {
          value: value.provenance || value.Provenance,
        }));
      }
    });
    lines.push('');
  });

  return lines.join('\n').trim();
};
