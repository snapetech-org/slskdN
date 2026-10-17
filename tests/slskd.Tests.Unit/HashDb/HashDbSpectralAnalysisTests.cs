// <copyright file="HashDbSpectralAnalysisTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.HashDb;

using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Moq;
using slskd.Audio;
using slskd.HashDb;
using Xunit;

public class HashDbSpectralAnalysisTests : IDisposable
{
    private readonly string testDir = Path.Combine(Path.GetTempPath(), $"hashdb-spectral-{Guid.NewGuid()}");
    private readonly Mock<ISpectralAnalyzer> analyzer = new();
    private readonly HashDbService service;

    public HashDbSpectralAnalysisTests()
    {
        Directory.CreateDirectory(testDir);
        service = new HashDbService(testDir, spectralAnalyzer: analyzer.Object);
    }

    public void Dispose()
    {
        slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={Path.Combine(testDir, "hashdb.db")}");
        Directory.Delete(testDir, recursive: true);
    }

    [Fact]
    public async Task ApplySpectralAnalysisAsync_WhenDownloadAnalysisIsOff_DoesNotDecode()
    {
        analyzer.SetupGet(a => a.AnalyzeCompletedDownloads).Returns(false);
        var variant = Flac();

        await service.ApplySpectralAnalysisAsync(variant, "track.flac");

        analyzer.Verify(
            a => a.AnalyzeAsync(It.IsAny<string>(), It.IsAny<int>(), It.IsAny<double>(), It.IsAny<CancellationToken>()),
            Times.Never);
        Assert.Null(variant.EffectiveBandwidthHz);
    }

    [Fact]
    public async Task ApplySpectralAnalysisAsync_SkipsLossyCodecs()
    {
        analyzer.SetupGet(a => a.AnalyzeCompletedDownloads).Returns(true);
        var variant = Flac();
        variant.Codec = "MP3";

        await service.ApplySpectralAnalysisAsync(variant, "track.mp3");

        analyzer.Verify(
            a => a.AnalyzeAsync(It.IsAny<string>(), It.IsAny<int>(), It.IsAny<double>(), It.IsAny<CancellationToken>()),
            Times.Never);
    }

    [Fact]
    public async Task ApplySpectralAnalysisAsync_RecordsALossyVerdictOnTheVariant()
    {
        analyzer.SetupGet(a => a.AnalyzeCompletedDownloads).Returns(true);
        analyzer
            .Setup(a => a.AnalyzeAsync("track.flac", 44100, 240, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new SpectralAnalysisResult
            {
                Verdict = SpectralVerdict.Lossy,
                SampleRateHz = 44100,
                CutoffHz = 16600,
                AboveShelfDb = -50,
                EstimatedSource = "MP3 128 kbps",
            });
        var variant = Flac();

        await service.ApplySpectralAnalysisAsync(variant, "track.flac");

        Assert.True(variant.TranscodeSuspect);
        Assert.Equal(16600, variant.EffectiveBandwidthHz);
        Assert.StartsWith("spectral: lossy shelf at 16.6 kHz", variant.TranscodeReason);
    }

    [Fact]
    public async Task ApplySpectralAnalysisAsync_AnalyzerFailureLeavesTheVariantAsBuilt()
    {
        analyzer.SetupGet(a => a.AnalyzeCompletedDownloads).Returns(true);
        analyzer
            .Setup(a => a.AnalyzeAsync(It.IsAny<string>(), It.IsAny<int>(), It.IsAny<double>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("decoder crashed"));
        var variant = Flac();

        await service.ApplySpectralAnalysisAsync(variant, "track.flac");

        Assert.False(variant.TranscodeSuspect);
        Assert.Null(variant.EffectiveBandwidthHz);
        Assert.Equal(1.0, variant.QualityScore);
    }

    private static AudioVariant Flac() => new()
    {
        Codec = "FLAC",
        SampleRateHz = 44100,
        BitDepth = 16,
        Channels = 2,
        DurationMs = 240_000,
        BitrateKbps = 900,
        QualityScore = 1.0,
    };
}
