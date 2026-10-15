import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
import * as sourceProvidersApi from '../../../lib/sourceProviders';
import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Header,
  Icon,
  Label,
  Message,
  Popup,
  Segment,
  Statistic,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);

export const normalizeProvider = (provider = {}) => ({
  active: provider.active ?? provider.Active ?? false,
  capabilities: asArray(provider.capabilities ?? provider.Capabilities),
  description: provider.description ?? provider.Description ?? '',
  disabledReason: provider.disabledReason ?? provider.DisabledReason ?? '',
  domain: provider.domain ?? provider.Domain ?? 'Any',
  id: provider.id ?? provider.Id ?? '',
  name: provider.name ?? provider.Name ?? '',
  networkPolicy: provider.networkPolicy ?? provider.NetworkPolicy ?? '',
  registered: provider.registered ?? provider.Registered ?? false,
  requiresConfiguration:
    provider.requiresConfiguration ?? provider.RequiresConfiguration ?? false,
  riskLevel: provider.riskLevel ?? provider.RiskLevel ?? 'local',
  sortOrder: provider.sortOrder ?? provider.SortOrder ?? 100,
});

export const normalizeProfilePolicy = (policy = {}) => ({
  autoDownloadEnabled:
    policy.autoDownloadEnabled ?? policy.AutoDownloadEnabled ?? false,
  notes: policy.notes ?? policy.Notes ?? '',
  profileId: policy.profileId ?? policy.ProfileId ?? '',
  profileName: policy.profileName ?? policy.ProfileName ?? '',
  providerPriority: asArray(policy.providerPriority ?? policy.ProviderPriority),
});

// A real risk gradient, not a different hue per category: safest to most
// exposed maps onto the same four semantic colors used everywhere else.
const riskColor = (riskLevel) => {
  switch (riskLevel) {
    case 'local':
    case 'trusted-mesh':
      return 'green';
    case 'configured-network':
    case 'configured-lan':
      return 'blue';
    case 'public-network':
      return 'orange';
    case 'high-risk':
      return 'red';
    default:
      return 'grey';
  }
};

const SourceProviders = () => {
  useInterfaceLanguage();
  const [catalog, setCatalog] = useState({
    acquisitionPlanningEnabled: false,
    providers: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const providers = useMemo(
    () =>
      catalog.providers
        .filter((provider) => provider && typeof provider === 'object' && !Array.isArray(provider))
        .map(normalizeProvider)
        .sort((left, right) => left.sortOrder - right.sortOrder),
    [catalog.providers],
  );
  const profilePolicies = useMemo(
    () => asArray(catalog.profilePolicies)
      .filter((policy) => policy && typeof policy === 'object' && !Array.isArray(policy))
      .map(normalizeProfilePolicy),
    [catalog.profilePolicies],
  );
  const activeCount = providers.filter((provider) => provider.active).length;
  const configuredCount = providers.filter(
    (provider) => provider.registered && !provider.requiresConfiguration,
  ).length;

  const load = async () => {
    setLoading(true);
    setError('');

    try {
      setCatalog(await sourceProvidersApi.getSourceProviders());
    } catch (loadError) {
      setError(getApiErrorMessage(loadError, { t: interfaceText }));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="source-providers">
      {loading && (
        <Message info>
          <Icon
            loading
            name="spinner"
          />
          <LocalizedText source={"Loading source providers"} /></Message>
      )}
      {error && (
        <Message
          error
          header={interfaceText("Source providers unavailable")}
          content={error}
         {...interfaceTextProps("Source providers unavailable")}/>
      )}
      <Segment>
        <div className="source-providers-header">
          <Header as="h3">
            <Icon name="random" />
            <Header.Content>
              <LocalizedText source={"Source Providers"} /><Header.Subheader>
                <LocalizedText source={"Search, discovery, download, and verification sources available to acquisition planning."} /></Header.Subheader>
            </Header.Content>
          </Header>
          <Popup
            content={interfaceText("Reload the provider catalogue and current enablement state.")}
            position="top center"
            trigger={
              <Button
                aria-label={interfaceText("Refresh source providers")}
                icon="refresh"
                onClick={load}
               {...interfaceTextProps("Refresh source providers")}/>
            }
           {...interfaceTextProps("Reload the provider catalogue and current enablement state.")}/>
        </div>
        <Statistic.Group
          className="source-providers-summary"
          size="small"
        >
          <Statistic>
            <Statistic.Value>{activeCount}</Statistic.Value>
            <Statistic.Label><LocalizedText source={"Active"} /></Statistic.Label>
          </Statistic>
          <Statistic>
            <Statistic.Value>{providers.length}</Statistic.Value>
            <Statistic.Label><LocalizedText source={"Known"} /></Statistic.Label>
          </Statistic>
          <Statistic>
            <Statistic.Value>{configuredCount}</Statistic.Value>
            <Statistic.Label><LocalizedText source={"Ready"} /></Statistic.Label>
          </Statistic>
        </Statistic.Group>
        {!catalog.acquisitionPlanningEnabled && (
          <Message
            info
            header={interfaceText("Acquisition planning is disabled")}
            content={interfaceText("Providers remain visible here so enablement gaps are inspectable before automation is turned on.")}
           {...interfaceTextProps("Acquisition planning is disabled")}/>
        )}
      </Segment>
      <Card.Group
        className="source-provider-grid"
        itemsPerRow={3}
        stackable
      >
        {providers.map((provider) => (
          <Card
            className="source-provider-card"
            key={provider.id}
          >
            <Card.Content>
              <div className="source-provider-title-row">
                <Card.Header>{provider.name}</Card.Header>
                <Label color={provider.active ? 'green' : 'grey'}>
                  <Icon name={provider.active ? 'check circle' : 'pause circle'} />
                  {provider.active ? <LocalizedText source={"Active"} /> : <LocalizedText source={"Disabled"} />}
                </Label>
              </div>
              <Card.Meta>{provider.domain}</Card.Meta>
              <Card.Description>{provider.description}</Card.Description>
              <div className="source-provider-labels">
                <Label color={riskColor(provider.riskLevel)}>
                  {provider.riskLevel}
                </Label>
                {/* Registration is a fact, not a state that needs attention. */}
                <Label basic>
                  {provider.registered ? <LocalizedText source={"Registered"} /> : <LocalizedText source={"Not Registered"} />}
                </Label>
                {provider.requiresConfiguration && (
                  <Label color="yellow"><LocalizedText source={"Needs Config"} /></Label>
                )}
              </div>
            </Card.Content>
            <Card.Content>
              <Label.Group size="small">
                {provider.capabilities.map((capability) => (
                  <Label key={capability}>{capability}</Label>
                ))}
              </Label.Group>
            </Card.Content>
            <Card.Content extra>
              <p className="source-provider-policy">{provider.networkPolicy}</p>
              {provider.disabledReason && (
                <p className="source-provider-disabled">{provider.disabledReason}</p>
              )}
            </Card.Content>
          </Card>
        ))}
      </Card.Group>
      <Segment>
        <Header as="h4">
          <Icon name="sliders horizontal" />
          <Header.Content>
            <LocalizedText source={"Profile Provider Priority"} /><Header.Subheader>
              <LocalizedText source={"Read-only routing policy for each acquisition profile."} /></Header.Subheader>
          </Header.Content>
        </Header>
        <Card.Group
          className="source-provider-policy-grid"
          itemsPerRow={2}
          stackable
        >
          {profilePolicies.map((policy) => (
            <Card key={policy.profileId}>
              <Card.Content>
                <div className="source-provider-title-row">
                  <Card.Header>{policy.profileName}</Card.Header>
                  <Label color={policy.autoDownloadEnabled ? 'green' : 'grey'}>
                    <Icon name={policy.autoDownloadEnabled ? 'play' : 'pause'} />
                    {policy.autoDownloadEnabled ? <LocalizedText source={"Auto"} /> : <LocalizedText source={"Manual"} />}
                  </Label>
                </div>
                <Card.Description>{policy.notes}</Card.Description>
              </Card.Content>
              <Card.Content>
                <Label.Group size="small">
                  {policy.providerPriority.map((providerId, index) => (
                    <Label key={`${policy.profileId}-${providerId}`}>
                      {index + 1}. {providerId}
                    </Label>
                  ))}
                </Label.Group>
              </Card.Content>
            </Card>
          ))}
        </Card.Group>
      </Segment>
    </div>
  );
};

export default SourceProviders;
