import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';


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

const getErrorMessage = (error, fallback = 'The request failed. Try again.') =>
  getApiErrorMessage(error, { t: interfaceText }, fallback);

const normalizeContact = (contact) =>
  isObject(contact) && typeof contact.peerId === 'string' && contact.peerId.length > 0
    ? contact
    : null;

const withNavigate = (WrappedComponent) => {
  const RoutedComponent = (props) => {
    useInterfaceLanguage();
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
        throw new Error(interfaceText('Identity invite response did not include an invite link.'));
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
      let errorMessage = getErrorMessage(error, 'Failed to create invite');
      if (error.response) {
        const status = error.response.status;
        const url = error.response.config?.url || interfaceText('Unknown');
        const contentLength = error.response.headers?.['content-length'];

        console.error('[Contacts] Response status:', status);
        console.error('[Contacts] Response URL:', url);
        console.error('[Contacts] Response data:', error.response.data);

        // Check for empty body
        if (contentLength === '0' || contentLength === 0) {
          console.error(
            `[Contacts] HTTP ${status} with empty body from ${url}`,
          );
        }

        if (status === 400 && !error.response.data) {
          // 400 with empty body likely means CSRF validation failed or user identity missing
          errorMessage = interfaceText(
            'Request failed. This may be due to: missing CSRF token (try refreshing the page), user identity not available (configure Soulseek username or enable Identity & Friends), or invalid input.',
          );
        } else if (status === 401) {
          errorMessage = interfaceText('Authentication required. Please refresh the page.');
        } else if (status === 403) {
          errorMessage = interfaceText('Not authorized.');
        } else if (status === 404) {
          // 404 could be route mismatch (double prefix bug) or feature disabled
          if (url.includes('/api/v0/api/v0')) {
            errorMessage = interfaceText(
              'Endpoint not found: {url} (possible route mismatch - check browser console)',
              { url },
            );
          } else {
            errorMessage = interfaceText(
              'Identity & Friends feature is not enabled, or endpoint not found.',
            );
          }
        } else if (status >= 500) {
          errorMessage = interfaceText('Server error. Please check server logs.');
        }
      }

      this.setState({
        createInviteModalOpen: false,
        error:
          errorMessage ||
          interfaceText('Failed to create invite. Please ensure Identity & Friends is enabled and configured.'),
        inviteQrDataUrl: null,
      });
    }
  };

  handleDeleteContact = async (id) => {
    if (!window.confirm(interfaceText('Delete this contact?'))) return;
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
                  <LocalizedText source={"Retry Contacts"} /></Button>
              </Message>
            )}
            {loading ? (
              <LoaderSegment />
            ) : contactsLoadError && contacts.length === 0 ? (
              <Message negative data-testid="contacts-load-error">
                <Message.Header><LocalizedText source={"Contacts could not be loaded"} /></Message.Header>
                <p>{contactsLoadError}</p>
                <Button
                  onClick={this.loadContacts}
                  primary
                  tooltip="Retry loading your saved contacts."
                >
                  <LocalizedText source={"Retry Contacts"} /></Button>
              </Message>
            ) : contacts.length === 0 ? (
              <Segment placeholder>
                <Header icon>
                  <Icon name="users" />
                  <LocalizedText source={"No contacts yet"} /></Header>
                <Button
                  as="button"
                  data-testid="contacts-create-invite-empty"
                  onClick={this.handleCreateInvite}
                  primary
                  tooltip="Generate a 24-hour invite link and QR code so a friend can add you."
                >
                  <LocalizedText source={"Create Invite"} /></Button>
              </Segment>
            ) : (
              <Table>
                <Table.Header>
                  <Table.Row>
                    <Table.HeaderCell><LocalizedText source={"Nickname"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Peer ID"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Verified"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Last Seen"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Actions"} /></Table.HeaderCell>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {visibleContacts.map((contact) => (
                    <Table.Row
                      data-testid={`contact-row-${contact.nickname || contact.peerId.slice(0, 8)}`}
                      key={contact.id}
                    >
                      <Table.Cell>{contact.nickname || interfaceText('Unnamed')}</Table.Cell>
                      <Table.Cell>
                        <code style={{ fontSize: '0.85em' }}>
                          {contact.peerId.slice(0, 16)}...
                        </code>
                      </Table.Cell>
                      <Table.Cell>
                        {contact.verified ? (
                          <Label color="green"><LocalizedText source={"Verified"} /></Label>
                        ) : (
                          <Label><LocalizedText source={"Unverified"} /></Label>
                        )}
                      </Table.Cell>
                      <Table.Cell>
                        {contact.lastSeen
                          ? new Date(contact.lastSeen).toLocaleString(getRegionalLocale())
                          : <LocalizedText source={"Never"} />}
                      </Table.Cell>
                      <Table.Cell>
                        <Button.Group size="small">
                          <Popup
                            content={interfaceText("Open a private chat with this contact.")}
                            trigger={
                              <Button
                                aria-label={interfaceText('Chat with {contact}', {
                                  contact: contact.nickname || contact.peerId,
                                })}
                                icon="chat"
                                onClick={() => this.openChat(contact)}
                              />
                            }
                           {...interfaceTextProps("Open a private chat with this contact.")}/>
                          <Popup
                            content={interfaceText("Browse this contact's shared files.")}
                            trigger={
                              <Button
                                aria-label={interfaceText('Browse files shared by {contact}', {
                                  contact: contact.nickname || contact.peerId,
                                })}
                                icon="folder open"
                                onClick={() => this.browseContact(contact)}
                              />
                            }
                           {...interfaceTextProps("Browse this contact's shared files.")}/>
                          <Popup
                            content={interfaceText("Remove this saved contact.")}
                            trigger={
                              <Button
                                aria-label={interfaceText('Remove {contact} as a contact', {
                                  contact: contact.nickname || contact.peerId,
                                })}
                                icon="trash"
                                negative
                                onClick={() =>
                                  this.handleDeleteContact(contact.id)
                                }
                              />
                            }
                           {...interfaceTextProps("Remove this saved contact.")}/>
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
                  {contactPageStart}–{contactPageEnd} <LocalizedText source={"of"} />{" "}{contacts.length}
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
                <Message.Header><LocalizedText source={"Nearby discovery failed"} /></Message.Header>
                <p>{nearbyError}</p>
                <Button
                  onClick={this.loadNearby}
                  primary
                  tooltip="Try nearby peer discovery again."
                >
                  <LocalizedText source={"Retry Nearby"} /></Button>
              </Message>
            ) : nearby.length === 0 ? (
              <Segment placeholder>
                <Header icon>
                  <Icon name="wifi" />
                  <LocalizedText source={"No nearby peers found"} /></Header>
                <p><LocalizedText source={"Make sure you're on the same network and mDNS is working."} /></p>
                <Button
                  onClick={this.loadNearby}
                  tooltip="Query local-network discovery again to refresh the nearby peers list."
                >
                  <LocalizedText source={"Refresh"} /></Button>
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
                        <LocalizedText source={"Code:"} />{" "}<code>{peer.peerCode}</code>
                        <br />
                        <LocalizedText source={"Endpoint:"} />{" "}{peer.endpoint}
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
                        <LocalizedText source={"Add Contact"} /></Button>
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            )}
            {nearby.length > NEARBY_PAGE_SIZE && (
              <div className="contacts-pagination">
                <span>
                  {nearbyPageStart}–{nearbyPageEnd} <LocalizedText source={"of"} />{" "}{nearby.length}
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
              <LocalizedText source={"Contacts"} /><Header.Subheader><LocalizedText source={"Manage your peer contacts"} /></Header.Subheader>
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
              <LocalizedText source={"Create Invite"} /></Button>
            <Button
              as="button"
              data-testid="contacts-add-friend"
              onClick={() => this.setState({ addFriendModalOpen: true })}
              tooltip="Open the form to add a contact from an invite link or QR code."
            >
              <Icon name="user plus" />
              <LocalizedText source={"Add Friend"} /></Button>
            <Button
              onClick={this.loadNearby}
              tooltip="Query local-network discovery again to refresh the nearby peers list."
            >
              <Icon name="refresh" />
              <LocalizedText source={"Refresh Nearby"} /></Button>
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
            <Modal.Header><LocalizedText source={"Add Friend from Invite"} /></Modal.Header>
            <Modal.Content>
              <p><LocalizedText source={"Paste an invite link:"} /></p>
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
            <Modal.Header><LocalizedText source={"Add Nearby Contact"} /></Modal.Header>
            <Modal.Content>
              <p><LocalizedText source={"Choose a nickname for"} />{" "}{nearbyAddPeer?.displayName || nearbyAddPeer?.peerId}.</p>
              <Form>
                <Form.Field>
                  <label htmlFor="nearby-contact-nickname"><LocalizedText source={"Nickname"} /></label>
                  <input
                    autoFocus
                    data-testid="nearby-contact-nickname"
                    id="nearby-contact-nickname"
                    onChange={(event) => this.setState({ nearbyNickname: event.target.value })}
                    placeholder={interfaceText("Contact name")}
                    type="text"
                    value={nearbyNickname}
                   {...interfaceTextProps("Nickname")}/>
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
                <LocalizedText source={"Cancel"} /></Button>
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
                <LocalizedText source={"Add Contact"} /></Button>
            </Modal.Actions>
          </Modal>

          {/* Create Invite Modal */}
          <Modal
            onClose={() => this.setState({ createInviteModalOpen: false })}
            open={createInviteModalOpen}
          >
            <Modal.Header><LocalizedText source={"Invite Created"} /></Modal.Header>
            <Modal.Content>
              <p><LocalizedText source={"Share this invite link:"} /></p>
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
                  <LocalizedText source={"Friend Code:"} />{' '}
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
                    alt={interfaceText("QR invite code")}
                    data-testid="contacts-invite-qr"
                    src={inviteQrDataUrl}
                    style={{
                      height: 192,
                      imageRendering: 'pixelated',
                      width: 192,
                    }}
                   {...interfaceTextProps("QR invite code")}/>
                </Segment>
              )}
            </Modal.Content>
            <Modal.Actions>
              <Button
                onClick={() => this.setState({ createInviteModalOpen: false })}
                tooltip="Close the invite and return to your contacts list."
              >
                <LocalizedText source={"Close"} /></Button>
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
          interfaceText('This browser does not support QR scanning from images yet.'),
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
          throw new Error(interfaceText('No slskdN invite QR code was found in that image.'));
        }

        this.setState({ inviteLink, scanError: null });
      } finally {
        bitmap.close?.();
      }
    } catch (error) {
      this.setState({ scanError: getErrorMessage(error, 'QR scan failed.') });
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
          <label><LocalizedText source={"Invite Link:"} /></label>
          <input
            data-testid="contacts-add-invite-input"
            onChange={(e) => this.setState({ inviteLink: e.target.value })}
            placeholder={interfaceText("slskdn://invite/...")}
            style={{ padding: '0.5em', width: '100%' }}
            type="text"
            value={this.state.inviteLink}
           {...interfaceTextProps("slskdn://invite/...")}/>
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
            title={interfaceText("Scan a QR invite image from your camera or photo library.")}
            type="button"
           {...interfaceTextProps("Scan a QR invite image from your camera or photo library.")}>
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
          <label><LocalizedText source={"Nickname:"} /></label>
          <input
            data-testid="contacts-contact-nickname"
            onChange={(e) => this.setState({ nickname: e.target.value })}
            placeholder={interfaceText("Friend's name")}
            style={{ padding: '0.5em', width: '100%' }}
            type="text"
            value={this.state.nickname}
           {...interfaceTextProps("Friend's name")}/>
        </div>
        <Button
          data-testid="contacts-add-invite-submit"
          primary
          type="submit"
          tooltip="Validate the invite link and save this peer to your contacts."
        >
          <LocalizedText source={"Add Contact"} /></Button>
      </form>
    );
  }
}

export default withNavigate(Contacts);
