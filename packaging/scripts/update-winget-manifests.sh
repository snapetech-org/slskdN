#!/usr/bin/env bash

set -euo pipefail

CHANNEL="${1:-}"
VERSION="${2:-}"
WIN_X64_URL="${3:-}"
WIN_X64_SHA="${4:-}"
RELEASE_TAG="${5:-$VERSION}"

if [ -z "$CHANNEL" ] || [ -z "$VERSION" ] || [ -z "$WIN_X64_URL" ] || [ -z "$WIN_X64_SHA" ]; then
    echo "Usage: $0 <stable> <version> <win-x64-url> <win-x64-sha> [release-tag]"
    exit 1
fi

case "$CHANNEL" in
    stable)
        PACKAGE_IDENTIFIER="snapetech.slskdn"
        FILE_BASENAME="snapetech.slskdn"
        PACKAGE_NAME="slskdN"
        MONIKER="slskdn"
        COMMAND_ALIAS="slskdn"
        SHORT_DESCRIPTION="Soulseek client with built-in SongID and Discovery Graph"
        DESCRIPTION=$(cat <<'EOF'
slskdN is an unofficial batteries-included fork of slskd that makes identity
and discovery first-class features for Soulseek.

Stable features include:
- SongID for YouTube, Spotify, text, and local-file identification
- Discovery Graph atlas across SongID, MusicBrainz, and search
- Multi-source downloads, auto-replace, and wishlist/background search
- Mesh, Solid, and package-manager friendly distribution
EOF
)
        RELEASE_NOTES=$(cat <<EOF
Stable Release $VERSION

See https://github.com/snapetech-org/slskdN/releases/tag/$RELEASE_TAG for details.
EOF
)
        RELEASE_NOTES_URL="https://github.com/snapetech-org/slskdN/releases/tag/$RELEASE_TAG"
        ;;
    *)
        echo "Unknown channel: $CHANNEL"
        exit 1
        ;;
esac

if [[ "$VERSION" =~ ^([0-9]{10})-slskdn\.([0-9]+)$ ]]; then
    WINGET_VERSION="${BASH_REMATCH[1]}.${BASH_REMATCH[2]}"
else
    WINGET_VERSION="$(echo "$VERSION" | sed 's/-/./g')"
fi
MANIFEST_DIR="packaging/winget"
INSTALLER_FILE="$MANIFEST_DIR/${FILE_BASENAME}.installer.yaml"
LOCALE_FILE="$MANIFEST_DIR/${FILE_BASENAME}.locale.en-US.yaml"
VERSION_FILE="$MANIFEST_DIR/${FILE_BASENAME}.yaml"
RELEASE_DATE="$(date -u +%Y-%m-%d)"

cat > "$INSTALLER_FILE" <<EOF
# yaml-language-server: \$schema=https://aka.ms/winget-manifest.installer.1.6.0.schema.json

PackageIdentifier: $PACKAGE_IDENTIFIER
PackageVersion: "$WINGET_VERSION"
InstallerType: zip
ReleaseDate: $RELEASE_DATE
NestedInstallerType: portable
NestedInstallerFiles:
- RelativeFilePath: slskd.exe
  PortableCommandAlias: $COMMAND_ALIAS
Commands:
- $COMMAND_ALIAS
Installers:
- Architecture: x64
  InstallerUrl: $WIN_X64_URL
  InstallerSha256: $WIN_X64_SHA
ManifestType: installer
ManifestVersion: 1.6.0
EOF

cat > "$LOCALE_FILE" <<EOF
# yaml-language-server: \$schema=https://aka.ms/winget-manifest.defaultLocale.1.6.0.schema.json

PackageIdentifier: $PACKAGE_IDENTIFIER
PackageVersion: "$WINGET_VERSION"
PackageLocale: en-US
Publisher: slskdN Team
PublisherUrl: https://github.com/snapetech
PublisherSupportUrl: https://github.com/snapetech-org/slskdN/issues
PackageName: $PACKAGE_NAME
PackageUrl: https://github.com/snapetech-org/slskdN
License: AGPL-3.0-or-later
LicenseUrl: https://github.com/snapetech-org/slskdN/blob/main/LICENSE
ShortDescription: $SHORT_DESCRIPTION
Description: |-
$(printf '%s\n' "$DESCRIPTION" | sed 's/^/  /')
Moniker: $MONIKER
Tags:
  - soulseek
  - p2p
  - music
  - filesharing
ReleaseNotes: |-
$(printf '%s\n' "$RELEASE_NOTES" | sed 's/^/  /')
ReleaseNotesUrl: $RELEASE_NOTES_URL
ManifestType: defaultLocale
ManifestVersion: 1.6.0
EOF

cat > "$VERSION_FILE" <<EOF
# yaml-language-server: \$schema=https://aka.ms/winget-manifest.version.1.6.0.schema.json

PackageIdentifier: $PACKAGE_IDENTIFIER
PackageVersion: "$WINGET_VERSION"
DefaultLocale: en-US
ManifestType: version
ManifestVersion: 1.6.0
EOF

echo "Updated Winget manifests for $CHANNEL:"
echo "  - $INSTALLER_FILE"
echo "  - $LOCALE_FILE"
echo "  - $VERSION_FILE"
