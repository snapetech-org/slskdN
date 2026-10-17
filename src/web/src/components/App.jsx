import LocalizedText from "./Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../lib/interfaceLocale";
import { THEME_PALETTES, applyPalette } from '../lib/themes';
import 'react-toastify/dist/ReactToastify.css';
import './App.css';
import * as chat from '../lib/chat';
import { createApplicationHubConnection } from '../lib/hubFactory';
import * as rooms from '../lib/rooms';
import * as session from '../lib/session';
import { getLocalStorageItem, setLocalStorageItem } from '../lib/storage';
import { isPassthroughEnabled } from '../lib/token';
import { useExperiencePreference } from '../lib/experiencePreferences';

import AppContext from './AppContext';
import AppRoutes from './AppRoutes';
import ApplicationActions from './ApplicationActions';
import ConnectionStatusMenuItem from './ConnectionStatusMenuItem';
import LoginForm from './LoginForm';
import NetworkEndpointNotice, {
  getStoredNetworkEndpointSnapshot,
  getVpnPortForwards,
  getVpnPortSignature,
  hasDismissedVpnPortNotice,
  storeDismissedVpnPortNotice,
} from './NetworkEndpointNotice';
import PlayerBar from './Player/PlayerBar';
import { PlayerProvider } from './Player/PlayerContext';
import PrimaryNavigation from './PrimaryNavigation';
import ErrorSegment from './Shared/ErrorSegment';
import Footer from './Shared/Footer';
import ThemeMenu from './ThemeMenu';
import React, { Component, Suspense } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import {
  Icon,
  Loader,
  Menu,
  Popup,
  Segment,
  Sidebar,
} from 'semantic-ui-react';

const ROOM_ACTIVITY_SEEN_STORAGE_KEY = 'slskdn.rooms.lastSeenActivity';
const NAV_ACTIVITY_POLL_INTERVAL_MS = 10_000;

const normalizeTheme = (theme) => {
  if (theme === 'light' || theme === 'classic-dark') {
    return theme;
  }

  return 'slskdn';
};

const getSemanticTheme = (theme) => (theme === 'light' ? 'light' : 'dark');

const getSavedPalette = () => {
  const saved = getLocalStorageItem('slskdn-palette');
  if (!saved) return null;
  return THEME_PALETTES.some((p) => p.id === saved) ? saved : null;
};

const normalizeRoomActivity = (value) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(value)
      .map(([roomName, timestamp]) => [roomName, Number(timestamp)])
      .filter(
        ([roomName, timestamp]) =>
          roomName.length > 0 && Number.isFinite(timestamp) && timestamp > 0,
      ),
  );
};

const getStoredRoomActivity = () => {
  try {
    return normalizeRoomActivity(
      JSON.parse(getLocalStorageItem(ROOM_ACTIVITY_SEEN_STORAGE_KEY, '{}')),
    );
  } catch {
    return {};
  }
};

const storeRoomActivity = (activity) => {
  setLocalStorageItem(ROOM_ACTIVITY_SEEN_STORAGE_KEY, JSON.stringify(activity));
};

const setNavigationHeightVariable = (element) => {
  if (!element || typeof document === 'undefined') return;

  const bottom = Math.ceil(element.getBoundingClientRect().bottom);
  if (bottom > 0) {
    document.documentElement.style.setProperty(
      '--slskdn-nav-height',
      `${bottom}px`,
    );
  }
};

const initialState = {
  applicationOptions: {},
  applicationState: {},
  error: false,
  initialized: false,
  login: {
    error: undefined,
    pending: false,
  },
  navActivity: {
    chat: false,
    rooms: false,
  },
  retriesExhausted: false,
  palette: getSavedPalette(),
  themeMenuOpen: false,
};

class App extends Component {
  constructor(props) {
    super(props);

    this.state = initialState;
    this.applicationHub = undefined;
    this.mounted = false;
    this.navigationActivityInFlight = false;
    this.navigationActivityInterval = undefined;
    this.navigationResizeObserver = undefined;
    this.roomActivityBaselined = false;
  }

  componentDidMount() {
    this.mounted = true;
    this.init();
    this.startNavigationActivityPolling();
    this.startChromeMeasurement();
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
  }

  componentDidUpdate(previousProps) {
    if (previousProps.location?.pathname !== this.props.location?.pathname) {
      this.refreshNavigationActivity();
    }
    this.updateNavigationHeight();
  }

  componentWillUnmount() {
    this.mounted = false;
    if (this.applicationHub) {
      this.applicationHub.stop().catch(() => {});
      this.applicationHub = undefined;
    }

    this.stopNavigationActivityPolling();
    document.removeEventListener(
      'visibilitychange',
      this.handleVisibilityChange,
    );

    if (this.navigationResizeObserver) {
      this.navigationResizeObserver.disconnect();
      this.navigationResizeObserver = undefined;
    }
  }

  startChromeMeasurement = () => {
    this.updateNavigationHeight();
    if (typeof window.ResizeObserver !== 'function') {
      return;
    }

    const navigation = document.querySelector('.navigation');
    if (!navigation) {
      return;
    }

    this.navigationResizeObserver = new window.ResizeObserver(
      this.updateNavigationHeight,
    );
    this.navigationResizeObserver.observe(navigation);
  };

  updateNavigationHeight = () => {
    setNavigationHeightVariable(document.querySelector('.navigation'));
  };

  startNavigationActivityPolling = () => {
    this.refreshNavigationActivity();
    if (!this.navigationActivityInterval) {
      this.navigationActivityInterval = window.setInterval(
        this.refreshNavigationActivity,
        NAV_ACTIVITY_POLL_INTERVAL_MS,
      );
    }
  };

  stopNavigationActivityPolling = () => {
    if (this.navigationActivityInterval) {
      window.clearInterval(this.navigationActivityInterval);
      this.navigationActivityInterval = undefined;
    }
  };

  handleVisibilityChange = () => {
    if (document.hidden) {
      this.stopNavigationActivityPolling();
    } else {
      this.startNavigationActivityPolling();
    }
  };

  getCurrentPath = () =>
    this.props.location?.pathname || window.location?.pathname || '';

  isAuthenticated = () => session.isLoggedIn() || isPassthroughEnabled();

  getChatActivity = async () => {
    if (
      this.getCurrentPath().startsWith('/chat') ||
      this.getCurrentPath().startsWith('/messages')
    ) {
      return false;
    }

    return chat.hasUnAcknowledgedMessages();
  };

  getRoomsActivity = async () => {
    const latestByRoom = normalizeRoomActivity(await rooms.getActivity());

    if (
      this.getCurrentPath().startsWith('/rooms') ||
      this.getCurrentPath().startsWith('/messages')
    ) {
      storeRoomActivity(latestByRoom);
      this.roomActivityBaselined = true;
      return false;
    }

    const seenActivity = getStoredRoomActivity();
    if (!this.roomActivityBaselined && Object.keys(seenActivity).length === 0) {
      storeRoomActivity(latestByRoom);
      this.roomActivityBaselined = true;
      return false;
    }

    this.roomActivityBaselined = true;
    return Object.entries(latestByRoom).some(
      ([roomName, latest]) => latest > (seenActivity[roomName] || 0),
    );
  };

  refreshNavigationActivity = async () => {
    if (document.hidden || this.navigationActivityInFlight) {
      return;
    }

    if (!this.isAuthenticated()) {
      if (this.mounted) {
        this.setState({
          navActivity: {
            chat: false,
            rooms: false,
          },
        });
      }
      return;
    }

    this.navigationActivityInFlight = true;
    try {
      const [chatActivity, roomsActivity] = await Promise.all([
        this.getChatActivity(),
        this.getRoomsActivity(),
      ]);

      if (this.mounted) {
        this.setState({
          navActivity: {
            chat: chatActivity,
            rooms: roomsActivity,
          },
        });
      }
    } catch (error) {
      console.error('Failed to refresh navigation activity:', error);
    } finally {
      this.navigationActivityInFlight = false;
    }
  };

  startApplicationHub = () => {
    if (this.applicationHub) {
      this.applicationHub.stop().catch(() => {});
    }

    const HUB_START_TIMEOUT_MS = 30000;
    const appHub = createApplicationHubConnection();
    this.applicationHub = appHub;

    appHub.on('state', (state) => {
      this.setState({ applicationState: state });
    });

    appHub.on('options', (options) => {
      this.setState({ applicationOptions: options });
    });

    appHub.onreconnecting(() =>
      this.setState({ error: true, retriesExhausted: false }),
    );
    appHub.onclose(() =>
      this.setState({ error: true, retriesExhausted: true }),
    );
    appHub.onreconnected(() =>
      this.setState({ error: false, retriesExhausted: false }),
    );

    const hubStart = appHub.start();
    let hubTimeoutId;
    const hubTimeout = new Promise((_, reject) => {
      hubTimeoutId = setTimeout(
        () => reject(new Error('HubConnectionTimeout')),
        HUB_START_TIMEOUT_MS,
      );
    });

    Promise.race([hubStart, hubTimeout])
      .catch((error) => {
        if (this.applicationHub !== appHub) {
          return;
        }

        if (error?.message === 'HubConnectionTimeout') {
          console.warn(
            'Hub connection timed out during background startup; allowing the UI to continue while SignalR retries.',
          );
          return;
        }

        console.error(error);
        this.setState({ error: true, retriesExhausted: false });
      })
      .finally(() => {
        if (hubTimeoutId) {
          clearTimeout(hubTimeoutId);
        }

        // Prevent unhandled rejections if the timeout wins and the start later faults.
        hubStart.catch(() => {});
      });
  };

  init = async () => {
    this.setState({ initialized: false }, async () => {
      const INIT_TOTAL_TIMEOUT_MS = 30000;

      let initTimedOut = false;
      let initTimeoutId;
      try {
        const initTask = (async () => {
          const securityEnabled = await session.getSecurityEnabled();

          if (!securityEnabled) {
            console.debug('application security is not enabled, per api call');
            session.enablePassthrough();
          }

          if (await session.check()) {
            this.startApplicationHub();
          }

          const savedTheme = this.getSavedTheme();
          if (savedTheme != null) {
            this.setState({ theme: savedTheme });
          }

          this.setState({
            error: false,
          });
        })();

        // Safety timeout so a stalled init doesn't keep the UI on the big loader forever.
        const initTimeout = new Promise((resolve) => {
          initTimeoutId = setTimeout(() => {
            initTimedOut = true;
            resolve();
          }, INIT_TOTAL_TIMEOUT_MS);
        });

        await Promise.race([initTask, initTimeout]);

        // Prevent unhandled rejections if the timeout wins.
        initTask.catch((error) => {
          if (initTimedOut) {
            console.warn('Init completed after timeout.', error);
          }
        });

        if (initTimedOut) {
          console.warn('Init timed out; showing UI (hub/state may reconnect later).');
        }
      } catch (error) {
        if (!initTimedOut) {
          console.error(error);
          this.setState({ error: true, retriesExhausted: true });
        }
      } finally {
        if (initTimeoutId) {
          clearTimeout(initTimeoutId);
        }
        this.setState({ initialized: true });
      }
    });
  };

  getSavedTheme = () => {
    const savedTheme = getLocalStorageItem('slskd-theme');
    return savedTheme == null ? null : normalizeTheme(savedTheme);
  };

  setTheme = (theme) => {
    const nextTheme = normalizeTheme(theme);
    const nextSemantic = getSemanticTheme(nextTheme);
    setLocalStorageItem('slskd-theme', nextTheme);
    this.setState({
      theme: nextTheme,
      themeMenuOpen: false,
    }, () => {
      if (nextSemantic !== 'light' && this.state.palette) {
        applyPalette('dark', this.state.palette);
      } else {
        applyPalette(nextSemantic, null);
      }
    });
  };

  setPalette = (paletteId) => {
    const nextPalette = paletteId || null;
    setLocalStorageItem('slskdn-palette', nextPalette);
    const semanticTheme = getSemanticTheme(this.state.theme);
    if (semanticTheme !== 'light') {
      applyPalette(semanticTheme, nextPalette);
    }
    this.setState({ palette: nextPalette, themeMenuOpen: false });
  };

  openThemeMenu = () => {
    this.setState({ themeMenuOpen: true });
  };

  closeThemeMenu = () => {
    this.setState({ themeMenuOpen: false });
  };

  dismissVpnPortNotice = (signature, portForwards) => {
    storeDismissedVpnPortNotice(signature, portForwards);
    this.forceUpdate();
  };

  handleLogin = (username, password, rememberMe) => {
    this.setState(
      (previousState) => ({
        login: { ...previousState.login, error: undefined, pending: true },
      }),
      async () => {
        try {
          await session.login({ password, rememberMe, username });
          this.setState(
            (previousState) => ({
              login: { ...previousState.login, error: false, pending: false },
            }),
            () => this.init(),
          );
        } catch (error) {
          this.setState((previousState) => ({
            login: { ...previousState.login, error, pending: false },
          }));
        }
      },
    );
  };

  logout = () => {
    session.logout();
    this.setState({ login: { ...initialState.login } });
  };

  // eslint-disable-next-line complexity
  render() {
    const {
      applicationOptions = {},
      applicationState = {},
      error,
      initialized,
      login,
      navActivity,
      retriesExhausted,
      theme = normalizeTheme(this.getSavedTheme() || 'slskdn'),
      palette,
      themeMenuOpen,
    } = this.state;
    const semanticTheme = getSemanticTheme(theme);
    const {
      connectionWatchdog = {},
      pendingReconnect,
      pendingRestart,
      relay = {},
      server,
      shares = {},
      user,
      version = {},
    } = applicationState;
    const { current, isUpdateAvailable, latest } = version;
    const { scanPending: pendingShareRescan } = shares;
    const vpnPortForwards = getVpnPortForwards(applicationState.vpn);
    const vpnPortSignature = getVpnPortSignature(vpnPortForwards);
    const showVpnPortNotice =
      vpnPortSignature &&
      applicationState.vpn?.isReady &&
      !hasDismissedVpnPortNotice(vpnPortSignature);
    const previousNetworkEndpointSnapshot = getStoredNetworkEndpointSnapshot();

    const { controller, mode } = relay;

    if (!initialized) {
      return (
        <Loader
          active
          size="big"
        />
      );
    }

    if (!session.isLoggedIn() && !isPassthroughEnabled()) {
      if (error) {
        return (
          <ErrorSegment
            caption={
              <>
                <span>{this.props.localized ? this.props.localized('Lost connection to slskdN') : <LocalizedText source={"Lost connection to slskdN"} />}</span>
                <br />
                <span>
                  {this.props.localized
                    ? this.props.localized(retriesExhausted ? 'Refresh to reconnect' : 'Retrying...')
                    : retriesExhausted ? 'Refresh to reconnect' : <LocalizedText source={"Retrying..."} />}
                </span>
              </>
            }
            icon="attention"
            suppressPrefix
          />
        );
      }

      return (
        <LoginForm
          error={login.error}
          initialized={login.initialized}
          loading={login.pending}
          onLoginAttempt={this.handleLogin}
        />
      );
    }

    const isAgent = mode === 'Agent';
    document.title = 'slskdN';

    document.documentElement.classList.remove(
      'classic-dark',
      'dark',
      'light',
      'slskdn',
    );
    document.documentElement.classList.add(theme);
    if (semanticTheme === 'dark') {
      document.documentElement.classList.add('dark');
    }

    // Apply palette override if one is saved and we're in a dark variant
    // (light mode uses Semantic UI defaults and all CSS var references are
    // scoped under :root.dark selectors; palette vars have no effect there)
    if (palette && semanticTheme !== 'light') {
      applyPalette('dark', palette);
    } else {
      applyPalette(semanticTheme, null);
    }

    return (
      <>
        {error && (
          <Segment
            color="red"
            inverted
            style={{
              borderRadius: 0,
              margin: 0,
              padding: '0.75rem 1rem',
            }}
          >
            <Icon name="attention" />
            <LocalizedText source={"Lost connection to slskdN."} />{" "}{retriesExhausted ? <LocalizedText source={"Refresh to reconnect."} /> : <LocalizedText source={"Retrying..."} />}
          </Segment>
        )}
        <PlayerProvider>
          <Sidebar.Pushable
            as={Segment}
            className="app"
          >
            <Sidebar
              animation="overlay"
              as={Menu}
              className="navigation"
              direction="top"
              horizontal="true"
              icon="labeled"
              inverted
              visible
              width="thin"
            >
              <PrimaryNavigation
                isAgent={isAgent}
                navActivity={navActivity}
                version={version}
              />
            <Menu
              className="right"
              inverted
            >
              <ConnectionStatusMenuItem
                connectionWatchdog={connectionWatchdog}
                controller={controller}
                mode={mode}
                pendingReconnect={pendingReconnect}
                server={server}
                user={user}
              />
              <ThemeMenu
                closeThemeMenu={this.closeThemeMenu}
                onSetPalette={this.setPalette}
                onSetTheme={this.setTheme}
                openThemeMenu={this.openThemeMenu}
                open={themeMenuOpen}
                palette={palette}
                semanticTheme={semanticTheme}
                theme={theme}
              />
              {(pendingReconnect || pendingRestart || pendingShareRescan) && (
                <Popup
                  content={interfaceText("Open System Info to review pending actions.")}
                  trigger={(
                    <NavLink to="/system/info">
                      <Menu.Item
                        aria-label={interfaceText("Open System Info to review pending actions.")}
                        data-testid="nav-pending-action"
                        position="right"
                        title={interfaceText("Open System Info to review pending actions.")}
                       {...interfaceTextProps("Open System Info to review pending actions.")}>
                        <Icon.Group className="menu-icon-group">
                          <Icon
                            color="yellow"
                            name="exclamation circle"
                          />
                        </Icon.Group>
                        <LocalizedText source={"Pending Action"} /></Menu.Item>
                    </NavLink>
                  )}
                 {...interfaceTextProps("Open System Info to review pending actions.")}/>
              )}
              <ApplicationActions
                current={current}
                isLoggedIn={session.isLoggedIn()}
                isUpdateAvailable={isUpdateAvailable}
                latest={latest}
                onLogout={this.logout}
              >
                <NavLink to="/system">
                  <Menu.Item data-testid="nav-system">
                    <Icon name="cogs" />
                    <LocalizedText source={"System"} /></Menu.Item>
                </NavLink>
              </ApplicationActions>
            </Menu>
            </Sidebar>
            <Sidebar.Pusher className="app-content">
              {showVpnPortNotice && (
                <NetworkEndpointNotice
                  onDismiss={() =>
                    this.dismissVpnPortNotice(vpnPortSignature, vpnPortForwards)
                  }
                  options={applicationOptions}
                  portForwards={vpnPortForwards}
                />
              )}
              <AppContext.Provider
                // Note: Context value object recreated on each render (class component limitation)
                // Deferred: Optimize with useMemo when converting to functional component
                // See memory-bank/triage-todo-fixme.md (defer section) for details
                // eslint-disable-next-line react/jsx-no-constructed-context-values
                value={{ options: applicationOptions, state: applicationState }}
              >
                <Suspense
                  fallback={
                    <Segment
                      basic
                      className="view"
                    >
                      <Loader active />
                    </Segment>
                  }
                >
                  <AppRoutes
                    applicationOptions={applicationOptions}
                    applicationState={applicationState}
                    isAgent={isAgent}
                    theme={semanticTheme}
                  />
                </Suspense>
              </AppContext.Provider>
            </Sidebar.Pusher>
          </Sidebar.Pushable>
          <PlayerBar />
        </PlayerProvider>
        <ToastContainer
          autoClose={5_000}
          closeOnClick
          draggable={false}
          hideProgressBar={false}
          newestOnTop
          pauseOnFocusLoss
          pauseOnHover
          position="bottom-center"
          rtl={false}
        />
        <Footer />
      </>
    );
  }
}

const AppWithLocation = (props) => {
  const location = useLocation();
  const regionalFormat = useExperiencePreference('regionalFormat', 'system');
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const localized = (source) => (
    <span dir={directionFor(source)} lang={languageFor(source)}>{t(source)}</span>
  );
  return (
    <App
      {...props}
      location={location}
      localized={localized}
      regionalFormat={regionalFormat}
    />
  );
};

export { App };
export default AppWithLocation;
