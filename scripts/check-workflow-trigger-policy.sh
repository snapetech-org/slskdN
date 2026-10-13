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

if ! rg -q "build-main-\*" "$repo_root/.github/workflows/build-on-tag.yml"; then
  printf '.github/workflows/build-on-tag.yml must trigger on build-main-* tags\n' >&2
  failed=1
fi

if ! rg -q "build-dev-\*" "$repo_root/.github/workflows/build-on-tag.yml"; then
  printf '.github/workflows/build-on-tag.yml must trigger on build-dev-* tags\n' >&2
  failed=1
fi

if ! rg -q "build-dev-\*" "$repo_root/docs/build.md"; then
  printf 'docs/build.md must document build-dev-* tag builds\n' >&2
  failed=1
fi

if rg -n 'branches:\s*\[.*(master|main).*\]' "$repo_root/.github/workflows/build-on-tag.yml" >&2; then
  printf 'build-on-tag.yml must not run release builds on branch pushes\n' >&2
  failed=1
fi

if ! rg -q 'build-dev-\*|build-main-\*|[0-9]\{8,10\}-slskdn' "$repo_root/.github/workflows/ci.yml"; then
  printf '.github/workflows/ci.yml must keep release builds tag-addressable\n' >&2
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
for workflow in "$ci_workflow" "$ci_enhancements_workflow"; do
  if ! rg -Fq "github.event_name == 'pull_request' ||" "$workflow" ||
    ! rg -Fq "&& 'ubuntu-latest' || vars.PREFER_SELF_HOSTED != 'false' && fromJSON" "$workflow"; then
    printf '%s must route every pull request to hosted runners while preserving explicit runner preference\n' "${workflow#"$repo_root"/}" >&2
    failed=1
  fi
done

if ! rg -Fq "github.event_name == 'workflow_dispatch' && (github.ref != 'refs/heads/main' || inputs.runner == 'github-hosted')" "$ci_workflow" ||
  ! rg -Fq "github.event_name == 'workflow_dispatch' && github.ref != 'refs/heads/main'" "$ci_enhancements_workflow"; then
  printf 'CI workflows must keep non-main manual runs on hosted runners\n' >&2
  failed=1
fi

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
if not push or not re.search(r"(?m)^    tags:\n", push.group(1)):
    raise SystemExit("CI must preserve its release tag triggers")
if re.search(r"(?m)^    branches(?:-ignore)?:", push.group(1)):
    raise SystemExit("CI builds must not be added to branch pushes")
PYTHON
then
  printf '.github/workflows/ci.yml must keep builds tag-triggered\n' >&2
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
uses_pattern = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)")

def action_is_pinned(line):
    match = uses_pattern.match(line)
    if not match:
        return None
    action = match.group(1)
    if action.startswith("./"):
        return True
    return "@" in action and re.fullmatch(r"[0-9a-f]{40}", action.rsplit("@", 1)[1]) is not None

sha = "a" * 40
for line in (f"      uses: actions/checkout@{sha}", f"      - uses: actions/checkout@{sha}"):
    if action_is_pinned(line) is not True:
        raise SystemExit("action pin check must accept both YAML uses forms")
for line in ("      uses: actions/checkout@v7", "      - uses: actions/checkout@v7"):
    if action_is_pinned(line) is not False:
        raise SystemExit("action pin check must reject mutable refs in both YAML uses forms")

for name, text in texts.items():
    for line_number, line in enumerate(text.splitlines(), 1):
        pinned = action_is_pinned(line)
        if pinned is False:
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
tag_character_guard = 'if [[ ! "$TAG" =~ ^build-(main|dev)-[A-Za-z0-9][A-Za-z0-9._-]*$ ]]'
if tag_character_guard not in parse_job:
    raise SystemExit("tag-derived versions must be restricted before downstream shell interpolation")
for tag in (
    "build-main-2026101323-slskdn.351",
    "build-dev-0.25.0-dev.20261013",
):
    if not re.fullmatch(r"build-(main|dev)-[A-Za-z0-9][A-Za-z0-9._-]*", tag):
        raise SystemExit(f"tag-character guard rejected supported tag {tag}")
for tag in ("build-main-$(id)", "build-dev-version;id", "build-main-`id`"):
    if re.fullmatch(r"build-(main|dev)-[A-Za-z0-9][A-Za-z0-9._-]*", tag):
        raise SystemExit(f"tag-character guard accepted shell syntax in {tag}")
if "Manual publisher recovery requires an existing build-main-* tag" not in parse_job:
    raise SystemExit("manual publisher recovery must accept only stable build tags")
if 'Manual publisher recovery must run from refs/heads/main' not in parse_job or '"$GITHUB_REF" != "refs/heads/main"' not in parse_job:
    raise SystemExit("manual publisher recovery must reject non-main workflow refs")
if not re.search(r"(?m)^    permissions:\n      contents: read$", parse_job):
    raise SystemExit("manual publisher recovery must use a read-only token to verify the release")
if "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" not in parse_job:
    raise SystemExit("manual publisher recovery must authenticate its release lookup")
if 'gh release view "$VERSION" --repo "$GITHUB_REPOSITORY"' not in parse_job:
    raise SystemExit("manual publisher recovery must verify the existing release before publishing")
if 'repos/${GITHUB_REPOSITORY}/releases/latest' not in parse_job:
    raise SystemExit("manual publisher recovery must reject stale stable releases")
if 'repos/${GITHUB_REPOSITORY}/git/ref/tags/${TAG}' not in parse_job or 'echo "source_sha=$object_sha"' not in parse_job:
    raise SystemExit("publisher recovery must resolve the requested tag to an immutable commit")
if '"$object_sha" != "$GITHUB_SHA"' not in parse_job:
    raise SystemExit("tag-triggered builds must use the exact commit from the push event")
if "Select at least one publisher to retry" not in parse_job:
    raise SystemExit("manual publisher recovery must require an explicit target")
if "retry_docker" in tag_workflow:
    raise SystemExit("manual Docker recovery must not rebuild from source instead of release artifacts")

for job, retry_input in {
    "aur-main": "retry_aur",
    "copr-main": "retry_copr",
    "ppa-main": "retry_ppa",
    "nix-main": "retry_nix",
}.items():
    block = job_block(tag_workflow, job)
    if f"inputs.{retry_input}" not in block or "needs.release-main.result == 'success'" not in block:
        raise SystemExit(f"{job} must be selected explicitly for recovery and gated on the normal release")
    if "github.ref == 'refs/heads/main'" not in block:
        raise SystemExit(f"{job} must reject manual publisher recovery outside main")
    if job == "nix-main":
        if "ref: refs/heads/main" not in block:
            raise SystemExit("Nix recovery must update the current main tree")
        order = [block.index(marker) for marker in (
            "name: Update Metadata Files",
            "name: Verify Flake",
            "name: Run Nix package smoke",
            "name: Commit and Push",
        )]
        if order != sorted(order):
            raise SystemExit("Nix recovery must validate the exact tree before committing it")
        if "git reset --hard origin/main" in block or "git clean -fd" in block:
            raise SystemExit("Nix recovery must not replace the validated tree before pushing")
        if "git rev-parse refs/remotes/origin/main" not in block:
            raise SystemExit("Nix recovery must fail if main advances after validation")
    else:
        if "ref: ${{ needs.parse.outputs.source_sha }}" not in block:
            raise SystemExit(f"{job} must check out the commit resolved by the parse job")
        if not re.search(r"(?m)^    permissions:\n      contents: read$", block):
            raise SystemExit(f"{job} must have the minimum repository-read permission for release assets")

if "AUR recovery requires AUR_SSH_KEY" not in job_block(tag_workflow, "aur-main"):
    raise SystemExit("selected AUR recovery must fail when its publishing key is missing")
for job in ("copr-main", "ppa-main"):
    block = job_block(tag_workflow, job)
    if "continue-on-error: ${{ github.event_name != 'workflow_dispatch' }}" not in block:
        raise SystemExit(f"{job} recovery failures must fail the selected manual run")
if "COPR recovery requires a complete supported credential set" not in job_block(tag_workflow, "copr-main"):
    raise SystemExit("selected COPR recovery must fail when publishing credentials are missing")
if "PPA recovery requires GPG_PRIVATE_KEY" not in job_block(tag_workflow, "ppa-main"):
    raise SystemExit("selected PPA recovery must fail when its signing key is missing")
docker_job = job_block(tag_workflow, "docker-main")
if "github.event_name != 'workflow_dispatch'" not in docker_job or "ref: ${{ needs.parse.outputs.source_sha }}" not in docker_job:
    raise SystemExit("Docker publication must remain tag-only and use the parsed commit")

for job in ("build", "publish", "release-main", "announce-main", "docker-omnibus", "chocolatey-main", "homebrew-main"):
    block = job_block(tag_workflow, job)
    if "github.event_name != 'workflow_dispatch'" not in block:
        raise SystemExit(f"{job} must be skipped during selected publisher recovery")

for job in ("performance-regression", "dependency-scanning", "container-scanning"):
    match = re.search(rf"(?ms)^  {re.escape(job)}:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)", enhancements)
    if not match:
        raise SystemExit(f"ci-enhancements.yml is missing {job}")
    block = match.group(1)
    if re.search(r"(?m)^\s*continue-on-error:\s*true\s*$", block):
        raise SystemExit(f"ci-enhancements.yml {job} must fail when its checks fail")
    if job == "performance-regression":
        if "BENCHMARK_ARTIFACTS: ${{ github.workspace }}/tests/slskd.Tests.Performance/BenchmarkDotNet.Artifacts" not in block:
            raise SystemExit(
                "ci-enhancements.yml benchmark artifacts must use one workspace-rooted directory"
            )
        for required in (
            '--filter "*HashDbPerformanceBenchmarks.LookupHash_WithoutCache*"',
            "--buildTimeout 600",
            "--stopOnFirstError",
            '--artifacts "$BENCHMARK_ARTIFACTS"',
            "scripts/verify-benchmark-results.py",
            '"$BENCHMARK_ARTIFACTS/results"',
            "tests/slskd.Tests.Performance/BenchmarkDotNet.Artifacts/results/*.json",
            "tests/slskd.Tests.Performance/BenchmarkDotNet.Artifacts/results/*.md",
        ):
            if required not in block:
                raise SystemExit(
                    f"ci-enhancements.yml performance-regression must include {required}"
                )

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
  if ! awk -v job="$release_job" '
    $0 == "  " job ":" { in_job = 1; next }
    in_job && /^  [A-Za-z0-9_-]+:$/ { exit }
    in_job && index($0, "if: startsWith(github.ref, '\''refs/tags/'\'')") > 0 { found = 1 }
    END { exit !found }
  ' "$ci_workflow"; then
    printf '.github/workflows/ci.yml job %s must stay tag-gated\n' "$release_job" >&2
    failed=1
  fi
done

if [ "$failed" -ne 0 ]; then
  exit 1
fi

printf 'Workflow release triggers preserve the tag-only build policy.\n'
