#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manifest="$repo_root/vendor/slskNet.Runtime.sync"
vendor_root="$repo_root/vendor/slskNet.Runtime"
remote_required=true
source_override="${SLSKNET_RUNTIME_SOURCE_DIR:-}"

usage() {
    cat <<'EOF'
Usage: scripts/check-slsknet-runtime-sync.sh [--offline]

Verify that the checked-in slskNet.Runtime mirror is the declared fork
revision with its declared slskdN patch set applied.

--offline  skip the remote-head check; requires SLSKNET_RUNTIME_SOURCE_DIR
           to point at a local git checkout containing the declared commit
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --offline)
            remote_required=false
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'Unknown argument: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

read_manifest_value() {
    local key="$1"
    local value

    value="$(awk -F= -v key="$key" '$1 == key { print substr($0, index($0, "=") + 1); exit }' "$manifest")"
    if [[ -z "$value" ]]; then
        printf '%s is missing manifest value: %s\n' "${manifest#"$repo_root"/}" "$key" >&2
        exit 1
    fi

    printf '%s' "$value"
}

if [[ ! -f "$manifest" ]]; then
    printf 'Missing runtime sync manifest: %s\n' "${manifest#"$repo_root"/}" >&2
    exit 1
fi

runtime_repository="$(read_manifest_value repository)"
runtime_ref="$(read_manifest_value ref)"
expected_commit="$(read_manifest_value commit)"
patch_rel="$(read_manifest_value local_patch)"
patch_file="$repo_root/$patch_rel"

if [[ "$runtime_repository" != "https://github.com/snapetech-org/slskNet.Runtime.git" ]]; then
    printf 'Runtime sync manifest must target snapetech-org/slskNet.Runtime, got: %s\n' "$runtime_repository" >&2
    exit 1
fi

case "$runtime_ref" in
    refs/heads/*)
        runtime_ref_name="${runtime_ref#refs/heads/}"
        ;;
    refs/tags/*)
        runtime_ref_name="${runtime_ref#refs/tags/}"
        ;;
    *)
        printf 'Runtime sync manifest ref must be a branch or tag ref, got: %s\n' "$runtime_ref" >&2
        exit 1
        ;;
esac

if [[ ! "$expected_commit" =~ ^[0-9a-f]{40}$ ]]; then
    printf 'Runtime sync manifest commit must be a full lowercase SHA-1: %s\n' "$expected_commit" >&2
    exit 1
fi

if [[ ! -f "$patch_file" ]]; then
    printf 'Missing declared runtime patch: %s\n' "${patch_file#"$repo_root"/}" >&2
    exit 1
fi

if [[ ! -d "$vendor_root" ]]; then
    printf 'Missing vendored runtime directory: %s\n' "${vendor_root#"$repo_root"/}" >&2
    exit 1
fi

if [[ "$remote_required" == true ]]; then
    remote_commit="$(GIT_TERMINAL_PROMPT=0 git ls-remote "$runtime_repository" "$runtime_ref" | awk 'NR == 1 { print $1; exit }')"
    if [[ -z "$remote_commit" ]]; then
        printf 'Could not resolve the remote runtime ref: %s %s\n' "$runtime_repository" "$runtime_ref" >&2
        exit 1
    fi

    if [[ "$remote_commit" != "$expected_commit" ]]; then
        printf 'slskNet.Runtime has advanced: manifest=%s remote=%s\n' "$expected_commit" "$remote_commit" >&2
        printf 'Update the vendored mirror and manifest before merging or releasing.\n' >&2
        exit 1
    fi
else
    if [[ -z "$source_override" ]]; then
        printf 'Offline runtime sync checks require SLSKNET_RUNTIME_SOURCE_DIR.\n' >&2
        exit 1
    fi
    printf 'Remote runtime head check skipped explicitly (--offline).\n'
fi

temp_root="$(mktemp -d)"
trap 'rm -rf -- "$temp_root"' EXIT

if [[ -n "$source_override" ]]; then
    source_repository="$source_override"
    if [[ ! -d "$source_repository/.git" && ! -f "$source_repository/.git" ]]; then
        printf 'SLSKNET_RUNTIME_SOURCE_DIR is not a git checkout: %s\n' "$source_repository" >&2
        exit 1
    fi
else
    source_repository="$temp_root/source"
    GIT_TERMINAL_PROMPT=0 git clone --quiet --no-tags --depth 1 --branch "$runtime_ref_name" "$runtime_repository" "$source_repository"
fi

if ! git -C "$source_repository" cat-file -e "${expected_commit}^{commit}" 2>/dev/null; then
    printf 'Declared runtime commit is unavailable in source checkout: %s\n' "$expected_commit" >&2
    exit 1
fi

mkdir -p "$temp_root/composed/vendor/slskNet.Runtime"
git -C "$source_repository" archive --format=tar "$expected_commit" | tar -x -C "$temp_root/composed/vendor/slskNet.Runtime"
git -C "$temp_root/composed" init --quiet

if ! git -C "$temp_root/composed" apply --check --allow-empty "$patch_file"; then
    printf 'Declared slskdN runtime patch no longer applies to %s.\n' "$expected_commit" >&2
    printf 'Reconcile the local runtime changes before updating the baseline.\n' >&2
    exit 1
fi
git -C "$temp_root/composed" apply --allow-empty "$patch_file"

git -C "$source_repository" ls-tree -r --name-only "$expected_commit" | LC_ALL=C sort > "$temp_root/source-paths"
git -C "$repo_root" ls-files vendor/slskNet.Runtime | sed 's#^vendor/slskNet.Runtime/##' | LC_ALL=C sort > "$temp_root/vendor-paths"

if ! diff -u "$temp_root/source-paths" "$temp_root/vendor-paths"; then
    printf 'Vendored runtime file set differs from the declared source revision.\n' >&2
    exit 1
fi

failed=0
while IFS= read -r relative_path; do
    composed_file="$temp_root/composed/vendor/slskNet.Runtime/$relative_path"
    vendor_file="$vendor_root/$relative_path"

    if [[ ! -f "$composed_file" || ! -f "$vendor_file" ]]; then
        printf 'Runtime file missing after patch composition: %s\n' "$relative_path" >&2
        failed=1
    elif ! cmp -s "$composed_file" "$vendor_file"; then
        printf 'Runtime content drift: %s\n' "$relative_path" >&2
        failed=1
    fi
done < "$temp_root/source-paths"

untracked="$(git -C "$repo_root" ls-files --others --exclude-standard -- vendor/slskNet.Runtime)"
if [[ -n "$untracked" ]]; then
    printf 'Untracked files exist inside the vendored runtime:\n%s\n' "$untracked" >&2
    failed=1
fi

if [[ "$failed" -ne 0 ]]; then
    exit 1
fi

printf 'slskNet.Runtime sync check passed: %s with declared slskdN patch set.\n' "$expected_commit"
