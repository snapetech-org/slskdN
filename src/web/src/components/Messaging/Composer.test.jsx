import '@testing-library/jest-dom';
import Composer, { matchSuggestions } from './Composer';
import React, { useState } from 'react';
import userEvent from '@testing-library/user-event';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

const COMMANDS = [
  { description: 'Italic action.', name: 'me', syntax: '/me <action>' },
  { description: 'Open DM.', name: 'msg', syntax: '/msg <user>' },
  { description: 'Join room.', name: 'join', syntax: '/join <room>' },
  {
    aliases: ['part', 'leave'],
    description: 'Close tab.',
    name: 'close',
    syntax: '/close',
  },
  { description: 'Show help.', name: 'help', syntax: '/help' },
];

describe('matchSuggestions', () => {
  it('returns empty when input does not start with slash', () => {
    expect(matchSuggestions('hello', COMMANDS)).toEqual([]);
  });

  it('returns all commands when input is just /', () => {
    expect(matchSuggestions('/', COMMANDS)).toHaveLength(COMMANDS.length);
  });

  it('filters by prefix match on name', () => {
    const result = matchSuggestions('/m', COMMANDS);
    expect(result.map((c) => c.name)).toEqual(['me', 'msg']);
  });

  it('matches aliases too', () => {
    const result = matchSuggestions('/par', COMMANDS);
    expect(result.map((c) => c.name)).toEqual(['close']);
  });

  it('returns empty after a space (command already chosen)', () => {
    expect(matchSuggestions('/me waving', COMMANDS)).toEqual([]);
  });
});

const buildAdapter = () => ({
  list: () => Promise.resolve({ messages: [] }),
  send: vi.fn(() => Promise.resolve()),
});

const ControlledComposer = (props) => {
  const [value, setValue] = useState(props.initial || '');
  return (
    <Composer
      {...props}
      onChange={setValue}
      value={value}
    />
  );
};

describe('Composer', () => {
  it('shows suggestions when input starts with slash and Tab autocompletes', () => {
    const adapter = buildAdapter();
    render(<ControlledComposer adapter={adapter} commands={COMMANDS} />);
    const input = screen.getByLabelText('Message composer');

    fireEvent.change(input, { target: { value: '/m' } });
    expect(screen.getByText('/me <action>')).toBeInTheDocument();
    expect(screen.getByText('/msg <user>')).toBeInTheDocument();

    fireEvent.keyDown(input, { key: 'Tab' });
    expect(input.value).toBe('/me ');
  });

  it('explains command suggestions and why Send is disabled without sending', async () => {
    const user = userEvent.setup();
    const adapter = buildAdapter();
    render(<ControlledComposer adapter={adapter} commands={COMMANDS} />);

    const send = screen.getByRole('button', { name: 'Send' });
    expect(send).toBeDisabled();
    await user.hover(send.parentElement);
    expect(await screen.findByText(/Enter a message in the active conversation/))
      .toBeInTheDocument();

    const input = screen.getByLabelText('Message composer');
    fireEvent.change(input, { target: { value: '/me' } });
    await user.hover(screen.getByRole('option', { name: /\/me <action>/ }));
    expect(await screen.findByText(/Select to insert \/me <action> in the composer/))
      .toBeInTheDocument();
    expect(adapter.send).not.toHaveBeenCalled();
  });

  it('routes /help to the onCommand handler instead of sending', async () => {
    const adapter = buildAdapter();
    const onCommand = vi.fn(({ name }) => name === 'help');
    render(
      <ControlledComposer
        adapter={adapter}
        commands={COMMANDS}
        onCommand={onCommand}
      />,
    );
    const input = screen.getByLabelText('Message composer');
    fireEvent.change(input, { target: { value: '/help' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => {
      expect(onCommand).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'help' }),
      );
    });
    expect(adapter.send).not.toHaveBeenCalled();
    expect(input.value).toBe('');
  });

  it('navigates suggestions with arrow keys', () => {
    const adapter = buildAdapter();
    render(<ControlledComposer adapter={adapter} commands={COMMANDS} />);
    const input = screen.getByLabelText('Message composer');

    fireEvent.change(input, { target: { value: '/' } });
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    fireEvent.keyDown(input, { key: 'Tab' });
    expect(input.value).toBe('/msg ');
  });

  it('sends plain text via adapter.send when not a command', async () => {
    const adapter = buildAdapter();
    render(<ControlledComposer adapter={adapter} commands={COMMANDS} />);
    const input = screen.getByLabelText('Message composer');
    fireEvent.change(input, { target: { value: 'hello world' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => {
      expect(adapter.send).toHaveBeenCalledWith('hello world');
    });
  });

  it('shows send failures and keeps the draft available for retry', async () => {
    const user = userEvent.setup();
    const adapter = buildAdapter();
    adapter.send
      .mockRejectedValueOnce(new Error('Network disconnected'))
      .mockResolvedValueOnce();
    render(<ControlledComposer adapter={adapter} commands={COMMANDS} />);
    const input = screen.getByLabelText('Message composer');
    fireEvent.change(input, { target: { value: 'hello again' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(await screen.findByRole('alert'))
      .toHaveTextContent('The message could not be sent.');
    expect(input).toHaveValue('hello again');
    await user.click(screen.getByRole('button', { name: 'Send' }));

    await waitFor(() => expect(adapter.send).toHaveBeenCalledTimes(2));
    expect(input).toHaveValue('');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('reflects value updates from the parent', () => {
    const adapter = buildAdapter();
    render(
      <ControlledComposer
        adapter={adapter}
        commands={COMMANDS}
        initial={'> alice: hi\n'}
      />,
    );
    const input = screen.getByLabelText('Message composer');
    expect(input.value).toBe('> alice: hi\n');
  });
});
