#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

release_tag="${1:-}"
version="${release_tag#v}"
if [[ ! "$version" =~ ^([0-9]{4})([0-9]{2})([0-9]{2})([0-9]{2})-slskdn\.[0-9]+$ ]]; then
    echo "Usage: $0 vYYYYMMDDHH-slskdn.N" >&2
    exit 1
fi

year="${BASH_REMATCH[1]}"
month_number="$((10#${BASH_REMATCH[2]}))"
day_hour="${BASH_REMATCH[3]}${BASH_REMATCH[4]}"
cloudron_version="${year}.${month_number}.${day_hour}"
image="docker.io/snapetech/slskdn:${version}"
stable_image_version_file="packaging/docker/stable-image-version"
manifest_file="packaging/cloudron/CloudronManifest.json"
versions_file="packaging/cloudron/CloudronVersions.json"
dockerfile="packaging/cloudron/Dockerfile"
created_at="$(date -u '+%a, %d %b %Y %H:%M:%S GMT')"

if jq -e --arg version "$cloudron_version" '.versions | has($version)' "$versions_file" >/dev/null; then
    existing_image="$(jq -er --arg version "$cloudron_version" '.versions[$version].manifest.dockerImage' "$versions_file")"
    current_version="$(jq -er '.version' "$manifest_file")"
    current_image="$(cat "$stable_image_version_file")"
    if [[ "$existing_image" == "$image" && "$current_version" == "$cloudron_version" && "$current_image" == "$version" ]]; then
        echo "Cloudron already tracks ${version}."
        exit 0
    fi

    echo "Cloudron version ${cloudron_version} already exists; immutable entries cannot be replaced." >&2
    exit 1
fi

temp_manifest="$(mktemp)"
temp_versions="$(mktemp)"
temp_dockerfile="$(mktemp)"
temp_image_version="$(mktemp)"
trap 'rm -f "$temp_manifest" "$temp_versions" "$temp_dockerfile" "$temp_image_version"' EXIT

jq --arg version "$cloudron_version" \
    --arg changelog "* Cloudron community package for slskdN ${version}." \
    '.version = $version | .changelog = $changelog' \
    "$manifest_file" > "$temp_manifest"

jq --arg version "$cloudron_version" \
    --arg created_at "$created_at" \
    --arg image "$image" \
    --slurpfile manifest "$temp_manifest" \
    '.versions[$version] = {creationDate: $created_at, manifest: ($manifest[0] + {dockerImage: $image}), publishState: "testing", ts: $created_at}' \
    "$versions_file" > "$temp_versions"

sed -E "1s#^FROM docker.io/snapetech/slskdn:.*\$#FROM ${image}#" "$dockerfile" > "$temp_dockerfile"
if [[ "$(head -n 1 "$temp_dockerfile")" != "FROM ${image}" ]]; then
    echo "Could not update the Cloudron Dockerfile image." >&2
    exit 1
fi
printf '%s\n' "$version" > "$temp_image_version"

mv "$temp_manifest" "$manifest_file"
mv "$temp_versions" "$versions_file"
mv "$temp_dockerfile" "$dockerfile"
mv "$temp_image_version" "$stable_image_version_file"

echo "Cloudron now tracks ${version} as ${cloudron_version}."
