import SearchStatusIcon from '../SearchStatusIcon';
import { useInterfaceLanguage } from '../../../lib/interfaceLocale';
import React from 'react';
import { useMediaQuery } from 'react-responsive';
import { Button, Header, Icon, Popup, Segment } from 'semantic-ui-react';

const LocalizedText = ({ source, parameters }) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  return (
    <span lang={languageFor(source)} dir={directionFor(source)}>
      {t(source, parameters)}
    </span>
  );
};

const RefreshButton = ({
  creating,
  disabled,
  isSmallScreen,
  isTinyScreen,
  loaded,
  onCreate,
  searchText,
  working,
}) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const source = 'Search Again';
  if (!loaded) return null;

  return (
    <Button
      aria-label={t(source)}
      dir={directionFor(source)}
      disabled={disabled || working}
      icon={isSmallScreen && !isTinyScreen}
      lang={languageFor(source)}
      loading={creating}
      onClick={() => onCreate({ navigate: true, search: searchText })}
    >
      <Icon name="refresh" />
      {(!isSmallScreen || isTinyScreen) && <LocalizedText source={source} />}
    </Button>
  );
};

const StopOrDeleteButton = ({
  isComplete,
  isSmallScreen,
  isTinyScreen,
  removing,
  searchText,
  stopOrRemove,
  stopping,
  working,
}) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const source = isComplete ? 'Delete' : 'Stop';
  const accessibleSource = isComplete
    ? 'Delete completed search {search}'
    : 'Stop search {search}';

  return (
    <Button
      aria-label={t(accessibleSource, { search: searchText })}
      dir={directionFor(accessibleSource)}
      disabled={working}
      floated={isTinyScreen ? 'right' : undefined}
      icon={isSmallScreen && !isTinyScreen}
      lang={languageFor(accessibleSource)}
      loading={removing || stopping}
      negative
      onClick={stopOrRemove}
    >
      <Icon name={isComplete ? 'trash alternate' : 'stop circle'} />
      {(!isSmallScreen || isTinyScreen) && <LocalizedText source={source} />}
    </Button>
  );
};

const SearchDetailHeader = ({
  creating,
  disabled,
  loaded,
  loading,
  onCreate,
  onOpenGraph,
  onRemove,
  onStop,
  removing,
  search,
  stopping,
}) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const isSmallScreen = useMediaQuery({ query: '(max-width: 899px)' });
  const isTinyScreen = useMediaQuery({ query: '(max-width: 684px)' });

  const { isComplete, searchText, state } = search;
  const working = loading || creating || removing || stopping;
  const graphSource = 'Open Discovery Graph for {search}';

  const stopOrRemove = () => {
    if (isComplete) onRemove(search);
    else onStop(search);
  };

  const discoveryGraphButton = (
    <Button
      aria-label={t(graphSource, { search: searchText })}
      dir={directionFor(graphSource)}
      disabled={!loaded}
      icon={isSmallScreen && !isTinyScreen}
      lang={languageFor(graphSource)}
      onClick={onOpenGraph}
      style={!isSmallScreen ? { marginLeft: '0.5em' } : undefined}
    >
      <Icon name="crosshairs" />
      {(!isSmallScreen || isTinyScreen) && (
        <LocalizedText source="Discovery Graph" />
      )}
    </Button>
  );

  const stopSource = isComplete
    ? 'Delete this finished search.'
    : 'Stop this in-progress search.';

  const stopButton = (
    <StopOrDeleteButton
      isComplete={isComplete}
      isSmallScreen={isSmallScreen}
      isTinyScreen={isTinyScreen}
      removing={removing}
      searchText={searchText}
      stopOrRemove={stopOrRemove}
      stopping={stopping}
      working={working}
    />
  );

  return (
    <>
      <Segment className="search-detail-header-segment" raised>
        <Header>
          <SearchStatusIcon state={state} />
          {searchText}
        </Header>
        {!isTinyScreen && (
          <div className="search-detail-header-buttons">
            <Popup
              content={<LocalizedText source="Search Again" />}
              position="top center"
              trigger={
                <span>
                  <RefreshButton
                    creating={creating}
                    disabled={disabled}
                    isSmallScreen={isSmallScreen}
                    isTinyScreen={isTinyScreen}
                    loaded={loaded}
                    onCreate={onCreate}
                    searchText={searchText}
                    working={working}
                  />
                </span>
              }
            />
            <Popup
              content={<LocalizedText source="Open a Discovery Graph for this search phrase so the query history becomes a browsable neighborhood." />}
              position="top center"
              trigger={<span>{discoveryGraphButton}</span>}
            />
            <Popup
              content={<LocalizedText source={stopSource} />}
              position="top center"
              trigger={<span>{stopButton}</span>}
            />
          </div>
        )}
      </Segment>
      {isTinyScreen && (
        <Segment>
          <Popup
            content={<LocalizedText source="Search Again" />}
            position="top center"
            trigger={
              <span>
                <RefreshButton
                  creating={creating}
                  disabled={disabled}
                  isSmallScreen={isSmallScreen}
                  isTinyScreen={isTinyScreen}
                  loaded={loaded}
                  onCreate={onCreate}
                  searchText={searchText}
                  working={working}
                />
              </span>
            }
          />
          <Popup
            content={<LocalizedText source="Open a Discovery Graph for this search phrase so the query history becomes a browsable neighborhood." />}
            position="top center"
            trigger={<span>{discoveryGraphButton}</span>}
          />
          <Popup
            content={<LocalizedText source={stopSource} />}
            position="top center"
            trigger={<span>{stopButton}</span>}
          />
        </Segment>
      )}
    </>
  );
};

export default SearchDetailHeader;
