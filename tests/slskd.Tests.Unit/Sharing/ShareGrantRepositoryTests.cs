// <copyright file="ShareGrantRepositoryTests.cs" company="slskdN Team">
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

public sealed class ShareGrantRepositoryTests : IDisposable
{
    private readonly string _dbPath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"test_{Guid.NewGuid()}.db");
    private readonly CommandCaptureInterceptor _interceptor = new();
    private readonly ShareGrantMaterializationInterceptor _materialization = new();
    private readonly IDbContextFactory<CollectionsDbContext> _factory;

    public ShareGrantRepositoryTests()
    {
        var options = new DbContextOptionsBuilder<CollectionsDbContext>()
            .UseSqlite($"Data Source={_dbPath}")
            .AddInterceptors(_interceptor, _materialization)
            .Options;
        _factory = new TestDbContextFactory(options);

        using var db = new CollectionsDbContext(options);
        db.Database.EnsureCreated();
        _interceptor.Commands.Clear();
    }

    public void Dispose()
    {
        slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={_dbPath}");
        if (System.IO.File.Exists(_dbPath))
            System.IO.File.Delete(_dbPath);
    }

    [Fact]
    public async Task HasCollectionAccessAsync_UsesIndexedScalarQueryWithoutGrantHydration()
    {
        var directCollectionId = Guid.NewGuid();
        var groupCollectionId = Guid.NewGuid();
        var otherCollectionId = Guid.NewGuid();
        var groupId = Guid.NewGuid();
        await using (var db = await _factory.CreateDbContextAsync())
        {
            db.Collections.AddRange(
                new Collection { Id = directCollectionId, OwnerUserId = "owner", Title = "Direct" },
                new Collection { Id = groupCollectionId, OwnerUserId = "owner", Title = "Group" },
                new Collection { Id = otherCollectionId, OwnerUserId = "owner", Title = "Other" });
            db.ShareGroups.Add(new ShareGroup { Id = groupId, Name = "Group", OwnerUserId = "owner" });
            db.ShareGroupMembers.Add(new ShareGroupMember { ShareGroupId = groupId, UserId = "alice" });
            db.ShareGrants.Add(CreateGrant(directCollectionId, AudienceTypes.User, "alice"));
            db.ShareGrants.Add(CreateGrant(groupCollectionId, AudienceTypes.ShareGroup, groupId.ToString().ToLowerInvariant()));
            db.ShareGrants.Add(CreateGrant(groupCollectionId, AudienceTypes.User, "alice", DateTime.UtcNow.AddMinutes(-1)));
            db.ShareGrants.AddRange(Enumerable.Range(0, 1000)
                .Select(_ => CreateGrant(otherCollectionId, AudienceTypes.User, "alice")));
            await db.SaveChangesAsync();
        }

        var repository = new ShareGrantRepository(_factory);
        _interceptor.Commands.Clear();
        _materialization.Count = 0;
        Assert.True(await repository.HasCollectionAccessAsync(directCollectionId, "alice"));
        Assert.Equal(0, _materialization.Count);
        var directCommand = Assert.Single(_interceptor.Commands);
        Assert.Contains("SELECT EXISTS", directCommand, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("\"CollectionId\"", directCommand, StringComparison.Ordinal);
        Assert.Contains("ShareGroupMembers", directCommand, StringComparison.Ordinal);

        _interceptor.Commands.Clear();
        Assert.True(await repository.HasCollectionAccessAsync(groupCollectionId, "alice"));
        Assert.False(await repository.HasCollectionAccessAsync(groupCollectionId, "bob"));
        Assert.False(await repository.HasCollectionAccessAsync(otherCollectionId, "bob"));
        Assert.Equal(3, _interceptor.Commands.Count);
        Assert.Equal(0, _materialization.Count);

        await using var verification = await _factory.CreateDbContextAsync();
        await verification.Database.OpenConnectionAsync();
        await using var plan = verification.Database.GetDbConnection().CreateCommand();
        plan.CommandText = """
            EXPLAIN QUERY PLAN
            SELECT 1
            FROM ShareGrants AS grant
            WHERE grant.CollectionId = $collection_id
              AND (grant.ExpiryUtc IS NULL OR grant.ExpiryUtc > $now)
              AND (
                  (grant.AudienceType = 'User' AND grant.AudienceId = $user_id)
                  OR (
                      grant.AudienceType = 'ShareGroup'
                      AND EXISTS (
                          SELECT 1
                          FROM ShareGroupMembers AS member
                          WHERE member.UserId = $user_id
                            AND member.ShareGroupId = grant.AudienceId COLLATE NOCASE)))
            LIMIT 1
            """;
        AddPlanParameter(plan, "$collection_id", groupCollectionId);
        AddPlanParameter(plan, "$user_id", "alice");
        AddPlanParameter(plan, "$now", DateTime.UtcNow);
        await using var reader = await plan.ExecuteReaderAsync();
        var details = new List<string>();
        while (await reader.ReadAsync())
        {
            details.Add(reader.GetString(3));
        }

        Assert.Contains(details, detail => detail.Contains("IX_ShareGrants_CollectionId", StringComparison.Ordinal));
        Assert.Contains(details, detail => detail.Contains("sqlite_autoindex_ShareGroupMembers_1", StringComparison.Ordinal));
    }

    [Fact]
    public async Task GetAccessibleByIdAsync_DirectGrant_HydratesOnlyTarget()
    {
        var collectionId = Guid.NewGuid();
        var target = CreateGrant(collectionId, AudienceTypes.User, "alice");
        await using (var db = await _factory.CreateDbContextAsync())
        {
            db.Collections.Add(new Collection { Id = collectionId, OwnerUserId = "owner", Title = "Test" });
            db.ShareGrants.Add(target);
            db.ShareGrants.AddRange(Enumerable.Range(0, 1000)
                .Select(_ => CreateGrant(collectionId, AudienceTypes.User, "alice")));
            await db.SaveChangesAsync();
        }

        _interceptor.Commands.Clear();
        _materialization.Count = 0;
        var result = await new ShareGrantRepository(_factory).GetAccessibleByIdAsync(target.Id, "alice");

        Assert.NotNull(result);
        Assert.Equal(target.Id, result.Id);
        Assert.Equal(1, _materialization.Count);
        var command = Assert.Single(_interceptor.Commands);
        Assert.Contains("\"Id\"", command, StringComparison.Ordinal);
        Assert.Contains("LIMIT 1", command, StringComparison.OrdinalIgnoreCase);

        _interceptor.Commands.Clear();
        _materialization.Count = 0;
        Assert.Null(await new ShareGrantRepository(_factory).GetAccessibleByIdAsync(target.Id, "bob"));
        Assert.Equal(0, _materialization.Count);
        Assert.Single(_interceptor.Commands);
    }

    [Fact]
    public async Task GetAccessibleByIdAsync_GroupGrant_QueriesOnlyTargetMembership()
    {
        var collectionId = Guid.NewGuid();
        var groupId = Guid.NewGuid();
        var grant = CreateGrant(collectionId, AudienceTypes.ShareGroup, groupId.ToString());
        await using (var db = await _factory.CreateDbContextAsync())
        {
            db.Collections.Add(new Collection { Id = collectionId, OwnerUserId = "owner", Title = "Test" });
            db.ShareGroups.Add(new ShareGroup { Id = groupId, Name = "Group", OwnerUserId = "owner" });
            db.ShareGroupMembers.Add(new ShareGroupMember { ShareGroupId = groupId, UserId = "alice" });
            db.ShareGrants.Add(grant);
            await db.SaveChangesAsync();
        }

        _interceptor.Commands.Clear();
        _materialization.Count = 0;
        var result = await new ShareGrantRepository(_factory).GetAccessibleByIdAsync(grant.Id, "alice");

        Assert.NotNull(result);
        Assert.Equal(grant.Id, result.Id);
        Assert.Equal(1, _materialization.Count);
        Assert.Equal(2, _interceptor.Commands.Count);

        _interceptor.Commands.Clear();
        _materialization.Count = 0;
        Assert.Null(await new ShareGrantRepository(_factory).GetAccessibleByIdAsync(grant.Id, "bob"));
        Assert.Equal(1, _materialization.Count);
        Assert.Equal(2, _interceptor.Commands.Count);
    }

    [Fact]
    public async Task GetAccessibleByUserAsync_FiltersGroupMembershipInSingleQuery()
    {
        var collectionId = Guid.NewGuid();
        var memberGroupId = Guid.NewGuid();
        var otherGroupId = Guid.NewGuid();
        var directGrant = CreateGrant(collectionId, AudienceTypes.User, "alice");
        var memberGrant = CreateGrant(collectionId, AudienceTypes.ShareGroup, memberGroupId.ToString());
        var duplicateMemberGrant = CreateGrant(collectionId, AudienceTypes.ShareGroup, memberGroupId.ToString());
        var otherGroupGrant = CreateGrant(collectionId, AudienceTypes.ShareGroup, otherGroupId.ToString());
        var malformedGroupGrant = CreateGrant(collectionId, AudienceTypes.ShareGroup, "not-a-guid");
        var expiredGrant = CreateGrant(collectionId, AudienceTypes.User, "alice", DateTime.UtcNow.AddMinutes(-1));

        await using (var db = await _factory.CreateDbContextAsync())
        {
            db.Collections.Add(new Collection { Id = collectionId, OwnerUserId = "owner", Title = "Test" });
            db.ShareGroups.AddRange(
                new ShareGroup { Id = memberGroupId, Name = "Member", OwnerUserId = "owner" },
                new ShareGroup { Id = otherGroupId, Name = "Other", OwnerUserId = "owner" });
            db.ShareGroupMembers.Add(new ShareGroupMember { ShareGroupId = memberGroupId, UserId = "alice" });
            db.ShareGrants.AddRange(
                directGrant,
                memberGrant,
                duplicateMemberGrant,
                otherGroupGrant,
                malformedGroupGrant,
                expiredGrant,
                CreateGrant(collectionId, AudienceTypes.User, "bob"));
            await db.SaveChangesAsync();
        }

        _interceptor.Commands.Clear();
        var result = await new ShareGrantRepository(_factory).GetAccessibleByUserAsync("alice");

        Assert.Equal(new[] { directGrant.Id, memberGrant.Id, duplicateMemberGrant.Id }.OrderBy(id => id), result.Select(grant => grant.Id).OrderBy(id => id));
        var command = Assert.Single(_interceptor.Commands);
        Assert.Contains("EXISTS", command, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("ShareGroupMembers", command, StringComparison.Ordinal);
    }

    [Fact]
    public async Task GetAccessibleByUserAsync_WideGroupSetHydratesOnlyAccessibleGrants()
    {
        const int groupCount = 100;
        const int grantCount = 10_000;
        var collectionId = Guid.NewGuid();
        var groupIds = Enumerable.Range(0, groupCount).Select(_ => Guid.NewGuid()).ToArray();
        var memberGroupId = groupIds[0];
        var directGrant = CreateGrant(collectionId, AudienceTypes.User, "alice");
        var groupGrants = Enumerable.Range(0, grantCount)
            .Select(index => CreateGrant(collectionId, AudienceTypes.ShareGroup, groupIds[index % groupCount].ToString()))
            .ToList();
        var expectedMemberGrantIds = groupGrants
            .Where(grant => grant.AudienceId == memberGroupId.ToString())
            .Select(grant => grant.Id)
            .ToList();

        await using (var db = await _factory.CreateDbContextAsync())
        {
            db.Collections.Add(new Collection { Id = collectionId, OwnerUserId = "owner", Title = "Wide" });
            db.ShareGroups.Add(new ShareGroup { Id = memberGroupId, Name = "Member", OwnerUserId = "owner" });
            db.ShareGroupMembers.Add(new ShareGroupMember { ShareGroupId = memberGroupId, UserId = "alice" });
            db.ShareGrants.Add(directGrant);
            db.ShareGrants.AddRange(groupGrants);
            await db.SaveChangesAsync();
        }

        _interceptor.Commands.Clear();
        _materialization.Count = 0;
        var result = await new ShareGrantRepository(_factory).GetAccessibleByUserAsync("alice");

        Assert.Equal(1 + expectedMemberGrantIds.Count, result.Count);
        Assert.Equal(directGrant.Id, result[0].Id);
        Assert.Equal(
            expectedMemberGrantIds.OrderBy(id => id),
            result.Skip(1).Select(grant => grant.Id).OrderBy(id => id));
        Assert.Equal(result.Count, _materialization.Count);
        Assert.Single(_interceptor.Commands);
    }

    private static ShareGrant CreateGrant(Guid collectionId, string audienceType, string audienceId, DateTime? expiryUtc = null) =>
        new()
        {
            CollectionId = collectionId,
            AudienceType = audienceType,
            AudienceId = audienceId,
            ExpiryUtc = expiryUtc,
        };

    private static void AddPlanParameter(DbCommand command, string name, object value)
    {
        var parameter = command.CreateParameter();
        parameter.ParameterName = name;
        parameter.Value = value;
        command.Parameters.Add(parameter);
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

    private sealed class ShareGrantMaterializationInterceptor : IMaterializationInterceptor
    {
        public int Count { get; set; }

        public object InitializedInstance(MaterializationInterceptionData materializationData, object entity)
        {
            if (entity is ShareGrant)
            {
                Count++;
            }

            return entity;
        }
    }
}
