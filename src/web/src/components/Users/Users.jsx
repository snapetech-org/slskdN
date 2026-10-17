import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import './Users.css';
import { activeUserInfoKey } from '../../config';
import {
  getLocalStorageItem,
  removeLocalStorageItem,
  setLocalStorageItem,
} from '../../lib/storage';
import * as users from '../../lib/users';
import PlaceholderSegment from '../Shared/PlaceholderSegment';
import User from './User';
import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Icon, Input, Item, Loader, Segment } from 'semantic-ui-react';

const Users = () => {
  useInterfaceLanguage();
  const location = useLocation();
  const inputRef = useRef();
  const [user, setUser] = useState();
  const [usernameInput, setUsernameInput] = useState();
  const [selectedUsername, setSelectedUsername] = useState(undefined);
  // eslint-disable-next-line react/hook-use-state
  const [{ error, fetching }, setStatus] = useState({
    error: undefined,
    fetching: false,
  });

  const setInputText = (text) => {
    inputRef.current.value = text;
  };

  const setInputFocus = () => {
    inputRef.current.focus();
  };

  const clear = () => {
    removeLocalStorageItem(activeUserInfoKey);
    setSelectedUsername(undefined);
    setUser(undefined);
    setInputText('');
    setInputFocus();
  };

  const keyUp = (event) => (event.key === 'Escape' ? clear() : '');

  useLayoutEffect(() => {
    document.removeEventListener('keyup', keyUp, false);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const storedUsername =
      location.state?.user ||
      new URLSearchParams(location.search).get('user') ||
      getLocalStorageItem(activeUserInfoKey);

    if (storedUsername !== undefined) {
      setSelectedUsername(storedUsername);
      setInputText(storedUsername);
    }
  }, [location.search, location.state]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    document.addEventListener('keyup', keyUp, false);
    return () => document.removeEventListener('keyup', keyUp, false);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const fetchUser = async () => {
      if (!selectedUsername) {
        return;
      }

      setStatus({ error: undefined, fetching: true });

      try {
        const [info, status, endpoint] = await Promise.all([
          users.getInfo({ username: selectedUsername }),
          users.getStatus({ username: selectedUsername }),
          users.getEndpoint({ username: selectedUsername }),
        ]);

        setLocalStorageItem(activeUserInfoKey, selectedUsername);
        setUser({ ...info.data, ...status.data, ...endpoint.data });
        setStatus({ error: undefined, fetching: false });
      } catch (fetchError) {
        setStatus({ error: fetchError, fetching: false });
      }
    };

    fetchUser();
  }, [selectedUsername]);

  return (
    <div className="users-container">
      <Segment
        className="users-segment"
        raised
      >
        <div className="users-segment-icon">
          <Icon
            name="users"
            size="big"
          />
        </div>
        <Input
          action={
            !fetching &&
            (user == null
              ? {
                  'aria-label': interfaceText("Search for user"),
                  icon: 'search',
                  onClick: () => setSelectedUsername(usernameInput),
                  title: interfaceText("Search for user"),
                }
              : {
                  'aria-label': interfaceText("Clear selected user"),
                  color: 'red',
                  icon: 'x',
                  onClick: clear,
                  title: interfaceText("Clear selected user"),
                })
          }
          className="users-input"
          disabled={fetching}
          input={
            <input
              data-lpignore="true"
              disabled={Boolean(user) || fetching}
              placeholder={interfaceText("Username")}
              type="search"
             {...interfaceTextProps("Username")}/>
          }
          loading={fetching}
          onChange={(event) => setUsernameInput(event.target.value)}
          onKeyUp={(event) =>
            event.key === 'Enter' ? setSelectedUsername(usernameInput) : ''
          }
          placeholder={interfaceText("Username")}
          ref={inputRef}
          size="big"
         {...interfaceTextProps("Username")}/>
      </Segment>
      {fetching ? (
        <Loader
          active
          className="search-loader"
          inline="centered"
          size="big"
        />
      ) : (
        <div>
          {error ? (
            <span><LocalizedText source={"Failed to retrieve information for"} />{" "}{selectedUsername}</span>
          ) : user == null ? (
            <PlaceholderSegment
              caption={interfaceText("No user info to display")}
              icon="users"
            />
          ) : (
            <Segment
              className="users-user"
              raised
            >
              <Item.Group>
                <User {...user} />
              </Item.Group>
            </Segment>
          )}
        </div>
      )}
    </div>
  );
};

export default Users;
