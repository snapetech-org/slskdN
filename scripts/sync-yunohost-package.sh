#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

expected_origin="git@github.com:snapetech-org/slskdN.git"
origin_url="$(git remote get-url origin)"
if [[ "$origin_url" != "$expected_origin" ]]; then
  echo "Refusing YunoHost sync: origin is '$origin_url', expected '$expected_origin'." >&2
  exit 1
fi

source_commit="${1:-HEAD}"
if ! git cat-file -e "${source_commit}^{commit}" 2>/dev/null; then
  echo "Refusing YunoHost sync: '$source_commit' is not a commit in this checkout." >&2
  exit 1
fi

package_prefix="packaging/yunohost/slskdn_ynh"
target_url="git@github.com:YunoHost-Apps/slskdn_ynh.git"
target_branch="testing"

echo "Syncing $package_prefix at $source_commit to YunoHost-Apps/slskdn_ynh:$target_branch"
split_commit="$(git subtree split --prefix="$package_prefix" "$source_commit")"
git push "$target_url" "$split_commit:refs/heads/$target_branch"
