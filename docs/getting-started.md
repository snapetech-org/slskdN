# Getting Started with slskdN

This guide covers installation, first-run configuration, and the core Soulseek workflows.

## What is slskdN?

**slskdN** is an unofficial fork of [slskd](https://github.com/slskd/slskd), the web-based Soulseek client. It includes a Web UI, REST API, and the standard search, browse, and transfer workflows, along with extensions whose maturity varies. Check the [feature inventory](../FEATURE_INVENTORY.md) and [implementation status](status.md) before relying on an extension.

### Core workflow

- Search for files on Soulseek.
- Browse peer shares and enqueue downloads.
- Choose a download destination and monitor transfer progress.
- Configure shared folders, credentials, and daemon settings.

### Extended features

Wishlist automation, player and streaming, metadata discovery, Lidarr, mesh,
pods, and other extensions are documented in the relevant guides. Their
maturity, defaults, and verification coverage vary; consult the feature
inventory before enabling or relying on them. Experimental status does not
necessarily mean a feature is disabled by default.

## Installation

### Quick Install (Recommended)

#### Linux

**Arch Linux (AUR):**
```bash
yay -S slskdn-bin
# or
paru -S slskdn-bin
```

**Fedora/RHEL/openSUSE (COPR):**
```bash
sudo dnf copr enable slskdn/slskdn
sudo dnf install slskdn
```

**Ubuntu/Debian (PPA):**
```bash
sudo add-apt-repository ppa:snapetech/slskdn
sudo apt update
sudo apt install slskdn
```

**NixOS/Nix:**
```bash
nix-env -iA nixos.slskdn
# or add to configuration.nix
```

**Snap:**
```bash
sudo snap install slskdn
```

#### macOS

**Homebrew:**
```bash
brew install snapetech/slskdn/slskdn
```

#### Windows

**Chocolatey:**
```powershell
choco install slskdn
```

**Winget:**
```powershell
winget install snapetech.slskdn
```

**Scoop:**
```powershell
scoop bucket add snapetech https://github.com/snapetech/scoop-bucket
scoop install slskdn
```

### Docker

```bash
docker pull ghcr.io/snapetech-org/slskdn:latest
docker pull snapetech/slskdn:latest
docker run -d \
  --name slskdn \
  -p 5030:5030 \
  -v /path/to/config:/app/config \
  -v /path/to/downloads:/app/downloads \
  -v /path/to/shares:/app/shares \
  ghcr.io/snapetech-org/slskdn:latest
```

### Manual Installation

1. **Download the latest release** from [GitHub Releases](https://github.com/snapetech/slskdn/releases)
2. **Extract the archive** to your desired location
3. **Run the executable**:
   - Linux/macOS: `./slskdn`
   - Windows: `slskdn.exe`

### Building from Source

See [Building from Source](build.md) for detailed instructions.

## Initial Configuration

### First Run

1. **Start slskdN** using your preferred installation method
2. **Open your web browser** and navigate to `http://localhost:5030` (default port)
3. **Log in** with the default credentials:
   - Username: `slskd`
   - Password: `slskd` (change this immediately)

### First-Run Ports

| Purpose | Default | Notes |
|---------|---------|-------|
| Web UI / API | `5030/tcp` | Keep local or behind your own reverse proxy unless intentionally exposed. |
| HTTPS Web UI | `5031/tcp` | Configure certificate settings before forcing HTTPS. |
| Soulseek listen | `50300/tcp` | Forward or allow-list this when accepting inbound Soulseek transfers. Plain and type-1 obfuscated peer connections share this one port by default (`soulseek.obfuscation.listen_port: 0`). |
| Mesh TCP overlay rendezvous | `50300/tcp` | When DHT rendezvous is enabled, it shares the Soulseek listen port and is classified per connection by a TLS-vs-Soulseek byte sniff; no separate TCP overlay port is required. |
| Public DHT rendezvous / mesh overlay / QUIC | `50300/udp` | Disabled by default. Shares the same port number as the Soulseek listen port (TCP and UDP are separate port spaces, so this doesn't collide). Carries public BitTorrent DHT rendezvous, the UDP overlay control channel, and QUIC control- and data-plane traffic, demultiplexed on one socket. Mesh DHT metadata and file bytes stay on the overlay. Public DHT also requires `dht.lan_only: false`. |

For the usual consolidated configuration, forward one TCP port and optionally
one UDP port if public DHT/mesh/QUIC rendezvous is enabled. Plain Soulseek,
type-1 obfuscated traffic, and mesh TCP use the shared TCP listener unless you
explicitly configure a dedicated obfuscation port. With the VPN agent, the
provider's public forwarded port may differ from the local listener port; the
agent keeps the local socket bound and advertises the public port to Soulseek.
Lease renewal refreshes the mapping without rebuilding the live ingress path.

### Essential Settings

#### 1. Change Default Password

Use **System -> Policies** or edit `web.authentication` in YAML. If remote
configuration is disabled, edit the configuration file directly and restart.

#### 2. Configure Soulseek Credentials

Set `soulseek.username` and `soulseek.password` in YAML, then restart or
reconnect as indicated by the System status page. These are your Soulseek
account credentials; they are separate from the Web UI login password.

#### 3. Configure Download Directory

Use **System -> Options** for raw YAML or edit `directories.downloads`,
`directories.incomplete`, and `destinations.folders`. Destination folders must
exist, be writable, and be mounted into the container when using Docker. Set
`default: true` on one destination to make it the daemon-wide default.

#### 4. Search and Download

Open Search, enter a query, and download a result. These core steps do not
require share roots, an API key, Lidarr, DHT, or mesh.

### Optional: Share files with peers

Only add share roots if you want other Soulseek peers to browse those
directories. Choose exact directories in `shares.directories` in YAML, then use
**System -> Shares** for scan and status work. Shared roots expose their files
to peers; they are separate from your download destination.

### Optional: Add integrations and network features

An API key is only needed by the mutating API clients or automation that use
it. Configure Lidarr, wishlist, DHT, mesh, VPN, or other extensions only when
you need them. Review the [feature inventory](../FEATURE_INVENTORY.md) for
current maturity and defaults before enabling experimental features.

### Configuration File

Advanced configuration can be done via `config/slskd.yml`. See [Configuration Reference](config.md) for all available options.

**Example minimal configuration:**
```yaml
soulseek:
  username: "your-username"
  password: "your-password"

directories:
  downloads: "/path/to/downloads"
  incomplete: "/path/to/incomplete"

shares:
  directories:
    - "/path/to/shares"
```

## Basic Usage

### Searching for Files

1. **Navigate to Search** in the sidebar
2. **Enter your search query** (for example, `artist album`)
3. **Click Search** or press Enter
4. **Browse results** and click **Download** on desired files

Manual Search is direct user intent. It opens results without a separate
approval queue.

### Advanced Search Filters

Click the **⚙️ Advanced Filters** button to access:
- **Quality Presets**: "High Quality (320kbps+)", "Lossless Only", "Clear Quality"
- **Minimum Bitrate**: Filter by bitrate (kbps)
- **Minimum Bit Depth**: Filter by bit depth (bits)
- **Minimum Sample Rate**: Filter by sample rate (Hz)
- **File Extensions**: Filter by file type (e.g., `flac mp3 wav`)

### Downloading Files

1. On Search Results or Browse, choose a configured folder from **Download to**
2. **Click Download** on the desired file or folder
3. **Monitor progress** in the Downloads section
4. **Files are saved** to the selected destination; the browser remembers the
   choice for later manual downloads

To prevent unwanted categories from being downloaded, open **Download filters**
in the Downloads header and add one literal filename or path term per line.

Wishlist and other automatic downloads use the folder marked `default: true`.
If none is marked, they use `directories.downloads`. See
[Multiple Download Destinations](advanced-features.md#multiple-download-destinations)
for configuration and container-mount examples.

**Auto-Replace Stuck Downloads:**
- Enable the **"Auto-Replace"** toggle in Downloads header
- slskdN will automatically find alternatives for stuck downloads

### Multi-Source Rescue

For files with verified compatible sources, slskdN can use conservative
multi-source rescue paths:

1. Keep normal Soulseek downloads as the default path.
2. Enable accelerated/rescue behavior only where appropriate.
3. Monitor progress in Downloads, System -> Jobs, and System -> Swarm Analytics.
4. Mesh-overlay peers can support parallel chunks; public Soulseek peers use
   conservative failover to avoid noisy cancellation behavior.

### Wishlist / Background Search

1. **Navigate to Wishlist** in the sidebar
2. **Click "Add Search"**
3. **Enter search query and filters**
4. **Configure options**:
   - Auto-download: Automatically download matches
   - Interval: How often to run the search
   - Max results: Maximum results per run
5. **Save** and the search will run automatically in the background

## Advanced Features

### Collections & Sharing

**Create a Collection:**
1. Navigate to **Collections** in the sidebar
2. Click **"Create Collection"**
3. Add items (files, albums, etc.)
4. Configure sharing options

**Share with Others:**
1. Open your collection
2. Click **"Share"**
3. Configure share policy (who can access, download, etc.)
4. Share the collection link or grant access to specific users

### Scene ↔ Pod Bridging

Unified search across Pod/Mesh and Soulseek Scene networks:

1. **Enable the feature** in Settings → Features → Scene Pod Bridge
2. **Search results** will show badges indicating source (POD, SCENE, or POD+SCENE)
3. **Download/Stream** buttons work based on result source

### Streaming

Stream content while downloading:

1. **Start a download** (swarm or regular)
2. **Click "Stream"** button (available for Pod/Mesh content)
3. **Content streams** while download continues in background

### Job Management

Monitor all background jobs:

1. Navigate to **System → Jobs**
2. **View analytics**: Total, active, completed jobs
3. **Filter and sort** by type, status, date
4. **View swarm visualizations** for active downloads

### System Administration Surfaces

Use **System** for operator work:

- **Info**: daemon status, setup health, restart/reconnect cues, diagnostic bundles.
- **Network**: Soulseek, DHT, mesh, and public exposure health.
- **Security**: security dashboard and adversarial/privacy settings.
- **Policies**: guided YAML for webhooks/scripts, transfer policy, auth/API keys,
  HTTPS, rate limits, DHT, rescue mode, retention, and share scan pressure.
- **Experience**: browser-local Search, Player, and Messages
  preferences for page-specific behavior.
- **Integrations**: VPN, Lidarr, metadata providers, notifications, source feeds,
  FTP, Servarr readiness, and media-server execution contracts.
- **Source Providers**: read-only acquisition provider capability catalog.
- **Automations**: visible automation recipes and dry-run review.
- **Library Health**: scan results, reports, and review-first action exports.

### Pods, Rooms, And Messages

Use **Messages** as the unified conversation workspace. Direct messages, joined
rooms, and pod room channels can be opened as panels. Pod direct channels are
hidden from the normal list so they do not duplicate Soulseek DMs. Gold Star
Club membership is surfaced through pod/room workflows; leaving is intentionally
irreversible for local Gold Star status. Gold Star is dormant by default: an
operator must enable `feature.Pods: true` and set the exact daemon environment
value `SLSKDN_POD_GOLD_STAR_CLUB_AUTOJOIN=true` before startup. This opts in
only the local daemon/account; it does not enroll other users or testers.
See [Pods, Rooms, And Messages](pods-and-rooms.md) for the full policy.

## Troubleshooting

### Common Issues

#### Can't Connect to Soulseek

**Symptoms:** "Connection failed" or "Login failed"

**Solutions:**
1. **Check credentials**: Verify username and password in Settings → Soulseek
2. **Check firewall**: Ensure port `50300/tcp` (Soulseek listen) is not blocked
3. **Check network**: Verify internet connectivity
4. **Check Soulseek status**: Soulseek servers may be down

#### Downloads Stuck or Slow

**Symptoms:** Downloads not progressing or very slow

**Solutions:**
1. **Enable Auto-Replace**: Toggle "Auto-Replace" in Downloads header
2. **Check peer status**: User may be offline or have no free slots
3. **Check queue position**: Some users have long queues
4. **Try swarm download**: Multiple sources can improve speed

#### Web Interface Not Loading

**Symptoms:** Can't access web UI at `http://localhost:5030`

**Solutions:**
1. **Check if service is running**: `ps aux | grep slskdn` (Linux/macOS) or check Task Manager (Windows)
2. **Check port**: Verify port `5030` is not in use by another service
3. **Check firewall**: Ensure port `5030/tcp` is not blocked
4. **Check logs**: Look for error messages in log files

#### High CPU or Memory Usage

**Symptoms:** slskdN using excessive resources

**Solutions:**
1. **Reduce concurrent downloads**: Settings → Downloads → Max Concurrent Downloads
2. **Disable background features**: Disable wishlist, auto-replace if not needed
3. **Check for stuck processes**: Restart slskdN
4. **Review logs**: Check for errors or warnings

#### Search Not Finding Results

**Symptoms:** Searches return no results

**Solutions:**
1. **Check search sources**: Ensure Pod/Mesh or Soulseek Scene is enabled
2. **Try different search terms**: Be more or less specific
3. **Check filters**: Advanced filters may be too restrictive
4. **Wait longer**: Some searches take time to gather results

### Getting Help

1. **Check Logs**: 
   - Linux/macOS: `tail -f ~/.config/slskd/logs/slskd.log`
   - Windows: Check `%APPDATA%\slskd\logs\slskd.log`
   - Docker: `docker logs slskdn`

2. **Check Known Issues**: See [Known Issues](known_issues.md)

3. **Community Support**:
   - [Discord](https://discord.gg/5PyXBfvS6T)
   - [GitHub Issues](https://github.com/snapetech/slskdn/issues)

4. **Documentation**:
   - [Configuration Reference](config.md)
   - [Features Overview](FEATURES.md)
   - [How It Works](HOW-IT-WORKS.md)

## Next Steps

- **Explore Features**: Check out [Features Overview](FEATURES.md) for all available features
- **Configure Advanced Settings**: See [Configuration Reference](config.md) for detailed options
- **Learn About Architecture**: Read [How It Works](HOW-IT-WORKS.md) for technical details
- **Join the Community**: [Discord](https://discord.gg/5PyXBfvS6T)

## Security Best Practices

1. **Change default password** immediately after first login
2. **Use strong authentication**: Enable 2FA if available
3. **Configure firewall**: Only expose necessary ports
4. **Review share settings**: Ensure you're only sharing what you intend
5. **Keep updated**: Regularly update to latest version
6. **Review logs**: Periodically check logs for suspicious activity

See [Security Guidelines](SECURITY-GUIDELINES.md) for detailed security information.

---

**Need more help?** Check the [Documentation Index](README.md) or join our [Discord](https://discord.gg/5PyXBfvS6T)!
