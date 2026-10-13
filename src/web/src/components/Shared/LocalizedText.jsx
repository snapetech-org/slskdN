import React from 'react';
import { useInterfaceLanguage } from '../../lib/interfaceLocale';

const LocalizedText = ({ as: Element = 'span', source, values, children, ...props }) => {
  const { directionFor, languageFor, t } = useInterfaceLanguage();
  const text = typeof source === 'string' ? t(source, values) : children;

  return (
    <Element dir={typeof source === 'string' ? directionFor(source) : undefined}
      lang={typeof source === 'string' ? languageFor(source) : undefined}
      {...props}
    >
      {text}
    </Element>
  );
};

export default LocalizedText;
