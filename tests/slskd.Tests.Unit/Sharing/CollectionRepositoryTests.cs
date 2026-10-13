// <copyright file="CollectionRepositoryTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Sharing;

using System;
using System.Collections.Generic;
using System.Data.Common;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using slskd.Sharing;
using Xunit;

public sealed class CollectionRepositoryTests : IDisposable
{
    private readonly string _dbPath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"collection_repository_{Guid.NewGuid()}.db");
    private readonly CommandCaptureInterceptor _commands = new();
    private readonly CollectionItemMaterializationInterceptor _materialization = new();
    private readonly IDbContextFactory<CollectionsDbContext> _factory;

    public CollectionRepositoryTests()
    {
        var options = new DbContextOptionsBuilder<CollectionsDbContext>()
            .UseSqlite($"Data Source={_dbPath}")
            .AddInterceptors(_commands, _materialization)
            .Options;
        _factory = new TestDbContextFactory(options);

        using var db = new CollectionsDbContext(options);
        db.Database.EnsureCreated();
        _commands.Commands.Clear();
    }

    public void Dispose()
    {
        slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={_dbPath}");
        if (System.IO.File.Exists(_dbPath))
        {
            System.IO.File.Delete(_dbPath);
        }
    }

    [Fact]
    public async Task ContainsContentAsync_UsesCompositeIndexWithoutHydration()
    {
        var collectionId = Guid.NewGuid();
        var otherCollectionId = Guid.NewGuid();
        await using (var db = await _factory.CreateDbContextAsync())
        {
            db.Collections.AddRange(
                new Collection { Id = collectionId, OwnerUserId = "owner", Title = "Collection" },
                new Collection { Id = otherCollectionId, OwnerUserId = "owner", Title = "Other" });
            db.CollectionItems.AddRange(Enumerable.Range(0, 1000).Select(index => new CollectionItem
            {
                CollectionId = collectionId,
                ContentId = $"content:{index:D4}",
                Ordinal = index,
            }));
            await db.SaveChangesAsync();
        }

        var repository = new CollectionRepository(_factory);
        _commands.Commands.Clear();
        _materialization.Count = 0;
        Assert.True(await repository.ContainsContentAsync(collectionId, "content:0777"));
        Assert.Equal(0, _materialization.Count);
        var command = Assert.Single(_commands.Commands);
        Assert.Contains("EXISTS", command, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("\"CollectionId\"", command, StringComparison.Ordinal);
        Assert.Contains("\"ContentId\"", command, StringComparison.Ordinal);

        _commands.Commands.Clear();
        Assert.False(await repository.ContainsContentAsync(collectionId, "CONTENT:0777"));
        Assert.False(await repository.ContainsContentAsync(otherCollectionId, "content:0777"));
        Assert.Equal(2, _commands.Commands.Count);

        await using var verification = await _factory.CreateDbContextAsync();
        await verification.Database.OpenConnectionAsync();
        await using var plan = verification.Database.GetDbConnection().CreateCommand();
        plan.CommandText = """
            EXPLAIN QUERY PLAN
            SELECT 1
            FROM CollectionItems
            WHERE CollectionId = $collection_id
              AND ContentId = $content_id
            LIMIT 1
            """;
        var collectionParameter = plan.CreateParameter();
        collectionParameter.ParameterName = "$collection_id";
        collectionParameter.Value = collectionId;
        plan.Parameters.Add(collectionParameter);
        var contentParameter = plan.CreateParameter();
        contentParameter.ParameterName = "$content_id";
        contentParameter.Value = "content:0777";
        plan.Parameters.Add(contentParameter);
        await using var reader = await plan.ExecuteReaderAsync();
        Assert.True(await reader.ReadAsync());
        Assert.Contains(
            "IX_CollectionItems_CollectionId_ContentId",
            reader.GetString(3),
            StringComparison.Ordinal);
    }

    [Fact]
    public async Task ContentLookupIndexUpgrade_IsIdempotentAndRestoresIndex()
    {
        await using var db = await _factory.CreateDbContextAsync();
        await db.Database.ExecuteSqlRawAsync($"DROP INDEX {CollectionsDbContext.ContentLookupIndexName}");
        await db.Database.ExecuteSqlRawAsync(CollectionsDbContext.ContentLookupIndexSql);
        await db.Database.ExecuteSqlRawAsync(CollectionsDbContext.ContentLookupIndexSql);

        await db.Database.OpenConnectionAsync();
        await using var command = db.Database.GetDbConnection().CreateCommand();
        command.CommandText = "SELECT COUNT(*) FROM sqlite_master WHERE type = 'index' AND name = $name";
        var name = command.CreateParameter();
        name.ParameterName = "$name";
        name.Value = CollectionsDbContext.ContentLookupIndexName;
        command.Parameters.Add(name);
        Assert.Equal(1L, await command.ExecuteScalarAsync());
    }

    [Fact]
    public async Task GetItemAsync_HydratesOnlyTheScopedItem()
    {
        var collectionId = Guid.NewGuid();
        var otherCollectionId = Guid.NewGuid();
        var items = Enumerable.Range(0, 1000)
            .Select(index => new CollectionItem
            {
                CollectionId = collectionId,
                ContentId = $"item:{index:D4}",
                Ordinal = index,
            })
            .ToArray();
        await using (var db = await _factory.CreateDbContextAsync())
        {
            db.Collections.AddRange(
                new Collection { Id = collectionId, OwnerUserId = "owner", Title = "Collection" },
                new Collection { Id = otherCollectionId, OwnerUserId = "owner", Title = "Other" });
            db.CollectionItems.AddRange(items);
            await db.SaveChangesAsync();
        }

        _commands.Commands.Clear();
        _materialization.Count = 0;
        var result = await new CollectionRepository(_factory).GetItemAsync(collectionId, items[777].Id);

        Assert.NotNull(result);
        Assert.Equal(items[777].Id, result.Id);
        Assert.Equal(1, _materialization.Count);
        var command = Assert.Single(_commands.Commands);
        Assert.Contains("SELECT", command, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("\"CollectionId\"", command, StringComparison.Ordinal);
        Assert.Contains("\"Id\"", command, StringComparison.Ordinal);
        Assert.Contains("LIMIT 1", command, StringComparison.OrdinalIgnoreCase);

        _commands.Commands.Clear();
        _materialization.Count = 0;
        Assert.Null(await new CollectionRepository(_factory).GetItemAsync(otherCollectionId, items[777].Id));
        Assert.Equal(0, _materialization.Count);
        Assert.Single(_commands.Commands);
    }

    [Fact]
    public async Task AddItemAsync_AssignsNextOrdinalAndPersistsAllFieldsWithOneCommand()
    {
        var collectionId = Guid.NewGuid();
        await using (var db = await _factory.CreateDbContextAsync())
        {
            db.Collections.Add(new Collection { Id = collectionId, OwnerUserId = "owner", Title = "Collection" });
            db.CollectionItems.Add(new CollectionItem
            {
                CollectionId = collectionId,
                ContentId = "existing",
                Ordinal = 7,
            });
            await db.SaveChangesAsync();
        }

        var item = new CollectionItem
        {
            CollectionId = collectionId,
            ContentId = "content-id",
            MediaKind = "audio",
            FileName = "track.flac",
            Title = "Title",
            Artist = "Artist",
            Album = "Album",
            ContentHash = "hash",
        };
        _commands.Commands.Clear();
        _materialization.Count = 0;

        var result = await new CollectionRepository(_factory).AddItemAsync(item);

        Assert.Same(item, result);
        Assert.Equal(8, result.Ordinal);
        Assert.Equal(0, _materialization.Count);
        var command = Assert.Single(_commands.Commands);
        Assert.StartsWith("INSERT INTO \"CollectionItems\"", command.TrimStart(), StringComparison.OrdinalIgnoreCase);
        Assert.Contains("RETURNING \"Ordinal\"", command, StringComparison.OrdinalIgnoreCase);

        await using var verification = await _factory.CreateDbContextAsync();
        var persisted = await verification.CollectionItems.AsNoTracking().SingleAsync(candidate => candidate.Id == item.Id);
        Assert.Equal(item.CollectionId, persisted.CollectionId);
        Assert.Equal(item.Ordinal, persisted.Ordinal);
        Assert.Equal(item.ContentId, persisted.ContentId);
        Assert.Equal(item.MediaKind, persisted.MediaKind);
        Assert.Equal(item.FileName, persisted.FileName);
        Assert.Equal(item.Title, persisted.Title);
        Assert.Equal(item.Artist, persisted.Artist);
        Assert.Equal(item.Album, persisted.Album);
        Assert.Equal(item.ContentHash, persisted.ContentHash);
    }

    [Fact]
    public async Task AddItemAsync_MissingCollection_PreservesForeignKeyFailure()
    {
        _commands.Commands.Clear();
        var exception = await Assert.ThrowsAsync<DbUpdateException>(() =>
            new CollectionRepository(_factory).AddItemAsync(new CollectionItem
            {
                CollectionId = Guid.NewGuid(),
                ContentId = "missing-parent",
            }));

        Assert.IsType<SqliteException>(exception.InnerException);
        var command = Assert.Single(_commands.Commands);
        Assert.StartsWith("INSERT INTO \"CollectionItems\"", command.TrimStart(), StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task ReorderItemsAsync_UpdatesLargeOrderInBoundedCommandsWithoutHydration()
    {
        var collectionId = Guid.NewGuid();
        var items = Enumerable.Range(0, 1000)
            .Select(index => new CollectionItem
            {
                CollectionId = collectionId,
                ContentId = $"item:{index:D4}",
                Ordinal = index,
            })
            .ToArray();
        await using (var db = await _factory.CreateDbContextAsync())
        {
            db.Collections.Add(new Collection { Id = collectionId, OwnerUserId = "owner", Title = "Collection" });
            db.CollectionItems.AddRange(items);
            await db.SaveChangesAsync();
        }

        var requestedOrder = items.Select(item => item.Id).Reverse().ToArray();
        _commands.Commands.Clear();
        _materialization.Count = 0;

        await new CollectionRepository(_factory).ReorderItemsAsync(collectionId, requestedOrder);

        Assert.Equal(0, _materialization.Count);
        Assert.Equal(3, _commands.Commands.Count);
        Assert.All(_commands.Commands, command =>
            Assert.StartsWith("UPDATE \"CollectionItems\"", command.TrimStart(), StringComparison.OrdinalIgnoreCase));

        await using var verification = await _factory.CreateDbContextAsync();
        var persistedOrder = await verification.CollectionItems
            .AsNoTracking()
            .Where(item => item.CollectionId == collectionId)
            .OrderBy(item => item.Ordinal)
            .Select(item => item.Id)
            .ToArrayAsync();
        Assert.Equal(requestedOrder, persistedOrder);
    }

    [Fact]
    public async Task ReorderItemsAsync_PreservesLastDuplicateAndMissingItemBehavior()
    {
        var collectionId = Guid.NewGuid();
        var first = new CollectionItem { CollectionId = collectionId, ContentId = "first", Ordinal = 10 };
        var second = new CollectionItem { CollectionId = collectionId, ContentId = "second", Ordinal = 11 };
        var untouched = new CollectionItem { CollectionId = collectionId, ContentId = "untouched", Ordinal = 12 };
        await using (var db = await _factory.CreateDbContextAsync())
        {
            db.Collections.Add(new Collection { Id = collectionId, OwnerUserId = "owner", Title = "Collection" });
            db.CollectionItems.AddRange(first, second, untouched);
            await db.SaveChangesAsync();
        }

        _commands.Commands.Clear();
        await new CollectionRepository(_factory).ReorderItemsAsync(
            collectionId,
            [first.Id, Guid.NewGuid(), second.Id, first.Id]);
        Assert.Single(_commands.Commands);

        await using (var verification = await _factory.CreateDbContextAsync())
        {
            var ordinals = await verification.CollectionItems
                .AsNoTracking()
                .ToDictionaryAsync(item => item.ContentId, item => item.Ordinal);
            Assert.Equal(3, ordinals["first"]);
            Assert.Equal(2, ordinals["second"]);
            Assert.Equal(12, ordinals["untouched"]);
        }

        _commands.Commands.Clear();
        await new CollectionRepository(_factory).ReorderItemsAsync(collectionId, Array.Empty<Guid>());
        Assert.Empty(_commands.Commands);
    }

    private sealed class TestDbContextFactory(DbContextOptions<CollectionsDbContext> options)
        : IDbContextFactory<CollectionsDbContext>
    {
        public CollectionsDbContext CreateDbContext() => new(options);

        public ValueTask<CollectionsDbContext> CreateDbContextAsync(CancellationToken cancellationToken = default) =>
            ValueTask.FromResult(CreateDbContext());
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
}
