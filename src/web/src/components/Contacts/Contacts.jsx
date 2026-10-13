import { getRegionalLocale } from '../../lib/regionalFormat';
import * as identityAPI from '../../lib/identity';
import ErrorSegment from '../Shared/ErrorSegment';
import LoaderSegment from '../Shared/LoaderSegment';
import TooltipButton from '../Shared/TooltipButton';
import QRCode from 'qrcode';
import React, { Component } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Form,
  Header,
  Icon,
  Label,
  List,
  Message,
  Modal,
  Popup,
  Segment,
  Tab,
  Table,
} from 'semantic-ui-react';

const Button = TooltipButton;

const asArray = (value) => (Array.isArray(value) ? value : []);
const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);
const CONTACT_PAGE_SIZE = 100;
const NEARBY_PAGE_SIZE = 100;

const getErrorMessage = (error, fallback = 'Request failed') => {
  const data = error?.response?.data;

  if (typeof data === 'string') return data;
  if (isObject(data)) {
    return data.detail ||
      data.message ||
      data.error ||
      data.title ||
      JSON.stringify(data);
  }

  return error?.message || fallback;
};

const normalizeContact = (contact) =>
  isObject(contact) && typeof contact.peerId === 'string' && contact.peerId.length > 0
    ? contact
    : null;

const withNavigate = (WrappedComponent) => {
  const RoutedComponent = (props) => {
    const navigate = useNavigate();
    return (
      <WrappedComponent
        {...props}
        navigate={navigate}
      />
    );
  };

  RoutedComponent.displayName = `withNavigate(${WrappedComponent.displayName || WrappedComponent.name || 'Component'})`;
  return RoutedComponent;
};

class Contacts extends Component {
  state = {
    activeTab: 0,
    addFriendModalOpen: false,
    contactPage: 1,
    contacts: [],
    contactsLoadError: null,
    createInviteModalOpen: false,
    error: null,
    inviteFriendCode: null,
    inviteLink: null,
    inviteQrDataUrl: null,
    loading: true,
    nearby: [],
    nearbyAddError: null,
    nearbyAddPeer: null,
    nearbyAdding: false,
    nearbyNickname: '',
    nearbyError: null,
    nearbyLoading: false,
    nearbyPage: 1,
  };

  componentDidMount() {
    this.loadContacts();
    this.loadNearby();
  }

  loadContacts = async () => {
    try {
      this.setState({ contactsLoadError: null, error: null, loading: true });
      const response = await identityAPI.getContacts();
      this.setState({
        contactPage: 1,
        contacts: asArray(response.data).map(normalizeContact).filter(Boolean),
        contactsLoadError: null,
        loading: false,
      });
    } catch (error) {
      // If 401/403/404, feature not enabled or not authenticated - return empty list
      if (
        error.response?.status === 401 ||
        error.response?.status === 403 ||
        error.response?.status === 404
      ) {
        this.setState({
          contacts: [],
          contactsLoadError: null,
          error: null,
          loading: false,
        });
      } else {
        this.setState({
          contactsLoadError: getErrorMessage(error, 'Failed to load contacts.'),
          loading: false,
        });
      }
    }
  };

  loadNearby = async () => {
    try {
      this.setState({ nearbyError: null, nearbyLoading: true });
      const response = await identityAPI.getNearby();
      this.setState({
        nearby: asArray(response.data),
        nearbyError: null,
        nearbyLoading: false,
        nearbyPage: 1,
      });
    } catch (error) {
      this.setState({
        nearbyError: getErrorMessage(error, 'Nearby peer discovery failed.'),
        nearbyLoading: false,
      });
    }
  };

  handleAddFromInvite = async (inviteLink, nickname) => {
    try {
      await identityAPI.addContactFromInvite({ inviteLink, nickname });
      this.setState({ addFriendModalOpen: false });
      await this.loadContacts();
    } catch (error) {
      this.setState({ error: getErrorMessage(error, 'Failed to add contact') });
    }
  };

  handleAddFromDiscovery = async (peerId, nickname) => {
    try {
      this.setState({ nearbyAddError: null, nearbyAdding: true });
      await identityAPI.addContactFromDiscovery({ nickname, peerId });
      this.setState({
        nearbyAddError: null,
        nearbyAddPeer: null,
        nearbyAdding: false,
        nearbyNickname: '',
      });
      await this.loadContacts();
    } catch (error) {
      this.setState({
        nearbyAddError: getErrorMessage(error, 'Failed to add contact'),
        nearbyAdding: false,
      });
    }
  };

  handleCreateInvite = async () => {
    try {
      const response = await identityAPI.createInvite({ expiresInHours: 24 });
      const data = isObject(response.data) ? response.data : {};
      const inviteLink = typeof data.inviteLink === 'string' ? data.inviteLink : '';
      if (!inviteLink) {
        throw new Error('Identity invite response did not include an invite link.');
      }

      const inviteQrDataUrl = inviteLink
        ? await QRCode.toDataURL(inviteLink, {
            errorCorrectionLevel: 'M',
            margin: 2,
            scale: 6,
          })
        : null;
      this.setState({
        createInviteModalOpen: true,
        error: null,
        inviteFriendCode: typeof data.friendCode === 'string' ? data.friendCode : null,
        inviteLink,
        inviteQrDataUrl,
      });
    } catch (error) {
      console.error('[Contacts] Create invite error:', error);
      // Extract error message from response (supports ProblemDetails, object with message/error, or string)
      let errorMessage = error.message || 'Failed to create invite';
      if (error.response) {
        const status = error.response.status;
        const url = error.response.config?.url || 'unknown';
        const contentLength = error.response.headers['content-length'];

        console.error('[Contacts] Response status:', status);
        console.error('[Contacts] Response URL:', url);
        console.error('[Contacts] Response data:', error.response.data);

        // Check for empty body
        if (contentLength === '0' || contentLength === 0) {
          console.error(
            `[Contacts] HTTP ${status} with empty body from ${url}`,
          );
        }

        if (error.response.data) {
          if (typeof error.response.data === 'string') {
            errorMessage = error.response.data;
          } else if (error.response.data.detail) {
            errorMessage = error.response.data.detail; // ProblemDetails format
          } else if (error.response.data.message) {
            errorMessage = error.response.data.message;
          } else if (error.response.data.error) {
            errorMessage = error.response.data.error;
          } else if (error.response.data.title) {
            errorMessage = error.response.data.title; // ProblemDetails title as fallback
          } else {
            errorMessage = JSON.stringify(error.response.data);
          }
        } else if (status === 400) {
          // 400 with empty body likely means CSRF validation failed or user identity missing
          errorMessage =
            'Request failed. This may be due to: missing CSRF token (try refreshing the page), user identity not available (configure Soulseek username or enable Identity & Friends), or invalid input.';
        } else if (status === 401) {
          errorMessage = 'Authentication required. Please refresh the page.';
        } else if (status === 403) {
          errorMessage = 'Not authorized.';
        } else if (status === 404) {
          // 404 could be route mismatch (double prefix bug) or feature disabled
          if (url.includes('/api/v0/api/v0')) {
            errorMessage = `Endpoint not found: ${url} (possible route mismatch - check browser console)`;
          } else {
            errorMessage =
              'Identity & Friends feature is not enabled, or endpoint not found.';
          }
        } else if (status >= 500) {
          errorMessage = 'Server error. Please check server logs.';
        }
      }

      this.setState({
        createInviteModalOpen: false,
        error:
          errorMessage ||
          'Failed to create invite. Please ensure Identity & Friends is enabled and configured.',
        inviteQrDataUrl: null,
      });
    }
  };

  handleDeleteContact = async (id) => {
    if (!window.confirm('Delete this contact?')) return;
    try {
      await identityAPI.deleteContact(id);
      await this.loadContacts();
    } catch (error) {
      this.setState({ error: getErrorMessage(error, 'Failed to delete contact') });
    }
  };

  openChat = (contact) => {
    const username = contact.nickname || contact.peerId;
    this.props.navigate(`/chat?user=${encodeURIComponent(username)}`, {
      state: { user: username },
    });
  };

  browseContact = (contact) => {
    const username = contact.nickname || contact.peerId;
    this.props.navigate(`/browse?user=${encodeURIComponent(username)}`, {
      state: { user: username },
    });
  };

  render() {
    const {
      activeTab,
      addFriendModalOpen,
      contactPage,
      contacts,
      contactsLoadError,
      createInviteModalOpen,
      error,
      inviteFriendCode,
      inviteLink,
      inviteQrDataUrl,
      loading,
      nearby,
      nearbyAddError,
      nearbyAddPeer,
      nearbyAdding,
      nearbyError,
      nearbyLoading,
      nearbyNickname,
      nearbyPage,
    } = this.state;
    const contactPages = Math.max(1, Math.ceil(contacts.length / CONTACT_PAGE_SIZE));
    const currentContactPage = Math.min(contactPage, contactPages);
    const contactStart = (currentContactPage - 1) * CONTACT_PAGE_SIZE;
    const visibleContacts = contacts.slice(contactStart, contactStart + CONTACT_PAGE_SIZE);
    const contactPageStart = contacts.length === 0 ? 0 : contactStart + 1;
    const contactPageEnd = Math.min(contactStart + CONTACT_PAGE_SIZE, contacts.length);
    const nearbyPages = Math.max(1, Math.ceil(nearby.length / NEARBY_PAGE_SIZE));
    const currentNearbyPage = Math.min(nearbyPage, nearbyPages);
    const nearbyStart = (currentNearbyPage - 1) * NEARBY_PAGE_SIZE;
    const visibleNearby = nearby.slice(nearbyStart, nearbyStart + NEARBY_PAGE_SIZE);
    const nearbyPageStart = nearby.length === 0 ? 0 : nearbyStart + 1;
    const nearbyPageEnd = Math.min(nearbyStart + NEARBY_PAGE_SIZE, nearby.length);

    const panes = [
      {
        menuItem: 'All Contacts',
        render: () => (
          <Tab.Pane>
            {contactsLoadError && contacts.length > 0 && (
              <Message warning data-testid="contacts-load-warning">
                <p>{contactsLoadError}</p>
                <Button
                  onClick={this.loadContacts}
                  tooltip="Try loading the latest contacts again."
                >
                  Retry Contacts
                </Button>
              </Message>
            )}
            {loading ? (
              <LoaderSegment />
            ) : contactsLoadError && contacts.length === 0 ? (
              <Message negative data-testid="contacts-load-error">
                <Message.Header>Contacts could not be loaded</Message.Header>
                <p>{contactsLoadError}</p>
                <Button
                  onClick={this.loadContacts}
                  primary
                  tooltip="Retry loading your saved contacts."
                >
                  Retry Contacts
                </Button>
              </Message>
            ) : contacts.length === 0 ? (
              <Segment placeholder>
                <Header icon>
                  <Icon name="users" />
                  No contacts yet
                </Header>
                <Button
                  as="button"
                  data-testid="contacts-create-invite-empty"
                  onClick={this.handleCreateInvite}
                  primary
                  tooltip="Generate a 24-hour invite link and QR code so a friend can add you."
                >
                  Create Invite
                </Button>
              </Segment>
            ) : (
              <Table>
                <Table.Header>
                  <Table.Row>
                    <Table.HeaderCell>Nickname</Table.HeaderCell>
                    <Table.HeaderCell>Peer ID</Table.HeaderCell>
                    <Table.HeaderCell>Verified</Table.HeaderCell>
                    <Table.HeaderCell>Last Seen</Table.HeaderCell>
                    <Table.HeaderCell>Actions</Table.HeaderCell>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {visibleContacts.map((contact) => (
                    <Table.Row
                      data-testid={`contact-row-${contact.nickname || contact.peerId.slice(0, 8)}`}
                      key={contact.id}
                    >
                      <Table.Cell>{contact.nickname || 'Unnamed'}</Table.Cell>
                      <Table.Cell>
                        <code style={{ fontSize: '0.85em' }}>
                          {contact.peerId.slice(0, 16)}...
                        </code>
                      </Table.Cell>
                      <Table.Cell>
                        {contact.verified ? (
                          <Label color="green">Verified</Label>
                        ) : (
                          <Label>Unverified</Label>
                        )}
                      </Table.Cell>
                      <Table.Cell>
                        {contact.lastSeen
                          ? new Date(contact.lastSeen).toLocaleString(getRegionalLocale())
                          : 'Never'}
                      </Table.Cell>
                      <Table.Cell>
                        <Button.Group size="small">
                          <Popup
                            content="Open a private chat with this contact."
                            trigger={
                              <Button
                                aria-label={`Chat with ${contact.nickname || contact.peerId}`}
                                icon="chat"
                                onClick={() => this.openChat(contact)}
                              />
                            }
                          />
                          <Popup
                            content="Browse this contact's shared files."
                            trigger={
                              <Button
                                aria-label={`Browse files shared by ${contact.nickname || contact.peerId}`}
                                icon="folder open"
                                onClick={() => this.browseContact(contact)}
                              />
                            }
                          />
                          <Popup
                            content="Remove this saved contact."
                            trigger={
                              <Button
                                aria-label={`Remove ${contact.nickname || contact.peerId} as a contact`}
                                icon="trash"
                                negative
                                onClick={() =>
                                  this.handleDeleteContact(contact.id)
                                }
                              />
                            }
                          />
                        </Button.Group>
                      </Table.Cell>
                    </Table.Row>
                  ))}
                </Table.Body>
              </Table>
            )}
            {contacts.length > CONTACT_PAGE_SIZE && (
              <div className="contacts-pagination">
                <span>
                  {contactPageStart}–{contactPageEnd} of {contacts.length}
                </span>
                <Button
                  disabled={currentContactPage <= 1}
                  icon="chevron left"
                  onClick={() => this.setState({ contactPage: currentContactPage - 1 })}
                  size="mini"
                  tooltip="Show the previous page of contacts."
                />
                <Button
                  disabled={currentContactPage >= contactPages}
                  icon="chevron right"
                  onClick={() => this.setState({ contactPage: currentContactPage + 1 })}
                  size="mini"
                  tooltip="Show the next page of contacts without rendering the entire contact list at once."
                />
              </div>
            )}
          </Tab.Pane>
        ),
      },
      {
        menuItem: 'Nearby',
        render: () => (
          <Tab.Pane>
            {nearbyLoading ? (
              <LoaderSegment />
            ) : nearbyError ? (
              <Message negative data-testid="contacts-nearby-error">
                <Message.Header>Nearby discovery failed</Message.Header>
                <p>{nearbyError}</p>
                <Button
                  onClick={this.loadNearby}
                  primary
                  tooltip="Try nearby peer discovery again."
                >
                  Retry Nearby
                </Button>
              </Message>
            ) : nearby.length === 0 ? (
              <Segment placeholder>
                <Header icon>
                  <Icon name="wifi" />
                  No nearby peers found
                </Header>
                <p>Make sure you're on the same network and mDNS is working.</p>
                <Button
                  onClick={this.loadNearby}
                  tooltip="Query local-network discovery again to refresh the nearby peers list."
                >
                  Refresh
                </Button>
              </Segment>
            ) : (
              <List
                divided
                relaxed
              >
                {visibleNearby.map((peer, index) => (
                  <List.Item key={index}>
                    <List.Content>
                      <List.Header>{peer.displayName}</List.Header>
                      <List.Description>
                        Code: <code>{peer.peerCode}</code>
                        <br />
                        Endpoint: {peer.endpoint}
                      </List.Description>
                      <Button
                        onClick={() => this.setState({
                          nearbyAddError: null,
                          nearbyAddPeer: peer,
                          nearbyNickname: peer.displayName || '',
                        })}
                        primary
                        size="small"
                        style={{ marginTop: '0.5em' }}
                        tooltip="Choose a nickname and save this nearby peer as a contact."
                      >
                        Add Contact
                      </Button>
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            )}
            {nearby.length > NEARBY_PAGE_SIZE && (
              <div className="contacts-pagination">
                <span>
                  {nearbyPageStart}–{nearbyPageEnd} of {nearby.length}
                </span>
                <Button
                  disabled={currentNearbyPage <= 1}
                  icon="chevron left"
                  onClick={() => this.setState({ nearbyPage: currentNearbyPage - 1 })}
                  size="mini"
                  tooltip="Show the previous page of nearby peers."
                />
                <Button
                  disabled={currentNearbyPage >= nearbyPages}
                  icon="chevron right"
                  onClick={() => this.setState({ nearbyPage: currentNearbyPage + 1 })}
                  size="mini"
                  tooltip="Show the next page of nearby peers without rendering the entire discovery list at once."
                />
              </div>
            )}
          </Tab.Pane>
        ),
      },
    ];

    return (
      <div data-testid="contacts-root">
        <Container>
          <Header as="h1">
            <Icon name="address book" />
            <Header.Content>
              Contacts
              <Header.Subheader>Manage your peer contacts</Header.Subheader>
            </Header.Content>
          </Header>

          {error && <ErrorSegment caption={error} />}

          <div style={{ marginBottom: '1em' }}>
            {/* Always render Create Invite button - not conditional on loading state */}
            <Button
              as="button"
              data-testid="contacts-create-invite"
              onClick={this.handleCreateInvite}
              primary
              tooltip="Generate a 24-hour invite link and QR code so a friend can add you."
            >
              <Icon name="plus" />
              Create Invite
            </Button>
            <Button
              as="button"
              data-testid="contacts-add-friend"
              onClick={() => this.setState({ addFriendModalOpen: true })}
              tooltip="Open the form to add a contact from an invite link or QR code."
            >
              <Icon name="user plus" />
              Add Friend
            </Button>
            <Button
              onClick={this.loadNearby}
              tooltip="Query local-network discovery again to refresh the nearby peers list."
            >
              <Icon name="refresh" />
              Refresh Nearby
            </Button>
          </div>

          <Tab
            activeIndex={activeTab}
            onTabChange={(e, { activeIndex }) =>
              this.setState({ activeTab: activeIndex })
            }
            panes={panes}
          />

          {/* Add Friend Modal */}
          <Modal
            onClose={() => this.setState({ addFriendModalOpen: false })}
            open={addFriendModalOpen}
          >
            <Modal.Header>Add Friend from Invite</Modal.Header>
            <Modal.Content>
              <p>Paste an invite link:</p>
              <AddFriendForm
                onSubmit={(inviteLink, nickname) => {
                  this.handleAddFromInvite(inviteLink, nickname);
                }}
              />
            </Modal.Content>
          </Modal>

          <Modal
            data-testid="nearby-contact-dialog"
            closeIcon={false}
            onClose={() => this.setState({
              nearbyAddError: null,
              nearbyAddPeer: null,
              nearbyNickname: '',
            })}
            open={Boolean(nearbyAddPeer)}
          >
            <Modal.Header>Add Nearby Contact</Modal.Header>
            <Modal.Content>
              <p>Choose a nickname for {nearbyAddPeer?.displayName || nearbyAddPeer?.peerId}.</p>
              <Form>
                <Form.Field>
                  <label htmlFor="nearby-contact-nickname">Nickname</label>
                  <input
                    autoFocus
                    data-testid="nearby-contact-nickname"
                    id="nearby-contact-nickname"
                    onChange={(event) => this.setState({ nearbyNickname: event.target.value })}
                    placeholder="Contact name"
                    type="text"
                    value={nearbyNickname}
                  />
                </Form.Field>
              </Form>
              {nearbyAddError && (
                <Message negative data-testid="nearby-contact-add-error">
                  {nearbyAddError}
                </Message>
              )}
            </Modal.Content>
            <Modal.Actions>
              <Button
                disabled={nearbyAdding}
                onClick={() => this.setState({
                  nearbyAddError: null,
                  nearbyAddPeer: null,
                  nearbyNickname: '',
                })}
                tooltip="Close this dialog without adding the contact."
              >
                Cancel
              </Button>
              <Button
                data-testid="nearby-contact-add-submit"
                disabled={!nearbyNickname.trim() || nearbyAdding}
                loading={nearbyAdding}
                onClick={() => this.handleAddFromDiscovery(
                  nearbyAddPeer.peerId,
                  nearbyNickname.trim(),
                )}
                primary
                tooltip="Save this peer as a contact using the nickname above."
              >
                Add Contact
              </Button>
            </Modal.Actions>
          </Modal>

          {/* Create Invite Modal */}
          <Modal
            onClose={() => this.setState({ createInviteModalOpen: false })}
            open={createInviteModalOpen}
          >
            <Modal.Header>Invite Created</Modal.Header>
            <Modal.Content>
              <p>Share this invite link:</p>
              <div style={{ marginBottom: '1em' }}>
                <input
                  data-testid="contacts-invite-output"
                  onClick={(e) => e.target.select()}
                  readOnly
                  style={{ padding: '0.5em', width: '100%' }}
                  value={inviteLink || ''}
                />
              </div>
              {inviteFriendCode && (
                <p>
                  Friend Code:{' '}
                  <code data-testid="contacts-invite-friend-code">
                    {inviteFriendCode}
                  </code>
                </p>
              )}
              {inviteQrDataUrl && (
                <Segment
                  basic
                  compact
                  textAlign="center"
                >
                  <img
                    alt="QR invite code"
                    data-testid="contacts-invite-qr"
                    src={inviteQrDataUrl}
                    style={{
                      height: 192,
                      imageRendering: 'pixelated',
                      width: 192,
                    }}
                  />
                </Segment>
              )}
            </Modal.Content>
            <Modal.Actions>
              <Button
                onClick={() => this.setState({ createInviteModalOpen: false })}
                tooltip="Close the invite and return to your contacts list."
              >
                Close
              </Button>
            </Modal.Actions>
          </Modal>
        </Container>
      </div>
    );
  }
}

class AddFriendForm extends Component {
  fileInputRef = React.createRef();

  state = {
    inviteLink: '',
    nickname: '',
    scanError: null,
    scanning: false,
  };

  handleQrFileSelected = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    this.setState({ scanError: null, scanning: true });
    try {
      if (!('BarcodeDetector' in window) || !window.createImageBitmap) {
        throw new Error(
          'This browser does not support QR scanning from images yet.',
        );
      }

      const detector = new window.BarcodeDetector({ formats: ['qr_code'] });
      const bitmap = await window.createImageBitmap(file);
      try {
        const codes = await detector.detect(bitmap);
        const inviteLink = codes.find((code) =>
          code.rawValue?.startsWith('slskdn://invite/'),
        )?.rawValue;

        if (!inviteLink) {
          throw new Error('No slskdN invite QR code was found in that image.');
        }

        this.setState({ inviteLink, scanError: null });
      } finally {
        bitmap.close?.();
      }
    } catch (error) {
      this.setState({ scanError: error.message || 'QR scan failed.' });
    } finally {
      event.target.value = '';
      this.setState({ scanning: false });
    }
  };

  handleSubmit = (e) => {
    e.preventDefault();
    if (this.state.inviteLink && this.state.nickname) {
      this.props.onSubmit(this.state.inviteLink, this.state.nickname);
    }
  };

  render() {
    return (
      <form onSubmit={this.handleSubmit}>
        <div style={{ marginBottom: '1em' }}>
          <label>Invite Link:</label>
          <input
            data-testid="contacts-add-invite-input"
            onChange={(e) => this.setState({ inviteLink: e.target.value })}
            placeholder="slskdn://invite/..."
            style={{ padding: '0.5em', width: '100%' }}
            type="text"
            value={this.state.inviteLink}
          />
          <input
            accept="image/*"
            data-testid="contacts-add-invite-qr-file"
            onChange={this.handleQrFileSelected}
            ref={this.fileInputRef}
            style={{ display: 'none' }}
            type="file"
          />
          <Button
            data-testid="contacts-scan-invite-qr"
            disabled={this.state.scanning}
            icon
            onClick={() => this.fileInputRef.current?.click()}
            title="Scan a QR invite image from your camera or photo library."
            type="button"
          >
            <Icon name="qrcode" />
          </Button>
          {this.state.scanError && (
            <p
              data-testid="contacts-qr-scan-error"
              style={{ color: '#9f3a38', marginTop: '0.5em' }}
            >
              {this.state.scanError}
            </p>
          )}
        </div>
        <div style={{ marginBottom: '1em' }}>
          <label>Nickname:</label>
          <input
            data-testid="contacts-contact-nickname"
            onChange={(e) => this.setState({ nickname: e.target.value })}
            placeholder="Friend's name"
            style={{ padding: '0.5em', width: '100%' }}
            type="text"
            value={this.state.nickname}
          />
        </div>
        <Button
          data-testid="contacts-add-invite-submit"
          primary
          type="submit"
          tooltip="Validate the invite link and save this peer to your contacts."
        >
          Add Contact
        </Button>
      </form>
    );
  }
}

export default withNavigate(Contacts);
