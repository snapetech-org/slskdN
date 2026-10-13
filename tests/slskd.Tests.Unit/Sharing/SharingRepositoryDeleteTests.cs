// <copyright file="SharingRepositoryDeleteTests.cs" company="slskdN Team">
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
using slskd.Sharing;
using Xunit;

public sealed class SharingRepositoryDeleteTests : IDisposable
{
    private readonly string _dbPath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"sharing_delete_{Guid.NewGuid()}.db");
    private readonly CommandCaptureInterceptor _commands = new();
    private readonly IDbContextFactory<CollectionsDbContext> _factory;

    public SharingRepositoryDeleteTests()
    {
        var options = new DbContextOptionsBuilder<CollectionsDbContext>()
            .UseSqlite($"Data Source={_dbPath}")
            .AddInterceptors(_commands)
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
    public async Task CollectionDeletes_UseOneCommandAndPreserveResultsAndCascades()
    {
        var deletedCollectionId = Guid.NewGuid();
        var survivingCollectionId = Guid.NewGuid();
        var directItem = new CollectionItem { CollectionId = survivingCollectionId, ContentId = "direct" };
        await using (var db = await _factory.CreateDbContextAsync())
        {
            db.Collections.AddRange(
                new Collection { Id = deletedCollectionId, OwnerUserId = "owner", Title = "Deleted" },
                new Collection { Id = survivingCollectionId, OwnerUserId = "owner", Title = "Surviving" });
            db.CollectionItems.AddRange(
                new CollectionItem { CollectionId = deletedCollectionId, ContentId = "cascade" },
                directItem);
            db.ShareGrants.Add(new ShareGrant
            {
                CollectionId = deletedCollectionId,
                AudienceType = AudienceTypes.User,
                AudienceId = "recipient",
            });
            await db.SaveChangesAsync();
        }

        var repository = new CollectionRepository(_factory);
        _commands.Commands.Clear();
        Assert.True(await repository.RemoveItemAsync(directItem.Id));
        AssertSingleDelete("CollectionItems");

        _commands.Commands.Clear();
        Assert.False(await repository.RemoveItemAsync(Guid.NewGuid()));
        AssertSingleDelete("CollectionItems");

        _commands.Commands.Clear();
        Assert.True(await repository.DeleteAsync(deletedCollectionId));
        AssertSingleDelete("Collections");

        _commands.Commands.Clear();
        Assert.False(await repository.DeleteAsync(Guid.NewGuid()));
        AssertSingleDelete("Collections");

        await using var verification = await _factory.CreateDbContextAsync();
        Assert.False(await verification.CollectionItems.AnyAsync());
        Assert.False(await verification.ShareGrants.AnyAsync());
        Assert.True(await verification.Collections.AnyAsync(collection => collection.Id == survivingCollectionId));
    }

    [Fact]
    public async Task ShareGrantDeletes_UseOneCommandAndPreserveResults()
    {
        var collectionId = Guid.NewGuid();
        var grant = new ShareGrant
        {
            CollectionId = collectionId,
            AudienceType = AudienceTypes.User,
            AudienceId = "recipient",
        };
        await using (var db = await _factory.CreateDbContextAsync())
        {
            db.Collections.Add(new Collection { Id = collectionId, OwnerUserId = "owner", Title = "Collection" });
            db.ShareGrants.Add(grant);
            await db.SaveChangesAsync();
        }

        var repository = new ShareGrantRepository(_factory);
        _commands.Commands.Clear();
        Assert.True(await repository.DeleteAsync(grant.Id));
        AssertSingleDelete("ShareGrants");

        _commands.Commands.Clear();
        Assert.False(await repository.DeleteAsync(Guid.NewGuid()));
        AssertSingleDelete("ShareGrants");
    }

    [Fact]
    public async Task ShareGroupDeletes_UseOneCommandAndPreserveNoOpAndCascadeBehavior()
    {
        var deletedGroupId = Guid.NewGuid();
        var survivingGroupId = Guid.NewGuid();
        await using (var db = await _factory.CreateDbContextAsync())
        {
            db.ShareGroups.AddRange(
                new ShareGroup { Id = deletedGroupId, OwnerUserId = "owner", Name = "Deleted" },
                new ShareGroup { Id = survivingGroupId, OwnerUserId = "owner", Name = "Surviving" });
            db.ShareGroupMembers.AddRange(
                new ShareGroupMember { ShareGroupId = deletedGroupId, UserId = "cascade" },
                new ShareGroupMember { ShareGroupId = survivingGroupId, UserId = "direct" });
            await db.SaveChangesAsync();
        }

        var repository = new ShareGroupRepository(_factory);
        _commands.Commands.Clear();
        await repository.RemoveMemberAsync(survivingGroupId, "direct");
        AssertSingleDelete("ShareGroupMembers");

        _commands.Commands.Clear();
        await repository.RemoveMemberAsync(survivingGroupId, "missing");
        AssertSingleDelete("ShareGroupMembers");

        _commands.Commands.Clear();
        Assert.True(await repository.DeleteAsync(deletedGroupId));
        AssertSingleDelete("ShareGroups");

        _commands.Commands.Clear();
        Assert.False(await repository.DeleteAsync(Guid.NewGuid()));
        AssertSingleDelete("ShareGroups");

        await using var verification = await _factory.CreateDbContextAsync();
        Assert.False(await verification.ShareGroupMembers.AnyAsync());
        Assert.True(await verification.ShareGroups.AnyAsync(group => group.Id == survivingGroupId));
    }

    private void AssertSingleDelete(string table)
    {
        var command = Assert.Single(_commands.Commands);
        Assert.StartsWith($"DELETE FROM \"{table}\"", command.TrimStart(), StringComparison.OrdinalIgnoreCase);
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
}
