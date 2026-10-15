import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import * as collectionsAPI from '../../lib/collections';
import * as identityAPI from '../../lib/identity';
import { createRemoteShareStreamUrl } from '../../lib/streaming';
import ErrorSegment from '../Shared/ErrorSegment';
import LoaderSegment from '../Shared/LoaderSegment';
import TooltipButton from '../Shared/TooltipButton';
import React, { Component } from 'react';
import { toast } from 'react-toastify';
import {
  Container,
  Header,
  Icon,
  Label,
  Modal,
  Message,
  Popup,
  Segment,
  Table,
} from 'semantic-ui-react';

const Button = TooltipButton;

const asArray = (value) => (Array.isArray(value) ? value : []);
const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);
const SHARE_PAGE_SIZE = 100;
const MANIFEST_ITEM_PAGE_SIZE = 100;

const getErrorMessage = (error, fallback) =>
  getApiErrorMessage(error, { t: interfaceText }, fallback);

const normalizeBackfillResult = (data) =>
  isObject(data)
    ? {
        enqueued: Number.isFinite(Number(data.enqueued)) ? Number(data.enqueued) : 0,
        failed: Number.isFinite(Number(data.failed)) ? Number(data.failed) : 0,
        message: typeof data.message === 'string' ? data.message : '',
      }
    : { enqueued: 0, failed: 0, message: '' };

export default class SharedWithMe extends Component {
  state = {
    backfilling: false,
    backfillResult: null,
    contacts: [],
    error: null,
    loading: true,
    manifest: null,
    manifestError: null,
    manifestItemPage: 1,
    manifestLoading: false,
    manifestModalOpen: false,
    sharePage: 1,
    selectedShare: null,
    shares: [],
    streamError: null,
  };

  manifestRequestId = 0;

  componentDidMount() {
    this.loadData();
  }

  componentWillUnmount() {
    this.manifestRequestId += 1;
  }

  loadData = async () => {
    try {
      this.setState({ error: null, loading: true });
      const [sharesRes, contactsRes] = await Promise.all([
        collectionsAPI.getShares().catch((error) => {
          // If 401/403/404/400, user isn't authenticated or feature not enabled - return empty list
          if (
            error.response?.status === 401 ||
            error.response?.status === 403 ||
            error.response?.status === 404 ||
            error.response?.status === 400
          ) {
            return { data: [] };
          }

          // For other errors, rethrow to be caught below
          throw error;
        }),
        identityAPI.getContacts().catch(() => ({ data: [] })), // Gracefully handle if Identity not enabled
      ]);

      const shares = asArray(sharesRes.data);

      this.setState({
        contacts: asArray(contactsRes.data),
        loading: false,
        sharePage: 1,
        shares,
      });
      this.loadCollectionDetails(shares);
    } catch (error) {
      // Only show error if it's not an auth/feature issue (which we handle above)
      const isAuthOrFeatureError =
        error.response?.status === 401 ||
        error.response?.status === 403 ||
        error.response?.status === 404 ||
        error.response?.status === 400;
      this.setState({
        error: isAuthOrFeatureError
          ? null
          : getErrorMessage(error, 'Failed to load incoming shares'),
        loading: false,
      });
    }
  };

  loadCollectionDetails = async (shares) => {
    const sharesWithCollections = await Promise.all(
      asArray(shares).map(async (share) => {
        try {
          const collectionRes = await collectionsAPI.getCollection(
            share.collectionId,
          );
          return { ...share, collection: collectionRes.data };
        } catch (error) {
          console.warn(
            'Failed to load collection for share',
            share.id,
            error,
          );
          return share;
        }
      }),
    );

    this.setState(({ shares: currentShares }) => {
      const currentIds = currentShares.map((share) => share.id).join('\n');
      const loadedIds = shares.map((share) => share.id).join('\n');

      if (currentIds !== loadedIds) {
        return null;
      }

      return { shares: sharesWithCollections };
    });
  };

  getContactNickname = (audienceId, audiencePeerId) => {
    if (audiencePeerId) {
      const contact = this.state.contacts.find(
        (c) => c.peerId === audiencePeerId,
      );
      return contact?.nickname || null;
    }

    // For legacy UserId, try to find by matching (this is a best-effort)
    return null;
  };

  getOwnerNickname = (collection) => {
    // Try to get from manifest if available
    if (collection?.ownerContactNickname) {
      return collection.ownerContactNickname;
    }

    // Try to find contact by ownerUserId (best effort)
    if (collection?.ownerUserId) {
      // For now, we can't reliably map UserId to PeerId without additional data
      // This would require storing PeerId in Collection or a lookup table
      return null;
    }

    return null;
  };

  handleViewManifest = async (share) => {
    const requestId = ++this.manifestRequestId;
    try {
      this.setState({
        error: null,
        manifestLoading: true,
        manifestError: null,
        manifestModalOpen: true,
        manifestItemPage: 1,
        selectedShare: share,
        streamError: null,
      });
      const manifestRes = await collectionsAPI.getShareManifest(share.id);
      if (requestId !== this.manifestRequestId) return;
      this.setState({ manifest: manifestRes.data, manifestLoading: false });
    } catch (error) {
      if (requestId !== this.manifestRequestId) return;
      this.setState({
        manifest: null,
        manifestLoading: false,
        manifestError: getErrorMessage(error, 'Failed to load manifest'),
      });
    }
  };

  closeManifest = () => {
    this.manifestRequestId += 1;
    this.setState({
      backfillResult: null,
      manifest: null,
      manifestError: null,
      manifestModalOpen: false,
      selectedShare: null,
      streamError: null,
    });
  };

  handleStreamItem = async (item) => {
    const popup = window.open('about:blank', '_blank');
    if (!popup) {
      this.setState({
        streamError: interfaceText('Allow pop-ups for this site to open the secure stream.'),
      });
      return;
    }

    popup.opener = null;
    try {
      this.setState({ streamError: null });
      const streamUrl = await createRemoteShareStreamUrl(
        item.streamUrl,
        item.contentId,
        this.state.selectedShare?.shareToken,
      );
      if (!popup.closed) {
        popup.location.replace(streamUrl);
      }
    } catch (error) {
      if (!popup.closed) popup.close();
      this.setState({
        streamError: error instanceof TypeError
          ? interfaceText('Could not reach the share owner to prepare a secure stream. The owner may be offline or its CORS settings may not allow this app.')
          : getErrorMessage(error, 'Could not prepare a secure stream.'),
      });
    }
  };

  handleBackfill = async () => {
    const { selectedShare } = this.state;
    if (!selectedShare) return;

    try {
      this.setState({ backfilling: true, backfillResult: null, error: null });
      const result = await collectionsAPI.backfillShare(selectedShare.id);
      const backfillResult = normalizeBackfillResult(result.data);
      this.setState({
        backfilling: false,
        backfillResult,
      });

      if (backfillResult.failed === 0) {
        toast.success(backfillResult.message || interfaceText('Backfill started successfully'));
      } else {
        toast.warning(
          backfillResult.message || interfaceText('Backfill started with some failures'),
        );
      }
    } catch (error) {
      const errorMessage = getErrorMessage(error, 'Failed to start backfill');
      this.setState({
        backfilling: false,
        backfillResult: null,
        error: errorMessage,
      });
      toast.error(errorMessage);
    }
  };

  render() {
    const {
      error,
      loading,
      manifest,
      manifestError,
      manifestItemPage,
      manifestLoading,
      manifestModalOpen,
      selectedShare,
      sharePage,
      shares,
    } = this.state;
    const sharePages = Math.max(1, Math.ceil(shares.length / SHARE_PAGE_SIZE));
    const currentSharePage = Math.min(sharePage, sharePages);
    const shareStart = (currentSharePage - 1) * SHARE_PAGE_SIZE;
    const visibleShares = shares.slice(shareStart, shareStart + SHARE_PAGE_SIZE);
    const sharePageStart = shares.length === 0 ? 0 : shareStart + 1;
    const sharePageEnd = Math.min(shareStart + SHARE_PAGE_SIZE, shares.length);
    const manifestItems = asArray(manifest?.items);
    const incomingStreamUnavailable = Boolean(
      selectedShare?.allowStream &&
      manifestItems.length > 0 &&
      manifestItems.every((item) => !item?.streamUrl),
    );
    const manifestItemPages = Math.max(
      1,
      Math.ceil(manifestItems.length / MANIFEST_ITEM_PAGE_SIZE),
    );
    const currentManifestItemPage = Math.min(manifestItemPage, manifestItemPages);
    const manifestItemStart = (currentManifestItemPage - 1) * MANIFEST_ITEM_PAGE_SIZE;
    const visibleManifestItems = manifestItems.slice(
      manifestItemStart,
      manifestItemStart + MANIFEST_ITEM_PAGE_SIZE,
    );
    const manifestItemPageStart = manifestItems.length === 0 ? 0 : manifestItemStart + 1;
    const manifestItemPageEnd = Math.min(
      manifestItemStart + MANIFEST_ITEM_PAGE_SIZE,
      manifestItems.length,
    );

    return (
      <Container>
        <Header as="h1">
          <Icon name="share" />
          <Header.Content>
            <LocalizedText source={"Shared with Me"} /><Header.Subheader><LocalizedText source={"Collections shared with you"} /></Header.Subheader>
          </Header.Content>
        </Header>

        {error && !manifestModalOpen && <ErrorSegment caption={error} />}
        {error && !manifestModalOpen && (
          <Button
            onClick={this.loadData}
            primary
            tooltip="Retry loading the incoming collection list."
          >
            <LocalizedText source={"Retry"} /></Button>
        )}

        {shares.length === 0 ? (
          error ? null : (
            <Segment placeholder>
              <Header icon>
                <Icon name="inbox" />
                {loading ? <LocalizedText source={"Loading shares"} /> : <LocalizedText source={"No shares yet"} />}
              </Header>
              {!loading && <p><LocalizedText source={"Collections shared with you will appear here."} /></p>}
            </Segment>
          )
        ) : (
          <Table>
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell><LocalizedText source={"Collection"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Shared By"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Type"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Permissions"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Actions"} /></Table.HeaderCell>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {visibleShares.map((share) => {
                const ownerNickname = this.getOwnerNickname(share.collection);

                return (
                  <Table.Row
                    data-testid={`incoming-share-row-${share.collection?.title || 'Untitled'}`}
                    key={share.id}
                  >
                    <Table.Cell>
                      <strong>{share.collection?.title || interfaceText('Untitled')}</strong>
                      {share.collection?.description && (
                        <div
                          style={{
                            color: '#666',
                            fontSize: '0.9em',
                            marginTop: '0.25em',
                          }}
                        >
                          {share.collection.description}
                        </div>
                      )}
                    </Table.Cell>
                    <Table.Cell>
                      {ownerNickname && (
                        <Label
                          color="blue"
                          style={{ marginRight: '0.5em' }}
                        >
                          {ownerNickname}
                        </Label>
                      )}
                      <span>{share.collection?.ownerUserId || interfaceText('Unknown')}</span>
                    </Table.Cell>
                    <Table.Cell>
                      {share.collection?.type === 'ShareList' || !share.collection?.type
                        ? interfaceText('Share List')
                        : share.collection.type}
                    </Table.Cell>
                    <Table.Cell>
                      {share.allowStream && <Label color="green"><LocalizedText source={"Stream"} /></Label>}
                      {share.allowDownload && (
                        <Label color="blue"><LocalizedText source={"Download"} /></Label>
                      )}
                      {share.allowReshare && <Label><LocalizedText source={"Reshare"} /></Label>}
                    </Table.Cell>
                    <Table.Cell>
                      <Button
                        data-testid="incoming-share-open"
                        onClick={() => this.handleViewManifest(share)}
                        primary
                        size="small"
                        tooltip="Open this shared collection to review its contents and available actions."
                      >
                        <LocalizedText source={"View Contents"} /></Button>
                    </Table.Cell>
                  </Table.Row>
                );
              })}
            </Table.Body>
          </Table>
        )}
        {shares.length > SHARE_PAGE_SIZE && (
          <div className="shares-pagination">
            <span>
              {sharePageStart}–{sharePageEnd} <LocalizedText source={"of"} />{" "}{shares.length}
            </span>
            <Popup
              content={interfaceText("Show the previous page of incoming shares.")}
              trigger={
                <Button
                  aria-label={interfaceText("Previous incoming shares page")}
                  disabled={currentSharePage <= 1}
                  icon="chevron left"
                  onClick={() => this.setState({ sharePage: currentSharePage - 1 })}
                  size="mini"
                 {...interfaceTextProps("Previous incoming shares page")}/>
              }
             {...interfaceTextProps("Show the previous page of incoming shares.")}/>
            <Popup
              content={interfaceText("Show the next page of incoming shares without rendering the whole list at once.")}
              trigger={
                <Button
                  aria-label={interfaceText("Next incoming shares page")}
                  disabled={currentSharePage >= sharePages}
                  icon="chevron right"
                  onClick={() => this.setState({ sharePage: currentSharePage + 1 })}
                  size="mini"
                 {...interfaceTextProps("Next incoming shares page")}/>
              }
             {...interfaceTextProps("Show the next page of incoming shares without rendering the whole list at once.")}/>
          </div>
        )}

        {/* Manifest Modal */}
        <Modal
          closeIcon={false}
          onClose={this.closeManifest}
          open={manifestModalOpen}
          size="large"
        >
          <Modal.Header>
            {selectedShare?.collection?.title ||
              manifest?.title ||
              interfaceText('Collection Contents')}
            {manifest?.ownerContactNickname && (
              <span
                style={{
                  fontSize: '0.8em',
                  fontWeight: 'normal',
                  marginLeft: '1em',
                }}
              >
                <LocalizedText source={"by"} />{" "}{manifest.ownerContactNickname}
              </span>
            )}
          </Modal.Header>
          <Modal.Content>
            {error && <ErrorSegment caption={error} />}
            {manifestError ? (
              <Message negative data-testid="incoming-manifest-error">
                <Message.Content>{manifestError}</Message.Content>
                <Button
                  onClick={() => this.handleViewManifest(selectedShare)}
                  primary
                  tooltip="Retry loading this collection's contents without closing this dialog."
                >
                  <LocalizedText source={"Retry Contents"} /></Button>
              </Message>
            ) : manifestLoading ? (
              <LoaderSegment />
            ) : manifest ? (
              <div data-testid="shared-manifest">
                {this.state.streamError && (
                  <Message
                    data-testid="incoming-stream-error"
                    negative
                    role="alert"
                  >
                    {this.state.streamError}
                  </Message>
                )}
                {incomingStreamUnavailable && (
                  <Message info data-testid="incoming-stream-unavailable">
                    <LocalizedText source={"The share owner has not published a peer-reachable endpoint. Ask the owner to configure sharing.externalEndpoint before streaming items."} /></Message>
                )}
                {manifest.description && (
                  <p style={{ marginBottom: '1em' }}>{manifest.description}</p>
                )}
                {manifestItems.length > 0 ? (
                  <Table>
                    <Table.Header>
                      <Table.Row>
                        <Table.HeaderCell><LocalizedText source={"Content ID"} /></Table.HeaderCell>
                        <Table.HeaderCell><LocalizedText source={"Media Kind"} /></Table.HeaderCell>
                        <Table.HeaderCell><LocalizedText source={"Actions"} /></Table.HeaderCell>
                      </Table.Row>
                    </Table.Header>
                    <Table.Body>
                      {visibleManifestItems.map((item, index) => {
                        const itemIndex = manifestItemStart + index;
                        // Extract sha256 prefix from contentId (format: "sha256:...")
                        const sha256Prefix = item.contentId?.startsWith(
                          'sha256:',
                        )
                          ? item.contentId.slice(7, 15) // First 8 chars of hash
                          : item.contentId?.slice(0, 8) || `item-${itemIndex}`;
                        return (
                          <Table.Row
                            data-testid={`incoming-item-row-${sha256Prefix}`}
                            key={itemIndex}
                          >
                            <Table.Cell>
                              <code style={{ fontSize: '0.85em' }}>
                                {item.fileName ||
                                  item.contentId?.slice(0, 32) ||
                                  interfaceText('Unknown')}
                              </code>
                            </Table.Cell>
                            <Table.Cell>
                              {item.mediaKind || interfaceText('Unknown')}
                            </Table.Cell>
                            <Table.Cell>
                              {item.streamUrl && (
                                <Button
                                  data-testid={`incoming-stream-${sha256Prefix}`}
                                  onClick={() => this.handleStreamItem(item)}
                                  primary
                                  size="small"
                                  tooltip="Exchange the share credential for a short-lived ticket, then open this item without exposing the reusable share token in the URL."
                                >
                                  <Icon name="play" />
                                  <LocalizedText source={"Stream"} /></Button>
                              )}
                            </Table.Cell>
                          </Table.Row>
                        );
                      })}
                    </Table.Body>
                  </Table>
                ) : (
                  <Segment placeholder>
                    <Header icon>
                      <Icon name="file outline" />
                      <LocalizedText source={"No items in this collection"} /></Header>
                  </Segment>
                )}
                {manifestItems.length > MANIFEST_ITEM_PAGE_SIZE && (
                  <div className="shares-pagination">
                    <span>
                      {manifestItemPageStart}–{manifestItemPageEnd} <LocalizedText source={"of"} />{" "}{manifestItems.length}
                    </span>
                    <Popup
                      content={interfaceText("Show the previous page of manifest items.")}
                      trigger={
                        <Button
                          aria-label={interfaceText("Previous manifest page")}
                          disabled={currentManifestItemPage <= 1}
                          icon="chevron left"
                          onClick={() => this.setState({ manifestItemPage: currentManifestItemPage - 1 })}
                          size="mini"
                         {...interfaceTextProps("Previous manifest page")}/>
                      }
                     {...interfaceTextProps("Show the previous page of manifest items.")}/>
                    <Popup
                      content={interfaceText("Show the next page of manifest items without rendering the whole manifest at once.")}
                      trigger={
                        <Button
                          aria-label={interfaceText("Next manifest page")}
                          disabled={currentManifestItemPage >= manifestItemPages}
                          icon="chevron right"
                          onClick={() => this.setState({ manifestItemPage: currentManifestItemPage + 1 })}
                          size="mini"
                         {...interfaceTextProps("Next manifest page")}/>
                      }
                     {...interfaceTextProps("Show the next page of manifest items without rendering the whole manifest at once.")}/>
                  </div>
                )}
              </div>
            ) : (
              <ErrorSegment caption="Failed to load manifest" translateCaption />
            )}
          </Modal.Content>
          <Modal.Actions>
            {selectedShare?.allowDownload && (
              <Button
                data-testid="incoming-backfill"
                disabled={this.state.backfilling}
                loading={this.state.backfilling}
                onClick={this.handleBackfill}
                primary
                tooltip="Download every item in this shared collection when its grant permits downloads."
              >
                <Icon name="download" />
                <LocalizedText source={"Backfill All"} /></Button>
            )}
            {this.state.backfillResult && (
              <span
                style={{ color: '#666', fontSize: '0.9em', marginRight: '1em' }}
              >
                {this.state.backfillResult.enqueued} <LocalizedText source={"enqueued,"} />{' '}
                {this.state.backfillResult.failed} <LocalizedText source={"failed"} /></span>
            )}
            <Button
              onClick={this.closeManifest}
              tooltip="Close the collection contents and return to incoming shares."
            >
              <LocalizedText source={"Close"} /></Button>
          </Modal.Actions>
        </Modal>
      </Container>
    );
  }
}
