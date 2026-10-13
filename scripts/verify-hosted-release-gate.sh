#!/usr/bin/env bash

set -euo pipefail

usage() {
    echo "Usage: scripts/verify-hosted-release-gate.sh <run-id> <branch> <commit-sha>" >&2
}

if [[ $# -ne 3 ]]; then
    usage
    exit 2
fi

run_id="$1"
branch="$2"
commit_sha="$3"
repo="snapetech/slskdN"

if [[ ! "$run_id" =~ ^[1-9][0-9]*$ ]]; then
    echo "Hosted validation run ID must be a positive integer." >&2
    exit 2
fi
if [[ "$branch" != "main" ]]; then
    echo "Hosted release validation must run from main." >&2
    exit 2
fi
if [[ ! "$commit_sha" =~ ^[a-f0-9]{40}([a-f0-9]{24})?$ ]]; then
    echo "Commit SHA must be a full Git object ID." >&2
    exit 2
fi

workflow_json="$(gh api "repos/${repo}/actions/workflows/ci.yml")"
workflow_id="$(jq -er '.id | select(type == "number")' <<<"$workflow_json")"
workflow_path="$(jq -er '.path' <<<"$workflow_json")"
if [[ "$workflow_path" != ".github/workflows/ci.yml" ]]; then
    echo "The CI workflow path did not match the expected release gate." >&2
    exit 1
fi

run_json="$(gh api "repos/${repo}/actions/runs/${run_id}")"
if ! jq -e \
    --argjson workflow_id "$workflow_id" \
    --arg repo "$repo" \
    --arg branch "$branch" \
    --arg sha "$commit_sha" \
    '.workflow_id == $workflow_id
     and .repository.full_name == $repo
     and .event == "workflow_dispatch"
     and .head_branch == $branch
     and .head_sha == $sha
     and .status == "completed"
     and .conclusion == "success"' \
    <<<"$run_json" >/dev/null; then
    echo "Hosted CI run ${run_id} did not pass the release gate for ${branch} at ${commit_sha}." >&2
    exit 1
fi

run_url="$(jq -er '.html_url' <<<"$run_json")"
echo "Hosted CI release gate passed for ${branch} at ${commit_sha}: ${run_url}"
