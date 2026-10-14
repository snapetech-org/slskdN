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
            "case \"${3:-}\" in\n"
            "  origin) printf '%s\\n' \"$MOCK_ORIGIN_URL\" ;;\n"
            "  upstream) [[ -n \"${MOCK_UPSTREAM_URL:-}\" ]] || exit 1; printf '%s\\n' \"$MOCK_UPSTREAM_URL\" ;;\n"
            "  *) exit 2 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        mock_git.chmod(mock_git.stat().st_mode | stat.S_IXUSR)

        mock_gh = self.bin / "gh"
        mock_gh.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "case \"${1:-}\" in\n"
            "  repo) [[ \"${2:-}\" == set-default && \"${3:-}\" == --view ]] || exit 2; printf '%s\\n' \"$MOCK_DEFAULT_REPO\" ;;\n"
            "  api)\n"
            "    case \"${2:-}\" in\n"
            "      \"repos/${MOCK_ORIGIN_REPO}\") printf '%s\\n' \"$MOCK_ORIGIN_ID\" ;;\n"
            "      \"repos/${MOCK_DEFAULT_REPO_PATH}\") printf '%s\\n' \"$MOCK_DEFAULT_ID\" ;;\n"
            "      *) echo 'Unexpected GitHub API path' >&2; exit 3 ;;\n"
            "    esac\n"
            "    ;;\n"
            "  *) exit 2 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        mock_gh.chmod(mock_gh.stat().st_mode | stat.S_IXUSR)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def invoke(
        self,
        *,
        origin_url: str = "git@github.com:snapetech-org/slskdN.git",
        origin_repo: str = "snapetech-org/slskdN",
        origin_id: str = REPOSITORY_ID,
        default_repo: str = "snapetech/slskdN",
        default_id: str = REPOSITORY_ID,
        upstream_url: str = EXPECTED_UPSTREAM,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "PATH": f"{self.bin}{os.pathsep}{environment.get('PATH', '')}",
                "MOCK_ORIGIN_URL": origin_url,
                "MOCK_UPSTREAM_URL": upstream_url,
                "MOCK_DEFAULT_REPO": default_repo,
                "MOCK_ORIGIN_REPO": origin_repo,
                "MOCK_ORIGIN_ID": origin_id,
                "MOCK_DEFAULT_REPO_PATH": default_repo,
                "MOCK_DEFAULT_ID": default_id,
            }
        )
        return subprocess.run(
            ["bash", str(GUARD)],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_accepts_canonical_and_legacy_names_for_the_same_repository(self) -> None:
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("GitHub target verified by repository ID", result.stdout)

    def test_accepts_https_and_ssh_github_remotes(self) -> None:
        for origin_url in (
            "https://github.com/snapetech-org/slskdN.git",
            "ssh://git@github.com/snapetech/slskdN.git",
        ):
            with self.subTest(origin_url=origin_url):
                result = self.invoke(
                    origin_url=origin_url,
                    origin_repo=(
                        "snapetech-org/slskdN"
                        if "snapetech-org" in origin_url
                        else "snapetech/slskdN"
                    ),
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_origin_that_resolves_to_another_repository(self) -> None:
        result = self.invoke(
            origin_url="git@github.com:other-owner/slskdN.git",
            origin_repo="other-owner/slskdN",
            origin_id=OTHER_REPOSITORY_ID,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected repository ID", result.stderr)

    def test_rejects_default_that_resolves_to_another_repository(self) -> None:
        result = self.invoke(
            default_repo="other-owner/slskdN",
            default_id=OTHER_REPOSITORY_ID,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected repository ID", result.stderr)

    def test_rejects_non_github_origin(self) -> None:
        result = self.invoke(origin_url="git@github.invalid:slskdN.git")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("recognized GitHub URL", result.stderr)

    def test_rejects_unexpected_upstream_remote(self) -> None:
        result = self.invoke(upstream_url="git@github.com:slskd/slskd.git")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("read-only reference", result.stderr)

    def test_allows_an_unconfigured_upstream_remote(self) -> None:
        result = self.invoke(upstream_url="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("upstream: <unset>", result.stdout)


if __name__ == "__main__":
    unittest.main()
