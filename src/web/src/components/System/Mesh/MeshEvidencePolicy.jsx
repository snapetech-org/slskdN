import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import {
  evaluateMeshEvidenceEntries,
  formatMeshEvidenceReviewReport,
  getMeshEvidencePolicy,
  getMeshEvidencePolicySummary,
  inboundTrustTiers,
  outboundEvidenceTypes,
  parseMeshEvidenceReviewInput,
  resetMeshEvidencePolicy,
  setMeshEvidenceInboundTrustTier,
  setMeshEvidenceOutboundEnabled,
} from '../../../lib/meshEvidencePolicy';
import React, { useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import {
  Button,
  Checkbox,
  Dropdown,
  Header,
  Icon,
  Label,
  List,
  Message,
  Popup,
  Segment,
  Statistic,
  TextArea,
} from 'semantic-ui-react';

const inboundOptions = inboundTrustTiers.map((tier) => ({
  key: tier.id,
  text: interfaceText(tier.label),
  value: tier.id,
}));

const sampleEvidence = JSON.stringify(
  {
    evidence: [
      {
        confidence: 0.92,
        provenance: {
          peerId: 'fixture-peer',
          realmId: 'fixture-realm',
          signature: 'fixture-signature',
          trustTier: 'realm',
        },
        subject: 'mbid:recording:fixture-track',
        type: 'metadataCorrection',
        witnessCount: 3,
      },
      {
        confidence: 0.82,
        containsPath: true,
        provenance: {
          peerId: 'untrusted-peer',
          signature: 'fixture-signature',
          trustTier: 'untrusted',
        },
        subject: 'private-path-example',
        type: 'releaseCompleteness',
        witnessCount: 1,
      },
    ],
  },
  null,
  2,
);

const MeshEvidencePolicy = () => {
  useInterfaceLanguage();
  const [policy, setPolicy] = useState(getMeshEvidencePolicy);
  const [reviewError, setReviewError] = useState('');
  const [reviewInput, setReviewInput] = useState('');
  const [review, setReview] = useState(null);
  const summary = useMemo(() => getMeshEvidencePolicySummary(policy), [policy]);

  const setInboundTier = (_event, { value }) => {
    setPolicy(setMeshEvidenceInboundTrustTier(value));
    toast.info(interfaceText("Mesh evidence inbound trust policy updated"));
  };

  const toggleOutbound = (evidenceType, enabled) => {
    setPolicy(setMeshEvidenceOutboundEnabled(evidenceType.id, enabled));
    toast.info(
      `${evidenceType.label} publication ${enabled ? 'enabled' : 'disabled'}`,
    );
  };

  const resetPolicy = () => {
    setPolicy(resetMeshEvidencePolicy());
    toast.info(interfaceText("Mesh evidence policy reset to private defaults"));
  };

  const reviewEvidence = () => {
    try {
      const entries = parseMeshEvidenceReviewInput(reviewInput);
      setReview(evaluateMeshEvidenceEntries(entries, policy));
      setReviewError('');
    } catch {
      setReview(null);
      setReviewError(interfaceText('Invalid evidence JSON'));
    }
  };

  const copyReviewReport = async () => {
    if (!review) return;

    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(formatMeshEvidenceReviewReport(review));
      toast.success(interfaceText("Mesh evidence review copied"));
      return;
    }

    toast.info(interfaceText("Clipboard unavailable; select the review results manually"));
  };

  return (
    <Segment className="mesh-evidence-policy">
      <div className="mesh-evidence-policy-header">
        <Header as="h3">
          <Icon name="certificate" />
          <Header.Content>
            <LocalizedText source={"Mesh Evidence Policy"} /><Header.Subheader>
              <LocalizedText source={"Local controls for trusted metadata evidence. Nothing is published unless explicitly enabled here."} /></Header.Subheader>
          </Header.Content>
        </Header>
        <Popup
          content={interfaceText("Reset inbound and outbound mesh evidence controls to private defaults.")}
          position="top center"
          trigger={
            <Button
              aria-label={interfaceText("Reset mesh evidence policy to private defaults")}
              icon="undo"
              onClick={resetPolicy}
             {...interfaceTextProps("Reset mesh evidence policy to private defaults")}/>
          }
         {...interfaceTextProps("Reset inbound and outbound mesh evidence controls to private defaults.")}/>
      </div>

      <Statistic.Group
        size="small"
        widths="three"
      >
        <Statistic color={summary.inboundEnabled ? 'blue' : 'grey'}>
          <Statistic.Value>{summary.inboundEnabled ? <LocalizedText source={"On"} /> : <LocalizedText source={"Off"} />}</Statistic.Value>
          <Statistic.Label><LocalizedText source={"Inbound Evidence"} /></Statistic.Label>
        </Statistic>
        <Statistic color={summary.outboundEnabled ? 'orange' : 'grey'}>
          <Statistic.Value>{summary.enabledOutbound.length}</Statistic.Value>
          <Statistic.Label><LocalizedText source={"Outbound Types"} /></Statistic.Label>
        </Statistic>
        <Statistic color={policy.provenanceRequired ? 'green' : 'red'}>
          <Statistic.Value>
            {policy.provenanceRequired ? <LocalizedText source={"Required"} /> : <LocalizedText source={"Optional"} />}
          </Statistic.Value>
          <Statistic.Label><LocalizedText source={"Provenance"} /></Statistic.Label>
        </Statistic>
      </Statistic.Group>

      <div className="mesh-evidence-policy-grid">
        <Segment>
          <Header as="h4"><LocalizedText source={"Inbound Trust Gate"} /></Header>
          <Dropdown
            aria-label={interfaceText("Mesh evidence inbound trust tier")}
            fluid
            onChange={setInboundTier}
            options={inboundOptions}
            selection
            value={policy.inboundTrustTier}
           {...interfaceTextProps("Mesh evidence inbound trust tier")}/>
          <p className="mesh-evidence-policy-help">
            <LocalizedText source={summary.inboundTier.description} />
          </p>
          <Label color="green">
            <Icon name="lock" />
            <LocalizedText source={"Provenance required"} /></Label>
        </Segment>

        <Segment>
          <Header as="h4"><LocalizedText source={"Outbound Publication"} /></Header>
          <List
            divided
            relaxed
          >
            {outboundEvidenceTypes.map((evidenceType) => {
              const enabled = policy.outbound[evidenceType.id] === true;
              const label = interfaceText(evidenceType.label);
              const actionSource = enabled ? 'Disable {label} publication' : 'Enable {label} publication';
              const detailSource = enabled
                ? 'Disable publication of {label}. This remains local policy state until backend federation is wired.'
                : 'Enable publication of {label}. This remains local policy state until backend federation is wired.';

              return (
                <List.Item key={evidenceType.id}>
                  <List.Content floated="right">
                    <Popup
                      content={<LocalizedText source={detailSource} values={{ label }} />}
                      position="top center"
                      trigger={
                        <Checkbox
                          aria-label={interfaceText(actionSource, { label })}
                          {...interfaceTextProps(actionSource, { label })}
                          checked={enabled}
                          onChange={(_event, { checked }) =>
                            toggleOutbound(evidenceType, checked)
                          }
                          toggle
                        />
                      }
                    />
                  </List.Content>
                  <List.Icon
                    color={enabled ? 'orange' : 'grey'}
                    name={enabled ? 'share alternate' : 'lock'}
                    size="large"
                    verticalAlign="middle"
                  />
                  <List.Content>
                    <List.Header><LocalizedText source={evidenceType.label} /></List.Header>
                    <List.Description>
                      <LocalizedText source={evidenceType.description} />
                    </List.Description>
                  </List.Content>
                </List.Item>
              );
            })}
          </List>
        </Segment>
      </div>

      <Segment className="mesh-evidence-review">
        <Header as="h4">
          <Icon name="search" />
          <LocalizedText source={"Evidence Review Sandbox"} /><Header.Subheader>
            <LocalizedText source={"Paste signed mesh evidence JSON to preview local trust, provenance, k-anonymity, confidence, and privacy gates before anything is applied."} /></Header.Subheader>
        </Header>
        <TextArea
          aria-label={interfaceText("Mesh evidence review JSON")}
          className="mesh-evidence-review-input"
          onChange={(event) => setReviewInput(event.target.value)}
          placeholder={sampleEvidence}
          value={reviewInput}
         {...interfaceTextProps("Mesh evidence review JSON")}/>
        <div className="mesh-evidence-review-actions">
          <Popup
            content={interfaceText("Load a browser-local sample containing one acceptable realm-signed item and one rejected privacy-risk item.")}
            position="top center"
            trigger={
              <Button
                aria-label={interfaceText("Load sample mesh evidence")}
                onClick={() => {
                  setReviewInput(sampleEvidence);
                  setReviewError('');
                }}
               {...interfaceTextProps("Load sample mesh evidence")}>
                <Icon name="flask" />
                <LocalizedText source={"Load Sample"} /></Button>
            }
           {...interfaceTextProps("Load a browser-local sample containing one acceptable realm-signed item and one rejected privacy-risk item.")}/>
          <Popup
            content={interfaceText("Evaluate the pasted evidence locally. This does not publish, query peers, or apply ranking changes.")}
            position="top center"
            trigger={
              <Button
                aria-label={interfaceText("Review mesh evidence locally")}
                disabled={!reviewInput.trim()}
                onClick={reviewEvidence}
                primary
               {...interfaceTextProps("Review mesh evidence locally")}>
                <Icon name="check circle" />
                <LocalizedText source={"Review Evidence"} /></Button>
            }
           {...interfaceTextProps("Evaluate the pasted evidence locally. This does not publish, query peers, or apply ranking changes.")}/>
          <Popup
            content={interfaceText("Copy the current mesh evidence review report.")}
            position="top center"
            trigger={
              <Button
                aria-label={interfaceText("Copy mesh evidence review report")}
                disabled={!review}
                onClick={copyReviewReport}
               {...interfaceTextProps("Copy mesh evidence review report")}>
                <Icon name="copy" />
                <LocalizedText source={"Copy Report"} /></Button>
            }
           {...interfaceTextProps("Copy the current mesh evidence review report.")}/>
        </div>
        {reviewError && (
          <Message
            className="mesh-evidence-review-message"
            negative
          >
            <Message.Header><LocalizedText source={"Invalid evidence JSON"} /></Message.Header>
            <p>{reviewError}</p>
          </Message>
        )}
        {review && (
          <div className="mesh-evidence-review-results">
            <div className="mesh-evidence-review-summary">
              <Label color="blue">
                <LocalizedText source={"Total"} /><Label.Detail>{review.summary.total}</Label.Detail>
              </Label>
              <Label color="green">
                <LocalizedText source={"Accepted"} /><Label.Detail>{review.summary.accepted}</Label.Detail>
              </Label>
              <Label color="red">
                <LocalizedText source={"Rejected"} /><Label.Detail>{review.summary.rejected}</Label.Detail>
              </Label>
            </div>
            <List
              divided
              relaxed
            >
              {review.results.map((entry) => (
                <List.Item key={entry.id}>
                  <List.Icon
                    color={entry.accepted ? 'green' : 'red'}
                    name={entry.accepted ? 'check circle' : 'ban'}
                    size="large"
                    verticalAlign="middle"
                  />
                  <List.Content>
                    <List.Header>
                      {entry.type} · {entry.subject}
                    </List.Header>
                    <List.Description>
                      <LocalizedText source={"Confidence"} />{" "}{entry.confidence}<LocalizedText source={"; witnesses"} />{" "}{entry.witnessCount}<LocalizedText source={"; provenance"} />{" "}{entry.provenance.trustTier}
                      {entry.reasons.length > 0
                        ? `; rejected because ${entry.reasons.join(', ')}`
                        : <LocalizedText source={"; accepted for local use"} />}
                    </List.Description>
                  </List.Content>
                </List.Item>
              ))}
            </List>
          </div>
        )}
      </Segment>
    </Segment>
  );
};

export default MeshEvidencePolicy;
