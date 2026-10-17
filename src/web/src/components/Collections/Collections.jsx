import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import * as collectionsAPI from '../../lib/collections';
import * as streaming from '../../lib/streaming';
import PlayCollectionItemButton from '../Player/PlayCollectionItemButton';
import ErrorSegment from '../Shared/ErrorSegment';
import LoaderSegment from '../Shared/LoaderSegment';
import { TooltipButton } from '../Shared';
import React, { Component } from 'react';
import {
  Button,
  Container,
  Dropdown,
  Form,
  Header,
  Icon,
  Message,
  Modal,
  Popup,
  Segment,
  Table,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);
const COLLECTION_PAGE_SIZE = 100;
const COLLECTION_ITEM_PAGE_SIZE = 100;

const getCollectionTypeLabel = (type) => {
  if (type === 'Playlist') return interfaceText('Playlist');
  if (type === 'ShareList') return interfaceText('Share List');
  return type || interfaceText('Playlist');
};

const getErrorMessage = (error, fallback = 'The request failed. Try again.') =>
  getApiErrorMessage(error, { t: interfaceText }, fallback);

export default class Collections extends Component {
  constructor(props) {
    super(props);

    this.state = {
      addItemModalOpen: false,
      collectionItemPage: 1,
      collectionPage: 1,
      collections: [],
      createModalOpen: false,
      editItem: null,
      editFileTags: false,
      error: null,
      itemSearchLoading: false,
      itemSearchQuery: '',
      itemSearchResults: [],
      loading: true,
      newCollectionDescription: '',
      newCollectionTitle: '',
      newCollectionType: 'Playlist',
      selectedCollection: null,
      selectedCollectionItems: [],
      shareAllowDownload: true,
      shareAllowStream: true,
      shareAudienceId: null,
      shareGroups: [],
      shareGroupsLoading: false,
      shareModalOpen: false,
      shares: [],
    };
  }

  componentDidMount() {
    this.loadData();
    this.loadShareGroups();
  }

  loadData = async () => {
    try {
      this.setState({ error: null, loading: true });
      const response = await collectionsAPI.getCollections().catch((error) => {
        if (
          error.response?.status === 401 ||
          error.response?.status === 403 ||
          error.response?.status === 404
        ) {
          return { data: [] };
        }

        throw error;
      });
      this.setState({
        collectionPage: 1,
        collections: asArray(response.data),
        loading: false,
      });
    } catch (error) {
      const errorMessage = getErrorMessage(error, 'Failed to load collections');

      const isAuthOrFeatureError =
        error.response?.status === 401 ||
        error.response?.status === 403 ||
        error.response?.status === 404;
      this.setState({
        error: isAuthOrFeatureError ? null : errorMessage,
        loading: false,
      });
    }
  };

  loadShareGroups = async () => {
    try {
      this.setState({ shareGroupsLoading: true });
      const response = await collectionsAPI.getShareGroups().catch((error) => {
        if (
          error.response?.status === 401 ||
          error.response?.status === 403 ||
          error.response?.status === 404
        ) {
          return { data: [] };
        }

        throw error;
      });
      const shareGroups = asArray(response.data);
      this.setState((previousState) => ({
        shareAudienceId:
          previousState.shareAudienceId ?? shareGroups[0]?.id ?? null,
        shareGroups,
        shareGroupsLoading: false,
      }));
    } catch {
      this.setState({ shareGroups: [], shareGroupsLoading: false });
    }
  };

  loadShares = async (collectionId) => {
    try {
      if (!collectionId) {
        this.setState({ shares: [] });
        return;
      }

      const response = await collectionsAPI
        .getSharesByCollection(collectionId)
        .catch((error) => {
          if (
            error.response?.status === 401 ||
            error.response?.status === 403 ||
            error.response?.status === 404
          ) {
            return { data: [] };
          }

          throw error;
        });
      this.setState({ shares: asArray(response.data) });
    } catch {
      this.setState({ shares: [] });
    }
  };

  loadCollectionItems = async (collectionId) => {
    try {
      const response = await collectionsAPI.getCollectionItems(collectionId);
      this.setState({
        collectionItemPage: 1,
        selectedCollectionItems: asArray(response.data),
      });
    } catch (error) {
      console.error('[Collections] Error loading items:', error);
    }
  };

  handleCreateCollection = async () => {
    try {
      await collectionsAPI.createCollection({
        description: this.state.newCollectionDescription || undefined,
        title: this.state.newCollectionTitle,
        type: this.state.newCollectionType,
      });
      this.setState({
        createModalOpen: false,
        error: null,
        newCollectionDescription: '',
        newCollectionTitle: '',
        newCollectionType: 'Playlist',
      });
      await this.loadData();
    } catch (error) {
      const errorMessage = getErrorMessage(error, 'Failed to create collection');

      this.setState({ error: errorMessage });
    }
  };

  handleDeleteCollection = async (id) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(interfaceText('Delete this collection?'))) return;
    try {
      await collectionsAPI.deleteCollection(id);
      await this.loadData();
      if (this.state.selectedCollection?.id === id) {
        this.setState({
          collectionItemPage: 1,
          selectedCollection: null,
          selectedCollectionItems: [],
        });
      }
    } catch (error) {
      this.setState({ error: getErrorMessage(error, 'Failed to delete collection') });
    }
  };

  handleSelectCollection = async (collection) => {
    this.setState({ collectionItemPage: 1, selectedCollection: collection });
    await this.loadCollectionItems(collection.id);
    await this.loadShares(collection.id);
  };

  handleSearchItems = async (query) => {
    if (!query || query.length < 2) {
      this.setState({ itemSearchLoading: false, itemSearchResults: [] });
      return;
    }

    this.setState({ itemSearchLoading: true });
    try {
      const response = await collectionsAPI.searchLibraryItems(query, null, 20);
      const items = asArray(response.data?.items);
      this.setState({
        itemSearchLoading: false,
        itemSearchResults: items,
      });
    } catch (error) {
      console.error('[Collections] Search error:', error);
      this.setState({ itemSearchLoading: false, itemSearchResults: [] });
    }
  };

  handleAddItem = async () => {
    if (!this.state.selectedCollection) return;

    // Use selected search result if available, otherwise use query as fallback
    const selectedResult = this.state.itemSearchResults.find(
      (item) => item.contentId === this.state.itemSearchQuery,
    );
    const contentId = selectedResult
      ? selectedResult.contentId
      : this.state.itemSearchQuery;
    const mediaKind = selectedResult ? selectedResult.mediaKind : 'File'; // Default fallback

    if (!contentId) return;

    try {
      await collectionsAPI.addCollectionItem(this.state.selectedCollection.id, {
        bytes: selectedResult?.bytes,
        contentId,
        fileName: selectedResult?.fileName,
        mediaKind,
        sha256: selectedResult?.sha256,
      });
      this.setState({
        addItemModalOpen: false,
        error: null,
        itemSearchQuery: '',
        itemSearchResults: [],
      });
      await this.loadCollectionItems(this.state.selectedCollection.id);
    } catch (error) {
      const errorMessage = getErrorMessage(error, 'Failed to add item');

      this.setState({ error: errorMessage });
    }
  };

  handleOpenShareModal = () => {
    const { shareGroups } = this.state;
    this.setState({
      shareAllowDownload: true,
      shareAllowStream: true,
      shareAudienceId: shareGroups[0]?.id ?? null,
      shareModalOpen: true,
    });
  };

  handleCreateShare = async () => {
    const {
      selectedCollection,
      shareAllowDownload,
      shareAllowStream,
      shareAudienceId,
    } = this.state;
    if (!selectedCollection || !shareAudienceId) return;

    try {
      await collectionsAPI.createShare({
        allowDownload: shareAllowDownload,
        allowStream: shareAllowStream,
        audienceId:
          typeof shareAudienceId === 'string'
            ? shareAudienceId
            : String(shareAudienceId),
        audienceType: 'ShareGroup',
        collectionId: selectedCollection.id,
      });
      this.setState({ error: null, shareModalOpen: false });
      await this.loadShares(selectedCollection.id);
    } catch (error) {
      this.setState({ error: getErrorMessage(error, 'Failed to create share') });
    }
  };

  render() {
    const {
      addItemModalOpen,
      collectionItemPage,
      collectionPage,
      collections,
      createModalOpen,
      editItem,
      editFileTags,
      error,
      itemSearchLoading,
      itemSearchQuery,
      itemSearchResults,
      loading,
      newCollectionDescription,
      newCollectionTitle,
      newCollectionType,
      selectedCollection,
      selectedCollectionItems,
      shareAllowDownload,
      shareAllowStream,
      shareAudienceId,
      shareGroups,
      shareGroupsLoading,
      shareModalOpen,
      shares,
    } = this.state;

    const typeOptions = [
      { key: 'Playlist', text: interfaceText("Playlist"), value: 'Playlist' },
      { key: 'ShareList', text: interfaceText("Share List"), value: 'ShareList' },
    ];

    const collectionShares = shares;
    const collectionPages = Math.max(1, Math.ceil(collections.length / COLLECTION_PAGE_SIZE));
    const currentCollectionPage = Math.min(collectionPage, collectionPages);
    const collectionStart = (currentCollectionPage - 1) * COLLECTION_PAGE_SIZE;
    const visibleCollections = collections.slice(
      collectionStart,
      collectionStart + COLLECTION_PAGE_SIZE,
    );
    const collectionPageStart = collections.length === 0 ? 0 : collectionStart + 1;
    const collectionPageEnd = Math.min(
      collectionStart + COLLECTION_PAGE_SIZE,
      collections.length,
    );
    const itemPages = Math.max(
      1,
      Math.ceil(selectedCollectionItems.length / COLLECTION_ITEM_PAGE_SIZE),
    );
    const currentItemPage = Math.min(collectionItemPage, itemPages);
    const itemStart = (currentItemPage - 1) * COLLECTION_ITEM_PAGE_SIZE;
    const visibleCollectionItems = selectedCollectionItems.slice(
      itemStart,
      itemStart + COLLECTION_ITEM_PAGE_SIZE,
    );
    const itemPageStart = selectedCollectionItems.length === 0 ? 0 : itemStart + 1;
    const itemPageEnd = Math.min(
      itemStart + COLLECTION_ITEM_PAGE_SIZE,
      selectedCollectionItems.length,
    );

    return (
      <div data-testid="collections-root">
        <Container>
          <Header as="h1">
            <Icon name="list" />
            <Header.Content>
              <LocalizedText source={"Collections"} /><Header.Subheader>
                <LocalizedText source={"Manage your playlists and share lists"} /></Header.Subheader>
            </Header.Content>
          </Header>

          {error && <ErrorSegment caption={error} />}

          <div style={{ marginBottom: '1em' }}>
            <TooltipButton
              data-testid="collections-create"
              onClick={() => this.setState({ createModalOpen: true })}
              primary
              tooltip="Open the collection form to create a playlist or list for organizing items."
            >
              <Icon name="plus" />
              <LocalizedText source={"Create Collection"} /></TooltipButton>
          </div>

          {collections.length === 0 ? (
            <Segment placeholder>
              <Header icon>
                <Icon name="list" />
                {loading ? <LocalizedText source={"Loading collections"} /> : <LocalizedText source={"No collections yet"} />}
              </Header>
              <TooltipButton
                data-testid="collections-create-empty"
                onClick={() => this.setState({ createModalOpen: true })}
                primary
                tooltip="Open the collection form to create a playlist or list for organizing items."
              >
                <LocalizedText source={"Create Collection"} /></TooltipButton>
            </Segment>
          ) : (
            <Table celled>
              <Table.Header>
                <Table.Row>
                  <Table.HeaderCell><LocalizedText source={"Title"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Type"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Items"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Actions"} /></Table.HeaderCell>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {visibleCollections.map((collection) => (
                  <Table.Row
                    data-testid={`collection-row-${collection.title}`}
                    key={collection.id}
                    onClick={() => this.handleSelectCollection(collection)}
                    style={{ cursor: 'pointer' }}
                  >
                    <Table.Cell>{collection.title}</Table.Cell>
                    <Table.Cell>{getCollectionTypeLabel(collection.type)}</Table.Cell>
                    <Table.Cell>{collection.itemCount || 0}</Table.Cell>
                    <Table.Cell>
                      <TooltipButton
                        negative
                        onClick={(event) => {
                          event.stopPropagation();
                          this.handleDeleteCollection(collection.id);
                        }}
                        size="small"
                        tooltip="Delete this collection after confirmation when you no longer need it."
                      >
                        <LocalizedText source={"Delete"} /></TooltipButton>
                    </Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
            </Table>
          )}
          {collections.length > COLLECTION_PAGE_SIZE && (
            <div className="collections-pagination">
              <span>
                {collectionPageStart}–{collectionPageEnd} <LocalizedText source={"of"} />{" "}{collections.length}
              </span>
              <Popup
                content={interfaceText("Show the previous page of collections without reloading the route.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Previous collections page")}
                    disabled={currentCollectionPage <= 1}
                    icon="chevron left"
                    onClick={() => this.setState({ collectionPage: currentCollectionPage - 1 })}
                    size="mini"
                   {...interfaceTextProps("Previous collections page")}/>
                }
               {...interfaceTextProps("Show the previous page of collections without reloading the route.")}/>
              <Popup
                content={interfaceText("Show the next page of collections without rendering the entire list at once.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Next collections page")}
                    disabled={currentCollectionPage >= collectionPages}
                    icon="chevron right"
                    onClick={() => this.setState({ collectionPage: currentCollectionPage + 1 })}
                    size="mini"
                   {...interfaceTextProps("Next collections page")}/>
                }
               {...interfaceTextProps("Show the next page of collections without rendering the entire list at once.")}/>
            </div>
          )}

          {selectedCollection && (
            <Segment style={{ marginTop: '2em' }}>
              <Header as="h2">
                {selectedCollection.title}
                <Header.Subheader>
                  {getCollectionTypeLabel(selectedCollection.type)}
                </Header.Subheader>
              </Header>

              <div style={{ marginBottom: '1em' }}>
                <TooltipButton
                  data-testid="collection-add-item"
                  onClick={() => this.setState({ addItemModalOpen: true })}
                  primary
                  tooltip="Open item search so you can add a library item or content ID to this collection."
                >
                  <Icon name="plus" />
                  <LocalizedText source={"Add Item"} /></TooltipButton>
                <TooltipButton
                  data-testid="share-create"
                  onClick={this.handleOpenShareModal}
                  style={{ marginLeft: '0.5em' }}
                  tooltip="Choose a share group and permissions so its members can access this collection."
                >
                  <Icon name="share alternate" />
                  <LocalizedText source={"Share Collection"} /></TooltipButton>
              </div>

              <div data-testid="collection-items-table">
                {selectedCollectionItems.length === 0 ? (
                  <Message info><LocalizedText source={"No items in this collection yet."} /></Message>
                ) : (
                  <Table>
                    <Table.Header>
                      <Table.Row>
                        <Table.HeaderCell><LocalizedText source={"File Name"} /></Table.HeaderCell>
                        <Table.HeaderCell><LocalizedText source={"Media Kind"} /></Table.HeaderCell>
                        <Table.HeaderCell><LocalizedText source={"Actions"} /></Table.HeaderCell>
                      </Table.Row>
                    </Table.Header>
                    <Table.Body>
                      {visibleCollectionItems.map((item, index) => (
                        <Table.Row
                          data-testid={`collection-item-row-${index}`}
                          key={item.id}
                        >
                          <Table.Cell>
                            {item.title || item.fileName || item.contentId || interfaceText('N/A')}
                            {item.artist ? <small> — {item.artist}</small> : null}
                          </Table.Cell>
                          <Table.Cell>{item.mediaKind || interfaceText('Unknown')}</Table.Cell>
                          <Table.Cell>
                            <PlayCollectionItemButton item={item} />
                            <Popup
                              content={interfaceText("Edit how this item appears in the collection without changing the audio file.")}
                              trigger={
                                <Button
                                  aria-label={interfaceText('Edit {item} display metadata', {
                                    item: item.title || item.fileName || interfaceText('item'),
                                  })}
                                  icon="edit"
                                  onClick={() => this.setState({ editFileTags: false, editItem: { ...item } })}
                                  size="small"
                                />
                              }
                             {...interfaceTextProps("Edit how this item appears in the collection without changing the audio file.")}/>
                            <Popup
                              content={interfaceText("Edit the tags in this server audio file. Administrator access and write permission are required.")}
                              trigger={
                                <Button
                                  aria-label={interfaceText('Edit {item} audio file tags', {
                                    item: item.title || item.fileName || interfaceText('item'),
                                  })}
                                  icon="tags"
                                  onClick={() => this.setState({ editFileTags: true, editItem: { ...item } })}
                                  size="small"
                                />
                              }
                             {...interfaceTextProps("Edit the tags in this server audio file. Administrator access and write permission are required.")}/>
                            <Popup
                              content={interfaceText("Remove this item from the collection without deleting the shared file.")}
                              trigger={
                                <Button
                                  data-testid={`collection-item-remove-${index}`}
                                  negative
                                  onClick={async () => {
                                    try {
                                      await collectionsAPI.removeCollectionItem(
                                        selectedCollection.id,
                                        item.id,
                                      );
                                      await this.loadCollectionItems(
                                        selectedCollection.id,
                                      );
                                    } catch (error) {
                                      this.setState({ error: getErrorMessage(error) });
                                    }
                                  }}
                                  size="small"
                                >
                                  <LocalizedText source={"Remove"} /></Button>
                              }
                             {...interfaceTextProps("Remove this item from the collection without deleting the shared file.")}/>
                          </Table.Cell>
                        </Table.Row>
                      ))}
                    </Table.Body>
                  </Table>
                )}
                {selectedCollectionItems.length > COLLECTION_ITEM_PAGE_SIZE && (
                  <div className="collections-pagination">
                    <span>
                      {itemPageStart}–{itemPageEnd} <LocalizedText source={"of"} />{" "}{selectedCollectionItems.length}
                    </span>
                    <Popup
                      content={interfaceText("Show the previous page of collection items.")}
                      trigger={
                        <Button
                          aria-label={interfaceText("Previous collection items page")}
                          disabled={currentItemPage <= 1}
                          icon="chevron left"
                          onClick={() => this.setState({ collectionItemPage: currentItemPage - 1 })}
                          size="mini"
                         {...interfaceTextProps("Previous collection items page")}/>
                      }
                     {...interfaceTextProps("Show the previous page of collection items.")}/>
                    <Popup
                      content={interfaceText("Show the next page of collection items without rendering the entire collection at once.")}
                      trigger={
                        <Button
                          aria-label={interfaceText("Next collection items page")}
                          disabled={currentItemPage >= itemPages}
                          icon="chevron right"
                          onClick={() => this.setState({ collectionItemPage: currentItemPage + 1 })}
                          size="mini"
                         {...interfaceTextProps("Next collection items page")}/>
                      }
                     {...interfaceTextProps("Show the next page of collection items without rendering the entire collection at once.")}/>
                  </div>
                )}
              </div>

              <Segment
                data-testid="shares-list"
                style={{ marginTop: '1em' }}
              >
                <Header as="h4"><LocalizedText source={"Shares"} /></Header>
                {collectionShares.length === 0 ? (
                  <Message info><LocalizedText source={"No shares yet."} /></Message>
                ) : (
                  <Table>
                    <Table.Header>
                      <Table.Row>
                        <Table.HeaderCell><LocalizedText source={"Collection"} /></Table.HeaderCell>
                        <Table.HeaderCell><LocalizedText source={"Audience"} /></Table.HeaderCell>
                        <Table.HeaderCell><LocalizedText source={"Stream"} /></Table.HeaderCell>
                        <Table.HeaderCell><LocalizedText source={"Download"} /></Table.HeaderCell>
                      </Table.Row>
                    </Table.Header>
                    <Table.Body>
                      {collectionShares.map((share) => (
                        <Table.Row key={share.id}>
                          <Table.Cell>
                            {share.collection?.title ||
                              selectedCollection.title}
                          </Table.Cell>
                          <Table.Cell>
                            {share.audienceType === 'ShareGroup'
                              ? <LocalizedText source={"Group {audienceId}"} values={{ "audienceId": (share.audienceId) }} />
                              : share.audienceId}
                          </Table.Cell>
                          <Table.Cell>
                            {share.allowStream ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}
                          </Table.Cell>
                          <Table.Cell>
                            {share.allowDownload ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}
                          </Table.Cell>
                        </Table.Row>
                      ))}
                    </Table.Body>
                  </Table>
                )}
              </Segment>
            </Segment>
          )}

          {/* Create Collection Modal */}
          <Modal
            onClose={() =>
              this.setState({
                createModalOpen: false,
                newCollectionDescription: '',
                newCollectionTitle: '',
                newCollectionType: 'Playlist',
              })
            }
            open={createModalOpen}
          >
            <Modal.Header><LocalizedText source={"Create Collection"} /></Modal.Header>
            <Modal.Content>
              <Form>
                <Form.Field>
                  <label htmlFor="collection-type"><LocalizedText source={"Type"} /></label>
                  <Dropdown
                    data-testid="collections-type-select"
                    id="collection-type"
                    onChange={(event, { value }) =>
                      this.setState({ newCollectionType: value })
                    }
                    options={typeOptions}
                    selection
                    value={newCollectionType}
                  />
                </Form.Field>
                <Form.Input
                  data-testid="collections-title-input"
                  label={interfaceText("Title")}
                  onChange={(event) =>
                    this.setState({ newCollectionTitle: event.target.value })
                  }
                  placeholder={interfaceText("Enter collection title")}
                  value={newCollectionTitle}
                 {...interfaceTextProps("Title")}/>
                <Form.TextArea
                  label={interfaceText("Description")}
                  onChange={(event) =>
                    this.setState({
                      newCollectionDescription: event.target.value,
                    })
                  }
                  placeholder={interfaceText("Optional description")}
                  value={newCollectionDescription}
                 {...interfaceTextProps("Description")}/>
              </Form>
            </Modal.Content>
            <Modal.Actions>
              <TooltipButton
                onClick={() =>
                  this.setState({
                    createModalOpen: false,
                    newCollectionDescription: '',
                    newCollectionTitle: '',
                    newCollectionType: 'Playlist',
                  })
                }
                tooltip="Close the form and discard the collection details you entered."
              >
                <LocalizedText source={"Cancel"} /></TooltipButton>
              <TooltipButton
                data-testid="collections-create-submit"
                disabled={!newCollectionTitle.trim()}
                onClick={this.handleCreateCollection}
                primary
                tooltip="Save this collection so you can organize items here. Enter a title first to enable creation."
              >
                <LocalizedText source={"Create"} /></TooltipButton>
            </Modal.Actions>
          </Modal>

          {/* Share Collection Modal */}
          <Modal
            onClose={() => this.setState({ shareModalOpen: false })}
            open={shareModalOpen}
          >
            <Modal.Header><LocalizedText source={"Share Collection"} /></Modal.Header>
            <Modal.Content>
              {shareGroupsLoading ? (
                <LoaderSegment />
              ) : shareGroups.length === 0 ? (
                <Message warning><LocalizedText source={"No share groups available."} /></Message>
              ) : (
                <Form>
                  <Form.Field>
                    <label htmlFor="share-group"><LocalizedText source={"Share Group"} /></label>
                    <Dropdown
                      data-testid="share-audience-picker"
                      id="share-group"
                      onChange={(event, { value }) =>
                        this.setState({ shareAudienceId: value })
                      }
                      options={shareGroups.map((group) => ({
                        key: group.id,
                        text: group.name,
                        value: group.id,
                      }))}
                      selection
                      value={shareAudienceId}
                    />
                  </Form.Field>
                  <Form.Field>
                    <label htmlFor="share-allow-stream"><LocalizedText source={"Allow streaming"} /></label>
                    <input
                      checked={shareAllowStream}
                      data-testid="share-policy-stream"
                      id="share-allow-stream"
                      onChange={(event) =>
                        this.setState({
                          shareAllowStream: event.target.checked,
                        })
                      }
                      type="checkbox"
                    />
                  </Form.Field>
                  <Form.Field>
                    <label htmlFor="share-allow-download"><LocalizedText source={"Allow download"} /></label>
                    <input
                      checked={shareAllowDownload}
                      data-testid="share-policy-download"
                      id="share-allow-download"
                      onChange={(event) =>
                        this.setState({
                          shareAllowDownload: event.target.checked,
                        })
                      }
                      type="checkbox"
                    />
                  </Form.Field>
                </Form>
              )}
            </Modal.Content>
            <Modal.Actions>
              <TooltipButton
                onClick={() => this.setState({ shareModalOpen: false })}
                tooltip="Close this form without creating a share."
              >
                <LocalizedText source={"Cancel"} /></TooltipButton>
              <TooltipButton
                data-testid="share-create-submit"
                disabled={!shareAudienceId}
                onClick={this.handleCreateShare}
                primary
                tooltip="Share this collection with the selected group using the permissions below. Choose a group first to enable sharing."
              >
                <LocalizedText source={"Share"} /></TooltipButton>
            </Modal.Actions>
          </Modal>

          {/* Add Item Modal */}
          <Modal onClose={() => this.setState({ editItem: null })} open={Boolean(editItem)} size="small">
            <Modal.Header>{editFileTags ? <LocalizedText source={"Edit audio file tags"} /> : <LocalizedText source={"Edit collection display metadata"} />}</Modal.Header>
            <Modal.Content>
              <Form>
                {['title', 'artist', 'album'].map((field) => (
                  <Form.Input
                    key={field}
                    label={interfaceText(field[0].toUpperCase() + field.slice(1))}
                    onChange={(event) => this.setState({ editItem: { ...editItem, [field]: event.target.value } })}
                    value={editItem?.[field] || ''}
                  />
                ))}
              </Form>
            </Modal.Content>
            <Modal.Actions>
              <Popup content={interfaceText("Discard changes to this collection entry.")} trigger={
                <Button onClick={() => this.setState({ editItem: null })}><LocalizedText source={"Cancel"} /></Button>
              }  {...interfaceTextProps("Discard changes to this collection entry.")}/>
              <Popup content={interfaceText(editFileTags
                ? 'Write tags to the server audio file and update its collection references.'
                : 'Save this item’s display metadata without writing to the audio file.')} trigger={
                <Button
                  disabled={!editItem || !selectedCollection}
                  onClick={async () => {
                    try {
                      let shareScanStarted = true;
                      if (editFileTags) {
                        const response = await streaming.updatePlayerTags(editItem.contentId, {
                          album: editItem.album || '',
                          artist: editItem.artist || '',
                          title: editItem.title || editItem.fileName || '',
                        });
                        shareScanStarted = response.data?.shareScanStarted !== false;
                      } else {
                        await collectionsAPI.updateCollectionItem(selectedCollection.id, editItem.id, {
                          album: editItem.album || ' ',
                          artist: editItem.artist || ' ',
                          title: editItem.title || ' ',
                        });
                      }
                      await this.loadCollectionItems(selectedCollection.id);
                      this.setState({
                        editItem: null,
                        error: shareScanStarted ? null : interfaceText('Audio tags were saved, but the share scan could not start. Run a share scan to refresh the library.'),
                      });
                    } catch (saveError) {
                      this.setState({ error: getErrorMessage(saveError, 'Could not save display metadata') });
                    }
                  }}
                  primary
                ><LocalizedText source={"Save"} /></Button>
              } />
            </Modal.Actions>
          </Modal>

          <Modal
            onClose={() =>
              this.setState({
                addItemModalOpen: false,
                itemSearchQuery: '',
                itemSearchResults: [],
              })
            }
            open={addItemModalOpen}
          >
            <Modal.Header><LocalizedText source={"Add Item to"} />{" "}{selectedCollection?.title}</Modal.Header>
            <Modal.Content>
              <Form>
                <Form.Field>
                  <label htmlFor="collection-item-search">
                    <LocalizedText source={"Search for item"} /></label>
                  <Form.Input
                    data-testid="collection-item-search-input"
                    id="collection-item-search"
                    label={interfaceText("Search for item")}
                    loading={itemSearchLoading}
                    onChange={(event) => {
                      const query = event.target.value;
                      this.setState({ itemSearchQuery: query });
                      this.handleSearchItems(query);
                    }}
                    placeholder={interfaceText("Search by filename (e.g., sintel, aria, treasure)...")}
                    value={itemSearchQuery}
                   {...interfaceTextProps("Search for item")}/>
                </Form.Field>
                {itemSearchResults.length > 0 && (
                  <Form.Field>
                    <label htmlFor="collection-item-results">
                      <LocalizedText source={"Search Results"} /></label>
                    <Dropdown
                      data-testid="collection-item-results"
                      fluid
                      id="collection-item-results"
                      onChange={(event, { value }) => {
                        this.setState({ itemSearchQuery: value });
                      }}
                      options={itemSearchResults.map((item, index) => ({
                        key: item.contentId || index,
                        text: `${item.fileName || item.path} (${item.mediaKind || interfaceText('File')})`,
                        value: item.contentId,
                      }))}
                      placeholder={interfaceText("Select an item from search results")}
                      search
                      selection
                     {...interfaceTextProps("Select an item from search results")}/>
                  </Form.Field>
                )}
                {itemSearchQuery &&
                  itemSearchResults.length === 0 &&
                  !itemSearchLoading && (
                    <Message info>
                      <LocalizedText source={"No results found. You can still add the search query as a content ID."} /></Message>
                  )}
              </Form>
            </Modal.Content>
            <Modal.Actions>
              <TooltipButton
                onClick={() =>
                  this.setState({
                    addItemModalOpen: false,
                    itemSearchQuery: '',
                    itemSearchResults: [],
                  })
                }
                tooltip="Close item search and clear the current query and results."
              >
                <LocalizedText source={"Cancel"} /></TooltipButton>
              <TooltipButton
                data-testid="collection-add-item-submit"
                disabled={!itemSearchQuery.trim()}
                onClick={this.handleAddItem}
                primary
                tooltip="Add the selected search result or entered content ID to this collection. Enter a query first to enable."
              >
                <LocalizedText source={"Add Item"} /></TooltipButton>
            </Modal.Actions>
          </Modal>
        </Container>
      </div>
    );
  }
}
