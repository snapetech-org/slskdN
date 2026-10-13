// <copyright file="VersionedApiRoutesIntegrationTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Integration.Api;

using System;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using slskd.Messaging;
using slskd.Tests.Integration;
using Xunit;

public class VersionedApiRoutesIntegrationTests : IClassFixture<StubWebApplicationFactory>
{
    private readonly StubWebApplicationFactory _factory;

    public VersionedApiRoutesIntegrationTests(StubWebApplicationFactory factory)
    {
        _factory = factory;
    }

    [Fact]
    public async Task JobsList_VersionedRoute_ShouldSucceed()
    {
        using var client = _factory.CreateClient();

        var response = await client.GetAsync("/api/v0/jobs?limit=20&sortBy=created_at&sortOrder=desc");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task MediaCoreContentIdStats_VersionedRoute_ShouldSucceed()
    {
        using var client = _factory.CreateClient();

        var response = await client.GetAsync("/api/v0/mediacore/contentid/stats");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task MediaCoreHashAlgorithms_VersionedRoute_ShouldSucceed()
    {
        using var client = _factory.CreateClient();

        var response = await client.GetAsync("/api/v0/mediacore/perceptualhash/algorithms");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task MediaCoreConflictStrategies_VersionedRoute_ShouldSucceed()
    {
        using var client = _factory.CreateClient();

        var response = await client.GetAsync("/api/v0/mediacore/portability/strategies");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task UserNotesList_VersionedRoute_ShouldSucceed()
    {
        using var client = _factory.CreateClient();

        var response = await client.GetAsync("/api/v0/users/notes");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task SlashNamedRoomMessages_AreResolvedFromTheQueryString()
    {
        using var client = _factory.CreateClient();
        var tracker = _factory.Services.GetRequiredService<IRoomTracker>();
        var roomName = "/mu/";
        tracker.TryAdd(roomName, new Room { Name = roomName });

        var response = await client.GetAsync("/api/v0/rooms/by-name/messages?roomName=%2Fmu%2F");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task OrdinaryRoomMessages_KeepTheirExistingRoute()
    {
        using var client = _factory.CreateClient();
        var tracker = _factory.Services.GetRequiredService<IRoomTracker>();
        tracker.TryAdd("ambient", new Room { Name = "ambient" });

        var response = await client.GetAsync("/api/v0/rooms/joined/ambient/messages");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task FilesRoutes_ListDirectorySizesAndDeleteSelectedItems()
    {
        using var client = _factory.CreateClient();
        var options = _factory.Services
            .GetRequiredService<IOptionsMonitor<global::slskd.Options>>()
            .CurrentValue;
        var relativePath = $"api-files-{Guid.NewGuid():N}";
        var testRoot = Path.Combine(options.Directories.Downloads, relativePath);
        var albumPath = Path.Combine(testRoot, "Album");
        Directory.CreateDirectory(albumPath);
        await File.WriteAllBytesAsync(Path.Combine(albumPath, "track.flac"), new byte[4096]);
        await File.WriteAllBytesAsync(Path.Combine(testRoot, "single.flac"), new byte[123]);

        try
        {
            using var listingResponse = await client.GetAsync(
                "/api/v0/files/downloads/directories?includeDirectorySizes=true");
            Assert.Equal(HttpStatusCode.OK, listingResponse.StatusCode);
            using var listing = JsonDocument.Parse(await listingResponse.Content.ReadAsStringAsync());
            var listedDirectory = listing.RootElement
                .GetProperty("directories")
                .EnumerateArray()
                .Single(directory => directory.GetProperty("name").GetString() == relativePath);
            Assert.Equal(4096 + 123, listedDirectory.GetProperty("length").GetInt64());

            using var deleteRequest = new HttpRequestMessage(HttpMethod.Delete, "/api/v0/files/downloads/items")
            {
                Content = JsonContent.Create(new
                {
                    items = new[]
                    {
                        new { path = $"{relativePath}/Album", type = "directory" },
                        new { path = $"{relativePath}/single.flac", type = "file" },
                    },
                }),
            };
            using var deleteResponse = await client.SendAsync(deleteRequest);

            Assert.Equal(HttpStatusCode.OK, deleteResponse.StatusCode);
            using var deletion = JsonDocument.Parse(await deleteResponse.Content.ReadAsStringAsync());
            var results = deletion.RootElement.GetProperty("results").EnumerateArray().ToArray();
            Assert.Equal(2, results.Length);
            Assert.All(results, result => Assert.True(result.GetProperty("succeeded").GetBoolean()));
            Assert.False(Directory.Exists(albumPath));
            Assert.False(File.Exists(Path.Combine(testRoot, "single.flac")));
        }
        finally
        {
            if (Directory.Exists(testRoot))
            {
                Directory.Delete(testRoot, recursive: true);
            }
        }
    }

    [Fact]
    public async Task FilesRoutes_RejectInvalidBatchBeforeDeletingAnyItem()
    {
        using var client = _factory.CreateClient();
        var options = _factory.Services
            .GetRequiredService<IOptionsMonitor<global::slskd.Options>>()
            .CurrentValue;
        var relativePath = $"api-files-{Guid.NewGuid():N}";
        var testRoot = Path.Combine(options.Directories.Downloads, relativePath);
        var protectedDirectory = Path.Combine(testRoot, "Protect");
        var protectedFile = Path.Combine(protectedDirectory, "keep.flac");
        Directory.CreateDirectory(protectedDirectory);
        await File.WriteAllBytesAsync(protectedFile, new byte[32]);

        try
        {
            using var traversalRequest = new HttpRequestMessage(HttpMethod.Delete, "/api/v0/files/downloads/items")
            {
                Content = JsonContent.Create(new
                {
                    items = new[]
                    {
                        new { path = $"{relativePath}/Protect/keep.flac", type = "file" },
                        new { path = "../outside.flac", type = "file" },
                    },
                }),
            };
            using var traversalResponse = await client.SendAsync(traversalRequest);
            Assert.Equal(HttpStatusCode.BadRequest, traversalResponse.StatusCode);
            Assert.True(File.Exists(protectedFile));

            using var overlapRequest = new HttpRequestMessage(HttpMethod.Delete, "/api/v0/files/downloads/items")
            {
                Content = JsonContent.Create(new
                {
                    items = new[]
                    {
                        new { path = $"{relativePath}/Protect", type = "directory" },
                        new { path = $"{relativePath}/Protect/keep.flac", type = "file" },
                    },
                }),
            };
            using var overlapResponse = await client.SendAsync(overlapRequest);
            Assert.Equal(HttpStatusCode.BadRequest, overlapResponse.StatusCode);
            Assert.True(File.Exists(protectedFile));
        }
        finally
        {
            if (Directory.Exists(testRoot))
            {
                Directory.Delete(testRoot, recursive: true);
            }
        }
    }
}
