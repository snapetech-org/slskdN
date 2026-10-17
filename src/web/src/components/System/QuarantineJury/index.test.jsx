// <copyright file="index.test.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import QuarantineJury from '.';
import * as quarantineJuryApi from '../../../lib/quarantineJury';
import { resetInterfaceLanguage, setInterfaceLanguage } from '../../../lib/interfaceLocale';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { stubLocaleCatalogFetch } from '../../../test/localeCatalogFetchMock';

vi.mock('../../../lib/quarantineJury', () => ({
  acceptReleaseCandidate: vi.fn(),
  getRequests: vi.fn(),
  getReview: vi.fn(),
  routeRequest: vi.fn(),
}));

const review = {
  acceptance: null,
  acceptanceReason: 'Release candidate can be accepted after quorum.',
  aggregate: {
    dissentingJurors: ['actor:fixture-gamma'],
    quorumReached: true,
    reason: '2 of 3 jurors recommend release.',
    recommendation: 'ReleaseCandidate',
    requiredVotes: 2,
    totalVerdicts: 3,
    verdictCounts: {
      ReleaseCandidate: 2,
      UpholdQuarantine: 1,
    },
  },
  canAcceptReleaseCandidate: true,
  request: {
    createdAt: '2026-04-30T21:50:00Z',
    evidence: [
      {
        reference: 'sha256:fixture',
        summary: 'Fixture content id evidence',
        type: 'ContentId',
      },
    ],
    id: 'quarantine-jury:fixture',
    jurors: ['actor:fixture-alpha', 'actor:fixture-beta'],
    localReason: 'Fixture local quarantine reason',
    minJurorVotes: 2,
  },
  routeAttempts: [
    {
      channelId: 'safe-review',
      createdAt: '2026-04-30T21:51:00Z',
      failedJurors: [],
      id: 'route-1',
      podId: 'quarantine-jury',
      routedJurors: ['actor:fixture-alpha'],
      success: true,
      targetJurors: ['actor:fixture-alpha'],
    },
  ],
  verdicts: [
    {
      evidence: [],
      id: 'verdict-1',
      juror: 'actor:fixture-alpha',
      reason: 'Fixture juror evidence supports release.',
      verdict: 'ReleaseCandidate',
    },
  ],
};

describe('QuarantineJury', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    quarantineJuryApi.getRequests.mockResolvedValue([
      {
        createdAt: '2026-04-30T21:50:00Z',
        id: 'quarantine-jury:fixture',
        jurors: ['actor:fixture-alpha', 'actor:fixture-beta'],
        localReason: 'Fixture local quarantine reason',
        minJurorVotes: 2,
      },
    ]);
    quarantineJuryApi.getReview.mockResolvedValue(review);
    quarantineJuryApi.routeRequest.mockResolvedValue({
      id: 'route-2',
      success: true,
    });
    quarantineJuryApi.acceptReleaseCandidate.mockResolvedValue({
      decision: {
        acceptedBy: 'local-user',
        id: 'decision-1',
      },
      errors: [],
    });
  });

  afterEach(async () => {
    cleanup();
    await resetInterfaceLanguage();
    vi.unstubAllGlobals();
  });

  it('loads jury review evidence, routes explicitly, and accepts through confirmation', async () => {
    render(<QuarantineJury />);

    await screen.findByText('Fixture content id evidence');
    expect(screen.getByText('quarantine-jury:fixture')).toBeInTheDocument();
    expect(document.querySelector('.quarantine-jury-detail-head'))
      .toHaveTextContent('Review quarantine-jury:fixture');
    expect(screen.getByText('Fixture local quarantine reason')).toBeInTheDocument();
    expect(screen.getAllByText('Release Candidate').length).toBeGreaterThan(0);
    expect(screen.getByText('Fixture content id evidence')).toBeInTheDocument();
    expect(screen.getByText('Fixture juror evidence supports release.')).toBeInTheDocument();
    expect(screen.getByText('actor:fixture-gamma')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Route to Jurors'));

    await waitFor(() =>
      expect(quarantineJuryApi.routeRequest).toHaveBeenCalledWith(
        'quarantine-jury:fixture',
        expect.objectContaining({
          podId: 'quarantine-jury',
          targetJurors: ['actor:fixture-alpha', 'actor:fixture-beta'],
        }),
      ),
    );
    expect(await screen.findByText('Quarantine Jury route attempt recorded.')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Accept Release Candidate'));
    fireEvent.click(await screen.findByText('Accept Recommendation'));

    await waitFor(() =>
      expect(quarantineJuryApi.acceptReleaseCandidate).toHaveBeenCalledWith(
        'quarantine-jury:fixture',
        expect.objectContaining({
          acceptedBy: 'local-user',
        }),
      ),
    );
    expect(await screen.findByText('Release-candidate recommendation accepted for this review.')).toBeInTheDocument();
  });

  it('ignores malformed review route and verdict lists', async () => {
    quarantineJuryApi.getReview.mockResolvedValue({
      ...review,
      routeAttempts: { bad: true },
      verdicts: 'bad',
    });

    render(<QuarantineJury />);

    await screen.findByText('Fixture content id evidence');
    expect(screen.getByText('quarantine-jury:fixture')).toBeInTheDocument();
    expect(document.querySelector('.quarantine-jury-detail-head'))
      .toHaveTextContent('Review quarantine-jury:fixture');
    expect(screen.getByText('Fixture content id evidence')).toBeInTheDocument();
    expect(screen.queryByText('Fixture juror evidence supports release.')).not.toBeInTheDocument();
  });

  it('localizes only known persisted service errors and preserves unknown router text', async () => {
    stubLocaleCatalogFetch(vi);
    await setInterfaceLanguage('de');
    quarantineJuryApi.getReview.mockResolvedValue({
      ...review,
      routeAttempts: [
        {
          ...review.routeAttempts[0],
          errorMessage: 'Route metadata must be opaque and safe.',
          id: 'route-known',
          success: false,
        },
        {
          ...review.routeAttempts[0],
          errorMessage: 'Remote router detail: retry on the next cycle.',
          id: 'route-unknown',
          success: false,
        },
      ],
    });

    render(<QuarantineJury />);

    expect(await screen.findByText('Routenmetadaten müssen undurchsichtig und sicher sein.'))
      .toBeInTheDocument();
    expect(screen.getByText('Remote router detail: retry on the next cycle.'))
      .toBeInTheDocument();
  });
});
