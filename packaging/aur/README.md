# slskdn AUR Packages

This directory contains PKGBUILD files for the Arch User Repository (AUR).

## Drop-in Replacement

**slskdn is a drop-in replacement for slskd.** Both packages use identical paths:

| Resource | Path |
|----------|------|
| Binary launcher | `/usr/lib/slskd/slskd` |
| Bundled release payload | `/usr/lib/slskd/current/` |
| Symlink | `/usr/bin/slskd` |
| Config | `/etc/slskd/slskd.yml` |
| Data | `/var/lib/slskd/` |
| Service | `slskd.service` |
| User | `slskd` |

This means:
- **Your existing slskd config and data are preserved**
- **The systemd service name stays the same** (`systemctl status slskd`)
- **All your settings, downloads, and shares remain intact**

## Packages

### slskdn-bin (Recommended)

Binary package - quick installation, no build dependencies.
The package bundles the published self-contained .NET 10 runtime from the
GitHub release zip, so it should not depend on distro `aspnet-runtime` packages.

```bash
yay -S slskdn-bin
```

### slskdn

Source package - builds from source, requires build dependencies.

```bash
yay -S slskdn
```

## Upgrading from slskd

Simply replace slskd with slskdn:

```bash
# If using pacman/yay
yay -R slskd        # Remove old package
yay -S slskdn-bin   # Install slskdn

# Service continues to work
sudo systemctl restart slskd
```

Your config at `/etc/slskd/slskd.yml` and data at `/var/lib/slskd/` are preserved.

If an upgrade prints:

```text
warning: /etc/slskd/slskd.yml installed as /etc/slskd/slskd.yml.pacnew
```

pacman preserved your existing config and wrote the new packaged defaults to
`.pacnew`. Review the diff and merge only the defaults you want:

```bash
sudo diff -u /etc/slskd/slskd.yml /etc/slskd/slskd.yml.pacnew
sudo nano /etc/slskd/slskd.yml
sudo rm /etc/slskd/slskd.yml.pacnew
sudo systemctl restart slskd
```

AUR packages keep the drop-in launcher path at `/usr/lib/slskd/slskd`, but the bundled release payload now lives under `/usr/lib/slskd/current/` (backed by a versioned `releases/` directory). That keeps the compatibility path stable while avoiding pacman upgrade collisions with stale root-level payload files from older/manual installs.

Package upgrades restart `slskd.service` only when it is already running. Fresh installs still leave the service stopped until you review the config and run `systemctl enable --now slskd`.

## Fresh Installation

```bash
# Install
yay -S slskdn-bin

# Edit config
sudo nano /etc/slskd/slskd.yml

# Start service
sudo systemctl enable --now slskd

# Access web UI
xdg-open http://localhost:5030
```

## File Permissions

The AUR packages run the service as the `slskd` system user and group. Package
install/upgrade applies these defaults:

- `/etc/slskd/slskd.yml` is owned by `slskd:slskd` with group write access so
  the daemon can manage its configuration.
- `/var/lib/slskd`, `/var/lib/slskd/downloads`, and
  `/var/lib/slskd/incomplete` are owned by `slskd:slskd` with group write
  access.
- `slskd.service` uses `UMask=0002` so newly created files remain group
  accessible.

To edit the configuration or manage downloaded files as your normal user
without `sudo`, add that user to the service group:

```bash
sudo usermod -aG slskd "$USER"
```

Then start a new login session, reboot, or run:

```bash
newgrp slskd
```

For existing installs that were created before these package permissions were
fixed, this one-time repair matches the package defaults:

```bash
sudo chown slskd:slskd /etc/slskd/slskd.yml
sudo chmod 664 /etc/slskd/slskd.yml
sudo chown -R slskd:slskd /var/lib/slskd
sudo chmod -R g+rwX /var/lib/slskd
```

### Optional AUR extras for SongID workflows

`slskdn` installs with only the core runtime dependencies. If you want full SongID workflows, install any of these optional packages separately.

- `ffmpeg` — audio decoding and media handling used by SongID/AcoustID pipelines
- `python` — Python runtime for optional SongID tools
- `python-torchaudio` — optional advanced Python fingerprint and analysis features
- `docker` — containerized deployment (optional)

Why this is optional:
- Slskdn works without these for normal transfer/search/download behavior.
- SongID uses them only when advanced audio analysis is enabled in configuration.
- Keeping them optional avoids blocking installs on systems that do not need SongID extras or are behind Python package availability delays.

To avoid every optional dependency prompt (or accidental “all”), install like this:

```bash
yay -S --noconfirm slskdn-bin
```

## Configuration

The default config is at `/etc/slskd/slskd.yml`. Key settings:

```yaml
soulseek:
  username: your_username
  password: your_password

directories:
  downloads: /var/lib/slskd/downloads
  incomplete: /var/lib/slskd/incomplete

web:
  port: 5030
  https:
    disabled: true
  authentication:
    username: admin
    password: your_web_password

shares:
  directories:
    - /path/to/your/music
```

## CI / Release

- **Checksums**: `slskdn-bin` keeps the GitHub-hosted binary zip on `sha256sums=('SKIP' ...)`. GitHub release assets are not treated as immutable here, so only the repo-owned static packaging files (`slskd.service`, `slskd.yml`, `slskd.sysusers`) use real hashes. The binary package source filename includes `${pkgver}` so makepkg cannot reuse an older cached zip for a newer package version.
- **Source archive root**: the `slskdn` source package downloads lower-case release URLs, but GitHub extracts the `snapetech-org/slskdN` tag archive under a case-preserving `slskdN-<tag>/` directory. Keep the source PKGBUILD `cd` path tied to `_archive_root`, not `${pkgname}`, so clean `yay` builds can enter the extracted tree.

## Building Manually

```bash
# Clone
git clone https://aur.archlinux.org/slskdn-bin.git
cd slskdn-bin

# Build and install
makepkg -si
```
