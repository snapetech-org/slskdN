import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';


import './Rooms.css';
import TooltipButton from '../Shared/TooltipButton';
import React, { useState } from 'react';
import {
  Button,
  Header,
  Icon,
  Input,
  Modal,
  Popup,
  Radio,
} from 'semantic-ui-react';

const RoomCreateModal = ({ onCreateRoom, ...modalOptions }) => {
  useInterfaceLanguage();
  const [open, setOpen] = useState(false);
  const [roomName, setRoomName] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleCreate = async () => {
    const name = roomName.trim();
    if (!name) {
      setError(interfaceText("Room name cannot be empty"));
      return;
    }

    setLoading(true);
    setError('');

    try {
      await onCreateRoom(name, isPrivate);
      setOpen(false);
      setRoomName('');
      setIsPrivate(false);
    } catch (error) {
      setError(getApiErrorMessage(error, { t: interfaceText }, 'Failed to create room'));
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleCreate();
    }
  };

  const close = () => {
    if (!loading) {
      setOpen(false);
      setError('');
      setRoomName('');
      setIsPrivate(false);
    }
  };

  return (
    <>
      <Popup
        content={interfaceText("Create or join a public Soulseek room by name. Private room creation is not supported by this server API.")}
        trigger={
          <Button
            color="green"
            icon
            onClick={() => setOpen(true)}
            title={interfaceText("Create New Room")}
           {...interfaceTextProps("Create Room")}>
            <Icon name="plus" />
            <LocalizedText source={"Create Room"} /></Button>
        }
       {...interfaceTextProps("Create or join a public Soulseek room by name. Private room creation is not supported by this server API.")}/>
      <Modal
        size="small"
        {...modalOptions}
        onClose={close}
        open={open}
      >
        <Modal.Header>
          <Icon name="plus" />
          <LocalizedText source={"Create New Room"} /></Modal.Header>
        <Modal.Content>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <Header as="h4"><LocalizedText source={"Room Name"} /></Header>
              <Input
                error={Boolean(error)}
                fluid
                onChange={(_, { value }) => setRoomName(value)}
                onKeyPress={handleKeyPress}
                placeholder={interfaceText("Enter room name...")}
                value={roomName}
               {...interfaceTextProps("Enter room name...")}/>
              {error && (
                <div
                  style={{
                    color: '#db2828',
                    fontSize: '12px',
                    marginTop: '4px',
                  }}
                >
                  {error}
                </div>
              )}
            </div>

            <div>
              <Header as="h4"><LocalizedText source={"Room Type"} /></Header>
              <div style={{ display: 'flex', gap: '24px' }}>
                <div
                  style={{ alignItems: 'center', display: 'flex', gap: '8px' }}
                >
                  <Radio
                    checked={!isPrivate}
                    name="roomType"
                    onChange={() => setIsPrivate(false)}
                    value="public"
                  />
                  <div>
                    <strong><LocalizedText source={"Public Room"} /></strong>
                    <div className="room-create-type-description">
                      <LocalizedText source={"Anyone can join and see the room"} /></div>
                  </div>
                </div>
                <div
                  style={{ alignItems: 'center', display: 'flex', gap: '8px' }}
                >
                  <Popup
                    content={interfaceText("Private room creation is not supported by this server API.")}
                    trigger={
                      <Radio
                        checked={isPrivate}
                        disabled
                        name="roomType"
                        onChange={() => setIsPrivate(true)}
                        value="private"
                      />
                    }
                   {...interfaceTextProps("Private room creation is not supported by this server API.")}/>
                  <div>
                    <strong><LocalizedText source={"Private Room"} /></strong>
                    <div className="room-create-type-description">
                      <LocalizedText source={"Not supported by this server API"} /></div>
                  </div>
                </div>
              </div>
            </div>

            <div className="room-create-note">
              <Icon name="info circle" />
              <strong><LocalizedText source={"Note:"} /></strong> <LocalizedText source={"Public room creation depends on server permissions. Private room creation is currently unavailable."} /></div>
          </div>
        </Modal.Content>
        <Modal.Actions>
          <TooltipButton
            disabled={loading}
            onClick={close}
            tooltip="Close this dialog without creating or joining a room."
            type="button"
          >
            <LocalizedText source={"Cancel"} /></TooltipButton>
          <TooltipButton
            disabled={!roomName.trim() || loading}
            loading={loading}
            onClick={handleCreate}
            positive
            tooltip="Create a public Soulseek room with this name and join it. Other users can see the room and its participants."
            type="button"
          >
            <Icon name="plus" />
            <LocalizedText source={"Create Room"} /></TooltipButton>
        </Modal.Actions>
      </Modal>
    </>
  );
};

export default RoomCreateModal;
