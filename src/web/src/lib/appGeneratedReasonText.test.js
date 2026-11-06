import {
  localizeMediaCoreMatchReason,
  localizeRealmSubjectIndexConflictDescription,
  localizeRealmSubjectIndexConflictType,
  localizeTasteRecommendationReason,
} from './appGeneratedReasonText';

describe('appGeneratedReasonText', () => {
  it('localizes known Realm Subject Index types and descriptions with dynamic values intact', () => {
    expect(localizeRealmSubjectIndexConflictType('external-id')).toBe('External ID conflict');
    expect(localizeRealmSubjectIndexConflictDescription({
      key: 'musicbrainz:recording',
      subjectId: 'subject-42',
      type: 'external-id',
    })).toBe("Subject 'subject-42' has conflicting external id values for 'musicbrainz:recording'.");
    expect(localizeRealmSubjectIndexConflictDescription({
      description: 'provider-generated detail',
      type: 'unknown-conflict',
    })).toBe('provider-generated detail');
    expect(localizeRealmSubjectIndexConflictType('future-type')).toBe('future-type');
  });

  it('localizes only known federated taste reasons and preserves creators and unknown details', () => {
    expect(localizeTasteRecommendationReason(
      'appeared in 12 trusted federated music libraries',
    )).toBe('Appeared in 12 trusted federated music libraries');
    expect(localizeTasteRecommendationReason(
      'near your federated music graph for A&B Artist',
    )).toBe('Near your federated music graph for A&B Artist');
    expect(localizeTasteRecommendationReason('provider reason: keep verbatim'))
      .toBe('provider reason: keep verbatim');
  });

  it('localizes known MediaCore match reasons and preserves unknown backend text', () => {
    expect(localizeMediaCoreMatchReason('MBID + duration match')).toBe('MBID + duration match');
    expect(localizeMediaCoreMatchReason('Verification failed: only Weak confidence'))
      .toBe('Verification failed: only Weak confidence');
    expect(localizeMediaCoreMatchReason('future match detail')).toBe('future match detail');
  });
});
