import LocalizedText from "./LocalizedText";
import { interfaceText, interfaceTextProps } from "../../lib/interfaceLocale";
import React from 'react';
import { Message } from 'semantic-ui-react';

const FeatureGateNotice = ({ configurationKeys = [], featureGate, featureName }) => {
  if (featureGate?.enabled !== false) return null;

  return (
    <Message info role="status" size="small">
      <Message.Header>{featureName} <LocalizedText source={"is disabled"} /></Message.Header>
      <p>
        {featureGate.message ||
          'This feature is disabled in the server’s effective settings.'}
      </p>
      {configurationKeys.length > 0 && (
        <p>
          <LocalizedText source={"Review the server configuration:"} />{' '}
          {configurationKeys.map((key, index) => (
            <React.Fragment key={key}>
              {index > 0 ? ', ' : ''}
              <code>{key}</code>
            </React.Fragment>
          ))}
        </p>
      )}
    </Message>
  );
};

export default FeatureGateNotice;
