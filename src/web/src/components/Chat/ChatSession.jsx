import { interfaceText, interfaceTextProps } from "../../lib/interfaceLocale";
import './Chat.css';
import * as chat from '../../lib/chat';
import PlaceholderSegment from '../Shared/PlaceholderSegment';
import UserCard from '../Shared/UserCard';
import TooltipButton from '../Shared/TooltipButton';
import React, { Component, createRef } from 'react';
import {
  Card,
  Dimmer,
  Icon,
  Input,
  List,
  Loader,
  Segment,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const MAX_CACHED_MESSAGES = 100;
const POLL_INTERVAL_MS = 5_000;
const messageIdentity = (message) =>
  [message.id, message.timestamp, message.direction, message.username].join('|');
const messageTimestamp = (message) => {
  const numeric = Number(message?.timestamp);
  if (message?.timestamp !== '' && Number.isFinite(numeric)) return numeric;

  const parsed = Date.parse(message?.timestamp);
  return Number.isFinite(parsed) ? parsed : 0;
};
const conversationsMatch = (previous, next) => {
  if (!previous || !next) return previous === next;
  const previousMessages = asArray(previous.messages);
  const nextMessages = asArray(next.messages);
  return (
    previous.username === next.username &&
    previous.isActive === next.isActive &&
    previous.unAcknowledgedMessageCount === next.unAcknowledgedMessageCount &&
    previousMessages.length === nextMessages.length &&
    previousMessages.every(
      (message, index) =>
        messageIdentity(message) === messageIdentity(nextMessages[index]) &&
        message.message === nextMessages[index]?.message &&
        message.isAcknowledged === nextMessages[index]?.isAcknowledged,
    )
  );
};

class ChatSession extends Component {
  constructor(props) {
    super(props);

    this.state = {
      conversation: null,
      loading: false,
      message: '',
    };

    this.conversationRequest = null;
    this.interval = null;
    this.latestTimestamp = null;
    this.listRef = createRef();
    this.messageRef = undefined;
    this.mounted = false;
  }

  componentDidMount() {
    this.mounted = true;
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
    if (this.props.active !== false && !document.hidden) {
      this.startPolling();
    }
  }

  startPolling = () => {
    if (this.props.active === false || document.hidden || this.interval) return;

    this.fetchConversation();
    this.interval = window.setInterval(this.fetchConversation, POLL_INTERVAL_MS);
  };

  stopPolling = () => {
    if (!this.interval) return;

    window.clearInterval(this.interval);
    this.interval = null;
  };

  handleVisibilityChange = () => {
    if (document.hidden) {
      this.stopPolling();
      return;
    }

    if (this.props.active !== false) {
      this.startPolling();
    }
  };

  componentDidUpdate(previousProps) {
    if (previousProps.username !== this.props.username) {
      this.latestTimestamp = null;
      this.setState({ conversation: null, message: '' }, () => {
        if (this.props.active !== false && !document.hidden) {
          this.fetchConversation();
          this.focusInput();
        }
      });
    }

    if (previousProps.active === false && this.props.active !== false) {
      this.startPolling();
    }

    if (previousProps.active !== false && this.props.active === false) {
      this.stopPolling();
    }
  }

  componentWillUnmount() {
    this.mounted = false;
    this.stopPolling();
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
  }

  fetchConversation = () => {
    const { username } = this.props;
    if (!username) {
      if (this.mounted) {
        this.setState({ conversation: null, loading: false });
      }
      return Promise.resolve();
    }
    if (this.conversationRequest?.username === username) {
      return this.conversationRequest.promise;
    }

    if (!this.state.conversation) {
      this.setState({ loading: true });
    }

    const since =
      this.latestTimestamp === null ? null : Math.max(0, this.latestTimestamp - 1);
    const request = (async () => {
      try {
        const conversation = await chat.get({ since, username });
        if (
          !this.mounted ||
          document.hidden ||
          this.props.active === false ||
          this.props.username !== username
        ) {
          return;
        }
        const normalizedConversation =
          conversation && typeof conversation === 'object' && !Array.isArray(conversation)
            ? conversation
            : null;
        if (!normalizedConversation) {
          this.setState({ loading: false });
          return;
        }

        const received = asArray(normalizedConversation.messages).filter(
          (message) =>
            message && typeof message === 'object' && !Array.isArray(message),
        );
        received.forEach((message) => {
          const timestamp = messageTimestamp(message);
          if (this.latestTimestamp === null || timestamp > this.latestTimestamp) {
            this.latestTimestamp = timestamp;
          }
        });

        if (normalizedConversation.hasUnAcknowledgedMessages) {
          chat.acknowledge({ username }).catch(() => {});
        }

        let shouldScroll = false;
        this.setState((previous) => {
          const byId = new Map(
            asArray(previous.conversation?.messages).map((message) => [
              messageIdentity(message),
              message,
            ]),
          );
          received.forEach((message) => byId.set(messageIdentity(message), message));
          const messages = Array.from(byId.values())
            .sort(
              (left, right) =>
                messageTimestamp(left) - messageTimestamp(right) ||
                messageIdentity(left).localeCompare(messageIdentity(right)),
            )
            .slice(-MAX_CACHED_MESSAGES);
          const next = { ...normalizedConversation, messages };
          if (conversationsMatch(previous.conversation, next) && !previous.loading) {
            return null;
          }

          shouldScroll = true;
          return { conversation: next, loading: false };
        }, () => {
          if (shouldScroll) {
            this.scrollToLatestMessage();
          }
        });
      } catch (error) {
        console.error('Failed to fetch conversation:', error);
        if (this.mounted && this.props.username === username) {
          this.setState({ loading: false });
        }
      }
    })();
    const tracked = {
      promise: request.finally(() => {
        if (this.conversationRequest === tracked) {
          this.conversationRequest = null;
        }
      }),
      username,
    };
    this.conversationRequest = tracked;
    return tracked.promise;
  };

  scrollToLatestMessage = () => {
    try {
      if (this.listRef.current?.lastChild) {
        this.listRef.current.lastChild.scrollIntoView();
      }
    } catch {
      // no-op
    }
  };

  sendMessage = async (message) => {
    const { username } = this.props;
    if (!username || !message) return;

    await chat.send({ message, username });
    this.setState({ message: '' });

    // Refresh to show new message
    await this.fetchConversation();
  };

  sendReply = async () => {
    const { message } = this.state;
    if (!message || !message.trim()) return;

    await this.sendMessage(message.trim());
  };

  validInput = () => {
    const { username } = this.props;
    const { message } = this.state;
    return username && message && message.trim().length > 0;
  };

  focusInput = () => {
    if (this.messageRef?.current) {
      this.messageRef.current.focus();
    }
  };

  handleFocusInput = () => {
    this.focusInput();
  };

  formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const dtfUS = new Intl.DateTimeFormat('en', {
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      month: 'numeric',
    });

    return dtfUS.format(date);
  };

  deleteConversation = async () => {
    const { onDelete, username } = this.props;
    if (!username) return;

    await chat.remove({ username });
    if (onDelete) {
      onDelete(username);
    }
  };

  render() {
    const { user, username } = this.props;
    const { conversation, loading, message } = this.state;
    const messages = asArray(conversation?.messages).filter(
      (item) => item && typeof item === 'object' && !Array.isArray(item),
    );

    if (!username) {
      return (
        <PlaceholderSegment
          caption="Select a conversation or start a new chat"
          icon="comment"
        />
      );
    }

    if (this.props.active === false) {
      return (
        <Card className="chat-active-card">
          <Card.Content>
            <Card.Header>
              <Icon
                color="grey"
                name="comment"
              />
              {username}
              <TooltipButton
                aria-label={interfaceText("Delete saved conversation with {username}", { "username": (username) })}
                basic
                className="close-button"
                compact
                icon
                onClick={this.deleteConversation}
                tooltip={`Delete the saved direct-message conversation with ${username} and remove it from your chat list.`}
               {...interfaceTextProps("Delete saved conversation with {username}")}>
                <Icon color="red" name="close" />
              </TooltipButton>
            </Card.Header>
          </Card.Content>
        </Card>
      );
    }

    return (
      <Card
        className="chat-active-card"
        raised
      >
        <Card.Content onClick={this.handleFocusInput}>
          <Card.Header>
            <Icon
              color="green"
              name="circle"
            />
            <UserCard username={username}>{username}</UserCard>
              <TooltipButton
                aria-label={interfaceText("Delete saved conversation with {username}", { "username": (username) })}
                basic
                className="close-button"
                compact
                icon
                onClick={this.deleteConversation}
                tooltip={`Delete the saved direct-message conversation with ${username} and remove it from your chat list.`}
               {...interfaceTextProps("Delete saved conversation with {username}")}>
                <Icon color="red" name="close" />
              </TooltipButton>
          </Card.Header>
          <div className="chat">
            {loading ? (
              <Dimmer
                active
                inverted
              >
                <Loader inverted />
              </Dimmer>
            ) : (
              <Segment.Group>
                <Segment className="chat-history">
                  <List ref={this.listRef}>
                    {messages.map((message) => (
                      <List.Content
                        className={`chat-message ${message.direction === 'Out' ? 'chat-message-self' : ''}`}
                        key={`${message.timestamp}+${message.message}`}
                      >
                        <span className="chat-message-time">
                          {this.formatTimestamp(message.timestamp)}
                        </span>
                        <span className="chat-message-name">
                          {message.direction === 'Out'
                            ? user?.username || interfaceText('You')
                            : message.username}
                          :{' '}
                        </span>
                        <span className="chat-message-message">
                          {message.message}
                        </span>
                      </List.Content>
                    ))}
                    <List.Content id="chat-history-scroll-anchor" />
                  </List>
                </Segment>
                <Segment className="chat-input">
                  <Input
                    action={{
                      'aria-label': interfaceText("Send chat message"),
                      className: 'chat-message-button',
                      disabled: !this.validInput(),
                      icon: (
                        <Icon
                          color="green"
                          name="send"
                        />
                      ),
                      onClick: this.sendReply,
                      title: interfaceText("Send chat message to this user"),
                    }}
                    fluid
                    input={
                      <input
                        autoComplete="off"
                        data-lpignore="true"
                        id="chat-message-input"
                        type="text"
                      />
                    }
                    onChange={(event, { value }) =>
                      this.setState({ message: value })
                    }
                    onKeyUp={(event) =>
                      event.key === 'Enter' ? this.sendReply() : ''
                    }
                    ref={(input) => (this.messageRef = input && input.inputRef)}
                    transparent
                    value={message}
                  />
                </Segment>
              </Segment.Group>
            )}
          </div>
        </Card.Content>
      </Card>
    );
  }
}

export default ChatSession;
