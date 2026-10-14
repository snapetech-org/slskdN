#!/usr/bin/env python3
"""Contract tests for the hosted release-gate receipt verifier."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts/verify-hosted-release-gate.sh"
COMMIT = "a" * 40
WORKFLOW_ID = 123456
REPOSITORY_ID = 1108894784


class HostedReleaseGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="hosted-release-gate-")
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.data = self.root / "responses"
        self.bin.mkdir()
        self.data.mkdir()
        mock_gh = self.bin / "gh"
        mock_gh.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "case \"${2:-}\" in\n"
            "  repos/snapetech/slskdN) cat \"$MOCK_GH_DIR/repository.json\" ;;\n"
            "  repos/snapetech/slskdN/actions/workflows/ci.yml) cat \"$MOCK_GH_DIR/workflow.json\" ;;\n"
            "  repos/snapetech/slskdN/actions/runs/*) cat \"$MOCK_GH_DIR/run.json\" ;;\n"
            "  *) echo \"Unexpected API path: ${2:-}\" >&2; exit 3 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        mock_gh.chmod(mock_gh.stat().st_mode | stat.S_IXUSR)
        self.write_workflow()
        self.write_target_repository()
        self.run_data: dict[str, object] = {
            "workflow_id": WORKFLOW_ID,
            "repository": {"id": REPOSITORY_ID, "full_name": "snapetech-org/slskdN"},
            "event": "workflow_dispatch",
            "head_branch": "main",
            "head_sha": COMMIT,
            "status": "completed",
            "conclusion": "success",
            "html_url": "https://github.com/snapetech/slskdN/actions/runs/987654",
        }
        self.write_run()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_workflow(self, *, workflow_id: int = WORKFLOW_ID, path: str = ".github/workflows/ci.yml") -> None:
        (self.data / "workflow.json").write_text(
            json.dumps({"id": workflow_id, "path": path}), encoding="utf-8"
        )

    def write_target_repository(self, *, repository_id: int = REPOSITORY_ID) -> None:
        (self.data / "repository.json").write_text(
            json.dumps({"id": repository_id, "full_name": "snapetech-org/slskdN"}),
            encoding="utf-8",
        )

    def write_run(self) -> None:
        (self.data / "run.json").write_text(json.dumps(self.run_data), encoding="utf-8")

    def invoke(self, *, branch: str = "main", commit: str = COMMIT) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PATH"] = f"{self.bin}{os.pathsep}{environment.get('PATH', '')}"
        environment["MOCK_GH_DIR"] = str(self.data)
        return subprocess.run(
            [str(VERIFIER), "987654", branch, commit],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_accepts_a_successful_dispatch_for_the_exact_main_commit(self) -> None:
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Hosted CI release gate passed", result.stdout)
        self.assertIn("/actions/runs/987654", result.stdout)

    def test_rejects_a_run_for_a_different_commit(self) -> None:
        self.run_data["head_sha"] = "b" * 40
        self.write_run()
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("did not pass the release gate", result.stderr)

    def test_rejects_non_dispatch_runs(self) -> None:
        self.run_data["event"] = "push"
        self.write_run()
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)

    def test_rejects_failed_runs(self) -> None:
        self.run_data["conclusion"] = "failure"
        self.write_run()
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)

    def test_rejects_runs_from_another_repository(self) -> None:
        self.run_data["repository"] = {"id": 12345, "full_name": "slskd/slskd"}
        self.write_run()
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)

    def test_rejects_an_alias_that_resolves_to_another_repository(self) -> None:
        self.write_target_repository(repository_id=12345)
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected repository ID", result.stderr)

    def test_rejects_a_mismatched_workflow_path(self) -> None:
        self.write_workflow(path=".github/workflows/other.yml")
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("workflow path", result.stderr)

    def test_requires_main_and_a_full_commit_id(self) -> None:
        self.assertNotEqual(self.invoke(branch="feature").returncode, 0)
        self.assertNotEqual(self.invoke(commit="deadbeef").returncode, 0)


if __name__ == "__main__":
    unittest.main()
