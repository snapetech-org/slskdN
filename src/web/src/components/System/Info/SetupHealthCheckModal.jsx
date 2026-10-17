import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import {
  buildSetupHealthChecks,
  formatSetupHealthReport,
} from '../../../lib/setupHealthCheck';
import React, { useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import {
  Button,
  Header,
  Icon,
  Label,
  List,
  Message,
  Modal,
  Popup,
  Statistic,
} from 'semantic-ui-react';

const statusColors = {
  fail: 'red',
  pass: 'green',
  warn: 'yellow',
};

const statusIcons = {
  fail: 'warning sign',
  pass: 'check circle',
  warn: 'exclamation triangle',
};

const copyToClipboard = async (value) => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return true;
  }

  return false;
};

const LocalizedSetupHealthEvidence = ({ source }) => {
  const patterns = [
    [/^(\d+) share entry visible in options\.$/, "{count} share entry visible in options."],
    [/^(\d+) share entries visible in options\.$/, "{count} share entries visible in options."],
    [/^(\d+) enabled provider credential gap found\.$/, "{count} enabled provider credential gap found."],
    [/^(\d+) enabled provider credential gaps found\.$/, "{count} enabled provider credential gaps found."],
    [/^(\d+) active queued transfer item visible in state\.$/, "{count} active queued transfer item visible in state."],
    [/^(\d+) active queued transfer items visible in state\.$/, "{count} active queued transfer items visible in state."],
    [/^(\d+) failed job entry visible in state\.$/, "{count} failed job entry visible in state."],
    [/^(\d+) failed job entries visible in state\.$/, "{count} failed job entries visible in state."],
    [/^(\d+) automation recipe entry visible in state\.$/, "{count} automation recipe entry visible in state."],
    [/^(\d+) automation recipe entries visible in state\.$/, "{count} automation recipe entries visible in state."],
  ];
  for (const [pattern, template] of patterns) {
    const match = source.match(pattern);
    if (match) return <LocalizedText source={template} values={{ count: match[1] }} />;
  }
  const urlMatch = source.match(/^Configured URL base: (.*)$/);
  if (urlMatch) return <LocalizedText source="Configured URL base: {urlBase}" values={{ urlBase: urlMatch[1] }} />;
  return <LocalizedText source={source} />;
};

const LocalizedSetupHealthAction = ({ source }) => {
  const providerMatch = source.match(/^Add credentials or disable: (.*)\.$/);
  if (providerMatch) return <LocalizedText source="Add credentials or disable: {providers}." values={{ providers: providerMatch[1] }} />;
  return <LocalizedText source={source} />;
};

const SetupHealthCheckModal = ({ options = {}, state = {} }) => {
  useInterfaceLanguage();
  const [activeGroup, setActiveGroup] = useState('All');
  const [open, setOpen] = useState(false);
  const summary = useMemo(
    () =>
      buildSetupHealthChecks({
        options,
        state,
      }),
    [options, state],
  );
  const report = useMemo(() => formatSetupHealthReport(summary), [summary]);
  const groupNames = useMemo(
    () => ['All', ...Object.keys(summary.groups).sort()],
    [summary.groups],
  );
  const visibleChecks = useMemo(
    () =>
      activeGroup === 'All'
        ? summary.checks
        : summary.checks.filter((item) => item.group === activeGroup),
    [activeGroup, summary.checks],
  );

  const copyReport = async () => {
    const copied = await copyToClipboard(report);

    if (copied) {
      toast.success(interfaceText("Setup health report copied"));
      return;
    }

    toast.info(interfaceText("Select the setup health report text to copy it manually"));
  };

  return (
    <>
      <Popup
        content={interfaceText("Open a mobile-friendly setup health check for connection, identity, shares, downloads, restart, URL base, and remote-configuration readiness.")}
        position="top center"
        trigger={
          <Button
            aria-label={interfaceText("Open setup health check")}
            icon
            onClick={() => setOpen(true)}
           {...interfaceTextProps("Open setup health check")}>
            <Icon name="heartbeat" />
            <LocalizedText source={"Setup Health"} /></Button>
        }
       {...interfaceTextProps("Open a mobile-friendly setup health check for connection, identity, shares, downloads, restart, URL base, and remote-configuration readiness.")}/>
      <Modal
        centered={false}
        closeIcon
        onClose={() => setOpen(false)}
        open={open}
        size="large"
      >
        <Modal.Header>
          <Icon name="heartbeat" />
          <LocalizedText source={"Setup Health"} /></Modal.Header>
        <Modal.Content>
          <Message
            className="setup-health-summary"
            color={summary.totals.fail ? 'red' : summary.totals.warn ? 'yellow' : 'green'}
          >
            <Message.Header><LocalizedText source={summary.readiness} /></Message.Header>
            <p>
              <LocalizedText source={"This wizard uses the options and state already loaded in this browser. It does not contact peers, validate credentials, scan folders, retry jobs, or mutate configuration."} /></p>
          </Message>
          <Statistic.Group
            className="setup-health-stats"
            size="small"
          >
            <Statistic color={summary.totals.fail ? 'red' : summary.totals.warn ? 'yellow' : 'green'}>
              <Statistic.Value>{summary.score}</Statistic.Value>
              <Statistic.Label><LocalizedText source={"Score"} /></Statistic.Label>
            </Statistic>
            <Statistic color="green">
              <Statistic.Value>{summary.totals.pass}</Statistic.Value>
              <Statistic.Label><LocalizedText source={"Pass"} /></Statistic.Label>
            </Statistic>
            <Statistic color="yellow">
              <Statistic.Value>{summary.totals.warn}</Statistic.Value>
              <Statistic.Label><LocalizedText source={"Warn"} /></Statistic.Label>
            </Statistic>
            <Statistic color="red">
              <Statistic.Value>{summary.totals.fail}</Statistic.Value>
              <Statistic.Label><LocalizedText source={"Fail"} /></Statistic.Label>
            </Statistic>
          </Statistic.Group>
          {summary.nextSteps.length > 0 && (
            <Message warning>
              <Message.Header><LocalizedText source={"Next Steps"} /></Message.Header>
              <List bulleted>
                {summary.nextSteps.map((item) => (
                  <List.Item key={`${item.group}-${item.area}`}>
                    <strong><LocalizedText source={item.area} />:</strong> <LocalizedSetupHealthAction source={item.action} />
                  </List.Item>
                ))}
              </List>
            </Message>
          )}
          <div className="setup-health-filter-row">
            {groupNames.map((group) => {
              const groupSummary = summary.groups[group];
              const label =
                group === 'All'
                  ? `${summary.checks.length}`
                  : `${groupSummary.fail}/${groupSummary.warn}/${groupSummary.pass}`;

              return (
                <Popup
                  content={
                    group === 'All'
                      ? interfaceText("Show every diagnostic check.")
                      : interfaceText("Show {group} checks. Label is fail/warn/pass.", { group: interfaceText(group) })
                  }
                  key={group}
                  position="top center"
                  trigger={
                    <Button
                      aria-label={interfaceText("Show {group} setup health checks", { group: interfaceText(group) })}
                      basic={activeGroup !== group}
                      onClick={() => setActiveGroup(group)}
                      size="small"
                     {...interfaceTextProps("Show {group} setup health checks")}>
                      <LocalizedText source={group} />
                      <Label circular>{label}</Label>
                    </Button>
                  }
                />
              );
            })}
          </div>
          <div className="setup-health-grid">
            {visibleChecks.map((item) => (
              <section
                className={`setup-health-card setup-health-card-${item.status}`}
                key={item.area}
              >
                <div className="setup-health-card-head">
                  <Header
                    as="h4"
                    className="setup-health-card-title"
                  >
                    <Icon name={statusIcons[item.status]} />
                    <Header.Content><LocalizedText source={item.area} /></Header.Content>
                  </Header>
                  <Label color={statusColors[item.status]}>
                    <LocalizedText source={item.status.toUpperCase()} />
                  </Label>
                </div>
                <p className="setup-health-card-summary"><LocalizedText source={item.summary} /></p>
                <p className="setup-health-card-group"><LocalizedText source={item.group} /></p>
                <p className="setup-health-card-evidence"><LocalizedSetupHealthEvidence source={item.evidence} /></p>
                <p className="setup-health-card-action"><LocalizedSetupHealthAction source={item.action} /></p>
              </section>
            ))}
          </div>
        </Modal.Content>
        <Modal.Actions>
          <Popup
            content={interfaceText("Copy the setup health check report for support or your own setup notes.")}
            position="top center"
            trigger={
              <Button
                aria-label={interfaceText("Copy setup health report")}
                onClick={copyReport}
                primary
               {...interfaceTextProps("Copy setup health report")}>
                <Icon name="copy" />
                <LocalizedText source={"Copy Report"} /></Button>
            }
           {...interfaceTextProps("Copy the setup health check report for support or your own setup notes.")}/>
          <Popup
            content={interfaceText("Close the setup health check.")}
            position="top center"
            trigger={
              <Button
                aria-label={interfaceText("Close setup health check")}
                onClick={() => setOpen(false)}
               {...interfaceTextProps("Close setup health check")}>
                <LocalizedText source={"Close"} /></Button>
            }
           {...interfaceTextProps("Close the setup health check.")}/>
        </Modal.Actions>
      </Modal>
    </>
  );
};

export default SetupHealthCheckModal;
