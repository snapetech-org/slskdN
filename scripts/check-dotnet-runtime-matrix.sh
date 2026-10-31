#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failed=0

target_major="$(sed -n 's/.*<TargetFramework>net\([0-9][0-9]*\)\..*/\1/p' "$repo_root/src/slskd/slskd.csproj" | head -n1)"

if [ -z "$target_major" ]; then
  printf 'unable to read slskd target framework major version\n' >&2
  exit 1
fi

while IFS= read -r project; do
  project_path="${project#"$repo_root"/}"
  target_framework="$(sed -n 's/.*<TargetFramework>\([^<]*\)<\/TargetFramework>.*/\1/p' "$project" | head -n1)"
  if [ "$target_framework" != "net${target_major}.0" ]; then
    printf '%s targets %s; first-party projects under src/tests/tools must target net%s.0\n' \
      "$project_path" "${target_framework:-no single target framework}" "$target_major" >&2
    failed=1
  fi
done < <(find "$repo_root/src" "$repo_root/tests" "$repo_root/tools" -name '*.csproj' -print | sort)

pinned_sdk_major="$(sed -n 's/.*"version": "\([0-9][0-9]*\)\..*/\1/p' "$repo_root/global.json" | head -n1)"
if [ "$pinned_sdk_major" != "$target_major" ]; then
  printf 'global.json pins .NET %s but the application targets .NET %s\n' \
    "${pinned_sdk_major:-no SDK version}" "$target_major" >&2
  failed=1
fi

expect_literal() {
  local file="$1"
  local literal="$2"

  if ! grep -Fq -- "$literal" "$repo_root/$file"; then
    printf '%s is missing literal: %s\n' "$file" "$literal" >&2
    failed=1
  fi
}

expect_literal packaging/linux/install-from-release.sh "aspnetcore-runtime-${target_major}.0"
expect_literal packaging/proxmox-lxc/setup-inside-ct.sh "aspnetcore-runtime-${target_major}.0"
expect_literal packaging/proxmox-lxc/README.md ".NET ${target_major}"
expect_literal packaging/flatpak/io.github.slskd.slskdn.yml "Runtime/${target_major}.0."
expect_literal packaging/flatpak/io.github.slskd.slskdn.yml "dotnet-runtime-${target_major}.0."
expect_literal packaging/flatpak/FLATHUB_SUBMISSION.md ".NET ${target_major}.0 runtime"
expect_literal docs/FEATURES.md ".NET ${target_major}.0 or later"
expect_literal docs/dev/e2e-testing-guide.md ".NET ${target_major}.0 SDK"
expect_literal CONTRIBUTING.md ".NET ${target_major}.0 SDK"
workflow=".github/workflows/e2e-tests.yml"
if ! rg -q "^  DOTNET_VERSION: '${target_major}\.0\.[0-9]+'$" "$repo_root/$workflow"; then
  printf '%s must pin the application .NET %s.0 runtime version\n' "$workflow" "$target_major" >&2
  failed=1
fi
expect_literal "$workflow" 'dotnet-version: ${{ env.DOTNET_VERSION }}'

expect_hosted_workflows() {
  local workflow_directory="$repo_root/.github/workflows"
  local audited_workflow="$workflow_directory/feature-coherence-validation.yml"
  local policy_pattern='TRUSTED_MAIN_RUNNERS_ENABLED|PREFER_SELF_HOSTED|inputs\.runner|private-[[:alnum:]-]+-jit'
  local matches

  if [[ ! -f "$audited_workflow" || -L "$audited_workflow" ]]; then
    printf 'the audited public-fork validation workflow is missing or not a regular file\n' >&2
    failed=1
  else
    if ! rg -q '^    runs-on: ubuntu-latest$' "$audited_workflow"; then
      printf 'the public-fork validation workflow must use a fresh GitHub-hosted runner\n' >&2
      failed=1
    fi
    if ! rg -q '^permissions:$' "$audited_workflow" ||
      ! rg -q '^  contents: read$' "$audited_workflow" ||
      ! rg -q '^      contents: read$' "$audited_workflow"; then
      printf 'the public-fork validation workflow must keep contents access read-only\n' >&2
      failed=1
    fi
    if ! rg -q '^[[:space:]]+persist-credentials: false$' "$audited_workflow"; then
      printf 'the public-fork validation checkout must not persist credentials\n' >&2
      failed=1
    fi
  fi

  matches="$(rg -n "$policy_pattern" "$workflow_directory" 2>&1 || true)"
  if [[ -n "$matches" ]]; then
    printf '%s\n' "$matches" >&2
    printf 'GitHub workflows must not select private runner groups or manual runner overrides\n' >&2
    failed=1
  fi

  local route_pattern='^[[:space:]]*(runs-on|labels):.*(self-hosted|ng-shared-main-jit|gvisor-sandbox|"group":)'
  local workflow_file
  for workflow_file in "$workflow_directory"/*.yml "$workflow_directory"/*.yaml; do
    [[ -f "$workflow_file" ]] || continue
    if ! rg -q "$route_pattern" "$workflow_file"; then
      continue
    fi

    case "$(basename "$workflow_file")" in
      check-upstream-access.yml|ci.yml|gvisor-runner-smoke.yml|local-identity-leaks.yml|semgrep-community.yml|trivy-filesystem.yml)
        ;;
      *)
        printf '%s selects a non-hosted runner outside the approved main-only shared route\n' \
          "${workflow_file#"$repo_root"/}" >&2
        failed=1
        ;;
    esac
  done

  local shared_main_workflow
  local expected_routes
  for shared_main_workflow in \
    check-upstream-access.yml \
    ci.yml \
    local-identity-leaks.yml \
    semgrep-community.yml \
    trivy-filesystem.yml; do
    workflow_file="$workflow_directory/$shared_main_workflow"
    if [[ ! -f "$workflow_file" || -L "$workflow_file" ]]; then
      printf 'approved shared-runner workflow is missing or not a regular file: %s\n' \
        "$shared_main_workflow" >&2
      failed=1
      continue
    fi

    expected_routes=1
    [[ "$shared_main_workflow" != "ci.yml" ]] || expected_routes=2
    local route_count
    route_count="$(rg -F -c 'ng-shared-main-jit' "$workflow_file" || true)"
    if [[ "$route_count" != "$expected_routes" ]]; then
      printf '%s has %s shared-runner routes; expected %s\n' \
        "$shared_main_workflow" "${route_count:-0}" "$expected_routes" >&2
      failed=1
    fi

    local required_route_text
    for required_route_text in \
      'github.event_name == '\''push'\''' \
      'github.event_name == '\''workflow_dispatch'\''' \
      'github.ref == '\''refs/heads/main'\''' \
      'github.run_id' \
      '"group":"ng-shared-main-jit"' \
      '"labels":["self-hosted","linux","x64","ng-shared-main-slskdn","ng-main-run-{0}"]' \
      "|| 'ubuntu-latest'"; do
      if ! rg -Fq -- "$required_route_text" "$workflow_file"; then
        printf '%s is missing the main-only shared-runner condition: %s\n' \
          "$shared_main_workflow" "$required_route_text" >&2
        failed=1
      fi
    done
  done

  local non_shared_groups
  non_shared_groups="$(rg -n '"group"[[:space:]]*:' "$workflow_directory" | rg -v '"group":"ng-shared-main-jit"' || true)"
  if [[ -n "$non_shared_groups" ]]; then
    printf '%s\n' "$non_shared_groups" >&2
    printf 'Only the repository-scoped ng-shared-main-jit group is allowed for main CI\n' >&2
    failed=1
  fi

  local gvisor_workflow="$workflow_directory/gvisor-runner-smoke.yml"
  if [[ ! -f "$gvisor_workflow" || -L "$gvisor_workflow" ]] ||
    ! rg -q '^  workflow_dispatch:$' "$gvisor_workflow" ||
    ! rg -q "^    if: github.ref == 'refs/heads/main'$" "$gvisor_workflow" ||
    ! rg -q '^permissions: \{\}$' "$gvisor_workflow" ||
    ! rg -q '^    timeout-minutes: 5$' "$gvisor_workflow"; then
    printf 'gVisor runner smoke must be dispatch-only, main-only, permissionless, and time-bounded\n' >&2
    failed=1
  fi
  if rg -n '^  (push|pull_request|pull_request_target|schedule):$|actions/checkout|secrets\.|github\.token' \
    "$gvisor_workflow"; then
    printf 'gVisor runner smoke must not run untrusted refs or access repository code/secrets\n' >&2
    failed=1
  fi

  if ! python3 - "$workflow_directory" <<'PYTHON'
import re
import sys
from pathlib import Path

workflow_directory = Path(sys.argv[1])
shared_main_workflows = {
    "check-upstream-access.yml": 1,
    "ci.yml": 2,
    "local-identity-leaks.yml": 1,
    "semgrep-community.yml": 1,
    "trivy-filesystem.yml": 1,
}
shared_main_route = (
    "${{ (vars.NG_HOSTED_FIRST != 'true' || vars.NG_FORCE_JIT == 'true' "
    "|| github.run_attempt > 1) && (github.event_name == 'push' "
    "|| github.event_name == 'workflow_dispatch' || github.event_name == 'schedule') "
    "&& github.ref == 'refs/heads/main' && "
    "fromJSON(format('{{\"group\":\"ng-shared-main-jit\",\"labels\":["
    "\"self-hosted\",\"linux\",\"x64\",\"ng-shared-main-slskdn\","
    "\"ng-main-run-{0}\"]}}', github.run_id)) || 'ubuntu-latest' }}"
)
ci_shared_main_route = shared_main_route.replace(
    " || github.event_name == 'schedule'", ""
)
hosted_runner = re.compile(r"(?:ubuntu|windows|macos)-[A-Za-z0-9._-]+")
errors = []

for workflow in sorted((*workflow_directory.glob("*.yml"), *workflow_directory.glob("*.yaml"))):
    lines = workflow.read_text().splitlines()
    shared_route_count = 0
    for index, line in enumerate(lines):
        match = re.match(r"^(?P<indent> *)runs-on:(?P<value>.*)$", line)
        if match is None:
            continue

        value = match.group("value").strip()
        if value:
            if hosted_runner.fullmatch(value):
                continue
            expected_shared_route = (
                ci_shared_main_route if workflow.name == "ci.yml" else shared_main_route
            )
            if workflow.name in shared_main_workflows and value == expected_shared_route:
                shared_route_count += 1
                continue
            errors.append(f"{workflow.name}:{index + 1} uses an unapproved runner selector")
            continue

        parent_indent = len(match.group("indent"))
        mapping = {}
        for child in lines[index + 1 :]:
            if not child.strip():
                continue
            child_indent = len(child) - len(child.lstrip())
            if child_indent <= parent_indent:
                break
            child_match = re.match(r"^\s+([A-Za-z][A-Za-z0-9_-]*):\s*(\S+)\s*$", child)
            if child_match is not None:
                mapping[child_match.group(1)] = child_match.group(2)

        if workflow.name == "gvisor-runner-smoke.yml" and mapping == {
            "group": "gvisor-sandbox",
            "labels": "gvisor-sandbox",
        }:
            continue
        errors.append(f"{workflow.name}:{index + 1} uses an unapproved multiline runner selector")

    if workflow.name in shared_main_workflows:
        expected_route_count = shared_main_workflows[workflow.name]
        if shared_route_count != expected_route_count:
            errors.append(
                f"{workflow.name} has {shared_route_count} exact main-only shared routes; "
                f"expected {expected_route_count}"
            )

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
PYTHON
  then
    printf 'workflow runner selectors must use GitHub-hosted runners or an approved restricted route\n' >&2
    failed=1
  fi
}

expect_hosted_workflows

if rg -n '\.NET 8\.0|\.NET 8|aspnetcore-runtime-8\.0|dotnet-runtime-8\.0|dotnet-version: .8\.0\.x.' \
  "$repo_root/packaging/flatpak" \
  "$repo_root/packaging/proxmox-lxc" \
  "$repo_root/docs/FEATURES.md" \
  "$repo_root/docs/dev/e2e-testing-guide.md" \
  "$repo_root/CONTRIBUTING.md" >&2; then
  printf 'Active package/docs runtime references must match net%s.0, not .NET 8.\n' "$target_major" >&2
  failed=1
fi

if [ "$failed" -ne 0 ]; then
  exit 1
fi

printf '.NET runtime/package matrix matches the application target framework.\n'
