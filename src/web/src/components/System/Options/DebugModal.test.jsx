import DebugModal from './DebugModal';
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { getCurrentDebugView } from '../../../lib/options';

vi.mock('../../../lib/options', () => ({
  getCurrentDebugView: vi.fn(),
}));

vi.mock('../../Shared', () => ({
  CodeEditor: ({ value }) => <pre data-testid="debug-view">{value}</pre>,
  PlaceholderSegment: () => <div role="status">Loading debug view</div>,
  Switch: ({ children, ...rest }) => Object.values(rest).find(Boolean) || children,
}));

describe('DebugModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows the failure detail and retries the debug-view request', async () => {
    getCurrentDebugView
      .mockRejectedValueOnce({
        response: { data: { detail: 'Options view unavailable', status: 503 } },
      })
      .mockResolvedValueOnce('resolved: true\n');

    render(<DebugModal onClose={vi.fn()} open theme="dark" />);

    expect(await screen.findByText('Could not load the debug view.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retry Debug View' }));

    await waitFor(() => {
      expect(screen.getByTestId('debug-view')).toHaveTextContent('resolved: true');
    });
    expect(getCurrentDebugView).toHaveBeenCalledTimes(2);
  });
});
