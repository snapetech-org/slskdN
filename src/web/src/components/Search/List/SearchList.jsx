import ErrorSegment from '../../Shared/ErrorSegment';
import PlaceholderSegment from '../../Shared/PlaceholderSegment';
import SearchListRow from './SearchListRow';
import React, { useEffect, useMemo, useState } from 'react';
import { Button, Card, Checkbox, Icon, Loader, Popup, Table } from 'semantic-ui-react';

const SEARCH_LIST_PAGE_SIZE = 100;

const isSearchComplete = (search) =>
  search?.isComplete === true || String(search?.state ?? '').toLowerCase().includes('complete');

const SearchList = ({
  connecting = false,
  error = undefined,
  hasMoreFromServer = false,
  loadingMore = false,
  onLoadMore = () => {},
  onCleanup = () => {},
  onRemove = () => {},
  onRemoveAll = () => {},
  onRemoveSelected = async () => [],
  onResearchSelected = async () => [],
  onStop = () => {},
  onStopSelected = async () => [],
  removingAll = false,
  cleaningUp = false,
  bulkAction = null,
  searches = {},
  sourceFilter = 'all',
}) => {
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const bulkWorking = Boolean(bulkAction);
  const filteredSearchValues = useMemo(() => {
    const values = Object.values(searches);
    const filtered = sourceFilter === 'all'
      ? values
      : values.filter(
          (search) => (search.source || 'manual').toLowerCase() === sourceFilter.toLowerCase(),
        );

    return filtered.sort((a, b) => new Date(b.startedAt) - new Date(a.startedAt));
  }, [searches, sourceFilter]);

  useEffect(() => {
    setPage(1);
  }, [sourceFilter]);

  useEffect(() => {
    setSelectedIds(new Set());
  }, [sourceFilter]);

  useEffect(() => {
    const availableIds = new Set(Object.keys(searches));

    setSelectedIds((current) => {
      const next = new Set([...current].filter((id) => availableIds.has(id)));
      return next.size === current.size ? current : next;
    });
  }, [searches]);

  const searchCount = Object.keys(searches).length;
  const filteredCount = filteredSearchValues.length;
  const totalPages = Math.max(1, Math.ceil(filteredCount / SEARCH_LIST_PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const start = (currentPage - 1) * SEARCH_LIST_PAGE_SIZE;
  const pageSearches = filteredSearchValues.slice(start, start + SEARCH_LIST_PAGE_SIZE);
  const pageStart = filteredCount === 0 ? 0 : start + 1;
  const pageEnd = Math.min(start + SEARCH_LIST_PAGE_SIZE, filteredCount);

  const selectedSearches = filteredSearchValues.filter((search) => selectedIds.has(search.id));
  const selectedCompletedSearches = selectedSearches.filter(isSearchComplete);
  const selectedActiveSearches = selectedSearches.filter((search) => !isSearchComplete(search));
  const allVisibleSelected = filteredCount > 0 && selectedSearches.length === filteredCount;
  const someVisibleSelected = selectedSearches.length > 0 && !allVisibleSelected;

  const toggleAllVisible = () => {
    setSelectedIds((current) => {
      const next = new Set(current);

      if (allVisibleSelected) {
        filteredSearchValues.forEach((search) => next.delete(search.id));
      } else {
        filteredSearchValues.forEach((search) => next.add(search.id));
      }

      return next;
    });
  };

  const toggleSearch = (searchId, selected) => {
    setSelectedIds((current) => {
      const next = new Set(current);

      if (selected) {
        next.add(searchId);
      } else {
        next.delete(searchId);
      }

      return next;
    });
  };

  const clearSelection = () => setSelectedIds(new Set());

  const runSelectedAction = async (action, eligibleSearches) => {
    const processedIds = await action(eligibleSearches);

    if (Array.isArray(processedIds)) {
      setSelectedIds((current) => new Set([...current].filter((id) => !processedIds.includes(id))));
    }
  };

  return (
    <Card
      className="search-list-card"
      raised
    >
      <Card.Content>
        <div className="search-list-header">
          <div style={{ display: 'flex', gap: '0.5em', flexWrap: 'wrap', alignItems: 'center' }}>
            <Popup
              content="Clear all completed searches"
              position="top center"
              trigger={
                <Button
                  color="red"
                  compact
                  disabled={removingAll || Object.keys(searches).length === 0}
                  icon
                  labelPosition="left"
                  loading={removingAll}
                  onClick={onRemoveAll}
                  size="small"
                >
                  <Icon name="trash" />
                  Clear All
                </Button>
              }
            />
            <Popup
              content="Clear old searches"
              position="top center"
              trigger={
                <Button
                  color="orange"
                  compact
                  disabled={cleaningUp || Object.keys(searches).length === 0}
                  icon
                  labelPosition="left"
                  loading={cleaningUp}
                  onClick={onCleanup}
                  size="small"
                >
                  <Icon name="clock outline" />
                  Clear Old
                </Button>
              }
            />
          </div>
          <div className="search-list-count">
            {filteredCount} / {searchCount} loaded searches
          </div>
        </div>
        {selectedSearches.length > 0 && (
          <div className="search-list-selection-toolbar" role="toolbar" aria-label="Selected search actions">
            <span className="search-list-selection-summary">
              {selectedSearches.length} selected
              <span className="search-list-selection-count">
                {' '}
                ({selectedCompletedSearches.length} completed, {selectedActiveSearches.length} active)
              </span>
            </span>

            <Popup
              content="Run the selected completed searches again, one at a time, using the current acquisition profile."
              position="top center"
              trigger={(
                <span>
                  <Button
                    color="blue"
                    disabled={bulkWorking || selectedCompletedSearches.length === 0}
                    loading={bulkAction === 'research'}
                    onClick={() => runSelectedAction(onResearchSelected, selectedCompletedSearches)}
                  >
                    <Icon name="refresh" />
                    Search Again
                  </Button>
                </span>
              )}
            />

            <Popup
              content="Stop the selected searches that are still running."
              position="top center"
              trigger={(
                <span>
                  <Button
                    color="orange"
                    disabled={bulkWorking || selectedActiveSearches.length === 0}
                    loading={bulkAction === 'stop'}
                    onClick={() => runSelectedAction(onStopSelected, selectedActiveSearches)}
                  >
                    <Icon name="stop circle" />
                    Stop Active
                  </Button>
                </span>
              )}
            />

            <Popup
              content="Delete the selected completed searches from search history."
              position="top center"
              trigger={(
                <span>
                  <Button
                    color="red"
                    disabled={bulkWorking || selectedCompletedSearches.length === 0}
                    loading={bulkAction === 'remove'}
                    onClick={() => runSelectedAction(onRemoveSelected, selectedCompletedSearches)}
                  >
                    <Icon name="trash" />
                    Delete Selected
                  </Button>
                </span>
              )}
            />

            <Popup
              content="Clear the current selection without changing any searches."
              position="top center"
              trigger={(
                <Button
                  aria-label="Clear selection"
                  basic
                  disabled={bulkWorking}
                  icon="close"
                  onClick={clearSelection}
                />
              )}
            />
          </div>
        )}
        {connecting && (
          <Loader
            active
            inline="centered"
            size="small"
          />
        )}
        {error ? (
          <ErrorSegment caption={error} />
        ) : filteredCount === 0 && !connecting ? (
          <PlaceholderSegment
            caption={
              sourceFilter !== 'all'
                ? `No ${sourceFilter} searches to display`
                : 'No searches to display'
            }
            icon="search"
          />
        ) : (
          <div className="search-list-wrapper">
            <Table
              className="search-list-table unstackable"
              size="large"
            >
              <Table.Header>
                <Table.Row>
                  <Table.HeaderCell className="search-list-select">
                    <Popup
                      content="Select all searches in the current list filter."
                      position="top center"
                      trigger={(
                        <span>
                          <Checkbox
                            aria-label="Select all searches in current list"
                            checked={allVisibleSelected}
                            disabled={filteredCount === 0 || bulkWorking}
                            indeterminate={someVisibleSelected}
                            onChange={toggleAllVisible}
                          />
                        </span>
                      )}
                    />
                  </Table.HeaderCell>
                  <Table.HeaderCell className="search-list-action">
                    <Icon name="info circle" />
                  </Table.HeaderCell>
                  <Table.HeaderCell className="search-list-phrase">
                    Search
                  </Table.HeaderCell>
                  <Table.HeaderCell className="search-list-files">
                    Files
                  </Table.HeaderCell>
                  <Table.HeaderCell className="search-list-locked">
                    Locked
                  </Table.HeaderCell>
                  <Table.HeaderCell className="search-list-responses">
                    Responses
                  </Table.HeaderCell>
                  <Table.HeaderCell className="search-list-started">
                    Ended
                  </Table.HeaderCell>
                  <Table.HeaderCell className="search-list-action" />
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {pageSearches.map((search) => (
                  <SearchListRow
                    key={search.id}
                    onRemove={onRemove}
                    onStop={onStop}
                    onSelectionChange={(selected) => toggleSearch(search.id, selected)}
                    search={search}
                    selected={selectedIds.has(search.id)}
                    selectionDisabled={bulkWorking}
                  />
                ))}
              </Table.Body>
            </Table>
            {(filteredCount > SEARCH_LIST_PAGE_SIZE || hasMoreFromServer) && (
              <div className="search-list-pagination">
                <span>
                  {pageStart}–{pageEnd} of {filteredCount} loaded
                </span>
                <Popup
                  content="Go to the previous page of searches."
                  position="top center"
                  trigger={
                    <span>
                      <Button
                        aria-label="Previous search page"
                        disabled={currentPage <= 1}
                        icon="chevron left"
                        onClick={() => setPage(currentPage - 1)}
                        size="mini"
                      />
                    </span>
                  }
                />
                <Popup
                  content="Go to the next page of searches."
                  position="top center"
                  trigger={
                    <span>
                      <Button
                        aria-label="Next search page"
                        disabled={currentPage >= totalPages}
                        icon="chevron right"
                        onClick={() => setPage(currentPage + 1)}
                        size="mini"
                      />
                    </span>
                  }
                />
                {hasMoreFromServer && (
                  <Popup
                    content="Fetch the next bounded page from the server. Existing loaded rows and selections stay in place."
                    position="top center"
                    trigger={(
                      <Button
                        content="Load more searches"
                        disabled={loadingMore}
                        loading={loadingMore}
                        onClick={onLoadMore}
                        size="small"
                      />
                    )}
                  />
                )}
              </div>
            )}
          </div>
        )}
      </Card.Content>
    </Card>
  );
};

export default SearchList;
