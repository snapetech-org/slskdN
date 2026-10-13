# slskdn on Proxmox LXC

Template and scripts to run slskdn in a Proxmox **LXC** (Linux Container).

## Quick start

1. **Create an LXC** from a Debian 12 or Ubuntu 22.04 template (see below).
2. **Bind-mount** storage for app data and downloads (optional but recommended).
3. **Run the setup script** inside the container: `setup-inside-ct.sh`.
4. **Edit** `/etc/slskd/slskd.yml` (Soulseek username, shares, etc.).
5. **Start**: `systemctl enable --now slskd`.
6. **Web UI** at `http://<CT-IP>:5030`.

## 1. Create the LXC

On the Proxmox host:

```bash
# Download a Debian 12 or Ubuntu 22.04 template (if needed)
pveam update
pveam available | grep -E "debian-12|ubuntu-22"
pveam download local debian-12-standard_12.2-1_amd64.tar.zst

# Create the container (adjust VMID and storage)
pct create 200 local:vztmpl/debian-12-standard_12.2-1_amd64.tar.zst \
  --hostname slskdn \
  --memory 512 --swap 256 \
  --cores 1 \
  --rootfs local-lvm:4 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1
```

For bind-mounts (app data, downloads, shares), add `mp` entries. Example (`/etc/pve/lxc/200.conf` or via `pct set`):

```
mp0: /mnt/pve/storage/slskdn-data,mp=/var/lib/slskd
mp1: /mnt/pve/storage/slskdn-downloads,mp=/var/lib/slskd/downloads
```

Then:

```bash
pct start 200
pct exec 200 -- bash
```

## 2. Run the setup script inside the CT

Copy `setup-inside-ct.sh` into the container (or clone the repo, or run via `pct push`), then:

```bash
chmod +x setup-inside-ct.sh
./setup-inside-ct.sh
```

The script will:

- Install .NET 10 (Microsoft package repository)
- Download the slskdn Linux x64 release from GitHub
- Extract to `/opt/slskdn`
- Create `slskd` user and `/var/lib/slskd`, `/etc/slskd`
- Install a systemd unit and minimal config
- **Not** start the service (you edit config first)

You can pin a specific release tag with `SLSKDN_VERSION`:

```bash
SLSKDN_VERSION=2026101222-slskdn.350 ./setup-inside-ct.sh
```

If `SLSKDN_VERSION` is not set, the script resolves the latest release tag from GitHub automatically.

## 3. Configure and start

```bash
nano /etc/slskd/slskd.yml
# Set: soulseek.username, soulseek.password, shares.directories, directories.downloads, etc.

systemctl enable --now slskd
systemctl status slskd
```

## Ports

| Port  | Purpose                    |
|-------|----------------------------|
| 5030  | Web UI (HTTP)              |
| 5031  | HTTPS (if enabled)         |
| 50300 | Soulseek (forward on router) |

## Example pct.conf snippet

See `slskdn.conf.example` for `pct.conf`-style options you can merge into `/etc/pve/lxc/<vmid>.conf`.

## Alternative: Debian package

If you use our PPA or a .deb:

```bash
apt update && apt install -y slskdn
# Config: /etc/slskd/slskd.yml; data: /var/lib/slskd
systemctl enable --now slskd
```

The `setup-inside-ct.sh` path (binary from GitHub) is for when no repo is available.

## Links

- [slskdn](https://github.com/snapetech/slskdn)
- [Proxmox LXC](https://pve.proxmox.com/pve-docs/chapter-pct.html)
