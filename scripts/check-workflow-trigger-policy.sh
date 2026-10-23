#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failed=0

release_workflows=(
  "$repo_root/.github/workflows/build-on-tag.yml"
  "$repo_root/.github/workflows/ci.yml"
)

for workflow in "${release_workflows[@]}"; do
  rel="${workflow#"$repo_root"/}"
  if [ ! -f "$workflow" ]; then
    printf '%s is missing\n' "$rel" >&2
    failed=1
    continue
  fi
done

if ! rg -q "'v\*'" "$repo_root/.github/workflows/build-on-tag.yml"; then
  printf '.github/workflows/build-on-tag.yml must trigger on v<version> tags\n' >&2
  failed=1
fi

if rg -q "build-dev-\*" "$repo_root/.github/workflows/build-on-tag.yml"; then
  printf '.github/workflows/build-on-tag.yml must not start release builds from dev tags\n' >&2
  failed=1
fi

if ! rg -q 'v<version>' "$repo_root/docs/build.md"; then
  printf 'docs/build.md must document v<version> release tags\n' >&2
  failed=1
fi

if ! rg -q '^  workflow_dispatch:' "$repo_root/.github/workflows/codeql.yml"; then
  printf '.github/workflows/codeql.yml must support an exact-main validation dispatch\n' >&2
  failed=1
fi

if rg -n 'branches:\s*\[.*(master|main).*\]' "$repo_root/.github/workflows/build-on-tag.yml" >&2; then
  printf 'build-on-tag.yml must not run release builds on branch pushes\n' >&2
  failed=1
fi

if rg -q 'build-dev-\*|build-main-\*|"\[0-9\]' "$repo_root/.github/workflows/ci.yml"; then
  printf '.github/workflows/ci.yml must not trigger release builds from legacy or unprefixed tags\n' >&2
  failed=1
fi

if rg -n '\[0-9\]\+\.\[0-9\]\+\.\[0-9\]\+' "$repo_root/.github/workflows/ci.yml" "$repo_root/.github/workflows/ci-enhancements.yml" >&2; then
  printf 'GitHub tag filters are globs; do not use regex + quantifiers in release tag patterns\n' >&2
  failed=1
fi

while IFS= read -r workflow; do
  if rg -q '^\s*schedule:' "$workflow" && rg -q 'git (tag|push origin .*\$?NEW_VERSION|push origin .*\$?\{.*version.*\})' "$workflow"; then
    printf '%s must not create or push release tags from a scheduled workflow\n' "${workflow#"$repo_root"/}" >&2
    failed=1
  fi
done < <(find "$repo_root/.github/workflows" -maxdepth 1 -type f \( -name '*.yml' -o -name '*.yaml' \) | sort)

ci_workflow="$repo_root/.github/workflows/ci.yml"
ci_enhancements_workflow="$repo_root/.github/workflows/ci-enhancements.yml"
approved_events='["push","workflow_dispatch","schedule","release","repository_dispatch"]'
event_gate="contains(fromJSON('$approved_events'), github.event_name)"
for workflow in "$ci_workflow" "$ci_enhancements_workflow"; do
  workflow_name="$(basename "$workflow")"
  if [[ "$workflow" == "$ci_workflow" ]]; then
    if rg -n 'PREFER_SELF_HOSTED|inputs\.runner|private-[a-z-]+-jit|TRUSTED_MAIN_RUNNERS_ENABLED' "$workflow"; then
      printf '%s must not select a private runner\n' "$workflow_name" >&2
      failed=1
    fi
    for job in build nix-smoke; do
      job_block="$(sed -n "/^  $job:/,/^  [A-Za-z0-9_-]*:/p" "$workflow")"
      if [[ "$job_block" != *"ng-shared-main-jit"* ||
            "$job_block" != *"ng-shared-main-slskdn"* ||
            "$job_block" != *"ng-main-run-{0}"* ||
            "$job_block" != *"github.run_id"* ||
            "$job_block" != *"$event_gate"* ||
            "$job_block" != *"github.ref == 'refs/heads/main'"* ||
            "$job_block" != *"github.ref_type == 'tag' && startsWith(github.ref_name, 'v')"* ||
            "$job_block" != *"github.run_attempt > 1"* ||
            "$job_block" != *"|| 'ubuntu-latest'"* ]]; then
        printf '%s job %s must route only main validation to the shared pool\n' "$workflow_name" "$job" >&2
        failed=1
      fi
    done
    route_count="$(rg -n -F 'ng-shared-main-jit' "$workflow" | wc -l)"
    if [[ "$route_count" -ne 2 ]]; then
      printf '%s has an unexpected shared runner route count\n' "$workflow_name" >&2
      failed=1
    fi
  else
    if rg -n 'self-hosted|PREFER_SELF_HOSTED|inputs\.runner' "$workflow"; then
      printf '%s must stay on GitHub-hosted runners\n' "$workflow_name" >&2
      failed=1
    fi
    if ! rg -q '^    runs-on: ubuntu-latest$' "$workflow"; then
      printf '%s must keep CI jobs on GitHub-hosted Linux runners\n' "$workflow_name" >&2
      failed=1
    fi
  fi
done

upstream_access_workflow="$repo_root/.github/workflows/check-upstream-access.yml"
if rg -q '^\s*workflow_dispatch:' "$upstream_access_workflow" ||
  ! rg -Fq "if: github.event_name == 'schedule'" "$upstream_access_workflow"; then
  printf '.github/workflows/check-upstream-access.yml write workflow must not run from a manually selected ref\n' >&2
  failed=1
fi

if ! python3 - "$ci_workflow" <<'PYTHON'
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text()
push = re.search(r"(?ms)^  push:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)", text)
if not push or re.search(r"(?m)^    tags:\n", push.group(1)):
    raise SystemExit("CI must leave release tag triggers to build-on-tag.yml")
branches = [
    value.strip()
    for value in re.findall(r"(?m)^    branches:\s*\[([^\]]*)\]\s*$", push.group(1))
]
if branches != ["main"]:
    raise SystemExit("CI validation pushes must stay restricted to main")
PYTHON
then
  printf '.github/workflows/ci.yml must keep release builds separate from validation triggers\n' >&2
  failed=1
fi

if ! awk '
  $0 == "  load-testing:" { in_job = 1; next }
  in_job && /^  [A-Za-z0-9_-]+:$/ { exit }
  in_job && $0 == "    runs-on: ubuntu-latest" { found = 1 }
  END { exit !found }
' "$repo_root/.github/workflows/ci-enhancements.yml"; then
  printf '.github/workflows/ci-enhancements.yml load-testing must use an isolated hosted runner\n' >&2
  failed=1
fi

if ! awk '
  $0 == "      - name: Run Load Tests" { in_step = 1; next }
  in_step && /^      - name:/ { exit }
  in_step && $0 == "        env:" { has_env = 1 }
  in_step && $0 == "          BASE_URL: http://127.0.0.1:5099" { has_base_url = 1 }
  END { exit !(has_env && has_base_url) }
' "$repo_root/.github/workflows/ci-enhancements.yml"; then
  printf '.github/workflows/ci-enhancements.yml load test must receive its local BASE_URL through step environment\n' >&2
  failed=1
fi

if ! awk '
  $0 == "      - name: Start Application" { in_step = 1; next }
  in_step && /^      - name:/ { exit }
  in_step && /--no-connect/ { no_connect = 1 }
  in_step && /--no-auth/ { no_auth = 1 }
  in_step && /--no-https/ { no_https = 1 }
  in_step && /--http-address 127\.0\.0\.1/ { loopback = 1 }
  in_step && /--http-port 5099/ { port = 1 }
  END { exit !(no_connect && no_auth && no_https && loopback && port) }
' "$repo_root/.github/workflows/ci-enhancements.yml"; then
  printf '.github/workflows/ci-enhancements.yml must keep the API load-test instance offline, unauthenticated, and loopback-only\n' >&2
  failed=1
fi

if ! awk '
  $0 == "      - name: Start Application" { in_step = 1; next }
  in_step && /^      - name:/ { exit }
  in_step && /content_path: wwwroot/ { configured = 1 }
  in_step && /mkdir -p .*wwwroot/ { created = 1 }
  END { exit !(configured && created) }
' "$repo_root/.github/workflows/ci-enhancements.yml"; then
  printf '.github/workflows/ci-enhancements.yml must create the configured web root for its API-only process\n' >&2
  failed=1
fi

if ! python3 - "$repo_root/.github/workflows" <<'PYTHON'
import re
import sys
from pathlib import Path

workflow_dir = Path(sys.argv[1])
workflow_paths = [*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")]
texts = {path.name: path.read_text() for path in workflow_paths}
for name, text in texts.items():
    for line_number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^\s*uses:\s*([^\s#]+)", line)
        if not match:
            continue
        action = match.group(1)
        if action.startswith("./"):
            continue
        if "@" not in action or not re.fullmatch(r"[0-9a-f]{40}", action.rsplit("@", 1)[1]):
            raise SystemExit(f"{name}:{line_number} must pin its action to a full commit SHA")

ci = texts["ci.yml"]
enhancements = texts["ci-enhancements.yml"]
tag_workflow = texts["build-on-tag.yml"]

def job_block(workflow, job):
    match = re.search(rf"(?ms)^  {re.escape(job)}:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)", workflow)
    if not match:
        raise SystemExit(f"build-on-tag.yml is missing {job}")
    return match.group(1)

parse_job = job_block(tag_workflow, "parse")
if "Manual publisher recovery requires an existing v<version> release tag" not in parse_job:
    raise SystemExit("manual publisher recovery must require an existing release tag")
if not re.search(r"(?m)^    permissions:\n      contents: read$", parse_job):
    raise SystemExit("manual publisher recovery must use a read-only token to verify the release")
if "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" not in parse_job:
    raise SystemExit("manual publisher recovery must authenticate its release lookup")
if 'gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY"' not in parse_job:
    raise SystemExit("manual publisher recovery must verify the existing release before publishing")
if 'release_tag: ${{ steps.parse.outputs.release_tag }}' not in tag_workflow:
    raise SystemExit("Build on Tag must carry the GitHub Release tag separately from package version")
if "Select at least one publisher to retry" not in parse_job:
    raise SystemExit("manual publisher recovery must require an explicit target")

for job, retry_input in {
    "aur-main": "retry_aur",
    "copr-main": "retry_copr",
    "ppa-main": "retry_ppa",
    "docker-main": "retry_docker",
    "nix-main": "retry_nix",
}.items():
    block = job_block(tag_workflow, job)
    if f"inputs.{retry_input}" not in block or "needs.release-main.result == 'success'" not in block:
        raise SystemExit(f"{job} must be selected explicitly for recovery and gated on the normal release")
    if "ref: ${{ inputs.tag || github.ref }}" not in block:
        raise SystemExit(f"{job} must read source from the selected release tag during recovery")

for job in ("build", "publish", "release-main", "announce-main", "docker-omnibus", "chocolatey-main", "homebrew-main"):
    block = job_block(tag_workflow, job)
    if "github.event_name != 'workflow_dispatch'" not in block:
        raise SystemExit(f"{job} must be skipped during selected publisher recovery")

for job in ("performance-regression", "dependency-scanning", "container-scanning"):
    match = re.search(rf"(?ms)^  {re.escape(job)}:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)", enhancements)
    if not match:
        raise SystemExit(f"ci-enhancements.yml is missing {job}")
    if re.search(r"(?m)^\s*continue-on-error:\s*true\s*$", match.group(1)):
        raise SystemExit(f"ci-enhancements.yml {job} must fail when its checks fail")

if "pnpm audit --prod --audit-level high || true" in enhancements:
    raise SystemExit("pnpm audit failures must not be suppressed")
if not re.search(r"uses: aquasecurity/trivy-action@[0-9a-f]{40}", enhancements):
    raise SystemExit("Trivy must be pinned to a full commit SHA")
if not re.search(r"exit-code:\s*['\"]?1['\"]?", enhancements):
    raise SystemExit("Trivy must fail on HIGH/CRITICAL findings")
PYTHON
then
  printf 'CI action pinning or security scan policy checks failed\n' >&2
  failed=1
fi

for release_job in publish docker release; do
  if rg -q "^  ${release_job}:$" "$ci_workflow"; then
    printf '.github/workflows/ci.yml must leave release job %s to build-on-tag.yml\n' "$release_job" >&2
    failed=1
  fi
done

if [ "$failed" -ne 0 ]; then
  exit 1
fi

printf 'Workflow release triggers preserve the tag-only build policy.\n'
