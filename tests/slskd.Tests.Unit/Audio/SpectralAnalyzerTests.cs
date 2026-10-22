// <copyright file="SpectralAnalyzerTests.cs" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Audio;

using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using slskd.Audio;
using Xunit;

public class SpectralAnalyzerTests
{
    [Fact]
    public void Classify_FindsMp3LowpassAndEstimatedBitrate()
    {
        var levels = CreateSpectrum(44100, 16600, 50);

        var result = SpectralAnalyzer.Classify(levels, 100, 44100, 4);

        Assert.Equal(SpectralVerdict.Lossy, result.Verdict);
        Assert.Equal(16600, result.EffectiveBandwidthHz);
        Assert.Equal(16600, result.NominalLowpassHz);
        Assert.InRange(result.HfEnergyRatio!.Value, 0, 0.01);
        Assert.Contains("MP3 128 kbps", result.Reason, StringComparison.Ordinal);
    }

    [Fact]
    public void Classify_PreservesGradualNaturalRolloff()
    {
        var levels = Enumerable.Range(0, 221).Select(index => -20.0 - (index * 0.2)).ToArray();

        var result = SpectralAnalyzer.Classify(levels, 100, 44100, 4);

        Assert.Equal(SpectralVerdict.Genuine, result.Verdict);
        Assert.Null(result.EffectiveBandwidthHz);
    }

    [Fact]
    public void Classify_ReportsBorderlineMasteringFilterAsReviewOnly()
    {
        var levels = CreateSpectrum(48000, 20500, 25);

        var result = SpectralAnalyzer.Classify(levels, 100, 48000, 4);

        Assert.Equal(SpectralVerdict.Suspect, result.Verdict);
        Assert.Equal(20500, result.EffectiveBandwidthHz);
        Assert.Contains("review", result.Reason, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Classify_IdentifiesHighResolutionUpsampling()
    {
        var levels = CreateSpectrum(96000, 22000, 45);

        var result = SpectralAnalyzer.Classify(levels, 100, 96000, 4);

        Assert.Equal(SpectralVerdict.Upsampled, result.Verdict);
        Assert.Equal(22000, result.EffectiveBandwidthHz);
    }

    [Fact]
    public void Classify_LeavesSilenceInconclusive()
    {
        var result = SpectralAnalyzer.Classify(Enumerable.Repeat(-300.0, 221).ToArray(), 100, 44100);

        Assert.Equal(SpectralVerdict.Inconclusive, result.Verdict);
        Assert.Null(result.EffectiveBandwidthHz);
    }

    [Fact]
    public async Task AnalyzeFileAsync_UsesConfiguredFfmpegAndBoundsDecodedWindows()
    {
        using var directory = new TemporaryDirectory();
        var filePath = Path.Combine(directory.Path, "track.flac");
        await File.WriteAllTextAsync(filePath, "fake input");

        var executableName = OperatingSystem.IsWindows() ? "slskd.Tests.FakeFfmpeg.exe" : "slskd.Tests.FakeFfmpeg";
        var ffmpegPath = Path.Combine(AppContext.BaseDirectory, "fake-ffmpeg", executableName);
        Assert.True(File.Exists(ffmpegPath), $"Expected fake ffmpeg at {ffmpegPath}");

        var result = await new SpectralAnalyzer().AnalyzeFileAsync(filePath, ffmpegPath, 44100, 90000, 4)
            .WaitAsync(TimeSpan.FromSeconds(15));

        Assert.Equal(SpectralVerdict.Lossy, result.Verdict);
        Assert.Equal(4, result.FramesAnalyzed);
        Assert.InRange(result.EffectiveBandwidthHz!.Value, 16400, 16800);
    }

    private static double[] CreateSpectrum(int sampleRateHz, double cutoffHz, double dropDb)
    {
        var bandCount = (int)(sampleRateHz / 2 / 100) + 1;
        return Enumerable.Range(0, bandCount)
            .Select(index => index * 100 < cutoffHz ? -20.0 : -20.0 - dropDb)
            .ToArray();
    }

    private sealed class TemporaryDirectory : IDisposable
    {
        public TemporaryDirectory()
        {
            Path = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"slskdn-spectral-test-{Guid.NewGuid():N}");
            Directory.CreateDirectory(Path);
        }

        public string Path { get; }

        public void Dispose()
        {
            if (Directory.Exists(Path))
            {
                Directory.Delete(Path, recursive: true);
            }
        }
    }
}
