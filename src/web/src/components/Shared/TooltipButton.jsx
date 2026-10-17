import React from 'react';
import { Button, Popup } from 'semantic-ui-react';
import { useInterfaceLanguage } from '../../lib/interfaceLocale';

export const LocalizedPopup = ({ content, parameters = {}, translateContent = true, textDirection, textLanguage, ...props }) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const popupContent = typeof content === 'string' && translateContent
    ? <span lang={textLanguage || languageFor(content)} dir={textDirection || directionFor(content)}>{t(content, parameters)}</span>
    : content;

  return <Popup {...props} content={popupContent} />;
};

const getText = (children) => {
  if (typeof children === 'string') {
    return children;
  }

  if (Array.isArray(children)) {
    return children.map(getText).filter(Boolean).join(' ').trim();
  }

  if (React.isValidElement(children)) {
    const { source, children: nestedChildren } = children.props || {};
    return typeof source === 'string' ? source : getText(nestedChildren);
  }

  return '';
};

const TooltipButton = ({
  'aria-label': ariaLabel,
  children,
  content: buttonContent,
  popupPosition = 'top center',
  parameters = {},
  dir: providedDirection,
  lang: providedLanguage,
  title,
  tooltip,
  ...props
}) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const translateChildren = (value) => {
    if (typeof value === 'string') return t(value, parameters);
    if (Array.isArray(value)) return value.map(translateChildren);
    return value;
  };
  const translatedAriaLabel = typeof ariaLabel === 'string' ? t(ariaLabel, parameters) : ariaLabel;
  const translatedTitle = typeof title === 'string' ? t(title, parameters) : title;
  const translatedContent = typeof buttonContent === 'string' ? t(buttonContent, parameters) : translateChildren(buttonContent);
  const translatedChildren = translateChildren(children);
  const inferredSource = ariaLabel || title || getText(children) || getText(buttonContent) ||
    (typeof tooltip === 'string' ? tooltip : undefined);
  const inferredLabel = inferredSource ? t(inferredSource, parameters) : undefined;
  const metadataSource = ariaLabel || title || getText(children) || getText(buttonContent) ||
    (typeof tooltip === 'string' ? tooltip : undefined);
  const button = (
    <Button
      aria-label={translatedAriaLabel || inferredLabel}
      content={translatedContent}
      title={translatedTitle}
      {...props}
      lang={providedLanguage || (metadataSource ? languageFor(metadataSource) : undefined)}
      dir={providedDirection || (metadataSource ? directionFor(metadataSource) : undefined)}
    >
      {translatedChildren}
    </Button>
  );
  const popupSource = tooltip || title || inferredSource;
  const popupContent = popupSource;

  if (!popupContent) {
    return button;
  }

  return (
    <LocalizedPopup
      content={popupContent}
      parameters={parameters}
      position={popupPosition}
      textDirection={providedDirection}
      textLanguage={providedLanguage}
      trigger={props.disabled ? <span>{button}</span> : button}
    />
  );
};

TooltipButton.Group = Button.Group;
TooltipButton.Or = Button.Or;

export default TooltipButton;
