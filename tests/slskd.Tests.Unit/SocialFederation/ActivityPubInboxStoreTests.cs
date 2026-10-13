// <copyright file="ActivityPubInboxStoreTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.SocialFederation;

using Microsoft.Extensions.Logging;
using Moq;
using slskd.Mesh.Transport;
using slskd.SocialFederation;
using Xunit;

public sealed class ActivityPubInboxStoreTests : IDisposable
{
    private readonly string _dbPath = Path.Combine(Path.GetTempPath(), $"activitypub-inbox-{Guid.NewGuid():N}.db");

    public void Dispose()
    {
        slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={_dbPath}");
        File.Delete(_dbPath);
    }

    [Fact]
    public async Task StoreAsync_PrunesOldestEntriesPastCountLimit()
    {
        var store = CreateStore(maxEntries: 3, maxBytes: 1024 * 1024);
        for (var index = 0; index < 5; index++)
        {
            await store.StoreAsync("music", CreateActivity(index), $"{{\"index\":{index}}}");
        }

        var entries = await store.GetActivitiesAsync("music", 10);

        Assert.Equal(3, entries.Count);
        Assert.Equal(new[] { "activity-4", "activity-3", "activity-2" }, entries.Select(entry => entry.ActivityId));
    }

    [Fact]
    public async Task StoreAsync_PrunesOldestEntriesPastByteLimit()
    {
        var store = CreateStore(maxEntries: 100, maxBytes: 50);
        for (var index = 0; index < 3; index++)
        {
            await store.StoreAsync("music", CreateActivity(index), $"{{\"index\":{index},\"padding\":\"{new string('x', 20)}\"}}");
        }

        var entries = await store.GetActivitiesAsync("music", 10);

        Assert.Single(entries);
        Assert.Equal("activity-2", entries[0].ActivityId);
    }

    [Fact]
    public async Task StoreAsync_RejectsOversizedRawJsonBeforePersistence()
    {
        var store = CreateStore(maxEntries: 100, maxBytes: 2L * SecurityUtils.MaxRemotePayloadSize);
        var oversized = new string('x', SecurityUtils.MaxRemotePayloadSize + 1);

        await Assert.ThrowsAsync<ArgumentException>(() =>
            store.StoreAsync("music", CreateActivity(1), oversized));

        Assert.Empty(await store.GetActivitiesAsync("music", 10));
    }

    private ActivityPubInboxStore CreateStore(int maxEntries, long maxBytes)
    {
        return new ActivityPubInboxStore(
            Mock.Of<ILogger<ActivityPubInboxStore>>(),
            _dbPath,
            maxEntries,
            maxBytes,
            TimeSpan.FromDays(30));
    }

    private static ActivityPubActivity CreateActivity(int index) => new()
    {
        Id = $"activity-{index}",
        Type = "Create",
        Actor = "https://remote.example/actor",
    };
}
