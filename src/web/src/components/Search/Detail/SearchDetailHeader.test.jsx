import SearchDetailHeader from './SearchDetailHeader';
import React from 'react';
import { useMediaQuery } from 'react-responsive';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('react-responsive', () => ({ useMediaQuery: vi.fn() }));

describe('SearchDetailHeader', () => {
  beforeEach(() => {
    useMediaQuery.mockReturnValue(true);
  });

  it('labels a completed search action as Delete before results finish loading', async () => {
    const onRemove = vi.fn();
    const onStop = vi.fn();
    render(
      <SearchDetailHeader
        creating={false}
        disabled={false}
        loaded={false}
        loading={false}
        onCreate={vi.fn()}
        onOpenGraph={vi.fn()}
        onRemove={onRemove}
        onStop={onStop}
        removing={false}
        search={{
          isComplete: true,
          searchText: 'ambient music',
          state: 'Completed, TimedOut',
        }}
        stopping={false}
      />,
    );

    const button = screen.getByRole('button', { name: 'Delete completed search ambient music' });
    expect(button).toHaveTextContent('Delete');
    fireEvent.mouseEnter(button.parentElement);

    await waitFor(() => {
      expect(screen.getByText('Delete this finished search.')).toBeInTheDocument();
    });
    expect(onRemove).not.toHaveBeenCalled();
    expect(onStop).not.toHaveBeenCalled();
  });
});
