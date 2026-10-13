import { getRegionalLocale } from '../../lib/regionalFormat';
import './Wishlist.css';
import { urlBase } from '../../config';
import {
  buildWishlistRequestReviewPacket,
  buildWishlistRequestSummary,
  formatWishlistRequestReviewPacket,
  getWishlistRequestState,
  getRunnableWishlistRequests,
} from '../../lib/acquisitionRequests';
import * as wishlistAPI from '../../lib/wishlist';
import * as searchesAPI from '../../lib/searches';
import * as optionsAPI from '../../lib/options';
import { syncBlockedUsers } from '../../lib/userBlocks';
import { TooltipButton } from '../Shared';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
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
  Modal,
  Popup,
  Segment,
  Table,
} from 'semantic-ui-react';

const formatDate = (dateString) => {
  if (!dateString) return 'Never';
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return 'Never';
  return date.toLocaleString(getRegionalLocale());
};

const getVisibleHitCount = (item) => item.lastVisibleHitCount ?? item.lastMatchCount ?? 0;

const getHitBreakdown = (item) => ({
  blocked: item.lastBlockedHitCount ?? 0,
  filteredOut: item.lastFilteredOutHitCount ?? 0,
  hiddenLocked: item.lastHiddenLockedHitCount ?? 0,
  ignored: item.lastIgnoredResultHitCount ?? 0,
  responses: item.lastResponseCount ?? item.lastMatchCount ?? 0,
  visible: getVisibleHitCount(item),
});

const includesUsername = (usernames, username) => {
  const normalized = (username || '').toLocaleLowerCase();
  return Boolean(normalized) && usernames.some(
    (blockedUsername) => blockedUsername.toLocaleLowerCase() === normalized,
  );
};

const getUnseenCount = (item) => {
  if (!item.lastSearchId || !item.lastSearchedAt) return 0;
  if (!item.lastViewedAt) return getVisibleHitCount(item);
  const lastViewed = new Date(item.lastViewedAt).getTime();
  const lastSearch = new Date(item.lastSearchedAt).getTime();
  return lastSearch > lastViewed && getVisibleHitCount(item) > 0 ? getVisibleHitCount(item) : 0;
};

const getSearchLink = (item, searchId = item.lastSearchId) => {
  const params = new URLSearchParams();

  if (item.filter) {
    params.set('filter', item.filter);
  }

  const suffix = params.toString() ? `?${params.toString()}` : '';
  return `${urlBase}/searches/${encodeURIComponent(searchId)}${suffix}`;
};

const WishlistItemRow = ({
  item,
  onDelete,
  onEdit,
  onRunSearch,
  onMarkViewed,
  selected,
  onSelect,
  blockedUsers,
}) => {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [running, setRunning] = useState(false);
  const [showSearches, setShowSearches] = useState(false);
  const [relatedSearches, setRelatedSearches] = useState([]);
  const [loadingSearches, setLoadingSearches] = useState(false);
  const [expandedSearchId, setExpandedSearchId] = useState(null);
  const [expandedSearchResults, setExpandedSearchResults] = useState([]);
  const [loadingResults, setLoadingResults] = useState(false);
  const visibleExpandedSearchResults = useMemo(
    () => expandedSearchResults.filter((result) => !includesUsername(blockedUsers, result.username)),
    [blockedUsers, expandedSearchResults],
  );
  const requestState = getWishlistRequestState(item, []);
  const unseenCount = getUnseenCount(item);

  const handleRunSearch = async () => {
    setRunning(true);
    try {
      const result = await onRunSearch(item.id);
      toast.success(`Search completed with ${result.responseCount} results`);
    } catch (error) {
      toast.error(`Search failed: ${error.message}`);
    } finally {
      setRunning(false);
    }
  };

  const handleToggleSearches = async () => {
    const next = !showSearches;
    setShowSearches(next);
    if (next && relatedSearches.length === 0) {
      setLoadingSearches(true);
      try {
        const searches = await wishlistAPI.getSearches(item.id);
        setRelatedSearches(searches);
      } catch (error) {
        toast.error(`Failed to load searches: ${error.message}`);
      } finally {
        setLoadingSearches(false);
      }
    }
  };

  const handleMarkViewedClick = async () => {
    await onMarkViewed(item.id);
    toast.info(`Marked "${item.searchText}" as viewed`);
  };

  const handleToggleResults = async (searchId) => {
    if (expandedSearchId === searchId) {
      setExpandedSearchId(null);
      setExpandedSearchResults([]);
      return;
    }
    setExpandedSearchId(searchId);
    setLoadingResults(true);
    try {
      const results = await searchesAPI.getResponses({ id: searchId });
      setExpandedSearchResults(results);
    } catch (error) {
      toast.error(`Failed to load results: ${error.message}`);
      setExpandedSearchResults([]);
    } finally {
      setLoadingResults(false);
    }
  };

  return (
    <>
      <Table.Row>
        <Table.Cell>
          <Popup
            content="Select for bulk actions"
            position="top center"
            trigger={
              <Checkbox
                aria-label={`Select ${item.searchText} for bulk actions`}
                checked={selected}
                onChange={(_, { checked }) => onSelect(item.id, checked)}
              />
            }
          />
        </Table.Cell>
        <Table.Cell>
          <Icon
            color={item.enabled ? 'green' : 'grey'}
            name={item.enabled ? 'check circle' : 'circle outline'}
            style={{ marginRight: '0.5em' }}
          />
          <strong>{item.searchText}</strong>
          {item.filter && (
            <div className="wishlist-filter">Filter: {item.filter}</div>
          )}
        </Table.Cell>
        <Table.Cell textAlign="center">
          <Popup
            content="Auto-download best matches"
            trigger={
              <Icon
                color={item.autoDownload ? 'green' : 'grey'}
                name={item.autoDownload ? 'download' : 'download'}
              />
            }
          />
        </Table.Cell>
        <Table.Cell>{formatDate(item.lastSearchedAt)}</Table.Cell>
        <Table.Cell textAlign="center">
          <Popup
            content={() => {
              const hits = getHitBreakdown(item);
              return `${hits.visible} visible hits, ${hits.blocked} blocked, ${hits.hiddenLocked} locked (unreachable), ${hits.filteredOut} hidden by filter, ${hits.ignored} persistently ignored, ${hits.responses} responses`;
            }}
            position="top center"
            trigger={
              <span>
                {getVisibleHitCount(item)}
                {(item.lastHiddenLockedHitCount ?? 0) > 0 && (
                  <span className="wishlist-locked-count" style={{ color: '#999', marginLeft: '0.25em' }}>
                    {`(+${item.lastHiddenLockedHitCount} locked)`}
                  </span>
                )}
                {(item.lastBlockedHitCount ?? 0) > 0 && (
                  <span className="wishlist-blocked-count" style={{ color: '#999', marginLeft: '0.25em' }}>
                    {`(+${item.lastBlockedHitCount} blocked)`}
                  </span>
                )}
              </span>
            }
          />
          {unseenCount > 0 && (
            <Popup
              content={`${unseenCount} new result(s) since you last viewed this item`}
              trigger={
                <Label
                  color="red"
                  size="mini"
                  style={{ marginLeft: '0.5em' }}
                >
                  {unseenCount} new
                </Label>
              }
            />
          )}
        </Table.Cell>
        <Table.Cell textAlign="center">{item.totalSearchCount}</Table.Cell>
        <Table.Cell>
          <Popup
            content={requestState.summary}
            position="top center"
            trigger={
              <Label color={requestState.color}>
                {requestState.label}
              </Label>
            }
          />
        </Table.Cell>
        <Table.Cell>
          {item.lastSearchId && (
            <Link
              to={getSearchLink(item)}
            >
              <Popup
                content={item.filter
                  ? 'View the latest search results with this wishlist filter already applied.'
                  : 'View the latest search results for this wishlist item.'}
                position="top center"
                trigger={
                  <Button
                    aria-label={`View latest search results for ${item.searchText}`}
                    compact
                    icon="search"
                    size="tiny"
                    title="View last search results"
                  />
                }
              />
            </Link>
          )}
          {unseenCount > 0 && (
            <Popup
              content="Clear this item's new-results badge without opening its search history."
              position="top center"
              trigger={
                  <Button
                    aria-label={`Mark ${item.searchText} results as viewed`}
                    compact
                    icon="check"
                  onClick={handleMarkViewedClick}
                  size="tiny"
                  title="Mark viewed"
                />
              }
            />
          )}
          <TooltipButton
            aria-label={showSearches
              ? `Hide ${item.searchText} search history`
              : `Show ${item.searchText} search history`}
            compact
            icon={showSearches ? 'angle up' : 'angle down'}
            loading={loadingSearches}
            onClick={handleToggleSearches}
            size="tiny"
            tooltip={showSearches
              ? 'Hide earlier searches to return to the wishlist items.'
              : 'Review this item’s linked search history and past results.'}
          />
          <TooltipButton
            aria-label={`Run ${item.searchText} wishlist search now`}
            compact
            icon="play"
            loading={running}
            onClick={handleRunSearch}
            primary
            size="tiny"
            tooltip="Manually search Soulseek for current matches. This contacts peers now rather than waiting for the next scheduled run."
          />
          <TooltipButton
            aria-label={`Edit ${item.searchText} wishlist settings`}
            compact
            icon="edit"
            onClick={() => onEdit(item)}
            size="tiny"
            tooltip="Change this item’s search text, filters, result limits, and automation settings."
          />
          <TooltipButton
            aria-label={`Delete ${item.searchText} from Wishlist`}
            color="red"
            compact
            icon="trash"
            onClick={() => setConfirmDelete(true)}
            size="tiny"
            tooltip="Remove this wishlist entry after confirmation when you no longer want its search tracked."
          />
          <Confirm
            cancelButton={(
              <TooltipButton tooltip="Keep this wishlist item and return to the list.">
                Cancel
              </TooltipButton>
            )}
            confirmButton={(
              <TooltipButton
                color="red"
                tooltip="Remove this wishlist item and its saved search settings."
              >
                Delete
              </TooltipButton>
            )}
            content={`Delete wishlist item "${item.searchText}"?`}
            header="Confirm Delete"
            onCancel={() => setConfirmDelete(false)}
            onConfirm={() => {
              setConfirmDelete(false);
              onDelete(item.id);
            }}
            open={confirmDelete}
            size="mini"
          />
        </Table.Cell>
      </Table.Row>
      {showSearches && (
        <Table.Row>
          <Table.Cell colSpan="8" style={{ background: 'rgba(0,0,0,0.03)' }}>
            {loadingSearches ? (
              <Icon name="spinner" loading />
            ) : relatedSearches.length === 0 ? (
              <span style={{ color: '#999', fontStyle: 'italic' }}>
                No linked search history for this item yet.
                {item.lastSearchId && (
                  <>
                    {' '}
                    <Link
                      to={getSearchLink(item)}
                    >
                      Open latest search result.
                    </Link>
                  </>
                )}
              </span>
            ) : (
              <>
                <Table compact size="small" basic="very">
                  <Table.Header>
                    <Table.Row>
                      <Table.HeaderCell>Search</Table.HeaderCell>
                      <Table.HeaderCell>Source</Table.HeaderCell>
                      <Table.HeaderCell>Responses</Table.HeaderCell>
                      <Table.HeaderCell>Files</Table.HeaderCell>
                      <Table.HeaderCell>Started</Table.HeaderCell>
                      <Table.HeaderCell />
                    </Table.Row>
                  </Table.Header>
                  <Table.Body>
                    {relatedSearches.map((s) => (
                      <Table.Row key={s.id}>
                        <Table.Cell>{s.searchText}</Table.Cell>
                        <Table.Cell>
                          <Label
                            color={s.source === 'wishlist' ? 'blue' : s.source === 'auto-replace' ? 'orange' : 'grey'}
                            size="mini"
                          >
                            {s.source || 'manual'}
                          </Label>
                        </Table.Cell>
                        <Table.Cell>{s.responseCount}</Table.Cell>
                        <Table.Cell>{s.fileCount}</Table.Cell>
                        <Table.Cell>{formatDate(s.startedAt)}</Table.Cell>
                        <Table.Cell>
                          <Link
                            to={getSearchLink(item, s.id)}
                          >
                            <Popup
                              content={item.filter
                                ? 'View full search page with this wishlist filter already applied.'
                                : 'View full search page.'}
                              position="top center"
                              trigger={
                                <Button
                                  aria-label={`Open the full search for ${item.searchText}`}
                                  compact
                                  icon="external"
                                  size="mini"
                                />
                              }
                            />
                          </Link>
                          <Popup
                            content={expandedSearchId === s.id ? 'Hide results' : 'Show results inline'}
                            position="top center"
                            trigger={
                              <Button
                                aria-label={expandedSearchId === s.id
                                  ? `Hide ${item.searchText} results inline`
                                  : `Show ${item.searchText} results inline`}
                                compact
                                icon={expandedSearchId === s.id ? 'angle up' : 'angle down'}
                                loading={loadingResults && expandedSearchId === s.id}
                                onClick={() => handleToggleResults(s.id)}
                                size="mini"
                              />
                            }
                          />
                        </Table.Cell>
                      </Table.Row>
                    ))}
                  </Table.Body>
                </Table>
                {expandedSearchId && (
                  <div style={{ marginTop: '0.75em', padding: '0.5em', background: 'rgba(255,255,255,0.05)', borderRadius: '4px' }}>
                    {loadingResults ? (
                      <Icon name="spinner" loading />
                    ) : visibleExpandedSearchResults.length === 0 ? (
                      <span style={{ color: '#999', fontStyle: 'italic' }}>No results for this search.</span>
                    ) : (
                      <>
                        <Header as="h5" style={{ marginBottom: '0.5em' }}>
                          {visibleExpandedSearchResults.length} result(s)
                        </Header>
                        <Table compact size="small" basic="very" striped>
                          <Table.Header>
                            <Table.Row>
                              <Table.HeaderCell>Username</Table.HeaderCell>
                              <Table.HeaderCell>Directory</Table.HeaderCell>
                              <Table.HeaderCell>Files</Table.HeaderCell>
                              <Table.HeaderCell>Size</Table.HeaderCell>
                            </Table.Row>
                          </Table.Header>
                          <Table.Body>
                            {visibleExpandedSearchResults.slice(0, 20).map((r, idx) => {
                              const dir = r.files?.[0]?.filename
                                ? r.files[0].filename.split('/').slice(0, -1).join('/')
                                : '';
                              const totalSize = r.files?.reduce((sum, f) => sum + (f.size || 0), 0) || 0;
                              const sizeStr = totalSize > 1073741824
                                ? `${(totalSize / 1073741824).toFixed(1)} GB`
                                : totalSize > 1048576
                                  ? `${(totalSize / 1048576).toFixed(1)} MB`
                                  : `${(totalSize / 1024).toFixed(0)} KB`;
                              return (
                                <Table.Row key={idx}>
                                  <Table.Cell>{r.username}</Table.Cell>
                                  <Table.Cell className="truncate-cell" title={dir}>{dir}</Table.Cell>
                                  <Table.Cell>{r.fileCount}</Table.Cell>
                                  <Table.Cell>{sizeStr}</Table.Cell>
                                </Table.Row>
                              );
                            })}
                          </Table.Body>
                        </Table>
                        {visibleExpandedSearchResults.length > 20 && (
                          <span style={{ color: '#999', fontSize: '0.85em' }}>
                            Showing first 20 of {visibleExpandedSearchResults.length} results.
                          </span>
                        )}
                      </>
                    )}
                  </div>
                )}
              </>
            )}
          </Table.Cell>
        </Table.Row>
      )}
    </>
  );
};

const WishlistItemCard = ({
  item,
  onDelete,
  onEdit,
  onMarkViewed,
  onRunSearch,
  selected,
  onSelect,
  blockedUsers,
}) => {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [running, setRunning] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [relatedSearches, setRelatedSearches] = useState([]);
  const [loadingSearches, setLoadingSearches] = useState(false);
  const [expandedSearchId, setExpandedSearchId] = useState(null);
  const [expandedSearchResults, setExpandedSearchResults] = useState([]);
  const [loadingResults, setLoadingResults] = useState(false);
  const visibleExpandedSearchResults = useMemo(
    () => expandedSearchResults.filter((result) => !includesUsername(blockedUsers, result.username)),
    [blockedUsers, expandedSearchResults],
  );
  const requestState = getWishlistRequestState(item, []);
  const unseenCount = getUnseenCount(item);

  const handleRunSearch = async () => {
    setRunning(true);
    try {
      const result = await onRunSearch(item.id);
      toast.success(`Search completed with ${result.responseCount} results`);
    } catch (error) {
      toast.error(`Search failed: ${error.message}`);
    } finally {
      setRunning(false);
    }
  };

  const handleToggleExpand = async () => {
    const next = !expanded;
    setExpanded(next);
    if (next && relatedSearches.length === 0) {
      setLoadingSearches(true);
      try {
        const searches = await wishlistAPI.getSearches(item.id);
        setRelatedSearches(searches);
      } catch (error) {
        toast.error(`Failed to load searches: ${error.message}`);
      } finally {
        setLoadingSearches(false);
      }
    }
  };

  const handleMarkViewedClick = async () => {
    await onMarkViewed(item.id);
    toast.info(`Marked "${item.searchText}" as viewed`);
  };

  const handleToggleResults = async (searchId) => {
    if (expandedSearchId === searchId) {
      setExpandedSearchId(null);
      setExpandedSearchResults([]);
      return;
    }
    setExpandedSearchId(searchId);
    setLoadingResults(true);
    try {
      const results = await searchesAPI.getResponses({ id: searchId });
      setExpandedSearchResults(results);
    } catch (error) {
      toast.error(`Failed to load results: ${error.message}`);
      setExpandedSearchResults([]);
    } finally {
      setLoadingResults(false);
    }
  };

  return (
    <>
      <Segment
        className="wishlist-card"
        style={{
          borderLeft: selected ? '4px solid #2185d0' : '4px solid transparent',
          marginBottom: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75em' }}>
          <Checkbox
            aria-label={`Select ${item.searchText} for bulk actions`}
            checked={selected}
            onChange={(_, { checked }) => onSelect(item.id, checked)}
            style={{ marginTop: '0.3em' }}
          />
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5em', marginBottom: '0.25em' }}>
              <Icon
                color={item.enabled ? 'green' : 'grey'}
                name={item.enabled ? 'check circle' : 'circle outline'}
              />
              <strong style={{ fontSize: '1.1em' }}>{item.searchText}</strong>
              {item.filter && (
                <Label basic color="blue" size="mini">
                  {item.filter}
                </Label>
              )}
              {unseenCount > 0 && (
                <Popup
                  content={`${unseenCount} new result(s) since you last viewed this item`}
                  trigger={
                    <Label color="red" size="mini">
                      {unseenCount} new
                    </Label>
                  }
                />
              )}
              <Popup
                content={requestState.summary}
                position="top center"
                trigger={
                  <Label color={requestState.color} size="mini">
                    {requestState.label}
                  </Label>
                }
              />
            </div>
            <div style={{ display: 'flex', gap: '1em', fontSize: '0.85em', color: '#888', flexWrap: 'wrap' }}>
              <span>Last run: {formatDate(item.lastSearchedAt)}</span>
              <span>
                Hits: {getVisibleHitCount(item)}
                {(item.lastHiddenLockedHitCount ?? 0) > 0 && (
                  <Popup
                    content="Files matched but the uploader has them locked (not downloadable without sharing access)."
                    position="top center"
                    trigger={
                      <span style={{ color: '#999', marginLeft: '0.25em' }}>
                        {`(+${item.lastHiddenLockedHitCount} locked)`}
                      </span>
                    }
                  />
                )}
                {(item.lastBlockedHitCount ?? 0) > 0 && (
                  <Popup
                    content="Matching files from blocked users are excluded from Wishlist hits and automatic downloads."
                    position="top center"
                    trigger={
                      <span style={{ color: '#999', marginLeft: '0.25em' }}>
                        {`(+${item.lastBlockedHitCount} blocked)`}
                      </span>
                    }
                  />
                )}
              </span>
              <span>Runs: {item.totalSearchCount}</span>
              <span>
                Auto-download:{' '}
                <Icon name={item.autoDownload ? 'check' : 'close'} color={item.autoDownload ? 'green' : 'grey'} />
              </span>
              {item.autoDownload && item.maxDownloads && (
                <span>
                  Downloads: {item.totalDownloadCount}/{item.maxDownloads}
                </span>
              )}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.25em' }}>
            <Popup
              content={expanded
                ? 'Hide this item’s linked searches and result details.'
                : 'Show this item’s linked searches and past results inline.'}
              position="top center"
              trigger={
                <Button
                  aria-label={expanded
                    ? `Hide ${item.searchText} search history`
                    : `Show ${item.searchText} search history`}
                  compact
                  icon={expanded ? 'angle up' : 'angle down'}
                  loading={loadingSearches}
                  onClick={handleToggleExpand}
                  size="mini"
                />
              }
            />
            {item.lastSearchId && (
              <Link
                to={getSearchLink(item)}
              >
                <Popup
                  content={item.filter
                    ? 'View the latest search results with this wishlist filter already applied.'
                    : 'View the latest search results for this wishlist item.'}
                  position="top center"
                  trigger={
                    <Button
                      aria-label={`View latest search results for ${item.searchText}`}
                      compact
                      icon="search"
                      size="mini"
                    />
                  }
                />
              </Link>
            )}
            {unseenCount > 0 && (
              <Popup
                content="Clear this item's new-results badge without opening its search history."
                position="top center"
                trigger={
                  <Button
                    aria-label={`Mark ${item.searchText} results as viewed`}
                    compact
                    icon="check"
                    onClick={handleMarkViewedClick}
                    size="mini"
                  />
                }
              />
            )}
            <Popup
              content="Manually search Soulseek for current matches. This contacts peers now rather than waiting for the next scheduled run."
              position="top center"
              trigger={
                <Button
                  aria-label={`Run ${item.searchText} wishlist search now`}
                  compact
                  icon="play"
                  loading={running}
                  onClick={handleRunSearch}
                  primary
                  size="mini"
                />
              }
            />
            <Popup
              content="Change this item’s search text, filters, result limits, and automation settings."
              position="top center"
              trigger={
                <Button
                  aria-label={`Edit ${item.searchText} wishlist settings`}
                  compact
                  icon="edit"
                  onClick={() => onEdit(item)}
                  size="mini"
                />
              }
            />
            <Popup
              content="Remove this wishlist entry after confirmation when you no longer want its search tracked."
              position="top center"
              trigger={
                <Button
                  aria-label={`Delete ${item.searchText} from Wishlist`}
                  color="red"
                  compact
                  icon="trash"
                  onClick={() => setConfirmDelete(true)}
                  size="mini"
                />
              }
            />
          </div>
        </div>

        {expanded && (
          <div style={{ marginTop: '1em', paddingTop: '1em', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
            {loadingSearches ? (
              <Icon name="spinner" loading />
            ) : relatedSearches.length === 0 ? (
              <span style={{ color: '#999', fontStyle: 'italic' }}>
                No linked search history for this item yet.
                {item.lastSearchId && (
                  <>
                    {' '}
                    <Link
                      to={getSearchLink(item)}
                    >
                      Open latest search result.
                    </Link>
                  </>
                )}
              </span>
            ) : (
              <>
                <Table compact size="small" basic="very">
                  <Table.Header>
                    <Table.Row>
                      <Table.HeaderCell>Search</Table.HeaderCell>
                      <Table.HeaderCell>Source</Table.HeaderCell>
                      <Table.HeaderCell>Responses</Table.HeaderCell>
                      <Table.HeaderCell>Started</Table.HeaderCell>
                      <Table.HeaderCell />
                    </Table.Row>
                  </Table.Header>
                  <Table.Body>
                    {relatedSearches.map((s) => (
                      <Table.Row key={s.id}>
                        <Table.Cell>{s.searchText}</Table.Cell>
                        <Table.Cell>
                          <Label
                            color={s.source === 'wishlist' ? 'blue' : s.source === 'auto-replace' ? 'orange' : 'grey'}
                            size="mini"
                          >
                            {s.source || 'manual'}
                          </Label>
                        </Table.Cell>
                        <Table.Cell>{s.responseCount}</Table.Cell>
                        <Table.Cell>{formatDate(s.startedAt)}</Table.Cell>
                        <Table.Cell>
                          <Link
                            to={getSearchLink(item, s.id)}
                          >
                            <Popup
                              content={item.filter
                                ? 'View full search page with this wishlist filter already applied.'
                                : 'View full search page.'}
                              position="top center"
                              trigger={
                                <Button
                                  aria-label={`Open the full search for ${item.searchText}`}
                                  compact
                                  icon="external"
                                  size="mini"
                                />
                              }
                            />
                          </Link>
                          <Popup
                            content={expandedSearchId === s.id ? 'Hide results' : 'Show results inline'}
                            position="top center"
                            trigger={
                              <Button
                                aria-label={expandedSearchId === s.id
                                  ? `Hide ${item.searchText} results inline`
                                  : `Show ${item.searchText} results inline`}
                                compact
                                icon={expandedSearchId === s.id ? 'angle up' : 'angle down'}
                                loading={loadingResults && expandedSearchId === s.id}
                                onClick={() => handleToggleResults(s.id)}
                                size="mini"
                              />
                            }
                          />
                        </Table.Cell>
                      </Table.Row>
                    ))}
                  </Table.Body>
                </Table>
                {expandedSearchId && (
                  <div style={{ marginTop: '0.5em', padding: '0.5em', background: 'rgba(255,255,255,0.05)', borderRadius: '4px' }}>
                    {loadingResults ? (
                      <Icon name="spinner" loading />
                    ) : visibleExpandedSearchResults.length === 0 ? (
                      <span style={{ color: '#999', fontStyle: 'italic' }}>No results for this search.</span>
                    ) : (
                      <>
                        <Header as="h5" style={{ marginBottom: '0.5em' }}>
                          {visibleExpandedSearchResults.length} result(s)
                        </Header>
                        <Table compact size="small" basic="very" striped>
                          <Table.Header>
                            <Table.Row>
                              <Table.HeaderCell>Username</Table.HeaderCell>
                              <Table.HeaderCell>Directory</Table.HeaderCell>
                              <Table.HeaderCell>Files</Table.HeaderCell>
                              <Table.HeaderCell>Size</Table.HeaderCell>
                            </Table.Row>
                          </Table.Header>
                          <Table.Body>
                            {visibleExpandedSearchResults.slice(0, 20).map((r, idx) => {
                              const dir = r.files?.[0]?.filename
                                ? r.files[0].filename.split('/').slice(0, -1).join('/')
                                : '';
                              const totalSize = r.files?.reduce((sum, f) => sum + (f.size || 0), 0) || 0;
                              const sizeStr = totalSize > 1073741824
                                ? `${(totalSize / 1073741824).toFixed(1)} GB`
                                : totalSize > 1048576
                                  ? `${(totalSize / 1048576).toFixed(1)} MB`
                                  : `${(totalSize / 1024).toFixed(0)} KB`;
                              return (
                                <Table.Row key={idx}>
                                  <Table.Cell>{r.username}</Table.Cell>
                                  <Table.Cell className="truncate-cell" title={dir}>{dir}</Table.Cell>
                                  <Table.Cell>{r.fileCount}</Table.Cell>
                                  <Table.Cell>{sizeStr}</Table.Cell>
                                </Table.Row>
                              );
                            })}
                          </Table.Body>
                        </Table>
                        {visibleExpandedSearchResults.length > 20 && (
                          <span style={{ color: '#999', fontSize: '0.85em' }}>
                            Showing first 20 of {visibleExpandedSearchResults.length} results.
                          </span>
                        )}
                      </>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </Segment>
      <Confirm
        cancelButton={(
          <TooltipButton tooltip="Keep this wishlist item and return to the list.">
            Cancel
          </TooltipButton>
        )}
        confirmButton={(
          <TooltipButton
            color="red"
            tooltip="Remove this wishlist item and its saved search settings."
          >
            Delete
          </TooltipButton>
        )}
        content={`Delete wishlist item "${item.searchText}"?`}
        header="Confirm Delete"
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => {
          setConfirmDelete(false);
          onDelete(item.id);
        }}
        open={confirmDelete}
        size="mini"
      />
    </>
  );
};

const FILTER_PRESETS = [
  { label: 'FLAC', value: 'flac' },
  { label: 'MP3', value: 'mp3' },
  { label: 'MP3 320+', value: 'mp3 minbr:320' },
  { label: 'FLAC + MP3', value: 'flac OR mp3' },
  { label: 'FLAC + ALAC', value: 'flac OR alac' },
  { label: 'Lossless', value: 'flac OR alac OR wav OR ape' },
  { label: 'Any', value: '' },
];

const WISHLIST_VIEW_KEY = 'slskdn-wishlist-view-state';
const PAGE_SIZE_OPTIONS = [50, 100, 250, 500];

const SORT_OPTIONS = [
  { key: 'created-desc', text: 'Newest added', value: 'created-desc' },
  { key: 'az', text: 'A-Z', value: 'az' },
  { key: 'za', text: 'Z-A', value: 'za' },
  { key: 'last-searched', text: 'Last searched', value: 'last-searched' },
  { key: 'new-first', text: 'New results first', value: 'new-first' },
  { key: 'hits-desc', text: 'Most hits', value: 'hits-desc' },
];

const loadWishlistViewState = () => {
  try {
    const parsed = JSON.parse(localStorage.getItem(WISHLIST_VIEW_KEY) || '{}');
    return {
      autoOnly: Boolean(parsed.autoOnly),
      enabledOnly: Boolean(parsed.enabledOnly),
      hasResultsOnly: Boolean(parsed.hasResultsOnly),
      newOnly: Boolean(parsed.newOnly),
      pageSize: PAGE_SIZE_OPTIONS.includes(parsed.pageSize) ? parsed.pageSize : 100,
      query: parsed.query || '',
      sort: parsed.sort || 'created-desc',
    };
  } catch {
    return {
      autoOnly: false,
      enabledOnly: false,
      hasResultsOnly: false,
      newOnly: false,
      pageSize: 100,
      query: '',
      sort: 'created-desc',
    };
  }
};

const saveWishlistViewState = (state) => {
  localStorage.setItem(WISHLIST_VIEW_KEY, JSON.stringify(state));
};

const validateFilter = (filter) => {
  if (!filter || !filter.trim()) return null;
  const invalid = filter.match(/[^\w.:\-\s"]/);
  if (invalid) {
    return 'Filter may contain words, quoted phrases, extensions, minbr:/minbitrate: directives, exclusions prefixed with -, and OR';
  }
  if ((filter.match(/"/g) || []).length % 2 !== 0) return 'Quoted filter phrases must have a closing quote';
  return null;
};

const FilterPresetButtons = ({ filter, onChange }) => (
  <div style={{ marginTop: '0.5em' }}>
    {FILTER_PRESETS.map((preset) => (
      <Popup
        key={preset.value}
        content={
          preset.value
            ? `Filter to ${preset.label} files`
            : 'Accept any file format'
        }
        trigger={
          <Button
            active={filter === preset.value}
            compact
            onClick={() => onChange(preset.value)}
            size="mini"
            style={{ marginRight: '0.25em', marginBottom: '0.25em' }}
            toggle={!!preset.value}
          >
            {preset.label}
          </Button>
        }
      />
    ))}
  </div>
);

const WishlistModal = ({ item, onClose, onSave }) => {
  const [searchText, setSearchText] = useState(item?.searchText || '');
  const [filter, setFilter] = useState(item?.filter || '');
  const [enabled, setEnabled] = useState(item?.enabled ?? true);
  const [autoDownload, setAutoDownload] = useState(item?.autoDownload ?? false);
  const [maxResults, setMaxResults] = useState(item?.maxResults ?? 100);
  const [maxDownloads, setMaxDownloads] = useState(item?.maxDownloads || '');
  const [saving, setSaving] = useState(false);
  const [filterError, setFilterError] = useState(null);
  const [ignoredResults, setIgnoredResults] = useState([]);
  const [loadingIgnoredResults, setLoadingIgnoredResults] = useState(false);

  const isEdit = Boolean(item?.id);

  useEffect(() => {
    if (!isEdit) return;

    let cancelled = false;
    setLoadingIgnoredResults(true);
    wishlistAPI.getIgnoredResults(item.id)
      .then((rules) => {
        if (!cancelled) setIgnoredResults(rules);
      })
      .catch((error) => {
        console.error(error);
        if (!cancelled) toast.error('Failed to load ignored wishlist folders');
      })
      .finally(() => {
        if (!cancelled) setLoadingIgnoredResults(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isEdit, item?.id]);

  const restoreIgnoredResult = async (rule) => {
    try {
      await wishlistAPI.removeIgnoredResult(item.id, rule.id);
      setIgnoredResults((current) => current.filter((candidate) => candidate.id !== rule.id));
      toast.info(`Restored ${rule.directory} from ${rule.username}`);
    } catch (error) {
      console.error(error);
      toast.error(error?.response?.data ?? error?.message ?? error);
    }
  };

  const handleFilterChange = (value) => {
    setFilter(value);
    setFilterError(validateFilter(value));
  };

  const handleSave = async () => {
    if (!searchText.trim()) {
      toast.error('Search text is required');
      return;
    }
    if (filterError) {
      toast.error('Please fix the filter error before saving');
      return;
    }

    setSaving(true);
    try {
      await onSave({
        autoDownload,
        enabled,
        filter: filter.trim() || undefined,
        id: item?.id,
        maxDownloads: maxDownloads === '' ? null : Number.parseInt(maxDownloads, 10) || null,
        maxResults,
        searchText: searchText.trim(),
      });
      onClose();
    } catch (error) {
      toast.error(`Failed to save: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      onClose={onClose}
      open
      size="small"
    >
      <Modal.Header>
        <Icon name="star" />
        {isEdit ? 'Edit Wishlist Item' : 'Add to Wishlist'}
      </Modal.Header>
      <Modal.Content>
        <Form>
          <Form.Input
            label="Search Text"
            onChange={(event) => setSearchText(event.target.value)}
            placeholder="Enter search terms..."
            required
            value={searchText}
          />
          <Form.Field>
            <label>Filter (optional)</label>
            <Popup
              content={'Only accept matching filenames or extensions. Use -word to exclude a word or -"exact phrase" to exclude a specific album or folder name.'}
              position="top center"
              trigger={
                <Form.Input
                  error={!!filterError}
                  onChange={(event) => handleFilterChange(event.target.value)}
                  placeholder="e.g., flac OR mp3"
                  value={filter}
                />
              }
            />
            {filterError && (
              <Label basic color="red" pointing>
                {filterError}
              </Label>
            )}
            <FilterPresetButtons filter={filter} onChange={handleFilterChange} />
          </Form.Field>
          {isEdit && (
            <Segment>
              <Header as="h4">
                <Icon name="eye slash" />
                <Header.Content>
                  Ignored Result Folders
                  <Header.Subheader>
                    These peer folders stay hidden only for this wishlist item. Restore one to allow it in future searches and auto-download decisions.
                  </Header.Subheader>
                </Header.Content>
              </Header>
              {loadingIgnoredResults ? (
                <Icon loading name="spinner" />
              ) : ignoredResults.length === 0 ? (
                <span>No folders are ignored.</span>
              ) : (
                <Table basic="very" compact>
                  <Table.Body>
                    {ignoredResults.map((rule) => (
                      <Table.Row key={rule.id}>
                        <Table.Cell>
                          <strong>{rule.username}</strong>
                          <div className="truncate-cell" title={rule.directory}>{rule.directory}</div>
                        </Table.Cell>
                        <Table.Cell collapsing>
                          <Popup
                            content="Allow this peer folder to appear again in future runs of this wishlist item."
                            trigger={
                              <Button
                                aria-label={`Restore ${rule.username} ${rule.directory} to wishlist results`}
                                compact
                                icon="undo"
                                onClick={() => restoreIgnoredResult(rule)}
                                size="tiny"
                              />
                            }
                          />
                        </Table.Cell>
                      </Table.Row>
                    ))}
                  </Table.Body>
                </Table>
              )}
            </Segment>
          )}
          <Form.Input
            label="Max Results"
            max={1_000}
            min={10}
            onChange={(event) =>
              setMaxResults(Number.parseInt(event.target.value, 10) || 100)
            }
            type="number"
            value={maxResults}
          />
          <Form.Field>
            <Checkbox
              checked={enabled}
              label="Enabled (run automatically)"
              onChange={(_, data) => setEnabled(data.checked)}
              toggle
            />
          </Form.Field>
          <Form.Field>
            <Checkbox
              checked={autoDownload}
              label="Auto-download best matches"
              onChange={(_, data) => setAutoDownload(data.checked)}
              toggle
            />
          </Form.Field>
          <Form.Field>
            <Popup
              content="Automatically disable this item after N successful downloads. Leave blank to disable after the first download."
              position="top center"
              trigger={
                <label>
                  Auto-disable after downloads
                </label>
              }
            />
            <Form.Input
              label="Leave blank = disable after first download"
              min={1}
              onChange={(event) => setMaxDownloads(event.target.value)}
              placeholder="e.g., 5 for album parts"
              type="number"
              value={maxDownloads}
            />
          </Form.Field>
        </Form>
      </Modal.Content>
      <Modal.Actions>
        <TooltipButton
          onClick={onClose}
          tooltip="Close this form and discard unsaved wishlist changes."
        >
          Cancel
        </TooltipButton>
        <TooltipButton
          loading={saving}
          onClick={handleSave}
          primary
          tooltip={isEdit
            ? 'Save the updated search, filter, and automation settings for this wishlist item.'
            : 'Add this search to the wishlist with the filter and automation settings below.'}
        >
          {isEdit ? 'Save' : 'Add'}
        </TooltipButton>
      </Modal.Actions>
    </Modal>
  );
};

const BulkFilterModal = ({ count, onClose, onSave }) => {
  const [filter, setFilter] = useState('');
  const [filterError, setFilterError] = useState(null);
  const [saving, setSaving] = useState(false);

  const handleFilterChange = (value) => {
    setFilter(value);
    setFilterError(validateFilter(value));
  };

  const handleSave = async () => {
    if (filterError) {
      toast.error('Please fix the filter error before saving');
      return;
    }

    setSaving(true);
    try {
      await onSave(filter.trim());
      onClose();
    } catch (error) {
      toast.error(`Failed to update filters: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal onClose={onClose} open size="small">
      <Modal.Header>
        <Icon name="filter" />
        Edit Filter for {count} Wishlist Item{count === 1 ? '' : 's'}
      </Modal.Header>
      <Modal.Content>
        <p>
          Apply one filter to every selected item. Leave it blank to clear
          existing filters. Lidarr-synced filters may be refreshed by the next
          Lidarr wanted sync.
        </p>
        <Form>
          <Form.Field>
            <label>Filter (optional)</label>
            <Popup
              content="Use extensions or terms such as flac, mp3, or mp3 minbr:320. Prefix a term with - to exclude it."
              position="top center"
              trigger={
                <Form.Input
                  error={!!filterError}
                  onChange={(event) => handleFilterChange(event.target.value)}
                  placeholder="e.g., mp3 minbr:320"
                  value={filter}
                />
              }
            />
            {filterError && (
              <Label basic color="red" pointing>
                {filterError}
              </Label>
            )}
            <FilterPresetButtons filter={filter} onChange={handleFilterChange} />
          </Form.Field>
        </Form>
      </Modal.Content>
      <Modal.Actions>
        <TooltipButton
          onClick={onClose}
          tooltip="Close without changing filters on the selected wishlist items."
        >
          Cancel
        </TooltipButton>
        <TooltipButton
          loading={saving}
          onClick={handleSave}
          primary
          tooltip={`Apply this filter to ${count} selected wishlist ${count === 1 ? 'item' : 'items'} in one step.`}
        >
          Apply Filter
        </TooltipButton>
      </Modal.Actions>
    </Modal>
  );
};

const CsvImportModal = ({ onClose, onImport }) => {
  const [csvText, setCsvText] = useState('');
  const [filter, setFilter] = useState('');
  const [enabled, setEnabled] = useState(true);
  const [autoDownload, setAutoDownload] = useState(false);
  const [includeAlbum, setIncludeAlbum] = useState(false);
  const [maxResults, setMaxResults] = useState(100);
  const [importing, setImporting] = useState(false);

  const handleFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setCsvText(await file.text());
  };

  const handleImport = async () => {
    if (!csvText.trim()) {
      toast.error('CSV text is required');
      return;
    }

    setImporting(true);
    try {
      await onImport({
        autoDownload,
        csvText,
        enabled,
        filter: filter.trim() || undefined,
        includeAlbum,
        maxResults,
      });
      onClose();
    } catch (error) {
      toast.error(`CSV import failed: ${error.message}`);
    } finally {
      setImporting(false);
    }
  };

  return (
    <Modal
      onClose={onClose}
      open
      size="small"
    >
      <Modal.Header>
        <Icon name="file alternate outline" />
        Import CSV Playlist
      </Modal.Header>
      <Modal.Content>
        <Form>
          <Form.Input
            accept=".csv,text/csv"
            label="CSV File"
            onChange={handleFile}
            type="file"
          />
          <Form.TextArea
            label="CSV Text"
            onChange={(event) => setCsvText(event.target.value)}
            placeholder="Track name,Artist name,Album name"
            rows={8}
            value={csvText}
          />
          <Form.Input
            label="Filter (optional)"
            onChange={(event) => setFilter(event.target.value)}
            placeholder="e.g., flac OR mp3"
            value={filter}
          />
          <Form.Input
            label="Max Results"
            max={1_000}
            min={1}
            onChange={(event) =>
              setMaxResults(Number.parseInt(event.target.value, 10) || 100)
            }
            type="number"
            value={maxResults}
          />
          <Form.Group widths="equal">
            <Form.Field>
              <Checkbox
                checked={enabled}
                label="Enabled"
                onChange={(_, data) => setEnabled(data.checked)}
                toggle
              />
            </Form.Field>
            <Form.Field>
              <Checkbox
                checked={autoDownload}
                label="Auto-download matches"
                onChange={(_, data) => setAutoDownload(data.checked)}
                toggle
              />
            </Form.Field>
            <Form.Field>
              <Checkbox
                checked={includeAlbum}
                label="Include album"
                onChange={(_, data) => setIncludeAlbum(data.checked)}
                toggle
              />
            </Form.Field>
          </Form.Group>
        </Form>
      </Modal.Content>
      <Modal.Actions>
        <Popup
          content="Close the CSV importer without adding any wishlist searches."
          trigger={<Button onClick={onClose}>Cancel</Button>}
        />
        <Popup
          content="Create wishlist searches from the parsed CSV rows using the selected options."
          trigger={
            <Button
              loading={importing}
              onClick={handleImport}
              primary
            >
              Import
            </Button>
          }
        />
      </Modal.Actions>
    </Modal>
  );
};

const Wishlist = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalItem, setModalItem] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showBulkFilterModal, setShowBulkFilterModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [requestCopyStatus, setRequestCopyStatus] = useState('');
  const [bulkRunning, setBulkRunning] = useState(false);
  const [viewMode, setViewMode] = useState('table'); // 'table' or 'cards'
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [blockedUsers, setBlockedUsers] = useState(() => searchesAPI.getBlockedUsers());
  const [viewState, setViewState] = useState(loadWishlistViewState);
  const [page, setPage] = useState(1);
  const requestSummary = useMemo(
    () =>
      buildWishlistRequestSummary({
        items,
      }),
    [items],
  );
  const runnableRequests = useMemo(
    () => getRunnableWishlistRequests(items, { limit: 3 }),
    [items],
  );
  const updateViewState = useCallback((patch) => {
    setViewState((current) => {
      const next = { ...current, ...patch };
      saveWishlistViewState(next);
      return next;
    });
  }, []);

  const visibleItems = useMemo(() => {
    const query = viewState.query.trim().toLowerCase();
    const rows = items.filter((item) => {
      if (query && !`${item.searchText || ''} ${item.filter || ''}`.toLowerCase().includes(query)) {
        return false;
      }

      if (viewState.newOnly && getUnseenCount(item) === 0) {
        return false;
      }

      if (viewState.enabledOnly && !item.enabled) {
        return false;
      }

      if (viewState.autoOnly && !item.autoDownload) {
        return false;
      }

      if (viewState.hasResultsOnly && getVisibleHitCount(item) === 0) {
        return false;
      }

      return true;
    });

    rows.sort((a, b) => {
      switch (viewState.sort) {
        case 'az':
          return (a.searchText || '').localeCompare(b.searchText || '', undefined, { sensitivity: 'base' });
        case 'za':
          return (b.searchText || '').localeCompare(a.searchText || '', undefined, { sensitivity: 'base' });
        case 'last-searched':
          return new Date(b.lastSearchedAt || 0).getTime() - new Date(a.lastSearchedAt || 0).getTime();
        case 'new-first':
          return getUnseenCount(b) - getUnseenCount(a) || (a.searchText || '').localeCompare(b.searchText || '', undefined, { sensitivity: 'base' });
        case 'hits-desc':
          return getVisibleHitCount(b) - getVisibleHitCount(a) || (a.searchText || '').localeCompare(b.searchText || '', undefined, { sensitivity: 'base' });
        default:
          return new Date(b.createdAt || 0).getTime() - new Date(a.createdAt || 0).getTime();
      }
    });

    return rows;
  }, [items, viewState]);

  const pageCount = Math.max(1, Math.ceil(visibleItems.length / viewState.pageSize));
  const currentPage = Math.min(page, pageCount);
  const pageStart = (currentPage - 1) * viewState.pageSize;
  const pageItems = visibleItems.slice(pageStart, pageStart + viewState.pageSize);
  const pageEnd = Math.min(pageStart + pageItems.length, visibleItems.length);

  useEffect(() => {
    setPage(1);
  }, [
    viewState.autoOnly,
    viewState.enabledOnly,
    viewState.hasResultsOnly,
    viewState.newOnly,
    viewState.pageSize,
    viewState.query,
    viewState.sort,
  ]);

  const copyRequestReviewPacket = async () => {
    const packet = buildWishlistRequestReviewPacket({
      items,
    });
    const report = formatWishlistRequestReviewPacket(packet);

    if (!navigator.clipboard?.writeText) {
      setRequestCopyStatus('Clipboard unavailable; copy the request summary manually.');
      return;
    }

    try {
      await navigator.clipboard.writeText(report);
      setRequestCopyStatus('Wishlist request review copied.');
    } catch {
      setRequestCopyStatus('Unable to copy Wishlist request review.');
    }
  };

  const runEnabledSearches = async () => {
    setBulkRunning(true);
    const results = [];

    try {
      for (const item of runnableRequests) {
        try {
          const result = await wishlistAPI.runSearch(item.id);
          results.push({
            id: item.id,
            responseCount: result.responseCount ?? result.ResponseCount ?? 0,
            status: 'ran',
          });
        } catch (error) {
          results.push({
            error: error.message || 'Search failed',
            id: item.id,
            status: 'failed',
          });
        }
      }

      const ran = results.filter((result) => result.status === 'ran').length;
      const failed = results.filter((result) => result.status === 'failed').length;
      setRequestCopyStatus(
        `Ran ${ran} enabled Wishlist search${ran === 1 ? '' : 'es'}${
          failed ? `; ${failed} failed` : ''
        }. Downloads still require normal result selection and policy.`,
      );
      await loadItems();
    } finally {
      setBulkRunning(false);
    }
  };

  const [autoSearchEnabled, setAutoSearchEnabled] = useState(true);
  const [togglingAutoSearch, setTogglingAutoSearch] = useState(false);

  const loadOptions = useCallback(async () => {
    try {
      const opts = await optionsAPI.getCurrent();
      setAutoSearchEnabled(opts?.wishlist?.enabled ?? true);
    } catch {
      // leave optimistic default
    }
  }, []);

  const handleToggleAutoSearch = useCallback(async (_, { checked }) => {
    setTogglingAutoSearch(true);
    try {
      await optionsAPI.applyOverlay({ wishlist: { enabled: checked } });
      setAutoSearchEnabled(checked);
      toast.success(checked ? 'Auto-search enabled' : 'Auto-search paused');
    } catch (error) {
      toast.error(`Failed to update: ${error.message}`);
    } finally {
      setTogglingAutoSearch(false);
    }
  }, []);

  const loadItems = useCallback(async () => {
    try {
      const data = await wishlistAPI.getAll();
      setItems(Array.isArray(data) ? data : []);
    } catch (error) {
      toast.error(`Failed to load wishlist: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOptions();
    loadItems();
  }, [loadOptions, loadItems]);

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

  const handleAdd = () => {
    setModalItem(null);
    setShowModal(true);
  };

  const handleImportClick = () => {
    setShowImportModal(true);
  };

  const handleEdit = (item) => {
    setModalItem(item);
    setShowModal(true);
  };

  const handleSave = async (item) => {
    if (item.id) {
      await wishlistAPI.update(item.id, item);
      toast.success('Wishlist item updated');
    } else {
      await wishlistAPI.create(item);
      toast.success('Added to wishlist');
    }

    await loadItems();
  };

  const handleDelete = async (id) => {
    try {
      await wishlistAPI.remove(id);
      toast.success('Wishlist item deleted');
      await loadItems();
    } catch (error) {
      toast.error(`Failed to delete: ${error.message}`);
    }
  };

  const handleRunSearch = async (id) => {
    const result = await wishlistAPI.runSearch(id);
    await loadItems();
    return result;
  };

  const handleMarkViewed = async (id) => {
    try {
      await wishlistAPI.markViewed(id);
      await loadItems();
    } catch (error) {
      // Silently ignore mark-viewed failures; they don't block UX
    }
  };

  // Bulk operations
  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedIds(new Set(pageItems.map((i) => i.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleSelectItem = (id, checked) => {
    const next = new Set(selectedIds);
    if (checked) {
      next.add(id);
    } else {
      next.delete(id);
    }
    setSelectedIds(next);
  };

  const handleBulkEnable = async () => {
    for (const id of selectedIds) {
      await wishlistAPI.update(id, { ...items.find((i) => i.id === id), enabled: true });
    }
    toast.success(`Enabled ${selectedIds.size} item(s)`);
    setSelectedIds(new Set());
    await loadItems();
  };

  const handleBulkDisable = async () => {
    for (const id of selectedIds) {
      await wishlistAPI.update(id, { ...items.find((i) => i.id === id), enabled: false });
    }
    toast.success(`Disabled ${selectedIds.size} item(s)`);
    setSelectedIds(new Set());
    await loadItems();
  };

  const handleBulkFilterSave = async (filter) => {
    const ids = [...selectedIds];
    const result = await wishlistAPI.updateFilters(ids, filter);
    const updatedCount = result?.updatedCount ?? result?.UpdatedCount ?? ids.length;
    toast.success(`Updated filters for ${updatedCount} item(s)`);
    setSelectedIds(new Set());
    await loadItems();
  };

  const handleBulkDelete = async () => {
    for (const id of selectedIds) {
      await wishlistAPI.remove(id);
    }
    toast.success(`Deleted ${selectedIds.size} item(s)`);
    setSelectedIds(new Set());
    await loadItems();
  };

  const handleImport = async (request) => {
    const result = await wishlistAPI.importCsv(request);
    toast.success(
      `Imported ${result.createdCount} searches (${result.duplicateCount} duplicates, ${result.skippedCount} skipped)`,
    );
    await loadItems();
  };

  return (
    <div className="wishlist-container">
      <Segment
        className="wishlist-header"
        clearing
      >
        <Header
          as="h2"
          floated="left"
        >
          <Icon name="star" />
          <Header.Content>
            Wishlist
            <Header.Subheader>
              Saved searches that run automatically
            </Header.Subheader>
          </Header.Content>
        </Header>
        <Popup
          content={autoSearchEnabled
            ? 'Auto-search is on — enabled items are searched automatically in the background.'
            : 'Auto-search is paused — items will not be searched until you turn it back on.'}
          trigger={
            <Checkbox
              checked={autoSearchEnabled}
              className="wishlist-autosearch-toggle"
              disabled={togglingAutoSearch}
              floated="right"
              label={autoSearchEnabled ? 'Auto-search on' : 'Auto-search off'}
              onChange={handleToggleAutoSearch}
              toggle
            />
          }
        />
        <Popup
          content="Add one saved search to the wishlist. Enabled wishlist entries run later using the normal conservative scheduler."
          trigger={
            <Button
              floated="right"
              icon
              labelPosition="left"
              onClick={handleAdd}
              primary
            >
              <Icon name="plus" />
              Add Search
            </Button>
          }
        />
        <Popup
          content="Import a playlist CSV, such as a TuneMyMusic export, into wishlist searches without starting a large search burst immediately."
          trigger={
            <Button
              floated="right"
              icon
              labelPosition="left"
              onClick={handleImportClick}
            >
              <Icon name="file alternate outline" />
              Import CSV
            </Button>
          }
        />
      </Segment>

      {!loading && (
        <Segment className="wishlist-request-summary">
          <div className="wishlist-request-summary-header">
            <Header as="h3">
              <Icon name="clipboard check" />
              Request Portal Summary
              <Header.Subheader>
                Operator view of wanted music before acquisition jobs are wired.
              </Header.Subheader>
            </Header>
            <Popup
              content="Copy the current Wishlist request review packet. This does not start searches, peer browsing, downloads, or automation."
              position="top center"
              trigger={
                <Button
                  aria-label="Copy Wishlist request review"
                  onClick={copyRequestReviewPacket}
                  size="small"
                >
                  <Icon name="copy" />
                  Copy Review
                </Button>
              }
            />
            <Popup
              content="Run up to three enabled Wishlist searches now through the backend. This starts search jobs only; downloads still require the normal result selection and policy."
              position="top center"
              trigger={
                <Button
                  aria-label="Run enabled Wishlist searches"
                  disabled={runnableRequests.length === 0}
                  loading={bulkRunning}
                  onClick={runEnabledSearches}
                  primary
                  size="small"
                >
                  <Icon name="play" />
                  Run Enabled
                </Button>
              }
            />
            <Popup
              content="Clear all unseen results badges across your wishlist. This marks every item as viewed."
              position="top center"
              trigger={
                <Button
                  aria-label="Mark all wishlist items as viewed"
                  icon="checkmark"
                  onClick={async () => {
                    try {
                      await wishlistAPI.markAllViewed();
                      await loadItems();
                      toast.success('All wishlist items marked as viewed');
                    } catch (error) {
                      toast.error(`Failed: ${error.message}`);
                    }
                  }}
                  size="small"
                >
                  Mark All Viewed
                </Button>
              }
            />
          </div>
          <div className="wishlist-request-summary-grid">
            {/* Plain counts get a neutral pill; color is reserved for the two
                pills below that actually report a state worth noticing. */}
            <Label basic>
              Requests
              <Label.Detail>{requestSummary.total}</Label.Detail>
            </Label>
            <Label basic>
              Enabled
              <Label.Detail>{requestSummary.enabled}</Label.Detail>
            </Label>
            <Label basic>
              Automatic
              <Label.Detail>{requestSummary.automatic}</Label.Detail>
            </Label>
            <Label color={requestSummary.reviewCount > 0 ? 'yellow' : 'grey'}>
              Needs Review
              <Label.Detail>{requestSummary.reviewCount}</Label.Detail>
            </Label>
            <Label color={requestSummary.quotaStatus === 'Within quota' ? 'green' : 'orange'}>
              {requestSummary.quotaStatus}
              <Label.Detail>{requestSummary.quotaRemaining} left</Label.Detail>
            </Label>
          </div>
          {requestCopyStatus && (
            <Label basic>
              {requestCopyStatus}
            </Label>
          )}
        </Segment>
      )}

      {loading ? (
        <Segment
          loading
          placeholder
        />
      ) : items.length === 0 ? (
        <Segment
          inverted
          placeholder
        >
          <Header
            icon
            inverted
          >
            <Icon name="star outline" />
            No wishlist items yet
          </Header>
          <p>
            Add searches to your wishlist and they&apos;ll run automatically.
          </p>
          <TooltipButton
            onClick={handleAdd}
            primary
            tooltip="Add a search to your wishlist so you can track it manually or automate it with the options you choose."
          >
            Add Your First Search
          </TooltipButton>
        </Segment>
      ) : (
        <>
          {selectedIds.size > 0 && (
            <Segment secondary compact style={{ marginBottom: '1em' }}>
              <span style={{ marginRight: '1em' }}>
                {selectedIds.size} item(s) selected
              </span>
              <Popup
                content="Apply one filter to every selected wishlist item, or clear their filters."
                trigger={
                  <Button
                    aria-label="Edit filters for selected wishlist items"
                    compact
                    icon="filter"
                    onClick={() => setShowBulkFilterModal(true)}
                    size="small"
                  />
                }
              />
              <Popup
                content="Enable the selected wishlist searches so scheduled runs can check them again."
                trigger={
                  <Button
                    aria-label="Enable selected wishlist searches"
                    compact
                    icon="play"
                    onClick={handleBulkEnable}
                    size="small"
                  />
                }
              />
              <Popup
                content="Pause scheduled runs for all selected wishlist searches."
                trigger={
                  <Button
                    aria-label="Pause selected wishlist searches"
                    compact
                    icon="pause"
                    onClick={handleBulkDisable}
                    size="small"
                  />
                }
              />
              <Popup
                content="Delete selected wishlist searches after confirmation when they are no longer needed."
                trigger={
                  <Button
                    aria-label="Delete selected wishlist searches"
                    compact
                    color="red"
                    icon="trash"
                    onClick={handleBulkDelete}
                    size="small"
                  />
                }
              />
              <TooltipButton
                compact
                onClick={() => setSelectedIds(new Set())}
                size="small"
                tooltip="Clear the selection so bulk actions no longer affect these wishlist items."
              >
                Clear
              </TooltipButton>
            </Segment>
          )}
          <div style={{ marginBottom: '0.75em', display: 'flex', gap: '0.5em', alignItems: 'center', flexWrap: 'wrap' }}>
            <Button.Group size="mini">
              <Popup
                content="Show wishlist as a table with columns"
                trigger={
                  <Button
                    active={viewMode === 'table'}
                    aria-label="Show wishlist as a table"
                    icon="table"
                    onClick={() => setViewMode('table')}
                  />
                }
              />
              <Popup
                content="Show wishlist as expandable cards with inline results"
                trigger={
                  <Button
                    active={viewMode === 'cards'}
                    aria-label="Show wishlist as cards"
                    icon="th"
                    onClick={() => setViewMode('cards')}
                  />
                }
              />
            </Button.Group>
            <Input
              icon="search"
              onChange={(event) => updateViewState({ query: event.target.value })}
              placeholder="Filter wishlist..."
              size="mini"
              value={viewState.query}
            />
            <Dropdown
              compact
              onChange={(_, { value }) => updateViewState({ sort: value })}
              options={SORT_OPTIONS}
              selection
              size="mini"
              value={viewState.sort}
            />
            <Dropdown
              compact
              onChange={(_, { value }) => updateViewState({ pageSize: value })}
              options={PAGE_SIZE_OPTIONS.map((value) => ({
                key: value,
                text: `${value} per page`,
                value,
              }))}
              selection
              size="mini"
              value={viewState.pageSize}
            />
            <Checkbox
              checked={viewState.newOnly}
              label="New results"
              onChange={(_, { checked }) => updateViewState({ newOnly: checked })}
            />
            <Checkbox
              checked={viewState.enabledOnly}
              label="Enabled"
              onChange={(_, { checked }) => updateViewState({ enabledOnly: checked })}
            />
            <Checkbox
              checked={viewState.autoOnly}
              label="Auto"
              onChange={(_, { checked }) => updateViewState({ autoOnly: checked })}
            />
            <Checkbox
              checked={viewState.hasResultsOnly}
              label="Has results"
              onChange={(_, { checked }) => updateViewState({ hasResultsOnly: checked })}
            />
            <Label basic>
              Showing
              <Label.Detail>
                {visibleItems.length === 0
                  ? `0/${items.length}`
                  : `${pageStart + 1}-${pageEnd}/${visibleItems.length} of ${items.length}`}
              </Label.Detail>
            </Label>
            {pageCount > 1 && (
              <Button.Group size="mini">
                <Popup
                  content="Go to the previous page of wishlist items."
                  position="top center"
                  trigger={
                    <Button
                      aria-label="Previous wishlist page"
                      disabled={currentPage <= 1}
                      icon="angle left"
                      onClick={() => setPage((value) => Math.max(1, value - 1))}
                    />
                  }
                />
                <Popup
                  content="Shows your current wishlist page. Use the arrow buttons to move between pages."
                  position="top center"
                  trigger={(
                    <span
                      aria-label={`Page ${currentPage} of ${pageCount}`}
                      className="ui basic button"
                      role="status"
                      tabIndex={0}
                    >
                      {currentPage}/{pageCount}
                    </span>
                  )}
                />
                <Popup
                  content="Go to the next page of wishlist items."
                  position="top center"
                  trigger={
                    <Button
                      aria-label="Next wishlist page"
                      disabled={currentPage >= pageCount}
                      icon="angle right"
                      onClick={() => setPage((value) => Math.min(pageCount, value + 1))}
                    />
                  }
                />
              </Button.Group>
            )}
          </div>
          {viewMode === 'table' ? (
            <Table
              celled
              striped
            >
              <Table.Header>
                <Table.Row>
                  <Table.HeaderCell width={1}>
                    <Popup
                      content="Select all items on this page for bulk actions"
                      position="top center"
                      trigger={
                        <Checkbox
                          aria-label="Select all wishlist items on this page for bulk actions"
                          checked={pageItems.length > 0 && pageItems.every((item) => selectedIds.has(item.id))}
                          indeterminate={pageItems.some((item) => selectedIds.has(item.id)) && !pageItems.every((item) => selectedIds.has(item.id))}
                          onChange={(_, { checked }) => handleSelectAll(checked)}
                        />
                      }
                    />
                  </Table.HeaderCell>
                  <Table.HeaderCell>Search</Table.HeaderCell>
                  <Table.HeaderCell
                    textAlign="center"
                    width={1}
                  >
                    Auto
                  </Table.HeaderCell>
                  <Table.HeaderCell width={3}>Last Run</Table.HeaderCell>
                  <Table.HeaderCell
                    textAlign="center"
                    width={1}
                  >
                    <Popup
                      content="Hits matched by the search. Locked hits are shown separately because the uploader has restricted access — they aren't directly downloadable."
                      position="top center"
                      trigger={<span>Hits</span>}
                    />
                  </Table.HeaderCell>
                  <Table.HeaderCell
                    textAlign="center"
                    width={1}
                  >
                    Runs
                  </Table.HeaderCell>
                  <Table.HeaderCell width={2}>Request State</Table.HeaderCell>
                  <Table.HeaderCell width={3}>Actions</Table.HeaderCell>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {pageItems.map((item) => (
                  <WishlistItemRow
                    item={item}
                    key={item.id}
                    onDelete={handleDelete}
                    onEdit={handleEdit}
                    onMarkViewed={handleMarkViewed}
                    onRunSearch={handleRunSearch}
                    selected={selectedIds.has(item.id)}
                    onSelect={handleSelectItem}
                    blockedUsers={blockedUsers}
                  />
                ))}
              </Table.Body>
            </Table>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75em' }}>
              {pageItems.map((item) => (
                <WishlistItemCard
                  item={item}
                  key={item.id}
                  onDelete={handleDelete}
                  onEdit={handleEdit}
                  onMarkViewed={handleMarkViewed}
                  onRunSearch={handleRunSearch}
                  selected={selectedIds.has(item.id)}
                  onSelect={handleSelectItem}
                  blockedUsers={blockedUsers}
                />
              ))}
            </div>
          )}
        </>
      )}

      {showModal && (
        <WishlistModal
          item={modalItem}
          onClose={() => setShowModal(false)}
          onSave={handleSave}
        />
      )}

      {showBulkFilterModal && (
        <BulkFilterModal
          count={selectedIds.size}
          onClose={() => setShowBulkFilterModal(false)}
          onSave={handleBulkFilterSave}
        />
      )}

      {showImportModal && (
        <CsvImportModal
          onClose={() => setShowImportModal(false)}
          onImport={handleImport}
        />
      )}
    </div>
  );
};

export default Wishlist;
