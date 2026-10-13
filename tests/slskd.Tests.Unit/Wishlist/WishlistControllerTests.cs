// <copyright file="WishlistControllerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Wishlist;

using System.Linq.Expressions;
using Microsoft.Data.Sqlite;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Moq;
using slskd.Migrations;
using slskd.Search;
using slskd.Tests.Unit;
using slskd.Transfers.Downloads;
using slskd.Transfers.Ranking;
using slskd.Users.Notes;
using slskd.Wishlist;
using slskd.Wishlist.API;
using Soulseek;
using SlskdSearch = slskd.Search.Search;
using Xunit;

public class WishlistControllerTests : IDisposable
{
    private readonly SqliteConnection _connection;
    private readonly WishlistDbContextFactory _contextFactory;

    public WishlistControllerTests()
    {
        _connection = new SqliteConnection("Data Source=:memory:");
        _connection.Open();
        _contextFactory = new WishlistDbContextFactory(_connection);

        using var context = _contextFactory.CreateDbContext();
        context.Database.EnsureCreated();
    }

    public void Dispose()
    {
        _connection.Dispose();
    }

    [Fact]
    public async Task Create_TrimsSearchTextAndFilterBeforePersisting()
    {
        var service = new Mock<IWishlistService>();
        service
            .Setup(x => x.CreateAsync(It.IsAny<WishlistItem>()))
            .ReturnsAsync((WishlistItem item) =>
            {
                item.Id = Guid.NewGuid();
                return item;
            });

        var controller = new WishlistController(service.Object);

        var result = await controller.Create(new CreateWishlistRequest
        {
            SearchText = " artist - title ",
            Filter = " flac ",
            Enabled = true,
            AutoDownload = false,
            MaxResults = 25,
        });

        Assert.IsType<CreatedAtActionResult>(result);
        service.Verify(
            x => x.CreateAsync(It.Is<WishlistItem>(item =>
                item.SearchText == "artist - title" &&
                item.Filter == "flac" &&
                item.MaxResults == 25)),
            Times.Once);
    }

    [Fact]
    public async Task Update_WithBlankSearchTextAfterTrim_ReturnsBadRequest()
    {
        var controller = new WishlistController(Mock.Of<IWishlistService>());

        var result = await controller.Update(Guid.NewGuid(), new UpdateWishlistRequest
        {
            SearchText = "   ",
            Filter = " flac ",
        });

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Equal("SearchText is required", bad.Value);
    }

    [Fact]
    public async Task Create_WithNonPositiveMaxResults_ReturnsBadRequest()
    {
        var controller = new WishlistController(Mock.Of<IWishlistService>());

        var result = await controller.Create(new CreateWishlistRequest
        {
            SearchText = "artist - title",
            MaxResults = 0,
        });

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Equal("MaxResults must be greater than 0", bad.Value);
    }

    [Fact]
    public async Task Update_WithNonPositiveMaxResults_ReturnsBadRequest()
    {
        var controller = new WishlistController(Mock.Of<IWishlistService>());

        var result = await controller.Update(Guid.NewGuid(), new UpdateWishlistRequest
        {
            SearchText = "artist - title",
            MaxResults = -1,
        });

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Equal("MaxResults must be greater than 0", bad.Value);
    }

    [Fact]
    public async Task UpdateFilters_TrimsFilterAndReturnsUpdatedCount()
    {
        var service = new Mock<IWishlistService>();
        var ids = new[] { Guid.NewGuid(), Guid.NewGuid() };
        service
            .Setup(x => x.UpdateFiltersAsync(
                It.Is<IEnumerable<Guid>>(values => values.SequenceEqual(ids)),
                "mp3 minbr:320",
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(2);
        var controller = new WishlistController(service.Object);

        var result = await controller.UpdateFilters(
            new BulkWishlistFilterRequest
            {
                Ids = ids.ToList(),
                Filter = " mp3 minbr:320 ",
            });

        var ok = Assert.IsType<OkObjectResult>(result);
        var body = Assert.IsType<BulkWishlistFilterResult>(ok.Value);
        Assert.Equal(2, body.UpdatedCount);
        service.Verify(
            x => x.UpdateFiltersAsync(
                It.Is<IEnumerable<Guid>>(values => values.SequenceEqual(ids)),
                "mp3 minbr:320",
                It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task UpdateFilters_WithNoIds_ReturnsBadRequest()
    {
        var controller = new WishlistController(Mock.Of<IWishlistService>());

        var result = await controller.UpdateFilters(new BulkWishlistFilterRequest());

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Equal("At least one wishlist item ID is required", bad.Value);
    }

    [Fact]
    public async Task ImportCsv_TrimsFilterAndPassesOptions()
    {
        var service = new Mock<IWishlistService>();
        service
            .Setup(x => x.ImportCsvAsync(
                It.IsAny<string>(),
                It.IsAny<WishlistCsvImportOptions>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(new WishlistCsvImportResult
            {
                TotalRows = 1,
                CreatedCount = 1,
            });
        var controller = new WishlistController(service.Object);

        var result = await controller.ImportCsv(new ImportWishlistCsvRequest
        {
            CsvText = "Track name,Artist name\nSong,Artist",
            Filter = " flac ",
            Enabled = false,
            AutoDownload = true,
            IncludeAlbum = true,
            MaxResults = 25,
        });

        Assert.IsType<OkObjectResult>(result);
        service.Verify(
            x => x.ImportCsvAsync(
                "Track name,Artist name\nSong,Artist",
                It.Is<WishlistCsvImportOptions>(options =>
                    options.Filter == "flac" &&
                    options.Enabled == false &&
                    options.AutoDownload &&
                    options.IncludeAlbum &&
                    options.MaxResults == 25),
                It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task ImportCsv_WithBlankCsv_ReturnsBadRequest()
    {
        var controller = new WishlistController(Mock.Of<IWishlistService>());

        var result = await controller.ImportCsv(new ImportWishlistCsvRequest
        {
            CsvText = "   ",
        });

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Equal("CsvText is required", bad.Value);
    }

    [Fact]
    public void ParseCsvTracks_HandlesTuneMyMusicHeadersAndEscapedFields()
    {
        const string csv = "Track name,Artist name,Album name\n\"Song, Part 1\",\"Artist \"\"Name\"\"\",Album";

        var tracks = WishlistService.ParseCsvTracks(csv, includeAlbum: true);

        var track = Assert.Single(tracks);
        Assert.Equal("Artist \"Name\" Song, Part 1 Album", track.SearchText);
        Assert.Equal(2, track.RowNumber);
    }

    [Fact]
    public void ParseCsvTracks_SkipsHeaderlessRowsWithoutArtistAndTitle()
    {
        const string csv = "Song Only\nTitle,Artist";

        var tracks = WishlistService.ParseCsvTracks(csv, includeAlbum: false);

        Assert.Equal(2, tracks.Count);
        Assert.Equal(string.Empty, tracks[0].SearchText);
        Assert.Equal("Artist Title", tracks[1].SearchText);
    }

    [Fact]
    public void CreateSearchFileFilter_AllowsFilenameIncludesAndExcludes()
    {
        var filter = WishlistService.CreateSearchFileFilter("flac -chiefs -booka");

        Assert.True(filter(@"Music\The Adicts\2014 Album\01 Song.flac"));
        Assert.False(filter(@"Music\The Adicts\2014 Album\02 Song.mp3"));
        Assert.False(filter(@"Music\Chiefs\2014 Album\01 Song.flac"));
        Assert.False(filter(@"Music\Booka Shade\2014 Album\01 Song.flac"));
    }

    [Fact]
    public void CreateSearchFileFilter_WithOnlyExclusionsKeepsUnmatchedFiles()
    {
        var filter = WishlistService.CreateSearchFileFilter("-chiefs -booka");

        Assert.True(filter(@"Music\The Adicts\2014 Album\01 Song.mp3"));
        Assert.False(filter(@"Music\Chiefs\2014 Album\01 Song.flac"));
    }

    [Fact]
    public void CreateFileFilter_EnforcesMinimumBitrateFromMetadata()
    {
        var filter = WishlistService.CreateFileFilter("mp3 minbr:320");

        Assert.False(filter(new Soulseek.File(
            1,
            "Music\\Album\\01 Song.mp3",
            100,
            ".mp3",
            [new FileAttribute(FileAttributeType.BitRate, 128)])));
        Assert.True(filter(new Soulseek.File(
            2,
            "Music\\Album\\02 Song.mp3",
            100,
            ".mp3",
            [new FileAttribute(FileAttributeType.BitRate, 320)])));
        Assert.False(filter(new Soulseek.File(3, "Music\\Album\\03 Song.flac", 100, ".flac")));
    }

    [Fact]
    public void CreateSearchResultFileFilter_EnforcesMinimumBitrateFromStoredMetadata()
    {
        var filter = WishlistService.CreateSearchResultFileFilter("mp3 minbitrate:320");

        Assert.False(filter(new slskd.Search.File
        {
            Filename = "Music\\Album\\01 Song.mp3",
            BitRate = 128,
        }));
        Assert.True(filter(new slskd.Search.File
        {
            Filename = "Music\\Album\\02 Song.mp3",
            BitRate = 320,
        }));
        Assert.False(filter(new slskd.Search.File
        {
            Filename = "Music\\Album\\03 Song.flac",
            BitRate = 1000,
        }));
    }

    [Fact]
    public void CreateFileFilter_PreservesFormatAndBitrateAlternatives()
    {
        var filter = WishlistService.CreateFileFilter("mp3 minbr:320 OR aac minbr:256");

        Assert.True(filter(CreateSoulseekFile("01 Song.mp3", 320)));
        Assert.False(filter(CreateSoulseekFile("02 Song.mp3", 256)));
        Assert.True(filter(CreateSoulseekFile("03 Song.aac", 256)));
        Assert.False(filter(CreateSoulseekFile("04 Song.aac", 192)));
        Assert.False(filter(CreateSoulseekFile("05 Song.flac", 1_000)));
    }

    [Fact]
    public void CreateSearchResultFileFilter_AppliesGlobalExclusionsToEveryAlternative()
    {
        var filter = WishlistService.CreateSearchResultFileFilter("mp3 minbr:320 OR aac minbr:256 -demo");

        Assert.True(filter(new slskd.Search.File { Filename = "01 Song.mp3", BitRate = 320 }));
        Assert.True(filter(new slskd.Search.File { Filename = "02 Song.aac", BitRate = 256 }));
        Assert.False(filter(new slskd.Search.File { Filename = "03 Demo.aac", BitRate = 256 }));
        Assert.False(filter(new slskd.Search.File { Filename = "04 Song.aac", BitRate = 192 }));
    }

    [Fact]
    public void CreateSearchFileFilter_DoesNotAcceptUnknownBitrateForMetadataDirective()
    {
        var filter = WishlistService.CreateSearchFileFilter("mp3 minbr:320");

        Assert.False(filter("Music\\Album\\01 Song.mp3"));
    }

    [Theory]
    [InlineData("flac", "Song.flac", null, true)]
    [InlineData("alac", "Song.alac", null, true)]
    [InlineData("wav", "Song.wav", null, true)]
    [InlineData("ape", "Song.ape", null, true)]
    [InlineData("aiff", "Song.aiff", null, true)]
    [InlineData("aif", "Song.aif", null, true)]
    [InlineData("ogg minbr:192", "Song.ogg", 192, true)]
    [InlineData("oga minbr:192", "Song.oga", 191, false)]
    [InlineData("opus minbr:128", "Song.opus", 128, true)]
    [InlineData("m4a minbr:256", "Song.m4a", 256, true)]
    [InlineData("aac minbr:256", "Song.m4a", 256, false)]
    [InlineData("mp3 minbr:320", "Song.mp3", null, false)]
    public void CreateSearchResultFileFilter_HandlesSupportedFormatAndMetadataCombinations(
        string filterText,
        string filename,
        int? bitrate,
        bool expected)
    {
        var filter = WishlistService.CreateSearchResultFileFilter(filterText);

        Assert.Equal(expected, filter(new slskd.Search.File
        {
            Filename = filename,
            BitRate = bitrate,
        }));
    }

    [Fact]
    public async Task Update_PersistsMaxDownloads()
    {
        var itemId = Guid.NewGuid();
        await using (var context = _contextFactory.CreateDbContext())
        {
            context.WishlistItems.Add(new WishlistItem
            {
                Id = itemId,
                SearchText = "artist title",
                MaxResults = 25,
                MaxDownloads = null,
            });
            await context.SaveChangesAsync();
        }

        var service = new WishlistService(
            _contextFactory,
            Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            Mock.Of<ISearchService>(),
            Mock.Of<ISoulseekClient>(),
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            Mock.Of<ISourceRankingService>(),
            Mock.Of<IDownloadService>());

        await service.UpdateAsync(new WishlistItem
        {
            Id = itemId,
            SearchText = "artist title",
            MaxResults = 25,
            MaxDownloads = 5,
        });

        await using var verifyContext = _contextFactory.CreateDbContext();
        var item = await verifyContext.WishlistItems.FindAsync(itemId);
        Assert.NotNull(item);
        Assert.Equal(5, item.MaxDownloads);
    }

    private static Soulseek.File CreateSoulseekFile(string filename, int bitrate)
        => new(
            1,
            $"Music\\Album\\{filename}",
            100,
            Path.GetExtension(filename),
            [new FileAttribute(FileAttributeType.BitRate, bitrate)]);

    [Fact]
    public void SearchSourceMigration_BackfillsExistingNullSources()
    {
        var dbPath = Path.Combine(Path.GetTempPath(), $"slskdn-search-migration-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={dbPath}";

        try
        {
            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                using var create = new SqliteCommand(
                    """
                    CREATE TABLE Searches (
                        Id TEXT NOT NULL PRIMARY KEY,
                        SearchText TEXT NOT NULL,
                        Source TEXT NULL,
                        StartedAt TEXT NOT NULL,
                        State INTEGER NOT NULL,
                        Token INTEGER NOT NULL,
                        FileCount INTEGER NOT NULL,
                        LockedFileCount INTEGER NOT NULL,
                        ResponseCount INTEGER NOT NULL,
                        ResponsesJson TEXT NULL,
                        EndedAt TEXT NULL
                    );
                    INSERT INTO Searches (
                        Id, SearchText, Source, StartedAt, State, Token, FileCount, LockedFileCount, ResponseCount, ResponsesJson, EndedAt
                    ) VALUES (
                        '11111111-1111-1111-1111-111111111111', 'old search', NULL, '2026-05-19T00:00:00Z', 0, 1, 0, 0, 0, '[]', NULL
                    );
                    """,
                    connection);
                create.ExecuteNonQuery();
            }

            var migration = new Z05182026_SearchSourceAndWishlistItemIdMigration(new ConnectionStringDictionary(
                new Dictionary<Database, ConnectionString>
                {
                    [Database.Search] = connectionString,
                }));

            Assert.True(migration.NeedsToBeApplied());
            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());

            using var verifyConnection = new SqliteConnection(connectionString);
            verifyConnection.Open();
            using var verify = new SqliteCommand("SELECT Source FROM Searches", verifyConnection);
            Assert.Equal("manual", verify.ExecuteScalar());
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool(connectionString);
            if (System.IO.File.Exists(dbPath))
            {
                System.IO.File.Delete(dbPath);
            }
        }
    }

    [Fact]
    public async Task RunSearch_UsesNetworkScopeAndWishlistSafetySource()
    {
        var itemId = Guid.NewGuid();
        await using (var context = _contextFactory.CreateDbContext())
        {
            context.WishlistItems.Add(new WishlistItem
            {
                Id = itemId,
                SearchText = "artist title",
                MaxResults = 25,
            });
            await context.SaveChangesAsync();
        }

        SearchScope? capturedScope = null;
        string? capturedSafetySource = null;
        SearchOptions? capturedOptions = null;
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.IsAny<SearchOptions?>(),
                It.IsAny<List<string>?>(),
                It.IsAny<string>(),
                It.IsAny<Guid?>()))
            .Callback<Guid, SearchQuery, SearchScope, SearchOptions?, List<string>?, string, Guid?>((id, query, scope, options, providers, safetySource, wishlistItemId) =>
            {
                capturedScope = scope;
                capturedSafetySource = safetySource;
                capturedOptions = options;
            })
            .ReturnsAsync((Guid id, SearchQuery query, SearchScope scope, SearchOptions? options, List<string>? providers, string safetySource, Guid? wishlistItemId) =>
                new SlskdSearch
                {
                    Id = id,
                    SearchText = query.SearchText,
                    State = SearchStates.Requested,
                });
        searchService
            .Setup(service => service.FindAsync(It.IsAny<Expression<Func<SlskdSearch, bool>>>(), false))
            .ReturnsAsync(new SlskdSearch { State = SearchStates.Completed });
        searchService
            .Setup(service => service.FindAsync(It.IsAny<Expression<Func<SlskdSearch, bool>>>(), true))
            .ReturnsAsync((Expression<Func<SlskdSearch, bool>> expression, bool includeResponses) =>
                new SlskdSearch
                {
                    Id = itemId,
                    SearchText = "artist title",
                    State = SearchStates.Completed,
                    ResponseCount = 3,
                });

        var service = new WishlistService(
            _contextFactory,
            Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            searchService.Object,
            Mock.Of<ISoulseekClient>(),
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            Mock.Of<ISourceRankingService>(),
            Mock.Of<IDownloadService>());

        var result = await service.RunSearchAsync(itemId);

        Assert.Equal(SearchScopeType.Network, capturedScope?.Type);
        Assert.Equal("wishlist", capturedSafetySource);
        Assert.Equal(25, capturedOptions?.ResponseLimit);
        Assert.NotNull(capturedOptions?.FileFilter);
        Assert.True(capturedOptions!.FileFilter!(new Soulseek.File(1, "artist title.flac", 1, "flac")));
        Assert.False(capturedOptions.FileFilter(new Soulseek.File(1, "artist.flac", 1, "flac")));
        Assert.Equal(3, result.ResponseCount);
        searchService.Verify(
            service => service.FindAsync(It.IsAny<Expression<Func<SlskdSearch, bool>>>(), false),
            Times.Once);
        searchService.Verify(
            service => service.FindAsync(It.IsAny<Expression<Func<SlskdSearch, bool>>>(), true),
            Times.Once);
    }

    [Fact]
    public async Task RunSearch_StoresVisibleLockedAndFilteredHitCounts()
    {
        var itemId = Guid.NewGuid();
        await using (var context = _contextFactory.CreateDbContext())
        {
            context.WishlistItems.Add(new WishlistItem
            {
                Id = itemId,
                SearchText = "artist title",
                Filter = "flac -demo",
                MaxResults = 25,
            });
            await context.SaveChangesAsync();
        }

        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.IsAny<SearchOptions?>(),
                It.IsAny<List<string>?>(),
                It.IsAny<string>(),
                It.IsAny<Guid?>()))
            .ReturnsAsync((Guid id, SearchQuery query, SearchScope scope, SearchOptions? options, List<string>? providers, string safetySource, Guid? wishlistItemId) =>
                new SlskdSearch
                {
                    Id = id,
                    SearchText = query.SearchText,
                    State = SearchStates.Requested,
                });
        searchService
            .Setup(service => service.FindAsync(It.IsAny<Expression<Func<SlskdSearch, bool>>>(), false))
            .ReturnsAsync(new SlskdSearch { State = SearchStates.Completed });
        searchService
            .Setup(service => service.FindAsync(It.IsAny<Expression<Func<SlskdSearch, bool>>>(), true))
            .ReturnsAsync((Expression<Func<SlskdSearch, bool>> expression, bool includeResponses) =>
                new SlskdSearch
                {
                    Id = itemId,
                    SearchText = "artist title",
                    State = SearchStates.Completed,
                    ResponseCount = 1,
                    Responses =
                    [
                        new Response
                        {
                            Username = "alice",
                            FileCount = 3,
                            LockedFileCount = 2,
                            Files =
                            [
                                new slskd.Search.File { Filename = @"Music\Artist Title\Album\01 Song.flac", Size = 100 },
                                new slskd.Search.File { Filename = @"Music\Artist Title\Album\02 demo.flac", Size = 100 },
                                new slskd.Search.File { Filename = @"Music\Artist Title\Album\cover.jpg", Size = 100 },
                            ],
                            LockedFiles =
                            [
                                new slskd.Search.File { Filename = @"Music\Artist Title\Album\03 Locked.flac", Size = 100 },
                                new slskd.Search.File { Filename = @"Music\Artist Title\Album\04 Locked Demo.flac", Size = 100 },
                            ],
                        },
                    ],
                });

        var service = new WishlistService(
            _contextFactory,
            Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            searchService.Object,
            Mock.Of<ISoulseekClient>(),
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            Mock.Of<ISourceRankingService>(),
            Mock.Of<IDownloadService>());

        await service.RunSearchAsync(itemId);

        await using var verifyContext = _contextFactory.CreateDbContext();
        var item = await verifyContext.WishlistItems.FindAsync(itemId);
        Assert.NotNull(item);
        Assert.Equal(1, item.LastVisibleHitCount);
        Assert.Equal(1, item.LastHiddenLockedHitCount);
        Assert.Equal(3, item.LastFilteredOutHitCount);
        Assert.Equal(1, item.LastResponseCount);
        Assert.Equal(item.LastVisibleHitCount, item.LastMatchCount);
    }

    [Fact]
    public async Task RunSearch_ExcludesBlockedUsersFromHitsAndAutoDownload()
    {
        var itemId = Guid.NewGuid();
        await using (var context = _contextFactory.CreateDbContext())
        {
            context.WishlistItems.Add(new WishlistItem
            {
                Id = itemId,
                SearchText = "artist title",
                Filter = "flac",
                AutoDownload = true,
                Enabled = true,
            });
            await context.SaveChangesAsync();
        }

        var searchService = CreateCompletedSearchService(itemId);
        var rankingService = new Mock<ISourceRankingService>();
        var downloadService = new Mock<IDownloadService>();
        var blockService = new Mock<IUserBlockService>();
        blockService
            .Setup(service => service.GetBlockedUsernamesAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync((IReadOnlySet<string>)new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "ALICE" });

        var service = new WishlistService(
            _contextFactory,
            Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            searchService.Object,
            Mock.Of<ISoulseekClient>(),
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            rankingService.Object,
            downloadService.Object,
            blockService.Object);

        await service.RunSearchAsync(itemId);

        await using var verifyContext = _contextFactory.CreateDbContext();
        var item = await verifyContext.WishlistItems.FindAsync(itemId);
        Assert.NotNull(item);
        Assert.Equal(0, item.LastVisibleHitCount);
        Assert.Equal(2, item.LastBlockedHitCount);
        downloadService.Verify(
            download => download.EnqueueAsync(
                It.IsAny<string>(),
                It.IsAny<IEnumerable<slskd.Transfers.Downloads.DownloadEnqueueRequest>>(),
                It.IsAny<CancellationToken>()),
            Times.Never);
    }

    [Fact]
    public async Task RunSearch_WhenAutoDownloadEnqueueFails_DoesNotDisableWishlistItem()
    {
        var itemId = Guid.NewGuid();
        await using (var context = _contextFactory.CreateDbContext())
        {
            context.WishlistItems.Add(new WishlistItem
            {
                Id = itemId,
                SearchText = "artist title",
                Filter = "flac",
                AutoDownload = true,
                Enabled = true,
                MaxResults = 25,
            });
            await context.SaveChangesAsync();
        }

        var searchService = CreateCompletedSearchService(itemId);
        var rankingService = new Mock<ISourceRankingService>();
        rankingService
            .Setup(service => service.RankSourcesAsync(It.IsAny<IEnumerable<SourceCandidate>>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((IEnumerable<SourceCandidate> candidates, CancellationToken cancellationToken) =>
                candidates.Select(candidate => new RankedSource
                {
                    Username = candidate.Username,
                    Filename = candidate.Filename,
                    Size = candidate.Size,
                    SmartScore = 10,
                }));
        var downloadService = new Mock<IDownloadService>();
        downloadService
            .Setup(service => service.EnqueueAsync(
                It.IsAny<string>(),
                It.IsAny<IEnumerable<(string Filename, long Size)>>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync((new List<slskd.Transfers.Transfer>(), new List<string> { "failed.flac" }));

        var service = new WishlistService(
            _contextFactory,
            Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            searchService.Object,
            Mock.Of<ISoulseekClient>(),
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            rankingService.Object,
            downloadService.Object);

        await service.RunSearchAsync(itemId);

        await using var verifyContext = _contextFactory.CreateDbContext();
        var item = await verifyContext.WishlistItems.FindAsync(itemId);
        Assert.NotNull(item);
        Assert.True(item.Enabled);
        Assert.Equal(0, item.TotalDownloadCount);
    }

    [Fact]
    public async Task RunSearch_WhenAutoDownloadEnqueuesFiles_DisablesWishlistItemAndCountsEnqueued()
    {
        var itemId = Guid.NewGuid();
        await using (var context = _contextFactory.CreateDbContext())
        {
            context.WishlistItems.Add(new WishlistItem
            {
                Id = itemId,
                SearchText = "artist title",
                Filter = "flac",
                AutoDownload = true,
                Enabled = true,
                MaxResults = 25,
            });
            await context.SaveChangesAsync();
        }

        var searchService = CreateCompletedSearchService(itemId);
        var rankingService = new Mock<ISourceRankingService>();
        rankingService
            .Setup(service => service.RankSourcesAsync(It.IsAny<IEnumerable<SourceCandidate>>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((IEnumerable<SourceCandidate> candidates, CancellationToken cancellationToken) =>
                candidates.Select(candidate => new RankedSource
                {
                    Username = candidate.Username,
                    Filename = candidate.Filename,
                    Size = candidate.Size,
                    SmartScore = 10,
                }));
        var downloadService = new Mock<IDownloadService>();
        downloadService
            .Setup(service => service.EnqueueAsync(
                It.IsAny<string>(),
                It.IsAny<IEnumerable<slskd.Transfers.Downloads.DownloadEnqueueRequest>>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync((
                new List<slskd.Transfers.Transfer>
                {
                    new() { Id = Guid.NewGuid(), Username = "alice", Filename = @"Music\Album\01 Song.flac" },
                    new() { Id = Guid.NewGuid(), Username = "alice", Filename = @"Music\Album\02 Song.flac" },
                },
                new List<string>()));

        var service = new WishlistService(
            _contextFactory,
            Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            searchService.Object,
            Mock.Of<ISoulseekClient>(),
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            rankingService.Object,
            downloadService.Object);

        await service.RunSearchAsync(itemId);

        await using var verifyContext = _contextFactory.CreateDbContext();
        var item = await verifyContext.WishlistItems.FindAsync(itemId);
        Assert.NotNull(item);
        Assert.False(item.Enabled);
        Assert.Equal(2, item.TotalDownloadCount);
        downloadService.Verify(service => service.EnqueueAsync(
            "alice",
            It.Is<IEnumerable<slskd.Transfers.Downloads.DownloadEnqueueRequest>>(requests =>
                requests.All(request => request.WishlistItemId == itemId)),
            It.IsAny<CancellationToken>()));
    }

    [Fact]
    public async Task RunSearch_WhenReleaseContainsTooManyTracks_SkipsAutomaticDownload()
    {
        var itemId = Guid.NewGuid();
        await using (var context = _contextFactory.CreateDbContext())
        {
            context.WishlistItems.Add(new WishlistItem
            {
                Id = itemId,
                SearchText = "artist title",
                Filter = "flac",
                AutoDownload = true,
                Enabled = true,
                MaxResults = 100,
            });
            await context.SaveChangesAsync();
        }

        var responses = new[]
        {
            new Response
            {
                Username = "peer",
                Files = Enumerable.Range(1, 51)
                    .Select(index => new slskd.Search.File
                    {
                        Filename = $@"Music\Artist Title Track\Album\{index:00} Track.flac",
                        Size = index,
                    })
                    .ToList(),
            },
        };
        var searchService = CreateCompletedSearchService(itemId, responses);
        var rankingService = new Mock<ISourceRankingService>();
        rankingService
            .Setup(service => service.RankSourcesAsync(It.IsAny<IEnumerable<SourceCandidate>>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((IEnumerable<SourceCandidate> candidates, CancellationToken _) => candidates.Select(candidate => new RankedSource
            {
                Username = candidate.Username,
                Filename = candidate.Filename,
                Size = candidate.Size,
                SmartScore = 10,
            }));
        var downloadService = new Mock<IDownloadService>();

        var service = new WishlistService(
            _contextFactory,
            Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            searchService.Object,
            Mock.Of<ISoulseekClient>(),
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            rankingService.Object,
            downloadService.Object);

        await service.RunSearchAsync(itemId);

        downloadService.Verify(
            download => download.EnqueueAsync(
                It.IsAny<string>(),
                It.IsAny<IEnumerable<slskd.Transfers.Downloads.DownloadEnqueueRequest>>(),
                It.IsAny<CancellationToken>()),
            Times.Never);
    }

    [Fact]
    public async Task RunSearch_WhenItemIsDisabledDuringSearch_DoesNotAutoDownload()
    {
        var itemId = Guid.NewGuid();
        await using (var context = _contextFactory.CreateDbContext())
        {
            context.WishlistItems.Add(new WishlistItem
            {
                Id = itemId,
                SearchText = "artist title",
                Filter = "flac",
                AutoDownload = true,
                Enabled = true,
                MaxResults = 25,
            });
            await context.SaveChangesAsync();
        }

        var searchService = CreateCompletedSearchService(itemId);
        searchService
            .Setup(service => service.FindAsync(It.IsAny<Expression<Func<SlskdSearch, bool>>>(), true))
            .Callback(() =>
            {
                using var context = _contextFactory.CreateDbContext();
                var item = context.WishlistItems.Single(candidate => candidate.Id == itemId);
                item.Enabled = false;
                context.SaveChanges();
            })
            .ReturnsAsync(new SlskdSearch
            {
                Id = itemId,
                SearchText = "artist title",
                State = SearchStates.Completed,
                ResponseCount = 1,
                Responses =
                [
                    new Response
                    {
                        Username = "alice",
                        Files = [new slskd.Search.File { Filename = @"Music\Artist Title\Album\01 Song.flac", Size = 100 }],
                    },
                ],
            });
        var rankingService = new Mock<ISourceRankingService>();
        var downloadService = new Mock<IDownloadService>();

        var service = new WishlistService(
            _contextFactory,
            Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            searchService.Object,
            Mock.Of<ISoulseekClient>(),
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            rankingService.Object,
            downloadService.Object);

        await service.RunSearchAsync(itemId);

        downloadService.Verify(
            download => download.EnqueueAsync(
                It.IsAny<string>(),
                It.IsAny<IEnumerable<slskd.Transfers.Downloads.DownloadEnqueueRequest>>(),
                It.IsAny<CancellationToken>()),
            Times.Never);
    }

    [Fact]
    public async Task RunSearch_WhenItemIsDisabledDuringRanking_DoesNotAutoDownload()
    {
        var itemId = Guid.NewGuid();
        await using (var context = _contextFactory.CreateDbContext())
        {
            context.WishlistItems.Add(new WishlistItem
            {
                Id = itemId,
                SearchText = "artist title",
                Filter = "flac",
                AutoDownload = true,
                Enabled = true,
                MaxResults = 25,
            });
            await context.SaveChangesAsync();
        }

        var searchService = CreateCompletedSearchService(itemId);
        var rankingStarted = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        var releaseRanking = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        var rankingService = new Mock<ISourceRankingService>();
        rankingService
            .Setup(service => service.RankSourcesAsync(It.IsAny<IEnumerable<SourceCandidate>>(), It.IsAny<CancellationToken>()))
            .Returns(async (IEnumerable<SourceCandidate> candidates, CancellationToken cancellationToken) =>
            {
                rankingStarted.SetResult(true);
                await releaseRanking.Task.WaitAsync(cancellationToken);
                return candidates.Select(candidate => new RankedSource
                {
                    Username = candidate.Username,
                    Filename = candidate.Filename,
                    Size = candidate.Size,
                    SmartScore = 10,
                });
            });
        var downloadService = new Mock<IDownloadService>();

        var service = new WishlistService(
            _contextFactory,
            Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            searchService.Object,
            Mock.Of<ISoulseekClient>(),
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            rankingService.Object,
            downloadService.Object);

        var runTask = service.RunSearchAsync(itemId);
        await rankingStarted.Task.WaitAsync(TimeSpan.FromSeconds(5));

        await using (var context = _contextFactory.CreateDbContext())
        {
            var item = await context.WishlistItems.SingleAsync(candidate => candidate.Id == itemId);
            item.Enabled = false;
            await context.SaveChangesAsync();
        }

        releaseRanking.SetResult(true);
        await runTask;

        downloadService.Verify(
            download => download.EnqueueAsync(
                It.IsAny<string>(),
                It.IsAny<IEnumerable<slskd.Transfers.Downloads.DownloadEnqueueRequest>>(),
                It.IsAny<CancellationToken>()),
            Times.Never);
    }

    [Fact]
    public async Task RunSearch_WhenAutoDownloadLimitIsOne_EnqueuesOnlyOneFile()
    {
        var itemId = Guid.NewGuid();
        await using (var context = _contextFactory.CreateDbContext())
        {
            context.WishlistItems.Add(new WishlistItem
            {
                Id = itemId,
                SearchText = "artist title track",
                Filter = "flac",
                AutoDownload = true,
                Enabled = true,
                MaxResults = 25,
                MaxDownloads = 1,
            });
            await context.SaveChangesAsync();
        }

        var searchService = CreateCompletedSearchService(itemId);
        var rankingService = new Mock<ISourceRankingService>();
        rankingService
            .Setup(service => service.RankSourcesAsync(It.IsAny<IEnumerable<SourceCandidate>>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((IEnumerable<SourceCandidate> candidates, CancellationToken cancellationToken) =>
                candidates.Select(candidate => new RankedSource
                {
                    Username = candidate.Username,
                    Filename = candidate.Filename,
                    Size = candidate.Size,
                    SmartScore = 10,
                }));
        var downloadService = new Mock<IDownloadService>();
        downloadService
            .Setup(service => service.EnqueueAsync(
                It.IsAny<string>(),
                It.Is<IEnumerable<slskd.Transfers.Downloads.DownloadEnqueueRequest>>(requests => requests.Count() == 1),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync((
                new List<slskd.Transfers.Transfer>
                {
                    new() { Id = Guid.NewGuid(), Username = "alice", Filename = @"Music\Album\01 Song.flac" },
                },
                new List<string>()));

        var service = new WishlistService(
            _contextFactory,
            Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            searchService.Object,
            Mock.Of<ISoulseekClient>(),
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            rankingService.Object,
            downloadService.Object);

        await service.RunSearchAsync(itemId);

        await using var verifyContext = _contextFactory.CreateDbContext();
        var item = await verifyContext.WishlistItems.FindAsync(itemId);
        Assert.NotNull(item);
        Assert.False(item.Enabled);
        Assert.Equal(1, item.TotalDownloadCount);
        downloadService.Verify(service => service.EnqueueAsync(
            "alice",
            It.Is<IEnumerable<slskd.Transfers.Downloads.DownloadEnqueueRequest>>(requests => requests.Count() == 1),
            It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task RunSearch_WhenAutoDownloadHasMultipleBitrates_PrefersHighestBitrateGroup()
    {
        var itemId = Guid.NewGuid();
        await using (var context = _contextFactory.CreateDbContext())
        {
            context.WishlistItems.Add(new WishlistItem
            {
                Id = itemId,
                SearchText = "artist title track",
                Filter = "mp3",
                AutoDownload = true,
                Enabled = true,
                MaxResults = 25,
                MaxDownloads = 1,
            });
            await context.SaveChangesAsync();
        }

        var searchService = CreateCompletedSearchService(
            itemId,
            [
                new Response
                {
                    Username = "low-quality-peer",
                    HasFreeUploadSlot = true,
                    QueueLength = 0,
                    UploadSpeed = 1000,
                    Files =
                    [
                        new slskd.Search.File
                        {
                            BitRate = 128,
                            Filename = @"Music\Artist Title Track\Album\128\01 Song.mp3",
                            Size = 100,
                        },
                    ],
                },
                new Response
                {
                    Username = "high-quality-peer",
                    HasFreeUploadSlot = true,
                    QueueLength = 0,
                    UploadSpeed = 1000,
                    Files =
                    [
                        new slskd.Search.File
                        {
                            BitRate = 320,
                            Filename = @"Music\Artist Title Track\Album\320\01 Song.mp3",
                            Size = 100,
                        },
                    ],
                },
            ]);
        var rankingService = new Mock<ISourceRankingService>();
        rankingService
            .Setup(service => service.RankSourcesAsync(It.IsAny<IEnumerable<SourceCandidate>>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((IEnumerable<SourceCandidate> candidates, CancellationToken cancellationToken) =>
                candidates.Select(candidate => new RankedSource
                {
                    Filename = candidate.Filename,
                    SmartScore = 10,
                    Username = candidate.Username,
                }));
        var downloadService = new Mock<IDownloadService>();
        downloadService
            .Setup(service => service.EnqueueAsync(
                It.IsAny<string>(),
                It.IsAny<IEnumerable<slskd.Transfers.Downloads.DownloadEnqueueRequest>>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync((
                new List<slskd.Transfers.Transfer>
                {
                    new() { Id = Guid.NewGuid(), Username = "high-quality-peer", Filename = @"Music\Album\320\01 Song.mp3" },
                },
                new List<string>()));

        var service = new WishlistService(
            _contextFactory,
            Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            searchService.Object,
            Mock.Of<ISoulseekClient>(),
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            rankingService.Object,
            downloadService.Object);

        await service.RunSearchAsync(itemId);

        downloadService.Verify(service => service.EnqueueAsync(
            "high-quality-peer",
            It.Is<IEnumerable<slskd.Transfers.Downloads.DownloadEnqueueRequest>>(requests =>
                requests.Single().BitRate == 320),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task RunSearch_WhenSameBranchFormatsShareTrack_PrefersActualLosslessCopy()
    {
        var itemId = Guid.NewGuid();
        await using (var context = _contextFactory.CreateDbContext())
        {
            context.WishlistItems.Add(new WishlistItem
            {
                Id = itemId,
                SearchText = "artist title track",
                Filter = "mp3 flac",
                AutoDownload = true,
                Enabled = true,
                MaxResults = 25,
                MaxDownloads = 1,
            });
            await context.SaveChangesAsync();
        }

        var searchService = CreateCompletedSearchService(
            itemId,
            [
                new Response
                {
                    Username = "peer",
                    HasFreeUploadSlot = true,
                    QueueLength = 0,
                    UploadSpeed = 1000,
                    Files =
                    [
                        new slskd.Search.File
                        {
                            Filename = @"Music\Artist Title Track\Album\01 Song.mp3",
                            Size = 1_000,
                            BitRate = 320,
                        },
                        new slskd.Search.File
                        {
                            Filename = @"Music\Artist Title Track\Album\01 Song.flac",
                            Size = 100,
                        },
                    ],
                },
            ]);
        var rankingService = new Mock<ISourceRankingService>();
        rankingService
            .Setup(service => service.RankSourcesAsync(It.IsAny<IEnumerable<SourceCandidate>>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((IEnumerable<SourceCandidate> candidates, CancellationToken cancellationToken) =>
                candidates.Select(candidate => new RankedSource
                {
                    Filename = candidate.Filename,
                    SmartScore = 10,
                    Username = candidate.Username,
                }));
        var downloadService = new Mock<IDownloadService>();
        downloadService
            .Setup(service => service.EnqueueAsync(
                It.IsAny<string>(),
                It.IsAny<IEnumerable<slskd.Transfers.Downloads.DownloadEnqueueRequest>>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync((
                new List<slskd.Transfers.Transfer>
                {
                    new() { Id = Guid.NewGuid(), Username = "peer", Filename = @"Music\Album\01 Song.flac" },
                },
                new List<string>()));

        var service = new WishlistService(
            _contextFactory,
            Mock.Of<IDbContextFactory<slskd.Transfers.TransfersDbContext>>(),
            searchService.Object,
            Mock.Of<ISoulseekClient>(),
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            rankingService.Object,
            downloadService.Object);

        await service.RunSearchAsync(itemId);

        downloadService.Verify(service => service.EnqueueAsync(
            "peer",
            It.Is<IEnumerable<slskd.Transfers.Downloads.DownloadEnqueueRequest>>(requests =>
                requests.Single().Filename.EndsWith(".flac", StringComparison.OrdinalIgnoreCase)),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    private static Mock<ISearchService> CreateCompletedSearchService(
        Guid searchId,
        IReadOnlyList<Response>? responses = null)
    {
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.IsAny<SearchOptions?>(),
                It.IsAny<List<string>?>(),
                It.IsAny<string>(),
                It.IsAny<Guid?>()))
            .ReturnsAsync((Guid id, SearchQuery query, SearchScope scope, SearchOptions? options, List<string>? providers, string safetySource, Guid? wishlistItemId) =>
                new SlskdSearch
                {
                    Id = id,
                    SearchText = query.SearchText,
                    State = SearchStates.Requested,
                });
        searchService
            .Setup(service => service.FindAsync(It.IsAny<Expression<Func<SlskdSearch, bool>>>(), false))
            .ReturnsAsync(new SlskdSearch { State = SearchStates.Completed });
        searchService
            .Setup(service => service.FindAsync(It.IsAny<Expression<Func<SlskdSearch, bool>>>(), true))
            .ReturnsAsync(new SlskdSearch
            {
                Id = searchId,
                SearchText = "artist title",
                State = SearchStates.Completed,
                ResponseCount = 1,
                Responses = responses ??
                [
                    new Response
                    {
                        Username = "alice",
                        HasFreeUploadSlot = true,
                        QueueLength = 0,
                        UploadSpeed = 1000,
                        Files =
                        [
                            new slskd.Search.File { Filename = @"Music\Artist Title Track\Album\01 Song.flac", Size = 100 },
                            new slskd.Search.File { Filename = @"Music\Artist Title Track\Album\02 Song.flac", Size = 200 },
                        ],
                    },
                ],
            });

        return searchService;
    }

    private sealed class WishlistDbContextFactory : IDbContextFactory<WishlistDbContext>
    {
        private readonly DbContextOptions<WishlistDbContext> _options;

        public WishlistDbContextFactory(SqliteConnection connection)
        {
            _options = new DbContextOptionsBuilder<WishlistDbContext>()
                .UseSqlite(connection)
                .Options;
        }

        public WishlistDbContext CreateDbContext() => new(_options);

        public ValueTask<WishlistDbContext> CreateDbContextAsync(CancellationToken cancellationToken = default) =>
            ValueTask.FromResult(CreateDbContext());
    }
}
