import { interfaceText } from './interfaceLocale';

export const localizeSearchCandidateRankingReason = (reason) => {
  switch (reason) {
    case 'strong filename match':
      return interfaceText('strong filename match');
    case 'partial filename match':
      return interfaceText('partial filename match');
    case 'weak filename match':
      return interfaceText('weak filename match');
    case 'no media files visible':
      return interfaceText('no media files visible');
    case 'lossless fast-good-enough candidate':
      return interfaceText('lossless fast-good-enough candidate');
    case 'high bitrate fast-good-enough candidate':
      return interfaceText('high bitrate fast-good-enough candidate');
    case 'limited fast-good-enough quality evidence':
      return interfaceText('limited fast-good-enough quality evidence');
    case 'broad folder candidate':
      return interfaceText('broad folder candidate');
    case 'small folder candidate':
      return interfaceText('small folder candidate');
    case 'mostly lossless files':
      return interfaceText('mostly lossless files');
    case 'mixed lossless files':
      return interfaceText('mixed lossless files');
    case 'no lossless signal':
      return interfaceText('no lossless signal');
    case 'plausible file sizes':
      return interfaceText('plausible file sizes');
    case 'mixed file size evidence':
      return interfaceText('mixed file size evidence');
    case 'free upload slot':
      return interfaceText('free upload slot');
    case 'queued upload':
      return interfaceText('queued upload');
    case 'short queue':
      return interfaceText('short queue');
    case 'long queue':
      return interfaceText('long queue');
    case 'fast peer':
      return interfaceText('fast peer');
    case 'trusted download history':
      return interfaceText('trusted download history');
    case 'poor download history':
      return interfaceText('poor download history');
    case 'limited download history':
      return interfaceText('limited download history');
    case 'local source available':
      return interfaceText('local source available');
    case 'mesh source available':
      return interfaceText('mesh source available');
    case 'local quality signals ignored':
      return interfaceText('local quality signals ignored');
    case 'local trust override':
      return interfaceText('local trust override');
    case 'local caution override':
      return interfaceText('local caution override');
    case 'positive local quality signals':
      return interfaceText('positive local quality signals');
    case 'local caution signals':
      return interfaceText('local caution signals');
    case 'mixed local quality signals':
      return interfaceText('mixed local quality signals');
    case 'preferred extension match':
      return interfaceText('preferred extension match');
    case 'missing preferred extension':
      return interfaceText('missing preferred extension');
    case 'preferred lossless match':
      return interfaceText('preferred lossless match');
    case 'missing preferred lossless files':
      return interfaceText('missing preferred lossless files');
    case 'preferred bitrate match':
      return interfaceText('preferred bitrate match');
    case 'below preferred bitrate':
      return interfaceText('below preferred bitrate');
    default:
      return reason;
  }
};
