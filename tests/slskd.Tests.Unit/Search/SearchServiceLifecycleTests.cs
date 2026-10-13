// <copyright file="SearchServiceLifecycleTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Search;

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Data.Common;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;
using Microsoft.AspNetCore.SignalR;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Moq;
using slskd.Common.Security;
using slskd.Search;
using slskd.Search.API;
using slskd.Search.Providers;
using slskd.VirtualSoulfind.Capture;
using Serilog;
using Serilog.Core;
using Serilog.Events;
using Soulseek;
using ProviderSearchRequest = slskd.Search.Providers.SearchRequest;
using Xunit;

public class SearchServiceLifecycleTests
{
    [Fact]
    public void TryCancel_RemovesAndDisposesTrackedCancellationToken()
    {
        using var service = CreateService();
        var searchId = Guid.NewGuid();
        using var cts = new CancellationTokenSource();

        GetCancellationTokens(service)[searchId] = cts;

        Assert.True(service.TryCancel(searchId));
        Assert.False(GetCancellationTokens(service).ContainsKey(searchId));
        Assert.True(cts.IsCancellationRequested);
        Assert.Throws<ObjectDisposedException>(() => _ = cts.Token.WaitHandle);
    }

    [Fact]
    public void Dispose_CancelsAndDisposesAllTrackedCancellationTokens()
    {
        var service = CreateService();
        var firstId = Guid.NewGuid();
        var secondId = Guid.NewGuid();
        using var firstCts = new CancellationTokenSource();
        using var secondCts = new CancellationTokenSource();
        var tracked = GetCancellationTokens(service);
        tracked[firstId] = firstCts;
        tracked[secondId] = secondCts;

        service.Dispose();

        Assert.Empty(tracked);
        Assert.True(firstCts.IsCancellationRequested);
        Assert.True(secondCts.IsCancellationRequested);
        Assert.Throws<ObjectDisposedException>(() => _ = firstCts.Token.WaitHandle);
        Assert.Throws<ObjectDisposedException>(() => _ = secondCts.Token.WaitHandle);
    }

    [Fact]
    public void IsExpectedSearchCancellation_WhenSearchTokenCancelled_ReturnsTrue()
    {
        using var cts = new CancellationTokenSource();
        cts.Cancel();

        var result = SearchService.IsExpectedSearchCancellation(
            new OperationCanceledException(),
            cts.Token,
            applicationIsShuttingDown: false);

        Assert.True(result);
    }

    [Fact]
    public void IsExpectedSearchCancellation_WhenApplicationShuttingDown_ReturnsTrue()
    {
        using var cts = new CancellationTokenSource();

        var result = SearchService.IsExpectedSearchCancellation(
            new OperationCanceledException(),
            cts.Token,
            applicationIsShuttingDown: true);

        Assert.True(result);
    }

    [Fact]
    public void IsExpectedSearchCancellation_WhenNotCancelled_ReturnsFalse()
    {
        using var cts = new CancellationTokenSource();

        var result = SearchService.IsExpectedSearchCancellation(
            new OperationCanceledException(),
            cts.Token,
            applicationIsShuttingDown: false);

        Assert.False(result);
    }

    [Fact]
    public void IsSearchUnavailableDuringLogin_WhenSoulseekStillLoggingIn_ReturnsTrue()
    {
        var result = SearchService.IsSearchUnavailableDuringLogin(
            new InvalidOperationException("The server connection must be connected and logged in to perform a search (currently: Connected, LoggingIn)"));

        Assert.True(result);
    }

    [Fact]
    public void IsSearchUnavailableDuringLogin_WhenDifferentInvalidOperation_ReturnsFalse()
    {
        var result = SearchService.IsSearchUnavailableDuringLogin(
            new InvalidOperationException("Search rate limit exceeded. See Soulseek safety configuration."));

        Assert.False(result);
    }

    [Fact]
    public void IsExpectedSearchFinalizationFailure_WhenObjectDisposedDuringShutdown_ReturnsTrue()
    {
        var result = SearchService.IsExpectedSearchFinalizationFailure(
            new ObjectDisposedException("SearchDbContext"),
            applicationIsShuttingDown: true);

        Assert.True(result);
    }

    [Fact]
    public void IsExpectedSearchFinalizationFailure_WhenObjectDisposedDuringRuntime_ReturnsFalse()
    {
        var result = SearchService.IsExpectedSearchFinalizationFailure(
            new ObjectDisposedException("SearchDbContext"),
            applicationIsShuttingDown: false);

        Assert.False(result);
    }

    [Fact]
    public void IsExpectedSearchRuntimeShutdownFailure_WhenLockDisposingDuringShutdown_ReturnsTrue()
    {
        var result = SearchService.IsExpectedSearchRuntimeShutdownFailure(
            new InvalidOperationException("The lock is being disposed while still being used. It either is being held by a thread and/or has active waiters waiting to acquire the lock."),
            applicationIsShuttingDown: true);

        Assert.True(result);
    }

    [Fact]
    public void IsExpectedSearchRuntimeShutdownFailure_WhenLockDisposingDuringRuntime_ReturnsFalse()
    {
        var result = SearchService.IsExpectedSearchRuntimeShutdownFailure(
            new InvalidOperationException("The lock is being disposed while still being used."),
            applicationIsShuttingDown: false);

        Assert.False(result);
    }

    [Fact]
    public void IsExpectedSearchRuntimeShutdownFailure_WhenDifferentExceptionDuringShutdown_ReturnsFalse()
    {
        var result = SearchService.IsExpectedSearchRuntimeShutdownFailure(
            new InvalidOperationException("Search backend failed."),
            applicationIsShuttingDown: true);

        Assert.False(result);
    }

    [Fact]
    public void ApplyResponseSummary_IncludesEarlyMeshResponses()
    {
        var search = new slskd.Search.Search();
        var responses = new List<Response>
        {
            new()
            {
                Username = "mesh-peer",
                FileCount = 1,
                LockedFileCount = 0,
                Files = new List<slskd.Search.File>
                {
                    new()
                    {
                        Filename = "song.flac",
                        Size = 1234,
                    },
                },
                LockedFiles = new List<slskd.Search.File>(),
            },
        };

        SearchService.ApplyResponseSummary(search, responses);

        Assert.Equal(1, search.ResponseCount);
        Assert.Equal(1, search.FileCount);
        Assert.Equal(0, search.LockedFileCount);
    }

    [Fact]
    public void WithSoulseekSearch_PreservesPersistedProvenanceAndResponseAvailability()
    {
        var wishlistItemId = Guid.NewGuid();
        var startedAt = DateTime.UtcNow.AddSeconds(-1);
        var original = new slskd.Search.Search
        {
            Id = Guid.NewGuid(),
            ResponsesAvailable = true,
            SearchText = "artist title",
            Source = "wishlist",
            StartedAt = startedAt,
            Token = 42,
            WishlistItemId = wishlistItemId,
        };
        var progress = new Soulseek.Search(
            SearchQuery.FromText("artist title"),
            SearchScope.Network,
            42,
            SearchStates.InProgress,
            responseCount: 3,
            fileCount: 12,
            lockedFileCount: 2);

        var updated = original.WithSoulseekSearch(progress);

        Assert.Equal(original.Id, updated.Id);
        Assert.Equal("artist title", updated.SearchText);
        Assert.Equal("wishlist", updated.Source);
        Assert.Equal(startedAt, updated.StartedAt);
        Assert.Equal(42, updated.Token);
        Assert.Equal(wishlistItemId, updated.WishlistItemId);
        Assert.True(updated.ResponsesAvailable);
        Assert.Equal(3, updated.ResponseCount);
        Assert.Equal(12, updated.FileCount);
        Assert.Equal(2, updated.LockedFileCount);
        Assert.Equal(SearchStates.InProgress, updated.State);
    }

    [Fact]
    public async Task ListAsync_ResponseLessProjectionPreservesProvenance()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<SearchDbContext>()
            .UseSqlite(connection)
            .Options;
        var searchId = Guid.NewGuid();
        var wishlistItemId = Guid.NewGuid();
        await using (var context = new SearchDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
            context.Searches.Add(new slskd.Search.Search
            {
                Id = searchId,
                Responses =
                [
                    new Response
                    {
                        FileCount = 1,
                        Files =
                        [
                            new slskd.Search.File
                            {
                                Filename = "artist\\album\\track.flac",
                                Size = 1_024,
                            },
                        ],
                        Username = "peer",
                    },
                ],
                SearchText = "artist title",
                Source = "wishlist",
                State = SearchStates.InProgress,
                Token = 42,
                WishlistItemId = wishlistItemId,
            });
            await context.SaveChangesAsync();
        }

        using var service = new SearchService(
            CreateSearchHub().Object,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            Mock.Of<ISoulseekClient>(),
            new SearchDbContextFactory(options),
            Mock.Of<ISoulseekSafetyLimiter>());

        var listed = Assert.Single(await service.ListAsync());
        Assert.Equal(searchId, listed.Id);
        Assert.Equal("artist title", listed.SearchText);
        Assert.Equal("wishlist", listed.Source);
        Assert.Equal(wishlistItemId, listed.WishlistItemId);
        Assert.True(listed.ResponsesAvailable);
        Assert.Empty(listed.Responses);
    }

    [Fact]
    public async Task ListAsync_ContinuesByStartedAtAndIdAfterANewSearchArrives()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<SearchDbContext>()
            .UseSqlite(connection)
            .Options;
        var startedAt = new DateTime(2026, 10, 13, 12, 0, 0, DateTimeKind.Utc);
        var firstId = Guid.Parse("ffffffff-ffff-ffff-ffff-ffffffffffff");
        var cursorId = Guid.Parse("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee");
        var nextId = Guid.Parse("dddddddd-dddd-dddd-dddd-dddddddddddd");
        var olderId = Guid.Parse("cccccccc-cccc-cccc-cccc-cccccccccccc");
        await using (var context = new SearchDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
            context.Searches.AddRange(
                new slskd.Search.Search { Id = firstId, StartedAt = startedAt, Source = "Wishlist" },
                new slskd.Search.Search { Id = cursorId, StartedAt = startedAt, Source = "wishlist" },
                new slskd.Search.Search { Id = nextId, StartedAt = startedAt, Source = "wishlist" },
                new slskd.Search.Search { Id = olderId, StartedAt = startedAt.AddHours(-1), Source = "wishlist" });
            await context.SaveChangesAsync();
        }

        using var service = new SearchService(
            CreateSearchHub().Object,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            Mock.Of<ISoulseekClient>(),
            new SearchDbContextFactory(options),
            Mock.Of<ISoulseekSafetyLimiter>());

        var firstPage = await service.ListAsync(limit: 2, source: "wishlist");
        Assert.Equal([firstId, cursorId], firstPage.Select(search => search.Id));

        await using (var context = new SearchDbContext(options))
        {
            context.Searches.Add(new slskd.Search.Search
            {
                Id = Guid.NewGuid(),
                StartedAt = startedAt.AddHours(1),
                Source = "wishlist",
            });
            await context.SaveChangesAsync();
        }

        var continuation = await service.ListAsync(
            limit: 2,
            source: "wishlist",
            afterStartedAt: firstPage[^1].StartedAt,
            afterId: firstPage[^1].Id);

        Assert.Equal([nextId, olderId], continuation.Select(search => search.Id));
    }

    [Fact]
    public async Task NotifyTrafficObserverAsync_WhenOneResponseFails_Continues()
    {
        var observer = new Mock<ITrafficObserver>();
        var query = "query\r\nforged";
        var responses = new[]
        {
            new SearchResponse("first", 1, true, 0, 0, Array.Empty<Soulseek.File>(), Array.Empty<Soulseek.File>()),
            new SearchResponse("second", 1, true, 0, 0, Array.Empty<Soulseek.File>(), Array.Empty<Soulseek.File>()),
        };

        observer
            .Setup(m => m.OnSearchResultsAsync(query, responses[0], It.IsAny<CancellationToken>()))
            .Returns(Task.FromException(new InvalidOperationException("observer\r\nfailed")));
        observer
            .Setup(m => m.OnSearchResultsAsync(query, responses[1], It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var sink = new CapturingSink();
        await SearchService.NotifyTrafficObserverAsync(
            observer.Object,
            query,
            responses,
            new LoggerConfiguration().MinimumLevel.Debug().WriteTo.Sink(sink).CreateLogger(),
            CancellationToken.None);

        observer.Verify(
            m => m.OnSearchResultsAsync(query, It.IsAny<SearchResponse>(), It.IsAny<CancellationToken>()),
            Times.Exactly(2));

        var logEvent = Assert.Single(sink.Events);
        Assert.Null(logEvent.Exception);
        Assert.Contains("query\\r\\nforged", logEvent.RenderMessage());
        Assert.Contains("observer\\r\\nfailed", logEvent.RenderMessage());
        Assert.DoesNotContain(query, logEvent.RenderMessage());
        Assert.DoesNotContain("observer\r\nfailed", logEvent.RenderMessage());
    }

    [Fact]
    public async Task StartAsync_WhenBridgedSearch_PreservesSourceAndWishlistItemId()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<SearchDbContext>()
            .UseSqlite(connection)
            .Options;
        await using (var context = new SearchDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var hub = CreateSearchHub();
        var provider = new Mock<ISearchProvider>();
        provider.Setup(p => p.Name).Returns("pod");
        provider.Setup(p => p.StartSearchAsync(
                It.IsAny<slskd.Search.Providers.SearchRequest>(),
                It.IsAny<ISearchResultSink>(),
                It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var wishlistItemId = Guid.NewGuid();
        using var service = new SearchService(
            hub.Object,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options
            {
                Feature = new slskd.Options.FeatureOptions
                {
                    ScenePodBridge = true,
                },
            }),
            Mock.Of<ISoulseekClient>(),
            new SearchDbContextFactory(options),
            Mock.Of<ISoulseekSafetyLimiter>(),
            searchProviders: [provider.Object]);

        var search = await service.StartAsync(
            Guid.NewGuid(),
            SearchQuery.FromText("artist title"),
            SearchScope.Network,
            new SearchOptions(),
            requestedProviders: null,
            safetySource: "wishlist",
            wishlistItemId: wishlistItemId);

        Assert.Equal("wishlist", search.Source);
        Assert.Equal(wishlistItemId, search.WishlistItemId);

        await using var verifyContext = new SearchDbContext(options);
        var persisted = await verifyContext.Searches.AsNoTracking().SingleAsync();
        Assert.Equal("wishlist", persisted.Source);
        Assert.Equal(wishlistItemId, persisted.WishlistItemId);
    }

    [Fact]
    public async Task StartAsync_WhenBridgedWishlistSearchFiltersEveryProviderResult()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<SearchDbContext>()
            .UseSqlite(connection)
            .Options;
        await using (var context = new SearchDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var hub = CreateSearchHub();
        var provider = new Mock<ISearchProvider>();
        provider.Setup(candidate => candidate.Name).Returns("pod");
        ProviderSearchRequest? capturedRequest = null;
        provider.Setup(candidate => candidate.StartSearchAsync(
                It.IsAny<ProviderSearchRequest>(),
                It.IsAny<ISearchResultSink>(),
                It.IsAny<CancellationToken>()))
            .Returns((ProviderSearchRequest request, ISearchResultSink sink, CancellationToken _) =>
            {
                capturedRequest = request;
                sink.AddResult(new SearchResult
                {
                    Provider = "pod",
                    PrimarySource = "pod",
                    SourceProviders = ["pod"],
                    Response = new Response
                    {
                        Username = "peer",
                        FileCount = 2,
                        Files =
                        [
                            new slskd.Search.File { Extension = "flac", Filename = "Artist Title/01.flac", Size = 1 },
                            new slskd.Search.File { Extension = "flac", Filename = "Artist/02.flac", Size = 2 },
                        ],
                    },
                });
                return Task.CompletedTask;
            });

        var fileFilter = new Func<Soulseek.File, bool>(file => file.Extension == "flac");
        var wishlistItemId = Guid.NewGuid();
        using var service = new SearchService(
            hub.Object,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options
            {
                Feature = new slskd.Options.FeatureOptions
                {
                    ScenePodBridge = true,
                },
            }),
            Mock.Of<ISoulseekClient>(),
            new SearchDbContextFactory(options),
            Mock.Of<ISoulseekSafetyLimiter>(),
            searchProviders: [provider.Object]);

        var search = await service.StartAsync(
            Guid.NewGuid(),
            SearchQuery.FromText("artist title"),
            SearchScope.Network,
            new SearchOptions(fileFilter: fileFilter),
            requestedProviders: null,
            safetySource: "wishlist",
            wishlistItemId: wishlistItemId);

        var response = Assert.Single(search.Responses);
        var file = Assert.Single(response.Files);
        Assert.Equal("Artist Title/01.flac", file.Filename);
        Assert.Same(fileFilter, capturedRequest!.FileFilter);
        Assert.Equal(1, search.FileCount);
    }

    [Fact]
    public async Task StartAsync_WhenClientLaunchFails_ReleasesCancellationToken()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<SearchDbContext>()
            .UseSqlite(connection)
            .Options;
        await using (var context = new SearchDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var client = new Mock<ISoulseekClient>();
        client.Setup(candidate => candidate.GetNextToken()).Returns(42);
        client
            .Setup(candidate => candidate.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken?>()))
            .Throws(new InvalidOperationException("search launch failed"));
        var safetyLimiter = new Mock<ISoulseekSafetyLimiter>();
        safetyLimiter.Setup(limiter => limiter.TryConsumeSearch("wishlist")).Returns(true);
        using var service = new SearchService(
            CreateSearchHub().Object,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            client.Object,
            new SearchDbContextFactory(options),
            safetyLimiter.Object);

        await Assert.ThrowsAsync<InvalidOperationException>(() => service.StartAsync(
            Guid.NewGuid(),
            SearchQuery.FromText("artist title"),
            SearchScope.Network,
            new SearchOptions(),
            requestedProviders: null,
            safetySource: "wishlist"));

        Assert.Empty(GetCancellationTokens(service));
        await using var verifyContext = new SearchDbContext(options);
        var persisted = await verifyContext.Searches.AsNoTracking().SingleAsync();
        Assert.True(persisted.State.HasFlag(SearchStates.Errored));
    }

    [Fact]
    public async Task StartAsync_AfterLaunch_ContinuesPublishingBoundedProgress()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<SearchDbContext>()
            .UseSqlite(connection)
            .Options;
        await using (var context = new SearchDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var updates = new ConcurrentQueue<slskd.Search.Search>();
        var completion = new TaskCompletionSource<Soulseek.Search>(TaskCreationOptions.RunContinuationsAsynchronously);
        Action<SearchResponse>? responseHandler = null;
        SearchOptions? capturedOptions = null;
        var client = new Mock<ISoulseekClient>();
        client.Setup(candidate => candidate.GetNextToken()).Returns(42);
        client
            .Setup(candidate => candidate.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken?>()))
            .Callback<SearchQuery, Action<SearchResponse>, SearchScope, int?, SearchOptions, CancellationToken?>(
                (_, handler, _, _, searchOptions, _) =>
                {
                    responseHandler = handler;
                    capturedOptions = searchOptions;
                })
            .Returns(completion.Task);
        var safetyLimiter = new Mock<ISoulseekSafetyLimiter>();
        safetyLimiter.Setup(limiter => limiter.TryConsumeSearch("wishlist")).Returns(true);
        var wishlistItemId = Guid.NewGuid();
        using var service = new SearchService(
            CreateSearchHub(updates).Object,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            client.Object,
            new SearchDbContextFactory(options),
            safetyLimiter.Object);

        await service.StartAsync(
            Guid.NewGuid(),
            SearchQuery.FromText("artist title"),
            SearchScope.Network,
            new SearchOptions(),
            requestedProviders: null,
            safetySource: "wishlist",
            wishlistItemId: wishlistItemId);

        var firstResponse = new SearchResponse(
            "peer-one",
            42,
            hasFreeUploadSlot: true,
            uploadSpeed: 1,
            queueLength: 0,
            [new Soulseek.File(1, "artist title\\album\\one.flac", 1_024, "flac")]);
        var secondResponse = new SearchResponse(
            "peer-two",
            42,
            hasFreeUploadSlot: true,
            uploadSpeed: 1,
            queueLength: 0,
            [new Soulseek.File(1, "artist title\\album\\two.flac", 2_048, "flac")]);
        var inProgress = new Soulseek.Search(
            SearchQuery.FromText("artist title"),
            SearchScope.Network,
            42,
            SearchStates.InProgress,
            responseCount: 2,
            fileCount: 2,
            lockedFileCount: 0);

        Assert.NotNull(responseHandler);
        Assert.NotNull(capturedOptions);
        responseHandler(firstResponse);
        capturedOptions.ResponseReceived((inProgress, firstResponse));
        Assert.Single(updates, update => update.ResponseCount == 1);

        responseHandler(secondResponse);
        capturedOptions.ResponseReceived((inProgress, secondResponse));
        Assert.DoesNotContain(updates, update => update.ResponseCount == 2);

        Assert.True(await WaitUntilAsync(
            () => updates.Any(update => update.ResponseCount == 2),
            attempts: 120,
            delayMs: 25));

        await using (var progressContext = new SearchDbContext(options))
        {
            var progressRow = await progressContext.Searches.AsNoTracking().SingleAsync();
            Assert.Equal(0, progressRow.ResponseCount);
            Assert.Empty(progressRow.Responses);
        }

        completion.SetResult(new Soulseek.Search(
            SearchQuery.FromText("artist title"),
            SearchScope.Network,
            42,
            SearchStates.Completed,
            responseCount: 2,
            fileCount: 2,
            lockedFileCount: 0));
        Assert.True(await WaitUntilAsync(
            () => GetCancellationTokens(service).IsEmpty,
            attempts: 120,
            delayMs: 25));

        await using var verifyContext = new SearchDbContext(options);
        var persisted = await verifyContext.Searches.AsNoTracking().SingleAsync();
        Assert.Equal("wishlist", persisted.Source);
        Assert.Equal(wishlistItemId, persisted.WishlistItemId);
        Assert.Equal(2, persisted.ResponseCount);
        Assert.Equal(2, persisted.Responses.Count());
    }

    [Fact]
    public async Task DeleteAsync_DuringSearch_CancelsWorkAndDoesNotPublishCompletionAfterDelete()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<SearchDbContext>()
            .UseSqlite(connection)
            .Options;
        await using (var context = new SearchDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var updates = new ConcurrentQueue<slskd.Search.Search>();
        var deletes = new ConcurrentQueue<slskd.Search.Search>();
        var completion = new TaskCompletionSource<Soulseek.Search>(TaskCreationOptions.RunContinuationsAsynchronously);
        SearchOptions? capturedSearchOptions = null;
        CancellationToken? capturedCancellationToken = null;
        var client = new Mock<ISoulseekClient>();
        client.Setup(candidate => candidate.GetNextToken()).Returns(42);
        client
            .Setup(candidate => candidate.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken?>()))
            .Callback<SearchQuery, Action<SearchResponse>, SearchScope, int?, SearchOptions, CancellationToken?>(
                (_, _, _, _, searchOptions, cancellationToken) =>
                {
                    capturedSearchOptions = searchOptions;
                    capturedCancellationToken = cancellationToken;
                })
            .Returns(completion.Task);
        var safetyLimiter = new Mock<ISoulseekSafetyLimiter>();
        safetyLimiter.Setup(limiter => limiter.TryConsumeSearch("user")).Returns(true);
        using var service = new SearchService(
            CreateSearchHub(updates, deletes).Object,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            client.Object,
            new SearchDbContextFactory(options),
            safetyLimiter.Object);

        var searchId = Guid.NewGuid();
        await service.StartAsync(
            searchId,
            SearchQuery.FromText("artist title"),
            SearchScope.Network);

        Assert.NotNull(capturedSearchOptions);
        capturedSearchOptions.StateChanged?.Invoke((
            SearchStates.InProgress,
            new Soulseek.Search(
                SearchQuery.FromText("artist title"),
                SearchScope.Network,
                42,
                SearchStates.InProgress,
                responseCount: 0,
                fileCount: 0,
                lockedFileCount: 0)));
        capturedSearchOptions.StateChanged?.Invoke((
            SearchStates.InProgress,
            new Soulseek.Search(
                SearchQuery.FromText("artist title"),
                SearchScope.Network,
                42,
                SearchStates.Completed,
                responseCount: 0,
                fileCount: 0,
                lockedFileCount: 0)));

        var search = await service.FindAsync(candidate => candidate.Id == searchId);
        Assert.NotNull(search);
        var updatesBeforeDelete = updates.Count;

        await service.DeleteAsync(search);

        Assert.True(capturedCancellationToken.HasValue);
        Assert.True(capturedCancellationToken.Value.IsCancellationRequested);
        Assert.Equal(searchId, Assert.Single(deletes).Id);

        completion.SetResult(new Soulseek.Search(
            SearchQuery.FromText("artist title"),
            SearchScope.Network,
            42,
            SearchStates.Completed,
            responseCount: 0,
            fileCount: 0,
            lockedFileCount: 0));

        Assert.True(await WaitUntilAsync(
            () => GetCancellationTokens(service).IsEmpty,
            attempts: 120,
            delayMs: 25));
        Assert.Equal(updatesBeforeDelete, updates.Count);

        await using var verifyContext = new SearchDbContext(options);
        Assert.False(await verifyContext.Searches.AnyAsync(candidate => candidate.Id == searchId));
    }

    [Fact]
    public async Task StartAsync_WishlistLowResult_UsesBoundedLeadingTermFallback()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<SearchDbContext>()
            .UseSqlite(connection)
            .Options;
        await using (var context = new SearchDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var queries = new List<string>();
        var timeouts = new List<int>();
        var nextToken = 41;
        var client = new Mock<ISoulseekClient>();
        client.Setup(candidate => candidate.GetNextToken()).Returns(() => nextToken++);
        client
            .Setup(candidate => candidate.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken?>()))
            .Returns((
                SearchQuery searchQuery,
                Action<SearchResponse> responseHandler,
                SearchScope searchScope,
                int? token,
                SearchOptions searchOptions,
                CancellationToken? _) =>
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

                responseHandler(new SearchResponse(
                    "fallback-peer",
                    token ?? 0,
                    hasFreeUploadSlot: true,
                    uploadSpeed: 1,
                    queueLength: 0,
                    [new Soulseek.File(1, "Linkin Park/Meteora/01.flac", 2_048, "flac")]));
                responseHandler(new SearchResponse(
                    "false-positive-peer",
                    token ?? 0,
                    hasFreeUploadSlot: true,
                    uploadSpeed: 1,
                    queueLength: 0,
                    [new Soulseek.File(1, "Park/Meteora/01.flac", 2_048, "flac")]));

                return Task.FromResult(new Soulseek.Search(
                    searchQuery,
                    searchScope,
                    token ?? 0,
                    SearchStates.Completed,
                    responseCount: 10,
                    fileCount: 10,
                    lockedFileCount: 0));
            });

        var safetyLimiter = new Mock<ISoulseekSafetyLimiter>();
        safetyLimiter.Setup(limiter => limiter.TryConsumeSearch("wishlist")).Returns(true);
        using var service = new SearchService(
            CreateSearchHub().Object,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            client.Object,
            new SearchDbContextFactory(options),
            safetyLimiter.Object);

        var searchId = Guid.NewGuid();
        var wishlistItemId = Guid.NewGuid();
        await service.StartAsync(
            searchId,
            SearchQuery.FromText("Linkin Park Meteora"),
            SearchScope.Network,
            new SearchOptions(searchTimeout: 15_000),
            requestedProviders: null,
            safetySource: "wishlist",
            wishlistItemId: wishlistItemId);

        Assert.True(await WaitUntilAsync(
            () => GetCancellationTokens(service).IsEmpty,
            attempts: 120,
            delayMs: 25));

        Assert.Equal(["Linkin Park Meteora", "Park Meteora"], queries);
        Assert.Equal([15_000, SmartSearchFallback.FallbackTimeoutMilliseconds], timeouts);
        safetyLimiter.Verify(limiter => limiter.TryConsumeSearch("wishlist"), Times.Exactly(2));

        await using var verifyContext = new SearchDbContext(options);
        var persisted = await verifyContext.Searches.AsNoTracking().SingleAsync();
        Assert.True(persisted.State.HasFlag(SearchStates.Completed));
        Assert.Equal(wishlistItemId, persisted.WishlistItemId);
        Assert.Equal(1, persisted.ResponseCount);
        Assert.Equal(1, persisted.FileCount);
        Assert.Single(persisted.Responses);
    }

    [Fact]
    public async Task StartAsync_WishlistLowResult_DefersCompletedStateUntilFallbackFinishes()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<SearchDbContext>()
            .UseSqlite(connection)
            .Options;
        await using (var context = new SearchDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var fallbackCalled = new TaskCompletionSource<object?>(TaskCreationOptions.RunContinuationsAsynchronously);
        var fallbackCompletion = new TaskCompletionSource<Soulseek.Search>(TaskCreationOptions.RunContinuationsAsynchronously);
        var nextToken = 50;
        var client = new Mock<ISoulseekClient>();
        client.Setup(candidate => candidate.GetNextToken()).Returns(() => nextToken++);
        client
            .Setup(candidate => candidate.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken?>()))
            .Returns((
                SearchQuery searchQuery,
                Action<SearchResponse> _,
                SearchScope searchScope,
                int? token,
                SearchOptions searchOptions,
                CancellationToken? _) =>
            {
                if (searchQuery.SearchText == "Linkin Park Meteora")
                {
                    searchOptions.StateChanged?.Invoke((
                        SearchStates.InProgress,
                        new Soulseek.Search(
                            searchQuery,
                            searchScope,
                            token ?? 0,
                            SearchStates.InProgress,
                            responseCount: 0,
                            fileCount: 0,
                            lockedFileCount: 0)));
                    searchOptions.StateChanged?.Invoke((
                        SearchStates.InProgress,
                        new Soulseek.Search(
                            searchQuery,
                            searchScope,
                            token ?? 0,
                            SearchStates.Completed,
                            responseCount: 0,
                            fileCount: 0,
                            lockedFileCount: 0)));

                    return Task.FromResult(new Soulseek.Search(
                        searchQuery,
                        searchScope,
                        token ?? 0,
                        SearchStates.Completed,
                        responseCount: 0,
                        fileCount: 0,
                        lockedFileCount: 0));
                }

                fallbackCalled.TrySetResult(null);
                return fallbackCompletion.Task;
            });

        var safetyLimiter = new Mock<ISoulseekSafetyLimiter>();
        safetyLimiter.Setup(limiter => limiter.TryConsumeSearch("wishlist")).Returns(true);
        using var service = new SearchService(
            CreateSearchHub().Object,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            client.Object,
            new SearchDbContextFactory(options),
            safetyLimiter.Object);

        await service.StartAsync(
            Guid.NewGuid(),
            SearchQuery.FromText("Linkin Park Meteora"),
            SearchScope.Network,
            new SearchOptions(searchTimeout: 15_000),
            requestedProviders: null,
            safetySource: "wishlist");

        await fallbackCalled.Task.WaitAsync(TimeSpan.FromSeconds(5));
        await using (var verifyPendingContext = new SearchDbContext(options))
        {
            var pending = await verifyPendingContext.Searches.AsNoTracking().SingleAsync();
            Assert.False(pending.State.HasFlag(SearchStates.Completed));
        }

        fallbackCompletion.SetResult(new Soulseek.Search(
            SearchQuery.FromText("Park Meteora"),
            SearchScope.Network,
            nextToken,
            SearchStates.Completed,
            responseCount: 10,
            fileCount: 10,
            lockedFileCount: 0));

        Assert.True(await WaitUntilAsync(
            () => GetCancellationTokens(service).IsEmpty,
            attempts: 200,
            delayMs: 25));
        await using var verifyContext = new SearchDbContext(options);
        var completed = await verifyContext.Searches.AsNoTracking().SingleAsync();
        Assert.True(completed.State.HasFlag(SearchStates.Completed));
    }

    [Fact]
    public async Task CleanupAsync_WithLargeExpiredSet_UsesBoundedSetBasedDeletesAndBroadcastsEachSearch()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var commandInterceptor = new RecordingCommandInterceptor();
        var options = new DbContextOptionsBuilder<SearchDbContext>()
            .UseSqlite(connection)
            .AddInterceptors(commandInterceptor)
            .Options;
        var now = DateTime.UtcNow;
        var expiredSearches = Enumerable.Range(0, 501)
            .Select(index => CreateCompletedSearch(now.AddDays(-2).AddSeconds(index)))
            .ToList();
        var retainedSearches = Enumerable.Range(0, 2)
            .Select(index => CreateCompletedSearch(now.AddMinutes(-index)))
            .ToList();
        await using (var context = new SearchDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
            context.Searches.AddRange(expiredSearches.Concat(retainedSearches));
            await context.SaveChangesAsync();
        }

        commandInterceptor.Commands.Clear();
        var deletedSearches = new ConcurrentQueue<slskd.Search.Search>();
        using var service = new SearchService(
            CreateSearchHub(deletes: deletedSearches).Object,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            Mock.Of<ISoulseekClient>(),
            new SearchDbContextFactory(options),
            Mock.Of<ISoulseekSafetyLimiter>());

        var deletedCount = await service.CleanupAsync(maxAgeDays: 1);

        Assert.Equal(501, deletedCount);
        Assert.Equal(
            expiredSearches.Select(search => search.Id).OrderBy(id => id),
            deletedSearches.Select(search => search.Id).OrderBy(id => id));
        Assert.All(deletedSearches, search => Assert.Empty(search.Responses));
        Assert.Equal(
            3,
            commandInterceptor.Commands.Count(command =>
                command.StartsWith("DELETE FROM \"Searches\"", StringComparison.Ordinal)));
        await using var verifyContext = new SearchDbContext(options);
        Assert.Equal(
            retainedSearches.Select(search => search.Id).OrderBy(id => id),
            await verifyContext.Searches
                .AsNoTracking()
                .OrderBy(search => search.Id)
                .Select(search => search.Id)
                .ToListAsync());
    }

    [Fact]
    public async Task CleanupAsync_WithCountLimit_DeletesOnlyOldestExcessSearches()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<SearchDbContext>()
            .UseSqlite(connection)
            .Options;
        var startedAt = DateTime.UtcNow.AddHours(-1);
        var searches = Enumerable.Range(0, 301)
            .Select(index => CreateCompletedSearch(startedAt.AddSeconds(index)))
            .ToList();
        await using (var context = new SearchDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
            context.Searches.AddRange(searches);
            await context.SaveChangesAsync();
        }

        using var service = new SearchService(
            CreateSearchHub().Object,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            Mock.Of<ISoulseekClient>(),
            new SearchDbContextFactory(options),
            Mock.Of<ISoulseekSafetyLimiter>());

        var deletedCount = await service.CleanupAsync(maxCount: 101);

        Assert.Equal(200, deletedCount);
        await using var verifyContext = new SearchDbContext(options);
        Assert.Equal(
            searches.Skip(200).Select(search => search.Id),
            await verifyContext.Searches
                .AsNoTracking()
                .OrderBy(search => search.StartedAt)
                .ThenBy(search => search.Id)
                .Select(search => search.Id)
                .ToListAsync());
    }

    private static SearchService CreateService()
    {
        return new SearchService(
            Mock.Of<IHubContext<SearchHub>>(),
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            Mock.Of<ISoulseekClient>(),
            Mock.Of<IDbContextFactory<SearchDbContext>>(),
            Mock.Of<ISoulseekSafetyLimiter>());
    }

    private static Mock<IHubContext<SearchHub>> CreateSearchHub(
        ConcurrentQueue<slskd.Search.Search>? updates = null,
        ConcurrentQueue<slskd.Search.Search>? deletes = null)
    {
        var clientProxy = new Mock<IClientProxy>();
        clientProxy
            .Setup(client => client.SendCoreAsync(
                It.IsAny<string>(),
                It.IsAny<object?[]>(),
                It.IsAny<CancellationToken>()))
            .Callback<string, object?[], CancellationToken>((method, arguments, _) =>
            {
                if (
                    updates != null
                    && method == SearchHubMethods.Update
                    && arguments.FirstOrDefault() is slskd.Search.Search search
                )
                {
                    updates.Enqueue(search);
                }

                if (
                    deletes != null
                    && method == SearchHubMethods.Delete
                    && arguments.FirstOrDefault() is slskd.Search.Search deletedSearch
                )
                {
                    deletes.Enqueue(deletedSearch);
                }
            })
            .Returns(Task.CompletedTask);

        var clients = new Mock<IHubClients>();
        clients.Setup(c => c.All).Returns(clientProxy.Object);

        var hub = new Mock<IHubContext<SearchHub>>();
        hub.Setup(h => h.Clients).Returns(clients.Object);
        return hub;
    }

    private static slskd.Search.Search CreateCompletedSearch(DateTime startedAt)
    {
        return new slskd.Search.Search
        {
            Id = Guid.NewGuid(),
            EndedAt = startedAt.AddSeconds(1),
            SearchText = "retained search",
            StartedAt = startedAt,
            State = SearchStates.Completed,
        };
    }

    private static ConcurrentDictionary<Guid, CancellationTokenSource> GetCancellationTokens(SearchService service)
    {
        var property = typeof(SearchService).GetProperty(
            "CancellationTokens",
            BindingFlags.Instance | BindingFlags.NonPublic);

        return Assert.IsType<ConcurrentDictionary<Guid, CancellationTokenSource>>(property?.GetValue(service));
    }

    private static async Task<bool> WaitUntilAsync(Func<bool> condition, int attempts, int delayMs)
    {
        for (var attempt = 0; attempt < attempts; attempt++)
        {
            if (condition())
            {
                return true;
            }

            await Task.Delay(delayMs);
        }

        return condition();
    }

    private sealed class SearchDbContextFactory : IDbContextFactory<SearchDbContext>
    {
        private readonly DbContextOptions<SearchDbContext> _options;

        public SearchDbContextFactory(DbContextOptions<SearchDbContext> options)
        {
            _options = options;
        }

        public SearchDbContext CreateDbContext() => new(_options);

        public ValueTask<SearchDbContext> CreateDbContextAsync(CancellationToken cancellationToken = default) =>
            ValueTask.FromResult(CreateDbContext());
    }

    private sealed class RecordingCommandInterceptor : DbCommandInterceptor
    {
        public List<string> Commands { get; } = new();

        public override InterceptionResult<int> NonQueryExecuting(
            DbCommand command,
            CommandEventData eventData,
            InterceptionResult<int> result)
        {
            Commands.Add(command.CommandText);
            return base.NonQueryExecuting(command, eventData, result);
        }

        public override ValueTask<InterceptionResult<int>> NonQueryExecutingAsync(
            DbCommand command,
            CommandEventData eventData,
            InterceptionResult<int> result,
            CancellationToken cancellationToken = default)
        {
            Commands.Add(command.CommandText);
            return ValueTask.FromResult(result);
        }
    }

    private sealed class CapturingSink : ILogEventSink
    {
        public List<LogEvent> Events { get; } = [];

        public void Emit(LogEvent logEvent) => Events.Add(logEvent);
    }
}
