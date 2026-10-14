# Self-Hosted Relay Tester Guide

This checklist tests the Tailscale-native CGNAT design: slskdN and all shares
remain on the home server, while an OCI VPS exposes one public Soulseek TCP port
and supplies outbound internet access only to the slskdN container. Tailscale is
the tunnel; do not add a second WireGuard tunnel or run slskdN on OCI.

Replace every uppercase placeholder before running a command. The examples use
TCP `50300` for Soulseek and TCP `8010` for the private relay status API.

## 1. Record The Two Tailscale Addresses

Run this on both hosts:

```bash
tailscale ip -4
tailscale status
```

Record these values:

```text
OCI_TAILSCALE_IP=100.x.y.z
HOME_TAILSCALE_IP=100.a.b.c
OCI_PUBLIC_IP=your OCI public IPv4 address
```

The home address must belong to the Tailscale node whose network namespace
contains slskdN. When using the recommended Docker sidecar, use the sidecar's
Tailscale address, not the host's separate Tailscale address.

## 2. Enable OCI As An Exit Node

On OCI:

```bash
sudo tailscale set --advertise-exit-node
tailscale ping HOME_TAILSCALE_IP
```

Approve OCI's advertised exit-node route in the Tailscale admin console. Ensure
the tailnet ACL permits:

- OCI to `HOME_TAILSCALE_IP:50300/tcp`
- the home slskdN namespace to `OCI_TAILSCALE_IP:8010/tcp`

In the OCI security list or NSG and the host firewall, allow public TCP `50300`.
Do not expose TCP `8010` publicly; it listens on the private Tailscale address.

## 3. Install The Released Relay Companion On OCI

Install the relay's operating-system prerequisites on OCI. For Debian or
Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y conntrack curl iproute2 iptables unzip
```

Download the Linux archive for the release being tested:

```bash
RELEASE=RELEASE_TAG
curl -fLO "https://github.com/snapetech-org/slskdN/releases/download/${RELEASE}/slskdn-main-linux-glibc-x64.zip"
rm -rf /tmp/slskdn-relay-release
mkdir -p /tmp/slskdn-relay-release
unzip -q slskdn-main-linux-glibc-x64.zip -d /tmp/slskdn-relay-release
sudo install -m 0755 /tmp/slskdn-relay-release/vpn-agent/slskdN-vpn-agent /usr/local/bin/slskdN-vpn-agent
sudo install -d -m 0755 /etc/slskdN-relay
sudo install -m 0644 /tmp/slskdn-relay-release/vpn-agent/systemd/slskdN-relay.service /etc/systemd/system/slskdN-relay.service
sudo install -m 0600 /tmp/slskdn-relay-release/vpn-agent/examples/self-hosted-relay-tailscale.env.example /etc/slskdN-relay/relay.env
```

Edit `/etc/slskdN-relay/relay.env`:

```ini
SLSKDN_RELAY_TUNNEL_TYPE=tailscale
SLSKDN_RELAY_IFACE=tailscale0
SLSKDN_RELAY_PUBLIC_IFACE=eth0
SLSKDN_RELAY_HOME_IP=HOME_TAILSCALE_IP
SLSKDN_RELAY_PUBLIC_PORT=50300
SLSKDN_RELAY_TARGET_PORT=50300
SLSKDN_RELAY_API_PORT=8010
SLSKDN_RELAY_API_KEY_FILE=/etc/slskdN-relay/api-keys
SLSKDN_RELAY_CONNECTION_LIMIT=128
SLSKDN_RELAY_BANDWIDTH_MBIT=100
```

Use the actual OCI public interface reported by `ip route show default`; it may
not be `eth0`. Do not set `SLSKDN_RELAY_TUNNEL_CIDR` in Tailscale mode. The
companion derives and enforces the exact home `/32`.

Create the independent status key and Tailscale service ordering:

```bash
openssl rand -base64 48 | sudo tee /etc/slskdN-relay/api-keys >/dev/null
sudo chmod 600 /etc/slskdN-relay/api-keys
sudo install -d -m 0755 /etc/systemd/system/slskdN-relay.service.d
sudo tee /etc/systemd/system/slskdN-relay.service.d/tailscale.conf >/dev/null <<'EOF'
[Unit]
After=tailscaled.service
Requires=tailscaled.service
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now slskdN-relay
sudo systemctl status --no-pager slskdN-relay
```

## 4. Put Only slskdN Behind The OCI Exit Node

The home Docker Compose file should give a Tailscale sidecar ownership of the
network namespace and make slskdN share it:

```yaml
services:
  tailscale-slskdn:
    image: tailscale/tailscale:stable
    hostname: slskdn-home
    environment:
      TS_STATE_DIR: /var/lib/tailscale
      TS_USERSPACE: "false"
    volumes:
      - tailscale-state:/var/lib/tailscale
      - /dev/net/tun:/dev/net/tun
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    ports:
      - "127.0.0.1:5030:5030"

  slskdn:
    image: ghcr.io/snapetech/slskdn:RELEASE_TAG
    network_mode: service:tailscale-slskdn
    depends_on:
      - tailscale-slskdn
    # Retain the existing slskdN volumes and environment.

volumes:
  tailscale-state:
```

Remove `ports` from the `slskdn` service because Docker requires shared-
namespace ports on `tailscale-slskdn`. Start the services, authenticate the
sidecar, and select OCI as its exit node:

```bash
docker compose up -d
docker compose exec tailscale-slskdn tailscale up
docker compose exec tailscale-slskdn tailscale set --exit-node=OCI_TAILSCALE_IP
docker compose exec tailscale-slskdn tailscale status
```

Do not select the OCI exit node on the home host itself. Doing so would route
unrelated host and container traffic through OCI.

## 5. Configure slskdN

Read the first line of `/etc/slskdN-relay/api-keys` on OCI and place it in the
home slskdN configuration:

```yaml
soulseek:
  listen_port: 50300

integrations:
  vpn:
    enabled: true
    port_forwarding: true
    self_hosted_relay: true
    polling_interval: 5000
    gluetun:
      url: http://OCI_TAILSCALE_IP:8010
      timeout: 5000
      api_key: RELAY_STATUS_API_KEY
```

Restart slskdN after changing its configuration.

## 6. Acceptance Checks

On OCI, replace `RELAY_STATUS_API_KEY` locally without posting it publicly:

```bash
curl -fsS -H "X-API-Key: RELAY_STATUS_API_KEY" \
  "http://OCI_TAILSCALE_IP:8010/v1/slskdn/relay"
sudo iptables -t nat -S SLSKDN-RELAY-NAT
sudo iptables -S SLSKDN-RELAY-FWD
sudo conntrack -L -p tcp 2>/dev/null | grep 'dport=50300' || true
```

The JSON must show `"transport":"tailscale"`, `"connected":true`, the OCI
public IP and port `50300`, and a non-empty peer path. The forwarding rules must
target only `HOME_TAILSCALE_IP/32`.

From the home slskdN network namespace:

```bash
docker compose exec slskdn sh -lc 'wget -qO- https://ifconfig.me/ip || curl -fsS https://ifconfig.me/ip'
```

This must return `OCI_PUBLIC_IP`, not the home ISP address. In slskdN, open
System -> Integrations -> VPN and confirm:

- provider is Self-hosted relay
- status is Connected
- transport is tailscale
- advertised endpoint is `OCI_PUBLIC_IP:50300`
- Latest Peer Activity and Peer Path are populated

Use an external TCP checker or a Soulseek client outside the home network to
connect to `OCI_PUBLIC_IP:50300`. While that check is active, OCI's conntrack
output should show the forwarded connection.

## 7. Fail-Closed Check

Stop Tailscale on OCI, leaving the home sidecar configured to use that now-
unavailable exit node, then repeat the namespace public-IP check:

```bash
# Run on OCI:
sudo systemctl stop tailscaled
```

The request must fail; it must not return the home ISP address. The slskdN VPN
panel must become disconnected after its polling interval. Restore OCI
Tailscale and the relay companion, then confirm recovery:

```bash
# Run on OCI:
sudo systemctl start tailscaled
sudo systemctl restart slskdN-relay

# Run at home:
docker compose exec tailscale-slskdn tailscale status
```

## 8. Report Results

Send these items, with API/auth keys redacted:

- release tag and CPU architecture
- OCI distribution and public-interface name
- `systemctl status slskdN-relay` output
- authenticated `/v1/slskdn/relay` JSON with no API key included
- `tailscale ping HOME_TAILSCALE_IP` output
- whether the path is direct or DERP
- whether the namespace public-IP check returned OCI's public IP
- whether external TCP `50300` connected
- whether the fail-closed check prevented home-ISP fallback
- relevant `journalctl -u slskdN-relay --since '-15 min'` output

Do not send `/etc/slskdN-relay/api-keys`, Tailscale auth keys, node private
keys, slskdN API keys, or share paths.
