#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manifest="$repo_root/vendor/slskNet.Runtime.sync"
vendor_root="$repo_root/vendor/slskNet.Runtime"
patch_rel="vendor/slskNet.Runtime.patches/0001-slskdN-local-runtime-delta.patch"
patch_file="$repo_root/$patch_rel"
apply_changes=false

usage() {
    cat <<'EOF'
Usage: scripts/sync-slsknet-runtime.sh --apply

Fetch the declared branch or release tag from
snapetech-org/slskNet.Runtime, apply the declared
slskdN-local patch set, refresh the vendored mirror, and update the manifest.

The command refuses to modify a dirty vendored runtime or a dirty sync
manifest/patch. Review and commit the resulting diff separately.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --apply)
            apply_changes=true
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

if [[ "$apply_changes" != true ]]; then
    usage >&2
    exit 2
fi

read_manifest_value() {
    local key="$1"
    awk -F= -v key="$key" '$1 == key { print substr($0, index($0, "=") + 1); exit }' "$manifest"
}

resolve_remote_commit() {
    local repository="$1"
    local ref="$2"
    local remote_refs

    if ! remote_refs="$(GIT_TERMINAL_PROMPT=0 git ls-remote "$repository" "$ref" "${ref}^{}")"; then
        return 1
    fi

    # Annotated tags advertise both the tag-object SHA and a peeled commit SHA.
    # Prefer the peeled commit; branches and lightweight tags only have a direct SHA.
    printf '%s\n' "$remote_refs" | awk -v ref="$ref" -v peeled="${ref}^{}" '
        $2 == peeled { peeled_sha = $1 }
        $2 == ref { direct_sha = $1 }
        END {
            if (peeled_sha != "") print peeled_sha
            else if (direct_sha != "") print direct_sha
        }
    '
}

if [[ ! -f "$manifest" || ! -f "$patch_file" ]]; then
    printf 'Runtime sync manifest or patch is missing.\n' >&2
    exit 1
fi

runtime_repository="$(read_manifest_value repository)"
runtime_ref="$(read_manifest_value ref)"
current_commit="$(read_manifest_value commit)"
case "$runtime_ref" in
    refs/heads/*)
        runtime_ref_name="${runtime_ref#refs/heads/}"
        ;;
    refs/tags/*)
        runtime_ref_name="${runtime_ref#refs/tags/}"
        ;;
    *)
        printf 'Runtime sync manifest ref must be a branch or tag ref.\n' >&2
        exit 1
        ;;
esac

if [[ "$runtime_repository" != "https://github.com/snapetech-org/slskNet.Runtime.git" ]]; then
    printf 'Runtime sync manifest must target snapetech-org/slskNet.Runtime.\n' >&2
    exit 1
fi

if [[ -n "$(git -C "$repo_root" status --porcelain --untracked-files=all -- vendor/slskNet.Runtime vendor/slskNet.Runtime.sync vendor/slskNet.Runtime.patches)" ]]; then
    printf 'Runtime sync inputs are dirty; commit or stash them before syncing.\n' >&2
    exit 1
fi

remote_commit="$(resolve_remote_commit "$runtime_repository" "$runtime_ref")" || remote_commit=""
if [[ -z "$remote_commit" ]]; then
    printf 'Could not resolve the remote runtime ref.\n' >&2
    exit 1
fi

if [[ "$remote_commit" == "$current_commit" ]]; then
    printf 'Vendored slskNet.Runtime is already based on %s.\n' "$current_commit"
    exit 0
fi

temp_root="$(mktemp -d)"
trap 'rm -rf -- "$temp_root"' EXIT

source_repository="$temp_root/source"
GIT_TERMINAL_PROMPT=0 git clone --quiet --no-tags --depth 1 --branch "$runtime_ref_name" "$runtime_repository" "$source_repository"

mkdir -p "$temp_root/composed/vendor/slskNet.Runtime"
git -C "$source_repository" archive --format=tar "$remote_commit" | tar -x -C "$temp_root/composed/vendor/slskNet.Runtime"
git -C "$temp_root/composed" init --quiet

if ! git -C "$temp_root/composed" apply --check --allow-empty "$patch_file"; then
    printf 'The existing slskdN runtime patch does not apply to %s.\n' "$remote_commit" >&2
    printf 'Reconcile or upstream the local runtime changes before updating.\n' >&2
    exit 1
fi
git -C "$temp_root/composed" apply --allow-empty "$patch_file"

git -C "$source_repository" ls-tree -r --name-only "$remote_commit" | LC_ALL=C sort > "$temp_root/source-paths"
git -C "$repo_root" ls-files vendor/slskNet.Runtime | sed 's#^vendor/slskNet.Runtime/##' | LC_ALL=C sort > "$temp_root/vendor-paths"

while IFS= read -r tracked_path; do
    relative_path="${tracked_path#vendor/slskNet.Runtime/}"
    if ! rg -q --fixed-strings --line-regexp "$relative_path" "$temp_root/source-paths"; then
        rm -- "$vendor_root/$relative_path"
    fi
done < "$temp_root/vendor-paths"

while IFS= read -r relative_path; do
    source_file="$temp_root/composed/vendor/slskNet.Runtime/$relative_path"
    vendor_file="$vendor_root/$relative_path"
    mkdir -p "$(dirname "$vendor_file")"
    cp -p "$source_file" "$vendor_file"
done < "$temp_root/source-paths"

mkdir -p "$temp_root/diff/baseline/vendor/slskNet.Runtime" "$temp_root/diff/current/vendor"
git -C "$source_repository" archive --format=tar "$remote_commit" | tar -x -C "$temp_root/diff/baseline/vendor/slskNet.Runtime"
# Use the composed working tree, not HEAD, for the refreshed local delta.
while IFS= read -r relative_path; do
    source_file="$temp_root/composed/vendor/slskNet.Runtime/$relative_path"
    current_file="$temp_root/diff/current/vendor/slskNet.Runtime/$relative_path"
    mkdir -p "$(dirname "$current_file")"
    cp -p "$source_file" "$current_file"
done < "$temp_root/source-paths"

set +e
(
    cd "$temp_root/diff"
    git diff --no-index --binary --src-prefix=a/ --dst-prefix=b/ baseline/vendor/slskNet.Runtime current/vendor/slskNet.Runtime
) > "$temp_root/new-patch" 2>&1
diff_status=$?
set -e
if [[ "$diff_status" -gt 1 ]]; then
    cat "$temp_root/new-patch" >&2
    exit "$diff_status"
fi
sed -e 's|a/baseline/|a/|g' -e 's|b/current/|b/|g' "$temp_root/new-patch" > "$patch_file"

sed -i -E "s/^commit=.*/commit=$remote_commit/" "$manifest"

printf 'Updated vendored slskNet.Runtime from %s to %s.\n' "$current_commit" "$remote_commit"
printf 'Run scripts/check-slsknet-runtime-sync.sh and review the generated diff.\n'
