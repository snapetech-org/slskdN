import {
  localizeDiscoveryGraphEdgeType,
  localizeDiscoveryGraphEvidenceLaneLabel,
  localizeDiscoveryGraphEvidenceLaneSummary,
  localizeDiscoveryGraphNodeType,
  localizeDiscoveryGraphReason,
  localizeDiscoveryGraphSummary,
} from './discoveryGraphLocale';

describe('discoveryGraphLocale', () => {
  it('localizes allowlisted types and leaves unknown values unchanged', () => {
    expect(localizeDiscoveryGraphNodeType('songid_run')).toBe('SongID run');
    expect(localizeDiscoveryGraphNodeType('remote_extension')).toBe('remote_extension');
    expect(localizeDiscoveryGraphEdgeType('candidate_neighbor')).toBe('Candidate neighbor');
    expect(localizeDiscoveryGraphEdgeType('remote_extension')).toBe('remote_extension');
  });

  it('localizes known generated summaries and reasons only', () => {
    expect(localizeDiscoveryGraphSummary(
      'Fallback discovery seed without a SongID run context.',
    )).toBe('Fallback discovery seed without a SongID run context.');
    expect(localizeDiscoveryGraphReason('Exact track identity.')).toBe('Exact track identity.');
    expect(localizeDiscoveryGraphReason('Remote provider detail')).toBe('Remote provider detail');
  });

  it('localizes known evidence labels and generated summaries while preserving provenance data', () => {
    expect(localizeDiscoveryGraphEvidenceLaneLabel('byzantine', 'Byzantine'))
      .toBe('Byzantine');
    expect(localizeDiscoveryGraphEvidenceLaneLabel('extension_lane', 'Extension Lane'))
      .toBe('Extension Lane');
    expect(localizeDiscoveryGraphEvidenceLaneSummary({
      lane: 'metadata',
      summary: 'Metadata contributed 82%.',
    })).toBe('Metadata contributed 82%.');
    expect(localizeDiscoveryGraphEvidenceLaneSummary({
      lane: 'evidence',
      summary: '2 evidence items attached.',
    })).toBe('2 evidence items attached.');
    expect(localizeDiscoveryGraphEvidenceLaneSummary({
      lane: 'provenance',
      summary: 'Source: songid_segment.',
    })).toBe('Source: songid_segment.');
    expect(localizeDiscoveryGraphEvidenceLaneSummary({
      lane: 'extension_lane',
      summary: 'Extension-generated explanation',
    })).toBe('Extension-generated explanation');
  });
});
