import { REGIONAL_FORMAT_OPTIONS } from '../../../lib/regionalFormat';
import { INTERFACE_LANGUAGE_OPTIONS, useInterfaceLanguage } from '../../../lib/interfaceLocale';
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

const getPreferenceActionError = (error, fallback) => {
  const data = error?.response?.data;
  if (typeof data === 'string') return data;
  if (data && typeof data === 'object') {
    return data.detail || data.message || data.title || JSON.stringify(data);
  }

  return error?.message || fallback;
};

const ExperienceSettings = () => {
  const [form, setForm] = useState(defaults);
  const [feedback, setFeedback] = useState(null);
  const { language, setLanguage, t } = useInterfaceLanguage();

  useEffect(() => {
    setForm(readStoredPreferences());
  }, []);

  const update = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
    setFeedback(null);
  };

  const save = () => {
    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify({ ...readStoredPreferenceRecord(), ...form }),
      );
      notifyExperiencePreferencesChanged();
      setFeedback({
        message: 'Experience preferences saved locally in this browser.',
        type: 'success',
      });
    } catch (error) {
      setFeedback({
        message: getPreferenceActionError(error, 'Could not save browser preferences.'),
        type: 'error',
      });
    }
  };

  const reset = () => {
    try {
      localStorage.removeItem(storageKey);
      setForm(defaults);
      notifyExperiencePreferencesChanged();
      setFeedback({
        message: 'Experience preferences reset to defaults.',
        type: 'success',
      });
    } catch (error) {
      setFeedback({
        message: getPreferenceActionError(error, 'Could not reset browser preferences.'),
        type: 'error',
      });
    }
  };

  const copyReport = async () => {
    try {
      if (typeof navigator.clipboard?.writeText !== 'function') {
        throw new Error('Clipboard access is not available in this browser.');
      }

      await navigator.clipboard.writeText(buildReport(form));
      setFeedback({
        message: 'Experience preference report copied.',
        type: 'success',
      });
    } catch (error) {
      setFeedback({
        message: getPreferenceActionError(error, 'Could not copy the preference report.'),
        type: 'error',
      });
    }
  };

  return (
    <div className="experience-settings">
      <Segment>
        <Header as="h3">
          <Icon name="compass" />
          Experience Preferences
        </Header>
        <p>
          These choices are stored in this browser and do not change server
          configuration or start new searches or downloads. Hiding the player
          stops current playback and clears its local queue.
        </p>
      </Segment>

      {feedback && (
        <Message
          negative={feedback.type === 'error'}
          positive={feedback.type === 'success'}
          size="small"
        >
          {feedback.message}
        </Message>
      )}

      <Card.Group
        itemsPerRow={1}
        stackable
      >
        <Card fluid>
          <Card.Content>
            <Card.Header><Icon name="language" /> {t('Interface language')}</Card.Header>
            <Card.Meta>{t('Choose the language used for the interface.')} {t('Translations currently cover navigation and language settings; most other screens are still in English.')}</Card.Meta>
          </Card.Content>
          <Card.Content>
            <Form>
              <Form.Select
                aria-label={t('Interface language')}
                label={t('Interface language')}
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
              {t('Regional format')}
            </Card.Header>
            <Card.Meta>{t('Choose how dates, times, and numbers are displayed. This setting is separate from interface language.')}</Card.Meta>
          </Card.Content>
          <Card.Content>
            <Form>
              <Form.Select
                aria-label={t('Regional format')}
                label={t('Date, time, and number format')}
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
              Search
            </Card.Header>
            <Card.Meta>Control the local review panel shown with song search results.</Card.Meta>
          </Card.Content>
          <Card.Content>
            <Form>
              <Popup
                content="Show the album-candidate review panel below song searches. It only organizes results already received and does not start another search or contact more peers."
                trigger={
                  <Checkbox
                    aria-label="Show album candidates preference"
                    checked={form.searchAlbumCandidatesVisible}
                    label="Show album candidates"
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
              Player
            </Card.Header>
            <Card.Meta>Show or hide the persistent music player across the Web UI.</Card.Meta>
          </Card.Content>
          <Card.Content>
            <Form>
              <Popup
                content="Hide the player across the Web UI. Current playback stops and the browser player queue is cleared; the Show player control stays available at the bottom of the page."
                trigger={
                  <Checkbox
                    aria-label="Show browser player preference"
                    checked={form.playerVisible}
                    label="Show browser player"
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
          content="Save these choices to this browser. This does not edit server configuration or start a search or download. Hiding the player stops current playback and clears its local queue."
          trigger={
            <Button
              icon
              labelPosition="left"
              onClick={save}
              primary
            >
              <Icon name="save" />
              Save Local Preferences
            </Button>
          }
        />
        <Popup
          content="Clear browser-local experience preferences and restore the supported defaults."
          trigger={
            <Button
              icon
              labelPosition="left"
              onClick={reset}
            >
              <Icon name="undo" />
              Reset
            </Button>
          }
        />
        <Popup
          content="Copy a short report of these browser-local choices to include with a support request."
          trigger={
            <Button
              icon
              labelPosition="left"
              onClick={copyReport}
            >
              <Icon name="copy" />
              Copy Report
            </Button>
          }
        />
      </div>
    </div>
  );
};

export default ExperienceSettings;
