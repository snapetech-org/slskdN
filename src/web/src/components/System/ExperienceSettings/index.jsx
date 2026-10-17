import { interfaceText, interfaceTextProps, INTERFACE_LANGUAGE_OPTIONS, resetInterfaceLanguage, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { REGIONAL_FORMAT_OPTIONS } from '../../../lib/regionalFormat';

import React, { useEffect, useState } from 'react';
import {
  Button,
  Card,
  Checkbox,
  Form,
  Header,
  Icon,
  Message,
  Popup,
  Segment,
} from 'semantic-ui-react';
import {
  EXPERIENCE_PREFERENCES_STORAGE_KEY,
  notifyExperiencePreferencesChanged,
  setExperiencePreferencesSnapshot,
} from '../../../lib/experiencePreferences';

const storageKey = EXPERIENCE_PREFERENCES_STORAGE_KEY;

const defaults = {
  regionalFormat: 'system',
  playerVisible: true,
  searchAlbumCandidatesVisible: true,
};

const isObject = (value) =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

const readStoredPreferenceRecord = () => {
  try {
    const stored = JSON.parse(localStorage.getItem(storageKey) || '{}');
    return isObject(stored) ? stored : {};
  } catch {
    return {};
  }
};

const normalizeStoredPreferences = (stored) => {
  if (!isObject(stored)) {
    return { ...defaults };
  }

  return {
    regionalFormat: typeof stored.regionalFormat === 'string' && REGIONAL_FORMAT_OPTIONS.some((option) => option.value === stored.regionalFormat)
      ? stored.regionalFormat
      : defaults.regionalFormat,
    playerVisible: typeof stored.playerVisible === 'boolean'
      ? stored.playerVisible
      : defaults.playerVisible,
    searchAlbumCandidatesVisible: typeof stored.searchAlbumCandidatesVisible === 'boolean'
      ? stored.searchAlbumCandidatesVisible
      : defaults.searchAlbumCandidatesVisible,
  };
};

const readStoredPreferences = () =>
  normalizeStoredPreferences(readStoredPreferenceRecord());

const buildReport = (form) =>
  [
    'slskdN browser experience preferences',
    `Regional format: ${form.regionalFormat}`,
    `Search: album_candidates=${form.searchAlbumCandidatesVisible}`,
    `Player: visible=${form.playerVisible}`,
  ].join('\n');

const ExperienceSettings = () => {
  const [form, setForm] = useState(defaults);
  const [feedback, setFeedback] = useState(null);
  const { language, setLanguage, t, languageFor, directionFor } = useInterfaceLanguage();
  const localized = (source) => (
    <span dir={directionFor(source)} lang={languageFor(source)}>
      {t(source)}
    </span>
  );

  useEffect(() => {
    setForm(readStoredPreferences());
  }, []);

  const update = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
    setFeedback(null);
  };

  const save = () => {
    setExperiencePreferencesSnapshot(form);
    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify({ ...readStoredPreferenceRecord(), ...form }),
      );
      notifyExperiencePreferencesChanged();
      setFeedback({
        message: interfaceText("Experience preferences saved locally in this browser."),
        type: 'success',
      });
    } catch {
      notifyExperiencePreferencesChanged();
      setFeedback({
        message: interfaceText("Could not save browser preferences."),
        type: 'error',
      });
    }
  };

  const reset = () => {
    setExperiencePreferencesSnapshot(defaults);
    resetInterfaceLanguage();
    try {
      localStorage.removeItem(storageKey);
      setForm(defaults);
      notifyExperiencePreferencesChanged();
      setFeedback({
        message: interfaceText("Experience preferences reset to defaults."),
        type: 'success',
      });
    } catch {
      setForm(defaults);
      notifyExperiencePreferencesChanged();
      setFeedback({
        message: interfaceText("Could not reset browser preferences."),
        type: 'error',
      });
    }
  };

  const copyReport = async () => {
    try {
      if (typeof navigator.clipboard?.writeText !== 'function') throw new Error();

      await navigator.clipboard.writeText(buildReport(form));
      setFeedback({
        message: interfaceText("Experience preference report copied."),
        type: 'success',
      });
    } catch {
      setFeedback({
        message: interfaceText("Could not copy the preference report."),
        type: 'error',
      });
    }
  };

  return (
    <div className="experience-settings">
      <Segment>
        <Header as="h3">
          <Icon name="compass" />
          {localized('Experience Preferences')}
        </Header>
        <p>
          {localized('These choices are stored in this browser and do not change server configuration or start new searches or downloads. Hiding the player stops current playback and clears its local queue.')}
        </p>
      </Segment>

      {feedback && (
        <Message
          negative={feedback.type === 'error'}
          positive={feedback.type === 'success'}
          size="small"
        >
          {localized(feedback.message)}
        </Message>
      )}

      <Card.Group
        itemsPerRow={1}
        stackable
      >
        <Card fluid>
          <Card.Content>
            <Card.Header><Icon name="language" /> {localized('Interface language')}</Card.Header>
            <Card.Meta>{localized('Choose the language used for the interface.')} {localized('Other parts of the interface are still being localized.')}</Card.Meta>
          </Card.Content>
          <Card.Content>
            <Form>
              <Form.Select
                dir={directionFor('Interface language')}
                aria-label={t('Interface language')}
                label={localized('Interface language')}
                lang={languageFor('Interface language')}
                onChange={(_, { value }) => setLanguage(value)}
                options={INTERFACE_LANGUAGE_OPTIONS}
                value={language}
              />
            </Form>
          </Card.Content>
        </Card>
        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="globe" />
              {localized('Regional format')}
            </Card.Header>
            <Card.Meta>{localized('Choose how dates, times, and numbers are displayed. This setting is separate from interface language.')}</Card.Meta>
          </Card.Content>
          <Card.Content>
            <Form>
              <Form.Select
                dir={directionFor('Regional format')}
                aria-label={t('Regional format')}
                label={localized('Date, time, and number format')}
                lang={languageFor('Regional format')}
                onChange={(_, { value }) => update('regionalFormat', value)}
                options={REGIONAL_FORMAT_OPTIONS}
                value={form.regionalFormat}
              />
            </Form>
          </Card.Content>
        </Card>
        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="search" />
              {localized('Search')}
            </Card.Header>
            <Card.Meta>{localized('Control the local review panel shown with song search results.')}</Card.Meta>
          </Card.Content>
          <Card.Content>
            <Form>
              <Popup
                content={localized('Show the album-candidate review panel below song searches. It only organizes results already received and does not start another search or contact more peers.')}
                trigger={
                  <Checkbox
                    aria-label={t('Show album candidates preference')}
                    dir={directionFor('Show album candidates preference')}
                    lang={languageFor('Show album candidates preference')}
                    checked={form.searchAlbumCandidatesVisible}
                    label={localized('Show album candidates')}
                    onChange={(_, { checked }) =>
                      update('searchAlbumCandidatesVisible', Boolean(checked))
                    }
                    toggle
                  />
                }
              />
            </Form>
          </Card.Content>
        </Card>

        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="play circle" />
              {localized('Player')}
            </Card.Header>
            <Card.Meta>{localized('Show or hide the persistent music player across the Web UI.')}</Card.Meta>
          </Card.Content>
          <Card.Content>
            <Form>
              <Popup
                content={localized('Hide the player across the Web UI. Current playback stops and the browser player queue is cleared; the Show player control stays available at the bottom of the page.')}
                trigger={
                  <Checkbox
                    aria-label={t('Show browser player preference')}
                    dir={directionFor('Show browser player preference')}
                    lang={languageFor('Show browser player preference')}
                    checked={form.playerVisible}
                    label={localized('Show browser player')}
                    onChange={(_, { checked }) =>
                      update('playerVisible', Boolean(checked))
                    }
                    toggle
                  />
                }
              />
            </Form>
          </Card.Content>
        </Card>
      </Card.Group>

      <div className="integration-actions">
        <Popup
          content={localized('Save these choices to this browser. This does not edit server configuration or start a search or download. Hiding the player stops current playback and clears its local queue.')}
          trigger={
            <Button
              dir={directionFor('Save Local Preferences')}
              lang={languageFor('Save Local Preferences')}
              icon
              labelPosition="left"
              onClick={save}
              primary
            >
              <Icon name="save" />
              {localized('Save Local Preferences')}
            </Button>
          }
        />
        <Popup
          content={localized('Clear browser-local experience preferences and restore the supported defaults.')}
          trigger={
            <Button
              dir={directionFor('Reset')}
              lang={languageFor('Reset')}
              icon
              labelPosition="left"
              onClick={reset}
            >
              <Icon name="undo" />
              {localized('Reset')}
            </Button>
          }
        />
        <Popup
          content={localized('Copy a short report of these browser-local choices to include with a support request.')}
          trigger={
            <Button
              dir={directionFor('Copy Report')}
              lang={languageFor('Copy Report')}
              icon
              labelPosition="left"
              onClick={copyReport}
            >
              <Icon name="copy" />
              {localized('Copy Report')}
            </Button>
          }
        />
      </div>
    </div>
  );
};

export default ExperienceSettings;
