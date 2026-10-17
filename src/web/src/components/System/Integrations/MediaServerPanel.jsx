import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
// <copyright file="MediaServerPanel.jsx" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
import React, { useState } from 'react';
import {
  buildMediaServerExecutionContract,
  buildMediaServerPathDiagnostic,
  buildMediaServerSyncPreview,
  defaultMediaServerAutomations,
  formatMediaServerExecutionContractReport,
  formatMediaServerSyncReport,
  mediaServerAutomationContracts,
  mediaServerAdapters,
} from '../../../lib/mediaServerIntegrations';
import TooltipButton from '../../Shared/TooltipButton';
import {
  Button,
  Card,
  Form,
  Header,
  Icon,
  Message,
  Popup,
  Segment,
} from 'semantic-ui-react';

const MediaServerPanel = () => {
  useInterfaceLanguage();
  const [activeAdapterId, setActiveAdapterId] = useState(
    mediaServerAdapters[0]?.id ?? null,
  );
  const [baseUrl, setBaseUrl] = useState('');
  const [tokenConfigured, setTokenConfigured] = useState(false);
  const [localPath, setLocalPath] = useState('');
  const [serverPath, setServerPath] = useState('');
  const [remotePathFrom, setRemotePathFrom] = useState('');
  const [remotePathTo, setRemotePathTo] = useState('');
  const [userMappingConfigured, setUserMappingConfigured] = useState(false);
  const [confirmationRequired, setConfirmationRequired] = useState(true);
  const [rateLimitPerMinute, setRateLimitPerMinute] = useState(6);
  const [dedupeWindowHours, setDedupeWindowHours] = useState(24);
  const [enabledAutomations, setEnabledAutomations] = useState(
    () => ({ ...defaultMediaServerAutomations }),
  );
  const [syncReport, setSyncReport] = useState(null);
  const [pathDiagnostic, setPathDiagnostic] = useState(null);
  const [contractReport, setContractReport] = useState(null);

  const hasAdapters = mediaServerAdapters.length > 0;
  const hasContracts = mediaServerAutomationContracts.length > 0;

  const getSyncPreview = () =>
    buildMediaServerSyncPreview({
      adapterId: activeAdapterId,
      baseUrl,
      localPath,
      remotePathFrom,
      remotePathTo,
      serverPath,
      tokenConfigured,
    });

  const handlePreviewSync = () => {
    setSyncReport(formatMediaServerSyncReport(getSyncPreview()));
  };

  const handlePathDiagnostic = () => {
    setPathDiagnostic(
      buildMediaServerPathDiagnostic({
        localPath,
        remotePathFrom,
        remotePathTo,
        serverPath,
      }),
    );
  };

  const handleReviewContract = () => {
    const contract = buildMediaServerExecutionContract({
      confirmationRequired,
      dedupeWindowHours,
      enabledAutomations,
      rateLimitPerMinute,
      syncPreview: getSyncPreview(),
      userMappingConfigured,
    });
    setContractReport(formatMediaServerExecutionContractReport(contract));
  };

  const updateAutomation = (automationId, enabled) => {
    setEnabledAutomations((current) => ({
      ...current,
      [automationId]: enabled,
    }));
  };

  return (
    <Card fluid>
      <Card.Content>
        <Card.Header>
          <Icon name="server" />
          <LocalizedText source={"Media Servers"} /></Card.Header>
        <Card.Meta>
          <LocalizedText source={"Local readiness reviews for Plex, Jellyfin/Emby, and Navidrome. Nothing here saves credentials or contacts a media server."} /></Card.Meta>
      </Card.Content>
      <Card.Content>
        <Message info size="small">
          <LocalizedText source={"Enter the values you want to review. They remain in this page only; preview and contract actions do not run scans or other server work."} /></Message>

        {!hasAdapters && (
          <Message info size="small">
            <LocalizedText source={"No registered media server adapters are available."} /></Message>
        )}

        {!hasContracts && hasAdapters && (
          <Message warning size="small">
            <LocalizedText source={"No media server automation contracts are available."} /></Message>
        )}

        {hasAdapters && (
          <div className="integration-actions">
            {mediaServerAdapters.map((adapter) => (
              <Popup
                content={interfaceText("Review {label} integration readiness and path mapping.", { "label": (adapter.label) })}
                key={adapter.id}
                position="top center"
                trigger={
                  <Button
                    aria-label={interfaceText("Review {label} sync readiness", { "label": (adapter.label) })}
                    basic={activeAdapterId !== adapter.id}
                    color={
                      activeAdapterId === adapter.id ? 'purple' : undefined
                    }
                    icon
                    labelPosition="left"
                    onClick={() => setActiveAdapterId(adapter.id)}
                   {...interfaceTextProps("Review {label} sync readiness")}>
                    <Icon name={adapter.icon || 'server'} />
                    <LocalizedText source={adapter.label} />
                  </Button>
                }
               {...interfaceTextProps("Review {label} integration readiness and path mapping.")}/>
            ))}
          </div>
        )}

        <Form
          className="media-server-review-form"
          onSubmit={(event) => event.preventDefault()}
        >
          <section className="media-server-review-section">
            <Header as="h4"><LocalizedText source={"Connection"} /></Header>
            <Form.Group widths="equal">
              <Form.Input
                aria-label={interfaceText("Media server base URL")}
                id="media-server-base-url"
                label={interfaceText("Media server base URL")}
                onChange={(_event, { value }) => setBaseUrl(value)}
                placeholder="https://media.example"
                value={baseUrl}
               {...interfaceTextProps("Media server base URL")}/>
              <Form.Checkbox
                aria-label={interfaceText("API token is configured")}
                checked={tokenConfigured}
                id="media-server-token-configured"
                label={interfaceText("API token is configured")}
                onChange={(_event, { checked }) => setTokenConfigured(checked)}
               {...interfaceTextProps("API token is configured")}/>
            </Form.Group>
          </section>

          <section className="media-server-review-section">
            <Header as="h4"><LocalizedText source={"Path mapping"} /></Header>
            <Form.Group widths="equal">
              <Form.Input
                aria-label={interfaceText("Completed-download path on slskdN")}
                id="media-server-local-path"
                label={interfaceText("Completed-download path on slskdN")}
                onChange={(_event, { value }) => setLocalPath(value)}
                placeholder="/downloads/music"
                value={localPath}
               {...interfaceTextProps("Completed-download path on slskdN")}/>
              <Form.Input
                aria-label={interfaceText("Library path on the media server")}
                id="media-server-server-path"
                label={interfaceText("Library path on the media server")}
                onChange={(_event, { value }) => setServerPath(value)}
                placeholder="/library/music"
                value={serverPath}
               {...interfaceTextProps("Library path on the media server")}/>
            </Form.Group>

            <Form.Group widths="equal">
              <Form.Input
                aria-label={interfaceText("Remote path mapping: from")}
                id="media-server-remote-path-from"
                label={interfaceText("Remote path mapping: from")}
                onChange={(_event, { value }) => setRemotePathFrom(value)}
                placeholder="/downloads"
                value={remotePathFrom}
               {...interfaceTextProps("Remote path mapping: from")}/>
              <Form.Input
                aria-label={interfaceText("Remote path mapping: to")}
                id="media-server-remote-path-to"
                label={interfaceText("Remote path mapping: to")}
                onChange={(_event, { value }) => setRemotePathTo(value)}
                placeholder="/library"
                value={remotePathTo}
               {...interfaceTextProps("Remote path mapping: to")}/>
            </Form.Group>
          </section>

          <section className="media-server-review-section">
            <Header as="h4"><LocalizedText source={"Safety contract"} /></Header>
            <Form.Group widths="equal">
              <Form.Checkbox
                aria-label={interfaceText("Media server user mapping is configured")}
                checked={userMappingConfigured}
                id="media-server-user-mapping-configured"
                label={interfaceText("Media server user mapping is configured")}
                onChange={(_event, { checked }) =>
                  setUserMappingConfigured(checked)
                }
               {...interfaceTextProps("Media server user mapping is configured")}/>
              <Form.Checkbox
                aria-label={interfaceText("Require confirmation for actions")}
                checked={confirmationRequired}
                id="media-server-confirmation-required"
                label={interfaceText("Require confirmation for actions")}
                onChange={(_event, { checked }) =>
                  setConfirmationRequired(checked)
                }
               {...interfaceTextProps("Require confirmation for actions")}/>
            </Form.Group>

            <Form.Group widths="equal">
              <Form.Input
                aria-label={interfaceText("Maximum calls per minute")}
                id="media-server-rate-limit"
                label={interfaceText("Maximum calls per minute")}
                min={0}
                onChange={(_event, { value }) =>
                  setRateLimitPerMinute(Number(value))
                }
                type="number"
                value={rateLimitPerMinute}
               {...interfaceTextProps("Maximum calls per minute")}/>
              <Form.Input
                aria-label={interfaceText("Dedupe window in hours")}
                id="media-server-dedupe-window"
                label={interfaceText("Dedupe window in hours")}
                min={0}
                onChange={(_event, { value }) =>
                  setDedupeWindowHours(Number(value))
                }
                type="number"
                value={dedupeWindowHours}
               {...interfaceTextProps("Dedupe window in hours")}/>
            </Form.Group>

            <Form.Group grouped>
              <Header as="h5">
                <LocalizedText source={"Include automations in the local readiness review"} /></Header>
              {mediaServerAutomationContracts.map((automation) => (
                <Form.Checkbox
                  aria-label={interfaceText("Include {label} in review", { "label": (automation.label) })}
                  checked={Boolean(enabledAutomations[automation.id])}
                  id={`media-server-automation-${automation.id}`}
                  key={automation.id}
                  label={interfaceText("{label}: {description}", { "label": (automation.label), "description": (automation.description) })}
                  onChange={(_event, { checked }) =>
                    updateAutomation(automation.id, checked)
                  }
                 {...interfaceTextProps("Include {label} in review")}/>
              ))}
            </Form.Group>
          </section>
        </Form>

        <div className="integration-actions">
          <TooltipButton
            disabled={!hasAdapters}
            icon
            labelPosition="left"
            onClick={handlePreviewSync}
            tooltip="Check URL, token, and path readiness. This creates a local report and does not contact the media server."
          >
            <Icon name="sync" />
            <LocalizedText source={"Preview Sync"} /></TooltipButton>
          <TooltipButton
            disabled={!hasAdapters}
            icon
            labelPosition="left"
            onClick={handlePathDiagnostic}
            tooltip="Compare the local and server paths, applying the optional remote mapping; this check stays in your browser."
          >
            <Icon name="folder open" />
            <LocalizedText source={"Path Diagnostic"} /></TooltipButton>
          <TooltipButton
            disabled={!hasContracts}
            icon
            labelPosition="left"
            onClick={handleReviewContract}
            primary
            tooltip="Review readiness gates and selected automations. This report runs no media server actions."
          >
            <Icon name="clipboard check" />
            <LocalizedText source={"Review Contract"} /></TooltipButton>
        </div>

        {contractReport && (
          <Segment style={{ marginTop: '1em' }}>
            <Header as="h4"><LocalizedText source={"Contract Review"} /></Header>
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {contractReport}
            </pre>
          </Segment>
        )}

        {syncReport && (
          <Segment style={{ marginTop: '1em' }}>
            <Header as="h4"><LocalizedText source={"Sync Preview"} /></Header>
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {syncReport}
            </pre>
          </Segment>
        )}

        {pathDiagnostic && (
          <Segment style={{ marginTop: '1em' }}>
            <Header as="h4"><LocalizedText source={"Path Diagnostic"} /></Header>
            <Message color={pathDiagnostic.color} size="small">
              <Message.Header><LocalizedText source={pathDiagnostic.status} /></Message.Header>
              <p><LocalizedText source={pathDiagnostic.message} /></p>
              {pathDiagnostic.mappedPath && (
                <p>
                  <LocalizedText source={"Mapped path:"} />{" "}<code>{pathDiagnostic.mappedPath}</code>
                </p>
              )}
            </Message>
          </Segment>
        )}
      </Card.Content>
    </Card>
  );
};

export default MediaServerPanel;
