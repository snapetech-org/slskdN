import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import { getRegionalLocale } from '../../lib/regionalFormat';
import './MessagingV2.css';
import * as chat from '../../lib/chat';
import {
  applyHumanChallengeAutoResponse,
  canApplyHumanChallengeAutoResponse,
  getHumanChallengeAutoResponseEnabled,
  readStoredHumanChallengeAutoResponse,
  writeStoredHumanChallengeAutoResponse,
} from '../../lib/humanChallengeAutoResponse';
import {
  loadWorkspace,
  makeTabId,
  MEMBER_WIDTH_RANGE,
  saveWorkspace,
  TREE_WIDTH_RANGE,
  ZOOM_LEVELS,
} from '../../lib/messagingStorage';
import * as pods from '../../lib/pods';
import * as rooms from '../../lib/rooms';
import * as slskdn from '../../lib/slskdn';
import Composer from './Composer';
import {
  asArray,
  channelLabel,
  decodePodTarget,
  encodePodTarget,
  isPodDirectChannel,
} from './Messaging';
import {
  createChatAdapter,
  createPodAdapter,
  createRoomAdapter,
} from './messagingAdapters';
import CommandHelp from './CommandHelp';
import MessageStream from './MessageStream';
import QuickSwitcher from './QuickSwitcher';
import UserPopover from './UserPopover';
import AppContext from '../AppContext';
import PodListenAlongPanel from '../Player/PodListenAlongPanel';
import React, {
  useContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Popup } from 'semantic-ui-react';
import { useNavigate, useParams } from 'react-router-dom';

const NETWORKS = ['all', 'soulseek', 'mesh'];
const ROOM_DIRECTORY_MAX_RETRIES = 20;
const MESSAGING_HYDRATION_INTERVAL_MS = 10_000;
const MEMBER_HYDRATION_INTERVAL_MS = 10_000;
const POD_HYDRATION_INTERVAL_MS = 60_000;

const COMPOSER_COMMANDS = [
  {
    get description() { return interfaceText("Send an italic action (e.g. /me waves)."); },
    name: 'me',
    syntax: '/me <action>',
  },
  {
    get description() { return interfaceText("Open a direct-message tab with the given user."); },
    name: 'msg',
    syntax: '/msg <user>',
  },
  {
    get description() { return interfaceText("Join (or create) a Soulseek room."); },
    name: 'join',
    syntax: '/join <room>',
  },
  {
    aliases: ['part', 'leave'],
    get description() { return interfaceText("Leave the current room or pod, or close the current DM tab."); },
    name: 'close',
    syntax: '/close',
  },
  {
    get description() { return interfaceText("Set message density."); },
    name: 'zoom',
    syntax: '/zoom <s|m|l|xl>',
  },
  {
    get description() { return interfaceText("Refetch messages for the current tab."); },
    name: 'reload',
    syntax: '/reload',
  },
  {
    get description() { return interfaceText("Open the channel switcher."); },
    name: 'switch',
    syntax: '/switch',
  },
  {
    get description() { return interfaceText("Show this command list."); },
    name: 'help',
    syntax: '/help',
  },
];

const tabAccent = (tab) => (tab.type === 'pod' ? 'mesh' : 'slsk');

const GOLD_STAR_CLUB_POD_ID = 'pod:901d57a2c1bb4e5d90d57a2c1bb4e5d0';

const tabLabel = (tab) => {
  if (tab.type === 'room') return `#${tab.target}`;
  if (tab.type === 'pod') return tab.label || interfaceText("Pod channel");
  return `@${tab.target}`;
};

const tabSubtitle = (tab) => {
  if (tab.type === 'room') return interfaceText("Soulseek room");
  if (tab.type === 'pod') return interfaceText("Mesh channel");
  return interfaceText("Soulseek DM");
};

const formatUnread = (count) => {
  if (!Number.isFinite(count) || count <= 0) return null;
  return count > 99 ? '99+' : String(count);
};

const conversationListSignature = (conversations) =>
  conversations
    .map((conversation) =>
      [
        conversation.username,
        conversation.hasUnAcknowledgedMessages === true ? '1' : '0',
        conversation.unAcknowledgedMessageCount || 0,
      ].join('\u0001'))
    .join('\u0002');

const roomListSignature = (rooms) => rooms.join('\u0001');

const getActionErrorDetail = (error) =>
  getApiErrorMessage(error, { t: interfaceText }, 'Please try again.');

const InlineLoadError = ({ message, onRetry, retryLabel, testId }) => (
  <div
    className="msgv2-tree-load-error"
    data-testid={testId}
    role="alert"
  >
    <span>{message}</span>
    <Popup
      content={interfaceText(retryLabel)}
      position="top center"
      trigger={(
        <button
          aria-label={interfaceText(retryLabel)}
          className="msgv2-tree-add-go"
          onClick={onRetry}
          title={interfaceText(retryLabel)}
          type="button"
        >
          <LocalizedText source={"Retry"} /></button>
      )}
    />
  </div>
);

const podChannelListSignature = (channels) =>
  channels
    .map((channel) =>
      [
        channel.channelId,
        channel.channelKind,
        channel.channelName,
        channel.podId,
        channel.podName,
        channel.target,
      ].join('\u0001'))
    .join('\u0002');

const discoveredPodListSignature = (podsToCompare) =>
  podsToCompare
    .map((pod) =>
      [
        pod.podId || pod.PodId,
        pod.name || pod.Name,
        pod.focusContentId || pod.FocusContentId,
        pod.visibility || pod.Visibility,
        asArray(pod.tags || pod.Tags).join('\u0003'),
      ].join('\u0001'))
    .join('\u0002');

const zoomIndex = (zoom) => Math.max(0, ZOOM_LEVELS.indexOf(zoom));

const MessagingV2 = ({ initialKind = 'mixed', state }) => {
  const { language } = useInterfaceLanguage();
  const navigate = useNavigate();
  const params = useParams();
  const appContext = useContext(AppContext) || {};
  const options = appContext.options || {};

  const [workspace, setWorkspace] = useState(loadWorkspace);
  const persistTimer = useRef(null);

  const persistWorkspace = useCallback((next) => {
    if (persistTimer.current) {
      window.clearTimeout(persistTimer.current);
    }
    persistTimer.current = window.setTimeout(() => {
      saveWorkspace(next);
    }, 200);
  }, []);

  const updateWorkspace = useCallback(
    (mutator) => {
      setWorkspace((previous) => {
        const next = mutator(previous);
        if (next === previous) return previous;
        persistWorkspace(next);
        return next;
      });
    },
    [persistWorkspace],
  );

  useEffect(() => () => {
    if (persistTimer.current) window.clearTimeout(persistTimer.current);
    if (roomDirectoryRetryTimer.current) {
      window.clearTimeout(roomDirectoryRetryTimer.current);
    }
  }, []);

  const [conversations, setConversations] = useState([]);
  const [joinedRooms, setJoinedRooms] = useState([]);
  const [availableRooms, setAvailableRooms] = useState([]);
  const [featureGates, setFeatureGates] = useState(null);
  const [messagingLoadError, setMessagingLoadError] = useState('');
  const [podLoadError, setPodLoadError] = useState('');
  const [podDiscoveryError, setPodDiscoveryError] = useState('');
  const [podChannels, setPodChannels] = useState([]);
  const [discoveredPods, setDiscoveredPods] = useState([]);
  const [networkFilter, setNetworkFilter] = useState('all');
  const [memberRailOpen, setMemberRailOpen] = useState(true);
  const [adapterMembers, setAdapterMembers] = useState([]);
  const [qsOpen, setQsOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [streamReloadToken, setStreamReloadToken] = useState(0);
  const [dmDraft, setDmDraft] = useState('');
  const [roomDraft, setRoomDraft] = useState('');
  const [podDraft, setPodDraft] = useState('');
  const [dmAddOpen, setDmAddOpen] = useState(false);
  const [roomAddOpen, setRoomAddOpen] = useState(false);
  const [roomJoinError, setRoomJoinError] = useState('');
  const [actionError, setActionError] = useState('');
  const [roomDirectoryLoading, setRoomDirectoryLoading] = useState(false);
  const [roomDirectoryRequested, setRoomDirectoryRequested] = useState(false);
  const [podAddOpen, setPodAddOpen] = useState(false);
  const [userPopover, setUserPopover] = useState(null);
  const [composerDraft, setComposerDraft] = useState('');
  const [humanCheckAutoResponseEnabled, setHumanCheckAutoResponseEnabled] =
    useState(() =>
      getHumanChallengeAutoResponseEnabled(options) ||
      readStoredHumanChallengeAutoResponse(),
    );
  const [humanCheckSaving, setHumanCheckSaving] = useState(false);
  const [humanCheckError, setHumanCheckError] = useState(false);
  const composerInputRef = useRef(null);
  const lastWheelZoomAt = useRef(0);
  const roomDirectoryRetryTimer = useRef(null);
  const roomDirectoryRetryCount = useRef(0);
  const messagingHydrationInFlight = useRef(null);
  const messagingHydrationInterval = useRef(null);
  const mountedRef = useRef(false);
  const podHydrationInFlight = useRef(null);
  const podHydrationInterval = useRef(null);
  const currentUser = state?.user?.username;
  const podsFeatureEnabled = featureGates?.pods?.enabled !== false;

  const reportActionFailure = useCallback((action, error) => {
    setActionError(interfaceText('{action}: {message}', {
      action: interfaceText(action),
      message: getActionErrorDetail(error),
    }));
  }, []);

  const hydrateMessaging = useCallback(() => {
    if (messagingHydrationInFlight.current) {
      return messagingHydrationInFlight.current;
    }

    const request = (async () => {
      try {
        const [serverConversations, serverJoinedRooms] = await Promise.all([
          chat.getAll(),
          rooms.getJoined(),
        ]);
        if (!mountedRef.current) return;

        setMessagingLoadError('');

        const nextConversations = asArray(serverConversations)
          .filter((c) => c && typeof c === 'object' && !Array.isArray(c) && c.username)
          .sort((a, b) => {
            if (a.hasUnAcknowledgedMessages !== b.hasUnAcknowledgedMessages) {
              return a.hasUnAcknowledgedMessages ? -1 : 1;
            }
            return a.username.localeCompare(b.username);
          });
        const nextJoinedRooms = asArray(serverJoinedRooms).filter(Boolean).sort();

        setConversations((previous) =>
          conversationListSignature(previous) === conversationListSignature(nextConversations)
            ? previous
            : nextConversations);
        setJoinedRooms((previous) =>
          roomListSignature(previous) === roomListSignature(nextJoinedRooms)
            ? previous
            : nextJoinedRooms);
      } catch (error) {
        if (mountedRef.current) {
          setMessagingLoadError(
            interfaceText('Could not load saved conversations and joined rooms: {message}', {
              message: getActionErrorDetail(error),
            }),
          );
        }
      }
    })();
    const trackedRequest = request.finally(() => {
      if (messagingHydrationInFlight.current === trackedRequest) {
        messagingHydrationInFlight.current = null;
      }
    });
    messagingHydrationInFlight.current = trackedRequest;
    return trackedRequest;
  }, []);

  const hydratePods = useCallback(() => {
    if (podHydrationInFlight.current) {
      return podHydrationInFlight.current;
    }

    const request = (async () => {
      try {
        let serverPods;
        try {
          serverPods = await pods.list();
        } catch (error) {
          if (mountedRef.current) {
            setPodLoadError(
              interfaceText('Could not load saved pod channels: {message}', {
                message: getActionErrorDetail(error),
              }),
            );
          }
          return;
        }

        let serverDiscoveredPods;
        try {
          serverDiscoveredPods = asArray(await (
            typeof pods.discoverAll === 'function'
              ? pods.discoverAll(50)
              : []
          ));
        } catch (error) {
          if (mountedRef.current) {
            setPodDiscoveryError(
              interfaceText('Could not refresh discovered pods: {message}', {
                message: getActionErrorDetail(error),
              }),
            );
          }
        }
        if (!mountedRef.current) return;

        setPodLoadError('');
        if (serverDiscoveredPods !== undefined) setPodDiscoveryError('');

        const nextDiscoveredPods = asArray(serverDiscoveredPods)
          .filter((pod) => pod && typeof pod === 'object' && !Array.isArray(pod))
          .sort((a, b) =>
            (a.name || a.Name || a.podId || a.PodId || '').localeCompare(
              b.name || b.Name || b.podId || b.PodId || '',
            ));
        const nextPodChannels = asArray(serverPods)
          .filter((pod) => pod && typeof pod === 'object' && !Array.isArray(pod))
          .flatMap((pod) =>
            asArray(pod.channels)
              .filter((channel) =>
                channel && typeof channel === 'object' && !Array.isArray(channel))
              .map((channel) => ({
                channelId: channel.channelId,
                channelKind: channel.kind,
                channelName: channel.name,
                podId: pod.podId,
                podName: pod.name || pod.podId,
                target: encodePodTarget(pod.podId, channel.channelId),
              })),
          )
          .sort((a, b) => channelLabel(a).localeCompare(channelLabel(b)));

        if (serverDiscoveredPods !== undefined) {
          setDiscoveredPods((previous) =>
            discoveredPodListSignature(previous) === discoveredPodListSignature(nextDiscoveredPods)
              ? previous
              : nextDiscoveredPods);
        }
        setPodChannels((previous) =>
          podChannelListSignature(previous) === podChannelListSignature(nextPodChannels)
            ? previous
            : nextPodChannels);
      } catch (error) {
        if (mountedRef.current) {
          setPodLoadError(
            interfaceText('Could not load pod channels: {message}', {
              message: getActionErrorDetail(error),
            }),
          );
        }
      }
    })();
    const trackedRequest = request.finally(() => {
      if (podHydrationInFlight.current === trackedRequest) {
        podHydrationInFlight.current = null;
      }
    });
    podHydrationInFlight.current = trackedRequest;
    return trackedRequest;
  }, []);

  const refreshMessagingAfterMutation = useCallback(async () => {
    if (messagingHydrationInFlight.current) {
      await messagingHydrationInFlight.current;
    }
    return hydrateMessaging();
  }, [hydrateMessaging]);

  const refreshPodsAfterMutation = useCallback(async () => {
    if (podHydrationInFlight.current) {
      await podHydrationInFlight.current;
    }
    return hydratePods();
  }, [hydratePods]);

  const refreshFeatureGates = useCallback(async () => {
    const capabilities = await slskdn.getCapabilities();
    const nextFeatureGates = capabilities?.featureGates || {};
    if (mountedRef.current) setFeatureGates(nextFeatureGates);
    return nextFeatureGates;
  }, []);

  const hydrate = useCallback(async () => {
    const gates = await refreshFeatureGates();
    await hydrateMessaging();
    if (gates.pods?.enabled !== false) await hydratePods();
  }, [hydrateMessaging, hydratePods, refreshFeatureGates]);

  const loadAvailableRooms = useCallback(async () => {
    setRoomDirectoryRequested(true);
    setRoomDirectoryLoading(true);
    const serverAvailableRooms = await Promise.resolve(rooms.getAvailable()).catch(() => null);
    const nextAvailableRooms = asArray(serverAvailableRooms)
        .map((room) => (typeof room === 'string' ? room : room?.name || room?.Name || ''))
        .filter(Boolean)
        .sort((a, b) => a.localeCompare(b));
    let retryScheduled = false;

    setAvailableRooms((previous) => {
      if (nextAvailableRooms.length > 0) {
        roomDirectoryRetryCount.current = 0;
        return nextAvailableRooms;
      }

      if (previous.length > 0) {
        return previous;
      }

      if (roomDirectoryRetryCount.current < ROOM_DIRECTORY_MAX_RETRIES && !roomDirectoryRetryTimer.current) {
        roomDirectoryRetryCount.current += 1;
        retryScheduled = true;
        roomDirectoryRetryTimer.current = window.setTimeout(() => {
          roomDirectoryRetryTimer.current = null;
          loadAvailableRooms().catch((error) => {
            console.error('Failed to retry available rooms:', error);
          });
        }, 1_500);
      }

      return nextAvailableRooms;
    });
    if (!retryScheduled) {
      setRoomDirectoryLoading(false);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    const stopPolling = () => {
      if (messagingHydrationInterval.current) {
        window.clearInterval(messagingHydrationInterval.current);
        messagingHydrationInterval.current = null;
      }
      if (podHydrationInterval.current) {
        window.clearInterval(podHydrationInterval.current);
        podHydrationInterval.current = null;
      }
    };
    const startPolling = () => {
      if (document.hidden) return;
      if (!messagingHydrationInterval.current) {
        messagingHydrationInterval.current = window.setInterval(
          hydrateMessaging,
          MESSAGING_HYDRATION_INTERVAL_MS,
        );
      }
      if (!podHydrationInterval.current) {
        podHydrationInterval.current = window.setInterval(async () => {
          const gates = await refreshFeatureGates();
          if (!mountedRef.current) return;
          if (gates.pods?.enabled !== false) await hydratePods();
        }, POD_HYDRATION_INTERVAL_MS);
      }
    };
    const refreshAndHydrate = async () => {
      await hydrate();
      if (!mountedRef.current) return;
      startPolling();
    };
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
        return;
      }

      void refreshAndHydrate();
    };

    if (!document.hidden) {
      void refreshAndHydrate();
    }
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      mountedRef.current = false;
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [hydrate, hydratePods, refreshFeatureGates]);

  useEffect(() => {
    if (!roomAddOpen) return;
    roomDirectoryRetryCount.current = 0;
    loadAvailableRooms().catch((error) => {
      console.error('Failed to load available rooms:', error);
    });
  }, [loadAvailableRooms, roomAddOpen]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      roomDirectoryRetryCount.current = 0;
      loadAvailableRooms().catch((error) => {
        console.error('Failed to warm available rooms:', error);
      });
    }, 3_000);
    return () => window.clearTimeout(timer);
  }, [loadAvailableRooms]);

  const visiblePodChannels = useMemo(
    () => podChannels.filter((channel) => !isPodDirectChannel(channel)),
    [podChannels],
  );
  const visibleWorkspaceTabs = podsFeatureEnabled
    ? workspace.tabs
    : workspace.tabs.filter((tab) => tab.type !== 'pod');

  const openTab = useCallback(
    (type, target, label) => {
      const trimmed = `${target || ''}`.trim();
      if (!trimmed) return;
      updateWorkspace((previous) => {
        const existing = previous.tabs.find(
          (tab) => tab.type === type && tab.target === trimmed,
        );
        if (existing) {
          if (previous.activeTabId === existing.id) return previous;
          return { ...previous, activeTabId: existing.id };
        }
        const counter = previous.tabCounter + 1;
        const id = makeTabId(counter, type);
        const newTab = { id, label, target: trimmed, type };
        return {
          ...previous,
          activeTabId: id,
          tabCounter: counter,
          tabs: [...previous.tabs, newTab],
        };
      });
    },
    [updateWorkspace],
  );

  const closeTab = useCallback(
    (tabId) => {
      updateWorkspace((previous) => {
        const tabs = previous.tabs.filter((tab) => tab.id !== tabId);
        let activeTabId = previous.activeTabId;
        if (activeTabId === tabId) {
          const closedIndex = previous.tabs.findIndex((tab) => tab.id === tabId);
          activeTabId = tabs[closedIndex]?.id ?? tabs[closedIndex - 1]?.id ?? null;
        }
        return { ...previous, activeTabId, tabs };
      });
    },
    [updateWorkspace],
  );

  const activateTab = useCallback(
    (tabId) => {
      updateWorkspace((previous) =>
        previous.activeTabId === tabId ? previous : { ...previous, activeTabId: tabId },
      );
    },
    [updateWorkspace],
  );

  const setZoom = useCallback(
    (zoom) => {
      if (!ZOOM_LEVELS.includes(zoom)) return;
      updateWorkspace((previous) =>
        previous.zoom === zoom ? previous : { ...previous, zoom },
      );
    },
    [updateWorkspace],
  );

  const adjustZoom = useCallback(
    (delta) => {
      updateWorkspace((previous) => {
        const currentIndex = zoomIndex(previous.zoom);
        const nextIndex = Math.min(
          ZOOM_LEVELS.length - 1,
          Math.max(0, currentIndex + delta),
        );
        const nextZoom = ZOOM_LEVELS[nextIndex];
        return previous.zoom === nextZoom ? previous : { ...previous, zoom: nextZoom };
      });
    },
    [updateWorkspace],
  );

  const handleWheelZoom = useCallback(
    (event) => {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      const now = Date.now();
      if (now - lastWheelZoomAt.current < 90) return;
      lastWheelZoomAt.current = now;
      adjustZoom(event.deltaY < 0 ? 1 : -1);
    },
    [adjustZoom],
  );

  const toggleSection = useCallback(
    (section) => {
      updateWorkspace((previous) => ({
        ...previous,
        collapsedSections: {
          ...previous.collapsedSections,
          [section]: !previous.collapsedSections[section],
        },
      }));
    },
    [updateWorkspace],
  );

  const setTreeWidth = useCallback(
    (width) => {
      const clamped = Math.min(
        TREE_WIDTH_RANGE.max,
        Math.max(TREE_WIDTH_RANGE.min, Math.round(width)),
      );
      updateWorkspace((previous) =>
        previous.paneSettings.treeWidth === clamped
          ? previous
          : {
              ...previous,
              paneSettings: { ...previous.paneSettings, treeWidth: clamped },
            },
      );
    },
    [updateWorkspace],
  );

  const setMemberWidth = useCallback(
    (width) => {
      const clamped = Math.min(
        MEMBER_WIDTH_RANGE.max,
        Math.max(MEMBER_WIDTH_RANGE.min, Math.round(width)),
      );
      updateWorkspace((previous) =>
        previous.paneSettings.memberWidth === clamped
          ? previous
          : {
              ...previous,
              paneSettings: { ...previous.paneSettings, memberWidth: clamped },
            },
      );
    },
    [updateWorkspace],
  );

  const treeResize = useDragResize({
    direction: 'right',
    onChange: setTreeWidth,
    range: TREE_WIDTH_RANGE,
    value: workspace.paneSettings.treeWidth,
  });
  const memberResize = useDragResize({
    direction: 'left',
    onChange: setMemberWidth,
    range: MEMBER_WIDTH_RANGE,
    value: workspace.paneSettings.memberWidth,
  });

  const deleteConversation = useCallback(
    async (username) => {
      if (!username) return;
      if (!window.confirm(`Permanently delete the saved message thread with "${username}"?`)) {
        return;
      }
      setActionError('');
      try {
        await chat.remove({ username });
        await refreshMessagingAfterMutation();
        updateWorkspace((previous) => {
          const tabs = previous.tabs.filter(
            (tab) => !(tab.type === 'chat' && tab.target === username),
          );
          return tabs.length === previous.tabs.length
            ? previous
            : {
                ...previous,
                activeTabId: tabs.find((tab) => tab.id === previous.activeTabId)
                  ? previous.activeTabId
                  : tabs[0]?.id ?? null,
                tabs,
              };
        });
      } catch (error) {
        reportActionFailure('Could not delete the saved message thread', error);
      }
    },
    [refreshMessagingAfterMutation, reportActionFailure, updateWorkspace],
  );

  const leaveRoom = useCallback(
    async (roomName) => {
      if (!roomName) return;
      if (!window.confirm(`Leave room "${roomName}"?`)) return;
      setActionError('');
      try {
        await rooms.leave({ roomName });
        await refreshMessagingAfterMutation();
        updateWorkspace((previous) => {
          const tabs = previous.tabs.filter(
            (tab) => !(tab.type === 'room' && tab.target === roomName),
          );
          return tabs.length === previous.tabs.length
            ? previous
            : {
                ...previous,
                activeTabId: tabs.find((tab) => tab.id === previous.activeTabId)
                  ? previous.activeTabId
                  : tabs[0]?.id ?? null,
                tabs,
              };
        });
      } catch (error) {
        reportActionFailure(`Could not leave room ${roomName}`, error);
      }
    },
    [refreshMessagingAfterMutation, reportActionFailure, updateWorkspace],
  );

  const leavePod = useCallback(
    async (channel) => {
      const peerId = state?.user?.username || 'local-peer';
      const podName = channel?.podName || channel?.podId;
      if (!channel?.podId) return;
      const prompt =
        channel.podId === GOLD_STAR_CLUB_POD_ID
          ? `Permanently leave ${podName}? Gold Star Club membership is irrevocable.`
          : `Leave pod "${podName}"? This exits the pod and removes its channels.`;
      if (!window.confirm(prompt)) return;
      setActionError('');
      try {
        await pods.leave(channel.podId, peerId);
        await refreshPodsAfterMutation();
        updateWorkspace((previous) => {
          const tabs = previous.tabs.filter((tab) => {
            if (tab.type !== 'pod') return true;
            const { podId } = decodePodTarget(tab.target);
            return podId !== channel.podId;
          });
          return tabs.length === previous.tabs.length
            ? previous
            : {
                ...previous,
                activeTabId: tabs.find((tab) => tab.id === previous.activeTabId)
                  ? previous.activeTabId
                  : tabs[0]?.id ?? null,
                tabs,
              };
        });
      } catch (error) {
        reportActionFailure(`Could not leave pod ${podName}`, error);
      }
    },
    [refreshPodsAfterMutation, reportActionFailure, state?.user?.username, updateWorkspace],
  );

  const startDirectMessage = useCallback(() => {
    const trimmed = dmDraft.trim();
    if (!trimmed) return;
    openTab('chat', trimmed);
    setDmDraft('');
    setDmAddOpen(false);
  }, [dmDraft, openTab]);

  const joinRoomByName = useCallback(async (roomName) => {
    const trimmed = roomName.trim();
    if (!trimmed) return false;
    setActionError('');
    setRoomJoinError('');
    try {
      await rooms.join({ roomName: trimmed });
      await refreshMessagingAfterMutation();
      openTab('room', trimmed);
      return true;
    } catch (error) {
      const message = getApiErrorMessage(error, { t: interfaceText }, 'Room join failed. Try again shortly.');
      setRoomJoinError(message);
      return false;
    }
  }, [openTab, refreshMessagingAfterMutation]);

  const joinRoomFromPicker = useCallback(async (roomName) => {
    const joined = await joinRoomByName(roomName);
    if (!joined) return;
    setRoomDraft('');
    setRoomAddOpen(false);
  }, [joinRoomByName]);

  const createPodFromInput = useCallback(async () => {
    const name = podDraft.trim();
    if (!name) return;
    setActionError('');
    try {
      const created = await pods.create({
        channels: [
          {
            channelId: 'general',
            kind: 'General',
            name: 'General',
          },
        ],
        description: null,
        externalBindings: [],
        name,
        tags: [],
        visibility: 'Unlisted',
      }, currentUser || 'local-peer');
      const channel = {
        channelId: 'general',
        channelName: 'General',
        podId: created.podId,
        podName: created.name || name,
        target: encodePodTarget(created.podId, 'general'),
      };
      await refreshPodsAfterMutation();
      openTab('pod', channel.target, channelLabel(channel));
      setPodDraft('');
      setPodAddOpen(false);
    } catch (error) {
      reportActionFailure('Could not create the pod room', error);
    }
  }, [currentUser, openTab, podDraft, refreshPodsAfterMutation, reportActionFailure]);

  const saveDiscoveredPod = useCallback(async (pod) => {
    const podId = pod.podId || pod.PodId;
    const name = pod.name || pod.Name || podId;
    if (!podId) return;
    setActionError('');
    try {
      const saved = await pods.create({
        channels: [
          {
            channelId: 'general',
            kind: 'General',
            name: 'General',
          },
        ],
        externalBindings: [],
        focusContentId: pod.focusContentId || pod.FocusContentId || null,
        name,
        podId,
        tags: asArray(pod.tags || pod.Tags),
        visibility: pod.visibility || pod.Visibility || 'Unlisted',
      }, currentUser || 'local-peer');
      const firstChannel = asArray(saved.channels)[0] || { channelId: 'general', name: 'General' };
      const channel = {
        channelId: firstChannel.channelId,
        channelName: firstChannel.name,
        podId: saved.podId,
        podName: saved.name || name,
        target: encodePodTarget(saved.podId, firstChannel.channelId),
      };
      await refreshPodsAfterMutation();
      openTab('pod', channel.target, channelLabel(channel));
    } catch (error) {
      reportActionFailure(`Could not join discovered pod ${name}`, error);
    }
  }, [currentUser, openTab, refreshPodsAfterMutation, reportActionFailure]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setQsOpen((open) => !open);
      } else if (event.key === 'Escape' && qsOpen) {
        setQsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [qsOpen]);

  const quickSwitcherItems = useMemo(() => {
    const items = [];
    for (const conversation of conversations) {
      items.push({
        accent: 'slsk',
        id: `chat:${conversation.username}`,
        label: conversation.username,
        prefix: '@',
        sublabel: interfaceText("Soulseek DM"),
        target: conversation.username,
        type: 'chat',
      });
    }
    for (const roomName of joinedRooms) {
      items.push({
        accent: 'slsk',
        id: `room:${roomName}`,
        label: roomName,
        prefix: '#',
        sublabel: interfaceText("Soulseek room"),
        target: roomName,
        type: 'room',
      });
    }
    for (const channel of visiblePodChannels) {
      const label = channelLabel(channel);
      items.push({
        accent: 'mesh',
        id: `pod:${channel.target}`,
        label,
        prefix: '&',
        sublabel: interfaceText("Mesh channel"),
        target: channel.target,
        type: 'pod',
        tabLabel: label,
      });
    }
    return items;
  }, [conversations, joinedRooms, language, visiblePodChannels]);

  const activeTab = visibleWorkspaceTabs.find((tab) => tab.id === workspace.activeTabId) ?? null;

  useEffect(() => {
    if (visibleWorkspaceTabs.length > 0) return;
    if (initialKind === 'chat' && conversations[0]?.username) {
      openTab('chat', conversations[0].username);
    } else if (initialKind === 'room' && joinedRooms[0]) {
      openTab('room', joinedRooms[0]);
    } else if (initialKind === 'pod' && podsFeatureEnabled && visiblePodChannels[0]) {
      openTab('pod', visiblePodChannels[0].target, channelLabel(visiblePodChannels[0]));
    }
  }, [conversations, initialKind, joinedRooms, openTab, podsFeatureEnabled, visiblePodChannels, visibleWorkspaceTabs.length]);

  useEffect(() => {
    if (!podsFeatureEnabled || initialKind !== 'pod' || !params?.podId || visiblePodChannels.length === 0) {
      return;
    }
    const target =
      visiblePodChannels.find(
        (channel) =>
          channel.podId === params.podId &&
          (!params.channelId || channel.channelId === params.channelId),
      ) ?? visiblePodChannels.find((channel) => channel.podId === params.podId);
    if (target) {
      openTab('pod', target.target, channelLabel(target));
    }
  }, [initialKind, openTab, params?.channelId, params?.podId, podsFeatureEnabled, visiblePodChannels]);

  const showSoulseek = !podsFeatureEnabled || networkFilter !== 'mesh';
  const showMesh = podsFeatureEnabled && networkFilter !== 'soulseek';

  const activePodChannel = useMemo(
    () =>
      activeTab?.type === 'pod'
        ? podChannels.find((channel) => channel.target === activeTab.target) ?? {
            ...decodePodTarget(activeTab.target),
            podName: activeTab.label,
          }
        : null,
    [activeTab?.label, activeTab?.target, activeTab?.type, podChannels],
  );

  const adapter = useMemo(() => {
    if (!activeTab) return null;
    if (activeTab.type === 'chat') {
      return createChatAdapter({ currentUser, username: activeTab.target });
    }
    if (activeTab.type === 'room') {
      return createRoomAdapter({ currentUser, roomName: activeTab.target });
    }
    if (activeTab.type === 'pod' && activePodChannel) {
      return createPodAdapter({ channel: activePodChannel, currentUser });
    }
    return null;
  }, [activePodChannel, activeTab?.target, activeTab?.type, currentUser]);

  useEffect(() => {
    if (!adapter || typeof adapter.members !== 'function') {
      setAdapterMembers((previous) => (previous.length === 0 ? previous : []));
      return undefined;
    }
    let cancelled = false;
    let inFlight = false;
    let interval = null;
    setAdapterMembers((previous) => (previous.length === 0 ? previous : []));
    const applyMembers = (members) => {
      const next = Array.isArray(members) ? members : [];
      setAdapterMembers((previous) =>
        memberListSignature(previous) === memberListSignature(next) ? previous : next,
      );
    };
    const refresh = async () => {
      if (cancelled || document.hidden || inFlight) return;
      inFlight = true;
      try {
        const members = await adapter.members();
        if (!cancelled && !document.hidden) applyMembers(members);
      } catch {
        // Retain the last successful membership snapshot on transient failures.
      } finally {
        inFlight = false;
      }
    };
    const stopPolling = () => {
      if (interval) {
        window.clearInterval(interval);
        interval = null;
      }
    };
    const startPolling = () => {
      if (document.hidden || interval) return;
      refresh();
      interval = window.setInterval(refresh, MEMBER_HYDRATION_INTERVAL_MS);
    };
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        startPolling();
      }
    };

    startPolling();
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      cancelled = true;
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [adapter]);

  const handleSenderClick = useCallback((username, event) => {
    if (!username) return;
    const x = event?.clientX ?? window.innerWidth / 2;
    const y = event?.clientY ?? window.innerHeight / 2;
    setUserPopover({ username, x, y });
  }, []);

  const closeUserPopover = useCallback(() => setUserPopover(null), []);

  useEffect(() => {
    setComposerDraft('');
  }, [activeTab?.id]);

  useEffect(() => {
    setHumanCheckAutoResponseEnabled(
      getHumanChallengeAutoResponseEnabled(options) ||
        readStoredHumanChallengeAutoResponse(),
    );
  }, [options]);

  const canApplyHumanCheck = canApplyHumanChallengeAutoResponse(options);

  const setHumanCheckAutoResponse = useCallback(
    async (enabled) => {
      setHumanCheckAutoResponseEnabled(enabled);
      writeStoredHumanChallengeAutoResponse(enabled);
      setHumanCheckError(false);

      if (!canApplyHumanCheck) {
        setHumanCheckError(true);
        return;
      }

      setHumanCheckSaving(true);
      try {
        await applyHumanChallengeAutoResponse(enabled);
      } catch {
        setHumanCheckError(true);
      } finally {
        setHumanCheckSaving(false);
      }
    },
    [canApplyHumanCheck],
  );

  const handleCopyMessage = useCallback(async (message) => {
    if (!message?.body) return;
    setActionError('');
    try {
      await navigator.clipboard.writeText(message.body);
    } catch (error) {
      reportActionFailure('Could not copy the message', error);
    }
  }, [reportActionFailure]);

  const handleQuoteMessage = useCallback((message) => {
    if (!message) return;
    const quote = `> ${message.sender}: ${message.body}\n`;
    setComposerDraft((previous) => `${quote}${previous}`);
    window.setTimeout(() => {
      composerInputRef.current?.focus();
    }, 0);
  }, []);

  const userPopoverActions = useMemo(
    () => ({
      browse: (username) => {
        navigate(`/browse?user=${encodeURIComponent(username)}`, {
          state: { user: username },
        });
        closeUserPopover();
      },
      message: (username) => {
        openTab('chat', username);
        closeUserPopover();
      },
      profile: (username) => {
        navigate(`/users?user=${encodeURIComponent(username)}`, {
          state: { user: username },
        });
        closeUserPopover();
      },
    }),
    [closeUserPopover, navigate, openTab],
  );

  const handleComposerCommand = useCallback(
    ({ argv, name }) => {
      if (name === 'close') {
        if (activeTab) closeTab(activeTab.id);
        return true;
      }
      if (name === 'part' || name === 'leave') {
        if (!activeTab) return true;
        if (activeTab.type === 'room') {
          leaveRoom(activeTab.target);
          return true;
        }
        if (activeTab.type === 'pod' && activePodChannel) {
          leavePod(activePodChannel);
          return true;
        }
        closeTab(activeTab.id);
        return true;
      }
      if (name === 'zoom') {
        const target = (argv[0] || '').toLowerCase();
        if (ZOOM_LEVELS.includes(target)) setZoom(target);
        return true;
      }
      if (name === 'msg' && argv.length >= 1) {
        openTab('chat', argv[0]);
        return true;
      }
      if (name === 'join' && argv.length >= 1) {
        const roomName = argv.join(' ').trim();
        rooms.join({ roomName }).then(() => {
          openTab('room', roomName);
          refreshMessagingAfterMutation();
        });
        return true;
      }
      if (name === 'reload') {
        setStreamReloadToken((value) => value + 1);
        return true;
      }
      if (name === 'switch' || name === 'k') {
        setQsOpen(true);
        return true;
      }
      if (name === 'help' || name === '?') {
        setHelpOpen(true);
        return true;
      }
      return false;
    },
    [activePodChannel, activeTab, closeTab, leavePod, leaveRoom, openTab, refreshMessagingAfterMutation, setZoom],
  );

  const showMembers = activeTab && activeTab.type !== 'chat' && memberRailOpen;
  const joinableRooms = availableRooms.filter(
    (roomName) => !joinedRooms.includes(roomName),
  );
  const joinableDiscoveredPods = discoveredPods.filter((pod) => {
    const podId = pod.podId || pod.PodId;
    return podId && !podChannels.some((channel) => channel.podId === podId);
  });

  const showRoomPlayback = Boolean(activePodChannel &&
    podChannels.some((channel) => channel.target === activeTab?.target) &&
    !isPodDirectChannel(activePodChannel));

  const gridStyle = {
    '--msgv2-member-width': showMembers ? `${workspace.paneSettings.memberWidth}px` : '0px',
    '--msgv2-tree-width': `${workspace.paneSettings.treeWidth}px`,
  };

  const totalUnread = conversations.reduce(
    (sum, c) => sum + (c.hasUnAcknowledgedMessages ? c.unAcknowledgedMessageCount || 1 : 0),
    0,
  );

  return (
    <div
      className="msgv2"
      data-zoom={workspace.zoom}
      onWheelCapture={handleWheelZoom}
      style={gridStyle}
    >
      <aside className="msgv2-rail">
        <Popup
          content={interfaceText("Show direct messages and rooms from all messaging networks.")}
          trigger={(
            <button
              aria-label={interfaceText("All networks")}
              className={`msgv2-rail-pill ${networkFilter === 'all' ? 'is-active' : ''}`}
              onClick={() => setNetworkFilter('all')}
              title={interfaceText("All networks")}
              type="button"
             {...interfaceTextProps("All networks")}>
              ⌂
            </button>
          )}
         {...interfaceTextProps("Show direct messages and rooms from all messaging networks.")}/>
        <Popup
          content={interfaceText("Show only Soulseek direct messages and rooms.")}
          trigger={(
            <button
              aria-label={interfaceText("Soulseek only")}
              className={`msgv2-rail-pill msgv2-rail-slsk ${networkFilter === 'soulseek' ? 'is-active' : ''}`}
              data-accent="slsk"
              onClick={() => setNetworkFilter('soulseek')}
              title={interfaceText("Soulseek only")}
              type="button"
             {...interfaceTextProps("Soulseek only")}>
              <LocalizedText source={"S"} />{totalUnread > 0 && <span className="msgv2-rail-badge">{formatUnread(totalUnread)}</span>}
            </button>
          )}
         {...interfaceTextProps("Show only Soulseek direct messages and rooms.")}/>
        {podsFeatureEnabled && (
          <Popup
            content={interfaceText("Show only mesh pod conversations.")}
            trigger={(
              <button
                aria-label={interfaceText("Mesh only")}
                className={`msgv2-rail-pill msgv2-rail-mesh ${networkFilter === 'mesh' ? 'is-active' : ''}`}
                data-accent="mesh"
                onClick={() => setNetworkFilter('mesh')}
                title={interfaceText("Mesh only")}
                type="button"
               {...interfaceTextProps("Mesh only")}>
                <LocalizedText source={"M"} /></button>
            )}
           {...interfaceTextProps("Show only mesh pod conversations.")}/>
        )}
        <div className="msgv2-rail-spacer" />
        <Popup
          content={interfaceText("Refresh conversations and, while the room picker is open, reload the available room list.")}
          trigger={(
            <button
              aria-label={interfaceText("Refresh")}
              className="msgv2-rail-pill msgv2-rail-icon"
              onClick={() => {
                void hydrate();
                if (roomAddOpen) loadAvailableRooms();
              }}
              title={interfaceText("Refresh")}
              type="button"
             {...interfaceTextProps("Refresh")}>
              ↻
            </button>
          )}
         {...interfaceTextProps("Refresh conversations and, while the room picker is open, reload the available room list.")}/>
      </aside>

      <nav
        aria-label={interfaceText("Conversations")}
        className="msgv2-tree"
       {...interfaceTextProps("Conversations")}>
        <div className="msgv2-tree-header">
          <span className="msgv2-tree-title"><LocalizedText source={"Channels"} /></span>
          <span className="msgv2-tree-meta">{NETWORKS.includes(networkFilter) && networkFilter !== 'all' ? interfaceText(networkFilter === 'mesh' ? 'Mesh' : 'Soulseek') : ''}</span>
        </div>

        {!podsFeatureEnabled && (
          <div className="msgv2-feature-notice" role="status">
            <LocalizedText source={"Mesh Pods are disabled by server configuration."} /></div>
        )}

        {showSoulseek && (
          <TreeSection
            accent="slsk"
            addLabel={interfaceText('Start a direct message')}
            addPanel={
              <InlineAddForm
                buttonLabel="DM"
                onCancel={() => {
                  setDmAddOpen(false);
                  setDmDraft('');
                }}
                onChange={setDmDraft}
                onSubmit={startDirectMessage}
                placeholder={interfaceText("username")}
                value={dmDraft}
               {...interfaceTextProps("username")}/>
            }
            collapsed={workspace.collapsedSections.soulseekDirect}
            count={conversations.length}
            onAddToggle={() => setDmAddOpen((open) => !open)}
            onToggle={() => toggleSection('soulseekDirect')}
            showAdd={dmAddOpen}
            title={interfaceText("Soulseek · DMs")}
           {...interfaceTextProps("Soulseek · DMs")}>
            {messagingLoadError && (
              <InlineLoadError
                message={messagingLoadError}
                onRetry={() => hydrateMessaging()}
                retryLabel="Retry loading saved conversations"
                testId="messaging-list-error"
              />
            )}
            {conversations.length === 0 ? (
              messagingLoadError
                ? null
                : <EmptyHint><LocalizedText source={"No saved direct messages."} /></EmptyHint>
            ) : (
              conversations.map((c) => {
                const unread = c.hasUnAcknowledgedMessages
                  ? c.unAcknowledgedMessageCount || 1
                  : 0;
                const isActive =
                  activeTab?.type === 'chat' && activeTab.target === c.username;
                return (
                  <TreeRow
                    accent="slsk"
                    actionLabel={interfaceText('Delete saved thread with {username}', {
                      username: c.username,
                    })}
                    isActive={isActive}
                    key={c.username}
                    onAction={() => deleteConversation(c.username)}
                    onActivate={() => openTab('chat', c.username)}
                    prefix="@"
                    target={c.username}
                    unread={unread}
                  />
                );
              })
            )}
          </TreeSection>
        )}

        {showSoulseek && (
          <TreeSection
            accent="slsk"
            addLabel={interfaceText('Join or create a room')}
            addPanel={
              <RoomJoinSearch
                availableRooms={joinableRooms}
                joinedRooms={joinedRooms}
                error={roomJoinError}
                isLoading={roomDirectoryLoading}
                requested={roomDirectoryRequested}
                onCancel={() => {
                  setRoomAddOpen(false);
                  setRoomDraft('');
                  setRoomJoinError('');
                }}
                onChange={(nextValue) => {
                  setRoomDraft(nextValue);
                  if (roomJoinError) setRoomJoinError('');
                }}
                onJoinRoom={joinRoomFromPicker}
                value={roomDraft}
              />
            }
            collapsed={workspace.collapsedSections.soulseekRooms}
            count={joinedRooms.length}
            onAddToggle={() => setRoomAddOpen((open) => !open)}
            onToggle={() => toggleSection('soulseekRooms')}
            showAdd={roomAddOpen}
            title={interfaceText("Soulseek · Rooms")}
           {...interfaceTextProps("Soulseek · Rooms")}>
            {messagingLoadError && (
              <InlineLoadError
                message={messagingLoadError}
                onRetry={() => hydrateMessaging()}
                retryLabel="Retry loading joined rooms"
              />
            )}
            {joinedRooms.length === 0 && joinableRooms.length === 0 ? (
              messagingLoadError
                ? null
                : <EmptyHint><LocalizedText source={"No rooms reported by the Soulseek server."} /></EmptyHint>
            ) : (
              <>
              {joinedRooms.length === 0 ? (
                <EmptyHint><LocalizedText source={"Search above to join or create a room."} /></EmptyHint>
              ) : joinedRooms.map((roomName) => {
                const isActive =
                  activeTab?.type === 'room' && activeTab.target === roomName;
                return (
                  <TreeRow
                    accent="slsk"
                    actionLabel={interfaceText('Leave room {roomName}', { roomName })}
                    isActive={isActive}
                    key={roomName}
                    onAction={() => leaveRoom(roomName)}
                    onActivate={() => openTab('room', roomName)}
                    prefix="#"
                    target={roomName}
                  />
                );
              })}
              </>
            )}
          </TreeSection>
        )}

        {showMesh && (
          <TreeSection
            accent="mesh"
            addLabel={interfaceText('Create a pod room')}
            addPanel={
              <InlineAddForm
                buttonLabel="Create"
                onCancel={() => {
                  setPodAddOpen(false);
                  setPodDraft('');
                }}
                onChange={setPodDraft}
                onSubmit={createPodFromInput}
                placeholder={interfaceText("pod room name")}
                value={podDraft}
               {...interfaceTextProps("pod room name")}/>
            }
            collapsed={workspace.collapsedSections.meshPods}
            count={visiblePodChannels.length + joinableDiscoveredPods.length}
            onAddToggle={() => setPodAddOpen((open) => !open)}
            onToggle={() => toggleSection('meshPods')}
            showAdd={podAddOpen}
            title={interfaceText("Mesh · Pod channels")}
           {...interfaceTextProps("Mesh · Pod channels")}>
            {podLoadError && (
              <InlineLoadError
                message={podLoadError}
                onRetry={() => hydratePods()}
                retryLabel="Retry loading saved pod channels"
                testId="pod-list-error"
              />
            )}
            {podDiscoveryError && (
              <InlineLoadError
                message={podDiscoveryError}
                onRetry={() => hydratePods()}
                retryLabel="Retry refreshing discovered pods"
                testId="pod-discovery-error"
              />
            )}
            {visiblePodChannels.length === 0 && joinableDiscoveredPods.length === 0 ? (
              podLoadError || podDiscoveryError
                ? null
                : <EmptyHint><LocalizedText source={"No pod rooms or discovered pods yet."} /></EmptyHint>
            ) : (
              <>
              {visiblePodChannels.length === 0 ? (
                <EmptyHint><LocalizedText source={"No joined pod channels."} /></EmptyHint>
              ) : visiblePodChannels.map((channel) => {
                const label = channelLabel(channel);
                const isActive =
                  activeTab?.type === 'pod' && activeTab.target === channel.target;
                return (
                  <TreeRow
                    accent="mesh"
                    actionLabel={interfaceText('Leave pod {pod}', {
                      pod: channel.podName || channel.podId,
                    })}
                    isActive={isActive}
                    key={channel.target}
                    onAction={() => leavePod(channel)}
                    onActivate={() => openTab('pod', channel.target, label)}
                    prefix="&"
                    target={label}
                  />
                );
              })}
              {joinableDiscoveredPods.length > 0 && (
                <TreeSubhead><LocalizedText source={"Discovered pods"} /></TreeSubhead>
              )}
              {joinableDiscoveredPods.slice(0, 50).map((pod) => {
                const podId = pod.podId || pod.PodId;
                const name = pod.name || pod.Name || podId;
                return (
                  <TreeRow
                    accent="mesh"
                    key={`discovered-${podId}`}
                    onActivate={() => saveDiscoveredPod(pod)}
                    prefix="+"
                    target={name}
                  />
                );
              })}
              </>
            )}
          </TreeSection>
        )}
      </nav>

      <div
        aria-label={interfaceText("Resize channel tree")}
        aria-orientation="vertical"
        className={`msgv2-handle msgv2-handle-tree ${treeResize.dragging ? 'is-dragging' : ''}`}
        onKeyDown={treeResize.onKeyDown}
        onPointerDown={treeResize.onPointerDown}
        role="separator"
        tabIndex={0}
       {...interfaceTextProps("Resize channel tree")}/>

      <main className={`msgv2-view${showRoomPlayback ? ' msgv2-view-with-playback' : ''}${actionError ? ' msgv2-view-has-action-error' : ''}`}>
        {actionError && (
          <div
            aria-live="assertive"
            className="msgv2-action-error"
            data-testid="messaging-action-error"
            role="alert"
          >
            {actionError}
          </div>
        )}
        <header className="msgv2-tabs">
          <div className="msgv2-tabs-strip">
            {visibleWorkspaceTabs.length === 0 ? (
              <span className="msgv2-tabs-empty"><LocalizedText source={"No tabs open"} /></span>
            ) : (
              visibleWorkspaceTabs.map((tab) => {
                const isActive = tab.id === workspace.activeTabId;
                return (
                  <div
                    className={`msgv2-tab-entry ${isActive ? 'is-active' : ''}`}
                    data-accent={tabAccent(tab)}
                    key={tab.id}
                  >
                    <Popup
                      content={interfaceText("Open {label} ({kind}) in the message workspace. Middle-click the tab to close it.", { label: tabLabel(tab), kind: tabSubtitle(tab) })}
                      trigger={(
                      <button
                        aria-current={isActive ? 'page' : undefined}
                        className="msgv2-tab"
                        onAuxClick={(event) => {
                          if (event.button === 1) {
                            event.preventDefault();
                            closeTab(tab.id);
                          }
                        }}
                        onClick={() => activateTab(tab.id)}
                        title={tabSubtitle(tab)}
                        type="button"
                      >
                        <span className="msgv2-tab-label">{tabLabel(tab)}</span>
                      </button>
                      )}
                    />
                    <Popup
                      content={interfaceText("Close {label} without closing the other message tabs.", { label: tabLabel(tab) })}
                      trigger={(
                        <button
                          aria-label={interfaceText("Close {label}", { label: tabLabel(tab) })}
                          className="msgv2-tab-close"
                          onClick={() => closeTab(tab.id)}
                          type="button"
                        >
                          ×
                        </button>
                      )}
                    />
                  </div>
                );
              })
            )}
          </div>
          <div className="msgv2-tabs-actions">
            <Popup
              content={humanCheckSaving
                ? 'Wait for the current setting update to finish.'
                : canApplyHumanCheck
                  ? 'Toggle automatic replies to private messages that look like human-check or share-gate prompts.'
                  : 'Toggle this saved local preference. Enable remote configuration to apply it to daemon-side replies.'}
              trigger={(
                <span className="msgv2-icon-button-trigger">
                  <button
                    aria-label={interfaceText("Private-message auto response")}
                    aria-pressed={humanCheckAutoResponseEnabled}
                    className={`msgv2-icon-button ${humanCheckAutoResponseEnabled ? 'is-on' : ''} ${humanCheckError ? 'is-warning' : ''}`}
                    disabled={humanCheckSaving}
                    onClick={() =>
                      setHumanCheckAutoResponse(!humanCheckAutoResponseEnabled)
                    }
                    title={interfaceText(canApplyHumanCheck
                      ? 'Automatically answer private messages that look like human-check or share-gate prompts.'
                      : 'Saved locally. Enable remote configuration to apply this to daemon-side replies.')}
                    type="button"
                   {...interfaceTextProps("Private-message auto response")}>
                    <LocalizedText source={"H"} /></button>
                </span>
              )}
            />
            {activeTab && activeTab.type !== 'chat' && (
              <Popup
                content={interfaceText(memberRailOpen
                  ? 'Hide the current room or pod member list.'
                  : 'Show the current room or pod member list.')}
                trigger={(
                  <button
                    aria-label={interfaceText(memberRailOpen ? 'Hide members' : 'Show members')}
                    aria-pressed={memberRailOpen}
                    className={`msgv2-icon-button ${memberRailOpen ? 'is-on' : ''}`}
                    onClick={() => setMemberRailOpen((open) => !open)}
                    title={interfaceText(memberRailOpen ? 'Hide members' : 'Show members')}
                    type="button"
                  >
                    ☰
                  </button>
                )}
              />
            )}
            <DensityToggle
              onAdjust={adjustZoom}
              onChange={setZoom}
              value={workspace.zoom}
            />
          </div>
        </header>

        {showRoomPlayback && (
          <div className="msgv2-room-playback">
            <PodListenAlongPanel
              channelId={activePodChannel.channelId}
              compact
              key={activeTab.id}
              podId={activePodChannel.podId}
              user={currentUser}
            />
          </div>
        )}

        <section className="msgv2-stage">
          {initialKind === 'pod' && !podsFeatureEnabled ? (
            <div className="msgv2-empty" role="status">
              <div className="msgv2-empty-glyph">⌬</div>
              <div className="msgv2-empty-title"><LocalizedText source={"Mesh Pods are disabled"} /></div>
              <div className="msgv2-empty-hint">
                <LocalizedText source={"Enable"} />{" "}<code>feature.Pods</code> <LocalizedText source={"in the server configuration to use pod rooms and discovery."} /></div>
            </div>
          ) : activeTab ? (
            <MessageStream
              adapter={adapter}
              emptyHint={interfaceText("No messages yet in {label}.", { label: tabLabel(activeTab) })}
              key={`${activeTab.id}#${streamReloadToken}`}
              onCopy={handleCopyMessage}
              onQuote={handleQuoteMessage}
              onSenderClick={handleSenderClick}
            />
          ) : (
            <div className="msgv2-empty">
              <div className="msgv2-empty-glyph">⌬</div>
              <div className="msgv2-empty-title"><LocalizedText source={"No conversation open"} /></div>
              <div className="msgv2-empty-hint">
                <LocalizedText source={"Pick something from the channel list, or press"} />{" "}<kbd><LocalizedText source={"Ctrl"} /></kbd>+<kbd><LocalizedText source={"K"} /></kbd>.
              </div>
            </div>
          )}
        </section>

        <Composer
          adapter={adapter}
          commands={COMPOSER_COMMANDS}
          inputRef={composerInputRef}
          label={activeTab ? interfaceText("Message {label}", { label: tabLabel(activeTab) }) : interfaceText("Message composer")}
          onChange={setComposerDraft}
          onCommand={handleComposerCommand}
          placeholder={
            activeTab
              ? interfaceText("Message {label} — type / for commands, /help for the full list", { label: tabLabel(activeTab) })
              : undefined
          }
          value={composerDraft}
        />
      </main>

      {showMembers && (
        <div
          aria-label={interfaceText("Resize member rail")}
          aria-orientation="vertical"
          className={`msgv2-handle msgv2-handle-member ${memberResize.dragging ? 'is-dragging' : ''}`}
          onKeyDown={memberResize.onKeyDown}
          onPointerDown={memberResize.onPointerDown}
          role="separator"
          tabIndex={0}
         {...interfaceTextProps("Resize member rail")}/>
      )}

      {showMembers && (
        <MemberRail
          members={adapterMembers}
          onSelect={handleSenderClick}
        />
      )}

      <QuickSwitcher
        items={quickSwitcherItems}
        onClose={() => setQsOpen(false)}
        onPick={(item) => {
          openTab(item.type, item.target, item.tabLabel);
          setQsOpen(false);
        }}
        open={qsOpen}
      />

      <CommandHelp
        commands={COMPOSER_COMMANDS}
        onClose={() => setHelpOpen(false)}
        open={helpOpen}
      />

      <UserPopover
        anchor={userPopover ? { x: userPopover.x, y: userPopover.y } : null}
        onBrowse={userPopoverActions.browse}
        onClose={closeUserPopover}
        onMessage={userPopoverActions.message}
        onProfile={userPopoverActions.profile}
        open={Boolean(userPopover)}
        username={userPopover?.username}
      />
    </div>
  );
};

const memberKey = (member) =>
  member.peerId || member.username || member.PeerId || member.name || '';

const memberDisplay = (member) =>
  member.peerId || member.username || member.PeerId || member.name || 'unknown';

const memberRole = (member) =>
  member.role || member.Role || (member.isOperator ? 'operator' : null);

const memberListSignature = (members) =>
  members
    .map((member) => `${memberKey(member)}\u0001${memberDisplay(member)}\u0001${memberRole(member) || ''}`)
    .sort()
    .join('\u0002');

const MemberRail = React.memo(({ members, onSelect }) => (
  <aside
    aria-label={interfaceText("Members")}
    className="msgv2-members"
   {...interfaceTextProps("Members")}>
    <div className="msgv2-members-header">
      <LocalizedText source={"Members"} />{" "}<span className="msgv2-members-count">{members.length}</span>
    </div>
    {members.length === 0 ? (
      <div className="msgv2-members-hint"><LocalizedText source={"No members reported yet."} /></div>
    ) : (
      <ul className="msgv2-members-list">
        {members.map((member) => {
          const display = memberDisplay(member);
          const role = memberRole(member);
          return (
            <li
              className="msgv2-members-item"
              key={memberKey(member) || display}
            >
              <Popup
                content={interfaceText("Open the available messaging actions for {display}.", { "display": (display) })}
                trigger={(
                  <button
                    className="msgv2-members-name"
                    onClick={(event) => onSelect?.(display, event)}
                    title={display}
                    type="button"
                  >
                    {display}
                  </button>
                )}
               {...interfaceTextProps("Open the available messaging actions for {display}.")}/>
              {role && <span className="msgv2-members-role">{role}</span>}
            </li>
          );
        })}
      </ul>
    )}
  </aside>
));

const TreeSection = ({
  accent,
  addLabel,
  addPanel,
  collapsed,
  count,
  onAddToggle,
  onToggle,
  showAdd,
  title,
  children,
}) => (
  <section
    className={`msgv2-tree-section ${collapsed ? 'is-collapsed' : ''}`}
    data-accent={accent}
  >
    <div className="msgv2-tree-section-head-row">
      <Popup
        content={interfaceText(collapsed
          ? 'Expand {section} to show its conversations.'
          : 'Collapse {section} to hide its conversations.', {
          section: title,
        })}
        trigger={(
          <button
            aria-expanded={!collapsed}
            className="msgv2-tree-section-head"
            onClick={onToggle}
            type="button"
          >
            <span className="msgv2-tree-caret">{collapsed ? '▸' : '▾'}</span>
            <span className="msgv2-tree-section-title">{title}</span>
            <span className="msgv2-tree-section-count">{count}</span>
          </button>
        )}
      />
      {onAddToggle && (
        <Popup
          content={interfaceText(showAdd
            ? 'Close the form to {action} in {section}.'
            : 'Open a form to {action} in {section}.', {
            action: addLabel,
            section: title,
          })}
          trigger={(
            <button
              aria-label={addLabel}
              aria-pressed={showAdd}
              className={`msgv2-tree-section-add ${showAdd ? 'is-on' : ''}`}
              onClick={onAddToggle}
              title={addLabel}
              type="button"
            >
              {showAdd ? '×' : '+'}
            </button>
          )}
        />
      )}
    </div>
    {!collapsed && showAdd && addPanel && (
      <div className="msgv2-tree-add-panel">{addPanel}</div>
    )}
    {!collapsed && <div className="msgv2-tree-section-body">{children}</div>}
  </section>
);

const TreeRow = ({
  accent,
  actionLabel,
  isActive,
  onAction,
  onActivate,
  prefix,
  target,
  unread,
}) => (
  <div
    className={`msgv2-tree-row-wrap ${isActive ? 'is-active' : ''}`}
    data-accent={accent}
  >
    <Popup
      content={interfaceText("Open {prefix}{target} in the message workspace.", { "prefix": (prefix), "target": (target) })}
      trigger={(
        <button
          className={`msgv2-tree-row ${isActive ? 'is-active' : ''}`}
          data-accent={accent}
          onClick={onActivate}
          title={interfaceText("{prefix}{target}", { "prefix": (prefix), "target": (target) })}
          type="button"
         {...interfaceTextProps("{prefix}{target}")}>
          <span className="msgv2-tree-row-prefix">{prefix}</span>
          <span className="msgv2-tree-row-name">{target}</span>
          {unread > 0 && (
            <span className="msgv2-tree-row-unread">{formatUnread(unread)}</span>
          )}
        </button>
      )}
     {...interfaceTextProps("Open {prefix}{target} in the message workspace.")}/>
    {onAction && (
      <Popup
        content={actionLabel}
        trigger={(
          <button
            aria-label={actionLabel}
            className="msgv2-tree-row-action"
            onClick={(event) => {
              event.stopPropagation();
              onAction();
            }}
            tabIndex={-1}
            title={actionLabel}
            type="button"
          >
            ×
          </button>
        )}
      />
    )}
  </div>
);

const EmptyHint = ({ children }) => (
  <div className="msgv2-tree-empty">{children}</div>
);

const TreeSubhead = ({ children }) => (
  <div className="msgv2-tree-subhead">{children}</div>
);

const RoomJoinSearch = ({
  availableRooms,
  error,
  isLoading,
  joinedRooms,
  onCancel,
  onChange,
  onJoinRoom,
  requested,
  value,
}) => {
  useInterfaceLanguage();
  const inputRef = useRef(null);
  const query = value.trim();
  const normalizedQuery = query.toLocaleLowerCase();
  const joinedLookup = useMemo(
    () => new Set(joinedRooms.map((roomName) => roomName.toLocaleLowerCase())),
    [joinedRooms],
  );
  const matches = useMemo(() => {
    if (!normalizedQuery) return [];
    const exact = [];
    const startsWith = [];
    const contains = [];
    const seen = new Set();
    const addMatch = (roomName, status) => {
      const normalizedRoom = roomName.toLocaleLowerCase();
      if (seen.has(normalizedRoom)) return;
      seen.add(normalizedRoom);
      const match = { roomName, status };
      if (normalizedRoom === normalizedQuery) exact.push(match);
      else if (normalizedRoom.startsWith(normalizedQuery)) startsWith.push(match);
      else if (normalizedRoom.includes(normalizedQuery)) contains.push(match);
    };
    joinedRooms.forEach((roomName) => addMatch(roomName, 'joined'));
    availableRooms.forEach((roomName) => addMatch(roomName, 'available'));
    return [...exact, ...startsWith, ...contains].slice(0, 16);
  }, [availableRooms, joinedRooms, normalizedQuery]);
  const exactAvailable = matches.some(
    (match) =>
      match.status === 'available' &&
      match.roomName.toLocaleLowerCase() === normalizedQuery,
  );
  const exactJoined = normalizedQuery && joinedLookup.has(normalizedQuery);
  const canSubmit = query.length > 0;
  const submitLabel = exactJoined ? 'Open' : exactAvailable ? 'Join' : 'Join/Create';

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const submit = useCallback(() => {
    if (!canSubmit) return;
    onJoinRoom(query);
  }, [canSubmit, onJoinRoom, query]);

  return (
    <div className="msgv2-room-search">
      <div className="msgv2-tree-add">
        <input
          aria-label={interfaceText("Search or create Soulseek room")}
          className="msgv2-tree-add-input"
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              submit();
            } else if (event.key === 'Escape') {
              event.preventDefault();
              onCancel();
            }
          }}
          placeholder={interfaceText("search or create room")}
          ref={inputRef}
          type="text"
          value={value}
         {...interfaceTextProps("Search or create Soulseek room")}/>
        <Popup
          content={canSubmit
            ? interfaceText('Join the matching Soulseek room, or create {query} if it does not exist.', { query })
            : interfaceText('Enter a room name to search the directory and enable joining or creating a Soulseek room.')}
          {...interfaceTextProps(
            canSubmit
              ? 'Join the matching Soulseek room, or create {query} if it does not exist.'
              : 'Enter a room name to search the directory and enable joining or creating a Soulseek room.',
            { query },
          )}
          trigger={(
            <span>
              <button
                aria-label={interfaceText("Join/Create room")}
                className="msgv2-tree-add-go"
                disabled={!canSubmit}
                onClick={submit}
                title={interfaceText("Join a matching Soulseek room, or create it if it does not exist")}
                type="button"
               {...interfaceTextProps("Join/Create room")}>
                {submitLabel}
              </button>
            </span>
          )}
        />
      </div>
      {!query ? (
        <div className="msgv2-room-search-hint">
          {isLoading
            ? <LocalizedText source={"Loading room directory... type a room name any time."} />
            : availableRooms.length > 0
              ? <LocalizedText
                source="{count} available rooms. Type to filter or enter a new room name."
                values={{ count: availableRooms.length.toLocaleString(getRegionalLocale()) }}
              />
              : requested
                ? <LocalizedText source="Still waiting for the room directory. Type a room name to join or create it." />
                : <LocalizedText source="Type a room name to join or create it." />}
        </div>
      ) : (
        <>
          {isLoading && matches.length === 0 && (
            <div className="msgv2-room-search-hint"><LocalizedText source={"Loading matching rooms... press Enter to join or create #{query} now."} values={{ query }} /></div>
          )}
          {matches.length > 0 && (
            <div
              aria-label={interfaceText("Matching Soulseek rooms")}
              className="msgv2-room-search-results"
             {...interfaceTextProps("Matching Soulseek rooms")}>
              {matches.map(({ roomName, status }) => (
                <Popup
                  content={status === 'joined'
                    ? interfaceText('Open the existing {roomName} conversation.', { roomName })
                    : interfaceText('Join the Soulseek room {roomName} and add it to your workspace.', { roomName })}
                  key={roomName}
                  {...interfaceTextProps(
                    status === 'joined'
                      ? 'Open the existing {roomName} conversation.'
                      : 'Join the Soulseek room {roomName} and add it to your workspace.',
                    { roomName },
                  )}
                  trigger={(
                    <button
                      aria-label={interfaceText(
                        status === 'joined' ? 'Open {roomName}' : 'Join {roomName}',
                        { roomName },
                      )}
                      className="msgv2-room-search-result"
                      onClick={() => onJoinRoom(roomName)}
                      title={interfaceText(
                        status === 'joined' ? 'Open {roomName}' : 'Join {roomName}',
                        { roomName },
                      )}
                      type="button"
                     {...interfaceTextProps(
                       status === 'joined' ? 'Open {roomName}' : 'Join {roomName}',
                       { roomName },
                     )}>
                      <span className="msgv2-tree-row-prefix">#</span>
                      <span className="msgv2-tree-row-name">{roomName}</span>
                      <span className="msgv2-room-search-result-meta">
                        {status === 'joined' ? <LocalizedText source={"Open"} /> : <LocalizedText source={"Join"} />}
                      </span>
                    </button>
                  )}
                />
              ))}
            </div>
          )}
          {!exactAvailable && !exactJoined && (
            <Popup
              content={interfaceText("Join the Soulseek room {query}, or create it if it does not exist.", { "query": (query) })}
              trigger={(
                <button
                  className="msgv2-room-search-create"
                  onClick={submit}
                  title={interfaceText("Join or create {query}", { "query": (query) })}
                  type="button"
                 {...interfaceTextProps("Join or create {query}")}>
                  <LocalizedText source={"Join/Create #"} />{query}
                </button>
              )}
             {...interfaceTextProps("Join the Soulseek room {query}, or create it if it does not exist.")}/>
          )}
          {exactJoined && (
            <div className="msgv2-room-search-hint"><LocalizedText source={"Already joined. Press Enter to open."} /></div>
          )}
        </>
      )}
      {error && <div className="msgv2-room-search-error">{error}</div>}
    </div>
  );
};

const InlineAddForm = ({
  buttonLabel,
  onCancel,
  onChange,
  onSubmit,
  placeholder,
  value,
}) => {
  useInterfaceLanguage();
  const inputRef = useRef(null);
  const actionDescription = interfaceText(buttonLabel === 'DM'
    ? 'Start a direct-message conversation with the entered username.'
    : 'Create a channel in this pod with the entered name.');
  useEffect(() => {
    inputRef.current?.focus();
  }, []);
  return (
    <div className="msgv2-tree-add">
      <input
        className="msgv2-tree-add-input"
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') {
            event.preventDefault();
            onSubmit();
          } else if (event.key === 'Escape') {
            event.preventDefault();
            onCancel();
          }
        }}
        placeholder={placeholder}
        ref={inputRef}
        type="text"
        value={value}
      />
      <Popup
        content={value.trim().length === 0
          ? interfaceText('Enter a name to enable this action. {description}', {
            description: actionDescription,
          })
          : actionDescription}
        trigger={(
          <span>
            <button
              className="msgv2-tree-add-go"
              disabled={value.trim().length === 0}
              onClick={onSubmit}
              type="button"
            >
              {interfaceText(buttonLabel)}
            </button>
          </span>
        )}
      />
    </div>
  );
};

const DensityToggle = ({ onAdjust, onChange, value }) => (
  <div
    aria-label={interfaceText("Messages UI size")}
    className="msgv2-density"
   {...interfaceTextProps("Messages UI size")}>
    <Popup
      content={interfaceText(zoomIndex(value) === 0
        ? 'Messages UI is already at its smallest size.'
        : 'Make the entire Messages UI smaller to fit more messages on screen.')}
      trigger={(
        <span className="msgv2-density-step-trigger">
          <button
            aria-label={interfaceText("Make Messages UI smaller")}
            className="msgv2-density-step"
            disabled={zoomIndex(value) === 0}
            onClick={() => onAdjust(-1)}
            title={interfaceText("Make the entire Messages UI smaller")}
            type="button"
           {...interfaceTextProps("Make Messages UI smaller")}>
            −
          </button>
        </span>
      )}
    />
    <div
      aria-label={interfaceText("Messages UI size presets")}
      className="msgv2-density-presets"
      role="radiogroup"
     {...interfaceTextProps("Messages UI size presets")}>
      {ZOOM_LEVELS.map((level) => (
        <Popup
          content={interfaceText('Set the Messages UI size to {size} to match your screen and reading preference.', {
            size: level.toUpperCase(),
          })}
          key={level}
          trigger={(
            <button
              aria-checked={value === level}
              className={`msgv2-density-pip ${value === level ? 'is-active' : ''}`}
              onClick={() => onChange(level)}
              role="radio"
              title={interfaceText('Messages UI size {size}', { size: level.toUpperCase() })}
              type="button"
            >
              {level.toUpperCase()}
            </button>
          )}
        />
      ))}
    </div>
    <Popup
      content={interfaceText(zoomIndex(value) === ZOOM_LEVELS.length - 1
        ? 'Messages UI is already at its largest size.'
        : 'Make the entire Messages UI larger for easier reading.')}
      trigger={(
        <span className="msgv2-density-step-trigger">
          <button
            aria-label={interfaceText("Make Messages UI larger")}
            className="msgv2-density-step"
            disabled={zoomIndex(value) === ZOOM_LEVELS.length - 1}
            onClick={() => onAdjust(1)}
            title={interfaceText("Make the entire Messages UI larger")}
            type="button"
           {...interfaceTextProps("Make Messages UI larger")}>
            +
          </button>
        </span>
      )}
    />
  </div>
);

const useDragResize = ({ direction, onChange, range, value }) => {
  const [dragging, setDragging] = useState(false);
  const startRef = useRef(null);

  const handleMove = useCallback(
    (event) => {
      if (!startRef.current) return;
      const dx = event.clientX - startRef.current.x;
      const delta = direction === 'right' ? dx : -dx;
      const next = Math.min(range.max, Math.max(range.min, startRef.current.value + delta));
      onChange(next);
    },
    [direction, onChange, range.max, range.min],
  );

  const stopDrag = useCallback(() => {
    setDragging(false);
    startRef.current = null;
    window.removeEventListener('pointermove', handleMove);
    window.removeEventListener('pointerup', stopDrag);
    document.body.classList.remove('msgv2-resizing');
  }, [handleMove]);

  const onPointerDown = useCallback(
    (event) => {
      event.preventDefault();
      startRef.current = { value, x: event.clientX };
      setDragging(true);
      document.body.classList.add('msgv2-resizing');
      window.addEventListener('pointermove', handleMove);
      window.addEventListener('pointerup', stopDrag);
    },
    [handleMove, stopDrag, value],
  );

  const onKeyDown = useCallback(
    (event) => {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      const sign = event.key === 'ArrowRight' ? 1 : -1;
      const delta = direction === 'right' ? sign * 16 : -sign * 16;
      const next = Math.min(range.max, Math.max(range.min, value + delta));
      onChange(next);
    },
    [direction, onChange, range.max, range.min, value],
  );

  useEffect(
    () => () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', stopDrag);
      document.body.classList.remove('msgv2-resizing');
    },
    [handleMove, stopDrag],
  );

  return { dragging, onKeyDown, onPointerDown };
};

export default MessagingV2;
