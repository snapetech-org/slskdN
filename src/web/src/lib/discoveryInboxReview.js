// <copyright file="discoveryInboxReview.js" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import { interfaceText } from './interfaceLocale';

const normalize = (value = '') => value.toLowerCase();

export const classifyDiscoveryInboxImpact = (item = {}) => {
  const text = normalize(
    [
      item.networkImpact,
      item.reason,
      item.source,
      item.acquisitionProfile,
    ].join(' '),
  );

  if (
    /\b(download|stream|peer browse|browse peer|automatic|auto-download)\b/u.test(text)
  ) {
    return {
      color: 'red',
      icon: 'warning sign',
      label: 'Network risk',
      level: 'network-risk',
    };
  }

  if (/\b(search|provider|metadata|release radar|listenbrainz|spotify|apple)\b/u.test(text)) {
    return {
      color: 'orange',
      icon: 'wifi',
      label: 'Provider review',
      level: 'provider-review',
    };
  }

  if (/\b(local|manual review|no network|browser-local)\b/u.test(text)) {
    return {
      color: 'green',
      icon: 'shield',
      label: interfaceText('Local/manual'),
      level: 'local-manual',
    };
  }

  return {
    color: 'blue',
    icon: 'question circle',
    label: 'Needs estimate',
    level: 'needs-estimate',
  };
};

export const buildDiscoveryInboxReviewSummary = (items = []) => {
  const counts = items.reduce(
    (summary, item) => {
      const impact = classifyDiscoveryInboxImpact(item);

      return {
        ...summary,
        [impact.level]: (summary[impact.level] || 0) + 1,
        total: summary.total + 1,
      };
    },
    {
      'local-manual': 0,
      'needs-estimate': 0,
      'network-risk': 0,
      'provider-review': 0,
      total: 0,
    },
  );

  return {
    ...counts,
    canBulkApproveSafely:
      counts.total > 0 &&
      counts['network-risk'] === 0 &&
      counts['needs-estimate'] === 0,
  };
};
