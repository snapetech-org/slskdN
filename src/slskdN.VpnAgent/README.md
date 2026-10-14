# slskdN VPN Host Integration

This bundle documents and installs a host-side VPN setup for slskdN. It is
intentionally outside Kubernetes: the app runs as a host service, web UI remains
local, and Soulseek traffic is routed through a VPN interface.

The default implementation is WireGuard plus NAT-PMP for VPN providers that
expose port forwarding through NAT-PMP. OpenVPN, Tailscale, and other tunnel
interfaces are supported as externally-managed interfaces. The app entry point
is `slskdN-vpn-agent`; it owns the Gluetun-compatible API, ingress forwarding,
UID split routing, verification, status, watchdog behavior, and ingress cleanup.

## Guide Map

- [Start Here: VPN Agent](GETTING_STARTED.md): release installation and exact
  first-use steps for Linux, Windows, and macOS.
- [Manual Linux WireGuard setup](manual-linux-wireguard.md): full
  WireGuard/NAT-PMP path with outbound routing, ingress configs, services, and
  verification.
- [External tunnel setup](external-tunnel.md): OpenVPN, Tailscale, static
  forwarded ports, and externally-managed tunnel interfaces.
- [Self-hosted relay](self-hosted-relay.md): keep slskdN and shares behind
  CGNAT while a bounded Tailscale or WireGuard VPS companion provides public
  ingress/egress.
- [Self-hosted relay tester guide](https://github.com/snapetech-org/slskdN/blob/main/docs/self-hosted-relay-tester-guide.md):
  install a published release and run the exact OCI/home acceptance checks.
- [Windows and macOS](windows-macos.md): platform fail-closed behavior,
  required inputs, and limitations.
- [API contract](api-contract.md): Gluetun-compatible endpoints, slskdN
  port-forward summary endpoint, runtime state files, and command ownership.

## Supported Modes

| Mode | Tunnel owner | Port forwarding | Best for |
|------|--------------|-----------------|----------|
| `wireguard` | `wg-quick` / this host setup | NAT-PMP or static; per-slot netns supported | Full transparent setup with dynamic forwarded ports |
| `openvpn` | Existing OpenVPN service/client | Static or host-namespace NAT-PMP if the provider supports it | Users with `.ovpn` providers or distro OpenVPN services |
| `tailscale` | `tailscaled` | Usually static/manual; Tailscale does not provide generic public VPN port forwarding | Private tailnet routing or custom exit-node setups |
| other | Existing tunnel interface | Static or provider-specific backend | Any Linux tunnel exposing an interface name |

The agent includes platform-specific fail-closed enforcement paths:

- Linux: UID policy routing through the VPN routing table plus a blackhole
  fallback route.
- Windows: Windows Defender Firewall rules block the configured slskdN program
  on every currently-up non-VPN interface, leaving the named VPN interface
  usable.
- macOS: a `pf` anchor blocks the configured service user from egressing on any
  interface other than the named VPN interface, while preserving loopback.

Provider port forwarding still depends on the VPN provider. NAT-PMP dynamic
claiming is strongest on Linux/WireGuard because each ingress slot can own its
own namespace. Windows/macOS should use the same status API with static or
provider-managed forwarded ports unless a provider-specific claiming backend is
added.

## How Custom This Is

The setup has three layers:

1. Standard Linux policy routing:
   the application service runs under one UID, and that UID is routed through the
   configured VPN interface.
   A blackhole default route in the VPN table makes traffic fail closed if the VPN
   route is missing.
2. Provider-specific port forwarding:
   the checked-in default uses `natpmpc` to ask the VPN provider for forwarded
   ports and renews the leases before they expire. Other backends can write the
   same runtime state without changing the routing layer.
3. Custom glue:
   some providers return short-lived, random public ports. slskdN can consume a
   Gluetun control API and dynamically advertise the forwarded port without
   rebinding its local listener, but this setup does not require a real Gluetun
   instance. The local compatibility service exposes just enough of the Gluetun
   API for slskdN, and the agent keeps transparent DNAT rules in sync with the
   current listener.

So: not a one-off shell hack, but also not stock slskdN. The repeatable part is
in this directory. The non-repeatable part is only the private VPN config
material, which must stay out of git.

## Do You Need the Agent?

Consolidating slskdN listener ports reduces how many forwarded ports are useful,
but it does not replace the host VPN enforcement layer.

Keep the agent when you want any of these:

- slskdN's Soulseek traffic must fail closed if the VPN is down
- the web UI/API must stay local while Soulseek traffic uses VPN egress
- the VPN provider gives random or short-lived forwarded ports
- slskdN should learn the current forwarded Soulseek port automatically
- inbound VPN forwards should DNAT transparently back to the host service
- multiple VPN configs should each hold one forwarded ingress slot

You usually do not need the agent when:

- you are not using a VPN for Soulseek traffic
- your VPN client already provides a trusted kill switch and a stable forwarded
  port that you configure manually in slskdN
- you only need outbound privacy and do not care about inbound reachability
- you run slskdN inside a container/network namespace already owned by another
  VPN manager

The practical default is: use slskdN's consolidated ports plus this agent for a
repeatable Linux install. Treat no-agent setups as manual/advanced installs
where the operator owns fail-closed routing and forwarded-port updates.

## Provider-Agnostic Boundary

These parts are generic and can work with WireGuard, OpenVPN, Tailscale, or any
other tunnel that exposes a Linux network interface:

- UID policy routing for the configured service user
- fail-closed blackhole route in the VPN routing table
- excluding local web UI/API traffic from the VPN route
- the local Gluetun-compatible API consumed by slskdN
- the public Soulseek port advertisement following the forwarded public port
  while the local `soulseek.listen_port` remains bound to its configured port

WireGuard has the deepest checked-in support:

- `wg-quick` can bring up the outbound tunnel
- one WireGuard config can be used per inbound forwarding slot
- each inbound slot gets a network namespace
- veth/DNAT sends each VPN namespace back to the host slskdN listener
- NAT-PMP can be run inside the matching namespace so each tunnel can claim and
  hold its own port

OpenVPN, Tailscale, and provider desktop clients are supported as
externally-managed tunnel interfaces. Set `SLSKDN_VPN_TUNNEL_TYPE` and
`SLSKDN_VPN_IFACE` to the interface that already exists. In that mode the agent
does not start the VPN client; it applies fail-closed UID routing, verifies the
interface, exposes forwarded-port state to slskdN, and can use either static
forward files or NAT-PMP from the host namespace if the provider supports it.

Examples:

```bash
# OpenVPN tun interface managed by an existing openvpn-client service
SLSKDN_VPN_TUNNEL_TYPE=openvpn
SLSKDN_VPN_IFACE=tun0
SLSKDN_VPN_TUNNEL_SERVICE=openvpn-client@provider

# Tailscale interface managed by tailscaled
SLSKDN_VPN_TUNNEL_TYPE=tailscale
SLSKDN_VPN_IFACE=tailscale0
SLSKDN_VPN_TUNNEL_SERVICE=tailscaled
VPN_PORT_FORWARD_BACKEND=static
```

The Linux backend requires systemd, `ip rule`, and iptables. WireGuard mode also
requires WireGuard tools. The C# agent and state/API contract are portable, and
the `platform-split` command now provides platform-native fail-closed adapters:

- Linux: this backend, using service UID policy routing and netns ingress slots
- Windows: Windows Defender Firewall rules for the configured slskdN executable
  and non-VPN interfaces; set `SLSKDN_APP_PATH` and `SLSKDN_VPN_IFACE`
- macOS: a `pf` anchor keyed by `SLSKDN_SERVICE_USER` and `SLSKDN_VPN_IFACE`;
  the helper installs the anchor file and references it from `/etc/pf.conf`

Provider-specific port claiming is still backend-dependent. Use static/provider
forward files on Windows and macOS unless your provider exposes a claim API that
has been added to the agent.

These parts are provider-specific:

- how a forwarded public port is requested
- whether the provider supports multiple simultaneous forwarded ports
- whether the provider gives a stable port or random short leases
- how often forwarded ports must be renewed
- whether public port and private/local port can differ
- whether the provider exposes NAT-PMP, PCP, UPnP, a REST API, static account
  assignments, or no forwarding API at all

For NAT-PMP providers, the provider backend calls `natpmpc` against the gateway
configured by `PF_GATEWAY`, stores `pfN.env`, and renews before the provider
lease expires.

For another provider, keep the routing, systemd, and Gluetun shim model, then
switch or replace only the provider backend in `slskdN-vpn-agent ingress`. In
WireGuard mode the provider backend can also use netns/DNAT slots. In external
tunnel mode the provider must forward directly to the host/tunnel interface. The
backend writes the same state fields for each slot:

```env
local_port=50300
target_port=51000
proto=tcp
public_port=51000
public_ip=203.0.113.10
namespace=slskdNpf0
```

The Gluetun-compatible API reads `public_ip` and `public_port` from `pf0.env`.
slskdN does not care whether the port came from NAT-PMP, a static VPN
provider dashboard, a provider REST API, or a real Gluetun container.

Backend selection is controlled with:

```bash
SLSKDN_VPN_TUNNEL_TYPE=wireguard
VPN_PORT_FORWARD_BACKEND=natpmp
```

Supported checked-in values:

- `SLSKDN_VPN_TUNNEL_TYPE=wireguard`: full outbound, netns ingress, NAT-PMP, and
  static-forward support
- `SLSKDN_VPN_TUNNEL_TYPE=openvpn`: externally-managed OpenVPN interface; split
  routing plus static or host-namespace NAT-PMP forwarding
- `SLSKDN_VPN_TUNNEL_TYPE=tailscale`: externally-managed Tailscale interface;
  split routing plus static forwarding when a reachable public endpoint is
  available
- any other `SLSKDN_VPN_TUNNEL_TYPE` value is treated as an external tunnel
  interface and verified by interface name
- `natpmp`: NAT-PMP behavior, using `natpmpc`
- `static`: reads preassigned forwarded ports from files

Other port-forward providers should be added as a new claim method in
`Program.cs` and a new branch in `ClaimIngressSlot()`.

## Provider Patterns

### NAT-PMP or PCP Providers

This is the NAT-PMP path. Configure it when:

- the VPN provider supports NAT-PMP or compatible port mapping
- `PF_GATEWAY` points to the provider's NAT-PMP gateway
- `natpmpc -g "$GW" -a ...` returns `Mapped public port ...`

Set `PF_GATEWAY` in the systemd unit or service environment if the provider's
NAT-PMP gateway is not the default `10.2.0.1`.

### Static Forwarded-Port Providers

If the provider assigns static ports in an account dashboard, no claim loop is
needed. Set:

```bash
VPN_PORT_FORWARD_BACKEND=static
SLSKDN_VPN_STATIC_FORWARD_DIR=/etc/slskdN-vpn/static-forwards
```

Create one file per slot:

```bash
sudo install -d -m 700 /etc/slskdN-vpn/static-forwards
sudo tee /etc/slskdN-vpn/static-forwards/pf0.env >/dev/null <<'EOF'
public_port=51000
public_ip=203.0.113.10
local_port=50300
proto=tcp
EOF
```

Only `public_port` and `public_ip` are required. If `local_port` or `proto` are
present, the agent verifies they match the discovered slskdN listener slot before
writing runtime state.

For the Soulseek TCP slot, `public_port` must be the port slskdN should
advertise. The private/local port is normally `50300`; if a static provider
requires a different private port for the Soulseek slot, set
`SOULSEEK_PRIVATE_PORT` in the service environment so the namespace and DNAT rule
are created for that port from the start.

### Provider REST API

If the provider exposes an API for forwarded ports, replace only the NAT-PMP call
inside a new backend method with API calls and write the same `pfN.env` state.
The rest of the ingress flow should not need to change.

### Real Gluetun

If slskdN runs behind a real Gluetun instance, most of this bundle is unnecessary.
Point slskdN directly at Gluetun's control server:

```yaml
integrations:
  vpn:
    enabled: true
    port_forwarding: true
    polling_interval: 5000
    gluetun:
      url: http://127.0.0.1:8000
      timeout: 5000
```

You would still need fail-closed routing if slskdN is not actually inside
Gluetun's network namespace/container.

### Providers Without Port Forwarding

Outbound can still be forced through VPN, but inbound Soulseek connectivity will
be degraded or unavailable. Search may work while downloads/uploads are unreliable
because peers cannot open inbound connections to the advertised listener.

In that case, keep only the split-routing/fail-closed layer and disable
`integrations.vpn.port_forwarding`.

## Files Installed

App:

- `/usr/local/lib/slskdN-vpn-agent/slskdN-vpn-agent`
- `/usr/local/bin/slskdN-vpn-agent`

Systemd units:

- `wg-quick@slskdN-vpn.service`
- `slskdN-vpn-split.service`
- `slskdN-vpn-ingress.service`
- `slskdN-vpn-ingress-renew.timer`
- `slskdN-vpn-gluetun-compat.service`
- `slskdN-vpn-watchdog.service`
- `slskdN-vpn-watchdog.timer`

State:

- `/var/lib/slskdN-vpn/pfN.env`
- `/var/lib/slskdN-vpn/summary.env`

Secrets and VPN configs:

- `/etc/wireguard/slskdN-vpn.conf`
- `/etc/wireguard/slskdN-vpn-ingress/*.conf`
- provider OpenVPN configs, Tailscale auth material, or other tunnel credentials
  managed by the chosen VPN client

Do not commit VPN configs or credentials. They contain private keys, auth tokens,
or account-identifying material.

Redacted examples live in `examples/`.

## Required Inputs

Install packages for WireGuard mode:

```bash
sudo apt-get install -y dotnet-sdk-10.0 wireguard-tools natpmpc jq curl iptables iproute2
```

For external OpenVPN/Tailscale mode, install the tunnel client instead of
`wireguard-tools`. Keep `natpmpc` only if the provider exposes NAT-PMP from the
host namespace:

```bash
# OpenVPN example
sudo apt-get install -y dotnet-sdk-10.0 openvpn jq curl iptables iproute2

# Tailscale example
sudo apt-get install -y dotnet-sdk-10.0 tailscale jq curl iptables iproute2
```

Create the primary outbound WireGuard config:

```bash
sudo install -d -m 700 /etc/wireguard
sudo install -m 600 vpn-outbound.conf /etc/wireguard/slskdN-vpn.conf
```

Create one or more ingress WireGuard configs:

```bash
sudo install -d -m 700 /etc/wireguard/slskdN-vpn-ingress
sudo install -m 600 pf0.conf /etc/wireguard/slskdN-vpn-ingress/00-soulseek.conf
sudo install -m 600 pf1.conf /etc/wireguard/slskdN-vpn-ingress/pf1.conf
sudo install -m 600 pf2.conf /etc/wireguard/slskdN-vpn-ingress/pf2.conf
```

Recommended: use a different VPN key/config for outbound than for ingress.
Running the same WireGuard private key in two interfaces at once can break
handshakes.

For OpenVPN, Tailscale, or another external tunnel, start that tunnel before
starting the agent and note the interface name:

```bash
ip link show tun0       # common OpenVPN interface
ip link show tailscale0 # common Tailscale interface
```

## slskdN Config

Configure slskdN with the canonical `integrations` section:

```yaml
integrations:
  vpn:
    enabled: true
    port_forwarding: true
    polling_interval: 5000
    gluetun:
      url: http://127.0.0.1:8010
      timeout: 5000
```

The compatibility service reads `/var/lib/slskdN-vpn/pf0.env` and exposes:

- `GET /v1/publicip/ip`
- `GET /v1/portforward`
- `GET /v1/openvpn/portforwarded`
- `GET /v1/openvpn/status`
- `GET /v1/slskdn/portforwards`

slskdN polls that API, marks VPN ready, and rewrites `soulseek.listenPort` to
the forwarded public port.

`/v1/slskdn/portforwards` is the slskdN extension for multiple forwarded
listeners. It returns the ingress mode, claimed slot count, and every `pfN`
mapping, for example:

```json
{
  "mode": "core",
  "claimed": 3,
  "forwards": [
    {
      "slot": 0,
      "localPort": 50300,
      "targetPort": 51000,
      "proto": "tcp",
      "publicPort": 51000,
      "publicIp": "203.0.113.10",
      "namespace": "slskdNpf0"
    }
  ]
}
```

The ordinary Gluetun-compatible endpoints remain single-port endpoints for
compatibility. Slot `pf0` is the Soulseek TCP slot and is the port slskdN
advertises today. Additional slots let slskdN inspect DHT/overlay mappings
without requiring every VPN provider to mimic Gluetun.

### Port Budget and Renewal

The consolidated default needs one public TCP forward for regular Soulseek,
type-1 obfuscated peer traffic, and mesh TCP rendezvous. Public DHT, mesh UDP,
and QUIC rendezvous use one optional UDP forward on the same port number. A
dedicated obfuscation TCP forward is only needed when
`soulseek.obfuscation.listen_port` is explicitly nonzero.

`pfN.env` records both `public_port` and the local `local_port`/`target_port`.
They may differ: the provider-facing public port is what slskdN advertises,
while DNAT still delivers to the stable local listener. The renewal timer calls
`renew-ingress` to refresh NAT-PMP leases without tearing down the existing
namespace, veth, or DNAT path. A full `ingress` reconciliation is reserved for
startup or recovery. The watchdog checks every active ingress namespace's
WireGuard handshake independently of the primary VPN tunnel; if an ingress
slot goes stale, it immediately reconciles the ingress service so the provider
lease can be reclaimed before the public port expires. Keep
`slskdN-vpn-watchdog.timer` enabled for this recovery path.

For WireGuard ingress, DNAT terminates on a host-side veth address. On Linux
hosts with a native nftables input policy, the agent also manages a narrow input
chain/jump for the configured target ports; iptables `FORWARD` rules alone do
not permit packets that are locally delivered to the host veth.

## Install

From this repo:

```bash
cd src/slskdN.VpnAgent
sudo ./install.sh
```

The installer defaults to `SLSKDN_VPN_TUNNEL_TYPE=wireguard` and
`VPN_PORT_FORWARD_BACKEND=natpmp`. For a static provider, pass the backend
explicitly:

```bash
sudo VPN_PORT_FORWARD_BACKEND=static ./install.sh
```

For an externally-managed OpenVPN or Tailscale interface, start the VPN client
first and pass the tunnel type/interface:

```bash
sudo SLSKDN_VPN_TUNNEL_TYPE=openvpn \
  SLSKDN_VPN_IFACE=tun0 \
  SLSKDN_VPN_TUNNEL_SERVICE=openvpn-client@provider \
  VPN_PORT_FORWARD_BACKEND=static \
  ./install.sh
```

Then restart slskdN once:

```bash
sudo systemctl restart slskdN
```

For Windows fail-closed enforcement, run an elevated shell and point the agent
at the installed slskdN executable and the VPN interface alias shown by
`Get-NetAdapter`:

```powershell
$env:SLSKDN_APP_PATH = "C:\Program Files\slskdN\slskd.exe"
$env:SLSKDN_VPN_IFACE = "ProtonVPN"
slskdN-vpn-agent platform-split
```

For macOS fail-closed enforcement, run as root and use the active VPN `utun`
interface from `ifconfig`:

```bash
sudo SLSKDN_SERVICE_USER=slskdN \
  SLSKDN_VPN_IFACE=utun4 \
  slskdN-vpn-agent platform-split
```

The timer renews NAT-PMP mappings every 30 seconds by default without
restarting the ingress service. Keep the timer shorter than the provider lease
lifetime. If a mapping is lost, the renewal command can claim a replacement and
the compatibility API exposes the new public port for slskdN to advertise.

## Service User and UID

There is no universal UID. Each install may use a different numeric UID or a different service account.
The agent resolves the UID from the configured service user at runtime.

Defaults:

```bash
SLSKDN_SERVICE_USER=slskdN
SLSKDN_PROCESS_NAME=slskdN
SLSKDN_SERVICE_NAME=slskdN
```

Use explicit overrides when the app is packaged differently:

```bash
SLSKDN_SERVICE_USER=slskdN
SLSKDN_SERVICE_UID=12345
SLSKDN_PROCESS_NAME=slskdN
SLSKDN_SERVICE_NAME=slskdN
```

`SLSKDN_SERVICE_UID` is optional when the user exists in `/etc/passwd`; it is
only needed for unusual service managers or containers where name lookup is not
available.

## App Commands

The installed app entry point is:

```bash
slskdN-vpn-agent <command>
```

Commands:

- `slskdN-vpn-agent api`: serve the Gluetun-compatible control API
- `slskdN-vpn-agent ingress`: discover slskdN listener ports, create VPN ingress namespaces, and claim/write forwarded port state
- `slskdN-vpn-agent renew-ingress`: renew existing NAT-PMP mappings without rebuilding ingress namespaces or veth links
- `slskdN-vpn-agent cleanup-ingress`: remove ingress namespaces, veth links, rules, and route tables
- `slskdN-vpn-agent split`: configure UID policy routing and fail-closed table
- `slskdN-vpn-agent platform-split`: configure Windows/macOS native firewall
  enforcement, or Linux UID policy routing
- `slskdN-vpn-agent verify`: run the full health check
- `slskdN-vpn-agent status`: alias-style human status check
- `slskdN-vpn-agent watchdog`: run one watchdog check and recover ingress after repeated failures

## Forwarding Modes

The default ingress mode is `core`: Soulseek TCP, all discovered TCP app
listeners such as DHT rendezvous, and one selected UDP forward. This is the
recommended mode for current slskdN because it benefits from consolidated
listener ports without hiding required TCP services.

```ini
[Service]
Environment=SLSKDN_VPN_INGRESS_MODE=core
Environment=SLSKDN_VPN_COMPACT_UDP_PORT=50300
```

Use `compact` only when you intentionally want to hold just the Soulseek TCP
forward plus one UDP forward:

```ini
[Service]
Environment=SLSKDN_VPN_INGRESS_MODE=compact
Environment=SLSKDN_VPN_COMPACT_UDP_PORT=50300
```

Use `all` when you want every discovered public slskdN listener to get its own
VPN ingress slot:

```ini
[Service]
Environment=SLSKDN_VPN_INGRESS_MODE=all
```

`core` and `compact` are not protocol multiplexers. Core skips extra UDP
listeners. Compact skips any other discovered TCP or UDP listeners. Use compact
only after slskdN is configured so skipped listeners are disabled, private-only,
or reachable through a future app-level mux.

The agent scales by config count, not by hard-coded port names. Each complete
WireGuard config in `/etc/wireguard/slskdN-vpn-ingress/*.conf` can back one
ingress slot. The default ceiling is 20 slots and can be changed with
`SLSKDN_VPN_MAX_INGRESS_SLOTS`. Two configs claim up to two forwarded ports;
twenty configs claim up to twenty, subject to provider account limits and host
resources.

The companion exposes all claimed mappings through `/v1/slskdn/portforwards`;
older slskdN builds only consume the `pf0` Soulseek mapping through the
Gluetun-compatible API.

slskdN now defaults `dht.dht_port` to the same numeric value as
`soulseek.listen_port` (`50300`), since TCP and UDP port spaces are separate
and don't collide. `dht.overlay_port` (the mesh TCP overlay handshake port)
stays a distinct number (`50305`) because it's TCP like the Soulseek listen
port and can't share a number with it:

```yaml
dht:
  overlay_port: 50305  # TCP, distinct from soulseek.listen_port (also TCP)
  dht_port: 50300      # UDP, shares soulseek.listen_port's number
```

That's two protocol mappings for most VPN providers: one TCP for the Soulseek
listen port (which also now carries type-1 obfuscated connections by default,
sharing that same TCP port -- see `docs/soulseek-type1-obfuscation.md`) and
one UDP. `SharedMeshUdpListener` is the "one UDP owner inside slskdN that
demultiplexes DHT and overlay packets before dispatching them" this section
used to describe as future work -- it's implemented now, and also demuxes
QUIC control- and data-plane traffic onto that same UDP port by ALPN. Getting
to one TCP total for Soulseek peer traffic *and* mesh overlay traffic (still
two separate TCP ports, `50300` and `50305`) would require slskdN to add a
TCP protocol multiplexer in front of both; that remains unimplemented.

## Manual Install

Use this section if you do not want to run `install.sh`. These commands do the
same thing explicitly.

### 1. Install Prerequisites

Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y dotnet-sdk-10.0 wireguard-tools natpmpc jq curl iptables iproute2
```

Fedora/RHEL-style hosts:

```bash
sudo dnf install -y dotnet-sdk-10.0 wireguard-tools natpmpc jq curl iptables iproute
```

For OpenVPN or Tailscale external tunnel mode, replace `wireguard-tools` with
the VPN client package and omit `natpmpc` unless the provider supports NAT-PMP:

```bash
sudo apt-get install -y dotnet-sdk-10.0 openvpn jq curl iptables iproute2
sudo apt-get install -y dotnet-sdk-10.0 tailscale jq curl iptables iproute2
```

### 2. Add VPN Configs

#### WireGuard Mode

Create the directories:

```bash
sudo install -d -m 700 /etc/wireguard
sudo install -d -m 700 /etc/wireguard/slskdN-vpn-ingress
```

Install the outbound config:

```bash
sudo install -m 600 /path/to/vpn-outbound.conf /etc/wireguard/slskdN-vpn.conf
```

Install ingress configs. Use as many complete VPN configs as you want to hold
forwarded ports for:

```bash
sudo install -m 600 /path/to/pf0.conf /etc/wireguard/slskdN-vpn-ingress/00-soulseek.conf
sudo install -m 600 /path/to/pf1.conf /etc/wireguard/slskdN-vpn-ingress/pf1.conf
sudo install -m 600 /path/to/pf2.conf /etc/wireguard/slskdN-vpn-ingress/pf2.conf
```

`00-soulseek.conf` is consumed first and is used for the Soulseek TCP listener.
Do not reuse the outbound private key in an ingress config at the same time.

#### External Tunnel Mode

For OpenVPN, Tailscale, or another provider client, configure and start the VPN
client using that provider's normal instructions. The slskdN agent only needs
the interface name and, optionally, the systemd unit name:

```bash
ip link show tun0
ip link show tailscale0
systemctl is-active openvpn-client@provider
systemctl is-active tailscaled
```

If the provider gives static forwarded ports, create static forward files:

```bash
sudo install -d -m 700 /etc/slskdN-vpn/static-forwards
sudo tee /etc/slskdN-vpn/static-forwards/pf0.env >/dev/null <<'EOF'
public_port=51000
public_ip=203.0.113.10
local_port=50300
proto=tcp
EOF
```

### 3. Install the Agent

From this repo directory:

```bash
cd src/slskdN.VpnAgent
sudo dotnet publish slskdN-vpn-agent.csproj -c Release -r linux-x64 --self-contained true -p:PublishSingleFile=true -o /usr/local/lib/slskdN-vpn-agent
sudo ln -sfn /usr/local/lib/slskdN-vpn-agent/slskdN-vpn-agent /usr/local/bin/slskdN-vpn-agent
sudo install -d -m 755 /var/lib/slskdN-vpn
```

### 4. Install Systemd Units

```bash
cd src/slskdN.VpnAgent
sudo install -D -m 644 systemd/slskdN-vpn-split.service /etc/systemd/system/slskdN-vpn-split.service
sudo install -D -m 644 systemd/slskdN-vpn-ingress.service /etc/systemd/system/slskdN-vpn-ingress.service
sudo install -D -m 644 systemd/slskdN-vpn-ingress-renew.service /etc/systemd/system/slskdN-vpn-ingress-renew.service
sudo install -D -m 644 systemd/slskdN-vpn-ingress-renew.timer /etc/systemd/system/slskdN-vpn-ingress-renew.timer
sudo install -D -m 644 systemd/slskdN-vpn-gluetun-compat.service /etc/systemd/system/slskdN-vpn-gluetun-compat.service
sudo install -D -m 644 systemd/slskdN-vpn-watchdog.service /etc/systemd/system/slskdN-vpn-watchdog.service
sudo install -D -m 644 systemd/slskdN-vpn-watchdog.timer /etc/systemd/system/slskdN-vpn-watchdog.timer
sudo systemctl daemon-reload
```

### 5. Configure slskdN

Edit `/etc/slskdN/slskd.yml` and add:

```yaml
integrations:
  vpn:
    enabled: true
    port_forwarding: true
    polling_interval: 5000
    gluetun:
      url: http://127.0.0.1:8010
      timeout: 5000
```

If the file already has `integrations:`, merge the `vpn:` block into it instead
of adding a second top-level `integrations:` key.

### 6. Enable Services

Start the outbound VPN and UID policy routing:

```bash
sudo systemctl enable --now wg-quick@slskdN-vpn.service
sudo systemctl enable --now slskdN-vpn-split.service
```

Start the Gluetun-compatible status API and the VPN ingress renewal timer:

```bash
sudo systemctl enable --now slskdN-vpn-gluetun-compat.service
sudo systemctl enable --now slskdN-vpn-ingress-renew.timer
sudo systemctl enable --now slskdN-vpn-watchdog.timer
```

Restart slskdN and force one immediate ingress reconciliation:

```bash
sudo systemctl restart slskdN
sleep 10
sudo systemctl restart slskdN-vpn-ingress.service
```

The `sleep` gives slskdN time to poll the compatibility API and move its
Soulseek listener to the current forwarded public port. The timer will keep
things reconciled after that.

### Backend Environment Overrides

For non-default backends, add a systemd drop-in:

```bash
sudo systemctl edit slskdN-vpn-ingress.service
```

Example for static provider ports:

```ini
[Service]
Environment=VPN_PORT_FORWARD_BACKEND=static
Environment=SLSKDN_VPN_STATIC_FORWARD_DIR=/etc/slskdN-vpn/static-forwards
```

Example for NAT-PMP with a provider-specific gateway:

```ini
[Service]
Environment=VPN_PORT_FORWARD_BACKEND=natpmp
Environment=PF_GATEWAY=10.8.0.1
Environment=PF_LIFETIME=300
```

Example for OpenVPN external tunnel mode:

```ini
[Service]
Environment=SLSKDN_VPN_TUNNEL_TYPE=openvpn
Environment=SLSKDN_VPN_IFACE=tun0
Environment=SLSKDN_VPN_TUNNEL_SERVICE=openvpn-client@provider
Environment=VPN_PORT_FORWARD_BACKEND=static
Environment=SLSKDN_VPN_STATIC_FORWARD_DIR=/etc/slskdN-vpn/static-forwards
```

Example for Tailscale external tunnel mode:

```ini
[Service]
Environment=SLSKDN_VPN_TUNNEL_TYPE=tailscale
Environment=SLSKDN_VPN_IFACE=tailscale0
Environment=SLSKDN_VPN_TUNNEL_SERVICE=tailscaled
Environment=VPN_PORT_FORWARD_BACKEND=static
Environment=SLSKDN_VPN_STATIC_FORWARD_DIR=/etc/slskdN-vpn/static-forwards
```

Then reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart slskdN-vpn-ingress.service
sudo systemctl restart slskdN-vpn-ingress-renew.timer
```

### 7. Manual One-Shot Port Claim

If you only want to test the port-claiming layer without enabling the timer:

```bash
sudo systemctl start wg-quick@slskdN-vpn.service
sudo systemctl start slskdN-vpn-split.service
sudo /usr/local/bin/slskdN-vpn-agent ingress
sudo /usr/local/bin/slskdN-vpn-agent api
```

The last command runs in the foreground. In another shell:

```bash
curl -fsS http://127.0.0.1:8010/v1/publicip/ip
curl -fsS http://127.0.0.1:8010/v1/portforward
```

Stop the foreground agent process with `Ctrl-C` when done.

## Verification

Use the bundled verifier when available:

```bash
sudo /usr/local/bin/slskdN-vpn-agent verify
```

From a repo checkout, without installing or changing anything:

```bash
cd src/slskdN.VpnAgent
sudo ./install.sh --check
```

`--check` only runs validation; it does not install files or restart services.

Check services:

```bash
systemctl is-active slskdN wg-quick@slskdN-vpn slskdN-vpn-split slskdN-vpn-gluetun-compat slskdN-vpn-ingress-renew.timer
```

Check egress split:

```bash
sudo -u slskdN curl -4 -m 10 -s https://ifconfig.me
curl -4 -m 10 -s https://ifconfig.me
```

The two IPs should differ. The first should be the VPN egress IP.

Check slskdN VPN state:

```bash
curl -fsS -H "X-API-Key: <api-key>" http://127.0.0.1:5030/api/v0/application | jq '.server,.vpn'
```

Expected:

- server state: `Connected, LoggedIn`
- VPN `isReady: true`
- VPN `forwardedPort` set

Check current VPN mappings:

```bash
sudo cat /var/lib/slskdN-vpn/summary.env
for f in /var/lib/slskdN-vpn/pf*.env; do echo "--$(basename "$f")"; sudo cat "$f"; done
```

## Watchdog

`slskdN-vpn-watchdog.timer` runs every minute. It calls
`/usr/local/bin/slskdN-vpn-agent watchdog`, which internally runs verification quietly
and records consecutive failures in
`/var/lib/slskdN-vpn/watchdog.failures`.

An active ingress WireGuard namespace with a missing or stale handshake, or a
failed NAT-PMP renewal unit, is reconciled immediately. Other verification failures use the configured
consecutive-failure threshold (three by default) before restarting
`slskdN-vpn-ingress.service`. It does not restart slskdN by default.
That keeps recovery focused on the most common failure: stale or missing port
forwarding state.

Tune the threshold with a systemd drop-in:

```ini
[Service]
Environment=SLSKDN_VPN_WATCHDOG_THRESHOLD=5
```

Check watchdog logs:

```bash
journalctl -t slskdN-vpn-watchdog -n 100 --no-pager
```

The per-slot handshake age limit defaults to 300 seconds and can be adjusted
with `SLSKDN_VPN_INGRESS_HANDSHAKE_MAX_AGE`. This is a liveness check for the
WireGuard ingress namespaces, not a requirement that a provider reuse the same
public port after a restart; always read the current `public_port` from
`/v1/slskdn/portforwards` or `pfN.env`.

## Systemd Hardening

The long-running C# compatibility service is restricted with
`NoNewPrivileges`, `ProtectSystem=full`, `ProtectHome`, and a narrow
`ReadWritePaths`.

The netns/iptables services need root networking privileges, so their hardening
is intentionally conservative: `NoNewPrivileges`, `ProtectHome`, and scoped state
write paths. Do not add a tight capability bounding set without testing
WireGuard interface creation, iptables, policy routing, and netns cleanup.

## Typical Listener Shape

At the time this was codified, slskdN exposed:

- Web UI/API: TCP `5030`, `5031` locally, excluded from VPN ingress
- Soulseek TCP listener: dynamic public forwarded port from the VPN provider
- DHT rendezvous TCP: `50305`
- DHT UDP: `50306` on the current deployed app; current slskdN defaults use UDP `50300` (shares the Soulseek TCP listen port's number)
- Overlay UDP: `50400`, intentionally not forwarded in `core` mode

The ingress command discovers active slskdN ports with `ss`, excludes web/mDNS
ports, and cleans stale namespaces when the listener set changes.

## Failure Modes

- If the primary WireGuard peer has no handshake, slskdN outbound fails closed.
- If the VPN provider changes the forwarded public port, slskdN learns the new port through
  the compatibility API and the ingress command refreshes DNAT on the next timer.
- If no NAT-PMP mappings can be claimed, `/var/lib/slskdN-vpn/summary.env`
  will show `claimed=0` and slskdN VPN readiness should fail.
- If downloads time out while search works, check that slskdN's advertised
  `forwardedPort` matches `/var/lib/slskdN-vpn/pf0.env public_port`.
