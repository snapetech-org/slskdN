import '@testing-library/jest-dom';
import MessageStream, { autolink } from './MessageStream';
import { __test__ } from './messagingAdapters';
import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const { classifyBody } = __test__;

const setDocumentHidden = (hidden) => {
  Object.defineProperty(document, 'hidden', {
    configurable: true,
    value: hidden,
  });
};

afterEach(() => {
  vi.useRealTimers();
  setDocumentHidden(false);
});

describe('classifyBody', () => {
  it('treats plain text as text', () => {
    expect(classifyBody('hi there')).toEqual({ body: 'hi there', kind: 'text' });
  });

  it('detects /me prefix and strips it', () => {
    expect(classifyBody('/me waves')).toEqual({ body: 'waves', kind: 'me' });
  });

  it('detects CTCP ACTION and strips wrappers', () => {
    const ctcp = `ACTION dances`;
    expect(classifyBody(ctcp)).toEqual({ body: 'dances', kind: 'me' });
  });

  it('parses listen-along JSON payload as a card', () => {
    const payload = {
      action: 'play',
      artist: 'Aphex Twin',
      kind: 'slskdn.listenAlong.v1',
      title: 'Xtal',
    };
    const result = classifyBody(JSON.stringify(payload));
    expect(result.kind).toBe('listenalong');
    expect(result.meta.artist).toBe('Aphex Twin');
  });

  it('ignores unrelated JSON', () => {
    const result = classifyBody('{"foo":"bar"}');
    expect(result.kind).toBe('text');
  });
});

const buildAdapter = (messages) => ({
  list: () => Promise.resolve({ messages }),
  pollIntervalMs: 1_000_000,
});

describe('MessageStream', () => {
  it('splits message URLs into link parts', () => {
    expect(autolink('open https://example.test/path, then reply')).toEqual([
      'open ',
      { url: 'https://example.test/path' },
      ', then reply',
    ]);
  });

  it('renders messages, collapses same-sender bursts, and shows listen-along card', async () => {
    const t = 1_700_000_000_000;
    const adapter = buildAdapter([
      { body: 'hey', id: 'a', isSelf: false, kind: 'text', sender: 'alice', ts: t },
      { body: 'still alice', id: 'b', isSelf: false, kind: 'text', sender: 'alice', ts: t + 5_000 },
      { body: 'hi alice', id: 'c', isSelf: true, kind: 'text', sender: 'me', ts: t + 10_000 },
      {
        body: 'whatever',
        id: 'd',
        isSelf: false,
        kind: 'listenalong',
        meta: { action: 'play', artist: 'Aphex Twin', title: 'Xtal' },
        sender: 'carol',
        ts: t + 15_000,
      },
    ]);

    render(<MessageStream adapter={adapter} />);

    await waitFor(() => {
      expect(screen.getByText('hey')).toBeInTheDocument();
    });

    expect(screen.getByText('still alice')).toBeInTheDocument();
    expect(screen.getByText('hi alice')).toBeInTheDocument();
    expect(screen.getByText('Xtal')).toBeInTheDocument();

    // alice nick should appear once (collapsed for the second message)
    const aliceNicks = screen.getAllByRole('button', { name: 'alice' });
    expect(aliceNicks).toHaveLength(1);

    // listen-along card uses its own marker
    expect(screen.getByText('— Aphex Twin')).toBeInTheDocument();
  });

  it('shows empty hint when there are no messages', async () => {
    const adapter = buildAdapter([]);
    render(<MessageStream adapter={adapter} emptyHint="nothing here yet" />);
    await waitFor(() => {
      expect(screen.getByText('nothing here yet')).toBeInTheDocument();
    });
  });

  it('shows a message-list failure and retries when the initial load fails', async () => {
    const adapter = {
      list: vi.fn()
        .mockRejectedValueOnce(new Error('Message service unavailable'))
        .mockResolvedValueOnce({ messages: [] }),
      pollIntervalMs: 1_000_000,
    };
    render(<MessageStream adapter={adapter} emptyHint="No messages yet." />);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The message history could not be loaded.',
    );
    expect(screen.queryByText('No messages yet.')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));

    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(screen.getByText('No messages yet.')).toBeInTheDocument();
    });
  });

  it('keeps the last loaded messages visible after polling fails and retries in place', async () => {
    const firstMessage = {
      body: 'last known message',
      id: 'known',
      isSelf: false,
      kind: 'text',
      sender: 'alice',
      ts: 1_700_000_000_000,
    };
    const adapter = {
      list: vi.fn()
        .mockResolvedValueOnce({ messages: [firstMessage] })
        .mockRejectedValueOnce({ response: { data: { detail: 'Chat refresh failed' } } })
        .mockResolvedValueOnce({ messages: [firstMessage] }),
      pollIntervalMs: 1_000_000,
    };
    render(<MessageStream adapter={adapter} />);
    expect(await screen.findByText('last known message')).toBeInTheDocument();

    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
    });
    expect(await screen.findByRole('alert')).toHaveTextContent('The message history could not be loaded.');
    expect(screen.getByText('last known message')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(screen.getByText('last known message')).toBeInTheDocument();
    });
  });

  it('does not poll until visible and suspends polling while hidden', async () => {
    vi.useFakeTimers();
    setDocumentHidden(true);
    const list = vi.fn().mockResolvedValue({ messages: [] });
    const adapter = { list, pollIntervalMs: 1_000 };

    render(<MessageStream adapter={adapter} />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(list).not.toHaveBeenCalled();

    await act(async () => {
      setDocumentHidden(false);
      document.dispatchEvent(new Event('visibilitychange'));
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(list).toHaveBeenCalledTimes(1);

    await act(async () => {
      setDocumentHidden(true);
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(5_000);
    });
    expect(list).toHaveBeenCalledTimes(1);
  });

  it('does not overlap slow message refreshes', async () => {
    vi.useFakeTimers();
    setDocumentHidden(false);
    let resolveList;
    const list = vi.fn(() => new Promise((resolve) => {
      resolveList = resolve;
    }));
    const adapter = { list, pollIntervalMs: 1_000 };

    render(<MessageStream adapter={adapter} />);
    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });
    expect(list).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveList({ messages: [] });
      await Promise.resolve();
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(1_000);
    });
    expect(list).toHaveBeenCalledTimes(2);
  });

  it('autolinks URLs in message bodies', async () => {
    const t = 1_700_000_000_000;
    const adapter = buildAdapter([
      {
        body: 'check https://example.com/path?q=1 and ftp://files.example.org out',
        id: 'm1',
        isSelf: false,
        kind: 'text',
        sender: 'alice',
        ts: t,
      },
    ]);
    render(<MessageStream adapter={adapter} />);
    await waitFor(() => {
      expect(screen.getByText('https://example.com/path?q=1')).toBeInTheDocument();
    });
    const link = screen.getByText('https://example.com/path?q=1');
    expect(link.tagName).toBe('A');
    expect(link).toHaveAttribute('href', 'https://example.com/path?q=1');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    expect(screen.getByText('ftp://files.example.org')).toHaveAttribute(
      'href',
      'ftp://files.example.org',
    );
  });

  it('searches within the active message stream and highlights matches', async () => {
    const t = 1_700_000_000_000;
    const adapter = buildAdapter([
      { body: 'first needle', id: 's1', isSelf: false, kind: 'text', sender: 'alice', ts: t },
      { body: 'second line', id: 's2', isSelf: false, kind: 'text', sender: 'bob', ts: t + 1_000 },
      { body: 'third needle', id: 's3', isSelf: false, kind: 'text', sender: 'carol', ts: t + 2_000 },
    ]);

    render(<MessageStream adapter={adapter} />);

    await waitFor(() => {
      expect(screen.getByText('first needle')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('Search active conversation'), {
      target: { value: 'needle' },
    });

    expect(screen.getByText('1/2')).toBeInTheDocument();
    expect(screen.getAllByText('needle')).toHaveLength(2);

    fireEvent.click(screen.getByLabelText('Next search match'));
    expect(screen.getByText('2/2')).toBeInTheDocument();
  });
});

describe('MessageStream hover actions', () => {
  it('invokes onQuote and onCopy with the original message', async () => {
    const t = 1_700_000_000_000;
    const adapter = {
      list: () =>
        Promise.resolve({
          messages: [
            {
              body: 'hey',
              id: 'q1',
              isSelf: false,
              kind: 'text',
              sender: 'alice',
              ts: t,
            },
          ],
        }),
      pollIntervalMs: 1_000_000,
    };
    const onQuote = vi.fn();
    const onCopy = vi.fn();

    render(
      <MessageStream
        adapter={adapter}
        onCopy={onCopy}
        onQuote={onQuote}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('hey')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText('Quote message'));
    expect(onQuote).toHaveBeenCalledWith(
      expect.objectContaining({ body: 'hey', sender: 'alice' }),
    );

    fireEvent.click(screen.getByLabelText('Copy message'));
    expect(onCopy).toHaveBeenCalledWith(
      expect.objectContaining({ body: 'hey' }),
    );
  });

  it('omits the action toolbar when no callbacks are provided', async () => {
    const adapter = {
      list: () =>
        Promise.resolve({
          messages: [
            {
              body: 'hey',
              id: 'q2',
              isSelf: false,
              kind: 'text',
              sender: 'alice',
              ts: 1_700_000_000_000,
            },
          ],
        }),
      pollIntervalMs: 1_000_000,
    };
    render(<MessageStream adapter={adapter} />);
    await waitFor(() => {
      expect(screen.getByText('hey')).toBeInTheDocument();
    });
    expect(screen.queryByLabelText('Quote message')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Copy message')).not.toBeInTheDocument();
  });
});

describe('autolink', () => {
  it('returns the original text for plain strings', () => {
    expect(autolink('no urls here')).toEqual(['no urls here']);
  });

  it('splits a string with one url', () => {
    const parts = autolink('hi https://example.com cool');
    expect(parts).toEqual([
      'hi ',
      { url: 'https://example.com' },
      ' cool',
    ]);
  });

  it('does not include trailing punctuation in the url', () => {
    const parts = autolink('see https://example.com.');
    expect(parts[1]).toEqual({ url: 'https://example.com' });
    expect(parts[2]).toBe('.');
  });

  it('handles multiple urls', () => {
    const parts = autolink('one http://a.example two http://b.example three');
    const urls = parts.filter((part) => typeof part !== 'string').map((part) => part.url);
    expect(urls).toEqual(['http://a.example', 'http://b.example']);
  });
});
