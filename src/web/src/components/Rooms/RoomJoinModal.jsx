import { getRegionalLocale } from '../../lib/regionalFormat';
import './Rooms.css';
import * as rooms from '../../lib/rooms';
import TooltipButton from '../Shared/TooltipButton';
import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import {
  Button,
  Dimmer,
  Header,
  Icon,
  Input,
  Loader,
  Modal,
  Popup,
  Segment,
  Table,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const normalizeRoom = (room) => {
  if (
    !room ||
    typeof room !== 'object' ||
    Array.isArray(room) ||
    typeof room.name !== 'string' ||
    !room.name
  ) {
    return undefined;
  }

  return {
    ...room,
    isModerated: room.isModerated === true,
    isOwned: room.isOwned === true,
    isPrivate: room.isPrivate === true,
    userCount: Number.isFinite(room.userCount) ? room.userCount : 0,
  };
};

const RoomJoinModal = ({ joinRoom: parentJoinRoom, ...modalOptions }) => {
  const [open, setOpen] = useState(false);
  const [available, setAvailable] = useState([]);
  const [selected, setSelected] = useState(undefined);
  const [sortBy, setSortBy] = useState('name');
  const [sortOrder, setSortOrder] = useState('desc');
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const getAvailableRooms = async () => {
      setLoading(true);
      try {
        const availableResult = await rooms.getAvailable();
        setAvailable(
          asArray(availableResult).map(normalizeRoom).filter(Boolean),
        );
      } catch {
        toast.error('Failed to load room list');
        setAvailable([]);
      } finally {
        setLoading(false);
      }
    };

    if (open) getAvailableRooms();
  }, [open]);

  const sortedAvailable = useMemo(() => {
    const sorted = [...available].filter((room) =>
      room.name.toLowerCase().includes(filter.toLowerCase()),
    );

    sorted.sort((a, b) => {
      const comparison = typeof a[sortBy] === 'string'
        ? a[sortBy].localeCompare(b[sortBy])
        : a[sortBy] - b[sortBy];

      return sortOrder === 'asc' ? comparison : -comparison;
    });

    return sorted;
  }, [available, filter, sortBy, sortOrder]);

  const close = () => {
    setAvailable([]);
    setSelected(undefined);
    setSortBy('name');
    setSortOrder('desc');
    setFilter('');
    setOpen(false);
  };

  const joinRoom = async () => {
    await parentJoinRoom(selected);
    close();
  };

  const isSelected = (room) => selected === room.name;
  const changeSort = (nextSortBy) => {
    if (sortBy === nextSortBy) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
      return;
    }

    setSortBy(nextSortBy);
    setSortOrder('asc');
  };

  return (
    <>
      <Popup
        content="Browse available Soulseek rooms and join the selected room."
        trigger={
          <Button
            color="green"
            icon
            onClick={() => setOpen(true)}
            title="Join Room"
          >
            <Icon name="sign in" />
            Join Room
          </Button>
        }
      />
      <Modal
        className="join-room-modal"
        onClose={() => close()}
        open={open}
        {...modalOptions}
      >
        <Header>
          <Icon name="comments" />
          <Modal.Content>Join Room</Modal.Content>
        </Header>
        <Modal.Content scrolling>
          {loading ? (
            <Dimmer
              active
              inverted
            >
              <Loader
                content="Loading Room List"
                inverted
              />
            </Dimmer>
          ) : (
            <>
              <Input
                fluid
                icon="filter"
                onChange={(_, event) => setFilter(event.value)}
                placeholder="Room Filter"
              />
              {!filter.trim() ? (
                <Segment
                  placeholder
                  textAlign="center"
                >
                  <Header icon>
                    <Icon name="search" />
                    Type to search rooms
                  </Header>
                  <p>{available.length.toLocaleString(getRegionalLocale())} rooms available. Enter a name above to filter.</p>
                </Segment>
              ) : sortedAvailable.length === 0 ? (
                <Segment
                  placeholder
                  textAlign="center"
                >
                  <Header icon>
                    <Icon name="comments outline" />
                    No rooms match &ldquo;{filter}&rdquo;
                  </Header>
                  <p>Try a different search term.</p>
                </Segment>
              ) : (
                <Table
                  celled
                  selectable
                >
                    <Table.Header>
                      <Table.Row>
                      <Table.HeaderCell
                        aria-sort={sortBy === 'name'
                          ? sortOrder === 'asc' ? 'ascending' : 'descending'
                          : 'none'}
                      >
                        <TooltipButton
                          aria-label="Sort available rooms by name"
                          basic
                          className="room-sort-button"
                          compact
                          fluid
                          onClick={() => changeSort('name')}
                          style={{ textAlign: 'left' }}
                          tooltip={sortBy === 'name'
                            ? `Sort room names ${sortOrder === 'asc' ? 'descending' : 'ascending'} to change the order of the list.`
                            : 'Sort available Soulseek rooms alphabetically so you can find a room by name.'}
                        >
                          Name
                          {sortBy === 'name' && (
                            <Icon name={sortOrder === 'asc' ? 'chevron up' : 'chevron down'} />
                          )}
                        </TooltipButton>
                      </Table.HeaderCell>
                      <Table.HeaderCell
                        aria-sort={sortBy === 'userCount'
                          ? sortOrder === 'asc' ? 'ascending' : 'descending'
                          : 'none'}
                      >
                        <TooltipButton
                          aria-label="Sort available rooms by user count"
                          basic
                          className="room-sort-button"
                          compact
                          fluid
                          onClick={() => changeSort('userCount')}
                          style={{ textAlign: 'left' }}
                          tooltip={sortBy === 'userCount'
                            ? `Sort room member counts ${sortOrder === 'asc' ? 'descending' : 'ascending'} to change the order of the list.`
                            : 'Sort available Soulseek rooms by participant count so you can find active rooms.'}
                        >
                          Users
                          {sortBy === 'userCount' && (
                            <Icon name={sortOrder === 'asc' ? 'chevron up' : 'chevron down'} />
                          )}
                        </TooltipButton>
                      </Table.HeaderCell>
                    </Table.Row>
                  </Table.Header>
                  <Table.Body>
                    {sortedAvailable.map((room) => (
                      <Table.Row
                        key={room.name}
                        onClick={() => setSelected(room.name)}
                        style={isSelected(room) ? { fontWeight: 'bold' } : {}}
                      >
                        <Table.Cell>
                          {isSelected(room) && (
                            <Icon
                              color="green"
                              name="check"
                            />
                          )}
                          {room.isPrivate && <Icon name="lock" />}
                          {room.isOwned && <Icon name="chess queen" />}
                          {room.isModerated && <Icon name="gavel" />}
                          {room.name}
                        </Table.Cell>
                        <Table.Cell>{room.userCount}</Table.Cell>
                      </Table.Row>
                    ))}
                  </Table.Body>
                </Table>
              )}
            </>
          )}
        </Modal.Content>
        <Modal.Actions>
          <TooltipButton
            onClick={() => close()}
            tooltip="Close the dialog without joining a Soulseek room."
            type="button"
          >
            Cancel
          </TooltipButton>
          <TooltipButton
            disabled={!selected}
            onClick={() => joinRoom()}
            positive
            tooltip="Join the selected Soulseek room; its members will see this account in the participant list."
            type="button"
          >
            Join
          </TooltipButton>
        </Modal.Actions>
      </Modal>
    </>
  );
};

export default RoomJoinModal;
