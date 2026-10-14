# slskdN - Synology Package Center (SPK)

Install slskdN, an unofficial fork of slskd, on Synology NAS devices through Package Center. Features advanced VPN and mesh networking capabilities for secure, private decentralized community services.

## Installation

### Prerequisites

- Synology DSM 7.0 or later
- At least 2GB RAM available
- 2GB free storage space
- Internet connection for downloads

### Installing the Package

1. **Download the SPK file** from the [slskdN releases page](https://github.com/snapetech-org/slskdN/releases)
2. **Open Package Center** on your Synology DSM
3. **Click "Manual Install"** (top right)
4. **Upload the SPK file** (`slskdn.spk`)
5. **Follow the installation wizard**

### First-Time Setup

After installation:

1. **Start slskdN**: Package Center → Installed → slskdN → Run
2. **Access Web UI**: Open http://your-nas-ip:5030
3. **Create Account**: Set up admin username/password
4. **Configure Soulseek**: Enter your Soulseek credentials
5. **Set Up Shares**: Configure shared folders

## Configuration

### Package Settings

The package automatically configures:

- **Data directories** in `/var/packages/slskdn/shares/slskdn/`
- **Configuration file** at `/var/packages/slskdn/shares/slskdn/config/slskd.yml`
- **Service integration** with DSM

### Customizing Configuration

Edit the configuration file:
```
sudo vi /var/packages/slskdn/shares/slskdn/config/slskd.yml
```

Then restart the package from Package Center.

### Directory Structure

```
/var/packages/slskdn/
├── shares/slskdn/
│   ├── config/          # Configuration files
│   ├── shared/          # Files you're sharing
│   ├── downloads/       # Downloaded files
│   ├── incomplete/      # Temporary downloads
│   └── logs/           # Application logs
├── target/              # Application binaries
└── var/                 # Runtime data
```

## Usage

### Starting/Stopping

- **Via Package Center**: Select slskdN → Run/Stop
- **Via DSM Desktop**: Click slskdN icon
- **Via Command Line**:
  ```bash
  sudo /usr/local/etc/rc.d/slskdn.sh start
  sudo /usr/local/etc/rc.d/slskdn.sh stop
  sudo /usr/local/etc/rc.d/slskdn.sh status
  ```

### Accessing Web UI

- **URL**: http://your-nas-ip:5030
- **Default credentials**: Set during first run
- **Features**:
  - Search and access community content
  - Manage shared community resources
  - View transfer and service status
  - Configure advanced networking options

### Soulseek Network

- **Listen Port**: 2234 (TCP)
- **Web UI Port**: 5030 (HTTP)
- **Firewall**: Automatically configured if enabled

## Storage Management

### Shared Folders

Create shared folders in DSM and configure them in slskdN:

1. **DSM Storage & Snapshots** → **Shared Folder** → Create
2. **slskdN Web UI** → Settings → Directories → Add shared folder

### Download Location

Configure download location in slskdN settings to point to a DSM shared folder.

### Permissions

The package creates a dedicated user/group:
- **User**: `slskdn`
- **Group**: `slskdn`

Ensure shared folders have appropriate permissions for this user.

## Performance Tuning

### For High-Performance NAS

```yaml
# In slskd.yml
global:
  upload:
    slots: 8
    speedLimit: 0
  download:
    slots: 16
    speedLimit: 0

system:
  memory:
    maxWorkingSet: 1024MB
```

### For Resource-Constrained NAS

```yaml
# In slskd.yml
global:
  upload:
    slots: 2
    speedLimit: 51200  # 50 MB/s
  download:
    slots: 4
    speedLimit: 102400  # 100 MB/s

system:
  memory:
    maxWorkingSet: 256MB
```

## Troubleshooting

### Service Won't Start

1. **Check logs**:
   ```bash
   cat /var/packages/slskdn/shares/slskdn/logs/*.log
   ```

2. **Check service status**:
   ```bash
   sudo /usr/local/etc/rc.d/slskdn.sh status
   ```

3. **Check port conflicts**:
   ```bash
   netstat -tln | grep :5030
   netstat -tln | grep :2234
   ```

### Cannot Connect to Soulseek

- Verify username/password in configuration
- Check network connectivity
- Ensure ports 2234 and 5030 are not blocked
- Try different Soulseek listen port

### Storage Issues

- Check disk space: `df -h`
- Verify permissions on shared folders
- Ensure slskdn user has access

### Performance Issues

- Monitor resource usage in Resource Monitor
- Adjust upload/download slots in configuration
- Check for background processes consuming resources

## Upgrading

### Via Package Center

1. Download new SPK file
2. Package Center → Manual Install
3. Select upgrade option
4. Configuration is preserved

### Backup Configuration

Before upgrading, backup your configuration:
```bash
cp -r /var/packages/slskdn/shares/slskdn/config /volume1/backup/
```

## Uninstalling

1. **Stop the package** in Package Center
2. **Uninstall** from Package Center
3. **Optional**: Remove data directories
   ```bash
   sudo rm -rf /var/packages/slskdn
   ```

**Note**: User data is preserved during uninstallation for safety.

## Building the Package

### Prerequisites

- Linux system with Synology toolkit
- .NET 10 SDK, as pinned in the repository's `global.json`
- SPK packaging tools

### Build Process

```bash
# Build a linux-x64 SPK from source.
SLSKDN_VERSION=2026051600-slskdn.259 \
  packaging/synology-spk/build-spk.sh

# Reuse an existing publish directory instead of publishing again.
SLSKDN_VERSION=2026051600-slskdn.259 \
SLSKDN_SPK_PUBLISH_DIR=/path/to/publish-linux-x64 \
  packaging/synology-spk/build-spk.sh

# Override the Synology package architecture metadata for another DSM target.
SLSKDN_SPK_RUNTIME=linux-arm64 \
SLSKDN_SPK_ARCH=aarch64 \
SLSKDN_VERSION=2026051600-slskdn.259 \
  packaging/synology-spk/build-spk.sh
```

The builder publishes the real `slskd` application binary into `package.tgz`.
It fails if the payload does not contain an executable `slskd`.

## Security

### Firewall

The package automatically configures firewall rules if DSM firewall is enabled.

### Access Control

- Web UI access can be restricted to specific IP ranges
- API access can be secured with API keys
- File sharing permissions follow DSM shared folder permissions

### Data Protection

- Configuration files are stored with restrictive permissions
- Logs are rotated and can be configured for privacy
- No sensitive data is exposed in DSM interfaces

## Advanced Features

### Mesh Networking (Experimental)

Enable decentralized peer discovery:

```yaml
mesh:
  enabled: true
  peerId: ""  # Auto-generated
```

### API Access

Access REST API with authentication:

```yaml
security:
  apiKeys:
    - "your-secure-api-key"
  requireApiKey: true
```

### VPN & Mesh Networking

slskdN includes advanced VPN features for secure private networking:

#### Pod-Based VPN

Create encrypted tunnels between trusted peers:

```yaml
# Enable pod-core VPN functionality
podcore:
  enabled: true
  peerId: ""  # Auto-generated unique identifier
```

#### Mesh Overlay Network

Enable decentralized peer discovery:

```yaml
mesh:
  enabled: true
  networkName: "my-private-network"
  networkPassword: "secure-password"
  peerId: ""  # Auto-generated
```

#### Anonymous Transports

Route traffic through privacy networks:

```yaml
transports:
  tor:
    enabled: true  # Route through Tor
  i2p:
    enabled: false  # Alternative: I2P network
  relay:
    enabled: false  # Use trusted relays
```

#### Privacy Layer

Protect against traffic analysis:

```yaml
privacy:
  enabled: true
  messagePadding: true    # Prevent size-based analysis
  timingObfuscation: true # Add random delays
  messageBatching: true   # Batch messages together
```

#### VPN Usage

1. **Enable VPN features** in configuration
2. **Create or join a pod** through the web UI
3. **Configure port forwarding** to access remote services
4. **Set up secure tunnels** between pod members

VPN tunnels provide encrypted, authenticated connections allowing secure access to services without exposing them to the public internet.

## Support

- **Documentation**: https://github.com/snapetech-org/slskdN#readme
- **Issues**: https://github.com/snapetech-org/slskdN/issues
- **Upstream slskd**: https://github.com/slskd/slskd
- **Synology Forums**: Community support
- **Soulseek Forums**: Network-specific help

## License

slskdN is licensed under GPL-3.0.

---

**Note**: This SPK package is designed for Synology DSM 7.0+.
Test thoroughly before deploying in production environments.
