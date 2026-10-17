import '@testing-library/jest-dom';
import * as optionsApi from '../../../lib/options';
import AdminPolicies from './index';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import YAML from 'yaml';

vi.mock('../../../lib/options', () => ({
  getYaml: vi.fn(),
  updateYaml: vi.fn(),
}));

const renderPolicies = (options = {}) =>
  render(
    <AdminPolicies
      options={{
        remoteConfiguration: true,
        ...options,
      }}
    />,
  );

describe('AdminPolicies', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('surfaces the broad operator policy groups without exposing configured secrets', () => {
    renderPolicies({
      integrations: {
        webhooks: {
          notify: {
            call: {
              url: 'https://hooks.example/slskdn',
            },
            on: ['DownloadFileComplete'],
            retry: {
              attempts: 3,
            },
          },
        },
        scripts: {
          local: {
            on: ['All'],
            run: {
              command: './hook.sh',
            },
          },
        },
      },
      web: {
        authentication: {
          apiKeys: {
            automation: {
              key: 'existing-api-key-secret',
            },
          },
          jwt: {
            key: 'existing-jwt-secret',
          },
        },
        https: {
          certificate: {
            password: 'existing-pfx-secret',
          },
        },
      },
    });

    expect(screen.getByText('Actions: Webhooks and Scripts')).toBeInTheDocument();
    expect(screen.getByText('Transfer Policy')).toBeInTheDocument();
    expect(screen.getByText('Security and Access')).toBeInTheDocument();
    expect(screen.getByText('Search and Network Policy')).toBeInTheDocument();
    expect(screen.getByText('Retention and Storage')).toBeInTheDocument();
    expect(screen.getByText('JWT Key Set')).toBeInTheDocument();
    expect(screen.getByText('API Key Set')).toBeInTheDocument();
    expect(screen.getByText('Certificate Password Set')).toBeInTheDocument();
    expect(screen.queryByText('existing-api-key-secret')).not.toBeInTheDocument();
    expect(screen.queryByText('existing-jwt-secret')).not.toBeInTheDocument();
    expect(screen.queryByText('existing-pfx-secret')).not.toBeInTheDocument();
  });

  it('saves guided policy settings to YAML through the options API', async () => {
    const user = userEvent.setup();
    optionsApi.getYaml.mockResolvedValue('web:\n  authentication: {}\n');
    optionsApi.updateYaml.mockResolvedValue({});
    renderPolicies();

    await user.type(screen.getByLabelText('Webhook policy name'), 'ops');
    await user.type(
      screen.getByLabelText('Webhook target URL'),
      'https://hooks.example/slskdn',
    );
    await user.type(
      screen.getByLabelText('Webhook event names'),
      'DownloadFileComplete\nPrivateMessageReceived',
    );
    await user.click(screen.getByLabelText('Ignore webhook certificate errors'));
    await user.type(screen.getByLabelText('Script policy name'), 'local');
    await user.type(screen.getByLabelText('Script command'), './hook.sh');
    await user.type(screen.getByLabelText('API key replacement value'), 'new-api-key-secret');
    await user.type(screen.getByLabelText('API key policy name'), 'automation');
    await user.type(screen.getByLabelText('JWT replacement key'), 'new-jwt-secret');
    await user.click(screen.getByLabelText('Enforce web security hardening'));
    await user.click(screen.getByLabelText('Enable auto replace stuck downloads'));
    await user.click(screen.getByLabelText('Use LAN-only DHT rendezvous'));
    await user.click(screen.getByLabelText('Probe share media attributes'));
    await user.type(
      screen.getByLabelText('Global download exclusions'),
      'acapella\ninstrumental\na cappella',
    );

    await user.click(screen.getByRole('button', { name: 'Save YAML' }));

    await waitFor(() => expect(optionsApi.updateYaml).toHaveBeenCalledTimes(1));
    const yaml = optionsApi.updateYaml.mock.calls[0][0].yaml;
    const saved = YAML.parse(yaml);

    expect(saved.integrations.webhooks.ops.on).toEqual([
      'DownloadFileComplete',
      'PrivateMessageReceived',
    ]);
    expect(saved.integrations.webhooks.ops.call.url).toBe(
      'https://hooks.example/slskdn',
    );
    expect(saved.integrations.webhooks.ops.call.ignore_certificate_errors).toBe(
      true,
    );
    expect(saved.integrations.scripts.local.run.command).toBe('./hook.sh');
    expect(saved.transfers.download.auto_replace_stuck).toBe(true);
    expect(saved.scheduled_limits).toBeUndefined();
    expect(saved.transfers.upload.scheduled_limits.enabled).toBe(false);
    expect(saved.transfers.download.scheduled_limits.enabled).toBe(false);
    expect(saved.filters.search_retention.max_age_days).toBe(30);
    expect(saved.filters.search_retention.max_count).toBe(1000);
    expect(saved.filters.search_retention.cleanup_interval_seconds).toBe(86400);
    expect(saved.filters.download.exclude).toEqual([
      'acapella',
      'instrumental',
      'a cappella',
    ]);
    expect(saved.features).toBeUndefined();
    expect(saved.feature.scene_pod_bridge).toBe(false);
    expect(saved.web.enforce_security).toBe(true);
    expect(saved.web.authentication.jwt.key).toBe('new-jwt-secret');
    expect(saved.web.authentication.api_keys.automation.key).toBe(
      'new-api-key-secret',
    );
    expect(saved.dht.lan_only).toBe(true);
    expect(saved.shares.probe_media_attributes).toBe(false);
    expect(saved.retention.logs).toBe(14);
  });

  it('requires a key value before saving a new API key policy', async () => {
    const user = userEvent.setup();
    optionsApi.getYaml.mockResolvedValue('web:\n  authentication: {}\n');
    optionsApi.updateYaml.mockResolvedValue({});
    renderPolicies();

    await user.clear(screen.getByLabelText('API key policy name'));
    await user.type(screen.getByLabelText('API key policy name'), 'automation');
    await user.clear(screen.getByLabelText('API key scopes'));
    await user.type(screen.getByLabelText('API key scopes'), 'search:read');

    const save = screen.getByRole('button', { name: 'Save YAML' });
    expect(save).toBeDisabled();
    expect(
      screen.getByText('A new API key needs a name and value before its policy can be saved.'),
    ).toBeInTheDocument();

    await user.type(screen.getByLabelText('API key replacement value'), 'new-api-key-secret');
    expect(save).toBeEnabled();
    await user.click(save);

    await waitFor(() => expect(optionsApi.updateYaml).toHaveBeenCalledTimes(1));
    const saved = YAML.parse(optionsApi.updateYaml.mock.calls[0][0].yaml);
    expect(saved.web.authentication.api_keys.automation).toMatchObject({
      key: 'new-api-key-secret',
      role: 'ReadOnly',
      scopes: 'search:read',
    });
  });

  it('requires a replacement value before adding API policy under a new name', async () => {
    const user = userEvent.setup();
    optionsApi.getYaml.mockResolvedValue(`
web:
  authentication:
    api_keys:
      automation:
        key: existing-api-key-secret
`);
    optionsApi.updateYaml.mockResolvedValue({});
    renderPolicies({
      web: {
        authentication: {
          apiKeys: {
            automation: { key: 'existing-api-key-secret' },
          },
        },
      },
    });

    const name = screen.getByLabelText('API key policy name');
    await user.clear(name);
    await user.type(name, 'replacement');

    const save = screen.getByRole('button', { name: 'Save YAML' });
    expect(save).toBeDisabled();
    expect(
      screen.getByText(
        'Enter a key value before adding API key settings under a different name.',
      ),
    ).toBeInTheDocument();

    await user.type(screen.getByLabelText('API key replacement value'), 'replacement-secret');
    await user.click(save);
    await waitFor(() => expect(optionsApi.updateYaml).toHaveBeenCalledTimes(1));
    const saved = YAML.parse(optionsApi.updateYaml.mock.calls[0][0].yaml);
    expect(saved.web.authentication.api_keys).toEqual({
      automation: { key: 'existing-api-key-secret' },
      replacement: {
        cidr: '127.0.0.1/32,::1/128',
        key: 'replacement-secret',
        role: 'ReadOnly',
        scopes: '*',
      },
    });
  });

  it('shows save errors and keeps the policy form available for retry', async () => {
    const user = userEvent.setup();
    optionsApi.getYaml.mockResolvedValue('web:\n  authentication: {}\n');
    optionsApi.updateYaml
      .mockRejectedValueOnce({ response: { data: 'Configuration was rejected.' } })
      .mockResolvedValueOnce({});
    renderPolicies();

    const save = screen.getByRole('button', { name: 'Save YAML' });
    await user.click(save);
    expect(await screen.findByText('The request failed. Try again.')).toBeInTheDocument();
    expect(save).toBeEnabled();

    await user.click(save);
    expect(await screen.findByText(
      'Policy settings saved to YAML. Restart-signalled options still require a daemon restart.',
    )).toBeInTheDocument();
  });

  it('blocks empty required integer fields instead of silently using defaults', async () => {
    const user = userEvent.setup();
    optionsApi.getYaml.mockResolvedValue('transfers:\n  upload:\n    slots: 12\n');
    optionsApi.updateYaml.mockResolvedValue({});
    renderPolicies({
      transfers: {
        upload: { slots: 12 },
      },
    });

    await user.clear(screen.getByLabelText('Global upload slots'));

    const save = screen.getByRole('button', { name: 'Save YAML' });
    expect(save).toBeDisabled();
    expect(screen.getByText('Upload slots must be a whole number.')).toBeInTheDocument();

    await user.type(screen.getByLabelText('Global upload slots'), '16');
    expect(save).toBeEnabled();
    await user.click(save);
    await waitFor(() => expect(optionsApi.updateYaml).toHaveBeenCalledTimes(1));

    const saved = YAML.parse(optionsApi.updateYaml.mock.calls[0][0].yaml);
    expect(saved.transfers.upload.slots).toBe(16);
  });

  it('does not invent empty webhook or script policies when saving other settings', async () => {
    const user = userEvent.setup();
    optionsApi.getYaml.mockResolvedValue('web:\n  authentication: {}\n');
    optionsApi.updateYaml.mockResolvedValue({});
    renderPolicies();

    expect(screen.getByLabelText('Webhook policy name')).toHaveValue('');
    expect(screen.getByLabelText('Script policy name')).toHaveValue('');

    await user.click(screen.getByRole('button', { name: 'Save YAML' }));

    await waitFor(() => expect(optionsApi.updateYaml).toHaveBeenCalledTimes(1));
    const saved = YAML.parse(optionsApi.updateYaml.mock.calls[0][0].yaml);

    expect(saved.integrations).toBeUndefined();
  });

  it('does not emit invalid legacy auto-replace defaults or an empty API key', async () => {
    const user = userEvent.setup();
    optionsApi.getYaml.mockResolvedValue(`
auto_replace:
  size_threshold_percent: 0
web:
  authentication: {}
`);
    optionsApi.updateYaml.mockResolvedValue({});
    renderPolicies({
      autoReplace: {
        sizeThresholdPercent: 0,
      },
      web: {
        authentication: {
          apiKeys: {},
        },
      },
    });

    await user.clear(screen.getByLabelText('Incoming search concurrency'));
    await user.type(screen.getByLabelText('Incoming search concurrency'), '12');
    await user.click(screen.getByRole('button', { name: 'Save YAML' }));

    await waitFor(() => expect(optionsApi.updateYaml).toHaveBeenCalledTimes(1));
    const saved = YAML.parse(optionsApi.updateYaml.mock.calls[0][0].yaml);

    expect(saved.auto_replace.size_threshold_percent).toBe(0);
    expect(saved.transfers.download.auto_replace_threshold).toBeUndefined();
    expect(saved.transfers.download.auto_replace_interval).toBeUndefined();
    expect(saved.web.authentication.api_keys).toBeUndefined();
    expect(saved.throttling.search.incoming.concurrency).toBe(12);
  });

  it('preserves an existing API key when no replacement is supplied', async () => {
    const user = userEvent.setup();
    const existingKey = 'existing-api-key-secret';
    optionsApi.getYaml.mockResolvedValue(`
web:
  authentication:
    api_keys:
      automation:
        key: ${existingKey}
`);
    optionsApi.updateYaml.mockResolvedValue({});
    renderPolicies({
      web: {
        authentication: {
          apiKeys: {
            automation: {
              key: existingKey,
            },
          },
        },
      },
    });

    await user.click(screen.getByRole('button', { name: 'Save YAML' }));

    await waitFor(() => expect(optionsApi.updateYaml).toHaveBeenCalledTimes(1));
    const saved = YAML.parse(optionsApi.updateYaml.mock.calls[0][0].yaml);

    expect(saved.web.authentication.api_keys.automation.key).toBe(existingKey);
  });

  it('requires complete webhook and script policy drafts', async () => {
    const user = userEvent.setup();
    renderPolicies();

    await user.type(screen.getByLabelText('Webhook policy name'), 'ops');
    await user.type(screen.getByLabelText('Script policy name'), 'local');

    expect(screen.getByRole('button', { name: 'Save YAML' })).toBeDisabled();
    expect(screen.getByText('Webhook settings need a target URL.')).toBeInTheDocument();
    expect(
      screen.getByText('Script settings need either a command or an executable.'),
    ).toBeInTheDocument();
  });

  it('allows loopback-only no-auth without passthrough CIDRs', () => {
    renderPolicies({
      web: {
        allowRemoteNoAuth: false,
        authentication: {
          disabled: true,
        },
      },
    });

    expect(screen.getByRole('button', { name: 'Save YAML' })).toBeEnabled();
    expect(
      screen.queryByText('Remote no-auth mode needs an explicit CIDR allowlist.'),
    ).not.toBeInTheDocument();
  });

  it('still requires a CIDR allowlist for remote no-auth', () => {
    renderPolicies({
      web: {
        allowRemoteNoAuth: true,
        authentication: {
          disabled: true,
        },
      },
    });

    expect(screen.getByRole('button', { name: 'Save YAML' })).toBeDisabled();
    expect(
      screen.getByText('Remote no-auth mode needs an explicit CIDR allowlist.'),
    ).toBeInTheDocument();
  });

  it('keeps save disabled when remote configuration is off', () => {
    render(<AdminPolicies options={{ remoteConfiguration: false }} />);

    expect(
      screen.getByText(/Remote configuration is disabled/),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save YAML' })).toBeDisabled();
  });

  it('allows saving when HTTPS uses the generated certificate', () => {
    renderPolicies({
      web: {
        https: {
          disabled: false,
          certificate: {
            pfx: '',
          },
        },
      },
    });

    expect(screen.getByRole('button', { name: 'Save YAML' })).toBeEnabled();
    expect(screen.queryByText('HTTPS needs a certificate PFX path.')).not.toBeInTheDocument();
  });
});
