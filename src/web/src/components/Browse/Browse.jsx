import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import BrowseSession from './BrowseSession';
import { getLocalStorageItem, setLocalStorageItem } from '../../lib/storage';
import TooltipButton from '../Shared/TooltipButton';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Icon, Menu, Tab } from 'semantic-ui-react';

let tabCounter = 0;

const isTab = (tab) =>
  tab && typeof tab === 'object' && !Array.isArray(tab) && typeof tab.key === 'string';

const normalizeTab = (tab) => ({
  key: tab.key,
  label: typeof tab.label === 'string' && tab.label ? tab.label : 'New Tab',
  username: typeof tab.username === 'string' ? tab.username : '',
});

const createBrowseTab = (username = '') => {
  tabCounter += 1;
  return {
    key: `tab-${tabCounter}`,
    label: username || interfaceText('New Tab'),
    username,
  };
};

// Load tabs from localStorage
const loadTabsFromStorage = () => {
  try {
    const saved = getLocalStorageItem('slskd-browse-tabs');

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
    'slskd-browse-tabs',
    JSON.stringify({ tabCounter, tabs: tabsToSave }),
  );
};

const Browse = () => {
  useInterfaceLanguage();
  const location = useLocation();
  const requestedUser =
    location.state?.user ||
    new URLSearchParams(location.search).get('user') ||
    '';
  const requestedUsername = requestedUser.trim();
  const initialTabsRef = useRef(null);

  if (initialTabsRef.current === null) {
    const savedTabs = loadTabsFromStorage();
    const requestedIndex = requestedUsername
      ? savedTabs.findIndex((tab) => tab.username === requestedUsername)
      : -1;

    if (requestedUsername && requestedIndex === -1) {
      initialTabsRef.current = {
        activeIndex: savedTabs.length,
        tabs: [...savedTabs, createBrowseTab(requestedUsername)],
      };
    } else {
      initialTabsRef.current = {
        activeIndex: requestedIndex >= 0 ? requestedIndex : 0,
        tabs: savedTabs,
      };
    }
  }

  const [tabs, setTabs] = useState(() => initialTabsRef.current.tabs);
  const [activeIndex, setActiveIndex] = useState(
    () => initialTabsRef.current.activeIndex,
  );
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

  const createTab = useCallback((username = '') => createBrowseTab(username), []);

  // Create initial tab on mount
  useEffect(() => {
    if (tabs.length === 0 && !requestedUsername) {
      setTabs([createTab()]);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-create tab if all closed, and reset counter to keep numbers reasonable
  useEffect(() => {
    if (tabs.length === 0 && !requestedUsername) {
      tabCounter = 0; // Reset counter when starting fresh
      setTabs([createTab()]);
    }
  }, [tabs.length, createTab, requestedUsername]);

  // Save tabs to localStorage whenever they change
  useEffect(() => {
    if (tabs.length > 0) {
      saveTabsToStorage(tabs);
    }
  }, [tabs]);

  // Handle navigation with user in state or URL (quick browse from search; URL supports new tabs)
  useEffect(() => {
    const user = requestedUsername;

    if (user) {
      setTabs((previous) => {
        const existingIndex = previous.findIndex((t) => t.username === user);
        if (existingIndex !== -1) {
          setActiveIndex(existingIndex);
          return previous;
        }

        const newTabs = [...previous, createTab(user)];
        setActiveIndex(newTabs.length - 1);
        return newTabs;
      });

      // Clear the state to prevent re-triggering
      if (location.state?.user) {
        window.history.replaceState({}, document.title);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedUsername]);

  const handleAddTab = () => {
    setTabs((previous) => {
      const newTabs = [...previous, createTab()];
      setActiveIndex(newTabs.length - 1);
      return newTabs;
    });
  };

  const panes = tabs.map((tab) => ({
    menuItem: (
      <Menu.Item key={tab.key}>
        <Icon name={tab.username ? 'folder open' : 'search'} />
        {tab.label}
        {tabs.length > 1 && (
          <TooltipButton
            aria-label={interfaceText("Close {label} browse tab", { "label": (tab.label) })}
            basic
            className="browse-tab-close"
            compact
            icon
            onClick={(event) => {
              event.stopPropagation();
              closeTabRef.current?.(tab.key);
            }}
            size="mini"
            style={{ marginLeft: '8px', opacity: 0.7 }}
            tooltip="Close the {label} browse tab without changing the user's shared files."
           {...interfaceTextProps("Close {label} browse tab", { label: tab.label })}>
            <Icon name="close" />
          </TooltipButton>
        )}
      </Menu.Item>
    ),
    render: () => (
      <Tab.Pane
        attached={false}
        key={tab.key}
        style={{ border: 'none', boxShadow: 'none' }}
      >
        <BrowseSession
          key={tab.key}
          onUsernameChange={(newUsername) =>
            updateTabRef.current?.(tab.key, newUsername)
          }
          username={tab.username}
        />
      </Tab.Pane>
    ),
  }));

  return (
    <div className="browse-page">
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
                aria-label={interfaceText("Open a new browse tab")}
                key="add-tab"
                onClick={handleAddTab}
                title={interfaceText("Open a new browse tab")}
               {...interfaceTextProps("Open a new browse tab")}>
                <Icon name="plus" />
              </Menu.Item>
            ),
            render: () => null,
          },
        ]}
        renderActiveOnly
      />
    </div>
  );
};

export default Browse;
