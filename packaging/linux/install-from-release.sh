#!/usr/bin/env bash
set -euo pipefail

SLSKDN_VERSION="${SLSKDN_VERSION:-}"
DEST="${SLSKDN_DEST:-/opt/slskdn}"
USER="${SLSKDN_USER:-slskd}"
DATA_DIR="${SLSKDN_DATA_DIR:-/var/lib/slskd}"
CONFIG_DIR="${SLSKDN_CONFIG_DIR:-/etc/slskd}"
CONFIG_FILE="${CONFIG_DIR}/slskd.yml"
SERVICE_FILE="/etc/systemd/system/slskd.service"

resolve_release_tag() {
  local requested="$1"
  if [ -n "$requested" ]; then
    echo "$requested"
    return
  fi

  local latest_json latest_tag
  latest_json="$(wget -qO- https://api.github.com/repos/snapetech-org/slskdN/releases/latest)"
  latest_tag="$(echo "$latest_json" | sed -n 's/.*"tag_name":[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
  if [ -z "$latest_tag" ]; then
    echo "Unable to resolve latest release tag from GitHub API" >&2
    exit 1
  fi

  echo "$latest_tag"
}

detect_asset_candidates() {
  local arch
  arch="$(uname -m)"

  case "$arch" in
    x86_64|amd64)
      printf '%s\n' \
        'slskdn-main-linux-glibc-x64.zip' \
        'slskdn-main-linux-x64.zip' \
        "slskdn-${SLSKDN_VERSION//-slskdn/.}-linux-x64.zip" \
        "slskdn-${SLSKDN_VERSION}-linux-x64.zip"
      ;;
    aarch64|arm64)
      printf '%s\n' \
        'slskdn-main-linux-glibc-arm64.zip' \
        'slskdn-main-linux-arm64.zip' \
        "slskdn-${SLSKDN_VERSION//-slskdn/.}-linux-arm64.zip" \
        "slskdn-${SLSKDN_VERSION}-linux-arm64.zip"
      ;;
    *)
      echo "Unsupported architecture: $arch" >&2
      exit 1
      ;;
  esac
}

download_asset() {
  local release_tag="$1"
  local asset_name="$2"
  local destination="$3"
  local url="https://github.com/snapetech-org/slskdN/releases/download/${release_tag}/${asset_name}"

  if wget -q -O "$destination" "$url"; then
    echo "$url"
    return 0
  fi

  rm -f "$destination"
  return 1
}

download_checksums() {
  local release_tag="$1"
  local destination="$2"
  local url="https://github.com/snapetech-org/slskdN/releases/download/${release_tag}/SHA256SUMS.txt"

  wget -q -O "$destination" "$url"
}

verify_asset_checksum() {
  local checksum_file="$1"
  local asset_name="$2"

  if [ ! -s "$checksum_file" ]; then
    echo "Missing SHA256SUMS.txt for release ${SLSKDN_VERSION}; refusing to install unverified artifact." >&2
    exit 1
  fi

  if ! grep -Eq "^[0-9a-fA-F]{64}[[:space:]]+\\*?${asset_name//./\\.}$" "$checksum_file"; then
    echo "SHA256SUMS.txt does not contain ${asset_name}; refusing to install unverified artifact." >&2
    exit 1
  fi

  sha256sum --check --ignore-missing "$checksum_file"
}

resolve_dotnet_apt_source() {
  local distro_id="$1"
  local distro_version="$2"
  local distro_codename="$3"
  local ubuntu_codename="$4"

  if [ "$distro_id" = "linuxmint" ]; then
    case "$ubuntu_codename" in
      noble)
        printf 'ubuntu 24.04 noble native\n'
        ;;
      jammy)
        printf 'ubuntu 22.04 jammy microsoft\n'
        ;;
      *)
        echo "Unsupported Linux Mint Ubuntu base: ${ubuntu_codename:-unknown}" >&2
        return 1
        ;;
    esac
  elif [ "$distro_id" = "ubuntu" ] && [ "$distro_version" = "24.04" ]; then
    printf 'ubuntu 24.04 noble native\n'
  else
    printf '%s %s %s microsoft\n' "$distro_id" "$distro_version" "$distro_codename"
  fi
}

install_dotnet_runtime() {
  . /etc/os-release

  local legacy_mint_source="/etc/apt/sources.list.d/microsoft.list"
  if [ "$ID" = "linuxmint" ] &&
    [ -f "$legacy_mint_source" ] &&
    grep -q 'packages.microsoft.com/linuxmint/' "$legacy_mint_source"; then
    rm -f "$legacy_mint_source"
  fi

  local package_source
  package_source="$(resolve_dotnet_apt_source "$ID" "$VERSION_ID" "${VERSION_CODENAME:-}" "${UBUNTU_CODENAME:-}")"
  local repo_id repo_version codename feed
  read -r repo_id repo_version codename feed <<< "$package_source"

  apt-get update -qq
  apt-get install -y -qq wget ca-certificates unzip gpg

  if [ "$feed" = "microsoft" ]; then
    wget -qO /etc/apt/trusted.gpg.d/microsoft.asc https://packages.microsoft.com/keys/microsoft.asc
    local repo="https://packages.microsoft.com/${repo_id}/${repo_version}/prod"
    echo "deb [arch=$(dpkg --print-architecture)] ${repo} ${codename} main" > /etc/apt/sources.list.d/microsoft.list
    apt-get update -qq
  fi

  apt-get install -y -qq aspnetcore-runtime-10.0 yt-dlp
}

write_default_config() {
  if [ -f "$CONFIG_FILE" ]; then
    echo "Config already exists: $CONFIG_FILE"
    return
  fi

  cat > "$CONFIG_FILE" <<'CFG'
# slskd configuration — edit: soulseek.username, soulseek.password, shares.directories
# See https://github.com/snapetech-org/slskdN for full options

soulseek:
  username:
  password:
  description: slskd user

directories:
  downloads: /var/lib/slskd/downloads
  incomplete: /var/lib/slskd/incomplete

web:
  port: 5030
  https:
    disabled: true

# Public BitTorrent DHT rendezvous and the mesh overlay are enabled by default.
# Set feature.Dht and dht.enabled false to disable DHT cleanly. Forward
# 50305/tcp and 50305/udp when exposing the mesh publicly. If a
# VPN rewrites public ports, set
# advertised_overlay_port manually or use vpn_port_sync after enabling the VPN
# integration.
# dht:
#   enabled: true
#   lan_only: false
#   overlay_port: 50305
#   advertised_overlay_port: 0
#   vpn_port_sync: disabled
#   dht_port: 50305

# integrations:
#   vpn:
#     enabled: false
#     port_forwarding: false
#     gluetun:
#       url: http://127.0.0.1:8010
CFG

  chown "${USER}:${USER}" "$CONFIG_FILE"
  echo "Created $CONFIG_FILE — please set soulseek.username and soulseek.password"
}

write_systemd_unit() {
  cat > "$SERVICE_FILE" <<SVC
[Unit]
Description=slskd - Soulseek client/server
Documentation=https://github.com/snapetech-org/slskdN
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USER}
Group=${USER}
ExecStart=/usr/bin/dotnet ${DEST}/slskd.dll --config ${CONFIG_FILE}
WorkingDirectory=${DATA_DIR}
Environment="HOME=${DATA_DIR}"
Environment="DOTNET_ROOT=/usr/share/dotnet"
UMask=0002
Restart=on-failure
RestartSec=10

NoNewPrivileges=yes
ProtectSystem=full
PrivateTmp=yes
ReadWritePaths=${DATA_DIR} ${CONFIG_DIR}

[Install]
WantedBy=multi-user.target
SVC

  systemctl daemon-reload
}

install_vpn_agent_payload() {
  local agent_root="${DEST}/vpn-agent"
  local agent_bin="${agent_root}/slskdN-vpn-agent"
  local unit unit_name

  if [ ! -x "$agent_bin" ]; then
    echo "VPN agent payload not present in this release asset; skipping VPN helper install."
    return
  fi

  install -d -m 0755 /usr/local/lib/slskdN-vpn-agent
  install -m 0755 "$agent_bin" /usr/local/lib/slskdN-vpn-agent/slskdN-vpn-agent
  ln -sfn /usr/local/lib/slskdN-vpn-agent/slskdN-vpn-agent /usr/local/bin/slskdN-vpn-agent

  if [ -d "${agent_root}/systemd" ]; then
    for unit_name in \
      slskdN-vpn-split.service \
      slskdN-vpn-ingress.service \
      slskdN-vpn-ingress-renew.service \
      slskdN-vpn-ingress-renew.timer \
      slskdN-vpn-gluetun-compat.service \
      slskdN-vpn-watchdog.service \
      slskdN-vpn-watchdog.timer; do
      unit="/etc/systemd/system/${unit_name}"
      install -D -m 0644 "${agent_root}/systemd/${unit_name}" "$unit"
      sed -i "/^\\[Install\\]/,\$! s/slskdN\\.service/slskd.service/g" "$unit"
    done
  fi

  install -d -m 0755 /var/lib/slskdN-vpn
  systemctl daemon-reload
}

main() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root." >&2
    exit 1
  fi

  echo "[1/7] Installing .NET runtime 10.0 and prerequisites..."
  install_dotnet_runtime

  SLSKDN_VERSION="$(resolve_release_tag "$SLSKDN_VERSION")"

  echo "[2/7] Downloading slskdn ${SLSKDN_VERSION}..."
  local work_dir
  work_dir="$(mktemp -d)"
  trap "rm -rf '$work_dir'" EXIT
  cd "$work_dir"

  local zip=""
  local release_tag
  local resolved_release_tag=""
  for release_tag in "$SLSKDN_VERSION" "${SLSKDN_VERSION//.slskdn./-slskdn.}"; do
    while IFS= read -r candidate; do
      if download_asset "$release_tag" "$candidate" "$candidate" >/dev/null; then
        zip="$candidate"
        resolved_release_tag="$release_tag"
        break 2
      fi
    done < <(detect_asset_candidates)
  done

  if [ -z "$zip" ]; then
    echo "Download failed for ${SLSKDN_VERSION}: no matching Linux release asset found" >&2
    exit 1
  fi

  local checksum_file="SHA256SUMS.txt"
  download_checksums "$resolved_release_tag" "$checksum_file"
  verify_asset_checksum "$checksum_file" "$zip"

  echo "[3/7] Replacing installed tree at ${DEST}..."
  systemctl stop slskd 2>/dev/null || true
  rm -rf "$DEST"
  mkdir -p "$DEST"
  unzip -o -q "$zip" -d "$DEST"
  if [ ! -f "${DEST}/slskd.dll" ]; then
    echo "Expected slskd.dll in ${DEST}; contents: $(ls -la "$DEST")" >&2
    exit 1
  fi
  install_vpn_agent_payload

  echo "[4/7] Creating user and directories..."
  id -u "$USER" >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin -d "$DATA_DIR" "$USER"
  mkdir -p "$DATA_DIR" "$DATA_DIR/downloads" "$DATA_DIR/incomplete" "$CONFIG_DIR"
  chown -R "${USER}:${USER}" "$DATA_DIR" "$DEST"
  chmod -R g+rwX "$DATA_DIR"

  echo "[5/7] Installing config..."
  write_default_config
  chown "${USER}:${USER}" "$CONFIG_FILE"
  chmod 664 "$CONFIG_FILE"

  echo "[6/7] Installing systemd unit..."
  write_systemd_unit

  echo "[7/7] Done."
  echo
  echo "Installed release ${SLSKDN_VERSION} to ${DEST}."
  echo "Systemd now runs: /usr/bin/dotnet ${DEST}/slskd.dll --config ${CONFIG_FILE}"
  echo "The optional Linux VPN agent is installed but not active; it is native Linux software and does not use Wine."
  echo "To set it up, first configure the VPN integration in ${CONFIG_FILE}, then follow ${DEST}/vpn-agent/GETTING_STARTED.md and run: sudo ${DEST}/vpn-agent/install.sh"
  echo "The VPN routing service starts before slskd so Soulseek traffic is protected when the app starts."
  echo "Web UI: http://localhost:5030 (HTTPS is disabled unless you configure it)."
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
