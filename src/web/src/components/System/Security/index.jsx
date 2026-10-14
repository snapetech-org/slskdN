import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";


import './Security.css';
import * as securityApi from '../../../lib/security';
import AdversarialSettings from './AdversarialSettings';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Button,
  Dimmer,
  Header,
  Icon,
  Loader,
  Message,
  Popup,
  Segment,
  Statistic,
  Tab,
} from 'semantic-ui-react';

const Security = () => {
  useInterfaceLanguage();
  const dashboardLoadedRef = useRef(false);
  const dashboardSignatureRef = useRef(null);
  const fetchInFlightRef = useRef(false);
  const mountedRef = useRef(false);
  const pollIntervalRef = useRef(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async (showRefreshing = false) => {
    if (document.hidden || !mountedRef.current || fetchInFlightRef.current) {
      return;
    }

    fetchInFlightRef.current = true;
    try {
      if (showRefreshing) {
        setRefreshing(true);
      }

      const dashboardData = await securityApi.getDashboard();
      if (!mountedRef.current || document.hidden) return;
      const signature = JSON.stringify(dashboardData ?? null);
      if (dashboardSignatureRef.current !== signature) {
        dashboardSignatureRef.current = signature;
        setDashboard(dashboardData);
      }

      dashboardLoadedRef.current = true;
      setError(null);
    } catch (fetchError) {
      if (!mountedRef.current || document.hidden) return;
      if (!dashboardLoadedRef.current) {
        setError(fetchError.message || interfaceText('Failed to load security data'));
      }
    } finally {
      fetchInFlightRef.current = false;
      if (mountedRef.current && !document.hidden) {
        setLoading(false);
        if (showRefreshing) {
          setRefreshing(false);
        }
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    const stopPolling = () => {
      if (pollIntervalRef.current) {
        window.clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
    const startPolling = () => {
      if (document.hidden || pollIntervalRef.current) return;

      fetchData();
      pollIntervalRef.current = window.setInterval(fetchData, 30_000);
    };
    const handleVisibilityChange = () => {
      if (document.hidden) {
        setRefreshing(false);
        stopPolling();
      } else {
        startPolling();
      }
    };

    startPolling();
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      stopPolling();
    };
  }, [fetchData]);

  if (loading) {
    return (
      <Segment placeholder>
        <Dimmer
          active
          inverted
        >
          <Loader><LocalizedText source={"Loading Security Status..."} /></Loader>
        </Dimmer>
      </Segment>
    );
  }

  if (error && !dashboard) {
    return (
      <Message negative>
        <Message.Header><LocalizedText source={"Security Module Unavailable"} /></Message.Header>
        <p>{error}</p>
        <p><LocalizedText source={"Security features may not be enabled on this server."} /></p>
        <Popup
          content={interfaceText("Try loading the security dashboard again after the service is enabled or the connection recovers.")}
          position="top center"
          trigger={
            <Button
              aria-label={interfaceText("Retry loading the Security dashboard")}
              onClick={() => fetchData(true)}
              size="small"
             {...interfaceTextProps("Retry loading the Security dashboard")}>
              <LocalizedText source={"Retry"} /></Button>
          }
         {...interfaceTextProps("Try loading the security dashboard again after the service is enabled or the connection recovers.")}/>
      </Message>
    );
  }

  const stats = dashboard || {};

  // Check if security is enabled but no data is available yet
  const hasAnyData =
    stats.networkGuardStats ||
    stats.reputationStats ||
    stats.violationStats ||
    stats.eventStats ||
    stats.paranoidStats ||
    stats.honeypotStats ||
    stats.fingerprintStats ||
    stats.canaryStats ||
    stats.entropyStats ||
    stats.consensusStats ||
    stats.verificationStats ||
    stats.disclosureStats ||
    stats.temporalStats;

  if (!hasAnyData) {
    return (
      <Message info>
        <Message.Header>
          <Icon name="info circle" />
          <LocalizedText source={"Security System Active - No Activity Yet"} /></Message.Header>
        <p>
          <LocalizedText source={"The security subsystem is running but hasn't collected data yet. This is normal for:"} /></p>
        <ul>
          <li>
            <strong><LocalizedText source={"Fresh installations"} /></strong> <LocalizedText source={"- Security features need time to observe network activity"} /></li>
          <li>
            <strong><LocalizedText source={"Standalone mode"} /></strong> <LocalizedText source={"- Most security features activate when mesh networking is enabled"} /></li>
          <li>
            <strong><LocalizedText source={"Low traffic"} /></strong> <LocalizedText source={"- Peer reputation, violation tracking, and behavioral analysis require peer interactions"} /></li>
        </ul>
        <p>
          <strong><LocalizedText source={"To activate security features:"} /></strong>
        </p>
        <ol>
          <li><LocalizedText source={"Connect to the Soulseek network (if not already connected)"} /></li>
          <li>
            <LocalizedText source={"Enable mesh networking via DHT/Overlay (check footer for connectivity)"} /></li>
          <li><LocalizedText source={"Wait for peer connections and transfer activity"} /></li>
        </ol>
        <p>
          <LocalizedText source={"Security monitoring will begin automatically once peer activity is detected. Check the"} />{" "}<strong><LocalizedText source={"Mesh"} /></strong> <LocalizedText source={"tab to verify connectivity."} /></p>
        <Popup
          content={interfaceText("Request the latest security snapshot now instead of waiting for the next automatic refresh.")}
          position="top center"
          trigger={
            <Button
              aria-label={interfaceText("Refresh Security status")}
              icon="refresh"
              loading={refreshing}
              onClick={() => fetchData(true)}
              primary
              size="small"
             {...interfaceTextProps("Refresh Security status")}>
              <LocalizedText source={"Refresh Status"} /></Button>
          }
         {...interfaceTextProps("Request the latest security snapshot now instead of waiting for the next automatic refresh.")}/>
      </Message>
    );
  }

  const panes = [
    {
      menuItem: {
        content: interfaceText("Status"),
        icon: 'shield alternate',
        key: 'status',
      },
      render: () => (
        <Tab.Pane>
          <div className="security-dashboard">
            <div className="security-header">
              <Header as="h3">
                <Icon name="shield alternate" />
                <Header.Content>
                  <LocalizedText source={"Security Status"} /><Header.Subheader>
                    <LocalizedText source={"Real-time security monitoring"} /></Header.Subheader>
                </Header.Content>
              </Header>
              <Popup
                content={interfaceText("Request the latest security snapshot now to check recent network activity.")}
                position="top center"
                trigger={
                  <Button
                    aria-label={interfaceText("Refresh the security dashboard")}
                    icon="refresh"
                    loading={refreshing}
                    onClick={() => fetchData(true)}
                    size="tiny"
                    title={interfaceText("Refresh")}
                   {...interfaceTextProps("Refresh the security dashboard")}/>
                }
               {...interfaceTextProps("Request the latest security snapshot now to check recent network activity.")}/>
            </div>

            <Statistic.Group
              className="security-summary-stats"
              size="small"
              widths={4}
            >
              <Statistic color="blue">
                <Statistic.Value>
                  {stats.networkGuardStats?.globalConnections ?? 0}
                </Statistic.Value>
                <Statistic.Label><LocalizedText source={"Active Connections"} /></Statistic.Label>
              </Statistic>
              <Statistic color="teal">
                <Statistic.Value>
                  {stats.reputationStats?.totalPeers ?? 0}
                </Statistic.Value>
                <Statistic.Label><LocalizedText source={"Tracked Peers"} /></Statistic.Label>
              </Statistic>
              <Statistic color="orange">
                <Statistic.Value>
                  {stats.violationStats?.trackedIps ?? 0}
                </Statistic.Value>
                <Statistic.Label><LocalizedText source={"Tracked Violators"} /></Statistic.Label>
              </Statistic>
              <Statistic color="green">
                <Statistic.Value>
                  {stats.eventStats?.totalEvents ?? 0}
                </Statistic.Value>
                <Statistic.Label><LocalizedText source={"Security Events"} /></Statistic.Label>
              </Statistic>
            </Statistic.Group>

            <Segment>
              <Header as="h4">
                <Icon name="info circle" />
                <LocalizedText source={"Security Overview"} /></Header>
              <p>
                <strong><LocalizedText source={"Network Guard:"} /></strong> <LocalizedText source={"Rate limiting and connection caps are"} />{" "}{stats.networkGuardStats ? <LocalizedText source={"active"} /> : <LocalizedText source={"inactive"} />}.
              </p>
              <p>
                <strong><LocalizedText source={"Peer Reputation:"} /></strong>{' '}
                {stats.reputationStats?.trustedPeers ?? 0} <LocalizedText source={"trusted,"} />{' '}
                {stats.reputationStats?.untrustedPeers ?? 0} <LocalizedText source={"untrusted peers."} /></p>
              <p>
                <strong><LocalizedText source={"Violations:"} /></strong>{' '}
                {stats.violationStats?.trackedIps ?? 0} <LocalizedText source={"IPs,"} />{' '}
                {stats.violationStats?.trackedUsernames ?? 0} <LocalizedText source={"usernames tracked."} /></p>
              <p>
                <strong><LocalizedText source={"Crypto Health:"} /></strong> <LocalizedText source={"Entropy checks:"} />{' '}
                {stats.entropyStats?.checkCount ?? 0}<LocalizedText source={", Warnings:"} />{' '}
                {stats.entropyStats?.warningCount ?? 0}
              </p>
            </Segment>
          </div>
        </Tab.Pane>
      ),
    },
    {
      menuItem: {
        content: interfaceText("Adversarial"),
        icon: 'user secret',
        key: 'adversarial',
      },
      render: () => (
        <Tab.Pane>
          <AdversarialSettings />
        </Tab.Pane>
      ),
    },
  ];

  return (
    <Tab
      activeIndex={activeIndex}
      onTabChange={(_event, { activeIndex: nextIndex }) =>
        setActiveIndex(nextIndex)
      }
      panes={panes}
    />
  );
};

export default Security;
