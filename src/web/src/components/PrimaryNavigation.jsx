import React from 'react';
import { NavLink } from 'react-router-dom';
import { Icon, Menu, Popup } from 'semantic-ui-react';

const NAVIGATION_GROUPS = [
  {
    icon: 'compass outline',
    key: 'discover',
    label: 'Discover',
    items: [
      { icon: 'crosshairs', label: 'Discovery Graph', testId: 'nav-discovery-graph', to: '/discovery-graph' },
      { icon: 'list alternate outline', label: 'Playlist Intake', testId: 'nav-playlist-intake', to: '/playlist-intake' },
      { icon: 'star', label: 'Wishlist', testId: 'nav-wishlist', to: '/wishlist' },
      { icon: 'music', label: 'Lidarr', testId: 'nav-lidarr', to: '/lidarr' },
    ],
  },
  {
    icon: 'user circle outline',
    key: 'network',
    label: 'Network',
    items: [
      { icon: 'users', label: 'Users', testId: 'nav-users', to: '/users' },
      { icon: 'address book', label: 'Contacts', testId: 'nav-contacts', to: '/contacts' },
      { icon: 'key', label: 'Solid', testId: 'nav-solid', to: '/solid' },
    ],
  },
  {
    icon: 'share alternate',
    key: 'sharing',
    label: 'Sharing',
    items: [
      { icon: 'list', label: 'Collections', testId: 'nav-collections', to: '/collections' },
      { icon: 'users', label: 'Share Groups', testId: 'nav-groups', to: '/sharegroups' },
      { icon: 'share', label: 'Shared with Me', testId: 'nav-shared-with-me', to: '/shared' },
      { icon: 'folder open', label: 'Browse', testId: 'nav-browse', to: '/browse' },
    ],
  },
];

const NavigationIcon = ({ alert, alertTestId, name }) => (
  <span className="navigation-alert-icon">
    <Icon name={name} />
    {alert && (
      <span
        aria-label="New activity"
        className="navigation-alert-dot"
        data-testid={alertTestId}
        role="status"
      />
    )}
  </span>
);

const NavigationDropdown = ({ group }) => {
  const [open, setOpen] = React.useState(false);

  return (
    <Popup
      className="navigation-dropdown-popup"
      on="click"
      onClose={() => setOpen(false)}
      onOpen={() => setOpen(true)}
      open={open}
      position="bottom left"
      trigger={(
        <Menu.Item
          aria-expanded={open}
          aria-haspopup="menu"
          className="navigation-dropdown-trigger"
          data-navigation-targets={group.items.map((item) => item.testId).join(' ')}
          data-testid={`nav-group-${group.key}`}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              setOpen((current) => !current);
            }
          }}
          role="button"
          tabIndex={0}
        >
          <Icon name={group.icon} />
          {group.label}
          <Icon name="dropdown" />
        </Menu.Item>
      )}
    >
      <Menu className="navigation-dropdown-menu" vertical>
        {group.items.map((item) => (
          <NavLink key={item.to} onClick={() => setOpen(false)} to={item.to}>
            <Menu.Item data-testid={item.testId}>
              <Icon name={item.icon} />
              {item.label}
            </Menu.Item>
          </NavLink>
        ))}
      </Menu>
    </Popup>
  );
};

const PrimaryNavigation = ({ isAgent, navActivity, version }) => (
  <div className="navigation-primary">
    {version.isCanary && (
      <Menu.Item>
        <Icon color="yellow" name="flask" />
        Canary
      </Menu.Item>
    )}
    {isAgent ? (
      <Menu.Item>
        <Icon name="detective" />
        Agent Mode
      </Menu.Item>
    ) : (
      <>
        <NavLink to="/dashboard">
          <Menu.Item data-testid="nav-dashboard">
            <Icon name="exchange" />
            Overview
          </Menu.Item>
        </NavLink>
        <NavLink to="/searches">
          <Menu.Item data-testid="nav-search">
            <Icon name="search" />
            Search
          </Menu.Item>
        </NavLink>
        <NavLink to="/downloads">
          <Menu.Item data-testid="nav-downloads">
            <Icon name="download" />
            Downloads
          </Menu.Item>
        </NavLink>
        <NavLink to="/uploads">
          <Menu.Item data-testid="nav-uploads">
            <Icon name="upload" />
            Uploads
          </Menu.Item>
        </NavLink>
        <NavLink to="/messages">
          <Menu.Item data-testid="nav-messages">
            <NavigationIcon
              alert={navActivity.rooms || navActivity.chat}
              alertTestId={navActivity.chat ? 'nav-chat-alert' : 'nav-rooms-alert'}
              name="comments"
            />
            Messages
          </Menu.Item>
        </NavLink>
        {NAVIGATION_GROUPS.map((group) => (
          <NavigationDropdown group={group} key={group.key} />
        ))}
      </>
    )}
  </div>
);

export default PrimaryNavigation;
