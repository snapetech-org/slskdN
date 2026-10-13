// <copyright file="StubWebApplicationFactory.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Integration;

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq.Expressions;
using System.Reflection;
using System.Security.Claims;
using System.Text.Encodings.Web;
using System.Threading;
using System.Threading.Tasks;
using Soulseek;
using slskd.Transfers.Downloads;
using Transfer = slskd.Transfers.Transfer;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.ApplicationParts;
using Microsoft.AspNetCore.Mvc.Controllers;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Asp.Versioning;
using Asp.Versioning.ApiExplorer;
using global::slskd.API.Compatibility;
using global::slskd.API.Native;
using global::slskd.Jobs;
using global::slskd.Integrations.MusicBrainz;
using global::slskd.Integrations.MusicBrainz.Models;
using global::slskd.LibraryHealth;
using global::slskd.Search;
using global::slskd.Transfers;
using global::slskd.Transfers.MultiSource.Caching;
using slskd.Common.Moderation;
using slskd.MediaCore;
using slskd.Core.Features;
using slskd.Shares;
using slskd.VirtualSoulfind.v2.Backends;
using slskd.VirtualSoulfind.v2.Catalogue;
using slskd.VirtualSoulfind.v2.Intents;
using slskd.VirtualSoulfind.v2.Planning;
using slskd.VirtualSoulfind.v2.Sources;
using slskd.VirtualSoulfind.Bridge;
using slskd.Core;
using slskd.Streaming;
using slskd.Mesh;
using slskd.Search.Providers;
using slskd.Common.Security.API;
using slskd.MediaCore.API.Controllers;
using System.Linq;
using Moq;
using OptionsModel = global::slskd.Options;

/// <summary>
/// Integration test host using real controllers with lightweight stubs.
/// </summary>
public class StubWebApplicationFactory : WebApplicationFactory<ProgramStub>
{
    protected override IHostBuilder CreateHostBuilder()
    {
        // Content root: HostBuilder.CreateHostingEnvironment uses a path like solutionRoot/slskd.Tests.Integration.
        // From bin/Release/net10.0 go up 5 levels to repo root (slskdn), then slskd.Tests.Integration.
        var baseDir = AppContext.BaseDirectory;
        var solutionRoot = Path.GetFullPath(Path.Combine(baseDir, "..", "..", "..", "..", ".."));
        var testContentRoot = Path.Combine(solutionRoot, "slskd.Tests.Integration");
        var testTempRoot = Path.Combine(Path.GetTempPath(), "slskdn-test");
        var testDownloadsRoot = Path.Combine(testTempRoot, "downloads");
        var testIncompleteRoot = Path.Combine(testTempRoot, "incomplete");
        var testOptions = new OptionsModel
        {
            RemoteFileManagement = true,
            WarmCache = new global::slskd.WarmCacheOptions
            {
                Enabled = true,
            },
            VirtualSoulfind = new VirtualSoulfindOptions
            {
                Bridge = new BridgeOptions { Enabled = true, Port = 2242 },
            },
            Directories = new OptionsModel.DirectoriesOptions
            {
                Downloads = testDownloadsRoot,
                Incomplete = testIncompleteRoot,
            },
        };
        System.IO.Directory.CreateDirectory(testContentRoot);
        System.IO.Directory.CreateDirectory(testDownloadsRoot);
        System.IO.Directory.CreateDirectory(testIncompleteRoot);

        // Manually create host builder to avoid default path inference issues
        return new HostBuilder()
            .UseContentRoot(testContentRoot)
            .UseEnvironment("Test")
            .ConfigureHostConfiguration(config =>
            {
                // Set content root via configuration to ensure it's used
                config.AddInMemoryCollection(new Dictionary<string, string?>
                {
                    [HostDefaults.ContentRootKey] = testContentRoot
                });
            })
            .ConfigureWebHostDefaults(webBuilder =>
            {
                webBuilder.UseTestServer();
                webBuilder.UseContentRoot(testContentRoot);

                webBuilder.ConfigureAppConfiguration(config =>
                {
                    config.AddInMemoryCollection(new Dictionary<string, string?>
                    {
                        ["Logging:LogLevel:Default"] = "Warning"
                    });
                });

                webBuilder.ConfigureServices(services =>
                {
                    services.AddLogging(b => b.SetMinimumLevel(LogLevel.Warning));

                    services.AddAuthentication("Test")
                        .AddScheme<AuthenticationSchemeOptions, TestAuthHandler>("Test", options => { });
                    services.AddAuthorization(options =>
                    {
                        options.DefaultPolicy = new AuthorizationPolicyBuilder("Test")
                            .RequireAuthenticatedUser()
                            .Build();

                        // Register AuthPolicy.Any for controllers that use it
                        options.AddPolicy(slskd.AuthPolicy.Any, policy =>
                        {
                            policy.AuthenticationSchemes.Add("Test");
                            policy.RequireAuthenticatedUser();
                        });

                        options.AddPolicy(slskd.AuthPolicy.JwtOnly, policy =>
                        {
                            policy.AuthenticationSchemes.Add("Test");
                            policy.RequireAuthenticatedUser();
                        });

                        options.AddPolicy(slskd.AuthPolicy.ApiKeyOnly, policy =>
                        {
                            policy.AuthenticationSchemes.Add("Test");
                            policy.RequireAuthenticatedUser();
                        });
                    });

                    // Add API versioning (required for routes with apiVersion constraint)
                    services.AddApiVersioning(options =>
                    {
                        options.ReportApiVersions = true;
                        options.DefaultApiVersion = new Asp.Versioning.ApiVersion(0, 0);
                        options.AssumeDefaultVersionWhenUnspecified = true;
                    })
                    .AddMvc()
                    .AddApiExplorer(options =>
                    {
                        options.GroupNameFormat = "'v'VVV";
                        options.SubstituteApiVersionInUrl = true;
                    });

                    services.AddControllers()
                        .AddJsonOptions(options =>
                        {
                            options.JsonSerializerOptions.Converters.Add(new System.Text.Json.Serialization.JsonStringEnumConverter());
                            options.JsonSerializerOptions.DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull;
                        })
                        .AddApplicationPart(typeof(CapabilitiesController).Assembly)
                        .AddApplicationPart(typeof(global::slskd.Files.API.FilesController).Assembly)
                        .AddApplicationPart(typeof(DownloadsCompatibilityController).Assembly)
                        .AddApplicationPart(typeof(LibraryHealthController).Assembly)
                        .AddApplicationPart(typeof(global::slskd.API.Compatibility.LibraryCompatibilityController).Assembly)
                        .AddApplicationPart(typeof(global::slskd.API.Compatibility.ServerCompatibilityController).Assembly)
                        .AddApplicationPart(typeof(global::slskd.API.Compatibility.RoomsCompatibilityController).Assembly)
                        .AddApplicationPart(typeof(global::slskd.API.Compatibility.UsersCompatibilityController).Assembly)
                        .AddApplicationPart(typeof(JobsController).Assembly)
                        .AddApplicationPart(typeof(SearchCompatibilityController).Assembly)
                        .AddApplicationPart(typeof(global::slskd.API.VirtualSoulfind.DisasterModeController).Assembly)
                        .AddApplicationPart(typeof(global::slskd.Search.API.SearchActionsController).Assembly)
                        .AddApplicationPart(typeof(global::slskd.Transfers.MultiSource.API.AnalyticsController).Assembly)
                        .AddApplicationPart(typeof(global::slskd.API.VirtualSoulfind.BridgeController).Assembly)
                        .AddApplicationPart(typeof(global::slskd.API.VirtualSoulfind.BridgeAdminController).Assembly)
                        .AddApplicationPart(typeof(SecurityController).Assembly)
                        .AddApplicationPart(typeof(ContentIdController).Assembly)
                        .AddApplicationPart(typeof(global::slskd.Users.Notes.API.UserNotesController).Assembly)
                        .ConfigureApplicationPartManager(manager =>
                        {
                            // Exclude conflicting controllers - use JobsController instead
                            var existingProvider = manager.FeatureProviders.OfType<ControllerFeatureProvider>().FirstOrDefault();
                            if (existingProvider != null)
                            {
                                manager.FeatureProviders.Remove(existingProvider);
                            }
                            manager.FeatureProviders.Add(new ExcludeControllerFeatureProvider(
                                typeof(global::slskd.Jobs.API.DiscographyJobsController),
                                typeof(global::slskd.Jobs.API.LabelCrateJobsController)));
                        })
                        .AddApplicationPart(typeof(SearchCompatibilityController).Assembly)
                        .AddApplicationPart(typeof(global::slskd.API.VirtualSoulfind.DisasterModeController).Assembly);

                    var discographyService = new StubDiscographyJobService();
                    var labelCrateService = new StubLabelCrateJobService();

                    services.AddSingleton<global::slskd.Users.Notes.IUserNoteService>(_ => Mock.Of<global::slskd.Users.Notes.IUserNoteService>(service =>
                        service.GetAllNotesAsync(It.IsAny<CancellationToken>()) ==
                            Task.FromResult<IEnumerable<global::slskd.Users.Notes.UserNote>>(Array.Empty<global::slskd.Users.Notes.UserNote>())));

                    services.AddSingleton<IOptionsMonitor<OptionsModel>>(_ => new StaticOptionsMonitor<OptionsModel>(testOptions))
                        .AddSingleton<IOptionsSnapshot<OptionsModel>>(_ =>
                        {
                            var snapshot = new Mock<IOptionsSnapshot<OptionsModel>>();
                            snapshot.SetupGet(x => x.Value).Returns(testOptions);
                            return snapshot.Object;
                        })
                        .AddSingleton<global::slskd.Files.FileService>()
                        .AddSingleton<IDiscographyJobService>(discographyService)
                        .AddSingleton<ILabelCrateJobService>(labelCrateService)
                        .AddSingleton<IMusicBrainzClient>(_ => Mock.Of<IMusicBrainzClient>(client =>
                            client.GetReleaseAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()) ==
                                Task.FromResult<AlbumTarget?>(new AlbumTarget
                                {
                                    MusicBrainzReleaseId = "test-release",
                                    MusicBrainzArtistId = "test-artist",
                                    Artist = "Test Artist",
                                    Title = "Test Release",
                                })))
                        .AddSingleton<IJobServiceWithList>(new JobServiceListAdapter(discographyService, labelCrateService))
                        .AddSingleton<IFeatureGate, TestFeatureGate>()
                        .AddSingleton<ILibraryHealthService, StubLibraryHealthService>()
                        .AddSingleton<IDownloadService, StubDownloadService>()
                        .AddSingleton<ITransferService>(_ => NullProxy<ITransferService>.Create())
                        .AddSingleton<ISearchService, StubSearchService>()
                        .AddSingleton<IWarmCachePopularityService>(_ => NullProxy<IWarmCachePopularityService>.Create())
                        .AddSingleton<slskd.Transfers.MultiSource.Analytics.ISwarmAnalyticsService, StubSwarmAnalyticsService>()
                        .AddSingleton<global::slskd.VirtualSoulfind.DisasterMode.IDisasterModeCoordinator, StubDisasterModeCoordinator>()
                        .AddSingleton<global::slskd.VirtualSoulfind.ShadowIndex.IShadowIndexQuery, StubShadowIndexQueryForFactory>()
                        // ISoulseekClient for CompatibilityController (GET /api/info) — Soulbeet
                        .AddSingleton<ISoulseekClient>(_ => Mock.Of<ISoulseekClient>(x =>
                            x.State == SoulseekClientStates.LoggedIn && x.Username == "test-user"))
                        .AddSingleton<slskd.Messaging.IRoomTracker, slskd.Messaging.RoomTracker>()
                        .AddSingleton<slskd.Messaging.IRoomService>(_ => Mock.Of<slskd.Messaging.IRoomService>())
                        .AddSingleton<slskd.IStateMonitor<slskd.State>>(_ =>
                        {
                            var monitor = new Mock<slskd.IStateMonitor<slskd.State>>();
                            monitor.SetupGet(x => x.CurrentValue).Returns(new slskd.State
                            {
                                User = new slskd.UserState { Username = "test-user" },
                            });
                            return monitor.Object;
                        });

                    // VirtualSoulfind / Moderation / MediaCore for ModerationIntegrationTests
                    services.AddSingleton<IIntentQueue, InMemoryIntentQueue>();
                    services.AddSingleton<IModerationProvider, NoopModerationProvider>();
                    services.AddSingleton<IDescriptorPublisher, StubDescriptorPublisher>();
                    services.AddSingleton<IContentIdRegistry, ContentIdRegistry>();
                    services.AddSingleton<IPerceptualHasher, PerceptualHasher>();
                    services.AddSingleton<IMetadataPortability>(_ => Mock.Of<IMetadataPortability>());
                    services.AddOptions<MediaCoreOptions>();
                    services.AddSingleton<IContentDescriptorPublisher, ContentDescriptorPublisher>();
                    services.AddSingleton<ICatalogueStore, InMemoryCatalogueStore>();
                    services.AddSingleton<ISourceRegistry, InMemorySourceRegistry>();
                    services.AddSingleton<IPeerReputationStore, StubPeerReputationStore>();
                    services.AddSingleton<PeerReputationService>();
                    services.AddSingleton<IShareRepository, StubShareRepository>();
                    services.AddSingleton<IContentBackend, LocalLibraryBackend>();
                    services.AddSingleton<IPlanner, MultiSourcePlanner>();

                    // ShareService and ContentLocator for SearchActionsController
                    services.AddSingleton<IShareService>(sp => new StubShareService(sp.GetRequiredService<IShareRepository>()));
                    services.AddSingleton<IContentLocator>(sp => new StubContentLocator(sp.GetRequiredService<IShareService>(), sp.GetRequiredService<ILogger<StubContentLocator>>()));

                    // Mesh services for remote pod download
                    services.AddSingleton<IMeshContentFetcher, StubMeshContentFetcher>();
                    services.AddSingleton<IMeshDirectory, StubMeshDirectory>();
                    services.AddSingleton<IMeshStreamTicketService, MeshStreamTicketService>();

                    // Bridge (NicotinePlus / legacy client) — BridgeController, BridgeAdminController
                    services.AddSingleton<StubBridgeApi>();
                    services.AddSingleton<IBridgeApi>(sp => sp.GetRequiredService<StubBridgeApi>());
                    services.AddSingleton<ISoulfindBridgeService, TestSoulfindBridgeService>();
                    services.AddSingleton<IBridgeDashboard, BridgeDashboard>();
                    services.AddSingleton<ITransferProgressProxy>(_ => NullProxy<ITransferProgressProxy>.Create());
                });

                webBuilder.Configure(app =>
                {
                    app.UseRouting();
                    app.UseAuthentication();
                    app.UseAuthorization();
                    app.UseEndpoints(endpoints => { endpoints.MapControllers(); });
                });
            });
    }
}

internal sealed class TestFeatureGate : IFeatureGate
{
    public FeatureGateResult Get(FeatureId feature) =>
        new(feature, FeatureStatus.Experimental, true, "Integration test feature gate is enabled.");

    public bool IsEnabled(FeatureId feature) => true;
}

internal class StaticOptionsMonitor<T> : IOptionsMonitor<T> where T : class
{
    private readonly T value;
    public StaticOptionsMonitor(T value) => this.value = value;
    public T CurrentValue => value;
    public T Get(string name) => value;
    public IDisposable OnChange(Action<T, string> listener) => NullDisposable.Instance;

    private class NullDisposable : IDisposable
    {
        public static readonly NullDisposable Instance = new();
        public void Dispose() { }
    }
}

internal class TestAuthHandler : AuthenticationHandler<AuthenticationSchemeOptions>
{
    public TestAuthHandler(IOptionsMonitor<AuthenticationSchemeOptions> options, ILoggerFactory logger, UrlEncoder encoder)
        : base(options, logger, encoder) { }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        var identity = new ClaimsIdentity("Test");
        identity.AddClaim(new Claim(ClaimTypes.Name, "test-user"));
        identity.AddClaim(new Claim(ClaimTypes.Role, slskd.Authentication.Role.ReadWrite.ToString()));
        identity.AddClaim(new Claim(ClaimTypes.Role, slskd.Authentication.Role.Administrator.ToString()));
        var principal = new ClaimsPrincipal(identity);
        var ticket = new AuthenticationTicket(principal, "Test");
        return Task.FromResult(AuthenticateResult.Success(ticket));
    }
}

internal class StubSwarmAnalyticsService : slskd.Transfers.MultiSource.Analytics.ISwarmAnalyticsService
{
    public Task<slskd.Transfers.MultiSource.Analytics.SwarmAnalyticsDashboard> GetDashboardAsync(
        TimeSpan timeWindow,
        int rankingLimit = 20,
        CancellationToken cancellationToken = default)
    {
        return Task.FromResult(new slskd.Transfers.MultiSource.Analytics.SwarmAnalyticsDashboard(
            new slskd.Transfers.MultiSource.Analytics.SwarmPerformanceMetrics { TimeWindow = timeWindow },
            new List<slskd.Transfers.MultiSource.Analytics.PeerPerformanceRanking>(),
            new slskd.Transfers.MultiSource.Analytics.SwarmEfficiencyMetrics(),
            new List<slskd.Transfers.MultiSource.Analytics.SwarmRecommendation>()));
    }

    public Task<slskd.Transfers.MultiSource.Analytics.SwarmPerformanceMetrics> GetPerformanceMetricsAsync(
        TimeSpan? timeWindow = null,
        CancellationToken cancellationToken = default)
    {
        return Task.FromResult(new slskd.Transfers.MultiSource.Analytics.SwarmPerformanceMetrics
        {
            TimeWindow = timeWindow ?? TimeSpan.FromHours(24)
        });
    }

    public Task<List<slskd.Transfers.MultiSource.Analytics.PeerPerformanceRanking>> GetPeerRankingsAsync(
        int limit = 20,
        CancellationToken cancellationToken = default)
    {
        return Task.FromResult(new List<slskd.Transfers.MultiSource.Analytics.PeerPerformanceRanking>());
    }

    public Task<slskd.Transfers.MultiSource.Analytics.SwarmEfficiencyMetrics> GetEfficiencyMetricsAsync(
        TimeSpan? timeWindow = null,
        CancellationToken cancellationToken = default)
    {
        return Task.FromResult(new slskd.Transfers.MultiSource.Analytics.SwarmEfficiencyMetrics());
    }

    public Task<slskd.Transfers.MultiSource.Analytics.SwarmTrends> GetTrendsAsync(
        TimeSpan timeWindow,
        int dataPoints = 24,
        CancellationToken cancellationToken = default)
    {
        return Task.FromResult(new slskd.Transfers.MultiSource.Analytics.SwarmTrends());
    }

    public Task<List<slskd.Transfers.MultiSource.Analytics.SwarmRecommendation>> GetRecommendationsAsync(
        CancellationToken cancellationToken = default)
    {
        return Task.FromResult(new List<slskd.Transfers.MultiSource.Analytics.SwarmRecommendation>());
    }
}

internal sealed class StubDisasterModeCoordinator : global::slskd.VirtualSoulfind.DisasterMode.IDisasterModeCoordinator
{
    public global::slskd.VirtualSoulfind.DisasterMode.DisasterModeLevel CurrentLevel { get; private set; }

    public event EventHandler<global::slskd.VirtualSoulfind.DisasterMode.DisasterModeLevelChangedEventArgs>? DisasterModeLevelChanged;

    public Task DeactivateDisasterModeAsync(CancellationToken ct = default)
    {
        return SetDisasterModeLevelAsync(
            global::slskd.VirtualSoulfind.DisasterMode.DisasterModeLevel.Normal,
            "Test deactivation",
            ct);
    }

    public Task SetDisasterModeLevelAsync(
        global::slskd.VirtualSoulfind.DisasterMode.DisasterModeLevel level,
        string reason,
        CancellationToken ct = default)
    {
        var previousLevel = CurrentLevel;
        CurrentLevel = level;
        DisasterModeLevelChanged?.Invoke(this, new global::slskd.VirtualSoulfind.DisasterMode.DisasterModeLevelChangedEventArgs
        {
            Level = level,
            PreviousLevel = previousLevel,
            Timestamp = DateTimeOffset.UtcNow,
            Reason = reason,
        });

        return Task.CompletedTask;
    }

    public void Dispose() { }
}

internal sealed class StubShadowIndexQueryForFactory : global::slskd.VirtualSoulfind.ShadowIndex.IShadowIndexQuery
{
    public Task<global::slskd.VirtualSoulfind.ShadowIndex.ShadowIndexQueryResult?> QueryAsync(string mbid, CancellationToken ct = default)
    {
        return Task.FromResult<global::slskd.VirtualSoulfind.ShadowIndex.ShadowIndexQueryResult?>(new global::slskd.VirtualSoulfind.ShadowIndex.ShadowIndexQueryResult
        {
            MBID = mbid,
            TotalPeerCount = 2,
            CanonicalVariants = new List<global::slskd.VirtualSoulfind.ShadowIndex.VariantHint>
            {
                new()
                {
                    Codec = "FLAC",
                    BitrateKbps = 1000,
                    SizeBytes = 25_000_000,
                    QualityScore = 100,
                },
            },
        });
    }

    public async Task<Dictionary<string, global::slskd.VirtualSoulfind.ShadowIndex.ShadowIndexQueryResult>> QueryBatchAsync(
        List<string> mbids,
        CancellationToken ct = default)
    {
        var results = new Dictionary<string, global::slskd.VirtualSoulfind.ShadowIndex.ShadowIndexQueryResult>();

        foreach (var mbid in mbids)
        {
            var result = await QueryAsync(mbid, ct);
            if (result != null)
            {
                results[mbid] = result;
            }
        }

        return results;
    }
}

internal class StubDiscographyJobService : IDiscographyJobService
{
    private readonly ConcurrentDictionary<string, DiscographyJob> jobs = new();

    public Task<string> CreateJobAsync(DiscographyJobRequest request, CancellationToken ct = default)
    {
        var id = Guid.NewGuid().ToString("N");
        var job = new DiscographyJob
        {
            JobId = id,
            ArtistId = request.ArtistId ?? "",
            ArtistName = request.ArtistId ?? "",
            Profile = request.Profile,
            TargetDirectory = request.TargetDirectory ?? string.Empty,
            TotalReleases = 0,
            Status = JobStatus.Pending,
            CreatedAt = DateTimeOffset.UtcNow,
        };
        jobs[id] = job;
        return Task.FromResult(id);
    }

    public Task<DiscographyJob?> GetJobAsync(string jobId, CancellationToken ct = default)
    {
        jobs.TryGetValue(jobId, out var job);
        return Task.FromResult(job);
    }

    public Task SetReleaseStatusAsync(string jobId, string releaseId, JobStatus status, CancellationToken ct = default) => Task.CompletedTask;

    // Helper method for test host
    public IReadOnlyList<DiscographyJob> GetAllJobs() => jobs.Values.ToList();
}

internal class StubLabelCrateJobService : ILabelCrateJobService
{
    private readonly ConcurrentDictionary<string, LabelCrateJob> jobs = new();

    public Task<string> CreateJobAsync(LabelCrateJobRequest request, CancellationToken ct = default)
    {
        var id = Guid.NewGuid().ToString("N");
        jobs[id] = new LabelCrateJob
        {
            JobId = id,
            LabelId = request.LabelId ?? string.Empty,
            LabelName = request.LabelName ?? request.LabelId ?? string.Empty,
            Limit = request.Limit > 0 ? request.Limit : 10,
            TotalReleases = request.Limit > 0 ? request.Limit : 0,
            Status = JobStatus.Pending,
            CreatedAt = DateTimeOffset.UtcNow
        };
        return Task.FromResult(id);
    }

    public Task<LabelCrateJob?> GetJobAsync(string jobId, CancellationToken ct = default)
    {
        jobs.TryGetValue(jobId, out var job);
        return Task.FromResult(job);
    }

    public Task SetReleaseStatusAsync(string jobId, string releaseId, JobStatus status, CancellationToken ct = default) => Task.CompletedTask;

    // Helper method for test host
    public IReadOnlyList<LabelCrateJob> GetAllJobs() => jobs.Values.ToList();
}

internal class ExcludeControllerFeatureProvider : ControllerFeatureProvider, IApplicationFeatureProvider<ControllerFeature>
{
    private readonly HashSet<Type> excludeTypes;

    public ExcludeControllerFeatureProvider(params Type[] excludeTypes)
    {
        this.excludeTypes = new HashSet<Type>(excludeTypes);
    }

    void IApplicationFeatureProvider<ControllerFeature>.PopulateFeature(
        IEnumerable<ApplicationPart> parts, ControllerFeature feature)
    {
        foreach (var part in parts.OfType<IApplicationPartTypeProvider>())
        {
            IEnumerable<TypeInfo> types;
            try
            {
                types = part.Types.ToList();
            }
            catch
            {
                if (part is not AssemblyPart assemblyPart)
                {
                    continue;
                }

                try
                {
                    types = assemblyPart.Assembly.GetTypes().Select(t => t.GetTypeInfo());
                }
                catch (ReflectionTypeLoadException ex)
                {
                    types = ex.Types.Where(t => t != null).Select(t => t!.GetTypeInfo());
                }
                catch
                {
                    continue;
                }
            }

            foreach (var type in types)
            {
                try
                {
                    if (IsController(type) && !feature.Controllers.Contains(type))
                    {
                        feature.Controllers.Add(type);
                    }
                }
                catch
                {
                    // Skip types whose base classes or attributes can't be resolved.
                }
            }
        }
    }

    protected override bool IsController(TypeInfo typeInfo)
    {
        if (excludeTypes.Contains(typeInfo.AsType()))
            return false;
        return base.IsController(typeInfo);
    }
}

internal class JobServiceListAdapter : global::slskd.API.Native.IJobServiceWithList
{
    private readonly StubDiscographyJobService discographyService;
    private readonly StubLabelCrateJobService labelCrateService;

    public JobServiceListAdapter(StubDiscographyJobService discographyService, StubLabelCrateJobService labelCrateService)
    {
        this.discographyService = discographyService;
        this.labelCrateService = labelCrateService;
    }

    public Task<global::slskd.Jobs.JobListPage> GetJobListPageAsync(
        string? type,
        string? status,
        int limit,
        int offset,
        string? sortBy,
        bool descending,
        CancellationToken cancellationToken = default)
    {
        var items = new List<global::slskd.Jobs.JobListItem>();
        if (type == null || type.Equals("discography", StringComparison.OrdinalIgnoreCase))
        {
            items.AddRange(discographyService.GetAllJobs().Select(job => new global::slskd.Jobs.JobListItem(
                job.JobId,
                "discography",
                job.Status.ToString().ToLowerInvariant(),
                job.CreatedAt,
                job.TotalReleases,
                job.CompletedReleases,
                job.FailedReleases)));
        }

        if (type == null || type.Equals("label_crate", StringComparison.OrdinalIgnoreCase))
        {
            items.AddRange(labelCrateService.GetAllJobs().Select(job => new global::slskd.Jobs.JobListItem(
                job.JobId,
                "label_crate",
                job.Status.ToString().ToLowerInvariant(),
                job.CreatedAt,
                job.TotalReleases,
                job.CompletedReleases,
                job.FailedReleases)));
        }

        if (status != null)
        {
            items = items
                .Where(item => item.Status.Equals(status, StringComparison.OrdinalIgnoreCase))
                .ToList();
        }

        items = sortBy?.ToLowerInvariant() switch
        {
            "status" => descending
                ? items.OrderByDescending(item => item.Status).ToList()
                : items.OrderBy(item => item.Status).ToList(),
            "created_at" or "created" => descending
                ? items.OrderByDescending(item => item.CreatedAt).ToList()
                : items.OrderBy(item => item.CreatedAt).ToList(),
            "id" => descending
                ? items.OrderByDescending(item => item.Id).ToList()
                : items.OrderBy(item => item.Id).ToList(),
            null => items.OrderByDescending(item => item.CreatedAt).ToList(),
            _ => items,
        };

        return Task.FromResult(new global::slskd.Jobs.JobListPage(
            items.Skip(offset).Take(limit).ToList(),
            items.Count));
    }
}

internal sealed class StubDownloadService : IDownloadService
{
    private readonly ConcurrentDictionary<Guid, Transfer> _storage = new();

    public void AddOrSupersede(Transfer transfer)
    {
        _storage[transfer.Id] = transfer;
    }

    public Task<(List<Transfer> Enqueued, List<string> Failed)> EnqueueAsync(string username, IEnumerable<(string Filename, long Size)> files, CancellationToken cancellationToken = default)
        => EnqueueAsync(username, files.Select(file => (file.Filename, file.Size, BatchId: (Guid?)null)), cancellationToken);

    public Task<(List<Transfer> Enqueued, List<string> Failed)> EnqueueAsync(string username, IEnumerable<(string Filename, long Size, Guid? BatchId)> files, CancellationToken cancellationToken = default)
        => EnqueueAsync(username, files.Select(file => (file.Filename, file.Size, file.BatchId, DestinationDirectory: (string?)null)), cancellationToken);

    public Task<(List<Transfer> Enqueued, List<string> Failed)> EnqueueAsync(string username, IEnumerable<(string Filename, long Size, Guid? BatchId, string? DestinationDirectory)> files, CancellationToken cancellationToken = default)
        => EnqueueAsync(
            username,
            files.Select(file => new DownloadEnqueueRequest
            {
                Filename = file.Filename,
                Size = file.Size,
                BatchId = file.BatchId,
                DestinationDirectory = file.DestinationDirectory,
            }),
            cancellationToken);

    public Task<(List<Transfer> Enqueued, List<string> Failed)> EnqueueAsync(string username, IEnumerable<DownloadEnqueueRequest> files, CancellationToken cancellationToken = default)
    {
        var enqueued = new List<Transfer>();
        foreach (var file in files)
        {
            var t = new Transfer
            {
                Id = Guid.NewGuid(),
                Username = username ?? "",
                Filename = file.Filename ?? "",
                Size = file.Size,
                Direction = Soulseek.TransferDirection.Download,
                State = TransferStates.Queued,
                BytesTransferred = 0,
                AverageSpeed = 0,
                RequestedAt = DateTime.UtcNow,
                BatchId = file.BatchId,
                DestinationDirectory = file.DestinationDirectory,
            };
            _storage[t.Id] = t;
            enqueued.Add(t);
        }
        return Task.FromResult((enqueued, new List<string>()));
    }

    public Transfer Find(Expression<Func<Transfer, bool>> expression)
    {
        var pred = expression.Compile();
        foreach (var t in _storage.Values)
            if (pred(t)) return t;
        return null!;
    }

    public Task<int> GetPlaceInQueueAsync(Guid id) => Task.FromResult(0);

    public List<Transfer> List(Expression<Func<Transfer, bool>>? expression = null, bool includeRemoved = false)
    {
        var list = includeRemoved ? _storage.Values.ToList() : _storage.Values.Where(t => !t.Removed).ToList();
        if (expression != null)
        {
            var pred = expression.Compile();
            list = list.Where(pred).ToList();
        }
        return list;
    }

    public async IAsyncEnumerable<Transfer> StreamAutoRetryCandidatesAsync(
        DateTime endedBefore,
        [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var candidates = _storage.Values
            .Where(transfer => transfer.Direction == Soulseek.TransferDirection.Download)
            .Where(transfer => !transfer.Removed)
            .Where(transfer =>
                (transfer.State & TransferStates.Completed) == TransferStates.Completed &&
                (transfer.State & TransferStates.Succeeded) != TransferStates.Succeeded &&
                (transfer.State & TransferStates.Cancelled) != TransferStates.Cancelled &&
                (transfer.State & TransferStates.Rejected) != TransferStates.Rejected)
            .Where(transfer => transfer.EndedAt.HasValue && transfer.EndedAt.Value < endedBefore)
            .OrderBy(transfer => transfer.EndedAt)
            .ThenBy(transfer => transfer.Id);

        foreach (var transfer in candidates)
        {
            cancellationToken.ThrowIfCancellationRequested();
            yield return transfer;
            await Task.Yield();
        }
    }

    public int Count(bool includeRemoved = false)
        => includeRemoved ? _storage.Count : _storage.Values.Count(transfer => !transfer.Removed);

    public List<Transfer> ListCompleted(DateTime asOf, int offset, int limit)
        => _storage.Values
            .Where(transfer =>
                (transfer.State & TransferStates.Completed) == TransferStates.Completed &&
                (transfer.State & TransferStates.Succeeded) == TransferStates.Succeeded)
            .Where(transfer => transfer.EndedAt.HasValue && transfer.EndedAt.Value <= asOf)
            .OrderByDescending(transfer => transfer.EndedAt)
            .ThenByDescending(transfer => transfer.RequestedAt)
            .ThenByDescending(transfer => transfer.Id)
            .Skip(offset)
            .Take(limit)
            .ToList();

    public int Prune(int age, TransferStates stateHasFlag = TransferStates.Completed) => 0;

    public int PruneRemoved(int age) => 0;

    public void Remove(Guid id, bool deleteFile = false)
    {
        if (_storage.TryGetValue(id, out var t)) t.Removed = true;
    }

    public bool TryCancel(Guid id) => false;

    public bool TryFail(Guid id, Exception exception) => false;

    public Task ShutdownAsync(CancellationToken cancellationToken = default) => Task.CompletedTask;

    public void Update(Transfer transfer)
    {
        _storage[transfer.Id] = transfer;
    }

    public void Dispose() { }
}

internal class StubLibraryHealthService : ILibraryHealthService
{
    public Task<string> StartScanAsync(LibraryHealthScanRequest request, CancellationToken ct = default) => Task.FromResult(Guid.NewGuid().ToString("N"));

    public Task<LibraryHealthScan?> GetScanStatusAsync(string scanId, CancellationToken ct = default) => Task.FromResult<LibraryHealthScan?>(new LibraryHealthScan
    {
        ScanId = scanId,
        LibraryPath = "(all)",
        StartedAt = DateTimeOffset.UtcNow,
        CompletedAt = DateTimeOffset.UtcNow,
        Status = ScanStatus.Completed
    });

    public Task<List<LibraryIssue>> GetIssuesAsync(LibraryHealthIssueFilter filter, CancellationToken ct = default) => Task.FromResult(new List<LibraryIssue>());
    public Task<LibraryIssuePage> GetIssuePageAsync(LibraryHealthIssueFilter filter, CancellationToken ct = default) => Task.FromResult(new LibraryIssuePage());
    public Task<List<LibraryIssueTypeSummary>> GetIssueTypeSummariesAsync(string libraryPath, CancellationToken ct = default) => Task.FromResult(new List<LibraryIssueTypeSummary>());
    public Task<List<LibraryIssueArtistSummary>> GetIssueArtistSummariesAsync(string libraryPath, int limit, CancellationToken ct = default) => Task.FromResult(new List<LibraryIssueArtistSummary>());
    public Task<List<LibraryIssueReleaseSummary>> GetIssueReleaseSummariesAsync(string libraryPath, int limit, CancellationToken ct = default) => Task.FromResult(new List<LibraryIssueReleaseSummary>());
    public Task<List<IssueCodecGroup>> GetIssueCodecSummariesAsync(string libraryPath, CancellationToken ct = default) => Task.FromResult(new List<IssueCodecGroup>());
    public Task<LibraryHealthDashboard> GetDashboardAsync(string libraryPath, int artistLimit, int issueLimit, CancellationToken ct = default) => Task.FromResult(new LibraryHealthDashboard { Summary = new LibraryHealthSummary { LibraryPath = libraryPath } });

    public Task UpdateIssueStatusAsync(string issueId, LibraryIssueStatus newStatus, CancellationToken ct = default) => Task.CompletedTask;

    public Task<string> CreateRemediationJobAsync(List<string> issueIds, CancellationToken ct = default) => Task.FromResult(Guid.NewGuid().ToString("N"));

    public Task<LibraryHealthSummary> GetSummaryAsync(string libraryPath, CancellationToken ct = default) => Task.FromResult(new LibraryHealthSummary { LibraryPath = libraryPath ?? "(all)", TotalIssues = 0, IssuesOpen = 0, IssuesResolved = 0 });
}

/// <summary>Configurable bridge API for integration tests. Resolve as StubBridgeApi to seed SearchResults/Rooms.</summary>
internal class StubBridgeApi : IBridgeApi
{
    public Task<LegacyTransferProgress?> GetTransferProgressAsync(string transferId, CancellationToken ct = default) =>
        Task.FromResult<LegacyTransferProgress?>(null);

    public List<BridgeUser> SearchResults { get; set; } = new();
    public List<BridgeRoom> Rooms { get; set; } = new();

    public Task<BridgeSearchResult> SearchAsync(string query, CancellationToken ct = default) =>
        Task.FromResult(new BridgeSearchResult { Query = query, Users = SearchResults });

    public Task<string> DownloadAsync(string username, string filename, string? targetPath, CancellationToken ct = default) =>
        Task.FromResult(Guid.NewGuid().ToString("N"));

    public Task<List<BridgeRoom>> GetRoomsAsync(CancellationToken ct = default) =>
        Task.FromResult(Rooms);
}

/// <summary>Bridge service that does not start a real soulfind process. For integration tests.</summary>
internal class TestSoulfindBridgeService : ISoulfindBridgeService
{
    private bool _isRunning;
    private DateTimeOffset? _startedAt;

    public bool IsRunning => _isRunning;

    public Task StartAsync(CancellationToken ct = default)
    {
        _isRunning = true;
        _startedAt = DateTimeOffset.UtcNow;
        return Task.CompletedTask;
    }

    public Task StopAsync(CancellationToken ct = default)
    {
        _isRunning = false;
        _startedAt = null;
        return Task.CompletedTask;
    }

    public Task<BridgeHealthStatus> GetHealthAsync(CancellationToken ct = default) =>
        Task.FromResult(new BridgeHealthStatus
        {
            IsHealthy = _isRunning,
            Version = "1.0.0-test",
            ActiveConnections = 0,
            StartedAt = _startedAt ?? DateTimeOffset.MinValue
        });

    public void RecordClientConnection(string clientId)
    {
    }

    public void RecordClientDisconnection(string clientId)
    {
    }
}

internal class NullProxy<T> : DispatchProxy where T : class
{
    public static T Create() => DispatchProxy.Create<T, NullProxy<T>>();

    protected override object? Invoke(MethodInfo? targetMethod, object?[]? args)
    {
        var returnType = targetMethod?.ReturnType;
        if (returnType == null || returnType == typeof(void)) return null;

        if (returnType == typeof(Task)) return Task.CompletedTask;
        if (returnType.IsGenericType && returnType.GetGenericTypeDefinition() == typeof(Task<>))
        {
            var resultType = returnType.GenericTypeArguments[0];
            var result = resultType.IsValueType ? Activator.CreateInstance(resultType) : null;
            return typeof(Task).GetMethod(nameof(Task.FromResult))!.MakeGenericMethod(resultType).Invoke(null, new[] { result });
        }

        if (returnType == typeof(ValueTask)) return new ValueTask();
        if (returnType.IsGenericType && returnType.GetGenericTypeDefinition() == typeof(ValueTask<>))
        {
            var resultType = returnType.GenericTypeArguments[0];
            var value = resultType.IsValueType ? Activator.CreateInstance(resultType) : null;
            return Activator.CreateInstance(typeof(ValueTask<>).MakeGenericType(resultType), value);
        }

        return returnType.IsValueType ? Activator.CreateInstance(returnType) : null;
    }
}

// Stub implementations for SearchActionsController tests

internal class StubShareService : IShareService
{
    private readonly IShareRepository _repository;
    private readonly slskd.Shares.Host _localHost;

    public StubShareService(IShareRepository repository)
    {
        _repository = repository;
        _localHost = new slskd.Shares.Host("local");
    }

    public IShareRepository GetLocalRepository() => _repository;
    public IReadOnlyList<slskd.Shares.Host> Hosts => new[] { _localHost };
    public slskd.Shares.Host LocalHost => _localHost;
    public slskd.IStateMonitor<slskd.ShareState> StateMonitor => NullProxy<slskd.IStateMonitor<slskd.ShareState>>.Create();
    public bool IsScanning => false;

    public void AddOrUpdateHost(slskd.Shares.Host host) { }
    public Task<IEnumerable<Soulseek.Directory>> BrowseAsync(slskd.Shares.Share share = null) => Task.FromResult(Enumerable.Empty<Soulseek.Directory>());
    public Task DumpAsync(string filename) => Task.CompletedTask;
    public Task InitializeAsync(bool forceRescan = false) => Task.CompletedTask;
    public Task<Soulseek.Directory> ListDirectoryAsync(string directory) => Task.FromResult(new Soulseek.Directory(directory));
    public Task<IEnumerable<slskd.Shares.Scan>> ListScansAsync(long startedAtOrAfter = 0) => Task.FromResult(Enumerable.Empty<slskd.Shares.Scan>());
    public void RequestScan() { }
    public Task<(string Host, string Filename, long Size)> ResolveFileAsync(string remoteFilename) => Task.FromResult(("local", remoteFilename, 0L));
    public Task ScanAsync() => Task.CompletedTask;
    public Task<IEnumerable<Soulseek.File>> SearchAsync(Soulseek.SearchQuery query, int? limit = null) => Task.FromResult(Enumerable.Empty<Soulseek.File>());
    public Task<IEnumerable<Soulseek.File>> SearchLocalAsync(Soulseek.SearchQuery query) => Task.FromResult(Enumerable.Empty<Soulseek.File>());
    public bool TryCancelScan() => false;
    public bool TryGetHost(string name, out slskd.Shares.Host host) { host = _localHost; return name == "local"; }
    public bool TryRemoveHost(string name) => false;

    public void Dispose() { }
}

internal class StubContentLocator : IContentLocator
{
    private readonly IShareService _shareService;
    private readonly ILogger<StubContentLocator> _logger;

    public StubContentLocator(IShareService shareService, ILogger<StubContentLocator> logger)
    {
        _shareService = shareService;
        _logger = logger;
    }

    // This fixture intentionally has no local content; registrations remain unavailable.
    public string? RegisterLocalFile(string absolutePath) => null;

    public ResolvedContent? Resolve(string contentId, CancellationToken cancellationToken = default)
    {
        // For tests, return null (content not local) to test remote download path
        return null;
    }
}

internal class StubMeshContentFetcher : IMeshContentFetcher
{
    private readonly Dictionary<(string PeerId, string ContentId), byte[]> _contentStore = new();
    private readonly HashSet<(string PeerId, string ContentId, MeshRadioScope Radio)> _radioScopes = new();

    public void SeedRadioContent(string peerId, string contentId, MeshRadioScope radio, byte[] content)
    {
        SeedContent(peerId, contentId, content);
        _radioScopes.Add((peerId, contentId, radio));
    }

    public Task<MeshContentFetchResult> FetchRadioAsync(string peerId, string contentId, MeshRadioScope radio, long offset, int length, CancellationToken cancellationToken = default)
    {
        if (!_radioScopes.Contains((peerId, contentId, radio)))
        {
            return Task.FromResult(new MeshContentFetchResult { Error = "Radio capability is unavailable.", SizeValid = false });
        }

        return FetchAsync(peerId, contentId, expectedSize: length, offset: offset, length: length, cancellationToken: cancellationToken);
    }


    /// <summary>
    /// Seeds content for testing. Call this in tests to set up expected fetch results.
    /// </summary>
    public void SeedContent(string peerId, string contentId, byte[] content)
    {
        _contentStore[(peerId, contentId)] = content;
    }

    public Task<MeshContentFetchResult> FetchAsync(
        string peerId,
        string contentId,
        long? expectedSize = null,
        string? expectedHash = null,
        long offset = 0,
        int length = 0,
        CancellationToken cancellationToken = default)
    {
        var key = (peerId, contentId);
        if (!_contentStore.TryGetValue(key, out var content))
        {
            return Task.FromResult(new MeshContentFetchResult
            {
                Error = "Content not found",
                SizeValid = false,
                HashValid = false
            });
        }

        // Handle range requests
        var actualContent = content;
        if (offset > 0 || (length > 0 && length < content.Length))
        {
            var start = (int)offset;
            var end = length > 0 ? Math.Min(start + length, content.Length) : content.Length;
            actualContent = new byte[end - start];
            Array.Copy(content, start, actualContent, 0, end - start);
        }

        var result = new MeshContentFetchResult
        {
            Data = new MemoryStream(actualContent),
            Size = actualContent.Length,
            SizeValid = !expectedSize.HasValue || actualContent.Length == expectedSize.Value,
            HashValid = true // Skip hash validation in tests for simplicity
        };

        return Task.FromResult(result);
    }
}

internal class StubMeshDirectory : IMeshDirectory
{
    private readonly Dictionary<string, List<MeshPeerDescriptor>> _peersByContent = new();

    /// <summary>
    /// Seeds peers for testing. Call this in tests to set up expected peer lookups.
    /// </summary>
    public void SeedPeers(string contentId, params MeshPeerDescriptor[] peers)
    {
        _peersByContent[contentId] = peers.ToList();
    }

    public Task<MeshPeerDescriptor?> FindPeerByIdAsync(string peerId, CancellationToken ct = default)
    {
        // Find peer in any content's peer list
        foreach (var peers in _peersByContent.Values)
        {
            var peer = peers.FirstOrDefault(p => p.PeerId == peerId);
            if (peer != null)
                return Task.FromResult<MeshPeerDescriptor?>(peer);
        }
        return Task.FromResult<MeshPeerDescriptor?>(null);
    }

    public Task<IReadOnlyList<MeshPeerDescriptor>> FindPeersByContentAsync(string contentId, CancellationToken ct = default)
    {
        if (_peersByContent.TryGetValue(contentId, out var peers))
        {
            return Task.FromResult<IReadOnlyList<MeshPeerDescriptor>>(peers);
        }
        return Task.FromResult<IReadOnlyList<MeshPeerDescriptor>>(Array.Empty<MeshPeerDescriptor>());
    }

    public Task<IReadOnlyList<MeshContentDescriptor>> FindContentByPeerAsync(string peerId, CancellationToken ct = default)
    {
        var contentList = new List<MeshContentDescriptor>();
        foreach (var (contentId, peers) in _peersByContent)
        {
            if (peers.Any(p => p.PeerId == peerId))
            {
                contentList.Add(new MeshContentDescriptor(contentId, null, null, null));
            }
        }
        return Task.FromResult<IReadOnlyList<MeshContentDescriptor>>(contentList);
    }
}

internal class StubSearchService : ISearchService
{
    private readonly ConcurrentDictionary<Guid, global::slskd.Search.Search> _searches = new();

    /// <summary>
    /// Seeds a search for testing. Call this in tests to set up expected search results.
    /// </summary>
    public void SeedSearch(global::slskd.Search.Search search)
    {
        _searches[search.Id] = search;
    }

    public Task DeleteAsync(global::slskd.Search.Search search)
    {
        _searches.TryRemove(search.Id, out _);
        return Task.CompletedTask;
    }

    public Task<global::slskd.Search.Search> FindAsync(System.Linq.Expressions.Expression<Func<global::slskd.Search.Search, bool>> expression, bool includeResponses = false)
    {
        var compiled = expression.Compile();
        var search = _searches.Values.FirstOrDefault(compiled);
        if (search == null)
        {
            return Task.FromResult<global::slskd.Search.Search>(null!);
        }
        return Task.FromResult(search);
    }

    public Task<List<global::slskd.Search.Search>> ListAsync(System.Linq.Expressions.Expression<Func<global::slskd.Search.Search, bool>> expression = null, int limit = 0, int offset = 0, string? source = null)
    {
        var searches = expression != null
            ? _searches.Values.Where(expression.Compile()).ToList()
            : _searches.Values.ToList();

        if (!string.IsNullOrWhiteSpace(source))
        {
            var sourceFilter = source!.Trim().ToLowerInvariant();
            searches = searches.Where(s => s.Source.ToLowerInvariant() == sourceFilter).ToList();
        }

        if (offset > 0)
            searches = searches.Skip(offset).ToList();
        if (limit > 0)
            searches = searches.Take(limit).ToList();

        return Task.FromResult(searches);
    }

    public void Update(global::slskd.Search.Search search)
    {
        _searches[search.Id] = search;
    }

    public Task<global::slskd.Search.Search> StartAsync(Guid id, Soulseek.SearchQuery query, Soulseek.SearchScope scope, Soulseek.SearchOptions options = null, List<string> requestedProviders = null)
    {
        return StartAsync(id, query, scope, options, requestedProviders, "user");
    }

    public Task<global::slskd.Search.Search> StartAsync(Guid id, Soulseek.SearchQuery query, Soulseek.SearchScope scope, Soulseek.SearchOptions options, List<string> requestedProviders, string safetySource, Guid? wishlistItemId = null)
    {
        var search = new global::slskd.Search.Search
        {
            Id = id,
            SearchText = query.SearchText,
            State = Soulseek.SearchStates.Completed,
            StartedAt = DateTime.UtcNow,
            EndedAt = DateTime.UtcNow,
            Token = 0
        };
        _searches[id] = search;
        return Task.FromResult(search);
    }

    public bool TryCancel(Guid id)
    {
        if (_searches.TryGetValue(id, out var search))
        {
            search.State = Soulseek.SearchStates.Cancelled;
            return true;
        }
        return false;
    }

    public Task<int> PruneAsync(int age) => Task.FromResult(0);
    public Task<int> DeleteAllAsync() => Task.FromResult(0);
    public Task<int> CleanupAsync(int maxAgeDays = 0, int maxCount = 0) => Task.FromResult(0);
    public Task<List<global::slskd.Search.Search>> GetByWishlistItemIdAsync(Guid wishlistItemId, int limit = 50) => Task.FromResult(new List<global::slskd.Search.Search>());

    public void Dispose() { }
}
