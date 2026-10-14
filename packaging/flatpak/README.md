# slskdN - Flatpak Package

Install slskdN (Soulseek Network Client - Next Generation) on Linux using Flatpak. Features advanced VPN and mesh networking capabilities for secure, private decentralized community services.

## Installation

### Prerequisites

- Linux distribution with Flatpak support
- Flatpak installed (`sudo apt install flatpak` on Ubuntu/Debian)
- Flathub repository added (if not already present)

### Add Flathub Repository (if needed)

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
```

### Install slskdN

#### From Flathub (when available)

```bash
flatpak install flathub io.github.slskd.slskdn
```

#### Manual Installation

```bash
# Clone or download the Flatpak manifest
# Build and install locally
flatpak-builder --install --user build-dir io.github.slskd.slskdn.yml
```

#### Development Installation

```bash
# From source directory
flatpak-builder --install --user build-dir packaging/flatpak/io.github.slskd.slskdn.yml
```

## Usage

### Launch slskdN

```bash
# From applications menu
# Search for "slskdN" in your desktop environment

# Or from command line
flatpak run io.github.slskd.slskdn
```

### First-Time Setup

1. **Access Web UI**: Open http://localhost:5030 in your browser
2. **Create Account**: Set up an admin username and password
3. **Configure Soulseek**: Enter your Soulseek network credentials
4. **Set Up Shares**: Configure folders to share with other users
5. **Start Using**: Search for and download files!

## Configuration

### Data Locations

slskdN stores data in your home directory:

```
~/.config/slskdn/          # Configuration files
~/Documents/slskdn/shared/ # Files you're sharing
~/Downloads/slskdn/        # Downloaded files
~/.cache/slskdn/incomplete/ # Temporary download files
```

### Configuration File

The main configuration file is automatically created at:
```
~/.config/slskdn/slskd.yml
```

### Environment Variables

Override configuration using environment variables:

```bash
# Set custom web UI port
flatpak run --env=SLSKD_HTTP_PORT=8080 io.github.slskd.slskdn

# Enable debug logging
flatpak run --env=SLSKD_LOG_LEVEL=debug io.github.slskd.slskdn

# Enable VPN features
flatpak run --env=SLSKD_PODCORE_ENABLED=true --env=SLSKD_MESH_ENABLED=true io.github.slskd.slskdn
```

### VPN Configuration

slskdN includes advanced VPN features for secure private networking:

#### Pod-Based VPN

Create encrypted tunnels between trusted peers:

```yaml
# In ~/.config/slskdn/slskd.yml
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

The VPN features allow you to create secure, private networks between trusted peers:

1. **Enable VPN features** in the configuration file or environment variables
2. **Create or join a pod** through the web UI at Settings → Pods
3. **Configure VPN gateway** settings for pod-based tunneling
4. **Set up port forwarding** to access remote services securely
5. **Configure privacy layer** options for enhanced anonymity

VPN tunnels provide encrypted, authenticated connections allowing secure access to services without exposing them to the public internet.

### Flatpak Permissions

slskdN requests the following permissions:

- **Network**: Access to Soulseek network and web interface
- **File System**: Access to downloads, documents, and music directories
- **Graphics**: Hardware acceleration for web interface
- **Wayland/X11**: Display server access

## Troubleshooting

### Cannot Connect to Web UI

```bash
# Check if slskdN is running
flatpak ps | grep slskdn

# Check logs
flatpak run --command=sh io.github.slskd.slskdn -c 'tail -f ~/.cache/slskdn/logs/*.log'
```

### Permission Issues

If you encounter file access issues:

```bash
# Override permissions for specific directories
flatpak override --filesystem=/path/to/your/music io.github.slskd.slskdn
```

### Port Conflicts

If port 5030 is already in use:

```bash
# Edit configuration file
nano ~/.config/slskdn/slskd.yml

# Change the port setting and restart
flatpak run io.github.slskd.slskdn
```

### Soulseek Connection Issues

1. Verify username/password are correct
2. Check network connectivity
3. Ensure port 2234 is not blocked
4. Try different Soulseek listen port in configuration

## Building

### Prerequisites

- `flatpak` and `flatpak-builder` installed
- Access to Flathub runtimes
- ImageMagick or similar tool for icon conversion (optional)

### Prepare Icons

Before building, convert the SVG icon to PNG format:

```bash
# Convert SVG to PNG (requires ImageMagick)
convert slskdn.svg -background transparent -size 512x512 slskdn.png

# Or use inkscape
inkscape -w 512 -h 512 slskdn.svg -o slskdn.png
```

### Build Commands

```bash
# Build the package
flatpak-builder build-dir io.github.slskd.slskdn.yml

# Test the build
flatpak-builder --run build-dir io.github.slskd.slskdn.yml sh

# Create a bundle (optional)
flatpak build-bundle build-dir slskdn.flatpak io.github.slskd.slskdn
```

### Updating the Manifest

When new releases are available:

1. Update version and download URLs in `io.github.slskd.slskdn.yml`
2. Update SHA256 hashes for new binaries and .NET runtime
3. Test the build locally on multiple distributions
4. Submit updated manifest to Flathub

### Flathub Submission Checklist

Before submitting to Flathub:

- [ ] Update version, download URL, and sha256 in `io.github.slskd.slskdn.yml` for the new release
- [ ] Test on multiple Linux distributions (Ubuntu, Fedora, Arch)
- [ ] Ensure all permissions are minimal and justified
- [ ] Verify sandbox escape is not possible
- [ ] Test VPN features work within Flatpak sandbox
- [ ] Validate desktop integration works correctly
- [ ] Confirm all dependencies are available on Flathub

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

## File Structure

```
packaging/flatpak/
├── io.github.slskd.slskdn.yml    # Flatpak manifest
├── slskdn.desktop               # Desktop file
├── slskdn.metainfo.xml.in       # App metadata source (the .in suffix keeps CA's XML scanner from treating it as an Unraid template)
├── slskdn.svg                   # Application icon
└── README.md                    # This file
```

## Permissions and Security

slskdN is sandboxed within Flatpak:

- **Network access** is limited to necessary ports
- **File access** is restricted to user directories
- **No system access** beyond what's required
- **Isolated from system** for security

## Contributing

To contribute to the Flatpak package:

1. Test changes locally with `flatpak-builder`
2. Ensure manifest follows Flathub guidelines
3. Submit pull requests with tested changes
4. Update documentation as needed

## Support

- **Documentation**: https://github.com/snapetech-org/slskdN#readme
- **Issues**: https://github.com/snapetech-org/slskdN/issues
- **Upstream slskd**: https://github.com/slskd/slskd
- **Flathub**: https://flathub.org/apps/io.github.slskd.slskdn (when available)

## License

slskdN is licensed under GPL-3.0.

---

**Note**: This Flatpak package is designed for submission to Flathub.
Update URLs, hashes, and metadata before submitting.
