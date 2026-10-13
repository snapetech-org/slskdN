import { interfaceText, interfaceTextProps } from "../../lib/interfaceLocale";
import * as transfers from '../../lib/transfers';
import { formatBytes } from '../../lib/util';
import FileList from '../Shared/FileList';
import TooltipButton from '../Shared/TooltipButton';
import React, { Component } from 'react';
import { Card, Icon, Message } from 'semantic-ui-react';

const Button = TooltipButton;

const getDownloadErrorMessage = (error) => {
  const data = error?.response?.data;

  if (typeof data === 'string') return data;
  if (data && typeof data === 'object') {
    return data.detail || data.message || data.title || JSON.stringify(data);
  }

  return error?.message || 'The download request could not be completed.';
};

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
                aria-label={`Download ${selectedFiles.length} selected file${selectedFiles.length === 1 ? '' : 's'}`}
                color="green"
                content={interfaceText("Download")}
                disabled={downloadRequest === 'inProgress'}
                icon="download"
                label={{
                  as: 'a',
                  basic: false,
                  content: `${selectedFiles.length} file${selectedFiles.length === 1 ? '' : 's'}, ${selectedSize}`,
                }}
                labelPosition="right"
                onClick={() => this.download(username, selectedFiles)}
                tooltip={`Queue ${selectedFiles.length} selected file${selectedFiles.length === 1 ? '' : 's'} from ${name} for download.`}
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
