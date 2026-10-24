#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <private-key-file>" >&2
    exit 1
fi
key_file="$1"
[[ -f "$key_file" && ! -L "$key_file" ]] || {
    echo "ERROR: private key must be a regular, non-symlink file." >&2
    exit 1
}
install -d -m 0700 ~/.ssh
install -m 0600 "$key_file" ~/.ssh/aur
cat > ~/.ssh/known_hosts <<'EOF'
aur.archlinux.org ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEuBKrPzbawxA/k2g6NcyV5jmqwJ2s+zpgZGZ7tpLIcN
EOF
actual_fingerprint="$(ssh-keygen -lf ~/.ssh/known_hosts -E sha256 | awk '{print $2}')"
[[ "$actual_fingerprint" == "SHA256:RFzBCUItH9LZS0cKB5UE6ceAYhBD5C8GeOBip8Z11+4" ]] || {
    echo "ERROR: pinned AUR host key fingerprint mismatch." >&2
    exit 1
}
cat > ~/.ssh/config <<'EOF'
Host aur.archlinux.org
  HostName aur.archlinux.org
  User aur
  IdentityFile ~/.ssh/aur
  IdentitiesOnly yes
  UserKnownHostsFile ~/.ssh/known_hosts
  GlobalKnownHostsFile /dev/null
  StrictHostKeyChecking yes
  BatchMode yes
  PasswordAuthentication no
  ProxyCommand nc -X connect -x 10.0.2.100:3128 %h %p
EOF
chmod 0600 ~/.ssh/config ~/.ssh/known_hosts
