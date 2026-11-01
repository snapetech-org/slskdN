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

expect_private_workflows() {
  local workflow_directory="$repo_root/.github/workflows"
  local fork_workflow="$workflow_directory/feature-coherence-validation.yml"

  if [[ ! -f "$fork_workflow" || -L "$fork_workflow" ]] ||
    ! rg -q '^      group: public-fork-jit$' "$fork_workflow" ||
    ! rg -q 'ng-public-run-\$\{\{ github\.run_id \}\}' "$fork_workflow" ||
    ! rg -q '^permissions:$' "$fork_workflow" ||
    ! rg -q '^  contents: read$' "$fork_workflow" ||
    ! rg -q '^      contents: read$' "$fork_workflow" ||
    ! rg -q '^[[:space:]]+persist-credentials: false$' "$fork_workflow"; then
    printf 'public-fork validation must use its isolated run-scoped private JIT group, read-only permissions, and credential-free checkout\n' >&2
    failed=1
  fi

  if rg -n 'NG_HOSTED_FIRST|NG_FORCE_JIT|ubuntu-latest|windows-latest|macos-latest' "$workflow_directory"; then
    printf 'workflows must not contain hosted fallback or legacy hosted-first routing\n' >&2
    failed=1
  fi

  if ! python3 - "$workflow_directory" <<'PYTHON'
import re
import sys
from pathlib import Path

workflow_directory = Path(sys.argv[1])
allowed_groups = {
    "ng-shared-main-jit",
    "packer-windows",
    "gvisor-sandbox",
    "public-fork-jit",
}
hosted_runner = re.compile(r"(?:ubuntu|windows|macos)-[A-Za-z0-9._-]+")
errors = []

for workflow in sorted((*workflow_directory.glob("*.yml"), *workflow_directory.glob("*.yaml"))):
    lines = workflow.read_text().splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^(?P<indent> *)runs-on:(?P<value>.*)$", line)
        if match is None:
            continue

        block_lines = [line]
        parent_indent = len(match.group("indent"))
        for child in lines[index + 1 :]:
            if child.strip() and len(child) - len(child.lstrip()) <= parent_indent:
                break
            block_lines.append(child)
        block = "\n".join(block_lines)
        value = match.group("value").strip()
        if hosted_runner.search(value) or hosted_runner.search(block):
            errors.append(f"{workflow.name}:{index + 1} selects hosted runner capacity")
            continue

        group_match = re.search(r'"group"\s*:\s*"([^\"]+)"', block)
        if group_match is None:
            group_match = re.search(r"(?m)^\s+group:\s*([A-Za-z0-9_-]+)\s*$", block)
        if group_match is None:
            errors.append(f"{workflow.name}:{index + 1} has no approved private runner group")
            continue
        group = group_match.group(1)
        if group not in allowed_groups:
            errors.append(f"{workflow.name}:{index + 1} selects unapproved runner group {group}")
            continue

        if group == "ng-shared-main-jit":
            required = ('"self-hosted"', '"ng-main-run-{0}"', '"gha-{0}-', 'github.run_id')
        elif group == "packer-windows":
            required = ('"self-hosted"', '"gha-{0}-', 'github.run_id')
        elif group == "public-fork-jit":
            required = ('"self-hosted"', 'ng-public-run-${{ github.run_id }}')
        else:
            required = ('gvisor-sandbox',)
        missing = [token for token in required if token not in block]
        if missing:
            errors.append(f"{workflow.name}:{index + 1} lacks private JIT scope: {', '.join(missing)}")

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
PYTHON
  then
    printf 'workflow runner selectors must use compatible private JIT groups with run-scoped labels; hosted runners and fallbacks are prohibited\n' >&2
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
}

expect_private_workflows

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
