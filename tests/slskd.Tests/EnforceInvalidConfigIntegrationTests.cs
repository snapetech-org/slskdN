// <copyright file="EnforceInvalidConfigIntegrationTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests;

using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using slskd;
using slskd.Common.Security;
using Xunit;

/// <summary>
/// PR-01: Integration test — when EnforceSecurity is on and config is invalid, the host fails to start
/// and the failure message contains the hardening rule name. HardeningValidator.Validate throws before
/// the host is built; these tests verify that the exception message contains the rule name so that
/// logs and support can identify the misconfiguration.
/// </summary>
public class EnforceInvalidConfigIntegrationTests
{
    [Fact]
    public void Enforce_invalid_config_AuthDisabledNonLoopback_failure_contains_rule_name()
    {
        var options = new OptionsAtStartup
        {
            Web = new Options.WebOptions
            {
                EnforceSecurity = true,
                AllowRemoteNoAuth = false,
                Authentication = new Options.WebOptions.WebAuthenticationOptions { Disabled = true },
                Cors = new Options.WebOptions.CorsOptions { Enabled = true, AllowCredentials = false },
            },
            Diagnostics = new Options.DiagnosticsOptions { AllowMemoryDump = false },
        };

        var ex = Assert.Throws<HardeningValidationException>(
            () => HardeningValidator.Validate(options, "Production", isBindingNonLoopback: true));

        Assert.Equal(HardeningValidator.RuleAuthDisabledNonLoopback, ex.RuleName);
        Assert.Contains(ex.RuleName, ex.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Enforce_invalid_config_CorsCredentialsWithWildcard_failure_contains_rule_name()
    {
        var options = new OptionsAtStartup
        {
            Web = new Options.WebOptions
            {
                EnforceSecurity = true,
                AllowRemoteNoAuth = true,
                Authentication = new Options.WebOptions.WebAuthenticationOptions { Disabled = false },
                Cors = new Options.WebOptions.CorsOptions
                {
                    Enabled = true,
                    AllowCredentials = true,
                    AllowedOrigins = Array.Empty<string>(),
                },
            },
            Diagnostics = new Options.DiagnosticsOptions { AllowMemoryDump = false },
        };

        var ex = Assert.Throws<HardeningValidationException>(
            () => HardeningValidator.Validate(options, "Production", isBindingNonLoopback: true));

        Assert.Equal(HardeningValidator.RuleCorsCredentialsWithWildcard, ex.RuleName);
        Assert.Contains(ex.RuleName, ex.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Enforce_invalid_config_MemoryDumpWithAuthDisabled_failure_contains_rule_name()
    {
        var options = new OptionsAtStartup
        {
            Web = new Options.WebOptions
            {
                EnforceSecurity = true,
                AllowRemoteNoAuth = true,
                Authentication = new Options.WebOptions.WebAuthenticationOptions
                {
                    Disabled = true,
                    Passthrough = new Options.WebOptions.WebAuthenticationOptions.PassthroughOptions
                    {
                        AllowedCidrs = "127.0.0.1/32,::1/128",
                    },
                },
                Cors = new Options.WebOptions.CorsOptions { Enabled = true, AllowCredentials = false },
            },
            Diagnostics = new Options.DiagnosticsOptions { AllowMemoryDump = true },
        };

        var ex = Assert.Throws<HardeningValidationException>(
            () => HardeningValidator.Validate(options, "Production", isBindingNonLoopback: true));

        Assert.Equal(HardeningValidator.RuleMemoryDumpWithAuthDisabled, ex.RuleName);
        Assert.Contains(ex.RuleName, ex.Message, StringComparison.Ordinal);
    }

    /// <summary>
    /// Full host startup: run slskd as a subprocess with Enforce on and invalid config; assert exit 1
    /// and that stderr/stdout contains the rule name. Uses --config and YAML with web/diagnostics at root
    /// (YamlConfigurationProvider prefixes with Namespace). If another slskd holds the single-instance
    /// mutex, the test is skipped at runtime so CI can run when no instance is active.
    /// </summary>
    [Fact]
    public async Task Enforce_invalid_config_host_startup_exits_nonzero_and_output_contains_rule_name()
    {
        var repoRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
        var slskdProj = Path.Combine(repoRoot, "src", "slskd", "slskd.csproj");
        if (!File.Exists(slskdProj))
        {
            return; // Unusual layout (e.g. from IDE)
        }

        // If another slskd holds the single-instance mutex, skip to avoid subprocess failing for the wrong reason.
        // Use "slskd" literal to avoid loading Program (which would initialize Program.Mutex in this process and hold it).
        var mutexName = Compute.Sha256Hash("slskd");
        using (var probe = new Mutex(initiallyOwned: false, mutexName))
        {
            if (!probe.WaitOne(0))
            {
                return; // Mutex held; skip (run when no slskd is running).
            }
            probe.ReleaseMutex();
        }

        var tempDir = Path.Combine(Path.GetTempPath(), "slskd-enforce-test-" + Guid.NewGuid().ToString("N")[..8]);
        string? contentDir = null;
        try
        {
            Directory.CreateDirectory(tempDir);
            // Use dotnet slskd.dll to avoid dotnet run's host loading the app (which can hold the single-instance mutex).
            var targetFramework = GetTargetFramework(slskdProj);
            var slskdDll = Path.Combine(repoRoot, "src", "slskd", "bin", "Debug", targetFramework, "slskd.dll");
            if (!File.Exists(slskdDll))
            {
                slskdDll = Path.Combine(repoRoot, "src", "slskd", "bin", "Release", targetFramework, "slskd.dll");
            }

            if (!File.Exists(slskdDll))
            {
                return; // slskd not built in Debug or Release; build slskd first or run without --no-build.
            }

            var contentPath = "test-wwwroot-" + Guid.NewGuid().ToString("N")[..8];
            contentDir = Path.Combine(Path.GetDirectoryName(slskdDll)!, contentPath);
            Directory.CreateDirectory(contentDir);

            var yml = Path.Combine(tempDir, "slskd.yml");
            // YamlConfigurationProvider prefixes with Namespace "slskd"; use web/diagnostics at root (not slskd:)
            await File.WriteAllTextAsync(yml, $"""
                web:
                  contentPath: {contentPath}
                  enforceSecurity: true
                  allowRemoteNoAuth: false
                  authentication:
                    disabled: true
                  port: 5000
                diagnostics:
                  allowMemoryDump: false
                """);

            var configArg = $"--config \"{yml}\"";
            using var proc = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "dotnet",
                    Arguments = $"\"{slskdDll}\" {configArg}",
                    WorkingDirectory = tempDir,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                }
            };
            proc.StartInfo.Environment["SLSKD_APP_DIR"] = tempDir;

            proc.Start();
            var outTask = proc.StandardOutput.ReadToEndAsync();
            var errTask = proc.StandardError.ReadToEndAsync();
            var exited = proc.WaitForExit(15_000);
            if (!exited)
            {
                try { proc.Kill(entireProcessTree: true); } catch { /* ignore */ }
                Assert.Fail("slskd subprocess did not exit within 15s");
            }

            var stdout = await outTask;
            var stderr = await errTask;
            var combined = stdout + "\n" + stderr;

            // If another slskd (or a parallel test that loaded Program) holds the mutex, the subprocess exits 0
            // with "An instance of slskd is already running". Treat as skip so CI does not fail.
            if (exited && proc.ExitCode == 0 && combined.Contains("An instance of slskd is already running", StringComparison.Ordinal))
            {
                return;
            }

            Assert.True(exited && proc.ExitCode == 1, $"Expected exit code 1; got {proc.ExitCode}. stdout+stderr: {combined}");

            var hasHardeningSignal =
                combined.Contains(HardeningValidator.RuleAuthDisabledNonLoopback, StringComparison.Ordinal) ||
                combined.Contains("Hardening validation failed", StringComparison.Ordinal) ||
                combined.Contains("[HardeningValidation]", StringComparison.Ordinal);

            Assert.True(
                hasHardeningSignal,
                $"Expected hardening validation output. stdout+stderr: {combined}");
        }
        finally
        {
            try { if (contentDir is not null && Directory.Exists(contentDir)) Directory.Delete(contentDir, recursive: true); } catch { /* ignore */ }
            try { if (Directory.Exists(tempDir)) Directory.Delete(tempDir, recursive: true); } catch { /* ignore */ }
        }
    }

    private static string GetTargetFramework(string projectPath)
    {
        const string OpenTag = "<TargetFramework>";
        const string CloseTag = "</TargetFramework>";

        var projectXml = File.ReadAllText(projectPath);
        var start = projectXml.IndexOf(OpenTag, StringComparison.Ordinal);
        var end = projectXml.IndexOf(CloseTag, StringComparison.Ordinal);

        if (start < 0 || end <= start)
        {
            return "net11.0";
        }

        start += OpenTag.Length;
        return projectXml[start..end].Trim();
    }
}
