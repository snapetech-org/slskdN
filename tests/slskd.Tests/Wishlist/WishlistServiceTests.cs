// <copyright file="WishlistServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Tests.Wishlist;

using System;
using System.Collections.Generic;
using System.Linq.Expressions;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using slskd.Search;
using slskd.Wishlist;
using Xunit;
using SlskdSearch = slskd.Search.Search;
using SearchOptions = Soulseek.SearchOptions;
using SearchQuery = Soulseek.SearchQuery;
using SearchScope = Soulseek.SearchScope;
using SearchStates = Soulseek.SearchStates;

public class WishlistServiceTests
{
    [Fact]
    public async Task Ignored_results_are_scoped_to_the_wishlist_peer_and_directory()
    {
        var connectionString = $"Data Source=file:wishlist-ignore-{Guid.NewGuid():N}?mode=memory&cache=shared";
        await using var keeper = new SqliteConnection(connectionString);
        await keeper.OpenAsync();
        var options = new DbContextOptionsBuilder<WishlistDbContext>().UseSqlite(connectionString).Options;
        var factory = new TestWishlistDbContextFactory(options);
        var wishlistItemId = Guid.NewGuid();

        await using (var context = factory.CreateDbContext())
        {
            await context.Database.EnsureCreatedAsync();
            context.WishlistItems.Add(new WishlistItem { Id = wishlistItemId, SearchText = "album" });
            await context.SaveChangesAsync();
        }

        var service = new WishlistService(factory, null!, new CompletingSearchService(), null!, null!, null!, null!);
        var first = await service.IgnoreResultAsync(wishlistItemId, "peer", @"Music\Artist\Album\");
        var duplicate = await service.IgnoreResultAsync(wishlistItemId, "peer", "Music/Artist/Album");
        var rules = await service.ListIgnoredResultsAsync(wishlistItemId);

        Assert.Equal(first.Id, duplicate.Id);
        Assert.Single(rules);
        Assert.Equal("Music/Artist/Album", rules[0].Directory);
        await service.DeleteIgnoredResultAsync(wishlistItemId, first.Id);
        Assert.Empty(await service.ListIgnoredResultsAsync(wishlistItemId));
    }

    [Fact]
    public async Task RunSearchAsync_preserves_filter_edits_saved_while_search_is_running()
    {
        var connectionString = $"Data Source=file:wishlist-{Guid.NewGuid():N}?mode=memory&cache=shared";
        await using var keeper = new SqliteConnection(connectionString);
        await keeper.OpenAsync();

        var options = new DbContextOptionsBuilder<WishlistDbContext>()
            .UseSqlite(connectionString)
            .Options;
        var factory = new TestWishlistDbContextFactory(options);

        await using (var context = factory.CreateDbContext())
        {
            await context.Database.EnsureCreatedAsync();
            context.WishlistItems.Add(new WishlistItem
            {
                Id = Guid.Parse("11111111-1111-1111-1111-111111111111"),
                SearchText = "rare album",
                Filter = "flac",
                Enabled = true,
                AutoDownload = false,
                MaxResults = 100,
                CreatedAt = DateTime.UtcNow,
            });
            await context.SaveChangesAsync();
        }

        var searchService = new CompletingSearchService();
        var service = new WishlistService(factory, null!, searchService, null!, null!, null!, null!);
        var runSearch = service.RunSearchAsync(Guid.Parse("11111111-1111-1111-1111-111111111111"));

        await searchService.Started.Task;

        await using (var context = factory.CreateDbContext())
        {
            var item = await context.WishlistItems.SingleAsync();
            item.Filter = "mp3";
            await context.SaveChangesAsync();
        }

        await runSearch;

        await using (var context = factory.CreateDbContext())
        {
            var item = await context.WishlistItems.SingleAsync();
            Assert.Equal("mp3", item.Filter);
            Assert.Equal(1, item.TotalSearchCount);
        }
    }

    private sealed class TestWishlistDbContextFactory : IDbContextFactory<WishlistDbContext>
    {
        public TestWishlistDbContextFactory(DbContextOptions<WishlistDbContext> options)
        {
            Options = options;
        }

        private DbContextOptions<WishlistDbContext> Options { get; }

        public WishlistDbContext CreateDbContext() => new(Options);
    }

    private sealed class CompletingSearchService : ISearchService
    {
        private SlskdSearch? search;

        public TaskCompletionSource Started { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

        public Task DeleteAsync(SlskdSearch search) => Task.CompletedTask;

        public Task<SlskdSearch?> FindAsync(Expression<Func<SlskdSearch, bool>> expression, bool includeResponses = false)
        {
            return Task.FromResult(search);
        }

        public Task<List<SlskdSearch>> ListAsync(
            Expression<Func<SlskdSearch, bool>>? expression = null,
            int limit = 0,
            int offset = 0,
            string? source = null,
            DateTime? afterStartedAt = null,
            Guid? afterId = null)
        {
            return Task.FromResult(new List<SlskdSearch>());
        }

        public void Update(SlskdSearch search)
        {
        }

        public Task<SlskdSearch> StartAsync(
            Guid id,
            SearchQuery query,
            SearchScope scope,
            SearchOptions? options = null,
            List<string>? requestedProviders = null)
        {
            return StartAsync(id, query, scope, options, requestedProviders, safetySource: "user");
        }

        public Task<SlskdSearch> StartAsync(
            Guid id,
            SearchQuery query,
            SearchScope scope,
            SearchOptions? options,
            List<string>? requestedProviders,
            string safetySource,
            Guid? wishlistItemId = null)
        {
            search = new SlskdSearch
            {
                Id = id,
                SearchText = query.SearchText,
                Source = safetySource,
                StartedAt = DateTime.UtcNow,
                State = SearchStates.Completed,
                WishlistItemId = wishlistItemId,
            };
            Started.TrySetResult();
            return Task.FromResult(search);
        }

        public bool TryCancel(Guid id) => false;

        public Task<int> PruneAsync(int age) => Task.FromResult(0);

        public Task<int> DeleteAllAsync() => Task.FromResult(0);

        public Task<int> CleanupAsync(int maxAgeDays = 0, int maxCount = 0) => Task.FromResult(0);

        public Task<List<SlskdSearch>> GetByWishlistItemIdAsync(Guid wishlistItemId, int limit = 50)
        {
            return Task.FromResult(new List<SlskdSearch>());
        }

        public void Dispose()
        {
        }
    }
}
