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
    text: '⭐ Smart Ranking (Best Overall)',
    value: 'smart',
  },
  {
    key: 'uploadSpeed',
    text: 'Upload Speed (Fastest to Slowest)',
    value: 'uploadSpeed',
  },
  {
    key: 'queueLength',
    text: 'Queue Depth (Least to Most)',
    value: 'queueLength',
  },
  {
    key: 'fileCount',
    text: 'File Count (Most to Least)',
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
          toast.error('Failed to load ignored wishlist results');
        }
      }
    };

    loadIgnoredResults();
    return () => {
      cancelled = true;
    };
  }, [search.wishlistItemId]);

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
      toast.info(`Ignored ${request.directory} from ${request.username} for this wishlist item`);
    } catch (error_) {
      console.error(error_);
      toast.error(error_?.response?.data ?? error_?.message ?? error_);
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
      toast.info(`Blocked ${username} from search results`);
    } catch (error_) {
      toast.error(`Failed to block ${username}: ${error_.message}`);
    }
  }, []);

  const handleUnblockUser = useCallback(async (username) => {
    try {
      const updated = await unblockUserOnServer(username);
      setBlockedUsers(updated);
      toast.info(`Unblocked ${username}`);
    } catch (error_) {
      toast.error(`Failed to unblock ${username}: ${error_.message}`);
    }
  }, []);

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
      toast.error(
        error_?.response?.data ??
          error_?.message ??
          'Failed to build discovery graph',
      );
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
      toast.error('No nearby track nodes were available to queue');
      return;
    }

    try {
      const count = await createBatch({ queries });
      toast.success(`Started ${count} nearby graph searches`);
    } catch (error_) {
      console.error(error_);
      toast.error(
        error_?.response?.data ??
          error_?.message ??
          'Failed to queue nearby graph searches',
      );
    }
  };

  const remove = async () => {
    reset();
    onRemove(search);
  };

  const saveAsDefault = () => {
    setLocalStorageItem('slskd-default-search-filter', resultFilters);
    setHasSavedDefault(true);
    toast.success('Search filters saved as default');
  };

  const clearSavedDefault = () => {
    removeLocalStorageItem('slskd-default-search-filter');
    setHasSavedDefault(false);
    toast.info('Saved default filter cleared');
  };

  const openSaveFilter = () => {
    setSaveFilterName(search.searchText || 'Search filter');
    setSaveFilterError('');
    setSaveFilterOpen(true);
  };

  const saveNamedFilter = () => {
    const name = saveFilterName.trim();
    if (!name) {
      setSaveFilterError('Enter a name for this saved filter.');
      return;
    }
    if (!resultFilters.trim()) {
      setSaveFilterError('Add at least one result condition before saving.');
      return;
    }

    try {
      const next = saveSearchFilter({ name, value: resultFilters });
      setSavedFilters(next);
      setSaveFilterOpen(false);
      toast.success('Search filter saved');
    } catch (error_) {
      setSaveFilterError(
        error_?.message || 'Could not save this filter in browser storage.',
      );
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
    toast.info('Saved search filter removed');
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

    toast.success(`Saved local album rule for ${rule.albumTitle}`);
  };

  const filteredCount = results?.length - sortedAndFilteredResults.length;
  const remainingCount = sortedAndFilteredResults.length - displayCount;
  const loaded = !removing && !creating && !loading && results;

  if (error) {
    return <ErrorSegment caption={error?.message ?? error} />;
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
                ? `Found ${fileCount} files ${
                    lockedFileCount > 0
                      ? `(plus ${lockedFileCount} locked) `
                      : ''
                  }from ${responseCount} users`
                : 'Loading results...'}
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
              content="Choose how search results are ordered. Smart Ranking balances quality and availability."
              trigger={(
                <Dropdown
                  aria-label="Sort search results"
                  button
                  className="search-options-sort icon"
                  floating
                  icon="sort"
                  labeled
                  onChange={(_event, { value }) => setResultSort(value)}
                  options={sortDropdownOptions}
                  text={
                    sortDropdownOptions.find((o) => o.value === resultSort).text
                  }
                />
              )}
            />
            <Popup
              content="Choose how many matching results to render at once."
              trigger={(
                <Dropdown
                  aria-label="Results per page"
                  button
                  className="search-options-pagesize"
                  floating
                  onChange={(_event, { value }) => handlePageSizeChange(value)}
                  options={[
                    { key: '10', text: '10 per page', value: 10 },
                    { key: '25', text: '25 per page', value: 25 },
                    { key: '50', text: '50 per page', value: 50 },
                    { key: '100', text: '100 per page', value: 100 },
                    { key: 'all', text: 'Show All', value: 999_999 },
                  ]}
                  style={{ marginLeft: '0.5em' }}
                  text={pageSize >= 999_999 ? 'Show All' : `${pageSize} per page`}
                />
              )}
            />
            <DownloadDestinationSelector onChange={setDownloadDestination} />
            <div className="search-option-toggles">
              <Checkbox
                checked={hideLocked}
                className="search-options-hide-locked"
                label="Hide Locked Results"
                onChange={() => setHideLocked(!hideLocked)}
                toggle
              />
              <Checkbox
                checked={hideNoFreeSlots}
                className="search-options-hide-no-slots"
                label="Hide Results with No Free Slots"
                onChange={() => setHideNoFreeSlots(!hideNoFreeSlots)}
                toggle
              />
              <Checkbox
                checked={hideBlockedUsers}
                className="search-options-hide-blocked"
                label={`Hide Blocked Users (${blockedUsers.length})`}
                onChange={() => setHideBlockedUsers(!hideBlockedUsers)}
                toggle
              />
              <Checkbox
                checked={foldResults}
                className="search-options-fold-results"
                label="Fold Results"
                onChange={() => setFoldResults(!foldResults)}
                toggle
              />
              <Popup
                content="Fold duplicate file candidates that appear from multiple providers or peers, keeping the highest-ranked visible result and showing the folded sources as metadata."
                position="top center"
                trigger={
                  <Checkbox
                    checked={foldDuplicateResults}
                    className="search-options-fold-duplicates"
                    label={`Fold Duplicates${
                      deduplicatedResults.foldedCount > 0
                        ? ` (${deduplicatedResults.foldedCount})`
                        : ''
                    }`}
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
                ? 'Wishlist search: use “Ignore for Wishlist” below a result folder to hide that peer and folder from future runs of this wishlist item.'
                : 'Folder ignores are available only for wishlist searches because each rule belongs to one wishlist item. Open a result from Wishlist history to use them.'}
            </div>
            <Input
              action={
                <Button.Group>
                  {savedFilters.length > 0 && (
                    <Popup
                      content="Load a saved browser-local filter into the current result list."
                      trigger={(
                        <Dropdown
                          aria-label="Load saved filter"
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
                          title="Load saved filter"
                        />
                      )}
                    />
                  )}
                  {Boolean(resultFilters) && (
                    <Popup
                      content="Remove the current filter text and show results without these conditions."
                      trigger={(
                        <Button
                          aria-label="Clear current filter"
                          color="red"
                          icon="x"
                          onClick={() => setResultFilters('')}
                          title="Clear current filter"
                        />
                      )}
                    />
                  )}
                  {Boolean(resultFilters) && (
                    <Popup
                      content="Save the current result filter under a name for reuse later."
                      trigger={(
                        <Button
                          aria-label="Save named filter"
                          color="teal"
                          icon="bookmark"
                          onClick={openSaveFilter}
                          title="Save named filter"
                        />
                      )}
                    />
                  )}
                  {savedFilters.some((filter) => filter.value === resultFilters) && (
                    <Popup
                      content="Remove the saved filter that exactly matches the current filter text."
                      trigger={(
                        <Button
                          aria-label="Delete matching saved filter"
                          color="orange"
                          icon="minus circle"
                          onClick={deleteNamedFilter}
                          title="Delete matching saved filter"
                        />
                      )}
                    />
                  )}
                  <Popup
                    content="Use the current filter automatically for future search-result lists in this browser."
                    trigger={(
                      <Button
                        aria-label="Save as default filter"
                        color="blue"
                        icon="save"
                        onClick={saveAsDefault}
                        title="Save as default filter"
                      />
                    )}
                  />
                  {hasSavedDefault && (
                    <Popup
                      content="Remove the saved default filter from this browser."
                      trigger={(
                        <Button
                          aria-label="Clear saved default filter"
                          color="orange"
                          icon="trash"
                          onClick={clearSavedDefault}
                          title="Clear saved default filter"
                        />
                      )}
                    />
                  )}
                  <SearchFilterModal
                    filterString={resultFilters}
                    onChange={setResultFilters}
                    trigger={
                      <Popup
                        content="Build result-filter conditions without memorizing the filter syntax."
                        trigger={(
                          <Button
                            aria-label="Advanced Filters"
                            icon
                            title="Advanced Filters"
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
              label={{ content: 'Filter', icon: 'filter' }}
              onChange={(_event, data) => setResultFilters(data.value)}
              placeholder="
                lackluster container -bothersome iscbr|isvbr islossless|islossy 
                minbr:320 minfilesize:100mb maxfilesize:2gb minfilesinfolder:8 minlength:5000
              "
              value={resultFilters}
            />
          </Segment>
        )}
        {loaded && albumCandidates.length > 0 && (
          <Segment
            className="search-album-picker-segment"
            raised
          >
            <Header as="h4">
              Album candidates
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
                      content="Save this visible album review as a browser-local rule preview for similar future searches. This does not alter download behavior or contact peers."
                      position="top center"
                      trigger={
                        <Button
                          aria-label={`Save album rule ${candidate.albumTitle}`}
                          icon="bookmark outline"
                          onClick={() => saveAlbumCandidateRule(candidate)}
                          size="mini"
                        />
                      }
                    />
                    <Popup
                      content="Focus the current result filter on this album folder name without starting another search or download."
                      position="top center"
                      trigger={
                        <Button
                          aria-label={`Focus album candidate ${candidate.albumTitle}`}
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
                      {candidate.trackCount}/{candidate.expectedTrackCount}{' '}
                      visible tracks · {candidate.sourceCount} source
                      {candidate.sourceCount === 1 ? '' : 's'} ·{' '}
                      {Math.round(candidate.completenessRatio * 100)}%
                    </List.Description>
                    <div className="search-album-candidate-review">
                      <span>
                        Formats:{' '}
                        {candidate.formatMix
                          .map((item) => `${item.format} ${item.count}`)
                          .join(', ')}
                      </span>
                      {candidate.missingTrackNumbers.length > 0 && (
                        <span>
                          Missing:{' '}
                          {candidate.missingTrackNumbers.slice(0, 8).join(', ')}
                        </span>
                      )}
                      {candidate.durationVarianceSeconds > 0 && (
                        <span>
                          Duration spread:{' '}
                          {Math.round(candidate.durationVarianceSeconds / 60)}m
                        </span>
                      )}
                      {candidate.substitutionOptions.length > 0 && (
                        <span>
                          Substitutions:{' '}
                          {candidate.substitutionOptions
                            .map(
                              (option) =>
                                `track ${option.trackNumber} (${option.optionCount})`,
                            )
                            .join(', ')}
                        </span>
                      )}
                    </div>
                    {candidate.substitutionOptions.length > 0 && (
                      <div className="search-album-candidate-substitutions">
                        {candidate.substitutionOptions.slice(0, 4).map((option) => (
                          <Popup
                            content={`Manual review options from ${option.sources.join(', ')} in ${option.formats.join(', ')}. This only describes visible alternatives; it does not select or download them.`}
                            key={option.trackNumber}
                            position="top center"
                            trigger={
                              <Label
                                color="teal"
                                size="tiny"
                              >
                                <Icon name="exchange" />
                                Track {option.trackNumber}: {option.optionCount}{' '}
                                options
                              </Label>
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
                          content="This is a local confidence warning from visible search result metadata only; it does not reject the candidate or contact peers."
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
          cancelButton="Keep Result"
          confirmButton="Ignore Folder"
          content={ignoreRequest
            ? `Hide “${ignoreRequest.directory}” from ${ignoreRequest.username} in every future run of this wishlist item? Other results from this user will remain visible.`
            : ''}
          header="Ignore Wishlist Folder"
          onCancel={() => setIgnoreRequest(null)}
          onConfirm={handleIgnoreWishlistDirectory}
          open={Boolean(ignoreRequest)}
          size="small"
        />
        {loaded &&
          (remainingCount > 0 ? (
            <Popup
              content="Add the next batch of matching results to the current list."
              trigger={(
                <Button
                  className="showmore-button"
                  fluid
                  onClick={() => setDisplayCount(displayCount + pageSize)}
                  primary
                  size="large"
                >
                  Show {remainingCount > pageSize ? pageSize : remainingCount} More
                  Results{' '}
                  {`(${remainingCount} remaining, ${filteredCount} hidden by filter(s))`}
                </Button>
              )}
            >
            </Popup>
          ) : filteredCount > 0 ? (
            <div className="showmore-button" role="status">
              {`All results shown. ${filteredCount} results hidden by filter(s)`}
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
        <Modal.Header>Save Search Filter</Modal.Header>
        <Modal.Content>
          <p>Save the current result filter in this browser for later searches.</p>
          <Form>
            <Form.Field>
              <label htmlFor="saved-search-filter-name">Filter name</label>
              <input
                autoFocus
                id="saved-search-filter-name"
                onChange={(event) => setSaveFilterName(event.target.value)}
                placeholder="Filter name"
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
            content="Close this dialog without saving the current result filter."
            trigger={(
              <Button onClick={() => setSaveFilterOpen(false)}>
                Cancel
              </Button>
            )}
          />
          <Popup
            content="Save this filter under the name above in this browser."
            trigger={(
              <Button
                disabled={!saveFilterName.trim() || !resultFilters.trim()}
                onClick={saveNamedFilter}
                primary
              >
                Save Filter
              </Button>
            )}
          />
        </Modal.Actions>
      </Modal>
    </>
  );
};

export default SearchDetail;
