# [Support] slskdN - Soulseek web client and Docker image

slskdN is an unofficial, batteries-included fork of slskd, a web client for the Soulseek file-sharing network.

This thread is for Unraid installation, configuration, and container-specific support.

Project: https://github.com/snapetech/slskdN
Docker image: https://ghcr.io/snapetech/slskdn
Unraid template: https://github.com/snapetech/slskdN/raw/refs/heads/main/packaging/unraid/slskdn.xml
License: AGPL-3.0

## Community Applications status

The slskdN Unraid template is being submitted to Community Applications. Until approval, the template can be installed manually from the repository.

## Template usability feedback

Community feedback requested that Docker environment variables be exposed in the template and left blank when optional, so users do not have to hunt through documentation for settings that were omitted from the template.

The current template exposes the documented optional SLSKD_* environment overrides as advanced fields with blank values. Core ports, paths, credentials, and image-managed runtime settings retain safe defaults.

## Container details

Web UI: 5030/tcp
HTTPS Web UI: 5031/tcp
Soulseek incoming connections and slskdN mesh overlay: 50300/tcp (plain,
obfuscated, and mesh TCP connections share this one port by default)
Public DHT, mesh overlay control, and QUIC control/data-plane traffic: 50300/udp (one shared UDP socket)

Port 50300/tcp should be forwarded from the router to the Unraid server for the best Soulseek and mesh connectivity.

If DHT, mesh, or QUIC services are enabled, also forward 50300/udp. TCP and UDP are separate port spaces, so both mappings use the same port number.

Ports 55305 and 55401 are loopback-only QUIC backend ports and should not be published.

## Default paths

/app - application data, configuration, and databases
/downloads - completed downloads; choose an Unraid share before starting
/app/incomplete - incomplete downloads; stored in the writable App Data mapping
/music - optional music library; read-only access is recommended

The Downloads path is required and must be filled with the desired share before
starting the container. Incomplete files are kept under `/app/incomplete`,
which slskdN creates in the writable App Data mapping. Music Library remains
optional and can be left unmounted.

## Environment settings

PUID: 1000
PGID: 1000
TZ: America/Chicago
Web UI username: slskd
Web UI password: slskd
Soulseek username: set in the web UI or the template field
Soulseek password: set in the web UI or the template field

The template includes advanced fields for the documented optional SLSKD_* Docker environment overrides covering completed-download destinations, retries, retention, shares, search, Soulseek behavior, obfuscation, proxies, authentication, metrics, notifications, logging, and integrations. Optional fields are blank by default.

Runtime-only SLSKD_SCRIPT_DATA and image metadata variables such as SLSKD_DOCKER_TAG are not user configuration fields. The complete environment-variable reference is here:

https://github.com/snapetech/slskdN/blob/main/docs/config.md

Change the default web UI username and password after the first login. Do not combine PUID/PGID with a Docker --user override.

## First run

1. Install the template from Community Applications when the listing is approved, or use the raw template XML as a local user template until then.
2. Choose an Unraid share and directory for Downloads.
3. Optionally choose a read-only Unraid share and directory for Music Library.
4. Open the web UI at http://YOUR_UNRAID_IP:5030.
5. Change the default web UI credentials.
6. Configure the Soulseek account and shared folders.
7. Forward 50300/tcp, and forward 50300/udp if DHT, mesh, or QUIC services are enabled.

## Features

- Automatic replacement of stuck downloads with alternative sources
- Wishlist and background search with automatic downloads
- Source ranking based on speed, queue, and history
- User notes and download history
- Blocked users in search results
- Multiple download destinations
- File deletion from the web UI
- Push notifications through Ntfy, Pushover, and Pushbullet
- Tabbed browse sessions
- DHT and mesh networking when explicitly enabled
- Additional slskdN enhancements

## Reporting problems

Please include:

- Unraid version
- Container image tag
- Container logs
- Template settings
- Host-to-container path mappings
- Exact steps to reproduce the issue

Redact passwords, API keys, Soulseek credentials, public IP addresses, and other private information from logs.

Application source and general bug reports are maintained at:

https://github.com/snapetech/slskdN
