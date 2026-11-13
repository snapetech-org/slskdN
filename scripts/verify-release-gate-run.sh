#!/usr/bin/env bash

set -euo pipefail

usage() {
    echo "Usage: scripts/verify-release-gate-run.sh <run-id> <branch> <commit-sha>" >&2
}

if [[ $# -ne 3 ]]; then
    usage
    exit 2
fi

run_id="$1"
branch="$2"
commit_sha="$3"
repo="snapetech-org/slskdN"
expected_repo_id="1108894784"

if [[ ! "$run_id" =~ ^[1-9][0-9]*$ ]]; then
    echo "CI validation run ID must be a positive integer." >&2
    exit 2
fi
if [[ "$branch" != "main" ]]; then
    echo "CI validation must run from main." >&2
    exit 2
fi
if [[ ! "$commit_sha" =~ ^[a-f0-9]{40}([a-f0-9]{24})?$ ]]; then
    echo "Commit SHA must be a full Git object ID." >&2
    exit 2
fi

repo_id="$(gh api "repos/${repo}" | jq -er '.id | select(type == "number")')"
if [[ "$repo_id" != "$expected_repo_id" ]]; then
    echo "Configured GitHub target resolved to unexpected repository ID ${repo_id}." >&2
    exit 1
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
    --argjson repo_id "$expected_repo_id" \
    --arg branch "$branch" \
    --arg sha "$commit_sha" \
    '.workflow_id == $workflow_id
     and .repository.id == $repo_id
     and .event == "workflow_dispatch"
     and .head_branch == $branch
     and .head_sha == $sha
     and .status == "completed"
     and .conclusion == "success"' \
    <<<"$run_json" >/dev/null; then
    echo "CI run ${run_id} did not pass the release gate for ${branch} at ${commit_sha}." >&2
    exit 1
fi

jobs_json="$(gh api "repos/${repo}/actions/runs/${run_id}/jobs?per_page=100")"
if ! jq -e --arg run_id "$run_id" '
    def valid_gate_job($name; $job_label):
      any(.jobs[]?;
        .name == $name
        and .status == "completed"
        and .conclusion == "success"
        and (
          (
            .runner_group_name == "ng-shared-main-jit"
            and ((.labels // []) | index("self-hosted") != null)
            and ((.labels // []) | index("ng-main-run-" + $run_id) != null)
            and ((.labels // []) | index($job_label) != null)
          )
          or
          (
            ((.labels // []) | index("self-hosted") == null)
            and ((.labels // []) | index("ubuntu-latest") != null or index("ubuntu-24.04") != null)
          )
        ));
    valid_gate_job("Build and Test"; "gha-\($run_id)-build")
    and valid_gate_job("Nix Package Smoke"; "gha-\($run_id)-nix-smoke")
  ' <<<"$jobs_json" >/dev/null; then
    echo "CI run ${run_id} did not complete both release-gate jobs on supported public or private runners." >&2
    exit 1
fi

run_url="$(jq -er '.html_url' <<<"$run_json")"
echo "CI release gate passed for ${branch} at ${commit_sha}: ${run_url}"
