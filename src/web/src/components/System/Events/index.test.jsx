import '@testing-library/jest-dom';
import Events from './index';
import { list } from '../../../lib/events';
import React from 'react';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../lib/events', () => ({
  list: vi.fn(),
}));

describe('Events', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders malformed event data without crashing the table', async () => {
    list.mockResolvedValue({
      events: [
        {
          data: '{not-json',
          id: 'event-1',
          timestamp: '2026-05-05T18:30:00Z',
          type: 'MalformedPayload',
        },
      ],
      totalCount: 1,
    });

    render(<Events />);

    expect(await screen.findByText('{not-json')).toBeInTheDocument();
    expect(screen.getByText('MalformedPayload')).toBeInTheDocument();
  });

  it('pretty-prints valid event JSON data', async () => {
    list.mockResolvedValue({
      events: [
        {
          data: JSON.stringify({ message: 'ok' }),
          id: 'event-2',
          timestamp: '2026-05-05T18:31:00Z',
          type: 'ValidPayload',
        },
      ],
      totalCount: 1,
    });

    render(<Events />);

    expect(await screen.findByText(/"message": "ok"/)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Show identifier for event event-2' }),
    ).toBeInTheDocument();
    expect(screen.getByText(/"message": "ok"/).closest('pre')).toBeInTheDocument();
  });

  it('renders an empty table for malformed event list payloads', async () => {
    list.mockResolvedValue({
      events: [],
      totalCount: 1,
    });

    render(<Events />);

    expect(await screen.findByText('No events')).toBeInTheDocument();
  });

  it('retries after a failed event request', async () => {
    list
      .mockRejectedValueOnce(new Error('events unavailable'))
      .mockResolvedValueOnce({
        events: [{
          data: '{"message":"recovered"}',
          id: 'recovered-event',
          timestamp: '2026-05-05T18:32:00Z',
          type: 'RecoveredEvent',
        }],
        totalCount: 1,
      });

    render(<Events />);

    expect(await screen.findByText('The request failed. Try again.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Try Again' }));

    expect(await screen.findByText('RecoveredEvent')).toBeInTheDocument();
    expect(list).toHaveBeenCalledTimes(2);
  });

  it('ignores a slower response for a page that is no longer active', async () => {
    let completeSecondPage;
    list
      .mockResolvedValueOnce({
        events: [{
          data: '{}',
          id: 'initial-event',
          timestamp: '2026-05-05T18:33:00Z',
          type: 'InitialEvent',
        }],
        totalCount: 30,
      })
      .mockReturnValueOnce(
        new Promise((resolve) => {
          completeSecondPage = resolve;
        }),
      )
      .mockResolvedValueOnce({
        events: [{
          data: '{}',
          id: 'returned-first-page-event',
          timestamp: '2026-05-05T18:34:00Z',
          type: 'ReturnedFirstPageEvent',
        }],
        totalCount: 30,
      });

    render(<Events />);
    expect(await screen.findByText('InitialEvent')).toBeInTheDocument();

    fireEvent.click(screen.getByText('2', { exact: true }));
    await waitFor(() =>
      expect(list).toHaveBeenNthCalledWith(2, { limit: 10, offset: 10 }),
    );
    fireEvent.click(screen.getByText('1', { exact: true }));
    expect(await screen.findByText('ReturnedFirstPageEvent')).toBeInTheDocument();

    await act(async () => {
      completeSecondPage({
        events: [{
          data: '{}',
          id: 'stale-second-page-event',
          timestamp: '2026-05-05T18:35:00Z',
          type: 'StaleSecondPageEvent',
        }],
        totalCount: 30,
      });
    });

    expect(screen.queryByText('StaleSecondPageEvent')).not.toBeInTheDocument();
    expect(screen.getByText('ReturnedFirstPageEvent')).toBeInTheDocument();
  });
});
