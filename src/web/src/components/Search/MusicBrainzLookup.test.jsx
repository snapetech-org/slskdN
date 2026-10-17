// <copyright file="MusicBrainzLookup.test.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import * as musicBrainz from '../../lib/musicBrainz';
import MusicBrainzLookup from './MusicBrainzLookup';
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { toast } from 'react-toastify';

vi.mock('../../lib/discoveryGraph', () => ({
  buildDiscoveryGraph: vi.fn(),
}));
vi.mock('../../lib/musicBrainz', () => ({
  resolveTarget: vi.fn(),
}));
vi.mock('../../lib/searches', () => ({
  createBatch: vi.fn(),
}));
vi.mock('react-toastify', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));
vi.mock('./DiscoveryGraphModal', () => ({
  default: () => null,
}));

describe('MusicBrainzLookup', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('rejects malformed target responses without enabling graph actions', async () => {
    musicBrainz.resolveTarget.mockResolvedValue({ data: null });

    render(<MusicBrainzLookup />);

    fireEvent.change(screen.getByPlaceholderText('e.g. 1c3b3668-...'), {
      target: { value: 'release-id' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Resolve target' }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        'The request failed. Try again.',
      ),
    );

    expect(toast.success).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Graph' })).toBeDisabled();
  });
});
