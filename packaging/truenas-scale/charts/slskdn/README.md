# slskdN - TrueNAS SCALE App

A Helm chart for deploying slskdN (Soulseek Network Client - Next Generation) on TrueNAS SCALE.

## About slskdN

slskdN is a modern, private, decentralized mesh community service for Soulseek, written in C#. It's a fork of the original slskd project with enhanced features including:

- **Pod-Scoped VPN**: Secure private networking for trusted peer groups
- **Multi-source downloads**: Download files from multiple peers simultaneously
- **Mesh overlay network**: Decentralized peer discovery and communication
- **Advanced search**: MusicBrainz integration for better search results
- **Privacy features**: Tor/I2P transport support for anonymity
- **Enterprise security**: Certificate pinning, rate limiting, and comprehensive threat mitigation

## Installation

### Prerequisites

- TrueNAS SCALE 22.12 or later
- At least 256MB RAM available
- Storage space for downloads and shared files

### Installing the Chart

1. In TrueNAS SCALE, go to **Apps** → **Available Applications**
2. Search for "slskdn" or manually add the chart repository
3. Click **Install**
4. Configure the following required settings:
   - **Host Path**: Storage location on your TrueNAS system (e.g., `/mnt/tank/slskdn`)
   - **Soulseek Username**: Your Soulseek network username
   - **Soulseek Password**: Your Soulseek network password

### Configuration

#### Required Settings

- **Username/Password**: Your Soulseek network credentials
- **Host Path**: Where slskdN will store its data and downloads

#### Optional Settings

- **Upload/Download Limits**: Speed limits for network usage
- **API Keys**: For programmatic access to the REST API
- **Mesh Features**: Advanced peer-to-peer networking (experimental)
- **VPN Configuration**: Pod-scoped private networking and tunneling

### VPN Configuration

slskdN includes advanced VPN-like features for secure private networking:

#### Mesh Networking
- **Enable Mesh**: Connect to the decentralized mesh overlay network
- **Peer ID**: Unique identifier for this instance in the mesh
- **Network Name**: Name of the mesh network to join
- **Network Password**: Optional password for private mesh networks

#### Pod-Based VPN
- **Enable Pod Core**: Activate pod-scoped VPN functionality
- **Pod Peer ID**: Identifier for pod networking operations
- **VPN Gateways**: Create secure tunnels between trusted peers

#### Anonymous Transports
- **Tor Transport**: Route traffic through Tor for anonymity
- **I2P Transport**: Use I2P network for anonymous communication
- **Relay Transport**: Use trusted relay nodes for restricted networks

#### Privacy Layer
- **Message Padding**: Prevent size-based traffic analysis
- **Timing Obfuscation**: Add random delays to prevent timing attacks
- **Message Batching**: Group messages to reduce traffic patterns

## Usage

After installation:

1. Access the web UI at `http://your-truenas-ip:5030`
2. Log in with your configured username/password
3. Configure shared folders and download locations
4. Start searching and downloading files
5. **Optional**: Configure VPN features for secure private networking

### Using VPN Features

The VPN features allow you to create secure, private networks between trusted peers:

1. **Enable Mesh Networking** in the configuration
2. **Create or join a Pod** through the web UI
3. **Configure VPN Gateway** settings for pod-based tunneling
4. **Set up Port Forwarding** to access remote services securely
5. **Configure Privacy Layer** options for enhanced anonymity

VPN tunnels provide encrypted, authenticated connections between pod members, allowing secure access to services without exposing them to the public internet.

## Storage

slskdN uses the following storage locations:

- **Config**: Application configuration and database (`/app/config`)
- **Downloads**: Downloaded files (`/app/downloads`)
- **Shared**: Files you're sharing with others (`/app/shared`)
- **Incomplete**: Temporary files during downloads (`/app/incomplete`)

All storage is mapped to your configured host path.

## Networking

- **Web UI**: Port 5030 (HTTP)
- **Soulseek Network**: Port 2234 (configurable)
- **Optional HTTPS**: Port 5031 (if enabled)

## Security

slskdN includes enterprise-grade security features:

- **Certificate Pinning**: Prevents MITM attacks
- **Rate Limiting**: Protects against DoS attacks
- **Privacy Logging**: Safe logging without data leakage
- **Transport Encryption**: TLS for all connections
- **API Key Authentication**: Optional API security

## Troubleshooting

### Common Issues

1. **Can't connect to Soulseek network**
   - Verify username/password are correct
   - Check network connectivity
   - Ensure Soulseek listen port (2234) is not blocked

2. **Slow downloads**
   - Check upload/download speed limits
   - Verify peer connections in the web UI
   - Consider enabling mesh features for better peer discovery

3. **Storage permission errors**
   - Ensure the host path exists and is writable
   - Check file system permissions

### Logs

View application logs in TrueNAS SCALE:
1. Go to **Apps** → **Installed Applications**
2. Select slskdN → **Logs**

Or access logs via the web UI at `/logs`.

## Upgrading

To upgrade slskdN:

1. Go to **Apps** → **Installed Applications**
2. Select slskdN → **Upgrade**
3. Review and apply any new configuration options

## Support

- **Documentation**: https://github.com/snapetech-org/slskdN#readme
- **Issues**: https://github.com/snapetech-org/slskdN/issues
- **Upstream slskd**: https://github.com/slskd/slskd
- **Community**: Soulseek forums and Discord

## License

slskdN is licensed under the GPL-3.0 License.

## Version History

- **0.2.0**: VPN and Advanced Networking Release
  - Pod-scoped VPN functionality
  - Mesh overlay network support
  - Tor/I2P anonymous transport options
  - Privacy layer (traffic analysis protection)
  - Enhanced security with certificate pinning
  - Rate limiting and resource governance

- **0.1.0**: Initial TrueNAS SCALE release
  - Basic deployment configuration
  - Persistent storage setup
  - Web UI access
  - Soulseek network integration
