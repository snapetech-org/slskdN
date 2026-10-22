// <copyright file="ContentVerificationServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Transfers.MultiSource;

using slskd.HashDb;
using slskd.HashDb.Models;
using Moq;
using slskd.Transfers.MultiSource;
using Soulseek;
using Xunit;

public sealed class ContentVerificationServiceTests : IDisposable
{
    private readonly string _tempDirectory = Path.Combine(Path.GetTempPath(), $"slskdn-verification-tests-{Guid.NewGuid():N}");

    public ContentVerificationServiceTests()
    {
        System.IO.Directory.CreateDirectory(_tempDirectory);
    }

    public void Dispose()
    {
        if (System.IO.Directory.Exists(_tempDirectory))
        {
            System.IO.Directory.Delete(_tempDirectory, recursive: true);
        }
    }

    [Fact]
    public async Task LimitedWriteStream_ByteArrayAsyncWrite_StopsAtByteLimit()
    {
        using var destination = new MemoryStream();
        using var cancellation = new CancellationTokenSource();
        using var limited = new LimitedWriteStream(destination, 3, cancellation);

        await limited.WriteAsync(new byte[] { 1, 2, 3, 4 }, 0, 4, cancellation.Token);

        Assert.Equal(new byte[] { 1, 2, 3 }, destination.ToArray());
        Assert.Equal(3, limited.BytesWritten);
        Assert.True(limited.LimitReached);
        Assert.True(cancellation.IsCancellationRequested);
    }

    [Fact]
    public async Task LimitedWriteStream_MemoryAsyncWrite_StopsAtByteLimit()
    {
        using var destination = new MemoryStream();
        using var cancellation = new CancellationTokenSource();
        using var limited = new LimitedWriteStream(destination, 3, cancellation);

        await limited.WriteAsync(new ReadOnlyMemory<byte>(new byte[] { 5, 6, 7, 8 }), cancellation.Token);

        Assert.Equal(new byte[] { 5, 6, 7 }, destination.ToArray());
        Assert.Equal(3, limited.BytesWritten);
        Assert.True(limited.LimitReached);
        Assert.True(cancellation.IsCancellationRequested);
    }

    [Fact]
    public void ContentVerificationResult_BestSources_ReturnsSnapshot()
    {
        var source = new VerifiedSource { Username = "peer-a", ContentHash = "hash-a" };
        var result = new ContentVerificationResult
        {
            SourcesByHash = new Dictionary<string, List<VerifiedSource>>
            {
                ["hash-a"] = new() { source },
            },
        };

        var bestSources = result.BestSources;

        bestSources.Clear();

        Assert.Single(result.SourcesByHash["hash-a"]);
        Assert.Single(result.BestSources);
    }

    [Fact]
    public void ContentVerificationResult_BestSemanticSources_ReturnsSnapshot()
    {
        var source = new VerifiedSource { Username = "peer-a", MusicBrainzRecordingId = "mbid-a" };
        var result = new ContentVerificationResult
        {
            BestSemanticKey = "mbid-a|flac",
            SourcesBySemanticKey = new Dictionary<string, List<VerifiedSource>>
            {
                ["mbid-a|flac"] = new() { source },
            },
        };

        var bestSources = result.BestSemanticSources.ToList();

        bestSources.Clear();

        Assert.Single(result.SourcesBySemanticKey["mbid-a|flac"]);
        Assert.Single(result.BestSemanticSources);
    }

    [Fact]
    public async Task VerifySourcesAsync_BoundsConcurrentSoulseekProbes()
    {
        var active = 0;
        var maxActive = 0;
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.DownloadAsync(
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
                var current = Interlocked.Increment(ref active);
                try
                {
                    int observed;
                    do
                    {
                        observed = Volatile.Read(ref maxActive);
                        if (current <= observed)
                        {
                            break;
                        }
                    }
                    while (Interlocked.CompareExchange(ref maxActive, current, observed) != observed);

                    await Task.Delay(50, cancellationToken);
                    var stream = await outputStreamFactory();
                    await stream.WriteAsync(new byte[ContentVerificationService.VerificationChunkSize], cancellationToken);
                    return new Transfer(TransferDirection.Download, username, remoteFilename, token ?? 1, TransferStates.Completed, size, 0, ContentVerificationService.VerificationChunkSize);
                }
                finally
                {
                    Interlocked.Decrement(ref active);
                }
            });

        var service = CreateService(soulseekClient.Object);
        var request = new ContentVerificationRequest
        {
            Filename = "song.flac",
            FileSize = ContentVerificationService.VerificationChunkSize + 1,
            TimeoutMs = 5000,
        };

        for (var i = 0; i < 10; i++)
        {
            request.CandidateSources[$"concurrency-peer-{Guid.NewGuid():N}-{i}"] = $"song-{i}.flac";
        }

        await service.VerifySourcesAsync(request, CancellationToken.None);

        Assert.InRange(maxActive, 1, ContentVerificationService.MaxConcurrentVerificationProbes);
    }

    [Fact]
    public async Task VerifySourcesAsync_WhenDownloadThrows_ReturnsSanitizedFailureReason()
    {
        var username = $"test-peer-{Guid.NewGuid():N}";
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("sensitive verification detail"));

        var service = CreateService(soulseekClient.Object);

        var result = await service.VerifySourcesAsync(
            new ContentVerificationRequest
            {
                Filename = "song.flac",
                FileSize = ContentVerificationService.VerificationChunkSize + 1,
                CandidateSources = new Dictionary<string, string>
                {
                    [username] = @"Music\song.flac",
                },
                TimeoutMs = 1000,
            },
            CancellationToken.None);

        var failed = Assert.Single(result.FailedSources);
        Assert.Equal(username, failed.Username);
        Assert.Equal("Verification failed", failed.Reason);
        Assert.DoesNotContain("sensitive", failed.Reason, StringComparison.OrdinalIgnoreCase);
        soulseekClient.Verify(client => client.DownloadAsync(
            It.IsAny<string>(),
            It.IsAny<string>(),
            It.IsAny<Func<Task<Stream>>>(),
            It.IsAny<long>(),
            It.IsAny<long>(),
            It.IsAny<int?>(),
            It.IsAny<TransferOptions>(),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public void PeerProbeBudget_PersistsConsumptionBeforeAllowingAnotherProcess()
    {
        var path = Path.Combine(_tempDirectory, "verification-probe-budget.json");
        var firstProcess = new PeerProbeBudget(path, maxProbesPerPeerPerDay: 1);

        Assert.Equal(PeerProbeBudgetDecision.Allowed, firstProcess.TryConsume("peer-a", out var firstFailure));
        Assert.Null(firstFailure);

        var restartedProcess = new PeerProbeBudget(path, maxProbesPerPeerPerDay: 1);
        Assert.Equal(PeerProbeBudgetDecision.Exhausted, restartedProcess.TryConsume("PEER-A", out var secondFailure));
        Assert.Null(secondFailure);
    }

    [Fact]
    public async Task VerifySourcesAsync_WhenProbeBudgetIsCorrupt_SkipsRemoteProbe()
    {
        var username = $"budget-peer-{Guid.NewGuid():N}";
        var path = Path.Combine(_tempDirectory, "verification-probe-budget.json");
        await System.IO.File.WriteAllTextAsync(path, "not json");
        var soulseekClient = new Mock<ISoulseekClient>();
        var service = CreateService(soulseekClient.Object, new PeerProbeBudget(path, ContentVerificationService.MaxProbesPerPeerPerDay));

        var result = await service.VerifySourcesAsync(new ContentVerificationRequest
        {
            Filename = "song.flac",
            FileSize = ContentVerificationService.VerificationChunkSize + 1,
            CandidateSources = new Dictionary<string, string> { [username] = "song.flac" },
        });

        Assert.Equal("Verification probe budget unavailable; probe skipped", Assert.Single(result.FailedSources).Reason);
        soulseekClient.VerifyNoOtherCalls();
    }

    [Fact]
    public async Task VerifySourcesAsync_WhenProbeBudgetCannotBeSaved_SkipsRemoteProbe()
    {
        var username = $"budget-peer-{Guid.NewGuid():N}";
        var blockerPath = Path.Combine(_tempDirectory, "file-not-directory");
        await System.IO.File.WriteAllTextAsync(blockerPath, "file");
        var budgetPath = Path.Combine(blockerPath, "verification-probe-budget.json");
        var soulseekClient = new Mock<ISoulseekClient>();
        var service = CreateService(soulseekClient.Object, new PeerProbeBudget(budgetPath, ContentVerificationService.MaxProbesPerPeerPerDay));

        var result = await service.VerifySourcesAsync(new ContentVerificationRequest
        {
            Filename = "song.flac",
            FileSize = ContentVerificationService.VerificationChunkSize + 1,
            CandidateSources = new Dictionary<string, string> { [username] = "song.flac" },
        });

        Assert.Equal("Verification probe budget unavailable; probe skipped", Assert.Single(result.FailedSources).Reason);
        soulseekClient.VerifyNoOtherCalls();
    }

    [Fact]
    public async Task TryGetKnownHashAsync_WhenHashDbLookupIsCancelled_PropagatesCancellation()
    {
        var enteredLookup = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var hashDb = new Mock<IHashDbService>();
        hashDb
            .Setup(database => database.LookupHashAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(async (string _, CancellationToken token) =>
            {
                enteredLookup.TrySetResult();
                await Task.Delay(Timeout.Infinite, token);
                return null;
            });
        var service = CreateService(Mock.Of<ISoulseekClient>(), hashDb: hashDb.Object);
        using var cancellation = new CancellationTokenSource();

        var lookup = service.TryGetKnownHashAsync("song.flac", 42, cancellation.Token);
        await enteredLookup.Task;
        cancellation.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => lookup);
    }

    [Fact]
    public async Task StoreVerifiedHashAsync_WhenHashDbStoreIsCancelled_PropagatesCancellation()
    {
        var enteredStore = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var hashDb = new Mock<IHashDbService>();
        hashDb
            .Setup(database => database.StoreHashFromVerificationAsync(
                It.IsAny<string>(), It.IsAny<long>(), It.IsAny<string>(), It.IsAny<int?>(), It.IsAny<int?>(), It.IsAny<int?>(), It.IsAny<CancellationToken>()))
            .Returns(async (string _, long _, string _, int? _, int? _, int? _, CancellationToken token) =>
            {
                enteredStore.TrySetResult();
                await Task.Delay(Timeout.Infinite, token);
            });
        var service = CreateService(Mock.Of<ISoulseekClient>(), hashDb: hashDb.Object);
        using var cancellation = new CancellationTokenSource();

        var store = service.StoreVerifiedHashAsync("song.flac", 42, "hash", cancellation.Token);
        await enteredStore.Task;
        cancellation.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => store);
    }

    [Fact]
    public async Task VerifySourcesAsync_WhenMetadataLookupIsCancelled_PropagatesCancellation()
    {
        var username = $"metadata-cancel-peer-{Guid.NewGuid():N}";
        var lookupCount = 0;
        var enteredMetadataLookup = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var hashDb = new Mock<IHashDbService>();
        hashDb
            .Setup(database => database.LookupHashAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(async (string _, CancellationToken token) =>
            {
                if (Interlocked.Increment(ref lookupCount) == 1)
                {
                    return null;
                }

                enteredMetadataLookup.TrySetResult();
                await Task.Delay(Timeout.Infinite, token);
                return null;
            });
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (
                string probeUsername,
                string remoteFilename,
                Func<Task<Stream>> outputStreamFactory,
                long size,
                long startOffset,
                int? transferToken,
                TransferOptions transferOptions,
                CancellationToken token) =>
            {
                var stream = await outputStreamFactory();
                await stream.WriteAsync(new byte[ContentVerificationService.VerificationChunkSize], token);
                return new Transfer(
                    TransferDirection.Download,
                    probeUsername,
                    remoteFilename,
                    transferToken ?? 1,
                    TransferStates.Completed,
                    size,
                    startOffset,
                    ContentVerificationService.VerificationChunkSize);
            });
        var service = CreateService(soulseekClient.Object, hashDb: hashDb.Object);
        using var cancellation = new CancellationTokenSource();

        var verification = service.VerifySourcesAsync(new ContentVerificationRequest
        {
            Filename = "song.flac",
            FileSize = ContentVerificationService.VerificationChunkSize + 1,
            CandidateSources = new Dictionary<string, string> { [username] = "song.flac" },
        }, cancellation.Token);
        await enteredMetadataLookup.Task;
        cancellation.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => verification);
    }

    [Fact]
    public async Task VerifySourcesAsync_WhenCallerCancelsProbe_PropagatesCancellation()
    {
        var username = $"cancel-peer-{Guid.NewGuid():N}";
        var enteredDownload = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (
                string _,
                string _,
                Func<Task<Stream>> _,
                long _,
                long _,
                int? _,
                TransferOptions _,
                CancellationToken token) =>
            {
                enteredDownload.TrySetResult();
                await Task.Delay(Timeout.Infinite, token);
                throw new InvalidOperationException("The cancelled download unexpectedly completed.");
            });
        var service = CreateService(soulseekClient.Object);
        using var cancellation = new CancellationTokenSource();

        var verification = service.VerifySourcesAsync(new ContentVerificationRequest
        {
            Filename = "song.flac",
            FileSize = ContentVerificationService.VerificationChunkSize + 1,
            CandidateSources = new Dictionary<string, string> { [username] = "song.flac" },
        }, cancellation.Token);
        await enteredDownload.Task;
        cancellation.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => verification);
    }

    private ContentVerificationService CreateService(
        ISoulseekClient soulseekClient,
        PeerProbeBudget? budget = null,
        IHashDbService? hashDb = null)
    {
        budget ??= new PeerProbeBudget(
            Path.Combine(_tempDirectory, $"verification-probe-budget-{Guid.NewGuid():N}.json"),
            ContentVerificationService.MaxProbesPerPeerPerDay);
        return new ContentVerificationService(soulseekClient, hashDb, meshSync: null, optionsMonitor: null, probeBudget: budget);
    }
}
