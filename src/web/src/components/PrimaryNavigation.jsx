import { useInterfaceLanguage } from "../lib/interfaceLocale";
import React from 'react';
import { NavLink } from 'react-router-dom';
import { Icon, Menu, Popup } from 'semantic-ui-react';


const NAVIGATION_GROUPS = [
  {
    icon: 'compass outline',
    key: 'discover',
    label: "Discover",
    items: [
      { icon: 'crosshairs', label: "Discovery Graph", testId: 'nav-discovery-graph', to: '/discovery-graph' },
      { icon: 'list alternate outline', label: "Playlist Intake", testId: 'nav-playlist-intake', to: '/playlist-intake' },
      { icon: 'star', label: "Wishlist", testId: 'nav-wishlist', to: '/wishlist' },
      { icon: 'music', label: "Lidarr", testId: 'nav-lidarr', to: '/lidarr' },
    ],
  },
  {
    icon: 'user circle outline',
    key: 'network',
    label: "Network",
    items: [
      { icon: 'users', label: "Users", testId: 'nav-users', to: '/users' },
      { icon: 'address book', label: "Contacts", testId: 'nav-contacts', to: '/contacts' },
      { icon: 'key', label: "Solid", testId: 'nav-solid', to: '/solid' },
    ],
  },
  {
    icon: 'share alternate',
    key: 'sharing',
    label: "Sharing",
    items: [
      { icon: 'list', label: "Collections", testId: 'nav-collections', to: '/collections' },
      { icon: 'users', label: "Share Groups", testId: 'nav-groups', to: '/sharegroups' },
      { icon: 'share', label: "Shared with Me", testId: 'nav-shared-with-me', to: '/shared' },
      { icon: 'folder open', label: "Browse", testId: 'nav-browse', to: '/browse' },
    ],
  },
];

const LocalizedText = ({ source }) => {
  const { directionFor, languageFor, t } = useInterfaceLanguage();
  return (
    <span dir={directionFor(source)} lang={languageFor(source)}>
      {t(source)}
    </span>
  );
};

const NavigationIcon = ({ alert, alertTestId, name }) => {
  const { directionFor, languageFor, t } = useInterfaceLanguage();
  return (
    <span className="navigation-alert-icon">
      <Icon name={name} />
      {alert && (
        <span
          aria-label={t('New activity')}
          className="navigation-alert-dot"
          data-testid={alertTestId}
          dir={directionFor('New activity')}
          lang={languageFor('New activity')}
          role="status"
        />
      )}
    </span>
  );
};

const NavigationDropdown = ({ group }) => {
  const [open, setOpen] = React.useState(false);
  const { directionFor, languageFor, t } = useInterfaceLanguage();
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
          aria-label={t(group.label)}
          aria-expanded={open}
          aria-haspopup="menu"
          className="navigation-dropdown-trigger"
          data-navigation-targets={group.items.map((item) => item.testId).join(' ')}
          data-testid={`nav-group-${group.key}`}
          dir={directionFor(group.label)}
          lang={languageFor(group.label)}
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
          <LocalizedText source={group.label} />
          <Icon name="dropdown" />
        </Menu.Item>
      )}
    >
      <Menu className="navigation-dropdown-menu" vertical>
        {group.items.map((item) => (
          <NavLink key={item.to} onClick={() => setOpen(false)} to={item.to}>
            <Menu.Item data-testid={item.testId} dir={directionFor(item.label)} lang={languageFor(item.label)}>
              <Icon name={item.icon} />
              <LocalizedText source={item.label} />
            </Menu.Item>
          </NavLink>
        ))}
      </Menu>
    </Popup>
  );
};

const PrimaryNavigation = ({ isAgent, navActivity, version }) => {
  const { directionFor, languageFor, t } = useInterfaceLanguage();
  return (
  <div className="navigation-primary">
    {version.isCanary && (
      <Menu.Item dir={directionFor('Canary')} lang={languageFor('Canary')}>
        <Icon color="yellow" name="flask" />
        <LocalizedText source="Canary" />
      </Menu.Item>
    )}
    {isAgent ? (
      <Menu.Item dir={directionFor('Agent Mode')} lang={languageFor('Agent Mode')}>
        <Icon name="detective" />
        <LocalizedText source="Agent Mode" />
      </Menu.Item>
    ) : (
      <>
        <NavLink aria-label={t('Overview')} to="/dashboard">
          <Menu.Item data-testid="nav-dashboard" dir={directionFor('Overview')} lang={languageFor('Overview')}>
            <Icon name="exchange" />
            <LocalizedText source="Overview" />
          </Menu.Item>
        </NavLink>
        <NavLink aria-label={t('Search')} to="/searches">
          <Menu.Item data-testid="nav-search" dir={directionFor('Search')} lang={languageFor('Search')}>
            <Icon name="search" />
            <LocalizedText source="Search" />
          </Menu.Item>
        </NavLink>
        <NavLink aria-label={t('Downloads')} to="/downloads">
          <Menu.Item data-testid="nav-downloads" dir={directionFor('Downloads')} lang={languageFor('Downloads')}>
            <Icon name="download" />
            <LocalizedText source="Downloads" />
          </Menu.Item>
        </NavLink>
        <NavLink aria-label={t('Uploads')} to="/uploads">
          <Menu.Item data-testid="nav-uploads" dir={directionFor('Uploads')} lang={languageFor('Uploads')}>
            <Icon name="upload" />
            <LocalizedText source="Uploads" />
          </Menu.Item>
        </NavLink>
        <NavLink aria-label={t('Messages')} to="/messages">
          <Menu.Item data-testid="nav-messages" dir={directionFor('Messages')} lang={languageFor('Messages')}>
            <NavigationIcon
              alert={navActivity.rooms || navActivity.chat}
              alertTestId={navActivity.chat ? 'nav-chat-alert' : 'nav-rooms-alert'}
              name="comments"
            />
            <LocalizedText source="Messages" />
          </Menu.Item>
        </NavLink>
        {NAVIGATION_GROUPS.map((group) => (
          <NavigationDropdown group={group} key={group.key} />
        ))}
      </>
    )}
  </div>
  );
};

export default PrimaryNavigation;
