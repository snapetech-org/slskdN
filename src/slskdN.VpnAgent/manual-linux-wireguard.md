# Manual Linux WireGuard Setup

Use this path when the host should own the WireGuard tunnel, fail-closed
routing, dynamic port claims, and ingress DNAT for slskdN.

For a released ZIP install, start with
[`GETTING_STARTED.md`](GETTING_STARTED.md). The source-build steps below are
for a full repository checkout and are not needed with the bundled Linux
helper.

## When To Use

- slskdN runs as a host service, not inside a VPN-owned container.
- Soulseek traffic must use VPN egress while Web UI/API stay local.
- The VPN provider supports NAT-PMP/PCP or gives static forwarded ports.
- You can supply one outbound WireGuard config and optional per-ingress
  WireGuard configs for forwarded-port slots.

## Inputs

- `SLSKDN_SERVICE_USER`: the service user running slskdN.
- `/etc/wireguard/slskdN-vpn.conf`: outbound WireGuard config.
- `/etc/wireguard/slskdN-vpn-ingress/*.conf`: one or more ingress configs,
  one per forwarded public port slot. The bundled installer requires at least
  one because this setup configures port forwarding.
- Each ingress endpoint must be an IPv4 address or a hostname that resolves to
  IPv4 so the namespace can route WireGuard handshake traffic through the host
  gateway before applying its tunnel default route.
- `integrations.vpn` enabled in `/etc/slskdN/slskd.yml`.

Do not reuse the same private key for the outbound tunnel and a simultaneous
ingress tunnel.

## Manual install from a source checkout

Install prerequisites:

```bash
sudo dnf install -y dotnet-sdk-11.0 wireguard-tools natpmpc jq curl iptables iproute nftables
```

Install VPN configs:

```bash
sudo install -d -m 700 /etc/wireguard
sudo install -d -m 700 /etc/wireguard/slskdN-vpn-ingress
sudo install -m 600 /path/to/vpn-outbound.conf /etc/wireguard/slskdN-vpn.conf
sudo install -m 600 /path/to/pf0.conf /etc/wireguard/slskdN-vpn-ingress/00-soulseek.conf
```

Publish and install the agent:

```bash
cd src/slskdN.VpnAgent
sudo dotnet publish slskdN-vpn-agent.csproj -c Release -r linux-x64 --self-contained true -p:PublishSingleFile=true -o /usr/local/lib/slskdN-vpn-agent
sudo ln -sfn /usr/local/lib/slskdN-vpn-agent/slskdN-vpn-agent /usr/local/bin/slskdN-vpn-agent
sudo install -d -m 755 /var/lib/slskdN-vpn
```

Install systemd units:

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

Enable the services:

```bash
sudo systemctl enable --now wg-quick@slskdN-vpn.service
sudo systemctl enable --now slskdN-vpn-split.service
sudo systemctl enable --now slskdN-vpn-gluetun-compat.service
sudo systemctl enable --now slskdN-vpn-ingress-renew.timer
sudo systemctl enable --now slskdN-vpn-watchdog.timer
```

Restart slskdN, then reconcile ingress once:

```bash
sudo systemctl restart slskdN
sleep 10
sudo systemctl restart slskdN-vpn-ingress.service
```

## slskdN Config

Merge this under the existing top-level `integrations:` key:

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

## Verification

```bash
sudo /usr/local/bin/slskdN-vpn-agent verify
systemctl is-active slskdN wg-quick@slskdN-vpn slskdN-vpn-split slskdN-vpn-gluetun-compat slskdN-vpn-ingress-renew.timer
sudo cat /var/lib/slskdN-vpn/summary.env
```

The Web UI/API should remain reachable on local/LAN addresses. Soulseek TCP
should advertise the forwarded public port reported by the compatibility API,
even when that differs from the local listener port. The default consolidated
port budget is one TCP forward for regular/type-1 Soulseek and mesh TCP, plus
one optional UDP forward for DHT/mesh/QUIC. The renewal timer refreshes leases
without rebuilding the ingress namespace or veth. On hosts with a native
nftables input policy, `nftables` is required so the agent can allow DNATed
packets delivered to the host-side veth.
