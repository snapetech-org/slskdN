import React from 'react';
import LocalizedText from './LocalizedText';
import { formatRegionalNumber, useRegionalLocale } from '../../lib/regionalFormat';

export const NewMessageCount = ({ count }) => {
  const locale = useRegionalLocale();
  return <LocalizedText source="↓ New messages: {count}" values={{ count: formatRegionalNumber(count, undefined, locale) }} />;
};

export const AutoFixableIssueCount = ({ count }) => {
  const locale = useRegionalLocale();
  return <LocalizedText source="Queue fixes (auto-fixable issues: {count})" values={{ count: formatRegionalNumber(count, undefined, locale) }} />;
};
