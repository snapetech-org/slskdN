import { interfaceText, interfaceTextProps } from "../../../lib/interfaceLocale";
export const contentExamples = {
  audio: {
    album: {
      content: 'content:audio:album:mb-67890',
      external: 'mb:release:67890',
    },
    artist: {
      content: 'content:audio:artist:mb-abc123',
      external: 'mb:artist:abc123',
    },
    track: {
      content: 'content:audio:track:mb-12345',
      external: 'mb:recording:12345',
    },
  },
  image: {
    artwork: {
      content: 'content:image:artwork:discogs-11111',
      external: 'discogs:release:11111',
    },
    photo: {
      content: 'content:image:photo:flickr-67890',
      external: 'flickr:photo:67890',
    },
  },
  video: {
    movie: {
      content: 'content:video:movie:imdb-tt0111161',
      external: 'imdb:tt0111161',
    },
    series: {
      content: 'content:video:series:tvdb-12345',
      external: 'tvdb:series:12345',
    },
  },
};

export const podWorkflowSections = [
  {
    get description() { return interfaceText("Publish or retrieve pod metadata through DHT workflows."); },
    href: '#podcore-dht-publishing',
    get label() { return interfaceText("DHT Publishing"); },
    risk: 'Publishes metadata',
  },
  {
    get description() { return interfaceText("Manage signed membership records, bans, and roles."); },
    href: '#pod-membership-management',
    get label() { return interfaceText("Membership"); },
    risk: 'Publishes membership state',
  },
  {
    get description() { return interfaceText("Verify membership, message authenticity, and role claims."); },
    href: '#pod-membership-verification',
    get label() { return interfaceText("Verification"); },
    risk: 'Read-only checks',
  },
  {
    get description() { return interfaceText("Find listed pods by name, tag, content, or registry scan."); },
    href: '#pod-discovery',
    get label() { return interfaceText("Discovery"); },
    risk: 'Read-only unless registering',
  },
  {
    get description() { return interfaceText("Request, accept, leave, and review pod membership flows."); },
    href: '#pod-join-leave',
    get label() { return interfaceText("Join/Leave"); },
    risk: 'Publishes signed membership events',
  },
  {
    get description() { return interfaceText("Route messages, target peers, and review deduplication state."); },
    href: '#pod-message-routing',
    get label() { return interfaceText("Routing"); },
    risk: 'Sends pod messages',
  },
  {
    get description() { return interfaceText("Search, count, clean up, rebuild, and vacuum pod messages."); },
    href: '#pod-message-storage',
    get label() { return interfaceText("Storage"); },
    risk: 'Local storage operations',
  },
  {
    get description() { return interfaceText("Synchronize missed messages and last-seen timestamps."); },
    href: '#pod-message-backfill',
    get label() { return interfaceText("Backfill"); },
    risk: 'Syncs pod state',
  },
  {
    get description() { return interfaceText("Create, inspect, update, and delete pod channels."); },
    href: '#pod-channel-management',
    get label() { return interfaceText("Channels"); },
    risk: 'Mutates pod structure',
  },
  {
    get description() { return interfaceText("Search content and create content-linked pods."); },
    href: '#pod-content-linking',
    get label() { return interfaceText("Content Linking"); },
    risk: 'Can create pods',
  },
  {
    get description() { return interfaceText("Publish, aggregate, and review pod opinions."); },
    href: '#pod-opinion-management',
    get label() { return interfaceText("Opinions"); },
    risk: 'Publishes opinion data',
  },
  {
    get description() { return interfaceText("Sign messages, verify signatures, and generate key pairs."); },
    href: '#pod-message-signing',
    get label() { return interfaceText("Signing"); },
    risk: 'Handles key material',
  },
];

export const podWorkflowFilterOptions = [
  { key: 'all', get text() { return interfaceText("Show all pod workflows"); }, value: 'all' },
  ...podWorkflowSections.map((section) => ({
    key: section.href,
    text: section.label,
    value: section.href.slice(1),
  })),
];
