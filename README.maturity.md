<h1 align="center">slskdN</h1>
<p align="center"><strong>A web interface and daemon for Soulseek file sharing</strong></p>
<p align="center">
  <a href="https://github.com/snapetech/slskdn/releases">Releases</a> ·
  <a href="https://github.com/snapetech/slskdn/issues">Issues</a> ·
  <a href="https://discord.gg/5PyXBfvS6T">Community</a>
</p>

slskdN is an unofficial fork of [slskd](https://github.com/slskd/slskd). It
provides a web UI, REST API, and Soulseek client. It also includes extended
search, automation, media, and networking features at different levels of
maturity.

> **Check feature maturity before relying on an extension.** The
> [feature inventory](FEATURE_INVENTORY.md) is the canonical per-feature
> status. [Implementation status](docs/status.md) summarizes the main groups.
> Experimental features are not guaranteed stable, and feature gates have
> feature-specific defaults.

## Get started

- [Install and configure slskdN](docs/getting-started.md)
- [Configuration reference](docs/config.md)
- [Docker deployment](docs/docker.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Build from source](docs/build.md)

For first use, follow the setup guide to install the daemon, open its Web UI,
set credentials, configure a download directory and Soulseek account, then
search, browse, and manage transfers.

### Install the latest stable release on Linux

Download the current stable installer and run it with administrator privileges:

```bash
curl -fsSLO https://github.com/snapetech/slskdn/releases/latest/download/install-linux-release.sh
sudo bash install-linux-release.sh
```

The installer configures the system service. See the [setup guide](docs/getting-started.md)
for configuration and first-login steps.

## Use the main workflows
See the [UI localization roadmap](docs/localization-roadmap.md) for supported languages, translated workflows, and remaining gaps.


- [Dashboard](docs/dashboard.md) — review successful transfers from the last
  seven days and open the corresponding download or upload list.
- [Search and discovery](docs/soulseek-native-discovery.md) — search peers and
  review optional discovery tools.
- [Browse and download](docs/advanced-features.md) — select files and folders,
  choose a destination, and follow transfer progress. [Transfer Operations](docs/transfer-operations.md)
  explains path templates, file-name collisions, permissions, request history
  retention, API timestamp format, and paging through long transfer lists.
- [Wishlist and Lidarr](docs/lidarr-integration.md) — configure background
  acquisition workflows and their safeguards.
- [Messages, rooms, and pods](docs/pods-and-rooms.md) — review the distinct
  Soulseek and mesh messaging surfaces.
- [Player and listening parties](docs/listening-party.md) — configure local
  playback and optional shared listening.
- [System settings](docs/system-surfaces.md) — manage policies, integrations,
  metrics, diagnostics, and local experience preferences.

## Feature maturity

The stable baseline is slskd-compatible daemon behavior, the Web UI and REST
API, and standard single-source Soulseek transfers. The project also ships
experimental features; their maturity, gates, tests, and smoke coverage vary.
Consult the inventory and feature-specific guide before enabling an extension.

DHT rendezvous, mesh networking, pods, federation, VirtualSoulfind, and
multi-source downloads are distinct experimental systems. Their presence in
the UI, API, configuration, or documentation does not mean they are enabled,
interoperable, or suitable for production in every setup.

## Roadmap-only security claims

Some proposed security systems remain design-only. See the separate documents
for [implemented security controls](docs/security/implemented-security.md),
the [security roadmap](docs/security/security-roadmap.md), and
[security non-goals](docs/security/security-non-goals.md).

`HashFromAudioFileEnabled` is unavailable in this build; enabling it causes
startup validation to fail. Runtime SongID capabilities are reported by the
application and may differ with configuration and installed tools.

## Project status and contribution

- [Feature inventory](FEATURE_INVENTORY.md) — canonical maturity and coverage
  table.
- [Implementation status](docs/status.md) — user- and contributor-facing
  summary.
- [Feature overview](docs/FEATURES.md) — detailed capability descriptions.
- [Contributing](CONTRIBUTING.md) — development and contribution guidance.
- [API documentation](docs/api-documentation.md) — HTTP API reference.

slskdN is an unofficial fork. The separate [slskr project](https://github.com/snapetech/slskr)
is a Rust implementation; consult that repository for its own status and
compatibility claims.

- Support maintenance: [Ko-fi](https://ko-fi.com/snapetech).

## License

GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
