import React from 'react';
import { useInterfaceLanguage } from '../../lib/interfaceLocale';

const isolateRtlValues = (template, values) => {
  if (typeof template !== 'string' || !values) return template;

  const parts = [];
  const placeholderPattern = /\{([a-zA-Z][a-zA-Z0-9_]*)\}/g;
  let lastIndex = 0;
  let partIndex = 0;
  let match;

  while ((match = placeholderPattern.exec(template)) !== null) {
    const value = values[match[1]];
    if (typeof value !== 'string' && typeof value !== 'number') continue;

    parts.push(template.slice(lastIndex, match.index));
    parts.push(
      <bdi dir="auto" key={`localized-value-${partIndex}`}>
        {String(value)}
      </bdi>,
    );
    lastIndex = match.index + match[0].length;
    partIndex += 1;
  }

  if (partIndex === 0) return template;
  parts.push(template.slice(lastIndex));
  return parts;
};

const LocalizedText = ({ as: Element = 'span', source, values, children, ...props }) => {
  const { directionFor, languageFor, t } = useInterfaceLanguage();
  const direction = typeof source === 'string' ? directionFor(source) : undefined;
  const text = typeof source !== 'string'
    ? children
    : direction === 'rtl'
      ? isolateRtlValues(t(source), values)
      : t(source, values);
  const language = typeof source === 'string' ? languageFor(source) : undefined;

  if (Element === 'span' && language === 'en' && Object.keys(props).length === 0) {
    return text;
  }

  return (
    <Element dir={direction}
      lang={language}
      {...props}
    >
      {text}
    </Element>
  );
};

export default LocalizedText;
