// <copyright file="MultiSourceDownloadServiceSanitizationTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Transfers.MultiSource;

using System.IO;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using slskd.Common.Security;
using slskd.Integrations.Chromaprint;
using slskd.MediaCore;
using slskd.Transfers.MultiSource;
using Soulseek;
using Xunit;

public class MultiSourceDownloadServiceSanitizationTests
{
    [Fact]
    public async Task DownloadAsync_WithMixedSources_SequentialFailoverSkipsMeshOverlaySources()
    {
        var client = new Mock<ISoulseekClient>();
        client
            .Setup(c => c.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (
                string username,
                string remoteFilename,
                Func<Task<Stream>> outputStreamFactory,
                long size,
                long startOffset,
                int? token,
                TransferOptions options,
                CancellationToken cancellationToken) =>
            {
                var bytes = new byte[] { 1, 2, 3, 4 };
                var stream = await outputStreamFactory().ConfigureAwait(false);
                await stream.WriteAsync(bytes, 0, bytes.Length, cancellationToken).ConfigureAwait(false);

                return new Transfer(
                    TransferDirection.Download,
                    username,
                    remoteFilename,
                    token ?? 1,
                    TransferStates.Completed | TransferStates.Succeeded,
                    size,
                    startOffset,
                    bytes.Length);
            });

        var service = new MultiSourceDownloadService(
            NullLogger<MultiSourceDownloadService>.Instance,
            client.Object,
            Mock.Of<IContentVerificationService>());

        var outputPath = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid():N}.bin");

        try
        {
            var result = await service.DownloadAsync(
                new MultiSourceDownloadRequest
                {
                    Filename = "song.flac",
                    FileSize = 4,
                    OutputPath = outputPath,
                    Sources =
                    [
                        new VerifiedSource
                        {
                            Username = "mesh-peer",
                            FullPath = "mesh://song.flac",
                            Method = VerificationMethod.MeshOverlay,
                        },
                        new VerifiedSource
                        {
                            Username = "soulseek-peer",
                            FullPath = @"Music\song.flac",
                            Method = VerificationMethod.ContentSha256,
                        },
                    ],
                },
                CancellationToken.None);

            Assert.NotNull(result);
            client.Verify(
                c => c.DownloadAsync(
                    "mesh-peer",
                    It.IsAny<string>(),
                    It.IsAny<Func<Task<Stream>>>(),
                    It.IsAny<long>(),
                    It.IsAny<long>(),
                    It.IsAny<int?>(),
                    It.IsAny<TransferOptions>(),
                    It.IsAny<CancellationToken>()),
                Times.Never);
            client.Verify(
                c => c.DownloadAsync(
                    "soulseek-peer",
                    @"Music\song.flac",
                    It.IsAny<Func<Task<Stream>>>(),
                    4,
                    0,
                    It.IsAny<int?>(),
                    It.IsAny<TransferOptions>(),
                    It.IsAny<CancellationToken>()),
                Times.Once);
        }
        finally
        {
            if (System.IO.File.Exists(outputPath))
            {
                System.IO.File.Delete(outputPath);
            }
        }
    }

    [Fact]
    public async Task DownloadAsync_WhenTopLevelDownloadFlowThrows_ReturnsSanitizedErrorMessage()
    {
        var service = new MultiSourceDownloadService(
            NullLogger<MultiSourceDownloadService>.Instance,
            Mock.Of<ISoulseekClient>(),
            Mock.Of<IContentVerificationService>());

        var result = await service.DownloadAsync(
            new MultiSourceDownloadRequest
            {
                Filename = "song.flac",
                FileSize = 0,
                OutputPath = "\0invalid-output-path",
                Sources =
                [
                    new VerifiedSource
                    {
                        Username = "alice",
                        FullPath = @"Music\song.flac",
                    },
                ],
            },
            CancellationToken.None);

        Assert.False(result.Success);
        Assert.Equal("Output path is outside allowed download or temporary directories", result.Error);
        Assert.DoesNotContain("invalid", result.Error, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task FindVerifiedSourcesAsync_WhenSafetyLimiterExhausted_DoesNotSearchSoulseek()
    {
        var client = new Mock<ISoulseekClient>(MockBehavior.Strict);
        var safetyLimiter = new Mock<ISoulseekSafetyLimiter>();
        safetyLimiter
            .Setup(limiter => limiter.TryConsumeSearch("multisource-source-discovery"))
            .Returns(false);

        var service = new MultiSourceDownloadService(
            NullLogger<MultiSourceDownloadService>.Instance,
            client.Object,
            Mock.Of<IContentVerificationService>(),
            soulseekSafetyLimiter: safetyLimiter.Object);

        var result = await service.FindVerifiedSourcesAsync(
            @"Music\song.flac",
            1234,
            cancellationToken: CancellationToken.None);

        Assert.Equal(@"Music\song.flac", result.Filename);
        Assert.Equal(1234, result.FileSize);
        client.Verify(
            c => c.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken>()),
            Times.Never);
    }

    [Fact]
    public async Task FindVerifiedSourcesAsync_EscapesLogBreakingSearchTextAndPreservesFilename()
    {
        var query = "alpha\r\nforged.flac";
        var logger = new Mock<ILogger<MultiSourceDownloadService>>();
        logger.Setup(entry => entry.IsEnabled(LogLevel.Information)).Returns(true);
        var safetyLimiter = new Mock<ISoulseekSafetyLimiter>();
        safetyLimiter
            .Setup(limiter => limiter.TryConsumeSearch("multisource-source-discovery"))
            .Returns(false);
        var service = new MultiSourceDownloadService(
            logger.Object,
            Mock.Of<ISoulseekClient>(),
            Mock.Of<IContentVerificationService>(),
            soulseekSafetyLimiter: safetyLimiter.Object);

        var result = await service.FindVerifiedSourcesAsync(query, 1234, cancellationToken: CancellationToken.None);

        Assert.Equal(query, result.Filename);
        logger.Verify(
            entry => entry.Log(
                LogLevel.Information,
                It.IsAny<EventId>(),
                It.Is<It.IsAnyType>((state, _) =>
                    state.ToString()!.Contains("alpha\\r\\nforged") &&
                    !state.ToString()!.Contains(query)),
                It.IsAny<System.Exception?>(),
                It.IsAny<System.Func<It.IsAnyType, System.Exception?, string>>()),
            Times.Once);
    }

    [Fact]
    public async Task FindVerifiedSourcesAsync_WhenCallerCancelsMediaCoreDiscovery_PropagatesCancellation()
    {
        var discoveryStarted = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var mediaCore = new Mock<IMediaCoreSwarmService>();
        mediaCore
            .Setup(service => service.DiscoverContentVariantsAsync(
                It.IsAny<string>(),
                It.IsAny<long>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (string filename, long fileSize, CancellationToken cancellationToken) =>
            {
                discoveryStarted.TrySetResult();
                await Task.Delay(Timeout.Infinite, cancellationToken);
                return new ContentVariantsResult(
                    filename,
                    fileSize,
                    Array.Empty<ContentVariant>(),
                    new Dictionary<string, double>());
            });
        var service = new MultiSourceDownloadService(
            NullLogger<MultiSourceDownloadService>.Instance,
            Mock.Of<ISoulseekClient>(),
            Mock.Of<IContentVerificationService>(),
            mediaCoreSwarmService: mediaCore.Object);
        using var cancellation = new CancellationTokenSource();

        var discovery = service.FindVerifiedSourcesAsync("song.flac", 512, cancellationToken: cancellation.Token);
        await discoveryStarted.Task.WaitAsync(TimeSpan.FromSeconds(30));
        cancellation.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => discovery.WaitAsync(TimeSpan.FromSeconds(30)));
    }

    [Fact]
    public async Task FindVerifiedSourcesAsync_WhenCallerCancelsSoulseekSearch_PropagatesCancellation()
    {
        var searchStarted = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var client = new Mock<ISoulseekClient>();
        client
            .Setup(soulseekClient => soulseekClient.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (
                SearchQuery _,
                Action<SearchResponse> _,
                SearchScope _,
                int? _,
                SearchOptions _,
                CancellationToken cancellationToken) =>
            {
                searchStarted.TrySetResult();
                await Task.Delay(Timeout.Infinite, cancellationToken);
                return null!;
            });
        var service = new MultiSourceDownloadService(
            NullLogger<MultiSourceDownloadService>.Instance,
            client.Object,
            Mock.Of<IContentVerificationService>());
        using var cancellation = new CancellationTokenSource();

        var search = service.FindVerifiedSourcesAsync("song.flac", 512, cancellationToken: cancellation.Token);
        await searchStarted.Task.WaitAsync(TimeSpan.FromSeconds(30));
        cancellation.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => search.WaitAsync(TimeSpan.FromSeconds(30)));
    }

    [Fact]
    public async Task DownloadAsync_WhenCallerCancelsChunkDownload_PropagatesCancellationAndCleansUp()
    {
        var downloadStarted = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var client = new Mock<ISoulseekClient>();
        client
            .Setup(soulseekClient => soulseekClient.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (
                string username,
                string remoteFilename,
                Func<Task<Stream>> outputStreamFactory,
                long size,
                long startOffset,
                int? token,
                TransferOptions transferOptions,
                CancellationToken cancellationToken) =>
            {
                downloadStarted.TrySetResult();
                await Task.Delay(Timeout.Infinite, cancellationToken);
                return new Transfer(
                    TransferDirection.Download,
                    username,
                    remoteFilename,
                    token ?? 1,
                    TransferStates.Completed | TransferStates.Succeeded,
                    size,
                    startOffset,
                    512);
            });
        var service = new MultiSourceDownloadService(
            NullLogger<MultiSourceDownloadService>.Instance,
            client.Object,
            Mock.Of<IContentVerificationService>());
        var requestId = Guid.NewGuid();
        var request = new MultiSourceDownloadRequest
        {
            Id = requestId,
            Filename = "song.flac",
            FileSize = 512,
            ChunkSize = 512,
            OutputPath = Path.Combine(Path.GetTempPath(), $"{requestId:N}.flac"),
            Sources =
            [
                new VerifiedSource
                {
                    Username = "mesh-peer",
                    FullPath = "mesh://song.flac",
                    Method = VerificationMethod.MeshOverlay,
                },
            ],
        };
        var tempDirectory = Path.Combine(Path.GetTempPath(), "slskdn-multidownload", requestId.ToString());
        using var cancellation = new CancellationTokenSource();

        var download = service.DownloadAsync(request, cancellation.Token);
        await downloadStarted.Task.WaitAsync(TimeSpan.FromSeconds(30));
        cancellation.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => download.WaitAsync(TimeSpan.FromSeconds(30)));
        Assert.False(System.IO.Directory.Exists(tempDirectory));
        Assert.False(service.ActiveDownloads.ContainsKey(requestId));
    }

    [Fact]
    public async Task DownloadAsync_WhenCallerCancelsFingerprintVerification_PropagatesAndCleansUp()
    {
        var verificationStarted = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var fingerprintService = new Mock<IFingerprintExtractionService>();
        fingerprintService
            .Setup(service => service.ExtractFingerprintAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(async (string _, CancellationToken cancellationToken) =>
            {
                verificationStarted.TrySetResult();
                await Task.Delay(Timeout.Infinite, cancellationToken);
                return "fingerprint";
            });

        var bytes = new byte[] { 1, 2, 3, 4 };
        var client = new Mock<ISoulseekClient>();
        client
            .Setup(soulseekClient => soulseekClient.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (
                string username,
                string remoteFilename,
                Func<Task<Stream>> outputStreamFactory,
                long size,
                long startOffset,
                int? token,
                TransferOptions transferOptions,
                CancellationToken cancellationToken) =>
            {
                var stream = await outputStreamFactory().ConfigureAwait(false);
                await stream.WriteAsync(bytes, 0, bytes.Length, cancellationToken).ConfigureAwait(false);
                return new Transfer(
                    TransferDirection.Download,
                    username,
                    remoteFilename,
                    token ?? 1,
                    TransferStates.Completed | TransferStates.Succeeded,
                    size,
                    startOffset,
                    bytes.Length);
            });

        var service = new MultiSourceDownloadService(
            NullLogger<MultiSourceDownloadService>.Instance,
            client.Object,
            Mock.Of<IContentVerificationService>(),
            fingerprintExtractionService: fingerprintService.Object);
        var requestId = Guid.NewGuid();
        var outputPath = Path.Combine(Path.GetTempPath(), $"{requestId:N}.flac");
        var request = new MultiSourceDownloadRequest
        {
            Id = requestId,
            Filename = "song.flac",
            FileSize = bytes.Length,
            ChunkSize = bytes.Length,
            OutputPath = outputPath,
            TargetFingerprint = "expected-fingerprint",
            Sources =
            [
                new VerifiedSource
                {
                    Username = "mesh-peer",
                    FullPath = "mesh://song.flac",
                    Method = VerificationMethod.MeshOverlay,
                },
            ],
        };
        var tempDirectory = Path.Combine(Path.GetTempPath(), "slskdn-multidownload", requestId.ToString());
        using var cancellation = new CancellationTokenSource();

        var download = service.DownloadAsync(request, cancellation.Token);
        await verificationStarted.Task.WaitAsync(TimeSpan.FromSeconds(30));
        cancellation.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => download.WaitAsync(TimeSpan.FromSeconds(30)));
        Assert.False(System.IO.File.Exists(outputPath));
        Assert.False(System.IO.Directory.Exists(tempDirectory));
        Assert.False(service.ActiveDownloads.ContainsKey(requestId));
    }
}
