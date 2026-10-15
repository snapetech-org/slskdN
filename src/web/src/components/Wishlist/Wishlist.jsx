import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';


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
  if (!dateString) return interfaceText('Never');
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return interfaceText('Never');
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
  useInterfaceLanguage();
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
      toast.success(interfaceText("Search completed with {responseCount} results", { "responseCount": (result.responseCount) }));
    } catch (error) {
      toast.error(interfaceText("Search failed: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
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
        toast.error(interfaceText("Failed to load searches: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
      } finally {
        setLoadingSearches(false);
      }
    }
  };

  const handleMarkViewedClick = async () => {
    await onMarkViewed(item.id);
    toast.info(interfaceText("Marked \"{searchText}\" as viewed", { "searchText": (item.searchText) }));
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
      toast.error(interfaceText("Failed to load results: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
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
            content={interfaceText("Select for bulk actions")}
            position="top center"
            trigger={
              <Checkbox
                aria-label={interfaceText("Select {searchText} for bulk actions", { "searchText": (item.searchText) })}
                checked={selected}
                onChange={(_, { checked }) => onSelect(item.id, checked)}
               {...interfaceTextProps("Select {searchText} for bulk actions")}/>
            }
           {...interfaceTextProps("Select for bulk actions")}/>
        </Table.Cell>
        <Table.Cell>
          <Icon
            color={item.enabled ? 'green' : 'grey'}
            name={item.enabled ? 'check circle' : 'circle outline'}
            style={{ marginRight: '0.5em' }}
          />
          <strong>{item.searchText}</strong>
          {item.filter && (
            <div className="wishlist-filter"><LocalizedText source={"Filter:"} />{" "}{item.filter}</div>
          )}
        </Table.Cell>
        <Table.Cell textAlign="center">
          <Popup
            content={interfaceText("Auto-download best matches")}
            trigger={
              <Icon
                color={item.autoDownload ? 'green' : 'grey'}
                name={item.autoDownload ? 'download' : 'download'}
              />
            }
           {...interfaceTextProps("Auto-download best matches")}/>
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
                    {interfaceText("(+{lastHiddenLockedHitCount} locked)", { "lastHiddenLockedHitCount": (item.lastHiddenLockedHitCount) })}
                  </span>
                )}
                {(item.lastBlockedHitCount ?? 0) > 0 && (
                  <span className="wishlist-blocked-count" style={{ color: '#999', marginLeft: '0.25em' }}>
                    {interfaceText("(+{lastBlockedHitCount} blocked)", { "lastBlockedHitCount": (item.lastBlockedHitCount) })}
                  </span>
                )}
              </span>
            }
          />
          {unseenCount > 0 && (
            <Popup
              content={interfaceText("{unseenCount} new result(s) since you last viewed this item", { "unseenCount": (unseenCount) })}
              trigger={
                <Label
                  color="red"
                  size="mini"
                  style={{ marginLeft: '0.5em' }}
                >
                  {unseenCount} <LocalizedText source={"new"} /></Label>
              }
             {...interfaceTextProps("{unseenCount} new result(s) since you last viewed this item")}/>
          )}
        </Table.Cell>
        <Table.Cell textAlign="center">{item.totalSearchCount}</Table.Cell>
        <Table.Cell>
          <Popup
            content={<LocalizedText source={requestState.summary} />}
            position="top center"
            trigger={
              <Label color={requestState.color}>
                <LocalizedText source={requestState.label} />
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
                    aria-label={interfaceText("View latest search results for {searchText}", { "searchText": (item.searchText) })}
                    compact
                    icon="search"
                    size="tiny"
                    title={interfaceText("View last search results")}
                   {...interfaceTextProps("View latest search results for {searchText}")}/>
                }
              />
            </Link>
          )}
          {unseenCount > 0 && (
            <Popup
              content={interfaceText("Clear this item's new-results badge without opening its search history.")}
              position="top center"
              trigger={
                  <Button
                    aria-label={interfaceText("Mark {searchText} results as viewed", { "searchText": (item.searchText) })}
                    compact
                    icon="check"
                  onClick={handleMarkViewedClick}
                  size="tiny"
                  title={interfaceText("Mark viewed")}
                 {...interfaceTextProps("Mark {searchText} results as viewed")}/>
              }
             {...interfaceTextProps("Clear this item's new-results badge without opening its search history.")}/>
          )}
          <TooltipButton
            aria-label={interfaceText(showSearches
              ? 'Hide {searchText} search history'
              : 'Show {searchText} search history', {
              searchText: item.searchText,
            })}
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
            aria-label={interfaceText("Run {searchText} wishlist search now", { "searchText": (item.searchText) })}
            compact
            icon="play"
            loading={running}
            onClick={handleRunSearch}
            primary
            size="tiny"
            tooltip="Manually search Soulseek for current matches. This contacts peers now rather than waiting for the next scheduled run."
           {...interfaceTextProps("Run {searchText} wishlist search now")}/>
          <TooltipButton
            aria-label={interfaceText("Edit {searchText} wishlist settings", { "searchText": (item.searchText) })}
            compact
            icon="edit"
            onClick={() => onEdit(item)}
            size="tiny"
            tooltip="Change this item’s search text, filters, result limits, and automation settings."
           {...interfaceTextProps("Edit {searchText} wishlist settings")}/>
          <TooltipButton
            aria-label={interfaceText("Delete {searchText} from Wishlist", { "searchText": (item.searchText) })}
            color="red"
            compact
            icon="trash"
            onClick={() => setConfirmDelete(true)}
            size="tiny"
            tooltip="Remove this wishlist entry after confirmation when you no longer want its search tracked."
           {...interfaceTextProps("Delete {searchText} from Wishlist")}/>
          <Confirm
            cancelButton={(
              <TooltipButton tooltip="Keep this wishlist item and return to the list.">
                <LocalizedText source={"Cancel"} /></TooltipButton>
            )}
            confirmButton={(
              <TooltipButton
                color="red"
                tooltip="Remove this wishlist item and its saved search settings."
              >
                <LocalizedText source={"Delete"} /></TooltipButton>
            )}
            content={interfaceText("Delete wishlist item \"{searchText}\"?", { "searchText": (item.searchText) })}
            header={interfaceText("Confirm Delete")}
            onCancel={() => setConfirmDelete(false)}
            onConfirm={() => {
              setConfirmDelete(false);
              onDelete(item.id);
            }}
            open={confirmDelete}
            size="mini"
           {...interfaceTextProps("Delete wishlist item \"{searchText}\"?")}/>
        </Table.Cell>
      </Table.Row>
      {showSearches && (
        <Table.Row>
          <Table.Cell colSpan="8" style={{ background: 'rgba(0,0,0,0.03)' }}>
            {loadingSearches ? (
              <Icon name="spinner" loading />
            ) : relatedSearches.length === 0 ? (
              <span style={{ color: '#999', fontStyle: 'italic' }}>
                <LocalizedText source={"No linked search history for this item yet."} />{item.lastSearchId && (
                  <>
                    {' '}
                    <Link
                      to={getSearchLink(item)}
                    >
                      <LocalizedText source={"Open latest search result."} /></Link>
                  </>
                )}
              </span>
            ) : (
              <>
                <Table compact size="small" basic="very">
                  <Table.Header>
                    <Table.Row>
                      <Table.HeaderCell><LocalizedText source={"Search"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Source"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Responses"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Files"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Started"} /></Table.HeaderCell>
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
                            {s.source || interfaceText('Manual')}
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
                              content={interfaceText(item.filter
                                ? 'View full search page with this wishlist filter already applied.'
                                : 'View full search page.')}
                              position="top center"
                              trigger={
                                <Button
                                  aria-label={interfaceText("Open the full search for {searchText}", { "searchText": (item.searchText) })}
                                  compact
                                  icon="external"
                                  size="mini"
                                 {...interfaceTextProps("Open the full search for {searchText}")}/>
                              }
                            />
                          </Link>
                          <Popup
                            content={interfaceText(expandedSearchId === s.id ? 'Hide results' : 'Show results inline')}
                            position="top center"
                            trigger={
                              <Button
                                aria-label={interfaceText(expandedSearchId === s.id
                                  ? 'Hide {searchText} results inline'
                                  : 'Show {searchText} results inline', {
                                  searchText: item.searchText,
                                })}
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
                      <span style={{ color: '#999', fontStyle: 'italic' }}><LocalizedText source={"No results for this search."} /></span>
                    ) : (
                      <>
                        <Header as="h5" style={{ marginBottom: '0.5em' }}>
                          {visibleExpandedSearchResults.length} <LocalizedText source={"result(s)"} /></Header>
                        <Table compact size="small" basic="very" striped>
                          <Table.Header>
                            <Table.Row>
                              <Table.HeaderCell><LocalizedText source={"Username"} /></Table.HeaderCell>
                              <Table.HeaderCell><LocalizedText source={"Directory"} /></Table.HeaderCell>
                              <Table.HeaderCell><LocalizedText source={"Files"} /></Table.HeaderCell>
                              <Table.HeaderCell><LocalizedText source={"Size"} /></Table.HeaderCell>
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
                            <LocalizedText source={"Showing the first 20 of {count} results."} values={{ count: visibleExpandedSearchResults.length }} />
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
  useInterfaceLanguage();
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
      toast.success(interfaceText("Search completed with {responseCount} results", { "responseCount": (result.responseCount) }));
    } catch (error) {
      toast.error(interfaceText("Search failed: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
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
        toast.error(interfaceText("Failed to load searches: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
      } finally {
        setLoadingSearches(false);
      }
    }
  };

  const handleMarkViewedClick = async () => {
    await onMarkViewed(item.id);
    toast.info(interfaceText("Marked \"{searchText}\" as viewed", { "searchText": (item.searchText) }));
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
      toast.error(interfaceText("Failed to load results: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
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
            aria-label={interfaceText("Select {searchText} for bulk actions", { "searchText": (item.searchText) })}
            checked={selected}
            onChange={(_, { checked }) => onSelect(item.id, checked)}
            style={{ marginTop: '0.3em' }}
           {...interfaceTextProps("Select {searchText} for bulk actions")}/>
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
                  content={interfaceText("{unseenCount} new result(s) since you last viewed this item", { "unseenCount": (unseenCount) })}
                  trigger={
                    <Label color="red" size="mini">
                      {unseenCount} <LocalizedText source={"new"} /></Label>
                  }
                 {...interfaceTextProps("{unseenCount} new result(s) since you last viewed this item")}/>
              )}
              <Popup
                content={<LocalizedText source={requestState.summary} />}
                position="top center"
                trigger={
                  <Label color={requestState.color} size="mini">
                    <LocalizedText source={requestState.label} />
                  </Label>
                }
              />
            </div>
            <div style={{ display: 'flex', gap: '1em', fontSize: '0.85em', color: '#888', flexWrap: 'wrap' }}>
              <span><LocalizedText source={"Last run:"} />{" "}{formatDate(item.lastSearchedAt)}</span>
              <span>
                <LocalizedText source={"Hits:"} />{" "}{getVisibleHitCount(item)}
                {(item.lastHiddenLockedHitCount ?? 0) > 0 && (
                  <Popup
                    content={interfaceText("Files matched but the uploader has them locked (not downloadable without sharing access).")}
                    position="top center"
                    trigger={
                      <span style={{ color: '#999', marginLeft: '0.25em' }}>
                        {interfaceText("(+{lastHiddenLockedHitCount} locked)", { "lastHiddenLockedHitCount": (item.lastHiddenLockedHitCount) })}
                      </span>
                    }
                   {...interfaceTextProps("Files matched but the uploader has them locked (not downloadable without sharing access).")}/>
                )}
                {(item.lastBlockedHitCount ?? 0) > 0 && (
                  <Popup
                    content={interfaceText("Matching files from blocked users are excluded from Wishlist hits and automatic downloads.")}
                    position="top center"
                    trigger={
                      <span style={{ color: '#999', marginLeft: '0.25em' }}>
                        {interfaceText("(+{lastBlockedHitCount} blocked)", { "lastBlockedHitCount": (item.lastBlockedHitCount) })}
                      </span>
                    }
                   {...interfaceTextProps("Matching files from blocked users are excluded from Wishlist hits and automatic downloads.")}/>
                )}
              </span>
              <span><LocalizedText source={"Runs:"} />{" "}{item.totalSearchCount}</span>
              <span>
                <LocalizedText source={"Auto-download:"} />{' '}
                <Icon name={item.autoDownload ? 'check' : 'close'} color={item.autoDownload ? 'green' : 'grey'} />
              </span>
              {item.autoDownload && item.maxDownloads && (
                <span>
                  <LocalizedText source={"Downloads:"} />{" "}{item.totalDownloadCount}/{item.maxDownloads}
                </span>
              )}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.25em' }}>
            <Popup
              content={interfaceText(expanded
                ? 'Hide this item’s linked searches and result details.'
                : 'Show this item’s linked searches and past results inline.')}
              position="top center"
              trigger={
                <Button
                  aria-label={interfaceText(expanded
                    ? 'Hide {searchText} search history'
                    : 'Show {searchText} search history', {
                    searchText: item.searchText,
                  })}
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
                      aria-label={interfaceText("View latest search results for {searchText}", { "searchText": (item.searchText) })}
                      compact
                      icon="search"
                      size="mini"
                     {...interfaceTextProps("View latest search results for {searchText}")}/>
                  }
                />
              </Link>
            )}
            {unseenCount > 0 && (
              <Popup
                content={interfaceText("Clear this item's new-results badge without opening its search history.")}
                position="top center"
                trigger={
                  <Button
                    aria-label={interfaceText("Mark {searchText} results as viewed", { "searchText": (item.searchText) })}
                    compact
                    icon="check"
                    onClick={handleMarkViewedClick}
                    size="mini"
                   {...interfaceTextProps("Mark {searchText} results as viewed")}/>
                }
               {...interfaceTextProps("Clear this item's new-results badge without opening its search history.")}/>
            )}
            <Popup
              content={interfaceText("Manually search Soulseek for current matches. This contacts peers now rather than waiting for the next scheduled run.")}
              position="top center"
              trigger={
                <Button
                  aria-label={interfaceText("Run {searchText} wishlist search now", { "searchText": (item.searchText) })}
                  compact
                  icon="play"
                  loading={running}
                  onClick={handleRunSearch}
                  primary
                  size="mini"
                 {...interfaceTextProps("Run {searchText} wishlist search now")}/>
              }
             {...interfaceTextProps("Manually search Soulseek for current matches. This contacts peers now rather than waiting for the next scheduled run.")}/>
            <Popup
              content={interfaceText("Change this item’s search text, filters, result limits, and automation settings.")}
              position="top center"
              trigger={
                <Button
                  aria-label={interfaceText("Edit {searchText} wishlist settings", { "searchText": (item.searchText) })}
                  compact
                  icon="edit"
                  onClick={() => onEdit(item)}
                  size="mini"
                 {...interfaceTextProps("Edit {searchText} wishlist settings")}/>
              }
             {...interfaceTextProps("Change this item’s search text, filters, result limits, and automation settings.")}/>
            <Popup
              content={interfaceText("Remove this wishlist entry after confirmation when you no longer want its search tracked.")}
              position="top center"
              trigger={
                <Button
                  aria-label={interfaceText("Delete {searchText} from Wishlist", { "searchText": (item.searchText) })}
                  color="red"
                  compact
                  icon="trash"
                  onClick={() => setConfirmDelete(true)}
                  size="mini"
                 {...interfaceTextProps("Delete {searchText} from Wishlist")}/>
              }
             {...interfaceTextProps("Remove this wishlist entry after confirmation when you no longer want its search tracked.")}/>
          </div>
        </div>

        {expanded && (
          <div style={{ marginTop: '1em', paddingTop: '1em', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
            {loadingSearches ? (
              <Icon name="spinner" loading />
            ) : relatedSearches.length === 0 ? (
              <span style={{ color: '#999', fontStyle: 'italic' }}>
                <LocalizedText source={"No linked search history for this item yet."} />{item.lastSearchId && (
                  <>
                    {' '}
                    <Link
                      to={getSearchLink(item)}
                    >
                      <LocalizedText source={"Open latest search result."} /></Link>
                  </>
                )}
              </span>
            ) : (
              <>
                <Table compact size="small" basic="very">
                  <Table.Header>
                    <Table.Row>
                      <Table.HeaderCell><LocalizedText source={"Search"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Source"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Responses"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Started"} /></Table.HeaderCell>
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
                            {s.source || interfaceText('Manual')}
                          </Label>
                        </Table.Cell>
                        <Table.Cell>{s.responseCount}</Table.Cell>
                        <Table.Cell>{formatDate(s.startedAt)}</Table.Cell>
                        <Table.Cell>
                          <Link
                            to={getSearchLink(item, s.id)}
                          >
                            <Popup
                              content={interfaceText(item.filter
                                ? 'View full search page with this wishlist filter already applied.'
                                : 'View full search page.')}
                              position="top center"
                              trigger={
                                <Button
                                  aria-label={interfaceText("Open the full search for {searchText}", { "searchText": (item.searchText) })}
                                  compact
                                  icon="external"
                                  size="mini"
                                 {...interfaceTextProps("Open the full search for {searchText}")}/>
                              }
                            />
                          </Link>
                          <Popup
                            content={interfaceText(expandedSearchId === s.id ? 'Hide results' : 'Show results inline')}
                            position="top center"
                            trigger={
                              <Button
                                aria-label={interfaceText(expandedSearchId === s.id
                                  ? 'Hide {searchText} results inline'
                                  : 'Show {searchText} results inline', {
                                  searchText: item.searchText,
                                })}
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
                      <span style={{ color: '#999', fontStyle: 'italic' }}><LocalizedText source={"No results for this search."} /></span>
                    ) : (
                      <>
                        <Header as="h5" style={{ marginBottom: '0.5em' }}>
                          {visibleExpandedSearchResults.length} <LocalizedText source={"result(s)"} /></Header>
                        <Table compact size="small" basic="very" striped>
                          <Table.Header>
                            <Table.Row>
                              <Table.HeaderCell><LocalizedText source={"Username"} /></Table.HeaderCell>
                              <Table.HeaderCell><LocalizedText source={"Directory"} /></Table.HeaderCell>
                              <Table.HeaderCell><LocalizedText source={"Files"} /></Table.HeaderCell>
                              <Table.HeaderCell><LocalizedText source={"Size"} /></Table.HeaderCell>
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
                            <LocalizedText source={"Showing the first 20 of {count} results."} values={{ count: visibleExpandedSearchResults.length }} />
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
            <LocalizedText source={"Cancel"} /></TooltipButton>
        )}
        confirmButton={(
          <TooltipButton
            color="red"
            tooltip="Remove this wishlist item and its saved search settings."
          >
            <LocalizedText source={"Delete"} /></TooltipButton>
        )}
        content={interfaceText("Delete wishlist item \"{searchText}\"?", { "searchText": (item.searchText) })}
        header={interfaceText("Confirm Delete")}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => {
          setConfirmDelete(false);
          onDelete(item.id);
        }}
        open={confirmDelete}
        size="mini"
       {...interfaceTextProps("Delete wishlist item \"{searchText}\"?")}/>
    </>
  );
};

const FILTER_PRESETS = [
  { get label() { return interfaceText("FLAC"); }, value: 'flac' },
  { get label() { return interfaceText("MP3"); }, value: 'mp3' },
  { get label() { return interfaceText("MP3 320+"); }, value: 'mp3 minbr:320' },
  { get label() { return interfaceText("FLAC + MP3"); }, value: 'flac OR mp3' },
  { get label() { return interfaceText("FLAC + ALAC"); }, value: 'flac OR alac' },
  { get label() { return interfaceText("Lossless"); }, value: 'flac OR alac OR wav OR ape' },
  { get label() { return interfaceText("Any"); }, value: '' },
];

const WISHLIST_VIEW_KEY = 'slskdn-wishlist-view-state';
const PAGE_SIZE_OPTIONS = [50, 100, 250, 500];

const SORT_OPTIONS = [
  { key: 'created-desc', get text() { return interfaceText("Newest added"); }, value: 'created-desc' },
  { key: 'az', text: 'A-Z', value: 'az' },
  { key: 'za', text: 'Z-A', value: 'za' },
  { key: 'last-searched', get text() { return interfaceText("Last searched"); }, value: 'last-searched' },
  { key: 'new-first', get text() { return interfaceText("New results first"); }, value: 'new-first' },
  { key: 'hits-desc', get text() { return interfaceText("Most hits"); }, value: 'hits-desc' },
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
    return interfaceText('Filter may contain words, quoted phrases, extensions, minbr:/minbitrate: directives, exclusions prefixed with -, and OR');
  }
  if ((filter.match(/"/g) || []).length % 2 !== 0) return interfaceText('Quoted filter phrases must have a closing quote');
  return null;
};

const FilterPresetButtons = ({ filter, onChange }) => (
  <div style={{ marginTop: '0.5em' }}>
    {FILTER_PRESETS.map((preset) => (
      <Popup
        key={preset.value}
        content={
          preset.value
            ? interfaceText("Filter to {format} files", { format: interfaceText(preset.label) })
            : interfaceText("Accept any file format")
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
            {interfaceText(preset.label)}
          </Button>
        }
      />
    ))}
  </div>
);

const WishlistModal = ({ item, onClose, onSave }) => {
  useInterfaceLanguage();
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
        if (!cancelled) toast.error(interfaceText("Failed to load ignored wishlist folders"));
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
      toast.info(interfaceText("Restored {directory} from {username}", { "directory": (rule.directory), "username": (rule.username) }));
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t: interfaceText }));
    }
  };

  const handleFilterChange = (value) => {
    setFilter(value);
    setFilterError(validateFilter(value));
  };

  const handleSave = async () => {
    if (!searchText.trim()) {
      toast.error(interfaceText("Search text is required"));
      return;
    }
    if (filterError) {
      toast.error(interfaceText("Please fix the filter error before saving"));
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
      toast.error(interfaceText("Failed to save: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
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
        {isEdit ? <LocalizedText source={"Edit Wishlist Item"} /> : <LocalizedText source={"Add to Wishlist"} />}
      </Modal.Header>
      <Modal.Content>
        <Form>
          <Form.Input
            label={interfaceText("Search Text")}
            onChange={(event) => setSearchText(event.target.value)}
            placeholder={interfaceText("Enter search terms...")}
            required
            value={searchText}
           {...interfaceTextProps("Search Text")}/>
          <Form.Field>
            <label><LocalizedText source={"Filter (optional)"} /></label>
            <Popup
              content={interfaceText('Only accept matching filenames or extensions. Use -word to exclude a word or -"exact phrase" to exclude a specific album or folder name.')}
              position="top center"
              trigger={
                <Form.Input
                  error={!!filterError}
                  onChange={(event) => handleFilterChange(event.target.value)}
                  placeholder={interfaceText("e.g., flac OR mp3")}
                  value={filter}
                 {...interfaceTextProps("e.g., flac OR mp3")}/>
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
                  <LocalizedText source={"Ignored Result Folders"} /><Header.Subheader>
                    <LocalizedText source={"These peer folders stay hidden only for this wishlist item. Restore one to allow it in future searches and auto-download decisions."} /></Header.Subheader>
                </Header.Content>
              </Header>
              {loadingIgnoredResults ? (
                <Icon loading name="spinner" />
              ) : ignoredResults.length === 0 ? (
                <span><LocalizedText source={"No folders are ignored."} /></span>
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
                            content={interfaceText("Allow this peer folder to appear again in future runs of this wishlist item.")}
                            trigger={
                              <Button
                                aria-label={interfaceText("Restore {username} {directory} to wishlist results", { "username": (rule.username), "directory": (rule.directory) })}
                                compact
                                icon="undo"
                                onClick={() => restoreIgnoredResult(rule)}
                                size="tiny"
                               {...interfaceTextProps("Restore {username} {directory} to wishlist results")}/>
                            }
                           {...interfaceTextProps("Allow this peer folder to appear again in future runs of this wishlist item.")}/>
                        </Table.Cell>
                      </Table.Row>
                    ))}
                  </Table.Body>
                </Table>
              )}
            </Segment>
          )}
          <Form.Input
            label={interfaceText("Max Results")}
            max={1_000}
            min={10}
            onChange={(event) =>
              setMaxResults(Number.parseInt(event.target.value, 10) || 100)
            }
            type="number"
            value={maxResults}
           {...interfaceTextProps("Max Results")}/>
          <Form.Field>
            <Checkbox
              checked={enabled}
              label={interfaceText("Enabled (run automatically)")}
              onChange={(_, data) => setEnabled(data.checked)}
              toggle
             {...interfaceTextProps("Enabled (run automatically)")}/>
          </Form.Field>
          <Form.Field>
            <Checkbox
              checked={autoDownload}
              label={interfaceText("Auto-download best matches")}
              onChange={(_, data) => setAutoDownload(data.checked)}
              toggle
             {...interfaceTextProps("Auto-download best matches")}/>
          </Form.Field>
          <Form.Field>
            <Popup
              content={interfaceText("Automatically disable this item after N successful downloads. Leave blank to disable after the first download.")}
              position="top center"
              trigger={
                <label>
                  <LocalizedText source={"Auto-disable after downloads"} /></label>
              }
             {...interfaceTextProps("Automatically disable this item after N successful downloads. Leave blank to disable after the first download.")}/>
            <Form.Input
              label={interfaceText("Leave blank = disable after first download")}
              min={1}
              onChange={(event) => setMaxDownloads(event.target.value)}
              placeholder={interfaceText("e.g., 5 for album parts")}
              type="number"
              value={maxDownloads}
             {...interfaceTextProps("Leave blank = disable after first download")}/>
          </Form.Field>
        </Form>
      </Modal.Content>
      <Modal.Actions>
        <TooltipButton
          onClick={onClose}
          tooltip="Close this form and discard unsaved wishlist changes."
        >
          <LocalizedText source={"Cancel"} /></TooltipButton>
        <TooltipButton
          loading={saving}
          onClick={handleSave}
          primary
          tooltip={isEdit
            ? 'Save the updated search, filter, and automation settings for this wishlist item.'
            : 'Add this search to the wishlist with the filter and automation settings below.'}
        >
          {isEdit ? <LocalizedText source={"Save"} /> : <LocalizedText source={"Add"} />}
        </TooltipButton>
      </Modal.Actions>
    </Modal>
  );
};

const BulkFilterModal = ({ count, onClose, onSave }) => {
  useInterfaceLanguage();
  const [filter, setFilter] = useState('');
  const [filterError, setFilterError] = useState(null);
  const [saving, setSaving] = useState(false);

  const handleFilterChange = (value) => {
    setFilter(value);
    setFilterError(validateFilter(value));
  };

  const handleSave = async () => {
    if (filterError) {
      toast.error(interfaceText("Please fix the filter error before saving"));
      return;
    }

    setSaving(true);
    try {
      await onSave(filter.trim());
      onClose();
    } catch (error) {
      toast.error(interfaceText("Failed to update filters: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal onClose={onClose} open size="small">
      <Modal.Header>
        <Icon name="filter" />
        <LocalizedText
          source={count === 1 ? 'Edit Filter for {count} Wishlist Item' : 'Edit Filter for {count} Wishlist Items'}
          values={{ count }}
        />
      </Modal.Header>
      <Modal.Content>
        <p>
          <LocalizedText source={"Apply one filter to every selected item. Leave it blank to clear existing filters. Lidarr-synced filters may be refreshed by the next Lidarr wanted sync."} /></p>
        <Form>
          <Form.Field>
            <label><LocalizedText source={"Filter (optional)"} /></label>
            <Popup
              content={interfaceText("Use extensions or terms such as flac, mp3, or mp3 minbr:320. Prefix a term with - to exclude it.")}
              position="top center"
              trigger={
                <Form.Input
                  error={!!filterError}
                  onChange={(event) => handleFilterChange(event.target.value)}
                  placeholder={interfaceText("e.g., mp3 minbr:320")}
                  value={filter}
                 {...interfaceTextProps("e.g., mp3 minbr:320")}/>
              }
             {...interfaceTextProps("Use extensions or terms such as flac, mp3, or mp3 minbr:320. Prefix a term with - to exclude it.")}/>
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
          <LocalizedText source={"Cancel"} /></TooltipButton>
        <TooltipButton
          loading={saving}
          onClick={handleSave}
          primary
          parameters={{ count }}
          tooltip={count === 1
            ? 'Apply this filter to {count} selected wishlist item in one step.'
            : 'Apply this filter to {count} selected wishlist items in one step.'}
        >
          <LocalizedText source={"Apply Filter"} /></TooltipButton>
      </Modal.Actions>
    </Modal>
  );
};

const CsvImportModal = ({ onClose, onImport }) => {
  useInterfaceLanguage();
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
      toast.error(interfaceText("CSV text is required"));
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
      toast.error(interfaceText("CSV import failed: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
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
        <LocalizedText source={"Import CSV Playlist"} /></Modal.Header>
      <Modal.Content>
        <Form>
          <Form.Input
            accept=".csv,text/csv"
            label={interfaceText("CSV File")}
            onChange={handleFile}
            type="file"
           {...interfaceTextProps("CSV File")}/>
          <Form.TextArea
            label={interfaceText("CSV Text")}
            onChange={(event) => setCsvText(event.target.value)}
            placeholder={interfaceText("Track name,Artist name,Album name")}
            rows={8}
            value={csvText}
           {...interfaceTextProps("CSV Text")}/>
          <Form.Input
            label={interfaceText("Filter (optional)")}
            onChange={(event) => setFilter(event.target.value)}
            placeholder={interfaceText("e.g., flac OR mp3")}
            value={filter}
           {...interfaceTextProps("Filter (optional)")}/>
          <Form.Input
            label={interfaceText("Max Results")}
            max={1_000}
            min={1}
            onChange={(event) =>
              setMaxResults(Number.parseInt(event.target.value, 10) || 100)
            }
            type="number"
            value={maxResults}
           {...interfaceTextProps("Max Results")}/>
          <Form.Group widths="equal">
            <Form.Field>
              <Checkbox
                checked={enabled}
                label={interfaceText("Enabled")}
                onChange={(_, data) => setEnabled(data.checked)}
                toggle
               {...interfaceTextProps("Enabled")}/>
            </Form.Field>
            <Form.Field>
              <Checkbox
                checked={autoDownload}
                label={interfaceText("Auto-download matches")}
                onChange={(_, data) => setAutoDownload(data.checked)}
                toggle
               {...interfaceTextProps("Auto-download matches")}/>
            </Form.Field>
            <Form.Field>
              <Checkbox
                checked={includeAlbum}
                label={interfaceText("Include album")}
                onChange={(_, data) => setIncludeAlbum(data.checked)}
                toggle
               {...interfaceTextProps("Include album")}/>
            </Form.Field>
          </Form.Group>
        </Form>
      </Modal.Content>
      <Modal.Actions>
        <Popup
          content={interfaceText("Close the CSV importer without adding any wishlist searches.")}
          trigger={<Button onClick={onClose}><LocalizedText source={"Cancel"} /></Button>}
         {...interfaceTextProps("Close the CSV importer without adding any wishlist searches.")}/>
        <Popup
          content={interfaceText("Create wishlist searches from the parsed CSV rows using the selected options.")}
          trigger={
            <Button
              loading={importing}
              onClick={handleImport}
              primary
            >
              <LocalizedText source={"Import"} /></Button>
          }
         {...interfaceTextProps("Create wishlist searches from the parsed CSV rows using the selected options.")}/>
      </Modal.Actions>
    </Modal>
  );
};

const Wishlist = () => {
  useInterfaceLanguage();
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
      setRequestCopyStatus(interfaceText('Clipboard unavailable; copy the request summary manually.'));
      return;
    }

    try {
      await navigator.clipboard.writeText(report);
      setRequestCopyStatus(interfaceText('Wishlist request review copied.'));
    } catch {
      setRequestCopyStatus(interfaceText('Unable to copy Wishlist request review.'));
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
            error: getApiErrorMessage(error, { t: interfaceText }, 'Search failed'),
            id: item.id,
            status: 'failed',
          });
        }
      }

      const ran = results.filter((result) => result.status === 'ran').length;
      const failed = results.filter((result) => result.status === 'failed').length;
      setRequestCopyStatus(failed > 0
        ? interfaceText('Ran {ran} enabled Wishlist searches; failed: {failed}. Downloads still require normal result selection and policy.', { ran, failed })
        : interfaceText('Ran {ran} enabled Wishlist searches. Downloads still require normal result selection and policy.', { ran }));
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
      toast.success(interfaceText(checked ? 'Auto-search enabled' : 'Auto-search paused'));
    } catch (error) {
      toast.error(interfaceText("Failed to update: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
    } finally {
      setTogglingAutoSearch(false);
    }
  }, []);

  const loadItems = useCallback(async () => {
    try {
      const data = await wishlistAPI.getAll();
      setItems(Array.isArray(data) ? data : []);
    } catch (error) {
      toast.error(interfaceText("Failed to load wishlist: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
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
      toast.success(interfaceText("Wishlist item updated"));
    } else {
      await wishlistAPI.create(item);
      toast.success(interfaceText("Added to wishlist"));
    }

    await loadItems();
  };

  const handleDelete = async (id) => {
    try {
      await wishlistAPI.remove(id);
      toast.success(interfaceText("Wishlist item deleted"));
      await loadItems();
    } catch (error) {
      toast.error(interfaceText("Failed to delete: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
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
    toast.success(interfaceText("Enabled {size} item(s)", { "size": (selectedIds.size) }));
    setSelectedIds(new Set());
    await loadItems();
  };

  const handleBulkDisable = async () => {
    for (const id of selectedIds) {
      await wishlistAPI.update(id, { ...items.find((i) => i.id === id), enabled: false });
    }
    toast.success(interfaceText("Disabled {size} item(s)", { "size": (selectedIds.size) }));
    setSelectedIds(new Set());
    await loadItems();
  };

  const handleBulkFilterSave = async (filter) => {
    const ids = [...selectedIds];
    const result = await wishlistAPI.updateFilters(ids, filter);
    const updatedCount = result?.updatedCount ?? result?.UpdatedCount ?? ids.length;
    toast.success(interfaceText("Updated filters for {updatedCount} item(s)", { "updatedCount": (updatedCount) }));
    setSelectedIds(new Set());
    await loadItems();
  };

  const handleBulkDelete = async () => {
    for (const id of selectedIds) {
      await wishlistAPI.remove(id);
    }
    toast.success(interfaceText("Deleted {size} item(s)", { "size": (selectedIds.size) }));
    setSelectedIds(new Set());
    await loadItems();
  };

  const handleImport = async (request) => {
    const result = await wishlistAPI.importCsv(request);
    toast.success(
      interfaceText("Imported {createdCount} searches ({duplicateCount} duplicates, {skippedCount} skipped)", { "createdCount": (result.createdCount), "duplicateCount": (result.duplicateCount), "skippedCount": (result.skippedCount) }),
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
            <LocalizedText source={"Wishlist"} /><Header.Subheader>
              <LocalizedText source={"Saved searches that run automatically"} /></Header.Subheader>
          </Header.Content>
        </Header>
        <Popup
          content={interfaceText(autoSearchEnabled
            ? 'Auto-search is on — enabled items are searched automatically in the background.'
            : 'Auto-search is paused — items will not be searched until you turn it back on.')}
          trigger={
            <Checkbox
              checked={autoSearchEnabled}
              className="wishlist-autosearch-toggle"
              disabled={togglingAutoSearch}
              floated="right"
              label={interfaceText(autoSearchEnabled ? 'Auto-search on' : 'Auto-search off')}
              onChange={handleToggleAutoSearch}
              toggle
            />
          }
        />
        <Popup
          content={interfaceText("Add one saved search to the wishlist. Enabled wishlist entries run later using the normal conservative scheduler.")}
          trigger={
            <Button
              floated="right"
              icon
              labelPosition="left"
              onClick={handleAdd}
              primary
            >
              <Icon name="plus" />
              <LocalizedText source={"Add Search"} /></Button>
          }
         {...interfaceTextProps("Add one saved search to the wishlist. Enabled wishlist entries run later using the normal conservative scheduler.")}/>
        <Popup
          content={interfaceText("Import a playlist CSV, such as a TuneMyMusic export, into wishlist searches without starting a large search burst immediately.")}
          trigger={
            <Button
              floated="right"
              icon
              labelPosition="left"
              onClick={handleImportClick}
            >
              <Icon name="file alternate outline" />
              <LocalizedText source={"Import CSV"} /></Button>
          }
         {...interfaceTextProps("Import a playlist CSV, such as a TuneMyMusic export, into wishlist searches without starting a large search burst immediately.")}/>
      </Segment>

      {!loading && (
        <Segment className="wishlist-request-summary">
          <div className="wishlist-request-summary-header">
            <Header as="h3">
              <Icon name="clipboard check" />
              <LocalizedText source={"Request Portal Summary"} /><Header.Subheader>
                <LocalizedText source={"Operator view of wanted music before acquisition jobs are wired."} /></Header.Subheader>
            </Header>
            <Popup
              content={interfaceText("Copy the current Wishlist request review packet. This does not start searches, peer browsing, downloads, or automation.")}
              position="top center"
              trigger={
                <Button
                  aria-label={interfaceText("Copy Wishlist request review")}
                  onClick={copyRequestReviewPacket}
                  size="small"
                 {...interfaceTextProps("Copy Wishlist request review")}>
                  <Icon name="copy" />
                  <LocalizedText source={"Copy Review"} /></Button>
              }
             {...interfaceTextProps("Copy the current Wishlist request review packet. This does not start searches, peer browsing, downloads, or automation.")}/>
            <Popup
              content={interfaceText("Run up to three enabled Wishlist searches now through the backend. This starts search jobs only; downloads still require the normal result selection and policy.")}
              position="top center"
              trigger={
                <Button
                  aria-label={interfaceText("Run enabled Wishlist searches")}
                  disabled={runnableRequests.length === 0}
                  loading={bulkRunning}
                  onClick={runEnabledSearches}
                  primary
                  size="small"
                 {...interfaceTextProps("Run enabled Wishlist searches")}>
                  <Icon name="play" />
                  <LocalizedText source={"Run Enabled"} /></Button>
              }
             {...interfaceTextProps("Run up to three enabled Wishlist searches now through the backend. This starts search jobs only; downloads still require the normal result selection and policy.")}/>
            <Popup
              content={interfaceText("Clear all unseen results badges across your wishlist. This marks every item as viewed.")}
              position="top center"
              trigger={
                <Button
                  aria-label={interfaceText("Mark all wishlist items as viewed")}
                  icon="checkmark"
                  onClick={async () => {
                    try {
                      await wishlistAPI.markAllViewed();
                      await loadItems();
                      toast.success(interfaceText("All wishlist items marked as viewed"));
                    } catch (error) {
                      toast.error(interfaceText("Failed: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
                    }
                  }}
                  size="small"
                 {...interfaceTextProps("Mark all wishlist items as viewed")}>
                  <LocalizedText source={"Mark All Viewed"} /></Button>
              }
             {...interfaceTextProps("Clear all unseen results badges across your wishlist. This marks every item as viewed.")}/>
          </div>
          <div className="wishlist-request-summary-grid">
            {/* Plain counts get a neutral pill; color is reserved for the two
                pills below that actually report a state worth noticing. */}
            <Label basic>
              <LocalizedText source={"Requests"} /><Label.Detail>{requestSummary.total}</Label.Detail>
            </Label>
            <Label basic>
              <LocalizedText source={"Enabled"} /><Label.Detail>{requestSummary.enabled}</Label.Detail>
            </Label>
            <Label basic>
              <LocalizedText source={"Automatic"} /><Label.Detail>{requestSummary.automatic}</Label.Detail>
            </Label>
            <Label color={requestSummary.reviewCount > 0 ? 'yellow' : 'grey'}>
              <LocalizedText source={"Needs Review"} /><Label.Detail>{requestSummary.reviewCount}</Label.Detail>
            </Label>
            <Label color={requestSummary.quotaStatus === 'Within quota' ? 'green' : 'orange'}>
              <LocalizedText source={requestSummary.quotaStatus} />
              <Label.Detail>
                <LocalizedText source="{count} left" values={{ count: requestSummary.quotaRemaining }} />
              </Label.Detail>
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
            <LocalizedText source={"No wishlist items yet"} /></Header>
          <p>
            <LocalizedText source={"Add searches to your wishlist and they&apos;ll run automatically."} /></p>
          <TooltipButton
            onClick={handleAdd}
            primary
            tooltip="Add a search to your wishlist so you can track it manually or automate it with the options you choose."
          >
            <LocalizedText source={"Add Your First Search"} /></TooltipButton>
        </Segment>
      ) : (
        <>
          {selectedIds.size > 0 && (
            <Segment secondary compact style={{ marginBottom: '1em' }}>
              <span style={{ marginRight: '1em' }}>
                {selectedIds.size} <LocalizedText source={"item(s) selected"} /></span>
              <Popup
                content={interfaceText("Apply one filter to every selected wishlist item, or clear their filters.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Edit filters for selected wishlist items")}
                    compact
                    icon="filter"
                    onClick={() => setShowBulkFilterModal(true)}
                    size="small"
                   {...interfaceTextProps("Edit filters for selected wishlist items")}/>
                }
               {...interfaceTextProps("Apply one filter to every selected wishlist item, or clear their filters.")}/>
              <Popup
                content={interfaceText("Enable the selected wishlist searches so scheduled runs can check them again.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Enable selected wishlist searches")}
                    compact
                    icon="play"
                    onClick={handleBulkEnable}
                    size="small"
                   {...interfaceTextProps("Enable selected wishlist searches")}/>
                }
               {...interfaceTextProps("Enable the selected wishlist searches so scheduled runs can check them again.")}/>
              <Popup
                content={interfaceText("Pause scheduled runs for all selected wishlist searches.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Pause selected wishlist searches")}
                    compact
                    icon="pause"
                    onClick={handleBulkDisable}
                    size="small"
                   {...interfaceTextProps("Pause selected wishlist searches")}/>
                }
               {...interfaceTextProps("Pause scheduled runs for all selected wishlist searches.")}/>
              <Popup
                content={interfaceText("Delete selected wishlist searches after confirmation when they are no longer needed.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Delete selected wishlist searches")}
                    compact
                    color="red"
                    icon="trash"
                    onClick={handleBulkDelete}
                    size="small"
                   {...interfaceTextProps("Delete selected wishlist searches")}/>
                }
               {...interfaceTextProps("Delete selected wishlist searches after confirmation when they are no longer needed.")}/>
              <TooltipButton
                compact
                onClick={() => setSelectedIds(new Set())}
                size="small"
                tooltip="Clear the selection so bulk actions no longer affect these wishlist items."
              >
                <LocalizedText source={"Clear"} /></TooltipButton>
            </Segment>
          )}
          <div style={{ marginBottom: '0.75em', display: 'flex', gap: '0.5em', alignItems: 'center', flexWrap: 'wrap' }}>
            <Button.Group size="mini">
              <Popup
                content={interfaceText("Show wishlist as a table with columns")}
                trigger={
                  <Button
                    active={viewMode === 'table'}
                    aria-label={interfaceText("Show wishlist as a table")}
                    icon="table"
                    onClick={() => setViewMode('table')}
                   {...interfaceTextProps("Show wishlist as a table")}/>
                }
               {...interfaceTextProps("Show wishlist as a table with columns")}/>
              <Popup
                content={interfaceText("Show wishlist as expandable cards with inline results")}
                trigger={
                  <Button
                    active={viewMode === 'cards'}
                    aria-label={interfaceText("Show wishlist as cards")}
                    icon="th"
                    onClick={() => setViewMode('cards')}
                   {...interfaceTextProps("Show wishlist as cards")}/>
                }
               {...interfaceTextProps("Show wishlist as expandable cards with inline results")}/>
            </Button.Group>
            <Input
              icon="search"
              onChange={(event) => updateViewState({ query: event.target.value })}
              placeholder={interfaceText("Filter wishlist...")}
              size="mini"
              value={viewState.query}
             {...interfaceTextProps("Filter wishlist...")}/>
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
              label={interfaceText("New results")}
              onChange={(_, { checked }) => updateViewState({ newOnly: checked })}
             {...interfaceTextProps("New results")}/>
            <Checkbox
              checked={viewState.enabledOnly}
              label={interfaceText("Enabled")}
              onChange={(_, { checked }) => updateViewState({ enabledOnly: checked })}
             {...interfaceTextProps("Enabled")}/>
            <Checkbox
              checked={viewState.autoOnly}
              label={interfaceText("Auto")}
              onChange={(_, { checked }) => updateViewState({ autoOnly: checked })}
             {...interfaceTextProps("Auto")}/>
            <Checkbox
              checked={viewState.hasResultsOnly}
              label={interfaceText("Has results")}
              onChange={(_, { checked }) => updateViewState({ hasResultsOnly: checked })}
             {...interfaceTextProps("Has results")}/>
            <Label basic>
              <LocalizedText source={"Showing"} /><Label.Detail>
                {visibleItems.length === 0
                  ? <LocalizedText source={"0/{length}"} values={{ "length": (items.length) }} />
                  : `${pageStart + 1}-${pageEnd}/${visibleItems.length} of ${items.length}`}
              </Label.Detail>
            </Label>
            {pageCount > 1 && (
              <Button.Group size="mini">
                <Popup
                  content={interfaceText("Go to the previous page of wishlist items.")}
                  position="top center"
                  trigger={
                    <Button
                      aria-label={interfaceText("Previous wishlist page")}
                      disabled={currentPage <= 1}
                      icon="angle left"
                      onClick={() => setPage((value) => Math.max(1, value - 1))}
                     {...interfaceTextProps("Previous wishlist page")}/>
                  }
                 {...interfaceTextProps("Go to the previous page of wishlist items.")}/>
                <Popup
                  content={interfaceText("Shows your current wishlist page. Use the arrow buttons to move between pages.")}
                  position="top center"
                  trigger={(
                    <span
                      aria-label={interfaceText("Page {currentPage} of {pageCount}", { "currentPage": (currentPage), "pageCount": (pageCount) })}
                      className="ui basic button"
                      role="status"
                      tabIndex={0}
                     {...interfaceTextProps("Page {currentPage} of {pageCount}")}>
                      {currentPage}/{pageCount}
                    </span>
                  )}
                 {...interfaceTextProps("Shows your current wishlist page. Use the arrow buttons to move between pages.")}/>
                <Popup
                  content={interfaceText("Go to the next page of wishlist items.")}
                  position="top center"
                  trigger={
                    <Button
                      aria-label={interfaceText("Next wishlist page")}
                      disabled={currentPage >= pageCount}
                      icon="angle right"
                      onClick={() => setPage((value) => Math.min(pageCount, value + 1))}
                     {...interfaceTextProps("Next wishlist page")}/>
                  }
                 {...interfaceTextProps("Go to the next page of wishlist items.")}/>
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
                      content={interfaceText("Select all items on this page for bulk actions")}
                      position="top center"
                      trigger={
                        <Checkbox
                          aria-label={interfaceText("Select all wishlist items on this page for bulk actions")}
                          checked={pageItems.length > 0 && pageItems.every((item) => selectedIds.has(item.id))}
                          indeterminate={pageItems.some((item) => selectedIds.has(item.id)) && !pageItems.every((item) => selectedIds.has(item.id))}
                          onChange={(_, { checked }) => handleSelectAll(checked)}
                         {...interfaceTextProps("Select all wishlist items on this page for bulk actions")}/>
                      }
                     {...interfaceTextProps("Select all items on this page for bulk actions")}/>
                  </Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Search"} /></Table.HeaderCell>
                  <Table.HeaderCell
                    textAlign="center"
                    width={1}
                  >
                    <LocalizedText source={"Auto"} /></Table.HeaderCell>
                  <Table.HeaderCell width={3}><LocalizedText source={"Last Run"} /></Table.HeaderCell>
                  <Table.HeaderCell
                    textAlign="center"
                    width={1}
                  >
                    <Popup
                      content={interfaceText("Hits matched by the search. Locked hits are shown separately because the uploader has restricted access — they aren't directly downloadable.")}
                      position="top center"
                      trigger={<span><LocalizedText source={"Hits"} /></span>}
                     {...interfaceTextProps("Hits matched by the search. Locked hits are shown separately because the uploader has restricted access — they aren't directly downloadable.")}/>
                  </Table.HeaderCell>
                  <Table.HeaderCell
                    textAlign="center"
                    width={1}
                  >
                    <LocalizedText source={"Runs"} /></Table.HeaderCell>
                  <Table.HeaderCell width={2}><LocalizedText source={"Request State"} /></Table.HeaderCell>
                  <Table.HeaderCell width={3}><LocalizedText source={"Actions"} /></Table.HeaderCell>
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
