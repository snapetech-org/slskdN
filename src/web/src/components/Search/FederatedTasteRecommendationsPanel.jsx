import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
// <copyright file="FederatedTasteRecommendationsPanel.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import {
  fetchTasteRecommendations,
  previewTasteRecommendationGraph,
  promoteTasteRecommendationToWishlist,
  subscribeTasteRecommendationReleaseRadar,
} from '../../lib/tasteRecommendations';
import { formatRegionalNumber, useRegionalLocale } from '../../lib/regionalFormat';
import FeatureGateNotice from '../Shared/FeatureGateNotice';
import useFeatureGates, { isFeatureEnabled } from '../Shared/useFeatureGates';
import React, { useState } from 'react';
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

const getCreator = (workRef = {}) => workRef.creator || workRef.Creator || '';

const getTitle = (workRef = {}) => workRef.title || workRef.Title || 'Untitled recommendation';

const getSearchText = (workRef = {}) =>
  [getCreator(workRef), getTitle(workRef)].filter(Boolean).join(' ') || getTitle(workRef);

const asArray = (value) => (Array.isArray(value) ? value : []);

const FederatedTasteRecommendationsPanel = ({ disabled }) => {
  useInterfaceLanguage();
  const regionalLocale = useRegionalLocale();
  const { featureGates, ready: featureGatesReady } = useFeatureGates();
  const socialFederationEnabled =
    featureGatesReady && isFeatureEnabled(featureGates, 'socialFederation');
  const [error, setError] = useState('');
  const [graphPreview, setGraphPreview] = useState(null);
  const [includeSoulseekRecommendations, setIncludeSoulseekRecommendations] = useState(false);
  const [includeSourceActors, setIncludeSourceActors] = useState(false);
  const [limit, setLimit] = useState(20);
  const [loading, setLoading] = useState(false);
  const [minimumTrustedSources, setMinimumTrustedSources] = useState(2);
  const [recommendations, setRecommendations] = useState([]);
  const [status, setStatus] = useState('');
  const [summary, setSummary] = useState(null);

  const loadRecommendations = async () => {
    setError('');
    setLoading(true);
    try {
      const response = await fetchTasteRecommendations({
        includeSoulseekRecommendations,
        includeSourceActors,
        limit: Number(limit) || 20,
        minimumTrustedSources: Number(minimumTrustedSources) || 2,
      });
      const nextRecommendations = asArray(response.data?.recommendations);
      setSummary(response.data);
      setRecommendations(nextRecommendations);
      setStatus(interfaceText('Loaded {count} privacy-filtered recommendations.', {
        count: nextRecommendations.length,
      }));
    } catch (loadError) {
      setError(getApiErrorMessage(
        loadError,
        { t: interfaceText },
        'Unable to load federated taste recommendations.',
      ));
    } finally {
      setLoading(false);
    }
  };

  const promoteToWishlist = async (recommendation) => {
    try {
      await promoteTasteRecommendationToWishlist({
        note: 'Promoted from federated taste recommendation review.',
        workRef: recommendation.workRef,
      });
      setStatus(interfaceText('Promoted {title} to Wishlist.', {
        title: getTitle(recommendation.workRef),
      }));
    } catch (promoteError) {
      toast.error(getApiErrorMessage(promoteError, { t: interfaceText }));
    }
  };

  const subscribeRadar = async (recommendation) => {
    try {
      await subscribeTasteRecommendationReleaseRadar({
        scope: 'trusted',
        workRef: recommendation.workRef,
      });
      setStatus(interfaceText('Subscribed {creator} to Release Radar.', {
        creator: getCreator(recommendation.workRef),
      }));
    } catch (subscribeError) {
      toast.error(getApiErrorMessage(subscribeError, { t: interfaceText }));
    }
  };

  const previewGraph = async (recommendation) => {
    try {
      const response = await previewTasteRecommendationGraph({
        workRef: recommendation.workRef,
      });
      setGraphPreview(response.data);
      setStatus(interfaceText('Discovery Graph previewed for {title}.', {
        title: getTitle(recommendation.workRef),
      }));
    } catch (previewError) {
      toast.error(getApiErrorMessage(previewError, { t: interfaceText }));
    }
  };

  if (disabled) {
    return (
      <Segment raised>
        <Header as="h4"><LocalizedText source={"Federated Taste Recommendations"} /></Header>
        <p><LocalizedText source={"Connect to the server to load privacy-filtered recommendations."} /></p>
      </Segment>
    );
  }

  if (!featureGatesReady) {
    return (
      <Segment raised>
        <Header as="h4"><LocalizedText source={"Federated Taste Recommendations"} /></Header>
        <Message info size="small"><LocalizedText source={"Checking feature availability…"} /></Message>
      </Segment>
    );
  }

  if (!socialFederationEnabled) {
    return (
      <Segment raised>
        <Header as="h4"><LocalizedText source={"Federated Taste Recommendations"} /></Header>
        <FeatureGateNotice
          configurationKeys={['feature.SocialFederation']}
          featureGate={featureGates.socialFederation}
          featureName="Social federation"
        />
      </Segment>
    );
  }

  return (
    <Segment
      loading={loading}
      raised
    >
      <Header as="h4"><LocalizedText source={"Federated Taste Recommendations"} /></Header>
      <Form>
        <Form.Group widths="equal">
          <Form.Input
            aria-label={interfaceText("Taste recommendation limit")}
            label={interfaceText("Limit")}
            min={1}
            onChange={(event) => setLimit(event.target.value)}
            type="number"
            value={limit}
           {...interfaceTextProps("Taste recommendation limit")}/>
          <Form.Input
            aria-label={interfaceText("Minimum trusted taste sources")}
            label={interfaceText("Minimum trusted sources")}
            min={1}
            onChange={(event) => setMinimumTrustedSources(event.target.value)}
            type="number"
            value={minimumTrustedSources}
           {...interfaceTextProps("Minimum trusted taste sources")}/>
          <Form.Field>
            <label><LocalizedText source={"Reveal source actors"} /></label>
            <Checkbox
              aria-label={interfaceText("Reveal federated recommendation source actors")}
              checked={includeSourceActors}
              onChange={(_event, data) => setIncludeSourceActors(data.checked)}
              toggle
             {...interfaceTextProps("Reveal federated recommendation source actors")}/>
          </Form.Field>
          <Form.Field>
            <label><LocalizedText source={"Include Soulseek native"} /></label>
            <Checkbox
              aria-label={interfaceText("Include Soulseek native recommendations")}
              checked={includeSoulseekRecommendations}
              onChange={(_event, data) => setIncludeSoulseekRecommendations(data.checked)}
              toggle
             {...interfaceTextProps("Include Soulseek native recommendations")}/>
          </Form.Field>
        </Form.Group>
        <Popup
          content={interfaceText("Load privacy-filtered recommendations from followed federated actors. Optionally include raw native Soulseek recommendation seeds.")}
          position="top center"
          trigger={
            <Button
              onClick={loadRecommendations}
              primary
              type="button"
            >
              <Icon name="users" />
              <LocalizedText source={"Load Recommendations"} /></Button>
          }
         {...interfaceTextProps("Load privacy-filtered recommendations from followed federated actors. Optionally include raw native Soulseek recommendation seeds.")}/>
      </Form>
      {status && <Message compact size="mini">{status}</Message>}
      {error && <Message compact error size="mini">{String(error)}</Message>}
      {summary && (
        <div className="search-acquisition-profile-strip">
          <Label basic>
            <LocalizedText source={"Trusted actors"} /><Label.Detail>{summary.trustedActorCount}</Label.Detail>
          </Label>
          <Label basic>
            <LocalizedText source={"Candidates"} /><Label.Detail>{summary.candidateCount}</Label.Detail>
          </Label>
          <Label basic>
            <LocalizedText source={"Minimum sources"} /><Label.Detail>{summary.minimumTrustedSources}</Label.Detail>
          </Label>
        </div>
      )}
      {graphPreview && (
        <Message compact size="mini">
          <LocalizedText
            source={"Graph preview: {nodes} nodes, {edges} edges."}
            values={{
              nodes: formatRegionalNumber(graphPreview.nodeCount, undefined, regionalLocale),
              edges: formatRegionalNumber(graphPreview.edgeCount, undefined, regionalLocale),
            }}
          />
        </Message>
      )}
      <List divided relaxed>
        {recommendations.map((recommendation) => {
          const title = getTitle(recommendation.workRef);
          const creator = getCreator(recommendation.workRef);

          return (
            <List.Item key={recommendation.workRef?.id || `${creator}-${title}`}>
              <List.Icon name="user friends" />
              <List.Content>
                <List.Header>{[creator, title].filter(Boolean).join(' - ') || title}</List.Header>
                <List.Description>
                  {recommendation.trustedSourceCount} <LocalizedText source={"trusted sources · score"} />{" "}{Math.round((recommendation.score || 0) * 100)}%
                </List.Description>
                {asArray(recommendation.reasons).map((reason) => (
                  <Label basic key={reason}>{reason}</Label>
                ))}
                {includeSourceActors && asArray(recommendation.sourceActors).length > 0 && (
                  <div className="search-acquisition-profile-summary">
                    {asArray(recommendation.sourceActors).join(', ')}
                  </div>
                )}
                <Popup
                  content={interfaceText("Promote this WorkRef to Wishlist through the backend review handoff without starting a download.")}
                  position="top center"
                  trigger={
                    <Button
                      aria-label={interfaceText("Promote {title} taste recommendation to Wishlist", { "title": (title) })}
                      onClick={() => promoteToWishlist(recommendation)}
                      size="mini"
                      type="button"
                     {...interfaceTextProps("Promote {title} taste recommendation to Wishlist")}>
                      <Icon name="heart" />
                      <LocalizedText source={"Wishlist"} /></Button>
                  }
                 {...interfaceTextProps("Promote this WorkRef to Wishlist through the backend review handoff without starting a download.")}/>
                <Popup
                  content={interfaceText("Subscribe this artist to Release Radar using trusted scope.")}
                  position="top center"
                  trigger={
                    <Button
                      aria-label={interfaceText("Subscribe {title} taste recommendation to Release Radar", { "title": (title) })}
                      onClick={() => subscribeRadar(recommendation)}
                      size="mini"
                      type="button"
                     {...interfaceTextProps("Subscribe {title} taste recommendation to Release Radar")}>
                      <Icon name="rss" />
                      <LocalizedText source={"Radar"} /></Button>
                  }
                 {...interfaceTextProps("Subscribe this artist to Release Radar using trusted scope.")}/>
                <Popup
                  content={interfaceText("Preview nearby Discovery Graph evidence for this WorkRef.")}
                  position="top center"
                  trigger={
                    <Button
                      aria-label={interfaceText("Preview {title} taste recommendation graph", { "title": (title) })}
                      onClick={() => previewGraph(recommendation)}
                      size="mini"
                      type="button"
                     {...interfaceTextProps("Preview {title} taste recommendation graph")}>
                      <Icon name="share alternate" />
                      <LocalizedText source={"Graph"} /></Button>
                  }
                 {...interfaceTextProps("Preview nearby Discovery Graph evidence for this WorkRef.")}/>
              </List.Content>
            </List.Item>
          );
        })}
      </List>
    </Segment>
  );
};

export default FederatedTasteRecommendationsPanel;
