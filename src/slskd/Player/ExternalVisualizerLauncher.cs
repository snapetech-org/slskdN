// <copyright file="ExternalVisualizerLauncher.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Player;

using System;
using System.Diagnostics;
using System.IO;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

public interface IExternalVisualizerLauncher
{
    ExternalVisualizerStatus GetStatus();

    ExternalVisualizerLaunchResult Launch();
}

public interface IExternalProcessStarter
{
    int Start(ProcessStartInfo startInfo);
}

public sealed class ExternalProcessStarter : IExternalProcessStarter
{
    public int Start(ProcessStartInfo startInfo)
    {
        // nosemgrep: csharp.lang.security.injections.os-command.os-command-injection -- this starts an administrator-configured executable with UseShellExecute=false and the caller-populated ArgumentList.
        using var process = Process.Start(startInfo);
        return process?.Id ?? 0;
    }
}

public sealed class ExternalVisualizerLauncher : IExternalVisualizerLauncher
{
    private readonly IOptionsMonitor<global::slskd.Options> _options;
    private readonly IExternalProcessStarter _starter;
    private readonly ILogger<ExternalVisualizerLauncher> _logger;

    public ExternalVisualizerLauncher(
        IOptionsMonitor<global::slskd.Options> options,
        IExternalProcessStarter starter,
        ILogger<ExternalVisualizerLauncher> logger)
    {
        _options = options;
        _starter = starter;
        _logger = logger;
    }

    public ExternalVisualizerStatus GetStatus()
    {
        var options = _options.CurrentValue.Player.ExternalVisualizer;
        var configuredPath = options.Path?.Trim() ?? string.Empty;
        var resolvedPath = ResolveExecutablePath(configuredPath);
        var workingDirectory = ResolveWorkingDirectory(options.WorkingDirectory, resolvedPath);

        return new ExternalVisualizerStatus(
            Enabled: options.Enabled,
            Configured: !string.IsNullOrWhiteSpace(configuredPath),
            Available: resolvedPath != null,
            Name: string.IsNullOrWhiteSpace(options.Name) ? "External visualizer" : options.Name.Trim(),
            Path: configuredPath,
            ResolvedPath: resolvedPath,
            WorkingDirectory: workingDirectory,
            Arguments: options.Arguments ?? Array.Empty<string>());
    }

    public ExternalVisualizerLaunchResult Launch()
    {
        var status = GetStatus();
        if (!status.Enabled)
        {
            return ExternalVisualizerLaunchResult.NotStarted("External visualizer launching is disabled in configuration.");
        }

        if (status.ResolvedPath == null)
        {
            return ExternalVisualizerLaunchResult.NotStarted("External visualizer path is not configured or does not exist.");
        }

        var startInfo = new ProcessStartInfo
        {
            FileName = status.ResolvedPath,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        if (!string.IsNullOrWhiteSpace(status.WorkingDirectory))
        {
            startInfo.WorkingDirectory = status.WorkingDirectory;
        }

        foreach (var argument in status.Arguments)
        {
            if (!string.IsNullOrWhiteSpace(argument))
            {
                startInfo.ArgumentList.Add(argument);
            }
        }

        try
        {
            var processId = _starter.Start(startInfo);
            _logger.LogInformation("Started external visualizer {Name} from {Path}", status.Name, status.ResolvedPath);
            return ExternalVisualizerLaunchResult.Success(status.Name, processId);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to start external visualizer {Path}", status.ResolvedPath);
            return ExternalVisualizerLaunchResult.NotStarted(ex.Message);
        }
    }

    private static string? ResolveExecutablePath(string? executablePath)
    {
        if (string.IsNullOrWhiteSpace(executablePath))
        {
            return null;
        }

        var trimmed = executablePath.Trim();
        if (HasDirectoryComponent(trimmed))
        {
            return File.Exists(trimmed) ? Path.GetFullPath(trimmed) : null;
        }

        var path = Environment.GetEnvironmentVariable("PATH");
        if (string.IsNullOrWhiteSpace(path))
        {
            return null;
        }

        foreach (var directory in path.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            var candidate = Path.Combine(directory, trimmed);
            if (File.Exists(candidate))
            {
                return candidate;
            }

            if (OperatingSystem.IsWindows() && !Path.HasExtension(trimmed))
            {
                foreach (var extension in GetWindowsExecutableExtensions())
                {
                    candidate = Path.Combine(directory, trimmed + extension);
                    if (File.Exists(candidate))
                    {
                        return candidate;
                    }
                }
            }
        }

        return null;
    }

    private static string? ResolveWorkingDirectory(string? configuredWorkingDirectory, string? resolvedPath)
    {
        if (!string.IsNullOrWhiteSpace(configuredWorkingDirectory))
        {
            return Directory.Exists(configuredWorkingDirectory)
                ? Path.GetFullPath(configuredWorkingDirectory)
                : null;
        }

        return resolvedPath == null ? null : Path.GetDirectoryName(resolvedPath);
    }

    private static bool HasDirectoryComponent(string executablePath)
    {
        return Path.IsPathRooted(executablePath) ||
            executablePath.Contains(Path.DirectorySeparatorChar) ||
            executablePath.Contains(Path.AltDirectorySeparatorChar);
    }

    private static string[] GetWindowsExecutableExtensions()
    {
        var pathExt = Environment.GetEnvironmentVariable("PATHEXT");
        return string.IsNullOrWhiteSpace(pathExt)
            ? new[] { ".EXE", ".BAT", ".CMD", ".COM" }
            : pathExt.Split(';', StringSplitOptions.RemoveEmptyEntries);
    }
}

public sealed record ExternalVisualizerStatus(
    bool Enabled,
    bool Configured,
    bool Available,
    string Name,
    string Path,
    string? ResolvedPath,
    string? WorkingDirectory,
    string[] Arguments);

public sealed record ExternalVisualizerLaunchResult(
    bool Started,
    string? Name,
    int? ProcessId,
    string? Error)
{
    public static ExternalVisualizerLaunchResult Success(string name, int processId)
    {
        return new ExternalVisualizerLaunchResult(true, name, processId <= 0 ? null : processId, null);
    }

    public static ExternalVisualizerLaunchResult NotStarted(string error)
    {
        return new ExternalVisualizerLaunchResult(false, null, null, error);
    }
}
