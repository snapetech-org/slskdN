import { formatRegionalNumber, useRegionalLocale } from '../../../lib/regionalFormat';
import SearchStatusIcon from '../SearchStatusIcon';
import { buildDiscoveryGraph } from '../../../lib/discoveryGraph';
import DiscoveryGraphModal from '../DiscoveryGraphModal';
import * as searches from '../../../lib/searches';
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
import { useInterfaceLanguage } from '../../../lib/interfaceLocale';
import SearchActionIcon from './SearchActionIcon';
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button, Checkbox, Icon, Label, Popup, Table } from 'semantic-ui-react';
import { toast } from 'react-toastify';

const sourceColors = {
  'auto-replace': 'orange',
  manual: 'grey',
  wishlist: 'blue',
};

const sourceIcons = {
  'auto-replace': 'sync',
  manual: 'search',
  wishlist: 'bookmark',
};

const SourceBadge = ({ source }) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const normalizedSource = (source || 'manual').toLowerCase();
  const color = sourceColors[normalizedSource] || 'grey';
  const icon = sourceIcons[normalizedSource] || 'search';
  const sourceLabel = {
    'auto-replace': 'Auto-Replace',
    manual: 'Manual',
    wishlist: 'Wishlist',
  }[normalizedSource] || normalizedSource;
  const localized = (text) => (
    <span dir={directionFor(text)} lang={languageFor(text)}>{t(text)}</span>
  );

  return (
    <Popup
      content={(
        <span dir={directionFor('Search started by {source}')} lang={languageFor('Search started by {source}')}>
          {t('Search started by {source}', {
            source: normalizedSource === 'auto-replace'
              ? t('Auto-Replace (automatic stuck-download replacement)')
              : t(sourceLabel),
          })}
        </span>
      )}
      position="top center"
      trigger={
        <Label
          as="span"
          color={color}
          size="mini"
          style={{ marginLeft: '0.5em' }}
        >
          <Icon name={icon} />
          {localized(sourceLabel)}
        </Label>
      }
    />
  );
};

const asArray = (value) => (Array.isArray(value) ? value : []);

const SearchListRow = ({
  onRemove,
  onSelectionChange = () => {},
  onStop,
  search,
  selected = false,
  selectionDisabled = false,
}) => {
  const regionalLocale = useRegionalLocale();
  const { language, t, languageFor, directionFor } = useInterfaceLanguage();
  const localized = (source) => (
    <span dir={directionFor(source)} lang={languageFor(source)}>{t(source)}</span>
  );
  const localizedError = (error, fallback) => (
    <span dir={language === 'ar' ? 'rtl' : 'ltr'} lang={language}>
      {getApiErrorMessage(error, { t }, fallback)}
    </span>
  );
  const [working, setWorking] = useState(false);
  const [graphData, setGraphData] = useState(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphOpen, setGraphOpen] = useState(false);
  const [graphRequest, setGraphRequest] = useState(null);
  const invoke = async (function_) => {
    setWorking(true);

    try {
      await function_();
    } catch (error) {
      console.error(error);
    } finally {
      setWorking(false);
    }
  };

  const openDiscoveryGraph = async (request) => {
    setGraphLoading(true);
    setGraphOpen(true);
    setGraphRequest(request);

    try {
      const graph = await buildDiscoveryGraph(request);
      setGraphData(graph);
    } catch (error) {
      console.error(error);
      toast.error(localizedError(error, 'The discovery graph could not be loaded.'));
      setGraphOpen(false);
    } finally {
      setGraphLoading(false);
    }
  };

  const handleOpenGraph = async () => {
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

    await handleOpenGraph();
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
      const count = await searches.createBatch({ queries });
      toast.success((
        <span dir={directionFor('Nearby graph searches started: {count}.')} lang={languageFor('Nearby graph searches started: {count}.')}>
          {t('Nearby graph searches started: {count}.', {
        count: formatRegionalNumber(count, undefined, regionalLocale),
          })}
        </span>
      ));
    } catch (error) {
      console.error(error);
      toast.error(localizedError(error, 'Nearby graph searches could not be queued.'));
    }
  };

  return (
    <>
      <Table.Row
        aria-selected={selected}
        className={selected ? 'search-list-row-selected' : undefined}
        disabled={working}
        style={{ cursor: working ? 'wait' : undefined }}
      >
        <Table.Cell className="search-list-select">
          <Popup
            content={localized('Select this search for a bulk action.')}
            position="top center"
            trigger={(
              <span>
                <Checkbox
                  aria-label={t('Select search {search}', { search: search.searchText || search.id })}
                  dir={directionFor('Select search {search}')}
                  lang={languageFor('Select search {search}')}
                  checked={selected}
                  disabled={selectionDisabled || working}
                  onChange={(event, data) => onSelectionChange(data.checked)}
                />
              </span>
            )}
          />
        </Table.Cell>
        <Table.Cell>
          <SearchStatusIcon state={search.state} />
        </Table.Cell>
        <Table.Cell>
          <Link to={`/searches/${encodeURIComponent(search.id)}`}>
            {search.searchText}
          </Link>
          <SourceBadge source={search.source} />
          <Popup
            content={localized('Open a Discovery Graph for this search phrase so the query history becomes a browsable neighborhood.')}
            position="top center"
            trigger={
              <Button
                aria-label={t('Open Discovery Graph for {search}', { search: search.searchText || search.id })}
                dir={directionFor('Open Discovery Graph for {search}')}
                lang={languageFor('Open Discovery Graph for {search}')}
                basic
                compact
                icon
                color="blue"
                onClick={handleOpenGraph}
                style={{ marginLeft: '0.5em' }}
              >
                <Icon name="crosshairs" />
              </Button>
            }
          />
        </Table.Cell>
        <Table.Cell>{formatRegionalNumber(search.fileCount, undefined, regionalLocale)}</Table.Cell>
        <Table.Cell>
          <Icon
            color="yellow"
            name="lock"
            size="small"
          />
          {formatRegionalNumber(search.lockedFileCount, undefined, regionalLocale)}
        </Table.Cell>
        <Table.Cell>{formatRegionalNumber(search.responseCount, undefined, regionalLocale)}</Table.Cell>
        <Table.Cell>
          {search.endedAt ? new Date(search.endedAt).toLocaleTimeString(regionalLocale) : '-'}
        </Table.Cell>
        <Table.Cell>
          <SearchActionIcon
            loading={working}
            onRemove={() => invoke(() => onRemove(search))}
            onStop={() => invoke(() => onStop(search))}
            search={search}
            style={{ cursor: 'pointer' }}
          />
        </Table.Cell>
      </Table.Row>
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
    </>
  );
};

export default SearchListRow;
