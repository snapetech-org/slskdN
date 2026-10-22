// <copyright file="BackfillSchedulerServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Backfill;

using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using slskd.Backfill;
using slskd.Capabilities;
using slskd.HashDb;
using slskd.HashDb.Models;
using slskd.Mesh;
using Soulseek;
using Xunit;

public class BackfillSchedulerServiceTests
{
    [Fact]
    public async Task TriggerCycleAsync_ReusesBatchedCandidateCounts()
    {
        var hashDb = CreateHashDb();
        hashDb.Setup(service => service.GetBackfillCandidatesAsync(10, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new[]
            {
                new FlacInventoryEntry
                {
                    FileId = "file-1",
                    PeerId = "alice",
                    Path = "song.flac",
                    Size = 1234,
                },
            });
        hashDb.Setup(service => service.GetPeerBackfillCountsTodayAsync(
                It.IsAny<IReadOnlyCollection<string>>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase) { ["alice"] = 10 });
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient.Setup(client => client.GetUserStatusAsync("alice", It.IsAny<CancellationToken>()))
            .ReturnsAsync(new UserStatus("alice", UserPresence.Online, false));
        var service = new BackfillSchedulerService(
            hashDb.Object,
            Mock.Of<IMeshSyncService>(),
            soulseekClient.Object,
            Mock.Of<ICapabilityService?>(),
            NullLogger<BackfillSchedulerService>.Instance);

        var result = await service.TriggerCycleAsync();

        Assert.Equal(1, result.CandidatesEvaluated);
        Assert.Equal(1, result.RateLimited);
        Assert.Equal(0, result.BackfillsAttempted);
        hashDb.Verify(candidateStore => candidateStore.GetPeerBackfillCountsTodayAsync(
            It.IsAny<IReadOnlyCollection<string>>(),
            It.IsAny<CancellationToken>()), Times.Once);
        hashDb.Verify(candidateStore => candidateStore.GetPeerBackfillCountTodayAsync(
            It.IsAny<string>(),
            It.IsAny<CancellationToken>()), Times.Never);
    }

    [Fact]
    public async Task GetCandidatesAsync_ClampsLimitAndPropagatesStatusCancellation()
    {
        using var cts = new CancellationTokenSource();
        var hashDb = CreateHashDb();
        hashDb
            .Setup(service => service.GetBackfillCandidatesAsync(100, cts.Token))
            .ReturnsAsync(new[]
            {
                new FlacInventoryEntry
                {
                    FileId = "file-1",
                    PeerId = "alice",
                    Path = "song.flac",
                    Size = 1234,
                    DiscoveredAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                },
            });
        hashDb
            .Setup(service => service.GetPeerBackfillCountsTodayAsync(
                It.Is<IReadOnlyCollection<string>>(peerIds => peerIds.SequenceEqual(new[] { "alice" })),
                cts.Token))
            .ReturnsAsync(new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase) { ["alice"] = 3 });

        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.GetUserStatusAsync("alice", cts.Token))
            .ReturnsAsync(new UserStatus("alice", UserPresence.Online, false));

        var service = new BackfillSchedulerService(
            hashDb.Object,
            Mock.Of<IMeshSyncService>(),
            soulseekClient.Object,
            Mock.Of<ICapabilityService?>(),
            NullLogger<BackfillSchedulerService>.Instance);

        var candidates = (await service.GetCandidatesAsync(5000, cts.Token)).ToList();

        var candidate = Assert.Single(candidates);
        Assert.True(candidate.IsPeerOnline);
        Assert.Equal(3, candidate.PeerBackfillsToday);
        hashDb.Verify(service => service.GetPeerBackfillCountTodayAsync(
            It.IsAny<string>(),
            It.IsAny<CancellationToken>()), Times.Never);
    }

    [Fact]
    public async Task GetCandidatesAsync_WhenStatusLookupIsCanceled_PropagatesCancellation()
    {
        using var cts = new CancellationTokenSource();
        var hashDb = CreateHashDb();
        hashDb
            .Setup(service => service.GetBackfillCandidatesAsync(10, cts.Token))
            .ReturnsAsync(new[]
            {
                new FlacInventoryEntry
                {
                    FileId = "file-1",
                    PeerId = "alice",
                    Path = "song.flac",
                    Size = 1234,
                    DiscoveredAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                },
            });
        hashDb
            .Setup(service => service.GetPeerBackfillCountsTodayAsync(
                It.IsAny<IReadOnlyCollection<string>>(),
                cts.Token))
            .ReturnsAsync(new Dictionary<string, int>());

        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.GetUserStatusAsync("alice", cts.Token))
            .Callback(() => cts.Cancel())
            .ThrowsAsync(new OperationCanceledException(cts.Token));

        var service = new BackfillSchedulerService(
            hashDb.Object,
            Mock.Of<IMeshSyncService>(),
            soulseekClient.Object,
            Mock.Of<ICapabilityService?>(),
            NullLogger<BackfillSchedulerService>.Instance);

        await Assert.ThrowsAsync<OperationCanceledException>(() => service.GetCandidatesAsync(10, cts.Token));
    }

    [Fact]
    public async Task BackfillFileAsync_WhenHeaderDownloadThrows_ReturnsSanitizedErrorMessage()
    {
        var hashDb = new Mock<IHashDbService>();
        hashDb
            .Setup(service => service.UpsertFlacEntryAsync(It.IsAny<FlacInventoryEntry>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        hashDb
            .Setup(service => service.MarkFlacHashFailedAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<System.IO.Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("sensitive transfer detail"));

        var service = new BackfillSchedulerService(
            hashDb.Object,
            Mock.Of<IMeshSyncService>(),
            soulseekClient.Object,
            Mock.Of<ICapabilityService?>(),
            NullLogger<BackfillSchedulerService>.Instance);

        var result = await service.BackfillFileAsync("alice", @"Music\song.flac", 1234, CancellationToken.None);

        Assert.False(result.Success);
        Assert.Equal("Failed to read FLAC header", result.Error);
        Assert.DoesNotContain("sensitive", result.Error, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task BackfillFileAsync_WhenWaitingCancellationFires_DoesNotReleaseUnacquiredSemaphore()
    {
        var hashDb = CreateHashDb();
        var soulseekClient = new Mock<ISoulseekClient>();
        var releaseDownloads = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var downloadsStarted = 0;

        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<System.IO.Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async () =>
            {
                Interlocked.Increment(ref downloadsStarted);
                await releaseDownloads.Task;
                return new Transfer(TransferDirection.Download, "peer", "file", 1, TransferStates.Completed, 1, 0, 1);
            });

        var service = new BackfillSchedulerService(
            hashDb.Object,
            Mock.Of<IMeshSyncService>(),
            soulseekClient.Object,
            Mock.Of<ICapabilityService?>(),
            NullLogger<BackfillSchedulerService>.Instance);

        var first = service.BackfillFileAsync("alice", "one.flac", 100, CancellationToken.None);
        var second = service.BackfillFileAsync("bob", "two.flac", 100, CancellationToken.None);

        while (Volatile.Read(ref downloadsStarted) < 2)
        {
            await Task.Delay(10);
        }

        using var cts = new CancellationTokenSource();
        var third = service.BackfillFileAsync("carol", "three.flac", 100, cts.Token);
        cts.Cancel();
        var thirdResult = await third;

        Assert.False(thirdResult.Success);
        Assert.Equal(2, service.ActiveBackfillCount);

        releaseDownloads.SetResult();
        await Task.WhenAll(first, second);
        Assert.Equal(0, service.ActiveBackfillCount);
    }

    [Fact]
    public async Task BackfillFileAsync_WhenHeaderIsNotFlac_DoesNotStoreEmptyHash()
    {
        var hashDb = CreateHashDb();
        var soulseekClient = new Mock<ISoulseekClient>();

        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<System.IO.Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (
                string username,
                string remoteFilename,
                Func<Task<System.IO.Stream>> outputStreamFactory,
                long size,
                long startOffset,
                int? token,
                TransferOptions options,
                CancellationToken cancellationToken) =>
            {
                var stream = await outputStreamFactory();
                var invalidHeader = new byte[42];
                await stream.WriteAsync(invalidHeader, cancellationToken);
                return new Transfer(TransferDirection.Download, username, remoteFilename, token ?? 1, TransferStates.Completed, size, 0, 42);
            });

        var service = new BackfillSchedulerService(
            hashDb.Object,
            Mock.Of<IMeshSyncService>(),
            soulseekClient.Object,
            Mock.Of<ICapabilityService?>(),
            NullLogger<BackfillSchedulerService>.Instance);

        var result = await service.BackfillFileAsync("alice", "bad.flac", 100, CancellationToken.None);

        Assert.False(result.Success);
        Assert.Equal("Failed to parse FLAC header", result.Error);
        hashDb.Verify(
            service => service.UpdateFlacHashAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<HashSource>(),
                It.IsAny<CancellationToken>()),
            Times.Never);
        hashDb.Verify(
            service => service.StoreHashFromVerificationAsync(
                It.IsAny<string>(),
                It.IsAny<long>(),
                It.IsAny<string>(),
                It.IsAny<int?>(),
                It.IsAny<int?>(),
                It.IsAny<int?>(),
                It.IsAny<CancellationToken>()),
            Times.Never);
    }

    private static Mock<IHashDbService> CreateHashDb()
    {
        var hashDb = new Mock<IHashDbService>();
        hashDb
            .Setup(service => service.UpsertFlacEntryAsync(It.IsAny<FlacInventoryEntry>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        hashDb
            .Setup(service => service.MarkFlacHashFailedAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        hashDb
            .Setup(service => service.UpdateFlacHashAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<HashSource>(),
                It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        hashDb
            .Setup(service => service.StoreHashFromVerificationAsync(
                It.IsAny<string>(),
                It.IsAny<long>(),
                It.IsAny<string>(),
                It.IsAny<int?>(),
                It.IsAny<int?>(),
                It.IsAny<int?>(),
                It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        hashDb
            .Setup(service => service.IncrementPeerBackfillCountAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        return hashDb;
    }
}
