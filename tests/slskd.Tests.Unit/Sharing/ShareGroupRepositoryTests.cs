// <copyright file="ShareGroupRepositoryTests.cs" company="slskdN Team">
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

public class ShareGroupRepositoryTests : IDisposable
{
    private readonly string _dbPath;
    private readonly CommandCaptureInterceptor _commands = new();
    private readonly IDbContextFactory<CollectionsDbContext> _factory;

    public ShareGroupRepositoryTests()
    {
        _dbPath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"test_{Guid.NewGuid()}.db");
        var options = new DbContextOptionsBuilder<CollectionsDbContext>()
            .UseSqlite($"Data Source={_dbPath}")
            .AddInterceptors(_commands)
            .Options;
        _factory = new TestDbContextFactory(options);

        // Ensure database is created
        using var db = new CollectionsDbContext(options);
        db.Database.EnsureCreated();
        _commands.Commands.Clear();
    }

    public void Dispose()
    {
        slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={_dbPath}");
        if (System.IO.File.Exists(_dbPath))
            System.IO.File.Delete(_dbPath);
    }

    [Fact]
    public async Task AddMemberAsync_CreatesAndDeduplicatesWithOneCommand()
    {
        var repo = new ShareGroupRepository(_factory);
        var groupId = Guid.NewGuid();
        using (var db = await _factory.CreateDbContextAsync())
        {
            db.ShareGroups.Add(new ShareGroup { Id = groupId, Name = "Test", OwnerUserId = "alice" });
            await db.SaveChangesAsync();
        }

        _commands.Commands.Clear();
        await repo.AddMemberAsync(groupId, "bob", default);
        AssertSingleConditionalInsert();

        _commands.Commands.Clear();
        await repo.AddMemberAsync(groupId, "bob", default);
        AssertSingleConditionalInsert();

        using var verification = await _factory.CreateDbContextAsync();
        var member = Assert.Single(await verification.ShareGroupMembers.AsNoTracking().ToListAsync());
        Assert.Equal("bob", member.UserId);
        Assert.Null(member.PeerId);
    }

    [Fact]
    public async Task AddMemberByPeerIdAsync_CreatesMemberWithPeerId()
    {
        var repo = new ShareGroupRepository(_factory);
        var groupId = Guid.NewGuid();
        var group = new ShareGroup { Id = groupId, Name = "Test", OwnerUserId = "alice" };

        using (var db = await _factory.CreateDbContextAsync())
        {
            db.ShareGroups.Add(group);
            await db.SaveChangesAsync();
        }

        _commands.Commands.Clear();
        await repo.AddMemberByPeerIdAsync(groupId, "peer123", default);
        AssertSingleConditionalInsert();

        using (var db = await _factory.CreateDbContextAsync())
        {
            var member = await db.ShareGroupMembers.FirstOrDefaultAsync(m => m.ShareGroupId == groupId && m.PeerId == "peer123");
            Assert.NotNull(member);
            Assert.Equal("peer123", member.PeerId);
            Assert.Equal("peer123", member.UserId); // UserId should be set to PeerId for backward compatibility
        }
    }

    [Fact]
    public async Task AddMemberByPeerIdAsync_Duplicate_DoesNotAddAgain()
    {
        var repo = new ShareGroupRepository(_factory);
        var groupId = Guid.NewGuid();
        var group = new ShareGroup { Id = groupId, Name = "Test", OwnerUserId = "alice" };

        using (var db = await _factory.CreateDbContextAsync())
        {
            db.ShareGroups.Add(group);
            await db.SaveChangesAsync();
        }

        _commands.Commands.Clear();
        await repo.AddMemberByPeerIdAsync(groupId, "peer123", default);
        AssertSingleConditionalInsert();

        _commands.Commands.Clear();
        await repo.AddMemberByPeerIdAsync(groupId, "peer123", default);
        AssertSingleConditionalInsert();

        using (var db = await _factory.CreateDbContextAsync())
        {
            var count = await db.ShareGroupMembers.CountAsync(m => m.ShareGroupId == groupId && m.PeerId == "peer123");
            Assert.Equal(1, count);
        }
    }

    [Fact]
    public async Task AddMemberByPeerIdAsync_DuplicateLegacyPeer_DoesNotAddAgain()
    {
        var repo = new ShareGroupRepository(_factory);
        var groupId = Guid.NewGuid();
        using (var db = await _factory.CreateDbContextAsync())
        {
            db.ShareGroups.Add(new ShareGroup { Id = groupId, Name = "Test", OwnerUserId = "alice" });
            db.ShareGroupMembers.Add(new ShareGroupMember
            {
                ShareGroupId = groupId,
                UserId = "legacy-user-id",
                PeerId = "peer123",
            });
            await db.SaveChangesAsync();
        }

        _commands.Commands.Clear();
        await repo.AddMemberByPeerIdAsync(groupId, "peer123", default);
        AssertSingleConditionalInsert();

        using var verification = await _factory.CreateDbContextAsync();
        var member = Assert.Single(await verification.ShareGroupMembers.AsNoTracking().ToListAsync());
        Assert.Equal("legacy-user-id", member.UserId);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task AddMemberAsync_MissingGroup_PreservesForeignKeyFailure(bool byPeerId)
    {
        var repository = new ShareGroupRepository(_factory);
        Func<Task> addMember = byPeerId
            ? () => repository.AddMemberByPeerIdAsync(Guid.NewGuid(), "peer123", default)
            : () => repository.AddMemberAsync(Guid.NewGuid(), "bob", default);
        _commands.Commands.Clear();
        var exception = await Assert.ThrowsAsync<DbUpdateException>(addMember);
        Assert.IsType<SqliteException>(exception.InnerException);
        AssertSingleConditionalInsert();
    }

    [Fact]
    public async Task RemoveMemberByPeerIdAsync_RemovesMember()
    {
        var repo = new ShareGroupRepository(_factory);
        var groupId = Guid.NewGuid();
        var group = new ShareGroup { Id = groupId, Name = "Test", OwnerUserId = "alice" };

        using (var db = await _factory.CreateDbContextAsync())
        {
            db.ShareGroups.Add(group);
            db.ShareGroupMembers.Add(new ShareGroupMember { ShareGroupId = groupId, UserId = "peer123", PeerId = "peer123" });
            await db.SaveChangesAsync();
        }

        _commands.Commands.Clear();
        await repo.RemoveMemberByPeerIdAsync(groupId, "peer123", default);
        AssertSinglePeerDelete();

        using (var db = await _factory.CreateDbContextAsync())
        {
            var member = await db.ShareGroupMembers.FirstOrDefaultAsync(m => m.ShareGroupId == groupId && m.PeerId == "peer123");
            Assert.Null(member);
        }
    }

    [Fact]
    public async Task RemoveMemberByPeerIdAsync_DuplicatePeer_RemovesOnlyOneMember()
    {
        var repo = new ShareGroupRepository(_factory);
        var groupId = Guid.NewGuid();
        using (var db = await _factory.CreateDbContextAsync())
        {
            db.ShareGroups.Add(new ShareGroup { Id = groupId, Name = "Test", OwnerUserId = "alice" });
            db.ShareGroupMembers.AddRange(
                new ShareGroupMember { ShareGroupId = groupId, UserId = "legacy-1", PeerId = "peer123" },
                new ShareGroupMember { ShareGroupId = groupId, UserId = "legacy-2", PeerId = "peer123" });
            await db.SaveChangesAsync();
        }

        _commands.Commands.Clear();
        await repo.RemoveMemberByPeerIdAsync(groupId, "peer123", default);
        AssertSinglePeerDelete();

        using var verification = await _factory.CreateDbContextAsync();
        Assert.Single(await verification.ShareGroupMembers.AsNoTracking().ToListAsync());
    }

    [Fact]
    public async Task RemoveMemberByPeerIdAsync_MissingPeer_UsesOneNoOpCommand()
    {
        _commands.Commands.Clear();
        await new ShareGroupRepository(_factory).RemoveMemberByPeerIdAsync(Guid.NewGuid(), "missing", default);
        AssertSinglePeerDelete();
    }

    [Fact]
    public async Task RemoveMemberByPeerIdAsync_DeleteFailure_PreservesExceptionBoundary()
    {
        var groupId = Guid.NewGuid();
        using (var db = await _factory.CreateDbContextAsync())
        {
            db.ShareGroups.Add(new ShareGroup { Id = groupId, Name = "Test", OwnerUserId = "alice" });
            db.ShareGroupMembers.Add(new ShareGroupMember { ShareGroupId = groupId, UserId = "peer123", PeerId = "peer123" });
            await db.SaveChangesAsync();
            await db.Database.ExecuteSqlRawAsync("""
                CREATE TRIGGER BlockMemberDelete
                BEFORE DELETE ON ShareGroupMembers
                BEGIN
                    SELECT RAISE(ABORT, 'blocked');
                END
                """);
        }

        _commands.Commands.Clear();
        var exception = await Assert.ThrowsAsync<DbUpdateException>(() =>
            new ShareGroupRepository(_factory).RemoveMemberByPeerIdAsync(groupId, "peer123", default));
        Assert.IsType<SqliteException>(exception.InnerException);
        AssertSinglePeerDelete();
    }

    [Fact]
    public async Task GetMembersAsync_ReturnsAllMembers()
    {
        var repo = new ShareGroupRepository(_factory);
        var groupId = Guid.NewGuid();
        var group = new ShareGroup { Id = groupId, Name = "Test", OwnerUserId = "alice" };

        using (var db = await _factory.CreateDbContextAsync())
        {
            db.ShareGroups.Add(group);
            db.ShareGroupMembers.Add(new ShareGroupMember { ShareGroupId = groupId, UserId = "bob", PeerId = null });
            db.ShareGroupMembers.Add(new ShareGroupMember { ShareGroupId = groupId, UserId = "peer123", PeerId = "peer123" });
            await db.SaveChangesAsync();
        }

        var members = await repo.GetMembersAsync(groupId, default);

        Assert.Equal(2, members.Count);
        Assert.Contains(members, m => m.PeerId == "peer123");
        Assert.Contains(members, m => m.PeerId == null && m.UserId == "bob");
    }

    [Fact]
    public async Task IsMemberByPeerIdAsync_ReturnsTrueWhenMember()
    {
        var repo = new ShareGroupRepository(_factory);
        var groupId = Guid.NewGuid();
        var group = new ShareGroup { Id = groupId, Name = "Test", OwnerUserId = "alice" };

        using (var db = await _factory.CreateDbContextAsync())
        {
            db.ShareGroups.Add(group);
            db.ShareGroupMembers.Add(new ShareGroupMember { ShareGroupId = groupId, UserId = "peer123", PeerId = "peer123" });
            await db.SaveChangesAsync();
        }

        var isMember = await repo.IsMemberByPeerIdAsync(groupId, "peer123", default);

        Assert.True(isMember);
    }

    [Fact]
    public async Task IsMemberByPeerIdAsync_ReturnsFalseWhenNotMember()
    {
        var repo = new ShareGroupRepository(_factory);
        var groupId = Guid.NewGuid();
        var group = new ShareGroup { Id = groupId, Name = "Test", OwnerUserId = "alice" };

        using (var db = await _factory.CreateDbContextAsync())
        {
            db.ShareGroups.Add(group);
            await db.SaveChangesAsync();
        }

        var isMember = await repo.IsMemberByPeerIdAsync(groupId, "peer123", default);

        Assert.False(isMember);
    }

    private void AssertSingleConditionalInsert()
    {
        var command = Assert.Single(_commands.Commands);
        Assert.StartsWith("INSERT INTO \"ShareGroupMembers\"", command.TrimStart(), StringComparison.OrdinalIgnoreCase);
        Assert.Contains("WHERE NOT EXISTS", command, StringComparison.OrdinalIgnoreCase);
    }

    private void AssertSinglePeerDelete()
    {
        var command = Assert.Single(_commands.Commands);
        Assert.StartsWith("DELETE FROM \"ShareGroupMembers\"", command.TrimStart(), StringComparison.OrdinalIgnoreCase);
        Assert.Contains("WHERE rowid =", command, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("LIMIT 1", command, StringComparison.OrdinalIgnoreCase);
    }

    private class TestDbContextFactory : IDbContextFactory<CollectionsDbContext>
    {
        private readonly DbContextOptions<CollectionsDbContext> _options;

        public TestDbContextFactory(DbContextOptions<CollectionsDbContext> options)
        {
            _options = options;
        }

        public CollectionsDbContext CreateDbContext() => new(_options);

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
