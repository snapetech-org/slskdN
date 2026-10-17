import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
// <copyright file="ArtistReleaseRadarPanel.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import {
  fetchArtistReleaseRadarNotifications,
  fetchArtistReleaseRadarSubscriptions,
  routeArtistReleaseRadarNotification,
  subscribeArtistReleaseRadar,
} from '../../lib/musicBrainz';
import React, { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import {
  Button,
  Checkbox,
  Form,
  Header,
  Icon,
  Label,
  List,
  Message,
  Popup,
  Segment,
} from 'semantic-ui-react';

const getWorkTitle = (notification = {}) =>
  notification.workRef?.title ||
  notification.workRef?.Title ||
  notification.recordingId ||
  'Unresolved radar hit';

const getWorkArtist = (notification = {}) =>
  notification.workRef?.artist ||
  notification.workRef?.Artist ||
  notification.workRef?.creator ||
  notification.workRef?.Creator ||
  '';

const parseList = (value = '') =>
  value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

const asArray = (value) => (Array.isArray(value) ? value : []);
const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);

const ArtistReleaseRadarPanel = ({ disabled }) => {
  useInterfaceLanguage();
  const [artistId, setArtistId] = useState('');
  const [artistName, setArtistName] = useState('');
  const [enabled, setEnabled] = useState(true);
  const [error, setError] = useState(null);
  const [mutedReleaseGroups, setMutedReleaseGroups] = useState('');
  const [notifications, setNotifications] = useState([]);
  const [routeTargets, setRouteTargets] = useState('');
  const [scope, setScope] = useState('trusted');
  const [status, setStatus] = useState(null);
  const [subscriptions, setSubscriptions] = useState([]);
  const [unreadOnly, setUnreadOnly] = useState(false);

  const loadRadar = async () => {
    if (disabled) return;

    setError(null);
    try {
      const [subscriptionsResponse, notificationsResponse] = await Promise.all([
        fetchArtistReleaseRadarSubscriptions(),
        fetchArtistReleaseRadarNotifications({ unreadOnly }),
      ]);
      setSubscriptions(asArray(subscriptionsResponse.data).filter(isObject));
      setNotifications(asArray(notificationsResponse.data).filter(isObject));
    } catch {
      setError('Unable to load release radar.');
    }
  };

  useEffect(() => {
    loadRadar();
  }, [disabled, unreadOnly]);

  const subscribe = async () => {
    if (!artistId.trim()) {
      toast.error(interfaceText("Artist MBID is required"));
      return;
    }

    setError(null);
    try {
      await subscribeArtistReleaseRadar({
        artistId: artistId.trim(),
        artistName: artistName.trim(),
        enabled,
        mutedReleaseGroupIds: parseList(mutedReleaseGroups),
        scope,
      });
      setStatus({
        source: 'Watching {artist}.',
        values: { artist: artistName.trim() || artistId.trim() },
      });
      setArtistId('');
      setArtistName('');
      await loadRadar();
    } catch {
      setError('Unable to save release radar subscription.');
    }
  };

  const routeNotification = async (notification) => {
    setError(null);
    try {
      const response = await routeArtistReleaseRadarNotification({
        notificationId: notification.id,
        targetPeerIds: parseList(routeTargets),
      });
      setStatus({
        source: response.data?.success ? 'Route sent for {title}.' : 'Route recorded for {title}.',
        values: { title: getWorkTitle(notification) },
      });
    } catch {
      setError('Unable to route release radar notification.');
    }
  };

  if (disabled) {
    return (
      <Segment raised>
        <Header as="h4"><LocalizedText source={"Artist Release Radar"} /></Header>
        <p><LocalizedText source={"Connect to the server to review artist radar subscriptions."} /></p>
      </Segment>
    );
  }

  return (
    <Segment raised>
      <Header as="h4"><LocalizedText source={"Artist Release Radar"} /></Header>
      <Form>
        <Form.Group widths="equal">
          <Form.Input
            aria-label={interfaceText("Release radar artist MBID")}
            label={interfaceText("Artist MBID")}
            onChange={(event) => setArtistId(event.target.value)}
            value={artistId}
           {...interfaceTextProps("Release radar artist MBID")}/>
          <Form.Input
            aria-label={interfaceText("Release radar artist name")}
            label={interfaceText("Artist name")}
            onChange={(event) => setArtistName(event.target.value)}
            value={artistName}
           {...interfaceTextProps("Release radar artist name")}/>
          <Form.Input
            aria-label={interfaceText("Muted release group IDs")}
            label={interfaceText("Muted release groups")}
            onChange={(event) => setMutedReleaseGroups(event.target.value)}
            placeholder={interfaceText("comma-separated MBIDs")}
            value={mutedReleaseGroups}
           {...interfaceTextProps("Muted release group IDs")}/>
        </Form.Group>
        <Form.Group widths="equal">
          <Form.Select
            aria-label={interfaceText("Release radar scope")}
            label={interfaceText("Scope")}
            onChange={(_event, data) => setScope(data.value)}
            options={[
              { key: 'trusted', text: interfaceText("Trusted"), value: 'trusted' },
              { key: 'realm', text: interfaceText("Realm"), value: 'realm' },
              { key: 'local', text: interfaceText("Local"), value: 'local' },
            ]}
            value={scope}
           {...interfaceTextProps("Release radar scope")}/>
          <Form.Field>
            <label><LocalizedText source={"Enabled"} /></label>
            <Checkbox
              aria-label={interfaceText("Enable release radar subscription")}
              checked={enabled}
              onChange={(_event, data) => setEnabled(data.checked)}
              toggle
             {...interfaceTextProps("Enable release radar subscription")}/>
          </Form.Field>
          <Form.Field>
            <label><LocalizedText source={"Unread filter"} /></label>
            <Checkbox
              aria-label={interfaceText("Show unread release radar notifications only")}
              checked={unreadOnly}
              onChange={(_event, data) => setUnreadOnly(data.checked)}
              toggle
             {...interfaceTextProps("Show unread release radar notifications only")}/>
          </Form.Field>
        </Form.Group>
        <Popup
          content={interfaceText("Save this artist radar subscription. It observes already-ingested trusted radar evidence and does not poll MusicBrainz, search Soulseek, browse peers, or download.")}
          position="top center"
          trigger={
            <Button
              disabled={!artistId.trim()}
              onClick={subscribe}
              primary
              type="button"
            >
              <Icon name="rss" />
              <LocalizedText source={"Watch Artist"} /></Button>
          }
         {...interfaceTextProps("Save this artist radar subscription. It observes already-ingested trusted radar evidence and does not poll MusicBrainz, search Soulseek, browse peers, or download.")}/>
        <Popup
          content={interfaceText("Reload release radar subscriptions and notifications from the local backend.")}
          position="top center"
          trigger={
            <Button
              onClick={loadRadar}
              type="button"
            >
              <Icon name="refresh" />
              <LocalizedText source={"Refresh Radar"} /></Button>
          }
         {...interfaceTextProps("Reload release radar subscriptions and notifications from the local backend.")}/>
      </Form>
      {status && (
        <Message compact size="mini">
          <LocalizedText
            source={status.source}
            values={status.values?.title === 'Unresolved radar hit'
              ? { ...status.values, title: interfaceText('Unresolved radar hit') }
              : status.values}
          />
        </Message>
      )}
      {error && (
        <Message compact error size="mini">
          <LocalizedText source={error} />
        </Message>
      )}
      <div className="search-acquisition-profile-strip">
        <Label basic>
          <LocalizedText source={"Subscriptions"} /><Label.Detail>{subscriptions.length}</Label.Detail>
        </Label>
        <Label basic>
          <LocalizedText source={"Notifications"} /><Label.Detail>{notifications.length}</Label.Detail>
        </Label>
      </div>
      <List divided relaxed>
        {subscriptions.map((subscription) => {
          return (
            <List.Item key={subscription.id || subscription.artistId}>
              <List.Icon name={subscription.enabled ? 'rss' : 'pause circle'} />
              <List.Content>
                <List.Header>{subscription.artistName || subscription.artistId}</List.Header>
                <List.Description>
                  {subscription.scope}{' '}
                  <LocalizedText source="scope · muted" />{' '}
                  {asArray(subscription.mutedReleaseGroupIds).length}
                </List.Description>
              </List.Content>
            </List.Item>
          );
        })}
      </List>
      <Form>
        <Form.Input
          aria-label={interfaceText("Release radar route target peers")}
          label={interfaceText("Route target peers")}
          onChange={(event) => setRouteTargets(event.target.value)}
          placeholder={interfaceText("optional comma-separated peer IDs")}
          value={routeTargets}
         {...interfaceTextProps("Release radar route target peers")}/>
      </Form>
      <List divided relaxed>
        {notifications.map((notification) => {
          const title = getWorkTitle(notification);
          const hasResolvedTitle = title !== 'Unresolved radar hit';
          const localizedTitle = hasResolvedTitle ? title : interfaceText('Unresolved radar hit');
          const artist = getWorkArtist(notification);

          return (
            <List.Item key={notification.id}>
              <List.Icon name={notification.read ? 'check circle' : 'bell'} />
              <List.Content>
                <List.Header>
                  {[artist, hasResolvedTitle ? title : null].filter(Boolean).join(' - ') || (
                    <LocalizedText source="Unresolved radar hit" />
                  )}
                </List.Header>
                <List.Description>
                  {notification.sourceRealm || <LocalizedText source="Unknown realm" />}
                  {' · '}{Math.round((notification.confidence || 0) * 100)}%
                </List.Description>
                <Popup
                  content={interfaceText("Route this radar notification to explicitly listed trusted peers through the backend route service.")}
                  position="top center"
                  trigger={
                    <Button
                      aria-label={interfaceText('Route {title} radar hit', { title: localizedTitle })}
                      onClick={() => routeNotification(notification)}
                      size="mini"
                      type="button"
                     {...interfaceTextProps('Route {title} radar hit', { title: localizedTitle })}>
                      <Icon name="send" />
                      <LocalizedText source={"Route"} /></Button>
                  }
                 {...interfaceTextProps("Route this radar notification to explicitly listed trusted peers through the backend route service.")}/>
              </List.Content>
            </List.Item>
          );
        })}
      </List>
    </Segment>
  );
};

export default ArtistReleaseRadarPanel;
