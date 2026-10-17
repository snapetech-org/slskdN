import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';


import { getRegionalLocale } from '../../lib/regionalFormat';
import './Pods.css';
import { urlBase } from '../../config';
import * as pods from '../../lib/pods';
import PlaceholderSegment from '../Shared/PlaceholderSegment';
import PodListenAlongPanel from '../Player/PodListenAlongPanel';
import PortForwarding from './PortForwarding';
import VpnGatewayConfig from './VpnGatewayConfig';
import { TooltipButton } from '../Shared';
import React, { Component } from 'react';
import { toast } from 'react-toastify';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  Button,
  Dimmer,
  Dropdown,
  Form,
  Header,
  Icon,
  Input,
  Label,
  List,
  Loader,
  Message,
  Modal,
  Popup,
  Segment,
  Tab,
} from 'semantic-ui-react';

const initialState = {
  activeChannelId: null,
  activeDetailTab: 0,
  activePodId: null,
  loading: false,
  members: [],
  messageInput: '',
  messages: {},
  podDetail: null,
  pods: [],
  createModalOpen: false,
  createDescription: '',
  createName: '',
  createTags: '',
  createVisibility: 'Unlisted',
  discoveryLoading: false,
  discoveryQuery: '',
  discoveryResults: [],
};

const GOLD_STAR_CLUB_POD_ID = 'pod:901d57a2c1bb4e5d90d57a2c1bb4e5d0';
const MAX_CACHED_MESSAGES = 100;
const MESSAGE_POLL_INTERVAL_MS = 2_000;
const POD_POLL_INTERVAL_MS = 60_000;
const asArray = (value) => (Array.isArray(value) ? value : []);
const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);
const messageIdentity = (message) =>
  message.messageId ||
  [
    message.podId,
    message.channelId,
    message.timestampUnixMs,
    message.senderPeerId,
    message.body,
    message.signature,
  ].join('|');
const messageListsMatch = (previous, next) =>
  previous.length === next.length &&
  previous.every(
    (message, index) =>
      messageIdentity(message) === messageIdentity(next[index]) &&
      message.body === next[index]?.body &&
      message.signature === next[index]?.signature,
  );
const podListSignature = (podList) => JSON.stringify(podList);

const withRouter = (WrappedComponent) => {
  const RoutedComponent = (props) => {
    useInterfaceLanguage();
    const location = useLocation();
    const navigate = useNavigate();
    const params = useParams();

    return (
      <WrappedComponent
        {...props}
        location={location}
        navigate={navigate}
        params={params}
      />
    );
  };

  RoutedComponent.displayName = `withRouter(${WrappedComponent.displayName || WrappedComponent.name || 'Component'})`;

  return RoutedComponent;
};

export class Pods extends Component {
  constructor(props) {
    super(props);

    this.state = initialState;
    this.latestMessageTimestamp = new Map();
    this.messageInterval = null;
    this.messageRequests = new Map();
    this.mounted = false;
    this.podInterval = null;
    this.podsRequest = null;
    this.selectionVersion = 0;
  }

  componentDidMount() {
    this.mounted = true;
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
    if (!document.hidden) {
      this.hydrateWorkspace();
      this.startPolling();
    }
  }

  componentDidUpdate(previousProps) {
    // Handle route changes
    const podId = this.props.params?.podId;
    const channelId = this.props.params?.channelId;
    const previousPodId = previousProps.params?.podId;
    const previousChannelId = previousProps.params?.channelId;

    if (
      (podId !== previousPodId || channelId !== previousChannelId) &&
      podId &&
      !document.hidden
    ) {
      this.selectPod(podId, channelId);
    }
  }

  componentWillUnmount() {
    this.mounted = false;
    this.selectionVersion += 1;
    this.stopPolling();
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
  }

  startPolling = () => {
    if (document.hidden) return;

    if (!this.messageInterval) {
      this.messageInterval = window.setInterval(
        this.fetchMessages,
        MESSAGE_POLL_INTERVAL_MS,
      );
    }
    if (!this.podInterval) {
      this.podInterval = window.setInterval(this.fetchPods, POD_POLL_INTERVAL_MS);
    }
  };

  stopPolling = () => {
    if (this.messageInterval) {
      window.clearInterval(this.messageInterval);
      this.messageInterval = null;
    }
    if (this.podInterval) {
      window.clearInterval(this.podInterval);
      this.podInterval = null;
    }
  };

  handleVisibilityChange = () => {
    if (document.hidden) {
      this.stopPolling();
      return;
    }

    this.hydrateWorkspace();
    this.startPolling();
  };

  hydrateWorkspace = async () => {
    const podList = await this.fetchPods();
    if (!this.mounted || document.hidden || podList.length === 0) return;

    const routedPodId = this.props.params?.podId;
    const routedChannelId = this.props.params?.channelId;
    const preferredPod =
      podList.find((pod) => pod.podId === routedPodId) ||
      podList.find((pod) => pod.podId === this.state.activePodId) ||
      podList.find((pod) => pod.podId === GOLD_STAR_CLUB_POD_ID) ||
      podList[0];
    const channelId =
      preferredPod.podId === routedPodId
        ? routedChannelId || null
        : this.state.activeChannelId;

    if (
      this.state.podDetail?.podId === preferredPod.podId &&
      this.state.activePodId === preferredPod.podId &&
      (!channelId || this.state.activeChannelId === channelId)
    ) {
      await this.fetchMessages();
      return;
    }

    await this.selectPod(preferredPod.podId, channelId, preferredPod);
  };

  fetchPods = () => {
    if (document.hidden) return Promise.resolve(this.state.pods);
    if (this.podsRequest) return this.podsRequest;

    const request = (async () => {
      try {
        const podList = asArray(await pods.list()).filter(isObject);
        if (this.mounted && !document.hidden) {
          this.setState((previous) => {
            if (podListSignature(previous.pods) === podListSignature(podList)) {
              return null;
            }

            const selected = podList.find(
              (pod) => pod.podId === previous.activePodId,
            );
            return {
              podDetail: selected || previous.podDetail,
              pods: podList,
            };
          });
        }
        return podList;
      } catch (error) {
        console.error('Failed to fetch pods:', error);
        return this.state.pods;
      }
    })();
    const trackedRequest = request.finally(() => {
      if (this.podsRequest === trackedRequest) {
        this.podsRequest = null;
      }
    });
    this.podsRequest = trackedRequest;
    return trackedRequest;
  };

  getLocalPeerId = () => {
    return this.props.state?.user?.username || 'local-peer';
  };

  fetchPodDetail = async (podId) => {
    try {
      const [detail, members] = await Promise.all([
        pods.get(podId),
        pods.getMembers(podId),
      ]);
      if (
        this.mounted &&
        !document.hidden &&
        this.state.activePodId === podId
      ) {
        this.setState({
          members: asArray(members).filter(isObject),
          podDetail: detail,
        });
      }
      return { detail, members: asArray(members).filter(isObject) };
    } catch (error) {
      console.error('Failed to fetch pod detail:', error);
      return null;
    }
  };

  fetchMessages = (podId = this.state.activePodId, channelId = this.state.activeChannelId) => {
    if (!podId || !channelId || document.hidden) return Promise.resolve();

    const key = `${podId}:${channelId}`;
    if (this.messageRequests.has(key)) {
      return this.messageRequests.get(key);
    }

    const latestTimestamp = this.latestMessageTimestamp.get(key);
    const since = latestTimestamp == null ? null : Math.max(0, latestTimestamp - 1);
    const request = (async () => {
      try {
        const received = asArray(
          await pods.getMessages(podId, channelId, since),
        ).filter(isObject);
        if (
          !this.mounted ||
          document.hidden ||
          this.state.activePodId !== podId ||
          this.state.activeChannelId !== channelId
        ) {
          return;
        }

        received.forEach((message) => {
          const timestamp = Number(message.timestampUnixMs) || 0;
          const current = this.latestMessageTimestamp.get(key);
          if (current == null || timestamp > current) {
            this.latestMessageTimestamp.set(key, timestamp);
          }
        });

        this.setState((previous) => {
          const byId = new Map(
            asArray(previous.messages[key]).map((message) => [
              messageIdentity(message),
              message,
            ]),
          );
          received.forEach((message) => byId.set(messageIdentity(message), message));
          const merged = Array.from(byId.values())
            .sort(
              (left, right) =>
                (Number(left.timestampUnixMs) || 0) -
                  (Number(right.timestampUnixMs) || 0) ||
                messageIdentity(left).localeCompare(messageIdentity(right)),
            )
            .slice(-MAX_CACHED_MESSAGES);
          if (messageListsMatch(asArray(previous.messages[key]), merged)) {
            return null;
          }

          return { messages: { ...previous.messages, [key]: merged } };
        });
      } catch (error) {
        console.error('Failed to fetch messages:', error);
      }
    })();
    const trackedRequest = request.finally(() => {
      if (this.messageRequests.get(key) === trackedRequest) {
        this.messageRequests.delete(key);
      }
    });
    this.messageRequests.set(key, trackedRequest);
    return trackedRequest;
  };

  getChannelIndex = (podDetail, channelId) =>
    Math.max(
      0,
      podDetail?.channels?.findIndex((channel) => channel.channelId === channelId) ??
        0,
    );

  selectPod = async (podId, channelId = null, listedPod = null) => {
    if (
      this.state.podDetail?.podId === podId &&
      this.state.activePodId === podId &&
      (!channelId || this.state.activeChannelId === channelId)
    ) {
      return;
    }

    const selectionVersion = ++this.selectionVersion;
    this.setState({ activePodId: podId, loading: true });

    try {
      const listedDetail =
        listedPod ||
        this.state.pods.find((pod) => pod.podId === podId);
      const [detail, memberResponse] = await Promise.all([
        listedDetail || pods.get(podId),
        pods.getMembers(podId),
      ]);
      const members = asArray(memberResponse).filter(isObject);
      if (
        !this.mounted ||
        document.hidden ||
        this.selectionVersion !== selectionVersion
      ) {
        return;
      }

      const selectedChannelId =
        channelId || asArray(detail?.channels)[0]?.channelId || null;
      await new Promise((resolve) => {
        this.setState(
          {
            activeChannelId: selectedChannelId,
            activeDetailTab: this.getChannelIndex(detail, selectedChannelId),
            activePodId: podId,
            loading: false,
            members,
            podDetail: detail,
          },
          resolve,
        );
      });

      const currentPodId = this.props.params?.podId;
      const currentChannelId = this.props.params?.channelId;
      if (podId !== currentPodId || selectedChannelId !== currentChannelId) {
        const path = selectedChannelId
          ? `${urlBase}/pods/${encodeURIComponent(podId)}/channels/${encodeURIComponent(selectedChannelId)}`
          : `${urlBase}/pods/${encodeURIComponent(podId)}`;
        this.props.navigate(path);
      }

      if (selectedChannelId) {
        await this.fetchMessages(podId, selectedChannelId);
      }
    } catch (error) {
      console.error('Failed to select pod:', error);
      if (
        this.mounted &&
        !document.hidden &&
        this.selectionVersion === selectionVersion
      ) {
        this.setState({ loading: false });
      }
    }
  };

  handleDetailTabChange = (_event, { activeIndex }) => {
    const { activePodId, podDetail } = this.state;
    const channel = podDetail?.channels?.[activeIndex];

    this.setState({ activeDetailTab: activeIndex });

    if (!channel || !activePodId) {
      return;
    }

    this.setState({ activeChannelId: channel.channelId }, async () => {
      const currentPodId = this.props.params?.podId;
      const currentChannelId = this.props.params?.channelId;

      if (
        activePodId !== currentPodId ||
        channel.channelId !== currentChannelId
      ) {
        this.props.navigate(
          `${urlBase}/pods/${encodeURIComponent(activePodId)}/channels/${encodeURIComponent(channel.channelId)}`,
        );
      }

      await this.fetchMessages();
    });
  };

  handleSendMessage = async () => {
    const { activeChannelId, activePodId, messageInput } = this.state;
    const { state: applicationState } = this.props;

    if (!activePodId || !activeChannelId || !messageInput.trim()) {
      return;
    }

    // Get peerId from application state (username)
    const senderPeerId = applicationState?.user?.username || 'local-peer';

    try {
      await pods.sendMessage(
        activePodId,
        activeChannelId,
        messageInput,
        senderPeerId,
      );
      this.setState({ messageInput: '' });
      // Messages will be refreshed by interval
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error(interfaceText("Failed to send message: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
    }
  };

  handleOpenCreatePod = () => {
    this.setState({
      createDescription: '',
      createModalOpen: true,
      createName: '',
      createTags: '',
      createVisibility: 'Unlisted',
    });
  };

  handleCreatePod = async () => {
    const {
      createDescription,
      createName,
      createTags,
      createVisibility,
    } = this.state;
    const name = createName.trim();
    if (!name) return;

    try {
      const newPod = await pods.create({
        channels: [
          {
            channelId: 'general',
            kind: 'General',
            name: 'General',
          },
        ],
        description: createDescription.trim() || null,
        externalBindings: [],
        name,
        tags: createTags
          .split(',')
          .map((tag) => tag.trim())
          .filter(Boolean),
        visibility: createVisibility,
      }, this.getLocalPeerId());

      this.setState({ createModalOpen: false });
      const podList = await this.fetchPods();
      await this.selectPod(
        newPod.podId,
        null,
        podList.find((pod) => pod.podId === newPod.podId) || newPod,
      );
    } catch (error) {
      console.error('Failed to create pod:', error);
      toast.error(interfaceText("Failed to create pod: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
    }
  };

  handleDiscoverPods = async () => {
    const query = this.state.discoveryQuery.trim();
    this.setState({ discoveryLoading: true });

    try {
      const discovered = query
        ? await pods.discoverByName(query)
        : await pods.discoverAll(50);
      this.setState({ discoveryResults: asArray(discovered).filter(isObject) });
    } catch (error) {
      console.error('Failed to discover pods:', error);
      toast.error(interfaceText("Failed to discover pods: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
    } finally {
      this.setState({ discoveryLoading: false });
    }
  };

  handleSaveDiscoveredPod = async (pod) => {
    const podId = pod.podId || pod.PodId;
    const name = pod.name || pod.Name || podId;
    const tags = asArray(pod.tags || pod.Tags);
    const visibility = pod.visibility || pod.Visibility || 'Unlisted';
    const focusContentId = pod.focusContentId || pod.FocusContentId || null;

    if (!podId) return;

    try {
      const savedPod = await pods.create({
        channels: [
          {
            channelId: 'general',
            kind: 'General',
            name: 'General',
          },
        ],
        externalBindings: [],
        focusContentId,
        name,
        podId,
        tags,
        visibility,
      }, this.getLocalPeerId());

      toast.success(interfaceText("Saved pod {name}", { "name": (name) }));
      const podList = await this.fetchPods();
      await this.selectPod(
        savedPod.podId,
        null,
        podList.find((item) => item.podId === savedPod.podId) || savedPod,
      );
    } catch (error) {
      console.error('Failed to save discovered pod:', error);
      toast.error(interfaceText("Failed to save pod: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
    }
  };

  handleLeaveActivePod = async () => {
    const { activePodId, podDetail } = this.state;
    const peerId = this.getLocalPeerId();
    const podName = podDetail?.name || activePodId;

    if (!activePodId || !peerId) return;

    if (
      podDetail?.podId === 'pod:901d57a2c1bb4e5d90d57a2c1bb4e5d0' &&
        !window.confirm(interfaceText(
        'Leaving Gold Star Club is irrevocable. You will not be able to rejoin or recover Gold Star status later. Leave anyway?',
      ),
      )
    ) {
      return;
    }

    try {
      await pods.leave(activePodId, peerId);
      toast.success(interfaceText("Left {podName}", { "podName": (podName) }));
      await this.fetchPodDetail(activePodId);
    } catch (error) {
      console.error('Failed to leave pod:', error);
      toast.error(interfaceText("Failed to leave pod: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
    }
  };

  render() {
    const {
      activeChannelId,
      activePodId,
      loading,
      members,
      messageInput,
      messages,
      podDetail,
      pods: podsList,
      createDescription,
      createModalOpen,
      createName,
      createTags,
      createVisibility,
      discoveryLoading,
      discoveryQuery,
      discoveryResults,
    } = this.state;

    const currentMessages =
      activePodId && activeChannelId
        ? asArray(messages[`${activePodId}:${activeChannelId}`])
        : [];
    const localPeerId = this.getLocalPeerId();
    const isMember = members.some((member) => member.peerId === localPeerId);
    const isGoldStarClub = podDetail?.podId === GOLD_STAR_CLUB_POD_ID;
    const activeChannel = podDetail?.channels?.find(
      (channel) => channel.channelId === activeChannelId,
    );

    return (
      <div className="pods-workspace">
        {/* Pod List Sidebar */}
        <Segment className="pods-sidebar">
          <div className="pods-sidebar-header">
            <h3><LocalizedText source={"Pods"} /></h3>
            <Popup
              content={interfaceText("Create a durable pod with a default channel. It is saved by the daemon and restored after restart.")}
              trigger={
                <Button
                  aria-label={interfaceText("Create a pod")}
                  icon="plus"
                  onClick={this.handleOpenCreatePod}
                  size="small"
                 {...interfaceTextProps("Create a pod")}/>
              }
             {...interfaceTextProps("Create a durable pod with a default channel. It is saved by the daemon and restored after restart.")}/>
          </div>
          <Input
            action={
              <Popup
              content={interfaceText("Search the pod discovery index for listed pods. This sends your search term to the discovery service so you can find pods to save locally.")}
              trigger={
                <Button
                  aria-label={interfaceText("Search the pod discovery index")}
                  icon="search"
                    loading={discoveryLoading}
                    onClick={this.handleDiscoverPods}
                   {...interfaceTextProps("Search the pod discovery index")}/>
                }
               {...interfaceTextProps("Search the pod discovery index for listed pods. This sends your search term to the discovery service so you can find pods to save locally.")}/>
            }
            fluid
            onChange={(e) =>
              this.setState({ discoveryQuery: e.target.value })
            }
            onKeyUp={(e) => {
              if (e.key === 'Enter') {
                this.handleDiscoverPods();
              }
            }}
            placeholder={interfaceText("Find pods...")}
            size="small"
            value={discoveryQuery}
           {...interfaceTextProps("Find pods...")}/>
          {discoveryResults.length > 0 && (
            <Segment className="pod-discovery-results">
              <Header
                as="h5"
                dividing
              >
                <LocalizedText source={"Discovered"} /></Header>
              <List selection>
                {discoveryResults.slice(0, 6).map((pod) => {
                  const podId = pod.podId || pod.PodId;
                  const name = pod.name || pod.Name || podId;
                  const tags = asArray(pod.tags || pod.Tags);
                  const local = podsList.some((item) => item.podId === podId);

                  return (
                    <List.Item
                      key={podId}
                      onClick={() => local && this.selectPod(podId)}
                    >
                      <List.Content>
                        <List.Header>
                          {name}
                          {local && (
                            <Label
                              color="green"
                              size="mini"
                            >
                              <LocalizedText source={"saved"} /></Label>
                          )}
                        </List.Header>
                        <List.Description>
                          {tags.length > 0 ? tags.join(', ') : podId}
                        </List.Description>
                      </List.Content>
                      {!local && (
                        <List.Content floated="right">
                          <Popup
                            content={interfaceText("Save this pod's details in your local pod list so it is available after restarts. This does not join the pod.")}
                            trigger={
                              <Button
                                aria-label={interfaceText("Save discovered pod {name} locally", { "name": (name) })}
                                basic
                                icon="save"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  this.handleSaveDiscoveredPod(pod);
                                }}
                                size="mini"
                               {...interfaceTextProps("Save discovered pod {name} locally")}/>
                            }
                           {...interfaceTextProps("Save this pod's details in your local pod list so it is available after restarts. This does not join the pod.")}/>
                        </List.Content>
                      )}
                    </List.Item>
                  );
                })}
              </List>
            </Segment>
          )}
          {podsList.length === 0 ? (
            <PlaceholderSegment
              caption="No pods yet"
              icon="users"
            />
          ) : (
            <List selection>
              {podsList.map((pod) => (
                <List.Item
                  active={pod.podId === activePodId}
                  key={pod.podId}
                  onClick={() => this.selectPod(pod.podId)}
                >
                  <List.Content>
                    <List.Header>{pod.name || pod.podId}</List.Header>
                    <List.Description>
                      {pod.tags?.join(', ') || <LocalizedText source={"No tags"} />}
                    </List.Description>
                  </List.Content>
                </List.Item>
              ))}
            </List>
          )}
        </Segment>

        {/* Pod Detail */}
        <Segment className="pod-detail">
          {loading ? (
            <Dimmer active>
              <Loader />
            </Dimmer>
          ) : !podDetail ? (
            <PlaceholderSegment
              caption="Select a pod to view details"
              icon="users"
            />
          ) : (
            <>
              <div className="pod-detail-header">
                <h2>{podDetail.name || podDetail.podId}</h2>
                <div className="pod-detail-meta">
                  <span>
                    <strong><LocalizedText source={"Members:"} /></strong> {members.length}
                  </span>
                  <span>
                    <strong><LocalizedText source={"Channels:"} /></strong> {podDetail.channels?.length || 0}
                  </span>
                  <span>
                    <strong><LocalizedText source={"Visibility:"} /></strong> {podDetail.visibility}
                  </span>
                </div>
                {podDetail.description && <p>{podDetail.description}</p>}
                {isGoldStarClub && (
                  <Message warning>
                    <Icon name="star" />
                    <LocalizedText source={"Gold Star Club membership is limited to the first 250 nodes. Leaving this pod permanently revokes local Gold Star status. There are no rejoins."} /></Message>
                )}
                {podDetail.tags?.length > 0 && (
                  <div className="pod-tag-list">
                    {podDetail.tags.map((tag) => (
                      <Label
                        key={tag}
                        size="small"
                      >
                        {tag}
                      </Label>
                    ))}
                  </div>
                )}
                {isMember && (
                  <Popup
                    content={
                      isGoldStarClub
                        ? interfaceText('Permanently leave Gold Star Club. This is irrevocable and cannot be undone.')
                        : interfaceText('Remove the current peer from this pod and stop participating in its channels. Leave when you no longer want this peer to participate.')
                    }
                    trigger={
                      <Button
                        aria-label={isGoldStarClub
                          ? interfaceText('Permanently leave Gold Star Club')
                          : interfaceText('Leave pod {pod}', { pod: podDetail.name || podDetail.podId })}
                        icon
                        labelPosition="left"
                        negative={isGoldStarClub}
                        onClick={this.handleLeaveActivePod}
                        size="small"
                      >
                        <Icon name="sign-out" />
                        {isGoldStarClub ? <LocalizedText source={"Revoke Gold Star"} /> : <LocalizedText source={"Leave Pod"} />}
                      </Button>
                    }
                  />
                )}
              </div>
              {activeChannelId && activeChannel?.kind !== 'Direct' && (
                <PodListenAlongPanel
                  channelId={activeChannelId}
                  compact
                  podId={activePodId}
                  user={this.props.state?.user?.username}
                />
              )}

              {podDetail.channels?.length > 0 ? (
                <>
                  <div className="pod-channel-selector">
                    {podDetail.channels.map((channel, index) => (
                      <TooltipButton
                        active={channel.channelId === activeChannelId}
                        aria-label={interfaceText('Open {channel} channel', {
                          channel: channel.name || channel.channelId,
                        })}
                        icon={channel.kind === 'Direct' ? 'comments' : 'comment alternate'}
                        key={channel.channelId}
                        labelPosition="left"
                        onClick={() =>
                          this.handleDetailTabChange(null, { activeIndex: index })
                        }
                        size="small"
                        tooltip={interfaceText(
                          'Open {channel} to read its messages and compose updates for the channel participants.',
                          { channel: channel.name || channel.channelId },
                        )}
                      >
                        {channel.name || channel.channelId}
                      </TooltipButton>
                    ))}
                  </div>
                  <Segment className="pod-channel-chat">
                    <div className="pod-channel-heading">
                      <div>
                        <Header
                          as="h3"
                          content={activeChannel?.name || activeChannelId}
                        />
                        <span className="pod-channel-subtitle">
                          {activeChannel?.kind === 'Direct'
                            ? <LocalizedText source={"Direct pod channel"} />
                            : interfaceText('{kind} channel', {
                              kind: activeChannel?.kind || interfaceText('Pod'),
                            })}
                        </span>
                      </div>
                      <Label basic>
                        {currentMessages.length}{' '}
                        {currentMessages.length === 1 ? <LocalizedText source={"message"} /> : <LocalizedText source={"messages"} />}
                      </Label>
                    </div>
                    <Segment className="pod-message-history">
                      {currentMessages.length === 0 ? (
                        <PlaceholderSegment
                          caption="No messages yet"
                          icon="comments"
                        />
                      ) : (
                        <List relaxed="very">
                          {currentMessages.map((message, index) => (
                            <List.Item key={index}>
                              <List.Content>
                                <List.Header>
                                  {message.senderPeerId}
                                  <span
                                    style={{
                                      color: '#999',
                                      fontSize: '0.8em',
                                      marginLeft: '10px',
                                    }}
                                  >
                                    {new Date(
                                      message.timestampUnixMs,
                                    ).toLocaleTimeString(getRegionalLocale())}
                                  </span>
                                </List.Header>
                                <List.Description>{message.body}</List.Description>
                              </List.Content>
                            </List.Item>
                          ))}
                        </List>
                      )}
                    </Segment>
                    <Segment className="pod-message-composer">
                      <Input
                        action={
                          <Popup
                            content={interfaceText("Send this text to the active pod channel's participants. Use this when you want to share an update with them.")}
                            trigger={
                              <Button
                                aria-label={interfaceText("Send a message to the active pod channel")}
                                icon="send"
                                onClick={this.handleSendMessage}
                                primary
                               {...interfaceTextProps("Send a message to the active pod channel")}/>
                            }
                           {...interfaceTextProps("Send this text to the active pod channel's participants. Use this when you want to share an update with them.")}/>
                        }
                        fluid
                        onChange={(e) =>
                          this.setState({ messageInput: e.target.value })
                        }
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') {
                            this.handleSendMessage();
                          }
                        }}
                        placeholder={interfaceText("Type a message...")}
                        value={messageInput}
                       {...interfaceTextProps("Type a message...")}/>
                    </Segment>
                  </Segment>
                  <Tab
                    menu={{ pointing: true }}
                    panes={[
                      {
                        menuItem: {
                          content: interfaceText("VPN Gateway"),
                          icon: 'shield',
                          key: 'vpn-gateway',
                        },
                        render: () => (
                          <Tab.Pane>
                            <VpnGatewayConfig
                              podDetail={podDetail}
                              podId={activePodId}
                            />
                          </Tab.Pane>
                        ),
                      },
                      {
                        menuItem: {
                          content: interfaceText("Port Forwarding"),
                          icon: 'exchange',
                          key: 'port-forwarding',
                        },
                        render: () => (
                          <Tab.Pane>
                            <PortForwarding />
                          </Tab.Pane>
                        ),
                      },
                    ]}
                  />
                </>
              ) : (
                <PlaceholderSegment
                  caption="No channels available"
                  icon="comments"
                />
              )}
            </>
          )}
        </Segment>
        <Modal
          onClose={() => this.setState({ createModalOpen: false })}
          open={createModalOpen}
          size="small"
        >
          <Modal.Header><LocalizedText source={"Create Pod"} /></Modal.Header>
          <Modal.Content>
            <Form>
              <Form.Field>
                <label><LocalizedText source={"Name"} /></label>
                <Input
                  autoFocus
                  onChange={(e) =>
                    this.setState({ createName: e.target.value })
                  }
                  placeholder={interfaceText("listening circle, label crate, private crew")}
                  value={createName}
                 {...interfaceTextProps("listening circle, label crate, private crew")}/>
              </Form.Field>
              <Form.TextArea
                label={interfaceText("Description")}
                onChange={(e, { value }) =>
                  this.setState({ createDescription: value })
                }
                placeholder={interfaceText("What this pod is for")}
                value={createDescription}
               {...interfaceTextProps("Description")}/>
              <Form.Field>
                <label><LocalizedText source={"Tags"} /></label>
                <Input
                  onChange={(e) =>
                    this.setState({ createTags: e.target.value })
                  }
                  placeholder={interfaceText("ambient, friends, vinyl")}
                  value={createTags}
                 {...interfaceTextProps("ambient, friends, vinyl")}/>
              </Form.Field>
              <Form.Field>
                <label><LocalizedText source={"Visibility"} /></label>
                <Dropdown
                  fluid
                  onChange={(e, { value }) =>
                    this.setState({ createVisibility: value })
                  }
                  options={[
                    { key: 'unlisted', text: interfaceText("Unlisted"), value: 'Unlisted' },
                    { key: 'listed', text: interfaceText("Listed"), value: 'Listed' },
                    { key: 'private', text: interfaceText("Private"), value: 'Private' },
                  ]}
                  selection
                  value={createVisibility}
                />
              </Form.Field>
              <Message info>
                <Icon name="save" />
                <LocalizedText source={"Pods are stored by the server, so the list and messages survive browser reloads and daemon restarts."} /></Message>
            </Form>
          </Modal.Content>
          <Modal.Actions>
            <TooltipButton
              onClick={() => this.setState({ createModalOpen: false })}
              tooltip="Close this form without creating a pod; the entered details are discarded."
            >
              <LocalizedText source={"Cancel"} /></TooltipButton>
            <TooltipButton
              disabled={!createName.trim()}
              onClick={this.handleCreatePod}
              primary
              tooltip="Create a pod with a General channel and save it on the server so it remains available after restarts."
            >
              <LocalizedText source={"Create"} /></TooltipButton>
          </Modal.Actions>
        </Modal>
      </div>
    );
  }
}

export default withRouter(Pods);
