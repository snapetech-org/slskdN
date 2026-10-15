import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../../lib/interfaceLocale";
import { formatTransferState } from '../../lib/transfers';
import { getRegionalLocale } from '../../lib/regionalFormat';
import './TrafficTicker.css';
import { createTransfersHubConnection } from '../../lib/hubFactory';
import React, { useEffect, useState } from 'react';
import { Icon, List, Popup } from 'semantic-ui-react';

const localizeActivityState = (state = '') => {
  if (state === 'InProgress') return interfaceText('In Progress');
  if (['Requested', 'Queued, Locally', 'Queued, Remotely'].includes(state)) return interfaceText('Queued');
  return interfaceText(formatTransferState(state));
};

const MAX_ACTIVITIES = 50; // Keep last 50 activities

const getActivityIcon = (direction, state) => {
  const isCompleted = state.includes('Completed');
  const isFailed =
    state.includes('Errored') ||
    state.includes('Cancelled') ||
    state.includes('TimedOut') ||
    state.includes('Rejected');

  if (direction === 'Download') {
    if (isCompleted) {
      return isFailed ? 'x' : 'checkmark';
    }

    return 'download';
  } else {
    if (isCompleted) {
      return isFailed ? 'x' : 'checkmark';
    }

    return 'upload';
  }
};

const getActivityColor = (direction, state) => {
  const isCompleted = state.includes('Completed');
  const isFailed =
    state.includes('Errored') ||
    state.includes('Cancelled') ||
    state.includes('TimedOut') ||
    state.includes('Rejected');

  if (isFailed) return 'red';
  if (isCompleted) return 'green';
  if (direction === 'Download') return 'blue';
  return 'teal';
};

const formatActivity = (activity) => {
  const {
    averageSpeed,
    direction,
    filename,
    percentComplete,
    size,
    state,
    username,
  } = activity;
  const fileName = filename.split('\\').pop().split('/').pop();
  const displayedState = localizeActivityState(state);

  if (state.includes('Completed')) {
    const speedText =
      averageSpeed > 0 ? ` @ ${formatBytes(averageSpeed)}/s` : '';
    return `${direction === 'Download' ? '↓' : '↑'} ${username}/${fileName} ${displayedState}${speedText}`;
  }

  if (state.includes('InProgress') && percentComplete > 0) {
    return `${direction === 'Download' ? '↓' : '↑'} ${username}/${fileName} ${percentComplete.toFixed(1)}%`;
  }

  return `${direction === 'Download' ? '↓' : '↑'} ${username}/${fileName} ${displayedState}`;
};

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1_024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const index = Math.floor(Math.log(bytes) / Math.log(k));
  return (
    Number.parseFloat((bytes / k ** index).toFixed(1)) + ' ' + sizes[index]
  );
};

const TrafficTicker = () => {
  const [activities, setActivities] = useState([]);
  const [connected, setConnected] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const transfersHub = createTransfersHubConnection();

    transfersHub.on('activity', (activity) => {
      setActivities((previous) => [
        activity,
        ...previous.slice(0, MAX_ACTIVITIES - 1),
      ]);
    });

    transfersHub.onreconnecting(() => setConnected(false));
    transfersHub.onreconnected(() => setConnected(true));
    transfersHub.onclose(() => setConnected(false));

    transfersHub.start().then(() => setConnected(true));

    return () => {
      transfersHub.stop();
    };
  }, []);

  const visibleActivities = expanded ? activities : activities.slice(0, 10);
  const hasMore = activities.length > 10;

  return (
    <div className="traffic-ticker">
      <div className="traffic-ticker-header">
        <Icon name="exchange" />
        <span><LocalizedText source={"Transfer Activity"} /></span>
        <Icon
          color={connected ? 'green' : 'red'}
          name={connected ? 'wifi' : 'remove'}
          size="small"
          title={
            connected
              ? interfaceText('Connected to transfer feed')
              : interfaceText('Disconnected from transfer feed')
          }
        />
      </div>

      <div className="traffic-ticker-content">
        {activities.length === 0 ? (
          <div className="traffic-ticker-empty">
            <Icon name="clock outline" />
            <span><LocalizedText source={"No recent activity"} /></span>
          </div>
        ) : (
          <List
            divided
            relaxed
          >
            {visibleActivities.map((activity, index) => (
              <List.Item key={`${activity.timestamp}-${index}`}>
                <List.Content>
                  <div className="traffic-activity">
                    <Icon
                      color={getActivityColor(
                        activity.direction,
                        activity.state,
                      )}
                      name={getActivityIcon(activity.direction, activity.state)}
                      size="small"
                    />
                    <Popup
                      content={`${new Date(activity.timestamp).toLocaleTimeString(getRegionalLocale())} - ${interfaceText(activity.direction)} ${localizeActivityState(activity.state)}`}
                      position="top left"
                      trigger={
                        <span className="traffic-activity-text">
                          {formatActivity(activity)}
                        </span>
                      }
                    />
                  </div>
                </List.Content>
              </List.Item>
            ))}
          </List>
        )}

        {hasMore && (
          <div className="traffic-ticker-toggle">
            <Popup
              content={expanded
                ? interfaceText('Collapse the activity list to its 10 most recent transfer events.')
                : interfaceText(
                  'Show {count} older transfer events so you can review recent network activity.',
                  { count: activities.length - 10 },
                )}
              trigger={(
                <button
                  className="traffic-ticker-toggle-button"
                  onClick={() => setExpanded(!expanded)}
                  type="button"
                >
                  {expanded ? <LocalizedText source={"Show Less"} /> : `Show ${activities.length - 10} More`}
                </button>
              )}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default TrafficTicker;
