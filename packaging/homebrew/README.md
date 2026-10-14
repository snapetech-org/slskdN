# slskdN - Homebrew Formula

Install slskdN (Decentralized Mesh Community Service - Next Generation) on macOS using Homebrew.

## Installation

### Prerequisites

- macOS 10.15 or later
- [Homebrew](https://brew.sh/) package manager

The published Homebrew formula uses a self-contained release archive, so you do
not need to install the .NET SDK or runtime to run slskdN.

### Install slskdN

```bash
# Add the slskdN tap (once available)
# brew tap slskd/slskdn

# Install slskdN
brew install slskd/slskdn/slskdn
```

## Usage

### Start slskdN Service

```bash
# Start slskdN as a background service
brew services start slskdn

# Check service status
brew services list | grep slskdn
```

### Access Web UI

Open http://localhost:5030 in your browser.

### First-Time Setup

1. **Create Account**: Set up an admin username and password
2. **Configure Soulseek**: Enter your Soulseek network credentials
3. **Set Up Shares**: Configure folders to share with other users
4. **Optional VPN Setup**: Configure pod-based VPN for secure private networking
5. **Start Using**: Search for and download files!

### VPN Setup (Optional)

The VPN features allow you to create secure, private networks between trusted peers:

1. **Enable VPN features** in the configuration or environment variables
2. **Create or join a pod** through the web UI at Settings → Pods
3. **Configure VPN gateway** settings for pod-based tunneling
4. **Set up port forwarding** to access remote services securely
5. **Configure privacy layer** options for enhanced anonymity

VPN tunnels provide encrypted, authenticated connections allowing secure access to services without exposing them to the public internet.

## Configuration

### Configuration File

The main configuration file is located at:
```
$(brew --prefix)/etc/slskdn/slskd.yml
```

### Data Directories

slskdN stores data in:
```
$(brew --prefix)/var/slskdn/
├── shared/          # Files you're sharing
├── downloads/       # Downloaded files
└── incomplete/      # Temporary download files
```

### Environment Variables

You can override configuration using environment variables:

```bash
# Set custom web UI port
export SLSKD_HTTP_PORT=8080

# Enable HTTPS (requires certificate configuration)
export SLSKD_WEBUI_HTTPS=true

# Set Soulseek listen port
export SLSKD_SLSK_LISTEN_PORT=2235

# Configure data directories
export SLSKD_SHARED_DIR="/path/to/shared"
export SLSKD_DOWNLOADS_DIR="/path/to/downloads"
```

## Advanced Configuration

### Soulseek Network Settings

```yaml
# In $(brew --prefix)/etc/slskdn/slskd.yml
soulseek:
  username: "your_soulseek_username"
  password: "your_soulseek_password"
  listen:
    port: 2234
  connection:
    timeout: 10000
```

### Web UI Settings

```yaml
web:
  enabled: true
  port: 5030
  https:
    enabled: false
    certificate:
      pfx: "/path/to/cert.pfx"
      password: "cert_password"
```

### Security Settings

```yaml
security:
  apiKeys:
    - "your-secure-api-key"
  requireApiKey: false
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

#### VPN Environment Variables

```bash
# Enable VPN features
export SLSKD_PODCORE_ENABLED=true
export SLSKD_MESH_ENABLED=true
export SLSKD_TRANSPORTS_TOR_ENABLED=true
export SLSKD_PRIVACY_ENABLED=true
```

### Legacy Mesh Features (Advanced)

```yaml
mesh:
  enabled: false  # Set to true for basic mesh features
  peerId: ""      # Auto-generated if empty
  parent: ""      # Parent mesh node (optional)
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
brew services list

# View logs
tail -f $(brew --prefix)/var/log/slskdn.log
tail -f $(brew --prefix)/var/log/slskdn.error.log
```

### Cannot Connect to Soulseek

1. Verify username/password are correct
2. Check network connectivity
3. Ensure port 2234 is not blocked by firewall
4. Try a different Soulseek listen port

### Permission Issues

```bash
# Fix permissions on data directories
sudo chown -R $(whoami) $(brew --prefix)/var/slskdn
chmod -R 755 $(brew --prefix)/var/slskdn
```

### Port Conflicts

If port 5030 is already in use:

```bash
# Edit configuration file
nano $(brew --prefix)/etc/slskdn/slskd.yml

# Change port and restart
brew services restart slskdn
```

## Upgrading

```bash
# Update Homebrew
brew update

# Upgrade slskdN
brew upgrade slskdn

# Restart service
brew services restart slskdn
```

## Uninstalling

```bash
# Stop service
brew services stop slskdn

# Remove service
brew services remove slskdn

# Uninstall slskdN
brew uninstall slskdn

# Remove configuration (optional)
rm -rf $(brew --prefix)/etc/slskdn
rm -rf $(brew --prefix)/var/slskdn
```

## Development

### Building from Source

Install the [.NET 10 SDK](https://dotnet.microsoft.com/download) specified by
the repository's `global.json` before building.

```bash
# Clone repository
git clone https://github.com/snapetech-org/slskdN.git
cd slskdn

# Build for macOS
dotnet publish src/slskd/slskd.csproj \
  -c Release \
  -r osx-x64 \
  --self-contained true \
  -p:PublishSingleFile=true \
  -p:PublishTrimmed=true \
  -o ./bin/publish/osx-x64

# Test installation
./bin/publish/osx-x64/slskd --version
```

### Updating the Formula

When new releases are available, update the formula:

1. Update version and URLs in `slskdn.rb`
2. Update SHA256 hash: `shasum -a 256 <downloaded-tarball>`
3. Test the formula: `brew install --build-from-source slskdn.rb`
4. Submit pull request to homebrew-core

## Features

slskdN includes many advanced community service features:

- **Pod-Scoped VPN**: Secure private networking for trusted community groups
- **Multi-source content delivery**: Efficient peer-to-peer content distribution
- **Web UI**: Modern web interface for easy management and VPN configuration
- **API**: RESTful API for automation and community service integration
- **Privacy features**: Tor/I2P transport support with traffic analysis protection
- **Enterprise security**: Certificate pinning, rate limiting, comprehensive threat mitigation
- **Mesh networking**: Decentralized peer discovery and community communication
- **Anonymous transports**: WebSocket, HTTP tunnel, Obfs4, Meek protocol support

## Support

- **Documentation**: https://github.com/snapetech-org/slskdN#readme
- **Issues**: https://github.com/snapetech-org/slskdN/issues
- **Upstream slskd**: https://github.com/slskd/slskd
- **Discussions**: GitHub Discussions
- **Soulseek Forums**: Community support

## License

slskdN is licensed under GPL-3.0.

## Contributing

Contributions are welcome! See the main repository for contribution guidelines.
