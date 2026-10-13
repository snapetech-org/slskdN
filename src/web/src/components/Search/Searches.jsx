import './Search.css';
import {
  acquisitionProfiles,
  getAcquisitionProfile,
  getStoredAcquisitionProfileId,
  setStoredAcquisitionProfileId,
} from '../../lib/acquisitionProfiles';
import { createSearchHubConnection } from '../../lib/hubFactory';
import { getCapabilities } from '../../lib/slskdn';
import { getLocalStorageItem, setLocalStorageItem } from '../../lib/storage';
import * as library from '../../lib/searches';
import ErrorSegment from '../Shared/ErrorSegment';
import PlaceholderSegment from '../Shared/PlaceholderSegment';
import SearchDetail from './Detail/SearchDetail';
import SearchList from './List/SearchList';
import React, {
  Suspense,
  lazy,
  useEffect,
  useRef,
  useState,
} from 'react';
import {
  Link,
  useLocation,
  useNavigate,
  useParams,
} from 'react-router-dom';
import { toast } from 'react-toastify';
import {
  Button,
  Checkbox,
  Dropdown,
  Header,
  Icon,
  Input,
  Message,
  Popup,
  Segment,
} from 'semantic-ui-react';
import { v4 as uuidv4 } from 'uuid';

const AlbumCompletionPanel = lazy(() => import('./AlbumCompletionPanel'));
const ArtistReleaseRadarPanel = lazy(() => import('./ArtistReleaseRadarPanel'));
const DiscographyCoveragePanel = lazy(() => import('./DiscographyCoveragePanel'));
const DiscoveryGraphAtlasPanel = lazy(() => import('./DiscoveryGraphAtlasPanel'));
const FederatedTasteRecommendationsPanel = lazy(() =>
  import('./FederatedTasteRecommendationsPanel'),
);
const MusicBrainzLookup = lazy(() => import('./MusicBrainzLookup'));
const SongIDPanel = lazy(() => import('./SongIDPanel'));
const SoulseekDiscoveryPanel = lazy(() => import('./SoulseekDiscoveryPanel'));

const SEARCH_API_PAGE_SIZE = 250;
const SEARCH_HUB_INITIAL_LIMIT = 500;

const getSearchContinuation = (records) => {
  const lastRecord = records.at(-1);
  const afterId = typeof lastRecord?.id === 'string' ? lastRecord.id : null;
  const afterStartedAt = typeof lastRecord?.startedAt === 'string'
    ? lastRecord.startedAt
    : null;

  return afterId && afterStartedAt ? { afterId, afterStartedAt } : null;
};

const isObject = (value) =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

const hasSearchId = (value) => isObject(value) && typeof value.id === 'string';

const DISCOVERY_TOOL_SECTION_KEYS = [
  'songid',
  'musicbrainz',
  'discographyCoverage',
  'artistReleaseRadar',
  'soulseekDiscovery',
  'federatedTaste',
  'discoveryGraphAtlas',
  'albumCompletion',
];

const toSearchMap = (searchesEvent) =>
  (Array.isArray(searchesEvent) ? searchesEvent : [])
    .filter(hasSearchId)
    .reduce((accumulator, search) => {
      accumulator[search.id] = search;
      return accumulator;
    }, {});

const CollapsibleSection = ({
  children,
  defaultOpen = true,
  storageKey,
  title,
}) => {
  const [open, setOpen] = useState(() => {
    if (!storageKey) {
      return defaultOpen;
    }

    const stored = getLocalStorageItem(storageKey);
    if (stored === null) {
      return defaultOpen;
    }

    return stored === 'open';
  });

  const toggleOpen = () => {
    setOpen((current) => {
      const next = !current;

      if (storageKey) {
        setLocalStorageItem(storageKey, next ? 'open' : 'closed');
      }

      return next;
    });
  };

  return (
    <Segment raised>
      <div
        style={{
          alignItems: 'center',
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: open ? '1em' : 0,
        }}
      >
        <Header
          as="h4"
          style={{ margin: 0 }}
        >
          {title}
        </Header>
        <Popup
          content={
            open
              ? `Collapse the ${title.toLowerCase()} panel to free up room on the page.`
              : `Expand the ${title.toLowerCase()} panel to inspect its contents.`
          }
          position="top center"
          trigger={
            <Button
              aria-label={`${open ? 'Collapse' : 'Expand'} ${title}`}
              icon
              onClick={toggleOpen}
              size="mini"
            >
              <Icon name={open ? 'angle up' : 'angle down'} />
            </Button>
          }
        />
      </div>
      {open ? (
        <Suspense
          fallback={
            <PlaceholderSegment
              caption={`Loading ${title}`}
              icon="circle notched"
            />
          }
        >
          {children}
        </Suspense>
      ) : null}
    </Segment>
  );
};

const Searches = ({ server } = {}) => {
  const normalizedServer = server ?? { isConnected: false };
  const isServerConnecting =
    normalizedServer.isConnecting || normalizedServer.IsLoggingIn;
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState(undefined);
  const [searches, setSearches] = useState({});
  const [initialSearchesLoaded, setInitialSearchesLoaded] = useState(false);
  const [searchPageState, setSearchPageState] = useState({});

  const [removing, setRemoving] = useState(false);
  const [removingAll, setRemovingAll] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [creating, setCreating] = useState(false);
  const [cleaningUp, setCleaningUp] = useState(false);
  const [bulkAction, setBulkAction] = useState(null);
  const [sourceFilter, setSourceFilter] = useState('all');

  // Scene ↔ Pod Bridging provider selection (opt-in; normal search stays Soulseek-compatible by default)
  const [scenePodBridgeEnabled, setScenePodBridgeEnabled] = useState(false);
  const [providerPod, setProviderPod] = useState(true);
  const [providerScene, setProviderScene] = useState(true); // Enabled by default when feature is on
  const [showProviderOptions, setShowProviderOptions] = useState(false);
  const [acquisitionProfileId, setAcquisitionProfileId] = useState(() =>
    getStoredAcquisitionProfileId(getLocalStorageItem),
  );

  const inputRef = useRef();
  const processedUrlSearchRef = useRef(new Set());
  const searchPageStateRef = useRef({});
  const loadSearchPageRef = useRef();

  const updateSearchPageState = (source, patch) => {
    const key = source || 'all';
    const next = {
      ...searchPageStateRef.current,
      [key]: {
        ...(searchPageStateRef.current[key] ?? {
          afterId: null,
          afterStartedAt: null,
          hasMore: false,
          initialized: false,
          loading: false,
          offset: 0,
        }),
        ...patch,
      },
    };
    searchPageStateRef.current = next;
    setSearchPageState(next);
  };

  loadSearchPageRef.current = async (source = 'all', reset = false) => {
    const key = source || 'all';
    const current = searchPageStateRef.current[key] ?? {
      afterId: null,
      afterStartedAt: null,
      hasMore: false,
      initialized: false,
      loading: false,
      offset: 0,
    };
    if (current.loading || (!reset && current.initialized && !current.hasMore)) {
      return;
    }

    const offset = reset ? 0 : current.offset;
    updateSearchPageState(key, {
      hasMore: reset ? true : current.hasMore,
      initialized: reset ? false : current.initialized,
      loading: true,
      afterId: reset ? null : current.afterId,
      afterStartedAt: reset ? null : current.afterStartedAt,
      offset,
    });

    try {
      const page = await library.getAll(
        SEARCH_API_PAGE_SIZE,
        key === 'all' ? null : key,
        0,
        reset ? null : current.afterStartedAt,
        reset ? null : current.afterId,
      );
      const records = Array.isArray(page) ? page : [];
      const continuation = getSearchContinuation(records);
      setSearches((currentSearches) => ({
        ...currentSearches,
        ...toSearchMap(records),
      }));
      updateSearchPageState(key, {
        afterId: continuation?.afterId ?? null,
        afterStartedAt: continuation?.afterStartedAt ?? null,
        hasMore: records.length === SEARCH_API_PAGE_SIZE && Boolean(continuation),
        initialized: true,
        loading: false,
        offset: offset + records.length,
      });
      return true;
    } catch (loadError) {
      updateSearchPageState(key, { loading: false });
      console.error('Failed to load another search page', loadError);
      if (key === 'all' && !current.initialized && Object.keys(searches).length === 0) {
        setError(
          loadError?.response?.data ?? loadError?.message ?? 'Could not load searches',
        );
      } else {
        toast.error('Could not load more searches');
      }
      return false;
    }
  };

  const location = useLocation();
  const routerNavigate = useNavigate();
  const { id: searchId } = useParams();
  const acquisitionProfile = getAcquisitionProfile(acquisitionProfileId);
  const searchProviders = scenePodBridgeEnabled
    ? [providerPod && 'pod', providerScene && 'scene'].filter(Boolean)
    : null;
  const acquisitionProfileOptions = acquisitionProfiles.map((profile) => ({
    content: (
      <div>
        <strong>{profile.label}</strong>
        <div className="search-acquisition-profile-option-summary">
          {profile.summary}
        </div>
      </div>
    ),
    icon: profile.icon,
    key: profile.id,
    text: profile.label,
    value: profile.id,
  }));

  const updateAcquisitionProfile = (event, { value }) => {
    setAcquisitionProfileId(
      setStoredAcquisitionProfileId(setLocalStorageItem, value).id,
    );
  };

  // Handle URL query parameters for predictable search URLs
  useEffect(() => {
    const urlParameters = new URLSearchParams(location.search);
    const queryParameter = urlParameters.get('q');

    if (
      queryParameter &&
      !creating &&
      !searchId &&
      !processedUrlSearchRef.current.has(location.search)
    ) {
      processedUrlSearchRef.current.add(location.search);
      // Automatically create a search from the URL query parameter
      create({
        navigate: false,
        search: queryParameter,
      }).then((id) => {
        if (id) {
          routerNavigate(`/searches/${encodeURIComponent(id)}`, { replace: true });
          return;
        }

        routerNavigate('/searches', { replace: true });
      });
    }
  }, [location.search, creating, searchId]); // eslint-disable-line react-hooks/exhaustive-deps

  const onConnecting = () => {
    setConnecting(true);
  };

  const onConnected = () => {
    setConnecting(false);
    setError(undefined);
  };

  const onConnectionError = (connectionError) => {
    setConnecting(false);
    setError(connectionError);
  };

  const onUpdate = (update) => {
    setSearches((current) =>
      typeof update === 'function' ? update(current) : update,
    );
    onConnected();
  };

  useEffect(() => {
    onConnecting();

    const searchHub = createSearchHubConnection();

    searchHub.on('list', (searchesEvent) => {
      const records = Array.isArray(searchesEvent) ? searchesEvent : [];
      const continuation = getSearchContinuation(records);
      onUpdate((current) => ({ ...current, ...toSearchMap(records) }));
      setInitialSearchesLoaded(true);
      onConnected();
      updateSearchPageState('all', {
        afterId: continuation?.afterId ?? null,
        afterStartedAt: continuation?.afterStartedAt ?? null,
        hasMore: records.length === SEARCH_HUB_INITIAL_LIMIT && Boolean(continuation),
        initialized: true,
        loading: false,
        offset: records.length,
      });
    });

    searchHub.on('update', (search) => {
      if (hasSearchId(search)) {
        onUpdate((old) => ({ ...old, [search.id]: search }));
      }
    });

    searchHub.on('delete', (search) => {
      if (hasSearchId(search)) {
        onUpdate((old) => {
          delete old[search.id];
          return { ...old };
        });
      }
    });

    searchHub.on('create', (search) => {
      if (hasSearchId(search)) {
        onUpdate((old) => ({ ...old, [search.id]: search }));
      }
    });

    searchHub.onreconnecting((connectionError) =>
      onConnectionError(connectionError?.message ?? 'Disconnected'),
    );
    searchHub.onreconnected(() => onConnected());
    searchHub.onclose((connectionError) =>
      onConnectionError(connectionError?.message ?? 'Disconnected'),
    );

    const loadInitialSearches = async () => {
      try {
        if (await loadSearchPageRef.current('all', true)) {
          onConnected();
        }
      } catch (loadError) {
        console.error(loadError);
        setError(loadError?.response?.data ?? loadError?.message ?? loadError);
      } finally {
        setInitialSearchesLoaded(true);
      }
    };

    const connect = async () => {
      try {
        onConnecting();
        await searchHub.start();
      } catch (connectionError) {
        toast.error(connectionError?.message ?? 'Failed to connect');
        onConnectionError(connectionError?.message ?? 'Failed to connect');
        await loadInitialSearches();
      }
    };

    connect();

    // Scene ↔ Pod Bridging is opt-in. Do not infer it from generic capabilities,
    // otherwise ordinary searches silently leave the proven Soulseek path.
    const checkFeatureFlag = async () => {
      try {
        const capabilities = await getCapabilities();
        const enabled =
          capabilities?.feature?.scenePodBridge === true ||
          capabilities?.features?.includes('scene_pod_bridge') === true;
        setScenePodBridgeEnabled(enabled);
      } catch (error_) {
        // Feature flag check failed - assume disabled
        console.debug(
          'Scene ↔ Pod Bridging feature flag check failed:',
          error_,
        );
      }
    };

    checkFeatureFlag();

    return () => {
      searchHub.stop();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    inputRef?.current?.focus();
  }, []);

  useEffect(() => {
    if (!searchId || !initialSearchesLoaded || searches[searchId]) {
      return;
    }

    let cancelled = false;

    const loadSearch = async () => {
      try {
        const search = await library.get({ id: searchId });
        if (!cancelled && hasSearchId(search)) {
          onUpdate((old) => ({ ...old, [search.id]: search }));
        }
      } catch {
        if (!cancelled) {
          routerNavigate('/searches', { replace: true });
        }
      }
    };

    loadSearch();

    return () => {
      cancelled = true;
    };
  }, [initialSearchesLoaded, routerNavigate, searchId, searches]);

  // create a new search, and optionally navigate to it to display the details
  // we do this if the user clicks the search icon, or repeats an existing search
  const create = async ({ navigate = false, search } = {}) => {
    const ref = inputRef?.current;
    const searchText = search || ref?.value;
    const id = uuidv4();

    if (!searchText) {
      toast.error('Please enter a search phrase');
      return;
    }

    try {
      setCreating(true);

      await library.create({
        acquisitionProfile: acquisitionProfile.id,
        id,
        providers: searchProviders,
        searchText,
      });

      if (ref) {
        ref.value = '';
        ref.focus();
      }

      setCreating(false);

      if (navigate) {
        routerNavigate(`/searches/${encodeURIComponent(id)}`);
      }

      return id;
    } catch (createError) {
      console.error(createError);
      toast.error(
        createError?.response?.data ?? createError?.message ?? createError,
      );
      setCreating(false);
    }
  };

  // delete a search
  const remove = async (search) => {
    try {
      setRemoving(true);

      await library.remove({ id: search.id });
      setSearches((old) => {
        delete old[search.id];
        return { ...old };
      });

      setRemoving(false);
    } catch (error_) {
      console.error(error_);
      toast.error(error?.response?.data ?? error?.message ?? error);
      setRemoving(false);
    }
  };

  // delete all searches
  const removeAll = async () => {
    try {
      setRemovingAll(true);
      const result = await library.removeAll();
      setSearches({});
      toast.success(`Cleared ${result?.data?.deleted ?? 'all'} searches`);
      setRemovingAll(false);
    } catch (removeAllError) {
      console.error(removeAllError);
      toast.error(
        removeAllError?.response?.data ??
          removeAllError?.message ??
          removeAllError,
      );
      setRemovingAll(false);
    }
  };

  // clean up old searches (retention-based)
  const cleanup = async () => {
    try {
      setCleaningUp(true);
      const result = await library.cleanupSearches();
      toast.success(`Cleaned up ${result?.data?.deleted ?? 'old'} searches`);
      setCleaningUp(false);
    } catch (cleanupError) {
      console.error(cleanupError);
      toast.error(
        cleanupError?.response?.data ??
          cleanupError?.message ??
          cleanupError,
      );
      setCleaningUp(false);
    }
  };

  // stop an in-progress search
  const stop = async (search) => {
    try {
      setStopping(true);
      await library.stop({ id: search.id });
      setStopping(false);
    } catch (stoppingError) {
      console.error(stoppingError);
      toast.error(
        stoppingError?.response?.data ??
          stoppingError?.message ??
          stoppingError,
      );
      setStopping(false);
    }
  };

  const removeSelected = async (selectedSearches) => {
    const processedIds = [];

    setBulkAction('remove');

    try {
      for (const search of selectedSearches) {
        await library.remove({ id: search.id });
        processedIds.push(search.id);
      }

      toast.success(`Deleted ${processedIds.length} selected searches`);
    } catch (error_) {
      console.error(error_);
      toast.error(
        error_?.response?.data ??
          error_?.message ??
          error_,
      );
    } finally {
      if (processedIds.length > 0) {
        setSearches((old) => {
          const next = { ...old };
          processedIds.forEach((id) => delete next[id]);
          return next;
        });
      }
      setBulkAction(null);
    }

    return processedIds;
  };

  const stopSelected = async (selectedSearches) => {
    const processedIds = [];

    setBulkAction('stop');

    try {
      for (const search of selectedSearches) {
        await library.stop({ id: search.id });
        processedIds.push(search.id);
      }

      toast.success(`Stopped ${processedIds.length} selected searches`);
    } catch (error_) {
      console.error(error_);
      toast.error(
        error_?.response?.data ??
          error_?.message ??
          error_,
      );
    } finally {
      setBulkAction(null);
    }

    return processedIds;
  };

  const researchSelected = async (selectedSearches) => {
    const searchable = selectedSearches.filter(
      (search) => typeof search.searchText === 'string' && search.searchText.trim(),
    );

    if (searchable.length === 0) {
      toast.error('The selected searches do not contain searchable text');
      return [];
    }

    setBulkAction('research');

    try {
      const count = await library.createBatch({
        acquisitionProfile: acquisitionProfile.id,
        providers: searchProviders,
        queries: searchable.map((search) => search.searchText),
      });
      toast.success(`Started ${count} selected searches again`);
      return searchable.map((search) => search.id);
    } catch (error_) {
      console.error(error_);
      toast.error(
        error_?.response?.data ??
          error_?.message ??
          error_,
      );
      return [];
    } finally {
      setBulkAction(null);
    }
  };

  // if searchId is not null, there's an id in the route.
  // display the details for the search, if there is one
  if (searchId) {
    if (searches[searchId]) {
      return (
        <SearchDetail
          creating={creating}
          disabled={!normalizedServer.isConnected}
          onCreate={create}
          onRemove={remove}
          onStop={stop}
          removing={removing}
          search={searches[searchId]}
          stopping={stopping}
        />
      );
    }

    if (!initialSearchesLoaded) {
      return (
        <PlaceholderSegment
          caption="Loading search details"
          icon="search"
        />
      );
    }
  }

  const hasPreviouslyExpandedDiscoveryTool =
    DISCOVERY_TOOL_SECTION_KEYS.some(
      (key) =>
        getLocalStorageItem(`slskdn.search.section.${key}`) === 'open',
    );

  return (
    <>
      <CollapsibleSection
        storageKey="slskdn.search.section.search"
        title="Search"
      >
        <Segment className="search-segment">
          <div className="search-segment-icon">
            <Icon
              name="search"
              size="big"
            />
          </div>
          <Input
            action={
              <>
                <Popup
                  content="Queue this search without leaving the search page."
                  position="top center"
                  trigger={
                    <Button
                      aria-label="Queue search"
                      disabled={creating || !normalizedServer.isConnected}
                      icon="plus"
                      onClick={create}
                    />
                  }
                />
                <Popup
                  content="Start this search and open its detailed results immediately."
                  position="top center"
                  trigger={
                    <Button
                      aria-label="Search and open results"
                      disabled={creating || !normalizedServer.isConnected}
                      icon="search"
                      onClick={() => create({ navigate: true })}
                    />
                  }
                />
              </>
            }
            className="search-input"
            disabled={creating || !normalizedServer.isConnected}
            input={
              <input
                data-lpignore="true"
                data-testid="search-input"
                placeholder={
                  normalizedServer.isConnected
                    ? 'Search phrase'
                    : isServerConnecting
                      ? 'Connecting to Soulseek…'
                      : 'Connect to Soulseek to search'
                }
                type="search"
              />
            }
            loading={creating}
            onKeyUp={(keyUpEvent) =>
              keyUpEvent.key === 'Enter' ? create({ navigate: true }) : undefined
            }
            placeholder="Search phrase"
            ref={inputRef}
            size="big"
          />
          {!normalizedServer.isConnected && (
            <Message
              className="search-connection-notice"
              info
              size="small"
            >
              <Message.Header>
                {isServerConnecting
                  ? 'Connecting to Soulseek'
                  : 'Soulseek connection needed'}
              </Message.Header>
              <p>
                {isServerConnecting
                  ? 'Search and peer browsing will be available when the connection completes.'
                  : 'Connect to search files, browse peer shares, and send Soulseek messages. Check your credentials in connection settings, then use Disconnected in the top bar to reconnect.'}
              </p>
              {!isServerConnecting && (
                <Popup
                  content="Open System → Options to review your Soulseek credentials, then use Disconnected in the top bar to reconnect."
                  position="top center"
                  trigger={
                    <Link
                      className="ui basic small button"
                      to="/system/options"
                    >
                      Open connection settings
                    </Link>
                  }
                />
              )}
            </Message>
          )}
          {scenePodBridgeEnabled && (
            <div
              style={{
                background: 'rgba(0,0,0,0.05)',
                borderRadius: '4px',
                marginTop: '0.75em',
                padding: '0.75em',
              }}
            >
              <div
                style={{
                  alignItems: 'center',
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '1em',
                }}
              >
                <span style={{ fontSize: '0.95em', fontWeight: 'bold' }}>
                  Search Sources:
                </span>
                <Checkbox
                  checked={providerPod}
                  label={
                    <label>
                      <Icon
                        name="sitemap"
                        style={{ marginRight: '0.25em' }}
                      />
                      Pod/Mesh
                    </label>
                  }
                  onChange={(e, { checked }) => setProviderPod(checked)}
                  toggle
                />
                <Checkbox
                  checked={providerScene}
                  label={
                    <label>
                      <Icon
                        name="globe"
                        style={{ marginRight: '0.25em' }}
                      />
                      Soulseek Scene
                    </label>
                  }
                  onChange={(e, { checked }) => setProviderScene(checked)}
                  toggle
                />
                {!providerPod && !providerScene && (
                  <span
                    style={{
                      color: 'orange',
                      fontSize: '0.9em',
                      fontStyle: 'italic',
                    }}
                  >
                    <Icon name="warning" /> At least one source must be selected
                  </span>
                )}
              </div>
            </div>
          )}
          <div className="search-acquisition-profile-strip">
            <div className="search-acquisition-profile-label">
              <Icon name={acquisitionProfile.icon} />
              Acquisition Profile
            </div>
            <Popup
              content={`${acquisitionProfile.label}: ${acquisitionProfile.description}`}
              position="top center"
              trigger={
                <Dropdown
                  aria-label="Acquisition profile"
                  className="search-acquisition-profile-dropdown"
                  data-testid="acquisition-profile-select"
                  onChange={updateAcquisitionProfile}
                  options={acquisitionProfileOptions}
                  selection
                  value={acquisitionProfile.id}
                />
              }
            />
            <span className="search-acquisition-profile-summary">
              {acquisitionProfile.summary}
            </span>
          </div>
        </Segment>
      </CollapsibleSection>
      <CollapsibleSection
        defaultOpen={hasPreviouslyExpandedDiscoveryTool}
        storageKey="slskdn.search.section.discoveryTools"
        title="Music discovery tools"
      >
        <CollapsibleSection
          defaultOpen={false}
          storageKey="slskdn.search.section.songid"
          title="SongID"
        >
          <SongIDPanel disabled={!normalizedServer.isConnected} />
        </CollapsibleSection>
        <CollapsibleSection
          defaultOpen={false}
          storageKey="slskdn.search.section.musicbrainz"
          title="MusicBrainz Lookup"
        >
          <MusicBrainzLookup disabled={!normalizedServer.isConnected} />
        </CollapsibleSection>
        <CollapsibleSection
          defaultOpen={false}
          storageKey="slskdn.search.section.discographyCoverage"
          title="Discography Concierge"
        >
          <DiscographyCoveragePanel disabled={!normalizedServer.isConnected} />
        </CollapsibleSection>
        <CollapsibleSection
          defaultOpen={false}
          storageKey="slskdn.search.section.artistReleaseRadar"
          title="Artist Release Radar"
        >
          <ArtistReleaseRadarPanel disabled={!normalizedServer.isConnected} />
        </CollapsibleSection>
        <CollapsibleSection
          defaultOpen={false}
          storageKey="slskdn.search.section.soulseekDiscovery"
          title="Soulseek Discovery"
        >
          <SoulseekDiscoveryPanel
            disabled={!normalizedServer.isConnected}
            onSearch={(search) => create({ navigate: true, search })}
          />
        </CollapsibleSection>
        <CollapsibleSection
          defaultOpen={false}
          storageKey="slskdn.search.section.federatedTaste"
          title="Federated Taste"
        >
          <FederatedTasteRecommendationsPanel disabled={!normalizedServer.isConnected} />
        </CollapsibleSection>
        <CollapsibleSection
          defaultOpen={false}
          storageKey="slskdn.search.section.discoveryGraphAtlas"
          title="Discovery Graph Atlas"
        >
          <DiscoveryGraphAtlasPanel disabled={!normalizedServer.isConnected} />
        </CollapsibleSection>
        <CollapsibleSection
          defaultOpen={false}
          storageKey="slskdn.search.section.albumCompletion"
          title="Album Completion"
        >
          <AlbumCompletionPanel disabled={!normalizedServer.isConnected} />
        </CollapsibleSection>
      </CollapsibleSection>
      <CollapsibleSection
        defaultOpen
        storageKey="slskdn.search.section.searchResults"
        title="Search Results"
      >
        {error ? (
          <ErrorSegment caption={error?.message ?? error} />
        ) : Object.keys(searches).length === 0 ? (
          <PlaceholderSegment
            caption={
              connecting || !initialSearchesLoaded
                ? 'Loading searches'
                : 'No searches to display'
            }
            icon="search"
          />
        ) : (
          <>
            <div style={{ marginBottom: '1em', display: 'flex', gap: '1em', alignItems: 'center' }}>
              <span style={{ fontSize: '0.9em', fontWeight: 'bold' }}>
                Filter by source:
              </span>
              <Popup
                content="Show only searches from a specific source. Auto-replace searches are automatic stuck-download replacements."
                position="top center"
                trigger={
                  <Dropdown
                    aria-label="Search source filter"
                    compact
                    onChange={(_, { value }) => {
                      setSourceFilter(value);
                      if (!searchPageStateRef.current[value]?.initialized) {
                        const initialPage = searchPageStateRef.current.all;
                        if (initialPage?.initialized) {
                          updateSearchPageState(value, {
                            afterId: initialPage.afterId,
                            afterStartedAt: initialPage.afterStartedAt,
                            hasMore: initialPage.hasMore,
                            initialized: true,
                            loading: false,
                            offset: initialPage.offset,
                          });
                          if (initialPage.hasMore) {
                            loadSearchPageRef.current(value);
                          }
                        } else {
                          loadSearchPageRef.current(value, true);
                        }
                      }
                    }}
                    options={[
                      { key: 'all', text: 'All Sources', value: 'all' },
                      { key: 'manual', text: 'Manual', value: 'manual', icon: 'search' },
                      { key: 'wishlist', text: 'Wishlist', value: 'wishlist', icon: 'bookmark' },
                      { key: 'auto-replace', text: 'Auto-Replace', value: 'auto-replace', icon: 'sync' },
                    ]}
                    selection
                    value={sourceFilter}
                  />
                }
              />
            </div>
            <SearchList
              bulkAction={bulkAction}
              cleaningUp={cleaningUp}
              connecting={connecting}
              error={error}
              hasMoreFromServer={Boolean(
                searchPageState[sourceFilter]?.hasMore ||
                  !searchPageState[sourceFilter]?.initialized,
              )}
              loadingMore={searchPageState[sourceFilter]?.loading ?? false}
              onLoadMore={() => loadSearchPageRef.current(sourceFilter)}
              onCleanup={cleanup}
              onRemove={remove}
              onRemoveAll={removeAll}
              onRemoveSelected={removeSelected}
              onResearchSelected={researchSelected}
              onStop={stop}
              onStopSelected={stopSelected}
              removingAll={removingAll}
              searches={searches}
              sourceFilter={sourceFilter}
            />
          </>
        )}
      </CollapsibleSection>
    </>
  );
};

export default Searches;
