import React from 'react';
import { Header, Icon, Segment } from 'semantic-ui-react';
import { useInterfaceLanguage } from '../../lib/interfaceLocale';
import UI_LABELS from '../../lib/ui-labels.json';

const ErrorSegment = ({ caption, icon = 'x', suppressPrefix = false }) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const captionSource = typeof caption === 'string' &&
    Object.prototype.hasOwnProperty.call(UI_LABELS, caption)
    ? caption
    : 'The request failed. Try again.';
  const localizedCaption = typeof caption === 'string' ? (
    <span dir={directionFor(captionSource)} lang={languageFor(captionSource)}>
      {t(captionSource)}
    </span>
  ) : caption;
  return (
    <Segment
      basic
      className="error-segment"
      placeholder
    >
      <Header icon>
        <Icon
          color="red"
          name={icon}
        />
        {!suppressPrefix && (
          <span dir={directionFor('Error:')} lang={languageFor('Error:')}>
            {t('Error:')}{' '}
          </span>
        )}
        {localizedCaption}
      </Header>
    </Segment>
  );
};

export default ErrorSegment;
