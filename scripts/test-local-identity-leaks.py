#!/usr/bin/env python3
"""Contract tests for the local identity leak scanner."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
SCANNER = REPOSITORY_ROOT / "scripts" / "check-local-identity-leaks.sh"


@unittest.skipUnless(shutil.which("rg") and shutil.which("jq"), "rg and jq are required")
class LocalIdentityScannerTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(prefix="identity-scan-contract-")
        self.root = Path(self.temporary_directory.name) / "repo"
        (self.root / "scripts").mkdir(parents=True)
        (self.root / "docs").mkdir()
        shutil.copyfile(SCANNER, self.root / "scripts" / "check-local-identity-leaks.sh")
        self.fake_bin = Path(self.temporary_directory.name) / "bin"
        self.fake_bin.mkdir()
        self._write_executable("hostname", "#!/bin/sh\nprintf '%s\\n' 'synthetic-host'\n")
        self._write_executable(
            "id",
            "#!/bin/sh\nif [ \"${1:-}\" = '-un' ]; then printf '%s\\n' 'synthetic-user'; fi\n",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_executable(self, name, contents):
        executable = self.fake_bin / name
        executable.write_text(contents, encoding="utf-8")
        executable.chmod(0o755)

    def _git(self, *arguments):
        result = subprocess.run(
            ["git", *arguments], cwd=self.root, text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def _initialize_repository(self, changelog, subject=None):
        (self.root / "docs" / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
        self._git("init", "--quiet")
        self._git("config", "user.name", "Scanner Contract Test")
        self._git("config", "user.email", "scanner-test@example.invalid")
        self._git("add", "--all")
        self._git("commit", "--quiet", "-m", "fixture baseline")
        self._git("tag", "build-main-fixture")
        if subject:
            self._git("commit", "--quiet", "--allow-empty", "-m", subject)

    def _run_scanner(self, **overrides):
        environment = os.environ.copy()
        environment.update(
            {
                "PATH": f"{self.fake_bin}{os.pathsep}{environment.get('PATH', '')}",
                "HOME": "/validation/task/home",
                "USER": "synthetic-user",
                "LOCAL_IDENTITY_DENYLIST": "",
                "LOCAL_IDENTITY_DENYLIST_FILE": "",
                "SLSKDN_LOCAL_IDENTITY_DENYLIST": "",
                "SLSKDN_LOCAL_IDENTITY_DENYLIST_FILE": "",
                "SLSKDN_FORBIDDEN_LOCAL_HOSTNAME": "",
                "LOCAL_IDENTITY_SCAN_COMMITS": "1",
                "LOCAL_IDENTITY_SCAN_RUNTIME_IDENTITIES": "1",
            }
        )
        environment.update(overrides)
        return subprocess.run(
            ["bash", str(self.root / "scripts" / "check-local-identity-leaks.sh")],
            cwd=self.root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_plain_identity_matches_whole_words_in_commit_messages(self):
        changelog = "## [Unreleased]\n\nNo release text.\n\n## [1.0.0]\n"
        self._initialize_repository(changelog, "docs: inspect runtime probe homes")

        plural_result = self._run_scanner(
            LOCAL_IDENTITY_DENYLIST="home",
            LOCAL_IDENTITY_SCAN_RUNTIME_IDENTITIES="0",
        )
        exact_result = self._run_scanner(
            LOCAL_IDENTITY_DENYLIST="homes",
            LOCAL_IDENTITY_SCAN_RUNTIME_IDENTITIES="0",
        )

        self.assertEqual(plural_result.returncode, 0, plural_result.stderr)
        self.assertNotEqual(exact_result.returncode, 0)
        self.assertIn("recent commit messages", exact_result.stderr)

    def test_sandbox_runtime_home_is_not_treated_as_operator_identity(self):
        changelog = "## [Unreleased]\n\nNo release text.\n\n## [1.0.0]\n"
        self._initialize_repository(changelog, "docs: inspect home")

        isolated_result = self._run_scanner(LOCAL_IDENTITY_SCAN_RUNTIME_IDENTITIES="0")
        runtime_result = self._run_scanner(LOCAL_IDENTITY_SCAN_RUNTIME_IDENTITIES="1")

        self.assertEqual(isolated_result.returncode, 0, isolated_result.stderr)
        self.assertNotEqual(runtime_result.returncode, 0)
        self.assertIn("recent commit messages", runtime_result.stderr)

    def test_explicit_path_tokens_still_scan_release_copy_literally(self):
        changelog = (
            "## [Unreleased]\n\n"
            "Example local destination: /srv/private/operator/downloads.\n\n"
            "## [1.0.0]\n"
        )
        self._initialize_repository(changelog)

        result = self._run_scanner(
            LOCAL_IDENTITY_DENYLIST="/srv/private/operator",
            LOCAL_IDENTITY_SCAN_COMMITS="0",
            LOCAL_IDENTITY_SCAN_RUNTIME_IDENTITIES="0",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("docs/CHANGELOG.md Unreleased", result.stderr)


if __name__ == "__main__":
    unittest.main()
