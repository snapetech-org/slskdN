import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import './Chat.css';
import { activeChatKey } from '../../config';
import * as chat from '../../lib/chat';
import {
  getLocalStorageItem,
  getSessionStorageItem,
  removeSessionStorageItem,
  setLocalStorageItem,
} from '../../lib/storage';
import ChatSession from './ChatSession';
import TooltipButton from '../Shared/TooltipButton';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Button,
  Icon,
  Input,
  Label,
  Menu,
  Popup,
  Segment,
  Tab,
} from 'semantic-ui-react';

let tabCounter = 0;
const asArray = (value) => (Array.isArray(value) ? value : []);
const isTab = (tab) =>
  tab && typeof tab === 'object' && !Array.isArray(tab) && typeof tab.key === 'string';

const normalizeTab = (tab) => ({
  key: tab.key,
  label: typeof tab.label === 'string' && tab.label ? tab.label : 'New Chat',
  username: typeof tab.username === 'string' ? tab.username : '',
});

// Load tabs from localStorage
const loadTabsFromStorage = () => {
  try {
    const saved = getLocalStorageItem('slskd-chat-tabs');

    if (saved) {
      const parsed = JSON.parse(saved);
      if (!Array.isArray(parsed.tabs)) {
        return [];
      }

      // Restore tabCounter to avoid key collisions
      tabCounter = Number.isInteger(parsed.tabCounter) && parsed.tabCounter >= 0
        ? parsed.tabCounter
        : 0;
      return parsed.tabs.filter(isTab).map(normalizeTab);
    }
  } catch {
    // ignore
  }

  return [];
};

// Save tabs to localStorage
const saveTabsToStorage = (tabsToSave) => {
  setLocalStorageItem(
    'slskd-chat-tabs',
    JSON.stringify({ tabCounter, tabs: tabsToSave }),
  );
};

const Chat = ({ state }) => {
  useInterfaceLanguage();
  const location = useLocation();
  const [tabs, setTabs] = useState(() => loadTabsFromStorage());
  const [activeIndex, setActiveIndex] = useState(0);
  const [conversations, setConversations] = useState([]);
  const [usernameInput, setUsernameInput] = useState('');
  const closeTabRef = useRef(null);
  const updateTabRef = useRef(null);

  const closeTab = useCallback((tabKey) => {
    setTabs((previous) => {
      const newTabs = previous.filter((t) => t.key !== tabKey);
      setActiveIndex((currentIndex) =>
        currentIndex >= newTabs.length
          ? Math.max(0, newTabs.length - 1)
          : currentIndex,
      );
      return newTabs;
    });
  }, []);

  const updateTabLabel = useCallback((tabKey, newUsername) => {
    setTabs((previous) =>
      previous.map((t) =>
        t.key === tabKey
          ? { ...t, label: newUsername, username: newUsername }
          : t,
      ),
    );
  }, []);

  closeTabRef.current = closeTab;
  updateTabRef.current = updateTabLabel;

  const createTab = useCallback((username = '') => {
    tabCounter += 1;
    const tabKey = `chat-tab-${tabCounter}`;
    return {
      key: tabKey,
      label: username || 'New Chat',
      username,
    };
  }, []);

  const startConversation = useCallback(
    (username) => {
      if (!username || !username.trim()) return;

      const trimmedUsername = username.trim();
      const existingIndex = tabs.findIndex(
        (t) => t.username === trimmedUsername,
      );

      if (existingIndex === -1) {
        setTabs((previous) => {
          const newTabs = [...previous, createTab(trimmedUsername)];
          setActiveIndex(newTabs.length - 1);
          return newTabs;
        });
      } else {
        setActiveIndex(existingIndex);
      }
    },
    [createTab, tabs],
  );

  const hydrateConversations = useCallback(async () => {
    try {
      const serverConversations = await chat.getAll();
      const activeConversations = asArray(serverConversations)
        .filter((conversation) =>
          conversation && typeof conversation === 'object' && !Array.isArray(conversation))
        .filter((conversation) => typeof conversation.username === 'string' && conversation.username)
        .sort((a, b) => {
          if (a.hasUnAcknowledgedMessages !== b.hasUnAcknowledgedMessages) {
            return a.hasUnAcknowledgedMessages ? -1 : 1;
          }

          return a.username.localeCompare(b.username);
        });

      setConversations(activeConversations);
      if (activeConversations.length > 0) {
        setTabs((previous) => {
          const existingUsernames = new Set(
            previous.map((tab) => tab.username).filter(Boolean),
          );
          const restoredTabs = activeConversations
            .filter((conversation) => !existingUsernames.has(conversation.username))
            .map((conversation) => createTab(conversation.username));

          return restoredTabs.length > 0
            ? [...previous.filter((tab) => tab.username), ...restoredTabs]
            : previous;
        });
      }
    } catch (error) {
      console.error('Failed to hydrate conversations:', error);
    }
  }, [createTab]);

  // Create initial tab on mount if none exist
  useEffect(() => {
    if (tabs.length === 0) {
      setTabs([createTab()]);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    hydrateConversations();
  }, [hydrateConversations]);

  // Auto-create tab if all closed, and reset counter to keep numbers reasonable
  useEffect(() => {
    if (tabs.length === 0) {
      tabCounter = 0; // Reset counter when starting fresh
      setTabs([createTab()]);
    }
  }, [tabs.length, createTab]);

  // Save tabs to localStorage whenever they change
  useEffect(() => {
    if (tabs.length > 0) {
      saveTabsToStorage(tabs);
    }
  }, [tabs]);

  // Handle navigation with username in URL or state.
  useEffect(() => {
    const username =
      location.state?.user ||
      new URLSearchParams(location.search).get('user') ||
      getSessionStorageItem(activeChatKey);

    if (username) {
      const existingIndex = tabs.findIndex((t) => t.username === username);

      if (existingIndex === -1) {
        // Create new tab for this user
        setTabs((previous) => {
          const newTabs = [...previous, createTab(username)];
          setActiveIndex(newTabs.length - 1);
          return newTabs;
        });
      } else {
        setActiveIndex(existingIndex);
      }

      // Clear the state to prevent re-triggering
      window.history.replaceState({}, document.title);
      removeSessionStorageItem(activeChatKey);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search, location.state]);

  const handleAddTab = () => {
    setTabs((previous) => {
      const newTabs = [...previous, createTab()];
      setActiveIndex(newTabs.length - 1);
      return newTabs;
    });
  };

  const handleDeleteConversation = useCallback(
    async (username) => {
      // Remove the conversation from chat API
      try {
        await chat.remove({ username });
      } catch (error) {
        console.error('Failed to remove conversation:', error);
      }

      // Close the tab
      const tabToClose = tabs.find((t) => t.username === username);
      if (tabToClose) {
        closeTabRef.current?.(tabToClose.key);
      }
    },
    [tabs],
  );

  const panes = tabs.map((tab, index) => ({
    menuItem: (
      <Menu.Item key={tab.key}>
        <Icon name={tab.username ? 'comment' : 'search'} />
        {tab.label}
        {tabs.length > 1 && (
          <TooltipButton
            aria-label={interfaceText("Close {label} chat tab", { "label": (tab.label) })}
            basic
            className="chat-tab-close"
            compact
            icon
            onClick={(event) => {
              event.stopPropagation();
              closeTabRef.current?.(tab.key);
            }}
            size="mini"
            style={{ marginLeft: '8px', opacity: 0.7 }}
            tooltip={`Close the ${tab.label} tab. Its saved conversation remains available in the chat list.`}
           {...interfaceTextProps("Close {label} chat tab")}>
            <Icon name="close" />
          </TooltipButton>
        )}
      </Menu.Item>
    ),
    pane: (
      <Tab.Pane
        attached={false}
        key={tab.key}
        style={{ border: 'none', boxShadow: 'none' }}
      >
        <ChatSession
          active={index === activeIndex}
          key={tab.key}
          onDelete={handleDeleteConversation}
          user={state?.user}
          username={tab.username}
        />
      </Tab.Pane>
    ),
  }));

  return (
    <div className="chats">
      <Segment
        className="chat-segment"
        raised
      >
        <div className="chat-segment-icon">
          <Icon
            name="comment"
            size="big"
          />
        </div>
        <Input
          action={{
            'aria-label': interfaceText("Start chat with user"),
            icon: 'chat',
            onClick: () => {
              if (usernameInput?.trim()) {
                startConversation(usernameInput.trim());
                setUsernameInput('');
              }
            },
            title: interfaceText("Start chat with user"),
          }}
          className="chat-input"
          onChange={(event) => setUsernameInput(event.target.value)}
          onKeyUp={(event) => {
            if (event.key === 'Enter' && usernameInput?.trim()) {
              startConversation(usernameInput.trim());
              setUsernameInput('');
            }
          }}
          placeholder={interfaceText("Chat with user...")}
          size="big"
          value={usernameInput}
         {...interfaceTextProps("Chat with user...")}/>
        <Popup
          content={interfaceText("Reload saved conversations from the server after a browser refresh or restart.")}
          trigger={
            <Button
              aria-label={interfaceText("Reload saved conversations")}
              icon="refresh"
              onClick={hydrateConversations}
              title={interfaceText("Reload saved conversations")}
             {...interfaceTextProps("Reload saved conversations")}/>
          }
         {...interfaceTextProps("Reload saved conversations from the server after a browser refresh or restart.")}/>
      </Segment>
      {conversations.length > 0 && (
        <Segment className="chat-recovery-rail">
          {conversations.map((conversation) => (
            <Popup
              content={interfaceText("Open this saved conversation.")}
              key={conversation.username}
              trigger={
                <Button
                  basic
                  compact
                  onClick={() => startConversation(conversation.username)}
                  size="small"
                >
                  <Icon name="comment alternate" />
                  {conversation.username}
                  {conversation.hasUnAcknowledgedMessages && (
                    <Label
                      circular
                      color="red"
                      size="mini"
                    >
                      {conversation.unAcknowledgedMessageCount}
                    </Label>
                  )}
                </Button>
              }
             {...interfaceTextProps("Open this saved conversation.")}/>
          ))}
        </Segment>
      )}
      <Tab
        activeIndex={activeIndex}
        menu={{
          attached: false,
          inverted: true,
          secondary: true,
          tabular: false,
        }}
        onTabChange={(event, { activeIndex: newIndex }) =>
          setActiveIndex(newIndex)
        }
        panes={[
          ...panes,
          {
            menuItem: (
              <Menu.Item
                aria-label={interfaceText("Open a new chat tab")}
                key="add-tab"
                onClick={handleAddTab}
                title={interfaceText("Open a new chat tab")}
               {...interfaceTextProps("Open a new chat tab")}>
                <Icon name="plus" />
              </Menu.Item>
            ),
            pane: null,
          },
        ]}
        renderActiveOnly={false}
      />
    </div>
  );
};

export default Chat;
