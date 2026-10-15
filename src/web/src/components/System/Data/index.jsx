import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { clearCompleted } from '../../../lib/transfers';
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
import React, { useState } from 'react';
import { toast } from 'react-toastify';
import { Button, Divider, Header, Icon, Message, Popup } from 'semantic-ui-react';

const clear = async ({ direction, setError, setLoading }) => {
  setLoading(true);
  setError('');

  try {
    await clearCompleted({ direction });
    toast.success(interfaceText("Completed {direction}s cleared!", { "direction": (direction) }));
  } catch (error) {
    setError(getApiErrorMessage(error, { t: interfaceText }));
  } finally {
    setLoading(false);
  }
};

const Data = () => {
  useInterfaceLanguage();
  const [up, setUp] = useState(false);
  const [down, setDown] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [downloadError, setDownloadError] = useState('');

  return (
    <div className="transfer-data">
      <Header
        as="h2"
        className="transfer-header"
      >
        <LocalizedText source={"Transfer Data"} /></Header>
      <Divider />
      <p>
        <LocalizedText source={"The Uploads and Downloads pages can become unresponsive if too many transfers are displayed. Remove completed transfer records to keep those pages responsive; downloaded files on disk are not removed."} /></p>
      <div className="transfer-data-actions">
        <Popup
          content={interfaceText("Remove completed upload records from transfer history to keep the Uploads page responsive.")}
          on={['hover', 'focus']}
          position="top center"
          trigger={(
            <Button
              disabled={up}
              loading={up}
              negative
              onClick={() => clear({
                direction: 'upload',
                setError: setUploadError,
                setLoading: setUp,
              })}
            >
              <Icon name="trash alternate" />
              <LocalizedText source={"Clear All Completed Uploads"} /></Button>
          )}
         {...interfaceTextProps("Remove completed upload records from transfer history to keep the Uploads page responsive.")}/>
        <Popup
          content={interfaceText("Remove completed download records from transfer history. Files already saved on disk are not deleted.")}
          on={['hover', 'focus']}
          position="top center"
          trigger={(
            <Button
              disabled={down}
              loading={down}
              negative
              onClick={() => clear({
                direction: 'download',
                setError: setDownloadError,
                setLoading: setDown,
              })}
            >
              <Icon name="trash alternate" />
              <LocalizedText source={"Clear All Completed Downloads"} /></Button>
          )}
         {...interfaceTextProps("Remove completed download records from transfer history. Files already saved on disk are not deleted.")}/>
      </div>
      {(uploadError || downloadError) && (
        <div aria-live="polite" className="transfer-data-errors">
          {uploadError && (
            <Message
              content={interfaceText("Uploads: {uploadError}", { "uploadError": (uploadError) })}
              negative
              role="alert"
             {...interfaceTextProps("Uploads: {uploadError}")}/>
          )}
          {downloadError && (
            <Message
              content={interfaceText("Downloads: {downloadError}", { "downloadError": (downloadError) })}
              negative
              role="alert"
             {...interfaceTextProps("Downloads: {downloadError}")}/>
          )}
        </div>
      )}
    </div>
  );
};

export default Data;
