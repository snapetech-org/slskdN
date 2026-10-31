import React, { Fragment } from 'react';
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

// React-node parameters are app-owned presentation fragments; plain opaque
// values still get their own bidi boundary. Translation text is never markup.
export const LocalizedRichText = ({ source, values = {} }) => {
  const { directionFor, languageFor, t } = useInterfaceLanguage();
  const parts = t(source).split(/(\{[a-zA-Z][a-zA-Z0-9_]*\})/g);
  return (
    <span dir={directionFor(source)} lang={languageFor(source)}>
      {parts.map((part, index) => {
        const token = /^\{([a-zA-Z][a-zA-Z0-9_]*)\}$/.exec(part);
        if (!token || !Object.hasOwn(values, token[1])) return <Fragment key={index}>{part}</Fragment>;
        const value = values[token[1]];
        return typeof value === 'string' || typeof value === 'number'
          ? <bdi dir="auto" key={index}>{String(value)}</bdi>
          : <Fragment key={index}>{value}</Fragment>;
      })}
    </span>
  );
};
