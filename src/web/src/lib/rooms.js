import api from './api';

const roomEndpoint = (roomName, operation, query = {}) => {
  const hasPathSeparator = roomName.includes('/');
  const path = hasPathSeparator
    ? `/rooms/by-name${operation}`
    : `/rooms/joined/${encodeURIComponent(roomName)}${operation}`;
  const parameters = new URLSearchParams();

  if (hasPathSeparator) {
    parameters.set('roomName', roomName);
  }

  Object.entries(query).forEach(([key, value]) => {
    if (value != null) {
      parameters.set(key, String(value));
    }
  });

  const queryString = parameters.toString();
  return queryString ? `${path}?${queryString}` : path;
};

export const getAvailable = async () => {
  const response = (await api.get('/rooms/available')).data;

  if (!Array.isArray(response)) {
    console.warn('got non-array response from rooms API', response);
    return [];
  }

  return response;
};

export const getJoined = async () => {
  const response = (await api.get('/rooms/joined')).data;

  if (!Array.isArray(response)) {
    console.warn('got non-array response from rooms API', response);
    return [];
  }

  return response;
};

export const getActivity = async () => {
  const response = (await api.get('/rooms/activity')).data;

  if (!response || typeof response !== 'object' || Array.isArray(response)) {
    console.warn('got non-object response from room activity API', response);
    return {};
  }

  return Object.fromEntries(
    Object.entries(response)
      .map(([roomName, timestamp]) => [roomName, Number(timestamp)])
      .filter(
        ([roomName, timestamp]) =>
          roomName.length > 0 && Number.isFinite(timestamp) && timestamp > 0,
      ),
  );
};

export const getMessages = async ({ roomName, since = null }) => {
  const response = (
    await api.get(roomEndpoint(roomName, '/messages', { since }))
  ).data;

  if (!Array.isArray(response)) {
    console.warn('got non-array response from rooms API', response);
    return [];
  }

  return response;
};

export const getUsers = async ({ roomName }) => {
  const response = (await api.get(roomEndpoint(roomName, '/users'))).data;

  if (!Array.isArray(response)) {
    console.warn('got non-array response from rooms API', response);
    return [];
  }

  return response;
};

export const join = async ({ roomName }) => {
  return api.post('/rooms/joined', JSON.stringify(roomName));
};

export const leave = async ({ roomName }) => {
  return api.delete(roomEndpoint(roomName, ''));
};

export const sendMessage = async ({ roomName, message }) => {
  return api.post(
    roomEndpoint(roomName, '/messages'),
    JSON.stringify(message),
  );
};

export const setTicker = async ({ roomName, message }) => {
  return api.post(
    roomEndpoint(roomName, '/ticker'),
    JSON.stringify(message),
  );
};

export const addRoomMember = async ({ roomName, username }) => {
  return api.post(
    roomEndpoint(roomName, '/members'),
    JSON.stringify(username),
  );
};
