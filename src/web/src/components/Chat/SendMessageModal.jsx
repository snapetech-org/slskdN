import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import './Chat.css';
import React, { useEffect } from 'react';
import { Form, Header, Icon, Input, Modal } from 'semantic-ui-react';
import { TooltipButton } from '../Shared';

const usernameRef = React.createRef();

const SendMessageModal = ({ initiateConversation, ...rest }) => {
  useInterfaceLanguage();
  const [open, setOpen] = React.useState(false);
  const [username, setUsername] = React.useState('');
  const [message, setMessage] = React.useState('');

  useEffect(() => {
    if (open) {
      usernameRef.current.focus();
    }
  }, [open]);

  const validInput = () => {
    return username.length > 0 && message.length > 0;
  };

  const sendMessage = async () => {
    if (!validInput()) {
      usernameRef.current.focus();
      return;
    }

    await initiateConversation(username, message);
    setOpen(false);
  };

  return (
    <Modal
      onClose={() => setOpen(false)}
      onOpen={() => setOpen(true)}
      open={open}
      {...rest}
    >
      <Header>
        <Icon name="send" />
        <Modal.Content><LocalizedText source={"Send Private Message"} /></Modal.Content>
      </Header>
      <Modal.Content>
        <Form>
          <Form.Field>
            <Input
              onChange={(_event, data) => setUsername(data.value)}
              placeholder={interfaceText("Username")}
              ref={usernameRef}
             {...interfaceTextProps("Username")}/>
          </Form.Field>
          <Form.Field>
            <Input
              onChange={(_event, data) => setMessage(data.value)}
              placeholder={interfaceText("Message")}
             {...interfaceTextProps("Message")}/>
          </Form.Field>
        </Form>
      </Modal.Content>
      <Modal.Actions>
        <TooltipButton
          onClick={() => setOpen(false)}
          tooltip={interfaceText('Close this dialog without sending the private message.')}
        >
          <LocalizedText source={"Cancel"} /></TooltipButton>
        <TooltipButton
          disabled={!validInput()}
          onClick={() => sendMessage()}
          positive
          tooltip={
            validInput()
              ? interfaceText('Start or open a private conversation and send this message.')
              : interfaceText('Enter a username and message before sending.')
          }
        >
          <LocalizedText source={"Send"} /></TooltipButton>
      </Modal.Actions>
    </Modal>
  );
};

export default SendMessageModal;
