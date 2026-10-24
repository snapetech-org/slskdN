#!/usr/bin/env bash
# Verify release artifacts: download, verify checksums, inspect bundled feature
# markers, and run the Linux binary for version output.
# Usage:
#   ./scripts/verify-release-artifacts.sh [TAG]
#   TAG defaults to the latest canonical v<version> release.
set -euo pipefail

REPO="${REPO:-snapetech/slskdn}"
TAG="${1:-}"

if [ -z "$TAG" ]; then
  echo "Fetching latest v release tag..."
  # gh release list columns: title, type, tag, date (tab-separated)
  TAG=$(gh release list --repo "$REPO" --limit 100 | awk -F'\t' '$3 ~ /^v[0-9]/ {print $3; exit}')
  if [ -z "$TAG" ]; then
    echo "No v<version> release found. Pass a historical release tag explicitly."
    exit 1
  fi
  echo "Using tag: $TAG"
fi

RELEASE_TAG="$TAG"
if [[ "$TAG" == build-main-* ]]; then
  RELEASE_TAG="${TAG#build-main-}"
elif [[ "$TAG" == build-dev-* ]]; then
  RELEASE_TAG="${TAG#build-dev-}"
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT
cd "$WORK_DIR"

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

echo "Downloading assets from $REPO @ $RELEASE_TAG..."
gh release download "$RELEASE_TAG" --repo "$REPO" --dir . || fail "Download failed (gh auth? release exists?)"

shopt -s nullglob
zip_files=(*.zip)
if [ "${#zip_files[@]}" -eq 0 ]; then
  fail "No zip assets were downloaded for $TAG"
fi

echo ""
echo "=== SHA256 checksums ==="
for f in "${zip_files[@]}"; do
  sha=$(sha256sum "$f" | awk '{print $1}')
  echo "$sha  $f"
done

if [ -f SHA256SUMS.txt ]; then
  echo ""
  echo "=== Published SHA256SUMS verification ==="
  sha256sum --ignore-missing -c SHA256SUMS.txt
else
  fail "SHA256SUMS.txt is missing from release assets"
fi

echo ""
echo "=== Required release asset checks ==="
for required_asset in \
  slskdn-main-linux-glibc-x64.zip \
  slskdn-main-linux-glibc-arm64.zip \
  slskdn-main-linux-musl-x64.zip \
  slskdn-main-osx-x64.zip \
  slskdn-main-osx-arm64.zip; do
  if [[ ("$TAG" == v* || "$TAG" == build-main-* || "$TAG" =~ -slskdn\.[0-9]+$) && ! -f "$required_asset" ]]; then
    fail "Missing required main release asset: $required_asset"
  fi
done

if [[ "$TAG" == build-dev-* || "$TAG" =~ \.dev\. ]]; then
  for required_asset in \
    slskdn-dev-linux-glibc-x64.zip \
    slskdn-dev-linux-glibc-arm64.zip \
    slskdn-dev-linux-musl-x64.zip \
    slskdn-dev-osx-x64.zip \
    slskdn-dev-osx-arm64.zip; do
    if [ ! -f "$required_asset" ]; then
      fail "Missing required dev release asset: $required_asset"
    fi
  done
fi

echo ""
echo "=== Version check (Linux x64 binary) ==="
LINUX_ZIP=""
for f in slskdn-dev-linux-glibc-x64.zip slskdn-main-linux-glibc-x64.zip slskdn-dev-linux-x64.zip slskdn-main-linux-x64.zip slskdn-*-linux-x64.zip; do
  if [ -f "$f" ]; then LINUX_ZIP="$f"; break; fi
done
if [ -n "$LINUX_ZIP" ]; then
  unzip -q -o "$LINUX_ZIP" -d extracted
  if [ -x extracted/vpn-agent/slskdN-vpn-agent ]; then
    echo "VPN helper payload present."
  else
    fail "Linux x64 zip is missing executable vpn-agent/slskdN-vpn-agent"
  fi
  for required_file in \
    vpn-agent/GETTING_STARTED.md \
    vpn-agent/README.md \
    vpn-agent/manual-linux-wireguard.md \
    vpn-agent/external-tunnel.md \
    vpn-agent/windows-macos.md \
    vpn-agent/api-contract.md \
    vpn-agent/self-hosted-relay-tester-guide.md; do
    if [ ! -s "extracted/$required_file" ]; then
      fail "Linux x64 zip is missing $required_file"
    fi
  done
  if [ ! -x extracted/vpn-agent/install.sh ]; then
    fail "Linux x64 zip is missing executable vpn-agent/install.sh"
  fi

  marker_found=0
  for web_asset_pattern in 'wwwroot/static/js/*.js' 'wwwroot/assets/*.js'; do
    web_asset_dump="$WORK_DIR/web-assets-${web_asset_pattern//[^A-Za-z0-9]/_}.js"
    if unzip -p "$LINUX_ZIP" "$web_asset_pattern" >"$web_asset_dump" 2>/dev/null &&
       grep -Fq 'slskdn-footer-session-total' "$web_asset_dump"; then
      marker_found=1
      break
    fi
  done

  if [ "$marker_found" -eq 1 ]; then
    echo "Footer session-total marker present in bundled Web assets."
  else
    fail "Linux x64 zip Web bundle is missing slskdn-footer-session-total"
  fi

  if [ -f extracted/slskd ]; then
    chmod +x extracted/slskd
    version_output="$(./extracted/slskd --version 2>/dev/null || ./extracted/slskd -v 2>/dev/null || true)"
    if [ -z "$version_output" ]; then
      fail "Linux x64 binary did not print version output"
    fi
    echo "$version_output"
  else
    echo "No extracted/slskd found; listing:" >&2
    ls -la extracted/
    fail "Linux x64 zip is missing slskd binary"
  fi
else
  fail "No Linux x64 zip found to run version and payload checks."
fi

echo ""
echo "Release artifact verification passed."
