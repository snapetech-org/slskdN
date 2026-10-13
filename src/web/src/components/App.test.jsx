import '@testing-library/jest-dom';
import App from './App';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

const {
  check,
  createApplicationHubConnection,
  getSecurityEnabled,
  getRoomActivity,
  hasUnAcknowledgedMessages,
  isLoggedIn,
  logout,
} = vi.hoisted(() => ({
  check: vi.fn(),
  createApplicationHubConnection: vi.fn(),
  getSecurityEnabled: vi.fn(),
  getRoomActivity: vi.fn(),
  hasUnAcknowledgedMessages: vi.fn(),
  isLoggedIn: vi.fn(),
  logout: vi.fn(),
}));

vi.mock('../lib/chat', () => ({
  hasUnAcknowledgedMessages,
}));

vi.mock('../lib/hubFactory', () => ({
  createApplicationHubConnection,
}));

vi.mock('../lib/rooms', () => ({
  getActivity: getRoomActivity,
}));

vi.mock('../lib/session', () => ({
  check,
  getSecurityEnabled,
  isLoggedIn,
  login: vi.fn(),
  logout,
}));

vi.mock('../lib/token', () => ({
  isPassthroughEnabled: vi.fn(() => false),
}));

vi.mock('../lib/relay', () => ({
  connect: vi.fn(),
  disconnect: vi.fn(),
}));

vi.mock('../lib/server', () => ({
  connect: vi.fn(),
  disconnect: vi.fn(),
}));

vi.mock('./Browse/Browse', () => ({ default: () => <div>Browse</div> }));
vi.mock('./Chat/Chat', () => ({ default: () => <div>Chat</div> }));
vi.mock('./Dashboard/Dashboard', () => ({ default: () => <div>Dashboard</div> }));
vi.mock('./Collections/Collections', () => ({
  default: () => <div>Collections</div>,
}));
vi.mock('./Contacts/Contacts', () => ({ default: () => <div>Contacts</div> }));
vi.mock('./Search/DiscoveryGraphAtlasPage', () => ({
  default: () => <div>Discovery Graph</div>,
}));
vi.mock('./Lidarr/Lidarr', () => ({ default: () => <div>Lidarr</div> }));
vi.mock('./LoginForm', () => ({ default: () => <div>Login Form</div> }));
vi.mock('./Messaging/Messaging', () => ({ default: () => <div>Messages</div> }));
vi.mock('./Pods/Pods', () => ({ default: () => <div>Pods</div> }));
vi.mock('./PlaylistIntake/PlaylistIntake', () => ({
  default: () => <div>Playlist Intake</div>,
}));
vi.mock('./Rooms/Rooms', () => ({ default: () => <div>Rooms</div> }));
vi.mock('./Search/Searches', () => ({ default: () => <div>Searches</div> }));
vi.mock('./Shared/ErrorSegment', () => ({
  default: ({ caption }) => <div>{caption}</div>,
}));
vi.mock('./Shared/Footer', () => ({ default: () => <div>Footer</div> }));
vi.mock('./ShareGroups/ShareGroups', () => ({
  default: () => <div>Share Groups</div>,
}));
vi.mock('./Shares/SharedWithMe', () => ({
  default: () => <div>Shared With Me</div>,
}));
vi.mock('./Solid/SolidSettings', () => ({
  default: () => <div>Solid</div>,
}));
vi.mock('./System/System', () => ({ default: () => <div>System</div> }));
vi.mock('./Transfers/TransferManager', () => ({
  default: () => <div>Transfers</div>,
}));
vi.mock('./Users/Users', () => ({ default: () => <div>Users</div> }));
vi.mock('./Wishlist/Wishlist', () => ({ default: () => <div>Wishlist</div> }));

let hubHandlers;

describe('App', () => {
  beforeEach(() => {
    hubHandlers = {};
    const hub = {
      on: vi.fn((event, handler) => {
        hubHandlers[event] = handler;
      }),
      onclose: vi.fn(),
      onreconnected: vi.fn(),
      onreconnecting: vi.fn(),
      start: vi.fn(() => new Promise(() => {})),
      stop: vi.fn(() => Promise.resolve()),
    };

    createApplicationHubConnection.mockReturnValue(hub);
    getSecurityEnabled.mockResolvedValue(true);
    check.mockResolvedValue(true);
    hasUnAcknowledgedMessages.mockResolvedValue(false);
    getRoomActivity.mockResolvedValue({});
    isLoggedIn.mockReturnValue(true);

    window.matchMedia = vi.fn().mockReturnValue({
      addEventListener: vi.fn(),
      matches: false,
      removeEventListener: vi.fn(),
    });
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    document.documentElement.className = '';
  });

  it('routes the home page to Dashboard without logging a route miss', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      expect(screen.getByTestId('nav-dashboard').closest('a')).toHaveAttribute('href', '/dashboard');
    });

    expect(consoleError).not.toHaveBeenCalledWith('[Router] Route miss for:', '/');
  });

  it('redirects unknown routes without exposing runtime debug diagnostics', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <MemoryRouter initialEntries={['/unknown-route']}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Dashboard')).toBeInTheDocument();
    expect(window).not.toHaveProperty('routeMissPath');
    expect(window).not.toHaveProperty('routeMissElement');
    expect(document.querySelector('[data-testid="route-miss"]')).toBeNull();
    expect(consoleError).not.toHaveBeenCalledWith(
      '[Router] Route miss for:',
      '/unknown-route',
    );
  });

  it('renders Collections without route-debug side effects', async () => {
    const consoleLog = vi.spyOn(console, 'log').mockImplementation(() => {});
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <MemoryRouter initialEntries={['/collections']}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Collections')).toBeInTheDocument();
    expect(window).not.toHaveProperty('routeMatchedCollections');
    expect(consoleLog).not.toHaveBeenCalledWith(
      '[Router] /collections route matched!',
      '/collections',
    );
    expect(consoleLog).not.toHaveBeenCalledWith(
      '[Router] Collections rendered successfully',
    );
    expect(consoleError).not.toHaveBeenCalledWith(
      '[Router] Error rendering Collections:',
      expect.anything(),
    );
  });

  it('makes the pending-action alert a labeled link across its full target', async () => {
    render(
      <MemoryRouter initialEntries={['/searches']}>
        <App />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Searches')).toBeInTheDocument();
    }, { timeout: 15_000 });

    act(() => {
      hubHandlers.state({ pendingRestart: true });
    });

    const action = await screen.findByTestId('nav-pending-action');
    expect(action.closest('a')).toHaveAttribute('href', '/system/info');
    expect(action).toHaveAttribute(
      'aria-label',
      'Open System Info to review pending actions.',
    );
    expect(action).toHaveAttribute(
      'title',
      'Open System Info to review pending actions.',
    );
  });

  it('explains an available version and opens its release details', async () => {
    render(
      <MemoryRouter initialEntries={['/searches']}>
        <App />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Searches')).toBeInTheDocument();
    }, { timeout: 15_000 });

    act(() => {
      hubHandlers.state({
        version: {
          current: '1.2.3',
          isUpdateAvailable: true,
          latest: '1.2.4',
        },
      });
    });

    const updateAction = await screen.findByTestId('nav-update-available');
    expect(updateAction).toHaveAttribute('aria-label', expect.stringContaining('1.2.4'));
    expect(updateAction).toHaveAttribute('title', expect.stringContaining('release notes'));
    fireEvent.click(updateAction);

    expect(await screen.findByText('1.2.3')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'See Release Notes' })).toHaveAttribute(
      'href',
      'https://github.com/snapetech/slskdn/releases',
    );
  });

  it('explains logout, lets the user cancel, and confirms ending the session', async () => {
    render(
      <MemoryRouter initialEntries={['/searches']}>
        <App />
      </MemoryRouter>,
    );

    const logoutAction = await screen.findByTestId('logout');
    expect(logoutAction).toHaveAttribute(
      'aria-label',
      'Log out of this web session.',
    );
    expect(logoutAction).toHaveAttribute(
      'title',
      'End this web session and return to the login screen.',
    );

    fireEvent.click(logoutAction);
    expect(await screen.findByText('Are you sure you want to log out?')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByText('Are you sure you want to log out?')).not.toBeInTheDocument();
    expect(logout).not.toHaveBeenCalled();

    fireEvent.click(logoutAction);
    fireEvent.click(await screen.findByRole('button', { name: 'Log Out' }));
    expect(logout).toHaveBeenCalledTimes(1);
  });

  it('does not keep the initial loader visible while the app hub startup stalls', async () => {
    const { container } = render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    expect(container.querySelector('.ui.active.loader')).toBeInTheDocument();

    await waitFor(() => {
      expect(container.querySelector('.ui.active.loader')).not.toBeInTheDocument();
    });

    expect(createApplicationHubConnection).toHaveBeenCalledTimes(1);
    expect(check).toHaveBeenCalled();
  });

  it('opens the theme menu and applies the selected theme', async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    const themeMenu = await screen.findByTestId('theme-menu');
    fireEvent.click(themeMenu);
    const lightTheme = await screen.findByTestId('theme-option-light');
    expect(lightTheme).toHaveAttribute(
      'aria-label',
      'Use the Light theme for the web UI.',
    );
    expect(lightTheme).toHaveAttribute(
      'title',
      'Use the Light theme for the web UI.',
    );
    fireEvent.click(lightTheme);

    await waitFor(() => {
      expect(localStorage.getItem('slskd-theme')).toBe('light');
      expect(document.documentElement).toHaveClass('light');
    });
  });

  it('explains palette choices and applies and resets dark-theme colors', async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    const themeMenu = await screen.findByTestId('theme-menu');
    fireEvent.click(themeMenu);

    const palette = await screen.findByRole('button', {
      name: 'Apply the Aurora palette to the dark theme.',
    });
    expect(palette).toHaveAttribute(
      'title',
      'Apply the Aurora palette to the dark theme.',
    );
    fireEvent.click(palette);

    await waitFor(() => {
      expect(localStorage.getItem('slskdn-palette')).toBe('aurora');
    });

    fireEvent.click(themeMenu);
    const resetPalette = await screen.findByTitle(
      'Restore the default colors for the dark theme.',
    );
    expect(resetPalette).toHaveAttribute(
      'aria-label',
      'Restore the default colors for the dark theme.',
    );
    fireEvent.click(resetPalette);

    await waitFor(() => {
      expect(localStorage.getItem('slskdn-palette')).toBe('null');
    });
  });

  it('opens grouped navigation menus and routes to their items', async () => {
    render(
      <MemoryRouter initialEntries={['/searches']}>
        <App />
      </MemoryRouter>,
    );

    const discoverMenu = await screen.findByTestId('nav-group-discover');
    expect(discoverMenu).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(discoverMenu);

    expect(discoverMenu).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(await screen.findByTestId('nav-wishlist'));

    expect(await screen.findByText('Wishlist')).toBeInTheDocument();
  });

  it('opens grouped navigation menus from the keyboard', async () => {
    render(
      <MemoryRouter initialEntries={['/searches']}>
        <App />
      </MemoryRouter>,
    );

    const discoverMenu = await screen.findByTestId('nav-group-discover');
    fireEvent.keyDown(discoverMenu, { key: 'Enter' });

    expect(await screen.findByTestId('nav-wishlist')).toBeInTheDocument();
    expect(discoverMenu).toHaveAttribute('aria-expanded', 'true');
  });

  it('keeps the browser tab title focused on slskdN branding', async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    }, { timeout: 15_000 });

    expect(document.title).toBe('slskdN');
  });

  it.each([
    ['/dashboard', 'Dashboard'],
    ['/collections', 'Collections'],
    ['/solid', 'Solid'],
    ['/discovery-graph', 'Discovery Graph'],
    ['/playlist-intake', 'Playlist Intake'],
    ['/searches', 'Searches'],
    ['/searches/123', 'Searches'],
    ['/wishlist', 'Wishlist'],
    ['/lidarr', 'Lidarr'],
    ['/browse', 'Browse'],
    ['/users', 'Users'],
    ['/contacts', 'Contacts'],
    ['/sharegroups', 'Share Groups'],
    ['/shared', 'Shared With Me'],
    ['/chat', 'Messages'],
    ['/pods', 'Messages'],
    ['/pods/pod-1', 'Messages'],
    ['/pods/pod-1/channels/channel-1', 'Messages'],
    ['/rooms', 'Messages'],
    ['/messages', 'Messages'],
    ['/uploads', 'Transfers'],
    ['/downloads', 'Transfers'],
    ['/system', 'System'],
    ['/system/info', 'System'],
  ])('renders the top-level route %s', async (path, expectedText) => {
    render(
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>,
    );

    expect((await screen.findAllByText(expectedText)).length).toBeGreaterThan(0);
  });

  it('shows chat activity in the header when conversations have unread messages', async () => {
    hasUnAcknowledgedMessages.mockResolvedValue(true);

    render(
      <MemoryRouter initialEntries={['/searches']}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByTestId('nav-chat-alert')).toBeInTheDocument();
    expect(hasUnAcknowledgedMessages).toHaveBeenCalledTimes(1);
  });

  it('shows room activity in the header when joined rooms have newer incoming messages', async () => {
    localStorage.setItem(
      'slskdn.rooms.lastSeenActivity',
      JSON.stringify({ chill: Date.parse('2026-04-30T00:00:00Z') }),
    );
    getRoomActivity.mockResolvedValue({
      chill: Date.parse('2026-04-30T00:01:00Z'),
    });

    render(
      <MemoryRouter initialEntries={['/searches']}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByTestId('nav-rooms-alert')).toBeInTheDocument();
  });

  it('does not overlap slow navigation activity polls', async () => {
    vi.useFakeTimers();
    let resolveActivity;
    getRoomActivity.mockReturnValue(
      new Promise((resolve) => {
        resolveActivity = resolve;
      }),
    );

    render(
      <MemoryRouter initialEntries={['/searches']}>
        <App />
      </MemoryRouter>,
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });

    expect(getRoomActivity).toHaveBeenCalledTimes(1);

    resolveActivity({});
    await act(async () => {
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(10_000);
    });

    expect(getRoomActivity).toHaveBeenCalledTimes(2);
  });

  it('ignores malformed stored room activity shapes before comparing timestamps', async () => {
    localStorage.setItem(
      'slskdn.rooms.lastSeenActivity',
      JSON.stringify(['bad']),
    );
    getRoomActivity.mockResolvedValue({
      chill: Date.parse('2026-04-30T00:01:00Z'),
    });

    render(
      <MemoryRouter initialEntries={['/searches']}>
        <App />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.queryByTestId('nav-rooms-alert')).not.toBeInTheDocument();
    });
    expect(JSON.parse(localStorage.getItem('slskdn.rooms.lastSeenActivity'))).toEqual({
      chill: Date.parse('2026-04-30T00:01:00Z'),
    });
  });

  it('ignores malformed room activity payloads', async () => {
    getRoomActivity.mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/searches']}>
        <App />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Searches')).toBeInTheDocument();
    }, { timeout: 15_000 });
    expect(screen.queryByTestId('nav-chat-alert')).not.toBeInTheDocument();
    expect(screen.queryByTestId('nav-rooms-alert')).not.toBeInTheDocument();
  });

  it('shows a dismissible network endpoint notice when ports are reported', async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    }, { timeout: 15_000 });

    hubHandlers.state({
      server: { isConnected: true },
      vpn: {
        isReady: true,
        portForwards: [
          {
            localPort: 50300,
            proto: 'tcp',
            publicIPAddress: '203.0.113.10',
            publicPort: 51000,
            slot: 0,
            targetPort: 51000,
          },
          {
            localPort: 50305,
            proto: 'tcp',
            publicIPAddress: '203.0.113.20',
            publicPort: 51001,
            slot: 1,
            targetPort: 50305,
          },
        ],
      },
    });

    const notice = await screen.findByTestId('vpn-port-change-notice');
    expect(notice).toBeInTheDocument();
    expect(notice).toHaveTextContent(
      /Ingress ports changed: older builds needed 5 public forwards/u,
    );
    expect(notice).toHaveTextContent(/Soulseek TCP 50300/u);
    expect(notice).toHaveTextContent(/mesh\/DHT\/QUIC TCP\/UDP 50305/u);
    expect(screen.queryByText('Used to need')).not.toBeInTheDocument();
    expect(screen.queryByText('Need now')).not.toBeInTheDocument();
    expect(screen.queryByText('TCP 50301')).not.toBeInTheDocument();
    expect(screen.queryByText('legacy mesh UDP overlay')).not.toBeInTheDocument();
    expect(screen.queryByText('UDP 50400')).not.toBeInTheDocument();
    expect(screen.queryByText(/active:/u)).not.toBeInTheDocument();
    expect(screen.queryByText('not reported')).not.toBeInTheDocument();
    expect(screen.queryByText(/203\.0\.113\./u)).not.toBeInTheDocument();

    fireEvent.click(screen.getByTitle('Dismiss port migration reminder permanently'));

    await waitFor(() => {
      expect(
        screen.queryByTestId('vpn-port-change-notice'),
      ).not.toBeInTheDocument();
    });
    expect(
      localStorage.getItem('slskdn.networkEndpoints.dismissedForever'),
    ).toBe('true');
  });

  it('keeps the network endpoint notice dismissed when forwarded ports change', async () => {
    localStorage.setItem('slskdn.networkEndpoints.dismissedForever', 'true');

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    }, { timeout: 15_000 });

    hubHandlers.state({
      server: { isConnected: true },
      vpn: {
        isReady: true,
        portForwards: [
          {
            localPort: 50300,
            proto: 'tcp',
            publicIPAddress: '203.0.113.10',
            publicPort: 52000,
            slot: 0,
            targetPort: 52000,
          },
          {
            localPort: 50305,
            proto: 'tcp',
            publicIPAddress: '203.0.113.20',
            publicPort: 52001,
            slot: 1,
            targetPort: 50305,
          },
        ],
      },
    });

    await waitFor(() => {
      expect(screen.queryByTestId('vpn-port-change-notice')).not.toBeInTheDocument();
    });
  });

  it('uses configured ingress ports in the network endpoint notice', async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    }, { timeout: 15_000 });

    hubHandlers.options({
      dht: {
        dhtPort: 62010,
        overlayPort: 62000,
      },
      soulseek: {
        listenPort: 61000,
      },
    });
    hubHandlers.state({
      server: { isConnected: true },
      vpn: {
        isReady: true,
        portForwards: [
          {
            localPort: 61000,
            proto: 'tcp',
            publicIPAddress: '203.0.113.10',
            publicPort: 61000,
            slot: 0,
            targetPort: 61000,
          },
          {
            localPort: 62000,
            proto: 'tcp',
            publicIPAddress: '203.0.113.20',
            publicPort: 62000,
            slot: 1,
            targetPort: 62000,
          },
          {
            localPort: 62010,
            proto: 'udp',
            publicIPAddress: '203.0.113.20',
            publicPort: 62010,
            slot: 2,
            targetPort: 62010,
          },
        ],
      },
    });

    const notice = await screen.findByTestId('vpn-port-change-notice');
    expect(notice).toBeInTheDocument();
    expect(notice).toHaveTextContent(/Soulseek TCP 61000/u);
    expect(notice).toHaveTextContent(/mesh\/QUIC TCP 62000/u);
    expect(notice).toHaveTextContent(/DHT UDP 62010/u);
    expect(screen.queryByText(/TCP\/UDP 50305/u)).not.toBeInTheDocument();
  });
});
