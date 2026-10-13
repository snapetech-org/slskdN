// <copyright file="HashDbControllerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.HashDb.API;

using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Moq;
using slskd.HashDb;
using slskd.HashDb.API;
using slskd.HashDb.Models;
using slskd.HashDb.Optimization;
using slskd.Search;
using Xunit;

public class HashDbControllerTests
{
    [Fact]
    public void GetMetadataProcessing_ReturnsBoundedServiceSnapshot()
    {
        var snapshot = new MetadataProcessingStatus(
            [new MetadataProcessingEvent(Guid.NewGuid(), "track.flac", "acoustid", "running", null, DateTime.UtcNow, null)],
            []);
        var hashDb = new Mock<IHashDbService>();
        hashDb.Setup(service => service.GetMetadataProcessingStatus(25)).Returns(snapshot);
        var controller = new HashDbController(
            hashDb.Object,
            Mock.Of<IDbContextFactory<SearchDbContext>>());

        var result = Assert.IsType<OkObjectResult>(controller.GetMetadataProcessing(25));

        Assert.Same(snapshot, result.Value);
    }

    [Fact]
    public async Task OptimizeIndexes_WhenOptimizationThrows_DoesNotLeakExceptionMessage()
    {
        var optimizationService = new Mock<IHashDbOptimizationService>();
        optimizationService
            .Setup(service => service.OptimizeIndexesAsync(It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("sensitive detail"));

        var controller = new HashDbController(
            Mock.Of<IHashDbService>(),
            Mock.Of<IDbContextFactory<SearchDbContext>>(),
            optimizationService.Object);

        var result = await controller.OptimizeIndexes();

        var error = Assert.IsType<ObjectResult>(result);
        Assert.Equal(500, error.StatusCode);
        Assert.DoesNotContain("sensitive detail", error.Value?.ToString() ?? string.Empty);
        Assert.Contains("Failed to optimize indexes", error.Value?.ToString() ?? string.Empty);
    }

    [Fact]
    public async Task GetSlowQueries_WhenOptimizationThrows_DoesNotLeakExceptionMessage()
    {
        var optimizationService = new Mock<IHashDbOptimizationService>();
        optimizationService
            .Setup(service => service.GetSlowQueryStatsAsync(It.IsAny<int>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("sensitive detail"));

        var controller = new HashDbController(
            Mock.Of<IHashDbService>(),
            Mock.Of<IDbContextFactory<SearchDbContext>>(),
            optimizationService.Object);

        var result = await controller.GetSlowQueries();

        var error = Assert.IsType<ObjectResult>(result);
        Assert.Equal(500, error.StatusCode);
        Assert.DoesNotContain("sensitive detail", error.Value?.ToString() ?? string.Empty);
        Assert.Contains("Failed to get slow query stats", error.Value?.ToString() ?? string.Empty);
    }

    [Fact]
    public async Task ProfileQuery_WithDisallowedQuery_DoesNotLeakValidationMessage()
    {
        var controller = new HashDbController(
            Mock.Of<IHashDbService>(),
            Mock.Of<IDbContextFactory<SearchDbContext>>(),
            Mock.Of<IHashDbOptimizationService>());

        var result = await controller.ProfileQuery(new ProfileQueryRequest
        {
            Query = "DELETE FROM files"
        });

        var badRequest = Assert.IsType<BadRequestObjectResult>(result);
        Assert.DoesNotContain("DELETE", badRequest.Value?.ToString() ?? string.Empty);
        Assert.Contains("Query is not allowed for profiling", badRequest.Value?.ToString() ?? string.Empty);
    }

    [Fact]
    public async Task LookupHash_TrimsFlacKeyBeforeLookup()
    {
        var hashDb = new Mock<IHashDbService>();
        hashDb
            .Setup(service => service.LookupHashAsync("flac-key-1", It.IsAny<CancellationToken>()))
            .ReturnsAsync(new HashDbEntry { FlacKey = "flac-key-1", ByteHash = "hash", Size = 1 });

        var controller = new HashDbController(
            hashDb.Object,
            Mock.Of<IDbContextFactory<SearchDbContext>>(),
            Mock.Of<IHashDbOptimizationService>());

        var result = await controller.LookupHash(" flac-key-1 ");

        var ok = Assert.IsType<OkObjectResult>(result);
        var entry = Assert.IsType<HashDbEntry>(ok.Value);
        Assert.Equal("flac-key-1", entry.FlacKey);
        hashDb.Verify(service => service.LookupHashAsync("flac-key-1", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task LookupHash_WhenEntryMissing_DoesNotLeakFlacKey()
    {
        var hashDb = new Mock<IHashDbService>();
        hashDb
            .Setup(service => service.LookupHashAsync("flac-key-1", It.IsAny<CancellationToken>()))
            .ReturnsAsync((HashDbEntry?)null);

        var controller = new HashDbController(
            hashDb.Object,
            Mock.Of<IDbContextFactory<SearchDbContext>>(),
            Mock.Of<IHashDbOptimizationService>());

        var result = await controller.LookupHash(" flac-key-1 ");

        var notFound = Assert.IsType<NotFoundObjectResult>(result);
        Assert.Contains("No hash found for key", notFound.Value?.ToString() ?? string.Empty);
        Assert.DoesNotContain("flac-key-1", notFound.Value?.ToString() ?? string.Empty, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void GenerateKey_TrimsFilenameBeforeGeneratingKey()
    {
        var controller = new HashDbController(
            Mock.Of<IHashDbService>(),
            Mock.Of<IDbContextFactory<SearchDbContext>>(),
            Mock.Of<IHashDbOptimizationService>());

        var result = controller.GenerateKey(" song.flac ", 123L);

        var ok = Assert.IsType<OkObjectResult>(result);
        Assert.DoesNotContain("filename", ok.Value?.ToString() ?? string.Empty, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("size =", ok.Value?.ToString() ?? string.Empty, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("flacKey", ok.Value?.ToString() ?? string.Empty);
    }

    [Fact]
    public async Task LookupHashesBySize_WhenQueried_DoesNotEchoRequestedSize()
    {
        var hashDb = new Mock<IHashDbService>();
        hashDb
            .Setup(service => service.LookupHashesBySizeAsync(123L, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new[] { new HashDbEntry { FlacKey = "flac-key-1", ByteHash = "hash", Size = 123L } });

        var controller = new HashDbController(
            hashDb.Object,
            Mock.Of<IDbContextFactory<SearchDbContext>>(),
            Mock.Of<IHashDbOptimizationService>());

        var result = await controller.LookupHashesBySize(123L);

        var ok = Assert.IsType<OkObjectResult>(result);
        Assert.DoesNotContain("size = 123", ok.Value?.ToString() ?? string.Empty, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("count = 1", ok.Value?.ToString() ?? string.Empty);
    }

    [Fact]
    public async Task GetInventoryBySize_WhenQueried_DoesNotEchoRequestedSize()
    {
        var hashDb = new Mock<IHashDbService>();
        hashDb
            .Setup(service => service.GetFlacEntriesBySizeAsync(123L, 100, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new[] { new FlacInventoryEntry { Path = "song.flac", Size = 123L } });

        var controller = new HashDbController(
            hashDb.Object,
            Mock.Of<IDbContextFactory<SearchDbContext>>(),
            Mock.Of<IHashDbOptimizationService>());

        var result = await controller.GetInventoryBySize(123L);

        var ok = Assert.IsType<OkObjectResult>(result);
        Assert.DoesNotContain("size = 123", ok.Value?.ToString() ?? string.Empty, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("count = 1", ok.Value?.ToString() ?? string.Empty);
    }

    [Fact]
    public async Task GetEntriesSinceSeq_WhenQueried_DoesNotEchoRequestedSequence()
    {
        var hashDb = new Mock<IHashDbService>();
        hashDb
            .Setup(service => service.GetEntriesSinceSeqAsync(42L, 1000, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new[] { new HashDbEntry { SeqId = 99, FlacKey = "flac-key-1", ByteHash = "hash", Size = 123L } });
        hashDb
            .Setup(service => service.GetLatestSeqIdAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(99L);

        var controller = new HashDbController(
            hashDb.Object,
            Mock.Of<IDbContextFactory<SearchDbContext>>(),
            Mock.Of<IHashDbOptimizationService>());

        var result = await controller.GetEntriesSinceSeq(42L);

        var ok = Assert.IsType<OkObjectResult>(result);
        Assert.DoesNotContain("sinceSeq", ok.Value?.ToString() ?? string.Empty, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("latestSeq = 99", ok.Value?.ToString() ?? string.Empty);
    }

    [Fact]
    public async Task StoreHash_TrimsFilenameAndByteHashBeforeDispatch()
    {
        var hashDb = new Mock<IHashDbService>();
        hashDb
            .Setup(service => service.StoreHashFromVerificationAsync("song.flac", 123L, "bytehash", null, null, null, It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var controller = new HashDbController(
            hashDb.Object,
            Mock.Of<IDbContextFactory<SearchDbContext>>(),
            Mock.Of<IHashDbOptimizationService>());

        var result = await controller.StoreHash(new StoreHashRequest
        {
            Filename = " song.flac ",
            Size = 123L,
            ByteHash = " bytehash ",
        });

        var ok = Assert.IsType<OkObjectResult>(result);
        Assert.DoesNotContain("flacKey", ok.Value?.ToString() ?? string.Empty, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("stored", ok.Value?.ToString() ?? string.Empty);
        hashDb.Verify(
            service => service.StoreHashFromVerificationAsync("song.flac", 123L, "bytehash", null, null, null, It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task BackfillFromHistory_FlattensSearchPageIntoOneIngestionCall()
    {
        var dbPath = Path.Combine(Path.GetTempPath(), $"hashdb-controller-{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<SearchDbContext>()
            .UseSqlite($"Data Source={dbPath}")
            .Options;
        var newest = DateTime.UtcNow;
        var oldest = newest.AddMinutes(-2);

        try
        {
            await using (var context = new SearchDbContext(options))
            {
                await context.Database.EnsureCreatedAsync();
                context.Searches.AddRange(
                    new Search
                    {
                        Id = Guid.NewGuid(),
                        StartedAt = newest,
                        Responses = new[]
                        {
                            new Response
                            {
                                Username = "peer-newest",
                                Files = new[] { new slskd.Search.File { Filename = "/music/newest.flac", Size = 50_000_000 } },
                            },
                        },
                    },
                    new Search
                    {
                        Id = Guid.NewGuid(),
                        StartedAt = newest.AddMinutes(-1),
                        Responses = Array.Empty<Response>(),
                    },
                    new Search
                    {
                        Id = Guid.NewGuid(),
                        StartedAt = oldest,
                        Responses = new[]
                        {
                            new Response
                            {
                                Username = "peer-oldest",
                                Files = new[] { new slskd.Search.File { Filename = "/music/oldest.flac", Size = 50_000_001 } },
                            },
                        },
                    });
                await context.SaveChangesAsync();
            }

            List<Response>? capturedResponses = null;
            var hashDb = new Mock<IHashDbService>();
            hashDb
                .Setup(service => service.GetBackfillProgressAsync(It.IsAny<CancellationToken>()))
                .ReturnsAsync((DateTimeOffset?)null);
            hashDb
                .Setup(service => service.BackfillFromSearchResponsesAsync(
                    It.IsAny<IEnumerable<Response>>(),
                    int.MaxValue,
                    It.IsAny<CancellationToken>()))
                .Callback<IEnumerable<Response>, int, CancellationToken>((responses, _, _) =>
                    capturedResponses = responses.ToList())
                .ReturnsAsync(2);
            hashDb
                .Setup(service => service.SetBackfillProgressAsync(
                    It.IsAny<DateTimeOffset>(),
                    It.IsAny<CancellationToken>()))
                .Returns(Task.CompletedTask);
            var controller = new HashDbController(
                hashDb.Object,
                new SearchDbContextFactory(options),
                Mock.Of<IHashDbOptimizationService>());

            var result = await controller.BackfillFromHistory(batchSize: 10);

            Assert.IsType<OkObjectResult>(result);
            Assert.NotNull(capturedResponses);
            Assert.Equal(new[] { "peer-newest", "peer-oldest" }, capturedResponses!.Select(response => response.Username));
            hashDb.Verify(service => service.BackfillFromSearchResponsesAsync(
                It.IsAny<IEnumerable<Response>>(),
                int.MaxValue,
                It.IsAny<CancellationToken>()), Times.Once);
            hashDb.Verify(service => service.SetBackfillProgressAsync(
                It.Is<DateTimeOffset>(value => value == new DateTimeOffset(oldest)),
                It.IsAny<CancellationToken>()), Times.Once);
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={dbPath}");
            if (System.IO.File.Exists(dbPath))
            {
                System.IO.File.Delete(dbPath);
            }
        }
    }

    private sealed class SearchDbContextFactory : IDbContextFactory<SearchDbContext>
    {
        private readonly DbContextOptions<SearchDbContext> options;

        public SearchDbContextFactory(DbContextOptions<SearchDbContext> options)
        {
            this.options = options;
        }

        public SearchDbContext CreateDbContext() => new(options);

        public ValueTask<SearchDbContext> CreateDbContextAsync(CancellationToken cancellationToken = default) =>
            ValueTask.FromResult(CreateDbContext());
    }
}
