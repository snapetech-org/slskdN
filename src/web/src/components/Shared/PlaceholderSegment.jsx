import React from 'react';
import { Header, Icon, Segment } from 'semantic-ui-react';
import { useInterfaceLanguage } from '../../lib/interfaceLocale';

const PlaceholderSegment = ({ caption, icon, size, ...rest }) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const className =
    size === 'small' ? 'placeholder-segment-small' : 'placeholder-segment';
  const localizedCaption = typeof caption === 'string' ? (
    <span dir={directionFor(caption)} lang={languageFor(caption)}>
      {languageFor(caption) !== 'en' ? t(caption) : caption}
    </span>
  ) : caption;

  return (
    <Segment
      basic
      className={className}
      placeholder
      {...rest}
    >
      <Header icon>
        <Icon name={icon} />
        {localizedCaption}
      </Header>
    </Segment>
  );
};

export default PlaceholderSegment;
