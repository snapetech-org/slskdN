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

expect_linux_self_hosted_job_temp_dir() {
  local workflow_directory="$repo_root/.github/workflows"

  if ! python3 - "$workflow_directory" <<'PYTHON'
import re
import sys
from pathlib import Path

directory = Path(sys.argv[1])
workflow_paths = sorted(directory.glob("*.yml")) + sorted(directory.glob("*.yaml"))
eligible_jobs = 0
failed = False

for path in workflow_paths:
    text = path.read_text()
    jobs_heading = re.search(r"(?m)^jobs:\s*$", text)
    if not jobs_heading:
        continue

    jobs_text = text[jobs_heading.end():]
    headers = list(re.finditer(r"(?m)^  ([A-Za-z0-9_-]+):\s*$", jobs_text))
    for number, header in enumerate(headers):
        end = headers[number + 1].start() if number + 1 < len(headers) else len(jobs_text)
        job_name = header.group(1)
        job = jobs_text[header.end():end]
        runs_on = re.search(r"(?m)^    runs-on:\s*(.*)$", job)
        if not runs_on:
            continue

        runner = runs_on.group(1)
        if "self-hosted" not in runner or "Linux" not in runner:
            continue
        eligible_jobs += 1
        steps_heading = re.search(r"(?m)^    steps:\s*$", job)
        if not steps_heading:
            print(f"{path.name}:{job_name} has no steps", file=sys.stderr)
            failed = True
            continue

        steps_text = job[steps_heading.end():]
        step_headers = list(re.finditer(r"(?m)^      - ", steps_text))
        if not step_headers:
            print(f"{path.name}:{job_name} has no steps", file=sys.stderr)
            failed = True
            continue

        first_end = step_headers[1].start() if len(step_headers) > 1 else len(steps_text)
        first_step = steps_text[step_headers[0].start():first_end]
        name = re.search(r"(?m)^      - name:\s*(.+)$", first_step)
        if not name or name.group(1).strip() != "Configure runner temporary storage":
            print(
                f"{path.name}:{job_name} must configure runner temporary storage in its first step",
                file=sys.stderr,
            )
            failed = True
            continue

        remaining_steps = steps_text[first_end:]
        if re.search(r"(?<![A-Za-z0-9_])/(?:tmp|var/tmp)(?:/|\b)", remaining_steps):
            print(
                f"{path.name}:{job_name} uses a shared temporary path after configuring TMPDIR",
                file=sys.stderr,
            )
            failed = True

        required = (
            "shell: bash",
            "set -euo pipefail",
            '[[ -z "${RUNNER_TEMP:-}"',
            '"$RUNNER_TEMP" != /*',
            '! -d "$RUNNER_TEMP"',
            '! -r "$RUNNER_TEMP"',
            '! -w "$RUNNER_TEMP"',
            '! -x "$RUNNER_TEMP"',
            'pwd -P',
            '/|/tmp|/tmp/*|/var/tmp|/var/tmp/*',
            'GITHUB_ENV:?GITHUB_ENV is required',
            r"printf 'TMPDIR=%s\nTMP=%s\nTEMP=%s\n'",
            '>> "$GITHUB_ENV"',
        )
        missing = [fragment for fragment in required if fragment not in first_step]
        if missing:
            print(
                f"{path.name}:{job_name} runner-temp setup is missing required checks: "
                + ", ".join(missing),
                file=sys.stderr,
            )
            failed = True

if eligible_jobs == 0:
    print("no Linux self-hosted workflow jobs were found to validate", file=sys.stderr)
    raise SystemExit(1)
if failed:
    raise SystemExit(1)
print(f"all {eligible_jobs} Linux self-hosted workflow jobs fail closed on runner.temp")
PYTHON
  then
    failed=1
  fi
}

expect_linux_self_hosted_job_temp_dir


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
