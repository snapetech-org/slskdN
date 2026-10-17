import { interfaceText, interfaceTextProps } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import * as transfers from '../../lib/transfers';
import { formatBytes } from '../../lib/util';
import FileList from '../Shared/FileList';
import TooltipButton from '../Shared/TooltipButton';
import React, { Component } from 'react';
import { Card, Icon, Message } from 'semantic-ui-react';

const Button = TooltipButton;

const getDownloadErrorMessage = (error) =>
  getApiErrorMessage(error, { t: interfaceText }, 'The download request could not be completed.');

const initialState = {
  downloadError: '',
  downloadRequest: undefined,
};

const asArray = (value) => (Array.isArray(value) ? value : []);

class Directory extends Component {
  constructor(props) {
    super(props);

    this.state = {
      ...initialState,
      files: asArray(this.props.files).map((f) => ({ selected: false, ...f })),
    };
  }

  componentDidUpdate(previousProps) {
    if (this.props.name !== previousProps.name) {
      this.setState({
        files: asArray(this.props.files).map((f) => ({ selected: false, ...f })),
      });
    }
  }

  handleFileSelectionChange = (file, state) => {
    file.selected = state;
    this.setState((previousState) => ({
      downloadError: '',
      downloadRequest: undefined,
      tree: previousState.tree,
    }));
  };

  download = (username, files) => {
    this.setState({ downloadRequest: 'inProgress' }, async () => {
      try {
        const requests = asArray(files).map(({ filename, size, bitRate, sampleRate, bitDepth, length }) => ({
          filename,
          size,
          bitRate,
          sampleRate,
          bitDepth,
          length,
        }));
        await transfers.download({
          destination: this.props.destination,
          files: requests,
          username,
        });

        this.setState({ downloadRequest: 'complete' });
      } catch (error) {
        this.setState({
          downloadError: getDownloadErrorMessage(error),
          downloadRequest: 'error',
        });
      }
    });
  };

  render() {
    const { locked, marginTop, name, onClose, username } = this.props;
    const { downloadError, downloadRequest, files } = this.state;

    const selectedFiles = files.filter((f) => f.selected);

    const selectedSize = formatBytes(
      selectedFiles.reduce((total, f) => total + f.size, 0),
    );

    return (
      <Card
        className="browse-selected-directory-card"
        raised
      >
        <Card.Content>
          <div style={{ marginTop: marginTop || 0 }}>
            <FileList
              directoryName={name}
              disabled={downloadRequest === 'inProgress'}
              files={files}
              locked={locked}
              onClose={onClose}
              onSelectionChange={this.handleFileSelectionChange}
            />
          </div>
        </Card.Content>
        {selectedFiles.length > 0 && (
          <Card.Content extra>
            <span>
              <Button
                aria-label={interfaceText(selectedFiles.length === 1
                  ? 'Download {count} selected file'
                  : 'Download {count} selected files', { count: selectedFiles.length })}
                color="green"
                content={interfaceText("Download")}
                disabled={downloadRequest === 'inProgress'}
                icon="download"
                label={{
                  as: 'a',
                  basic: false,
                  content: interfaceText(selectedFiles.length === 1
                    ? '{count} file, {size}'
                    : '{count} files, {size}', { count: selectedFiles.length, size: selectedSize }),
                }}
                labelPosition="right"
                onClick={() => this.download(username, selectedFiles)}
                tooltip={interfaceText(selectedFiles.length === 1
                  ? 'Queue {count} selected file from {directory} for download.'
                  : 'Queue {count} selected files from {directory} for download.', {
                  count: selectedFiles.length,
                  directory: name,
                })}
               {...interfaceTextProps("Download")}/>
              {downloadRequest === 'inProgress' && (
                <Icon
                  loading
                  name="circle notch"
                  size="large"
                />
              )}
              {downloadRequest === 'complete' && (
                <Icon
                  color="green"
                  name="checkmark"
                  size="large"
                />
              )}
              {downloadRequest === 'error' && (
                <Message
                  data-testid="browse-download-error"
                  negative
                  size="small"
                >
                  <Icon color="red" name="x" />
                  {downloadError}
                </Message>
              )}
            </span>
          </Card.Content>
        )}
      </Card>
    );
  }
}

export default Directory;
