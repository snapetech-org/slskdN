import LocalizedText from "../Shared/LocalizedText";
import { interfaceAttributeText, interfacePresentationText, interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { usePlayer } from './PlayerContext';
import React from 'react';
import { Button, Icon, Popup } from 'semantic-ui-react';

const PlayCollectionItemButton = ({ item, size = 'small' }) => {
  useInterfaceLanguage();
  const { playItem, playerVisible } = usePlayer();

  if (!playerVisible) return null;

  return (
    <Popup
      content={<LocalizedText source={"Play this item through the local stream endpoint and update your now-playing status."} />}
      trigger={
        <Button
          {...interfaceTextProps("Play {track} in the browser player")} aria-label={interfaceAttributeText("Play {track} in the browser player", { track: item.title || item.fileName || item.contentId || interfaceText("Track") })}
          data-testid="player-play-item"
          icon
          onClick={() => playItem(item, { replaceQueue: true })}
          size={size}
        >
          <Icon name="play" />
        </Button>
      }
     {...interfaceTextProps("Play this item through the local stream endpoint and update your now-playing status.")}/>
  );
};

export default PlayCollectionItemButton;
