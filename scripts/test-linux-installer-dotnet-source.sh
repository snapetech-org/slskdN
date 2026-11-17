#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$repo_root/packaging/linux/install-from-release.sh"

assert_source() {
  local expected="$1"
  shift
  local actual
  actual="$(resolve_dotnet_apt_source "$@")"

  if [[ "$actual" != "$expected" ]]; then
    printf 'Expected APT source mapping %s, got %s\n' "$expected" "$actual" >&2
    exit 1
  fi
}

assert_source "ubuntu 24.04 noble backports" linuxmint 22.3 zena noble
assert_source "ubuntu 24.04 noble backports" ubuntu 24.04 noble ""
assert_source "ubuntu 22.04 jammy backports" linuxmint 21.3 vera jammy
assert_source "debian 12 bookworm microsoft" debian 12 bookworm ""

if resolve_dotnet_apt_source linuxmint 20.3 ulyssa focal >/dev/null 2>&1; then
  echo "Unsupported Linux Mint bases must fail before configuring an APT source." >&2
  exit 1
fi

printf 'Linux installer .NET APT source mappings passed.\n'
