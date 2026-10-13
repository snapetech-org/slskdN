import { getRegionalLocale } from '../../lib/regionalFormat';
import * as collectionsAPI from '../../lib/collections';
import * as identityAPI from '../../lib/identity';
import ErrorSegment from '../Shared/ErrorSegment';
import LoaderSegment from '../Shared/LoaderSegment';
import TooltipButton from '../Shared/TooltipButton';
import React, { Component } from 'react';
import {
  Container,
  Dropdown,
  Form,
  Header,
  Icon,
  List,
  Message,
  Modal,
  Segment,
  Table,
} from 'semantic-ui-react';

const Button = TooltipButton;

const asArray = (value) => (Array.isArray(value) ? value : []);
const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);

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

export default class ShareGroups extends Component {
  state = {
    addMemberModalOpen: false,
    contacts: [],
    createModalOpen: false,
    error: null,
    loading: true,
    memberDetails: [],
    memberDetailsError: null,
    memberDetailsGroup: null,
    memberDetailsLoading: false,
    memberDetailsModalOpen: false,
    newGroupName: '',
    selectedContactId: null,
    selectedGroup: null,
    selectedUserId: null,
    shareGroups: [],
    usePeerId: true,
  };

  memberDetailsRequestId = 0;

  componentDidMount() {
    this.loadData();
  }

  componentWillUnmount() {
    this.memberDetailsRequestId += 1;
  }

  loadData = async () => {
    try {
      this.setState({ error: null, loading: true });
      const [groupsRes, contactsRes] = await Promise.all([
        collectionsAPI.getShareGroups().catch((error) => {
          // If 401/403/404, feature not enabled or not authenticated - return empty list
          // 400 errors might have useful messages, so let them through
          if (
            error.response?.status === 401 ||
            error.response?.status === 403 ||
            error.response?.status === 404
          ) {
            return { data: [] };
          }

          throw error;
        }),
        identityAPI.getContacts().catch(() => ({ data: [] })), // Gracefully handle if Identity not enabled
      ]);
      this.setState({
        contacts: asArray(contactsRes.data),
        loading: false,
        shareGroups: asArray(groupsRes.data),
      });
    } catch (error) {
      // Extract error message from response
      let errorMessage = error.message;
      if (error.response?.data) {
        if (typeof error.response.data === 'string') {
          errorMessage = error.response.data;
        } else if (error.response.data.message) {
          errorMessage = error.response.data.message;
        } else if (error.response.data.error) {
          errorMessage = error.response.data.error;
        } else {
          errorMessage = JSON.stringify(error.response.data);
        }
      }

      // Only suppress errors for 401/403/404 (auth/feature disabled)
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

  handleCreateGroup = async () => {
    try {
      await collectionsAPI.createShareGroup({ name: this.state.newGroupName });
      this.setState({ createModalOpen: false, error: null, newGroupName: '' });
      await this.loadData();
    } catch (error) {
      console.error('[ShareGroups] Create group error:', error);
      // Extract error message from response (supports ProblemDetails, object with message/error, or string)
      let errorMessage = error.message || 'Failed to create share group';
      if (error.response) {
        const status = error.response.status;
        const url = error.response.config?.url || 'unknown';
        const contentLength = error.response.headers['content-length'];

        console.error('[ShareGroups] Response status:', status);
        console.error('[ShareGroups] Response URL:', url);
        console.error('[ShareGroups] Response data:', error.response.data);

        // Check for empty body
        if (contentLength === '0' || contentLength === 0) {
          console.error(
            `[ShareGroups] HTTP ${status} with empty body from ${url}`,
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
              'Collections sharing feature is not enabled, or endpoint not found.';
          }
        } else if (status >= 500) {
          errorMessage = 'Server error. Please check server logs.';
        }
      }

      this.setState({
        error:
          errorMessage ||
          'Failed to create share group. Please configure Soulseek username or enable Identity & Friends.',
      });
    }
  };

  handleAddMember = async () => {
    if (!this.state.selectedGroup) return;

    try {
      const data =
        this.state.usePeerId && this.state.selectedContactId
          ? { peerId: this.state.selectedContactId }
          : {
              userId: this.state.selectedUserId || this.state.selectedContactId,
            };

      await collectionsAPI.addShareGroupMember(
        this.state.selectedGroup.id,
        data,
      );
      this.setState({
        addMemberModalOpen: false,
        error: null,
        selectedContactId: null,
        selectedUserId: null,
      });
      await this.loadData();
    } catch (error) {
      // Extract error message from response (supports ProblemDetails, object with message/error, or string)
      let errorMessage = error.message;
      if (error.response?.data) {
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
      }

      this.setState({
        error:
          errorMessage ||
          'Failed to add member. Please configure Soulseek username or enable Identity & Friends.',
      });
    }
  };

  handleDeleteGroup = async (id) => {
    if (!window.confirm('Delete this share group?')) return;
    try {
      await collectionsAPI.deleteShareGroup(id);
      await this.loadData();
    } catch (error) {
      this.setState({ error: getErrorMessage(error, 'Failed to delete share group') });
    }
  };

  handleRemoveMember = async (groupId, userId) => {
    if (!window.confirm('Remove this member?')) return;
    try {
      await collectionsAPI.removeShareGroupMember(groupId, userId);
      await this.loadData();
    } catch (error) {
      this.setState({ error: getErrorMessage(error, 'Failed to remove member') });
    }
  };

  handleViewMembers = async (group) => {
    const requestId = ++this.memberDetailsRequestId;
    this.setState({
      memberDetails: [],
      memberDetailsError: null,
      memberDetailsGroup: group,
      memberDetailsLoading: true,
      memberDetailsModalOpen: true,
    });

    try {
      const membersRes = await collectionsAPI.getShareGroupMembers(
        group.id,
        true,
      );
      if (requestId !== this.memberDetailsRequestId) return;
      this.setState({
        memberDetails: asArray(membersRes.data),
        memberDetailsLoading: false,
      });
    } catch (error) {
      if (requestId !== this.memberDetailsRequestId) return;
      this.setState({
        memberDetailsError: getErrorMessage(error, 'Failed to load group members'),
        memberDetailsLoading: false,
      });
    }
  };

  closeMemberDetails = () => {
    this.memberDetailsRequestId += 1;
    this.setState({
      memberDetails: [],
      memberDetailsError: null,
      memberDetailsGroup: null,
      memberDetailsLoading: false,
      memberDetailsModalOpen: false,
    });
  };

  render() {
    const {
      addMemberModalOpen,
      contacts,
      createModalOpen,
      error,
      loading,
      memberDetails,
      memberDetailsError,
      memberDetailsGroup,
      memberDetailsLoading,
      memberDetailsModalOpen,
      newGroupName,
      selectedContactId,
      selectedGroup,
      selectedUserId,
      shareGroups,
      usePeerId,
    } = this.state;

    const contactOptions = contacts.map((c) => ({
      contact: c,
      key: c.id,
      text: `${c.nickname || 'Unnamed'} (${c.peerId?.slice(0, 16)}...)`,
      value: c.peerId,
    }));

    return (
      <Container>
        <Header as="h1">
          <Icon name="users" />
          <Header.Content>
            Share Groups
            <Header.Subheader>
              Manage groups for sharing collections
            </Header.Subheader>
          </Header.Content>
        </Header>

        {error && <ErrorSegment caption={error} />}

        <div style={{ marginBottom: '1em' }}>
          <Button
            data-testid="groups-create"
            onClick={() => this.setState({ createModalOpen: true })}
            primary
            tooltip="Create a named group that can be granted access to shared collections."
          >
            <Icon name="plus" />
            Create Group
          </Button>
        </div>

        {shareGroups.length === 0 ? (
          <Segment placeholder>
            <Header icon>
              <Icon name="users" />
              {loading ? 'Loading share groups' : 'No share groups yet'}
            </Header>
            <Button
              onClick={() => this.setState({ createModalOpen: true })}
              primary
              tooltip="Create the first share group for collection permissions."
            >
              Create Your First Group
            </Button>
          </Segment>
        ) : (
          <Table>
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell>Name</Table.HeaderCell>
                <Table.HeaderCell>Members</Table.HeaderCell>
                <Table.HeaderCell>Created</Table.HeaderCell>
                <Table.HeaderCell>Actions</Table.HeaderCell>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {shareGroups.map((group) => (
                <Table.Row
                  data-testid={`group-row-${group.name}`}
                  key={group.id}
                >
                  <Table.Cell>{group.name}</Table.Cell>
                  <Table.Cell>
                    <Button
                      data-testid="group-view-members"
                      onClick={() => this.handleViewMembers(group)}
                      size="small"
                      tooltip="Show the contacts or users currently assigned to this group."
                    >
                      View Members
                    </Button>
                  </Table.Cell>
                  <Table.Cell>
                    {new Date(group.createdAt).toLocaleDateString(getRegionalLocale())}
                  </Table.Cell>
                  <Table.Cell>
                    <Button
                      data-testid="group-add-member"
                      onClick={() =>
                        this.setState({
                          addMemberModalOpen: true,
                          selectedGroup: group,
                        })
                      }
                      primary
                      size="small"
                      tooltip="Add a contact or Soulseek username to this share group."
                    >
                      Add Member
                    </Button>
                    <Button
                      negative
                      onClick={() => this.handleDeleteGroup(group.id)}
                      size="small"
                      tooltip="Delete this share group and remove its collection access."
                    >
                      Delete
                    </Button>
                  </Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table>
        )}

        {/* Create Group Modal */}
        <Modal
          onClose={() =>
            this.setState({ createModalOpen: false, newGroupName: '' })
          }
          open={createModalOpen}
        >
          <Modal.Header>Create Share Group</Modal.Header>
          <Modal.Content>
            <Form>
              <Form.Input
                data-testid="groups-name-input"
                label="Group Name"
                onChange={(e) =>
                  this.setState({ newGroupName: e.target.value })
                }
                placeholder="Enter group name"
                value={newGroupName}
              />
            </Form>
          </Modal.Content>
          <Modal.Actions>
            <Button
              onClick={() =>
                this.setState({ createModalOpen: false, newGroupName: '' })
              }
              tooltip="Close this dialog without creating a share group."
            >
              Cancel
            </Button>
            <Button
              data-testid="groups-create-submit"
              disabled={!newGroupName.trim()}
              onClick={this.handleCreateGroup}
              primary
              tooltip="Create this share group."
            >
              Create
            </Button>
          </Modal.Actions>
        </Modal>

        {/* Add Member Modal */}
        <Modal
          onClose={() =>
            this.setState({
              addMemberModalOpen: false,
              selectedContactId: null,
              selectedGroup: null,
              selectedUserId: null,
            })
          }
          open={addMemberModalOpen}
        >
          <Modal.Header>Add Member to {selectedGroup?.name}</Modal.Header>
          <Modal.Content>
            {contacts.length > 0 ? (
              <Form>
                <Form.Field>
                  <label>Add from Contacts</label>
                  <Dropdown
                    data-testid="group-member-picker"
                    fluid
                    onChange={(e, { value }) =>
                      this.setState({
                        selectedContactId: value,
                        usePeerId: true,
                      })
                    }
                    options={contactOptions}
                    placeholder="Select a contact"
                    search
                    selection
                    value={selectedContactId}
                  />
                </Form.Field>
                <Message info>
                  <p>Or enter a Soulseek username (legacy):</p>
                  <Form.Input
                    onChange={(e) =>
                      this.setState({
                        selectedUserId: e.target.value,
                        usePeerId: false,
                      })
                    }
                    placeholder="Soulseek username"
                    value={selectedUserId}
                  />
                </Message>
              </Form>
            ) : (
              <Form>
                <Form.Field>
                  <label>Soulseek Username (legacy)</label>
                  <Form.Input
                    onChange={(e) =>
                      this.setState({ selectedUserId: e.target.value })
                    }
                    placeholder="Enter username"
                    value={selectedUserId}
                  />
                </Form.Field>
                <Message warning>
                  No contacts available. Add contacts from the Contacts page to
                  use friend-based sharing.
                </Message>
              </Form>
            )}
          </Modal.Content>
          <Modal.Actions>
            <Button
              onClick={() =>
                this.setState({
                  addMemberModalOpen: false,
                  selectedContactId: null,
                  selectedGroup: null,
                  selectedUserId: null,
                })
              }
              tooltip="Close this dialog without adding a member."
            >
              Cancel
            </Button>
            <Button
              data-testid="group-member-add-submit"
              disabled={!selectedContactId && !selectedUserId}
              onClick={this.handleAddMember}
              primary
              tooltip="Add the selected contact or username to this share group."
            >
              Add Member
            </Button>
          </Modal.Actions>
        </Modal>

        <Modal
          closeIcon={false}
          onClose={this.closeMemberDetails}
          open={memberDetailsModalOpen}
        >
          <Modal.Header>Members of {memberDetailsGroup?.name || 'Share Group'}</Modal.Header>
          <Modal.Content>
            {memberDetailsLoading ? (
              <LoaderSegment />
            ) : memberDetailsError ? (
              <Message negative>
                <Message.Content>{memberDetailsError}</Message.Content>
                <Button
                  onClick={() =>
                    memberDetailsGroup && this.handleViewMembers(memberDetailsGroup)
                  }
                  primary
                  tooltip="Retry loading members for this share group."
                >
                  Retry Members
                </Button>
              </Message>
            ) : memberDetails.length > 0 ? (
              <List divided relaxed>
                {memberDetails.map((member, index) => (
                  <List.Item key={member.userId || member.peerId || index}>
                    {member.contactNickname || member.nickname || member.userId || member.peerId || 'Unknown member'}
                  </List.Item>
                ))}
              </List>
            ) : (
              <Segment placeholder>No members are assigned to this group.</Segment>
            )}
          </Modal.Content>
          <Modal.Actions>
            <Button
              onClick={this.closeMemberDetails}
              tooltip="Close the member list and return to share groups."
            >
              Close
            </Button>
          </Modal.Actions>
        </Modal>
      </Container>
    );
  }
}
