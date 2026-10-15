import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';


import { urlBase } from '../../config';
import * as pods from '../../lib/pods';
import * as portForwarding from '../../lib/portForwarding';
import React, { Component } from 'react';
import { TooltipButton } from '../Shared';
import {
  Button,
  Card,
  Dimmer,
  Dropdown,
  Form,
  Icon,
  Input,
  Label,
  List,
  Loader,
  Message,
  Modal,
  Popup,
  Segment,
  Statistic,
  Tab,
  Table,
} from 'semantic-ui-react';

const initialState = {
  activeTab: 0,
  availablePortCount: 0,
  availablePorts: [],
  availablePortsLoaded: false,
  createForm: {
    destinationHost: '',
    destinationPort: '',
    localPort: '',
    serviceName: '',
  },
  creatingForwarding: false,
  error: null,
  forwardingStatus: [],
  loading: false,
  pods: [],
  selectedPodDetail: null,
  selectedPodId: null,
  showCreateModal: false,
  stoppingForwarding: false,
  success: null,
  vpnPodMembers: {},
  vpnPodMembersLoaded: false,
};

const AVAILABLE_PORT_PREVIEW_LIMIT = 100;
const STATUS_POLL_INTERVAL_MS = 10_000;
const asArray = (value) => (Array.isArray(value) ? value : []);
const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);
const PortForwardingError = ({ error }) => {
  if (typeof error === 'string') return <LocalizedText source={error} />;
  if (error?.source) return <LocalizedText source={error.source} values={error.values} />;
  return error?.message || String(error);
};
const forwardingStatusSignature = (statuses) =>
  statuses
    .map((status) =>
      [
        status.activeConnections,
        status.bytesForwarded,
        status.destinationHost,
        status.destinationPort,
        status.isActive,
        status.localPort,
        status.performance?.averageBytesPerConnection,
        status.performance?.isHighThroughput,
        status.podId,
        status.serviceName,
        status.streamMappingEnabled,
      ].join('\u0001'))
    .sort()
    .join('\u0002');

class PortForwarding extends Component {
  availablePortsRequest = null;
  initialized = false;
  mounted = false;
  statusInterval = null;
  statusRequest = null;
  vpnPodMembersRequest = null;

  constructor(props) {
    super(props);
    this.state = initialState;
  }

  componentDidMount() {
    this.mounted = true;
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
    if (!document.hidden) {
      this.initializeComponent();
      this.startStatusPolling();
    }
  }

  componentWillUnmount() {
    this.mounted = false;
    this.stopStatusPolling();
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
  }

  startStatusPolling = () => {
    if (document.hidden || this.statusInterval) return;
    this.statusInterval = window.setInterval(
      this.fetchForwardingStatus,
      STATUS_POLL_INTERVAL_MS,
    );
  };

  stopStatusPolling = () => {
    if (!this.statusInterval) return;
    window.clearInterval(this.statusInterval);
    this.statusInterval = null;
  };

  handleVisibilityChange = () => {
    if (document.hidden) {
      this.stopStatusPolling();
      return;
    }

    if (!this.initialized) {
      this.initializeComponent();
    } else {
      this.fetchForwardingStatus();
    }
    this.startStatusPolling();
  };

  initializeComponent = async () => {
    this.initialized = true;
    this.setState({ error: null, loading: true });

    try {
      await Promise.all([
        this.fetchPods(),
        this.fetchForwardingStatus(),
      ]);
    } catch (error) {
      console.error('Failed to initialize port forwarding:', error);
      if (this.mounted) this.setState({ error: { message: getApiErrorMessage(error, { t: interfaceText }) } });
    } finally {
      if (this.mounted) this.setState({ loading: false });
    }
  };

  fetchPods = async () => {
    try {
      const podsList = await pods.list();
      if (this.mounted) {
        this.setState({ pods: asArray(podsList).filter(isObject) });
      }
    } catch (error) {
      console.error('Failed to fetch pods:', error);
      if (this.mounted) this.setState({ pods: [] });
    }
  };

  fetchAvailablePorts = async () => {
    if (this.availablePortsRequest) return this.availablePortsRequest;
    this.availablePortsRequest = (async () => {
      try {
        const result = await portForwarding.getAvailablePorts(
          1_024,
          65_535,
          AVAILABLE_PORT_PREVIEW_LIMIT,
        );
        if (!this.mounted) return;
        const availablePorts = asArray(result?.availablePorts);
        this.setState({
          availablePortCount: Number.isFinite(result?.availablePortCount)
            ? result.availablePortCount
            : availablePorts.length,
          availablePorts,
          availablePortsLoaded: true,
        });
      } catch (error) {
        console.error('Failed to fetch available ports:', error);
      }
    })().finally(() => {
      this.availablePortsRequest = null;
    });
    return this.availablePortsRequest;
  };

  fetchForwardingStatus = async () => {
    if (this.statusRequest) return this.statusRequest;
    this.statusRequest = (async () => {
      try {
        const status = asArray(await portForwarding.getForwardingStatus())
          .filter(isObject);
        if (!this.mounted) return;
        this.setState((previous) =>
          forwardingStatusSignature(previous.forwardingStatus) ===
          forwardingStatusSignature(status)
            ? null
            : { forwardingStatus: status });
      } catch (error) {
        console.error('Failed to fetch forwarding status:', error);
      }
    })().finally(() => {
      this.statusRequest = null;
    });
    return this.statusRequest;
  };

  fetchVpnPodMembers = async () => {
    if (this.vpnPodMembersRequest) return this.vpnPodMembersRequest;
    const podList = this.state.pods;
    const vpnCapablePods = podList.filter(
      (pod) =>
        pod.capabilities?.includes('PrivateServiceGateway') ||
        pod.privateServicePolicy?.enabled === true,
    );

    this.vpnPodMembersRequest = Promise.all(
      vpnCapablePods.map(async (pod) => {
        try {
          return [pod.podId, asArray(await pods.getMembers(pod.podId)).length];
        } catch (error) {
          console.error(`Failed to fetch members for pod ${pod.podId}:`, error);
          return [pod.podId, null];
        }
      }),
    )
      .then((entries) => {
        if (!this.mounted) return;
        this.setState({
          vpnPodMembers: Object.fromEntries(entries),
          vpnPodMembersLoaded: true,
        });
      })
      .finally(() => {
        this.vpnPodMembersRequest = null;
      });
    return this.vpnPodMembersRequest;
  };

  refreshForwardingStatusAfterMutation = async () => {
    if (this.statusRequest) await this.statusRequest;
    return this.fetchForwardingStatus();
  };

  refreshAvailablePortsAfterMutation = async () => {
    if (!this.state.availablePortsLoaded) return;
    if (this.availablePortsRequest) await this.availablePortsRequest;
    return this.fetchAvailablePorts();
  };

  handleTabChange = (_event, { activeIndex }) => {
    this.setState({ activeTab: activeIndex }, () => {
      if (activeIndex === 1 && !this.state.availablePortsLoaded) {
        this.fetchAvailablePorts();
      } else if (activeIndex === 3 && !this.state.vpnPodMembersLoaded) {
        this.fetchVpnPodMembers();
      }
    });
  };

  handlePodSelection = async (podId) => {
    this.setState({
      loading: true,
      selectedPodDetail: null,
      selectedPodId: podId,
    });

    try {
      const podDetail = await pods.get(podId);
      this.setState({ selectedPodDetail: podDetail });
    } catch (error) {
      console.error('Failed to fetch pod detail:', error);
      this.setState({
        error: {
          source: 'Failed to load pod details: {message}',
          values: { message: getApiErrorMessage(error, { t: interfaceText }) },
        },
      });
    } finally {
      this.setState({ loading: false });
    }
  };

  handleCreateForwarding = async () => {
    const { createForm, selectedPodId } = this.state;

    if (!selectedPodId) {
      this.setState({ error: 'Please select a pod first' });
      return;
    }

    // Validate form
    if (
      !createForm.localPort ||
      !createForm.destinationHost ||
      !createForm.destinationPort
    ) {
      this.setState({ error: 'Please fill in all required fields' });
      return;
    }

    const localPort = Number.parseInt(createForm.localPort);
    const destinationPort = Number.parseInt(createForm.destinationPort);

    if (isNaN(localPort) || localPort < 1_024 || localPort > 65_535) {
      this.setState({ error: 'Local port must be between 1024 and 65535' });
      return;
    }

    if (
      isNaN(destinationPort) ||
      destinationPort < 1 ||
      destinationPort > 65_535
    ) {
      this.setState({ error: 'Destination port must be between 1 and 65535' });
      return;
    }

    this.setState({ creatingForwarding: true, error: null });

    try {
      await portForwarding.startForwarding({
        destinationHost: createForm.destinationHost,
        destinationPort,
        localPort,
        podId: selectedPodId,
        serviceName: createForm.serviceName || undefined,
      });

      // Reset form and refresh status
      this.setState({
        createForm: initialState.createForm,
        showCreateModal: false,
      });

      await Promise.all([
        this.refreshAvailablePortsAfterMutation(),
        this.refreshForwardingStatusAfterMutation(),
      ]);
    } catch (error) {
      console.error('Failed to create port forwarding:', error);
      this.setState({ error: { message: getApiErrorMessage(error, { t: interfaceText }) } });
    } finally {
      this.setState({ creatingForwarding: false });
    }
  };

  handleStopForwarding = async (localPort) => {
    this.setState({ error: null, stoppingForwarding: true, success: null });

    try {
      await portForwarding.stopForwarding(localPort);
      await Promise.all([
        this.refreshAvailablePortsAfterMutation(),
        this.refreshForwardingStatusAfterMutation(),
      ]);
      this.setState({
        success: {
          source: 'Successfully stopped forwarding on port {port}',
          values: { port: localPort },
        },
      });
    } catch (error) {
      console.error('Failed to stop port forwarding:', error);
      this.setState({ error: { message: getApiErrorMessage(error, { t: interfaceText }) } });
    } finally {
      this.setState({ stoppingForwarding: false });
    }
  };

  handleFormChange = (field, value) => {
    this.setState((previousState) => ({
      createForm: {
        ...previousState.createForm,
        [field]: value,
      },
    }));
  };

  render() {
    const {
      availablePortCount,
      availablePorts,
      createForm,
      creatingForwarding,
      error,
      forwardingStatus,
      loading,
      pods,
      selectedPodDetail,
      selectedPodId,
      showCreateModal,
      stoppingForwarding,
      success,
      vpnPodMembers,
    } = this.state;

    // Filter pods that have VPN gateway capability
    const vpnCapablePods = pods.filter(
      (pod) =>
        pod.capabilities?.includes('PrivateServiceGateway') ||
        pod.privateServicePolicy?.enabled === true,
    );
    const vpnPodStatus = Object.fromEntries(
      vpnCapablePods.map((pod) => {
        const rules = forwardingStatus.filter((rule) => rule.podId === pod.podId);
        return [
          pod.podId,
          {
            activeTunnels: rules.filter((rule) => rule.isActive).length,
            members: vpnPodMembers[pod.podId],
            name: pod.name || pod.podId,
            podId: pod.podId,
            status: pod.privateServicePolicy?.enabled ? 'Active' : 'Inactive',
            totalBandwidth: rules.reduce(
              (total, rule) => total + (rule.bytesForwarded || 0),
              0,
            ),
          },
        ];
      }),
    );

    const panes = [
      {
        menuItem: 'Active Forwarding',
        render: () => (
          <Tab.Pane>
            {forwardingStatus.length === 0 ? (
              <Segment placeholder>
                <Icon name="exchange" />
                <h3><LocalizedText source={"No active port forwarding"} /></h3>
                <p>
                  <LocalizedText source={"Start forwarding local ports to remote services through VPN tunnels."} /></p>
                <TooltipButton
                  disabled={vpnCapablePods.length === 0}
                  onClick={() => this.setState({ showCreateModal: true })}
                  primary
                  tooltip="Open the setup form to route a local app through a VPN-capable pod to a remote service. A pod must be available first."
                >
                  <LocalizedText source={"Start Forwarding"} /></TooltipButton>
              </Segment>
            ) : (
              <div>
                <div style={{ marginBottom: '20px', textAlign: 'right' }}>
                  <TooltipButton
                    disabled={vpnCapablePods.length === 0}
                    onClick={() => this.setState({ showCreateModal: true })}
                    primary
                    tooltip="Open the setup form for a loopback-only port forward through a VPN-capable pod. Use it to reach a remote service from an app on this machine."
                  >
                    <Icon name="plus" />
                    <LocalizedText source={"Add Forwarding"} /></TooltipButton>
                </div>

                <Table celled>
                  <Table.Header>
                    <Table.Row>
                      <Table.HeaderCell><LocalizedText source={"Local Port"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Pod"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Remote Service"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Status"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Connections"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Data Transferred"} /></Table.HeaderCell>
                      <Table.HeaderCell><LocalizedText source={"Actions"} /></Table.HeaderCell>
                    </Table.Row>
                  </Table.Header>
                  <Table.Body>
                    {forwardingStatus.map((forwarding) => (
                      <Table.Row key={forwarding.localPort}>
                        <Table.Cell>
                          <code>localhost:{forwarding.localPort}</code>
                        </Table.Cell>
                        <Table.Cell>
                          {forwarding.podId}
                          {forwarding.serviceName && (
                            <div style={{ color: 'var(--slskd-color-subtle, #666)', fontSize: '0.8em' }}>
                              <LocalizedText source={"Service:"} />{" "}{forwarding.serviceName}
                            </div>
                          )}
                        </Table.Cell>
                        <Table.Cell>
                          <code>
                            {forwarding.destinationHost}:
                            {forwarding.destinationPort}
                          </code>
                        </Table.Cell>
                        <Table.Cell>
                          <Label color={forwarding.isActive ? 'green' : 'red'}>
                            {forwarding.isActive ? <LocalizedText source={"Active"} /> : <LocalizedText source={"Inactive"} />}
                          </Label>
                        </Table.Cell>
                        <Table.Cell>{forwarding.activeConnections}</Table.Cell>
                        <Table.Cell>
                          {forwarding.bytesForwarded > 0
                            ? `${(forwarding.bytesForwarded / 1_024).toFixed(1)} KB`
                            : <LocalizedText source={"0 KB"} />}
                        </Table.Cell>
                        <Table.Cell>
                          <Popup
                            content={interfaceText("Stop forwarding on localhost:{localPort} and close this tunnel when you no longer need the local route.", { "localPort": (forwarding.localPort) })}
                            trigger={
                              <Button
                                aria-label={interfaceText("Stop forwarding on local port {localPort}", { "localPort": (forwarding.localPort) })}
                                color="red"
                                icon="stop"
                                loading={stoppingForwarding}
                                onClick={() =>
                                  this.handleStopForwarding(
                                    forwarding.localPort,
                                  )
                                }
                                size="small"
                               {...interfaceTextProps("Stop forwarding on local port {localPort}")}/>
                            }
                           {...interfaceTextProps("Stop forwarding on localhost:{localPort} and close this tunnel when you no longer need the local route.")}/>
                        </Table.Cell>
                      </Table.Row>
                    ))}
                  </Table.Body>
                </Table>
              </div>
            )}
          </Tab.Pane>
        ),
      },
      {
        menuItem: 'Available Ports',
        render: () => (
          <Tab.Pane>
            <div style={{ marginBottom: '20px' }}>
              <Statistic.Group size="small">
                <Statistic>
                  <Statistic.Value>{availablePortCount}</Statistic.Value>
                  <Statistic.Label><LocalizedText source={"Available Ports"} /></Statistic.Label>
                </Statistic>
                <Statistic>
                  <Statistic.Value>{forwardingStatus.length}</Statistic.Value>
                  <Statistic.Label><LocalizedText source={"In Use"} /></Statistic.Label>
                </Statistic>
              </Statistic.Group>
            </div>

            <Segment>
              <p><LocalizedText source={"Available ports for forwarding (1024-65535):"} /></p>
              <div
                style={{
                  backgroundColor: 'var(--slskd-color-inset, #f8f9fa)',
                  borderRadius: '4px',
                  fontFamily: 'monospace',
                  fontSize: '12px',
                  maxHeight: '400px',
                  overflowY: 'auto',
                  padding: '10px',
                }}
              >
                {availablePorts.length > 0 ? (
                  availablePorts.join(', ') +
                  (availablePortCount > availablePorts.length
                    ? ` ... (+${availablePortCount - availablePorts.length} more)`
                    : '')
                ) : (
                  <em><LocalizedText source={"No ports available or still loading..."} /></em>
                )}
              </div>
            </Segment>
          </Tab.Pane>
        ),
      },
      {
        menuItem: 'Tunnel Statistics',
        render: () => (
          <Tab.Pane>
            <div style={{ marginBottom: '20px' }}>
              <Statistic.Group widths="four">
                <Statistic>
                  <Statistic.Value>
                    {forwardingStatus.filter((status) => status.isActive).length}
                  </Statistic.Value>
                  <Statistic.Label><LocalizedText source={"Active Tunnels"} /></Statistic.Label>
                </Statistic>
                <Statistic>
                  <Statistic.Value>
                    {forwardingStatus.reduce(
                      (sum, status) => sum + (status.activeConnections || 0),
                      0,
                    )}
                  </Statistic.Value>
                  <Statistic.Label><LocalizedText source={"Total Connections"} /></Statistic.Label>
                </Statistic>
                <Statistic>
                  <Statistic.Value>
                    {(
                      forwardingStatus.reduce(
                        (sum, status) => sum + (status.bytesForwarded || 0),
                        0,
                      ) /
                      1_024 /
                      1_024
                    ).toFixed(2)}{' '}
                    MB
                  </Statistic.Value>
                  <Statistic.Label><LocalizedText source={"Data Transferred"} /></Statistic.Label>
                </Statistic>
                <Statistic>
                  <Statistic.Value>
                    {forwardingStatus.filter(
                      (status) => status.performance?.isHighThroughput,
                    ).length}
                  </Statistic.Value>
                  <Statistic.Label><LocalizedText source={"High Throughput"} /></Statistic.Label>
                </Statistic>
              </Statistic.Group>
            </div>

            <Table celled>
              <Table.Header>
                <Table.Row>
                  <Table.HeaderCell><LocalizedText source={"Local Port"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Data Transferred"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Connections"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Average / Connection"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Stream Mapping"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Throughput"} /></Table.HeaderCell>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {forwardingStatus.map((forwarding) => (
                  <Table.Row key={forwarding.localPort}>
                    <Table.Cell>
                      <code>localhost:{forwarding.localPort}</code>
                    </Table.Cell>
                    <Table.Cell>
                      {`${((forwarding.bytesForwarded || 0) / 1_024).toFixed(1)} KB`}
                    </Table.Cell>
                    <Table.Cell>{forwarding.activeConnections || 0}</Table.Cell>
                    <Table.Cell>
                      {`${((forwarding.performance?.averageBytesPerConnection || 0) / 1_024).toFixed(1)} KB`}
                    </Table.Cell>
                    <Table.Cell>
                      <Label color={forwarding.streamMappingEnabled ? 'green' : 'grey'}>
                        {forwarding.streamMappingEnabled ? <LocalizedText source={"Enabled"} /> : <LocalizedText source={"Disabled"} />}
                      </Label>
                    </Table.Cell>
                    <Table.Cell>
                      {forwarding.performance?.isHighThroughput ? <LocalizedText source={"High"} /> : <LocalizedText source={"Normal"} />}
                    </Table.Cell>
                  </Table.Row>
                ))}
                {forwardingStatus.length === 0 && (
                  <Table.Row>
                    <Table.Cell
                      colSpan={6}
                      textAlign="center"
                    >
                      <LocalizedText source={"No active tunnels to display statistics for"} /></Table.Cell>
                  </Table.Row>
                )}
              </Table.Body>
            </Table>
          </Tab.Pane>
        ),
      },
      {
        menuItem: 'VPN Pods',
        render: () => (
          <Tab.Pane>
            <div style={{ marginBottom: '20px' }}>
              <Statistic.Group widths="three">
                <Statistic>
                  <Statistic.Value>
                    {Object.keys(vpnPodStatus).length}
                  </Statistic.Value>
                  <Statistic.Label><LocalizedText source={"VPN-Capable Pods"} /></Statistic.Label>
                </Statistic>
                <Statistic>
                  <Statistic.Value>
                    {Object.values(vpnPodStatus).reduce(
                      (sum, pod) => sum + (pod.members || 0),
                      0,
                    )}
                  </Statistic.Value>
                  <Statistic.Label><LocalizedText source={"Total Members"} /></Statistic.Label>
                </Statistic>
                <Statistic>
                  <Statistic.Value>
                    {Object.values(vpnPodStatus).reduce(
                      (sum, pod) => sum + pod.activeTunnels,
                      0,
                    )}
                  </Statistic.Value>
                  <Statistic.Label><LocalizedText source={"Active Tunnels"} /></Statistic.Label>
                </Statistic>
              </Statistic.Group>
            </div>

            <Table celled>
              <Table.Header>
                <Table.Row>
                  <Table.HeaderCell><LocalizedText source={"Pod Name"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Members"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Active Tunnels"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Data Transferred"} /></Table.HeaderCell>
                  <Table.HeaderCell><LocalizedText source={"Status"} /></Table.HeaderCell>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {Object.values(vpnPodStatus).map((pod) => (
                  <Table.Row key={pod.podId}>
                    <Table.Cell>
                      <strong>{pod.name}</strong>
                      <div style={{ color: 'var(--slskd-color-subtle, #666)', fontSize: '0.8em' }}>
                        ID: {pod.podId}
                      </div>
                    </Table.Cell>
                    <Table.Cell>{pod.members ?? <LocalizedText source="Unavailable" />}</Table.Cell>
                    <Table.Cell>{pod.activeTunnels}</Table.Cell>
                    <Table.Cell>
                      {pod.totalBandwidth > 0
                        ? `${(pod.totalBandwidth / 1_024 / 1_024).toFixed(2)} MB`
                        : <LocalizedText source={"0 MB"} />}
                    </Table.Cell>
                    <Table.Cell>
                      <Label color={pod.status === 'Active' ? 'green' : 'grey'}>
                        <LocalizedText source={pod.status} />
                      </Label>
                    </Table.Cell>
                  </Table.Row>
                ))}
                {Object.keys(vpnPodStatus).length === 0 && (
                  <Table.Row>
                    <Table.Cell
                      colSpan={5}
                      textAlign="center"
                    >
                      <LocalizedText source={"No VPN-capable pods found"} /></Table.Cell>
                  </Table.Row>
                )}
              </Table.Body>
            </Table>
          </Tab.Pane>
        ),
      },
    ];

    return (
      <div style={{ padding: '20px' }}>
        <Dimmer active={loading}>
          <Loader />
        </Dimmer>

        <div style={{ marginBottom: '30px' }}>
          <h2><LocalizedText source={"Port Forwarding"} /></h2>
          <p>
            <LocalizedText source={"Forward local ports to remote services through secure VPN tunnels."} /></p>
        </div>

        {error && (
          <Message error>
            <Message.Header><LocalizedText source={"Error"} /></Message.Header>
            <p><PortForwardingError error={error} /></p>
            <TooltipButton
              onClick={() => this.setState({ error: null })}
              size="small"
              tooltip="Dismiss this error message. It does not change forwarding or configuration."
            >
              <LocalizedText source={"Dismiss"} /></TooltipButton>
          </Message>
        )}

        {success && (
          <Message success>
            <Message.Header><LocalizedText source={"Success"} /></Message.Header>
            <p><LocalizedText source={success.source} values={success.values} /></p>
            <TooltipButton
              onClick={() => this.setState({ success: null })}
              size="small"
              tooltip="Dismiss this success message. It does not change forwarding or configuration."
            >
              <LocalizedText source={"Dismiss"} /></TooltipButton>
          </Message>
        )}

        {vpnCapablePods.length === 0 && (
          <Message warning>
            <Message.Header><LocalizedText source={"No VPN-Capable Pods"} /></Message.Header>
            <p>
              <LocalizedText source={"You need at least one pod with VPN gateway capability to use port forwarding."} /></p>
            <p>
              <LocalizedText source={"Create or join a pod that has the"} />{' '}
              <code>PrivateServiceGateway</code> <LocalizedText source={"capability enabled."} /></p>
          </Message>
        )}

        <Tab
          activeIndex={this.state.activeTab}
          menu={{ pointing: true }}
          onTabChange={this.handleTabChange}
          panes={panes}
        />

        {/* Create Forwarding Modal */}
        <Modal
          onClose={() => this.setState({ showCreateModal: false })}
          open={showCreateModal}
          size="small"
        >
          <Modal.Header><LocalizedText source={"Start Port Forwarding"} /></Modal.Header>
          <Modal.Content>
            <Form>
              <Form.Field>
                <label><LocalizedText source={"VPN Pod"} /></label>
                <Dropdown
                  fluid
                  onChange={(e, { value }) => this.handlePodSelection(value)}
                  options={vpnCapablePods.map((pod) => ({
                    key: pod.podId,
                    text: pod.name || pod.podId,
                    value: pod.podId,
                  }))}
                  placeholder={interfaceText("Select a VPN-capable pod")}
                  selection
                  value={selectedPodId || ''}
                 {...interfaceTextProps("Select a VPN-capable pod")}/>
                {selectedPodDetail && (
                  <div
                    style={{
                      color: 'var(--slskd-color-subtle, #666)',
                      fontSize: '0.9em',
                      marginTop: '10px',
                    }}
                  >
                    <p>
                      <strong><LocalizedText source={"Members:"} /></strong>{' '}
                      {selectedPodDetail.members?.length || 0}
                    </p>
                    {selectedPodDetail.privateServicePolicy?.enabled && (
                      <p>
                        <strong><LocalizedText source={"VPN Gateway:"} /></strong> <LocalizedText source={"Enabled"} /></p>
                    )}
                  </div>
                )}
              </Form.Field>

              <Form.Field required>
                <label><LocalizedText source={"Local Port"} /></label>
                <Input
                  max="65535"
                  min="1024"
                  onChange={(e) =>
                    this.handleFormChange('localPort', e.target.value)
                  }
                  placeholder={interfaceText("e.g., 8080")}
                  type="number"
                  value={createForm.localPort}
                 {...interfaceTextProps("e.g., 8080")}/>
                <small style={{ color: 'var(--slskd-color-subtle, #666)' }}>
                  <LocalizedText source={"Port on your local machine (1024-65535)"} /></small>
              </Form.Field>

              <Form.Field required>
                <label><LocalizedText source={"Remote Host"} /></label>
                <Input
                  onChange={(e) =>
                    this.handleFormChange('destinationHost', e.target.value)
                  }
                  placeholder={interfaceText("e.g., database.internal.company.com")}
                  value={createForm.destinationHost}
                 {...interfaceTextProps("e.g., database.internal.company.com")}/>
                <small style={{ color: 'var(--slskd-color-subtle, #666)' }}>
                  <LocalizedText source={"Hostname or IP address of the remote service"} /></small>
              </Form.Field>

              <Form.Field required>
                <label><LocalizedText source={"Remote Port"} /></label>
                <Input
                  max="65535"
                  min="1"
                  onChange={(e) =>
                    this.handleFormChange('destinationPort', e.target.value)
                  }
                  placeholder={interfaceText("e.g., 5432")}
                  type="number"
                  value={createForm.destinationPort}
                 {...interfaceTextProps("e.g., 5432")}/>
                <small style={{ color: 'var(--slskd-color-subtle, #666)' }}>
                  <LocalizedText source={"Port number of the remote service"} /></small>
              </Form.Field>

              <Form.Field>
                <label><LocalizedText source={"Service Name (Optional)"} /></label>
                <Input
                  onChange={(e) =>
                    this.handleFormChange('serviceName', e.target.value)
                  }
                  placeholder={interfaceText("e.g., postgres-db")}
                  value={createForm.serviceName}
                 {...interfaceTextProps("e.g., postgres-db")}/>
                <small style={{ color: 'var(--slskd-color-subtle, #666)' }}>
                  <LocalizedText source={"Named service registered in the pod (for better organization)"} /></small>
              </Form.Field>
            </Form>
          </Modal.Content>
          <Modal.Actions>
            <TooltipButton
              onClick={() => this.setState({ showCreateModal: false })}
              tooltip="Close this setup form without starting the port forward."
            >
              <LocalizedText source={"Cancel"} /></TooltipButton>
            <TooltipButton
              disabled={
                !selectedPodId ||
                !createForm.localPort ||
                !createForm.destinationHost ||
                !createForm.destinationPort
              }
              loading={creatingForwarding}
              onClick={this.handleCreateForwarding}
              primary
              tooltip={`Open a loopback-only listener on localhost:${createForm.localPort || 'the selected port'} and route local app connections through this VPN pod to the remote service. Use this when you need local access to that service.`}
            >
              <LocalizedText source={"Start Forwarding"} /></TooltipButton>
          </Modal.Actions>
        </Modal>
      </div>
    );
  }
}

export default PortForwarding;
