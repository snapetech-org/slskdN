import React from 'react';
import { act, cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { interfacePresentationText, interfaceText, interfaceTextProps, resetInterfaceLanguage, setInterfaceLanguage } from '../../lib/interfaceLocale';
import LocalizedText, { LocalizedRichText } from './LocalizedText';
import { AutoFixableIssueCount, NewMessageCount } from './LocalizedCounts';
import { evaluateMeshEvidenceEntries, getMeshEvidenceReasonSource, getMeshEvidenceReasonValues } from '../../lib/meshEvidencePolicy';
import { setExperiencePreference } from '../../lib/experiencePreferences';
import PlayCollectionItemButton from '../Player/PlayCollectionItemButton';

vi.mock('../Player/PlayerContext', () => ({ usePlayer: () => ({ playItem: vi.fn(), playerVisible: true }) }));
// Synthetic targets exercise wiring and metadata, not translation correctness.
const fixture = {
  '↓ New messages: {count}': 'رسائل جديدة: {count}',
  'Queue fixes (auto-fixable issues: {count})': 'مشكلات قابلة للإصلاح: {count}',
  'Play {track} in the browser player': 'تشغيل {track}',
  'Play this item through the local stream endpoint and update your now-playing status.': 'تشغيل العنصر',
  'untrusted provenance tier: {tier}': 'مستوى المصدر: {tier}',
  'publication: {label}; port: {port}': 'نشر: {label}؛ منفذ: {port}',
  label: 'عنوان',
};
beforeEach(() => { setExperiencePreference('regionalFormat', 'ar'); vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(fixture), { status: 200 }))); });
afterEach(async () => { cleanup(); setExperiencePreference('regionalFormat', 'system'); await act(async () => { await resetInterfaceLanguage(); }); vi.unstubAllGlobals(); });

describe('localization presentation boundaries', () => {
  it.each([0, 1, 2, 11])('uses neutral count sources and isolated Arabic values at count %i', async (count) => {
    await act(async () => { await setInterfaceLanguage('ar'); });
    const { container } = render(<><NewMessageCount count={count} /><AutoFixableIssueCount count={count} /></>);
    const labels = container.querySelectorAll('span[lang="ar"][dir="rtl"]');
    expect(labels).toHaveLength(2);
    for (const label of labels) expect(label.querySelector('bdi[dir="auto"]').textContent).toBe(new Intl.NumberFormat('ar').format(count));
  });

  it('uses regional formatting only for numeric reasons and updates displayed counts on preference changes', async () => {
    expect(getMeshEvidenceReasonValues({ id: 'low-confidence', parameters: { minimum: 0.75 } }, 'ar').minimum).toBe(new Intl.NumberFormat('ar').format(0.75));
    const opaque = { tier: '42/peer' };
    expect(getMeshEvidenceReasonValues({ id: 'untrusted-tier', parameters: opaque }, 'ar')).toBe(opaque);
    await act(async () => { await setInterfaceLanguage('ar'); });
    const { container } = render(<NewMessageCount count={1234} />);
    expect(container.querySelector('bdi').textContent).toBe(new Intl.NumberFormat('ar').format(1234));
    act(() => { setExperiencePreference('regionalFormat', 'de'); });
    expect(container.querySelector('bdi').textContent).toBe('1.234');
  });

  it('isolates native attribute/dialog values without mutating plain helper data', async () => {
    await act(async () => { await setInterfaceLanguage('ar'); });
    const source = 'Play {track} in the browser player';
    for (const track of ['user/{track}/العربية', 'room #1', '/music/a.mp3', 42, 'backend:timeout']) {
      expect(interfacePresentationText(source, { track })).toBe(`تشغيل \u2068${track}\u2069`);
      expect(interfaceText(source, { track })).toBe(`تشغيل ${track}`);
    }
    expect(interfaceTextProps(source)).toMatchObject({ lang: 'ar', dir: 'rtl' });
    await act(async () => { await setInterfaceLanguage('en'); });
    expect(interfacePresentationText(source, { track: 'raw' })).toBe('Play raw in the browser player');
  });

  it('puts source metadata on the actual player action and keeps the popup source separate', async () => {
    await act(async () => { await setInterfaceLanguage('ar'); });
    render(<PlayCollectionItemButton item={{ title: 'path/{track}/42', contentId: 'raw-id' }} />);
    const button = screen.getByRole('button', { name: 'تشغيل \u2068path/{track}/42\u2069' });
    expect(button).toHaveAttribute('lang', 'ar');
    expect(button).toHaveAttribute('dir', 'rtl');
  });

  it('keeps rich app-owned fragments localized and opaque primitive values isolated', async () => {
    await act(async () => { await setInterfaceLanguage('ar'); });
    const { container } = render(<LocalizedRichText source="publication: {label}; port: {port}" values={{ label: <LocalizedText source="label" />, port: 'localhost:8080/{label}' }} />);
    expect(container.firstChild).toHaveAttribute('lang', 'ar');
    expect(container.firstChild).toHaveAttribute('dir', 'rtl');
    expect(container.querySelector('span[lang="ar"] span')).toHaveTextContent('عنوان');
    expect(container.querySelector('bdi').textContent).toBe('localhost:8080/{label}');
  });

  it('rerenders stored mesh reasons in the new language without evaluating again', async () => {
    const review = evaluateMeshEvidenceEntries([{ provenance: { trustTier: 'raw/{tier}' }, confidence: 1, witnessCount: 3 }], { inboundTrustTier: 'trusted', evidenceReview: { minimumConfidence: 0.5, minimumWitnesses: 2 } });
    const reason = review.rejected[0].reasons.find(({ id }) => id === 'untrusted-tier');
    const snapshot = JSON.stringify(review);
    const { container } = render(<LocalizedText source={getMeshEvidenceReasonSource(reason)} values={reason.parameters} />);
    expect(container.textContent).toBe('untrusted provenance tier: raw/{tier}');
    await act(async () => { await setInterfaceLanguage('ar'); });
    expect(container.textContent).toBe('مستوى المصدر: raw/{tier}');
    expect(container.querySelector('bdi').textContent).toBe('raw/{tier}');
    expect(JSON.stringify(review)).toBe(snapshot);
  });
});
