#!/usr/bin/env python3
"""Contract tests for repository identity checks in the GitHub target guard."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts/verify-github-target.sh"
REPOSITORY_ID = "1108894784"
OTHER_REPOSITORY_ID = "12345"
EXPECTED_REPO = "snapetech-org/slskdN"
EXPECTED_UPSTREAM = "https://github.com/slskd/slskd.git"


class VerifyGitHubTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="github-target-")
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()

        mock_git = self.bin / "git"
        mock_git.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "[[ \"${1:-}\" == remote && \"${2:-}\" == get-url ]] || exit 2\n"
            "if [[ \"${3:-}\" == --push && \"${4:-}\" == origin ]]; then\n"
            "  printf '%s\\n' \"$MOCK_PUSH_URL\"\n"
            "  exit 0\n"
            "fi\n"
            "[[ \"${3:-}\" == origin || \"${3:-}\" == upstream ]] || exit 2\n"
            "case \"${3:-}\" in\n"
            "  origin) printf '%s\\n' \"$MOCK_ORIGIN_URL\" ;;\n"
            "  upstream) [[ -n \"${MOCK_UPSTREAM_URL:-}\" ]] || exit 1; printf '%s\\n' \"$MOCK_UPSTREAM_URL\" ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        mock_git.chmod(mock_git.stat().st_mode | stat.S_IXUSR)

        mock_gh = self.bin / "gh"
        mock_gh.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "[[ \"${1:-}\" == api && \"${2:-}\" == \"repos/snapetech-org/slskdN\" && \"${3:-}\" == --jq && \"${4:-}\" == *'.id'* ]] || { echo 'Unexpected GitHub command' >&2; exit 2; }\n"
            "printf '%s\\n' \"$MOCK_REPOSITORY_ID\"\n",
            encoding="utf-8",
        )
        mock_gh.chmod(mock_gh.stat().st_mode | stat.S_IXUSR)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def invoke(
        self,
        *,
        origin_url: str = "git@github.com:snapetech-org/slskdN.git",
        push_url: str = "git@github.com:snapetech-org/slskdN.git",
        repository_id: str = REPOSITORY_ID,
        upstream_url: str = EXPECTED_UPSTREAM,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "PATH": f"{self.bin}{os.pathsep}{environment.get('PATH', '')}",
                "MOCK_ORIGIN_URL": origin_url,
                "MOCK_PUSH_URL": push_url,
                "MOCK_UPSTREAM_URL": upstream_url,
                "MOCK_REPOSITORY_ID": repository_id,
            }
        )
        environment.pop("GH_REPO", None)
        return subprocess.run(
            ["bash", str(GUARD)],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_accepts_canonical_fetch_and_push_urls(self) -> None:
        for url in (
            "git@github.com:snapetech-org/slskdN.git",
            "ssh://git@github.com/snapetech-org/slskdN.git",
            "https://github.com/snapetech-org/slskdN.git",
        ):
            with self.subTest(url=url):
                result = self.invoke(origin_url=url, push_url=url)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"{EXPECTED_REPO} (ID {REPOSITORY_ID})", result.stdout)

    def test_rejects_noncanonical_fetch_remote_even_if_api_target_is_valid(self) -> None:
        result = self.invoke(origin_url="git@github.com:snapetech/slskdN.git")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("origin fetch remote", result.stderr)

    def test_rejects_noncanonical_push_remote(self) -> None:
        result = self.invoke(push_url="git@github.com:other-owner/slskdN.git")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("origin push remote", result.stderr)

    def test_rejects_canonical_name_resolving_to_another_repository_id(self) -> None:
        result = self.invoke(repository_id=OTHER_REPOSITORY_ID)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected repository ID", result.stderr)

    def test_rejects_non_github_origin(self) -> None:
        result = self.invoke(origin_url="git@github.invalid:snapetech-org/slskdN.git")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("recognized GitHub URL", result.stderr)

    def test_rejects_unexpected_upstream_remote(self) -> None:
        result = self.invoke(upstream_url="git@github.com:slskd/slskd.git")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("read-only reference", result.stderr)

    def test_allows_an_unconfigured_upstream_remote_and_ignores_gh_default(self) -> None:
        result = self.invoke(upstream_url="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("upstream: <unset>", result.stdout)
        self.assertIn(f"--repo {EXPECTED_REPO}", result.stdout)


if __name__ == "__main__":
    unittest.main()
