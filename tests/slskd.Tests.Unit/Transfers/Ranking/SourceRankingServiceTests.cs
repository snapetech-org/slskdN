// <copyright file="SourceRankingServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Transfers.Ranking;

using System;
using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using slskd.Events;
using slskd.Transfers.Ranking;
using Xunit;

[Collection(AllocationTestCollection.Name)]
public sealed class SourceRankingServiceTests
{
    [Fact]
    public async Task RankSourcesAsync_PreservesHistoryScoringAndStableTieOrder()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<SourceRankingDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new SourceRankingDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var service = new SourceRankingService(
            new TestDbContextFactory(options),
            NullLogger<SourceRankingService>.Instance,
            new EventBus(new EventService(Mock.Of<IDbContextFactory<EventsDbContext>>())));
        const string successfulPeer = "peer-\"quoted/雪";

        try
        {
            await service.RecordSuccessAsync(successfulPeer);
            await service.RecordSuccessAsync(successfulPeer);
            await service.RecordSuccessAsync("neutral-peer");
            await service.RecordFailureAsync("neutral-peer");
            await service.RecordFailureAsync("failed-peer");
            await service.RecordFailureAsync("failed-peer");

            var candidates = new[]
            {
                new SourceCandidate { Username = "failed-peer", Filename = "failed.flac", QueueLength = 100 },
                new SourceCandidate { Username = successfulPeer, Filename = "successful.flac", QueueLength = 100 },
                new SourceCandidate { Username = "unseen-peer", Filename = "unseen.flac", QueueLength = 100 },
                new SourceCandidate { Username = "neutral-peer", Filename = "neutral.flac", QueueLength = 100 },
            };

            var ranked = Assert.IsType<List<RankedSource>>(await service.RankSourcesAsync(candidates));

            Assert.Equal(
                new[] { "successful.flac", "unseen.flac", "neutral.flac", "failed.flac" },
                ranked.Select(source => source.Filename));
            Assert.Equal(new[] { 15.0, 0.0, 0.0, -15.0 }, ranked.Select(source => source.HistoryScore));

            var histories = await service.GetHistoriesAsync(new[]
            {
                successfulPeer,
                "unseen-peer",
                successfulPeer,
                "neutral-peer",
                "failed-peer",
            });
            Assert.Equal(
                new[] { successfulPeer, "unseen-peer", "neutral-peer", "failed-peer" },
                histories.Keys);
            Assert.Equal((2, 0), (histories[successfulPeer].Successes, histories[successfulPeer].Failures));
            Assert.Equal((0, 0), (histories["unseen-peer"].Successes, histories["unseen-peer"].Failures));
            Assert.Equal((1, 1), (histories["neutral-peer"].Successes, histories["neutral-peer"].Failures));
            Assert.Equal((0, 2), (histories["failed-peer"].Successes, histories["failed-peer"].Failures));
        }
        finally
        {
            if (File.Exists(databasePath))
            {
                slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={databasePath}");
                File.Delete(databasePath);
            }
        }
    }

    [Fact]
    public async Task RankSourcesAsync_UnseenWideBatchHasBoundedAllocation()
    {
        const int candidateCount = 10_000;
        var databasePath = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<SourceRankingDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new SourceRankingDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var service = new SourceRankingService(
            new TestDbContextFactory(options),
            NullLogger<SourceRankingService>.Instance,
            new EventBus(new EventService(Mock.Of<IDbContextFactory<EventsDbContext>>())));
        var candidates = Enumerable.Range(0, candidateCount)
            .Select(index => new SourceCandidate
            {
                Username = $"peer-{index:D5}",
                Filename = $"file-{index:D5}.flac",
                Size = index,
                UploadSpeed = index,
                QueueLength = index % 100,
                HasFreeUploadSlot = index % 2 == 0,
            })
            .ToArray();

        try
        {
            _ = await service.RankSourcesAsync(candidates);

            var allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
            var ranked = Assert.IsType<List<RankedSource>>(await service.RankSourcesAsync(candidates));
            var allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;

            Assert.Equal(candidateCount, ranked.Count);
            Assert.True(
                allocatedBytes < 3_700_000,
                $"Wide unseen-source ranking allocated {allocatedBytes:N0} bytes.");
        }
        finally
        {
            if (File.Exists(databasePath))
            {
                slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={databasePath}");
                File.Delete(databasePath);
            }
        }
    }

    [Fact]
    public async Task GetHistoriesAsync_UnseenWideBatchHasBoundedAllocation()
    {
        const int usernameCount = 10_000;
        var databasePath = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<SourceRankingDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new SourceRankingDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var service = new SourceRankingService(
            new TestDbContextFactory(options),
            NullLogger<SourceRankingService>.Instance,
            new EventBus(new EventService(Mock.Of<IDbContextFactory<EventsDbContext>>())));
        var usernames = Enumerable.Range(0, usernameCount)
            .Select(index => $"peer-{index:D5}")
            .ToArray();

        try
        {
            _ = await service.GetHistoriesAsync(usernames);

            var allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
            var histories = await service.GetHistoriesAsync(usernames);
            var allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;

            Assert.Equal(usernameCount, histories.Count);
            Assert.True(
                allocatedBytes < 2_500_000,
                $"Wide unseen-history lookup allocated {allocatedBytes:N0} bytes.");
        }
        finally
        {
            if (File.Exists(databasePath))
            {
                slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={databasePath}");
                File.Delete(databasePath);
            }
        }
    }

    [Fact]
    public async Task RecordFailureAsync_ConcurrentNewUsername_RecordsEveryFailure()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<SourceRankingDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new SourceRankingDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var service = new SourceRankingService(
            new TestDbContextFactory(options),
            NullLogger<SourceRankingService>.Instance,
            new EventBus(new EventService(Mock.Of<IDbContextFactory<EventsDbContext>>())));

        try
        {
            var tasks = Enumerable.Range(0, 40)
                .Select(_ => service.RecordFailureAsync("same-user"));

            await Task.WhenAll(tasks);

            var history = await service.GetHistoryAsync("same-user");

            Assert.Equal(0, history.Successes);
            Assert.Equal(40, history.Failures);
        }
        finally
        {
            if (File.Exists(databasePath))
            {
                slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={databasePath}");
                File.Delete(databasePath);
            }
        }
    }

    [Fact]
    public async Task RecordSuccessAndFailureAsync_ExistingUsername_UpdatesCounters()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<SourceRankingDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new SourceRankingDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var service = new SourceRankingService(
            new TestDbContextFactory(options),
            NullLogger<SourceRankingService>.Instance,
            new EventBus(new EventService(Mock.Of<IDbContextFactory<EventsDbContext>>())));

        try
        {
            await service.RecordSuccessAsync("same-user");
            await service.RecordFailureAsync("same-user");
            await service.RecordFailureAsync("same-user");

            var history = await service.GetHistoryAsync("same-user");

            Assert.Equal(1, history.Successes);
            Assert.Equal(2, history.Failures);
        }
        finally
        {
            if (File.Exists(databasePath))
            {
                slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={databasePath}");
                File.Delete(databasePath);
            }
        }
    }

    private sealed class TestDbContextFactory : IDbContextFactory<SourceRankingDbContext>
    {
        private readonly DbContextOptions<SourceRankingDbContext> options;

        public TestDbContextFactory(DbContextOptions<SourceRankingDbContext> options)
        {
            this.options = options;
        }

        public SourceRankingDbContext CreateDbContext()
        {
            return new SourceRankingDbContext(options);
        }

        [SuppressMessage("Reliability", "CA2000:Dispose objects before losing scope", Justification = "IDbContextFactory transfers DbContext disposal ownership to the caller.")]
        public ValueTask<SourceRankingDbContext> CreateDbContextAsync(CancellationToken cancellationToken = default)
        {
            return ValueTask.FromResult(CreateDbContext());
        }
    }
}
