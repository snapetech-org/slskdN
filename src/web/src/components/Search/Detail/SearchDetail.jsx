import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import {
  createBatch,
  filterResponse,
  getBlockedUsers,
  getResponses,
  getUserDownloadStats,
  parseFiltersFromString,
} from '../../../lib/searches';
import {
  blockUserOnServer,
  syncBlockedUsers,
  unblockUserOnServer,
} from '../../../lib/userBlocks';
import {
  buildAlbumCandidates,
  getAlbumCandidateFilter,
} from '../../../lib/albumCandidatePicker';
import { saveAlbumDecisionRule } from '../../../lib/albumDecisionRules';
import { buildDiscoveryGraph } from '../../../lib/discoveryGraph';
import { rankSearchResponses } from '../../../lib/searchCandidateRanking';
import { deduplicateSearchResponses } from '../../../lib/searchResultDeduplication';
import {
  getSavedSearchFilters,
  removeSavedSearchFilter,
  saveSearchFilter,
} from '../../../lib/savedSearchFilters';
import { useExperiencePreference } from '../../../lib/experiencePreferences';
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';

import { formatRegionalNumber, useRegionalLocale } from '../../../lib/regionalFormat';
import {
  getLocalStorageItem,
  removeLocalStorageItem,
  setLocalStorageItem,
} from '../../../lib/storage';
import { getAllNotes } from '../../../lib/userNotes';
import { getGroups } from '../../../lib/users';
import { getDirectoryName, sleep } from '../../../lib/util';
import * as wishlistAPI from '../../../lib/wishlist';
import ErrorSegment from '../../Shared/ErrorSegment';
import DownloadDestinationSelector from '../../Shared/DownloadDestinationSelector';
import LoaderSegment from '../../Shared/LoaderSegment';
import Switch from '../../Shared/Switch';
import DiscoveryGraphModal from '../DiscoveryGraphModal';
import Response from '../Response';
import SearchDetailHeader from './SearchDetailHeader';
import SearchFilterModal from './SearchFilterModal';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import {
  Button,
  Checkbox,
  Confirm,
  Dropdown,
  Form,
  Header,
  Icon,
  Input,
  Label,
  List,
  Modal,
  Message,
  Popup,
  Segment,
} from 'semantic-ui-react';

const sortDropdownOptions = [
  {
    key: 'smart',
    get text() { return interfaceText("⭐ Smart Ranking (Best Overall)"); },
    value: 'smart',
  },
  {
    key: 'uploadSpeed',
    get text() { return interfaceText("Upload Speed (Fastest to Slowest)"); },
    value: 'uploadSpeed',
  },
  {
    key: 'queueLength',
    get text() { return interfaceText("Queue Depth (Least to Most)"); },
    value: 'queueLength',
  },
  {
    key: 'fileCount',
    get text() { return interfaceText("File Count (Most to Least)"); },
    value: 'fileCount',
  },
];

const asArray = (value) => (Array.isArray(value) ? value : []);

const includesUsername = (usernames, username) => {
  const normalized = (username || '').toLocaleLowerCase();
  return Boolean(normalized) && usernames.some(
    (blockedUsername) => blockedUsername.toLocaleLowerCase() === normalized,
  );
};

const scheduleAfterPaint = (callback) => {
  if (typeof window === 'undefined') {
    callback();
    return undefined;
  }

  if (typeof window.requestIdleCallback === 'function') {
    const idleHandle = window.requestIdleCallback(callback, { timeout: 1_500 });
    return () => window.cancelIdleCallback?.(idleHandle);
  }

  const timeout = window.setTimeout(callback, 250);
  return () => window.clearTimeout(timeout);
};

export const mapUserNotesByUsername = (payload) =>
  (Array.isArray(payload) ? payload : []).reduce((accumulator, note) => {
    if (note?.username) {
      accumulator[note.username] = note;
    }

    return accumulator;
  }, {});

export const getInitialResultFilters = ({
  getLocationSearch = () => window.location.search,
  getStoredDefault = () => getLocalStorageItem('slskd-default-search-filter', ''),
} = {}) => {
  const urlFilter = new URLSearchParams(getLocationSearch()).get('filter');
  return urlFilter ?? getStoredDefault();
};

export const shouldFetchSearchResponses = ({
  isComplete,
  responsesAvailable,
}) => isComplete || responsesAvailable;

export const batchUsernames = (usernames, batchSize = 100) => {
  const batches = [];

  for (let index = 0; index < usernames.length; index += batchSize) {
    batches.push(usernames.slice(index, index + batchSize));
  }

  return batches;
};

// eslint-disable-next-line complexity
const SearchDetail = ({
  creating,
  disabled,
  onCreate,
  onRemove,
  onStop,
  removing,
  search,
  stopping,
}) => {
  const regionalLocale = useRegionalLocale();
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const localized = useCallback((source, parameters) => (
    <span dir={directionFor(source)} lang={languageFor(source)}>
      {t(source, parameters)}
    </span>
  ), [directionFor, languageFor, t]);
  const localizedError = useCallback((error_, fallback) => (
    <span dir={directionFor(fallback)} lang={languageFor(fallback)}>
      {getApiErrorMessage(error_, { t }, fallback)}
    </span>
  ), [directionFor, languageFor, t]);
  const {
    fileCount,
    id,
    isComplete,
    lockedFileCount,
    responseCount,
    responsesAvailable,
    state,
  } = search;
  const acquisitionProfile = search.acquisitionProfile || 'lossless-exact';
  const showAlbumCandidates = useExperiencePreference(
    'searchAlbumCandidatesVisible',
    true,
  );
  const playerVisible = useExperiencePreference('playerVisible', true);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(undefined);
  const [downloadDestination, setDownloadDestination] = useState(undefined);

  const [results, setResults] = useState([]);

  // filters and sorting options
  const [hiddenResults, setHiddenResults] = useState([]);
  const [ignoredResults, setIgnoredResults] = useState([]);
  const [ignoreRequest, setIgnoreRequest] = useState(null);
  const [blockedUsers, setBlockedUsers] = useState(getBlockedUsers());
  const [hideBlockedUsers, setHideBlockedUsers] = useState(true);
  const [resultSort, setResultSort] = useState('smart');
  const [hideLocked, setHideLocked] = useState(true);
  const [hideNoFreeSlots, setHideNoFreeSlots] = useState(false);
  const [foldResults, setFoldResults] = useState(false);
  const [foldDuplicateResults, setFoldDuplicateResults] = useState(
    getLocalStorageItem('slskd-search-fold-duplicate-results', 'true') !==
      'false',
  );
  const [resultFilters, setResultFilters] = useState(getInitialResultFilters);
  const [savedFilters, setSavedFilters] = useState(getSavedSearchFilters());
  const [saveFilterOpen, setSaveFilterOpen] = useState(false);
  const [saveFilterName, setSaveFilterName] = useState('');
  const [saveFilterError, setSaveFilterError] = useState('');
  const [pageSize, setPageSize] = useState(
    Number.parseInt(getLocalStorageItem('slskd-search-page-size', '25'), 10),
  );
  const [displayCount, setDisplayCount] = useState(pageSize);
  const [userGroups, setUserGroups] = useState({});
  const [userGroupsLoading, setUserGroupsLoading] = useState(false);
  const [userStats, setUserStats] = useState({});
  const [userNotes, setUserNotes] = useState({});
  const [qualitySignalVersion, setQualitySignalVersion] = useState(0);
  const [graphData, setGraphData] = useState(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphOpen, setGraphOpen] = useState(false);
  const [graphRequest, setGraphRequest] = useState(null);

  const fetchUserNotes = useCallback(async ({ isCancelled } = {}) => {
    try {
      const response = await getAllNotes();
      if (!isCancelled?.()) {
        setUserNotes(mapUserNotesByUsername(response.data));
      }
    } catch (error_) {
      console.error('Failed to fetch user notes', error_);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const cancelScheduledFetch = scheduleAfterPaint(() =>
      fetchUserNotes({ isCancelled: () => cancelled }),
    );

    return () => {
      cancelled = true;
      cancelScheduledFetch?.();
    };
  }, [fetchUserNotes]);

  useEffect(() => {
    let cancelled = false;
    syncBlockedUsers()
      .then((updated) => {
        if (!cancelled) {
          setBlockedUsers(updated);
        }
      })
      .catch((error_) => {
        console.error('Failed to synchronize blocked users', error_);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const [hasSavedDefault, setHasSavedDefault] = useState(
    Boolean(getLocalStorageItem('slskd-default-search-filter')),
  );

  useEffect(() => {
    setResultFilters(getInitialResultFilters());
  }, [id]);

  useEffect(() => {
    let cancelled = false;

    const loadIgnoredResults = async () => {
      if (!search.wishlistItemId) {
        setIgnoredResults([]);
        return;
      }

      try {
        const rules = await wishlistAPI.getIgnoredResults(search.wishlistItemId);
        if (!cancelled) setIgnoredResults(rules);
      } catch (error_) {
        if (!cancelled) {
          console.error(error_);
          toast.error(localized('Could not load ignored Wishlist results.'));
        }
      }
    };

    loadIgnoredResults();
    return () => {
      cancelled = true;
    };
  }, [search.wishlistItemId, localized]);

  const isIgnoredWishlistFile = useCallback(
    (username, filename) => {
      const directory = getDirectoryName(filename).replaceAll('\\', '/').replace(/\/$/u, '');
      return ignoredResults.some(
        (rule) =>
          rule.username.toLowerCase() === username.toLowerCase() &&
          rule.directory.toLowerCase() === directory.toLowerCase(),
      );
    },
    [ignoredResults],
  );

  const handleIgnoreWishlistDirectory = async () => {
    const request = ignoreRequest;
    setIgnoreRequest(null);
    try {
      const rule = await wishlistAPI.ignoreResult(search.wishlistItemId, request);
      setIgnoredResults((current) => [
        rule,
        ...current.filter((candidate) => candidate.id !== rule.id),
      ]);
      toast.info(localized('Ignored folder {directory} from {username} for this Wishlist item.', {
        directory: request.directory,
        username: request.username,
      }));
    } catch (error_) {
      console.error(error_);
      toast.error(localizedError(error_, 'Could not ignore this Wishlist result.'));
    }
  };

  // Sync hasSavedDefault across tabs/searches when localStorage changes
  useEffect(() => {
    const handleStorageChange = (event) => {
      if (event.key === 'slskd-default-search-filter') {
        setHasSavedDefault(Boolean(event.newValue));
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  // Fetch user download stats for smart ranking
  useEffect(() => {
    let cancelled = false;

    const fetchStats = async () => {
      try {
        const stats = await getUserDownloadStats();
        if (!cancelled) {
          setUserStats(stats);
        }
      } catch {
        // Stats are optional, don't fail if unavailable
      }
    };

    const cancelScheduledFetch = scheduleAfterPaint(fetchStats);
    return () => {
      cancelled = true;
      cancelScheduledFetch?.();
    };
  }, []);

  // Handle blocking/unblocking users
  const handleBlockUser = useCallback(async (username) => {
    try {
      const updated = await blockUserOnServer(username);
      setBlockedUsers(updated);
      toast.info(localized('Blocked {username} from search results.', { username }));
    } catch (error_) {
      toast.error(localizedError(error_, 'Could not block this user.'));
    }
  }, [localized, localizedError]);

  const handleUnblockUser = useCallback(async (username) => {
    try {
      const updated = await unblockUserOnServer(username);
      setBlockedUsers(updated);
      toast.info(localized('Unblocked {username}.', { username }));
    } catch (error_) {
      toast.error(localizedError(error_, 'Could not unblock this user.'));
    }
  }, [localized, localizedError]);

  // Fetch durable results at completion or when early mesh responses are
  // explicitly available. Soulseek progress counts do not imply that the
  // response payload has been persisted yet.
  useEffect(() => {
    setLoading(false);
    setError(undefined);
    setResults([]);
  }, [id]);

  useEffect(() => {
    if (!shouldFetchSearchResponses({ isComplete, responsesAvailable })) {
      return undefined;
    }

    let cancelled = false;

    const get = async () => {
      try {
        setLoading(true);

        if (isComplete) {
          // the results may not be ready yet. this is very rare, but
          // if it happens the search will complete with no results.
          await sleep(500);
        }

        if (cancelled) return;

        const responses = await getResponses({ id });
        if (!cancelled) {
          setResults(responses);
          setLoading(false);
        }
      } catch (getError) {
        if (!cancelled) {
          setError(getError);
          setLoading(false);
        }
      }
    };

    const timeout = setTimeout(get, isComplete ? 0 : 250);
    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [id, isComplete, responsesAvailable]);

  // apply sorting and filters.  this can take a while for larger result
  // sets, so memoize it.
  const rankedAndFilteredResults = useMemo(() => {
    const sortOptions = {
      fileCount: { field: 'fileCount', order: 'desc' },
      queueLength: { field: 'queueLength', order: 'asc' },
      smart: { field: 'smartScore', order: 'desc' },
      uploadSpeed: { field: 'uploadSpeed', order: 'desc' },
    };

    const { field, order } = sortOptions[resultSort];

    const filters = parseFiltersFromString(resultFilters);

    return results
      .filter((r) => !hiddenResults.includes(r.username))
      .filter((r) => !(hideBlockedUsers && includesUsername(blockedUsers, r.username)))
      .map((response) => {
        if (!search.wishlistItemId || ignoredResults.length === 0) return response;
        const files = asArray(response.files).filter(
          (file) => !isIgnoredWishlistFile(response.username, file.filename),
        );
        const lockedFiles = asArray(response.lockedFiles).filter(
          (file) => !isIgnoredWishlistFile(response.username, file.filename),
        );
        return {
          ...response,
          fileCount: files.length,
          files,
          lockedFileCount: lockedFiles.length,
          lockedFiles,
        };
      })
      .map((r) => {
        if (hideLocked) {
          return { ...r, lockedFileCount: 0, lockedFiles: [] };
        }

        return r;
      })
      .map((response) => filterResponse({ filters, response }))
      .filter((r) => r.fileCount + r.lockedFileCount > 0)
      .filter((r) => !(hideNoFreeSlots && !r.hasFreeUploadSlot))
      .map((r) =>
        rankSearchResponses({
          acquisitionProfile,
          preferredConditions: filters,
          responses: [r],
          searchText: search.searchText,
          userStats,
        })[0],
      )
      .sort((a, b) => {
        const left = a[field] ?? 0;
        const right = b[field] ?? 0;

        if (order === 'asc') {
          return left - right;
        }

        return right - left;
      });
  }, [
    acquisitionProfile,
    blockedUsers,
    hiddenResults,
    ignoredResults,
    hideBlockedUsers,
    hideLocked,
    hideNoFreeSlots,
    resultFilters,
    resultSort,
    results,
    search.searchText,
    userStats,
    qualitySignalVersion,
    isIgnoredWishlistFile,
    search.wishlistItemId,
  ]);

  const deduplicatedResults = useMemo(
    () =>
      deduplicateSearchResponses({
        enabled: foldDuplicateResults,
        responses: rankedAndFilteredResults,
      }),
    [foldDuplicateResults, rankedAndFilteredResults],
  );

  const sortedAndFilteredResults = deduplicatedResults.responses;
  const visibleResults = useMemo(
    () => sortedAndFilteredResults.slice(0, displayCount),
    [displayCount, sortedAndFilteredResults],
  );
  const visibleUsernames = useMemo(
    () => [...new Set(visibleResults.map((response) => response.username).filter(Boolean))],
    [visibleResults],
  );

  useEffect(() => {
    let cancelled = false;

    if (visibleUsernames.length === 0) {
      setUserGroups({});
      setUserGroupsLoading(false);
      return undefined;
    }

    const loadGroups = async () => {
      setUserGroupsLoading(true);

      try {
        const groups = await Promise.all(
          batchUsernames(visibleUsernames).map((usernames) =>
            getGroups({ usernames }),
          ),
        );

        if (!cancelled) {
          setUserGroups(Object.assign({}, ...groups));
        }
      } catch {
        if (!cancelled) {
          setUserGroups({});
        }
      } finally {
        if (!cancelled) {
          setUserGroupsLoading(false);
        }
      }
    };

    loadGroups();
    return () => {
      cancelled = true;
    };
  }, [visibleUsernames]);

  const albumCandidates = useMemo(
    () => {
      if (!showAlbumCandidates) return [];

      return buildAlbumCandidates({
        responses: sortedAndFilteredResults,
        searchText: search.searchText,
      });
    },
    [search.searchText, showAlbumCandidates, sortedAndFilteredResults],
  );

  // when a user uses the action buttons, we will *probably* re-use this component,
  // but with a new search ID.  clear everything to prepare for the transition
  const reset = () => {
    setLoading(false);
    setError(undefined);
    setResults([]);
    setHiddenResults([]);
    setDisplayCount(pageSize);
  };

  const handlePageSizeChange = (newSize) => {
    setPageSize(newSize);
    setLocalStorageItem('slskd-search-page-size', newSize);
    // If we're showing less than the new page size, expand to fill it
    if (displayCount < newSize) {
      setDisplayCount(newSize);
    }
  };

  const handleFoldDuplicateResultsChange = () => {
    const nextValue = !foldDuplicateResults;
    setFoldDuplicateResults(nextValue);
    setLocalStorageItem(
      'slskd-search-fold-duplicate-results',
      String(nextValue),
    );
  };

  const create = async ({ navigate, search: searchForCreate }) => {
    reset();
    onCreate({ navigate, search: searchForCreate });
  };

  const openDiscoveryGraph = async (request) => {
    setGraphLoading(true);
    setGraphOpen(true);
    setGraphRequest(request);

    try {
      const graph = await buildDiscoveryGraph(request);
      setGraphData(graph);
    } catch (error_) {
      console.error(error_);
      toast.error(localizedError(error_, 'The discovery graph could not be loaded.'));
      setGraphOpen(false);
    } finally {
      setGraphLoading(false);
    }
  };

  const openSearchGraph = async () => {
    await openDiscoveryGraph({
      artist: search.searchText,
      scope: 'songid_run',
      title: search.searchText,
    });
  };

  const handleGraphRecenter = async (nodeId) => {
    if (!nodeId) {
      return;
    }

    const [nodeType, rawId] = nodeId.split(':');

    if (nodeType === 'artist') {
      await openDiscoveryGraph({ scope: 'artist', artistId: rawId });
      return;
    }

    if (nodeType === 'album' || nodeType === 'release-group') {
      await openDiscoveryGraph({ scope: 'album', releaseId: rawId });
      return;
    }

    if (nodeType === 'track') {
      await openDiscoveryGraph({ scope: 'track', recordingId: rawId });
      return;
    }

    await openSearchGraph();
  };

  const handleGraphCompare = async (nodeId, label) => {
    if (!graphRequest || !nodeId) {
      return;
    }

    await openDiscoveryGraph({
      ...graphRequest,
      compareLabel: label,
      compareNodeId: nodeId,
    });
  };

  const handleQueueNearby = async (graph) => {
    const queries = asArray(graph?.nodes)
      .filter((node) => node.nodeType === 'track')
      .map((node) => node.label || '')
      .filter(Boolean)
      .slice(0, 8);

    if (queries.length === 0) {
      toast.error(localized('No nearby track nodes were available to queue'));
      return;
    }

    try {
      const count = await createBatch({ queries });
      toast.success(localized('Nearby graph searches started: {count}.', {
        count: formatRegionalNumber(count, undefined, regionalLocale),
      }));
    } catch (error_) {
      console.error(error_);
      toast.error(localizedError(error_, 'Nearby graph searches could not be queued.'));
    }
  };

  const remove = async () => {
    reset();
    onRemove(search);
  };

  const saveAsDefault = () => {
    setLocalStorageItem('slskd-default-search-filter', resultFilters);
    setHasSavedDefault(true);
    toast.success(localized('Search filters saved as default.'));
  };

  const clearSavedDefault = () => {
    removeLocalStorageItem('slskd-default-search-filter');
    setHasSavedDefault(false);
    toast.info(localized('Saved default filter cleared.'));
  };

  const openSaveFilter = () => {
    setSaveFilterName(search.searchText || t('Search filter'));
    setSaveFilterError('');
    setSaveFilterOpen(true);
  };

  const saveNamedFilter = () => {
    const name = saveFilterName.trim();
    if (!name) {
      setSaveFilterError(interfaceText('Enter a name for this saved filter.'));
      return;
    }
    if (!resultFilters.trim()) {
      setSaveFilterError(interfaceText('Add at least one result condition before saving.'));
      return;
    }

    try {
      const next = saveSearchFilter({ name, value: resultFilters });
      setSavedFilters(next);
      setSaveFilterOpen(false);
      toast.success(localized('Search filter saved.'));
    } catch (error_) {
      console.error(error_);
      setSaveFilterError(interfaceText('Could not save this filter in browser storage.'));
    }
  };

  const loadNamedFilter = (name) => {
    const filter = savedFilters.find((item) => item.name === name);
    if (!filter) {
      return;
    }

    setResultFilters(filter.value);
  };

  const deleteNamedFilter = () => {
    const current = savedFilters.find((item) => item.value === resultFilters);
    if (!current) {
      return;
    }

    setSavedFilters(removeSavedSearchFilter(current.name));
    toast.info(localized('Saved search filter removed.'));
  };

  const focusAlbumCandidate = (candidate) => {
    const filter = getAlbumCandidateFilter(candidate);
    if (!filter) {
      return;
    }

    if (resultFilters.toLowerCase().includes(filter)) {
      return;
    }

    setResultFilters(`${resultFilters} ${filter}`.trim());
  };

  const saveAlbumCandidateRule = (candidate) => {
    const { rule } = saveAlbumDecisionRule({
      candidate,
      searchText: search.searchText,
    });

    toast.success(localized('Saved a local album rule for {album}.', { album: rule.albumTitle }));
  };

  const filteredCount = results?.length - sortedAndFilteredResults.length;
  const remainingCount = sortedAndFilteredResults.length - displayCount;
  const loaded = !removing && !creating && !loading && results;

  if (error) {
    return <ErrorSegment caption={t('Could not load search results. Try again later.')} />;
  }

  return (
    <>
      <SearchDetailHeader
        creating={creating}
        disabled={disabled}
        loaded={loaded}
        loading={loading}
        onCreate={create}
        onOpenGraph={openSearchGraph}
        onRemove={remove}
        onStop={onStop}
        removing={removing}
        search={search}
        stopping={stopping}
      />
      <Switch
        loading={loading && <LoaderSegment />}
        searching={
          !isComplete && (
            <LoaderSegment>
              {state === 'InProgress'
                ? lockedFileCount > 0
                  ? localized('Found {files} files (plus {locked} locked) from {users} users.', {
                    files: formatRegionalNumber(fileCount, undefined, regionalLocale),
                    locked: formatRegionalNumber(lockedFileCount, undefined, regionalLocale),
                    users: formatRegionalNumber(responseCount, undefined, regionalLocale),
                  })
                  : localized('Found {files} files from {users} users.', {
                    files: formatRegionalNumber(fileCount, undefined, regionalLocale),
                    users: formatRegionalNumber(responseCount, undefined, regionalLocale),
                  })
                : localized('Loading results...')}
            </LoaderSegment>
          )
        }
      >
        <DiscoveryGraphModal
          graph={graphData}
          loading={graphLoading}
          onClose={() => setGraphOpen(false)}
          onCompare={handleGraphCompare}
          onQueueNearby={handleQueueNearby}
          onRecenter={handleGraphRecenter}
          onRestoreBranch={(branch) => branch?.request && openDiscoveryGraph(branch.request)}
          open={graphOpen}
        />
        {loaded && (
          <Segment
            className="search-options"
            raised
          >
            <Popup
              content={localized('Choose how search results are ordered. Smart Ranking balances quality and availability.')}
              trigger={(
                <Dropdown
                  aria-label={t('Sort search results')}
                  lang={languageFor('Sort search results')}
                  dir={directionFor('Sort search results')}
                  button
                  className="search-options-sort icon"
                  floating
                  icon="sort"
                  labeled
                  onChange={(_event, { value }) => setResultSort(value)}
                  options={sortDropdownOptions.map((option) => ({ ...option, text: localized(option.text) }))}
                  text={
                    localized(sortDropdownOptions.find((o) => o.value === resultSort).text)
                  }
                />
              )}
            />
            <Popup
              content={localized('Choose how many matching results to render at once.')}
              trigger={(
                <Dropdown
                  aria-label={t('Results per page')}
                  lang={languageFor('Results per page')}
                  dir={directionFor('Results per page')}
                  button
                  className="search-options-pagesize"
                  floating
                  onChange={(_event, { value }) => handlePageSizeChange(value)}
                  options={[
                    { key: '10', text: localized('{count} per page', { count: formatRegionalNumber(10, undefined, regionalLocale) }), value: 10 },
                    { key: '25', text: localized('{count} per page', { count: formatRegionalNumber(25, undefined, regionalLocale) }), value: 25 },
                    { key: '50', text: localized('{count} per page', { count: formatRegionalNumber(50, undefined, regionalLocale) }), value: 50 },
                    { key: '100', text: localized('{count} per page', { count: formatRegionalNumber(100, undefined, regionalLocale) }), value: 100 },
                    { key: 'all', text: localized('Show All'), value: 999_999 },
                  ]}
                  style={{ marginLeft: '0.5em' }}
                  text={pageSize >= 999_999 ? localized('Show All') : localized('{count} per page', { count: formatRegionalNumber(pageSize, undefined, regionalLocale) })}
                />
              )}
            />
            <DownloadDestinationSelector onChange={setDownloadDestination} />
            <div className="search-option-toggles">
              <Checkbox
                checked={hideLocked}
                className="search-options-hide-locked"
                label={localized('Hide Locked Results')}
                onChange={() => setHideLocked(!hideLocked)}
                toggle
              />
              <Checkbox
                checked={hideNoFreeSlots}
                className="search-options-hide-no-slots"
                label={localized('Hide Results with No Free Slots')}
                onChange={() => setHideNoFreeSlots(!hideNoFreeSlots)}
                toggle
              />
              <Checkbox
                checked={hideBlockedUsers}
                className="search-options-hide-blocked"
                label={localized('Hide Blocked Users ({count})', { count: formatRegionalNumber(blockedUsers.length, undefined, regionalLocale) })}
                onChange={() => setHideBlockedUsers(!hideBlockedUsers)}
                toggle
              />
              <Checkbox
                checked={foldResults}
                className="search-options-fold-results"
                label={localized('Fold Results')}
                onChange={() => setFoldResults(!foldResults)}
                toggle
              />
              <Popup
              content={localized('Fold duplicate file candidates that appear from multiple providers or peers, keeping the highest-ranked visible result and showing the folded sources as metadata.')}
                position="top center"
                trigger={
                  <Checkbox
                    checked={foldDuplicateResults}
                    className="search-options-fold-duplicates"
                    label={deduplicatedResults.foldedCount > 0
                      ? localized('Fold Duplicates ({count})', { count: formatRegionalNumber(deduplicatedResults.foldedCount, undefined, regionalLocale) })
                      : localized('Fold Duplicates')}
                    onChange={handleFoldDuplicateResultsChange}
                    toggle
                  />
                }
              />
            </div>
            <div
              className="search-wishlist-ignore-guidance"
              role="note"
            >
              <Icon name={search.wishlistItemId ? 'ban' : 'info circle'} />
              {search.wishlistItemId
                ? localized('Wishlist search: use “Ignore for Wishlist” below a result folder to hide that peer and folder from future runs of this wishlist item.')
                : localized('Folder ignores are available only for wishlist searches because each rule belongs to one wishlist item. Open a result from Wishlist history to use them.')}
            </div>
            <Input
              action={
                <Button.Group>
                  {savedFilters.length > 0 && (
                    <Popup
                      content={localized('Load a saved browser-local filter into the current result list.')}
                      trigger={(
                        <Dropdown
                          aria-label={interfaceText("Load saved filter")}
                          lang={languageFor('Load saved filter')}
                          dir={directionFor('Load saved filter')}
                          button
                          className="icon"
                          floating
                          icon="bookmark"
                          onChange={(_event, { value }) => loadNamedFilter(value)}
                          options={savedFilters.map((filter) => ({
                            key: filter.name,
                            text: filter.name,
                            value: filter.name,
                          }))}
                          title={t('Load saved filter')}
                        />
                      )}
                    />
                  )}
                  {Boolean(resultFilters) && (
                    <Popup
                      content={localized('Remove the current filter text and show results without these conditions.')}
                      trigger={(
                        <Button
                          aria-label={interfaceText("Clear current filter")}
                          lang={languageFor('Clear current filter')}
                          dir={directionFor('Clear current filter')}
                          color="red"
                          icon="x"
                          onClick={() => setResultFilters('')}
                          title={t('Clear current filter')}
                        />
                      )}
                    />
                  )}
                  {Boolean(resultFilters) && (
                    <Popup
                      content={localized('Save the current result filter under a name for reuse later.')}
                      trigger={(
                        <Button
                          aria-label={interfaceText("Save named filter")}
                          lang={languageFor('Save named filter')}
                          dir={directionFor('Save named filter')}
                          color="teal"
                          icon="bookmark"
                          onClick={openSaveFilter}
                          title={t('Save named filter')}
                        />
                      )}
                    />
                  )}
                  {savedFilters.some((filter) => filter.value === resultFilters) && (
                    <Popup
                      content={localized('Remove the saved filter that exactly matches the current filter text.')}
                      trigger={(
                        <Button
                          aria-label={interfaceText("Delete matching saved filter")}
                          lang={languageFor('Delete matching saved filter')}
                          dir={directionFor('Delete matching saved filter')}
                          color="orange"
                          icon="minus circle"
                          onClick={deleteNamedFilter}
                          title={t('Delete matching saved filter')}
                        />
                      )}
                    />
                  )}
                  <Popup
                    content={localized('Use the current filter automatically for future search-result lists in this browser.')}
                    trigger={(
                      <Button
                        aria-label={interfaceText("Save as default filter")}
                        lang={languageFor('Save as default filter')}
                        dir={directionFor('Save as default filter')}
                        color="blue"
                        icon="save"
                        onClick={saveAsDefault}
                        title={t('Save as default filter')}
                      />
                    )}
                  />
                  {hasSavedDefault && (
                    <Popup
                      content={localized('Remove the saved default filter from this browser.')}
                      trigger={(
                        <Button
                          aria-label={interfaceText("Clear saved default filter")}
                          lang={languageFor('Clear saved default filter')}
                          dir={directionFor('Clear saved default filter')}
                          color="orange"
                          icon="trash"
                          onClick={clearSavedDefault}
                          title={t('Clear saved default filter')}
                        />
                      )}
                    />
                  )}
                  <SearchFilterModal
                    filterString={resultFilters}
                    onChange={setResultFilters}
                    trigger={
                      <Popup
                        content={localized('Build result-filter conditions without memorizing the filter syntax.')}
                        trigger={(
                          <Button
                            aria-label={interfaceText("Advanced Filters")}
                            lang={languageFor('Advanced Filters')}
                            dir={directionFor('Advanced Filters')}
                            icon
                            title={t('Advanced Filters')}
                          >
                            <Icon name="sliders horizontal" />
                          </Button>
                        )}
                      />
                    }
                  />
                </Button.Group>
              }
              className="search-filter"
              label={{ content: localized('Filter'), icon: 'filter' }}
              onChange={(_event, data) => setResultFilters(data.value)}
              placeholder={interfaceText("lackluster container -bothersome iscbr|isvbr islossless|islossy minbr:320 minfilesize:100mb maxfilesize:2gb minfilesinfolder:8 minlength:5000")}
              value={resultFilters}
             {...interfaceTextProps("lackluster container -bothersome iscbr|isvbr islossless|islossy minbr:320 minfilesize:100mb maxfilesize:2gb minfilesinfolder:8 minlength:5000")}/>
          </Segment>
        )}
        {loaded && albumCandidates.length > 0 && (
          <Segment
            className="search-album-picker-segment"
            raised
          >
            <Header as="h4" lang={languageFor('Album candidates')} dir={directionFor('Album candidates')}>
              {t('Album candidates')}
              <Label
                color="blue"
                size="mini"
              >
                {albumCandidates.length}
              </Label>
            </Header>
            <List
              className="search-album-candidate-list"
              divided
              relaxed
            >
              {albumCandidates.map((candidate) => (
                <List.Item
                  className="search-album-candidate"
                  key={candidate.key}
                >
                  <List.Content floated="right">
                    <Popup
              content={localized('Save this visible album review as a browser-local rule preview for similar future searches. This does not alter download behavior or contact peers.')}
                      position="top center"
                      trigger={
                        <Button
                          aria-label={t('Save album rule for {album}', { album: candidate.albumTitle })}
                          lang={languageFor('Save album rule for {album}')}
                          dir={directionFor('Save album rule for {album}')}
                          icon="bookmark outline"
                          onClick={() => saveAlbumCandidateRule(candidate)}
                          size="mini"
                        />
                      }
                    />
                    <Popup
                      content={localized('Focus the current result filter on this album folder name without starting another search or download.')}
                      position="top center"
                      trigger={
                        <Button
                          aria-label={t('Focus album candidate {album}', { album: candidate.albumTitle })}
                          lang={languageFor('Focus album candidate {album}')}
                          dir={directionFor('Focus album candidate {album}')}
                          icon="filter"
                          onClick={() => focusAlbumCandidate(candidate)}
                          size="mini"
                        />
                      }
                    />
                  </List.Content>
                  <List.Content>
                    <List.Header>
                      {candidate.albumTitle}
                      <Label
                        color="purple"
                        size="tiny"
                      >
                        {candidate.score}/100
                      </Label>
                    </List.Header>
                    <List.Description>
                        {t('{tracks} of {expected} visible tracks · {sources} sources · {percent}%', {
                          tracks: formatRegionalNumber(candidate.trackCount, undefined, regionalLocale),
                          expected: formatRegionalNumber(candidate.expectedTrackCount, undefined, regionalLocale),
                          sources: formatRegionalNumber(candidate.sourceCount, undefined, regionalLocale),
                          percent: formatRegionalNumber(Math.round(candidate.completenessRatio * 100), undefined, regionalLocale),
                        })}
                    </List.Description>
                    <div className="search-album-candidate-review">
                      <span>
                        {localized('Formats:')}{' '}
                        {candidate.formatMix
                          .map((item) => `${item.format} ${item.count}`)
                          .join(', ')}
                      </span>
                      {candidate.missingTrackNumbers.length > 0 && (
                        <span>
                          {localized('Missing:')}{' '}
                          {candidate.missingTrackNumbers.slice(0, 8).join(', ')}
                        </span>
                      )}
                      {candidate.durationVarianceSeconds > 0 && (
                        <span>
                          {t('Duration spread: {minutes} min', { minutes: formatRegionalNumber(Math.round(candidate.durationVarianceSeconds / 60), undefined, regionalLocale) })}
                        </span>
                      )}
                      {candidate.substitutionOptions.length > 0 && (
                        <span>
                          {localized('Substitutions:')}{' '}
                          {candidate.substitutionOptions
                            .map(
                              (option) =>
                                t('track {number} ({count} options)', {
                                  number: formatRegionalNumber(option.trackNumber, undefined, regionalLocale),
                                  count: formatRegionalNumber(option.optionCount, undefined, regionalLocale),
                                }),
                            )
                            .join(', ')}
                        </span>
                      )}
                    </div>
                    {candidate.substitutionOptions.length > 0 && (
                      <div className="search-album-candidate-substitutions">
                        {candidate.substitutionOptions.slice(0, 4).map((option) => (
                          <Popup
              content={localized('Manual review options from {sources} in {formats}. This only describes visible alternatives; it does not select or download them.', {
                sources: option.sources.join(', '),
                formats: option.formats.join(', '),
              })}
                            key={option.trackNumber}
                            position="top center"
                            trigger={
                              <Label
                                color="teal"
                                size="tiny"
                              >
                                <Icon name="exchange" />
                                <LocalizedText source={"Track"} />{" "}{option.trackNumber}: {option.optionCount}{' '}
                                <LocalizedText source={"options"} /></Label>
                            }
                          />
                        ))}
                      </div>
                    )}
                    <div className="search-album-candidate-labels">
                      {asArray(candidate.reasons).map((reason) => (
                        <Label
                          key={reason}
                          size="tiny"
                        >
                          {reason}
                        </Label>
                      ))}
                      {asArray(candidate.warnings).map((warning) => (
                        <Popup
                          content={localized('This is a local confidence warning from visible search result metadata only; it does not reject the candidate or contact peers.')}
                          key={warning}
                          position="top center"
                          trigger={
                            <Label
                              color="yellow"
                              size="tiny"
                            >
                              <Icon name="warning sign" />
                              {warning}
                            </Label>
                          }
                        />
                      ))}
                    </div>
                    <div className="search-album-candidate-paths">
                      {candidate.directories.join(' | ')}
                    </div>
                  </List.Content>
                </List.Item>
              ))}
            </List>
          </Segment>
        )}
        {loaded &&
          visibleResults.map((r, index) => (
            <Response
              disabled={disabled}
              destination={downloadDestination}
              downloadStats={r.downloadStats}
              isBlocked={includesUsername(blockedUsers, r.username)}
              isInitiallyFolded={foldResults}
              key={r.username}
              onBlock={() => handleBlockUser(r.username)}
              onHide={() => setHiddenResults([...hiddenResults, r.username])}
              onIgnoreDirectory={search.wishlistItemId
                ? (directory) => setIgnoreRequest({ directory, username: r.username })
                : undefined}
              onNoteUpdate={fetchUserNotes}
              onQualitySignalUpdate={() =>
                setQualitySignalVersion((version) => version + 1)
              }
              onUnblock={() => handleUnblockUser(r.username)}
              playerVisible={playerVisible}
              response={r}
              responseIndex={index}
              searchId={id}
              searchText={search.searchText}
              candidateRank={r.candidateRank}
              userGroup={userGroups[r.username]}
              userGroupLoading={userGroupsLoading}
              userNote={userNotes[r.username]}
            />
          ))}
        <Confirm
          cancelButton={localized('Keep Result')}
          confirmButton={localized('Ignore Folder')}
          content={ignoreRequest
            ? localized('Hide “{directory}” from {username} in every future run of this wishlist item? Other results from this user will remain visible.', {
              directory: ignoreRequest.directory,
              username: ignoreRequest.username,
            })
            : ''}
          header={localized('Ignore Wishlist Folder')}
          onCancel={() => setIgnoreRequest(null)}
          onConfirm={handleIgnoreWishlistDirectory}
          open={Boolean(ignoreRequest)}
          size="small"
        />
        {loaded &&
          (remainingCount > 0 ? (
            <Popup
              content={localized('Add the next batch of matching results to the current list.')}
              trigger={(
                <Button
                  className="showmore-button"
                  fluid
                  onClick={() => setDisplayCount(displayCount + pageSize)}
                  primary
                  size="large"
                >
                  {localized('Show {count} More Results', {
                    count: formatRegionalNumber(remainingCount > pageSize ? pageSize : remainingCount, undefined, regionalLocale),
                  })}{' '}
                  {localized('{remaining} remaining, {hidden} hidden by filters', {
                    remaining: formatRegionalNumber(remainingCount, undefined, regionalLocale),
                    hidden: formatRegionalNumber(filteredCount, undefined, regionalLocale),
                  })}
                </Button>
              )}
            >
            </Popup>
          ) : filteredCount > 0 ? (
            <div className="showmore-button" role="status">
              {localized('All results shown. {count} results hidden by filters', {
                count: formatRegionalNumber(filteredCount, undefined, regionalLocale),
              })}
            </div>
          ) : (
            ''
          ))}
      </Switch>
      <Modal
        closeIcon={false}
        data-testid="save-search-filter-dialog"
        onClose={() => setSaveFilterOpen(false)}
        open={saveFilterOpen}
        size="small"
      >
        <Modal.Header lang={languageFor('Save Search Filter')} dir={directionFor('Save Search Filter')}>{t('Save Search Filter')}</Modal.Header>
        <Modal.Content>
          <p lang={languageFor('Save the current result filter in this browser for later searches.')} dir={directionFor('Save the current result filter in this browser for later searches.')}>{t('Save the current result filter in this browser for later searches.')}</p>
          <Form>
            <Form.Field>
              <label htmlFor="saved-search-filter-name" lang={languageFor('Filter name')} dir={directionFor('Filter name')}>{t('Filter name')}</label>
              <input
                autoFocus
                id="saved-search-filter-name"
                onChange={(event) => setSaveFilterName(event.target.value)}
                placeholder={t('Filter name')}
                lang={languageFor('Filter name')}
                dir={directionFor('Filter name')}
                value={saveFilterName}
              />
            </Form.Field>
          </Form>
          {saveFilterError && (
            <Message negative role="alert">{saveFilterError}</Message>
          )}
        </Modal.Content>
        <Modal.Actions>
          <Popup
            content={localized('Close this dialog without saving the current result filter.')}
            trigger={(
              <Button onClick={() => setSaveFilterOpen(false)}>
                {localized('Cancel')}
              </Button>
            )}
          />
          <Popup
            content={localized('Save this filter under the name above in this browser.')}
            trigger={(
              <Button
                disabled={!saveFilterName.trim() || !resultFilters.trim()}
                onClick={saveNamedFilter}
                primary
              >
                {localized('Save Filter')}
              </Button>
            )}
          />
        </Modal.Actions>
      </Modal>
    </>
  );
};

export default SearchDetail;
