#!/usr/bin/env python3
"""Fail if BenchmarkDotNet did not produce measured HashDb results."""

import json
import math
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


if len(sys.argv) != 2:
    fail(f"Usage: {Path(sys.argv[0]).name} <BenchmarkDotNet results directory>")

results_dir = Path(sys.argv[1])
reports = sorted(
    results_dir.glob("*HashDbPerformanceBenchmarks-report-full-compressed.json")
)
if len(reports) != 1:
    fail(f"Expected exactly one HashDb BenchmarkDotNet report in {results_dir}; found {len(reports)}")

expected_benchmark = (
    "slskd.Tests.Performance.HashDb.HashDbPerformanceBenchmarks.LookupHash_WithoutCache"
)
report_path = reports[0]
try:
    report = json.loads(report_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as error:
    fail(f"Could not read benchmark report {report_path}: {error}")

if not isinstance(report, dict):
    fail(f"{report_path.name}: report root is not an object")

benchmarks = report.get("Benchmarks")
if not isinstance(benchmarks, list) or len(benchmarks) != 1:
    fail(f"{report_path.name}: expected exactly one selected benchmark")

benchmark = benchmarks[0]
if not isinstance(benchmark, dict):
    fail(f"{report_path.name}: invalid benchmark entry")
if benchmark.get("FullName") != expected_benchmark:
    fail(f"{report_path.name}: unexpected benchmark {benchmark.get('FullName')!r}")

measurements = benchmark.get("Measurements")
statistics = benchmark.get("Statistics")
if not isinstance(measurements, list) or not isinstance(statistics, dict):
    fail(f"{expected_benchmark}: no completed measurements")

results = [
    measurement
    for measurement in measurements
    if isinstance(measurement, dict)
    and measurement.get("IterationMode") == "Workload"
    and measurement.get("IterationStage") == "Result"
]
if not results or any(
    not isinstance(result.get("Operations"), int)
    or isinstance(result.get("Operations"), bool)
    or result["Operations"] <= 0
    or not isinstance(result.get("Nanoseconds"), (int, float))
    or isinstance(result.get("Nanoseconds"), bool)
    or not math.isfinite(result["Nanoseconds"])
    or result["Nanoseconds"] <= 0
    for result in results
):
    fail(f"{expected_benchmark}: no valid workload result measurements")

count = statistics.get("N")
mean = statistics.get("Mean")
if (
    not isinstance(count, int)
    or isinstance(count, bool)
    or count != len(results)
    or not isinstance(mean, (int, float))
    or isinstance(mean, bool)
    or not math.isfinite(mean)
    or mean <= 0
):
    fail(f"{expected_benchmark}: invalid aggregate statistics")

print(f"Validated {count} workload measurements for {expected_benchmark}.")
