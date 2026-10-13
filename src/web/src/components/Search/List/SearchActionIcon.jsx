import React from 'react';
import { Icon } from 'semantic-ui-react';
import TooltipButton from '../../Shared/TooltipButton';
import { useInterfaceLanguage } from '../../../lib/interfaceLocale';

const SearchActionIcon = ({ loading, onRemove, onStop, search, ...props }) => {
  const { t, languageFor, directionFor } = useInterfaceLanguage();
  const textSource = search.searchText || search.id;
  if (loading) {
    return (
      <Icon
        loading
        name="spinner"
        {...props}
      />
    );
  }

  if (search.state.includes('Completed')) {
    return (
      <TooltipButton
        aria-label={t('Delete completed search {search}', { search: textSource })}
        dir={directionFor('Delete completed search {search}')}
        lang={languageFor('Delete completed search {search}')}
        basic
        compact
        icon
        onClick={() => onRemove()}
        tooltip={(
          <span dir={directionFor('Delete the completed search {search} and its response history.')} lang={languageFor('Delete the completed search {search} and its response history.')}>
            {t('Delete the completed search {search} and its response history.', { search: textSource })}
          </span>
        )}
        {...props}
      >
        <Icon color="red" name="trash alternate" />
      </TooltipButton>
    );
  }

  return (
    <TooltipButton
      aria-label={t('Stop search {search}', { search: textSource })}
      dir={directionFor('Stop search {search}')}
      lang={languageFor('Stop search {search}')}
      basic
      compact
      icon
      onClick={() => onStop()}
      tooltip={(
        <span dir={directionFor('Stop {search} so it no longer requests responses from Soulseek peers.')} lang={languageFor('Stop {search} so it no longer requests responses from Soulseek peers.')}>
          {t('Stop {search} so it no longer requests responses from Soulseek peers.', { search: textSource })}
        </span>
      )}
      {...props}
    >
      <Icon color="red" name="stop circle" />
    </TooltipButton>
  );
};

export default SearchActionIcon;
