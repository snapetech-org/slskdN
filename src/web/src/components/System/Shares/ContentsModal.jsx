import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { browse } from '../../../lib/shares';
import { CodeEditor, LoaderSegment, Switch } from '../../Shared';
import React, { useEffect, useState } from 'react';
import { Button, Icon, Modal, Popup } from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const asText = (value) => (typeof value === 'string' ? value : '');

const ContentsModal = ({ onClose, share, theme }) => {
  useInterfaceLanguage();
  const [loading, setLoading] = useState(true);
  const [contents, setContents] = useState();

  const { id, localPath, remotePath } = share || {};

  useEffect(() => {
    let cancelled = false;

    const fetch = async () => {
      setLoading(true);

      const result = await browse({ id });

      if (cancelled) {
        return;
      }

      const directories = asArray(result).map((directory) => {
        const directoryName = asText(directory?.name);
        const lines = [directoryName.replace(remotePath, localPath)];
        const directoryFilesOrderedByFilename = [...asArray(directory?.files)].sort(
          (file1, file2) => asText(file1?.filename).localeCompare(asText(file2?.filename)),
        );

        for (const file of directoryFilesOrderedByFilename) {
          lines.push('\t' + asText(file?.filename).replace(remotePath, ''));
        }

        lines.push('');

        return lines.join('\n');
      });

      if (!cancelled) {
        setContents(directories.join('\n'));
        setLoading(false);
      }
    };

    if (id) {
      fetch();
    } else {
      setLoading(true);
      setContents();
    }

    return () => {
      cancelled = true;
    };
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Modal
      onClose={onClose}
      open={Boolean(share)}
      size="large"
    >
      <Modal.Header>
        <Icon name="folder" />
        {localPath}
      </Modal.Header>
      <Modal.Content
        className="share-ls-content"
        scrolling
      >
        <Switch loading={loading && <LoaderSegment className="modal-loader" />}>
          <CodeEditor
            basicSetup={false}
            editable={false}
            style={{ minHeight: 500 }}
            theme={theme}
            value={contents || ''}
          />
        </Switch>
      </Modal.Content>
      <Modal.Actions>
        <Popup
          content={interfaceText("Close the share contents window.")}
          trigger={(
            <Button
              aria-label={interfaceText("Close share contents")}
              onClick={onClose}
              title={interfaceText("Close the share contents window.")}
             {...interfaceTextProps("Close share contents")}>
              <LocalizedText source={"Close"} /></Button>
          )}
         {...interfaceTextProps("Close the share contents window.")}/>
      </Modal.Actions>
    </Modal>
  );
};

export default ContentsModal;
