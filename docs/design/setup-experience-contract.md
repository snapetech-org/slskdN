# Setup experience contract

Apply this to slskdN's existing first-run login and **System → Policies**,
**System → Options**, and **System → Shares** surfaces, plus
[Getting Started](../getting-started.md). The current guide asks operators to
change the default Web UI password, configure download destinations, configure
share roots, and separately enter Soulseek credentials. These are distinct
credentials and choices; preserve that distinction.

## Product-specific flow

Use the existing access-control surface to prompt for replacing default Web
UI credentials before exposing the service beyond its intended local network.
Then guide through the user's immediate task:

- **Search and download:** configure Soulseek credentials and one writable
  destination; validate connection and write access using existing health and
  status surfaces.
- **Share files:** ask whether to share anything. Start with no new share roots
  and let the operator choose specific directories through the current Shares
  settings; explain that shared roots expose files to other peers.
- **Optional automation or network features:** introduce wishlist, Lidarr,
  public DHT/mesh, VPN, and other extensions through their existing guides only
  when selected. Respect each feature's maturity, default, and safety gates.

Read only configured/masked state to skip completed questions. Do not copy the
Soulseek account password into Web UI auth, API tokens, or generated setup
reports. Explain port forwarding only when the operator enables a feature that
requires inbound connectivity.

## Contract

- Improve the existing login and System settings, not a parallel onboarding
  service or configuration store.
- Ask about user intent before enabling shares, automation, DHT/mesh, or other
  optional behavior.
- Keep sharing opt-in and use current directory validation; never add a host
  path to shares by guessing.
- Use existing settings saves, connection status, and setup-health checks as
  validation; keep the operator on the failing surface with an actionable fix.
- Do not claim experimental features are required or stable. Link the
  feature-maturity inventory from any optional branch.
- Keep the normal workflow short: secure access, connect Soulseek, choose a
  download destination, and search.

## Implementation tasks

Use the existing guide and Setup Health modal; do not add a new setup route.

- [x] **D1 — P1: Put the essential steps in the order a new operator needs.**
  Reorder the “Essential Settings” section in
  `docs/getting-started.md`: change the Web UI password, configure Soulseek
  credentials, choose a writable download destination, then search and
  download. Move share-directory setup under a clearly optional “Share files”
  step and state that it exposes chosen roots to other peers.
  **Done when:** an operator can start searching and downloading without
  configuring shares, Lidarr, DHT, mesh, or an API key; the guide keeps Web UI
  and Soulseek credentials clearly separate.

- [x] **D2 — P1: Separate core readiness from optional setup health.**
  In `src/web/src/lib/setupHealthCheck.js` and
  `src/web/src/components/System/Info/SetupHealthCheckModal.jsx`, keep an
  unconfigured writable destination and disconnected Soulseek session as
  core blockers, but render no share roots and unused API/integration
  credentials as optional information instead of lowering basic readiness.
  **Done when:** a server with authentication, a Soulseek connection, and a
  writable download path can be “ready to search/download” with zero shares
  and no optional integrations; configured shares and failed optional
  integrations remain visible with their current diagnostics.

- [x] **D3 — P2: Make health-check repairs open the owning existing settings
  surface.** Extend the current action data and
  `SetupHealthCheckModal.jsx` so checks for Policies, Options, and Shares
  open their matching System page; keep the modal read-only and preserve its
  current promise not to contact peers, test credentials, scan folders, or
  mutate configuration.
  **Done when:** each in-app repair action lands on the exact existing
  settings page and the diagnostic itself remains safe to open at any time.
