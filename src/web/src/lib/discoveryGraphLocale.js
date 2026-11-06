import { interfaceText } from './interfaceLocale';
import { formatRegionalNumber } from './regionalFormat';

export const localizeDiscoveryGraphNodeType = (nodeType) => {
  switch (nodeType) {
    case 'artist':
      return interfaceText('Artist');
    case 'album':
      return interfaceText('Album');
    case 'track':
      return interfaceText('Track');
    case 'segment':
      return interfaceText('Segment');
    case 'songid_run':
      return interfaceText('SongID run');
    case 'mix':
      return interfaceText('Mix cluster');
    case 'seed':
      return interfaceText('Seed');
    default:
      return nodeType;
  }
};

export const localizeDiscoveryGraphEdgeType = (edgeType) => {
  switch (edgeType) {
    case 'performed_by':
      return interfaceText('Performed by');
    case 'candidate_neighbor':
      return interfaceText('Candidate neighbor');
    case 'release_group':
      return interfaceText('Release group');
    case 'album_context':
      return interfaceText('Album context');
    case 'segment_context':
      return interfaceText('Segment context');
    case 'identity_candidate':
      return interfaceText('Identity candidate');
    case 'artist_context':
      return interfaceText('Artist context');
    case 'segment_candidate':
      return interfaceText('Segment candidate');
    case 'mix_cluster':
      return interfaceText('Mix cluster');
    case 'mix_segment':
      return interfaceText('Mix segment');
    case 'comparison':
      return interfaceText('Comparison');
    case 'metadata_context':
      return interfaceText('Metadata context');
    case 'comparison_context':
      return interfaceText('Comparison context');
    default:
      return edgeType;
  }
};

export const localizeDiscoveryGraphSummary = (summary) => {
  switch (summary) {
    case 'Artist neighborhood with SongID candidates and release-graph context.':
      return interfaceText('Artist neighborhood with SongID candidates and release-graph context.');
    case 'Album neighborhood with artist and nearby track context.':
      return interfaceText('Album neighborhood with artist and nearby track context.');
    case 'Track neighborhood with artist, alternatives, and segment ambiguity context.':
      return interfaceText('Track neighborhood with artist, alternatives, and segment ambiguity context.');
    case 'Fallback discovery seed without a SongID run context.':
      return interfaceText('Fallback discovery seed without a SongID run context.');
    case 'SongID neighborhood with candidates, ambiguity branches, and segment decomposition.':
      return interfaceText('SongID neighborhood with candidates, ambiguity branches, and segment decomposition.');
    default:
      return summary;
  }
};

export const localizeDiscoveryGraphReason = (reason) => {
  switch (reason) {
    case 'Seed artist for discovery topology.':
      return interfaceText('Seed artist for discovery topology.');
    case 'Track candidate attached to the selected artist.':
      return interfaceText('Track candidate attached to the selected artist.');
    case 'Nearby artist candidate surfaced in the same SongID context.':
      return interfaceText('Nearby artist candidate surfaced in the same SongID context.');
    case 'Release group from MusicBrainz artist graph.':
      return interfaceText('Release group from MusicBrainz artist graph.');
    case 'Seed release for discovery topology.':
      return interfaceText('Seed release for discovery topology.');
    case 'Track candidate sits near this album in the same SongID context.':
      return interfaceText('Track candidate sits near this album in the same SongID context.');
    case 'Seed recording for discovery topology.':
      return interfaceText('Seed recording for discovery topology.');
    case 'Alternative or adjacent track candidate from the same SongID run.':
      return interfaceText('Alternative or adjacent track candidate from the same SongID run.');
    case 'Fallback Discovery Graph seed.':
      return interfaceText('Fallback Discovery Graph seed.');
    case 'SongID run seed. Near nodes come from identity, ambiguity, and evidence context.':
      return interfaceText('SongID run seed. Near nodes come from identity, ambiguity, and evidence context.');
    case 'Ranked SongID track candidate.':
      return interfaceText('Ranked SongID track candidate.');
    case 'Album candidate near the current SongID result.':
      return interfaceText('Album candidate near the current SongID result.');
    case 'Artist candidate near the current SongID result.':
      return interfaceText('Artist candidate near the current SongID result.');
    case 'Candidate attached to a decomposed SongID segment.':
      return interfaceText('Candidate attached to a decomposed SongID segment.');
    case 'Mix cluster aggregated from contiguous segments.':
      return interfaceText('Mix cluster aggregated from contiguous segments.');
    case 'Pinned comparison node.':
      return interfaceText('Pinned comparison node.');
    case 'Track attached to the pinned comparison artist.':
      return interfaceText('Track attached to the pinned comparison artist.');
    case 'Album candidate resolves to this artist.':
      return interfaceText('Album candidate resolves to this artist.');
    case 'Track candidate resolves to this artist.':
      return interfaceText('Track candidate resolves to this artist.');
    case 'Track candidate co-occurred in the same identification neighborhood.':
      return interfaceText('Track candidate co-occurred in the same identification neighborhood.');
    case 'Artist candidate co-occurred in the same identification neighborhood.':
      return interfaceText('Artist candidate co-occurred in the same identification neighborhood.');
    case 'MusicBrainz release-graph expansion.':
      return interfaceText('MusicBrainz release-graph expansion.');
    case 'Track candidate shares artist context with the selected album.':
      return interfaceText('Track candidate shares artist context with the selected album.');
    case 'Timestamp/chapter decomposition linked this section to the seed neighborhood.':
      return interfaceText('Timestamp/chapter decomposition linked this section to the seed neighborhood.');
    case 'Exact track identity.':
      return interfaceText('Exact track identity.');
    case 'Plausible track identity.':
      return interfaceText('Plausible track identity.');
    case 'Album candidate derived from SongID identity resolution.':
      return interfaceText('Album candidate derived from SongID identity resolution.');
    case 'Artist context derived from SongID resolution.':
      return interfaceText('Artist context derived from SongID resolution.');
    case 'Mix or timestamp decomposition branch.':
      return interfaceText('Mix or timestamp decomposition branch.');
    case 'Segment-level candidate search path.':
      return interfaceText('Segment-level candidate search path.');
    case 'Detected mix cluster from segment decomposition.':
      return interfaceText('Detected mix cluster from segment decomposition.');
    case 'Segment belongs to this mix cluster.':
      return interfaceText('Segment belongs to this mix cluster.');
    case 'User-pinned comparison between the current seed and another graph node.':
      return interfaceText('User-pinned comparison between the current seed and another graph node.');
    case 'Track branch attached to the pinned comparison artist.':
      return interfaceText('Track branch attached to the pinned comparison artist.');
    case 'Artist supplied directly as fallback graph context.':
      return interfaceText('Artist supplied directly as fallback graph context.');
    case 'Album supplied directly as fallback graph context.':
      return interfaceText('Album supplied directly as fallback graph context.');
    case 'Track title supplied directly as fallback graph context.':
      return interfaceText('Track title supplied directly as fallback graph context.');
    default:
      return reason;
  }
};

export const localizeDiscoveryGraphEvidenceLaneLabel = (lane, label = '') => {
  switch (lane) {
    case 'identity':
      return interfaceText('Identity');
    case 'byzantine':
      return interfaceText('Byzantine');
    case 'action':
      return interfaceText('Action');
    case 'metadata':
      return interfaceText('Metadata');
    case 'confidence':
      return interfaceText('Confidence');
    case 'evidence':
      return interfaceText('Evidence');
    case 'provenance':
      return interfaceText('Provenance');
    default:
      return label || lane;
  }
};

export const localizeDiscoveryGraphEvidenceLaneSummary = (lane) => {
  const source = String(lane?.summary || '');
  if (!source) return source;

  const attached = source.match(/^(\d+) evidence items? attached\.$/u);
  if (attached) {
    const count = formatRegionalNumber(Number(attached[1]));
    return source.includes('item attached')
      ? interfaceText('{count} evidence item attached.', { count })
      : interfaceText('{count} evidence items attached.', { count });
  }

  if (lane?.lane === 'provenance') {
    const provenance = source.match(/^Source: (.+)\.$/u);
    if (provenance) {
      return interfaceText('Source: {provenance}.', { provenance: provenance[1] });
    }
  }

  const contributed = source.match(/^(.+) contributed (\d+(?:\.\d+)?)%\.$/u);
  if (contributed && lane?.lane) {
    return interfaceText('{label} contributed {percent}%.', {
      label: localizeDiscoveryGraphEvidenceLaneLabel(lane.lane, contributed[1]),
      percent: formatRegionalNumber(Number(contributed[2])),
    });
  }

  const observed = source.match(/^(.+) appears on (\d+) graph edges?\.$/u);
  if (observed && ['identity', 'byzantine', 'action', 'metadata', 'confidence'].includes(lane?.lane)) {
    const count = formatRegionalNumber(Number(observed[2]));
    const label = localizeDiscoveryGraphEvidenceLaneLabel(lane.lane, observed[1]);
    return observed[0].includes('edge.')
      ? interfaceText('{label} appears on {count} graph edge.', { count, label })
      : interfaceText('{label} appears on {count} graph edges.', { count, label });
  }

  return source;
};
