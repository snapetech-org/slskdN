import React from 'react';
import { useMediaQuery } from 'react-responsive';
import { Button, Icon, Popup } from 'semantic-ui-react';

const getText = (value) => {
  if (typeof value === 'string' || typeof value === 'number') return String(value);
  if (Array.isArray(value)) return value.map(getText).filter(Boolean).join(' ').trim();
  if (React.isValidElement(value)) return getText(value.props.children);
  return '';
};

const ShrinkableButton = ({
  children,
  icon,
  loading,
  mediaQuery,
  tooltip,
  'aria-label': ariaLabel,
  ...rest
}) => {
  const shouldShrink = useMediaQuery({ query: mediaQuery });
  const textLabel = getText(children);
  const accessibleLabel = ariaLabel || textLabel ||
    (typeof tooltip === 'string' ? tooltip : undefined);
  const button = (
    <Button
      aria-label={accessibleLabel}
      icon={shouldShrink || undefined}
      title={tooltip}
      {...rest}
    >
      <Icon
        loading={loading}
        name={icon}
      />
      {!shouldShrink && children}
    </Button>
  );

  if (!tooltip) return button;

  return (
    <Popup
      content={tooltip}
      trigger={rest.disabled ? <span>{button}</span> : button}
    />
  );
};

export default ShrinkableButton;
