import LocalizedText from "./LocalizedText";
import { interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import React from 'react';
import { Form, Message } from 'semantic-ui-react';

const DownloadExclusionsField = ({
  ariaLabel,
  disabled = false,
  label,
  onChange,
  value = '',
}) => {
  const { t } = useInterfaceLanguage();
  const ariaLabelSource = ariaLabel || 'Global download exclusions';
  const labelSource = label || 'Blocked filename/path terms';

  return (
    <>
      <Form.TextArea
        {...interfaceTextProps(ariaLabelSource)}
        aria-label={t(ariaLabelSource)}
        disabled={disabled}
        label={<LocalizedText source={labelSource} />}
        onChange={(_, { value: nextValue }) => onChange(nextValue)}
        placeholder={'acapella\ninstrumental\na cappella'}
        rows={7}
        value={value}
      />
      <Message
        info
        size="small"
      >
        <LocalizedText source={"One literal term per line. Matching is case-insensitive and checks the remote filename and folder path. Up to 100 terms are supported, with a maximum of 256 characters per term. Live policy changes cancel active transfers that become blocked."} /></Message>
    </>
  );
};

export default DownloadExclusionsField;
