#!/usr/bin/env bash
set -euo pipefail

have() {
  command -v "$1" >/dev/null 2>&1
}

can_install_packages() {
  if (( EUID == 0 )); then
    return 0
  fi

  have sudo && sudo -n true >/dev/null 2>&1
}

run_as_root() {
  if (( EUID == 0 )); then
    "$@"
  else
    sudo -n "$@"
  fi
}

missing=()
have jq || missing+=(jq)
have rg || missing+=(ripgrep)
if (( ${#missing[@]} == 0 )); then
  exit 0
fi

if can_install_packages; then
  packages=()
  for tool in "${missing[@]}"; do
    case "$tool" in
      jq|ripgrep) packages+=("$tool") ;;
    esac
  done

  if run_as_root apt-get update &&
    run_as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}"; then
    exit 0
  fi
  echo "Package installation is unavailable; using checksum-pinned scanner tools." >&2
fi

for tool in curl sha256sum tar gzip install mktemp mkdir chmod rm uname; do
  if ! have "$tool"; then
    echo "install-scanner-tools: $tool is required for the unprivileged fallback." >&2
    exit 1
  fi
done

runner_temp="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"
case "$runner_temp" in
  /*) ;;
  *)
    echo "install-scanner-tools: RUNNER_TEMP must be an absolute path." >&2
    exit 1
    ;;
esac
if [[ ! -d "$runner_temp" || -L "$runner_temp" ]]; then
  echo "install-scanner-tools: RUNNER_TEMP must be an existing, non-symlink directory." >&2
  exit 1
fi

tool_root="${runner_temp%/}/slskdn-ci-tools"
tool_bin="${tool_root}/bin"
mkdir -p "$tool_bin"
if [[ -L "$tool_root" || -L "$tool_bin" || ! -O "$tool_root" || ! -O "$tool_bin" ]]; then
  echo "install-scanner-tools: tool directories must be owned by this job and cannot be symlinks." >&2
  exit 1
fi
chmod 700 "$tool_root" "$tool_bin"

download_dir="$(mktemp -d "${runner_temp%/}/slskdn-tools.XXXXXX")"
cleanup() {
  rm -rf -- "$download_dir"
}
trap cleanup EXIT

install_unprivileged_tool() {
  local tool="$1"
  local arch
  local asset
  local asset_dir=""
  local checksum
  local version
  local url
  local command_name
  local download_path

  arch="$(uname -m)"
  case "$tool:$arch" in
    jq:x86_64|jq:amd64)
      version="1.8.2"
      asset="jq-linux-amd64"
      checksum="b1c22172dd303f3be49e935aa56aa48a8b7a46e0bc838b4997d3bb451495870f"
      url="https://github.com/jqlang/jq/releases/download/jq-${version}/${asset}"
      command_name="jq"
      ;;
    jq:aarch64|jq:arm64)
      version="1.8.2"
      asset="jq-linux-arm64"
      checksum="8b85c817833814ddca00a144c33705546355afccf0cf39b188f3cdb48b852309"
      url="https://github.com/jqlang/jq/releases/download/jq-${version}/${asset}"
      command_name="jq"
      ;;
    ripgrep:x86_64|ripgrep:amd64)
      version="15.2.0"
      asset="ripgrep-${version}-x86_64-unknown-linux-musl.tar.gz"
      asset_dir="ripgrep-${version}-x86_64-unknown-linux-musl"
      checksum="33e15bcf1624b25cdd2a55813a47a2f95dbe126268203e76aa6a585d1e7b149c"
      url="https://github.com/BurntSushi/ripgrep/releases/download/${version}/${asset}"
      command_name="rg"
      ;;
    ripgrep:aarch64|ripgrep:arm64)
      version="15.2.0"
      asset="ripgrep-${version}-aarch64-unknown-linux-musl.tar.gz"
      asset_dir="ripgrep-${version}-aarch64-unknown-linux-musl"
      checksum="800b1e7206afe799dfb5a6901f23147cfaabe0e52210538100f61e86e1740915"
      url="https://github.com/BurntSushi/ripgrep/releases/download/${version}/${asset}"
      command_name="rg"
      ;;
    *)
      echo "install-scanner-tools: no pinned ${tool} artifact for ${arch}." >&2
      return 1
      ;;
  esac

  download_path="${download_dir}/${asset}"
  if ! curl --fail --location --silent --show-error --retry 3 --retry-connrefused \
    --max-time 90 --output "$download_path" "$url"; then
    echo "install-scanner-tools: could not download pinned ${tool} ${version}." >&2
    return 1
  fi

  if ! printf '%s  %s\n' "$checksum" "$download_path" | sha256sum --check --status; then
    echo "install-scanner-tools: checksum validation failed for ${tool} ${version}." >&2
    return 1
  fi

  if [[ "$tool" == "ripgrep" ]]; then
    if ! tar --extract --gzip --to-stdout --file "$download_path" "${asset_dir}/rg" \
      >"${download_dir}/rg" || [[ ! -s "${download_dir}/rg" ]]; then
      echo "install-scanner-tools: could not extract pinned ripgrep ${version}." >&2
      return 1
    fi
    download_path="${download_dir}/rg"
  fi

  if ! install -m 0755 "$download_path" "${tool_bin}/${command_name}"; then
    echo "install-scanner-tools: could not install ${tool} ${version} in RUNNER_TEMP." >&2
    return 1
  fi
  echo "Installed pinned ${tool} ${version} in RUNNER_TEMP."
}

for tool in "${missing[@]}"; do
  install_unprivileged_tool "$tool"
done

if [[ -n "${GITHUB_PATH:-}" ]]; then
  if [[ -L "$GITHUB_PATH" || ! -f "$GITHUB_PATH" || ! -O "$GITHUB_PATH" ]]; then
    echo "install-scanner-tools: GITHUB_PATH must be a job-owned regular file." >&2
    exit 1
  fi
  printf '%s\n' "$tool_bin" >>"$GITHUB_PATH"
fi

echo "Scanner dependencies are available from ${tool_bin}."
