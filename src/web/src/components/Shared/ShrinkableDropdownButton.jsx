import ShrinkableButton from './ShrinkableButton';
import { interfaceAttributeText, interfacePresentationText, interfaceTextProps, useInterfaceLanguage } from '../../lib/interfaceLocale';
import React from 'react';
import { Button, Dropdown, Popup } from 'semantic-ui-react';

const ShrinkableDropdownButton = ({
  children,
  color,
  disabled,
  hidden,
  icon,
  loading,
  menuLabel,
  mediaQuery,
  onChange,
  onClick,
  options,
  tooltip,
}) => {
  useInterfaceLanguage();
  if (hidden) {
    return null;
  }

  const menu = (
    <Dropdown
      {...(!menuLabel && typeof children === 'string' ? interfaceTextProps("{label} options") : {})}
      aria-label={menuLabel || (typeof children === 'string' ? interfaceAttributeText("{label} options", { label: children }) : undefined)}
      className="button icon"
      disabled={disabled}
      onChange={onChange}
      options={options}
      title={tooltip}
      trigger={null}
    />
  );

  return (
    <Button.Group color={color}>
      <ShrinkableButton
        disabled={disabled}
        icon={icon}
        loading={loading}
        mediaQuery={mediaQuery}
        onClick={onClick}
        tooltip={tooltip}
      >
        {children}
      </ShrinkableButton>
      {tooltip ? (
        <Popup
          content={tooltip}
          trigger={disabled ? <span>{menu}</span> : menu}
        />
      ) : menu}
    </Button.Group>
  );
};

export default ShrinkableDropdownButton;
