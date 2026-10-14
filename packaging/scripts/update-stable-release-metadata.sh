#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

VERSION="${1:-}"
LINUX_X64_HEX="${2:-}"
LINUX_ARM64_HEX="${3:-}"
MACOS_X64_HEX="${4:-}"
MACOS_ARM64_HEX="${5:-}"
WIN_X64_HEX="${6:-}"
RELEASE_TAG="${7:-$VERSION}"

if [[ -z "$VERSION" || -z "$LINUX_X64_HEX" || -z "$LINUX_ARM64_HEX" || -z "$MACOS_X64_HEX" || -z "$MACOS_ARM64_HEX" || -z "$WIN_X64_HEX" ]]; then
    echo "Usage: $0 <version> <linux-glibc-x64-sha256-hex> <linux-glibc-arm64-sha256-hex> <macos-x64-sha256-hex> <macos-arm64-sha256-hex> <win-x64-sha256-hex> [release-tag]" >&2
    exit 1
fi

hex_to_sri() {
    local hex="$1"
    printf 'sha256-%s' "$(printf '%s' "$hex" | xxd -r -p | base64 -w0)"
}

LINUX_X64_SRI="$(hex_to_sri "$LINUX_X64_HEX")"
LINUX_ARM64_SRI="$(hex_to_sri "$LINUX_ARM64_HEX")"
MACOS_X64_SRI="$(hex_to_sri "$MACOS_X64_HEX")"
MACOS_ARM64_SRI="$(hex_to_sri "$MACOS_ARM64_HEX")"
WIN_URL="https://github.com/snapetech-org/slskdN/releases/download/${RELEASE_TAG}/slskdn-main-win-x64.zip"
PKGVER_DOTTED="${VERSION//-/.}"
VERSION_REGEX='[0-9][0-9.]*-slskdn\.[0-9]\+'

bash packaging/scripts/update-winget-manifests.sh     stable     "$VERSION"     "$WIN_URL"     "$WIN_X64_HEX"     "$RELEASE_TAG"

cat > Formula/slskdn.rb <<EOF
class Slskdn < Formula
  desc "Unofficial slskd fork with batteries-included Soulseek features"
  homepage "https://github.com/snapetech-org/slskdN"
  license "AGPL-3.0-or-later"
  version "$VERSION"
  on_macos do
    on_arm do
      url "https://github.com/snapetech-org/slskdN/releases/download/${RELEASE_TAG}/slskdn-main-osx-arm64.zip"
      sha256 "$MACOS_ARM64_HEX"
    end
    on_intel do
      url "https://github.com/snapetech-org/slskdN/releases/download/${RELEASE_TAG}/slskdn-main-osx-x64.zip"
      sha256 "$MACOS_X64_HEX"
    end
  end
  on_linux do
    url "https://github.com/snapetech-org/slskdN/releases/download/${RELEASE_TAG}/slskdn-main-linux-glibc-x64.zip"
    sha256 "$LINUX_X64_HEX"
  end
  def install
    libexec.install Dir["*"]
    (bin/"slskd").write_exec_script libexec/"slskd"
    (bin/"slskdn").write_exec_script libexec/"slskd"
    if (libexec/"vpn-agent/slskdN-vpn-agent").exist?
      (bin/"slskdN-vpn-agent").write_exec_script libexec/"vpn-agent/slskdN-vpn-agent"
    end
  end
end
EOF

cat > packaging/homebrew/Formula/slskdn.rb <<EOF
class Slskdn < Formula
  desc "Unofficial slskd fork with batteries-included Soulseek features"
  homepage "https://github.com/snapetech-org/slskdN"
  license "AGPL-3.0-or-later"
  version "$VERSION"

  on_macos do
    on_arm do
      url "https://github.com/snapetech-org/slskdN/releases/download/${RELEASE_TAG}/slskdn-main-osx-arm64.zip"
      sha256 "$MACOS_ARM64_HEX"
    end
    on_intel do
      url "https://github.com/snapetech-org/slskdN/releases/download/${RELEASE_TAG}/slskdn-main-osx-x64.zip"
      sha256 "$MACOS_X64_HEX"
    end
  end

  on_linux do
    url "https://github.com/snapetech-org/slskdN/releases/download/${RELEASE_TAG}/slskdn-main-linux-glibc-x64.zip"
    sha256 "$LINUX_X64_HEX"
  end

  def install
    libexec.install Dir["*"]
    (bin/"slskd").write_exec_script libexec/"slskd"
    (bin/"slskdn").write_exec_script libexec/"slskd"
    if (libexec/"vpn-agent/slskdN-vpn-agent").exist?
      (bin/"slskdN-vpn-agent").write_exec_script libexec/"vpn-agent/slskdN-vpn-agent"
    end
  end

  test do
    assert_match "slskd", shell_output("#{bin}/slskd --help", 1)
    if (bin/"slskdN-vpn-agent").exist?
      assert_match "slskdN-vpn-agent", shell_output("#{bin}/slskdN-vpn-agent --help")
    end
  end
end
EOF

sed -i 's/version = ".*";/version = "'"${VERSION}"'";/' flake.nix
sed -i '/stableSources = {/,/};/s|url = "https://github.com/snapetech-org/slskdN/releases/download/.*/slskdn-main-linux[^"]*x64.zip";|url = "https://github.com/snapetech-org/slskdN/releases/download/'"${RELEASE_TAG}"'/slskdn-main-linux-glibc-x64.zip";|' flake.nix
sed -i '/stableSources = {/,/};/s|url = "https://github.com/snapetech-org/slskdN/releases/download/.*/slskdn-main-linux[^"]*arm64.zip";|url = "https://github.com/snapetech-org/slskdN/releases/download/'"${RELEASE_TAG}"'/slskdn-main-linux-glibc-arm64.zip";|' flake.nix
sed -i '/stableSources = {/,/};/s|sha256 = ".*"; # x86_64-linux (glibc)|sha256 = "'"${LINUX_X64_SRI}"'"; # x86_64-linux (glibc)|' flake.nix
sed -i '/stableSources = {/,/};/s|sha256 = ".*"; # aarch64-linux (glibc)|sha256 = "'"${LINUX_ARM64_SRI}"'"; # aarch64-linux (glibc)|' flake.nix
sed -i '/stableSources = {/,/};/s|sha256 = ".*"; # x86_64-darwin|sha256 = "'"${MACOS_X64_SRI}"'"; # x86_64-darwin|' flake.nix
sed -i '/stableSources = {/,/};/s|sha256 = ".*"; # aarch64-darwin|sha256 = "'"${MACOS_ARM64_SRI}"'"; # aarch64-darwin|' flake.nix

sed -i "s|^version: '.*'|version: '${VERSION}'|" packaging/snap/snapcraft.yaml
sed -i "s|^    source: https://github.com/snapetech-org/slskdN/releases/download/.*/slskdn-main-linux-glibc-x64.zip|    source: https://github.com/snapetech-org/slskdN/releases/download/${RELEASE_TAG}/slskdn-main-linux-glibc-x64.zip|" packaging/snap/snapcraft.yaml
sed -i "s|^    source-checksum: sha256/[0-9a-f]\{64\}|    source-checksum: sha256/${LINUX_X64_HEX}|" packaging/snap/snapcraft.yaml

sed -i "s|# slskdN .* Linux .* x64|# slskdN ${VERSION} Linux glibc x64|" packaging/flatpak/io.github.slskd.slskdn.yml
sed -i "s|# Install slskdN (from .*: slskd, slskd.dll, deps, wwwroot)|# Install slskdN (from slskdn-main-linux-glibc-x64.zip: slskd, slskd.dll, deps, wwwroot)|" packaging/flatpak/io.github.slskd.slskdn.yml
python3 - <<PY_FLATPAK
from pathlib import Path
import re

path = Path("packaging/flatpak/io.github.slskd.slskdn.yml")
text = path.read_text()
pattern = re.compile(
    r"      # slskdN .*? asset slskdn-main-linux.*?zip\)\n"
    r"      - type: archive\n"
    r"        url: https://github.com/snapetech-org/slskdN/releases/download/.*/slskdn-main-linux.*?x64\.zip\n"
    r"        sha256: [0-9a-f]{64}\n",
    re.S,
)
replacement = (
    f"      # slskdN ${VERSION} Linux glibc x64 (snapetech; asset slskdn-main-linux-glibc-x64.zip)\n"
    f"      - type: archive\n"
    f"        url: https://github.com/snapetech-org/slskdN/releases/download/${RELEASE_TAG}/slskdn-main-linux-glibc-x64.zip\n"
    f"        sha256: ${LINUX_X64_HEX}\n"
)
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit("failed to update Flatpak slskdn archive block")
path.write_text(text)
PY_FLATPAK

bash scripts/check-flatpak-manifest-structure.sh

sed -i 's/appVersion: ".*"/appVersion: "'"${VERSION}"'"/' packaging/truenas-scale/charts/slskdn/Chart.yaml
sed -i 's/appVersion: ".*"/appVersion: "'"${VERSION}"'"/' packaging/helm/slskdn/Chart.yaml
sed -i "s/--set image.tag=.*/--set image.tag=${VERSION}/" packaging/helm/slskdn/README.md

sed -i "s#<version>.*</version>#<version>${VERSION}</version>#" packaging/chocolatey/slskdn.nuspec
sed -i "s#^\$url.*#\$url        = \"https://github.com/snapetech-org/slskdN/releases/download/${RELEASE_TAG}/slskdn-main-win-x64.zip\"#" packaging/chocolatey/tools/chocolateyinstall.ps1
sed -i "s#^\$checksum.*#\$checksum   = \"${WIN_X64_HEX}\"#" packaging/chocolatey/tools/chocolateyinstall.ps1

sed -i "s|^Source0:.*|Source0:        https://github.com/snapetech-org/slskdN/releases/download/${RELEASE_TAG}/slskdn-main-linux-glibc-x64.zip|" packaging/rpm/slskdn.spec
sed -i "s|^Version:.*|Version:        ${PKGVER_DOTTED}|" packaging/rpm/slskdn.spec
sed -i "s|${VERSION_REGEX} (slskdn-main-linux-glibc-x64.zip)|${VERSION} (slskdn-main-linux-glibc-x64.zip)|" packaging/rpm/slskdn.spec

sed -i "1c slskdn (${PKGVER_DOTTED}-1) stable; urgency=medium" packaging/debian/changelog
sed -i "s|stable release ${VERSION_REGEX}|stable release ${VERSION}|" packaging/debian/changelog
sed -i "s|SLSKDN_VERSION=${VERSION_REGEX}|SLSKDN_VERSION=${VERSION}|" packaging/proxmox-lxc/README.md

sed -i "s|^pkgver=.*|pkgver=${PKGVER_DOTTED}|" packaging/aur/PKGBUILD
sed -i "s|^pkgver=.*|pkgver=${PKGVER_DOTTED}|" packaging/aur/PKGBUILD-bin
sed -i 's|slskdn-main-linux-x64.zip::https://github.com/snapetech-org/slskdN/releases/download/${pkgver//.slskdn/-slskdn}/slskdn-main-linux-x64.zip|slskdn-${pkgver}-main-linux-glibc-x64.zip::https://github.com/snapetech-org/slskdN/releases/download/${pkgver//.slskdn/-slskdn}/slskdn-main-linux-glibc-x64.zip|' packaging/aur/PKGBUILD-bin

sed -i "s|https://github.com/snapetech-org/slskdN/releases/download/${VERSION_REGEX}/slskdn-main-linux-glibc-x64.zip|https://github.com/snapetech-org/slskdN/releases/download/${RELEASE_TAG}/slskdn-main-linux-glibc-x64.zip|g" packaging/flatpak/FLATHUB_SUBMISSION.md
sed -i 's|slskdn-main-linux-x64.zip|slskdn-main-linux-glibc-x64.zip|g' packaging/flatpak/FLATHUB_SUBMISSION.md

echo "Updated stable release metadata to ${VERSION} (tag ${RELEASE_TAG})."
