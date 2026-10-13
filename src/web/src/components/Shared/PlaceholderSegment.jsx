import React from 'react';
import { Header, Icon, Segment } from 'semantic-ui-react';
import { useInterfaceLanguage } from '../../lib/interfaceLocale';
import UI_LABELS from '../../lib/ui-labels.json';

const PlaceholderSegment = ({ caption, icon, size, ...rest }) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const className =
    size === 'small' ? 'placeholder-segment-small' : 'placeholder-segment';
  const localizedCaption = typeof caption === 'string' ? (
    <span dir={directionFor(caption)} lang={languageFor(caption)}>
      {Object.prototype.hasOwnProperty.call(UI_LABELS, caption) ? t(caption) : caption}
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
