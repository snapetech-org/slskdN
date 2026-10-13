import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { activeChatKey } from '../../config';
import { setSessionStorageItem } from '../../lib/storage';
import UserNoteModal from '../Users/UserNoteModal';
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Dropdown } from 'semantic-ui-react';

const UserContextMenu = ({ children, trigger, username }) => {
  useInterfaceLanguage();
  const navigate = useNavigate();

  const handleBrowse = () => {
    navigate(`/browse?user=${encodeURIComponent(username)}`, {
      state: { user: username },
    });
  };

  const handleChat = () => {
    setSessionStorageItem(activeChatKey, username);
    navigate(`/chat?user=${encodeURIComponent(username)}`, {
      state: { user: username },
    });
  };

  return (
    <Dropdown
      className="user-context-menu"
      pointing="left"
      trigger={trigger || children}
    >
      <Dropdown.Menu>
        <Dropdown.Header
          content={username}
          icon="user"
        />
        <Dropdown.Item
          icon="folder open"
          onClick={handleBrowse}
          text={interfaceText("Browse Files")}
         {...interfaceTextProps("Browse Files")}/>
        <Dropdown.Item
          icon="comments"
          onClick={handleChat}
          text={interfaceText("Private Chat")}
         {...interfaceTextProps("Private Chat")}/>
        <UserNoteModal
          trigger={
            <Dropdown.Item
              icon="sticky note"
              text={interfaceText("User Notes")}
             {...interfaceTextProps("User Notes")}/>
          }
          username={username}
        />
      </Dropdown.Menu>
    </Dropdown>
  );
};

export default UserContextMenu;
