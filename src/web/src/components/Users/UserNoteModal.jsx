import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import * as userNotes from '../../lib/userNotes';
import React, { useEffect, useState } from 'react';
import { Form, Header, Icon, Modal } from 'semantic-ui-react';
import { TooltipButton } from '../Shared';

const colors = [
  { icon: 'circle outline', get text() { return interfaceText("None"); }, value: null },
  {
    label: { circular: true, color: 'red', empty: true },
    get text() { return interfaceText("Red"); },
    value: 'red',
  },
  {
    label: { circular: true, color: 'orange', empty: true },
    get text() { return interfaceText("Orange"); },
    value: 'orange',
  },
  {
    label: { circular: true, color: 'yellow', empty: true },
    get text() { return interfaceText("Yellow"); },
    value: 'yellow',
  },
  {
    label: { circular: true, color: 'olive', empty: true },
    get text() { return interfaceText("Olive"); },
    value: 'olive',
  },
  {
    label: { circular: true, color: 'green', empty: true },
    get text() { return interfaceText("Green"); },
    value: 'green',
  },
  {
    label: { circular: true, color: 'teal', empty: true },
    get text() { return interfaceText("Teal"); },
    value: 'teal',
  },
  {
    label: { circular: true, color: 'blue', empty: true },
    get text() { return interfaceText("Blue"); },
    value: 'blue',
  },
  {
    label: { circular: true, color: 'violet', empty: true },
    get text() { return interfaceText("Violet"); },
    value: 'violet',
  },
  {
    label: { circular: true, color: 'purple', empty: true },
    get text() { return interfaceText("Purple"); },
    value: 'purple',
  },
  {
    label: { circular: true, color: 'pink', empty: true },
    get text() { return interfaceText("Pink"); },
    value: 'pink',
  },
  {
    label: { circular: true, color: 'brown', empty: true },
    get text() { return interfaceText("Brown"); },
    value: 'brown',
  },
  {
    label: { circular: true, color: 'grey', empty: true },
    get text() { return interfaceText("Grey"); },
    value: 'grey',
  },
  {
    label: { circular: true, color: 'black', empty: true },
    get text() { return interfaceText("Black"); },
    value: 'black',
  },
];

const isObject = (value) =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

const colorValues = new Set(colors.map(({ value }) => value));

const normalizeNoteResponse = (data) => {
  if (!isObject(data)) {
    return {
      color: null,
      isHighPriority: false,
      note: '',
    };
  }

  return {
    color: colorValues.has(data.color) ? data.color : null,
    isHighPriority:
      typeof data.isHighPriority === 'boolean' ? data.isHighPriority : false,
    note: typeof data.note === 'string' ? data.note : '',
  };
};

const UserNoteModal = ({ onClose, trigger, username }) => {
  useInterfaceLanguage();
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState('');
  const [color, setColor] = useState(null);
  const [isHighPriority, setIsHighPriority] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchNote = async () => {
      if (!username || !open) return;

      setLoading(true);
      try {
        const response = await userNotes.getNote({ username });
        const normalized = normalizeNoteResponse(response.data);
        setNote(normalized.note);
        setColor(normalized.color);
        setIsHighPriority(normalized.isHighPriority);
      } catch (error) {
        if (error.response && error.response.status === 404) {
          setNote('');
          setColor(null);
          setIsHighPriority(false);
        } else {
          console.error('Failed to fetch user note', error);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchNote();
  }, [open, username]);

  const handleClose = () => {
    setOpen(false);
    if (onClose) onClose();
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await userNotes.setNote({
        color,
        isHighPriority,
        note,
        username,
      });
      handleClose();
    } catch (error) {
      console.error('Failed to save user note', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      onClose={handleClose}
      onOpen={() => setOpen(true)}
      open={open}
      size="tiny"
      trigger={trigger}
    >
      <Header>
        <Icon name="sticky note outline" />
        <Modal.Content><LocalizedText source={"User Note:"} />{" "}{username}</Modal.Content>
      </Header>
      <Modal.Content>
        <Form loading={loading}>
          <Form.Dropdown
            fluid
            label={interfaceText("Color Rating")}
            onChange={(_, { value }) => setColor(value)}
            options={colors}
            placeholder={interfaceText("Select Color")}
            selection
            value={color}
           {...interfaceTextProps("Color Rating")}/>
          <Form.TextArea
            label={interfaceText("Note")}
            onChange={(event) => setNote(event.target.value)}
            placeholder={interfaceText("Enter notes about this user...")}
            rows={5}
            value={note}
           {...interfaceTextProps("Note")}/>
          <Form.Checkbox
            checked={isHighPriority}
            label={interfaceText("High Priority (Warning)")}
            onChange={(_, { checked }) => setIsHighPriority(checked)}
           {...interfaceTextProps("High Priority (Warning)")}/>
        </Form>
      </Modal.Content>
      <Modal.Actions>
        <TooltipButton
          onClick={handleClose}
          tooltip="Close without saving changes to this user's note."
        >
          <LocalizedText source={"Cancel"} /></TooltipButton>
        <TooltipButton
          disabled={loading}
          onClick={handleSave}
          primary
          tooltip="Save this user's color rating, priority flag, and note."
        >
          <LocalizedText source={"Save"} /></TooltipButton>
      </Modal.Actions>
    </Modal>
  );
};

export default UserNoteModal;
