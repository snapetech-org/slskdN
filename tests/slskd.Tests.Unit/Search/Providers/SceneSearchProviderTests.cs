// <copyright file="SceneSearchProviderTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Search.Providers;

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Logging;
using Moq;
using slskd.Common.Security;
using slskd.Search;
using slskd.Search.Providers;
using Soulseek;
using Xunit;

public sealed class SceneSearchProviderTests
{
    [Fact]
    public async Task StartSearchAsync_WhenRateLimited_EscapesQueryInLog()
    {
        const string query = "artist\r\nforged log entry";
        var logger = new Mock<ILogger<SceneSearchProvider>>();
        var limiter = new Mock<ISoulseekSafetyLimiter>();
        limiter.Setup(candidate => candidate.TryConsumeSearch("scene-provider")).Returns(false);
        var provider = new SceneSearchProvider(
            Mock.Of<ISoulseekClient>(),
            limiter.Object,
            logger.Object);

        await provider.StartSearchAsync(new SearchRequest { SearchText = query }, new RecordingSink(), CancellationToken.None);

        logger.Verify(candidate => candidate.Log(
            LogLevel.Warning,
            It.IsAny<EventId>(),
            It.Is<It.IsAnyType>((state, _) =>
                state.ToString()!.Contains("artist\\r\\nforged log entry", StringComparison.Ordinal) &&
                !state.ToString()!.Contains('\r') &&
                !state.ToString()!.Contains('\n')),
            It.IsAny<Exception?>(),
            It.IsAny<Func<It.IsAnyType, Exception?, string>>()), Times.Once);
    }

    [Fact]
    public async Task StartSearchAsync_WishlistLowResult_UsesBoundedSoulseekFallback()
    {
        var queries = new List<string>();
        var timeouts = new List<int>();
        var nextToken = 40;
        var client = new Mock<ISoulseekClient>();
        client.Setup(candidate => candidate.GetNextToken()).Returns(() => nextToken++);
        client
            .Setup(candidate => candidate.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns((
                SearchQuery searchQuery,
                Action<SearchResponse> responseHandler,
                SearchScope searchScope,
                int? token,
                SearchOptions searchOptions,
                CancellationToken _) =>
            {
                queries.Add(searchQuery.SearchText);
                timeouts.Add(searchOptions.SearchTimeout);

                if (searchQuery.SearchText == "Linkin Park Meteora")
                {
                    return Task.FromResult(new Soulseek.Search(
                        searchQuery,
                        searchScope,
                        token ?? 0,
                        SearchStates.Completed,
                        responseCount: 0,
                        fileCount: 0,
                        lockedFileCount: 0));
                }

                for (var index = 0; index < 10; index++)
                {
                    responseHandler(new SearchResponse(
                        $"fallback-peer-{index}",
                        token ?? 0,
                        hasFreeUploadSlot: true,
                        uploadSpeed: 1,
                        queueLength: 0,
                        [new Soulseek.File(
                            1,
                            $"Linkin Park/Meteora/{index:00}.flac",
                            2_048 + index,
                            "flac")]));
                }

                return Task.FromResult(new Soulseek.Search(
                    searchQuery,
                    searchScope,
                    token ?? 0,
                    SearchStates.Completed,
                    responseCount: 10,
                    fileCount: 10,
                    lockedFileCount: 0));
            });

        var limiter = new Mock<ISoulseekSafetyLimiter>();
        limiter.Setup(candidate => candidate.TryConsumeSearch("scene-provider")).Returns(true);
        var provider = new SceneSearchProvider(
            client.Object,
            limiter.Object,
            NullLogger<SceneSearchProvider>.Instance);
        var sink = new RecordingSink();

        await provider.StartSearchAsync(
            new SearchRequest
            {
                SearchText = "Linkin Park Meteora",
                TimeoutSeconds = 15,
                ResponseLimit = 100,
                FileLimit = 10_000,
                AllowSmartSoulseekFallback = true,
            },
            sink,
            CancellationToken.None);

        Assert.Equal(["Linkin Park Meteora", "Park Meteora"], queries);
        Assert.Equal([15_000, SmartSearchFallback.FallbackTimeoutMilliseconds], timeouts);
        limiter.Verify(candidate => candidate.TryConsumeSearch("scene-provider"), Times.Exactly(2));
        Assert.Equal(10, sink.Results.Count);
        Assert.All(sink.Results, result => Assert.Equal("scene", result.Provider));
        Assert.Equal("fallback-peer-0", sink.Results[0].SceneUserHint);
    }

    private sealed class RecordingSink : ISearchResultSink
    {
        public List<SearchResult> Results { get; } = new();

        public void AddResult(SearchResult result) => Results.Add(result);
    }
}
