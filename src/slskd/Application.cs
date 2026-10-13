// <copyright file="Application.cs" company="slskd Team">
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

// <copyright file="Application.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;

namespace slskd
{
    using System;
    using System.Collections.Concurrent;
    using System.Collections.Generic;
    using System.Diagnostics;
    using System.IO;
    using System.Linq;
    using System.Net;
    using System.Net.Sockets;
    using System.Reflection;
    using System.Text.Json;
    using System.Runtime;
    using System.Runtime.InteropServices;
    using System.Text.RegularExpressions;
    using System.Threading;
    using System.Threading.Tasks;
    using Microsoft.AspNetCore.SignalR;
    using Microsoft.Extensions.Caching.Memory;
    using Microsoft.Extensions.Hosting;
    using Serilog;
    using Serilog.Events;
    using slskd.Common.CodeQuality;
    using slskd.Common.Security;
    using slskd.Configuration;
    using slskd.Core.API;
    using slskd.Events;
    using slskd.Files;
    using slskd.Integrations.Pushbullet;
    using slskd.Messaging;
    using slskd.PodCore;
    using slskd.Relay;
    using slskd.Search;
    using slskd.Shares;
    using slskd.Telemetry;
    using slskd.Transfers;
    using slskd.Transfers.API;
    using slskd.Transfers.Downloads;
    using slskd.Users;
    using Soulseek;
    using Soulseek.Diagnostics;
    using Soulseek.Messaging.Messages;

    public interface IApplication : IHostedService
    {
        public Task CheckVersionAsync();
        public void CollectGarbage();
    }

    public sealed class Application : IApplication, IDisposable
    {
        private readonly List<PosixSignalRegistration> _posixSignalRegistrations = new();
        private readonly List<IDisposable> _changeRegistrations = new();
        private CancellationTokenSource? _startupInitializationCts;
        private Task? _startupInitializationTask;
        private ConsoleCancelEventHandler? _cancelKeyPressHandler;
        private EventHandler<LogRecord>? _programLogEmittedHandler;
        private EventHandler<string>? _privateRoomMembershipAddedHandler;
        private EventHandler<string>? _privateRoomMembershipRemovedHandler;
        private EventHandler<string>? _privateRoomModerationAddedHandler;
        private EventHandler<string>? _privateRoomModerationRemovedHandler;
        private EventHandler<DownloadDeniedEventArgs>? _downloadDeniedHandler;
        private EventHandler<DownloadFailedEventArgs>? _downloadFailedHandler;
        private readonly object _searchRetentionCleanupSyncRoot = new();
        private bool _searchRetentionCleanupRunning;
        private DateTime? _lastSearchRetentionCleanupAt;

        /// <summary>
        ///     The name of the default user group.
        /// </summary>
        public const string DefaultGroup = "default";

        /// <summary>
        ///     The name of the privileged user group.
        /// </summary>
        public const string PrivilegedGroup = "privileged";

        /// <summary>
        ///     The name of the leecher user group.
        /// </summary>
        public const string LeecherGroup = "leechers";

        /// <summary>
        ///     The name of the blacklisted user group.
        /// </summary>
        public const string BlacklistedGroup = "blacklisted";

        private static readonly string ApplicationShutdownTransferExceptionMessage = "Application shut down";
        private static readonly TimeSpan QueuedUploadLimitSnapshotLifetime = TimeSpan.FromSeconds(2);
        private static readonly Regex HumanChallengeDirectQuestionRegex = new(
            @"\b(are|r)\s+(u|you)\s+(a\s+)?(human|person|real|bot|robot|automated|automation)\b|\b(are|r)\s+(u|you)\s+(using|running)\s+(an?\s+)?(automated\s+)?(client|script|bot|robot)\b|\b(u|you)\s+(human|real|bot)\s*\??\b|\b(bot|human)\s*\?\s*$",
            RegexOptions.Compiled | RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        private static readonly Regex HumanChallengeIntentRegex = new(
            @"\b(prove|verify|confirm|show|tell|say|reply|respond|answer|type|write|pass|solve)\b",
            RegexOptions.Compiled | RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        private static readonly Regex HumanChallengeIdentityRegex = new(
            @"\b(human|person|real|bot|robot|automated|automation|script|client|captcha)\b|not\s+(a\s+)?bot|not\s+automated",
            RegexOptions.Compiled | RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        private static readonly Regex HumanChallengeNamedCheckRegex = new(
            @"\b(human|bot|robot|captcha|anti[-\s]?bot|anti[-\s]?leech)\s*(check|test|verification|verify|gate|screen|challenge)\b|\b(check|test|verification|verify|gate|screen|challenge)\s*(human|bot|robot|captcha)\b",
            RegexOptions.Compiled | RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        private static readonly Regex ShareGatePrivateMessageRegex = new(
            @"\b(not|n't|no)\s+shar(e|ing)\b|\bshar(e|ing)\s+(something|more|files?)\b|\bempty\s+shares?\b|\bno\s+leechers?\b|\bleechers?\b.{0,40}\b(ban|blocked?|only)\b|\b\d+k\+\s+file\s+users?\b",
            RegexOptions.Compiled | RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

#pragma warning disable SA1306 // Field names should begin with lower-case letter
        private static int EnqueueQueueDepth = 0;
        private static double CurrentEnqueueLatency = 0;
        private static int IncomingSearchRequestQueueDepth = 0;
#pragma warning restore SA1306 // Field names should begin with lower-case letter

        public Application(
            OptionsAtStartup optionsAtStartup,
            IOptionsMonitor<Options> optionsMonitor,
            IManagedState<State> state,
            ISoulseekClient soulseekClient,
            FileService fileService,
            ConnectionWatchdog connectionWatchdog,
            ITransferService transferService,
            IBrowseTracker browseTracker,
            IRoomService roomService,
            IUserService userService,
            IMessagingService messagingService,
            IShareService shareService,
            ISearchService searchService,
            Integrations.Notifications.INotificationService notificationService,
            IRelayService relayService,
            IHubContext<ApplicationHub> applicationHub,
            IHubContext<LogsHub> logHub,
            IHubContext<Transfers.API.TransfersHub> transfersHub,
            Events.EventBus eventBus,
            Events.EventService eventService,
            IServiceProvider serviceProvider,
            IServiceScopeFactory serviceScopeFactory,
            NowPlaying.NowPlayingService nowPlayingService,
            Transfers.MultiSource.Metrics.ITrafficAccountingService trafficAccountingService)
        {
            Log.Debug("[Application] Constructor called");
            Log.Debug("[Application] Setting up event handlers...");
            var hostLifetime = serviceProvider.GetService<IHostApplicationLifetime>();
            _cancelKeyPressHandler = (_, args) =>
            {
                args.Cancel = true;
                ShuttingDown = true;
                Program.MasterCancellationTokenSource.Cancel();
                Log.Information("Received SIGINT; stopping application");
                hostLifetime?.StopApplication();
            };
            Console.CancelKeyPress += _cancelKeyPressHandler;

            foreach (var signal in new[] { PosixSignal.SIGINT, PosixSignal.SIGQUIT, PosixSignal.SIGTERM })
            {
                _posixSignalRegistrations.Add(PosixSignalRegistration.Create(signal, context =>
                {
                    context.Cancel = true;
                    ShuttingDown = true;
                    Program.MasterCancellationTokenSource.Cancel();
                    Log.Information("Received {Signal}; stopping application", signal);
                    hostLifetime?.StopApplication();
                }));
            }

            OptionsAtStartup = optionsAtStartup;

            OptionsMonitor = optionsMonitor;
            RegisterChange(OptionsMonitor.OnChange(options =>
            {
                _ = TaskObservation.Observe(
                    OptionsMonitor_OnChange(options),
                    ex => Log.Error(
                        "Unexpected failure escaped option update handler: {Exception}",
                        LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString())));
            }));

            IncomingSearchRequestSemaphore = new SemaphoreSlim(
                initialCount: OptionsAtStartup.Throttling.Search.Incoming.Concurrency,
                maxCount: OptionsAtStartup.Throttling.Search.Incoming.Concurrency);

            PreviousOptions = OptionsMonitor.CurrentValue;

            Flags = Program.Flags;

            CompiledSearchRequestFilters = CompileSearchRequestFilters(
                OptionsAtStartup.Filters.Search.Request,
                Flags.CaseSensitiveRegEx);

            State = state;
            RegisterChange(State.OnChange(state => State_OnChange(state)));

            Files = fileService;

            Shares = shareService;
            RegisterChange(Shares.StateMonitor.OnChange(state => ShareState_OnChange(state)));

            Search = searchService;

            Transfers = transferService;
            BrowseTracker = browseTracker;
            Notifications = notificationService;

            RoomService = roomService;
            Users = userService;
            Users.WatchedUsersChanged += Users_WatchedUsersChanged;
            Messaging = messagingService;
            ApplicationHub = applicationHub;

            Relay = relayService;
            RegisterChange(Relay.StateMonitor.OnChange(relayState => State.SetValue(state => state with { Relay = relayState.Current })));

            LogHub = logHub;
            TransfersHub = transfersHub;
            _programLogEmittedHandler = (sender, log) =>
            {
                _ = TaskObservation.Observe(
                    LogHub.EmitLogAsync(log),
                    ex => Log.Error(
                        "Failed to emit log record to connected clients: {Exception}",
                        LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString())));
            };
            Program.LogEmitted += _programLogEmittedHandler;

            EventBus = eventBus;
            EventService = eventService;
            ServiceProvider = serviceProvider;
            ServiceScopeFactory = serviceScopeFactory;
            NowPlayingService = nowPlayingService;
            TrafficAccounting = trafficAccountingService;

            Client = soulseekClient;

            Client.DiagnosticGenerated += Client_DiagnosticGenerated;

            Client.TransferStateChanged += Client_TransferStateChanged;
            Client.TransferProgressUpdated += Client_TransferProgressUpdated;

            Client.BrowseProgressUpdated += Client_BrowseProgressUpdated;
            Client.UserStatusChanged += Client_UserStatusChanged;
            Client.PrivateMessageReceived += Client_PrivateMessageReceived;

            _privateRoomMembershipAddedHandler = (e, room) => Log.Information("Added to private room {Room}", LoggingSanitizer.SanitizeExternalIdentifier(room));
            _privateRoomMembershipRemovedHandler = (e, room) => Log.Information("Removed from private room {Room}", LoggingSanitizer.SanitizeExternalIdentifier(room));
            _privateRoomModerationAddedHandler = (e, room) => Log.Information("Promoted to moderator in private room {Room}", LoggingSanitizer.SanitizeExternalIdentifier(room));
            _privateRoomModerationRemovedHandler = (e, room) => Log.Information("Demoted from moderator in private room {Room}", LoggingSanitizer.SanitizeExternalIdentifier(room));
            Client.PrivateRoomMembershipAdded += _privateRoomMembershipAddedHandler;
            Client.PrivateRoomMembershipRemoved += _privateRoomMembershipRemovedHandler;
            Client.PrivateRoomModerationAdded += _privateRoomModerationAddedHandler;
            Client.PrivateRoomModerationRemoved += _privateRoomModerationRemovedHandler;

            Client.RoomMessageReceived += Client_RoomMessageReceived;
            Client.Disconnected += Client_Disconnected;
            Client.Connected += Client_Connected;
            Client.LoggedIn += Client_LoggedIn;
            Client.StateChanged += Client_StateChanged;
            Client.DistributedNetworkStateChanged += Client_DistributedNetworkStateChanged;
            _downloadDeniedHandler = (e, args) => Log.Information(
                "Download of {Filename} from {Username} was denied by the remote user: {Message}",
                LoggingSanitizer.SanitizeFilePath(args.Filename),
                LoggingSanitizer.SanitizeExternalIdentifier(args.Username),
                LoggingSanitizer.SanitizeExternalIdentifier(args.Message));
            _downloadFailedHandler = (e, args) => Log.Information(
                "Download of {Filename} from {Username} reported as failed by the remote user",
                LoggingSanitizer.SanitizeFilePath(args.Filename),
                LoggingSanitizer.SanitizeExternalIdentifier(args.Username));
            Client.DownloadDenied += _downloadDeniedHandler;
            Client.DownloadFailed += _downloadFailedHandler;

            Client.ExcludedSearchPhrasesReceived += Client_ExcludedSearchPhrasesReceived;

            ConnectionWatchdog = connectionWatchdog;

            Log.Debug("[Application] Registering clock events...");
            Clock.EveryMinute += Clock_EveryMinute;
            Clock.EveryThirtySeconds += Clock_EveryThirtySeconds;
            Clock.EveryFiveMinutes += Clock_EveryFiveMinutes;
            Clock.EveryThirtyMinutes += Clock_EveryThirtyMinutes;
            Clock.EveryHour += Clock_EveryHour;
            Log.Debug("[Application] Constructor completed");
        }

        /// <summary>
        ///     Gets a value indicating whether the application is in the process of shutting down.
        /// </summary>
        public static bool IsShuttingDown => Environment.HasShutdownStarted || ShuttingDown;

        private static bool ShuttingDown { get; set; } = false;

        private ISoulseekClient Client { get; set; }
        private FileService Files { get; }
        private IRoomService RoomService { get; set; }
        private IBrowseTracker BrowseTracker { get; set; }
        private ConnectionWatchdog ConnectionWatchdog { get; }
        private IMessagingService Messaging { get; set; }
        private ILogger Log { get; set; } = Serilog.Log.ForContext<Application>();
        private ConcurrentDictionary<string, ILogger> Loggers { get; } = new ConcurrentDictionary<string, ILogger>();
        private Options Options => OptionsMonitor.CurrentValue;
        private OptionsAtStartup OptionsAtStartup { get; set; }
        private IOptionsMonitor<Options> OptionsMonitor { get; set; }
        private SemaphoreSlim OptionsSyncRoot { get; } = new SemaphoreSlim(1, 1);
        private SemaphoreSlim BrowseCacheSyncRoot { get; } = new SemaphoreSlim(1, 1);
        private SemaphoreSlim GlobalEnqueueSemaphore { get; } = new SemaphoreSlim(10, 10);
        private SemaphoreSlim UserEnqueueSemaphoreSyncRoot { get; } = new SemaphoreSlim(1, 1);
        private ConcurrentDictionary<string, SemaphoreSlim> UserEnqueueSemaphores { get; } = new ConcurrentDictionary<string, SemaphoreSlim>();
        private Options PreviousOptions { get; set; }
        private Integrations.Notifications.INotificationService Notifications { get; }
        private DateTime SharesRefreshStarted { get; set; }
        private IManagedState<State> State { get; }
        private ITransferService Transfers { get; init; }
        private IHubContext<ApplicationHub> ApplicationHub { get; set; }
        private IHubContext<LogsHub> LogHub { get; set; }
        private IHubContext<Transfers.API.TransfersHub> TransfersHub { get; set; }
        private Events.EventBus EventBus { get; set; }
        private Events.EventService EventService { get; set; }
        private IUserService Users { get; set; }
        private IShareService Shares { get; set; }
        private ISearchService Search { get; set; }
        private IRelayService Relay { get; set; }
        private IMemoryCache Cache { get; set; } = new MemoryCache(new MemoryCacheOptions());
        private IReadOnlyList<Regex> CompiledSearchRequestFilters { get; set; } = [];

        // Admin-configured search filters run against untrusted, high-volume peer search
        // query text, so bound each match to prevent catastrophic-backtracking ReDoS.
        private static readonly TimeSpan SearchRequestFilterMatchTimeout = TimeSpan.FromMilliseconds(250);
        private ConcurrentDictionary<string, DateTimeOffset> HumanChallengeAutoResponseSentAt { get; } = new(StringComparer.InvariantCultureIgnoreCase);

        /// <summary>
        ///     Per-transfer last-emitted tick for coalescing high-frequency progress events
        ///     down to roughly <see cref="TransferProgressEmitIntervalMs"/>. Keyed by
        ///     direction|username|filename; pruned on terminal state change.
        /// </summary>
        private ConcurrentDictionary<string, long> TransferProgressLastEmitTicks { get; } = new(StringComparer.Ordinal);

        /// <summary>
        ///     Event-started traffic commits must finish before dependency injection
        ///     disposes their accounting service during graceful shutdown.
        /// </summary>
        private ConcurrentDictionary<int, Task> ActiveSoulseekDownloadAccountingCommits { get; } = new();

        private const long TransferProgressEmitIntervalMs = 1_000;

        private IReadOnlyList<Guid> ActiveDownloadIdsAtPreviousShutdown { get; set; } = [];
        private Options.FlagsOptions Flags { get; set; }
        private IReadOnlyList<string> ExcludedSearchPhrases { get; set; } = [];
        private SemaphoreSlim IncomingSearchRequestSemaphore { get; set; }
        private IServiceProvider ServiceProvider { get; set; }
        private IServiceScopeFactory ServiceScopeFactory { get; set; }
        private NowPlaying.NowPlayingService NowPlayingService { get; set; }
        private Transfers.MultiSource.Metrics.ITrafficAccountingService TrafficAccounting { get; }

        public void CollectGarbage()
        {
            var sw = new Stopwatch();

            Log.Debug("Collecting garbage");

            sw.Start();

            GCSettings.LargeObjectHeapCompactionMode = GCLargeObjectHeapCompactionMode.CompactOnce;
#pragma warning disable S1215 // "GC.Collect" should not be called
            GC.Collect(2, GCCollectionMode.Forced, blocking: true, compacting: true);
#pragma warning restore S1215 // "GC.Collect" should not be called

            sw.Stop();

            Log.Debug("Garbage collection completed in {Duration}ms", sw.ElapsedMilliseconds);
        }

        /// <summary>
        ///     Gets the version of the latest application release.
        /// </summary>
        /// <returns>The operation context.</returns>
        public async Task CheckVersionAsync()
        {
            if (Program.IsCanary)
            {
                // todo: use the docker hub API to find the latest canary tag
                Log.Information("Skipping version check for Canary build; check for updates manually.");
                return;
            }

            Log.Information("Checking GitHub Releases for latest version");

            try
            {
                var httpClientFactory = ServiceProvider.GetRequiredService<IHttpClientFactory>();
                using var http = httpClientFactory.CreateClient(Common.Security.OutboundUriGuard.NoRedirectHttpClientName);

                var latestRelease = await GitHub.GetLatestReleaseInfo(
                    organization: "snapetech",
                    repository: "slskdn",
                    userAgent: $"slskdN v{Program.FullVersion}",
                    http: http);
                var result = GitHub.CreateVersionCheckResult(latestRelease, DateTimeOffset.UtcNow);

                // Skip comparison if the returned version string contains dev/canary markers.
                var latestVersionString = result.Latest;
                if (latestVersionString.Contains("-dev-", StringComparison.OrdinalIgnoreCase) ||
                    latestVersionString.Contains("-canary-", StringComparison.OrdinalIgnoreCase))
                {
                    Log.Information("Latest release is a dev/canary build ({LatestVersion}), skipping version comparison", latestVersionString);
                    return;
                }

                State.SetValue(state => state with
                {
                    Version = state.Version with
                    {
                        CheckedAt = result.CheckedAt,
                        IsUpdateAvailable = result.IsUpdateAvailable,
                        Latest = result.Latest,
                        LatestTag = result.LatestTag,
                        LatestUrl = result.LatestUrl,
                    },
                });

                if (result.IsUpdateAvailable)
                {
                    Log.Information("A new version is available! {CurrentVersion} -> {LatestVersion}", Program.SemanticVersion, result.Latest);
                }
                else
                {
                    Log.Information("Version {CurrentVersion} is up to date.", Program.SemanticVersion);
                }
            }
            catch (GitHubException ex) when (ex.InnerException is FormatException)
            {
                // FormatException from Version.Parse() is wrapped in GitHubException
                // This is normal for dev/experimental builds with non-standard version strings
                Log.Debug("Failed to parse latest version string (this is normal for dev/experimental builds): {Message}",
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.InnerException?.Message ?? ex.Message));

                // Ignore parse errors to avoid noisy warnings on malformed tags (normal for dev builds)
            }
            catch (FormatException ex)
            {
                Log.Debug("Failed to parse latest version string (this is normal for dev/experimental builds): {Message}",
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.Message));

                // Ignore parse errors to avoid noisy warnings on malformed tags (normal for dev builds)
            }
            catch (Exception ex)
            {
                State.SetValue(state => state with
                {
                    Version = state.Version with
                    {
                        CheckedAt = DateTimeOffset.UtcNow,
                        IsUpdateAvailable = null,
                    },
                });
                Log.Warning("Failed to check version: {Message}", LoggingSanitizer.SanitizeExternalIdentifier(ex.Message));
            }
        }

        Task IHostedService.StartAsync(CancellationToken cancellationToken)
        {
            Log.Information("[Application] StartAsync called - beginning startup sequence");
            Log.Information("Application started");

            // Start the actual initialization in the background to avoid blocking other hosted services
            _startupInitializationCts?.Cancel();
            _startupInitializationCts?.Dispose();
            var startupInitializationCts = new CancellationTokenSource();
            _startupInitializationCts = startupInitializationCts;
            _startupInitializationTask = Task.Run(() => InitializeApplicationAsync(startupInitializationCts.Token), CancellationToken.None);
            _ = ObserveBackgroundTaskAsync(
                _startupInitializationTask,
                "Failed to initialize application in background task");

            return Task.CompletedTask;
        }

        private async Task InitializeApplicationAsync(CancellationToken cancellationToken)
        {
            Log.Debug("Cleaning up any dangling records");

            // if the application shut down "uncleanly", transfers may need to be cleaned up. we deliberately don't allow these
            // records to be updated if the application has started to shut down so that we can do this cleanup and properly
            // disposition them as having failed due to an application shutdown, instead of some random exception thrown while
            // things are being disposed.
            var activeUploads = Transfers.Uploads.List(t => t.EndedAt == null || !t.State.HasFlag(TransferStates.Completed), includeRemoved: true);

            foreach (var upload in activeUploads)
            {
                Log.Debug("Cleaning up dangling upload {Filename} to {Username}",
                    LoggingSanitizer.SanitizeFilePath(upload.Filename), LoggingSanitizer.SanitizeExternalIdentifier(upload.Username));
                upload.State = TransferStates.Completed | TransferStates.Errored;
                upload.EndedAt = DateTime.UtcNow;
                upload.Exception = ApplicationShutdownTransferExceptionMessage;
                Transfers.Uploads.Update(upload);
            }

            var activeDownloads = Transfers.Downloads.List(t => t.EndedAt == null || !t.State.HasFlag(TransferStates.Completed), includeRemoved: true);

            foreach (var download in activeDownloads)
            {
                Log.Debug("Cleaning up dangling download {Filename} from {Username}",
                    LoggingSanitizer.SanitizeFilePath(download.Filename), LoggingSanitizer.SanitizeExternalIdentifier(download.Username));
                download.State = TransferStates.Completed | TransferStates.Errored;
                download.EndedAt = DateTime.UtcNow;
                download.Exception = ApplicationShutdownTransferExceptionMessage;
                Transfers.Downloads.Update(download);
            }

            /*
                search records can be left 'dangling' as well. responses are held in memory and saved to the database
                when the search is complete, so when a search 'dangles' all responses have been lost. to avoid discrepancies,
                we need to zero the response and file counts as well as set the state and EndedAt.
            */
            var activeSearches = await Search.ListAsync(s => s.EndedAt == null || !s.State.HasFlag(SearchStates.Completed));

            foreach (var search in activeSearches)
            {
                Log.Debug("Cleaning up dangling search {Query} started {StartedAt}",
                    LoggingSanitizer.SanitizeQueryText(search.SearchText), search.StartedAt);
                search.Responses = [];
                search.ResponseCount = 0;
                search.FileCount = 0;
                search.LockedFileCount = 0;
                search.State = SearchStates.Completed | SearchStates.TimedOut;
                search.EndedAt = DateTime.UtcNow;

                Search.Update(search);
            }

            // save the ids of any downloads that were active, so we can re-enqueue them after we've connected and logged in.
            // we need to check the database before we re-request to make sure the user didn't remove them from the UI while
            // the application was running, but before it was logged in. so just save the ids.
            ActiveDownloadIdsAtPreviousShutdown = activeDownloads.Select(d => d.Id).ToList().AsReadOnly();
            Log.Debug("Downloads to resume upon connection: {Ids}", ActiveDownloadIdsAtPreviousShutdown.ToJson());

            Log.Debug("Configuring client");

            var patch = CreateStartupSoulseekClientOptionsPatch(
                OptionsAtStartup,
                ConfigureSocketKeepaliveOptions,
                UserInfoResolver,
                BrowseResponseResolver,
                DirectoryContentsResponseResolver,
                EnqueueDownload,
                SearchResponseResolver,
                PlaceInQueueResolver,
                Log.Warning,
                ConfigureSocketMtu);

            await Client.ReconfigureOptionsAsync(patch);

            Log.Debug("Client configured");
            Log.Information("Listening for incoming connections on {IP}:{Port}", OptionsAtStartup.Soulseek.ListenIpAddress, OptionsAtStartup.Soulseek.ListenPort);

            var obfuscationPlan = SoulseekObfuscationSupport.BuildPlan(OptionsAtStartup.Soulseek);
            if (obfuscationPlan.Enabled)
            {
                Log.Information(
                    "Soulseek type-1 obfuscation configured in {Mode} mode on port {Port}; runtime state is {RuntimeState}; supported connection types: {SupportedConnectionTypes}; regular fallback advertised: {AdvertiseRegularPort}; prefer outbound: {PreferOutbound}. {Summary}",
                    obfuscationPlan.Mode,
                    obfuscationPlan.EffectiveListenPort,
                    obfuscationPlan.RuntimeState,
                    string.Join(",", obfuscationPlan.SupportedConnectionTypes),
                    obfuscationPlan.AdvertiseRegularPort,
                    obfuscationPlan.PreferOutbound,
                    obfuscationPlan.Summary);

                foreach (var limitation in obfuscationPlan.Limitations)
                {
                    Log.Debug("Soulseek type-1 obfuscation note: {Limitation}", limitation);
                }
            }
            else
            {
                Log.Debug(
                    "Soulseek type-1 obfuscation disabled; supported runtime connection types would be {SupportedConnectionTypes}",
                    string.Join(",", obfuscationPlan.SupportedConnectionTypes));
            }

            if (OptionsAtStartup.Soulseek.Connection.Proxy.Enabled)
            {
                Log.Information($"Using Proxy {OptionsAtStartup.Soulseek.Connection.Proxy.Address}:{OptionsAtStartup.Soulseek.Connection.Proxy.Port}");
            }

            if (!OptionsAtStartup.Flags.NoVersionCheck)
            {
                _ = CheckVersionAsync();
            }

            if (!OptionsAtStartup.Flags.NoShareScan)
            {
                try
                {
                    await Shares.InitializeAsync(forceRescan: OptionsAtStartup.Flags.ForceShareScan);
                }
                catch (Exception)
                {
                    Log.Error("Failed to initialize shares. Sharing is disabled");
                }
            }

            // the placement of this may be a bit contentious long term; when the clock starts, all of the
            // scheduled tasks will fire for the first time. the clock EventArgs contain a FirstRun flag
            // to help timed logic decide whether to run, but as a safeguard the start is delayed until
            // *just* before the application connects to the server/controller, meaning all configuration
            // and bootup tasks are complete. if this needs to be moved higher, a way to defer tasks from
            // the first run of the clock will need to be introduced, and those deferred tasks will need
            // to be executed around here somewhere.
            Log.Information("Starting system clock...");
            await Clock.StartAsync();
            Log.Information("System clock started");

            if (OptionsAtStartup.Relay.Enabled && OptionsAtStartup.Relay.Mode.ToEnum<RelayMode>() == RelayMode.Agent)
            {
                Log.Information("Running in Agent relay mode; not connecting to the Soulseek server.");
                await Relay.Client.StartAsync(cancellationToken);
            }
            else
            {
                if (OptionsAtStartup.Relay.Enabled)
                {
                    Log.Information("Running in Controller relay mode.  Listening for incoming Agent connections.");

                    if (OptionsAtStartup.Relay.Mode.ToEnum<RelayMode>() == RelayMode.Debug)
                    {
                        Log.Warning("Running in Debug relay mode; connecting to controller");
                        _ = ObserveBackgroundTaskAsync(
                            Relay.Client.StartAsync(cancellationToken),
                            "Failed to start relay client in debug mode");
                    }
                }

                if (OptionsAtStartup.Flags.NoConnect)
                {
                    Log.Warning("Not connecting to the Soulseek server; 'no-connect' option is enabled");
                }
                else if (string.IsNullOrEmpty(OptionsAtStartup.Soulseek.Username) || string.IsNullOrEmpty(OptionsAtStartup.Soulseek.Password))
                {
                    Log.Warning($"Not connecting to the Soulseek server; username and/or password invalid.  Specify valid credentials and manually connect, or update config and restart.");
                }
                else
                {
                    ConnectionWatchdog.Start();
                }
            }

            if (OptionsAtStartup.Feature.Mesh ||
                (OptionsAtStartup.Feature.Dht && OptionsAtStartup.DhtRendezvous.Enabled) ||
                OptionsAtStartup.Feature.Pods ||
                OptionsAtStartup.Feature.VirtualSoulfind)
            {
                // Register enabled mesh services for DHT operations (non-blocking - run after startup completes)
                _ = RegisterMeshServicesInBackgroundAsync(cancellationToken);
            }

            Log.Information("[Application] Initialization complete");
        }

        private Task RegisterMeshServicesAsync(CancellationToken cancellationToken)
        {
            try
            {
                // Register DHT mesh service for FIND_NODE, FIND_VALUE, STORE, and PING RPCs (T-902)
                var router = ServiceProvider.GetService<Mesh.ServiceFabric.MeshServiceRouter>();
                if (router != null)
                {
                    var dhtService = OptionsAtStartup.Feature.Dht && OptionsAtStartup.DhtRendezvous.Enabled
                        ? ServiceProvider.GetService<Mesh.ServiceFabric.Services.DhtMeshService>()
                        : null;
                    if (dhtService is not null)
                    {
                        router.RegisterService(dhtService);
                        Log.Information("Registered DHT mesh service for Kademlia RPC operations");
                    }
                    else if (OptionsAtStartup.Feature.Dht && OptionsAtStartup.DhtRendezvous.Enabled)
                    {
                        Log.Warning("DhtMeshService not available for registration");
                    }

                    // Register hole punch mesh service for NAT traversal
                    var holePunchService = OptionsAtStartup.Feature.Mesh
                        ? ServiceProvider.GetService<Mesh.ServiceFabric.Services.HolePunchMeshService>()
                        : null;
                    if (holePunchService is not null)
                    {
                        router.RegisterService(holePunchService);
                        Log.Information("Registered hole punch mesh service for NAT traversal");
                    }
                    else if (OptionsAtStartup.Feature.Mesh)
                    {
                        Log.Warning("HolePunchMeshService not available for registration");
                    }

                    if (OptionsAtStartup.Feature.Mesh && OptionsAtStartup.Feature.Streaming)
                    {
                        router.RegisterService(ServiceProvider.GetRequiredService<Mesh.ServiceFabric.Services.ListedRadioMeshService>());
                    }

                    // Register MeshContent service for GetByContentId (T-906, def-5)
                    var meshContentService = OptionsAtStartup.Feature.Mesh
                        ? ServiceProvider.GetService<Mesh.ServiceFabric.Services.MeshContentMeshService>()
                        : null;
                    if (meshContentService is not null)
                    {
                        router.RegisterService(meshContentService);
                        Log.Information("Registered MeshContent mesh service for GetByContentId RPC");
                    }
                    else if (OptionsAtStartup.Feature.Mesh)
                    {
                        Log.Warning("MeshContentMeshService not available for registration");
                    }

                    var podsService = OptionsAtStartup.Feature.Pods
                        ? ServiceProvider.GetService<Mesh.ServiceFabric.Services.PodsMeshService>()
                        : null;
                    if (podsService is not null)
                    {
                        router.RegisterService(podsService);
                        Log.Information("Registered Pods mesh service for remote Pod workflows");
                    }
                    else if (OptionsAtStartup.Feature.Pods)
                    {
                        Log.Warning("PodsMeshService not available for registration");
                    }

                    var virtualSoulfindService = OptionsAtStartup.Feature.VirtualSoulfind
                        ? ServiceProvider.GetService<Mesh.ServiceFabric.Services.VirtualSoulfindMeshService>()
                        : null;
                    if (virtualSoulfindService is not null)
                    {
                        router.RegisterService(virtualSoulfindService);
                        Log.Information("Registered shadow-index mesh service for remote content discovery");
                    }
                    else if (OptionsAtStartup.Feature.VirtualSoulfind)
                    {
                        Log.Warning("VirtualSoulfindMeshService not available for registration");
                    }

                    var privateGatewayService = OptionsAtStartup.Feature.Mesh
                        ? ServiceProvider.GetService<Mesh.ServiceFabric.Services.PrivateGatewayMeshService>()
                        : null;
                    if (privateGatewayService is not null)
                    {
                        router.RegisterService(privateGatewayService);
                        Log.Information("Registered private-gateway mesh service for Pod forwarding");
                    }
                    else if (OptionsAtStartup.Feature.Mesh)
                    {
                        Log.Warning("PrivateGatewayMeshService not available for registration");
                    }

                    var introspectionService = OptionsAtStartup.Feature.Mesh
                        ? ServiceProvider.GetService<Mesh.ServiceFabric.Services.MeshIntrospectionService>()
                        : null;
                    if (introspectionService is not null)
                    {
                        router.RegisterService(introspectionService);
                        Log.Information("Registered mesh-introspect service");
                    }
                    else if (OptionsAtStartup.Feature.Mesh)
                    {
                        Log.Warning("MeshIntrospectionService not available for registration");
                    }
                }
                else
                {
                    // This may be expected during startup if router isn't initialized yet
                    Log.Debug("MeshServiceRouter not available for service registration");
                }
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Failed to register mesh services");
            }

            return Task.CompletedTask;
        }

        private async Task RegisterMeshServicesInBackgroundAsync(CancellationToken cancellationToken)
        {
            try
            {
                await RegisterMeshServicesAsync(cancellationToken).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
            {
                Log.Information("Mesh service registration cancelled");
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Failed to register mesh services in background");
            }
        }

        internal static SoulseekClientOptionsPatch CreateStartupSoulseekClientOptionsPatch(
            OptionsAtStartup optionsAtStartup,
            Action<Socket, Options.SoulseekOptions.ConnectionOptions> configureSocketKeepaliveOptions,
            Func<string, IPEndPoint, Task<UserInfo>> userInfoResolver,
            Func<string, IPEndPoint, Task<BrowseResponse>> browseResponseResolver,
            Func<string, IPEndPoint, int, string, Task<IEnumerable<Soulseek.Directory>>> directoryContentsResolver,
            Func<string, IPEndPoint, string, Task> enqueueDownload,
            Func<string, int, SearchQuery, Task<SearchResponse?>> searchResponseResolver,
            Func<string, IPEndPoint, string, Task<int?>> placeInQueueResolver,
            Action<string, string>? warnInvalidListenAddress = null,
            Action<Socket, Options.SoulseekOptions.ConnectionOptions>? configureServerSocketMtuOptions = null)
        {
            ProxyOptions? proxyOptions = null;

            if (optionsAtStartup.Soulseek.Connection.Proxy.Enabled)
            {
                proxyOptions = new ProxyOptions(
                    address: optionsAtStartup.Soulseek.Connection.Proxy.Address,
                    port: optionsAtStartup.Soulseek.Connection.Proxy.Port.GetValueOrDefault(),
                    username: optionsAtStartup.Soulseek.Connection.Proxy.Username,
                    password: optionsAtStartup.Soulseek.Connection.Proxy.Password);
            }

            var connectionOptions = new ConnectionOptions(
                readBufferSize: optionsAtStartup.Soulseek.Connection.Buffer.Read,
                writeBufferSize: optionsAtStartup.Soulseek.Connection.Buffer.Write,
                writeQueueSize: int.MaxValue,
                connectTimeout: optionsAtStartup.Soulseek.Connection.Timeout.Connect,
                inactivityTimeout: optionsAtStartup.Soulseek.Connection.Timeout.Inactivity,
                proxyOptions: proxyOptions);

            var serverOptions = connectionOptions.With(
                inactivityTimeout: -1,
                configureSocket: socket =>
                {
                    configureSocketKeepaliveOptions(socket, optionsAtStartup.Soulseek.Connection);
                    configureServerSocketMtuOptions?.Invoke(socket, optionsAtStartup.Soulseek.Connection);
                });

            var distributedOptions = connectionOptions.With(
                writeQueueSize: optionsAtStartup.Soulseek.Connection.Buffer.WriteQueue,
                configureSocket: socket => configureSocketKeepaliveOptions(socket, optionsAtStartup.Soulseek.Connection));

            var transferOptions = connectionOptions.With(
                readBufferSize: optionsAtStartup.Soulseek.Connection.Buffer.Transfer,
                writeBufferSize: optionsAtStartup.Soulseek.Connection.Buffer.Transfer,
                inactivityTimeout: optionsAtStartup.Soulseek.Connection.Timeout.Transfer);

            if (!IPAddress.TryParse(optionsAtStartup.Soulseek.ListenIpAddress, out _))
            {
                warnInvalidListenAddress?.Invoke(
                    "Invalid Soulseek listen IP address '{Address}', defaulting to 0.0.0.0",
                    optionsAtStartup.Soulseek.ListenIpAddress);
            }

            // NOTE: deliberately do NOT set listenIPAddress / listenPort / enableListener here.
            // Those are already applied via CreateInitialSoulseekClientOptions() when the
            // SoulseekClient is constructed. Including them in the startup patch causes
            // ReconfigureOptionsAsync to tear down and restart the TcpListener while
            // Listener.ListenContinuouslyAsync is mid-accept, producing the
            // "Not listening. You must call the Start() method before calling this method."
            // race and, in some cases, leaving the listener permanently stopped so all
            // incoming peer connections are refused and every transfer fails.
            return new SoulseekClientOptionsPatch(
                userEndPointCache: CreateUserEndPointCache(),
                maximumUploadSpeed: optionsAtStartup.Global.Upload.SpeedLimit,
                maximumDownloadSpeed: optionsAtStartup.Global.Download.SpeedLimit,
                autoAcknowledgePrivateMessages: false,
                acceptPrivateRoomInvitations: true,
                serverConnectionOptions: serverOptions,
                peerConnectionOptions: connectionOptions,
                transferConnectionOptions: transferOptions,
                incomingConnectionOptions: connectionOptions,
                peerObfuscationOptions: SoulseekObfuscationSupport.BuildRuntimeOptions(optionsAtStartup.Soulseek),
                distributedConnectionOptions: distributedOptions,
                userInfoResolver: userInfoResolver,
                browseResponseResolver: browseResponseResolver,
                directoryContentsResolver: directoryContentsResolver,
                enqueueDownload: enqueueDownload,
                searchResponseCache: new SearchResponseCache(),
                searchResponseResolver: searchResponseResolver,
                placeInQueueResolver: placeInQueueResolver);
        }

        internal static IReadOnlyList<Regex> CompileSearchRequestFilters(
            IEnumerable<string> filters,
            bool caseSensitive)
        {
            var regexOptions = RegexOptions.Compiled;

            if (!caseSensitive)
            {
                regexOptions |= RegexOptions.IgnoreCase;
            }

            return filters
                .Select(f => new Regex(f, regexOptions, SearchRequestFilterMatchTimeout))
                .ToList()
                .AsReadOnly();
        }

        private static UserEndPointCache CreateUserEndPointCache()
        {
            var overrides = Environment.GetEnvironmentVariable("SLSKDN_TEST_USER_ENDPOINT_OVERRIDES");
            if (string.IsNullOrWhiteSpace(overrides))
            {
                return new UserEndPointCache();
            }

            var fixedEndpoints = new Dictionary<string, IPEndPoint>(StringComparer.OrdinalIgnoreCase);
            foreach (var entry in overrides.Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
            {
                var separatorIndex = entry.IndexOf('=');
                if (separatorIndex <= 0 || separatorIndex == entry.Length - 1)
                {
                    continue;
                }

                var username = entry[..separatorIndex].Trim();
                var endpointText = entry[(separatorIndex + 1)..].Trim();
                var endpointSeparatorIndex = endpointText.LastIndexOf(':');
                if (endpointSeparatorIndex <= 0 || endpointSeparatorIndex == endpointText.Length - 1)
                {
                    continue;
                }

                var addressText = endpointText[..endpointSeparatorIndex];
                var portText = endpointText[(endpointSeparatorIndex + 1)..];
                if (IPAddress.TryParse(addressText, out var address) &&
                    int.TryParse(portText, out var port) &&
                    port > 0 &&
                    port <= 65535)
                {
                    fixedEndpoints[username] = new IPEndPoint(address, port);
                }
            }

            return new UserEndPointCache(fixedEndpoints);
        }

        async Task IHostedService.StopAsync(CancellationToken cancellationToken)
        {
            ShuttingDown = true;
            Log.Information("Application is shutting down");

            var startupInitializationCts = _startupInitializationCts;
            startupInitializationCts?.Cancel();

            if (_startupInitializationTask != null)
            {
                try
                {
                    await _startupInitializationTask.ConfigureAwait(false);
                }
                catch (OperationCanceledException ex) when (
                    startupInitializationCts is { IsCancellationRequested: true } &&
                    ex.CancellationToken == startupInitializationCts.Token)
                {
                    // Expected during shutdown.
                }
            }

            _startupInitializationTask = null;
            _startupInitializationCts?.Dispose();
            _startupInitializationCts = null;

            Clock.Stop();

            await Transfers.Downloads.ShutdownAsync(cancellationToken).ConfigureAwait(false);

            try
            {
                Client.Disconnect("Shutting down", new ApplicationShutdownException("Shutting down"));
            }
            catch (InvalidOperationException ex) when (ShuttingDown && ex.Message.Contains("Sequence contains no elements", StringComparison.Ordinal))
            {
                Log.Debug("Ignoring Soulseek disconnect race during shutdown: {Message}", LoggingSanitizer.SanitizeExternalIdentifier(ex.Message));
            }

            Client.Dispose();
            await DrainSoulseekDownloadAccountingCommitsAsync().ConfigureAwait(false);
            foreach (var registration in _posixSignalRegistrations)
            {
                registration.Dispose();
            }

            Log.Information("Client stopped");
        }

        private void ConfigureSocketKeepaliveOptions(Socket socket, Options.SoulseekOptions.ConnectionOptions options)
        {
            /*
                os-specific keepalive is configured for long-lived connections for the server and distributed parent/children
                there may be legitimate reasons for these connections to go idle, and for that reason we can't use an inactivity watchdog
                to determine when they are dead.

                the intent, assuming the inactivity option is set to 15 seconds, is to send a keepalive probe after 15 seconds of inactivity,
                and then again every 15 seconds until a total of 3 unanswered probes are sent, after which the socket will disconnect.
            */
            try
            {
                socket.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.KeepAlive, true);

                if (OperatingSystem.IsWindows() && OptionsAtStartup.Flags.LegacyWindowsTcpKeepalive)
                {
                    return;
                }

                // the following will throw an exception on operating systems prior to Windows 10, version 1709 (and whatever Server SKU that corresponds to)
                // see: https://learn.microsoft.com/en-us/windows/win32/winsock/ipproto-tcp-socket-options
                socket.SetSocketOption(SocketOptionLevel.Tcp, SocketOptionName.TcpKeepAliveRetryCount, 3); // TCP_KEEPCNT
                socket.SetSocketOption(SocketOptionLevel.Tcp, SocketOptionName.TcpKeepAliveTime, options.Timeout.Inactivity / 1000); // TCP_KEEPIDLE
                socket.SetSocketOption(SocketOptionLevel.Tcp, SocketOptionName.TcpKeepAliveInterval, options.Timeout.Inactivity / 1000); // TCP_KEEPINTVL
            }
            catch (SocketException ex)
            {
                Log.Warning("Failed to configure connection keepalive settings: \"{Message}\". Performance is degraded. Set the configuration flag \"Legacy Windows TCP Keepalive\" to avoid this.",
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.Message));
            }
        }

        private void ConfigureSocketMtu(Socket socket, Options.SoulseekOptions.ConnectionOptions options)
        {
            if (!options.Mtu.HasValue)
            {
                return;
            }

            if (!OperatingSystem.IsLinux() && !OperatingSystem.IsMacOS() && !OperatingSystem.IsFreeBSD())
            {
                Log.Warning("The configured Soulseek server MTU is not supported by this operating system; using its default");
                return;
            }

            var maximumSegmentSize = CalculateMaximumTcpSegmentSize(options.Mtu.Value, socket.AddressFamily);

            try
            {
                // TCP_MAXSEG is option 2 at the TCP level on the supported POSIX systems.
                socket.SetSocketOption(SocketOptionLevel.Tcp, (SocketOptionName)2, maximumSegmentSize);
            }
            catch (SocketException ex)
            {
                Log.Warning("Failed to apply the configured Soulseek server MTU: {Message}",
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.Message));
            }
            catch (PlatformNotSupportedException ex)
            {
                Log.Warning("Failed to apply the configured Soulseek server MTU: {Message}",
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.Message));
            }
        }

        internal static int CalculateMaximumTcpSegmentSize(int mtu, AddressFamily addressFamily)
        {
            var headerSize = addressFamily switch
            {
                AddressFamily.InterNetwork => 40,
                AddressFamily.InterNetworkV6 => 60,
                _ => throw new ArgumentOutOfRangeException(nameof(addressFamily), addressFamily, "The socket must use IPv4 or IPv6"),
            };

            return mtu - headerSize;
        }

        internal static (bool Files, bool Megabytes) EvaluateUploadLimits(
            int files,
            long bytes,
            Options.LimitsOptions.Limits? configured,
            Options.LimitsOptions.Limits? defaults,
            long size)
        {
            var fileLimit = configured?.Files ?? defaults?.Files;
            var megabyteLimit = configured?.Megabytes ?? defaults?.Megabytes;

            return (
                Files: fileLimit is not null && files + 1 > fileLimit,
                Megabytes: megabyteLimit is not null && bytes + size > megabyteLimit * 1_000_000L);
        }

        private static string GetQueuedUploadLimitSnapshotKey(string username)
            => $"QueuedUploadLimitSnapshot:{username.ToUpperInvariant()}";

        private readonly record struct QueuedUploadLimitSnapshot(int Files, long Bytes);

        // todo: consider moving this somewhere else; it's pretty long and complicated
        private async Task EnqueueDownload(string username, IPEndPoint endpoint, string filename)
        {
            Metrics.Enqueue.RequestsReceived.Inc(1);
            Log.Information(
                "[UPLOAD-DIAG] Received upload enqueue request from {Username} ({Endpoint}) for {Filename}; queueDepth={QueueDepth}, currentEnqueueLatency={CurrentLatency}ms",
                username,
                endpoint,
                filename,
                EnqueueQueueDepth,
                CurrentEnqueueLatency);

            /*
                circuit breaker/failsafe:

                if it would take longer than three minutes to process this request based on the number of waiting requests
                and the average processing latency, reject the request automatically to alleviate pressure on the system.

                the requesting client will almost certainly consider any file for which it hasn't gotten confirmation
                in over a minute to be failed, over 3 minutes is a safety buffer.
            */
            if (EnqueueQueueDepth * CurrentEnqueueLatency > 180_000)
            {
                Metrics.Enqueue.RequestsDropped.Inc(1);
                throw new DownloadEnqueueException("Overwhelmed with requests; try again later.");
            }

            var stopwatch = new Stopwatch();
            var decisionStopwatch = new Stopwatch();

            SemaphoreSlim? userSemaphore = null;
            Task userSemaphoreWaitTask = Task.CompletedTask;
            bool userSemaphoreAcquired = false;

            bool enqueueRequestsSemaphoreAcquired = false;
            bool cachedQueueLimitRejection = false;
            var queueLimitSnapshotKey = GetQueuedUploadLimitSnapshotKey(username);

            try
            {
                if (IsSelfUsername(username))
                {
                    Log.Information("Rejected self-upload enqueue request for {Username} ({IP})",
                        LoggingSanitizer.SanitizeExternalIdentifier(username), LoggingSanitizer.SanitizeIpAddress(endpoint.Address));
                    throw new DownloadEnqueueException("File not shared.");
                }

                if (Users.IsBlacklisted(username, endpoint.Address))
                {
                    Log.Information("Rejected enqueue request for blacklisted user {Username} ({IP})",
                        LoggingSanitizer.SanitizeExternalIdentifier(username), LoggingSanitizer.SanitizeIpAddress(endpoint.Address));
                    throw new DownloadEnqueueException("File not shared.");
                }

                /*
                    for limits to work properly (and to help alleviate strain from the db, make incoming requests 'fair' among competing users),
                    we need to ensure that we process only one request per user at a time.

                    it's important that we obtain the user semaphore FIRST (before the global semaphore) to prevent one user
                    from monopolizing the request queue; users must 'go to the back of the line' for each request

                    hopefully this process takes < 10ms on most systems, but on low-spec systems with high traffic, this
                    round-robin approach helps guarantee the best QoS for peers
                */
                Interlocked.Increment(ref EnqueueQueueDepth); // any request waiting on any semaphore counts

                try
                {
                    // obtain exclusive access over the user dictionary. if this blocks it'll only be for a few ns
                    // we should also only be holding it for a few ns per request
                    await UserEnqueueSemaphoreSyncRoot.WaitAsync();

                    try
                    {
                        // get the user's semaphore and START waiting; if we wait we'll tie up the sync root
                        userSemaphore = UserEnqueueSemaphores.GetOrAdd(username, new SemaphoreSlim(initialCount: 1, maxCount: 1));
                        userSemaphoreWaitTask = userSemaphore.WaitAsync();
                    }
                    finally
                    {
                        UserEnqueueSemaphoreSyncRoot.Release();
                    }

                    await userSemaphoreWaitTask;
                    userSemaphoreAcquired = true;

                    await GlobalEnqueueSemaphore.WaitAsync();
                    enqueueRequestsSemaphoreAcquired = true;
                }
                finally
                {
                    Interlocked.Decrement(ref EnqueueQueueDepth);
                    Metrics.Enqueue.CurrentQueueDepth.Set(EnqueueQueueDepth);
                }

                stopwatch.Start();

                // in order to properly determine if the requested file would exceed any limits, we need to know the size of the file
                // it helps, too, that this will tell us whether the file is even shared.
                (string Host, string Filename, long Size) resolved;

                try
                {
                    resolved = await Shares.ResolveFileAsync(filename);
                }
                catch (NotFoundException)
                {
                    throw new DownloadEnqueueException("File not shared.");
                }

                // get the user's group. this will be the name of the user's group, if they have been added to a
                // user defined group, or one of the built-ins; 'default', 'privileged', 'leecher', or 'blacklisted'
                var group = await Users.GetOrFetchGroupAsync(username);

                // privileged users aren't subject to limits (for now)
                // i'm putting this off because 1) limits are unique to slskd, so all other clients are "unlimited"
                // and 2) i can't figure out what the limits would be, if not unlimited. users should get some level
                // of control, but i'd need to figure out a lower bound
                if (string.Equals(group, PrivilegedGroup))
                {
                    Log.Debug("Limits bypassed for {Username} and {File}; user is privileged",
                        LoggingSanitizer.SanitizeExternalIdentifier(username), LoggingSanitizer.SanitizeFilePath(filename));
                    await Transfers.Uploads.EnqueueAsync(username, filename);
                    return;
                }

                // we'll fall back to global limits for any limit that isn't set at the group level
                var global = Options.Global.Limits;

                // resolve the limits and upload options for this user's group.
                Options.LimitsOptions limits;
                Options.GroupsOptions.UploadOptions groupUploadOptions;

                if (Options.Groups.UserDefined.TryGetValue(group, out var userDefinedOptions))
                {
                    limits = userDefinedOptions.Limits;
                    groupUploadOptions = userDefinedOptions.Upload;
                }
                else
                {
                    limits = group switch
                    {
                        DefaultGroup => Options.Groups.Default.Limits,
                        LeecherGroup => Options.Groups.Leechers.Limits,
                        _ => Options.Groups.Default.Limits, // that's weird! we'll just go with defaults..
                    };
                    groupUploadOptions = group switch
                    {
                        DefaultGroup => Options.Groups.Default.Upload,
                        LeecherGroup => Options.Groups.Leechers.Upload,
                        _ => Options.Groups.Default.Upload,
                    };
                }

                // enforce file type restrictions for the group (#56)
                var allowedTypes = groupUploadOptions?.AllowedFileTypes;
                if (allowedTypes != null && allowedTypes.Length > 0)
                {
                    var ext = Path.GetExtension(resolved.Filename);
                    if (!allowedTypes.Any(t => string.Equals(t, ext, StringComparison.OrdinalIgnoreCase)))
                    {
                        Log.Information("Rejected enqueue request for user {Username}: file type {Extension} not allowed for group {Group}",
                            LoggingSanitizer.SanitizeExternalIdentifier(username), LoggingSanitizer.SanitizeExternalIdentifier(ext),
                            LoggingSanitizer.SanitizeExternalIdentifier(group));
                        throw new DownloadEnqueueException($"File type {ext} is not permitted.");
                    }
                }

                static bool IsNull(Options.LimitsOptions.Limits? lim, Options.LimitsOptions.Limits? global)
                    => (lim?.Files ?? global?.Files ?? lim?.Megabytes ?? global?.Megabytes ?? lim?.Failures ?? global?.Failures) is null;

                /*
                 * we have limits set, so now we have to fetch the data and compare to see if any would be hit if we allow this transfer to be enqueued.
                 * the strategy here is to summarize all uploads:
                 * 1) belonging to this user
                 * 2) that were started within the time period
                 * 3) that did not end due to an error (state includes errored, exception column is set)
                */
                decisionStopwatch.Start();

                // start with the queue, since that should contain the fewest files and should be the least expensive to check
                // "queued" includes both queued and in progress; records with a null EndedAt property, which is guaranteed to be set
                // for terminal transfers.
                if (!IsNull(limits?.Queued, global?.Queued))
                {
                    if (Cache.TryGetValue<QueuedUploadLimitSnapshot>(queueLimitSnapshotKey, out var cachedQueue))
                    {
                        var cachedOver = EvaluateUploadLimits(
                            cachedQueue.Files,
                            cachedQueue.Bytes,
                            limits?.Queued,
                            global?.Queued,
                            resolved.Size);

                        if (cachedOver.Files || cachedOver.Megabytes)
                        {
                            cachedQueueLimitRejection = true;
                            Metrics.Enqueue.QueueLimitSnapshotRejections.Inc();
                            throw new DownloadEnqueueException($"Too many {(cachedOver.Megabytes ? "megabytes" : "files")}");
                        }

                        Cache.Remove(queueLimitSnapshotKey);
                    }

                    var queued = Transfers.Uploads.Summarize(
                        expression: t => t.Username == username && t.EndedAt == null);

                    Log.Debug("Fetched queue stats: files: {Files}, bytes: {Bytes} ({Time}ms)", queued.Files, queued.Bytes, decisionStopwatch.ElapsedMilliseconds);

                    var over = EvaluateUploadLimits(queued.Files, queued.Bytes, limits?.Queued, global?.Queued, resolved.Size);

                    if (over.Files || over.Megabytes)
                    {
                        Cache.Set(
                            queueLimitSnapshotKey,
                            new QueuedUploadLimitSnapshot(queued.Files, queued.Bytes),
                            QueuedUploadLimitSnapshotLifetime);
                        Log.Information("Rejected enqueue request for user {Username}: Queued limits exceeded",
                            LoggingSanitizer.SanitizeExternalIdentifier(username));

                        // note: return exactly 'Too many files' or 'Too many megabytes' to ensure interop with other clients.
                        // these messages are retryable, while anything else is not
                        throw new DownloadEnqueueException($"Too many {(over.Megabytes ? "megabytes" : "files")}");
                    }
                }

                // start with weekly, as this is the most likely limit to be hit and we want to keep the work to a minimum
                // transfers that 'count' for the weekly limit are uploads that:
                // * started within the last week
                // * which have or have not ended (assuming queued files will complete)
                // * that were not errored
                if (!IsNull(limits?.Weekly, global?.Weekly))
                {
                    var erroredState = TransferStates.Completed | TransferStates.Errored;
                    var cutoffDateTime = DateTime.UtcNow.AddDays(-7);

                    var failures = Transfers.Uploads.Summarize(
                        expression: t =>
                            t.Username == username
                            && t.StartedAt >= cutoffDateTime
                            && (t.State.HasFlag(erroredState) || t.Exception != null));

                    Log.Debug("Fetched weekly failures: {Failures} ({Time}ms)", failures.Files, decisionStopwatch.ElapsedMilliseconds);

                    var failureLimit = limits?.Weekly?.Failures ?? global?.Weekly?.Failures;

                    if (failureLimit is not null && failures.Files >= failureLimit)
                    {
                        Log.Information("Rejected enqueue request for user {Username}: Weekly failure limit met or exceeded",
                            LoggingSanitizer.SanitizeExternalIdentifier(username));
                        throw new DownloadEnqueueException("Too many failed transfers this week");
                    }

                    var weekly = Transfers.Uploads.Summarize(
                        expression: t =>
                            t.Username == username
                            && t.StartedAt >= cutoffDateTime
                            && !t.State.HasFlag(erroredState)
                            && t.Exception == null);

                    Log.Debug("Fetched weekly stats: files: {Files}, bytes: {Bytes} ({Time}ms)", weekly.Files, weekly.Bytes, decisionStopwatch.ElapsedMilliseconds);

                    var over = EvaluateUploadLimits(weekly.Files, weekly.Bytes, limits?.Weekly, global?.Weekly, resolved.Size);

                    if (over.Files || over.Megabytes)
                    {
                        Log.Information("Rejected enqueue request for user {Username}: Weekly limits exceeded",
                            LoggingSanitizer.SanitizeExternalIdentifier(username));
                        throw new DownloadEnqueueException($"Too many {(over.Files ? "files" : "megabytes")} this week");
                    }
                }

                // lastly, check daily limits. the criteria for this is the same as weekly, just looking over the previous day instead
                // of the previous 7.
                if (!IsNull(limits?.Daily, global?.Daily))
                {
                    var erroredState = TransferStates.Completed | TransferStates.Errored;
                    var cutoffDateTime = DateTime.UtcNow.AddDays(-1);

                    var failures = Transfers.Uploads.Summarize(
                        expression: t =>
                            t.Username == username
                            && t.StartedAt >= cutoffDateTime
                            && (t.State.HasFlag(erroredState) || t.Exception != null));

                    Log.Debug("Fetched daily failures: {Failures} ({Time}ms)", failures.Files, decisionStopwatch.ElapsedMilliseconds);

                    var failureLimit = limits?.Daily?.Failures ?? global?.Daily?.Failures;

                    if (failureLimit is not null && failures.Files >= failureLimit)
                    {
                        Log.Information("Rejected enqueue request for user {Username}: Daily failure limit met or exceeded",
                            LoggingSanitizer.SanitizeExternalIdentifier(username));
                        throw new DownloadEnqueueException("Too many failed transfers today");
                    }

                    var daily = Transfers.Uploads.Summarize(
                        expression: t =>
                            t.Username == username
                            && t.StartedAt >= cutoffDateTime
                            && !t.State.HasFlag(erroredState)
                            && t.Exception == null);

                    Log.Debug("Fetched daily stats: files: {Files}, bytes: {Bytes} ({Time}ms)", daily.Files, daily.Bytes, decisionStopwatch.ElapsedMilliseconds);

                    var over = EvaluateUploadLimits(daily.Files, daily.Bytes, limits?.Daily, global?.Daily, resolved.Size);

                    if (over.Files || over.Megabytes)
                    {
                        Log.Information("Rejected enqueue request for user {Username}: Daily limits exceeded",
                            LoggingSanitizer.SanitizeExternalIdentifier(username));
                        throw new DownloadEnqueueException($"Too many {(over.Files ? "files" : "megabytes")} today");
                    }
                }

                decisionStopwatch.Stop();

                // Raise event for passive FLAC discovery - this user is downloading from us (slskdn-specific)
                EventBus.Raise(new Events.PeerDownloadedFromUsEvent
                {
                    Username = username,
                    Filename = filename
                });

                await Transfers.Uploads.EnqueueAsync(username, filename);
                Cache.Remove(queueLimitSnapshotKey);

                stopwatch.Stop();

                // we only report metrics for successes so that each value is guaranteed to include the enqueue latency
                Metrics.Enqueue.RequestsAccepted.Inc(1);
                Metrics.Enqueue.Latency.Observe(stopwatch.ElapsedMilliseconds);
                Metrics.Enqueue.CurrentLatency.Update(stopwatch.ElapsedMilliseconds);

                Interlocked.Exchange(ref CurrentEnqueueLatency, Metrics.Enqueue.CurrentLatency.Value);

                Log.Information("Enqueue of {Filename} to {Username} completed in {ElapsedOverall}ms, decision made in {ElapsedDecision}ms",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    stopwatch.ElapsedMilliseconds, decisionStopwatch.ElapsedMilliseconds);
            }
            catch (DownloadEnqueueException ex)
            {
                Metrics.Enqueue.RequestsRejected.Inc(1);
                if (!cachedQueueLimitRejection)
                {
                    Log.Warning(
                        "[UPLOAD-DIAG] Rejected upload enqueue request from {Username} ({Endpoint}) for {Filename}: {Reason}",
                        username,
                        endpoint,
                        filename,
                        ex.Message);
                }

                throw;
            }
            finally
            {
                if (decisionStopwatch.IsRunning)
                {
                    decisionStopwatch.Stop();
                }

                // decision latency is reported here so that we can track both successes and failures; they do the same
                // work so lumping them together gives us the clearest picture
                Metrics.Enqueue.DecisionLatency.Observe(decisionStopwatch.ElapsedMilliseconds);
                Metrics.Enqueue.CurrentDecisionLatency.Update(decisionStopwatch.ElapsedMilliseconds);

                if (userSemaphoreAcquired)
                {
                    userSemaphore!.Release();
                }

                if (enqueueRequestsSemaphoreAcquired)
                {
                    GlobalEnqueueSemaphore.Release();
                }
            }
        }

        private bool IsSelfUsername(string username)
        {
            return !string.IsNullOrWhiteSpace(Client.Username)
                && string.Equals(username, Client.Username, StringComparison.OrdinalIgnoreCase);
        }

        /// <summary>
        ///     Creates and returns an instances of <see cref="BrowseResponse"/> in response to a remote request.
        /// </summary>
        /// <param name="username">The username of the requesting user.</param>
        /// <param name="endpoint">The IP endpoint of the requesting user.</param>
        /// <returns>A Task resolving an IEnumerable of Soulseek.Directory.</returns>
        private async Task<BrowseResponse> BrowseResponseResolver(string username, IPEndPoint endpoint)
        {
            Metrics.Browse.RequestsReceived.Inc(1);

            if (Users.IsBlacklisted(username, endpoint.Address))
            {
                Log.Information("Returned empty browse listing for blacklisted user {Username} ({IP})",
                    LoggingSanitizer.SanitizeExternalIdentifier(username), LoggingSanitizer.SanitizeIpAddress(endpoint.Address));
                return new BrowseResponse();
            }

            try
            {
                var sw = new Stopwatch();
                sw.Start();

                BrowseResponse? response = null;

                var cacheFilename = Path.Combine(Program.DataDirectory, "browse.cache");
                var cacheFileInfo = Files.ResolveFileInfo(cacheFilename);

                if (!cacheFileInfo.Exists)
                {
                    Log.Warning("Browse response not cached. Rebuilding...");
                    response = await CacheBrowseResponse();
                }
                else
                {
                    var stream = OpenBrowseCacheReadStream(cacheFilename);
                    response = new RawBrowseResponse(cacheFileInfo.Length, stream);
                }

                Log.Information("Sent browse response to {User}", LoggingSanitizer.SanitizeExternalIdentifier(username));

                sw.Stop();

                Metrics.Browse.ResponseLatency.Observe(sw.ElapsedMilliseconds);
                Metrics.Browse.CurrentResponseLatency.Update(sw.ElapsedMilliseconds);
                Metrics.Browse.ResponsesSent.Inc(1);

                return response;
            }
            catch (Exception ex)
            {
                Log.Warning("Failed to resolve browse response: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        private void Client_BrowseProgressUpdated(object? sender, BrowseProgressUpdatedEventArgs args)
        {
            BrowseTracker.AddOrUpdate(args.Username, args);
        }

        private void Client_Connected(object? sender, EventArgs e)
        {
            ConnectionWatchdog.Stop();
            Log.Information("Connected to the Soulseek server");
            UpdateTrackedUsersState();

            EventBus.Raise(new Events.SoulseekClientConnectedEvent());
        }

        private void Client_DiagnosticGenerated(object? sender, DiagnosticEventArgs args)
        {
            static LogEventLevel TranslateLogLevel(DiagnosticLevel diagnosticLevel) => diagnosticLevel switch
            {
                DiagnosticLevel.Trace => LogEventLevel.Verbose,
                DiagnosticLevel.Debug => LogEventLevel.Debug,
                DiagnosticLevel.Info => LogEventLevel.Information,
                DiagnosticLevel.Warning => LogEventLevel.Warning,
                DiagnosticLevel.None => default,
                _ => default,
            };

            var source = sender?.GetType().FullName ?? "Unknown";

            if (source.EndsWith("DistributedConnectionManager") && !Options.Soulseek.DistributedNetwork.Logging)
            {
                return;
            }

            var logger = Loggers.GetOrAdd(source, Log.ForContext("Context", "Soulseek").ForContext("SubContext", source));

            var level = TranslateLogLevel(args.Level);

            // Soulseek.NET races a Timer dispose against late SearchResponses after a search
            // completes; the resulting ObjectDisposedException on System.Timers.Timer is
            // surfaced as a Warning "Error handling peer message: SearchResponse ...". It is
            // benign — the search is already finished — so quiet it to Debug to keep the log
            // signal-to-noise high. Upstream library bug (Soulseek v10.0.0).
            if (level == LogEventLevel.Warning
                && args.Exception is ObjectDisposedException ode
                && ode.ObjectName == "System.Timers.Timer"
                && !string.IsNullOrEmpty(args.Message)
                && args.Message.Contains("handling peer message", StringComparison.OrdinalIgnoreCase))
            {
                level = LogEventLevel.Debug;
            }

            if (args.IncludesException && OptionsAtStartup.Debug)
            {
                logger.Write(
                    level,
                    "{Message} {Exception}",
                    LoggingSanitizer.SanitizeExternalIdentifier(args.Message),
                    LoggingSanitizer.SanitizeExternalIdentifier(args.Exception?.ToString()));
                return;
            }

            logger.Write(level, "{@Message}", LoggingSanitizer.SanitizeExternalIdentifier(args.Message));
        }

        private void Client_Disconnected(object? sender, SoulseekClientDisconnectedEventArgs args)
        {
            ClearTrackedUsersState();

            if (State.CurrentValue.PendingReconnect)
            {
                State.SetValue(state => state with { PendingReconnect = false });
            }

            if (args.Exception is ObjectDisposedException || args.Exception is ApplicationShutdownException)
            {
                Log.Information("Disconnected from the Soulseek server: the client is shutting down");
            }
            else if (args.Exception is IntentionalDisconnectException)
            {
                Log.Information("Disconnected from the Soulseek server: disconnected by the user");
            }
            else if (args.Exception is LoginRejectedException)
            {
                Log.Error("Disconnected from the Soulseek server: invalid username or password");
            }
            else if (args.Exception is KickedFromServerException)
            {
                Log.Error("Disconnected from the Soulseek server: another client logged in using the same username");
            }
            else if (args.Exception is VPNClientException)
            {
                Log.Error("Disconnected from the Soulseek server; VPN is required and the VPN client has gone down");
                ConnectionWatchdog.Start();
            }
            else
            {
                Log.Error("Disconnected from the Soulseek server: {Message}",
                    LoggingSanitizer.SanitizeExternalIdentifier(args.Exception?.Message ?? args.Message));
                ConnectionWatchdog.Start();
            }

            EventBus.Raise(new Events.SoulseekClientDisconnectedEvent()
            {
                Message = args.Message,
                Exception = args.Exception,
            });
        }

        private async Task RefreshUserStatistics(bool force = false)
        {
            if (force || !Cache.TryGetValue(CacheKeys.UserStatisticsToken, out _))
            {
                var stats = await Client.GetUserStatisticsAsync(Client.Username);
                var privileges = await Client.GetPrivilegesAsync();

                State.SetValue(state => state with
                {
                    User = state.User with
                    {
                        Statistics = stats.ToUserStatisticsState(),
                        Privileges = new UserPrivilegeState()
                        {
                            IsPrivileged = privileges > 0,
                            PrivilegesRemaining = privileges,
                        },
                    },
                });

                Cache.Set(CacheKeys.UserStatisticsToken, true, TimeSpan.FromHours(4));
            }
        }

        private void Client_LoggedIn(object? sender, EventArgs e)
            => _ = ObserveBackgroundTaskAsync(HandleClientLoggedInAsync(), "Failed to execute post-login actions");

        private async Task HandleClientLoggedInAsync()
        {
            Log.Information("Logged in to the Soulseek server as {Username}", LoggingSanitizer.SanitizeExternalIdentifier(Client.Username));

            // send whatever counts we have currently. we'll probably connect before the cache is primed, so these will be zero
            // initially, but we'll update them when the cache is filled.
            await Client.SetSharedCountsAsync(State.CurrentValue.Shares.Directories, State.CurrentValue.Shares.Files);

            // fetch our average upload speed from the server, so we can provide it along with search results
            await RefreshUserStatistics(force: true);

            await PublishConfiguredInterestsAsync();

            // we previously saved a list of all of the download ids that were active at the previous shutdown; fetch the latest
            // record for those transfers from the db and ensure they haven't been removed from the UI while the application was offline
            // the user doesn't want those transfers anymore and we don't want to add them back.
            var resumableDownloads = Transfers.Downloads.List(t => !t.Removed && ActiveDownloadIdsAtPreviousShutdown.Contains(t.Id));

            var blockedResumableDownloads = resumableDownloads
                .Where(download => DownloadFilter.IsExcluded(
                    download.Filename,
                    OptionsMonitor.CurrentValue.Filters.Download.Exclude))
                .ToList();
            foreach (var blockedDownload in blockedResumableDownloads)
            {
                Transfers.Downloads.TryCancel(blockedDownload.Id);
            }

            if (blockedResumableDownloads.Count > 0)
            {
                Log.Information(
                    "Skipped {Count} previously active download(s) blocked by the global download policy",
                    blockedResumableDownloads.Count);
                resumableDownloads = resumableDownloads
                    .Except(blockedResumableDownloads)
                    .ToList();
            }

            if (resumableDownloads.Any())
            {
                Log.Information("Attempting to re-enqueue previously active downloads...");

                var groups = resumableDownloads.GroupBy(d => d.Username);

                // re-request downloads. we use a try/catch here because there's a very good chance that the other user is offline.
                foreach (var group in groups)
                {
                    var username = group.Key;
                    var files = group.Select(f => (f.Filename, f.Size));

                    try
                    {
                        await Transfers.Downloads.EnqueueAsync(username, files);
                    }
                    catch (Exception ex)
                    {
                        Log.Warning("Failed to re-enqueue {Count} file(s) from {Username}: {Message}", files.Count(),
                            LoggingSanitizer.SanitizeExternalIdentifier(username), LoggingSanitizer.SanitizeExternalIdentifier(ex.Message));
                    }
                }
            }

            // clear the ids we saved at startup; we don't want to re-request these again if the connection is cycled
            ActiveDownloadIdsAtPreviousShutdown = [];
        }

        private async Task PublishConfiguredInterestsAsync()
        {
            var liked = OptionsMonitor.CurrentValue.Soulseek.LikedInterests
                .Select(interest => interest?.Trim())
                .Where(interest => !string.IsNullOrWhiteSpace(interest))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToList();
            var hated = OptionsMonitor.CurrentValue.Soulseek.HatedInterests
                .Select(interest => interest?.Trim())
                .Where(interest => !string.IsNullOrWhiteSpace(interest))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToList();

            foreach (var interest in liked)
            {
                try
                {
                    await Client.AddInterestAsync(interest).ConfigureAwait(false);
                }
                catch (Exception ex)
                {
                    Log.Warning("Failed to publish configured Soulseek liked interest {Interest}: {Message}",
                        LoggingSanitizer.SanitizeExternalIdentifier(interest), LoggingSanitizer.SanitizeExternalIdentifier(ex.Message));
                }
            }

            foreach (var interest in hated)
            {
                try
                {
                    await Client.AddHatedInterestAsync(interest).ConfigureAwait(false);
                }
                catch (Exception ex)
                {
                    Log.Warning("Failed to publish configured Soulseek disliked interest {Interest}: {Message}",
                        LoggingSanitizer.SanitizeExternalIdentifier(interest), LoggingSanitizer.SanitizeExternalIdentifier(ex.Message));
                }
            }
        }

        private void Client_PrivateMessageReceived(object? sender, PrivateMessageReceivedEventArgs args)
        {
            if (Users.IsBlacklisted(args.Username))
            {
                Log.Debug("Ignored private message from blacklisted user {Username}", LoggingSanitizer.SanitizeExternalIdentifier(args.Username));
                return;
            }
            else
            {
                // todo: raise blacklisted message event?
            }

            // HARDENING: Handle PODMSG group pod messages
            if (args.Message.StartsWith("PODMSG:", StringComparison.Ordinal))
            {
                _ = ObserveBackgroundTaskAsync(
                    Task.Run(() => HandlePodMessageAsync(args.Username, args.Message), CancellationToken.None),
                    "Failed to handle pod message from {Username}",
                    LoggingSanitizer.SanitizeExternalIdentifier(args.Username));
                return; // Don't process as regular PM
            }

            Messaging.Conversations.HandleMessageAsync(args.Username, PrivateMessage.FromEventArgs(args));

            if (!args.Replayed)
            {
                if (ShouldAutoRespondToHumanChallenge(args.Username, args.Message))
                {
                    _ = ObserveBackgroundTaskAsync(
                        SendHumanChallengeAutoResponseAsync(args.Username),
                        "Failed to send human-check auto response to {Username}",
                        LoggingSanitizer.SanitizeExternalIdentifier(args.Username));
                }

                _ = ObserveBackgroundTaskAsync(
                    Notifications.SendPrivateMessageAsync(args.Username, args.Message),
                    "Failed to send private-message notification from {Username}",
                    LoggingSanitizer.SanitizeExternalIdentifier(args.Username));
            }
        }

        private bool ShouldAutoRespondToHumanChallenge(string username, string message)
        {
            var autoResponse = Options.Soulseek.PrivateMessageAutoResponse;

            if (!autoResponse.Enabled ||
                string.IsNullOrWhiteSpace(autoResponse.Message) ||
                string.IsNullOrWhiteSpace(message) ||
                !IsPrivateMessageAutoResponseCandidate(message))
            {
                return false;
            }

            var cooldown = TimeSpan.FromMinutes(autoResponse.CooldownMinutes);
            var now = DateTimeOffset.UtcNow;

            if (HumanChallengeAutoResponseSentAt.TryGetValue(username, out var previous) &&
                now - previous < cooldown)
            {
                return false;
            }

            HumanChallengeAutoResponseSentAt[username] = now;
            return true;
        }

        internal static bool IsHumanChallengePrivateMessage(string message)
        {
            if (string.IsNullOrWhiteSpace(message))
            {
                return false;
            }

            var normalized = Regex.Replace(message.Trim(), @"\s+", " ");

            if (HumanChallengeDirectQuestionRegex.IsMatch(normalized) ||
                HumanChallengeNamedCheckRegex.IsMatch(normalized))
            {
                return true;
            }

            return HumanChallengeIntentRegex.IsMatch(normalized) &&
                HumanChallengeIdentityRegex.IsMatch(normalized);
        }

        internal static bool IsPrivateMessageAutoResponseCandidate(string message)
        {
            return IsHumanChallengePrivateMessage(message) ||
                IsShareGatePrivateMessage(message);
        }

        internal static bool IsShareGatePrivateMessage(string message)
        {
            if (string.IsNullOrWhiteSpace(message))
            {
                return false;
            }

            var normalized = Regex.Replace(message.Trim(), @"\s+", " ");
            return ShareGatePrivateMessageRegex.IsMatch(normalized);
        }

        private Task SendHumanChallengeAutoResponseAsync(string username)
        {
            var message = Options.Soulseek.PrivateMessageAutoResponse.Message.Trim();
            Log.Information("Sending human-check auto response to {Username}", LoggingSanitizer.SanitizeExternalIdentifier(username));
            return Messaging.Conversations.SendMessageAsync(username, message);
        }

        /// <summary>
        /// Handles inbound pod messages received via private messages.
        /// </summary>
        private async Task HandlePodMessageAsync(string username, string message)
        {
            try
            {
                // HARDENING: Enforce maximum message size before parsing (16KB limit)
                const int MaxMessageSize = 16 * 1024;
                if (message.Length > MaxMessageSize)
                {
                    Log.Warning("Pod message from {Username} exceeds size limit ({Size} > {MaxSize})",
                        LoggingSanitizer.SanitizeExternalIdentifier(username), message.Length, MaxMessageSize);
                    return;
                }

                // Extract JSON payload after "PODMSG:" prefix
                if (!message.StartsWith("PODMSG:", StringComparison.Ordinal) || message.Length <= "PODMSG:".Length)
                {
                    Log.Warning("Invalid PODMSG format from {Username}", LoggingSanitizer.SanitizeExternalIdentifier(username));
                    return;
                }

                var jsonPayload = message.Substring("PODMSG:".Length);

                // HARDENING: Enforce JSON payload size limit (12KB for actual JSON)
                const int MaxJsonSize = 12 * 1024;
                if (jsonPayload.Length > MaxJsonSize)
                {
                    Log.Warning("Pod message JSON payload from {Username} exceeds size limit ({Size} > {MaxSize})",
                        LoggingSanitizer.SanitizeExternalIdentifier(username), jsonPayload.Length, MaxJsonSize);
                    return;
                }

                // Parse PodMessage from JSON with strict options
                var options = new JsonSerializerOptions
                {
                    MaxDepth = 3, // Prevent deep nesting attacks
                    AllowTrailingCommas = false,
                    ReadCommentHandling = JsonCommentHandling.Disallow
                };

                var podMessage = JsonSerializer.Deserialize<PodCore.PodMessage>(jsonPayload, options);
                if (podMessage == null)
                {
                    Log.Warning("Failed to parse pod message JSON from {Username}", LoggingSanitizer.SanitizeExternalIdentifier(username));
                    return;
                }

                // HARDENING: Validate sender matches the message sender peer ID
                var expectedPeerId = $"bridge:{username}";
                if (podMessage.SenderPeerId != expectedPeerId)
                {
                    Log.Warning("Pod message sender validation failed: expected {Expected}, got {Actual} from {Username}",
                        LoggingSanitizer.SanitizeExternalIdentifier(expectedPeerId),
                        LoggingSanitizer.SanitizeExternalIdentifier(podMessage.SenderPeerId),
                        LoggingSanitizer.SanitizeExternalIdentifier(username));
                    return;
                }

                // HARDENING: Additional validation - ensure PodId and ChannelId are present and valid
                if (string.IsNullOrWhiteSpace(podMessage.PodId) || string.IsNullOrWhiteSpace(podMessage.ChannelId))
                {
                    Log.Warning("Pod message missing required PodId or ChannelId from {Username}", LoggingSanitizer.SanitizeExternalIdentifier(username));
                    return;
                }

                if (!PodCore.PodValidation.IsValidPodId(podMessage.PodId) || !PodCore.PodValidation.IsValidChannelId(podMessage.ChannelId))
                {
                    Log.Warning("Pod message contains invalid PodId or ChannelId from {Username}", LoggingSanitizer.SanitizeExternalIdentifier(username));
                    return;
                }

                // Store via IPodMessaging (using IServiceScopeFactory since IPodMessaging is Scoped)
                if (ServiceScopeFactory != null)
                {
                    using var scope = ServiceScopeFactory.CreateScope();
                    var podMessaging = scope.ServiceProvider.GetService<PodCore.IPodMessaging>();
                    if (podMessaging != null)
                    {
                        var stored = await podMessaging.SendAsync(podMessage);
                        if (stored)
                        {
                            Log.Debug("Stored pod message {MessageId} from {Username} in pod {PodId} channel {ChannelId}",
                                LoggingSanitizer.SanitizeExternalIdentifier(podMessage.MessageId),
                                LoggingSanitizer.SanitizeExternalIdentifier(username),
                                LoggingSanitizer.SanitizeExternalIdentifier(podMessage.PodId),
                                LoggingSanitizer.SanitizeExternalIdentifier(podMessage.ChannelId));
                        }
                        else
                        {
                            Log.Warning("Failed to store pod message {MessageId} from {Username}",
                                LoggingSanitizer.SanitizeExternalIdentifier(podMessage.MessageId),
                                LoggingSanitizer.SanitizeExternalIdentifier(username));
                        }
                    }
                    else
                    {
                        Log.Warning("IPodMessaging service not available, pod message {MessageId} from {Username} was not stored",
                            LoggingSanitizer.SanitizeExternalIdentifier(podMessage.MessageId),
                            LoggingSanitizer.SanitizeExternalIdentifier(username));
                    }
                }
                else
                {
                    Log.Warning("ServiceScopeFactory not available, pod message {MessageId} from {Username} was not stored",
                        LoggingSanitizer.SanitizeExternalIdentifier(podMessage.MessageId),
                        LoggingSanitizer.SanitizeExternalIdentifier(username));
                }
            }
            catch (Exception ex)
            {
                Log.Error("Error handling pod message from {Username}: {Exception}",
                    LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
            }
        }

        private void Client_RoomMessageReceived(object? sender, RoomMessageReceivedEventArgs args)
        {
            // note: this event is also subscribed in the RoomService class
            // this handler is only used for notifications.
            if (Users.IsBlacklisted(args.Username))
            {
                return;
            }

            var message = RoomMessage.FromEventArgs(args, DateTime.UtcNow);

            if (message.Message.Contains(Client.Username))
            {
                _ = ObserveBackgroundTaskAsync(
                    Notifications.SendRoomMentionAsync(message.RoomName, message.Username, message.Message),
                    "Failed to send room-mention notification from {Username} in {RoomName}",
                    LoggingSanitizer.SanitizeExternalIdentifier(message.Username),
                    LoggingSanitizer.SanitizeExternalIdentifier(message.RoomName));
            }
        }

        private void Client_StateChanged(object? sender, SoulseekClientStateChangedEventArgs e)
        {
            State.SetValue(state => state with
            {
                Server = state.Server with
                {
                    Address = Client.State.HasFlag(SoulseekClientStates.Disconnected) ? string.Empty : Client.Address ?? string.Empty,
                    IPEndPoint = Client.State.HasFlag(SoulseekClientStates.Disconnected) ? new IPEndPoint(IPAddress.None, 0) : Client.IPEndPoint ?? new IPEndPoint(IPAddress.None, 0),
                    State = Client.State,
                },
                User = state.User with
                {
                    Username = Client.Username,
                },
            });
        }

        private void Client_DistributedNetworkStateChanged(object? sender, DistributedNetworkInfo e)
        {
            State.SetValue(state => state with
            {
                DistributedNetwork = new DistributedNetworkState()
                {
                    BranchLevel = e.BranchLevel,
                    BranchRoot = e.BranchRoot,
                    CanAcceptChildren = e.CanAcceptChildren,
                    ChildLimit = e.ChildLimit,
                    Children = e.Children.Select(c => c.Username).ToList().AsReadOnly(),
                    HasParent = e.HasParent,
                    IsBranchRoot = e.IsBranchRoot,
                    Parent = e.Parent.Username,
                },
            });

            Metrics.DistributedNetwork.HasParent.Set(e.HasParent ? 1 : 0);
            Metrics.DistributedNetwork.BranchLevel.Set(e.BranchLevel);
            Metrics.DistributedNetwork.ChildLimit.Set(e.ChildLimit);
            Metrics.DistributedNetwork.Children.Set(e.Children.Count);
        }

        private void Clock_EveryThirtySeconds(object? sender, ClockEventArgs e)
        {
            State.SetValue(state => state with
            {
                Health = state.Health with
                {
                    Search = state.Health.Search with
                    {
                        Incoming = state.Health.Search.Incoming with
                        {
                            Latency = Metrics.Search.Incoming.CurrentResponseLatency.Value,
                            QueueDepth = IncomingSearchRequestQueueDepth,
                            DropRate = Metrics.Search.Incoming.CurrentRequestDropRate.Count,
                        },
                    },
                },
            });
        }

        private void Clock_EveryMinute(object? sender, ClockEventArgs e)
        {
            Metrics.DistributedNetwork.BroadcastLatency.Observe(Client.DistributedNetwork.AverageBroadcastLatency ?? 0);
            Metrics.DistributedNetwork.CurrentBroadcastLatency.Set(Client.DistributedNetwork.AverageBroadcastLatency ?? 0);
        }

        private void Clock_EveryFiveMinutes(object? sender, ClockEventArgs e)
        {
            _ = ObserveBackgroundTaskAsync(Task.Run(() => PruneSearches(DateTime.UtcNow), CancellationToken.None), "Failed to prune searches");
            _ = ObserveBackgroundTaskAsync(Task.Run(() => PruneTransfers(), CancellationToken.None), "Failed to prune transfers");
            _ = ObserveBackgroundTaskAsync(Task.Run(() => PruneEvents(), CancellationToken.None), "Failed to prune events");
        }

        private void Clock_EveryThirtyMinutes(object? sender, ClockEventArgs e)
        {
            _ = ObserveBackgroundTaskAsync(Task.Run(() => PruneFiles(), CancellationToken.None), "Failed to prune files");
        }

        private void Clock_EveryHour(object? sender, ClockEventArgs e)
        {
            _ = ObserveBackgroundTaskAsync(Task.Run(() => MaybeRescanShares(), CancellationToken.None), "Failed to evaluate scheduled share rescan");
        }

        private async Task MaybeRescanShares()
        {
            // ignore this if we're already scanning. there are multiple safeguards using
            // SemaphoreSlim later in the call chain if we manage to slip by somehow, though
            if (Shares.StateMonitor.CurrentValue.Scanning)
            {
                return;
            }

            var ttl = Options.Shares.Cache.Retention;

            // no configured TTL; never re-scan automatically
            if (!ttl.HasValue)
            {
                return;
            }

            // "x minutes ago"
            var cutoffTimestamp = DateTimeOffset.UtcNow
                .AddMinutes(-ttl.Value)
                .ToUnixTimeMilliseconds();

            // get a list of all scans that 1) started after our cutoff timestamp
            var scansInRange = await Shares.ListScansAsync(startedAtOrAfter: cutoffTimestamp);

            // 2) that succeeded (have a valid EndedAt)
            // and 3) have not been marked suspect
            // if there's no scan that meets all 3 criteria, try to re-scan
            if (!scansInRange.Any(s => s.EndedAt is not null && !s.Suspect))
            {
                Log.Information("Beginning scheduled re-scan of shares (previous scan is older than {Minutes} minutes)", ttl);

                // fire and forget. if something slips through the underlying logic will log.
                _ = ObserveBackgroundTaskAsync(Task.Run(() => Shares.ScanAsync(), CancellationToken.None), "Failed to start scheduled share scan");
            }
        }

        private void PruneFiles()
        {
            void PruneDirectory(int? age, string directory)
            {
                try
                {
                    if (!age.HasValue)
                    {
                        return;
                    }

                    Log.Debug("Pruning files older than {Age} minutes from {Directory}", age, LoggingSanitizer.SanitizeFilePath(directory));
                    var result = PruneDirectoryFiles(age.Value, directory, Files, DateTime.UtcNow);
                    Log.Debug("Found {Count} files in need of pruning", result.Found);
                    Log.Debug("Pruning complete. Deleted: {Deleted}, Errors: {Errors}", result.Deleted, result.Errors);
                }
                catch (Exception ex)
                {
                    Log.Error("Failed to prune files in directory {Directory}: {Message}",
                        LoggingSanitizer.SanitizeFilePath(directory), LoggingSanitizer.SanitizeExternalIdentifier(ex.Message));
                }
            }

            PruneDirectory(age: Options.Retention.Files.Incomplete, directory: Options.Directories.Incomplete);
            PruneDirectory(age: Options.Retention.Files.Complete, directory: Options.Directories.Downloads);
        }

        internal static (int Found, int Deleted, int Errors) PruneDirectoryFiles(
            int age,
            string directory,
            FileService fileService,
            DateTime utcNow)
        {
            var options = new EnumerationOptions
            {
                IgnoreInaccessible = true,
                AttributesToSkip = FileAttributes.Hidden | FileAttributes.System,
                RecurseSubdirectories = true,
            };
            var cutoff = utcNow.AddMinutes(-age);
            var found = 0;
            var deleted = 0;
            var errors = 0;

            foreach (var filename in System.IO.Directory.EnumerateFiles(directory, "*", options))
            {
                var file = fileService.ResolveFileInfo(filename);
                if (file.LastAccessTimeUtc > cutoff)
                {
                    continue;
                }

                found++;
                try
                {
                    file.Delete();
                    deleted++;
                }
                catch (Exception ex)
                {
                    errors++;
                    Serilog.Log.Warning("Failed to prune file {File}: {Message}",
                        LoggingSanitizer.SanitizeFilePath(file.FullName), LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                }
            }

            return (found, deleted, errors);
        }

        private void PruneTransfers()
        {
            var options = OptionsMonitor.CurrentValue.Retention;

            void PruneUpload(int? age, TransferStates state)
            {
                if (age.HasValue)
                {
                    Transfers.Uploads.Prune(age.Value, TransferStates.Completed | state);
                }
            }

            void PruneDownload(int? age, TransferStates state)
            {
                if (age.HasValue)
                {
                    Transfers.Downloads.Prune(age.Value, TransferStates.Completed | state);
                }
            }

            try
            {
                PruneUpload(options.Transfers.Upload.Succeeded, TransferStates.Succeeded);
                PruneUpload(options.Transfers.Upload.Cancelled, TransferStates.Cancelled);
                PruneUpload(options.Transfers.Upload.Errored, TransferStates.Errored);

                PruneDownload(options.Transfers.Download.Succeeded, TransferStates.Succeeded);
                PruneDownload(options.Transfers.Download.Cancelled, TransferStates.Cancelled);
                PruneDownload(options.Transfers.Download.Errored, TransferStates.Errored);

                if (options.Transfers.Removed.HasValue)
                {
                    Transfers.Uploads.PruneRemoved(options.Transfers.Removed.Value);
                    Transfers.Downloads.PruneRemoved(options.Transfers.Removed.Value);
                }
            }
            catch
            {
                Log.Error("Encountered one or more errors while pruning transfers");
            }
        }

        internal async Task PruneSearches(DateTime utcNow)
        {
            var age = OptionsMonitor.CurrentValue.Retention.Search;

            if (age.HasValue)
            {
                try
                {
                    var pruned = await Search.PruneAsync(age.Value);
                }
                catch
                {
                    Log.Error("Encountered one or more errors while pruning searches");
                }
            }

            // Apply search retention policy (cleanup based on max age and max count)
            var retentionConfig = OptionsMonitor.CurrentValue.Filters.SearchRetention;
            if ((retentionConfig.MaxAgeDays > 0 || retentionConfig.MaxCount > 0) &&
                TryBeginSearchRetentionCleanup(utcNow, retentionConfig.CleanupIntervalSeconds))
            {
                var succeeded = false;

                try
                {
                    var cleaned = await Search.CleanupAsync(retentionConfig.MaxAgeDays, retentionConfig.MaxCount);
                    succeeded = true;
                    if (cleaned > 0)
                    {
                        Log.Debug("Search retention cleanup removed {Count} searches", cleaned);
                    }
                }
                catch
                {
                    Log.Error("Encountered one or more errors while cleaning up searches");
                }
                finally
                {
                    CompleteSearchRetentionCleanup(utcNow, succeeded);
                }
            }
        }

        private bool TryBeginSearchRetentionCleanup(DateTime utcNow, int cleanupIntervalSeconds)
        {
            lock (_searchRetentionCleanupSyncRoot)
            {
                if (_searchRetentionCleanupRunning ||
                    (_lastSearchRetentionCleanupAt.HasValue &&
                     utcNow - _lastSearchRetentionCleanupAt.Value < TimeSpan.FromSeconds(cleanupIntervalSeconds)))
                {
                    return false;
                }

                _searchRetentionCleanupRunning = true;
                return true;
            }
        }

        private void CompleteSearchRetentionCleanup(DateTime startedAt, bool succeeded)
        {
            lock (_searchRetentionCleanupSyncRoot)
            {
                if (succeeded)
                {
                    _lastSearchRetentionCleanupAt = startedAt;
                }

                _searchRetentionCleanupRunning = false;
            }
        }

        private void PruneEvents()
        {
            var retention = OptionsMonitor.CurrentValue.Retention;

            try
            {
                EventService.PruneAsync(retention.Events, retention.EventsMaxCount);
            }
            catch
            {
                Log.Error("Encountered one or more errors while pruning events");
            }
        }

        private void Client_ExcludedSearchPhrasesReceived(object? sender, IReadOnlyCollection<string> e)
        {
            Log.Debug("Excluded search phrases: {Phrases}", string.Join(", ", e));
            ExcludedSearchPhrases = e.ToList();
        }

        private static string TransferCompositeKey(Soulseek.Transfer transfer)
            => $"{transfer.Direction}|{transfer.Username}|{transfer.Filename}";

        private global::slskd.Transfers.Transfer? ResolveTransferRecord(Soulseek.Transfer xfer)
        {
            try
            {
                return xfer.Direction == TransferDirection.Download
                    ? Transfers.Downloads.Find(t => t.Username == xfer.Username && t.Filename == xfer.Filename)
                    : Transfers.Uploads.Find(t => t.Username == xfer.Username && t.Filename == xfer.Filename);
            }
            catch
            {
                // Best-effort enrichment only. Clients fall back to the
                // (direction, username, filename) composite key and the periodic reconcile.
                return null;
            }
        }

        private void Client_TransferProgressUpdated(object? sender, TransferProgressUpdatedEventArgs args)
        {
            // Progress events fire very frequently. Coalesce to ~1 Hz per transfer by
            // sampling (dropping intermediate ticks); the terminal state-change event
            // carries the final bytes/percent so a dropped last sample self-corrects.
            var xfer = args.Transfer;

            if (xfer.Direction == TransferDirection.Download)
            {
                TrafficAccounting.RecordSoulseekDownloadProgress(
                    xfer.Token,
                    xfer.BytesTransferred,
                    xfer.StartOffset);
            }

            if (!xfer.State.HasFlag(TransferStates.InProgress))
            {
                return;
            }

            var key = TransferCompositeKey(xfer);
            var now = Environment.TickCount64;

            if (TransferProgressLastEmitTicks.TryGetValue(key, out var last) &&
                now - last < TransferProgressEmitIntervalMs)
            {
                return;
            }

            TransferProgressLastEmitTicks[key] = now;

            var progress = TransferActivity.FromTransferProgress(xfer, ResolveTransferRecord(xfer));
            _ = ObserveBackgroundTaskAsync(
                TransferHubExtensions.EmitTransferProgressAsync(TransfersHub, progress),
                "Failed to broadcast transfer progress for {Filename} from {Username}",
                LoggingSanitizer.SanitizeFilePath(xfer.Filename),
                LoggingSanitizer.SanitizeExternalIdentifier(xfer.Username));
        }

        private void Client_TransferStateChanged(object? sender, TransferStateChangedEventArgs args)
        {
            var xfer = args.Transfer;
            if (xfer.Direction == TransferDirection.Upload)
            {
                Cache.Remove(GetQueuedUploadLimitSnapshotKey(xfer.Username));
            }

            var direction = xfer.Direction.ToString().ToUpper();
            var user = xfer.Username;
            var file = xfer.Filename;
            var oldState = args.PreviousState;
            var state = xfer.State;

            var completed = xfer.State.HasFlag(TransferStates.Completed);

            if (completed && xfer.Direction == TransferDirection.Download)
            {
                QueueSoulseekDownloadAccountingCommit(xfer);
            }

            var progress = completed
                ? FormatCompletedTransferProgress(xfer.BytesTransferred, xfer.Size, xfer.PercentComplete, xfer.AverageSpeed)
                : string.Empty;
            Log.Information("[{Direction}] [{Username}/{Filename}] {PreviousState} => {State}{Progress}",
                direction,
                LoggingSanitizer.SanitizeExternalIdentifier(user),
                LoggingSanitizer.SanitizeFilePath(file),
                oldState,
                state,
                progress);

            if (completed)
            {
                // Stop tracking progress throttle state for finished transfers.
                TransferProgressLastEmitTicks.TryRemove(TransferCompositeKey(xfer), out _);
            }

            // Broadcast transfer activity to connected clients
            var activity = TransferActivity.FromTransferStateChange(xfer, oldState, ResolveTransferRecord(xfer));
            _ = ObserveBackgroundTaskAsync(
                TransferHubExtensions.EmitTransferActivityAsync(TransfersHub, activity),
                "Failed to broadcast transfer activity for {Filename} from {Username}",
                LoggingSanitizer.SanitizeFilePath(xfer.Filename),
                LoggingSanitizer.SanitizeExternalIdentifier(xfer.Username));

            if (xfer.Direction == TransferDirection.Upload && xfer.State.HasFlag(TransferStates.Completed | TransferStates.Succeeded) && args.Transfer.AverageSpeed > 0)
            {
                _ = ObserveBackgroundTaskAsync(
                    Client.SendUploadSpeedAsync(Convert.ToInt32(Math.Ceiling(args.Transfer.AverageSpeed))),
                    "Failed to report upload speed for {Username}",
                    LoggingSanitizer.SanitizeExternalIdentifier(xfer.Username));
            }
        }

        internal static string FormatCompletedTransferProgress(long bytesTransferred, long size, double percentComplete, double averageSpeed)
        {
            var displaySpeed = Math.Max(0, averageSpeed);
            return $" ({bytesTransferred}/{size} = {percentComplete}%) @ {displaySpeed.SizeSuffix()}/s";
        }

        private void QueueSoulseekDownloadAccountingCommit(Soulseek.Transfer transfer)
        {
            var completion = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            if (!ActiveSoulseekDownloadAccountingCommits.TryAdd(transfer.Token, completion.Task))
            {
                return;
            }

            _ = ObserveSoulseekDownloadAccountingCommitAsync(transfer, completion);
        }

        private async Task ObserveSoulseekDownloadAccountingCommitAsync(
            Soulseek.Transfer transfer,
            TaskCompletionSource<bool> completion)
        {
            try
            {
                await TrafficAccounting.CommitSoulseekDownloadAsync(
                    transfer.Token,
                    transfer.BytesTransferred,
                    transfer.StartOffset).ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                Log.Error("Failed to account Soulseek download traffic for {Filename} from {Username}: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename),
                    LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
            }
            finally
            {
                completion.TrySetResult(true);
                ActiveSoulseekDownloadAccountingCommits.TryRemove(transfer.Token, out _);
            }
        }

        private async Task DrainSoulseekDownloadAccountingCommitsAsync()
        {
            while (!ActiveSoulseekDownloadAccountingCommits.IsEmpty)
            {
                var commits = ActiveSoulseekDownloadAccountingCommits.Values.ToArray();
                if (commits.Length > 0)
                {
                    await Task.WhenAll(commits).ConfigureAwait(false);
                }
            }
        }

        private void Client_UserStatusChanged(object? sender, UserStatus args)
        {
            UpdateTrackedUsersState();
        }

        private void Users_WatchedUsersChanged(object? sender, EventArgs args)
        {
            UpdateTrackedUsersState();
        }

        private void UpdateTrackedUsersState()
        {
            var watchedUsernames = new HashSet<string>(Users.WatchedUsernames, StringComparer.OrdinalIgnoreCase);
            var users = Users.Users
                .Where(user => watchedUsernames.Contains(user.Username))
                .OrderBy(user => user.Username, StringComparer.OrdinalIgnoreCase)
                .ThenBy(user => user.Username, StringComparer.Ordinal)
                .ToArray();

            if (!State.CurrentValue.Users.SequenceEqual(users))
            {
                State.SetValue(state => state with { Users = users });
            }
        }

        private void ClearTrackedUsersState()
        {
            if (State.CurrentValue.Users.Length > 0)
            {
                State.SetValue(state => state with { Users = Array.Empty<User>() });
            }
        }

        private Task<int?> PlaceInQueueResolver(string username, IPEndPoint endpoint, string filename)
        {
            try
            {
                if (Users.IsBlacklisted(username, endpoint.Address))
                {
                    return Task.FromResult<int?>(null);
                }

                var place = Transfers.Uploads.Queue.EstimatePosition(username, filename);
                return Task.FromResult((int?)place);
            }
            catch (NotFoundException)
            {
                return Task.FromResult<int?>(null);
            }
            catch (Exception ex)
            {
                Log.Warning("Failed to estimate place in queue for {Filename} requested by {Username}: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        /// <summary>
        ///     Creates and returns a <see cref="Soulseek.Directory"/> in response to a remote request.
        /// </summary>
        /// <param name="username">The username of the requesting user.</param>
        /// <param name="endpoint">The IP endpoint of the requesting user.</param>
        /// <param name="token">The unique token for the request, supplied by the requesting user.</param>
        /// <param name="directory">The requested directory.</param>
        /// <returns>A Task resolving an instance of Soulseek.Directory containing the contents of the requested directory.</returns>
        private async Task<IEnumerable<Soulseek.Directory>> DirectoryContentsResponseResolver(string username, IPEndPoint endpoint, int token, string directory)
        {
            if (Users.IsBlacklisted(username, endpoint.Address))
            {
                Log.Information("Returned empty directory listing for blacklisted user {Username} ({IP})",
                    LoggingSanitizer.SanitizeExternalIdentifier(username), LoggingSanitizer.SanitizeIpAddress(endpoint.Address));
                return [new Soulseek.Directory(directory)];
            }

            try
            {
                var dir = await Shares.ListDirectoryAsync(directory);
                return [dir];
            }
            catch (Exception ex)
            {
                Log.Warning("Failed to resolve directory contents: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        private async Task OptionsMonitor_OnChange(Options newOptions)
        {
            // this code is known to fire more than once per update. i'm not sure whether these might be executed concurrently.
            // lock to be safe, because we need to accurately track the last value of Options for diffing purposes. threading
            // shenanigans here could lead to missed updates.
            await OptionsSyncRoot.WaitAsync();

            Log.Debug("OptionsMonitor OnChange Invoked");

            try
            {
                var pendingRestart = false;
                var pendingReconnect = false;
                var soulseekRequiresReconnect = false;

                var diff = PreviousOptions.DiffWith(newOptions);

                // don't react to duplicate/no-change events https://github.com/slskd/slskd/issues/126
                if (!diff.Any())
                {
                    Log.Debug("Diff of previous and new options is the same; nothing to do");
                    return;
                }

                Log.Debug("Diff of previous and new options contains {Count} changed properties: {Properties}", diff.Count(), diff.Select(p => p.FQN));

                foreach (var (property, fqn, left, right) in diff)
                {
                    static bool HasAttribute<T>(PropertyInfo? property) => property?.CustomAttributes.Any(a => a.AttributeType == typeof(T)) ?? false;
                    static string FormatOptionLogValue(PropertyInfo? property, object? value)
                    {
                        if (HasAttribute<SecretAttribute>(property))
                        {
                            return "*****";
                        }

                        return value?.ToJson() ?? "<null>";
                    }

                    var requiresRestart = HasAttribute<RequiresRestartAttribute>(property);
                    var requiresReconnect = HasAttribute<RequiresReconnectAttribute>(property);

                    Log.Debug($"{fqn} changed from '{FormatOptionLogValue(property, left)}' to '{FormatOptionLogValue(property, right)}'{(requiresRestart ? ". Restart required to take effect." : string.Empty)}{(requiresReconnect ? "; Reconnect required to take effect." : string.Empty)}");

                    pendingRestart |= requiresRestart;
                    pendingReconnect |= requiresReconnect;
                }

                if (PreviousOptions.Shares.Directories.Except(newOptions.Shares.Directories).Any()
                    || newOptions.Shares.Directories.Except(PreviousOptions.Shares.Directories).Any())
                {
                    State.SetValue(state => state with { Shares = state.Shares with { ScanPending = true } });
                    Log.Information("Shared directory configuration changed.  Shares must be re-scanned for changes to take effect.");
                }

                if (PreviousOptions.Shares.Filters.Except(newOptions.Shares.Filters).Any()
                    || newOptions.Shares.Filters.Except(PreviousOptions.Shares.Filters).Any())
                {
                    State.SetValue(state => state with { Shares = state.Shares with { ScanPending = true } });
                    Log.Information("File filter configuration changed.  Shares must be re-scanned for changes to take effect.");
                }

                if (PreviousOptions.Filters.Search.Request.Except(newOptions.Filters.Search.Request).Any()
                    || newOptions.Filters.Search.Request.Except(PreviousOptions.Filters.Search.Request).Any())
                {
                    CompiledSearchRequestFilters = CompileSearchRequestFilters(
                        newOptions.Filters.Search.Request,
                        Flags.CaseSensitiveRegEx);

                    Log.Information("Updated and re-compiled search response filters");
                }

                var previousDownloadExclusions = PreviousOptions.Filters.Download.Exclude ?? Array.Empty<string>();
                var newDownloadExclusions = newOptions.Filters.Download.Exclude ?? Array.Empty<string>();
                if (previousDownloadExclusions.Except(newDownloadExclusions, StringComparer.OrdinalIgnoreCase).Any()
                    || newDownloadExclusions.Except(previousDownloadExclusions, StringComparer.OrdinalIgnoreCase).Any())
                {
                    var newlyBlockedDownloads = Transfers.Downloads
                        .List(download => !download.State.HasFlag(TransferStates.Completed))
                        .Where(download => DownloadFilter.IsExcluded(download.Filename, newDownloadExclusions))
                        .ToList();

                    foreach (var download in newlyBlockedDownloads)
                    {
                        Transfers.Downloads.TryCancel(download.Id);
                    }

                    Log.Information(
                        "Updated global download exclusions; cancelled {Count} active download(s) now blocked by policy",
                        newlyBlockedDownloads.Count);
                }

                if (PreviousOptions.Rooms.Except(newOptions.Rooms).Any()
                    || newOptions.Rooms.Except(PreviousOptions.Rooms).Any())
                {
                    Log.Information("Room configuration changed.  Joining any newly added rooms.");
                    _ = ObserveBackgroundTaskAsync(
                        RoomService.TryJoinAsync(newOptions.Rooms),
                        "Failed to join rooms after configuration update");
                }

                // cancel active transfers for users newly added to the blacklist (#21)
                var previousBlacklist = PreviousOptions.Groups?.Blacklisted?.Members ?? Array.Empty<string>();
                var newBlacklist = newOptions.Groups?.Blacklisted?.Members ?? Array.Empty<string>();
                var newlyBlacklisted = newBlacklist.Except(previousBlacklist, StringComparer.OrdinalIgnoreCase).ToList();

                if (newlyBlacklisted.Count > 0)
                {
                    Log.Information(
                        "Cancelling active transfers for {Count} newly blacklisted user(s): {Users}",
                        newlyBlacklisted.Count,
                        newlyBlacklisted.Select(LoggingSanitizer.SanitizeExternalIdentifier).ToArray());

                    foreach (var username in newlyBlacklisted)
                    {
                        foreach (var download in Transfers.Downloads.List(t => string.Equals(t.Username, username, StringComparison.OrdinalIgnoreCase) && !t.State.HasFlag(TransferStates.Completed)))
                            Transfers.Downloads.TryCancel(download.Id);

                        foreach (var upload in Transfers.Uploads.List(t => string.Equals(t.Username, username, StringComparison.OrdinalIgnoreCase) && !t.State.HasFlag(TransferStates.Completed), includeRemoved: false))
                            Transfers.Uploads.TryCancel(upload.Id);
                    }
                }

                // determine whether any Soulseek options changed. if so, we need to construct a patch and invoke ReconfigureOptionsAsync().
                var slskDiff = PreviousOptions.Soulseek.DiffWith(newOptions.Soulseek);
                var globalDiff = PreviousOptions.Global.DiffWith(newOptions.Global);

                if (slskDiff.Any() || globalDiff.Any())
                {
                    var old = PreviousOptions.Soulseek;
                    var update = newOptions.Soulseek;

                    Log.Debug("Soulseek options changed from {Previous} to {Current}", PreviousOptions.Redact().Soulseek.ToJson(), newOptions.Redact().Soulseek.ToJson());

                    // determine whether any Connection options changed. if so, replace the whole object. Soulseek.NET doesn't
                    // offer a way to patch parts of connection options. the updates only affect new connections, so a partial
                    // patch doesn't make a lot of sense anyway.
                    var connectionDiff = old.Connection.DiffWith(update.Connection);

                    ConnectionOptions? connectionPatch = null;
                    ConnectionOptions? serverPatch = null;
                    ConnectionOptions? distributedPatch = null;
                    ConnectionOptions? transferPatch = null;
                    PeerObfuscationOptions? peerObfuscationPatch = null;

                    if (connectionDiff.Any())
                    {
                        var connection = update.Connection;

                        ProxyOptions? proxyPatch = null;

                        if (connection.Proxy.Enabled)
                        {
                            proxyPatch = new ProxyOptions(
                                address: connection.Proxy.Address,
                                port: connection.Proxy.Port.GetValueOrDefault(),
                                username: connection.Proxy.Username,
                                password: connection.Proxy.Password);
                        }

                        connectionPatch = new ConnectionOptions(
                            readBufferSize: connection.Buffer.Read,
                            writeBufferSize: connection.Buffer.Write,
                            writeQueueSize: connection.Buffer.WriteQueue,
                            connectTimeout: connection.Timeout.Connect,
                            inactivityTimeout: connection.Timeout.Inactivity,
                            proxyOptions: proxyPatch);

                        serverPatch = connectionPatch.With(
                            inactivityTimeout: -1, // don't disconnect due to inactivity
                            configureSocket: socket =>
                            {
                                ConfigureSocketKeepaliveOptions(socket, options: connection);
                                ConfigureSocketMtu(socket, options: connection);
                            });

                        distributedPatch = connectionPatch.With(
                            writeQueueSize: connection.Buffer.WriteQueue, // write queue set to keep distributed children from impacting performance
                            configureSocket: socket => ConfigureSocketKeepaliveOptions(socket, options: connection));

                        transferPatch = connectionPatch.With(
                            readBufferSize: OptionsAtStartup.Soulseek.Connection.Buffer.Transfer,
                            writeBufferSize: OptionsAtStartup.Soulseek.Connection.Buffer.Transfer,
                            inactivityTimeout: connection.Timeout.Transfer);
                    }

                    IPAddress? updateListenIpAddress = null;
                    if (!string.IsNullOrWhiteSpace(update.ListenIpAddress) && old.ListenIpAddress != update.ListenIpAddress)
                    {
                        if (!IPAddress.TryParse(update.ListenIpAddress, out updateListenIpAddress))
                        {
                            Log.Warning("Invalid Soulseek listen IP address '{Address}' in options update; keeping existing listen IP", update.ListenIpAddress);
                        }
                    }

                    var obfuscationDiff = old.Obfuscation.DiffWith(update.Obfuscation);
                    if (obfuscationDiff.Any() || old.ListenPort != update.ListenPort)
                    {
                        var previousPlan = SoulseekObfuscationSupport.BuildPlan(old);
                        var currentPlan = SoulseekObfuscationSupport.BuildPlan(update);

                        peerObfuscationPatch = SoulseekObfuscationSupport.BuildRuntimeOptions(update);

                        Log.Information(
                            "Soulseek type-1 obfuscation options changed: {PreviousMode}/{PreviousState} port {PreviousPort} -> {CurrentMode}/{CurrentState} port {CurrentPort}; supported connection types: {SupportedConnectionTypes}; regular fallback advertised: {AdvertiseRegularPort}; prefer outbound: {PreferOutbound}",
                            previousPlan.Mode,
                            previousPlan.RuntimeState,
                            previousPlan.EffectiveListenPort,
                            currentPlan.Mode,
                            currentPlan.RuntimeState,
                            currentPlan.EffectiveListenPort,
                            string.Join(",", currentPlan.SupportedConnectionTypes),
                            currentPlan.AdvertiseRegularPort,
                            currentPlan.PreferOutbound);

                        Log.Debug(
                            "Soulseek type-1 obfuscation runtime patch: enabled={Enabled}, listenPort={ListenPort}, type={Type}, advertiseRegularPort={AdvertiseRegularPort}, preferOutbound={PreferOutbound}",
                            peerObfuscationPatch.Enabled,
                            peerObfuscationPatch.ListenPort,
                            peerObfuscationPatch.Type,
                            peerObfuscationPatch.AdvertiseRegularPort,
                            peerObfuscationPatch.PreferOutbound);
                    }

                    var patch = new SoulseekClientOptionsPatch(
                        listenIPAddress: updateListenIpAddress,
                        listenPort: old.ListenPort == update.ListenPort ? null : update.ListenPort,
                        enableDistributedNetwork: old.DistributedNetwork.Disabled == update.DistributedNetwork.Disabled ? null : !update.DistributedNetwork.Disabled,
                        distributedChildLimit: old.DistributedNetwork.ChildLimit == update.DistributedNetwork.ChildLimit ? null : update.DistributedNetwork.ChildLimit,
                        acceptDistributedChildren: old.DistributedNetwork.DisableChildren == update.DistributedNetwork.DisableChildren ? null : !update.DistributedNetwork.DisableChildren,
                        maximumUploadSpeed: newOptions.Global.Upload.SpeedLimit,
                        maximumDownloadSpeed: newOptions.Global.Download.SpeedLimit,
                        serverConnectionOptions: serverPatch,
                        peerConnectionOptions: connectionPatch,
                        transferConnectionOptions: transferPatch,
                        incomingConnectionOptions: connectionPatch,
                        peerObfuscationOptions: peerObfuscationPatch,
                        distributedConnectionOptions: distributedPatch);

                    soulseekRequiresReconnect = await Client.ReconfigureOptionsAsync(patch);
                }

                // require a reconnect if the client is connected and any options marked [RequiresReconnect] changed, OR if the
                // call to reconfigure the client requires a reconnect
                if ((Client.State.HasFlag(SoulseekClientStates.Connected) && pendingReconnect) || soulseekRequiresReconnect)
                {
                    State.SetValue(state => state with { PendingReconnect = true });
                    Log.Information("One or more updated Soulseek options requires the client to be disconnected, then reconnected to the network to take effect.");
                }

                if (pendingRestart)
                {
                    State.SetValue(state => state with { PendingRestart = true });
                    Log.Information("One or more updated options requires an application restart to take effect.");
                }

                PreviousOptions = newOptions;
                _ = ObserveBackgroundTaskAsync(
                    ApplicationHub.BroadcastOptionsAsync(newOptions),
                    "Failed to broadcast updated options");

                Log.Information("Options updated successfully.");
            }
            catch (Exception ex)
            {
                Log.Error("Failed to apply option update: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
            }
            finally
            {
                OptionsSyncRoot.Release();
            }
        }

        /// <summary>
        ///     Determines whether <paramref name="searchText"/> matches any configured search-request filter.
        /// </summary>
        /// <param name="searchText">The incoming search text.</param>
        /// <returns><see langword="true"/> when a configured filter matches; otherwise, <see langword="false"/>.</returns>
        private bool MatchesAnySearchRequestFilter(string searchText)
        {
            foreach (var filter in CompiledSearchRequestFilters)
            {
                try
                {
                    if (filter.IsMatch(searchText))
                    {
                        return true;
                    }
                }
                catch (RegexMatchTimeoutException)
                {
                    // A pathological filter took too long against this query; don't let a
                    // crafted search term stall the resolver. Treat as no-match and continue.
                    Log.Warning("Search request filter timed out evaluating an incoming query; skipping that filter");
                }
            }

            return false;
        }

        private async Task<SearchResponse?> SearchResponseResolver(string username, int token, SearchQuery query)
        {
            Metrics.Search.Incoming.RequestsReceived.Inc(1);
            Metrics.Search.Incoming.CurrentRequestReceiveRate.CountUp(1);

            /*
                if the host is struggling to process incoming search results in a timely manner, requests will back up
                behind the SearchResponseSemaphore, potentially infinitely until the application runs out of memory and
                crashes.

                to prevent this from happening we must count the number of waiting requests in SearchResponseQueueDepth,
                and if that count exceeds the configured CircuitBreaker, we drop the search request and don't attempt
                to resolve a response.

                search requests arrive very consistently at a rate of about 30 per second, so we have about ~33 milliseconds
                to process each request on average before we get into trouble.
            */
            if (IncomingSearchRequestQueueDepth > OptionsMonitor.CurrentValue.Throttling.Search.Incoming.CircuitBreaker)
            {
                Metrics.Search.Incoming.RequestsDropped.Inc(1);
                Metrics.Search.Incoming.CurrentRequestDropRate.CountUp(1);

                return null;
            }

            Interlocked.Increment(ref IncomingSearchRequestQueueDepth);

            try
            {
                await IncomingSearchRequestSemaphore.WaitAsync();
            }
            finally
            {
                Interlocked.Decrement(ref IncomingSearchRequestQueueDepth);
                Metrics.Search.Incoming.CurrentRequestQueueDepth.Set(IncomingSearchRequestQueueDepth);
            }

            try
            {
                var sw = new Stopwatch();
                sw.Start();

                if (token < 0)
                {
                    Metrics.Search.Incoming.RequestsDropped.Inc(1);
                    Metrics.Search.Incoming.CurrentRequestDropRate.CountUp(1);

                    return null;
                }

                if (Users.IsBlacklisted(username))
                {
                    return null;
                }

                if (MatchesAnySearchRequestFilter(query.SearchText))
                {
                    return null;
                }

                // sometimes clients send search queries consisting only of exclusions; drop them.
                // no other clients send search results for these, even though it is technically possible.
                if (query.Terms.Count == 0)
                {
                    return null;
                }

                var filterLatency = sw.ElapsedMilliseconds;
                Metrics.Search.Incoming.Filter.Latency.Observe(filterLatency);
                Metrics.Search.Incoming.Filter.CurrentLatency.Update(filterLatency);

                try
                {
                    // append the list of excluded search phrases supplied by the server
                    // see https://github.com/jpdillingham/Soulseek.NET/issues/803
                    var queryWithExclusionsApplied = new SearchQuery(terms: query.Terms, exclusions: query.Exclusions.Concat(ExcludedSearchPhrases).Distinct());

                    var results = await Shares.SearchAsync(queryWithExclusionsApplied, limit: OptionsMonitor.CurrentValue.Throttling.Search.Incoming.ResponseFileLimit);

                    var queryLatency = sw.ElapsedMilliseconds - filterLatency;
                    Metrics.Search.Incoming.Query.Latency.Observe(queryLatency);
                    Metrics.Search.Incoming.Query.CurrentLatency.Update(queryLatency);

                    SearchResponse? response = null;

                    if (results.Any())
                    {
                        // fetch the user's IP address so that we can check whether it's blacklisted.
                        // it's unfortunate that we have to do this to get the IP, but we have to do it
                        // anyway to send the results, and the information is cached. whether we do it here
                        // or Soulseek.NET does it under the hood doesn't really matter.
                        try
                        {
                            var endpoint = await Client.GetUserEndPointAsync(username);

                            if (Users.IsBlacklisted(username, endpoint.Address))
                            {
                                return null;
                            }
                        }
                        catch (Soulseek.UserOfflineException)
                        {
                            return null;
                        }

                        // make sure our average speed (as reported by the server) is reasonably up to date
                        // we do this because we send the information along with the search response
                        await RefreshUserStatistics();

                        // note: the following uses cached user data to determine group, so if the user's data
                        // isn't cached they may get a forecast based on the wrong group.  this is a hot path though,
                        // and we don't want to incur the massive penalties that would caching data for each request.
                        var uploadForecast = Transfers.Uploads.Queue.ForecastPosition(username);

                        Log.Debug("Sending search response with {Count} files to {Username} for query '{Query}'", results.Count(),
                            LoggingSanitizer.SanitizeExternalIdentifier(username), LoggingSanitizer.SanitizeQueryText(query.SearchText));

                        // Raise event for passive FLAC discovery - this user searched us and we had results
                        EventBus.Raise(new Events.PeerSearchedUsEvent
                        {
                            Username = username,
                            SearchText = query.SearchText,
                            HadResults = true
                        });

                        response = new SearchResponse(
                            Client.Username,
                            token,
                            uploadSpeed: State.CurrentValue.User.Statistics.AverageSpeed,
                            hasFreeUploadSlot: uploadForecast.QueuePosition == 0,
                            queueLength: uploadForecast.QueuePosition,
                            fileList: results);
                    }

                    sw.Stop();

                    Metrics.Search.Incoming.ResponseLatency.Observe(sw.ElapsedMilliseconds);
                    Metrics.Search.Incoming.CurrentResponseLatency.Update(sw.ElapsedMilliseconds);

                    if (response is not null)
                    {
                        Metrics.Search.Incoming.ResponsesSent.Inc(1);
                        Metrics.Search.Incoming.CurrentResponseSendRate.CountUp(1);
                    }

                    // if no results, either return null or an instance of SearchResponse with a fileList of length 0 in either case, no
                    // response will be sent to the requestor.
                    return response;
                }
                catch (Exception ex) when (IsCancellationException(ex))
                {
                    Log.Debug("Search response resolution for query '{Query}' requested by {Username} was cancelled: {Message}",
                        LoggingSanitizer.SanitizeQueryText(query.SearchText),
                        LoggingSanitizer.SanitizeExternalIdentifier(username), LoggingSanitizer.SanitizeQueryText(ex.Message));
                    throw;
                }
                catch (Exception ex) when (IsTimeoutException(ex))
                {
                    Log.Debug("Search response resolution for query '{Query}' requested by {Username} timed out: {Message}",
                        LoggingSanitizer.SanitizeQueryText(query.SearchText),
                        LoggingSanitizer.SanitizeExternalIdentifier(username), LoggingSanitizer.SanitizeQueryText(ex.Message));
                    return null;
                }
                catch (Exception ex)
                {
                    Log.Warning("Failed to resolve search response: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                    throw;
                }
            }
            finally
            {
                IncomingSearchRequestSemaphore.Release();
            }
        }

        private static bool IsCancellationException(Exception exception)
        {
            if (exception is OperationCanceledException)
            {
                return true;
            }

            if (exception is AggregateException aggregateException)
            {
                var flattened = aggregateException.Flatten().InnerExceptions;
                return flattened.Count > 0 && flattened.All(IsCancellationException);
            }

            return exception.InnerException is not null && IsCancellationException(exception.InnerException);
        }

        private static bool IsTimeoutException(Exception exception)
        {
            if (exception is TimeoutException)
            {
                return true;
            }

            if (exception is AggregateException aggregateException)
            {
                var flattened = aggregateException.Flatten().InnerExceptions;
                return flattened.Count > 0 && flattened.All(IsTimeoutException);
            }

            return exception.InnerException is not null && IsTimeoutException(exception.InnerException);
        }

        private void ShareState_OnChange((ShareState Previous, ShareState Current) state)
        {
            var (previous, current) = state;
            bool rebuildBrowseCache = false;

            if (!previous.Scanning && current.Scanning)
            {
                // the scan is starting. update the application state without manipulation
                SharesRefreshStarted = DateTime.UtcNow;

                State.SetValue(s => s with { Shares = current });

                Log.Information("Share scan started");
            }
            else if (previous.Scanning && !current.Scanning)
            {
                // the scan is finishing. update the application state without manipulation...
                State.SetValue(s => s with { Shares = current });

                if (current.Faulted)
                {
                    Log.Error("Failed to scan shares.");
                }
                else
                {
                    // ...but if it completed successfully, immediately update again to lower the pending flag
                    State.SetValue(state => state with { Shares = state.Shares with { ScanPending = false } });
                    Log.Information("Shares scanned successfully. Found {Directories} directories and {Files} files in {Duration}ms", current.Directories, current.Files, (DateTime.UtcNow - SharesRefreshStarted).TotalMilliseconds);

                    SharesRefreshStarted = default;

                    if (Client.State.HasFlag(SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn))
                    {
                        _ = ObserveBackgroundTaskAsync(
                            Task.Run(async () =>
                            {
                                await Client.SetSharedCountsAsync(State.CurrentValue.Shares.Directories, State.CurrentValue.Shares.Files);
                                await RefreshUserStatistics(force: true);
                            }, CancellationToken.None),
                            "Failed to refresh shared counts after scan");
                    }
                }
            }
            else if (!previous.Ready && current.Ready)
            {
                // the share transitioned into ready without completing a scan; it was loaded from disk
                // this will (or should) also be true when the scan completes, which is why the code is using an else if here,
                // but only if it happens without a corresponding lowering of the scanning flag do we want to execute this.
                State.SetValue(state => state with { Shares = current with { ScanPending = false } });
                Log.Information("Share cache loaded from disk successfully. Sharing {Directories} directories and {Files} files", current.Directories, current.Files);
                rebuildBrowseCache = true;
            }
            else
            {
                // the scan is neither starting nor finishing; this is a status update of some sort,
                // not a state change. we want to clamp the frequency of these during a scan to avoid overwhelming clients,
                // only update if the progress has changed by at least 1%.
                var lastProgress = Math.Round(previous.ScanProgress * 100);
                var currentProgress = Math.Round(current.ScanProgress * 100);

                if (lastProgress != currentProgress && Math.Round(currentProgress, 0) % 1d == 0)
                {
                    State.SetValue(s => s with { Shares = current });
                    Log.Information("Scanned {Percent}% of shared directories. Found {Files} files so far.", currentProgress, current.Files);
                }
            }

            // if the host configuration changed, update *just* the hosts to avoid stepping on anything that might
            // have also happened above. a change in hosts will invalidate the cache, so do that too.
            if (previous.Hosts.ToJson() != current.Hosts.ToJson())
            {
                State.SetValue(state => state with
                {
                    Shares = state.Shares with
                    {
                        Hosts = current.Hosts,
                        Directories = current.Directories,
                        Files = current.Files,
                    },
                });

                rebuildBrowseCache = true;
            }

            // if a scan just completed successfully (but not failed!), shares were loaded from disk, or
            // host configuration changed, rebuild caches and upload shares to the network controller (if connected)
            if (rebuildBrowseCache)
            {
                _ = CacheBrowseResponse();
                _ = ObserveBackgroundTaskAsync(
                    Relay.Client.SynchronizeAsync(),
                    "Failed to synchronize relay shares after share state update");
            }
        }

        private async Task<BrowseResponse> CacheBrowseResponse()
        {
            await BrowseCacheSyncRoot.WaitAsync();

            string? temp = default;

            try
            {
                var sw = new Stopwatch();
                sw.Start();

                var destination = Path.Combine(Program.DataDirectory, "browse.cache");
                temp = Path.Combine(Program.DataDirectory, $"browse.cache.{Guid.NewGuid():N}.tmp");

                Log.Information("Warming browse response cache...");
                var directories = await Shares.BrowseAsync();
                var directoryCount = directories.Count();

                await using (var stream = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                {
                    BrowseResponseFactory.WriteToStream(
                        directoryCount,
                        directories,
                        0,
                        Array.Empty<Soulseek.Directory>(),
                        stream);
                }

                Log.Debug("Saved cache to temp file {File}", temp);

                ReplaceBrowseCacheFile(temp, destination);

                sw.Stop();
                Log.Information("Browse response cached successfully in {Duration}ms", sw.ElapsedMilliseconds);

                var cacheFileInfo = Files.ResolveFileInfo(destination);
                return new RawBrowseResponse(cacheFileInfo.Length, OpenBrowseCacheReadStream(destination));
            }
            catch (Exception ex)
            {
                Log.Error("Error caching browse response: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
            finally
            {
                if (!string.IsNullOrWhiteSpace(temp) && System.IO.File.Exists(temp))
                {
                    System.IO.File.Delete(temp);
                }

                BrowseCacheSyncRoot.Release();
            }
        }

        internal static FileStream OpenBrowseCacheReadStream(string cacheFilename)
        {
            return new FileStream(cacheFilename, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        }

        internal static void ReplaceBrowseCacheFile(string sourceFilename, string destinationFilename)
        {
            if (OperatingSystem.IsWindows() && System.IO.File.Exists(destinationFilename))
            {
                System.IO.File.Replace(sourceFilename, destinationFilename, null);
                return;
            }

            System.IO.File.Move(sourceFilename, destinationFilename, overwrite: true);
        }

        private void State_OnChange((State Previous, State Current) state)
        {
            _ = ObserveBackgroundTaskAsync(
                ApplicationHub.BroadcastStateAsync(state.Current),
                "Failed to broadcast application state");
        }

        /// <summary>
        ///     Creates and returns a <see cref="UserInfo"/> object in response to a remote request.
        /// </summary>
        /// <param name="username">The username of the requesting user.</param>
        /// <param name="endpoint">The IP endpoint of the requesting user.</param>
        /// <returns>A Task resolving the UserInfo instance.</returns>
        private async Task<UserInfo> UserInfoResolver(string username, IPEndPoint endpoint)
        {
            byte[]? pictureBytes = null;

            if (!string.IsNullOrWhiteSpace(Options.Soulseek.Picture))
            {
                try
                {
                    // note: the Picture setting is validated at startup to ensure it exists and that
                    // it is readable
                    pictureBytes = await System.IO.File.ReadAllBytesAsync(Options.Soulseek.Picture);
                }
                catch (Exception ex)
                {
                    // this isn't a serious enough problem to prevent us from continuing, so we'll just
                    // log a warning and continue, omitting the picture
                    Log.Warning("Failed to read Soulseek picture {Picture}: {Message}",
                        LoggingSanitizer.SanitizeFilePath(Options.Soulseek.Picture), LoggingSanitizer.SanitizeExternalIdentifier(ex.Message));
                }
            }

            // build the base description, optionally appending now-playing info (#39)
            var baseDescription = Options.Soulseek.Description;
            var nowPlayingSuffix = NowPlayingService?.GetDescriptionSuffix();
            var description = string.IsNullOrEmpty(nowPlayingSuffix)
                ? baseDescription
                : baseDescription + nowPlayingSuffix;

            if (Users.IsBlacklisted(username, endpoint.Address))
            {
                return new UserInfo(
                    description: description,
                    uploadSlots: 0,
                    queueLength: int.MaxValue,
                    hasFreeUploadSlot: false,
                    picture: pictureBytes);
            }

            try
            {
                // note: users must first be watched or cached for leech and privilege detection to work.
                // we are deliberately skipping it here; if the username is watched
                // leech detection works and they get accurate info, if not, they won't
                await Users.GetOrFetchGroupAsync(username);

                // forecast the position at which this user would enter the queue if they were to request
                // a file at this moment. this will be zero if a slot is available and the transfer would
                // begin immediately
                var uploadForecast = Transfers.Uploads.Queue.ForecastPosition(username);

                // if i get a user's info to determine whether i want to download files from them,
                // i want to know how many slots they have, which gives me an idea of how fast their
                // queue moves, and the length of the queue *ahead of me*, meaning how long i'd have to
                // wait until my first download starts.
                // revisited 3 years later: why was it important to leave this comment??
                var info = new UserInfo(
                    description: description,
                    uploadSlots: uploadForecast.Slots,
                    queueLength: uploadForecast.QueuePosition,
                    hasFreeUploadSlot: uploadForecast.QueuePosition == 0,
                    picture: pictureBytes);

                return info;
            }
            catch (Exception ex)
            {
                Log.Warning("Failed to resolve user info: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        private async Task ObserveBackgroundTaskAsync(Task task, string messageTemplate, params object[] propertyValues)
        {
            try
            {
                await task.ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                Log.Error(ex, messageTemplate, propertyValues);
            }
        }

        private void RegisterChange(IDisposable? registration)
        {
            if (registration != null)
            {
                _changeRegistrations.Add(registration);
            }
        }

        public void Dispose()
        {
            if (_cancelKeyPressHandler != null)
            {
                Console.CancelKeyPress -= _cancelKeyPressHandler;
                _cancelKeyPressHandler = null;
            }

            if (_programLogEmittedHandler != null)
            {
                Program.LogEmitted -= _programLogEmittedHandler;
                _programLogEmittedHandler = null;
            }

            Clock.EveryMinute -= Clock_EveryMinute;
            Clock.EveryThirtySeconds -= Clock_EveryThirtySeconds;
            Clock.EveryFiveMinutes -= Clock_EveryFiveMinutes;
            Clock.EveryThirtyMinutes -= Clock_EveryThirtyMinutes;
            Clock.EveryHour -= Clock_EveryHour;

            Client.DiagnosticGenerated -= Client_DiagnosticGenerated;
            Client.TransferStateChanged -= Client_TransferStateChanged;
            Client.TransferProgressUpdated -= Client_TransferProgressUpdated;
            Client.BrowseProgressUpdated -= Client_BrowseProgressUpdated;
            Client.UserStatusChanged -= Client_UserStatusChanged;
            Users.WatchedUsersChanged -= Users_WatchedUsersChanged;
            Client.PrivateMessageReceived -= Client_PrivateMessageReceived;

            if (_privateRoomMembershipAddedHandler != null)
            {
                Client.PrivateRoomMembershipAdded -= _privateRoomMembershipAddedHandler;
                _privateRoomMembershipAddedHandler = null;
            }

            if (_privateRoomMembershipRemovedHandler != null)
            {
                Client.PrivateRoomMembershipRemoved -= _privateRoomMembershipRemovedHandler;
                _privateRoomMembershipRemovedHandler = null;
            }

            if (_privateRoomModerationAddedHandler != null)
            {
                Client.PrivateRoomModerationAdded -= _privateRoomModerationAddedHandler;
                _privateRoomModerationAddedHandler = null;
            }

            if (_privateRoomModerationRemovedHandler != null)
            {
                Client.PrivateRoomModerationRemoved -= _privateRoomModerationRemovedHandler;
                _privateRoomModerationRemovedHandler = null;
            }

            Client.RoomMessageReceived -= Client_RoomMessageReceived;
            Client.Disconnected -= Client_Disconnected;
            Client.Connected -= Client_Connected;
            Client.LoggedIn -= Client_LoggedIn;
            Client.StateChanged -= Client_StateChanged;
            Client.DistributedNetworkStateChanged -= Client_DistributedNetworkStateChanged;

            if (_downloadDeniedHandler != null)
            {
                Client.DownloadDenied -= _downloadDeniedHandler;
                _downloadDeniedHandler = null;
            }

            if (_downloadFailedHandler != null)
            {
                Client.DownloadFailed -= _downloadFailedHandler;
                _downloadFailedHandler = null;
            }

            Client.ExcludedSearchPhrasesReceived -= Client_ExcludedSearchPhrasesReceived;

            foreach (var registration in _changeRegistrations)
            {
                registration.Dispose();
            }

            _changeRegistrations.Clear();
            _startupInitializationCts?.Cancel();
            _startupInitializationCts?.Dispose();
            _startupInitializationCts = null;
        }
    }
}
