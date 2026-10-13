// <copyright file="FingerprintExtractionServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Integrations.Chromaprint;

using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using slskd.Integrations.Chromaprint;
using Xunit;
using ChromaprintOptions = slskd.Options.IntegrationOptions.ChromaprintOptions;

public class FingerprintExtractionServiceTests
{
    [Fact]
    public void GetMaximumPcmBytes_ReturnsExpectedBound()
    {
        var options = new ChromaprintOptions
        {
            SampleRate = 44100,
            Channels = 2,
            DurationSeconds = 120,
        };

        var maxBytes = FingerprintExtractionService.GetMaximumPcmBytes(options);

        Assert.Equal(21168000, maxBytes);
    }

    [Fact]
    public async Task ReadBoundedPcmAsync_ReturnsBufferWithinLimit()
    {
        var expected = new byte[4096];
        new Random(1234).NextBytes(expected);
        await using var stream = new MemoryStream(expected);

        var actual = await FingerprintExtractionService.ReadBoundedPcmAsync(stream, expected.Length, default);

        Assert.Equal(expected, actual);
    }

    [Fact]
    public async Task ReadBoundedPcmAsync_ThrowsWhenStreamExceedsLimit()
    {
        await using var stream = new MemoryStream(new byte[FingerprintExtractionService.CopyBufferSize + 1]);

        var ex = await Assert.ThrowsAsync<InvalidOperationException>(() =>
            FingerprintExtractionService.ReadBoundedPcmAsync(stream, FingerprintExtractionService.CopyBufferSize, default));

        Assert.Contains("more PCM output than expected", ex.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task ExtractFingerprintAsync_StartsProcessBeforeReadingStandardError()
    {
        var options = new slskd.Options
        {
            Integration = new slskd.Options.IntegrationOptions
            {
                Chromaprint = new ChromaprintOptions
                {
                    Enabled = true,
                    FfmpegPath = GetFakeFfmpegPath(),
                    SampleRate = 1,
                    Channels = 1,
                    DurationSeconds = 1,
                },
            },
        };
        var chromaprint = new Mock<IChromaprintService>();
        var service = new FingerprintExtractionService(
            chromaprint.Object,
            new TestOptionsMonitor<slskd.Options>(options),
            NullLogger<FingerprintExtractionService>.Instance);
        var filePath = Path.GetTempFileName();

        try
        {
            using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            var exception = await Assert.ThrowsAsync<InvalidOperationException>(() =>
                service.ExtractFingerprintAsync(filePath, cancellation.Token));

            Assert.Contains("no PCM output", exception.Message, StringComparison.Ordinal);
            Assert.DoesNotContain("StandardError has not been redirected", exception.Message, StringComparison.Ordinal);
        }
        finally
        {
            File.Delete(filePath);
        }
    }

    [Fact]
    public async Task ExtractFingerprintAsync_CancellationWaitsForTheFfmpegProcessTreeToExit()
    {
        if (OperatingSystem.IsWindows())
        {
            return;
        }

        var directory = Path.Combine(Path.GetTempPath(), $"slskdn-fingerprint-cancel-{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        var filePath = Path.Combine(directory, "audio.flac");
        var scriptPath = Path.Combine(directory, "fake-ffmpeg.sh");
        var pidPath = Path.Combine(directory, "pid");
        File.WriteAllText(filePath, "audio fixture");
        File.WriteAllText(scriptPath, "#!/bin/sh\nprintf '%s' \"$$\" > '" + pidPath + "'\nsleep 30\n");
        File.SetUnixFileMode(scriptPath, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);

        var options = new slskd.Options
        {
            Integration = new slskd.Options.IntegrationOptions
            {
                Chromaprint = new ChromaprintOptions
                {
                    Enabled = true,
                    FfmpegPath = scriptPath,
                    SampleRate = 1,
                    Channels = 1,
                    DurationSeconds = 1,
                },
            },
        };
        var service = new FingerprintExtractionService(
            Mock.Of<IChromaprintService>(),
            new TestOptionsMonitor<slskd.Options>(options),
            NullLogger<FingerprintExtractionService>.Instance);
        int? childProcessId = null;
        using var cancellation = new CancellationTokenSource(TimeSpan.FromMilliseconds(100));

        try
        {
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
                service.ExtractFingerprintAsync(filePath, cancellation.Token));

            Assert.True(File.Exists(pidPath));
            childProcessId = int.Parse(File.ReadAllText(pidPath), System.Globalization.CultureInfo.InvariantCulture);
            Assert.False(IsProcessRunning(childProcessId.Value));
        }
        finally
        {
            if (childProcessId is null && File.Exists(pidPath))
            {
                childProcessId = int.Parse(File.ReadAllText(pidPath), System.Globalization.CultureInfo.InvariantCulture);
            }

            if (childProcessId is not null)
            {
                StopProcessTreeIfRunning(childProcessId.Value);
            }

            Directory.Delete(directory, recursive: true);
        }
    }

    [Fact]
    public void FormatDiagnostic_ReturnsUsefulFallbackForEmptyOutput()
    {
        Assert.Equal("(no diagnostic output)", FingerprintExtractionService.FormatDiagnostic(" \n\t"));
        Assert.Equal("decoder failed", FingerprintExtractionService.FormatDiagnostic(" \ndecoder failed\n"));
    }

    [Fact]
    public void FormatDiagnostic_EscapesLogBreakingCharacters()
    {
        Assert.Equal("decoder failed\\r\\nforged", FingerprintExtractionService.FormatDiagnostic("decoder failed\r\nforged"));
    }

    private static string GetFakeFfmpegPath()
    {
        var executableName = OperatingSystem.IsWindows() ? "slskd.Tests.FakeFfmpeg.exe" : "slskd.Tests.FakeFfmpeg";
        return Path.Combine(AppContext.BaseDirectory, "fake-ffmpeg", executableName);
    }

    private static bool IsProcessRunning(int processId)
    {
        var isRunning = false;
        foreach (var process in Process.GetProcesses())
        {
            using (process)
            {
                if (process.Id == processId)
                {
                    isRunning = !process.HasExited;
                }
            }
        }

        return isRunning;
    }

    private static void StopProcessTreeIfRunning(int processId)
    {
        foreach (var process in Process.GetProcesses())
        {
            using (process)
            {
                if (process.Id == processId && !process.HasExited)
                {
                    process.Kill(entireProcessTree: true);
                    process.WaitForExit(5000);
                }
            }
        }
    }
}
