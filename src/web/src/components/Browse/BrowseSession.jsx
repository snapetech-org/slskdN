import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
/* eslint-disable promise/prefer-await-to-then */
import './Browse.css';
import * as transfers from '../../lib/transfers';
import {
  getLocalStorageItem,
  getLocalStorageKeys,
  removeLocalStorageItem,
  setLocalStorageItem,
} from '../../lib/storage';
import * as userNotes from '../../lib/userNotes';
import * as users from '../../lib/users';
import PlaceholderSegment from '../Shared/PlaceholderSegment';
import DownloadDestinationSelector from '../Shared/DownloadDestinationSelector';
import UserCard from '../Shared/UserCard';
import UserNoteModal from '../Users/UserNoteModal';
import TooltipButton from '../Shared/TooltipButton';
import Directory from './Directory';
import DirectoryTree from './DirectoryTree';
import * as lzString from 'lz-string';
import React, { Component } from 'react';
import { toast } from 'react-toastify';
import {
  Button,
  Card,
  Icon,
  Input,
  Loader,
  Popup,
  Segment,
} from 'semantic-ui-react';

const initialState = {
  browseError: undefined,
  browseState: 'idle',
  browseStatus: 0,
  downloadDestination: undefined,
  info: {
    directories: 0,
    files: 0,
    lockedDirectories: 0,
    lockedFiles: 0,
  },
  selectedDirectory: {},
  selectedFiles: [],
  separator: '\\',
  tree: [],
  username: '',
  userNote: null,
};

const asArray = (value) => (Array.isArray(value) ? value : []);

const isDirectory = (directory) =>
  directory
  && typeof directory === 'object'
  && !Array.isArray(directory)
  && typeof directory.name === 'string';

const normalizeDirectory = (directory) => ({
  ...directory,
  children: asArray(directory.children)
    .filter(isDirectory)
    .map(normalizeDirectory),
  files: asArray(directory.files),
});

const MAX_BROWSE_CACHE_ENTRIES = 50;
const BROWSE_CACHE_PREFIX = 'slskd-browse-state-';
const BROWSE_CACHE_VERSION = 2;
const BROWSE_STATUS_POLL_INTERVAL_MS = 1_000;

const sameBrowseStatus = (left, right) =>
  left === right
  || (
    left
    && right
    && left.bytesRemaining === right.bytesRemaining
    && left.bytesTransferred === right.bytesTransferred
    && left.percentComplete === right.percentComplete
    && left.size === right.size
  );

const getBrowseErrorMessage = (error) =>
  getApiErrorMessage(error, { t: interfaceText }, 'Browse failed');

// Cleanup old browse cache entries using LRU strategy
const cleanupBrowseCache = () => {
  try {
    const cacheEntries = getLocalStorageKeys()
      .filter((key) => key.startsWith(BROWSE_CACHE_PREFIX))
      .map((key) => {
        const data = getLocalStorageItem(key, '');
        return { key, size: data ? data.length : 0 };
      });

    if (cacheEntries.length > MAX_BROWSE_CACHE_ENTRIES) {
      // Sort by size (larger = older/more complete browses, keep those)
      // Remove smallest/oldest entries first
      cacheEntries.sort((a, b) => a.size - b.size);
      const toRemove = cacheEntries.slice(
        0,
        cacheEntries.length - MAX_BROWSE_CACHE_ENTRIES,
      );
      for (const entry of toRemove) {
        removeLocalStorageItem(entry.key);
      }
    }
  } catch (error) {
    console.debug('Browse cache cleanup error:', error);
  }
};

class BrowseSession extends Component {
  browseGeneration = 0;
  mounted = false;
  pollInterval = null;
  statusRequest = null;

  constructor(props) {
    super(props);

    this.state = initialState;
  }

  componentDidMount() {
    this.mounted = true;
    // Check for username from props (tab only - navigation handled by parent)
    const userToBrowse = this.props.username;

    if (userToBrowse) {
      this.fetchUserNote(userToBrowse);
      // Try to load cached data first
      const hasCachedData = this.loadState();

      // Small delay to ensure ref is ready
      setTimeout(() => {
        if (this.inputtext) {
          this.inputtext.value = userToBrowse;
        }

        // Only fetch if we don't have cached data
        if (!hasCachedData) {
          this.setState({ username: userToBrowse }, this.browse);
        }
      }, 50);
    } else {
      this.loadState();
    }

    document.addEventListener('keyup', this.keyUp, false);
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
  }

  componentWillUnmount() {
    this.mounted = false;
    this.browseGeneration += 1;
    this.stopPolling();
    document.removeEventListener('keyup', this.keyUp, false);
    document.removeEventListener(
      'visibilitychange',
      this.handleVisibilityChange,
    );
  }

  fetchUserNote = async (username) => {
    try {
      const response = await userNotes.getNote({ username });
      this.setState({ userNote: response.data });
    } catch {
      this.setState({ userNote: null });
    }
  };

  // Start polling only when needed (during active browse)
  startPolling = () => {
    if (!this.mounted || document.hidden || this.pollInterval) return;

    this.pollInterval = window.setInterval(
      this.fetchStatus,
      BROWSE_STATUS_POLL_INTERVAL_MS,
    );
  };

  // Stop polling when not needed
  stopPolling = () => {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  };

  // Pause polling when page is hidden to save resources
  handleVisibilityChange = () => {
    if (document.hidden) {
      this.stopPolling();
    } else if (this.state.browseState === 'pending') {
      this.fetchStatus();
      this.startPolling();
    }
  };

  browse = () => {
    const username = this.inputtext.value;

    if (!username) {
      return;
    }

    this.browseGeneration += 1;

    // Notify parent to update tab label
    if (this.props.onUsernameChange) {
      this.props.onUsernameChange(username);
    }

    this.setState(
      {
        browseError: undefined,
        browseState: 'pending',
        browseStatus: 0,
        username,
      },
      () => {
        this.fetchUserNote(username);
        // Start polling only while browse is in progress
        this.startPolling();

        users
          .browse({ username })
          .then(async (response) => {
            let directories = asArray(response?.directories).filter(isDirectory);
            const lockedDirectories = asArray(response?.lockedDirectories)
              .filter(isDirectory);

            // we need to know the directory separator. assume it is \ to start
            let separator;

            const directoryCount = directories.length;
            const fileCount = directories.reduce((accumulator, directory) => {
              // examine each directory as we process it to see if it contains \ or /, and set separator accordingly
              if (!separator) {
                if (directory.name.includes('\\')) separator = '\\';
                else if (directory.name.includes('/')) separator = '/';
              }

              return accumulator + directory.fileCount;
            }, 0);

            const lockedDirectoryCount = lockedDirectories.length;
            const lockedFileCount = lockedDirectories.reduce(
              (accumulator, directory) => accumulator + directory.fileCount,
              0,
            );

            directories = directories.concat(
              lockedDirectories.map((d) => ({ ...d, locked: true })),
            );

            const tree = await this.getDirectoryTreeAsync({
              directories,
              separator,
            });

            this.setState({
              info: {
                directories: directoryCount,
                files: fileCount,
                lockedDirectories: lockedDirectoryCount,
                lockedFiles: lockedFileCount,
              },
              separator,
              tree,
            });
          })
          .then(() => {
            // Stop polling when browse completes
            this.stopPolling();
            this.setState(
              { browseError: undefined, browseState: 'complete' },
              () => {
                this.saveState();
              },
            );
          })
          .catch((error) => {
            // Stop polling on error too
            this.stopPolling();
            this.setState({
              browseError: getBrowseErrorMessage(error),
              browseState: 'error',
            });
          });
      },
    );
  };

  clear = () => {
    this.browseGeneration += 1;
    this.stopPolling();
    this.setState(initialState, () => {
      this.saveState();
      this.inputtext.focus();
    });
  };

  keyUp = (event) => (event.key === 'Escape' ? this.clear() : '');

  getStorageKey = () => {
    const username = this.props.username || this.state.username || 'default';
    return `slskd-browse-state-${username}`;
  };

  saveState = () => {
    if (this.inputtext) {
      this.inputtext.value = this.state.username;
      this.inputtext.disabled =
        this.state.browseState !== 'idle';
    }

    // Only save if we have actual browse data
    if (this.state.username && this.state.tree.length > 0) {
      try {
        setLocalStorageItem(
          this.getStorageKey(),
          lzString.compress(
            JSON.stringify({
              ...this.state,
              cacheVersion: BROWSE_CACHE_VERSION,
            }),
          ),
        );
        // Cleanup old cache entries to prevent unbounded growth
        cleanupBrowseCache();
      } catch (error) {
        console.error(error);
      }
    }
  };

  loadState = () => {
    // Try to load saved state for this username
    const username = this.props.username;

    if (username) {
      try {
        const key = `slskd-browse-state-${username}`;
        const savedState = JSON.parse(
          lzString.decompress(getLocalStorageItem(key, '') || ''),
        );

        const tree = asArray(savedState?.tree)
          .filter(isDirectory)
          .map(normalizeDirectory);
        if (
          savedState
          && typeof savedState === 'object'
          && !Array.isArray(savedState)
          && savedState.cacheVersion === BROWSE_CACHE_VERSION
          && tree.length > 0
          && (
            Number(savedState.info?.directories || 0) > 0 ||
            Number(savedState.info?.files || 0) > 0
          )
        ) {
          // We have cached data - use it instead of re-fetching
          this.setState({
            ...savedState,
            browseState: 'complete',
            selectedDirectory: isDirectory(savedState.selectedDirectory)
              ? normalizeDirectory(savedState.selectedDirectory)
              : initialState.selectedDirectory,
            tree,
          });
          return true; // Indicate we loaded cached data
        }

        removeLocalStorageItem(key);
      } catch {
        // ignore - will fetch fresh
      }
    }

    return false;
  };

  fetchStatus = () => {
    const { browseState, username } = this.state;
    if (
      !this.mounted
      || document.hidden
      || browseState !== 'pending'
      || !username
    ) return Promise.resolve();

    const generation = this.browseGeneration;
    if (
      this.statusRequest?.generation === generation
      && this.statusRequest.username === username
    ) return this.statusRequest.promise;

    const promise = users
      .getBrowseStatus({ username })
      .then((response) => {
        if (!this.mounted) return;
        if (document.hidden) return;
        if (
          this.browseGeneration !== generation
          || this.state.browseState !== 'pending'
          || this.state.username !== username
        ) return;

        this.setState((previous) =>
          sameBrowseStatus(previous.browseStatus, response.data)
            ? null
            : { browseStatus: response.data });
      })
      .catch(() => {
        // Ignore 404s and transient failures during status polling.
      })
      .finally(() => {
        if (this.statusRequest?.promise === promise) {
          this.statusRequest = null;
        }
      });

    this.statusRequest = { generation, promise, username };
    return promise;
  };

  getDirectoryTree = ({ directories, separator }) => {
    const validDirectories = asArray(directories).filter(isDirectory);

    if (validDirectories.length === 0) {
      return [];
    }

    const effectiveSeparator = separator || '\\';
    const nodesByName = new Map();
    const roots = [];

    for (const directory of validDirectories) {
      nodesByName.set(directory.name, { ...directory, children: [] });
    }

    for (const node of nodesByName.values()) {
      const parts = node.name.split(effectiveSeparator);
      const parentName =
        parts.length > 1 ? parts.slice(0, -1).join(effectiveSeparator) : '';
      const parent = parentName ? nodesByName.get(parentName) : null;

      if (parent) {
        parent.children.push(node);
      } else {
        roots.push(node);
      }
    }

    return roots;
  };

  getDirectoryTreeAsync = ({ directories, separator }) =>
    new Promise((resolve) => {
      if (typeof Worker !== 'function') {
        resolve(this.getDirectoryTree({ directories, separator }));
        return;
      }

      const worker = new Worker(
        new URL('./browseTreeWorker.js', import.meta.url),
        { type: 'module' },
      );
      const id = `${Date.now()}-${Math.random()}`;

      worker.onmessage = ({ data }) => {
        if (data.id !== id) {
          return;
        }

        worker.terminate();
        resolve(
          data.error ? this.getDirectoryTree({ directories, separator }) : data.tree,
        );
      };

      worker.onerror = () => {
        worker.terminate();
        resolve(this.getDirectoryTree({ directories, separator }));
      };

      worker.postMessage({ directories, id, separator });
    });

  selectDirectory = (directory) => {
    this.setState({ selectedDirectory: { ...directory, children: [] } }, () =>
      this.saveState(),
    );
  };

  handleDeselectDirectory = () => {
    this.setState({ selectedDirectory: initialState.selectedDirectory }, () =>
      this.saveState(),
    );
  };

  handleRefresh = () => {
    // Force re-fetch by clearing cache and browsing again
    const { username } = this.state;

    if (username) {
      // Clear the cached state for this user
      try {
        removeLocalStorageItem(`slskd-browse-state-${username}`);
      } catch {
        // ignore
      }

      // Re-browse
      this.browse();
    }
  };

  handleDownloadDirectory = (directory) => {
    const { downloadDestination, separator, username } = this.state;

    // Collect all files recursively
    const collectFiles = (folder) => {
      let collected = asArray(folder.files).map((f) => ({
        filename: `${folder.name}${separator}${f.filename}`,
        size: f.size,
        bitRate: f.bitRate,
        sampleRate: f.sampleRate,
        bitDepth: f.bitDepth,
        length: f.length,
      }));

      if (Array.isArray(folder.children)) {
        for (const child of folder.children) {
          collected = collected.concat(collectFiles(child));
        }
      }

      return collected;
    };

    const filesToDownload = collectFiles(directory);

    if (filesToDownload.length === 0) {
      toast.info(interfaceText("No files found in directory: {name}", { "name": (directory.name) }));
      return;
    }

    if (
      // eslint-disable-next-line no-alert
      window.confirm(interfaceText(
        'Download {count} files from {directory}?',
        { count: filesToDownload.length, directory: directory.name },
      ))
    ) {
      transfers
        .download({
          destination: downloadDestination,
          files: filesToDownload,
          username,
        })
        .then(() => {
          toast.success(interfaceText("Queued {length} files for download", { "length": (filesToDownload.length) }));
        })
        .catch((error) => {
          console.error(error);
          toast.error(interfaceText('Failed to queue download: {message}', {
            message: getApiErrorMessage(error, { t: interfaceText }),
          }));
        });
    }
  };

  handleDestinationChange = (downloadDestination) => {
    this.setState({ downloadDestination });
  };

  render() {
    const {
      browseError,
      browseState,
      browseStatus,
      downloadDestination,
      info,
      selectedDirectory,
      separator,
      tree,
      userNote,
      username,
    } = this.state;
    const { locked, name } = selectedDirectory;
    const pending = browseState === 'pending';
    const finished = ['complete', 'error'].includes(browseState);
    const emptyTree = finished && tree.length === 0;

    const files = asArray(selectedDirectory.files).map((f) => ({
      ...f,
      filename: `${name}${separator}${f.filename}`,
    }));

    return (
      <div className="search-container" data-testid="browse-content">
        <Segment
          className="browse-segment"
          raised
        >
          <div className="browse-segment-icon">
            <Icon
              name="folder open"
              size="big"
            />
          </div>
          <Input
            action={
              !pending && (
                <Popup
                  content={
                    interfaceText(browseState === 'idle'
                      ? "Browse this Soulseek user's shared files."
                      : 'Clear this browse result and enter another username.')
                  }
                  position="top center"
                  trigger={
                    <Button
                      aria-label={
                        interfaceText(browseState === 'idle'
                          ? 'Browse user files'
                          : 'Clear browse result')
                      }
                      color={browseState === 'idle' ? undefined : 'red'}
                      icon={browseState === 'idle' ? 'search' : 'x'}
                      onClick={
                        browseState === 'idle' ? this.browse : this.clear
                      }
                    />
                  }
                />
              )
            }
            className="search-input"
            disabled={pending}
            input={
              <input
                data-lpignore="true"
                placeholder={interfaceText("Username")}
                type="search"
               {...interfaceTextProps("Username")}/>
            }
            loading={pending}
            onKeyUp={(event) => (event.key === 'Enter' ? this.browse() : '')}
            placeholder={interfaceText("Username")}
            ref={(input) => (this.inputtext = input)}
            size="big"
           {...interfaceTextProps("Username")}/>
        </Segment>
        {pending ? (
          <Loader
            active
            className="search-loader"
            inline="centered"
            size="big"
          >
            <LocalizedText source={"Downloaded"} />{" "}{Math.round(browseStatus.percentComplete || 0)}<LocalizedText source={"% of Response"} /></Loader>
        ) : (
          <div>
            {browseError ? (
              <span className="browse-error">
                <LocalizedText
                  source="Failed to browse {username}: {message}"
                  values={{ username, message: browseError }}
                />
              </span>
            ) : (
              <div className="browse-container">
                {emptyTree ? (
                  <PlaceholderSegment
                    caption="No user share to display"
                    icon="folder open"
                  />
                ) : (
                  <Card
                    className="browse-tree-card"
                    raised
                  >
                    <Card.Content>
                      <Card.Header
                        style={{
                          alignItems: 'center',
                          display: 'flex',
                          justifyContent: 'space-between',
                        }}
                      >
                        <span>
                          <Icon
                            color="green"
                            name="circle"
                          />
                          <UserCard username={username}>{username}</UserCard>
                          {userNote && (
                            <Icon
                              color={userNote.color || 'grey'}
                              name={userNote.icon || 'sticky note'}
                              style={{ marginLeft: '8px' }}
                              title={userNote.note}
                            />
                          )}
                          <UserNoteModal
                            onClose={() => this.fetchUserNote(username)}
                            trigger={
                              <TooltipButton
                                aria-label={interfaceText("Edit user note for {username}", { "username": (username) })}
                                basic
                                compact
                                icon
                                size="small"
                                style={{ marginLeft: '4px', opacity: 0.5 }}
                                tooltip="Open your local note and color rating for {username}."
                               {...interfaceTextProps("Edit user note for {username}", { username })}>
                                <Icon color="grey" name="pencil alternate" />
                              </TooltipButton>
                            }
                            username={username}
                          />
                        </span>
                        <TooltipButton
                          aria-label={interfaceText("Refresh {username}'s shared files", { "username": (username) })}
                          basic
                          compact
                          icon
                          onClick={this.handleRefresh}
                          tooltip="Request {username}'s current shared file list from Soulseek and refresh this browse view."
                         {...interfaceTextProps("Refresh {username}'s shared files", { username })}>
                          <Icon name="refresh" />
                        </TooltipButton>
                      </Card.Header>
                      <Card.Meta className="browse-meta">
                        {interfaceText("{directories} directories, {files} files", { "directories": (info.directories), "files": (info.files) })}
                        {info.lockedDirectories
                          ? <LocalizedText source={"({lockedDirectories} locked directories, {lockedFiles} locked files)"} values={{ "lockedDirectories": (info.lockedDirectories), "lockedFiles": (info.lockedFiles) }} />
                          : ''}
                      </Card.Meta>
                    </Card.Content>
                    <Card.Content>
                      <DownloadDestinationSelector
                        onChange={this.handleDestinationChange}
                      />
                      <Segment className="browse-folderlist">
                        <DirectoryTree
                          onDownload={this.handleDownloadDirectory}
                          onSelect={(_, value) => this.selectDirectory(value)}
                          selectedDirectoryName={name}
                          tree={tree}
                        />
                      </Segment>
                    </Card.Content>
                  </Card>
                )}
                {name && (
                  <Directory
                    files={files}
                    destination={downloadDestination}
                    locked={locked}
                    name={name}
                    onClose={this.handleDeselectDirectory}
                    username={username}
                  />
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }
}

export default BrowseSession;
