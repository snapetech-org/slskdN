// <copyright file="ShareGrantAnnouncementServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Sharing;

using System;
using System.Collections.Generic;
using System.Data.Common;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using slskd.Sharing;
using Soulseek;
using Xunit;

public class ShareGrantAnnouncementServiceTests
{
    [Fact]
    public async Task IngestAsync_WithSenderOwnerMismatch_DoesNotPersistGrant()
    {
        using var fixture = new CollectionsDbFixture();
        var service = CreateService(fixture.Factory);
        var announcement = CreateAnnouncement(ownerUserId: "alice");

        await service.IngestAsync(announcement, senderUsername: "mallory", default);

        await using var db = await fixture.Factory.CreateDbContextAsync();
        Assert.False(await db.Collections.AnyAsync());
        Assert.False(await db.ShareGrants.AnyAsync());
    }

    [Fact]
    public async Task IngestAsync_WithSenderOwnerMatch_PersistsGrant()
    {
        using var fixture = new CollectionsDbFixture();
        var service = CreateService(fixture.Factory);
        var announcement = CreateAnnouncement(ownerUserId: "alice");

        await service.IngestAsync(announcement, senderUsername: "alice", default);

        await using var db = await fixture.Factory.CreateDbContextAsync();
        var collection = Assert.Single(await db.Collections.ToListAsync());
        var grant = Assert.Single(await db.ShareGrants.ToListAsync());

        Assert.Equal("alice", collection.OwnerUserId);
        Assert.Equal("network:recipient", grant.AudienceId);
        Assert.Equal("recipient", grant.AudiencePeerId);
        Assert.Equal("https://owner.example.test", grant.OwnerEndpoint);
        Assert.Equal("share-token", grant.ShareToken);
    }

    [Fact]
    public async Task IngestForWebAccountAsync_BindsExplicitWebAudience()
    {
        using var fixture = new CollectionsDbFixture();
        var service = CreateService(fixture.Factory);
        var announcement = CreateAnnouncement(ownerUserId: "alice");

        await service.IngestForWebAccountAsync(announcement, "web-recipient", default);

        await using var db = await fixture.Factory.CreateDbContextAsync();
        var grant = Assert.Single(await db.ShareGrants.ToListAsync());
        Assert.Equal("web-recipient", grant.AudienceId);
        Assert.Equal("recipient", grant.AudiencePeerId);
    }

    [Fact]
    public async Task IngestAsync_ReplacesLargeItemSetWithoutHydratingExistingRows()
    {
        var commands = new CommandCaptureInterceptor();
        var materialization = new CollectionItemMaterializationInterceptor();
        using var fixture = new CollectionsDbFixture(commands, materialization);
        var announcement = CreateAnnouncement(ownerUserId: "alice");
        await using (var db = await fixture.Factory.CreateDbContextAsync())
        {
            db.Collections.Add(new Collection
            {
                Id = announcement.CollectionId,
                OwnerUserId = "alice",
                Title = "Old",
            });
            db.CollectionItems.AddRange(Enumerable.Range(0, 1000).Select(index => new CollectionItem
            {
                CollectionId = announcement.CollectionId,
                Ordinal = index,
                ContentId = $"old:{index:D4}",
            }));
            await db.SaveChangesAsync();
        }

        commands.Commands.Clear();
        materialization.Count = 0;
        announcement.Items =
        [
            new ShareGrantAnnouncementItem { ContentId = "new:1", MediaKind = "audio" },
            new ShareGrantAnnouncementItem { ContentId = "new:2", MediaKind = "audio" },
        ];

        await CreateService(fixture.Factory).IngestAsync(announcement, senderUsername: "alice", default);
        Assert.Equal(0, materialization.Count);
        var ingestCommands = commands.Commands.ToList();

        await using var verification = await fixture.Factory.CreateDbContextAsync();
        var items = await verification.CollectionItems
            .AsNoTracking()
            .OrderBy(item => item.Ordinal)
            .ToListAsync();
        Assert.Equal(new[] { "new:1", "new:2" }, items.Select(item => item.ContentId));
        Assert.Single(ingestCommands, command =>
            command.TrimStart().StartsWith("DELETE FROM \"CollectionItems\"", StringComparison.OrdinalIgnoreCase));
        Assert.DoesNotContain(ingestCommands, command =>
            command.Contains("SELECT", StringComparison.OrdinalIgnoreCase) &&
            command.Contains("CollectionItems", StringComparison.Ordinal));
    }

    [Fact]
    public async Task IngestAsync_WhenReplacementInsertFails_RollsBackDeletedItems()
    {
        var failure = new CollectionItemInsertFailureInterceptor();
        using var fixture = new CollectionsDbFixture(failure);
        var announcement = CreateAnnouncement(ownerUserId: "alice");
        await using (var db = await fixture.Factory.CreateDbContextAsync())
        {
            db.Collections.Add(new Collection
            {
                Id = announcement.CollectionId,
                OwnerUserId = "alice",
                Title = "Old",
            });
            db.CollectionItems.Add(new CollectionItem
            {
                CollectionId = announcement.CollectionId,
                Ordinal = 0,
                ContentId = "old:1",
            });
            await db.SaveChangesAsync();
        }

        failure.Armed = true;
        announcement.Items = [new ShareGrantAnnouncementItem { ContentId = "new:1" }];

        var exception = await Assert.ThrowsAsync<DbUpdateException>(() =>
            CreateService(fixture.Factory).IngestAsync(announcement, senderUsername: "alice", default));
        Assert.IsType<InvalidOperationException>(exception.InnerException);

        await using var verification = await fixture.Factory.CreateDbContextAsync();
        var item = Assert.Single(await verification.CollectionItems.AsNoTracking().ToListAsync());
        Assert.Equal("old:1", item.ContentId);
        Assert.Equal("Old", (await verification.Collections.AsNoTracking().SingleAsync()).Title);
        Assert.False(await verification.ShareGrants.AnyAsync());
    }

    [Fact]
    public void Dispose_UnsubscribesSoulseekEvent()
    {
        var soulseekClient = new Mock<ISoulseekClient>();
        var service = new ShareGrantAnnouncementService(
            Mock.Of<Microsoft.EntityFrameworkCore.IDbContextFactory<CollectionsDbContext>>(),
            NullLogger<ShareGrantAnnouncementService>.Instance,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            soulseekClient.Object);

        service.Dispose();

        soulseekClient.VerifyRemove(x => x.PrivateMessageReceived -= It.IsAny<EventHandler<PrivateMessageReceivedEventArgs>>(), Times.Once);
    }

    private static ShareGrantAnnouncementService CreateService(Microsoft.EntityFrameworkCore.IDbContextFactory<CollectionsDbContext> factory)
    {
        return new ShareGrantAnnouncementService(
            factory,
            NullLogger<ShareGrantAnnouncementService>.Instance,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options
            {
                Soulseek = new slskd.Options.SoulseekOptions
                {
                    Username = "recipient",
                },
            }));
    }

    private static ShareGrantAnnouncement CreateAnnouncement(string ownerUserId)
    {
        return new ShareGrantAnnouncement
        {
            ShareGrantId = Guid.NewGuid(),
            CollectionId = Guid.NewGuid(),
            CollectionTitle = "Shared",
            OwnerUserId = ownerUserId,
            OwnerEndpoint = "https://owner.example.test",
            Token = "share-token",
            RecipientUserId = "recipient",
            Items =
            [
                new ShareGrantAnnouncementItem
                {
                    ContentId = "track:1",
                    MediaKind = "audio",
                },
            ],
        };
    }

    private sealed class CollectionsDbFixture : IDisposable
    {
        private readonly string _dbPath;

        public CollectionsDbFixture(params IInterceptor[] interceptors)
        {
            _dbPath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"share_grant_{Guid.NewGuid()}.db");
            var optionsBuilder = new DbContextOptionsBuilder<CollectionsDbContext>()
                .UseSqlite($"Data Source={_dbPath}");
            if (interceptors.Length > 0)
            {
                optionsBuilder.AddInterceptors(interceptors);
            }

            var options = optionsBuilder.Options;

            Factory = new TestDbContextFactory(options);

            using var db = new CollectionsDbContext(options);
            db.Database.EnsureCreated();
        }

        public Microsoft.EntityFrameworkCore.IDbContextFactory<CollectionsDbContext> Factory { get; }

        public void Dispose()
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={_dbPath}");
            if (System.IO.File.Exists(_dbPath))
            {
                System.IO.File.Delete(_dbPath);
            }
        }
    }

    private sealed class TestDbContextFactory : Microsoft.EntityFrameworkCore.IDbContextFactory<CollectionsDbContext>
    {
        private readonly DbContextOptions<CollectionsDbContext> _options;

        public TestDbContextFactory(DbContextOptions<CollectionsDbContext> options)
        {
            _options = options;
        }

        public CollectionsDbContext CreateDbContext() => new(_options);
    }

    private sealed class CommandCaptureInterceptor : DbCommandInterceptor
    {
        public List<string> Commands { get; } = new();

        public override ValueTask<InterceptionResult<int>> NonQueryExecutingAsync(
            DbCommand command,
            CommandEventData eventData,
            InterceptionResult<int> result,
            CancellationToken cancellationToken = default)
        {
            Commands.Add(command.CommandText);
            return ValueTask.FromResult(result);
        }

        public override ValueTask<InterceptionResult<DbDataReader>> ReaderExecutingAsync(
            DbCommand command,
            CommandEventData eventData,
            InterceptionResult<DbDataReader> result,
            CancellationToken cancellationToken = default)
        {
            Commands.Add(command.CommandText);
            return ValueTask.FromResult(result);
        }
    }

    private sealed class CollectionItemMaterializationInterceptor : IMaterializationInterceptor
    {
        public int Count { get; set; }

        public object InitializedInstance(MaterializationInterceptionData materializationData, object entity)
        {
            if (entity is CollectionItem)
            {
                Count++;
            }

            return entity;
        }
    }

    private sealed class CollectionItemInsertFailureInterceptor : DbCommandInterceptor
    {
        public bool Armed { get; set; }

        public override ValueTask<InterceptionResult<DbDataReader>> ReaderExecutingAsync(
            DbCommand command,
            CommandEventData eventData,
            InterceptionResult<DbDataReader> result,
            CancellationToken cancellationToken = default)
        {
            ThrowIfArmed(command);
            return ValueTask.FromResult(result);
        }

        public override ValueTask<InterceptionResult<int>> NonQueryExecutingAsync(
            DbCommand command,
            CommandEventData eventData,
            InterceptionResult<int> result,
            CancellationToken cancellationToken = default)
        {
            ThrowIfArmed(command);
            return ValueTask.FromResult(result);
        }

        private void ThrowIfArmed(DbCommand command)
        {
            if (Armed &&
                command.CommandText.Contains("INSERT INTO \"CollectionItems\"", StringComparison.Ordinal))
            {
                throw new InvalidOperationException("Injected collection-item insert failure");
            }
        }
    }
}
