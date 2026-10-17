import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import * as pods from '../../lib/pods';
import React, { useEffect, useState } from 'react';
import {
  Checkbox,
  Dropdown,
  Form,
  Header,
  Icon,
  Input,
  Label,
  Message,
  Modal,
  Segment,
  Tab,
  Table,
} from 'semantic-ui-react';
import { TooltipButton } from '../Shared';

const VpnGatewayConfig = ({ podDetail, podId }) => {
  useInterfaceLanguage();
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // VPN Policy state
  const [vpnPolicy, setVpnPolicy] = useState({
    allowedDestinations: [],
    allowPrivateRanges: true,
    allowPublicDestinations: false,
    dialTimeout: '00:00:30',
    enabled: false,

    gatewayPeerId: '',

    // 1GB
    idleTimeout: '01:00:00',

    maxBytesPerDayPerPeer: 1_073_741_824,

    maxConcurrentTunnelsPerPeer: 5,

    maxConcurrentTunnelsPod: 15,

    maxLifetime: '24:00:00',
    maxMembers: 3,
    maxNewTunnelsPerMinutePerPeer: 10,
    registeredServices: [],
  });

  // Modal states for adding destinations and services
  const [showAddDestination, setShowAddDestination] = useState(false);
  const [showAddService, setShowAddService] = useState(false);
  const [newDestination, setNewDestination] = useState({
    hostPattern: '',
    port: '',
    protocol: 'tcp',
  });
  const [newService, setNewService] = useState({
    description: '',
    destinationHost: '',
    destinationPort: '',
    kind: 'WebInterface',
    name: '',
    protocol: 'tcp',
  });

  useEffect(() => {
    if (podDetail?.privateServicePolicy) {
      setVpnPolicy({
        ...podDetail.privateServicePolicy,

        allowedDestinations:
          podDetail.privateServicePolicy.allowedDestinations || [],

        allowPrivateRanges:
          podDetail.privateServicePolicy.allowPrivateRanges ?? true,

        allowPublicDestinations:
          podDetail.privateServicePolicy.allowPublicDestinations ?? false,

        dialTimeout: podDetail.privateServicePolicy.dialTimeout || '00:00:30',

        gatewayPeerId: podDetail.privateServicePolicy.gatewayPeerId || '',

        idleTimeout: podDetail.privateServicePolicy.idleTimeout || '01:00:00',

        maxBytesPerDayPerPeer:
          podDetail.privateServicePolicy.maxBytesPerDayPerPeer || 1_073_741_824,

        maxConcurrentTunnelsPerPeer:
          podDetail.privateServicePolicy.maxConcurrentTunnelsPerPeer || 5,

        maxConcurrentTunnelsPod:
          podDetail.privateServicePolicy.maxConcurrentTunnelsPod || 15,

        maxLifetime: podDetail.privateServicePolicy.maxLifetime || '24:00:00',
        // Ensure defaults for missing fields
        maxMembers: podDetail.privateServicePolicy.maxMembers || 3,
        maxNewTunnelsPerMinutePerPeer:
          podDetail.privateServicePolicy.maxNewTunnelsPerMinutePerPeer || 10,
        registeredServices:
          podDetail.privateServicePolicy.registeredServices || [],
      });
    }
  }, [podDetail]);

  const hasVpnCapability = podDetail?.capabilities?.includes(
    'PrivateServiceGateway',
  );

  const handleSavePolicy = async () => {
    if (!podId) return;

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      // Create updated pod with VPN policy
      const updatedPod = {
        ...podDetail,
        privateServicePolicy: vpnPolicy.enabled ? vpnPolicy : null,
      };

      await pods.update(podId, updatedPod);
      setSuccess(interfaceText("VPN policy updated successfully"));
    } catch (error) {
      console.error('Failed to update VPN policy:', error);
      setError(getApiErrorMessage(error, { t: interfaceText }, 'Failed to update VPN policy'));
    } finally {
      setSaving(false);
    }
  };

  const handleAddDestination = () => {
    if (!newDestination.hostPattern || !newDestination.port) return;

    const updatedDestinations = [
      ...vpnPolicy.allowedDestinations,
      {
        hostPattern: newDestination.hostPattern,
        port: Number.parseInt(newDestination.port, 10),
        protocol: newDestination.protocol,
      },
    ];

    setVpnPolicy((previous) => ({
      ...previous,
      allowedDestinations: updatedDestinations,
    }));
    setNewDestination({ hostPattern: '', port: '', protocol: 'tcp' });
    setShowAddDestination(false);
  };

  const handleRemoveDestination = (index) => {
    const updatedDestinations = vpnPolicy.allowedDestinations.filter(
      (_, index_) => index_ !== index,
    );
    setVpnPolicy((previous) => ({
      ...previous,
      allowedDestinations: updatedDestinations,
    }));
  };

  const handleAddService = () => {
    if (
      !newService.name ||
      !newService.destinationHost ||
      !newService.destinationPort
    )
      return;

    const updatedServices = [
      ...vpnPolicy.registeredServices,
      {
        description: newService.description,
        destinationHost: newService.destinationHost,
        destinationPort: Number.parseInt(newService.destinationPort, 10),
        kind: newService.kind,
        name: newService.name,
        protocol: newService.protocol,
      },
    ];

    setVpnPolicy((previous) => ({
      ...previous,
      registeredServices: updatedServices,
    }));
    setNewService({
      description: '',
      destinationHost: '',
      destinationPort: '',
      kind: 'WebInterface',
      name: '',
      protocol: 'tcp',
    });
    setShowAddService(false);
  };

  const handleRemoveService = (index) => {
    const updatedServices = vpnPolicy.registeredServices.filter(
      (_, index_) => index_ !== index,
    );
    setVpnPolicy((previous) => ({
      ...previous,
      registeredServices: updatedServices,
    }));
  };

  const formatBytes = (bytes) => {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let value = bytes;
    let unitIndex = 0;

    while (value >= 1_024 && unitIndex < units.length - 1) {
      value /= 1_024;
      unitIndex++;
    }

    return `${value.toFixed(1)} ${units[unitIndex]}`;
  };

  if (!hasVpnCapability) {
    return (
      <Segment placeholder>
        <Header icon>
          <Icon name="lock" />
          <LocalizedText source={"VPN Gateway Not Enabled"} /></Header>
        <Segment.Inline>
          <p><LocalizedText source={"This pod does not have VPN gateway capability enabled."} /></p>
          <p>
            <LocalizedText source={"To enable VPN functionality, add the \"PrivateServiceGateway\" capability to the pod."} /></p>
        </Segment.Inline>
      </Segment>
    );
  }

  const serviceKindOptions = [
    { key: 'WebInterface', text: interfaceText("Web Interface"), value: 'WebInterface' },
    { key: 'Database', text: interfaceText("Database"), value: 'Database' },
    { key: 'SSH', text: interfaceText("SSH"), value: 'SSH' },
    { key: 'Custom', text: interfaceText("Custom"), value: 'Custom' },
  ];

  const protocolOptions = [
    { key: 'tcp', text: interfaceText("TCP"), value: 'tcp' },
    { key: 'udp', text: interfaceText("UDP"), value: 'udp' },
  ];

  const panes = [
    {
      menuItem: 'Basic Settings',
      pane: (
        <Tab.Pane key="basic-settings">
          <Form>
            <Form.Group>
              <Form.Field width={4}>
                <label><LocalizedText source={"Enable VPN Gateway"} /></label>
                <Checkbox
                  checked={vpnPolicy.enabled}
                  onChange={(e, { checked }) =>
                    setVpnPolicy((previous) => ({
                      ...previous,
                      enabled: checked,
                    }))
                  }
                  toggle
                />
              </Form.Field>
              <Form.Field width={4}>
                <label><LocalizedText source={"Max Pod Members"} /></label>
                <Input
                  disabled={!vpnPolicy.enabled}
                  max={3}
                  min={1}
                  onChange={(e, { value }) =>
                    setVpnPolicy((previous) => ({
                      ...previous,
                      maxMembers: Number.parseInt(value, 10) || 3,
                    }))
                  }
                  type="number"
                  value={vpnPolicy.maxMembers}
                />
                <small><LocalizedText source={"Hard limit of 3 for VPN-enabled pods"} /></small>
              </Form.Field>
              <Form.Field width={8}>
                <label><LocalizedText source={"Gateway Peer ID"} /></label>
                <Input
                  disabled={!vpnPolicy.enabled}
                  onChange={(e, { value }) =>
                    setVpnPolicy((previous) => ({
                      ...previous,
                      gatewayPeerId: value,
                    }))
                  }
                  placeholder="peer-id-of-gateway-node"
                  value={vpnPolicy.gatewayPeerId}
                />
              </Form.Field>
            </Form.Group>

            <Header as="h4"><LocalizedText source={"Network Access Control"} /></Header>
            <Form.Group>
              <Form.Field>
                <Checkbox
                  checked={vpnPolicy.allowPrivateRanges}
                  disabled={!vpnPolicy.enabled}
                  label={interfaceText("Allow private IP ranges (RFC1918)")}
                  onChange={(e, { checked }) =>
                    setVpnPolicy((previous) => ({
                      ...previous,
                      allowPrivateRanges: checked,
                    }))
                  }
                 {...interfaceTextProps("Allow private IP ranges (RFC1918)")}/>
              </Form.Field>
              <Form.Field>
                <Checkbox
                  checked={vpnPolicy.allowPublicDestinations}
                  disabled={!vpnPolicy.enabled}
                  label={interfaceText("Allow public internet destinations")}
                  onChange={(e, { checked }) =>
                    setVpnPolicy((previous) => ({
                      ...previous,
                      allowPublicDestinations: checked,
                    }))
                  }
                 {...interfaceTextProps("Allow public internet destinations")}/>
              </Form.Field>
            </Form.Group>
          </Form>
        </Tab.Pane>
      ),
    },
    {
      menuItem: 'Allowed Destinations',
      pane: (
        <Tab.Pane key="allowed-destinations">
          <div style={{ marginBottom: '20px' }}>
            <TooltipButton
              aria-label={interfaceText("Add an allowed destination")}
              content={interfaceText("Add Destination")}
              disabled={!vpnPolicy.enabled}
              icon="plus"
              onClick={() => setShowAddDestination(true)}
              primary
              tooltip="Add a host and port to this pod's allowed destination draft. Save the VPN configuration to apply the new route."
             {...interfaceTextProps("Add an allowed destination")}/>
          </div>

          <Table celled>
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell><LocalizedText source={"Host Pattern"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Port"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Protocol"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Actions"} /></Table.HeaderCell>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {vpnPolicy.allowedDestinations.map((destination, index) => (
                <Table.Row key={index}>
                  <Table.Cell>{destination.hostPattern}</Table.Cell>
                  <Table.Cell>{destination.port}</Table.Cell>
                  <Table.Cell>{destination.protocol?.toUpperCase()}</Table.Cell>
                  <Table.Cell>
                    <TooltipButton
                      aria-label={interfaceText("Remove allowed destination {hostPattern}:{port}", { "hostPattern": (destination.hostPattern), "port": (destination.port) })}
                      color="red"
                      disabled={!vpnPolicy.enabled}
                      icon="trash"
                      onClick={() => handleRemoveDestination(index)}
                      size="small"
                      tooltip="Remove {hostPattern}:{port} from the draft policy. Save the VPN configuration to stop allowing this route."
                     {...interfaceTextProps("Remove allowed destination {hostPattern}:{port}", { hostPattern: destination.hostPattern, port: destination.port })}/>
                  </Table.Cell>
                </Table.Row>
              ))}
              {vpnPolicy.allowedDestinations.length === 0 && (
                <Table.Row>
                  <Table.Cell
                    colSpan={4}
                    textAlign="center"
                  >
                    <LocalizedText source={"No destinations configured"} /></Table.Cell>
                </Table.Row>
              )}
            </Table.Body>
          </Table>
        </Tab.Pane>
      ),
    },
    {
      menuItem: 'Registered Services',
      pane: (
        <Tab.Pane key="registered-services">
          <div style={{ marginBottom: '20px' }}>
            <TooltipButton
              aria-label={interfaceText("Add a registered service")}
              content={interfaceText("Add Service")}
              disabled={!vpnPolicy.enabled}
              icon="plus"
              onClick={() => setShowAddService(true)}
              primary
              tooltip="Register a named service and destination in this pod's policy draft so members can find the route. Save the VPN configuration to apply it."
             {...interfaceTextProps("Add a registered service")}/>
          </div>

          <Table celled>
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell><LocalizedText source={"Name"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Description"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Type"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Destination"} /></Table.HeaderCell>
                <Table.HeaderCell><LocalizedText source={"Actions"} /></Table.HeaderCell>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {vpnPolicy.registeredServices.map((service, index) => (
                <Table.Row key={index}>
                  <Table.Cell>{service.name}</Table.Cell>
                  <Table.Cell>{service.description}</Table.Cell>
                  <Table.Cell>
                    <Label color="blue">{service.kind}</Label>
                  </Table.Cell>
                  <Table.Cell>
                    {service.destinationHost}:{service.destinationPort} (
                    {service.protocol})
                  </Table.Cell>
                  <Table.Cell>
                    <TooltipButton
                      aria-label={interfaceText("Remove registered service {name}", { "name": (service.name) })}
                      color="red"
                      disabled={!vpnPolicy.enabled}
                      icon="trash"
                      onClick={() => handleRemoveService(index)}
                      size="small"
                      tooltip="Remove {name} from the draft service list. Save the VPN configuration to stop advertising this route to pod members."
                     {...interfaceTextProps("Remove registered service {name}", { name: service.name })}/>
                  </Table.Cell>
                </Table.Row>
              ))}
              {vpnPolicy.registeredServices.length === 0 && (
                <Table.Row>
                  <Table.Cell
                    colSpan={5}
                    textAlign="center"
                  >
                    <LocalizedText source={"No services registered"} /></Table.Cell>
                </Table.Row>
              )}
            </Table.Body>
          </Table>
        </Tab.Pane>
      ),
    },
    {
      menuItem: 'Resource Limits',
      pane: (
        <Tab.Pane key="resource-limits">
          <Form>
            <Header as="h4"><LocalizedText source={"Connection Limits"} /></Header>
            <Form.Group widths="equal">
              <Form.Field>
                <label><LocalizedText source={"Max Concurrent Tunnels Per Peer"} /></label>
                <Input
                  disabled={!vpnPolicy.enabled}
                  max={20}
                  min={1}
                  onChange={(e, { value }) =>
                    setVpnPolicy((previous) => ({
                      ...previous,
                      maxConcurrentTunnelsPerPeer:
                        Number.parseInt(value, 10) || 5,
                    }))
                  }
                  type="number"
                  value={vpnPolicy.maxConcurrentTunnelsPerPeer}
                />
              </Form.Field>
              <Form.Field>
                <label><LocalizedText source={"Max Concurrent Tunnels (Pod Total)"} /></label>
                <Input
                  disabled={!vpnPolicy.enabled}
                  max={100}
                  min={1}
                  onChange={(e, { value }) =>
                    setVpnPolicy((previous) => ({
                      ...previous,
                      maxConcurrentTunnelsPod: Number.parseInt(value, 10) || 15,
                    }))
                  }
                  type="number"
                  value={vpnPolicy.maxConcurrentTunnelsPod}
                />
              </Form.Field>
            </Form.Group>

            <Form.Group widths="equal">
              <Form.Field>
                <label><LocalizedText source={"Max New Tunnels Per Minute Per Peer"} /></label>
                <Input
                  disabled={!vpnPolicy.enabled}
                  max={60}
                  min={1}
                  onChange={(e, { value }) =>
                    setVpnPolicy((previous) => ({
                      ...previous,
                      maxNewTunnelsPerMinutePerPeer:
                        Number.parseInt(value, 10) || 10,
                    }))
                  }
                  type="number"
                  value={vpnPolicy.maxNewTunnelsPerMinutePerPeer}
                />
              </Form.Field>
              <Form.Field>
                <label><LocalizedText source={"Max Bandwidth Per Day Per Peer"} /></label>
                <Input
                  disabled={!vpnPolicy.enabled}
                  min={0}
                  onChange={(e, { value }) =>
                    setVpnPolicy((previous) => ({
                      ...previous,
                      maxBytesPerDayPerPeer:
                        Number.parseInt(value, 10) * 1_024 * 1_024 ||
                        1_073_741_824,
                    }))
                  }
                  type="number"
                  value={Math.round(
                    vpnPolicy.maxBytesPerDayPerPeer / (1_024 * 1_024),
                  )} // Convert to MB
                />
                <small>
                  <LocalizedText source={"MB per day per peer ("} />{formatBytes(vpnPolicy.maxBytesPerDayPerPeer)})
                </small>
              </Form.Field>
            </Form.Group>

            <Header as="h4"><LocalizedText source={"Timeouts"} /></Header>
            <Form.Group widths="equal">
              <Form.Field>
                <label><LocalizedText source={"Idle Timeout (HH:MM:SS)"} /></label>
                <Input
                  disabled={!vpnPolicy.enabled}
                  onChange={(e, { value }) =>
                    setVpnPolicy((previous) => ({
                      ...previous,
                      idleTimeout: value,
                    }))
                  }
                  placeholder="01:00:00"
                  value={vpnPolicy.idleTimeout}
                />
                <small><LocalizedText source={"Close tunnels after this period of inactivity"} /></small>
              </Form.Field>
              <Form.Field>
                <label><LocalizedText source={"Max Lifetime (HH:MM:SS)"} /></label>
                <Input
                  disabled={!vpnPolicy.enabled}
                  onChange={(e, { value }) =>
                    setVpnPolicy((previous) => ({
                      ...previous,
                      maxLifetime: value,
                    }))
                  }
                  placeholder="24:00:00"
                  value={vpnPolicy.maxLifetime}
                />
                <small><LocalizedText source={"Maximum duration a tunnel can remain open"} /></small>
              </Form.Field>
              <Form.Field>
                <label><LocalizedText source={"Dial Timeout (HH:MM:SS)"} /></label>
                <Input
                  disabled={!vpnPolicy.enabled}
                  onChange={(e, { value }) =>
                    setVpnPolicy((previous) => ({
                      ...previous,
                      dialTimeout: value,
                    }))
                  }
                  placeholder="00:00:30"
                  value={vpnPolicy.dialTimeout}
                />
                <small><LocalizedText source={"Timeout for establishing outbound connections"} /></small>
              </Form.Field>
            </Form.Group>
          </Form>
        </Tab.Pane>
      ),
    },
  ];

  return (
    <div>
      {error && (
        <Message error>
          <Message.Header><LocalizedText source={"Configuration Error"} /></Message.Header>
          <p>{error}</p>
        </Message>
      )}

      {success && (
        <Message success>
          <Message.Header><LocalizedText source={"Configuration Updated"} /></Message.Header>
          <p>{success}</p>
        </Message>
      )}

      <Tab
        activeIndex={activeIndex}
        menu={{ pointing: true }}
        onTabChange={(_event, { activeIndex: nextIndex }) =>
          setActiveIndex(nextIndex)
        }
        panes={panes}
        renderActiveOnly={false}
      />

      <div style={{ marginTop: '20px', textAlign: 'right' }}>
        <TooltipButton
          disabled={!vpnPolicy.enabled}
          loading={saving}
          onClick={handleSavePolicy}
          primary
          tooltip="Save this pod's enabled VPN gateway policy so its destination rules, registered services, and limits take effect."
        >
          <LocalizedText source={"Save VPN Configuration"} /></TooltipButton>
      </div>

      {/* Add Destination Modal */}
      <Modal
        onClose={() => setShowAddDestination(false)}
        open={showAddDestination}
        size="small"
      >
        <Modal.Header><LocalizedText source={"Add Allowed Destination"} /></Modal.Header>
        <Modal.Content>
          <Form>
            <Form.Field required>
              <label><LocalizedText source={"Host Pattern"} /></label>
              <Input
                onChange={(e, { value }) =>
                  setNewDestination((previous) => ({
                    ...previous,
                    hostPattern: value,
                  }))
                }
                placeholder={interfaceText("example.com or *.example.com")}
                value={newDestination.hostPattern}
               {...interfaceTextProps("example.com or *.example.com")}/>
              <small>
                <LocalizedText source={"Use exact hostname or wildcard patterns (e.g., *.domain.com)"} /></small>
            </Form.Field>
            <Form.Field required>
              <label><LocalizedText source={"Port"} /></label>
              <Input
                max={65_535}
                min={1}
                onChange={(e, { value }) =>
                  setNewDestination((previous) => ({
                    ...previous,
                    port: value,
                  }))
                }
                placeholder="80"
                type="number"
                value={newDestination.port}
              />
            </Form.Field>
            <Form.Field>
              <label><LocalizedText source={"Protocol"} /></label>
              <Dropdown
                onChange={(e, { value }) =>
                  setNewDestination((previous) => ({
                    ...previous,
                    protocol: value,
                  }))
                }
                options={protocolOptions}
                selection
                value={newDestination.protocol}
              />
            </Form.Field>
          </Form>
        </Modal.Content>
        <Modal.Actions>
          <TooltipButton
            onClick={() => setShowAddDestination(false)}
            tooltip="Close the dialog and return to the allowed destination list without adding this entry."
          >
            <LocalizedText source={"Cancel"} /></TooltipButton>
          <TooltipButton
            aria-label={interfaceText("Add destination to draft policy")}
            disabled={!newDestination.hostPattern || !newDestination.port}
            onClick={handleAddDestination}
            primary
            tooltip="Add this host, port, and protocol to the draft allowlist. Save the VPN configuration to apply it to the pod."
           {...interfaceTextProps("Add destination to draft policy")}>
            <LocalizedText source={"Add Destination"} /></TooltipButton>
        </Modal.Actions>
      </Modal>

      {/* Add Service Modal */}
      <Modal
        onClose={() => setShowAddService(false)}
        open={showAddService}
        size="small"
      >
        <Modal.Header><LocalizedText source={"Add Registered Service"} /></Modal.Header>
        <Modal.Content>
          <Form>
            <Form.Field required>
              <label><LocalizedText source={"Service Name"} /></label>
              <Input
                onChange={(e, { value }) =>
                  setNewService((previous) => ({ ...previous, name: value }))
                }
                placeholder={interfaceText("My Web Service")}
                value={newService.name}
               {...interfaceTextProps("My Web Service")}/>
            </Form.Field>
            <Form.Field>
              <label><LocalizedText source={"Description"} /></label>
              <Input
                onChange={(e, { value }) =>
                  setNewService((previous) => ({
                    ...previous,
                    description: value,
                  }))
                }
                placeholder={interfaceText("Description of the service")}
                value={newService.description}
               {...interfaceTextProps("Description of the service")}/>
            </Form.Field>
            <Form.Field>
              <label><LocalizedText source={"Service Type"} /></label>
              <Dropdown
                onChange={(e, { value }) =>
                  setNewService((previous) => ({ ...previous, kind: value }))
                }
                options={serviceKindOptions}
                selection
                value={newService.kind}
              />
            </Form.Field>
            <Form.Field required>
              <label><LocalizedText source={"Destination Host"} /></label>
              <Input
                onChange={(e, { value }) =>
                  setNewService((previous) => ({
                    ...previous,
                    destinationHost: value,
                  }))
                }
                placeholder="service.internal.company.com"
                value={newService.destinationHost}
              />
            </Form.Field>
            <Form.Field required>
              <label><LocalizedText source={"Destination Port"} /></label>
              <Input
                max={65_535}
                min={1}
                onChange={(e, { value }) =>
                  setNewService((previous) => ({
                    ...previous,
                    destinationPort: value,
                  }))
                }
                placeholder="443"
                type="number"
                value={newService.destinationPort}
              />
            </Form.Field>
            <Form.Field>
              <label><LocalizedText source={"Protocol"} /></label>
              <Dropdown
                onChange={(e, { value }) =>
                  setNewService((previous) => ({
                    ...previous,
                    protocol: value,
                  }))
                }
                options={protocolOptions}
                selection
                value={newService.protocol}
              />
            </Form.Field>
          </Form>
        </Modal.Content>
        <Modal.Actions>
          <TooltipButton
            onClick={() => setShowAddService(false)}
            tooltip="Close the dialog and return to registered services without adding this entry."
          >
            <LocalizedText source={"Cancel"} /></TooltipButton>
          <TooltipButton
            aria-label={interfaceText("Add service to draft policy")}
            disabled={
              !newService.name ||
              !newService.destinationHost ||
              !newService.destinationPort
            }
            onClick={handleAddService}
            primary
            tooltip="Add this named service and destination to the draft policy. Save the VPN configuration to publish the route to pod members."
           {...interfaceTextProps("Add service to draft policy")}>
            <LocalizedText source={"Add Service"} /></TooltipButton>
        </Modal.Actions>
      </Modal>
    </div>
  );
};

export default VpnGatewayConfig;
