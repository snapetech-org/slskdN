import React, { lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

const Browse = lazy(() => import('./Browse/Browse'));
const Dashboard = lazy(() => import('./Dashboard/Dashboard'));
const Collections = lazy(() => import('./Collections/Collections'));
const Contacts = lazy(() => import('./Contacts/Contacts'));
const DiscoveryGraphAtlasPage = lazy(() =>
  import('./Search/DiscoveryGraphAtlasPage'));
const Messaging = lazy(() => import('./Messaging/Messaging'));
const PlaylistIntake = lazy(() => import('./PlaylistIntake/PlaylistIntake'));
const Searches = lazy(() => import('./Search/Searches'));
const ShareGroups = lazy(() => import('./ShareGroups/ShareGroups'));
const SharedWithMe = lazy(() => import('./Shares/SharedWithMe'));
const SolidSettings = lazy(() => import('./Solid/SolidSettings'));
const System = lazy(() => import('./System/System'));
const TransferManager = lazy(() => import('./Transfers/TransferManager'));
const Users = lazy(() => import('./Users/Users'));
const Wishlist = lazy(() => import('./Wishlist/Wishlist'));
const LidarrPage = lazy(() => import('./Lidarr/Lidarr'));

const RouteMissRedirect = () => <Navigate replace to="/dashboard" />;

const AppRoutes = ({ applicationOptions, applicationState, isAgent, theme }) => {
  if (isAgent) {
    return (
      <Routes>
        <Route
          element={(
            <System
              options={applicationOptions}
              state={applicationState}
            />
          )}
          path="/system"
        />
        <Route
          element={(
            <System
              options={applicationOptions}
              state={applicationState}
            />
          )}
          path="/system/:tab"
        />
        <Route
          element={<Navigate replace to="/system" />}
          path="*"
        />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route
        element={<Navigate replace to="/dashboard" />}
        path="/"
      />
      <Route
        element={<Dashboard />}
        path="/dashboard"
      />
      <Route
        element={(
          <div className="view">
            <Collections />
          </div>
        )}
        path="/collections"
      />
      <Route
        element={(
          <div className="view">
            <SolidSettings />
          </div>
        )}
        path="/solid"
      />
      <Route
        element={<DiscoveryGraphAtlasPage server={applicationState.server} />}
        path="/discovery-graph"
      />
      <Route
        element={(
          <div className="view">
            <PlaylistIntake />
          </div>
        )}
        path="/playlist-intake"
      />
      <Route
        element={(
          <div className="view">
            <Searches server={applicationState.server} />
          </div>
        )}
        path="/searches"
      />
      <Route
        element={(
          <div className="view">
            <Searches server={applicationState.server} />
          </div>
        )}
        path="/searches/:id"
      />
      <Route
        element={(
          <div className="view">
            <Wishlist />
          </div>
        )}
        path="/wishlist"
      />
      <Route
        element={(
          <div className="view">
            <LidarrPage />
          </div>
        )}
        path="/lidarr"
      />
      <Route
        element={<Browse />}
        path="/browse"
      />
      <Route
        element={<Users />}
        path="/users"
      />
      <Route
        element={<Contacts />}
        path="/contacts"
      />
      <Route
        element={(
          <div className="view">
            <ShareGroups />
          </div>
        )}
        path="/sharegroups"
      />
      <Route
        element={(
          <div className="view">
            <SharedWithMe />
          </div>
        )}
        path="/shared"
      />
      <Route
        element={(
          <Messaging
            initialKind="chat"
            state={applicationState}
          />
        )}
        path="/chat"
      />
      <Route
        element={(
          <Messaging
            initialKind="pod"
            state={applicationState}
          />
        )}
        path="/pods"
      />
      <Route
        element={(
          <Messaging
            initialKind="pod"
            state={applicationState}
          />
        )}
        path="/pods/:podId"
      />
      <Route
        element={(
          <Messaging
            initialKind="pod"
            state={applicationState}
          />
        )}
        path="/pods/:podId/channels/:channelId"
      />
      <Route
        element={(
          <Messaging
            initialKind="room"
            state={applicationState}
          />
        )}
        path="/rooms"
      />
      <Route
        element={(
          <Messaging
            initialKind="mixed"
            state={applicationState}
          />
        )}
        path="/messages"
      />
      <Route
        element={(
          <div className="view view-transfer">
            <TransferManager
              direction="upload"
              server={applicationState.server}
            />
          </div>
        )}
        path="/uploads"
      />
      <Route
        element={(
          <div className="view view-transfer">
            <TransferManager
              direction="download"
              server={applicationState.server}
            />
          </div>
        )}
        path="/downloads"
      />
      <Route
        element={(
          <System
            options={applicationOptions}
            state={applicationState}
            theme={theme}
          />
        )}
        path="/system"
      />
      <Route
        element={(
          <System
            options={applicationOptions}
            state={applicationState}
            theme={theme}
          />
        )}
        path="/system/:tab"
      />
      <Route
        element={<RouteMissRedirect />}
        path="*"
      />
    </Routes>
  );
};

export default AppRoutes;
