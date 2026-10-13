# slskdn Unraid Template

This template is the Community Applications package metadata for slskdN.

## Community Applications

The repository-level profile required by the current Community Applications submission portal is at [`ca_profile.xml`](../../ca_profile.xml). Submit the public GitHub repository through [Community Applications](https://ca.unraid.net/submit/new) after reviewing the [submission help](https://ca.unraid.net/submit/help).

Until the listing is approved, use the [template XML](https://github.com/snapetech/slskdN/raw/refs/heads/main/packaging/unraid/slskdn.xml) as a local user template. Copy it to `/boot/config/plugins/dockerMan/templates-user/slskdn.xml` on the Unraid flash, then open **Docker → Add Container → User Templates** and select `slskdn`.

The old **Settings → Docker → Template Repositories** instructions are obsolete on current Unraid releases.

## Default Paths

| Setting | Container Path | Default / Recommendation |
|---------|---------------|-------------------|
| App Data | `/app` | `/mnt/user/appdata/slskdn` |
| Downloads | `/downloads` | Choose a share and directory before starting |
| Music Library | `/music` | Optional; choose a read-only share and directory; `/music` is the default shared path |

## Default Ports

| Port | Purpose |
|------|---------|
| 5030 | Web UI (HTTP) |
| 5031 | Web UI (HTTPS) |
| 50300/tcp | Soulseek incoming connections and slskdN mesh overlay (plain, obfuscated, and mesh TCP connections share this port by default) |
| 50300/udp | Public DHT rendezvous, mesh overlay control, and QUIC control/data-plane traffic, all sharing one UDP socket |

Port 50300/tcp should be forwarded in your router for optimal Soulseek and mesh
connectivity. If DHT, mesh, or QUIC services are enabled, also forward
50300/udp. TCP and UDP use separate port spaces, so both mappings can share the
same number. The loopback-only QUIC backend ports (55305 and 55401) must not be
published.

## First Run

1. Access the web UI at `http://YOUR_UNRAID_IP:5030`
2. Default login: `slskd` / `slskd`
3. Go to **System** → Configure your Soulseek username/password
4. Select a read-only Music Library mapping if you want to share music; the
   template pre-fills `SLSKD_SHARED_DIR=/music` for that mapping
5. Configure any additional shared folders under **System** → **Shares**

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PUID` | User ID for file permissions | 1000 |
| `PGID` | Group ID for file permissions | 1000 |
| `TZ` | Timezone | America/Chicago |
| `SLSKD_USERNAME` | Web UI username | slskd; change it |
| `SLSKD_PASSWORD` | Web UI password | slskd; change it |
| `SLSKD_SLSK_USERNAME` | Soulseek username | (set in UI) |
| `SLSKD_SLSK_PASSWORD` | Soulseek password | (set in UI) |

The template also exposes the documented optional `SLSKD_*` environment
overrides as advanced fields with blank values. Leave them blank to use the
image and YAML defaults. This includes less-common settings for completed
download destinations, collision handling, retries, retention, shares, search,
Soulseek behavior, obfuscation, proxies, authentication, metrics, notifications,
logging, and integrations. The complete variable reference is in
[`docs/config.md`](../../docs/config.md). Runtime-only
`SLSKD_SCRIPT_DATA` and image metadata variables such as `SLSKD_DOCKER_TAG` are
not user configuration fields.

`SLSKD_SLSK_CONNECTION_MTU` optionally caps the Soulseek server TCP MTU from
1280 to 9000. Leave it blank to use the operating system default.

Blank optional variable fields may be passed by Unraid as variables such as
`SLSKD_HEADLESS=`. slskdN treats empty `SLSKD_*` values as unset, so they do not
cause Boolean or numeric configuration-binding errors and do not override the
YAML or image default. Enter an explicit value when an override is wanted.

Downloads is a required Unraid path field and must be filled with the share and
directory you want to use before the container is started. Completed files use
`/downloads`; incomplete files use `/app/incomplete`, which is created in the
writable App Data mapping. The template defaults `SLSKD_SHARED_DIR` to `/music`,
so select the optional Music Library mapping when you want that path shared;
leave it unmounted when no read-only share should be exposed.

Image-managed Docker runtime settings are also visible in the advanced section
with their safe image defaults. Do not combine `PUID`/`PGID` with a Docker
`--user` override.

## Template usability feedback

Community feedback requested that Docker environment variables be exposed in
the template and left blank when optional, so users do not have to hunt through
documentation for settings that were omitted from the template. The current
template follows that approach while keeping required values and image runtime
defaults safe.

## Support

- **Issues:** https://github.com/snapetech/slskdN/issues
- **Documentation:** https://github.com/snapetech/slskdN
- **Unraid support forum:** https://forums.unraid.net/forum/71-docker-containers/
- **Unraid submission help:** https://ca.unraid.net/submit/help
- **Copy-ready GitHub Markdown support post:** [`SUPPORT_POST.md`](SUPPORT_POST.md)
- **Copy-ready Unraid forum text:** [`SUPPORT_POST_FORUM.txt`](SUPPORT_POST_FORUM.txt)
