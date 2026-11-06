import { interfaceText } from './interfaceLocale';
import { formatRegionalNumber } from './regionalFormat';

const getTotalSize = (files) =>
  files.reduce((total, file) => total + (file.size || 0), 0);

const unique = (values) => [...new Set(values.filter(Boolean))];
const asArray = (value) => (Array.isArray(value) ? value : []);

export const buildSearchActionPreview = ({
  candidateRank,
  communityQualitySummary,
  files = [],
  response = {},
  route = 'download',
} = {}) => {
  const selectedFiles = Array.isArray(files) ? files : [];
  const sourceProviders = asArray(response.sourceProviders).filter(Boolean);
  const providerLabels = sourceProviders.length
    ? sourceProviders
    : ['soulseek'];
  const lockedCount = selectedFiles.filter((file) => file.locked).length;
  const warnings = [];

  if (lockedCount > 0) {
    warnings.push(`${lockedCount} selected file${lockedCount === 1 ? '' : 's'} may be locked`);
  }

  if (!response.hasFreeUploadSlot) {
    warnings.push('No free upload slot is currently advertised');
  }

  if ((response.queueLength || 0) >= 5) {
    warnings.push(`Queue depth is ${response.queueLength}`);
  }

  if ((communityQualitySummary?.score || 0) <= -6) {
    warnings.push('Local caution signals exist for this peer');
  }

  if (communityQualitySummary?.override?.note) {
    warnings.push(`Local quality note: ${communityQualitySummary.override.note}`);
  }

  if (communityQualitySummary?.override?.mode === 'ignore') {
    warnings.push('Local quality signals are ignored by reviewer override');
  }

  if ((candidateRank?.score || 0) > 0 && candidateRank.score < 45) {
    warnings.push(`Candidate score is ${candidateRank.score}/100`);
  }

  return {
    candidateScore: candidateRank?.score ?? null,
    fileCount: selectedFiles.length,
    filenames: selectedFiles.map((file) => file.filename),
    lockedCount,
    providerLabels,
    route,
    totalSizeBytes: getTotalSize(selectedFiles),
    username: response.username || '',
    warnings: unique(warnings),
  };
};

export const formatSearchActionPreview = (preview) => {
  const formatWarning = (warning) => {
    let match = warning.match(/^(\d+) selected files? may be locked$/u);
    if (match) {
      const source = Number(match[1]) === 1
        ? '{count} selected file may be locked'
        : '{count} selected files may be locked';
      return interfaceText(source, { count: formatRegionalNumber(Number(match[1])) });
    }
    match = warning.match(/^Queue depth is (\d+)$/u);
    if (match) return interfaceText('Queue depth is {count}', { count: formatRegionalNumber(Number(match[1])) });
    match = warning.match(/^Local quality note: (.*)$/u);
    if (match) return interfaceText('Local quality note: {note}', { note: match[1] });
    match = warning.match(/^Candidate score is (\d+(?:\.\d+)?)\/100$/u);
    if (match) return interfaceText('Candidate score is {score}/100', { score: formatRegionalNumber(Number(match[1])) });
    switch (warning) {
      case 'No free upload slot is currently advertised':
        return interfaceText('No free upload slot is currently advertised');
      case 'Local caution signals exist for this peer':
        return interfaceText('Local caution signals exist for this peer');
      case 'Local quality signals are ignored by reviewer override':
        return interfaceText('Local quality signals are ignored by reviewer override');
      default:
        return warning;
    }
  };

  const routeLabel = preview.route === 'download'
    ? interfaceText('Download')
    : preview.route;
  const lines = [
    interfaceText('Action: {action}', { action: routeLabel }),
    interfaceText('Source: {source}', { source: preview.username || interfaceText('unknown') }),
    interfaceText('Providers: {providers}', { providers: preview.providerLabels.join(', ') }),
    interfaceText('Files: {count}', { count: formatRegionalNumber(preview.fileCount) }),
    interfaceText('Total bytes: {count}', { count: formatRegionalNumber(preview.totalSizeBytes) }),
  ];

  if (preview.candidateScore !== null) {
    lines.push(interfaceText('Candidate score: {score}/100', {
      score: formatRegionalNumber(preview.candidateScore),
    }));
  }

  if (preview.warnings.length > 0) {
    lines.push(interfaceText('Warnings:'));
    preview.warnings.forEach((warning) => lines.push(interfaceText('- {warning}', {
      warning: formatWarning(warning),
    })));
  }

  lines.push(interfaceText('Selected files:'));
  preview.filenames.forEach((filename) => lines.push(interfaceText('- {filename}', { filename })));

  return lines.join('\n');
};
