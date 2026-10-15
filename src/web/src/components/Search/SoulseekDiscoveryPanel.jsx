import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
// <copyright file="SoulseekDiscoveryPanel.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import * as soulseekDiscovery from '../../lib/soulseekDiscovery';
import * as wishlist from '../../lib/wishlist';
import React, { useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import {
  Button as SemanticButton,
  Form,
  Header,
  Icon,
  Label,
  List,
  Message,
  Popup,
  Segment,
} from 'semantic-ui-react';
import TooltipButton from '../Shared/TooltipButton';

const Button = TooltipButton;

const getValue = (value, camel, pascal, fallback = undefined) =>
  value?.[camel] ?? value?.[pascal] ?? fallback;

const asArray = (value) => (Array.isArray(value) ? value : []);

const normalizeRecommendation = (recommendation) => ({
  item: getValue(recommendation, 'item', 'Item', ''),
  score: getValue(recommendation, 'score', 'Score', null),
});

const normalizeUser = (user) => {
  if (typeof user === 'string') {
    return { rating: null, username: user };
  }

  return {
    rating: getValue(user, 'rating', 'Rating', null),
    username: getValue(user, 'username', 'Username', ''),
  };
};

const getRecommendations = (payload) =>
  asArray(getValue(payload, 'recommendations', 'Recommendations', []))
    .map(normalizeRecommendation)
    .filter((recommendation) => recommendation.item);

const getUnrecommendations = (payload) =>
  asArray(getValue(payload, 'unrecommendations', 'Unrecommendations', []))
    .map(normalizeRecommendation)
    .filter((recommendation) => recommendation.item);

const getUsernames = (payload) =>
  asArray(getValue(payload, 'usernames', 'Usernames', []))
    .map(normalizeUser)
    .filter((user) => user.username);

const errorMessage = (error, fallback) =>
  getApiErrorMessage(error, { t: interfaceText }, fallback);

const SoulseekDiscoveryPanel = ({ disabled, onSearch }) => {
  useInterfaceLanguage();
  const [error, setError] = useState('');
  const [interest, setInterest] = useState('');
  const [item, setItem] = useState('');
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState([]);
  const [similarUsers, setSimilarUsers] = useState([]);
  const [status, setStatus] = useState('');
  const [title, setTitle] = useState('');
  const [unrecommendations, setUnrecommendations] = useState([]);
  const [userInterests, setUserInterests] = useState(null);
  const [username, setUsername] = useState('');

  const hasResults = useMemo(
    () =>
      recommendations.length > 0 ||
      unrecommendations.length > 0 ||
      similarUsers.length > 0 ||
      userInterests,
    [recommendations.length, similarUsers.length, unrecommendations.length, userInterests],
  );

  const clearResults = () => {
    setRecommendations([]);
    setSimilarUsers([]);
    setUnrecommendations([]);
    setUserInterests(null);
  };

  const run = async (action) => {
    setError('');
    setLoading(true);
    try {
      await action();
    } catch (actionError) {
      setError(errorMessage(actionError, 'The request failed. Try again.'));
    } finally {
      setLoading(false);
    }
  };

  const loadRecommendations = (global = false) =>
    run(async () => {
      const response = global
        ? await soulseekDiscovery.getGlobalRecommendations()
        : await soulseekDiscovery.getRecommendations();
      const payload = response.data || {};

      clearResults();
      setRecommendations(getRecommendations(payload));
      setUnrecommendations(getUnrecommendations(payload));
      setTitle(global ? 'Global recommendations' : 'My recommendations');
      setStatus(interfaceText('Recommendations loaded: {count}.', {
        count: getRecommendations(payload).length,
      }));
    });

  const loadItemRecommendations = () => {
    const trimmed = item.trim();
    if (!trimmed) {
      toast.error(interfaceText("Item is required"));
      return;
    }

    run(async () => {
      const response = await soulseekDiscovery.getItemRecommendations({
        item: trimmed,
      });

      clearResults();
      setRecommendations(getRecommendations(response.data || {}));
      setTitle(`Recommendations for ${trimmed}`);
      setStatus(interfaceText('Related recommendation seeds loaded for {item}.', { item: trimmed }));
    });
  };

  const loadSimilarUsers = () =>
    run(async () => {
      const response = await soulseekDiscovery.getSimilarUsers();
      const users = asArray(response.data);

      clearResults();
      setSimilarUsers(users.map(normalizeUser).filter((user) => user.username));
      setTitle('Similar users');
      setStatus(interfaceText('Loaded {count} similar users.', { count: users.length }));
    });

  const loadItemSimilarUsers = () => {
    const trimmed = item.trim();
    if (!trimmed) {
      toast.error(interfaceText("Item is required"));
      return;
    }

    run(async () => {
      const response = await soulseekDiscovery.getItemSimilarUsers({
        item: trimmed,
      });

      clearResults();
      setSimilarUsers(getUsernames(response.data || {}));
      setTitle(`Users similar to ${trimmed}`);
      setStatus(interfaceText('Users associated with {item} loaded.', { item: trimmed }));
    });
  };

  const loadUserInterests = (target = username) => {
    const trimmed = `${target || ''}`.trim();
    if (!trimmed) {
      toast.error(interfaceText("Username is required"));
      return;
    }

    run(async () => {
      const response = await soulseekDiscovery.getUserInterests({
        username: trimmed,
      });

      clearResults();
      setUserInterests(response.data || {});
      setTitle(`${trimmed} interests`);
      setStatus(interfaceText('Native interests loaded for {username}.', { username: trimmed }));
    });
  };

  const updateInterest = (hated = false, remove = false) => {
    const trimmed = interest.trim();
    if (!trimmed) {
      toast.error(interfaceText("Interest is required"));
      return;
    }

    const action = hated
      ? remove
        ? soulseekDiscovery.removeHatedInterest
        : soulseekDiscovery.addHatedInterest
      : remove
        ? soulseekDiscovery.removeInterest
        : soulseekDiscovery.addInterest;

    run(async () => {
      await action({ item: trimmed });
      const statusSource = remove
        ? hated ? 'Removed {interest} as a hated interest.' : 'Removed {interest} as an interest.'
        : hated ? 'Added {interest} as a hated interest.' : 'Added {interest} as an interest.';
      setStatus(interfaceText(statusSource, { interest: trimmed }));
      setInterest('');
    });
  };

  const addToWishlist = async (searchText) => {
    try {
      await wishlist.create({
        autoDownload: false,
        enabled: false,
        filter: 'source:soulseek-native-discovery; review-only',
        maxResults: 25,
        searchText,
      });
      toast.success(interfaceText("Added {searchText} to Wishlist for review", { "searchText": (searchText) }));
    } catch (wishlistError) {
      toast.error(errorMessage(wishlistError, 'Unable to add to Wishlist.'));
    }
  };

  const renderRecommendation = (recommendation) => (
    <List.Item key={`${recommendation.item}-${recommendation.score ?? 'n'}`}>
      <List.Content floated="right">
        <Popup
          content={interfaceText("Start a normal Soulseek search for this recommendation.")}
          trigger={
            <SemanticButton
              aria-label={interfaceText("Search {item}", { "item": (recommendation.item) })}
              icon="search"
              onClick={() => onSearch?.(recommendation.item)}
              size="mini"
             {...interfaceTextProps("Search {item}")}/>
          }
         {...interfaceTextProps("Start a normal Soulseek search for this recommendation.")}/>
        <Popup
          content={interfaceText("Save this raw recommendation to Wishlist for manual review.")}
          trigger={
            <SemanticButton
              aria-label={interfaceText("Add {item} to Wishlist", { "item": (recommendation.item) })}
              icon="bookmark outline"
              onClick={() => addToWishlist(recommendation.item)}
              size="mini"
             {...interfaceTextProps("Add {item} to Wishlist")}/>
          }
         {...interfaceTextProps("Save this raw recommendation to Wishlist for manual review.")}/>
      </List.Content>
      <List.Icon name="music" />
      <List.Content>
        <List.Header>{recommendation.item}</List.Header>
        {recommendation.score !== null && (
          <List.Description>
            <Label size="mini"><LocalizedText source={"score"} />{" "}{recommendation.score}</Label>
          </List.Description>
        )}
      </List.Content>
    </List.Item>
  );

  const renderSimilarUser = (user) => (
    <List.Item key={user.username}>
      <List.Content floated="right">
        <Popup
          content={interfaceText("Load this user's native Soulseek interests.")}
          trigger={
            <SemanticButton
              aria-label={interfaceText("Load {username} interests", { "username": (user.username) })}
              icon="heart outline"
              onClick={() => loadUserInterests(user.username)}
              size="mini"
             {...interfaceTextProps("Load {username} interests")}/>
          }
         {...interfaceTextProps("Load this user's native Soulseek interests.")}/>
      </List.Content>
      <List.Icon name="user" />
      <List.Content>
        <List.Header>{user.username}</List.Header>
        {user.rating !== null && (
          <List.Description>
            <Label size="mini"><LocalizedText source={"rating"} />{" "}{user.rating}</Label>
          </List.Description>
        )}
      </List.Content>
    </List.Item>
  );

  const renderInterestList = (label, values, color) => (
    <div style={{ marginBottom: '0.75em' }}>
      <Header
        as="h5"
        style={{ marginBottom: '0.35em' }}
      >
        {label}
      </Header>
      {values.length === 0 ? (
        <span style={{ opacity: 0.65 }}><LocalizedText source={"None reported"} /></span>
      ) : (
        values.map((value) => (
          <Label
            color={color}
            key={value}
            size="small"
          >
            {value}
          </Label>
        ))
      )}
    </div>
  );

  if (disabled) {
    return (
      <Segment raised>
        <Header as="h4"><LocalizedText source={"Soulseek Native Discovery"} /></Header>
        <p><LocalizedText source={"Connect to the server to use native Soulseek interests and recommendations."} /></p>
      </Segment>
    );
  }

  const liked = asArray(getValue(userInterests, 'liked', 'Liked', []));
  const hated = asArray(getValue(userInterests, 'hated', 'Hated', []));

  return (
    <Segment loading={loading}>
      <Header as="h4">
        <Icon name="compass outline" />
        <Header.Content><LocalizedText source={"Soulseek Native Discovery"} /></Header.Content>
      </Header>

      <Form>
        <Form.Group widths="equal">
          <Form.Input
            label={interfaceText("Interest")}
            onChange={(event) => setInterest(event.target.value)}
            placeholder={interfaceText("genre, artist, scene, tag")}
            value={interest}
           {...interfaceTextProps("Interest")}/>
          <Form.Input
            label={interfaceText("Item")}
            onChange={(event) => setItem(event.target.value)}
            placeholder={interfaceText("item to branch from")}
            value={item}
           {...interfaceTextProps("Item")}/>
          <Form.Input
            label={interfaceText("User")}
            onChange={(event) => setUsername(event.target.value)}
            placeholder={interfaceText("username")}
            value={username}
           {...interfaceTextProps("User")}/>
        </Form.Group>
        <Button.Group size="small">
          <Button
            icon
            labelPosition="left"
            onClick={() => updateInterest(false, false)}
            type="button"
            tooltip="Add this text to your Soulseek interest profile to shape future recommendations."
          >
            <Icon name="heart" />
            <LocalizedText source={"Add Interest"} /></Button>
          <Button
            icon
            labelPosition="left"
            onClick={() => updateInterest(true, false)}
            type="button"
            tooltip="Mark this text as something you do not want recommended."
          >
            <Icon name="ban" />
            <LocalizedText source={"Add Hated"} /></Button>
          <Button
            icon
            labelPosition="left"
            onClick={() => updateInterest(false, true)}
            type="button"
            tooltip="Remove this text from your interest profile."
          >
            <Icon name="minus circle" />
            <LocalizedText source={"Remove Interest"} /></Button>
          <Button
            icon
            labelPosition="left"
            onClick={() => updateInterest(true, true)}
            type="button"
            tooltip="Stop suppressing this text from recommendations."
          >
            <Icon name="minus square outline" />
            <LocalizedText source={"Remove Hated"} /></Button>
        </Button.Group>
        <Button.Group
          floated="right"
          size="small"
        >
          <Button
            icon
            labelPosition="left"
            onClick={() => loadRecommendations(false)}
            type="button"
            tooltip="Load recommendations based on your own Soulseek interests."
          >
            <Icon name="lightbulb outline" />
            <LocalizedText source={"My Recs"} /></Button>
          <Button
            icon
            labelPosition="left"
            onClick={() => loadRecommendations(true)}
            type="button"
            tooltip="Load shared recommendations across the Soulseek community."
          >
            <Icon name="globe" />
            <LocalizedText source={"Global"} /></Button>
          <Button
            icon
            labelPosition="left"
            onClick={loadSimilarUsers}
            type="button"
            tooltip="Find users with interests similar to yours."
          >
            <Icon name="users" />
            <LocalizedText source={"Similar Users"} /></Button>
          <Button
            icon
            labelPosition="left"
            onClick={loadItemRecommendations}
            type="button"
            tooltip="Find recommendations related to the item you entered."
          >
            <Icon name="sitemap" />
            <LocalizedText source={"Item Recs"} /></Button>
          <Button
            icon
            labelPosition="left"
            onClick={loadItemSimilarUsers}
            type="button"
            tooltip="Find users who are similar to people interested in this item."
          >
            <Icon name="user plus" />
            <LocalizedText source={"Item Users"} /></Button>
          <Button
            icon
            labelPosition="left"
            onClick={() => loadUserInterests()}
            type="button"
            tooltip="Fetch the entered user's public interest and hated-item lists."
          >
            <Icon name="address card outline" />
            <LocalizedText source={"User Interests"} /></Button>
        </Button.Group>
      </Form>

      {error && (
        <Message
          content={error}
          error
        />
      )}
      {status && (
        <Message
          content={status}
          positive={!error}
        />
      )}

      {hasResults && (
        <Segment secondary>
          <Header as="h5">{title || 'Discovery results'}</Header>
          {recommendations.length > 0 && (
            <List
              divided
              relaxed
            >
              {recommendations.map(renderRecommendation)}
            </List>
          )}
          {unrecommendations.length > 0 && (
            <>
              <Header as="h5"><LocalizedText source={"Unrecommendations"} /></Header>
              <List
                divided
                relaxed
              >
                {unrecommendations.map(renderRecommendation)}
              </List>
            </>
          )}
          {similarUsers.length > 0 && (
            <List
              divided
              relaxed
            >
              {similarUsers.map(renderSimilarUser)}
            </List>
          )}
          {userInterests && (
            <>
              {renderInterestList('Liked', liked, 'green')}
              {renderInterestList('Hated', hated, 'red')}
            </>
          )}
        </Segment>
      )}
    </Segment>
  );
};

export default SoulseekDiscoveryPanel;
