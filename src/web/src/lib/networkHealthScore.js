import { interfaceText } from './interfaceLocale';
import { formatRegionalNumber } from './regionalFormat';

const clamp = (value) => Math.max(0, Math.min(100, value));

const countSecurityWarnings = (mesh = {}) =>
  (mesh.warnings?.length || 0) +
  (mesh.signatureVerificationFailures || 0) +
  (mesh.reputationBasedRejections || 0) +
  (mesh.rateLimitViolations || 0) +
  (mesh.quarantinedPeers || 0);

export const buildNetworkHealthScore = ({
  discoveredPeers = [],
  meshPeers = [],
  stats = {},
} = {}) => {
  const dht = stats.dht || {};
  const mesh = stats.mesh || {};
  const backfill = stats.backfill || {};
  const hashDb = stats.hashDb || {};
  const activeMeshConnections = dht.activeMeshConnections || 0;
  const dhtNodes = dht.dhtNodeCount || 0;
  const discoveredCount = Math.max(
    discoveredPeers.length,
    dht.discoveredPeerCount || dht.totalPeersDiscovered || 0,
  );
  const meshCount = Math.max(
    meshPeers.length,
    mesh.connectedPeerCount || 0,
    activeMeshConnections,
  );
  const dhtRunning = dht.isDhtRunning === true;
  const dhtEnabled = dht.isEnabled === true;
  const lanOnly = dht.isLanOnly === true || dht.lanOnly === true;
  const securityWarningCount = countSecurityWarnings(mesh);
  const activeSwarms = stats.swarmJobs?.length || 0;
  const hashEntries = hashDb.totalEntries || 0;
  const findings = [];
  let score = 100;

  if (!dhtEnabled) {
    score -= 10;
    findings.push({
      action: 'Enable DHT rendezvous only if you want mesh peer discovery.',
      area: 'DHT',
      severity: 'info',
      summary: 'DHT rendezvous disabled',
    });
  } else if (!dhtRunning && !lanOnly) {
    score -= 18;
    findings.push({
      action: 'Check DHT startup logs and listener configuration.',
      area: 'DHT',
      severity: 'warn',
      summary: 'DHT rendezvous not running',
    });
  } else if (!lanOnly && dhtNodes === 0 && discoveredCount === 0 && meshCount === 0) {
    score -= 30;
    findings.push({
      action: 'Verify firewall, NAT, container port publishing, and the Soulseek listen port.',
      area: 'Connectivity',
      severity: 'fail',
      summary: 'Public rendezvous has no visible peers',
    });
  } else if (lanOnly && discoveredCount === 0 && meshCount === 0) {
    score -= 8;
    findings.push({
      action: 'Add trusted local peers or disable LAN-only mode for public discovery.',
      area: 'Connectivity',
      severity: 'info',
      summary: 'LAN-only mode has no local peers yet',
    });
  }

  if (meshCount === 0) {
    score -= 12;
    findings.push({
      action: 'Search, download, or configure trusted peers so slskdN can discover mesh-capable nodes.',
      area: 'Mesh',
      severity: 'warn',
      summary: 'No connected mesh peers',
    });
  }

  if (securityWarningCount > 0) {
    score -= Math.min(25, securityWarningCount * 3);
    findings.push({
      action: 'Review Mesh Sync Security counters before trusting inbound evidence.',
      area: 'Security',
      severity: 'warn',
      summary: `${securityWarningCount} mesh security signal${securityWarningCount === 1 ? '' : 's'} visible`,
    });
  }

  if (hashEntries === 0) {
    score -= 6;
    findings.push({
      action: 'Let searches/downloads populate HashDb or run a conservative history backfill.',
      area: 'HashDb',
      severity: 'info',
      summary: 'No hash entries visible',
    });
  }

  if (backfill.pendingCount > 100 && !backfill.isActive) {
    score -= 6;
    findings.push({
      action: 'Run backfill in batches when the network is idle.',
      area: 'Backfill',
      severity: 'info',
      summary: `${backfill.pendingCount} pending backfill candidates`,
    });
  }

  return {
    findings,
    inputs: {
      activeSwarms,
      dhtEnabled,
      dhtNodes,
      dhtRunning,
      discoveredCount,
      hashEntries,
      lanOnly,
      meshCount,
      securityWarningCount,
    },
    label:
      score >= 85
        ? 'Healthy'
        : score >= 65
          ? 'Degraded'
          : 'Needs attention',
    score: clamp(score),
  };
};

export const formatNetworkHealthReport = (health) => {
  const localizeHealthLabel = (label) => {
    switch (label) {
      case 'Healthy':
        return interfaceText('Healthy');
      case 'Degraded':
        return interfaceText('Degraded');
      case 'Needs attention':
        return interfaceText('Needs attention');
      default:
        return label;
    }
  };
  const localizeFindingArea = (area) => {
    switch (area) {
      case 'DHT':
        return interfaceText('DHT');
      case 'Connectivity':
        return interfaceText('Connectivity');
      case 'Mesh':
        return interfaceText('Mesh');
      case 'Security':
        return interfaceText('Security');
      case 'HashDb':
        return interfaceText('HashDb');
      case 'Backfill':
        return interfaceText('Backfill');
      default:
        return area;
    }
  };
  const localizeFindingSeverity = (severity) => {
    switch (severity) {
      case 'info':
        return interfaceText('Info');
      case 'warn':
        return interfaceText('Warn');
      case 'fail':
        return interfaceText('Fail');
      default:
        return severity;
    }
  };
  const localizeFindingAction = (action) => {
    switch (action) {
      case 'Enable DHT rendezvous only if you want mesh peer discovery.':
        return interfaceText('Enable DHT rendezvous only if you want mesh peer discovery.');
      case 'Check DHT startup logs and listener configuration.':
        return interfaceText('Check DHT startup logs and listener configuration.');
      case 'Verify firewall, NAT, container port publishing, and the Soulseek listen port.':
        return interfaceText('Verify firewall, NAT, container port publishing, and the Soulseek listen port.');
      case 'Add trusted local peers or disable LAN-only mode for public discovery.':
        return interfaceText('Add trusted local peers or disable LAN-only mode for public discovery.');
      case 'Search, download, or configure trusted peers so slskdN can discover mesh-capable nodes.':
        return interfaceText('Search, download, or configure trusted peers so slskdN can discover mesh-capable nodes.');
      case 'Review Mesh Sync Security counters before trusting inbound evidence.':
        return interfaceText('Review Mesh Sync Security counters before trusting inbound evidence.');
      case 'Let searches/downloads populate HashDb or run a conservative history backfill.':
        return interfaceText('Let searches/downloads populate HashDb or run a conservative history backfill.');
      case 'Run backfill in batches when the network is idle.':
        return interfaceText('Run backfill in batches when the network is idle.');
      default:
        return action;
    }
  };
  const formatFindingSummary = (finding) => {
    const securityMatch = finding.summary.match(/^(\d+) mesh security signals? visible$/u);
    if (securityMatch) {
      const source = Number(securityMatch[1]) === 1
        ? '{count} mesh security signal visible'
        : '{count} mesh security signals visible';
      return interfaceText(source, { count: formatRegionalNumber(Number(securityMatch[1])) });
    }
    const backfillMatch = finding.summary.match(/^(\d+) pending backfill candidates?$/u);
    if (backfillMatch) {
      const source = Number(backfillMatch[1]) === 1
        ? '{count} pending backfill candidate'
        : '{count} pending backfill candidates';
      return interfaceText(source, { count: formatRegionalNumber(Number(backfillMatch[1])) });
    }
    switch (finding.summary) {
      case 'DHT rendezvous disabled':
        return interfaceText('DHT rendezvous disabled');
      case 'DHT rendezvous not running':
        return interfaceText('DHT rendezvous not running');
      case 'Public rendezvous has no visible peers':
        return interfaceText('Public rendezvous has no visible peers');
      case 'LAN-only mode has no local peers yet':
        return interfaceText('LAN-only mode has no local peers yet');
      case 'No connected mesh peers':
        return interfaceText('No connected mesh peers');
      case 'No hash entries visible':
        return interfaceText('No hash entries visible');
      default:
        return finding.summary;
    }
  };

  const lines = [
    interfaceText('slskdN network health report'),
    interfaceText('Score: {score}/100', { score: formatRegionalNumber(health.score) }),
    interfaceText('Status: {status}', { status: localizeHealthLabel(health.label) }),
    interfaceText('Mesh peers: {count}', { count: formatRegionalNumber(health.inputs.meshCount) }),
    interfaceText('Discovered peers: {count}', { count: formatRegionalNumber(health.inputs.discoveredCount) }),
    interfaceText('DHT nodes: {count}', { count: formatRegionalNumber(health.inputs.dhtNodes) }),
    interfaceText('Hash entries: {count}', { count: formatRegionalNumber(health.inputs.hashEntries) }),
    interfaceText('Security signals: {count}', { count: formatRegionalNumber(health.inputs.securityWarningCount) }),
    '',
  ];

  if (health.findings.length > 0) {
    lines.push(interfaceText('Findings:'));
    health.findings.forEach((finding) => {
      lines.push(interfaceText('- [{severity}] {area}: {summary}', {
        area: localizeFindingArea(finding.area),
        severity: localizeFindingSeverity(finding.severity),
        summary: formatFindingSummary(finding),
      }));
      lines.push(interfaceText('  Action: {action}', { action: localizeFindingAction(finding.action) }));
    });
  } else {
    lines.push(interfaceText('Findings: none'));
  }

  return lines.join('\n');
};
