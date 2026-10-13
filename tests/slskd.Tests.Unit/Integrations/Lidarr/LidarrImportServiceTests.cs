// <copyright file="LidarrImportServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Integrations.Lidarr;

using System.Net.Http;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using slskd.Events;
using slskd.Integrations.Lidarr;
using slskd.Wishlist;
using Xunit;

public class LidarrImportServiceTests
{
    [Fact]
    public async Task ImportCompletedDirectoryAsync_WithSafeCandidate_QueuesManualImport()
    {
        var client = new FakeLidarrClient
        {
            Candidates =
            [
                SafeCandidate(),
            ],
        };
        var service = CreateService(
            client,
            new Options.IntegrationOptions.LidarrOptions
            {
                Enabled = true,
                Url = "http://lidarr.test",
                ApiKey = "key",
                AutoImportCompleted = true,
                ImportMode = "copy",
                ImportReplaceExistingFiles = true,
            });

        var result = await service.ImportCompletedDirectoryAsync("/downloads/music/Artist/Album");

        Assert.Equal(1, result.CandidateCount);
        Assert.Equal(1, result.SafeCandidateCount);
        Assert.Equal(42, result.CommandId);
        Assert.Equal("Copy", result.ImportMode);
        Assert.Single(client.ImportedFiles);
        Assert.True(client.ImportedFiles[0].ReplaceExistingFiles);
        Assert.Equal("Copy", client.LastImportMode);
    }

    [Fact]
    public async Task ImportDirectoryAsync_RunsWhenAutomaticImportIsDisabledAndCanRetryImmediately()
    {
        var client = new FakeLidarrClient
        {
            Candidates =
            [
                SafeCandidate(),
            ],
        };
        var service = CreateService(
            client,
            new Options.IntegrationOptions.LidarrOptions
            {
                Enabled = true,
                Url = "http://lidarr.test",
                ApiKey = "key",
                AutoImportCompleted = false,
            });

        var first = await service.ImportDirectoryAsync("/downloads/music/Artist/Album");
        var second = await service.ImportDirectoryAsync("/downloads/music/Artist/Album");

        Assert.Equal(42, first.CommandId);
        Assert.Equal(42, second.CommandId);
        Assert.Equal(2, client.CandidateRequestCount);
        Assert.False(first.AutoImportEnabled);
    }

    [Fact]
    public async Task ImportDirectoryAsync_WhenIntegrationIsDisabledExplainsWhyItSkipped()
    {
        var client = new FakeLidarrClient();
        var service = CreateService(
            client,
            new Options.IntegrationOptions.LidarrOptions
            {
                Enabled = false,
                AutoImportCompleted = true,
            });

        var result = await service.ImportDirectoryAsync("/downloads/music/Artist/Album");

        Assert.False(result.Enabled);
        Assert.Equal("Lidarr integration is disabled", result.SkippedReason);
        Assert.Equal(0, client.CandidateRequestCount);
    }

    [Fact]
    public async Task ImportCompletedDirectoryAsync_WhenAutomaticImportIsDisabledExplainsWhyItSkipped()
    {
        var client = new FakeLidarrClient();
        var service = CreateService(
            client,
            new Options.IntegrationOptions.LidarrOptions
            {
                Enabled = true,
                AutoImportCompleted = false,
            });

        var result = await service.ImportCompletedDirectoryAsync("/downloads/music/Artist/Album");

        Assert.True(result.Enabled);
        Assert.False(result.AutoImportEnabled);
        Assert.Equal("Automatic completed-directory import is disabled", result.SkippedReason);
        Assert.Equal(0, client.CandidateRequestCount);
    }

    [Fact]
    public async Task ImportCompletedDirectoryAsync_WithAmbiguousCandidate_SkipsImport()
    {
        var client = new FakeLidarrClient
        {
            Candidates =
            [
                RejectedCandidate(),
            ],
        };
        var service = CreateService(client, EnabledImportOptions());

        var result = await service.ImportCompletedDirectoryAsync("/downloads/music/Artist/Album");

        Assert.Equal(1, result.CandidateCount);
        Assert.Equal(0, result.SafeCandidateCount);
        Assert.Equal(["01 Track.flac"], result.RejectedFilenames);
        Assert.Equal("Lidarr candidates had rejections or ambiguous matches", result.SkippedReason);
        Assert.Empty(client.ImportedFiles);
    }

    [Fact]
    public async Task ImportCompletedDirectoryAsync_MapsOnlyPathBoundaryMatches()
    {
        var client = new FakeLidarrClient();
        var service = CreateService(
            client,
            new Options.IntegrationOptions.LidarrOptions
            {
                Enabled = true,
                Url = "http://lidarr.test",
                ApiKey = "key",
                AutoImportCompleted = true,
                ImportPathFrom = "/downloads/music",
                ImportPathTo = "/lidarr/inbox",
            });

        await service.ImportCompletedDirectoryAsync("/downloads/music2/Artist/Album");

        Assert.Equal(Path.GetFullPath("/downloads/music2/Artist/Album"), client.LastCandidateFolder);
    }

    [Fact]
    public async Task ImportCompletedDirectoryAsync_MapsChildPath()
    {
        var client = new FakeLidarrClient();
        var service = CreateService(
            client,
            new Options.IntegrationOptions.LidarrOptions
            {
                Enabled = true,
                Url = "http://lidarr.test",
                ApiKey = "key",
                AutoImportCompleted = true,
                ImportPathFrom = "/downloads/music",
                ImportPathTo = "/lidarr/inbox",
            });

        await service.ImportCompletedDirectoryAsync("/downloads/music/Artist/Album");

        Assert.Equal("/lidarr/inbox/Artist/Album", client.LastCandidateFolder);
    }

    [Fact]
    public async Task ImportCompletedDirectoryAsync_MapsToWindowsPathWhenRunningOnUnix()
    {
        var client = new FakeLidarrClient();
        var service = CreateService(
            client,
            new Options.IntegrationOptions.LidarrOptions
            {
                Enabled = true,
                Url = "http://lidarr.test",
                ApiKey = "key",
                AutoImportCompleted = true,
                ImportPathFrom = "/music/downloaded",
                ImportPathTo = @"D:\downloaded",
            });

        await service.ImportCompletedDirectoryAsync("/music/downloaded/2 Chainz - T.R.U. REALigion (Anniversary Edition)");

        Assert.Equal(
            @"D:\downloaded\2 Chainz - T.R.U. REALigion (Anniversary Edition)",
            client.LastCandidateFolder);
    }

    [Fact]
    public async Task ImportCompletedDirectoryAsync_DebouncesConcurrentDirectoryAttempts()
    {
        var client = new FakeLidarrClient
        {
            Candidates = [SafeCandidate()],
            CandidateDelay = TimeSpan.FromMilliseconds(50),
        };
        var service = CreateService(client, EnabledImportOptions());

        var first = service.ImportCompletedDirectoryAsync("/downloads/music/Artist/Album");
        var second = service.ImportCompletedDirectoryAsync("/downloads/music/Artist/Album");

        var results = await Task.WhenAll(first, second);

        Assert.Equal(1, client.CandidateRequestCount);
        Assert.Single(results, result => result.CommandId == 42);
        Assert.Single(results, result => result.SkippedReason == "Recently processed");
    }

    [Fact]
    public async Task ImportCompletedDirectoryAsync_DebouncesFailedDirectoryAttempt()
    {
        var client = new FakeLidarrClient
        {
            CandidateException = new TimeoutException("lidarr slow"),
        };
        var service = CreateService(client, EnabledImportOptions());

        await Assert.ThrowsAsync<TimeoutException>(() => service.ImportCompletedDirectoryAsync("/downloads/music/Artist/Album"));
        var result = await service.ImportCompletedDirectoryAsync("/downloads/music/Artist/Album");

        Assert.Equal(1, client.CandidateRequestCount);
        Assert.Equal("Recently processed", result.SkippedReason);
    }

    [Fact]
    public async Task ImportCompletedDirectoryAsync_SkipsAlreadyOwnedAlbumWithoutCallingManualImport()
    {
        // Mirrors a real Lidarr response: the release folder identifies an artist/album that
        // already has every track file on disk, which some Lidarr versions crash on when scanned
        // via manual-import (see ChromaprintContext-adjacent bug notes). The pre-check should
        // catch this before ever calling GetManualImportCandidatesAsync.
        var client = new FakeLidarrClient
        {
            ParseResult = new LidarrParseResult
            {
                Artist = new LidarrArtistResource { Id = 229, ArtistName = "Dua Lipa" },
                ParsedAlbumInfo = new LidarrParsedAlbumInfo { AlbumTitle = "Dua Lipa" },
            },
            ArtistAlbums =
            [
                new LidarrArtistAlbumResource
                {
                    Id = 2675,
                    Title = "Dua Lipa",
                    Monitored = true,
                    Statistics = new LidarrAlbumStatistics { TrackFileCount = 17, TrackCount = 17, TotalTrackCount = 17 },
                },
            ],
        };
        var service = CreateService(client, EnabledImportOptions());

        var result = await service.ImportCompletedDirectoryAsync("/downloads/music/Dua Lipa - Dua Lipa (Deluxe) (2017) [WEB-MP3]");

        Assert.Equal(0, client.CandidateRequestCount);
        Assert.Equal("Already fully in Lidarr library (Dua Lipa - Dua Lipa)", result.SkippedReason);
    }

    [Fact]
    public async Task ImportCompletedDirectoryAsync_DoesNotSkipAlreadyOwnedAlbumWhenReplaceExistingFilesIsEnabled()
    {
        var client = new FakeLidarrClient
        {
            Candidates = [SafeCandidate()],
            ParseResult = new LidarrParseResult
            {
                Artist = new LidarrArtistResource { Id = 229, ArtistName = "Dua Lipa" },
                ParsedAlbumInfo = new LidarrParsedAlbumInfo { AlbumTitle = "Dua Lipa" },
            },
            ArtistAlbums =
            [
                new LidarrArtistAlbumResource
                {
                    Id = 2675,
                    Title = "Dua Lipa",
                    Monitored = true,
                    Statistics = new LidarrAlbumStatistics { TrackFileCount = 17, TrackCount = 17, TotalTrackCount = 17 },
                },
            ],
        };
        var options = new Options.IntegrationOptions.LidarrOptions
        {
            Enabled = true,
            Url = "http://lidarr.test",
            ApiKey = "key",
            AutoImportCompleted = true,
            ImportReplaceExistingFiles = true,
        };
        var service = CreateService(client, options);

        var result = await service.ImportCompletedDirectoryAsync("/downloads/music/Dua Lipa - Dua Lipa (Deluxe) (2017) [WEB-MP3]");

        Assert.Equal(1, client.CandidateRequestCount);
        Assert.Equal(42, result.CommandId);
    }

    [Fact]
    public async Task ImportCompletedDirectoryAsync_RetriesTransientLidarrFailureAndSucceeds()
    {
        var client = new FakeLidarrClient
        {
            Candidates = [SafeCandidate()],
            CandidateException = new HttpRequestException("Response status code does not indicate success: 503 (Service Unavailable)."),
            FailAttempts = 1,
        };
        var options = new Options.IntegrationOptions.LidarrOptions
        {
            Enabled = true,
            Url = "http://lidarr.test",
            ApiKey = "key",
            AutoImportCompleted = true,
            ImportRetryMaxAttempts = 2,
            ImportRetryDelaySeconds = 1,
        };
        var service = CreateService(client, options);

        var result = await service.ImportCompletedDirectoryAsync("/downloads/music/Artist/Album");

        Assert.Equal(2, client.CandidateRequestCount);
        Assert.Equal(42, result.CommandId);
    }

    [Fact]
    public async Task ImportCompletedDirectoryAsync_ExhaustsRetriesThenThrows()
    {
        var client = new FakeLidarrClient
        {
            CandidateException = new HttpRequestException("Response status code does not indicate success: 503 (Service Unavailable)."),
        };
        var options = new Options.IntegrationOptions.LidarrOptions
        {
            Enabled = true,
            Url = "http://lidarr.test",
            ApiKey = "key",
            AutoImportCompleted = true,
            ImportRetryMaxAttempts = 2,
            ImportRetryDelaySeconds = 0,
        };
        var service = CreateService(client, options);

        await Assert.ThrowsAsync<HttpRequestException>(() => service.ImportCompletedDirectoryAsync("/downloads/music/Artist/Album"));

        Assert.Equal(3, client.CandidateRequestCount);
    }

    [Fact]
    public async Task ImportDirectoryAsync_PersistsHistoryAndRetriesAsANewAttempt()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"lidarr-history-{Guid.NewGuid():N}.db");
        try
        {
            var options = new DbContextOptionsBuilder<WishlistDbContext>()
                .UseSqlite($"Data Source={databasePath}")
                .Options;
            var contextFactory = new TestWishlistDbContextFactory(options);
            await using (var context = await contextFactory.CreateDbContextAsync())
            {
                await context.Database.EnsureCreatedAsync();
            }

            var client = new FakeLidarrClient
            {
                Candidates = [RejectedCandidate()],
            };
            var service = CreateService(client, EnabledImportOptions(), contextFactory);

            var firstResult = await service.ImportDirectoryAsync("/downloads/music/Artist/Album");
            var firstHistory = Assert.Single(await service.GetHistoryAsync());

            Assert.Equal(firstHistory.Id, firstResult.HistoryId);
            Assert.Equal(LidarrImportStatus.Skipped, firstHistory.Status);
            Assert.Equal("Lidarr candidates had rejections or ambiguous matches", firstHistory.SkippedReason);

            client.Candidates = [SafeCandidate()];
            var retryResult = await service.RetryImportAsync(firstHistory.Id);
            Assert.NotNull(retryResult);
            Assert.Equal(42, retryResult.CommandId);

            LidarrImportHistoryRecord? retryHistory = null;
            for (var attempt = 0; attempt < 20; attempt++)
            {
                retryHistory = (await service.GetHistoryAsync()).SingleOrDefault(history => history.Id != firstHistory.Id);
                if (retryHistory?.Status == LidarrImportStatus.Successful)
                {
                    break;
                }

                await Task.Delay(10);
            }

            Assert.NotNull(retryHistory);
            Assert.Equal(LidarrImportStatus.Successful, retryHistory!.Status);
            Assert.Equal(firstHistory.Id, retryHistory.RetryOfId);
            Assert.Equal("/downloads/music/Artist/Album", retryHistory.SourceDirectory);
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={databasePath}");
            File.Delete(databasePath);
            File.Delete(databasePath + "-shm");
            File.Delete(databasePath + "-wal");
        }
    }

    [Fact]
    public async Task ImportCompletedDirectoryAsync_SerializesDifferentDirectoryImports()
    {
        var client = new FakeLidarrClient
        {
            Candidates = [SafeCandidate()],
            CandidateDelay = TimeSpan.FromMilliseconds(50),
        };
        var service = CreateService(client, EnabledImportOptions());

        await Task.WhenAll(
            service.ImportCompletedDirectoryAsync("/downloads/music/Artist/Album One"),
            service.ImportCompletedDirectoryAsync("/downloads/music/Artist/Album Two"));

        Assert.Equal(2, client.CandidateRequestCount);
        Assert.Equal(1, client.MaxConcurrentCandidateRequests);
    }

    [Fact]
    public void IsExpectedExternalHttpFailure_ReturnsTrue_ForHttpRequestException()
    {
        var ex = new HttpRequestException("Response status code does not indicate success: 500 (Internal Server Error).");

        Assert.True(LidarrImportService.IsExpectedExternalHttpFailure(ex));
    }

    [Fact]
    public void IsExpectedExternalHttpFailure_ReturnsTrue_ForWrappedHttpRequestException()
    {
        var ex = new InvalidOperationException(
            "wrapped",
            new HttpRequestException("Connection refused"));

        Assert.True(LidarrImportService.IsExpectedExternalHttpFailure(ex));
    }

    private static LidarrImportService CreateService(
        FakeLidarrClient client,
        Options.IntegrationOptions.LidarrOptions lidarrOptions,
        IDbContextFactory<WishlistDbContext>? historyContextFactory = null)
        => new(
            client,
            new EventBus(null!),
            new TestOptionsMonitor<Options>(new Options
            {
                Integration = new Options.IntegrationOptions
                {
                    Lidarr = lidarrOptions,
                },
            }),
            historyContextFactory: historyContextFactory);

    private static Options.IntegrationOptions.LidarrOptions EnabledImportOptions()
        => new()
        {
            Enabled = true,
            Url = "http://lidarr.test",
            ApiKey = "key",
            AutoImportCompleted = true,
        };

    private static LidarrManualImportResource SafeCandidate()
        => new()
        {
            Id = 123,
            Path = "/downloads/music/Artist/Album/01 Track.flac",
            Artist = new LidarrArtistResource { Id = 1, ArtistName = "Artist" },
            Album = new LidarrAlbumResource { Id = 2, Title = "Album" },
            AlbumReleaseId = 3,
            Tracks = [new LidarrTrackResource { Id = 4, Title = "Track" }],
            Quality = JsonSerializer.Deserialize<JsonElement>("{}"),
        };

    private static LidarrManualImportResource RejectedCandidate()
        => new()
        {
            Id = 123,
            Path = "/downloads/music/Artist/Album/01 Track.flac",
            Artist = new LidarrArtistResource { Id = 1, ArtistName = "Artist" },
            Album = new LidarrAlbumResource { Id = 2, Title = "Album" },
            AlbumReleaseId = 3,
            Tracks = [new LidarrTrackResource { Id = 4, Title = "Track" }],
            Quality = JsonSerializer.Deserialize<JsonElement>("{}"),
            Rejections = [JsonSerializer.Deserialize<JsonElement>("{\"reason\":\"ambiguous\"}")],
        };

    private sealed class FakeLidarrClient : ILidarrClient
    {
        public IReadOnlyList<LidarrManualImportResource> Candidates { get; set; } = [];

        public TimeSpan CandidateDelay { get; init; } = TimeSpan.Zero;

        public Exception? CandidateException { get; init; }

        /// <summary>
        ///     The number of calls to <see cref="GetManualImportCandidatesAsync"/> that should throw
        ///     <see cref="CandidateException"/> before calls start succeeding. Defaults to always-throw
        ///     (for tests that never expect success) when <see cref="CandidateException"/> is set.
        /// </summary>
        public int FailAttempts { get; init; } = int.MaxValue;

        public int CandidateRequestCount { get; private set; }

        public int MaxConcurrentCandidateRequests { get; private set; }

        private int _activeCandidateRequests;

        public string LastCandidateFolder { get; private set; } = string.Empty;

        public string LastImportMode { get; private set; } = string.Empty;

        public List<LidarrManualImportResource> ImportedFiles { get; } = [];

        public LidarrParseResult? ParseResult { get; init; }

        public IReadOnlyList<LidarrArtistAlbumResource> ArtistAlbums { get; init; } = [];

        public Task<LidarrSystemStatus> GetSystemStatusAsync(CancellationToken cancellationToken = default)
            => Task.FromResult(new LidarrSystemStatus());

        public Task<LidarrParseResult?> ParseAsync(string title, CancellationToken cancellationToken = default)
            => Task.FromResult(ParseResult);

        public Task<IReadOnlyList<LidarrArtistAlbumResource>> GetAlbumsByArtistAsync(int artistId, CancellationToken cancellationToken = default)
            => Task.FromResult(ArtistAlbums);

        public Task<IReadOnlyList<LidarrQualityProfile>> GetQualityProfilesAsync(CancellationToken cancellationToken = default)
            => Task.FromResult<IReadOnlyList<LidarrQualityProfile>>([]);

        public Task<IReadOnlyList<LidarrTrackResource>> GetAlbumTracksAsync(int albumId, CancellationToken cancellationToken = default)
            => Task.FromResult<IReadOnlyList<LidarrTrackResource>>([]);

        public Task<LidarrAlbumDetail?> GetAlbumAsync(int albumId, CancellationToken cancellationToken = default)
            => Task.FromResult<LidarrAlbumDetail?>(null);

        public Task<IReadOnlyList<LidarrWantedAlbum>> GetWantedMissingAsync(int pageSize, CancellationToken cancellationToken = default)
            => Task.FromResult<IReadOnlyList<LidarrWantedAlbum>>([]);

        public Task<(IReadOnlyList<LidarrWantedAlbum> Records, int TotalRecords)> GetWantedMissingPageAsync(
            int page,
            int pageSize,
            CancellationToken cancellationToken = default)
            => Task.FromResult<(IReadOnlyList<LidarrWantedAlbum> Records, int TotalRecords)>(([], 0));

        public Task<IReadOnlyList<LidarrManualImportResource>> GetManualImportCandidatesAsync(
            string folder,
            bool filterExistingFiles,
            bool replaceExistingFiles,
            CancellationToken cancellationToken = default)
        {
            var activeRequests = Interlocked.Increment(ref _activeCandidateRequests);
            try
            {
                CandidateRequestCount++;
                MaxConcurrentCandidateRequests = Math.Max(MaxConcurrentCandidateRequests, activeRequests);
                LastCandidateFolder = folder;
                if (CandidateDelay > TimeSpan.Zero)
                {
                    return GetManualImportCandidatesWithDelayAsync(cancellationToken);
                }

                if (CandidateException is not null && CandidateRequestCount <= FailAttempts)
                {
                    return Task.FromException<IReadOnlyList<LidarrManualImportResource>>(CandidateException);
                }

                return Task.FromResult(Candidates);
            }
            finally
            {
                if (CandidateDelay == TimeSpan.Zero)
                {
                    Interlocked.Decrement(ref _activeCandidateRequests);
                }
            }
        }

        private async Task<IReadOnlyList<LidarrManualImportResource>> GetManualImportCandidatesWithDelayAsync(CancellationToken cancellationToken)
        {
            try
            {
                await Task.Delay(CandidateDelay, cancellationToken);
                if (CandidateException is not null && CandidateRequestCount <= FailAttempts)
                {
                    throw CandidateException;
                }

                return Candidates;
            }
            finally
            {
                Interlocked.Decrement(ref _activeCandidateRequests);
            }
        }

        public Task<LidarrCommandResponse> StartManualImportAsync(
            IReadOnlyList<LidarrManualImportResource> files,
            string importMode,
            bool replaceExistingFiles,
            CancellationToken cancellationToken = default)
        {
            LastImportMode = importMode;
            ImportedFiles.AddRange(files);
            return Task.FromResult(new LidarrCommandResponse { Id = 42, Name = "ManualImport", Status = "queued" });
        }

        public Task<LidarrCommandResponse> StartCommandAsync(string name, object payload, CancellationToken cancellationToken = default)
            => Task.FromResult(new LidarrCommandResponse { Id = 42, Name = name, Status = "queued" });

        public Task<LidarrCommandResponse> GetCommandAsync(int commandId, CancellationToken cancellationToken = default)
            => Task.FromResult(new LidarrCommandResponse { Id = commandId, Status = "completed" });
    }

    private sealed class TestWishlistDbContextFactory(DbContextOptions<WishlistDbContext> options)
        : IDbContextFactory<WishlistDbContext>
    {
        public WishlistDbContext CreateDbContext() => new(options);

        public ValueTask<WishlistDbContext> CreateDbContextAsync(CancellationToken cancellationToken = default)
            => ValueTask.FromResult(CreateDbContext());
    }
}
