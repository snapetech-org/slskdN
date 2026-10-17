import EditModal from './EditModal';
import React from 'react';
import userEvent from '@testing-library/user-event';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import {
  getYaml,
  getYamlLocation,
  updateYaml,
  validateYaml,
} from '../../../lib/options';

vi.mock('../../../lib/options', () => ({
  getYaml: vi.fn(),
  getYamlLocation: vi.fn(),
  updateYaml: vi.fn(),
  validateYaml: vi.fn(),
}));

vi.mock('../../Shared/CodeEditor', () => ({
  default: ({ onChange, value }) => (
    <textarea
      aria-label="Options YAML"
      onChange={(event) => onChange(event.target.value)}
      value={value || ''}
    />
  ),
}));

describe('EditModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getYaml.mockResolvedValue('remote_configuration: true\n');
    getYamlLocation.mockResolvedValue('/etc/slskd/slskd.yml');
    validateYaml.mockResolvedValue(null);
    updateYaml.mockResolvedValue({});
  });

  it('does not save when the current validation response reports an error', async () => {
    validateYaml.mockResolvedValue('invalid yaml');

    render(
      <EditModal
        onClose={vi.fn()}
        open
        theme="dark"
      />,
    );

    fireEvent.change(await screen.findByLabelText('Options YAML'), {
      target: { value: 'remote_configuration: [' },
    });
    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => {
      expect(validateYaml).toHaveBeenCalledWith({
        yaml: 'remote_configuration: [',
      });
    });
    expect(updateYaml).not.toHaveBeenCalled();
    expect(await screen.findByText(/The request failed\. Try again\./)).toBeInTheDocument();
  });

  it('renders structured update errors as stable text', async () => {
    updateYaml.mockRejectedValue({
      response: {
        data: {
          detail: 'Remote configuration is read-only',
          status: 400,
          title: 'Bad Request',
        },
      },
    });

    render(
      <EditModal
        onClose={vi.fn()}
        open
        theme="dark"
      />,
    );

    fireEvent.change(await screen.findByLabelText('Options YAML'), {
      target: { value: 'remote_configuration: false\n' },
    });
    fireEvent.click(screen.getByText('Save'));

    expect(await screen.findByText(/The request failed\. Try again\./))
      .toBeInTheDocument();
  });

  it('shows validation request failures and blocks saving invalid YAML', async () => {
    validateYaml.mockRejectedValue(new Error('YAML validator unavailable'));
    render(
      <EditModal
        onClose={vi.fn()}
        open
        theme="dark"
      />,
    );

    fireEvent.change(await screen.findByLabelText('Options YAML'), {
      target: { value: 'feature: true\n' },
    });

    expect(await screen.findByText(/The request failed\. Try again\./))
      .toBeInTheDocument();
    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => expect(validateYaml).toHaveBeenCalledWith({
      yaml: 'feature: true\n',
    }));
    expect(updateYaml).not.toHaveBeenCalled();
  });

  it('shows the remote options load error and retries in the dialog', async () => {
    const user = userEvent.setup();
    getYaml.mockRejectedValueOnce({
      response: { data: { detail: 'Options file unavailable', status: 503 } },
    });
    render(
      <EditModal
        onClose={vi.fn()}
        open
        theme="dark"
      />,
    );

    expect(await screen.findByText('The request failed. Try again.'))
      .toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Retry Options' }));

    expect(await screen.findByLabelText('Options YAML'))
      .toHaveValue('remote_configuration: true\n');
    expect(getYaml).toHaveBeenCalledTimes(2);
  });
});
