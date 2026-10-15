#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

fail() {
    echo "ERROR: $1" >&2
    exit 1
}

fail_if_empty() {
    local value="$1"
    local label="$2"
    if [[ -z "$value" ]]; then
        fail "${label} is missing"
    fi
}

expect_line() {
    local file="$1"
    local pattern="$2"
    grep -Eq -- "$pattern" "$file" || fail "$file is missing pattern: $pattern"
}

expect_literal() {
    local file="$1"
    local pattern="$2"
    grep -Fq -- "$pattern" "$file" || fail "$file is missing literal: $pattern"
}

expect_literal_before() {
    local file="$1"
    local first="$2"
    local second="$3"
    local first_line
    local second_line
    first_line="$(grep -Fn -- "$first" "$file" | head -1 | cut -d: -f1 || true)"
    second_line="$(grep -Fn -- "$second" "$file" | head -1 | cut -d: -f1 || true)"
    [[ -n "$first_line" ]] || fail "$file is missing literal: $first"
    [[ -n "$second_line" ]] || fail "$file is missing literal: $second"
    (( first_line < second_line )) || fail "$file must place '$first' before '$second'"
}

reject_line() {
    local file="$1"
    local pattern="$2"
    if grep -Eq -- "$pattern" "$file"; then
        fail "$file contains forbidden pattern: $pattern"
    fi
}

reject_literal() {
    local file="$1"
    local pattern="$2"
    if grep -Fq -- "$pattern" "$file"; then
        fail "$file contains forbidden literal: $pattern"
    fi
}

extract_release_from_url() {
    local url="$1"
    printf '%s\n' "${url##*/releases/download/}" | sed 's#/.*##'
}

extract_release_from_formula() {
    local file="$1"
    awk '/^  version "/ {gsub(/"/, "", $2); print substr($2, 1); exit}' "$file"
}

extract_stable_linux_sha() {
    local file="$1"
    awk '
      /on_linux do/ {in_linux=1; next}
      in_linux && $1=="sha256" {gsub(/"/, "", $2); print $2; exit}
      in_linux && /^  end/ {in_linux=0}
    ' "$file"
}

expect_line flake.nix 'makeWrapper \$out/libexec/\$\{pname\}/slskd \$out/bin/slskd'
expect_line flake.nix 'ln -s slskd \$out/bin/\$\{pname\}'
expect_line flake.nix 'nativeBuildInputs = \[ pkgs\.unzip pkgs\.makeWrapper pkgs\.autoPatchelfHook pkgs\.patchelf \];'
expect_line flake.nix 'pkgs\.libunwind'
expect_line flake.nix 'pkgs\.lttng-ust\.out'
expect_line flake.nix 'dontStrip = true;'
expect_line flake.nix '--replace-needed liblttng-ust\.so\.0 liblttng-ust\.so\.1'
expect_line flake.nix 'pkgs\.util-linux'
reject_line flake.nix 'releases/download/dev/'
reject_literal flake.nix 'slskdn-dev'

test -x scripts/create-release-tag.sh || fail 'scripts/create-release-tag.sh must be executable'
expect_literal scripts/create-release-tag.sh 'bash packaging/scripts/run-release-gate.sh'
expect_literal scripts/create-release-tag.sh './scripts/verify-github-target.sh'
expect_literal scripts/create-release-tag.sh 'bash scripts/check-release-branch-sync.sh'
expect_literal scripts/create-release-tag.sh 'git status --porcelain'
expect_literal scripts/create-release-tag.sh 'git ls-remote --exit-code --tags origin "refs/tags/$tag"'
expect_literal scripts/create-release-tag.sh 'git push origin "$tag"'
expect_literal scripts/create-release-tag.sh '^build-(main|dev)-'
expect_literal package.json '"packageManager": "pnpm@12.4.1"'
expect_literal pnpm-workspace.yaml "- 'src/web'"
expect_literal pnpm-workspace.yaml "- 'tests/e2e'"
expect_literal bin/build 'pnpm install --frozen-lockfile'
expect_literal bin/watch 'pnpm --filter @slskdn/web start'
reject_literal bin/build 'npm ci --legacy-peer-deps'
reject_literal packaging/aur/PKGBUILD 'npm ci --legacy-peer-deps'
expect_literal packaging/aur/PKGBUILD "'nodejs' 'pnpm'"
for workflow in \
    .github/workflows/build-on-tag.yml \
    .github/workflows/ci-enhancements.yml \
    .github/workflows/ci.yml \
    .github/workflows/e2e-tests.yml \
    .github/workflows/release-copr.yml \
    .github/workflows/release-linux.yml \
    .github/workflows/release-ppa.yml \
    .github/workflows/windows-smoke.yml; do
    expect_line "$workflow" 'uses: pnpm/setup@[0-9a-f]{40}[[:space:]]+# v3'
    expect_literal "$workflow" 'install: false'
done
for workflow in \
    .github/workflows/build-on-tag.yml \
    .github/workflows/ci.yml \
    .github/workflows/e2e-tests.yml; do
    expect_literal "$workflow" 'sudo apt-get install -y jq ripgrep'
done
expect_literal packaging/scripts/run-release-gate.sh 'exec node scripts/validate-development.mjs'
expect_literal scripts/validation-engine/config.mjs "'.github/workflows/build-on-tag.yml'"
for task_id in \
    release-branch-sync \
    packaging-metadata \
    remediation-baseline \
    release-note-tests \
    engine-contract-tests \
    web-install \
    web-tests \
    backend-unit-tests \
    backend-regression-tests \
    backend-integration-smoke \
    web-build \
    bundle-budget \
    built-web-output \
    subpath-web-smoke; do
    expect_literal scripts/validation-engine/config.mjs "id: '$task_id'"
done
reject_literal packaging/scripts/run-release-gate.sh 'timeout --preserve-status'
# Validate the job-wide, fail-closed runner-temp setup instead of requiring a
# step-scoped TMPDIR value that cannot reach later build and test steps.
bash scripts/check-dotnet-runtime-matrix.sh
# Keep the evidence uploads limited to the same paths enforced by the YAML contract.
for workflow in .github/workflows/ci.yml .github/workflows/e2e-tests.yml .github/workflows/build-on-tag.yml; do
    expect_literal "$workflow" '${{ runner.temp }}/slskdn-validation-*/receipt.json'
    expect_literal "$workflow" '${{ runner.temp }}/slskdn-validation-*/*.log'
done
reject_literal .github/workflows/ci.yml 'path: /tmp/slskdn-validation-*/'
reject_literal .github/workflows/e2e-tests.yml 'path: /tmp/slskdn-validation-*/'
expect_literal scripts/verify-release-artifacts.sh 'SHA256SUMS.txt'
expect_literal scripts/verify-release-artifacts.sh 'vpn-agent/slskdN-vpn-agent'
expect_literal scripts/verify-release-artifacts.sh 'slskdn-footer-session-total'
expect_literal_before .github/workflows/build-on-tag.yml 'if [[ -n "${COPR_LOGIN:-}" && -n "${COPR_TOKEN:-}" ]]; then' 'elif [[ -n "${COPR_KERBEROS_PRINCIPAL:-}" && -n "${COPR_KERBEROS_KEYTAB_B64:-}" ]]; then'
expect_literal_before .github/workflows/build-on-tag.yml 'if [[ -n "${COPR_LOGIN:-}" && -n "${COPR_TOKEN:-}" ]]; then' 'elif [[ -n "${COPR_FEDORA_USERNAME:-}" && -n "${COPR_FEDORA_PASSWORD:-}" && -n "${COPR_FEDORA_OTP_SECRET:-}" ]]; then'
expect_literal_before .github/workflows/release-copr.yml 'if [[ -n "${COPR_LOGIN:-}" && -n "${COPR_TOKEN:-}" ]]; then' 'elif [[ -n "${COPR_KERBEROS_PRINCIPAL:-}" && -n "${COPR_KERBEROS_KEYTAB_B64:-}" ]]; then'
expect_literal_before .github/workflows/release-copr.yml 'if [[ -n "${COPR_LOGIN:-}" && -n "${COPR_TOKEN:-}" ]]; then' 'elif [[ -n "${COPR_FEDORA_USERNAME:-}" && -n "${COPR_FEDORA_PASSWORD:-}" && -n "${COPR_FEDORA_OTP_SECRET:-}" ]]; then'
expect_literal .github/workflows/build-on-tag.yml 'krb5-user krb5-k5tls krb5-pkinit libkrb5-dev oathtool'
expect_literal .github/workflows/release-copr.yml 'krb5-user krb5-k5tls krb5-pkinit libkrb5-dev oathtool'
expect_literal .github/workflows/build-on-tag.yml 'includedir /etc/krb5.conf.d/'
expect_literal .github/workflows/release-copr.yml 'includedir /etc/krb5.conf.d/'
expect_literal .github/workflows/build-on-tag.yml 'pkinit_anchors = FILE:/etc/pki/ipa/fedoraproject_ipa_ca.crt'
expect_literal .github/workflows/release-copr.yml 'pkinit_anchors = FILE:/etc/pki/ipa/fedoraproject_ipa_ca.crt'
expect_literal .github/workflows/build-on-tag.yml '.fedorainfracloud.org = FEDORAPROJECT.ORG'
expect_literal .github/workflows/release-copr.yml '.fedorainfracloud.org = FEDORAPROJECT.ORG'
expect_literal .github/workflows/build-on-tag.yml 'fedorainfracloud.org = FEDORAPROJECT.ORG'
expect_literal .github/workflows/release-copr.yml 'fedorainfracloud.org = FEDORAPROJECT.ORG'
expect_literal .github/workflows/build-on-tag.yml 'copr_url = https://copr.fedorainfracloud.org'
expect_literal .github/workflows/release-copr.yml 'copr_url = https://copr.fedorainfracloud.org'
reject_literal .github/workflows/build-on-tag.yml 'copr_url = https://copr.fedoraproject.org'
reject_literal .github/workflows/release-copr.yml 'copr_url = https://copr.fedoraproject.org'
expect_literal .github/workflows/build-on-tag.yml 'copr-cli rich requests-gssapi'
expect_literal .github/workflows/release-copr.yml 'copr-cli rich requests-gssapi'
expect_literal .github/workflows/release-copr.yml 'copr_project="slskdn/slskdn"'
expect_literal .github/workflows/build-on-tag.yml 'copr-cli --debug build "$copr_project" "$srpm" --nowait'
expect_literal .github/workflows/release-copr.yml 'copr-cli --debug build "$copr_project" "$srpm" --nowait'
expect_literal .github/workflows/build-on-tag.yml 'for attempt in 1 2 3; do'
expect_literal .github/workflows/release-copr.yml 'for attempt in 1 2 3; do'
reject_literal .github/workflows/release-copr.yml '"$SRPM"'
reject_literal .github/workflows/release-copr.yml 'copr-cli create slskdn'
reject_literal .github/workflows/release-copr.yml 'copr-cli modify slskdn'
reject_literal .github/workflows/release-copr.yml 'copr_args'
expect_literal docs/dev/release-checklist.md 'scripts/create-release-tag.sh'
expect_literal docs/build.md 'scripts/create-release-tag.sh'
expect_literal memory-bank/decisions/adr-0005-tagging-system.md 'scripts/create-release-tag.sh'
expect_literal memory-bank/QUICK_REFERENCE.md 'scripts/create-release-tag.sh'

CLOUDRON_VERSION="$(jq -er '.version' packaging/cloudron/CloudronManifest.json)"
CLOUDRON_CATALOG_VERSION="$(jq -er --arg version "$CLOUDRON_VERSION" '.versions[$version].manifest.version' packaging/cloudron/CloudronVersions.json)"
if [[ "$CLOUDRON_CATALOG_VERSION" != "$CLOUDRON_VERSION" ]]; then
  fail "Cloudron version catalog ${CLOUDRON_CATALOG_VERSION} does not match manifest ${CLOUDRON_VERSION}"
fi
CLOUDRON_IMAGE="$(jq -er --arg version "$CLOUDRON_VERSION" '.versions[$version].manifest.dockerImage' packaging/cloudron/CloudronVersions.json)"
CLOUDRON_STABLE_IMAGE_VERSION="$(cat packaging/docker/stable-image-version)"
if [[ ! "$CLOUDRON_STABLE_IMAGE_VERSION" =~ ^[0-9]{10}-slskdn\.[0-9]+$ ]]; then
  fail "Stable Docker image version ${CLOUDRON_STABLE_IMAGE_VERSION} is not a release tag"
fi
if [[ "$CLOUDRON_IMAGE" != "docker.io/snapetech/slskdn:${CLOUDRON_STABLE_IMAGE_VERSION}" ]]; then
  fail "Cloudron image ${CLOUDRON_IMAGE} does not match the last published stable Docker image ${CLOUDRON_STABLE_IMAGE_VERSION}"
fi
CLOUDRON_DOCKERFILE_IMAGE="$(awk '$1 == "FROM" { print $2; exit }' packaging/cloudron/Dockerfile)"
if [[ "$CLOUDRON_DOCKERFILE_IMAGE" != "$CLOUDRON_IMAGE" ]]; then
  fail "Cloudron Dockerfile image ${CLOUDRON_DOCKERFILE_IMAGE} does not match catalog image ${CLOUDRON_IMAGE}"
fi
if ! jq -e --arg version "$CLOUDRON_VERSION" '
  .versions[$version] as $entry
  | $entry.manifest as $manifest
  | ($entry.publishState == "testing")
    and ($manifest.minBoxVersion == "10.0.0")
    and ($manifest.addons.localstorage == {})
    and (($manifest.mediaLinks | length) > 0)
    and ($manifest.packagerName == "Snapetech")
    and ($manifest.packagerUrl == "https://github.com/snapetech")
' packaging/cloudron/CloudronVersions.json >/dev/null; then
  fail "Cloudron community metadata is incomplete or is not marked testing"
fi
CLOUDRON_MANIFEST_METADATA="$(jq -cS 'del(.dockerImage)' packaging/cloudron/CloudronManifest.json)"
CLOUDRON_CATALOG_METADATA="$(jq -cS --arg version "$CLOUDRON_VERSION" '.versions[$version].manifest | del(.dockerImage)' packaging/cloudron/CloudronVersions.json)"
if [[ "$CLOUDRON_MANIFEST_METADATA" != "$CLOUDRON_CATALOG_METADATA" ]]; then
  fail "CloudronVersions.json manifest does not match CloudronManifest.json"
fi
expect_literal packaging/cloudron/Dockerfile 'SLSKD_APP_DIR=/app/data'
expect_literal packaging/cloudron/Dockerfile 'SLSKD_DOWNLOADS_DIR=/app/data/downloads'
expect_literal packaging/cloudron/Dockerfile 'SLSKD_SHARED_DIR=/app/data/music'
expect_literal packaging/cloudron/Dockerfile 'mkdir -p \"$SLSKD_DOWNLOADS_DIR\" \"$SLSKD_SHARED_DIR\"'

reject_literal docs/build.md 'git tag build-main-'
reject_literal docs/dev/release-checklist.md 'git tag build-main-'
reject_literal memory-bank/decisions/adr-0005-tagging-system.md 'git tag "build-main-${VERSION}"'
reject_literal memory-bank/QUICK_REFERENCE.md 'git tag build-main-'

expect_line ca_profile.xml '^<CommunityApplications>$'
expect_line ca_profile.xml '<Profile>[^<[:space:]][^<]*</Profile>'
expect_literal ca_profile.xml '<Icon>https://github.com/snapetech/slskdN/raw/refs/heads/main/etc/icon.svg</Icon>'
expect_literal ca_profile.xml '<WebPage>https://github.com/snapetech/slskdN</WebPage>'
expect_literal packaging/unraid/slskdn.xml '<Repository>ghcr.io/snapetech/slskdn:latest</Repository>'
expect_literal packaging/unraid/slskdn.xml '<Registry>https://ghcr.io</Registry>'
reject_literal packaging/unraid/slskdn.xml '<Registry>https://github.com/'
expect_literal packaging/unraid/slskdn.xml '<Category>Downloaders: MediaApp:Music Status:Stable</Category>'
expect_literal packaging/unraid/slskdn.xml '<Icon>https://github.com/snapetech/slskdN/raw/refs/heads/main/etc/icon.svg</Icon>'
expect_literal packaging/unraid/slskdn.xml '<TemplateURL>https://github.com/snapetech/slskdN/raw/refs/heads/main/packaging/unraid/slskdn.xml</TemplateURL>'
expect_literal packaging/unraid/slskdn.xml '<ReadMe>https://github.com/snapetech/slskdN/blob/main/README.md</ReadMe>'
expect_literal packaging/unraid/slskdn.xml '<Config Name="Soulseek and Mesh TCP Port" Target="50300" Default="50300" Mode="tcp"'
expect_literal packaging/unraid/slskdn.xml '<Config Name="DHT, Mesh, and QUIC UDP Port" Target="50300" Default="50300" Mode="udp"'
reject_literal packaging/unraid/slskdn.xml '<Config Name="Mesh Overlay TCP Port"'
reject_literal packaging/unraid/slskdn.xml '<Config Name="DHT and Mesh UDP Port"'
reject_literal packaging/unraid/slskdn.xml '<Config Name="QUIC Data Overlay UDP Port"'
expect_literal packaging/unraid/slskdn.xml '<Config Name="SLSKD_REMOTE_CONFIGURATION" Target="SLSKD_REMOTE_CONFIGURATION" Default=""'
expect_literal packaging/unraid/slskdn.xml '<Config Name="SLSKD_SLSK_PROXY_PASSWORD" Target="SLSKD_SLSK_PROXY_PASSWORD" Default=""'
expect_literal packaging/unraid/slskdn.xml 'Target="/downloads" Default=""'
expect_literal packaging/unraid/slskdn.xml 'Target="/music" Default=""'
expect_literal packaging/unraid/slskdn.xml '<Config Name="SLSKD_SHARED_DIR" Target="SLSKD_SHARED_DIR" Default="/music"'
expect_literal packaging/unraid/slskdn.xml 'Target="SLSKD_PUSHBULLET_ACCESS_TOKEN"'
expect_literal packaging/unraid/slskdn.xml 'Target="SLSKD_PUSHBULLET_NOTIFICATION_PREFIX"'
expect_literal packaging/unraid/slskdn.xml 'Target="SLSKD_SLSK_PROXY_ENABLED"'
expect_literal packaging/unraid/slskdn.xml 'Target="SLSKD_SHARES_PROBE_MEDIA_ATTRIBUTES"'
expect_literal packaging/unraid/slskdn.xml 'Target="SLSKD_DOWNLOADS_DIR" Default="/downloads"'
expect_literal packaging/unraid/slskdn.xml 'Target="SLSKD_INCOMPLETE_DIR" Default="/app/incomplete"'
reject_literal packaging/unraid/slskdn.xml 'Target="SLSKD_INCOMPLETE_DIR" Default="/downloads/incomplete"'
reject_literal packaging/unraid/slskdn.xml 'Target="SLSKD_PUSHBULLET_TOKEN"'
reject_literal packaging/unraid/slskdn.xml 'Target="SLSKD_PUSHBULLET_PREFIX"'
reject_literal packaging/unraid/slskdn.xml 'Target="SLSKD_SLSK_PROXY"'
reject_literal packaging/unraid/slskdn.xml '<Networking>'
reject_literal packaging/unraid/slskdn.xml '<Data>'
reject_literal packaging/unraid/slskdn.xml '<Environment>'
reject_literal packaging/unraid/slskdn.xml 'https://raw.githubusercontent.com/slskd/slskd/'
reject_literal ca_profile.xml 'https://raw.githubusercontent.com/snapetech/slskdn'
reject_literal ca_profile.xml 'https://github.com/snapetech/slskdn'
reject_literal packaging/unraid/slskdn.xml 'https://raw.githubusercontent.com/snapetech/slskdn'
reject_literal packaging/unraid/slskdn.xml 'https://github.com/snapetech/slskdn'
reject_literal packaging/unraid/README.md 'https://raw.githubusercontent.com/snapetech/slskdn'
reject_literal packaging/unraid/README.md 'https://github.com/snapetech/slskdn'
reject_literal packaging/unraid/SUPPORT_POST.md 'https://raw.githubusercontent.com/snapetech/slskdn'
reject_literal packaging/unraid/SUPPORT_POST.md 'https://github.com/snapetech/slskdn'
expect_literal packaging/unraid/README.md 'https://forums.unraid.net/forum/71-docker-containers/'
expect_literal packaging/unraid/SUPPORT_POST.md 'Community feedback requested that Docker environment variables be exposed in the template'
reject_line packaging/unraid/SUPPORT_POST.md '^>'

while IFS= read -r env_name; do
  case "$env_name" in
    SLSKD_SCRIPT_DATA|SLSKD_SOME_OPTION) continue ;;
  esac
  expect_literal packaging/unraid/slskdn.xml "Target=\"$env_name\""
done < <(grep -oE 'SLSKD_[A-Z0-9_]+' docs/config.md | sort -u)

expect_line packaging/winget/snapetech.slskdn.yaml '^PackageIdentifier: snapetech\.slskdn$'
expect_line packaging/winget/snapetech.slskdn.installer.yaml '^PackageIdentifier: snapetech\.slskdn$'
expect_line packaging/winget/snapetech.slskdn.installer.yaml 'PortableCommandAlias: slskdn$'
expect_line packaging/winget/snapetech.slskdn.locale.en-US.yaml '^PackageIdentifier: snapetech\.slskdn$'
expect_line packaging/winget/snapetech.slskdn.locale.en-US.yaml '^Moniker: slskdn$'
expect_line packaging/winget/snapetech.slskdn.locale.en-US.yaml '^PackageName: slskdN$'

expect_line packaging/homebrew/Formula/slskdn.rb '^class Slskdn < Formula$'
expect_literal packaging/homebrew/README.md 'export SLSKD_HTTP_PORT=8080'
expect_literal packaging/homebrew/README.md 'export SLSKD_SLSK_LISTEN_PORT=2235'
expect_literal packaging/flatpak/README.md '--env=SLSKD_HTTP_PORT=8080'
reject_literal packaging/homebrew/README.md 'export SLSKD_LISTEN_PORT=8080'
reject_literal packaging/homebrew/README.md 'export SLSKD_SOULSEEK_LISTEN_PORT=2235'
reject_literal packaging/flatpak/README.md '--env=SLSKD_LISTEN_PORT=8080'

expect_literal packaging/helm/slskdn/values.yaml 'repository: ghcr.io/snapetech/slskdn'
expect_literal packaging/helm/slskdn/values.yaml 'SLSKD_SLSK_USERNAME: ""'
expect_literal packaging/helm/slskdn/values.yaml 'SLSKD_SLSK_PASSWORD: ""'
expect_literal packaging/helm/slskdn/values.yaml 'SLSKD_HTTP_PORT: "5030"'
expect_literal packaging/helm/slskdn/values.yaml 'SLSKD_SLSK_LISTEN_PORT: "2234"'
expect_literal packaging/helm/slskdn/values.yaml 'SLSKD_APP_DIR: "/app/config"'
expect_literal packaging/helm/slskdn/values.yaml 'DOTNET_BUNDLE_EXTRACT_BASE_DIR: "/tmp/.net"'
expect_literal packaging/helm/slskdn/values.yaml 'SLSKD_UMASK: "0007"'
expect_literal packaging/helm/slskdn/values.yaml 'automountServiceAccountToken: false'
expect_literal packaging/helm/slskdn/values.yaml 'readOnlyRootFilesystem: true'
expect_literal packaging/helm/slskdn/values.yaml 'readOnly: true'
expect_literal packaging/helm/slskdn/values.yaml 'type: RuntimeDefault'
expect_literal packaging/helm/slskdn/values.yaml 'drop:'
expect_literal packaging/helm/slskdn/values.yaml '      - ALL'
expect_literal packaging/helm/slskdn/values.yaml 'networkPolicy:'
expect_literal packaging/helm/slskdn/values.yaml '  enabled: false'
expect_literal packaging/helm/slskdn/templates/deployment.yaml 'mountPath: /tmp'
expect_literal packaging/helm/slskdn/templates/deployment.yaml 'mountPath: /run'
expect_literal packaging/helm/slskdn/templates/deployment.yaml 'readOnly: {{ .Values.persistence.shares.readOnly | default true }}'
expect_literal packaging/helm/slskdn/templates/networkpolicy.yaml 'kind: NetworkPolicy'
expect_literal packaging/helm/slskdn/templates/networkpolicy.yaml 'port: {{ .Values.env.SLSKD_SLSK_LISTEN_PORT | int }}'
reject_literal packaging/helm/slskdn/values.yaml 'repository: slskd/slskdn'
reject_literal packaging/helm/slskdn/values.yaml 'SLSKD_USERNAME: ""'
reject_literal packaging/helm/slskdn/values.yaml 'SLSKD_PASSWORD: ""'
reject_literal packaging/helm/slskdn/values.yaml 'SLSKD_LISTEN_PORT: "5030"'
reject_literal packaging/helm/slskdn/values.yaml 'SLSKD_SOULSEEK_NO_LISTEN_PORT: "false"'
reject_literal packaging/helm/slskdn/values.yaml 'SLSKD_SOULSEEK_LISTEN_PORT: "2234"'

expect_literal packaging/truenas-scale/charts/slskdn/values.yaml 'repository: ghcr.io/snapetech/slskdn'
expect_literal packaging/truenas-scale/charts/slskdn/values.yaml 'SLSKD_SLSK_USERNAME: ""'
expect_literal packaging/truenas-scale/charts/slskdn/values.yaml 'SLSKD_SLSK_PASSWORD: ""'
expect_literal packaging/truenas-scale/charts/slskdn/values.yaml 'SLSKD_HTTP_PORT: "5030"'
expect_literal packaging/truenas-scale/charts/slskdn/values.yaml 'SLSKD_SLSK_LISTEN_PORT: "2234"'
expect_literal packaging/truenas-scale/charts/slskdn/values.yaml 'SLSKD_APP_DIR: "/app/config"'
expect_literal packaging/truenas-scale/charts/slskdn/values.yaml 'DOTNET_BUNDLE_EXTRACT_BASE_DIR: "/tmp/.net"'
expect_literal packaging/truenas-scale/charts/slskdn/values.yaml 'SLSKD_UMASK: "0007"'
expect_literal packaging/truenas-scale/charts/slskdn/values.yaml 'type: RuntimeDefault'
expect_literal packaging/truenas-scale/charts/slskdn/values.yaml 'readOnly: true'
expect_literal packaging/truenas-scale/charts/slskdn/values.yaml 'drop:'
expect_literal packaging/truenas-scale/charts/slskdn/values.yaml '      - ALL'
expect_literal packaging/truenas-scale/charts/slskdn/templates/deployment.yaml 'readOnly: {{ .Values.persistence.shares.readOnly | default true }}'
expect_literal packaging/truenas-scale/charts/slskdn/questions.yaml 'variable: env/SLSKD_SLSK_USERNAME'
expect_literal packaging/truenas-scale/charts/slskdn/questions.yaml 'variable: env/SLSKD_SLSK_PASSWORD'
expect_literal packaging/truenas-scale/charts/slskdn/questions.yaml 'variable: env/SLSKD_HTTP_PORT'
expect_literal packaging/truenas-scale/charts/slskdn/questions.yaml 'variable: env/SLSKD_SLSK_LISTEN_PORT'
expect_literal packaging/truenas-scale/charts/slskdn/questions.yaml 'default: "ghcr.io/snapetech/slskdn"'
reject_literal packaging/truenas-scale/charts/slskdn/values.yaml 'repository: slskd/slskdn'
reject_literal packaging/truenas-scale/charts/slskdn/questions.yaml 'default: "slskd/slskdn"'
reject_literal packaging/truenas-scale/charts/slskdn/values.yaml 'SLSKD_USERNAME: ""'
reject_literal packaging/truenas-scale/charts/slskdn/values.yaml 'SLSKD_PASSWORD: ""'
reject_literal packaging/truenas-scale/charts/slskdn/values.yaml 'SLSKD_LISTEN_PORT: "5030"'
reject_literal packaging/truenas-scale/charts/slskdn/values.yaml 'SLSKD_SOULSEEK_NO_LISTEN_PORT: "false"'
reject_literal packaging/truenas-scale/charts/slskdn/values.yaml 'SLSKD_SOULSEEK_LISTEN_PORT: "2234"'

expect_line .github/workflows/release-packages.yml 'slskdn-main-linux-glibc-x64\.zip'
expect_literal .github/workflows/build-on-tag.yml 'cp packaging/linux/install-from-release.sh release/install-linux-release.sh'
expect_literal .github/workflows/build-on-tag.yml 'sha256sum *.zip slskd.service slskd.yml slskd.sysusers slskd.tmpfiles install-linux-release.sh > SHA256SUMS.txt'
expect_literal README.md '/releases/latest/download/install-linux-release.sh'
expect_literal README.md 'sudo bash install-linux-release.sh'
reject_literal README.md '0.24.5-slskdn.133'
expect_literal .github/workflows/build-on-tag.yml 'cp packaging/aur/slskd.service packaging/aur/slskd.yml packaging/aur/slskd.sysusers packaging/aur/slskd.tmpfiles release/'
expect_literal .github/workflows/build-on-tag.yml 'dotnet publish src/slskdN.VpnAgent/slskdN-vpn-agent.csproj'
expect_literal .github/workflows/build-on-tag.yml 'publish-${{ matrix.runtime }}/vpn-agent'
expect_literal .github/workflows/build-on-tag.yml 'cp src/slskdN.VpnAgent/windows-macos.md publish-${{ matrix.runtime }}/vpn-agent/windows-macos.md'
expect_literal .github/workflows/build-on-tag.yml 'cp src/slskdN.VpnAgent/GETTING_STARTED.md publish-${{ matrix.runtime }}/vpn-agent/GETTING_STARTED.md'
expect_literal .github/workflows/build-on-tag.yml 'cp src/slskdN.VpnAgent/manual-linux-wireguard.md publish-${{ matrix.runtime }}/vpn-agent/manual-linux-wireguard.md'
expect_literal .github/workflows/build-on-tag.yml 'cp src/slskdN.VpnAgent/external-tunnel.md publish-${{ matrix.runtime }}/vpn-agent/external-tunnel.md'
expect_literal .github/workflows/build-on-tag.yml 'cp src/slskdN.VpnAgent/api-contract.md publish-${{ matrix.runtime }}/vpn-agent/api-contract.md'
expect_literal .github/workflows/build-on-tag.yml 'cp docs/self-hosted-relay-tester-guide.md publish-${{ matrix.runtime }}/vpn-agent/self-hosted-relay-tester-guide.md'
expect_literal .github/workflows/release-linux.yml 'cp src/slskdN.VpnAgent/GETTING_STARTED.md publish-linux-${{ matrix.arch }}/vpn-agent/GETTING_STARTED.md'
expect_literal .github/workflows/release-ppa.yml 'cp src/slskdN.VpnAgent/GETTING_STARTED.md publish-linux-x64/vpn-agent/GETTING_STARTED.md'
expect_literal .github/workflows/release-copr.yml 'cp src/slskdN.VpnAgent/GETTING_STARTED.md publish-linux-x64/vpn-agent/GETTING_STARTED.md'
expect_literal .github/workflows/build-on-tag.yml 'cp src/slskdN.VpnAgent/self-hosted-relay.md publish-${{ matrix.runtime }}/vpn-agent/self-hosted-relay.md'
expect_literal .github/workflows/build-on-tag.yml 'cp -r src/slskdN.VpnAgent/systemd publish-${{ matrix.runtime }}/vpn-agent/'
expect_literal .github/workflows/build-on-tag.yml 'cp -r src/slskdN.VpnAgent/examples publish-${{ matrix.runtime }}/vpn-agent/'
expect_literal .github/workflows/build-on-tag.yml 'packaging/snap/snapcraft.yaml'
expect_literal .github/workflows/build-on-tag.yml 'cp ../packaging/aur/slskd.tmpfiles slskd.tmpfiles'
expect_literal .github/workflows/build-on-tag.yml 'cp packaging/aur/slskd.tmpfiles ~/rpmbuild/SOURCES/'
expect_literal .github/workflows/build-on-tag.yml 'cp packaging/aur/slskd.tmpfiles slskdn-${VERSION}/usr/lib/tmpfiles.d/slskd.conf'
expect_literal .github/workflows/build-on-tag.yml 'group: slskdn-ppa-jammy'
expect_literal .github/workflows/build-on-tag.yml 'scripts/wait-for-launchpad-ppa-publication.sh'
expect_literal .github/workflows/release-linux.yml 'cp ../packaging/aur/slskd.tmpfiles .'
expect_literal .github/workflows/release-ppa.yml 'mkdir -p "$SRC_DIR/usr/lib/tmpfiles.d"'
expect_literal .github/workflows/release-ppa.yml 'cp packaging/aur/slskd.tmpfiles "$SRC_DIR/usr/lib/tmpfiles.d/slskd.conf"'
expect_literal .github/workflows/release-ppa.yml 'sudo apt-get install -y devscripts debhelper gnupg build-essential patchelf'
expect_literal .github/workflows/release-ppa.yml 'dpkg-buildpackage -us -uc -b -d'
expect_literal .github/workflows/release-ppa.yml 'dotnet publish src/slskdN.VpnAgent/slskdN-vpn-agent.csproj'
expect_literal .github/workflows/release-ppa.yml 'publish-linux-x64/vpn-agent'
expect_literal .github/workflows/release-ppa.yml 'test -x publish-linux-x64/vpn-agent/slskdN-vpn-agent'
expect_literal .github/workflows/release-ppa.yml 'group: slskdn-ppa-${{ matrix.ubuntu_series }}'
expect_literal .github/workflows/release-ppa.yml 'scripts/wait-for-launchpad-ppa-publication.sh'
test -x scripts/wait-for-launchpad-ppa-publication.sh || fail 'scripts/wait-for-launchpad-ppa-publication.sh must be executable'
expect_literal .github/workflows/release-linux.yml 'dotnet publish src/slskdN.VpnAgent/slskdN-vpn-agent.csproj'
expect_literal .github/workflows/release-linux.yml 'publish-linux-${{ matrix.arch }}/vpn-agent'
expect_literal .github/workflows/release-linux.yml 'test -x publish-linux-${{ matrix.arch }}/vpn-agent/slskdN-vpn-agent'
expect_literal .github/workflows/release-copr.yml 'dotnet publish src/slskdN.VpnAgent/slskdN-vpn-agent.csproj'
expect_literal .github/workflows/release-copr.yml 'publish-linux-x64/vpn-agent'
expect_literal .github/workflows/release-copr.yml 'test -x publish-linux-x64/vpn-agent/slskdN-vpn-agent'
expect_literal packaging/homebrew/Formula/slskdn.rb 'slskdN-vpn-agent'
expect_literal packaging/scripts/update-stable-release-metadata.sh 'slskdN-vpn-agent'
expect_literal packaging/chocolatey/tools/chocolateyinstall.ps1 'Install-BinFile -Name "slskdN-vpn-agent"'

expect_line .github/workflows/release-packages.yml '\$\{\{ steps\.version\.outputs\.tag \}\}-linux-x64\.zip'

expect_literal Dockerfile 'gosu'
expect_literal Dockerfile 'ffmpeg'
expect_literal Dockerfile 'libchromaprint-tools'
expect_literal Dockerfile 'COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./'
expect_literal Dockerfile 'COPY tests/e2e/package.json tests/e2e/package.json'
expect_literal Dockerfile 'require("./package.json").packageManager'
expect_literal Dockerfile 'npm install --global'
expect_literal Dockerfile 'ARG LIBMSQUIC_VERSION=2.4.18'
expect_literal Dockerfile 'libmsquic_${LIBMSQUIC_VERSION}_${deb_arch}.deb'
expect_literal Dockerfile 'packages.microsoft.com/ubuntu/24.04/prod/pool/main/libm/libmsquic'
expect_literal Dockerfile 'yt-dlp'
expect_literal Dockerfile 'COPY packaging/docker/slskdn-container-start /usr/local/bin/slskdn-container-start'
expect_literal Dockerfile 'COPY packaging/docker/install-optional-media-tools /usr/local/bin/install-optional-media-tools'
expect_literal Dockerfile 'COPY src/slskdN.VpnAgent src/slskdN.VpnAgent/.'
expect_literal Dockerfile 'SLSKD_DOCKER_REVISION=$REVISION'
expect_literal packaging/docker/Dockerfile.experimental-media 'ARG BASE_IMAGE=ghcr.io/snapetech/slskdn:latest'
expect_literal packaging/docker/Dockerfile.experimental-media 'FROM ${BASE_IMAGE}'
expect_literal packaging/docker/Dockerfile.experimental-media 'openjdk-21-jre-headless'
expect_literal packaging/docker/Dockerfile.experimental-media 'build-essential'
expect_literal packaging/docker/Dockerfile.experimental-media 'cargo'
expect_literal packaging/docker/Dockerfile.experimental-media 'python3-venv'
expect_literal packaging/docker/Dockerfile.experimental-media 'tesseract-ocr'
expect_literal packaging/docker/Dockerfile.experimental-media 'find / -xdev -type f \( -perm -4000 -o -perm -2000 \) -exec chmod a-s {} +'
expect_literal packaging/docker/install-optional-media-tools 'install-optional-media-tools [profile ...]'
expect_literal packaging/docker/install-optional-media-tools 'libclang-dev'
expect_literal packaging/docker/install-optional-media-tools 'SLSKDN_PIP_PACKAGES'
expect_literal packaging/docker/install-optional-media-tools 'SLSKDN_SONGREC_CRATE_VERSION'
expect_literal packaging/docker/install-optional-media-tools 'SLSKDN_RUST_TOOLCHAIN'
expect_literal packaging/docker/install-optional-media-tools 'PANAKO_JAR_URL'
expect_literal packaging/docker/install-optional-media-tools 'PANAKO_REPO'
expect_literal docs/docker.md 'install-optional-media-tools all'
expect_literal packaging/docker/slskdn-container-start 'exec gosu slskdn "$@"'
expect_literal packaging/docker/slskdn-container-start 'SLSKD_STRICT_APP_DIR_PERMISSIONS'
expect_literal packaging/docker/slskdn-container-start 'writable by others'
expect_literal packaging/synology-spk/build-spk.sh 'dotnet publish "$REPO_ROOT/src/slskd/slskd.csproj"'
expect_literal packaging/synology-spk/build-spk.sh 'SLSKDN_SPK_PUBLISH_DIR'
expect_literal packaging/synology-spk/build-spk.sh 'SPK package payload is missing executable slskd binary.'
expect_literal packaging/synology-spk/scripts/postinst './slskd --config /var/packages/slskdn/shares/slskdn/config/slskd.yml'
expect_literal packaging/synology-spk/README.md 'The builder publishes the real `slskd` application binary into `package.tgz`.'
expect_literal docs/docker.md 'Dockerfile.experimental-media'
expect_literal docs/docker.md 'install-optional-media-tools'
expect_literal src/slskd/SongID/SongIdCapabilities.cs 'DockerOptionalMediaHint'
expect_literal docs/docker.md '--security-opt apparmor=slskdn-docker'
expect_literal docs/docker.md 'SLSKD_STRICT_APP_DIR_PERMISSIONS=true'
expect_literal docs/docker.md 'run-docker-apparmor-smoke.sh'
expect_literal packaging/scripts/run-docker-apparmor-smoke.sh '--security-opt apparmor=slskdn-docker'
expect_literal packaging/scripts/run-docker-apparmor-smoke.sh 'Docker daemon is not advertising AppArmor support'
expect_literal packaging/scripts/run-docker-apparmor-smoke.sh 'headless Chromium'
expect_literal packaging/docker/apparmor/slskdn-docker 'profile slskdn-docker'
expect_literal packaging/docker/apparmor/slskdn-docker 'deny mount,'
expect_literal packaging/docker/apparmor/slskdn-docker '/shares/** r,'
expect_literal packaging/docker/apparmor/slskdn-docker '/downloads/** rwkl,'
expect_literal packaging/docker/apparmor/slskdn-docker '/app/** rwkl,'
reject_literal Dockerfile 'groupadd --gid 1000'
reject_literal Dockerfile 'useradd --uid 1000'
reject_literal Dockerfile 'SLSKD_DOCKER_REVISON'
reject_literal Dockerfile 'VOLUME /app'
reject_literal packaging/synology-spk/build-spk.sh 'placeholder binary'
reject_literal packaging/synology-spk/build-spk.sh 'This is a placeholder binary for the SPK package'
test -x packaging/docker/slskdn-container-start || fail 'packaging/docker/slskdn-container-start must be executable'
test -x packaging/scripts/run-docker-apparmor-smoke.sh || fail 'packaging/scripts/run-docker-apparmor-smoke.sh must be executable'
test -f packaging/docker/apparmor/slskdn-docker || fail 'packaging/docker/apparmor/slskdn-docker is missing'

sdk_minimum_version=$(awk -F '"' '/"version"/ { print $4; exit }' global.json)
fail_if_empty "$sdk_minimum_version" 'global.json SDK minimum version'
git ls-files --error-unmatch global.json >/dev/null 2>&1 || fail 'global.json must be tracked so source builds and release checks share the declared .NET SDK floor'
sdk_major="${sdk_minimum_version%%.*}"
ci_sdk_version=$(awk -F "'" '/DOTNET_VERSION:/ { print $2; exit }' .github/workflows/ci.yml)
if [[ ! "$ci_sdk_version" =~ ^${sdk_major}\.0\.[0-9]+$ ]]; then
  fail "CI SDK pin must be a stable .NET ${sdk_major}.0 SDK version"
fi
expect_literal .github/workflows/build-on-tag.yml "DOTNET_VERSION: '${ci_sdk_version}'"
expect_literal .github/workflows/ci-enhancements.yml "DOTNET_VERSION: '${ci_sdk_version}'"
expect_literal .github/workflows/e2e-tests.yml "DOTNET_VERSION: '${ci_sdk_version}'"
expect_literal .github/workflows/codeql.yml "DOTNET_VERSION: '${ci_sdk_version}'"
expect_literal .github/workflows/release-linux.yml "dotnet-version: '${ci_sdk_version}'"
expect_literal .github/workflows/release-copr.yml "dotnet-version: '${ci_sdk_version}'"
expect_literal .github/workflows/release-ppa.yml "dotnet-version: '${ci_sdk_version}'"
reject_literal .github/workflows/build-on-tag.yml "DOTNET_VERSION: '10'"
reject_literal .github/workflows/build-on-tag.yml 'dotnet-version: 10.0.x'
reject_literal .github/workflows/release-linux.yml 'dotnet-version: 10.0.x'
reject_literal .github/workflows/release-copr.yml 'dotnet-version: 10.0.x'
reject_literal .github/workflows/release-ppa.yml 'dotnet-version: 10.0.x'

expect_line packaging/aur/PKGBUILD '^source=\($'
expect_literal packaging/aur/PKGBUILD-bin '"slskdn-${pkgver}-main-linux-glibc-x64.zip::https://github.com/snapetech/slskdn/releases/download/${pkgver//.slskdn/-slskdn}/slskdn-main-linux-glibc-x64.zip"'
expect_literal packaging/aur/PKGBUILD-bin 'noextract=("slskdn-${pkgver}-main-linux-glibc-x64.zip")'
expect_line packaging/aur/PKGBUILD-bin '^install=slskd\.install$'
expect_line packaging/aur/PKGBUILD '^install=slskd\.install$'
expect_line packaging/aur/slskd.service '^ExecStart=/usr/lib/slskd/slskd --config /etc/slskd/slskd\.yml$'
expect_line packaging/aur/slskd.service '^UMask=0002$'
expect_line packaging/aur/slskd.tmpfiles '^d /var/lib/slskd 0775 slskd slskd -$'
expect_line packaging/aur/slskd.tmpfiles '^z /etc/slskd/slskd\.yml 0664 slskd slskd -$'
expect_literal packaging/aur/slskd.install 'systemd-tmpfiles --create /usr/lib/tmpfiles.d/slskd.conf'
expect_literal packaging/aur/slskd.install 'install -d -m 0755 /var/lib/slskdN-vpn'
expect_literal packaging/aur/slskd.install '/etc/slskd/slskd.yml.pacnew'
expect_literal packaging/aur/README.md 'sudo diff -u /etc/slskd/slskd.yml /etc/slskd/slskd.yml.pacnew'
expect_literal packaging/aur/PKGBUILD 'install -dm775 "${pkgdir}/var/lib/${_pkgname}"'
expect_literal packaging/aur/PKGBUILD 'install -dm775 "${pkgdir}/var/lib/${_pkgname}/downloads"'
expect_literal packaging/aur/PKGBUILD 'install -dm775 "${pkgdir}/var/lib/${_pkgname}/incomplete"'
expect_literal packaging/aur/PKGBUILD-bin 'install -dm775 "${pkgdir}/var/lib/${_pkgname}"'
expect_literal packaging/aur/PKGBUILD-bin 'install -dm775 "${pkgdir}/var/lib/${_pkgname}/downloads"'
expect_literal packaging/aur/PKGBUILD-bin 'install -dm775 "${pkgdir}/var/lib/${_pkgname}/incomplete"'
expect_literal packaging/debian/postinst 'install -dm775 -o slskd -g slskd /var/lib/slskd'
expect_literal packaging/debian/postinst 'install -dm775 -o slskd -g slskd /var/lib/slskd/downloads'
expect_literal packaging/debian/postinst 'install -dm775 -o slskd -g slskd /var/lib/slskd/incomplete'
expect_literal packaging/rpm/slskdn.spec 'install -dm775 %{buildroot}%{_sharedstatedir}/slskd'
expect_literal packaging/rpm/slskdn.spec 'install -dm775 %{buildroot}%{_sharedstatedir}/slskd/downloads'
expect_literal packaging/rpm/slskdn.spec 'install -dm775 %{buildroot}%{_sharedstatedir}/slskd/incomplete'
expect_literal packaging/rpm/slskdn.spec '%dir %attr(0775,slskd,slskd) %{_sharedstatedir}/slskd'
expect_literal packaging/rpm/slskdn.spec '%dir %attr(0775,slskd,slskd) %{_sharedstatedir}/slskd/downloads'
expect_literal packaging/rpm/slskdn.spec '%dir %attr(0775,slskd,slskd) %{_sharedstatedir}/slskd/incomplete'
expect_literal packaging/aur/PKGBUILD '_archive_root="slskdN-${pkgver//.slskdn/-slskdn}"'
expect_literal packaging/aur/PKGBUILD 'cd "${srcdir}/${_archive_root}"'
reject_literal packaging/aur/PKGBUILD 'cd "${srcdir}/slskdn-${pkgver//.slskdn/-slskdn}"'
expect_literal packaging/aur/PKGBUILD-bin 'local release_root="${app_root}/releases/${pkgver}"'
expect_literal packaging/aur/PKGBUILD-bin 'local archive="${srcdir}/slskdn-${pkgver}-main-linux-glibc-x64.zip"'
expect_literal packaging/aur/PKGBUILD-bin 'unzip -q "${archive}" -d "${stage_root}"'
expect_literal packaging/aur/PKGBUILD-bin 'Microsoft.AspNetCore.Diagnostics.Abstractions.dll'
expect_literal packaging/aur/PKGBUILD-bin 'install -Dm644 "${srcdir}/slskd.tmpfiles" "${pkgdir}/usr/lib/tmpfiles.d/${_pkgname}.conf"'
expect_literal packaging/aur/PKGBUILD-bin 'chmod -R u=rwX,go=rX "${release_root}"'
expect_literal packaging/aur/PKGBUILD-bin 'chmod 755 "${release_root}/slskd"'
expect_literal packaging/aur/PKGBUILD-bin 'exec /usr/lib/slskd/current/slskd "$@"'
expect_literal packaging/aur/PKGBUILD 'dotnet publish src/slskdN.VpnAgent/slskdN-vpn-agent.csproj'
expect_literal packaging/aur/PKGBUILD 'install -Dm755 "publish-vpn-agent/slskdN-vpn-agent" "${pkgdir}/usr/bin/slskdN-vpn-agent"'
expect_literal packaging/aur/PKGBUILD-bin 'install -Dm755 "${stage_root}/vpn-agent/slskdN-vpn-agent" "${pkgdir}/usr/bin/slskdN-vpn-agent"'
expect_literal packaging/aur/PKGBUILD 'install_vpn_unit "src/slskdN.VpnAgent/systemd/slskdN-vpn-ingress.service" "${pkgdir}/usr/lib/systemd/system/slskdN-vpn-ingress.service"'
expect_literal packaging/aur/PKGBUILD-bin 'install_vpn_unit "${stage_root}/vpn-agent/systemd/slskdN-vpn-ingress.service" "${pkgdir}/usr/lib/systemd/system/slskdN-vpn-ingress.service"'
expect_literal packaging/aur/PKGBUILD 'Environment=SLSKDN_CONFIG=/etc/slskd/slskd.yml'
expect_literal packaging/aur/PKGBUILD 'Environment=SLSKDN_SERVICE_NAME=slskd'
expect_literal packaging/aur/PKGBUILD 's#/usr/local/bin/slskdN-vpn-agent#/usr/bin/slskdN-vpn-agent#g'
expect_literal packaging/aur/PKGBUILD 's#slskdN\.service#slskd.service#g'
expect_literal src/slskdN.VpnAgent/systemd/slskdN-vpn-watchdog.service 'TimeoutStartSec=45s'
expect_literal src/slskdN.VpnAgent/systemd/slskdN-relay.service 'ExecStartPre=/usr/local/bin/slskdN-vpn-agent relay-apply'
expect_literal src/slskdN.VpnAgent/systemd/slskdN-relay.service 'ExecStart=/usr/local/bin/slskdN-vpn-agent relay-api'
expect_literal src/slskdN.VpnAgent/compose.relay.yml 'network_mode: host'
expect_literal src/slskdN.VpnAgent/compose.relay.yml 'NET_ADMIN'
expect_literal src/slskdN.VpnAgent/self-hosted-relay.md 'The VPS contains no slskdN API key'
expect_literal packaging/aur/PKGBUILD-bin 'Environment=SLSKDN_CONFIG=/etc/slskd/slskd.yml'
expect_literal packaging/aur/PKGBUILD-bin 'Environment=SLSKDN_SERVICE_NAME=slskd'
expect_literal packaging/aur/PKGBUILD-bin 's#/usr/local/bin/slskdN-vpn-agent#/usr/bin/slskdN-vpn-agent#g'
expect_literal packaging/aur/PKGBUILD-bin 's#slskdN\.service#slskd.service#g'
expect_literal packaging/debian/rules 'Environment=SLSKDN_CONFIG=/etc/slskd/slskd.yml'
expect_literal packaging/debian/rules 's#/usr/local/bin/slskdN-vpn-agent#/usr/bin/slskdN-vpn-agent#g'
expect_literal packaging/debian/rules 's#slskdN\.service#slskd.service#g'
reject_literal packaging/debian/rules 'slskdN-vpn-{split,ingress,gluetun-compat,watchdog}.service'
expect_literal packaging/debian/rules 'debian/slskdn/lib/systemd/system/slskdN-vpn-split.service \'
expect_literal packaging/debian/rules 'debian/slskdn/lib/systemd/system/slskdN-vpn-watchdog.service; do \'
expect_literal packaging/rpm/slskdn.spec 'Environment=SLSKDN_CONFIG=/etc/slskd/slskd.yml'
expect_literal packaging/rpm/slskdn.spec 's#/usr/local/bin/slskdN-vpn-agent#/usr/bin/slskdN-vpn-agent#g'
expect_literal packaging/rpm/slskdn.spec 's#slskdN\.service#slskd.service#g'
expect_literal packaging/aur/PKGBUILD 'local release_root="${app_root}/releases/${pkgver}"'
expect_literal packaging/aur/PKGBUILD '_dotnet_version="0.0.0-slskdn.${BASH_REMATCH[1]}.${BASH_REMATCH[2]}"'
expect_literal packaging/aur/PKGBUILD '-p:Version="$_dotnet_version"'
expect_literal packaging/aur/PKGBUILD '-p:PackageVersion="$_dotnet_version"'
expect_literal packaging/aur/PKGBUILD '-p:AllowMissingPrunePackageData=true'
expect_literal bin/publish '-p:AllowMissingPrunePackageData=true'
expect_literal packaging/aur/PKGBUILD 'install -Dm644 "${srcdir}/slskd.tmpfiles" "${pkgdir}/usr/lib/tmpfiles.d/${_pkgname}.conf"'
expect_literal .github/workflows/release-linux.yml "sha256sums=('SKIP' '\$SVC_SUM' '\$YML_SUM' '\$SYS_SUM' '\$TMP_SUM')"
expect_literal .github/workflows/release-linux.yml 'bash ../scripts/validate-aur-pkgbuild-hashes.sh PKGBUILD PKGBUILD-bin'
expect_literal .github/workflows/release-packages.yml 'cp packaging/aur/slskd.tmpfiles pkg/usr/lib/tmpfiles.d/slskd.conf'
expect_literal .github/workflows/release-packages.yml 'cp packaging/aur/slskd.tmpfiles ~/rpmbuild/SOURCES/'
expect_literal .github/workflows/release-copr.yml 'cp packaging/aur/slskd.tmpfiles ~/rpmbuild/SOURCES/'
reject_literal packaging/aur/PKGBUILD '_assembly_ver="${pkgver%.slskdn.*}.${pkgver##*.}"'
reject_literal packaging/aur/PKGBUILD '-p:Version="$_assembly_ver"'
expect_literal packaging/aur/PKGBUILD 'chmod -R u=rwX,go=rX "${release_root}"'
expect_literal packaging/aur/PKGBUILD 'chmod 755 "${release_root}/slskd"'
expect_literal packaging/aur/PKGBUILD 'exec /usr/lib/slskd/current/slskd "$@"'
expect_literal packaging/linux/install-from-release.sh 'install_vpn_agent_payload'
expect_literal packaging/linux/install-from-release.sh '/usr/local/bin/slskdN-vpn-agent'
expect_literal packaging/linux/install-from-release.sh 'resolve_dotnet_apt_source'
expect_literal packaging/linux/install-from-release.sh 'UBUNTU_CODENAME'
expect_literal packaging/linux/install-from-release.sh 'packages.microsoft.com/linuxmint/'
expect_literal packaging/debian/rules 'install -Dm755 usr/lib/slskd/vpn-agent/slskdN-vpn-agent debian/slskdn/usr/bin/slskdN-vpn-agent'
expect_literal packaging/rpm/slskdn.spec 'install -Dm755 %{buildroot}%{slskd_appdir}/vpn-agent/slskdN-vpn-agent %{buildroot}%{_bindir}/slskdN-vpn-agent'
test -f packaging/aur/slskd.install || fail 'packaging/aur/slskd.install is missing'
reject_line packaging/aur/PKGBUILD-bin 'slskdn-\$\{pkgver\}-linux-x64\.zip::https://github\.com/snapetech/slskdn/releases/download/\${pkgver//\.slskdn/-slskdn}/slskdn-\$\{pkgver\}-linux-x64\.zip'

bash packaging/scripts/validate-release-copy.sh

STABLE_FORMULA_VERSION=$(extract_release_from_formula Formula/slskdn.rb)
fail_if_empty "$STABLE_FORMULA_VERSION" "Stable Formula version"

STABLE_FORMULA_LINUX_SHA=$(extract_stable_linux_sha Formula/slskdn.rb)
fail_if_empty "$STABLE_FORMULA_LINUX_SHA" "Stable Formula Linux SHA"

HOMEBREW_VERSION=$(sed -n 's#^  version "\([^"]*\)"#\1#p' packaging/homebrew/Formula/slskdn.rb | head -n 1)
fail_if_empty "$HOMEBREW_VERSION" "Homebrew version"
if [[ "$HOMEBREW_VERSION" != "$STABLE_FORMULA_VERSION" ]]; then
  fail "Homebrew formula version ${HOMEBREW_VERSION} does not match stable Formula version ${STABLE_FORMULA_VERSION}"
fi

HOME_URL_VERSIONS_COUNT=0
while IFS= read -r homebrew_release; do
  ((HOME_URL_VERSIONS_COUNT += 1))
  if [[ "$homebrew_release" != "$STABLE_FORMULA_VERSION" ]]; then
    fail "Homebrew formula URL release (${homebrew_release}) does not match version ${HOMEBREW_VERSION}"
  fi
done < <(sed -n "s#.*releases/download/\([^/]*\)/.*#\1#p" packaging/homebrew/Formula/slskdn.rb | grep -v '^$')

if [[ "$HOME_URL_VERSIONS_COUNT" -ne 3 ]]; then
  fail "Homebrew formula should have exactly 3 release URLs, found $HOME_URL_VERSIONS_COUNT"
fi

FLATPAK_URL=$(sed -n "s#^[[:space:]]*url: \\(.*\\)#\\1#p" packaging/flatpak/io.github.slskd.slskdn.yml | grep '/releases/download/' | head -n 1)
if [[ -z "$FLATPAK_URL" ]]; then
  fail "Could not extract Flatpak release URL"
fi
FLATPAK_RELEASE=$(extract_release_from_url "$FLATPAK_URL")
if [[ "$FLATPAK_RELEASE" != "$STABLE_FORMULA_VERSION" ]]; then
  fail "Flatpak release ${FLATPAK_RELEASE} does not match stable Formula version ${STABLE_FORMULA_VERSION}"
fi
if ! grep -q "sha256: ${STABLE_FORMULA_LINUX_SHA}" packaging/flatpak/io.github.slskd.slskdn.yml; then
  fail "Flatpak source SHA should match stable Linux SHA ${STABLE_FORMULA_LINUX_SHA}"
fi

TRUENAS_CHART_VERSION=$(sed -n 's/^appVersion: "\(.*\)"$/\1/p' packaging/truenas-scale/charts/slskdn/Chart.yaml)
fail_if_empty "$TRUENAS_CHART_VERSION" "TrueNAS appVersion"
if [[ "$TRUENAS_CHART_VERSION" != "$STABLE_FORMULA_VERSION" ]]; then
  fail "TrueNAS chart appVersion ${TRUENAS_CHART_VERSION} does not match stable Formula version ${STABLE_FORMULA_VERSION}"
fi

HELM_CHART_VERSION=$(sed -n 's/^appVersion: "\(.*\)"$/\1/p' packaging/helm/slskdn/Chart.yaml)
fail_if_empty "$HELM_CHART_VERSION" "Helm appVersion"
if [[ "$HELM_CHART_VERSION" != "$STABLE_FORMULA_VERSION" ]]; then
  fail "Helm chart appVersion ${HELM_CHART_VERSION} does not match stable Formula version ${STABLE_FORMULA_VERSION}"
fi

SNAP_VERSION=$(sed -n "s/^version: '\(.*\)'$/\1/p" packaging/snap/snapcraft.yaml)
fail_if_empty "$SNAP_VERSION" "Snap version"
if [[ "$SNAP_VERSION" != "$STABLE_FORMULA_VERSION" ]]; then
  fail "Snap version ${SNAP_VERSION} does not match stable Formula version ${STABLE_FORMULA_VERSION}"
fi

SNAP_SOURCE=$(sed -n 's#^[[:space:]]*source: \(.*\)#\1#p' packaging/snap/snapcraft.yaml | head -n 1)
fail_if_empty "$SNAP_SOURCE" "Snap source"
SNAP_RELEASE=$(extract_release_from_url "$SNAP_SOURCE")
if [[ "$SNAP_RELEASE" != "$STABLE_FORMULA_VERSION" ]]; then
  fail "Snap source release ${SNAP_RELEASE} does not match stable Formula version ${STABLE_FORMULA_VERSION}"
fi
expect_literal packaging/snap/snapcraft.yaml "source-checksum: sha256/${STABLE_FORMULA_LINUX_SHA}"

validate_winget() {
    local installer_file="$1"
    local locale_file="$2"

    local manifest_version
    manifest_version=$(sed -n 's/^PackageVersion: \(.*\)/\1/p' "$installer_file" | head -n1)
    fail_if_empty "$manifest_version" "Winget PackageVersion in ${installer_file}"

    local installer_url
    installer_url=$(sed -n 's/^ *InstallerUrl: \(.*\)/\1/p' "$installer_file" | head -n1)
    fail_if_empty "$installer_url" "Winget InstallerUrl in ${installer_file}"

    local expected_release_tag="${manifest_version/.slskdn./-slskdn.}"

    if [[ "$installer_url" != *"${expected_release_tag}"* ]]; then
        fail "Winget manifest ${installer_file} url does not match release tag ${expected_release_tag}"
    fi

    if [[ -f "$locale_file" ]]; then
        local release_notes_url
        release_notes_url=$(sed -n 's/^ReleaseNotesUrl: \(.*\)/\1/p' "$locale_file" | head -n1)
        if [[ -n "$release_notes_url" && "$release_notes_url" != *"${expected_release_tag}"* ]]; then
            fail "Winget manifest ${locale_file} release notes url does not match release tag ${expected_release_tag}"
        fi
    fi
}

if [[ "${VALIDATE_WINGET_RELEASE_METADATA:-false}" == "true" ]]; then
  validate_winget packaging/winget/snapetech.slskdn.installer.yaml packaging/winget/snapetech.slskdn.locale.en-US.yaml

  WINGET_STABLE_VERSION=$(sed -n 's/^PackageVersion: \(.*\)$/\1/p' packaging/winget/snapetech.slskdn.installer.yaml | head -n1)
  if [[ "${WINGET_STABLE_VERSION/.slskdn./-slskdn.}" != "$STABLE_FORMULA_VERSION" ]]; then
    fail "Winget stable PackageVersion ${WINGET_STABLE_VERSION} does not match stable Formula version ${STABLE_FORMULA_VERSION}"
  fi
else
  echo "Skipping Winget release-version metadata validation; set VALIDATE_WINGET_RELEASE_METADATA=true to enforce it."
fi

CHOC_VERSION=$(sed -n 's#.*<version>\(.*\)</version>#\1#p' packaging/chocolatey/slskdn.nuspec | head -n 1)
if [[ -z "${CHOC_VERSION}" ]]; then
  fail "Could not extract Chocolatey version from packaging/chocolatey/slskdn.nuspec"
fi
expect_literal .github/workflows/build-on-tag.yml '$PackageVersion = "$($Matches[1]).0.0.$($Matches[2])"'
expect_literal .github/workflows/publish-chocolatey.yml '$PackageVersion = "$($Matches[1]).0.0.$($Matches[2])"'
reject_literal .github/workflows/build-on-tag.yml '$1.0.0-slskdn.$2'
reject_literal .github/workflows/publish-chocolatey.yml '$1.0.0-slskdn.$2'
expect_literal .github/workflows/build-on-tag.yml 'Invoke-WebRequest -Uri $packageEndpoint -Method Head'
expect_literal .github/workflows/publish-chocolatey.yml 'Invoke-WebRequest -Uri $packageEndpoint -Method Head'
if [[ "$CHOC_VERSION" != "$STABLE_FORMULA_VERSION" ]]; then
  fail "Chocolatey version ${CHOC_VERSION} does not match stable Formula version ${STABLE_FORMULA_VERSION}"
fi

CHOC_URL=$(sed -n 's#^\$url[[:space:]]*= "\([^"]*\)"#\1#p' packaging/chocolatey/tools/chocolateyinstall.ps1 | head -n 1)
if [[ -z "$CHOC_URL" ]]; then
  fail "Could not extract Chocolatey URL"
fi
CHOC_RELEASE=$(extract_release_from_url "$CHOC_URL")
if [[ "$CHOC_RELEASE" != "$STABLE_FORMULA_VERSION" ]]; then
  fail "Chocolatey installer URL release ${CHOC_RELEASE} does not match stable Formula version ${STABLE_FORMULA_VERSION}"
fi

if [[ "$CHOC_URL" != "https://github.com/snapetech/slskdn/releases/download/${CHOC_VERSION}/slskdn-main-win-x64.zip" ]]; then
  fail "Chocolatey installer URL must match version ${CHOC_VERSION}"
fi

expect_literal packaging/chocolatey/slskdn.nuspec "<version>${CHOC_VERSION}</version>"
expect_literal packaging/chocolatey/tools/chocolateyinstall.ps1 "releases/download/${CHOC_VERSION}/slskdn-main-win-x64.zip"

CHOC_CHECKSUM=$(sed -n 's#^\$checksum\s*=\s*\"\([^\"]*\)\"#\1#p' packaging/chocolatey/tools/chocolateyinstall.ps1 | head -n 1)
if [[ -z "${CHOC_CHECKSUM}" ]]; then
  fail "Could not extract checksum from packaging/chocolatey/tools/chocolateyinstall.ps1"
fi

if [[ "${#CHOC_CHECKSUM}" -ne 64 ]]; then
  fail "Chocolatey checksum in packaging/chocolatey/tools/chocolateyinstall.ps1 must be a 64-char SHA-256"
fi

if [[ ! "$CHOC_CHECKSUM" =~ ^[a-fA-F0-9]{64}$ ]]; then
  fail "Chocolatey checksum in packaging/chocolatey/tools/chocolateyinstall.ps1 must be hex"
fi

echo "Packaging metadata validation passed."
