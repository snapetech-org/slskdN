// <copyright file="AutoReplaceServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Transfers.AutoReplace;

using System;
using System.Collections.Generic;
using System.Linq;
using System.Linq.Expressions;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.AspNetCore.SignalR;
using Microsoft.Extensions.Options;
using Moq;
using slskd.Search;
using slskd.Transfers;
using slskd.Transfers.AutoReplace;
using slskd.Transfers.API;
using slskd.Transfers.Downloads;
using slskd.Transfers.Ranking;
using Soulseek;
using Xunit;
using SearchFile = slskd.Search.File;
using SearchModel = slskd.Search.Search;
using SlskdTransfer = slskd.Transfers.Transfer;
using SlskdOptions = slskd.Options;

public class AutoReplaceServiceTests
{
    [Fact]
    public void GetStuckDownloads_StopsAfterPersistedReplacementBudget()
    {
        var requestId = Guid.NewGuid();
        var currentAttempt = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            RequestId = requestId,
            Username = "last-source",
            Filename = "Artist - Track.flac",
            State = TransferStates.Completed | TransferStates.TimedOut,
        };
        var attempts = new List<SlskdTransfer>
        {
            new()
            {
                Id = Guid.NewGuid(),
                RequestId = requestId,
                Removed = true,
                State = TransferStates.Completed | TransferStates.TimedOut,
            },
            currentAttempt,
        };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Returns(new List<SlskdTransfer> { currentAttempt });
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), true))
            .Returns(attempts);

        var transfers = new Mock<ITransferService>();
        transfers.SetupGet(service => service.Downloads).Returns(downloads.Object);
        var options = new Mock<IOptionsMonitor<SlskdOptions>>();
        options.SetupGet(monitor => monitor.CurrentValue).Returns(new SlskdOptions
        {
            AutoReplace = new SlskdOptions.AutoReplaceOptions { MaxRetries = 1 },
        });

        using var service = new AutoReplaceService(
            transfers.Object,
            Mock.Of<ISearchService>(),
            Mock.Of<ISoulseekClient>(),
            options.Object,
            Mock.Of<ISourceRankingService>());

        Assert.Empty(service.GetStuckDownloads());
        downloads.Verify(
            downloadService => downloadService.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), true),
            Times.Once);
    }

    [Fact]
    public void GetStuckDownloads_AllowsInitialAttemptWithinPersistedReplacementBudget()
    {
        var requestId = Guid.NewGuid();
        var currentAttempt = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            RequestId = requestId,
            Username = "last-source",
            Filename = "Artist - Track.flac",
            State = TransferStates.Completed | TransferStates.TimedOut,
        };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Returns(new List<SlskdTransfer> { currentAttempt });
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), true))
            .Returns(new List<SlskdTransfer> { currentAttempt });

        var transfers = new Mock<ITransferService>();
        transfers.SetupGet(service => service.Downloads).Returns(downloads.Object);
        var options = new Mock<IOptionsMonitor<SlskdOptions>>();
        options.SetupGet(monitor => monitor.CurrentValue).Returns(new SlskdOptions
        {
            AutoReplace = new SlskdOptions.AutoReplaceOptions { MaxRetries = 1 },
        });

        using var service = new AutoReplaceService(
            transfers.Object,
            Mock.Of<ISearchService>(),
            Mock.Of<ISoulseekClient>(),
            options.Object,
            Mock.Of<ISourceRankingService>());

        Assert.Single(service.GetStuckDownloads());
    }

    [Fact]
    public void GetStuckDownloads_StopsAfterRecordedAutoReplaceAttempt()
    {
        var requestId = Guid.NewGuid();
        var currentAttempt = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            RequestId = requestId,
            AutoReplaceAttempts = 1,
            Username = "last-source",
            Filename = "Artist - Track.flac",
            State = TransferStates.Completed | TransferStates.TimedOut,
        };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Returns(new List<SlskdTransfer> { currentAttempt });
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), true))
            .Returns(new List<SlskdTransfer> { currentAttempt });

        var transfers = new Mock<ITransferService>();
        transfers.SetupGet(service => service.Downloads).Returns(downloads.Object);
        var options = new Mock<IOptionsMonitor<SlskdOptions>>();
        options.SetupGet(monitor => monitor.CurrentValue).Returns(new SlskdOptions
        {
            AutoReplace = new SlskdOptions.AutoReplaceOptions { MaxRetries = 1 },
        });

        using var service = new AutoReplaceService(
            transfers.Object,
            Mock.Of<ISearchService>(),
            Mock.Of<ISoulseekClient>(),
            options.Object,
            Mock.Of<ISourceRankingService>());

        Assert.Empty(service.GetStuckDownloads());
    }

    [Fact]
    public void GetStuckDownloads_DoesNotTreatCancelledDownloadsAsStuck()
    {
        var cancelled = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            Username = "source",
            Filename = "Artist - Track.flac",
            State = TransferStates.Completed | TransferStates.Cancelled,
        };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Returns((Expression<Func<SlskdTransfer, bool>> expression, bool _) =>
                new[] { cancelled }.Where(expression.Compile()).ToList());

        var transfers = new Mock<ITransferService>();
        transfers.SetupGet(service => service.Downloads).Returns(downloads.Object);
        var options = new Mock<IOptionsMonitor<SlskdOptions>>();
        options.SetupGet(monitor => monitor.CurrentValue).Returns(new SlskdOptions
        {
            AutoReplace = new SlskdOptions.AutoReplaceOptions { MaxRetries = 3 },
        });

        using var service = new AutoReplaceService(
            transfers.Object,
            Mock.Of<ISearchService>(),
            Mock.Of<ISoulseekClient>(),
            options.Object,
            Mock.Of<ISourceRankingService>());

        Assert.Empty(service.GetStuckDownloads());
    }

    [Fact]
    public async Task ProcessStuckDownloadsAsync_PersistsAttemptWhenNoAlternativeExists()
    {
        var currentAttempt = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            RequestId = Guid.NewGuid(),
            Username = "original-source",
            Filename = "Artist - Track.flac",
            Size = 1000,
            State = TransferStates.Completed | TransferStates.TimedOut,
        };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Returns(new List<SlskdTransfer> { currentAttempt });
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), true))
            .Returns(new List<SlskdTransfer> { currentAttempt });
        downloads
            .Setup(service => service.Update(It.IsAny<SlskdTransfer>()))
            .Callback<SlskdTransfer>(transfer => Assert.Equal(1, transfer.AutoReplaceAttempts));

        var transfers = new Mock<ITransferService>();
        transfers.SetupGet(service => service.Downloads).Returns(downloads.Object);

        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                SearchScope.Network,
                It.IsAny<SearchOptions>(),
                It.IsAny<List<string>>(),
                "auto-replace",
                It.IsAny<Guid?>()))
            .ReturnsAsync((Guid id, SearchQuery _, SearchScope _, SearchOptions _, List<string> _, string _, Guid? _) => new SearchModel
            {
                Id = id,
                State = SearchStates.Completed,
            });
        searchService
            .Setup(service => service.FindAsync(
                It.IsAny<Expression<Func<SearchModel, bool>>>(),
                false))
            .ReturnsAsync(new SearchModel { State = SearchStates.Completed });
        searchService
            .Setup(service => service.FindAsync(
                It.IsAny<Expression<Func<SearchModel, bool>>>(),
                true))
            .ReturnsAsync(new SearchModel
            {
                State = SearchStates.Completed,
                Responses = Array.Empty<Response>(),
            });

        var rankingService = new Mock<ISourceRankingService>();
        rankingService
            .Setup(service => service.RecordFailureAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var options = new Mock<IOptionsMonitor<SlskdOptions>>();
        options.SetupGet(monitor => monitor.CurrentValue).Returns(new SlskdOptions
        {
            AutoReplace = new SlskdOptions.AutoReplaceOptions { MaxRetries = 3 },
        });

        using var service = new AutoReplaceService(
            transfers.Object,
            searchService.Object,
            Mock.Of<ISoulseekClient>(),
            options.Object,
            rankingService.Object,
            searchCompletionTimeout: TimeSpan.FromMilliseconds(10),
            searchPollInterval: TimeSpan.FromMilliseconds(1),
            minimumSearchInterval: TimeSpan.Zero);

        var result = await service.ProcessStuckDownloadsAsync(new AutoReplaceRequest());

        Assert.Equal(1, result.Failed);
        downloads.Verify(service => service.Update(It.IsAny<SlskdTransfer>()), Times.Once);
        Assert.Equal(1, currentAttempt.AutoReplaceAttempts);
    }

    [Fact]
    public async Task FindAlternativesAsync_WaitsForPersistedCompletedSearchResponses()
    {
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                SearchScope.Network,
                It.IsAny<SearchOptions>(),
                It.IsAny<List<string>>(),
                "auto-replace",
                It.IsAny<Guid?>()))
            .ReturnsAsync((Guid id, SearchQuery _, SearchScope _, SearchOptions _, List<string> _, string _, Guid? _) => new SearchModel
            {
                Id = id,
                State = SearchStates.Requested,
            });

        searchService
            .SetupSequence(service => service.FindAsync(
                It.IsAny<Expression<Func<SearchModel, bool>>>(),
                false))
            .ReturnsAsync(new SearchModel { State = SearchStates.Requested })
            .ReturnsAsync(new SearchModel { State = SearchStates.Completed });
        searchService
            .Setup(service => service.FindAsync(
                It.IsAny<Expression<Func<SearchModel, bool>>>(),
                true))
            .ReturnsAsync(new SearchModel
            {
                State = SearchStates.Completed,
                Responses = new[]
                {
                    new Response
                    {
                        Username = "candidate",
                        HasFreeUploadSlot = true,
                        QueueLength = 2,
                        UploadSpeed = 1234,
                        Files = new[]
                        {
                            new SearchFile
                            {
                                Filename = "Artist - Track.flac",
                                Extension = "flac",
                                Size = 1000,
                            },
                        },
                    },
                },
            });

        var rankingService = new Mock<ISourceRankingService>();
        rankingService
            .Setup(service => service.RankSourcesAsync(
                It.IsAny<IEnumerable<SourceCandidate>>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync((IEnumerable<SourceCandidate> candidates, CancellationToken _) => candidates.Select(candidate => new RankedSource
            {
                Username = candidate.Username,
                Filename = candidate.Filename,
                Size = candidate.Size,
                HasFreeUploadSlot = candidate.HasFreeUploadSlot,
                QueueLength = candidate.QueueLength,
                UploadSpeed = candidate.UploadSpeed,
                SizeDiffPercent = candidate.SizeDiffPercent,
                SmartScore = 100,
            }));

        using var service = new AutoReplaceService(
            Mock.Of<ITransferService>(),
            searchService.Object,
            Mock.Of<ISoulseekClient>(),
            Mock.Of<IOptionsMonitor<SlskdOptions>>(),
            rankingService.Object,
            searchCompletionTimeout: TimeSpan.FromMilliseconds(50),
            searchPollInterval: TimeSpan.FromMilliseconds(1),
            minimumSearchInterval: TimeSpan.Zero);

        var alternatives = await service.FindAlternativesAsync(new FindAlternativeRequest
        {
            Username = "original",
            Filename = "Artist - Track.flac",
            Size = 1000,
        });

        var alternative = Assert.Single(alternatives);
        Assert.Equal("candidate", alternative.Username);
        Assert.Equal("Artist - Track.flac", alternative.Filename);
        searchService.Verify(
            service => service.FindAsync(It.IsAny<Expression<Func<SearchModel, bool>>>(), true),
            Times.Once);
        searchService.Verify(
            service => service.FindAsync(It.IsAny<Expression<Func<SearchModel, bool>>>(), false),
            Times.Exactly(2));
    }

    [Fact]
    public async Task FindAlternativesAsync_SkipsOwnSoulseekUsername()
    {
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                SearchScope.Network,
                It.IsAny<SearchOptions>(),
                It.IsAny<List<string>>(),
                "auto-replace",
                It.IsAny<Guid?>()))
            .ReturnsAsync((Guid id, SearchQuery _, SearchScope _, SearchOptions _, List<string> _, string _, Guid? _) => new SearchModel
            {
                Id = id,
                State = SearchStates.Completed,
            });

        searchService
            .Setup(service => service.FindAsync(
                It.IsAny<Expression<Func<SearchModel, bool>>>(),
                false))
            .ReturnsAsync(new SearchModel { State = SearchStates.Completed });
        searchService
            .Setup(service => service.FindAsync(
                It.IsAny<Expression<Func<SearchModel, bool>>>(),
                true))
            .ReturnsAsync(new SearchModel
            {
                State = SearchStates.Completed,
                Responses = new[]
                {
                    CreateSearchResponse("keef_shape"),
                    CreateSearchResponse("remote_candidate"),
                },
            });

        var rankingService = new Mock<ISourceRankingService>();
        rankingService
            .Setup(service => service.RankSourcesAsync(
                It.IsAny<IEnumerable<SourceCandidate>>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync((IEnumerable<SourceCandidate> candidates, CancellationToken _) => candidates.Select(candidate => new RankedSource
            {
                Username = candidate.Username,
                Filename = candidate.Filename,
                Size = candidate.Size,
                HasFreeUploadSlot = candidate.HasFreeUploadSlot,
                QueueLength = candidate.QueueLength,
                UploadSpeed = candidate.UploadSpeed,
                SizeDiffPercent = candidate.SizeDiffPercent,
                SmartScore = 100,
            }));

        var client = new Mock<ISoulseekClient>();
        client.SetupGet(c => c.Username).Returns("keef_shape");

        using var service = new AutoReplaceService(
            Mock.Of<ITransferService>(),
            searchService.Object,
            client.Object,
            Mock.Of<IOptionsMonitor<SlskdOptions>>(),
            rankingService.Object,
            searchCompletionTimeout: TimeSpan.FromMilliseconds(50),
            searchPollInterval: TimeSpan.FromMilliseconds(1),
            minimumSearchInterval: TimeSpan.Zero);

        var alternatives = await service.FindAlternativesAsync(new FindAlternativeRequest
        {
            Username = "original_source",
            Filename = "Artist - Track.flac",
            Size = 1000,
        });

        var alternative = Assert.Single(alternatives);
        Assert.Equal("remote_candidate", alternative.Username);
    }

    [Fact]
    public void IsPlausibleFilenameMatch_RejectsUnrelatedSameSizeAudio()
    {
        Assert.True(AutoReplaceService.IsPlausibleFilenameMatch(
            "Artist - Track.flac",
            "/music/Artist/Album/01 - Artist - Track.flac"));

        Assert.False(AutoReplaceService.IsPlausibleFilenameMatch(
            "Artist - Track.flac",
            "/music/Other Artist/Album/01 - Different Song.flac"));
    }

    [Fact]
    public void IsPlausibleFilenameMatch_RequiresAllIdentifyingTokens()
    {
        Assert.False(AutoReplaceService.IsPlausibleFilenameMatch(
            "David Guetta Never Take Away My Freedom.flac",
            "/music/David Guetta/Album/Never Take Away.flac"));
        Assert.False(AutoReplaceService.IsPlausibleFilenameMatch("Swim.flac", "/music/Any/Swim.flac"));
    }

    [Fact]
    public void BuildAlternativeSearchText_RetainsReleaseContext()
    {
        Assert.Equal(
            "David Guetta Listen Never Take Away My Freedom",
            AutoReplaceService.BuildAlternativeSearchText(
                @"/music/David Guetta/Listen/01 - Never Take Away My Freedom.flac"));
    }

    [Theory]
    [InlineData("Alpha Beta.flac", "/music/ALPHA_BETA.mp3", true)]
    [InlineData("Alpha Beta.flac", "/music/Alpha Other.mp3", false)]
    [InlineData("Alpha Beta Gamma Delta.flac", "/music/Alpha Alpha Other.mp3", false)]
    [InlineData("Kiss Song.flac", "/music/Kiss Song.mp3", true)]
    [InlineData("The Remastered.flac", "/music/The Remastered.mp3", false)]
    public void IsPlausibleFilenameMatch_PreservesTokenSemantics(
        string expected,
        string candidate,
        bool isMatch)
    {
        Assert.Equal(isMatch, AutoReplaceService.IsPlausibleFilenameMatch(expected, candidate));
    }

    [Fact]
    public void PreparedFilenameMatching_AvoidsPerCandidateTokenSets()
    {
        const string expected = "The Artist - Elaborate Track Title (2024 Remastered).flac";
        var candidates = Enumerable.Range(0, 10_000)
            .Select(index => $"/music/Other Artist/Album/{index:D5} - Different Song Title.flac")
            .ToArray();
        var expectedTokens = AutoReplaceService.GetMatchTokens(expected);

        _ = AutoReplaceService.IsPlausibleFilenameMatch(expectedTokens, candidates[0]);
        GC.Collect();
        GC.WaitForPendingFinalizers();
        GC.Collect();

        var before = GC.GetAllocatedBytesForCurrentThread();
        var matches = 0;
        foreach (var candidate in candidates)
        {
            if (AutoReplaceService.IsPlausibleFilenameMatch(expectedTokens, candidate))
            {
                matches++;
            }
        }

        var allocated = GC.GetAllocatedBytesForCurrentThread() - before;
        Assert.Equal(0, matches);
        Assert.InRange(allocated, 0, 6_000_000);
    }

    [Fact]
    public async Task ReplaceDownloadAsync_Emits_RequestIdentity_For_Removed_Attempt()
    {
        var original = new SlskdTransfer
        {
            BatchId = Guid.NewGuid(),
            Direction = TransferDirection.Download,
            Filename = "Artist - Track.flac",
            Id = Guid.NewGuid(),
            AutoReplaceAttempts = 2,
            RequestId = Guid.NewGuid(),
            Username = "original",
        };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.Find(It.IsAny<Expression<Func<SlskdTransfer, bool>>>()))
            .Returns(original);
        downloads
            .Setup(service => service.EnqueueAsync(
                "replacement",
                It.Is<IEnumerable<DownloadEnqueueRequest>>(files =>
                    files.Single().AutoReplaceAttempts == original.AutoReplaceAttempts),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync((new List<SlskdTransfer> { new() }, new List<string>()));
        var transfers = new Mock<ITransferService>();
        transfers.SetupGet(service => service.Downloads).Returns(downloads.Object);

        var clientProxy = new Mock<IClientProxy>();
        var clients = new Mock<IHubClients>();
        clients.SetupGet(value => value.All).Returns(clientProxy.Object);
        var hub = new Mock<IHubContext<TransfersHub>>();
        hub.SetupGet(value => value.Clients).Returns(clients.Object);

        using var service = new AutoReplaceService(
            transfers.Object,
            Mock.Of<ISearchService>(),
            Mock.Of<ISoulseekClient>(),
            Mock.Of<IOptionsMonitor<SlskdOptions>>(),
            Mock.Of<ISourceRankingService>(),
            transfersHub: hub.Object);

        var replaced = await service.ReplaceDownloadAsync(new ReplaceDownloadRequest
        {
            NewFilename = "Artist - Track.flac",
            NewSize = 1,
            NewUsername = "replacement",
            OriginalId = original.Id.ToString(),
            OriginalUsername = original.Username,
        });

        Assert.True(replaced);
        clientProxy.Verify(
            proxy => proxy.SendCoreAsync(
                TransferHubMethods.Removed,
                It.Is<object[]>(arguments =>
                    arguments.Length == 1 &&
                    ((TransferRemoved)arguments[0]).RequestId == original.RequestId),
                It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task ProcessStuckDownloadsAsync_WhenSearchBudgetExceeded_SkipsAndStopsCycle()
    {
        var downloads = new List<SlskdTransfer>
        {
            new()
            {
                Id = Guid.NewGuid(),
                Username = "source-one",
                Filename = "Artist - Track One.flac",
                Size = 1000,
                State = TransferStates.Completed | TransferStates.TimedOut,
            },
            new()
            {
                Id = Guid.NewGuid(),
                Username = "source-two",
                Filename = "Artist - Track Two.flac",
                Size = 1000,
                State = TransferStates.Completed | TransferStates.TimedOut,
            },
        };

        var downloadService = new Mock<IDownloadService>();
        downloadService
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Returns((Expression<Func<SlskdTransfer, bool>> expression, bool _) => downloads.Where(expression.Compile()).ToList());

        var transferService = new Mock<ITransferService>();
        transferService
            .SetupGet(service => service.Downloads)
            .Returns(downloadService.Object);

        using var searchService = new RateLimitedSearchService();

        var rankingService = new Mock<ISourceRankingService>();
        rankingService
            .Setup(service => service.RecordFailureAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        using var service = new AutoReplaceService(
            transferService.Object,
            searchService,
            Mock.Of<ISoulseekClient>(),
            Mock.Of<IOptionsMonitor<SlskdOptions>>(),
            rankingService.Object,
            searchCompletionTimeout: TimeSpan.FromMilliseconds(1),
            searchPollInterval: TimeSpan.FromMilliseconds(1),
            minimumSearchInterval: TimeSpan.Zero);

        var result = await service.ProcessStuckDownloadsAsync(new AutoReplaceRequest());

        Assert.Equal(0, result.Failed);
        Assert.Equal(1, result.Skipped);
        Assert.Contains("Search safety budget exhausted", Assert.Single(result.Details).Error);
        Assert.Equal(1, searchService.StartCount);
    }

    private sealed class RateLimitedSearchService : ISearchService
    {
        public int StartCount { get; private set; }

        public Task DeleteAsync(SearchModel search)
        {
            return Task.CompletedTask;
        }

        public Task<SearchModel> StartAsync(Guid id, SearchQuery query, SearchScope scope, SearchOptions options = null, List<string> requestedProviders = null)
        {
            return StartAsync(id, query, scope, options, requestedProviders, "user");
        }

        public Task<SearchModel> StartAsync(Guid id, SearchQuery query, SearchScope scope, SearchOptions options, List<string> requestedProviders, string safetySource, Guid? wishlistItemId = null)
        {
            StartCount++;
            throw new InvalidOperationException("Search rate limit exceeded. See Soulseek safety configuration.");
        }

        public Task<int> CleanupAsync(int maxAgeDays = 0, int maxCount = 0)
        {
            return Task.FromResult(0);
        }

        public Task<List<SearchModel>> GetByWishlistItemIdAsync(Guid wishlistItemId, int limit = 50)
        {
            return Task.FromResult(new List<SearchModel>());
        }

        public Task<SearchModel> FindAsync(Expression<Func<SearchModel, bool>> expression, bool includeResponses = false)
        {
            return Task.FromResult<SearchModel>(null);
        }

        public Task<List<SearchModel>> ListAsync(
            Expression<Func<SearchModel, bool>> expression = null,
            int limit = 0,
            int offset = 0,
            string? source = null,
            DateTime? afterStartedAt = null,
            Guid? afterId = null)
        {
            return Task.FromResult(new List<SearchModel>());
        }

        public void Update(SearchModel search)
        {
        }

        public bool TryCancel(Guid id)
        {
            return false;
        }

        public Task<int> PruneAsync(int age)
        {
            return Task.FromResult(0);
        }

        public Task<int> DeleteAllAsync()
        {
            return Task.FromResult(0);
        }

        public void Dispose()
        {
        }
    }

    private static Response CreateSearchResponse(string username)
    {
        return new Response
        {
            Username = username,
            HasFreeUploadSlot = true,
            QueueLength = 0,
            UploadSpeed = 1234,
            Files = new[]
            {
                new SearchFile
                {
                    Filename = "Artist - Track.flac",
                    Extension = "flac",
                    Size = 1000,
                },
            },
        };
    }
}
