import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import * as discoveryGraph from '../../lib/discoveryGraph';
import api from '../../lib/api';
import * as searches from '../../lib/searches';
import * as streaming from '../../lib/streaming';
import * as transfers from '../../lib/transfers';
import {
  buildSearchActionPreview,
  formatSearchActionPreview,
} from '../../lib/searchActionPreview';
import {
  getCommunityQualityLabel,
  getCommunityQualitySummary,
  recordCommunityQualitySignal,
} from '../../lib/communityQualitySignals';
import { getDirectoryContents } from '../../lib/users';
import { formatBytes, getDirectoryName, getFileName } from '../../lib/util';
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import { formatRegionalNumber, useRegionalLocale } from '../../lib/regionalFormat';
import DiscoveryGraphModal from './DiscoveryGraphModal';
import FileList from '../Shared/FileList';
import TooltipButton, { LocalizedPopup as Popup } from '../Shared/TooltipButton';
import UserCard from '../Shared/UserCard';
import UserNoteModal from '../Users/UserNoteModal';
import React, { Component } from 'react';

import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { Button as SemanticButton, Card, Icon, Label, List, Modal } from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const segment = (value) => encodeURIComponent(String(value));

const textContent = (children) => {
  if (typeof children === 'string') return children;
  if (Array.isArray(children)) return children.map(textContent).filter(Boolean).join(' ').trim();
  return '';
};

const translateChildren = (children, t, parameters) => {
  if (typeof children === 'string') return t(children, parameters);
  if (Array.isArray(children)) return children.map((child) => translateChildren(child, t, parameters));
  return children;
};

const Button = ({ children, content, title, parameters = {}, 'aria-label': ariaLabel, ...props }) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const source = ariaLabel || title || (typeof content === 'string' ? content : textContent(children));
  const translatedContent = typeof content === 'string' ? t(content, parameters) : content;
  const translatedChildren = translateChildren(children, t, parameters);
  return (
    <SemanticButton
      {...props}
      aria-label={typeof ariaLabel === 'string' ? t(ariaLabel, parameters) : (source ? t(source, parameters) : undefined)}
      content={translatedContent}
      dir={source ? directionFor(source) : undefined}
      lang={source ? languageFor(source) : undefined}
      title={typeof title === 'string' ? t(title, parameters) : title}
    >
      {translatedChildren}
    </SemanticButton>
  );
};

Button.Group = SemanticButton.Group;
Button.Or = SemanticButton.Or;

const getFileSignature = (file) => [
  file?.filename,
  file?.size,
  file?.locked === true ? 1 : 0,
].join(':');

const getResponseSignature = (response) => [
  response?.username,
  response?.token,
  response?.fileCount,
  response?.lockedFileCount,
  asArray(response?.files).map(getFileSignature).join('\u001f'),
  asArray(response?.lockedFiles).map(getFileSignature).join('\u001f'),
].join('\u001e');

export const buildSearchItemActionPath = (
  searchId,
  itemId,
  action,
  destination,
) => {
  const path = `/searches/${segment(searchId)}/items/${segment(itemId)}/${action}`;
  return destination
    ? `${path}?destination=${encodeURIComponent(destination)}`
    : path;
};

export const buildDownloadRequestFiles = (files, searchId, searchText) =>
  asArray(files).map(({ filename, size, bitRate, sampleRate, bitDepth, length }) => ({
    filename,
    size,
    bitRate,
    sampleRate,
    bitDepth,
    length,
    searchId,
    searchText,
  }));

const buildTree = (response) => {
  let files = asArray(response.files);
  const lockedFiles = asArray(response.lockedFiles);
  files = files.concat(lockedFiles.map((file) => ({ ...file, locked: true })));

  return files.reduce((dict, file) => {
    const directory = getDirectoryName(file.filename);
    const selectable = { selected: false, ...file };
    dict[directory] =
      dict[directory] === undefined
        ? [selectable]
        : dict[directory].concat(selectable);
    return dict;
  }, {});
};

const getBadgeColor = (downloadStats) => {
  if (!downloadStats) return null;
  if (downloadStats.successfulDownloads >= 5) return 'green';
  if (downloadStats.successfulDownloads >= 1) return 'blue';
  if (downloadStats.failedDownloads > downloadStats.successfulDownloads)
    return 'orange';
  return 'grey';
};

const getGroupIndicator = (group) => {
  switch (group) {
    case 'privileged':
      return { color: 'yellow', icon: 'star', tooltip: 'Privileged User' };
    case 'leechers':
      return {
        color: 'orange',
        icon: 'exclamation triangle',
        tooltip: 'Leecher (Low shares)',
      };
    case 'blacklisted':
      return { color: 'red', icon: 'ban', tooltip: 'Blacklisted User' };
    default:
      // For user-defined groups or default group, show a generic user icon
      return group && group !== 'default'
        ? { color: 'blue', icon: 'user', tooltip: 'Group: {group}', parameters: { group } }
        : null;
  }
};

const getSelectedFiles = (tree) => {
  return Object.keys(tree)
    .reduce((list, dict) => list.concat(tree[dict]), [])
    .filter((f) => f.selected);
};

const getSelectedSize = (selectedFiles) => {
  return formatBytes(selectedFiles.reduce((total, f) => total + f.size, 0));
};

class Response extends Component {
  constructor(props) {
    super(props);

    this.state = {
      downloadError: '',
      downloadRequest: undefined,
      fetchingDirectoryContents: false,
      graphData: null,
      graphLoading: false,
      graphOpen: false,
      graphRequest: null,
      isFolded: this.props.isInitiallyFolded,
      previewOpen: false,
      qualitySummary: getCommunityQualitySummary(this.props.response.username),
      tree: buildTree(this.props.response),
    };
    this.responseSignature = getResponseSignature(this.props.response);
  }

  localize = (source, parameters) => this.props.locale.t(source, parameters);

  localizedText = (source, parameters) => {
    const { languageFor, directionFor } = this.props.locale;
    return (
      <span lang={languageFor(source)} dir={directionFor(source)}>
        {this.localize(source, parameters)}
      </span>
    );
  };

  localizedError = (error, fallback) =>
    getApiErrorMessage(error, this.props.locale, fallback);

  localizedErrorText = (error, fallback) => {
    const { language } = this.props.locale;
    return (
      <span dir={language === 'ar' ? 'rtl' : 'ltr'} lang={language}>
        {this.localizedError(error, fallback)}
      </span>
    );
  };

  formatNumber = (value) =>
    formatRegionalNumber(value, undefined, this.props.regionalLocale);

  componentDidUpdate(previousProps) {
    const responseSignature = getResponseSignature(this.props.response);
    if (responseSignature !== this.responseSignature) {
      this.responseSignature = responseSignature;
      this.setState({ tree: buildTree(this.props.response) });
    }

    if (this.props.isInitiallyFolded !== previousProps.isInitiallyFolded) {
      this.setState({ isFolded: this.props.isInitiallyFolded });
    }

    if (this.props.response.username !== previousProps.response.username) {
      this.setState({
        qualitySummary: getCommunityQualitySummary(this.props.response.username),
      });
    }
  }

  handleFileSelectionChange = (file, state) => {
    file.selected = state;
    this.setState((previousState) => ({
      downloadError: '',
      downloadRequest: undefined,
      tree: previousState.tree,
    }));
  };

  download = (username, files) => {
    this.setState({ downloadRequest: 'inProgress' }, async () => {
      try {
        const { destination, response, responseIndex, searchId, searchText } = this.props;
        const sourceProviders = asArray(response.sourceProviders);

        // Check if this is a bridged search result (has provenance) and we have searchId
        if (
          sourceProviders.length > 0 &&
          searchId
        ) {
          // Use new action routing endpoint for bridged searches
          // Download all selected files
          const downloadPromises = files.map(async (file) => {
            const fileIndex =
              response.files?.findIndex((f) => f.filename === file.filename) ??
              response.lockedFiles?.findIndex(
                (f) => f.filename === file.filename,
              ) ??
              -1;
            if (fileIndex < 0) {
              throw new Error(`File ${file.filename} not found in response`);
            }

            const itemId = `${responseIndex ?? 0}:${fileIndex}`;
            return api.post(
              buildSearchItemActionPath(
                searchId,
                itemId,
                'download',
                destination,
              ),
            );
          });

          await Promise.all(downloadPromises);
        } else {
          // Use existing download method for non-bridged searches
          const requests = buildDownloadRequestFiles(files, searchId, searchText);
          await transfers.download({
            destination,
            files: requests,
            username,
          });
        }

        this.setState({ downloadRequest: 'complete' });
      } catch (error) {
        this.setState({
          downloadError: error.response || {
            data: error.message,
            status: 500,
            statusText: 'Error',
          },
          downloadRequest: 'error',
        });
      }
    });
  };

  streamPreview = async (username, file) => {
    if (!file) return;

    try {
      const result = await streaming.createPeerStreamTicket({
        username,
        filename: file.filename,
        size: file.size,
      });
      const streamUrl = streaming.buildPeerStreamUrl(result.streamUrl);
      if (streamUrl) {
        window.open(streamUrl, '_blank', 'noopener');
      }
    } catch (error) {
      toast.error(this.localizedError(error, 'Stream preview failed'));
    }
  };

  streamSearchActionPreview = async (file) => {
    const { response: responseProperty, responseIndex, searchId } = this.props;
    if (!file || !searchId) return;

    try {
      const fileIndex =
        responseProperty.files?.findIndex((f) => f.filename === file.filename) ??
        -1;
      if (fileIndex < 0) return;

      const itemId = `${responseIndex ?? 0}:${fileIndex}`;
      const result = await api.post(
        buildSearchItemActionPath(searchId, itemId, 'stream'),
      );

      if (result.data?.stream_url) {
        window.open(result.data.stream_url, '_blank', 'noopener');
      }
    } catch (error) {
      toast.error(this.localizedError(error, 'Stream failed'));
    }
  };

  getFullDirectory = async (username, directory) => {
    this.setState({ fetchingDirectoryContents: true });

    try {
      const oldTree = { ...this.state.tree };
      const oldFiles = oldTree[directory];

      try {
        // some clients might send more than one directory in the response,
        // if the requested directory contains subdirectories. the root directory
        // is always first, and for now we'll only display the contents of that.
        const allDirectories = await getDirectoryContents({
          directory,
          username,
        });
        const theRootDirectory = allDirectories?.[0];

        // some clients might send an empty response for some reason
        if (!theRootDirectory) {
          throw new Error('No directories were included in the response');
        }

        const { files, name } = theRootDirectory;

        // the api returns file names only, so we need to prepend the directory
        // to make it look like a search result.  we also need to preserve
        // any file selections, so check the old files and assign accordingly
        const fixedFiles = files.map((file) => ({
          ...file,
          filename: `${directory}\\${file.filename}`,
          selected:
            oldFiles.find(
              (f) => f.filename === `${directory}\\${file.filename}`,
            )?.selected ?? false,
        }));

        oldTree[name] = fixedFiles;
        this.setState({ tree: { ...oldTree } });
      } catch (error) {
        throw new Error(`Failed to process directory response: ${error}`, {
          cause: error,
        });
      }
    } catch (error) {
      console.error(error);
      toast.error(this.localizedError(error, 'Failed to load directory contents'));
    } finally {
      this.setState({ fetchingDirectoryContents: false });
    }
  };

  handleToggleFolded = () => {
    this.setState((previousState) => ({ isFolded: !previousState.isFolded }));
  };

  reportSuspiciousCandidate = () => {
    const { onQualitySignalUpdate, response } = this.props;

    recordCommunityQualitySignal({
      reason: 'Reported suspicious candidate from Search review.',
      type: 'suspicious-candidate',
      username: response.username,
    });

    this.setState({
      qualitySummary: getCommunityQualitySummary(response.username),
    });

    if (onQualitySignalUpdate) {
      onQualitySignalUpdate();
    }

    toast.success(this.localizedText(
      'Added a local caution signal for {username}. Nothing was published.',
      { username: response.username },
    ));
  };

  buildFallbackGraphRequest = () => {
    const { response } = this.props;
    const firstFile = response.files?.[0] || response.lockedFiles?.[0];
    const title = firstFile ? getFileName(firstFile.filename).replace(/\.[^.]+$/u, '') : response.username;

    return {
      scope: 'songid_run',
      artist: response.username,
      title,
    };
  };

  openDiscoveryGraph = async (request) => {
    this.setState({
      graphLoading: true,
      graphOpen: true,
      graphRequest: request,
    });

    try {
      const graph = await discoveryGraph.buildDiscoveryGraph(request);
      this.setState({
        graphData: graph,
      });
    } catch (error) {
      console.error(error);
      toast.error(this.localizedError(error, 'Failed to build discovery graph'));
      this.setState({
        graphOpen: false,
      });
    } finally {
      this.setState({
        graphLoading: false,
      });
    }
  };

  handleGraphCompare = async (nodeId, label) => {
    const { graphRequest } = this.state;
    if (!graphRequest || !nodeId) {
      return;
    }

    await this.openDiscoveryGraph({
      ...graphRequest,
      compareLabel: label,
      compareNodeId: nodeId,
    });
  };

  handleGraphRecenter = async (nodeId) => {
    if (!nodeId) {
      return;
    }

    const [nodeType, rawId] = nodeId.split(':');
    if (nodeType === 'artist') {
      await this.openDiscoveryGraph({ scope: 'artist', artistId: rawId });
      return;
    }

    if (nodeType === 'album' || nodeType === 'release-group') {
      await this.openDiscoveryGraph({ scope: 'album', releaseId: rawId });
      return;
    }

    if (nodeType === 'track') {
      await this.openDiscoveryGraph({ scope: 'track', recordingId: rawId });
      return;
    }

    await this.openDiscoveryGraph(this.buildFallbackGraphRequest());
  };

  handleQueueNearbyFromGraph = async (graph) => {
    const queries = asArray(graph?.nodes)
      .filter((node) => node.nodeType === 'track')
      .map((node) => node.label || '')
      .filter(Boolean)
      .slice(0, 8);

    if (queries.length === 0) {
      toast.error(this.localizedText('No nearby track nodes were available to queue'));
      return;
    }

    try {
      const count = await searches.createBatch({ queries });
      toast.success(this.localizedText('Started {count} nearby graph searches', { count }));
    } catch (error) {
      console.error(error);
      toast.error(this.localizedError(error, 'Failed to queue nearby graph searches'));
    }
  };

  copyPreview = async (preview) => {
    try {
      await navigator.clipboard.writeText(formatSearchActionPreview(preview));
      toast.success(this.localizedText('Copied action preview'));
    } catch (error) {
      console.error(error);
      toast.error(this.localizedText('Unable to copy action preview'));
    }
  };

  renderActionPreview = (preview, selectedSize) => (
    <Modal
      closeIcon
      onClose={() => this.setState({ previewOpen: false })}
      open={this.state.previewOpen}
      size="small"
    >
      <Modal.Header>{this.localizedText('Download action preview')}</Modal.Header>
      <Modal.Content>
        <List relaxed>
          <List.Item>
            <List.Header>{this.localizedText('Source')}</List.Header>
            <List.Description>{preview.username || this.localize('Unknown')}</List.Description>
          </List.Item>
          <List.Item>
            <List.Header>{this.localizedText('Providers')}</List.Header>
            <List.Description>{preview.providerLabels.join(', ')}</List.Description>
          </List.Item>
          <List.Item>
            <List.Header>{this.localizedText('Selected files')}</List.Header>
            <List.Description>
              {this.localizedText('Files selected: {count}', { count: this.formatNumber(preview.fileCount) })}, {selectedSize}
            </List.Description>
          </List.Item>
          {preview.candidateScore !== null && (
            <List.Item>
              <List.Header>{this.localizedText('Candidate score')}</List.Header>
              <List.Description>{preview.candidateScore}/100</List.Description>
            </List.Item>
          )}
        </List>
        {asArray(preview.warnings).length > 0 && (
          <div className="search-action-preview-warnings">
            {asArray(preview.warnings).map((warning) => (
              <Label
                color="orange"
                key={warning}
                size="small"
              >
                {this.localizedText(warning)}
              </Label>
            ))}
          </div>
        )}
        <pre className="search-action-preview-text">
          {formatSearchActionPreview(preview)}
        </pre>
      </Modal.Content>
      <Modal.Actions>
        <Popup
          content={interfaceText("Copy this planned action summary so you can review or export it before downloading.")}
          position="top center"
          trigger={
            <Button
              aria-label={interfaceText("Copy download action preview")}
              icon="copy"
              onClick={() => this.copyPreview(preview)}
             {...interfaceTextProps("Copy download action preview")}/>
          }
         {...interfaceTextProps("Copy this planned action summary so you can review or export it before downloading.")}/>
        <TooltipButton
          onClick={() => this.setState({ previewOpen: false })}
          tooltip="Close this preview and return to the selected files without starting a transfer."
          type="button"
        >
          <LocalizedText source={"Close"} /></TooltipButton>
      </Modal.Actions>
    </Modal>
  );

  renderDownloadAction = (
    selectedFiles,
    selectedSize,
    downloadRequest,
    downloadError,
  ) => {
    const noSelection = selectedFiles.length === 0;
    const { candidateRank, playerVisible = true, response } = this.props;
    const { qualitySummary } = this.state;
    const sourceProviders = asArray(response.sourceProviders);
    const hasPodSource = sourceProviders.includes('pod');
    const hasMeshSource = sourceProviders.includes('mesh');
    const primarySource = response.primarySource || 'scene';
    const selectedStreamFile = selectedFiles[0];
    const hasContentId = Boolean(
      selectedStreamFile?.contentId || response.podContentRef?.contentId,
    );
    const canStreamFromSearch =
      (hasPodSource || hasMeshSource) && hasContentId;
    let streamTooltip = 'Preview the first selected audio file from this Soulseek peer. This manual stream is limited and does not save the file or start a batch download.';
    let streamTooltipParameters = {};
    if (canStreamFromSearch) {
      streamTooltip =
        primarySource === 'mesh'
          ? 'Stream this content-ID result from the mesh peer.'
          : 'Stream from Pod: {availability}.';
      streamTooltipParameters = {
        availability: this.localize(primarySource === 'pod' ? 'Preferred' : 'Available'),
      };
    }
    const preview = buildSearchActionPreview({
      candidateRank,
      communityQualitySummary: response.communityQualitySummary || qualitySummary,
      files: selectedFiles,
      response,
    });
    const downloadTooltip = noSelection
      ? 'Select one or more files before starting a peer download.'
      : 'Queue {count} selected files from {username} for download; this starts Soulseek peer transfers.';
    const downloadTooltipParameters = {
      count: this.formatNumber(selectedFiles.length),
      username: response.username,
    };

    return (
      <Card.Content extra>
        <span>
          {!noSelection && this.renderActionPreview(preview, selectedSize)}
          <TooltipButton
            aria-label={interfaceText("Download selected files")}
            basic={noSelection}
            color={noSelection ? 'grey' : 'green'}
            content={interfaceText("Download")}
            disabled={
              noSelection ||
              this.props.disabled ||
              downloadRequest === 'inProgress'
            }
            icon="download"
            label={
              noSelection
                ? undefined
                : {
                    as: 'a',
                    basic: false,
                    content: <>{this.localizedText('Files selected: {count}', { count: this.formatNumber(selectedFiles.length) })}, {selectedSize}</>,
                  }
            }
            labelPosition={noSelection ? undefined : 'right'}
            onClick={() =>
              this.download(this.props.response.username, selectedFiles)
            }
            parameters={downloadTooltipParameters}
            tooltip={downloadTooltip}
           {...interfaceTextProps("Download selected files")}/>
          <Popup
            content={interfaceText("Preview the selected download action, route, files, size, and warnings without starting a transfer.")}
            position="top center"
            trigger={
              <Button
                basic
                content={interfaceText("Preview")}
                disabled={noSelection || downloadRequest === 'inProgress'}
                icon="clipboard list"
                onClick={() => this.setState({ previewOpen: true })}
               {...interfaceTextProps("Preview")}/>
            }
           {...interfaceTextProps("Preview the selected download action, route, files, size, and warnings without starting a transfer.")}/>
          {playerVisible && (
            <Popup
              content={streamTooltip}
              parameters={streamTooltipParameters}
              position="top center"
              trigger={
                <Button
                  basic
                  color="blue"
                  content={interfaceText("Stream")}
                  disabled={
                    noSelection ||
                    this.props.disabled ||
                    downloadRequest === 'inProgress'
                  }
                  icon="play"
                  onClick={() =>
                    canStreamFromSearch
                      ? this.streamSearchActionPreview(selectedFiles[0])
                      : this.streamPreview(
                          this.props.response.username,
                          selectedFiles[0],
                        )
                  }
                 {...interfaceTextProps("Stream")}/>
              }
            />
          )}
          {downloadRequest === 'inProgress' && (
            <Icon
              loading
              name="circle notch"
              size="large"
            />
          )}
          {downloadRequest === 'complete' && (
            <Icon
              color="green"
              name="checkmark"
              size="large"
            />
          )}
          {downloadRequest === 'error' && (
            <span>
              <Icon
                color="red"
                name="x"
                size="large"
              />
              <Label>
                {this.localizedErrorText(downloadError, 'Download failed')}{' '}
                {downloadError?.status &&
                  `(HTTP ${downloadError.status} ${downloadError.statusText || ''})`}
              </Label>
            </span>
          )}
        </span>
      </Card.Content>
    );
  };

  render() {
    const {
      downloadStats,
      isBlocked,
      onBlock,
      onNoteUpdate,
      onUnblock,
      response,
      candidateRank,
      playerVisible = true,
      userGroup,
      userGroupLoading,
      userNote,
    } = this.props;
    const free = response.hasFreeUploadSlot;

    const {
      downloadError,
      downloadRequest,
      fetchingDirectoryContents,
      isFolded,
      tree,
      graphData,
      graphLoading,
      graphOpen,
      qualitySummary,
    } = this.state;

    const selectedFiles = getSelectedFiles(tree);
    const selectedSize = getSelectedSize(selectedFiles);
    const badgeColor = getBadgeColor(downloadStats);
    const activeQualitySummary = response.communityQualitySummary || qualitySummary;
    const qualityLabel = getCommunityQualityLabel(activeQualitySummary);
    const sourceProviders = asArray(response.sourceProviders);
    const { languageFor, directionFor } = this.props.locale;
    const uploadSpeed = Number.isFinite(response.uploadSpeed)
      ? formatBytes(response.uploadSpeed)
      : this.localize('Unknown');
    const queueLength = Number.isFinite(response.queueLength)
      ? this.formatNumber(response.queueLength)
      : this.localize('Unknown');

    return (
      <>
        <Card
          className="result-card"
          raised
        >
          <Card.Content>
          <Card.Header className="result-card-header">
            <div className="result-card-identity">
              <TooltipButton
                aria-label={isFolded ? 'Expand search results from {username}' : 'Collapse search results from {username}'}
                parameters={{ username: response.username }}
                basic
                className="result-card-fold"
                compact
                icon
                onClick={this.handleToggleFolded}
                tooltip={isFolded ? 'Expand search results from {username}' : 'Collapse search results from {username}'}
              >
                <Icon name={isFolded ? 'chevron right' : 'chevron down'} />
              </TooltipButton>
              <span
                className={`result-card-presence ${free ? 'free' : 'queued'}`}
                title={this.localize(free ? 'Free upload slot available' : 'No free upload slot')}
                lang={languageFor(free ? 'Free upload slot available' : 'No free upload slot')}
                dir={directionFor(free ? 'Free upload slot available' : 'No free upload slot')}
              />
              <Link
                className="result-card-user"
                state={{ user: response.username }}
                title={this.localize('Browse files')}
                to={`/browse?user=${encodeURIComponent(response.username)}`}
              >
                <UserCard
                  deferSupplementalData
                  info={response}
                  username={response.username}
                >
                  {response.username}
                </UserCard>
              </Link>
              <div className="result-card-badges">
                {!userGroupLoading &&
                  userGroup &&
                  (() => {
                    const indicator = getGroupIndicator(userGroup);
                    return indicator ? (
                      <Popup
                        content={indicator.tooltip}
                        parameters={indicator.parameters}
                        position="top center"
                        trigger={
                          <Icon
                            color={indicator.color}
                            name={indicator.icon}
                            size="small"
                          />
                        }
                      />
                    ) : null;
                  })()}
                {downloadStats && (
                  <Popup
                    content={interfaceText("This peer has {successful} successful downloads and {failed} failed downloads.")}
                    parameters={{ successful: this.formatNumber(downloadStats.successfulDownloads), failed: this.formatNumber(downloadStats.failedDownloads) }}
                    position="top center"
                    trigger={
                      <Label
                        color={badgeColor}
                        size="tiny"
                      >
                        <Icon name="download" />
                        {this.formatNumber(downloadStats.successfulDownloads)}
                      </Label>
                    }
                   {...interfaceTextProps("This peer has {successful} successful downloads and {failed} failed downloads.")}/>
                )}
                {candidateRank?.score !== undefined && (
                  <Popup
                    content={candidateRank.reasons?.length > 0
                      ? 'Candidate score: {score}/100. Reasons: {reasons}'
                      : 'Candidate score: {score}/100'}
                    parameters={{ score: this.formatNumber(candidateRank.score), reasons: candidateRank.reasons?.join(', ') }}
                    position="top center"
                    trigger={
                      <Label
                        color="purple"
                        size="tiny"
                      >
                        <Icon name="star" />
                        {this.formatNumber(candidateRank.score)}
                      </Label>
                    }
                  />
                )}
                {response.duplicateGroup?.foldedCount > 0 && (
                  <Popup
                    content={interfaceText("Hidden duplicate results: {count}. Sources: {providers}. Use the Fold Duplicates search option to inspect each source.")}
                    parameters={{ count: this.formatNumber(response.duplicateGroup.foldedCount), providers: response.duplicateGroup.providers.join(', ') }}
                    position="top center"
                    trigger={
                      <Label
                        color="teal"
                        size="tiny"
                      >
                        <Icon name="clone" />
                        +{this.formatNumber(response.duplicateGroup.foldedCount)}
                      </Label>
                    }
                   {...interfaceTextProps("Hidden duplicate results: {count}. Sources: {providers}. Use the Fold Duplicates search option to inspect each source.")}/>
                )}
                {qualityLabel && (
                  <Popup
                    content={interfaceText("Local peer signals: {positive} positive; {negative} caution.")}
                    parameters={{ positive: this.formatNumber(activeQualitySummary.positive), negative: this.formatNumber(activeQualitySummary.negative) }}
                    position="top center"
                    trigger={
                      <Label
                        color={qualityLabel.color}
                        size="tiny"
                      >
                        <Icon name={qualityLabel.icon} />
                        {this.localizedText(qualityLabel.text)}
                      </Label>
                    }
                   {...interfaceTextProps("Local peer signals: {positive} positive; {negative} caution.")}/>
                )}
                {userNote && (
                  <Popup
                    content={userNote.note || 'User Note'}
                    translateContent={!userNote.note}
                    position="top center"
                    trigger={
                      <Label
                        circular
                        color={userNote.color || 'grey'}
                        empty={!userNote.icon}
                        icon={userNote.icon}
                        size="tiny"
                      />
                    }
                  />
                )}
                {sourceProviders.length > 0 && (
                    <>
                      {sourceProviders.includes('pod') && (
                        <Popup
                          content={interfaceText("Available from Pod/Mesh network")}
                          position="top center"
                          trigger={
                            <Label
                              color="blue"
                              size="tiny"
                            >
                              POD
                            </Label>
                          }
                         {...interfaceTextProps("Available from Pod/Mesh network")}/>
                      )}
                      {sourceProviders.includes('mesh') && (
                        <Popup
                          content={interfaceText("Found through the mesh overlay. Files with content IDs transfer over mesh; other files use the peer’s Soulseek share.")}
                          position="top center"
                          trigger={
                            <Label color="teal" size="tiny">
                              MESH
                            </Label>
                          }
                         {...interfaceTextProps("Found through the mesh overlay. Files with content IDs transfer over mesh; other files use the peer’s Soulseek share.")}/>
                      )}
                      {sourceProviders.includes('scene') && (
                        <Popup
                          content={interfaceText("Available from Soulseek Scene")}
                          position="top center"
                          trigger={
                            <Label
                              color="purple"
                              size="tiny"
                            >
                              SCENE
                            </Label>
                          }
                         {...interfaceTextProps("Available from Soulseek Scene")}/>
                      )}
                      {sourceProviders.length > 1 && (
                        <Popup
                          content={interfaceText("Available from {providers}. Preferred: {provider}.")}
                          parameters={{ providers: sourceProviders.map((provider) => provider.toUpperCase()).join(' and '), provider: response.primarySource?.toUpperCase() || sourceProviders[0].toUpperCase() }}
                          position="top center"
                          trigger={
                            <Label
                              color="teal"
                              size="tiny"
                            >
                              {sourceProviders.map((provider) => provider.toUpperCase()).join('+')}
                            </Label>
                          }
                         {...interfaceTextProps("Available from {providers}. Preferred: {provider}.")}/>
                      )}
                    </>
                  )}
                <UserNoteModal
                  onClose={onNoteUpdate}
                  trigger={
                    <TooltipButton
                      aria-label={interfaceText("Edit user note for {username}")}
                      basic
                      compact
                      icon
                      parameters={{ username: response.username }}
                      size="small"
                      tooltip="Open your local note and color rating for {username}."
                     {...interfaceTextProps("Edit user note for {username}")}>
                      <Icon color="grey" name="pencil alternate" />
                    </TooltipButton>
                  }
                  username={response.username}
                />
              </div>
            </div>
            <div className="result-card-actions">
              <Popup
                content={interfaceText("Open a Discovery Graph centered on this result to explore related context.")}
                position="top center"
                trigger={
                  <Button
                    aria-label={interfaceText("Open Discovery Graph for {username}")}
                    basic
                    compact
                    icon
                    parameters={{ username: response.username }}
                    color="blue"
                    onClick={() => this.openDiscoveryGraph(this.buildFallbackGraphRequest())}
                   {...interfaceTextProps("Open Discovery Graph for {username}")}>
                    <Icon name="share alternate" />
                  </Button>
                }
               {...interfaceTextProps("Open a Discovery Graph centered on this result to explore related context.")}/>
              <Popup
                content={interfaceText("Open this result in atlas mode to browse a wider neighborhood with semantic zoom controls.")}
                position="top center"
                trigger={
                  <Button
                    aria-label={interfaceText("Open Discovery Graph atlas for {username}")}
                    basic
                    compact
                    icon
                    parameters={{ username: response.username }}
                    color="teal"
                    onClick={() => this.openDiscoveryGraph(this.buildFallbackGraphRequest())}
                   {...interfaceTextProps("Open Discovery Graph atlas for {username}")}>
                    <Icon name="crosshairs" />
                  </Button>
                }
               {...interfaceTextProps("Open this result in atlas mode to browse a wider neighborhood with semantic zoom controls.")}/>
              <Popup
                content={interfaceText("Add a local caution signal for this peer/result. This only affects your browser-side review and does not publish a report.")}
                position="top center"
                trigger={
                  <Button
                    aria-label={interfaceText("Report suspicious result from {username}")}
                    basic
                    compact
                    icon
                    parameters={{ username: response.username }}
                    color="orange"
                    onClick={this.reportSuspiciousCandidate}
                   {...interfaceTextProps("Report suspicious result from {username}")}>
                    <Icon name="exclamation triangle" />
                  </Button>
                }
               {...interfaceTextProps("Add a local caution signal for this peer/result. This only affects your browser-side review and does not publish a report.")}/>
              <Popup
                content={
                  isBlocked
                    ? interfaceText('Unblock this user')
                    : interfaceText('Block this user from search results')
                }
                position="top center"
                trigger={
                  <Button
                    aria-label={isBlocked ? 'Unblock {username}' : 'Block {username} from search results'}
                    basic
                    compact
                    icon
                    parameters={{ username: response.username }}
                    color={isBlocked ? 'orange' : 'grey'}
                    onClick={isBlocked ? onUnblock : onBlock}
                  >
                    <Icon name={isBlocked ? 'ban' : 'user cancel'} />
                  </Button>
                }
              />
              <TooltipButton
                aria-label={interfaceText("Hide search result from {username}")}
                basic
                className="close-button"
                compact
                icon
                parameters={{ username: response.username }}
                onClick={() => this.props.onHide()}
                tooltip="Hide search result from {username}"
               {...interfaceTextProps("Hide search result from {username}")}>
                <Icon color="red" name="close" />
              </TooltipButton>
            </div>
          </Card.Header>
          <Card.Meta className="result-meta">
            <span>
              {this.localizedText('Upload speed: {speed}/s. Free upload slot: {slot}. Queue length: {queue}.', {
                speed: uploadSpeed,
                slot: this.localize(free ? 'Available' : 'Unavailable'),
                queue: queueLength,
              })}
            </span>
          </Card.Meta>
          {(isFolded ? [] : Object.keys(tree)).map((directory) => (
            <FileList
              directoryName={directory}
              disabled={downloadRequest === 'inProgress'}
              files={tree[directory]}
              footer={
                <Button.Group fluid size="tiny">
                  <Popup
                    content={interfaceText("Browse this peer for more files in the same folder before deciding whether the result is complete.")}
                    trigger={
                      <Button
                        disabled={fetchingDirectoryContents}
                        icon={fetchingDirectoryContents ? 'circle notch' : 'search'}
                        loading={fetchingDirectoryContents}
                        onClick={() => this.getFullDirectory(response.username, directory)}
                        content={interfaceText("Find More Files")}
                       {...interfaceTextProps("Find More Files")}/>
                    }
                   {...interfaceTextProps("Browse this peer for more files in the same folder before deciding whether the result is complete.")}/>
                  {this.props.onIgnoreDirectory && (
                    <Popup
                    content={interfaceText("Hide this peer’s copy of this folder from future Wishlist searches without blocking the peer or hiding other results.")}
                      trigger={
                        <Button
                          color="red"
                          content={interfaceText("Ignore for Wishlist")}
                          icon="eye slash"
                          onClick={() => this.props.onIgnoreDirectory(directory)}
                         {...interfaceTextProps("Ignore for Wishlist")}/>
                      }
                     {...interfaceTextProps("Hide this peer’s copy of this folder from future Wishlist searches without blocking the peer or hiding other results.")}/>
                  )}
                </Button.Group>
              }
              key={directory}
              locked={tree[directory].find((file) => file.locked)}
              onSelectionChange={this.handleFileSelectionChange}
            />
          ))}
          </Card.Content>
          {this.renderDownloadAction(
            selectedFiles,
            selectedSize,
            downloadRequest,
            downloadError,
          )}
        </Card>
        <DiscoveryGraphModal
          graph={graphData}
          loading={graphLoading}
          onClose={() => this.setState({ graphOpen: false })}
          onCompare={this.handleGraphCompare}
          onQueueNearby={this.handleQueueNearbyFromGraph}
          onRecenter={this.handleGraphRecenter}
          onRestoreBranch={(branch) =>
            branch?.request && this.openDiscoveryGraph(branch.request)
          }
          open={graphOpen}
        />
      </>
    );
  }
}

const ResponseWithLocale = (props) => {
  const locale = useInterfaceLanguage();
  const regionalLocale = useRegionalLocale();
  return <Response {...props} locale={locale} regionalLocale={regionalLocale} />;
};

export default ResponseWithLocale;
