// <copyright file="WishlistServicePersistenceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Tests.Unit.Wishlist;

using System.Data.Common;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Options;
using Moq;
using slskd.Migrations;
using slskd.Search;
using slskd.Transfers.Downloads;
using slskd.Transfers.Ranking;
using slskd.Wishlist;
using Soulseek;
using Xunit;

public sealed class WishlistServicePersistenceTests
{
    [Fact]
    public void LidarrWishlistTrackingMigration_AddsColumnsIdempotently()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"wishlist-lidarr-tracking-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={databasePath}";
        try
        {
            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText = "CREATE TABLE WishlistItems (Id TEXT NOT NULL PRIMARY KEY, SearchText TEXT NOT NULL, Filter TEXT NOT NULL)";
                command.ExecuteNonQuery();
            }

            var migration = new Z08032026_LidarrWishlistTrackingMigration(connectionString);
            migration.Apply();
            migration.Apply();

            var blockedHitCountMigration = new Z09062026_WishlistBlockedHitCountMigration(connectionString);
            blockedHitCountMigration.Apply();
            blockedHitCountMigration.Apply();

            using var verificationConnection = new SqliteConnection(connectionString);
            verificationConnection.Open();
            using var verificationCommand = verificationConnection.CreateCommand();
            verificationCommand.CommandText = "PRAGMA table_info(WishlistItems)";
            using var reader = verificationCommand.ExecuteReader();
            var columns = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            while (reader.Read())
            {
                columns.Add(reader.GetString(1));
            }

            Assert.Contains("LidarrAlbumId", columns);
            Assert.Contains("LidarrTrackId", columns);
            Assert.Contains("LastBlockedHitCount", columns);
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool(connectionString);
            System.IO.File.Delete(databasePath);
            System.IO.File.Delete(databasePath + "-shm");
            System.IO.File.Delete(databasePath + "-wal");
        }
    }

    [Fact]
    public async Task FindBySearchTextAsync_UsesCaseInsensitiveIndexAndHydratesOneRow()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"wishlist-lookup-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={databasePath}";
        try
        {
            var commandCapture = new CommandCaptureInterceptor();
            var options = new DbContextOptionsBuilder<WishlistDbContext>()
                .UseSqlite(connectionString)
                .AddInterceptors(commandCapture)
                .Options;
            var contextFactory = new TestDbContextFactory(options);
            var olderId = Guid.NewGuid();
            var newerId = Guid.NewGuid();
            await using (var context = await contextFactory.CreateDbContextAsync())
            {
                await context.Database.EnsureCreatedAsync();
                new Z07162026_WishlistSearchTextIndexMigration(connectionString).Apply();
                new Z07162026_WishlistSearchTextIndexMigration(connectionString).Apply();
                context.WishlistItems.AddRange(Enumerable.Range(1, 1000).Select(index => new WishlistItem
                {
                    SearchText = $"unrelated-{index}",
                    CreatedAt = DateTime.UtcNow.AddMinutes(-index),
                }));
                context.WishlistItems.AddRange(
                    new WishlistItem
                    {
                        Id = olderId,
                        SearchText = "TARGET SEARCH",
                        CreatedAt = DateTime.UtcNow.AddMinutes(-2),
                    },
                    new WishlistItem
                    {
                        Id = newerId,
                        SearchText = "target search",
                        CreatedAt = DateTime.UtcNow.AddMinutes(-1),
                    });
                await context.SaveChangesAsync();
            }

            commandCapture.Commands.Clear();
            commandCapture.ReadCommands.Clear();
            var optionsMonitor = new Mock<IOptionsMonitor<slskd.Options>>();
            optionsMonitor.SetupGet(monitor => monitor.CurrentValue).Returns(new slskd.Options());
            using var service = new WishlistService(
                contextFactory,
                Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
                Mock.Of<ISearchService>(),
                Mock.Of<ISoulseekClient>(),
                optionsMonitor.Object,
                Mock.Of<ISourceRankingService>(),
                Mock.Of<IDownloadService>());

            var found = await service.FindBySearchTextAsync(" Target Search ");

            Assert.NotNull(found);
            Assert.Equal(newerId, found!.Id);
            var read = Assert.Single(commandCapture.ReadCommands);
            Assert.Contains("COLLATE NOCASE", read, StringComparison.OrdinalIgnoreCase);
            Assert.Contains("LIMIT", read, StringComparison.OrdinalIgnoreCase);
            await using var connection = new SqliteConnection(connectionString);
            await connection.OpenAsync();
            await using var planCommand = connection.CreateCommand();
            planCommand.CommandText = """
                EXPLAIN QUERY PLAN
                SELECT Id
                FROM WishlistItems
                WHERE SearchText = 'target search' COLLATE NOCASE
                ORDER BY CreatedAt DESC
                LIMIT 1
                """;
            await using var reader = await planCommand.ExecuteReaderAsync();
            var plan = new List<string>();
            while (await reader.ReadAsync())
            {
                plan.Add(reader.GetString(3));
            }
            Assert.Contains(plan, detail =>
                detail.Contains("USING INDEX IX_WishlistItems_SearchText_NoCase", StringComparison.Ordinal));
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool(connectionString);
            System.IO.File.Delete(databasePath);
            System.IO.File.Delete(databasePath + "-shm");
            System.IO.File.Delete(databasePath + "-wal");
        }
    }

    [Fact]
    public async Task IgnoreResultAsync_UsesCaseInsensitiveCompositeIndexAndHydratesOneRule()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"wishlist-ignore-lookup-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={databasePath}";
        try
        {
            var commandCapture = new CommandCaptureInterceptor();
            var options = new DbContextOptionsBuilder<WishlistDbContext>()
                .UseSqlite(connectionString)
                .AddInterceptors(commandCapture)
                .Options;
            var contextFactory = new TestDbContextFactory(options);
            var wishlistItemId = Guid.NewGuid();
            var targetId = Guid.NewGuid();
            await using (var context = await contextFactory.CreateDbContextAsync())
            {
                await context.Database.EnsureCreatedAsync();
                context.WishlistItems.Add(new WishlistItem
                {
                    Id = wishlistItemId,
                    SearchText = "fixture",
                });
                context.WishlistIgnoredResults.AddRange(Enumerable.Range(0, 1000).Select(index => new WishlistIgnoredResult
                {
                    WishlistItemId = wishlistItemId,
                    Username = $"peer-{index:D4}",
                    Directory = $"Music/Directory-{index:D4}",
                }));
                context.WishlistIgnoredResults.Add(new WishlistIgnoredResult
                {
                    Id = targetId,
                    WishlistItemId = wishlistItemId,
                    Username = "TARGET PEER",
                    Directory = "Music/Target",
                });
                await context.SaveChangesAsync();
            }

            commandCapture.Commands.Clear();
            commandCapture.ReadCommands.Clear();
            var optionsMonitor = new Mock<IOptionsMonitor<slskd.Options>>();
            optionsMonitor.SetupGet(monitor => monitor.CurrentValue).Returns(new slskd.Options());
            using var service = new WishlistService(
                contextFactory,
                Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
                Mock.Of<ISearchService>(),
                Mock.Of<ISoulseekClient>(),
                optionsMonitor.Object,
                Mock.Of<ISourceRankingService>(),
                Mock.Of<IDownloadService>());

            var existing = await service.IgnoreResultAsync(
                wishlistItemId,
                "target peer",
                "Music\\Target\\");

            Assert.Equal(targetId, existing.Id);
            Assert.Equal(2, commandCapture.ReadCommands.Count);
            var lookup = commandCapture.ReadCommands[1];
            Assert.Contains("Username", lookup, StringComparison.Ordinal);
            Assert.Contains("Directory", lookup, StringComparison.Ordinal);
            Assert.Contains("LIMIT", lookup, StringComparison.OrdinalIgnoreCase);
            Assert.Empty(commandCapture.Commands);

            await using var connection = new SqliteConnection(connectionString);
            await connection.OpenAsync();
            await using var planCommand = connection.CreateCommand();
            planCommand.CommandText = $"""
                EXPLAIN QUERY PLAN
                SELECT Id
                FROM WishlistIgnoredResults
                WHERE WishlistItemId = '{wishlistItemId}'
                  AND Username = 'target peer'
                  AND Directory = 'Music/Target'
                LIMIT 1
                """;
            await using var reader = await planCommand.ExecuteReaderAsync();
            var plan = new List<string>();
            while (await reader.ReadAsync())
            {
                plan.Add(reader.GetString(3));
            }
            Assert.Contains(plan, detail =>
                detail.Contains("IX_WishlistIgnoredResults_WishlistItemId_Username_Directory", StringComparison.Ordinal));
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool(connectionString);
            System.IO.File.Delete(databasePath);
            System.IO.File.Delete(databasePath + "-shm");
            System.IO.File.Delete(databasePath + "-wal");
        }
    }

    [Fact]
    public async Task CreateManyAsync_WithOneHundredItems_UsesThreeMultiRowCommands()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var commandCapture = new CommandCaptureInterceptor();
        var options = new DbContextOptionsBuilder<WishlistDbContext>()
            .UseSqlite(connection)
            .AddInterceptors(commandCapture)
            .Options;
        var contextFactory = new TestDbContextFactory(options);
        await using (var context = await contextFactory.CreateDbContextAsync())
        {
            await context.Database.EnsureCreatedAsync();
            context.WishlistItems.AddRange(Enumerable.Range(1, 100).Select(index => new WishlistItem
            {
                SearchText = $"baseline-{index}",
            }));
            await context.SaveChangesAsync();
            Assert.Equal(100, commandCapture.Commands.Count);
            await context.WishlistItems.ExecuteDeleteAsync();
        }
        commandCapture.Commands.Clear();
        var optionsMonitor = new Mock<IOptionsMonitor<slskd.Options>>();
        optionsMonitor.SetupGet(monitor => monitor.CurrentValue).Returns(new slskd.Options());
        using var service = new WishlistService(
            contextFactory,
                Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            Mock.Of<ISearchService>(),
            Mock.Of<ISoulseekClient>(),
            optionsMonitor.Object,
            Mock.Of<ISourceRankingService>(),
            Mock.Of<IDownloadService>());
        var originalId = Guid.NewGuid();
        var items = Enumerable.Range(1, 100)
            .Select(index => new WishlistItem
            {
                Id = originalId,
                SearchText = $"search-{index}",
                Filter = "flac",
            })
            .ToList();
        var lastSearchId = Guid.NewGuid();
        var lastActivityAt = DateTime.UtcNow.AddMinutes(-5);
        items[0].Enabled = false;
        items[0].AutoDownload = true;
        items[0].MaxResults = 25;
        items[0].LastSearchedAt = lastActivityAt;
        items[0].LastMatchCount = 8;
        items[0].LastVisibleHitCount = 7;
        items[0].LastHiddenLockedHitCount = 6;
        items[0].LastFilteredOutHitCount = 5;
        items[0].LastIgnoredResultHitCount = 4;
        items[0].LastBlockedHitCount = 10;
        items[0].LastResponseCount = 3;
        items[0].TotalSearchCount = 2;
        items[0].TotalDownloadCount = 1;
        items[0].MaxDownloads = 9;
        items[0].LastSearchId = lastSearchId;
        items[0].LastViewedAt = lastActivityAt;
        items[0].LidarrAlbumId = 42;
        items[0].LidarrTrackId = 84;

        var created = await service.CreateManyAsync(items);

        Assert.Equal(100, created.Count);
        Assert.Equal(100, created.Select(item => item.Id).Distinct().Count());
        Assert.DoesNotContain(created, item => item.Id == originalId);
        Assert.Equal(3, commandCapture.Commands.Count);
        Assert.All(commandCapture.Commands, command =>
            Assert.StartsWith("INSERT INTO WishlistItems", command.TrimStart(), StringComparison.OrdinalIgnoreCase));
        await using var verificationContext = await contextFactory.CreateDbContextAsync();
        Assert.Equal(100, await verificationContext.WishlistItems.CountAsync());
        var stored = await verificationContext.WishlistItems.SingleAsync(item => item.SearchText == "search-1");
        Assert.False(stored.Enabled);
        Assert.True(stored.AutoDownload);
        Assert.Equal(25, stored.MaxResults);
        Assert.Equal(lastActivityAt, stored.LastSearchedAt);
        Assert.Equal(8, stored.LastMatchCount);
        Assert.Equal(7, stored.LastVisibleHitCount);
        Assert.Equal(6, stored.LastHiddenLockedHitCount);
        Assert.Equal(5, stored.LastFilteredOutHitCount);
        Assert.Equal(4, stored.LastIgnoredResultHitCount);
        Assert.Equal(10, stored.LastBlockedHitCount);
        Assert.Equal(3, stored.LastResponseCount);
        Assert.Equal(2, stored.TotalSearchCount);
        Assert.Equal(1, stored.TotalDownloadCount);
        Assert.Equal(9, stored.MaxDownloads);
        Assert.Equal(lastSearchId, stored.LastSearchId);
        Assert.Equal(lastActivityAt, stored.LastViewedAt);
        Assert.Equal(42, stored.LidarrAlbumId);
        Assert.Equal(84, stored.LidarrTrackId);

        await service.UpdateAsync(new WishlistItem
        {
            Id = stored.Id,
            SearchText = stored.SearchText,
            Filter = stored.Filter,
            Enabled = stored.Enabled,
            AutoDownload = stored.AutoDownload,
            MaxResults = stored.MaxResults,
            MaxDownloads = stored.MaxDownloads,
        });

        await using var updatedVerificationContext = await contextFactory.CreateDbContextAsync();
        var updated = await updatedVerificationContext.WishlistItems.SingleAsync(item => item.Id == stored.Id);
        Assert.Equal(42, updated.LidarrAlbumId);
        Assert.Equal(84, updated.LidarrTrackId);
    }

    [Fact]
    public async Task UpdateFiltersAsync_UpdatesAllItemsAtomicallyAndPreservesTracking()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<WishlistDbContext>()
            .UseSqlite(connection)
            .Options;
        var contextFactory = new TestDbContextFactory(options);
        var firstId = Guid.NewGuid();
        var secondId = Guid.NewGuid();
        await using (var context = await contextFactory.CreateDbContextAsync())
        {
            await context.Database.EnsureCreatedAsync();
            context.WishlistItems.AddRange(
                new WishlistItem
                {
                    Id = firstId,
                    SearchText = "first",
                    Filter = "flac",
                    LidarrAlbumId = 10,
                },
                new WishlistItem
                {
                    Id = secondId,
                    SearchText = "second",
                    Filter = "mp3",
                    LidarrTrackId = 20,
                });
            await context.SaveChangesAsync();
        }

        var optionsMonitor = new Mock<IOptionsMonitor<slskd.Options>>();
        optionsMonitor.SetupGet(monitor => monitor.CurrentValue).Returns(new slskd.Options());
        using var service = new WishlistService(
            contextFactory,
                Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            Mock.Of<ISearchService>(),
            Mock.Of<ISoulseekClient>(),
            optionsMonitor.Object,
            Mock.Of<ISourceRankingService>(),
            Mock.Of<IDownloadService>());

        var updated = await service.UpdateFiltersAsync([firstId, secondId], "mp3 minbr:320");

        Assert.Equal(2, updated);
        await using var verificationContext = await contextFactory.CreateDbContextAsync();
        var stored = await verificationContext.WishlistItems
            .Where(item => item.Id == firstId || item.Id == secondId)
            .OrderBy(item => item.SearchText)
            .ToListAsync();
        Assert.Equal(
            new[] { "mp3 minbr:320", "mp3 minbr:320" },
            stored.Select(item => item.Filter).ToArray());
        Assert.Equal(10, stored[0].LidarrAlbumId);
        Assert.Equal(20, stored[1].LidarrTrackId);

        await Assert.ThrowsAsync<NotFoundException>(() =>
            service.UpdateFiltersAsync([firstId, Guid.NewGuid()], "flac"));
        await using var afterFailureContext = await contextFactory.CreateDbContextAsync();
        Assert.All(
            await afterFailureContext.WishlistItems
                .Where(item => item.Id == firstId || item.Id == secondId)
                .ToListAsync(),
            item => Assert.Equal("mp3 minbr:320", item.Filter));
    }

    [Fact]
    public async Task ImportCsvAsync_WithOneHundredTracks_UsesThreeMultiRowCommands()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var commandCapture = new CommandCaptureInterceptor();
        var options = new DbContextOptionsBuilder<WishlistDbContext>()
            .UseSqlite(connection)
            .AddInterceptors(commandCapture)
            .Options;
        var contextFactory = new TestDbContextFactory(options);
        await using (var context = await contextFactory.CreateDbContextAsync())
        {
            await context.Database.EnsureCreatedAsync();
        }
        commandCapture.Commands.Clear();
        var optionsMonitor = new Mock<IOptionsMonitor<slskd.Options>>();
        optionsMonitor.SetupGet(monitor => monitor.CurrentValue).Returns(new slskd.Options());
        using var service = new WishlistService(
            contextFactory,
                Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            Mock.Of<ISearchService>(),
            Mock.Of<ISoulseekClient>(),
            optionsMonitor.Object,
            Mock.Of<ISourceRankingService>(),
            Mock.Of<IDownloadService>());
        var csv = "Track,Artist\n" + string.Join(
            '\n',
            Enumerable.Range(1, 100).Select(index => $"Track {index},Artist"));

        var result = await service.ImportCsvAsync(csv, new WishlistCsvImportOptions { Filter = "flac" });

        Assert.Equal(100, result.CreatedCount);
        Assert.Equal(3, commandCapture.Commands.Count);
        Assert.All(commandCapture.Commands, command =>
            Assert.StartsWith("INSERT INTO WishlistItems", command.TrimStart(), StringComparison.OrdinalIgnoreCase));
        await using var verificationContext = await contextFactory.CreateDbContextAsync();
        Assert.Equal(100, await verificationContext.WishlistItems.CountAsync());
    }

    [Fact]
    public async Task MarkAllViewedAsync_UsesOneSetBasedUpdate()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var commandCapture = new CommandCaptureInterceptor();
        var options = new DbContextOptionsBuilder<WishlistDbContext>()
            .UseSqlite(connection)
            .AddInterceptors(commandCapture)
            .Options;
        var contextFactory = new TestDbContextFactory(options);
        var alreadyViewedAt = DateTime.UtcNow;
        await using (var context = await contextFactory.CreateDbContextAsync())
        {
            await context.Database.EnsureCreatedAsync();
            context.WishlistItems.AddRange(
                Enumerable.Range(0, 501).Select(index => new WishlistItem
                {
                    SearchText = $"search-{index}",
                    LastSearchedAt = alreadyViewedAt,
                }));
            context.WishlistItems.Add(new WishlistItem
            {
                SearchText = "already-viewed",
                LastSearchedAt = alreadyViewedAt.AddMinutes(-1),
                LastViewedAt = alreadyViewedAt,
            });
            await context.SaveChangesAsync();
        }
        commandCapture.Commands.Clear();
        var optionsMonitor = new Mock<IOptionsMonitor<slskd.Options>>();
        optionsMonitor.SetupGet(monitor => monitor.CurrentValue).Returns(new slskd.Options());
        using var service = new WishlistService(
            contextFactory,
                Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            Mock.Of<ISearchService>(),
            Mock.Of<ISoulseekClient>(),
            optionsMonitor.Object,
            Mock.Of<ISourceRankingService>(),
            Mock.Of<IDownloadService>());

        await service.MarkAllViewedAsync();

        var command = Assert.Single(commandCapture.Commands);
        Assert.StartsWith("UPDATE", command.TrimStart(), StringComparison.OrdinalIgnoreCase);
        Assert.Contains("WHERE", command, StringComparison.OrdinalIgnoreCase);
        await using var verificationContext = await contextFactory.CreateDbContextAsync();
        Assert.Equal(501, await verificationContext.WishlistItems.CountAsync(item => item.LastViewedAt > alreadyViewedAt));
        var alreadyViewed = await verificationContext.WishlistItems.SingleAsync(item => item.SearchText == "already-viewed");
        Assert.Equal(alreadyViewedAt, alreadyViewed.LastViewedAt);
    }

    private sealed class TestDbContextFactory(DbContextOptions<WishlistDbContext> options)
        : IDbContextFactory<WishlistDbContext>
    {
        public WishlistDbContext CreateDbContext() => new(options);

        public ValueTask<WishlistDbContext> CreateDbContextAsync(CancellationToken cancellationToken = default) =>
            ValueTask.FromResult(CreateDbContext());
    }

    private sealed class CommandCaptureInterceptor : DbCommandInterceptor
    {
        public List<string> Commands { get; } = new();
        public List<string> ReadCommands { get; } = new();

        public override ValueTask<InterceptionResult<int>> NonQueryExecutingAsync(
            DbCommand command,
            CommandEventData eventData,
            InterceptionResult<int> result,
            CancellationToken cancellationToken = default)
        {
            CaptureCommand(command);
            return ValueTask.FromResult(result);
        }

        public override ValueTask<InterceptionResult<DbDataReader>> ReaderExecutingAsync(
            DbCommand command,
            CommandEventData eventData,
            InterceptionResult<DbDataReader> result,
            CancellationToken cancellationToken = default)
        {
            CaptureCommand(command);
            return ValueTask.FromResult(result);
        }

        private void CaptureCommand(DbCommand command)
        {
            var text = command.CommandText.TrimStart();
            if (text.StartsWith("INSERT", StringComparison.OrdinalIgnoreCase) ||
                text.StartsWith("UPDATE", StringComparison.OrdinalIgnoreCase))
            {
                Commands.Add(command.CommandText);
            }
            else if (text.StartsWith("SELECT", StringComparison.OrdinalIgnoreCase))
            {
                ReadCommands.Add(command.CommandText);
            }
        }
    }
}
