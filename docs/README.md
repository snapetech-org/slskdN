# Documentation Index

Maintained guide to current slskdn documentation. Historical snapshots,
completed workstream notes, and incident reports live under
[`archive/`](archive/) and should not be treated as current instructions.

## 🚀 Quick Start

- **[Getting Started](getting-started.md)** ← **Start here!** Complete guide for new users
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions
- **[Advanced Features](advanced-features.md)** - Detailed walkthrough of advanced features
- [System Requirements](system_requirements.md) - Hardware and software requirements
- [Configuration](config.md) - Complete configuration reference
- [Building from Source](build.md) - Build instructions
- [Docker Deployment](docker.md) - Container setup
- [YunoHost Packaging](../packaging/yunohost/README.md) - YunoHost app package and catalog submission process
- [Docker Download Permissions](docker-download-permissions.md) - UID/GID and bind-mount setup for writable download destinations
- [Reverse Proxy Setup](reverse_proxy.md) - Running behind a proxy
- [Known Issues](known_issues.md) - Current known problems
- [Runtime Feature Gates and Network Defaults](runtime-feature-gating.md) - Exact API-gate, service-lifecycle, pod enrollment, and network-default behavior

## 📘 User Guides

- [Dashboard](dashboard.md) - Seven-day totals for successful downloads and uploads
- [SongID and Discovery](songid-discovery.md) - Native identification and Discovery Graph workflows
- [System Admin Surfaces](system-surfaces.md) - Guided System UI for policies, integrations, diagnostics, source providers, and local preferences
- [Transfer Operations](transfer-operations.md) - Completed-download paths, template tokens, collision policy, permissions, request-history retention, and UTC API timestamps
- [Federation Diagnostics](federation-diagnostics.md) - Read-only ActivityPub and pod-signing diagnostics in System -> Integrations
- [Pods, Rooms, and Messages](pods-and-rooms.md) - Gold Star strict opt-in, pod rooms, unified messages, and listen-along boundaries
- [Soulseek Type-1 Obfuscation](soulseek-type1-obfuscation.md) - Default-on compatibility posture, mode semantics, runtime status, and safety caveats
- [Soulseek Native Discovery](soulseek-native-discovery.md) - UI and API guide for native interests, recommendations, similar users, item branching, user-interest lookup, and batch private messages
- [Pod Private Service Gateway](pod-vpn/vpn-user-guide.md) - Pod-scoped private service tunnels over mesh; not host VPN routing or internet egress
- [Lidarr Integration](lidarr-integration.md) - Configure quality-aware wanted sync, partial-album track recovery, auto-download, path mapping, and import behavior
- [Listening Party and Player](listening-party.md) - Integrated player, streaming, visualizers, and listen-along behavior
- [Virtual Soulfind User Guide](VIRTUAL_SOULFIND_USER_GUIDE.md) - Using Virtual Soulfind and Shadow Index
- [Solid Integration User Guide](SOLID_USER_GUIDE.md) - Using Solid WebID and Solid-OIDC integration

## 📖 Design Documents

### Core Features
- [DHT and Mesh Architecture](DHT_MESH_ARCHITECTURE.md) - Current terminology, discovery layers, overlay transport, and file-transfer boundaries
- [Multi-Source Downloads](multipart-downloads.md) - Network impact analysis and architecture
- [DHT Rendezvous Design](DHT_RENDEZVOUS_DESIGN.md) - Peer discovery and mesh overlay architecture
- [Music Discovery Federation Plan](design/music-discovery-federation-plan.md) - Planned mesh/social discovery features without backup or mirroring scope

### Security
- [Security Implementation Specs](SECURITY_IMPLEMENTATION_SPECS.md) - Detailed security feature specifications
- [CSRF Testing Guide](security/CSRF_TESTING_GUIDE.md) - CSRF protection testing and validation
- [Documentation Audit - Security Claims](archive/audits/DOCUMENTATION_AUDIT_SECURITY_CLAIMS.md) - Security claims review

## 🔧 Implementation Guides

- [How It Works](HOW-IT-WORKS.md) - Technical architecture overview
- [Features Overview](FEATURES.md) - Complete feature list and details
- [Lidarr Integration](lidarr-integration.md) - First-class plugin-free Lidarr quality-aware wanted sync, missing-track recovery, download handoff, and safe post-download import
- [Soulseek Type-1 Obfuscation](soulseek-type1-obfuscation.md) - Peer/distributed-message obfuscation options and runtime activation plan
- [Soulseek Native Discovery](soulseek-native-discovery.md) - Backend API and Web UI integration for native Soulseek discovery protocol features
- [VPN Agent](../src/slskdN.VpnAgent/README.md) - Host-side fail-closed VPN routing and forwarded-port integration
- [VPN Agent Setup](../src/slskdN.VpnAgent/GETTING_STARTED.md) - Release installation and first-use steps for Linux, Windows, and macOS
- [Self-Hosted Relay](../src/slskdN.VpnAgent/self-hosted-relay.md) - Tailscale-first public VPS ingress/egress for a home slskdN instance behind CGNAT
- [Self-Hosted Relay Tester Guide](self-hosted-relay-tester-guide.md) - Release installation, OCI/home setup, acceptance checks, and diagnostic evidence
- [System Admin Surfaces](system-surfaces.md) - Guided System UI and operator panels
- [Implementation Roadmap](IMPLEMENTATION_ROADMAP.md) - Development status and planned features

## 📚 Development Documentation

- [Development History](archive/DEVELOPMENT_HISTORY.md) - Feature completion timeline and releases
- [Fork Vision](archive/FORK_VISION.md) - Project philosophy and roadmap
- [Forking Guidance](FORKING.md) - Attribution and identity guidance for forks
- [Contributing](../CONTRIBUTING.md) - How to contribute to the project
- [API Documentation](api-documentation.md) - Complete API reference
- [Local Development](dev/LOCAL_DEVELOPMENT.md) - Development environment setup, including git hook installation
- [Player Quality Audit](dev/player-quality-audit.md) - Runtime evidence and remaining player completion work
- [Player Resource Measurement](dev/player-resource-measurement.md) - Isolated native CPU/memory protocol and evidence boundaries
- [Testing Policy](dev/testing-policy.md) - Required validation policy
- [Release Checklist](dev/release-checklist.md) - Release validation and packaging checklist

## 🔍 Additional Resources

- [Relay Mode](relay.md) - Relay server configuration
- [Migrations](migrations.md) - Database migration guide

---

**Note**: Prefer this index, [Getting Started](getting-started.md),
[Configuration](config.md), and feature-specific user guides for current
behavior.
