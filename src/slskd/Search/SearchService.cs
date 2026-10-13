// <copyright file="SearchService.cs" company="slskd Team">
//     Copyright (c) slskd Team. All rights reserved.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU Affero General Public License as published
//     by the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
//
//     This program is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU Affero General Public License for more details.
//
//     You should have received a copy of the GNU Affero General Public License
//     along with this program.  If not, see https://www.gnu.org/licenses/.
// </copyright>

// <copyright file="SearchService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;
using slskd.Telemetry;
using System.Diagnostics;

namespace slskd.Search
{
    using System;
    using System.Collections.Concurrent;
    using System.Collections.Generic;
    using System.Linq;
    using System.Linq.Expressions;
    using System.Threading;
    using System.Threading.Tasks;
    using Microsoft.AspNetCore.SignalR;
    using Microsoft.EntityFrameworkCore;
    using Serilog;
    using Serilog.Events;
    using slskd.Common.Security;
    using slskd.Search.API;
    using slskd.Search.Providers;
    using Soulseek;
    using SearchOptions = Soulseek.SearchOptions;
    using SearchQuery = Soulseek.SearchQuery;
    using SearchScope = Soulseek.SearchScope;
    using SearchStates = Soulseek.SearchStates;

    /// <summary>
    ///     Handles the lifecycle and persistence of searches.
    /// </summary>
    public interface ISearchService : IDisposable
    {
        /// <summary>
        ///     Deletes the specified search.
        /// </summary>
        /// <param name="search">The search to delete.</param>
        /// <returns>The operation context.</returns>
        Task DeleteAsync(Search search);

        /// <summary>
        ///     Finds a single search matching the specified <paramref name="expression"/>.
        /// </summary>
        /// <param name="expression">The expression to use to match searches.</param>
        /// <param name="includeResponses">A value indicating whether to include search responses in the result.</param>
        /// <returns>The found search, or default if not found.</returns>
        /// <exception cref="ArgumentException">Thrown when an expression is not supplied.</exception>
        Task<Search?> FindAsync(Expression<Func<Search, bool>> expression, bool includeResponses = false);

        /// <summary>
        ///     Returns a list of all completed and in-progress searches, with responses omitted, matching the optional <paramref name="expression"/>.
        /// </summary>
        /// <param name="expression">An optional expression used to match searches.</param>
        /// <param name="limit">Maximum number of searches to return (0 for unlimited, which is the default).</param>
        /// <param name="offset">Number of searches to skip (for pagination).</param>
        /// <param name="source">Optional source filter (e.g. "manual", "wishlist", "auto-replace").</param>
        /// <returns>The list of searches matching the specified expression, or all searches if no expression is specified.</returns>
        Task<List<Search>> ListAsync(Expression<Func<Search, bool>>? expression = null, int limit = 0, int offset = 0, string? source = null);

        /// <summary>
        ///     Updates the specified <paramref name="search"/>.
        /// </summary>
        /// <remark>
        ///     Round-trips the database; use accordingly.
        /// </remark>
        /// <param name="search">The search to update.</param>
        void Update(Search search);

        /// <summary>
        ///     Performs a search for the specified <paramref name="query"/> and <paramref name="scope"/>.
        /// </summary>
        /// <param name="id">A unique identifier for the search.</param>
        /// <param name="query">The search query.</param>
        /// <param name="scope">The search scope.</param>
        /// <param name="options">Search options.</param>
        /// <param name="requestedProviders">Optional list of provider names for Scene ↔ Pod Bridging (e.g., ["pod"], ["scene"]).</param>
        /// <returns>The completed search.</returns>
        Task<Search> StartAsync(Guid id, SearchQuery query, SearchScope scope, SearchOptions? options = null, List<string>? requestedProviders = null);

        /// <summary>
        ///     Performs a search for the specified <paramref name="query"/> and <paramref name="scope"/>, charging the safety limiter to the specified source.
        /// </summary>
        /// <param name="id">A unique identifier for the search.</param>
        /// <param name="query">The search query.</param>
        /// <param name="scope">The search scope.</param>
        /// <param name="options">Search options.</param>
        /// <param name="requestedProviders">Optional list of provider names for Scene ↔ Pod Bridging (e.g., ["pod"], ["scene"]).</param>
        /// <param name="safetySource">The safety-limiter source for this search producer.</param>
        /// <param name="wishlistItemId">Optional wishlist item ID that originated this search.</param>
        /// <returns>The completed search.</returns>
        Task<Search> StartAsync(Guid id, SearchQuery query, SearchScope scope, SearchOptions? options, List<string>? requestedProviders, string safetySource, Guid? wishlistItemId = null);

        /// <summary>
        ///     Cancels the search matching the specified <paramref name="id"/>, if it is in progress.
        /// </summary>
        /// <param name="id">The unique identifier for the search.</param>
        /// <returns>A value indicating whether the search was successfully cancelled.</returns>
        bool TryCancel(Guid id);

        /// <summary>
        ///     Removes <see cref="SearchStates.Completed"/> searches older than the specified <paramref name="age"/>.
        /// </summary>
        /// <param name="age">The age after which records are eligible for pruning, in minutes.</param>
        /// <returns>The number of pruned records.</returns>
        Task<int> PruneAsync(int age);

        /// <summary>
        ///     Deletes all completed searches.
        /// </summary>
        /// <returns>The number of deleted searches.</returns>
        Task<int> DeleteAllAsync();

        /// <summary>
        ///     Deletes old searches based on retention policies.
        /// </summary>
        /// <param name="maxAgeDays">Delete searches older than this many days (0 = no age limit).</param>
        /// <param name="maxCount">Keep at most this many searches (0 = no count limit).</param>
        /// <returns>The number of deleted searches.</returns>
        Task<int> CleanupAsync(int maxAgeDays = 0, int maxCount = 0);

        /// <summary>
        ///     Gets searches linked to a wishlist item.
        /// </summary>
        /// <param name="wishlistItemId">The wishlist item ID.</param>
        /// <param name="limit">Maximum number of searches to return.</param>
        /// <returns>The list of searches linked to the wishlist item.</returns>
        Task<List<Search>> GetByWishlistItemIdAsync(Guid wishlistItemId, int limit = 50);
    }

    /// <summary>
    ///     Handles the lifecycle and persistence of searches.
    /// </summary>
    public sealed partial class SearchService : ISearchService
    {
        private const int RetentionCleanupBatchSize = 250;
        private const int SearchProgressIntervalMs = 1_000;
        private readonly object _searchPersistenceSync = new();

        /// <summary>
        ///     Initializes a new instance of the <see cref="SearchService"/> class.
        /// </summary>
        /// <param name="searchHub"></param>
        /// <param name="optionsMonitor"></param>
        /// <param name="soulseekClient"></param>
        /// <param name="contextFactory">The database context to use.</param>
        /// <param name="safetyLimiter">The Soulseek safety limiter (H-08).</param>
        /// <param name="eventBus">The event bus for raising search events (optional).</param>
        /// <param name="disasterModeCoordinator">The disaster-mode coordinator for mesh-backed search fallback.</param>
        /// <param name="meshSearchService">The mesh search service for disaster-mode search execution.</param>
        /// <param name="meshOverlaySearchService">The overlay search service for DHT-backed mesh search.</param>
        /// <param name="trafficObserver">The optional traffic observer for bridged search capture.</param>
        /// <param name="searchProviders">Optional explicit search provider set.</param>
        public SearchService(
            IHubContext<SearchHub> searchHub,
            IOptionsMonitor<Options> optionsMonitor,
            ISoulseekClient soulseekClient,
            IDbContextFactory<SearchDbContext> contextFactory,
            slskd.Common.Security.ISoulseekSafetyLimiter safetyLimiter,
            slskd.Events.EventBus? eventBus = null,
            slskd.VirtualSoulfind.DisasterMode.IDisasterModeCoordinator? disasterModeCoordinator = null,
            slskd.VirtualSoulfind.DisasterMode.IMeshSearchService? meshSearchService = null,
            slskd.DhtRendezvous.Search.IMeshOverlaySearchService? meshOverlaySearchService = null,
            slskd.VirtualSoulfind.Capture.ITrafficObserver? trafficObserver = null,
            IEnumerable<ISearchProvider>? searchProviders = null)
        {
            SearchHub = searchHub;
            OptionsMonitor = optionsMonitor;
            Client = soulseekClient;
            ContextFactory = contextFactory;
            SafetyLimiter = safetyLimiter;
            EventBus = eventBus;
            DisasterModeCoordinator = disasterModeCoordinator;
            MeshSearchService = meshSearchService;
            MeshOverlaySearchService = meshOverlaySearchService;
            TrafficObserver = trafficObserver;
            SearchProviders = searchProviders?.ToList() ?? new List<ISearchProvider>();
        }

        private ConcurrentDictionary<Guid, CancellationTokenSource> CancellationTokens { get; }
            = new ConcurrentDictionary<Guid, CancellationTokenSource>();

        private ISoulseekClient Client { get; }
        private IDbContextFactory<SearchDbContext> ContextFactory { get; }
        private slskd.Events.EventBus? EventBus { get; }
        private ILogger Log { get; set; } = Serilog.Log.ForContext<Application>();
        private IOptionsMonitor<Options> OptionsMonitor { get; }
        private slskd.Common.Security.ISoulseekSafetyLimiter SafetyLimiter { get; }
        private IHubContext<SearchHub> SearchHub { get; set; }
        private slskd.VirtualSoulfind.DisasterMode.IDisasterModeCoordinator? DisasterModeCoordinator { get; }
        private slskd.VirtualSoulfind.DisasterMode.IMeshSearchService? MeshSearchService { get; }
        private slskd.DhtRendezvous.Search.IMeshOverlaySearchService? MeshOverlaySearchService { get; }
        private slskd.VirtualSoulfind.Capture.ITrafficObserver? TrafficObserver { get; }
        private List<ISearchProvider> SearchProviders { get; }

        public void Dispose()
        {
            foreach (var id in CancellationTokens.Keys.ToList())
            {
                ReleaseCancellationToken(id);
            }

            GC.SuppressFinalize(this);
        }

        /// <summary>
        ///     Deletes the specified search.
        /// </summary>
        /// <param name="search">The search to delete.</param>
        /// <returns>The operation context.</returns>
        public Task DeleteAsync(Search search)
        {
            if (search == default)
            {
                throw new ArgumentNullException(nameof(search));
            }

            TryCancel(search.Id);
            return DoDeleteAsync(search);

            async Task DoDeleteAsync(Search search)
            {
                Task? broadcast = null;
                lock (_searchPersistenceSync)
                {
                    using var context = ContextFactory.CreateDbContext();
                    var deleted = context.Searches
                        .Where(candidate => candidate.Id == search.Id)
                        .ExecuteDelete();

                    if (deleted > 0)
                    {
                        broadcast = SearchHub.BroadcastDeleteAsync(search);
                    }
                }

                if (broadcast != null)
                {
                    await broadcast.ConfigureAwait(false);
                }
            }
        }

        /// <summary>
        ///     Finds a single search matching the specified <paramref name="expression"/>.
        /// </summary>
        /// <param name="expression">The expression to use to match searches.</param>
        /// <param name="includeResponses">A value indicating whether to include search responses in the result.</param>
        /// <returns>The found search, or default if not found.</returns>
        /// <exception cref="ArgumentException">Thrown when an expression is not supplied.</exception>
        public Task<Search?> FindAsync(Expression<Func<Search, bool>> expression, bool includeResponses = false)
        {
            if (expression == default)
            {
                throw new ArgumentException("An expression must be supplied.", nameof(expression));
            }

            using var context = ContextFactory.CreateDbContext();

            var selector = context.Searches
                .AsNoTracking()
                .Where(expression);

            if (!includeResponses)
            {
                selector = selector.WithoutResponses();
            }

            return selector.FirstOrDefaultAsync();
        }

        /// <summary>
        ///     Returns a list of all completed and in-progress searches, with responses omitted, matching the optional <paramref name="expression"/>.
        /// </summary>
        /// <param name="expression">An optional expression used to match searches.</param>
        /// <param name="limit">Maximum number of searches to return (0 for unlimited, which is the default).</param>
        /// <param name="offset">Number of searches to skip (for pagination).</param>
        /// <param name="source">Optional source filter (e.g. "manual", "wishlist", "auto-replace").</param>
        /// <returns>The list of searches matching the specified expression, or all searches if no expression is specified.</returns>
        public Task<List<Search>> ListAsync(Expression<Func<Search, bool>>? expression = null, int limit = 0, int offset = 0, string? source = null)
        {
            expression ??= s => true;
            using var context = ContextFactory.CreateDbContext();

            var query = context.Searches
                .AsNoTracking()
                .Where(expression);

            if (!string.IsNullOrWhiteSpace(source))
            {
                var sourceFilter = source!.Trim().ToLowerInvariant();
                query = query.Where(s => s.Source.ToLowerInvariant() == sourceFilter);
            }

            query = query
                .OrderByDescending(s => s.StartedAt)
                .WithoutResponses();

            if (offset > 0)
            {
                query = query.Skip(offset);
            }

            if (limit > 0)
            {
                query = query.Take(limit);
            }

            return query.ToListAsync();
        }

        /// <summary>
        ///     Updates the specified <paramref name="search"/>.
        /// </summary>
        /// <param name="search">The search to update.</param>
        public void Update(Search search)
        {
            lock (_searchPersistenceSync)
            {
                PersistSearchIfPresent(search);
            }
        }

        private bool PersistSearchIfPresent(Search search)
        {
            using var context = ContextFactory.CreateDbContext();
            var responsesJson = search.ResponsesJson;

            return context.Searches
                .Where(candidate => candidate.Id == search.Id)
                .ExecuteUpdate(update => update
                    .SetProperty(candidate => candidate.EndedAt, search.EndedAt)
                    .SetProperty(candidate => candidate.FileCount, search.FileCount)
                    .SetProperty(candidate => candidate.LockedFileCount, search.LockedFileCount)
                    .SetProperty(candidate => candidate.ResponseCount, search.ResponseCount)
                    .SetProperty(candidate => candidate.ResponsesJson, responsesJson)
                    .SetProperty(candidate => candidate.State, search.State)) == 1;
        }

        private Task? PersistAndBroadcastSearchUpdate(Search search)
        {
            lock (_searchPersistenceSync)
            {
                if (!PersistSearchIfPresent(search))
                {
                    return null;
                }

                return SearchHub.BroadcastUpdateAsync(search);
            }
        }

        private Task? BroadcastSearchUpdateIfPresent(Search search)
        {
            lock (_searchPersistenceSync)
            {
                using var context = ContextFactory.CreateDbContext();
                if (!context.Searches.Any(candidate => candidate.Id == search.Id))
                {
                    return null;
                }

                return SearchHub.BroadcastUpdateAsync(search);
            }
        }

        private async Task ObserveSearchBroadcastAsync(Task broadcast, Guid searchId)
        {
            try
            {
                await broadcast.ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                Log.Error(
                    "Failed to broadcast update for search {SearchId}: {Exception}",
                    searchId,
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
            }
        }

        /// <summary>
        ///     Performs a search for the specified <paramref name="query"/> and <paramref name="scope"/>.
        /// </summary>
        /// <param name="id">A unique identifier for the search.</param>
        /// <param name="query">The search query.</param>
        /// <param name="scope">The search scope.</param>
        /// <param name="options">Search options.</param>
        /// <param name="requestedProviders">Optional search providers to limit execution to.</param>
        /// <returns>The completed search.</returns>
        public Task<Search> StartAsync(Guid id, SearchQuery query, SearchScope scope, SearchOptions? options = null, List<string>? requestedProviders = null)
        {
            return StartAsync(id, query, scope, options, requestedProviders, safetySource: "user");
        }

        public async Task<Search> StartAsync(Guid id, SearchQuery query, SearchScope scope, SearchOptions? options, List<string>? requestedProviders, string safetySource, Guid? wishlistItemId = null)
        {
            var safeQuery = LoggingSanitizer.SanitizeQueryText(query.SearchText);
            using var activity = SearchActivitySource.Source.StartActivity("search.start");
            activity?.SetTag("search.id", id.ToString());
            activity?.SetTag("search.query", safeQuery);
            activity?.SetTag("search.scope", scope.ToString());
            activity?.SetTag("search.providers", requestedProviders != null ? string.Join(",", requestedProviders) : "all");
            activity?.SetTag("search.safety_source", safetySource);

            // Check if Scene ↔ Pod Bridging is enabled
            var scenePodBridgeEnabled = OptionsMonitor.CurrentValue.Feature.ScenePodBridge;
            if (scenePodBridgeEnabled && SearchProviders.Any())
            {
                // Filter providers based on request, or use all if not specified
                var providersToUse = requestedProviders != null && requestedProviders.Any()
                    ? SearchProviders.Where(p => requestedProviders.Contains(p.Name)).ToList()
                    : SearchProviders;

                if (providersToUse.Any())
                {
                    return await StartBridgedSearchAsync(id, query, scope, options, providersToUse, safetySource, wishlistItemId);
                }
            }

            // H-08: Check Soulseek safety caps before initiating search
            if (!SafetyLimiter.TryConsumeSearch(safetySource))
            {
                var message = $"Search rate limit exceeded. See Soulseek safety configuration.";
                Log.Warning("[SAFETY] Search rejected for source={Source} query='{Query}': {Message}",
                    safetySource, safeQuery, LoggingSanitizer.SanitizeQueryText(message));

                throw new InvalidOperationException(message);
            }

            // T-823: Check if the legacy fallback is active; default behavior remains Soulseek + mesh together.
            if (DisasterModeCoordinator?.IsDisasterModeActive == true)
            {
                return await StartMeshOnlySearchAsync(id, query, options, safetySource, wishlistItemId);
            }

            var token = Client.GetNextToken();

            var cancellationTokenSource = new CancellationTokenSource();
            var searchCancellationToken = cancellationTokenSource.Token;
            CancellationTokens.TryAdd(id, cancellationTokenSource);

#pragma warning disable CA2000 // Ownership transfers to the search background task, with launch-failure cleanup in the surrounding catch.
            var progressRateLimiter = new RateLimiter(SearchProgressIntervalMs);
#pragma warning restore CA2000
            var backgroundOwnsResources = false;

            // initialize the search record, save it to the database, and broadcast the creation
            // we do this so the UI has some feedback to show to the user that we've gotten their request
            var search = new Search()
            {
                SearchText = query.SearchText,
                Token = token,
                Id = id,
                State = SearchStates.Requested,
                StartedAt = DateTime.UtcNow,
                Source = safetySource,
                WishlistItemId = wishlistItemId,
            };

            bool searchCreated = false;
            bool searchBroadcasted = false;

            try
            {
                Task createBroadcast;
                lock (_searchPersistenceSync)
                {
                    using var context = ContextFactory.CreateDbContext();
                    context.Add(search);
                    context.SaveChanges();

                    searchCreated = true;
                    createBroadcast = SearchHub.BroadcastCreateAsync(search);
                }

                await createBroadcast.ConfigureAwait(false);

                searchBroadcasted = true;

                // initialize the list of responses that we'll use to accumulate them
                // populated by the responseHandler we pass to SearchAsync
                List<SearchResponse> responses = new();
                IReadOnlyList<Response> latestMeshResponses = Array.Empty<Response>();
                object responseLock = new();
                int soulseekResponseCount = 0;
                int soulseekFileCount = 0;
                int soulseekLockedFileCount = 0;

                options ??= new SearchOptions();
                Func<IReadOnlyList<Response>, IReadOnlyList<Response>> applyWishlistPolicy = mergedResponses =>
                    wishlistItemId.HasValue
                        ? WishlistSearchPolicy.FilterResponses(mergedResponses, query.SearchText, options.FileFilter)
                        : mergedResponses;
                var smartFallbackMayStart = SmartSearchFallback.IsEnabledForSource(safetySource)
                    && SmartSearchFallback.CreateQueries(query.SearchText).Count > 0;
                options = options.WithActions(
                    stateChanged: (args) =>
                    {
                        // this logic is executed by Soulseek.NET upon each transition of the searcn, including the final
                        // transition to Completed. if for some reason something goes wrong, we won't see the final Completed
                        // transition, we should instead see the task below throw, in which case it will become
                        // faulted and we'll set the Completed flag manually in the catch block
                        var deferLowResultCompletion = smartFallbackMayStart
                            && args.Search.State.HasFlag(SearchStates.Completed)
                            && SmartSearchFallback.NeedsFallback(
                                args.Search.ResponseCount,
                                args.Search.FileCount + args.Search.LockedFileCount,
                                options.ResponseLimit,
                                options.FileLimit);

                        if (!deferLowResultCompletion)
                        {
                            search = search.WithSoulseekSearch(args.Search);
                            if (PersistAndBroadcastSearchUpdate(search) is { } updateBroadcast)
                            {
                                _ = ObserveSearchBroadcastAsync(updateBroadcast, id);
                            }
                        }

                        Log.Debug("Search for '{Query}' state changed: {State} (id: {Id})", safeQuery, search.State, id);
                    },
                    responseReceived: (args) => progressRateLimiter.Invoke(() =>
                    {
                        int responseCount;
                        int fileCount;
                        int lockedFileCount;
                        IReadOnlyList<Response> meshSnapshot;

                        lock (responseLock)
                        {
                            responseCount = soulseekResponseCount;
                            fileCount = soulseekFileCount;
                            lockedFileCount = soulseekLockedFileCount;
                            meshSnapshot = latestMeshResponses;
                        }

                        if (meshSnapshot.Count > 0)
                        {
                            List<SearchResponse> soulseekSnapshot;

                            lock (responseLock)
                            {
                                soulseekSnapshot = responses.ToList();
                            }

                            var merged = applyWishlistPolicy(MergeSearchResponses(soulseekSnapshot, meshSnapshot));
                            ApplyResponseSummary(search, merged);
                        }
                        else
                        {
                            search.ResponseCount = responseCount;
                            search.FileCount = fileCount;
                            search.LockedFileCount = lockedFileCount;
                        }

                        // Progress is transient because responses remain in memory until
                        // completion. Avoid writing an incomplete row for every update.
                        if (BroadcastSearchUpdateIfPresent(search) is { } progressBroadcast)
                        {
                            _ = ObserveSearchBroadcastAsync(progressBroadcast, id);
                        }
                    }));

                // initiate the search. this can throw at invocation if there's a problem with
                // the client state (e.g. disconnected) or a problem with the search (e.g. no terms)
                var soulseekSearchTask = RunSoulseekSearchAsync(
                    query,
                    scope,
                    token,
                    options,
                    response =>
                    {
                        lock (responseLock)
                        {
                            responses.Add(response);
                            soulseekResponseCount++;
                            soulseekFileCount += response.FileCount;
                            soulseekLockedFileCount += response.LockedFileCount;
                        }
                    },
                    searchCancellationToken,
                    safetySource,
                    () => smartFallbackMayStart = false);

                // search looks ok so far; let the rest of the logic run asynchronously
                // on a background thread. this logic needs to clean up after itself and
                // update the search record to accurately reflect the final state
                var finalizationTask = Task.Run(async () =>
                {
                    try
                    {
                        // Start mesh overlay search in parallel when enabled (hybrid mode)
                        // MeshParallelSearch flag or VirtualSoulfind.MeshSearch.Enabled can enable it
                        var meshEnabled = OptionsMonitor.CurrentValue.Feature.MeshParallelSearch
                            || OptionsMonitor.CurrentValue.VirtualSoulfind?.MeshSearch?.Enabled == true;
                        var meshTask = (meshEnabled && MeshOverlaySearchService != null)
                            ? MeshOverlaySearchService.SearchAsync(query.SearchText, searchCancellationToken)
                            : Task.FromResult((IReadOnlyList<Response>)Array.Empty<Response>());

                        var meshPublicationTask = PublishMeshResultsWhenReadyAsync(meshTask);

                        try
                        {
                            var soulseekSearch = await soulseekSearchTask;
                            search = search.WithSoulseekSearch(soulseekSearch);

                            Log.Debug("Search for '{Query}' ended normally (id: {Id})", safeQuery, id);
                        }
                        catch (Exception ex)
                        {
                            Log.Debug("Search for '{Query}' threw {Exception}: {Message} (id: {Id})",
                                safeQuery, ex.GetType(), LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()), id);

                            // OperationCanceledException might be thrown somewhere deeper, and we don't want that to count.
                            // User-cancelled searches trip the search token; host shutdown trips the app lifecycle flag.
                            if (IsExpectedSearchCancellation(ex, searchCancellationToken, Application.IsShuttingDown)
                                || IsExpectedSearchRuntimeShutdownFailure(ex, Application.IsShuttingDown))
                            {
                                var reason = Application.IsShuttingDown ? " during shutdown" : string.Empty;
                                Log.Information("Search for '{Query}' was cancelled{Reason}", safeQuery, reason);
                                search.State = SearchStates.Completed | SearchStates.Cancelled;
                            }
                            else if (IsSearchUnavailableDuringLogin(ex))
                            {
                                Log.Warning("Search for '{Query}' deferred because Soulseek is still logging in: {Message}",
                                    safeQuery, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                                search.State = SearchStates.Completed | SearchStates.Cancelled;
                            }
                            else
                            {
                                Log.Error("Failed to execute search for '{Query}': {Exception}",
                                    safeQuery, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                                search.State = SearchStates.Completed | SearchStates.Errored;
                            }
                        }

                        // No more Soulseek responses can arrive after the search task
                        // completes. Drain progress before the canonical save.
                        progressRateLimiter.Dispose();

                        // Await mesh overlay results (runs in parallel with Soulseek; bounded by per-peer timeout)
                        var meshResponses = await meshPublicationTask;

                        // it shouldn't be possible for this to happen, as the StateChanged callback is called before the
                        // SearchAsync() method returns, and we will have already updated the record at that time. if for
                        // some extremely odd reason that doesn't happen, make sure the record is persisted the final time
                        // with the Completed flag set to avoid it getting "stuck"
                        if (!search.State.HasFlag(SearchStates.Completed))
                        {
                            search.State |= SearchStates.Completed;
                        }

                        search.EndedAt = DateTime.UtcNow;

                        List<SearchResponse> soulseekSnapshot;
                        lock (responseLock)
                        {
                            soulseekSnapshot = responses.ToList();
                        }

                        var merged = applyWishlistPolicy(MergeSearchResponses(soulseekSnapshot, meshResponses));
                        search.Responses = merged;
                        search.ResponsesAvailable = true;
                        ApplyResponseSummary(search, merged);

                        var finalBroadcast = PersistAndBroadcastSearchUpdate(search);
                        if (finalBroadcast == null)
                        {
                            return;
                        }

                        // Raise event for passive FLAC discovery (HashDb will pick up FLAC files)
                        if (EventBus != null && soulseekSnapshot.Count > 0)
                        {
                            EventBus.Raise(new slskd.Events.SearchResponsesReceivedEvent
                            {
                                Responses = soulseekSnapshot,
                            });
                        }

                        // Notify traffic observer for Virtual Soulfind capture (Phase 6A: T-803)
                        if (TrafficObserver != null && soulseekSnapshot.Count > 0)
                        {
                            await NotifyTrafficObserverAsync(TrafficObserver, query.SearchText, soulseekSnapshot, Log, CancellationToken.None);
                        }

                        await finalBroadcast.ConfigureAwait(false);

                        Log.Debug("Search for '{Query}' finalized (id: {Id}): {Search}",
                            safeQuery, id, search with { SearchText = safeQuery, Responses = [] });
                        Log.Debug("Search for '{Query}' completed with {Responses} responses", safeQuery, search.ResponseCount);

                        var completionLog = safetySource == "user" || search.ResponseCount > 0
                            ? LogEventLevel.Information
                            : LogEventLevel.Debug;

                        Log.Write(
                            completionLog,
                            "Search completed: source={Source} query='{Query}' state={State} soulseekResponses={SoulseekResponses} meshResponses={MeshResponses} mergedResponses={MergedResponses} files={Files} durationMs={DurationMs}",
                            safetySource,
                            safeQuery,
                            search.State,
                            soulseekSnapshot.Count,
                            meshResponses.Count,
                            search.ResponseCount,
                            search.FileCount,
                            search.EndedAt.HasValue ? (long)(search.EndedAt.Value - search.StartedAt).TotalMilliseconds : 0);

                        async Task<IReadOnlyList<Response>> PublishMeshResultsWhenReadyAsync(Task<IReadOnlyList<Response>> pendingMeshTask)
                        {
                            IReadOnlyList<Response> meshResponses;
                            try
                            {
                                meshResponses = await pendingMeshTask;
                            }
                            catch (Exception ex)
                            {
                                Log.Debug("Mesh overlay search for '{Query}' failed: {Exception}",
                                    safeQuery, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                                meshResponses = Array.Empty<Response>();
                            }

                            if (meshResponses.Count == 0)
                            {
                                return meshResponses;
                            }

                            List<SearchResponse> soulseekSnapshot;
                            lock (responseLock)
                            {
                                latestMeshResponses = meshResponses;
                                soulseekSnapshot = responses.ToList();
                            }

                            var merged = applyWishlistPolicy(MergeSearchResponses(soulseekSnapshot, meshResponses));
                            search.Responses = merged;
                            search.ResponsesAvailable = true;
                            ApplyResponseSummary(search, merged);
                            var meshBroadcast = PersistAndBroadcastSearchUpdate(search);
                            if (meshBroadcast == null)
                            {
                                return meshResponses;
                            }

                            await meshBroadcast.ConfigureAwait(false);

                            Log.Debug(
                                "Published early mesh results for '{Query}' (id: {Id}): meshResponses={MeshResponses} mergedResponses={MergedResponses} files={Files}",
                                safeQuery,
                                id,
                                meshResponses.Count,
                                search.ResponseCount,
                                search.FileCount);

                            return meshResponses;
                        }
                    }
                    catch (Exception ex)
                    {
                        if (IsExpectedSearchFinalizationFailure(ex, Application.IsShuttingDown))
                        {
                            Log.Debug("Search finalization for '{Query}' stopped during shutdown: {Exception}",
                                safeQuery, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                            return;
                        }

                        // record may be left 'hanging' and will need to be cleaned up at the next boot; we tried to update but failed
                        Log.Error("Failed to finalize search for '{Query}': {Exception}",
                            safeQuery, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                    }
                    finally
                    {
                        progressRateLimiter.Dispose();
                        ReleaseCancellationToken(id);
                    }
                }, cancellationToken: CancellationToken.None);
                backgroundOwnsResources = true;
                _ = TaskObservation.Observe(
                    finalizationTask,
                    ex => Log.Warning("Search background task for '{Query}' failed (id: {Id}): {Exception}",
                        safeQuery, id, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString())));

                // broadcast and return the _newly created_ search; it will continue to be updated in the background
                if (BroadcastSearchUpdateIfPresent(search) is { } initialUpdateBroadcast)
                {
                    await initialUpdateBroadcast.ConfigureAwait(false);
                }

                return search;
            }
            catch (Exception ex)
            {
                if (!backgroundOwnsResources)
                {
                    progressRateLimiter.Dispose();
                    ReleaseCancellationToken(id);
                }

                // we'll end up here if the initial call throws for an ArgumentException, InvalidOperationException if
                // the app isn't connected, and a few other straightforward issues that arise before even requesting the search
                if (IsSearchUnavailableDuringLogin(ex))
                {
                    Log.Warning("Search {Search} deferred because Soulseek is still logging in: {Exception}",
                        new { query = safeQuery, scope, options }, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                }
                else
                {
                    Log.Error("Failed to execute search {Search}: {Exception}",
                        new { query = safeQuery, scope, options }, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                }

                // selectively 'undo' whatever actions we were able to take successfully
                if (searchCreated)
                {
                    search.State = SearchStates.Completed | SearchStates.Errored;
                    search.EndedAt = search.StartedAt;
                    var failureBroadcast = PersistAndBroadcastSearchUpdate(search);

                    if (searchBroadcasted && failureBroadcast != null)
                    {
                        await failureBroadcast.ConfigureAwait(false);
                    }
                }

                throw;
            }
        }

        internal static bool IsExpectedSearchCancellation(Exception exception, CancellationToken searchCancellationToken, bool applicationIsShuttingDown)
        {
            return exception is OperationCanceledException
                && (searchCancellationToken.IsCancellationRequested || applicationIsShuttingDown);
        }

        private Task<Soulseek.Search> RunSoulseekSearchAsync(
            SearchQuery query,
            SearchScope scope,
            int token,
            SearchOptions options,
            Action<SearchResponse> responseHandler,
            CancellationToken cancellationToken,
            string safetySource,
            Action fallbackStarted)
        {
            // Keep the initial invocation outside an async state machine so
            // launch-time validation/connection failures preserve StartAsync's
            // existing synchronous failure contract.
            var initialSearchTask = Client.SearchAsync(
                query,
                responseHandler,
                scope,
                token,
                options,
                cancellationToken);

            return ContinueSoulseekSearchAsync(
                initialSearchTask,
                query,
                scope,
                options,
                responseHandler,
                cancellationToken,
                safetySource,
                fallbackStarted);
        }

        private async Task<Soulseek.Search> ContinueSoulseekSearchAsync(
            Task<Soulseek.Search> initialSearchTask,
            SearchQuery query,
            SearchScope scope,
            SearchOptions options,
            Action<SearchResponse> responseHandler,
            CancellationToken cancellationToken,
            string safetySource,
            Action fallbackStarted)
        {
            var safeQuery = LoggingSanitizer.SanitizeQueryText(query.SearchText);
            var soulseekSearch = await initialSearchTask.ConfigureAwait(false);

            if (!SmartSearchFallback.IsEnabledForSource(safetySource) ||
                !SmartSearchFallback.NeedsFallback(
                    soulseekSearch.ResponseCount,
                    soulseekSearch.FileCount + soulseekSearch.LockedFileCount,
                    options.ResponseLimit,
                    options.FileLimit))
            {
                return soulseekSearch;
            }

            foreach (var fallbackText in SmartSearchFallback.CreateQueries(query.SearchText))
            {
                cancellationToken.ThrowIfCancellationRequested();

                if (!SafetyLimiter.TryConsumeSearch(safetySource))
                {
                    Log.Debug(
                        "Smart Wishlist fallback stopped by the Soulseek safety limiter for '{Query}'",
                        safeQuery);
                    break;
                }

                fallbackStarted();
                var fallbackQuery = SearchQuery.FromText(fallbackText);
                var fallbackOptions = options.WithSearchTimeout(
                    Math.Min(options.SearchTimeout, SmartSearchFallback.FallbackTimeoutMilliseconds));

                try
                {
                    Log.Information(
                        "Smart Wishlist fallback searching '{FallbackQuery}' after low-result query '{Query}' ({ResponseCount} responses, {FileCount} files)",
                        LoggingSanitizer.SanitizeQueryText(fallbackText),
                        safeQuery,
                        soulseekSearch.ResponseCount,
                        soulseekSearch.FileCount);

                    soulseekSearch = await Client.SearchAsync(
                        fallbackQuery,
                        responseHandler,
                        scope,
                        Client.GetNextToken(),
                        fallbackOptions,
                        cancellationToken).ConfigureAwait(false);

                    if (!SmartSearchFallback.NeedsFallback(
                            soulseekSearch.ResponseCount,
                            soulseekSearch.FileCount + soulseekSearch.LockedFileCount,
                            options.ResponseLimit,
                            options.FileLimit))
                    {
                        break;
                    }
                }
                catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
                {
                    throw;
                }
                catch (Exception ex)
                {
                    Log.Debug(
                        ex,
                        "Smart Wishlist fallback '{FallbackQuery}' failed after '{Query}': {Message}",
                        LoggingSanitizer.SanitizeQueryText(fallbackText),
                        safeQuery,
                        LoggingSanitizer.SanitizeQueryText(ex.Message));
                    break;
                }
            }

            return soulseekSearch;
        }

        internal static bool IsSearchUnavailableDuringLogin(Exception exception)
        {
            return exception is InvalidOperationException
                && exception.Message.Contains("must be connected and logged in", StringComparison.OrdinalIgnoreCase)
                && exception.Message.Contains("LoggingIn", StringComparison.OrdinalIgnoreCase);
        }

        internal static bool IsExpectedSearchFinalizationFailure(Exception exception, bool applicationIsShuttingDown)
            => applicationIsShuttingDown && exception is ObjectDisposedException;

        internal static bool IsExpectedSearchRuntimeShutdownFailure(Exception exception, bool applicationIsShuttingDown)
        {
            return applicationIsShuttingDown
                && exception is InvalidOperationException
                && exception.Message.Contains("lock is being disposed", StringComparison.OrdinalIgnoreCase);
        }

        internal static List<Response> MergeSearchResponses(IEnumerable<SearchResponse> soulseekResponses, IReadOnlyList<Response> meshResponses)
        {
            return SearchResponseMerger.Deduplicate(
                soulseekResponses.Select(r => Response.FromSoulseekSearchResponse(r)),
                meshResponses);
        }

        internal static void ApplyResponseSummary(Search search, IReadOnlyCollection<Response> responses)
        {
            search.ResponseCount = responses.Count;
            search.FileCount = responses.Sum(r => r.FileCount);
            search.LockedFileCount = responses.Sum(r => r.LockedFileCount);
        }

        internal static async Task NotifyTrafficObserverAsync(
            slskd.VirtualSoulfind.Capture.ITrafficObserver trafficObserver,
            string query,
            IEnumerable<SearchResponse> responses,
            ILogger log,
            CancellationToken cancellationToken)
        {
            foreach (var response in responses)
            {
                try
                {
                    await trafficObserver.OnSearchResultsAsync(query, response, cancellationToken).ConfigureAwait(false);
                }
                catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
                {
                    throw;
                }
                catch (Exception ex)
                {
                    log.Debug(
                        "Failed to notify traffic observer for search '{Query}': {Exception}",
                        LoggingSanitizer.SanitizeQueryText(query),
                        LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                }
            }
        }

        /// <summary>
        ///     Cancels the search matching the specified <paramref name="id"/>, if it is in progress.
        /// </summary>
        /// <param name="id">The unique identifier for the search.</param>
        /// <returns>A value indicating whether the search was successfully cancelled.</returns>
        public bool TryCancel(Guid id)
        {
            if (CancellationTokens.TryGetValue(id, out _))
            {
                ReleaseCancellationToken(id);
                return true;
            }

            return false;
        }

        /// <summary>
        ///     Removes <see cref="SearchStates.Completed"/> searches older than the specified <paramref name="age"/>.
        /// </summary>
        /// <param name="age">The age after which searches are eligible for pruning, in minutes.</param>
        /// <returns>The number of pruned records.</returns>
        public async Task<int> PruneAsync(int age)
        {
            try
            {
                using var context = ContextFactory.CreateDbContext();

                var cutoffDateTime = DateTime.UtcNow.AddMinutes(-age);

                // unlike other pruning operations, we don't care about state, since there's a 60 minute minimum
                // and searches are guaranteed to be at least 60 minutes old by the time they can be pruned, they will
                // be completed unless someone applied some rather dumb settings
                return await DeleteSearchesInBatchesAsync(
                    context,
                    context.Searches.Where(s => s.EndedAt.HasValue && s.EndedAt.Value < cutoffDateTime));
            }
            catch (Exception ex)
            {
                Log.Error("Failed to prune searches: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        /// <summary>
        ///     Deletes all completed searches.
        /// </summary>
        /// <returns>The number of deleted searches.</returns>
        public async Task<int> DeleteAllAsync()
        {
            try
            {
                using var context = ContextFactory.CreateDbContext();

                var deletedCount = await DeleteSearchesInBatchesAsync(
                    context,
                    context.Searches.Where(s => s.State.HasFlag(SearchStates.Completed)));

                Log.Information("Deleted {Count} searches", deletedCount);
                return deletedCount;
            }
            catch (Exception ex)
            {
                Log.Error("Failed to delete all searches: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        /// <summary>
        ///     Deletes old searches based on retention policies.
        /// </summary>
        /// <param name="maxAgeDays">Delete searches older than this many days (0 = no age limit).</param>
        /// <param name="maxCount">Keep at most this many searches (0 = no count limit).</param>
        /// <returns>The number of deleted searches.</returns>
        public async Task<int> CleanupAsync(int maxAgeDays = 0, int maxCount = 0)
        {
            try
            {
                using var context = ContextFactory.CreateDbContext();

                int deletedCount = 0;

                // Delete by age
                if (maxAgeDays > 0)
                {
                    var cutoff = DateTime.UtcNow.AddDays(-maxAgeDays);
                    var expiredCount = await DeleteSearchesInBatchesAsync(
                        context,
                        context.Searches.Where(s => s.State.HasFlag(SearchStates.Completed) && s.StartedAt < cutoff));

                    deletedCount += expiredCount;
                    if (expiredCount > 0)
                    {
                        Log.Information("Retention cleanup: deleted {Count} searches older than {Days} days", expiredCount, maxAgeDays);
                    }
                }

                // Delete by count (oldest first)
                if (maxCount > 0)
                {
                    var totalCount = await context.Searches
                        .CountAsync(s => s.State.HasFlag(SearchStates.Completed));

                    if (totalCount > maxCount)
                    {
                        var excessCount = totalCount - maxCount;
                        var excessDeletedCount = await DeleteSearchesInBatchesAsync(
                            context,
                            context.Searches.Where(s => s.State.HasFlag(SearchStates.Completed)),
                            excessCount);

                        deletedCount += excessDeletedCount;
                        if (excessDeletedCount > 0)
                        {
                            Log.Information("Retention cleanup: deleted {Count} oldest searches (limit: {MaxCount})", excessDeletedCount, maxCount);
                        }
                    }
                }

                return deletedCount;
            }
            catch (Exception ex)
            {
                Log.Error("Failed to cleanup searches: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        private async Task<int> DeleteSearchesInBatchesAsync(
            SearchDbContext context,
            IQueryable<Search> candidates,
            int maxCount = int.MaxValue)
        {
            var deletedCount = 0;

            while (deletedCount < maxCount)
            {
                var batchSize = Math.Min(RetentionCleanupBatchSize, maxCount - deletedCount);
                var batch = await candidates
                    .OrderBy(search => search.StartedAt)
                    .ThenBy(search => search.Id)
                    .Take(batchSize)
                    .WithoutResponses()
                    .AsNoTracking()
                    .ToListAsync();

                if (batch.Count == 0)
                {
                    break;
                }

                var ids = batch.Select(search => search.Id).ToList();
                var broadcasts = new List<Task>();
                int batchDeletedCount;
                lock (_searchPersistenceSync)
                {
                    var currentBatch = candidates
                        .Where(search => ids.Contains(search.Id))
                        .WithoutResponses()
                        .AsNoTracking()
                        .ToList();
                    var currentIds = currentBatch.Select(search => search.Id).ToList();

                    batchDeletedCount = currentIds.Count == 0
                        ? 0
                        : context.Searches
                            .Where(search => currentIds.Contains(search.Id))
                            .ExecuteDelete();

                    if (batchDeletedCount > 0)
                    {
                        foreach (var search in currentBatch)
                        {
                            broadcasts.Add(SearchHub.BroadcastDeleteAsync(search));
                        }
                    }
                }

                foreach (var broadcast in broadcasts)
                {
                    await broadcast.ConfigureAwait(false);
                }

                deletedCount += batchDeletedCount;
                if (batch.Count < batchSize)
                {
                    break;
                }
            }

            return deletedCount;
        }

        /// <summary>
        ///     Gets searches linked to a wishlist item.
        /// </summary>
        /// <param name="wishlistItemId">The wishlist item ID.</param>
        /// <param name="limit">Maximum number of searches to return.</param>
        /// <returns>The list of searches linked to the wishlist item.</returns>
        public async Task<List<Search>> GetByWishlistItemIdAsync(Guid wishlistItemId, int limit = 50)
        {
            using var context = ContextFactory.CreateDbContext();
            return await context.Searches
                .AsNoTracking()
                .Where(s => s.WishlistItemId == wishlistItemId)
                .OrderByDescending(s => s.StartedAt)
                .Take(limit)
                .WithoutResponses()
                .ToListAsync();
        }

        /// <summary>
        ///     Performs a mesh-only search when the legacy fallback is active (T-823).
        ///     Resolves query to MBIDs, queries DHT for overlay descriptors.
        /// </summary>
        /// <param name="id">A unique identifier for the search.</param>
        /// <param name="query">The search query.</param>
        /// <param name="options">Search options.</param>
        /// <param name="safetySource">The safety-limiter source for the search.</param>
        /// <param name="wishlistItemId">The originating wishlist item, if any.</param>
        /// <returns>The completed search with mesh-only results.</returns>
        private async Task<Search> StartMeshOnlySearchAsync(
            Guid id,
            SearchQuery query,
            SearchOptions? options = null,
            string safetySource = "user",
            Guid? wishlistItemId = null)
        {
            var safeQuery = LoggingSanitizer.SanitizeQueryText(query.SearchText);
            Log.Information("[VSF-DISASTER-SEARCH] Starting mesh-only search for query: {Query} (id: {Id})", safeQuery, id);

            var cancellationTokenSource = new CancellationTokenSource();
            var searchCancellationToken = cancellationTokenSource.Token;
            CancellationTokens.TryAdd(id, cancellationTokenSource);

            // Initialize search record for mesh-only search
            var search = new Search()
            {
                SearchText = query.SearchText,
                Token = 0, // Mesh searches don't use Soulseek tokens
                Id = id,
                State = SearchStates.Requested,
                StartedAt = DateTime.UtcNow,
                Source = safetySource,
                WishlistItemId = wishlistItemId,
            };

            try
            {
                Task createBroadcast;
                lock (_searchPersistenceSync)
                {
                    using var context = ContextFactory.CreateDbContext();
                    context.Add(search);
                    context.SaveChanges();
                    createBroadcast = SearchHub.BroadcastCreateAsync(search);
                }

                await createBroadcast.ConfigureAwait(false);

                // T-823: Mesh-only search implementation
                // Step 1: Resolve query to MBIDs (MusicBrainz IDs)
                var mbids = await ResolveQueryToMbidsAsync(query.SearchText, searchCancellationToken);

                if (mbids.Count == 0)
                {
                    Log.Information("[VSF-DISASTER-SEARCH] No MBIDs for query: {Query}, falling back to overlay text search", safeQuery);
                    IReadOnlyList<Response> overlayResponses;
                    if (MeshOverlaySearchService != null)
                    {
                        try
                        {
                            overlayResponses = await MeshOverlaySearchService.SearchAsync(query.SearchText, searchCancellationToken);
                        }
                        catch (Exception ex)
                        {
                            Log.Debug("[VSF-DISASTER-SEARCH] Overlay text search failed: {Exception}",
                                LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                            overlayResponses = Array.Empty<Response>();
                        }
                    }
                    else
                    {
                        overlayResponses = Array.Empty<Response>();
                    }

                    search.State = SearchStates.Completed;
                    search.EndedAt = DateTime.UtcNow;
                    var filteredOverlayResponses = wishlistItemId.HasValue
                        ? WishlistSearchPolicy.FilterResponses(overlayResponses, query.SearchText, options?.FileFilter)
                        : overlayResponses;
                    search.Responses = filteredOverlayResponses;
                    search.ResponsesAvailable = true;
                    ApplyResponseSummary(search, filteredOverlayResponses);
                    var fallbackBroadcast = PersistAndBroadcastSearchUpdate(search);
                    if (fallbackBroadcast != null)
                    {
                        await fallbackBroadcast.ConfigureAwait(false);
                    }

                    return search;
                }

                Log.Debug("[VSF-DISASTER-SEARCH] Resolved {Count} MBIDs for query: {Query}", mbids.Count, safeQuery);

                // Step 2: Query mesh for each MBID and aggregate results
                var meshResults = new List<slskd.VirtualSoulfind.DisasterMode.MeshPeerResult>();

                // Limit to 5 MBIDs to avoid flooding.
                foreach (var mbid in mbids.Take(5))
                {
                    try
                    {
                        if (MeshSearchService == null)
                        {
                            continue;
                        }

                        var mbidResult = await MeshSearchService.SearchByMbidAsync(mbid, searchCancellationToken);
                        if (mbidResult == null)
                        {
                            continue;
                        }

                        meshResults.AddRange(mbidResult.PeerResults);
                    }
                    catch (Exception ex)
                    {
                        Log.Debug("[VSF-DISASTER-SEARCH] Failed to search MBID {Mbid}: {Exception}",
                            LoggingSanitizer.SanitizeExternalIdentifier(mbid),
                            LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                    }
                }

                // Step 3: Convert mesh results to Search.Response format
                var responses = ConvertMeshResultsToResponses(meshResults, query.SearchText);
                var filteredResponses = wishlistItemId.HasValue
                    ? WishlistSearchPolicy.FilterResponses(responses, query.SearchText, options?.FileFilter)
                    : responses.ToList();

                // Update search record with results
                search.State = SearchStates.Completed;
                search.EndedAt = DateTime.UtcNow;
                ApplyResponseSummary(search, filteredResponses);

                // Add responses to search
                search.Responses = filteredResponses;
                search.ResponsesAvailable = true;

                var completionBroadcast = PersistAndBroadcastSearchUpdate(search);
                if (completionBroadcast != null)
                {
                    await completionBroadcast.ConfigureAwait(false);
                }

                Log.Information("[VSF-DISASTER-SEARCH] Mesh-only search completed: {PeerCount} peers, {FileCount} files (id: {Id})",
                    meshResults.Count, search.FileCount, id);

                return search;
            }
            catch (Exception ex)
            {
                Log.Error("[VSF-DISASTER-SEARCH] Mesh-only search failed for query: {Query} (id: {Id}): {Exception}",
                    safeQuery, id, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                search.State = SearchStates.Completed;
                search.EndedAt = DateTime.UtcNow;
                var failureBroadcast = PersistAndBroadcastSearchUpdate(search);
                if (failureBroadcast != null)
                {
                    await failureBroadcast.ConfigureAwait(false);
                }

                throw;
            }
            finally
            {
                CancellationTokens.TryRemove(id, out _);
            }
        }

        /// <summary>
        ///     Resolves a search query to MusicBrainz IDs for mesh search.
        /// </summary>
        /// <param name="query">The search query text.</param>
        /// <param name="ct">Cancellation token.</param>
        /// <returns>List of MBIDs to search for.</returns>
        private Task<List<string>> ResolveQueryToMbidsAsync(string query, CancellationToken ct)
        {
            _ = ct;
            var safeQuery = LoggingSanitizer.SanitizeQueryText(query);

            // For now, implement simple query parsing to extract potential MBIDs
            // In a full implementation, this would integrate with MusicBrainz API
            var mbids = new List<string>();

            // Check if query looks like an MBID
            if (System.Text.RegularExpressions.Regex.IsMatch(query, @"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", System.Text.RegularExpressions.RegexOptions.IgnoreCase))
            {
                mbids.Add(query.ToLowerInvariant());
                return Task.FromResult(mbids);
            }

            // For text queries, we would normally query MusicBrainz API
            // For this implementation, we'll use a simple heuristic or return empty
            // In production, this should integrate with IMusicBrainzClient
            Log.Debug("[VSF-DISASTER-SEARCH] Query '{Query}' is not an MBID - mesh search may return limited results", safeQuery);

            // MusicBrainz API integration deferred: requires IMusicBrainzClient integration
            // For now, return empty to indicate no MBIDs found (mesh search will proceed with text query)
            return Task.FromResult(mbids);
        }

        private void ReleaseCancellationToken(Guid id)
        {
            if (CancellationTokens.TryRemove(id, out var cts))
            {
                cts.Cancel();
                cts.Dispose();
            }
        }

        /// <summary>
        ///     Converts mesh search results to Search.Response format for compatibility.
        /// </summary>
        /// <param name="meshResults">Mesh search results.</param>
        /// <param name="originalQuery">The original search query.</param>
        /// <returns>Collection of Response objects.</returns>
        private IEnumerable<Response> ConvertMeshResultsToResponses(
            List<slskd.VirtualSoulfind.DisasterMode.MeshPeerResult> meshResults,
            string originalQuery)
        {
            var responses = new List<Response>();

            foreach (var peerResult in meshResults)
            {
                var files = new List<File>();

                foreach (var meshFile in peerResult.Files)
                {
                    files.Add(ConvertMeshFile(meshFile));
                }

                if (files.Count > 0)
                {
                    var response = new Response()
                    {
                        Username = peerResult.PeerId,
                        Token = 0, // Mesh searches don't use tokens
                        HasFreeUploadSlot = true, // Assume available
                        UploadSpeed = 1000000, // Default speed
                        QueueLength = 0, // Assume no queue
                        FileCount = files.Count,
                        Files = files,
                        LockedFileCount = 0,
                        LockedFiles = new List<File>()
                    };

                    responses.Add(response);
                }
            }

            return responses;
        }

        internal static File ConvertMeshFile(
            slskd.VirtualSoulfind.DisasterMode.MeshFileResult meshFile)
            => new()
            {
                Code = 1, // Download code
                Filename = meshFile.Filename,
                Size = meshFile.Size,
                Extension = System.IO.Path.GetExtension(meshFile.Filename) ?? string.Empty,
                BitRate = meshFile.BitrateKbps,
                Length = null,
                IsLocked = false,
            };
    }
}
