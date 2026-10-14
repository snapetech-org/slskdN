import LocalizedText from "./Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../lib/interfaceLocale";
import { getLocalStorageItem, setLocalStorageItem } from '../lib/storage';
import React from 'react';
import { Button, Icon, Popup, Segment } from 'semantic-ui-react';

const NETWORK_ENDPOINT_NOTICE_DISMISSED_FOREVER_STORAGE_KEY =
  'slskdn.networkEndpoints.dismissedForever';
const NETWORK_ENDPOINT_NOTICE_STORAGE_KEY =
  'slskdn.networkEndpoints.v2.dismissedSignature';
const NETWORK_ENDPOINT_SNAPSHOT_STORAGE_KEY =
  'slskdn.networkEndpoints.v2.lastDismissedSnapshot';
const LEGACY_NETWORK_ENDPOINT_SNAPSHOT_STORAGE_KEY =
  'slskdn.networkEndpoints.lastDismissedSnapshot';
const LEGACY_VPN_PORT_NOTICE_STORAGE_KEY =
  'slskdn.vpnForwardedPorts.dismissedSignature';

const normalizePortForwardProtocol = (proto) =>
  `${proto || ''}`.trim().toUpperCase();

const getOption = (source, ...keys) => {
  for (const key of keys) {
    if (source && Object.prototype.hasOwnProperty.call(source, key)) {
      return source[key];
    }
  }

  return undefined;
};

const toConfiguredPort = (value, fallback) => {
  const port = Number(value);
  return Number.isInteger(port) && port > 0 ? port : fallback;
};

export const getVpnPortForwards = (vpn = {}) => {
  if (Array.isArray(vpn.portForwards) && vpn.portForwards.length > 0) {
    return vpn.portForwards
      .filter((forward) => forward?.publicPort > 0)
      .map((forward) => ({
        localPort: forward.localPort,
        namespace: forward.namespace,
        proto: normalizePortForwardProtocol(forward.proto),
        publicIp: forward.publicIPAddress || forward.publicIp,
        publicPort: forward.publicPort,
        slot: forward.slot,
        targetPort: forward.targetPort,
      }))
      .sort((left, right) => (left.slot ?? 0) - (right.slot ?? 0));
  }

  if (vpn.forwardedPort > 0) {
    return [
      {
        proto: 'TCP',
        publicIp: vpn.publicIPAddress,
        publicPort: vpn.forwardedPort,
        slot: 0,
      },
    ];
  }

  return [];
};

export const getVpnPortSignature = (forwards) =>
  forwards
    .map((forward) =>
      [
        forward.slot ?? '',
        forward.proto ?? '',
        forward.publicIp ?? '',
        forward.publicPort ?? '',
        forward.localPort ?? '',
        forward.targetPort ?? '',
      ].join(':'),
    )
    .join('|');

const parseLegacyVpnPortSignature = (signature) => {
  if (!signature) return null;

  const portForwards = signature
    .split('|')
    .map((entry) => {
      const [slot, proto, publicIp, publicPort, localPort, targetPort] =
        entry.split(':');
      const slotNumber = Number.parseInt(slot, 10);
      const normalizedProto = normalizePortForwardProtocol(proto);

      return {
        label:
          slotNumber === 0
            ? 'Soulseek'
            : normalizedProto || 'Forward',
        localPort: Number.parseInt(localPort, 10) || undefined,
        proto: normalizedProto,
        publicIp: publicIp || undefined,
        publicPort: Number.parseInt(publicPort, 10) || undefined,
        slot: Number.isFinite(slotNumber) ? slotNumber : undefined,
        targetPort: Number.parseInt(targetPort, 10) || undefined,
      };
    })
    .filter((forward) => forward.publicPort > 0);

  return portForwards.length ? { portForwards, signature } : null;
};

export const hasDismissedVpnPortNotice = (signature) => {
  if (
    getLocalStorageItem(
      NETWORK_ENDPOINT_NOTICE_DISMISSED_FOREVER_STORAGE_KEY,
    ) === 'true'
  ) {
    return true;
  }

  return Boolean(signature) && (
    getLocalStorageItem(NETWORK_ENDPOINT_NOTICE_STORAGE_KEY, '') !== '' ||
    getLocalStorageItem(LEGACY_VPN_PORT_NOTICE_STORAGE_KEY, '') !== ''
  );
};

export const getStoredNetworkEndpointSnapshot = () => {
  try {
    const snapshot = JSON.parse(
      getLocalStorageItem(NETWORK_ENDPOINT_SNAPSHOT_STORAGE_KEY, 'null'),
    );
    if (snapshot?.signature) {
      return snapshot;
    }
  } catch {
    // Fall through to the legacy key used by the earlier VPN-only banner.
  }

  try {
    const snapshot = JSON.parse(
      getLocalStorageItem(LEGACY_NETWORK_ENDPOINT_SNAPSHOT_STORAGE_KEY, 'null'),
    );
    if (snapshot?.signature) {
      return snapshot;
    }
  } catch {
    // Fall through to the original single-signature key.
  }

  return parseLegacyVpnPortSignature(
    getLocalStorageItem(LEGACY_VPN_PORT_NOTICE_STORAGE_KEY, ''),
  );
};

export const storeDismissedVpnPortNotice = (signature, portForwards) => {
  setLocalStorageItem(
    NETWORK_ENDPOINT_NOTICE_DISMISSED_FOREVER_STORAGE_KEY,
    'true',
  );
  setLocalStorageItem(NETWORK_ENDPOINT_NOTICE_STORAGE_KEY, signature);
  setLocalStorageItem(
    NETWORK_ENDPOINT_SNAPSHOT_STORAGE_KEY,
    JSON.stringify({
      portForwards,
      signature,
    }),
  );
};

const buildCurrentIngressPorts = (options = {}) => {
  const soulseek = getOption(options, 'soulseek', 'Soulseek') || {};
  const dht = getOption(options, 'dht', 'dhtRendezvous', 'DhtRendezvous') || {};
  const soulseekListenPort = toConfiguredPort(
    getOption(soulseek, 'listenPort', 'listen_port', 'ListenPort'),
    50300,
  );
  const dhtOverlayPort = toConfiguredPort(
    getOption(dht, 'overlayPort', 'overlay_port', 'OverlayPort'),
    50305,
  );
  const dhtPort = toConfiguredPort(
    getOption(dht, 'dhtPort', 'dht_port', 'DhtPort'),
    50305,
  );
  const ports = [{
    config: 'soulseek.listen_port',
    label: interfaceText("Soulseek"),
    port: soulseekListenPort,
    proto: 'TCP',
  }];

  if (dhtOverlayPort === dhtPort) {
    ports.push({
      config: 'dht.overlay_port + dht.dht_port',
      label: 'mesh/DHT/QUIC',
      port: dhtOverlayPort,
      proto: 'TCP/UDP',
    });
  } else {
    ports.push(
      {
        config: 'dht.overlay_port',
        label: 'mesh/QUIC',
        port: dhtOverlayPort,
        proto: 'TCP',
      },
      {
        config: 'dht.dht_port',
        label: interfaceText("DHT"),
        port: dhtPort,
        proto: 'UDP',
      },
    );
  }

  return ports;
};

const formatIngressPort = (expected) =>
  `${expected.label} ${expected.proto} ${expected.port}`;

const formatCurrentIngressPorts = (options) =>
  buildCurrentIngressPorts(options).map(formatIngressPort).join(', ');

const NetworkEndpointNotice = ({ onDismiss, options, portForwards }) => {
  useInterfaceLanguage();
  if (!portForwards.length) {
    return null;
  }

  return (
    <Segment
      className="network-endpoint-change-notice"
      data-testid="vpn-port-change-notice"
    >
      <div className="network-endpoint-change-notice-body">
        <Icon name="exchange" />
        <div className="network-endpoint-change-notice-copy">
          <span>
            <strong><LocalizedText source={"Ingress ports changed:"} /></strong> <LocalizedText source={"older builds needed 5 public forwards; now keep {ports} reachable."} values={{ ports: formatCurrentIngressPorts(options) }} />
          </span>
        </div>
      </div>
      <Popup
        content={interfaceText("Dismiss this port migration reminder permanently in this browser.")}
        trigger={
          <Button
            basic
            compact
            icon="close"
            onClick={onDismiss}
            title={interfaceText("Dismiss port migration reminder permanently")}
           {...interfaceTextProps("Dismiss port migration reminder permanently")}/>
        }
       {...interfaceTextProps("Dismiss this port migration reminder permanently in this browser.")}/>
    </Segment>
  );
};

export default NetworkEndpointNotice;
