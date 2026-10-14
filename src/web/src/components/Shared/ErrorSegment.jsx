import React from 'react';
import { Header, Icon, Segment } from 'semantic-ui-react';
import { useInterfaceLanguage } from '../../lib/interfaceLocale';

const ErrorSegment = ({ caption, icon = 'x', suppressPrefix = false, translateCaption = false }) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const localizedCaption = typeof caption === 'string' && translateCaption ? (
    <span dir={directionFor(caption)} lang={languageFor(caption)}>
      {t(caption)}
    </span>
  ) : typeof caption === 'string' ? <span>{caption}</span> : caption;
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
