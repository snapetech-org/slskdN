#!/usr/bin/env python3
"""Contract tests for the required BenchmarkDotNet report validator."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("verify-benchmark-results.py")
REPORT_NAME = "HashDbPerformanceBenchmarks-report-full-compressed.json"
BENCHMARK = (
    "slskd.Tests.Performance.HashDb.HashDbPerformanceBenchmarks.LookupHash_WithoutCache"
)


class BenchmarkResultVerifierTests(unittest.TestCase):
    def test_workflow_output_matches_verifier_and_upload_path(self) -> None:
        repository = SCRIPT.parents[1]
        workflow = (repository / ".github/workflows/ci-enhancements.yml").read_text(
            encoding="utf-8"
        )
        artifacts = "tests/slskd.Tests.Performance/BenchmarkDotNet.Artifacts"
        results = f"{artifacts}/results"

        self.assertIn(f"--artifacts {artifacts}", workflow)
        self.assertGreaterEqual(workflow.count(results), 3)

    def run_verifier(self, report: object | None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="slskdn-benchmark-verifier-") as temp:
            results = Path(temp)
            if report is not None:
                (results / REPORT_NAME).write_text(json.dumps(report), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(results)],
                capture_output=True,
                check=False,
                text=True,
            )

    def test_valid_workload_measurement_passes(self) -> None:
        report = {
            "Benchmarks": [
                {
                    "FullName": BENCHMARK,
                    "Measurements": [
                        {
                            "IterationMode": "Workload",
                            "IterationStage": "Result",
                            "Operations": 1,
                            "Nanoseconds": 135956.0,
                        }
                    ],
                    "Statistics": {"N": 1, "Mean": 135956.0},
                }
            ]
        }

        result = self.run_verifier(report)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Validated 1 workload measurements", result.stdout)

    def test_missing_report_fails(self) -> None:
        result = self.run_verifier(None)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("found 0", result.stderr)

    def test_non_object_report_fails_with_validation_error(self) -> None:
        result = self.run_verifier([])

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("report root is not an object", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_report_without_selected_benchmark_fails(self) -> None:
        result = self.run_verifier({"Benchmarks": []})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected exactly one selected benchmark", result.stderr)


if __name__ == "__main__":
    unittest.main()
