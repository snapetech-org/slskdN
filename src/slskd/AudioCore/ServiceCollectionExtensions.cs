// <copyright file="ServiceCollectionExtensions.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.AudioCore
{
    using System;
    using Microsoft.Extensions.DependencyInjection;
    using Microsoft.Extensions.Logging;
    using Microsoft.Extensions.Options;
    using slskd.Audio;
    using slskd.Events;
    using slskd.HashDb;
    using slskd.HashDb.Optimization;
    using slskd.Integrations.AcoustId;
    using slskd.Integrations.AutoTagging;
    using slskd.Integrations.Chromaprint;
    using slskd.Integrations.MetadataFacade;
    using slskd.Integrations.MusicBrainz;
    using slskd.LibraryHealth;
    using slskd.LibraryHealth.Remediation;
    using slskd.MediaCore;
    using slskd.VirtualSoulfind.Core.Music;
    using slskdOptions = slskd.Options;

    /// <summary>
    ///     DI extensions for the AudioCore domain module. T-913.
    /// </summary>
    public static class ServiceCollectionExtensions
    {
        /// <summary>
        ///     Registers all AudioCore services: fingerprinting (Chromaprint), HashDb, IMediaVariantStore,
        ///     ICanonicalStatsService, IDedupeService, IAnalyzerMigrationService, ILibraryHealthService,
        ///     ILibraryHealthRemediationService, IMusicContentDomainProvider.
        /// </summary>
        /// <param name="services">The service collection.</param>
        /// <param name="appDirectory">The application data directory (for HashDb).</param>
        /// <returns>The service collection for chaining.</returns>
        /// <remarks>
        ///     Must be called after <see cref="EventBus"/>,
        ///     <see cref="IAcoustIdClient"/>, <see cref="IAutoTaggingService"/>, <see cref="IMusicBrainzClient"/> are registered.
        ///     See <see cref="AudioCore"/> for the full API boundary.
        /// </remarks>
        public static IServiceCollection AddAudioCore(this IServiceCollection services, string appDirectory)
        {
            if (services == null)
            {
                throw new ArgumentNullException(nameof(services));
            }

            if (string.IsNullOrEmpty(appDirectory))
            {
                throw new ArgumentException("App directory must be non-empty.", nameof(appDirectory));
            }

            // Fingerprinting (Chromaprint)
            services.AddSingleton<IChromaprintService, ChromaprintService>();
            services.AddSingleton<IFingerprintExtractionService, FingerprintExtractionService>();

            // Spectral transcode detection (opt-in via audio.spectral_analysis; idle unless enabled and requested)
            services.AddSingleton<ISpectralAnalyzer, SpectralAnalyzer>();

            // HashDb and MediaVariant store (Music)
            services.AddSingleton<IHashDbService>(sp => new HashDbService(
                appDirectory,
                sp.GetRequiredService<EventBus>(),
                sp,
                sp.GetRequiredService<IFingerprintExtractionService>(),
                sp.GetRequiredService<IAcoustIdClient>(),
                sp.GetRequiredService<IAutoTaggingService>(),
                sp.GetRequiredService<IMusicBrainzClient>(),
                sp.GetRequiredService<IOptionsMonitor<slskdOptions>>(),
                sp.GetService<Microsoft.Extensions.Caching.Memory.IMemoryCache>(),
                sp.GetRequiredService<ISpectralAnalyzer>()));
            services.AddSingleton<IMediaVariantStore, HashDbMediaVariantStore>();

            // HashDb optimization service
            var hashDbPath = System.IO.Path.Combine(appDirectory, "hashdb.db");
            services.AddSingleton<HashDb.Optimization.IHashDbOptimizationService>(sp =>
                new HashDb.Optimization.HashDbOptimizationService(
                    hashDbPath,
                    sp.GetRequiredService<ILogger<HashDb.Optimization.HashDbOptimizationService>>()));

            // HashDb optimization options (default: auto-optimize disabled)
            services.Configure<HashDb.Optimization.HashDbOptimizationOptions>(options =>
            {
                // Auto-optimization disabled by default (users can enable via config if needed)
                options.AutoOptimizeOnStartup = false;
            });

            // HashDb optimization hosted service (runs optimization on startup if enabled)
            services.AddHostedService<HashDb.Optimization.HashDbOptimizationHostedService>();

            // Canonical, dedupe, analyzer migration
            services.AddSingleton<ICanonicalStatsService, CanonicalStatsService>();
            services.AddSingleton<IDedupeService, DedupeService>();
            services.AddSingleton<IAnalyzerMigrationService, AnalyzerMigrationService>();

            // Library health
            services.AddSingleton<ILibraryHealthService>(sp => new LibraryHealthService(
                sp.GetRequiredService<IHashDbService>(),
                sp.GetRequiredService<ILibraryHealthRemediationService>(),
                sp.GetRequiredService<IMetadataFacade>(),
                sp.GetRequiredService<ICanonicalStatsService>(),
                sp.GetRequiredService<IMusicBrainzClient>(),
                sp.GetRequiredService<IOptionsMonitor<slskd.Options>>(),
                sp.GetRequiredService<ILogger<LibraryHealth.LibraryHealthService>>(),
                sp.GetRequiredService<ISpectralAnalyzer>()));
            services.AddSingleton<ILibraryHealthRemediationService, LibraryHealthRemediationService>();

            // Music domain provider
            services.AddSingleton<IMusicContentDomainProvider, MusicContentDomainProvider>();

            return services;
        }
    }
}
