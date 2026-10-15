import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import './Rooms.css';
import { getLocalStorageItem, setLocalStorageItem } from '../../lib/storage';
import * as rooms from '../../lib/rooms';
import PlaceholderSegment from '../Shared/PlaceholderSegment';
import RoomCreateModal from './RoomCreateModal';
import RoomJoinModal from './RoomJoinModal';
import RoomSession from './RoomSession';
import TooltipButton from '../Shared/TooltipButton';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import {
  Button,
  Dropdown,
  Icon,
  Menu,
  Popup,
  Segment,
  Tab,
} from 'semantic-ui-react';

let tabCounter = 0;
const asArray = (value) => (Array.isArray(value) ? value : []);
const isTab = (tab) =>
  tab && typeof tab === 'object' && !Array.isArray(tab) && typeof tab.key === 'string';
const sameStringList = (previous, next) =>
  previous.length === next.length &&
  previous.every((value, index) => value === next[index]);

const normalizeTab = (tab) => ({
  key: tab.key,
  label: typeof tab.label === 'string' && tab.label ? tab.label : 'New Room Tab',
  roomName: typeof tab.roomName === 'string' ? tab.roomName : '',
});

// Load tabs from localStorage
const loadTabsFromStorage = () => {
  try {
    const saved = getLocalStorageItem('slskd-room-tabs');

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
    'slskd-room-tabs',
    JSON.stringify({ tabCounter, tabs: tabsToSave }),
  );
};

const Rooms = () => {
  useInterfaceLanguage();
  const navigate = useNavigate();
  const [tabs, setTabs] = useState(() => loadTabsFromStorage());
  const [activeIndex, setActiveIndex] = useState(0);
  const [availableRooms, setAvailableRooms] = useState([]);
  const [joinedRooms, setJoinedRooms] = useState([]);
  const [roomSearchLoading, setRoomSearchLoading] = useState(false);
  const closeTabRef = useRef(null);
  const hydrationInFlightRef = useRef(null);
  const hydrationIntervalRef = useRef(null);
  const mountedRef = useRef(true);

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

  closeTabRef.current = closeTab;

  const createTab = useCallback((roomName = '') => {
    tabCounter += 1;
    const tabKey = `room-tab-${tabCounter}`;
    return {
      key: tabKey,
      label: roomName || interfaceText('New Room Tab'),
      roomName,
    };
  }, []);

  // Create initial tab on mount
  useEffect(() => {
    if (tabs.length === 0) {
      setTabs([createTab()]);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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

  const openRoomTab = useCallback(
    (roomName) => {
      if (!roomName) return;

      const existingTabIndex = tabs.findIndex((t) => t.roomName === roomName);
      if (existingTabIndex === -1) {
        setTabs((previous) => {
          const newTabs = [...previous, createTab(roomName)];
          setActiveIndex(newTabs.length - 1);
          return newTabs;
        });
      } else {
        setActiveIndex(existingTabIndex);
      }
    },
    [createTab, tabs],
  );

  const hydrateJoinedRooms = useCallback(() => {
    if (hydrationInFlightRef.current) {
      return hydrationInFlightRef.current;
    }

    const request = (async () => {
      try {
        const joined = await rooms.getJoined();
        if (!mountedRef.current || document.hidden) return;

        const normalized = asArray(joined)
          .filter((roomName) => typeof roomName === 'string' && roomName)
          .sort();
        setJoinedRooms((previous) =>
          sameStringList(previous, normalized) ? previous : normalized,
        );
        if (normalized.length > 0) {
          setTabs((previous) => {
            const existingRooms = new Set(
              previous.map((tab) => tab.roomName).filter(Boolean),
            );
            const restoredTabs = normalized
              .filter((roomName) => !existingRooms.has(roomName))
              .map((roomName) => createTab(roomName));

            return restoredTabs.length > 0
              ? [...previous.filter((tab) => tab.roomName), ...restoredTabs]
              : previous;
          });
        }
      } catch (error) {
        console.error('Failed to fetch joined rooms:', error);
      }
    })();
    const trackedRequest = request.finally(() => {
      if (hydrationInFlightRef.current === trackedRequest) {
        hydrationInFlightRef.current = null;
      }
    });
    hydrationInFlightRef.current = trackedRequest;
    return trackedRequest;
  }, [createTab]);

  useEffect(() => {
    mountedRef.current = true;
    const stopPolling = () => {
      if (hydrationIntervalRef.current) {
        window.clearInterval(hydrationIntervalRef.current);
        hydrationIntervalRef.current = null;
      }
    };
    const startPolling = () => {
      if (document.hidden || hydrationIntervalRef.current) return;
      hydrationIntervalRef.current = window.setInterval(hydrateJoinedRooms, 10_000);
    };
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
        return;
      }

      hydrateJoinedRooms();
      startPolling();
    };

    if (!document.hidden) {
      hydrateJoinedRooms();
      startPolling();
    }
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      mountedRef.current = false;
      hydrationInFlightRef.current = null;
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [hydrateJoinedRooms]);

  const fetchAvailableRooms = async () => {
    setRoomSearchLoading(true);
    try {
      const available = await rooms.getAvailable();
      setAvailableRooms(
        asArray(available)
          .filter((room) => room && typeof room === 'object' && !Array.isArray(room)),
      );
    } catch {
      setAvailableRooms([]);
    } finally {
      setRoomSearchLoading(false);
    }
  };

  const joinRoom = async (roomName) => {
    try {
      await rooms.join({ roomName });

      // Refresh joined rooms
      const joined = await rooms.getJoined();
      setJoinedRooms(
        asArray(joined)
          .filter((joinedRoomName) => typeof joinedRoomName === 'string' && joinedRoomName)
          .sort(),
      );
      openRoomTab(roomName);
    } catch (error) {
      console.error('Failed to join room:', error);
      toast.error(interfaceText('Failed to join room "{roomName}": {message}', {
        roomName,
        message: getApiErrorMessage(error, { t: interfaceText }),
      }));
    }
  };

  const leaveRoom = async (roomName) => {
    try {
      await rooms.leave({ roomName });

      // Refresh joined rooms
      const joined = await rooms.getJoined();
      setJoinedRooms(asArray(joined).filter(Boolean).sort());

      // Close the tab for this room
      const tabToClose = tabs.find((t) => t.roomName === roomName);
      if (tabToClose) {
        closeTabRef.current?.(tabToClose.key);
      }
    } catch (error) {
      console.error('Failed to leave room:', error);
    }
  };

  const createRoom = async (roomName, isPrivate) => {
    if (isPrivate) {
      throw new Error(interfaceText('Private room creation is not supported by this server API.'));
    }

    await joinRoom(roomName);
  };

  const handleAddTab = () => {
    setTabs((previous) => {
      const newTabs = [...previous, createTab()];
      setActiveIndex(newTabs.length - 1);
      return newTabs;
    });
  };

  const handleUserProfile = useCallback(
    (username) => {
      navigate(`/users?user=${encodeURIComponent(username)}`, {
        state: { user: username },
      });
    },
    [navigate],
  );

  const handleBrowseShares = useCallback(
    (username) => {
      navigate(`/browse?user=${encodeURIComponent(username)}`, {
        state: { user: username },
      });
    },
    [navigate],
  );

  const roomOptions = useMemo(
    () =>
      availableRooms
        .slice()
        .sort((a, b) => (b.userCount || 0) - (a.userCount || 0))
        .slice(0, 100)
        .map((r) => ({
          description: r.isPrivate ? interfaceText('Private') : '',
          key: r.name,
          text: `${r.name} (${r.userCount} users)`,
          value: r.name,
        })),
    [availableRooms],
  );

  const panes = tabs.map((tab, index) => ({
    menuItem: (
      <Menu.Item key={tab.key}>
        <Icon name={tab.roomName ? 'comments' : 'search'} />
        {tab.label}
        {tabs.length > 1 && (
          <TooltipButton
            aria-label={interfaceText("Close {label} room tab", { "label": (tab.label) })}
            basic
            className="room-tab-close"
            compact
            icon
            onClick={(event) => {
              event.stopPropagation();
              closeTabRef.current?.(tab.key);
            }}
            size="mini"
            style={{ marginLeft: '8px', opacity: 0.7 }}
            tooltip="Close the {label} room tab without leaving the Soulseek room."
           {...interfaceTextProps("Close {label} room tab", { label: tab.label })}>
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
        <RoomSession
          active={index === activeIndex}
          key={tab.key}
          onBrowseShares={handleBrowseShares}
          onLeaveRoom={leaveRoom}
          onUserProfile={handleUserProfile}
          roomName={tab.roomName}
        />
      </Tab.Pane>
    ),
  }));

  return (
    <div className="rooms">
      <Segment
        className="rooms-segment"
        raised
      >
        <div className="rooms-segment-icon">
          <Icon
            name="comments"
            size="big"
          />
        </div>
        <div
          style={{
            display: 'flex',
            flex: 1,
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <div style={{ alignItems: 'center', display: 'flex', gap: '8px' }}>
            <Dropdown
              className="rooms-input"
              clearable
              fluid
              loading={roomSearchLoading}
              onChange={(_, { value }) => {
                if (value) {
                  joinRoom(value);
                }
              }}
              onOpen={() => fetchAvailableRooms()}
              options={roomOptions}
              placeholder={interfaceText("Search existing rooms...")}
              search
              selection
             {...interfaceTextProps("Search existing rooms...")}/>
            <RoomJoinModal joinRoom={joinRoom} />
            <RoomCreateModal onCreateRoom={createRoom} />
            <Popup
              content={interfaceText("Reload rooms joined by the daemon and reopen their tabs.")}
              trigger={
                <Button
                  aria-label={interfaceText("Reload joined rooms")}
                  icon="refresh"
                  onClick={hydrateJoinedRooms}
                  title={interfaceText("Reload joined rooms")}
                 {...interfaceTextProps("Reload joined rooms")}/>
              }
             {...interfaceTextProps("Reload rooms joined by the daemon and reopen their tabs.")}/>
          </div>
        </div>
      </Segment>
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
                aria-label={interfaceText("Open a new room tab")}
                key="add-tab"
                onClick={handleAddTab}
                title={interfaceText("Open a new room tab")}
               {...interfaceTextProps("Open a new room tab")}>
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

export default Rooms;
