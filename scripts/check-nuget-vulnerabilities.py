#!/usr/bin/env python3
"""Fail when any first-party .NET project resolves a vulnerable NuGet package."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOTS = (REPOSITORY_ROOT / "src", REPOSITORY_ROOT / "tests", REPOSITORY_ROOT / "tools")
PACKAGE_GROUPS = ("topLevelPackages", "transitivePackages")


def main() -> int:
    projects = sorted(
        project
        for project_root in PROJECT_ROOTS
        for project in project_root.rglob("*.csproj")
    )
    if not projects:
        print("No first-party .NET projects were found to audit.", file=sys.stderr)
        return 1

    environment = os.environ.copy()
    environment["VERSION"] = "0.0.0"
    findings: list[str] = []

    for project in projects:
        relative_project = project.relative_to(REPOSITORY_ROOT)
        print(f"Auditing {relative_project}", flush=True)
        result = subprocess.run(
            [
                "dotnet",
                "list",
                str(project),
                "package",
                "--vulnerable",
                "--include-transitive",
                "--format",
                "json",
            ],
            cwd=REPOSITORY_ROOT,
            env=environment,
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode != 0:
            print(result.stdout, end="", file=sys.stderr)
            print(result.stderr, end="", file=sys.stderr)
            print(f"NuGet vulnerability scan failed for {relative_project}.", file=sys.stderr)
            return 1

        try:
            report = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            print(f"NuGet returned invalid JSON for {relative_project}: {error}", file=sys.stderr)
            return 1

        for project_report in report.get("projects", []):
            for framework in project_report.get("frameworks", []):
                framework_name = framework.get("framework", "unknown framework")
                for group_name in PACKAGE_GROUPS:
                    for package in framework.get(group_name, []):
                        vulnerabilities = package.get("vulnerabilities", [])
                        for vulnerability in vulnerabilities:
                            findings.append(
                                "{} [{}] {} {} ({}) {}".format(
                                    relative_project,
                                    framework_name,
                                    package.get("id", "unknown package"),
                                    package.get("resolvedVersion", "unknown version"),
                                    vulnerability.get("severity", "unknown severity"),
                                    vulnerability.get("advisoryurl", "advisory URL unavailable"),
                                )
                            )

    if findings:
        print("Vulnerable NuGet packages were found:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1

    print(f"No vulnerable NuGet packages found across {len(projects)} first-party projects.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
