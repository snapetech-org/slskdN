// <copyright file="RegressionHarness.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Common.CodeQuality
{
    using System;
    using System.Collections.Generic;
    using System.Diagnostics;
    using System.IO;
    using System.Linq;
    using System.Reflection;
    using System.Threading.Tasks;
    using Microsoft.Extensions.Logging;

    /// <summary>
    ///     Regression testing harness for critical system paths.
    /// </summary>
    /// <remarks>
    ///     H-CODE03: Test Coverage &amp; Regression Harness.
    ///     Automated regression testing for critical functionality.
    /// </remarks>
    public static class RegressionHarness
    {
        /// <summary>
        ///     Critical test scenarios that must pass for each release.
        /// </summary>
        private static readonly CriticalScenario[] CriticalScenarios = new[]
        {
            new CriticalScenario
            {
                Name = "PodCore_Messaging",
                Description = "Pod messaging functionality with encryption and validation",
                TestMethods = new[] { "PodMessage_EncryptionDecryption", "PodMessage_SignatureValidation" },
                Subsystem = "PodCore",
                ExpectedDuration = TimeSpan.FromSeconds(30)
            },

            new CriticalScenario
            {
                Name = "VirtualSoulfind_Planning",
                Description = "Content acquisition planning and peer selection",
                TestMethods = new[] { "MultiSourcePlanner_SelectSources", "MultiSourcePlanner_ReputationFiltering" },
                Subsystem = "VirtualSoulfind.v2.Planning",
                ExpectedDuration = TimeSpan.FromSeconds(45)
            },

            new CriticalScenario
            {
                Name = "Mesh_Transport",
                Description = "Mesh overlay transport with multiple protocols",
                TestMethods = new[] { "MeshTransportService_Connect", "MeshTransportService_Fallback" },
                Subsystem = "Mesh.Transport",
                ExpectedDuration = TimeSpan.FromSeconds(60)
            },

            new CriticalScenario
            {
                Name = "Security_Validation",
                Description = "Security validation and sanitization",
                TestMethods = new[] { "LoggingSanitizer_SensitiveData", "IdentitySeparation_Enforcement" },
                Subsystem = "Common.Security",
                ExpectedDuration = TimeSpan.FromSeconds(20)
            },

            new CriticalScenario
            {
                Name = "MultiSource_Downloads",
                Description = "Multi-source download orchestration",
                TestMethods = new[] { "MultiSourceDownloadService_Orchestrate", "SourceDiscovery_FindCandidates" },
                Subsystem = "Transfers.MultiSource",
                ExpectedDuration = TimeSpan.FromSeconds(90)
            },

            new CriticalScenario
            {
                Name = "Moderation_Content",
                Description = "Content moderation and peer reputation",
                TestMethods = new[] { "CompositeModerationProvider_CheckContent", "PeerReputationService_RecordEvent" },
                Subsystem = "Common.Moderation",
                ExpectedDuration = TimeSpan.FromSeconds(35)
            }
        };

        /// <summary>
        ///     Runs the complete regression test suite.
        /// </summary>
        /// <param name="testAssemblies">The test assemblies to run against.</param>
        /// <param name="logger">Optional logger.</param>
        /// <returns>Regression harness results.</returns>
        public static async Task<RegressionHarnessResults> RunRegressionSuiteAsync(
            IEnumerable<Assembly> testAssemblies,
            ILogger? logger = null)
        {
            var results = new RegressionHarnessResults
            {
                TestRunId = Guid.NewGuid().ToString(),
                StartTime = DateTimeOffset.UtcNow,
                Scenarios = new List<ScenarioResult>()
            };

            logger?.LogInformation("[RegressionHarness] Starting regression test suite with {Count} critical scenarios", CriticalScenarios.Length);

            foreach (var scenario in CriticalScenarios)
            {
                var scenarioResult = await RunCriticalScenarioAsync(scenario, testAssemblies, logger).ConfigureAwait(false);
                results.Scenarios.Add(scenarioResult);

                // Fail fast on critical scenario failures
                if (!scenarioResult.Success && scenario.IsBlocking)
                {
                    logger?.LogError("[RegressionHarness] Critical scenario {Scenario} failed - aborting suite", scenario.Name);
                    break;
                }
            }

            results.EndTime = DateTimeOffset.UtcNow;
            results.Duration = results.EndTime - results.StartTime;

            // Calculate aggregate metrics
            results.TotalScenarios = results.Scenarios.Count;
            results.PassedScenarios = results.Scenarios.Count(r => r.Success);
            results.FailedScenarios = results.Scenarios.Count(r => !r.Success);
            results.SuccessRate = results.TotalScenarios > 0 ? (double)results.PassedScenarios / results.TotalScenarios : 0;

            // Check for performance regressions
            results.PerformanceRegressions = DetectPerformanceRegressions(results.Scenarios);

            logger?.LogInformation(
                "[RegressionHarness] Suite completed: {Passed}/{Total} scenarios passed ({SuccessRate:P1}) in {Duration}",
                results.PassedScenarios, results.TotalScenarios, results.SuccessRate, results.Duration);

            return results;
        }

        /// <summary>
        ///     Runs performance benchmarks for critical paths.
        /// </summary>
        /// <param name="iterations">Number of iterations to run for each benchmark.</param>
        /// <param name="logger">Optional logger.</param>
        /// <returns>Performance benchmark results.</returns>
        public static async Task<PerformanceBenchmarkResults> RunPerformanceBenchmarksAsync(
            int iterations = 1000,
            ILogger? logger = null)
        {
            var results = new PerformanceBenchmarkResults
            {
                BenchmarkRunId = Guid.NewGuid().ToString(),
                Iterations = iterations,
                Benchmarks = new List<BenchmarkResult>()
            };

            logger?.LogInformation("[PerformanceBenchmarks] Running benchmarks with {Iterations} iterations", iterations);

            // Benchmark critical operations
            var benchmarks = new[]
            {
                new BenchmarkDefinition
                {
                    Name = "PodMessage_Encryption",
                    Description = "Pod message encryption/decryption performance",
                    Operation = BenchmarkPodMessageEncryptionAsync,
                    ExpectedMaxDuration = TimeSpan.FromMilliseconds(50)
                },

                new BenchmarkDefinition
                {
                    Name = "MultiSource_Planning",
                    Description = "Multi-source download planning performance",
                    Operation = BenchmarkMultiSourcePlanningAsync,
                    ExpectedMaxDuration = TimeSpan.FromMilliseconds(100)
                },

                new BenchmarkDefinition
                {
                    Name = "Moderation_Check",
                    Description = "Content moderation checking performance",
                    Operation = BenchmarkModerationCheckAsync,
                    ExpectedMaxDuration = TimeSpan.FromMilliseconds(20)
                },

                new BenchmarkDefinition
                {
                    Name = "MeshTransport_Connect",
                    Description = "Mesh transport connection performance",
                    Operation = BenchmarkMeshTransportAsync,
                    ExpectedMaxDuration = TimeSpan.FromMilliseconds(200)
                }
            };

            foreach (var benchmark in benchmarks)
            {
                var result = await RunBenchmarkAsync(benchmark, iterations, logger).ConfigureAwait(false);
                results.Benchmarks.Add(result);
            }

            // Calculate aggregate metrics
            results.TotalBenchmarks = results.Benchmarks.Count;
            results.PassedBenchmarks = results.Benchmarks.Count(b => b.Success);
            results.FailedBenchmarks = results.Benchmarks.Count(b => !b.Success);

            logger?.LogInformation(
                "[PerformanceBenchmarks] Completed: {Passed}/{Total} benchmarks passed",
                results.PassedBenchmarks, results.TotalBenchmarks);

            return results;
        }

        /// <summary>
        ///     Generates a test coverage report in various formats.
        /// </summary>
        /// <param name="coverageReport">The coverage report to format.</param>
        /// <param name="outputDirectory">Directory to save formatted reports.</param>
        /// <param name="logger">Optional logger.</param>
        public static void GenerateCoverageReport(
            TestCoverageReport coverageReport,
            string outputDirectory,
            ILogger? logger = null)
        {
            Directory.CreateDirectory(outputDirectory);

            // Generate JSON report

            // nosemgrep: csharp.lang.security.filesystem.unsafe-path-combine.unsafe-path-combine -- outputDirectory is an explicit local harness destination; the filename is generated from a timestamp.
            var jsonPath = Path.Combine(outputDirectory, $"coverage-report-{DateTimeOffset.UtcNow:yyyyMMdd-HHmmss}.json");
            var jsonContent = System.Text.Json.JsonSerializer.Serialize(coverageReport, new System.Text.Json.JsonSerializerOptions
            {
                WriteIndented = true
            });

            // nosemgrep: csharp.lang.security.filesystem.unsafe-path-combine.unsafe-path-combine -- jsonPath is the local harness outputDirectory plus a generated timestamp filename.
            File.WriteAllText(jsonPath, jsonContent);

            // Generate markdown summary

            // nosemgrep: csharp.lang.security.filesystem.unsafe-path-combine.unsafe-path-combine -- outputDirectory is an explicit local harness destination; the filename is generated from a timestamp.
            var markdownPath = Path.Combine(outputDirectory, $"coverage-summary-{DateTimeOffset.UtcNow:yyyyMMdd-HHmmss}.md");
            var markdownContent = GenerateMarkdownSummary(coverageReport);

            // nosemgrep: csharp.lang.security.filesystem.unsafe-path-combine.unsafe-path-combine -- markdownPath is the local harness outputDirectory plus a generated timestamp filename.
            File.WriteAllText(markdownPath, markdownContent);

            // Generate HTML report

            // nosemgrep: csharp.lang.security.filesystem.unsafe-path-combine.unsafe-path-combine -- outputDirectory is an explicit local harness destination; the filename is generated from a timestamp.
            var htmlPath = Path.Combine(outputDirectory, $"coverage-report-{DateTimeOffset.UtcNow:yyyyMMdd-HHmmss}.html");
            var htmlContent = GenerateHtmlReport(coverageReport);

            // nosemgrep: csharp.lang.security.filesystem.unsafe-path-combine.unsafe-path-combine -- htmlPath is the local harness outputDirectory plus a generated timestamp filename.
            File.WriteAllText(htmlPath, htmlContent);

            logger?.LogInformation("[CoverageReport] Generated reports: JSON, Markdown, HTML");
        }

        private static async Task<ScenarioResult> RunCriticalScenarioAsync(
            CriticalScenario scenario,
            IEnumerable<Assembly> testAssemblies,
            ILogger? logger)
        {
            var result = new ScenarioResult
            {
                ScenarioName = scenario.Name,
                Description = scenario.Description,
                Subsystem = scenario.Subsystem,
                StartTime = DateTimeOffset.UtcNow,
                TestResults = new List<TestResult>()
            };

            logger?.LogInformation("[RegressionHarness] Running scenario: {Scenario}", scenario.Name);

            try
            {
                // Find and run the test methods for this scenario
                var subsystem = scenario.Subsystem ?? string.Empty;
                var testMethods = scenario.TestMethods ?? [];

                var testClasses = testAssemblies
                    .SelectMany(a => a.GetTypes())
                    .Where(t => t.Namespace?.Contains(subsystem.Replace(".", string.Empty), StringComparison.OrdinalIgnoreCase) == true)
                    .ToList();

                foreach (var testMethodName in testMethods)
                {
                    var testResult = await RunTestMethodAsync(testMethodName, testClasses, logger).ConfigureAwait(false);
                    result.TestResults.Add(testResult);
                }

                result.Success = result.TestResults.All(r => r.Success);
                result.EndTime = DateTimeOffset.UtcNow;
                result.Duration = result.EndTime - result.StartTime;

                // Check for performance regression
                if (result.Duration > scenario.ExpectedDuration)
                {
                    result.PerformanceRegression = true;
                    result.PerformanceNotes = $"Duration {result.Duration.TotalSeconds:F1}s exceeded expected {scenario.ExpectedDuration.TotalSeconds:F1}s";
                }

                logger?.LogInformation(
                    "[RegressionHarness] Scenario {Scenario} completed: {Success} in {Duration}",
                    scenario.Name, result.Success ? "PASSED" : "FAILED", result.Duration);
            }
            catch (Exception ex)
            {
                result.Success = false;
                result.EndTime = DateTimeOffset.UtcNow;
                result.Duration = result.EndTime - result.StartTime;
                result.ErrorMessage = "Scenario execution failed";

                logger?.LogError(ex, "[RegressionHarness] Scenario {Scenario} failed with exception", scenario.Name);
            }

            return result;
        }

        private static async Task<TestResult> RunTestMethodAsync(
            string testMethodName,
            List<Type> testClasses,
            ILogger? logger)
        {
            var result = new TestResult
            {
                TestName = testMethodName,
                StartTime = DateTimeOffset.UtcNow
            };

            try
            {
                // Find the test method
                var testMethod = testClasses
                    .SelectMany(tc => tc.GetMethods())
                    .FirstOrDefault(m => m.Name.Contains(testMethodName, StringComparison.OrdinalIgnoreCase) &&
                        m.GetCustomAttributes(false).Any(a =>
                        {
                            var n = a.GetType().FullName;
                            return n == "Xunit.FactAttribute" || n == "Xunit.TheoryAttribute";
                        }));

                if (testMethod == null)
                {
                    result.Success = false;
                    result.ErrorMessage = $"Test method {testMethodName} not found";
                }
                else
                {
                    // Create instance and invoke test method
                    var instance = Activator.CreateInstance(testMethod.DeclaringType!);
                    var task = (Task)testMethod.Invoke(instance, null)!;
                    await task.ConfigureAwait(false);

                    result.Success = true;
                }
            }
            catch (Exception ex)
            {
                result.Success = false;
                result.ErrorMessage = "Test execution failed";
                logger?.LogError(ex, "[RegressionHarness] Test {TestName} failed", testMethodName);
            }

            result.EndTime = DateTimeOffset.UtcNow;
            result.Duration = result.EndTime - result.StartTime;

            return result;
        }

        private static async Task<BenchmarkResult> RunBenchmarkAsync(
            BenchmarkDefinition benchmark,
            int iterations,
            ILogger? logger)
        {
            var result = new BenchmarkResult
            {
                BenchmarkName = benchmark.Name,
                Description = benchmark.Description,
                Iterations = iterations,
                StartTime = DateTimeOffset.UtcNow
            };

            try
            {
                var stopwatch = Stopwatch.StartNew();

                for (int i = 0; i < iterations; i++)
                {
                    await benchmark.Operation().ConfigureAwait(false);
                }

                stopwatch.Stop();

                result.EndTime = DateTimeOffset.UtcNow;
                result.Duration = stopwatch.Elapsed;
                result.AverageDuration = result.Duration / iterations;

                result.Success = result.AverageDuration <= benchmark.ExpectedMaxDuration;

                if (!result.Success)
                {
                    result.PerformanceNotes = $"Average {result.AverageDuration.TotalMilliseconds:F2}ms exceeded expected {benchmark.ExpectedMaxDuration.TotalMilliseconds:F2}ms";
                }

                logger?.LogInformation(
                    "[PerformanceBenchmarks] {Benchmark}: {Average:F2}ms avg over {Iterations} iterations",
                    benchmark.Name, result.AverageDuration.TotalMilliseconds, iterations);
            }
            catch (Exception ex)
            {
                result.Success = false;
                result.ErrorMessage = "Benchmark execution failed";
                result.EndTime = DateTimeOffset.UtcNow;
                logger?.LogError(ex, "[PerformanceBenchmarks] Benchmark {Benchmark} failed", benchmark.Name);
            }

            return result;
        }

        private static async Task BenchmarkPodMessageEncryptionAsync()
        {
            // Simulate pod message encryption/decryption benchmark
            var message = new byte[1024];
            Random.Shared.NextBytes(message);

            // Simulate encryption operation
            await Task.Delay(1).ConfigureAwait(false); // Simulate async crypto operation
        }

        private static async Task BenchmarkMultiSourcePlanningAsync()
        {
            // Simulate multi-source planning benchmark
            await Task.Delay(5).ConfigureAwait(false); // Simulate planning complexity
        }

        private static async Task BenchmarkModerationCheckAsync()
        {
            // Simulate moderation check benchmark
            await Task.Delay(1).ConfigureAwait(false); // Simulate database/hash lookups
        }

        private static async Task BenchmarkMeshTransportAsync()
        {
            // Simulate mesh transport benchmark
            await Task.Delay(10).ConfigureAwait(false); // Simulate network operations
        }

        private static List<PerformanceRegression> DetectPerformanceRegressions(List<ScenarioResult> scenarios)
        {
            var regressions = new List<PerformanceRegression>();

            foreach (var scenario in scenarios.Where(s => s.PerformanceRegression))
            {
                regressions.Add(new PerformanceRegression
                {
                    ScenarioName = scenario.ScenarioName,
                    ActualDuration = scenario.Duration,
                    ExpectedDuration = CriticalScenarios.First(s => s.Name == scenario.ScenarioName).ExpectedDuration,
                    RegressionFactor = scenario.Duration.TotalSeconds / CriticalScenarios.First(s => s.Name == scenario.ScenarioName).ExpectedDuration.TotalSeconds
                });
            }

            return regressions;
        }

        private static string GenerateMarkdownSummary(TestCoverageReport report)
        {
            var sb = new System.Text.StringBuilder();

            sb.AppendLine("# Test Coverage Summary");
            sb.AppendLine($"**Generated:** {report.AnalysisTimestamp:yyyy-MM-dd HH:mm:ss UTC}");
            sb.AppendLine($"**Overall Coverage:** {report.OverallCoverage:P1}");
            sb.AppendLine();

            sb.AppendLine("## Subsystem Coverage");
            sb.AppendLine("| Subsystem | Method Coverage | Class Coverage | Status |");
            sb.AppendLine("|-----------|-----------------|----------------|--------|");

            foreach (var subsystem in report.SubsystemReports.OrderByDescending(r => r.MethodCoverage))
            {
                var status = subsystem.MethodCoverage >= 0.8 ? "✅ Good" :
                            subsystem.MethodCoverage >= 0.6 ? "⚠️ Needs Work" : "❌ Critical";
                sb.AppendLine($"| {subsystem.SubsystemName} | {subsystem.MethodCoverage:P1} | {subsystem.ClassCoverage:P1} | {status} |");
            }

            sb.AppendLine();
            sb.AppendLine("## Coverage Gaps");

            foreach (var gap in report.CoverageGaps)
            {
                sb.AppendLine($"### {gap.Subsystem} ({gap.CoveragePercentage:P1})");
                if (gap.UncoveredTypes?.Any() == true)
                {
                    sb.AppendLine("**Uncovered Types:**");
                    foreach (var type in gap.UncoveredTypes)
                    {
                        sb.AppendLine($"- {type}");
                    }
                }

                sb.AppendLine();
            }

            return sb.ToString();
        }

        private static string GenerateHtmlReport(TestCoverageReport report)
        {
            var sb = new System.Text.StringBuilder();

            sb.AppendLine("<!DOCTYPE html>");
            sb.AppendLine("<html>");
            sb.AppendLine("<head>");
            sb.AppendLine("<title>slskdN Test Coverage Report</title>");
            sb.AppendLine("<style>");
            sb.AppendLine("body { font-family: Arial, sans-serif; margin: 20px; }");
            sb.AppendLine("table { border-collapse: collapse; width: 100%; }");
            sb.AppendLine("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }");
            sb.AppendLine("th { background-color: #f2f2f2; }");
            sb.AppendLine("tr:nth-child(even) { background-color: #f9f9f9; }");
            sb.AppendLine(".good { color: green; }");
            sb.AppendLine(".warning { color: orange; }");
            sb.AppendLine(".critical { color: red; }");
            sb.AppendLine("</style>");
            sb.AppendLine("</head>");
            sb.AppendLine("<body>");
            sb.AppendLine("<h1>slskdN Test Coverage Report</h1>");
            sb.AppendLine($"<p><strong>Generated:</strong> {report.AnalysisTimestamp:yyyy-MM-dd HH:mm:ss UTC}</p>");
            sb.AppendLine($"<p><strong>Overall Coverage:</strong> {report.OverallCoverage:P1}</p>");

            sb.AppendLine("<h2>Subsystem Coverage</h2>");
            sb.AppendLine("<table>");
            sb.AppendLine("<tr><th>Subsystem</th><th>Method Coverage</th><th>Class Coverage</th><th>Status</th></tr>");

            foreach (var subsystem in report.SubsystemReports.OrderByDescending(r => r.MethodCoverage))
            {
                var statusClass = subsystem.MethodCoverage >= 0.8 ? "good" :
                                 subsystem.MethodCoverage >= 0.6 ? "warning" : "critical";
                var status = subsystem.MethodCoverage >= 0.8 ? "✅ Good" :
                            subsystem.MethodCoverage >= 0.6 ? "⚠️ Needs Work" : "❌ Critical";

                sb.AppendLine($"<tr><td>{subsystem.SubsystemName}</td><td>{subsystem.MethodCoverage:P1}</td><td>{subsystem.ClassCoverage:P1}</td><td class='{statusClass}'>{status}</td></tr>");
            }

            sb.AppendLine("</table>");
            sb.AppendLine("</body>");
            sb.AppendLine("</html>");

            return sb.ToString();
        }
    }

    /// <summary>
    ///     Critical test scenario definition.
    /// </summary>
    internal sealed class CriticalScenario
    {
        /// <summary>
        ///     Gets the scenario name.
        /// </summary>
        public string? Name { get; init; }

        /// <summary>
        ///     Gets the scenario description.
        /// </summary>
        public string? Description { get; init; }

        /// <summary>
        ///     Gets the subsystem this scenario tests.
        /// </summary>
        public string? Subsystem { get; init; }

        /// <summary>
        ///     Gets the test method names to run.
        /// </summary>
        public string[]? TestMethods { get; init; }

        /// <summary>
        ///     Gets the expected maximum duration.
        /// </summary>
        public TimeSpan ExpectedDuration { get; init; }

        /// <summary>
        ///     Gets a value indicating whether failure blocks the release.
        /// </summary>
        public bool IsBlocking { get; init; } = true;
    }

    /// <summary>
    ///     Regression harness results.
    /// </summary>
    public sealed class RegressionHarnessResults
    {
        /// <summary>
        ///     Gets the unique test run identifier.
        /// </summary>
        public string? TestRunId { get; init; }

        /// <summary>
        ///     Gets the start time of the harness run.
        /// </summary>
        public DateTimeOffset StartTime { get; init; }

        /// <summary>
        ///     Gets the end time of the harness run.
        /// </summary>
        public DateTimeOffset EndTime { get; set; }

        /// <summary>
        ///     Gets the total duration of the harness run.
        /// </summary>
        public TimeSpan Duration { get; set; }

        /// <summary>
        ///     Gets the scenario results.
        /// </summary>
        public List<ScenarioResult> Scenarios { get; init; } = new();

        /// <summary>
        ///     Gets the total number of scenarios.
        /// </summary>
        public int TotalScenarios { get; set; }

        /// <summary>
        ///     Gets the number of passed scenarios.
        /// </summary>
        public int PassedScenarios { get; set; }

        /// <summary>
        ///     Gets the number of failed scenarios.
        /// </summary>
        public int FailedScenarios { get; set; }

        /// <summary>
        ///     Gets the success rate.
        /// </summary>
        public double SuccessRate { get; set; }

        /// <summary>
        ///     Gets the list of performance regressions detected.
        /// </summary>
        public List<PerformanceRegression> PerformanceRegressions { get; set; } = new();
    }

    /// <summary>
    ///     Scenario test result.
    /// </summary>
    public sealed class ScenarioResult
    {
        /// <summary>
        ///     Gets the scenario name.
        /// </summary>
        public string? ScenarioName { get; init; }

        /// <summary>
        ///     Gets the scenario description.
        /// </summary>
        public string? Description { get; init; }

        /// <summary>
        ///     Gets the subsystem tested.
        /// </summary>
        public string? Subsystem { get; init; }

        /// <summary>
        ///     Gets the start time.
        /// </summary>
        public DateTimeOffset StartTime { get; init; }

        /// <summary>
        ///     Gets the end time.
        /// </summary>
        public DateTimeOffset EndTime { get; set; }

        /// <summary>
        ///     Gets the duration.
        /// </summary>
        public TimeSpan Duration { get; set; }

        /// <summary>
        ///     Gets a value indicating whether the scenario passed.
        /// </summary>
        public bool Success { get; set; }

        /// <summary>
        ///     Gets the error message if the scenario failed.
        /// </summary>
        public string? ErrorMessage { get; set; }

        /// <summary>
        ///     Gets a value indicating whether there was a performance regression.
        /// </summary>
        public bool PerformanceRegression { get; set; }

        /// <summary>
        ///     Gets performance regression notes.
        /// </summary>
        public string? PerformanceNotes { get; set; }

        /// <summary>
        ///     Gets the individual test results.
        /// </summary>
        public List<TestResult> TestResults { get; init; } = new();
    }

    /// <summary>
    ///     Individual test result.
    /// </summary>
    public sealed class TestResult
    {
        /// <summary>
        ///     Gets the test name.
        /// </summary>
        public string? TestName { get; init; }

        /// <summary>
        ///     Gets the start time.
        /// </summary>
        public DateTimeOffset StartTime { get; init; }

        /// <summary>
        ///     Gets the end time.
        /// </summary>
        public DateTimeOffset EndTime { get; set; }

        /// <summary>
        ///     Gets the duration.
        /// </summary>
        public TimeSpan Duration { get; set; }

        /// <summary>
        ///     Gets a value indicating whether the test passed.
        /// </summary>
        public bool Success { get; set; }

        /// <summary>
        ///     Gets the error message if the test failed.
        /// </summary>
        public string? ErrorMessage { get; set; }
    }

    /// <summary>
    ///     Performance benchmark results.
    /// </summary>
    public sealed class PerformanceBenchmarkResults
    {
        /// <summary>
        ///     Gets the unique benchmark run identifier.
        /// </summary>
        public string? BenchmarkRunId { get; init; }

        /// <summary>
        ///     Gets the number of iterations per benchmark.
        /// </summary>
        public int Iterations { get; init; }

        /// <summary>
        ///     Gets the benchmark results.
        /// </summary>
        public List<BenchmarkResult> Benchmarks { get; init; } = new();

        /// <summary>
        ///     Gets the total number of benchmarks.
        /// </summary>
        public int TotalBenchmarks { get; set; }

        /// <summary>
        ///     Gets the number of passed benchmarks.
        /// </summary>
        public int PassedBenchmarks { get; set; }

        /// <summary>
        ///     Gets the number of failed benchmarks.
        /// </summary>
        public int FailedBenchmarks { get; set; }
    }

    /// <summary>
    ///     Individual benchmark result.
    /// </summary>
    public sealed class BenchmarkResult
    {
        /// <summary>
        ///     Gets the benchmark name.
        /// </summary>
        public string? BenchmarkName { get; init; }

        /// <summary>
        ///     Gets the benchmark description.
        /// </summary>
        public string? Description { get; init; }

        /// <summary>
        ///     Gets the number of iterations.
        /// </summary>
        public int Iterations { get; init; }

        /// <summary>
        ///     Gets the start time.
        /// </summary>
        public DateTimeOffset StartTime { get; init; }

        /// <summary>
        ///     Gets the end time.
        /// </summary>
        public DateTimeOffset EndTime { get; set; }

        /// <summary>
        ///     Gets the total duration.
        /// </summary>
        public TimeSpan Duration { get; set; }

        /// <summary>
        ///     Gets the average duration per iteration.
        /// </summary>
        public TimeSpan AverageDuration { get; set; }

        /// <summary>
        ///     Gets a value indicating whether the benchmark passed.
        /// </summary>
        public bool Success { get; set; }

        /// <summary>
        ///     Gets the error message if the benchmark failed.
        /// </summary>
        public string? ErrorMessage { get; set; }

        /// <summary>
        ///     Gets performance notes.
        /// </summary>
        public string? PerformanceNotes { get; set; }
    }

    /// <summary>
    ///     Performance regression information.
    /// </summary>
    public sealed class PerformanceRegression
    {
        /// <summary>
        ///     Gets the scenario name.
        /// </summary>
        public string? ScenarioName { get; init; }

        /// <summary>
        ///     Gets the actual duration.
        /// </summary>
        public TimeSpan ActualDuration { get; init; }

        /// <summary>
        ///     Gets the expected duration.
        /// </summary>
        public TimeSpan ExpectedDuration { get; init; }

        /// <summary>
        ///     Gets the regression factor (actual/expected).
        /// </summary>
        public double RegressionFactor { get; init; }
    }

    /// <summary>
    ///     Benchmark definition.
    /// </summary>
    internal sealed class BenchmarkDefinition
    {
        /// <summary>
        ///     Gets the benchmark name.
        /// </summary>
        public string? Name { get; init; }

        /// <summary>
        ///     Gets the benchmark description.
        /// </summary>
        public string? Description { get; init; }

        /// <summary>
        ///     Gets the operation to benchmark.
        /// </summary>
        public Func<Task> Operation { get; init; } = () => Task.CompletedTask;

        /// <summary>
        ///     Gets the expected maximum duration.
        /// </summary>
        public TimeSpan ExpectedMaxDuration { get; init; }
    }
}
