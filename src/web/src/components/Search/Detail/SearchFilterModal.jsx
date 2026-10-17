import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import {
  parseFiltersFromString,
  serializeFiltersToString,
} from '../../../lib/searches';
import React, { useEffect, useState } from 'react';
import { Form, Header, Icon, Modal, Segment } from 'semantic-ui-react';
import TooltipButton from '../../Shared/TooltipButton';


const Button = TooltipButton;

const asArray = (value) => (Array.isArray(value) ? value : []);

const SearchFilterModal = ({ filterString, onChange, trigger }) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const localized = (source) => (
    <span dir={directionFor(source)} lang={languageFor(source)}>{t(source)}</span>
  );
  const inputLanguage = (source) => ({ dir: directionFor(source), lang: languageFor(source) });
  const [open, setOpen] = useState(false);
  const [filters, setFilters] = useState({});

  useEffect(() => {
    if (open) {
      setFilters(parseFiltersFromString(filterString || ''));
    }
  }, [filterString, open]);

  const handleChange = (key, value) => {
    setFilters((previous) => ({ ...previous, [key]: value }));
  };

  const handleSave = () => {
    const newString = serializeFiltersToString(filters);
    onChange(newString);
    setOpen(false);
  };

  return (
    <Modal
      onClose={() => setOpen(false)}
      onOpen={() => setOpen(true)}
      open={open}
      size="small"
      trigger={trigger}
    >
      <Header
        content={localized('Advanced Search Filters')}
        icon="filter"
      />
      <Modal.Content>
        <Form>
          <Segment>
            <Header size="tiny">{localized('Audio Properties')}</Header>
            <Form.Group widths="equal">
              <Form.Input
                {...inputLanguage('Min Bitrate (kbps)')}
                label={localized('Min Bitrate (kbps)')}
                min={0}
                onChange={(event) =>
                  handleChange(
                    'minBitRate',
                    Number.parseInt(event.target.value, 10) || 0,
                  )
                }
                placeholder={t('e.g. 320')}
                type="number"
                value={filters.minBitRate || ''}
              />
              <Form.Input
                {...inputLanguage('Min Bit Depth')}
                label={localized('Min Bit Depth')}
                min={0}
                onChange={(event) =>
                  handleChange(
                    'minBitDepth',
                    Number.parseInt(event.target.value, 10) || 0,
                  )
                }
                placeholder={t('e.g. 16 or 24')}
                type="number"
                value={filters.minBitDepth || ''}
              />
              <Form.Input
                {...inputLanguage('Min Sample Rate (Hz)')}
                label={localized('Min Sample Rate (Hz)')}
                min={0}
                onChange={(event) =>
                  handleChange(
                    'minSampleRate',
                    Number.parseInt(event.target.value, 10) || 0,
                  )
                }
                placeholder={t('e.g. 44100')}
                type="number"
                value={filters.minSampleRate || ''}
              />
            </Form.Group>
            <Form.Group inline>
              <Form.Checkbox
                checked={filters.isCBR || false}
                {...inputLanguage('CBR')}
                label={localized('CBR')}
                onChange={(_, { checked }) => handleChange('isCBR', checked)}
              />
              <Form.Checkbox
                checked={filters.isVBR || false}
                {...inputLanguage('VBR')}
                label={localized('VBR')}
                onChange={(_, { checked }) => handleChange('isVBR', checked)}
              />
              <Form.Checkbox
                checked={filters.isLossless || false}
                {...inputLanguage('Lossless')}
                label={localized('Lossless')}
                onChange={(_, { checked }) =>
                  handleChange('isLossless', checked)
                }
              />
              <Form.Checkbox
                checked={filters.isLossy || false}
                {...inputLanguage('Lossy')}
                label={localized('Lossy')}
                onChange={(_, { checked }) => handleChange('isLossy', checked)}
              />
            </Form.Group>
            <Form.Group>
              <Form.Field>
                <label>{localized('Quality Presets')}</label>
                <Button.Group>
                  <Button
                    compact
                    onClick={() => {
                      handleChange('minBitRate', 320);
                      handleChange('isLossless', false);
                      handleChange('isLossy', true);
                    }}
                    size="small"
                    type="button"
                    tooltip="Set a 320 kbps minimum and prefer lossy results for a high-bitrate match."
                  >
                    <Icon name="music" />
                    {localized('High Quality (320kbps+)')}
                  </Button>
                  <Button
                    compact
                    onClick={() => {
                      handleChange('isLossless', true);
                      handleChange('isLossy', false);
                      handleChange('minBitDepth', 16);
                      handleChange('minSampleRate', 44_100);
                    }}
                    size="small"
                    type="button"
                    tooltip="Require lossless files with at least 16-bit, 44.1 kHz audio."
                  >
                    <Icon name="star" />
                    {localized('Lossless Only')}
                  </Button>
                  <Button
                    compact
                    onClick={() => {
                      handleChange('minBitRate', 0);
                      handleChange('isLossless', false);
                      handleChange('isLossy', false);
                      handleChange('minBitDepth', 0);
                      handleChange('minSampleRate', 0);
                    }}
                    size="small"
                    type="button"
                    tooltip="Clear the bitrate, lossless, bit-depth, and sample-rate filters."
                  >
                    <Icon name="eraser" />
                    {localized('Clear Quality')}
                  </Button>
                </Button.Group>
              </Form.Field>
            </Form.Group>
          </Segment>

          <Segment>
            <Header size="tiny">{localized('File Properties')}</Header>
            <Form.Group widths="equal">
              <Form.Input
                {...inputLanguage('Min Size (bytes)')}
                label={localized('Min Size (bytes)')}
                min={0}
                onChange={(event) =>
                  handleChange(
                    'minFileSize',
                    Number.parseInt(event.target.value, 10) || 0,
                  )
                }
                placeholder={t('e.g. 1048576 (1MB)')}
                type="number"
                value={filters.minFileSize || ''}
              />
              <Form.Input
                {...inputLanguage('Max Size (bytes)')}
                label={localized('Max Size (bytes)')}
                min={0}
                onChange={(event) =>
                  handleChange(
                    'maxFileSize',
                    event.target.value
                      ? Number.parseInt(event.target.value, 10)
                      : Number.MAX_SAFE_INTEGER,
                  )
                }
                placeholder={t('e.g. 104857600 (100MB)')}
                type="number"
                value={
                  filters.maxFileSize === Number.MAX_SAFE_INTEGER
                    ? ''
                    : filters.maxFileSize
                }
              />
            </Form.Group>
            <Form.Group widths="equal">
              <Form.Input
                {...inputLanguage('Min Duration (seconds)')}
                label={localized('Min Duration (seconds)')}
                min={0}
                onChange={(event) =>
                  handleChange(
                    'minLength',
                    Number.parseInt(event.target.value, 10) || 0,
                  )
                }
                placeholder={t('e.g. 180 (3 min)')}
                type="number"
                value={filters.minLength || ''}
              />
              <Form.Input
                {...inputLanguage('Min Files in Folder')}
                label={localized('Min Files in Folder')}
                min={0}
                onChange={(event) =>
                  handleChange(
                    'minFilesInFolder',
                    Number.parseInt(event.target.value, 10) || 0,
                  )
                }
                placeholder={t('e.g. 8')}
                type="number"
                value={filters.minFilesInFolder || ''}
              />
            </Form.Group>
          </Segment>

          <Segment>
            <Header size="tiny">{localized('Keywords')}</Header>
            <Form.Input
              {...inputLanguage('Must Include (space separated)')}
              label={localized('Must Include (space separated)')}
              onChange={(event) =>
                handleChange(
                  'include',
                  event.target.value.split(' ').filter((t) => t.trim()),
                )
              }
              placeholder={interfaceText("remix instrumental")}
              value={asArray(filters.include).join(' ')}
             {...interfaceTextProps("remix instrumental")}/>
            <Form.Input
              {...inputLanguage('Must Exclude (space separated)')}
              label={localized('Must Exclude (space separated)')}
              onChange={(event) =>
                handleChange(
                  'exclude',
                  event.target.value.split(' ').filter((t) => t.trim()),
                )
              }
              placeholder={interfaceText("live demo")}
              value={asArray(filters.exclude).join(' ')}
             {...interfaceTextProps("live demo")}/>
          </Segment>

          <Segment>
            <Header size="tiny">{localized('Format/Codec')}</Header>
            <Form.Group>
              <Form.Field>
                <label>{localized('File Extensions (space separated)')}</label>
                <Form.Input
                  onChange={(event) =>
                    handleChange(
                      'extensions',
                      event.target.value
                        .split(' ')
                        .filter((t) => t.trim())
                        .map((t) => t.toLowerCase().replace(/^\./, '')),
                    )
                  }
                  {...inputLanguage('File Extensions (space separated)')}
                  placeholder={interfaceText("flac mp3 wav")}
                  value={asArray(filters.extensions).join(' ')}
                 {...interfaceTextProps("flac mp3 wav")}/>
                <label style={{ fontSize: '0.9em', opacity: 0.8 }}>
                  {localized('Filter by file extension (e.g., flac, mp3, wav, m4a)')}
                </label>
              </Form.Field>
            </Form.Group>
          </Segment>

          <Segment>
            <Header size="tiny">{localized('Ranking Preferences')}</Header>
            <Form.Group widths="equal">
              <Form.Input
                {...inputLanguage('Prefer Extensions')}
                label={localized('Prefer Extensions')}
                onChange={(event) =>
                  handleChange(
                    'preferExtensions',
                    event.target.value
                      .split(' ')
                      .filter((t) => t.trim())
                      .map((t) => t.toLowerCase().replace(/^\./, '')),
                  )
                }
                placeholder={interfaceText("flac wav")}
                value={asArray(filters.preferExtensions).join(' ')}
               {...interfaceTextProps("flac wav")}/>
              <Form.Input
                {...inputLanguage('Prefer Min Bitrate (kbps)')}
                label={localized('Prefer Min Bitrate (kbps)')}
                min={0}
                onChange={(event) =>
                  handleChange(
                    'preferMinBitRate',
                    Number.parseInt(event.target.value, 10) || 0,
                  )
                }
                placeholder={t('e.g. 320')}
                type="number"
                value={filters.preferMinBitRate || ''}
              />
            </Form.Group>
            <Form.Checkbox
              checked={filters.preferLossless || false}
                {...inputLanguage('Prefer lossless without hiding lossy fallback candidates')}
                label={localized('Prefer lossless without hiding lossy fallback candidates')}
              onChange={(_, { checked }) =>
                handleChange('preferLossless', checked)
              }
            />
          </Segment>
        </Form>
      </Modal.Content>
      <Modal.Actions>
        <Button
          onClick={() => setOpen(false)}
          tooltip="Close without applying these search filters."
        >
          {localized('Cancel')}
        </Button>
        <Button
          onClick={handleSave}
          primary
          tooltip="Apply these filters to the current search."
        >
          {localized('Apply Filters')}
        </Button>
      </Modal.Actions>
    </Modal>
  );
};

export default SearchFilterModal;
