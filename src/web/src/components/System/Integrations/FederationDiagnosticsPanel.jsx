import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../../../lib/interfaceLocale";


// <copyright file="FederationDiagnosticsPanel.jsx" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import React, { useEffect, useState } from 'react';
import * as federationDiagnostics from '../../../lib/federationDiagnostics';
import FeatureGateNotice from '../../Shared/FeatureGateNotice';
import useFeatureGates, { isFeatureEnabled } from '../../Shared/useFeatureGates';
import {
  Button,
  Card,
  Header,
  Icon,
  Message,
  Segment,
  Table,
  Label,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);

const valueOrDash = (value) =>
  value === undefined || value === null || value === '' ? '-' : value;

const boolLabel = (value, trueText = 'Enabled', falseText = 'Disabled') => (
  <Label>
    <Label.Detail>
      <Icon color={value ? 'green' : 'grey'} name={value ? 'check' : 'close'} />
    </Label.Detail>
    {value ? trueText : falseText}
  </Label>
);

const FederationDiagnosticsPanel = () => {
  const { featureGates, ready: featureGatesReady } = useFeatureGates();
  const socialFederationEnabled =
    featureGatesReady && isFeatureEnabled(featureGates, 'socialFederation');
  const [diagnostics, setDiagnostics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!socialFederationEnabled) return undefined;

    let mounted = true;

    const loadDiagnostics = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await federationDiagnostics.getDiagnostics();
        if (mounted) {
          setDiagnostics(response.data || {});
        }
      } catch (error_) {
        if (mounted) {
          setError(error_);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadDiagnostics();

    return () => {
      mounted = false;
    };
  }, [socialFederationEnabled]);

  if (!featureGatesReady || !socialFederationEnabled) {
    return (
      <Card fluid>
        <Card.Content>
          <Card.Header>
            <Icon name="share alternate" />
            <LocalizedText source={"Federation and Pod Diagnostics"} /></Card.Header>
          <Card.Meta>
            <LocalizedText source={"Read-only posture for ActivityPub, pod signing, and mesh-adjacent publishing."} /></Card.Meta>
        </Card.Content>
        <Card.Content>
          {featureGatesReady ? (
            <FeatureGateNotice
              configurationKeys={['feature.SocialFederation']}
              featureGate={featureGates.socialFederation}
              featureName="Social federation"
            />
          ) : (
            <Message info size="small"><LocalizedText source={"Checking feature availability…"} /></Message>
          )}
        </Card.Content>
      </Card>
    );
  }

  const federation = diagnostics?.federation || {};
  const publishing = diagnostics?.publishing || {};
  const pods = diagnostics?.pods || {};
  const mesh = diagnostics?.mesh || {};
  const warnings = asArray(diagnostics?.warnings);

  return (
    <Card fluid>
      <Card.Content>
        <Card.Header>
          <Icon name="share alternate" />
          <LocalizedText source={"Federation and Pod Diagnostics"} /></Card.Header>
        <Card.Meta>
          <LocalizedText source={"Read-only posture for ActivityPub, pod signing, and mesh-adjacent publishing."} /></Card.Meta>
      </Card.Content>
      <Card.Content>
        {error && (
          <Message
            negative
            size="small"
          >
            <LocalizedText source={"Federation diagnostics could not be loaded."} /></Message>
        )}
        <div className="integration-status-row">
          {boolLabel(federation.enabled, 'Federation On', 'Federation Off')}
          <Label>
            <Icon name="privacy" />
            <LocalizedText source={"Exposure:"} />{" "}{valueOrDash(federation.exposure)}
          </Label>
          {boolLabel(publishing.enabled, 'Publishing On', 'Publishing Off')}
          {boolLabel(
            federation.verifySignatures,
            'HTTP Signatures On',
            'HTTP Signatures Off',
          )}
        </div>
        <Table
          compact
          definition
          size="small"
        >
          <Table.Body>
            <Table.Row>
              <Table.Cell><LocalizedText source={"Domain configured"} /></Table.Cell>
              <Table.Cell>{federation.domainConfigured ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}</Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell><LocalizedText source={"Base URL configured"} /></Table.Cell>
              <Table.Cell>{federation.baseUrlConfigured ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}</Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell><LocalizedText source={"Publishable domains"} /></Table.Cell>
              <Table.Cell>{publishing.publishableDomains?.join(', ') || '-'}</Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell><LocalizedText source={"Publishing visibility"} /></Table.Cell>
              <Table.Cell>{valueOrDash(publishing.defaultVisibility)}</Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell><LocalizedText source={"Pod join signatures"} /></Table.Cell>
              <Table.Cell>{valueOrDash(pods.joinSignatureMode)}</Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell><LocalizedText source={"Pod message signatures"} /></Table.Cell>
              <Table.Cell>{valueOrDash(pods.messageSignatureMode)}</Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell><LocalizedText source={"Mesh self peer ID"} /></Table.Cell>
              <Table.Cell>{mesh.selfPeerIdConfigured ? <LocalizedText source={"Configured"} /> : <LocalizedText source={"Missing"} />}</Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell><LocalizedText source={"Soulseek rendezvous"} /></Table.Cell>
              <Table.Cell>{mesh.soulseekRendezvousEnabled ? <LocalizedText source={"Enabled"} /> : <LocalizedText source={"Disabled"} />}</Table.Cell>
            </Table.Row>
          </Table.Body>
        </Table>
        {warnings.length > 0 && (
          <Message
            size="small"
            warning
          >
            <Message.Header><LocalizedText source={"Federation posture warnings"} /></Message.Header>
            <Message.List items={warnings} />
          </Message>
        )}
        {!loading && warnings.length === 0 && diagnostics && (
          <Message
            positive
            size="small"
          >
            <LocalizedText source={"No federation or pod signing posture warnings were reported."} /></Message>
        )}
      </Card.Content>
    </Card>
  );
};

export default FederationDiagnosticsPanel;
