import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../../lib/interfaceLocale";
import { Icon, Item } from 'semantic-ui-react';

const ImagePlaceholder = () => (
  <div className="users-picture-placeholder ui small image">
    <Icon
      name="camera"
      size="big"
    />
  </div>
);

const Presence = ({ presence }) => {
  const colors = {
    Away: 'yellow',
    Online: 'green',
  };

  return (
    <Icon
      color={colors[presence] || 'grey'}
      name="circle"
    />
  );
};

const FreeUploadSlot = ({ hasFreeUploadSlot }) => (
  <Icon
    color={hasFreeUploadSlot ? 'green' : 'red'}
    name={hasFreeUploadSlot ? 'check' : 'close'}
  />
);

const User = ({
  address,
  description,
  hasPicture,
  picture,
  port,
  presence,
  queueLength,
  uploadSlots,
  username,
}) => (
  <Item>
    {hasPicture ? (
      <Item.Image
        size="small"
        src={`data:image;base64,${picture}`}
      />
    ) : (
      <ImagePlaceholder />
    )}

    <Item.Content>
      <Item.Header as="a">
        <Presence presence={presence} />
        {username}
      </Item.Header>
      <Item.Meta>
        <LocalizedText source={"Free Upload Slot:"} />{" "}<FreeUploadSlot hasFreeUploadSlot /><LocalizedText source={", Total Upload Slots:"} />{" "}{uploadSlots}<LocalizedText source={", Queue Length:"} />{" "}{queueLength}<LocalizedText source={", IP Address:"} />{" "}{address}
        <LocalizedText source={", Port:"} />{" "}{port}
      </Item.Meta>
      <Item.Description>{description || 'No user info.'}</Item.Description>
    </Item.Content>
  </Item>
);

export default User;
