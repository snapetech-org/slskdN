// <copyright file="HashDbService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.HashDb
{
    using System;
    using System.Collections.Generic;
    using System.Collections.Concurrent;
    using System.Diagnostics;
    using System.Globalization;
    using System.IO;
    using System.Linq;
    using System.Security.Cryptography;
    using System.Text.Json;
    using System.Threading;
    using System.Threading.Tasks;
    using Microsoft.Data.Sqlite;
    using Microsoft.Extensions.Caching.Memory;
    using Microsoft.Extensions.Options;
    using slskd.Telemetry;
    using Serilog;
    using slskd;
    using slskd.Audio;
    using slskd.Audio.Analyzers;
    using slskd.Capabilities;
    using slskd.Common.Security;
    using slskd.Events;
    using slskd.HashDb.Models;
    using slskd.Integrations.AcoustId;
    using slskd.Integrations.AutoTagging;
    using slskd.Integrations.Chromaprint;
    using slskd.Integrations.MusicBrainz;
    using slskd.Integrations.MusicBrainz.Models;
    using slskd.Jobs;
    using slskd.Mesh;
    using TagLib;
    using slskdOptions = slskd.Options;

    /// <summary>
    ///     SQLite-based hash database service.
    /// </summary>
    public partial class HashDbService : IHashDbService
    {
        /// <summary>
        ///     Size of verification chunk for hashing (32KB).
        /// </summary>
        private const int HashChunkSize = 32768;
        private const int FlacInventoryUpsertBatchSize = 100;
        private const int PeerUpsertBatchSize = 500;
        private const int MeshMergeLookupBatchSize = 500;
        private const int MeshMergeInsertBatchSize = 100;
        private const int AlbumTrackUpsertBatchSize = 100;
        private const int ReleaseJobUpsertBatchSize = 100;
        private const int CanonicalStatsUpsertBatchSize = 100;
        private const int VariantAnalysisUpdateBatchSize = 100;
        private const int HashLookupBatchSize = 500;
        private const int WarmCachePopularityUpsertBatchSize = 400;
        private const string SqlDotNetWhitespaceCharacterSet =
            "char(9) || char(10) || char(11) || char(12) || char(13) || " +
            "char(32) || char(133) || char(160) || char(5760) || " +
            "char(8192) || char(8193) || char(8194) || char(8195) || " +
            "char(8196) || char(8197) || char(8198) || char(8199) || " +
            "char(8200) || char(8201) || char(8202) || char(8232) || " +
            "char(8233) || char(8239) || char(8287) || char(12288)";

        private readonly string dbPath;
        private readonly ILogger log = Log.ForContext<HashDbService>();
        private readonly IServiceProvider? serviceProvider;
        private readonly IFingerprintExtractionService? fingerprintExtractionService;
        private readonly IAcoustIdClient? acoustIdClient;
        private readonly IAutoTaggingService? autoTaggingService;
        private readonly IMusicBrainzClient? musicBrainzClient;
        private readonly IOptionsMonitor<slskdOptions>? optionsMonitor;
        private readonly AudioSketchService? audioSketchService;
        private readonly ISpectralAnalyzer? spectralAnalyzer;
        private readonly QualityScorer qualityScorer = new();
        private readonly TranscodeDetector transcodeDetector = new();
        private readonly FlacAnalyzer flacAnalyzer = new();
        private readonly Mp3Analyzer mp3Analyzer = new();
        private readonly OpusAnalyzer opusAnalyzer = new();
        private readonly AacAnalyzer aacAnalyzer = new();
        private readonly IMemoryCache? hashCache;
        private static readonly JsonSerializerOptions CaseInsensitiveJson = new()
        {
            PropertyNameCaseInsensitive = true,
        };
        private long currentSeqId;
        private readonly ConcurrentDictionary<Guid, MetadataProcessingEvent> activeMetadataProcessing = new();
        private readonly ConcurrentQueue<MetadataProcessingEvent> metadataProcessingHistory = new();

        /// <summary>
        ///     Initializes a new instance of the <see cref="HashDbService"/> class.
        /// </summary>
        /// <param name="appDirectory">The application data directory.</param>
        /// <param name="eventBus">The event bus for subscribing to download events (optional).</param>
        /// <param name="serviceProvider">Service provider for lazy resolution of mesh sync (optional).</param>
        /// <param name="fingerprintExtractionService">Fingerprint extraction service (optional).</param>
        /// <param name="acoustIdClient">AcoustID client (optional).</param>
        /// <param name="autoTaggingService">Auto-tagging service (optional).</param>
        /// <param name="musicBrainzClient">MusicBrainz client (optional).</param>
        /// <param name="optionsMonitor">Options monitor for feature-dependent behavior (optional).</param>
        /// <param name="hashCache">Hash lookup cache (optional).</param>
        /// <param name="spectralAnalyzer">Spectral transcode detection for completed lossless downloads (optional; idle unless enabled).</param>
        public HashDbService(
            string appDirectory,
            EventBus? eventBus = null,
            IServiceProvider? serviceProvider = null,
            IFingerprintExtractionService? fingerprintExtractionService = null,
            IAcoustIdClient? acoustIdClient = null,
            IAutoTaggingService? autoTaggingService = null,
            IMusicBrainzClient? musicBrainzClient = null,
            IOptionsMonitor<slskdOptions>? optionsMonitor = null,
            IMemoryCache? hashCache = null,
            ISpectralAnalyzer? spectralAnalyzer = null)
        {
            this.spectralAnalyzer = spectralAnalyzer;
            this.serviceProvider = serviceProvider;
            this.fingerprintExtractionService = fingerprintExtractionService;
            this.acoustIdClient = acoustIdClient;
            this.autoTaggingService = autoTaggingService;
            this.musicBrainzClient = musicBrainzClient;
            this.optionsMonitor = optionsMonitor;
            this.hashCache = hashCache;
            if (optionsMonitor != null)
            {
                audioSketchService = new AudioSketchService(optionsMonitor);
            }

            dbPath = Path.Combine(appDirectory, "hashdb.db");
            InitializeDatabase();
            currentSeqId = GetLatestSeqIdSync();
            log.Information("[HashDb] Initialized at {Path}, current seq_id: {SeqId}",
                LoggingSanitizer.SanitizeFilePath(dbPath), currentSeqId);

            // Subscribe to events for hash discovery
            if (eventBus != null)
            {
                // Hash downloaded files
                eventBus.Subscribe<DownloadFileCompleteEvent>("HashDbService.DownloadComplete", OnDownloadCompleteAsync);

                // Discover FLAC files from search results for passive hash gathering
                eventBus.Subscribe<SearchResponsesReceivedEvent>("HashDbService.SearchResponses", OnSearchResponsesReceivedAsync);

                // Track peers who interact with us (for future passive browsing)
                eventBus.Subscribe<PeerSearchedUsEvent>("HashDbService.PeerSearchedUs", OnPeerSearchedUsAsync);
                eventBus.Subscribe<PeerDownloadedFromUsEvent>("HashDbService.PeerDownloadedFromUs", OnPeerDownloadedFromUsAsync);

                log.Information("[HashDb] Subscribed to download, search, and peer interaction events for hash discovery");
            }
        }

        /// <summary>
        ///     Handles when a peer searches us - track them for future passive FLAC discovery.
        /// </summary>
        private async Task OnPeerSearchedUsAsync(PeerSearchedUsEvent evt)
        {
            try
            {
                // Track this peer - they're active on the network and might have FLACs we want
                await TouchPeerAsync(evt.Username);
                log.Debug("[HashDb] Tracked peer {Username} who searched us (had results: {HadResults})",
                    LoggingSanitizer.SanitizeExternalIdentifier(evt.Username), evt.HadResults);
            }
            catch (Exception ex)
            {
                log.Warning(ex, "[HashDb] Error tracking peer {Username} from search",
                    LoggingSanitizer.SanitizeExternalIdentifier(evt.Username));
            }
        }

        /// <summary>
        ///     Handles when a peer downloads from us - track them for future passive FLAC discovery.
        /// </summary>
        private async Task OnPeerDownloadedFromUsAsync(PeerDownloadedFromUsEvent evt)
        {
            try
            {
                // Track this peer - they're active and downloading, good candidate for FLAC discovery
                await TouchPeerAsync(evt.Username);
                log.Debug("[HashDb] Tracked peer {Username} who downloaded {File}",
                    LoggingSanitizer.SanitizeExternalIdentifier(evt.Username), LoggingSanitizer.SanitizeFilePath(evt.Filename));
            }
            catch (Exception ex)
            {
                log.Warning(ex, "[HashDb] Error tracking peer {Username} from download",
                    LoggingSanitizer.SanitizeExternalIdentifier(evt.Username));
            }
        }

        /// <summary>
        ///     Handles search responses by discovering FLAC files for the inventory.
        /// </summary>
        private async Task OnSearchResponsesReceivedAsync(SearchResponsesReceivedEvent evt)
        {
            try
            {
                var flacCount = 0;
                var skippedCount = 0;

                IEnumerable<FlacInventoryEntry> EnumerateEntries()
                {
                    foreach (var response in evt.Responses)
                    {
                        foreach (var file in response.Files)
                        {
                            // Only interested in FLAC files large enough to hash
                            if (!file.Filename.EndsWith(".flac", StringComparison.OrdinalIgnoreCase))
                            {
                                continue;
                            }

                            if (file.Size < HashChunkSize)
                            {
                                skippedCount++;
                                continue;
                            }

                            flacCount++;
                            yield return new FlacInventoryEntry
                            {
                                PeerId = response.Username,
                                Path = file.Filename,
                                Size = file.Size,
                                HashStatusStr = "none",
                            };
                        }
                    }
                }

                using var conn = GetConnection();
                using var transaction = conn.BeginTransaction();
                var ingestion = await UpsertFlacEntriesInBatchesAsync(
                    conn,
                    transaction,
                    EnumerateEntries(),
                    CancellationToken.None).ConfigureAwait(false);
                transaction.Commit();

                if (flacCount > 0)
                {
                    log.Debug(
                        "[HashDb] Discovered {Count} FLAC files from search results with {CommandCount} database commands ({Skipped} too small)",
                        flacCount,
                        ingestion.CommandCount,
                        skippedCount);
                }
            }
            catch (Exception ex)
            {
                log.Warning(ex, "[HashDb] Error processing search responses for FLAC discovery");
            }
        }

        /// <summary>
        ///     Handles download completion by hashing the file and storing in the database.
        /// </summary>
        private async Task OnDownloadCompleteAsync(DownloadFileCompleteEvent evt)
        {
            var filename = Path.GetFileName(evt.LocalFilename);
            var pipeline = BeginMetadataStage(filename, "hash");
            try
            {
                var localFilename = evt.LocalFilename;
                var fileSize = evt.Transfer.Size;

                if (!IsAudioHashCandidate(localFilename, evt.RemoteFilename))
                {
                    log.Debug("[HashDb] Skipping hash for non-audio completed download {Filename}",
                        LoggingSanitizer.SanitizeFilePath(localFilename));
                    FinishMetadataStage(pipeline, "skipped", "Not a supported audio file");
                    return;
                }

                // Only hash files that are large enough
                if (fileSize < HashChunkSize)
                {
                    log.Debug("[HashDb] Skipping hash for {Filename}: file too small ({Size} bytes)",
                        LoggingSanitizer.SanitizeFilePath(localFilename), fileSize);
                    FinishMetadataStage(pipeline, "skipped", "File is too small for hashing");
                    return;
                }

                // Check if we already have a hash for this file
                var flacKey = HashDbEntry.GenerateFlacKey(evt.RemoteFilename, fileSize);
                var existing = await LookupHashAsync(flacKey);
                if (existing != null)
                {
                    log.Debug("[HashDb] Hash already exists for {Filename}", LoggingSanitizer.SanitizeFilePath(localFilename));
                    await IncrementHashUseCountAsync(flacKey);
                    FinishMetadataStage(pipeline, "complete", "Existing hash reused");
                    return;
                }

                // Hash the first 32KB of the downloaded file
                var hash = await ComputeFileHashAsync(localFilename);
                if (hash == null)
                {
                    log.Warning("[HashDb] Failed to compute hash for {Filename}", LoggingSanitizer.SanitizeFilePath(localFilename));
                    FinishMetadataStage(pipeline, "failed", "Hash computation failed");
                    return;
                }

                // Store the hash locally
                await StoreHashFromVerificationAsync(evt.RemoteFilename, fileSize, hash);
                log.Information("[HashDb] Stored hash for downloaded file {Filename}: {Hash}",
                    LoggingSanitizer.SanitizeFilePath(localFilename), LoggingSanitizer.SanitizeHash(hash));
                FinishMetadataStage(pipeline, "complete", "Hash stored");

                // Derive variant metadata + quality score
                try
                {
                    var variant = BuildVariantFromFile(localFilename, flacKey, fileSize);
                    await ApplySpectralAnalysisAsync(variant, localFilename).ConfigureAwait(false);
                    await UpdateVariantMetadataAsync(flacKey, variant).ConfigureAwait(false);
                }
                catch (Exception ex)
                {
                    log.Warning(ex, "[HashDb] Failed to derive audio variant metadata for {Filename}",
                        LoggingSanitizer.SanitizeFilePath(localFilename));
                }

                if (fingerprintExtractionService != null)
                {
                    var fingerprintStage = BeginMetadataStage(filename, "chromaprint");
                    try
                    {
                        var fingerprint = await fingerprintExtractionService.ExtractFingerprintAsync(localFilename).ConfigureAwait(false);

                        if (!string.IsNullOrWhiteSpace(fingerprint))
                        {
                            await UpdateHashFingerprintAsync(flacKey, fingerprint).ConfigureAwait(false);
                            log.Debug("[HashDb] Stored fingerprint for {Filename}", LoggingSanitizer.SanitizeFilePath(localFilename));
                            FinishMetadataStage(fingerprintStage, "complete", "Fingerprint stored");

                            await TryResolveAcoustIdAsync(localFilename, flacKey, fingerprint).ConfigureAwait(false);
                        }
                        else
                        {
                            FinishMetadataStage(fingerprintStage, "failed", "No fingerprint produced");
                        }
                    }
                    catch (Exception ex)
                    {
                        log.Warning(ex, "[HashDb] Fingerprint extraction failed for {Filename}",
                            LoggingSanitizer.SanitizeFilePath(localFilename));
                        FinishMetadataStage(fingerprintStage, "failed", $"Fingerprint extraction failed: {ex.GetType().Name}: {ex.Message}");
                    }
                }
                else
                {
                    var skipped = BeginMetadataStage(filename, "chromaprint");
                    FinishMetadataStage(skipped, "skipped", "Chromaprint is not configured");
                }

                // Publish to mesh for other slskdn clients (lazy resolution to avoid circular dependency)
                if (serviceProvider != null)
                {
                    var meshSync = serviceProvider.GetService(typeof(IMeshSyncService)) as IMeshSyncService;
                    if (meshSync != null)
                    {
                        await meshSync.PublishHashAsync(flacKey, hash, fileSize);
                        log.Debug("[HashDb] Published hash to mesh: {Key}", LoggingSanitizer.SanitizeHash(flacKey));
                    }
                }
            }
            catch (Exception ex)
            {
                FinishMetadataStage(pipeline, "failed", $"Hash processing failed ({ex.GetType().Name})");
                log.Error(ex, "[HashDb] Error hashing downloaded file {Filename}",
                    LoggingSanitizer.SanitizeFilePath(evt.LocalFilename));
            }
        }

        public MetadataProcessingStatus GetMetadataProcessingStatus(int limit = 50)
        {
            limit = Math.Clamp(limit, 1, 200);
            return new MetadataProcessingStatus(
                activeMetadataProcessing.Values.OrderBy(item => item.StartedAt).ToList(),
                metadataProcessingHistory.Reverse().Take(limit).ToList());
        }

        private MetadataProcessingEvent BeginMetadataStage(string filename, string stage)
        {
            var item = new MetadataProcessingEvent(Guid.NewGuid(), filename, stage, "running", null, DateTime.UtcNow, null);
            activeMetadataProcessing[item.Id] = item;
            return item;
        }

        private void FinishMetadataStage(MetadataProcessingEvent item, string status, string? detail)
        {
            if (!activeMetadataProcessing.TryRemove(item.Id, out _))
            {
                return;
            }

            metadataProcessingHistory.Enqueue(item with { Status = status, Detail = detail, FinishedAt = DateTime.UtcNow });
            while (metadataProcessingHistory.Count > 200)
            {
                metadataProcessingHistory.TryDequeue(out _);
            }
        }

        private static bool IsAudioHashCandidate(params string?[] filenames)
            => filenames.Any(PathGuard.HasSafeAudioExtension);

        /// <summary>
        ///     Computes SHA256 hash of the first 32KB of a file.
        /// </summary>
        private async Task<string?> ComputeFileHashAsync(string filename)
        {
            try
            {
                filename = filename?.Trim() ?? string.Empty;
                if (!System.IO.File.Exists(filename))
                {
                    return null;
                }

                var buffer = new byte[HashChunkSize];
                int bytesRead;

                using (var fs = new FileStream(filename, FileMode.Open, FileAccess.Read, FileShare.Read, HashChunkSize, useAsync: true))
                {
                    bytesRead = await fs.ReadAsync(buffer, 0, HashChunkSize);
                }

                if (bytesRead == 0)
                {
                    return null;
                }

                using var sha256 = SHA256.Create();
                var hashBytes = sha256.ComputeHash(buffer, 0, bytesRead);
                return BitConverter.ToString(hashBytes).Replace("-", string.Empty).ToLowerInvariant();
            }
            catch (Exception ex)
            {
                log.Warning(ex, "[HashDb] Error reading file for hashing: {Filename}",
                    LoggingSanitizer.SanitizeFilePath(filename));
                return null;
            }
        }

        /// <inheritdoc/>
        public long CurrentSeqId => currentSeqId;

        /// <summary>
        ///     Measures a completed lossless download's spectral shelf when audio.spectral_analysis enables it for
        ///     downloads, recording the result on <paramref name="variant"/>. A failed analysis leaves the variant as built.
        /// </summary>
        internal async Task ApplySpectralAnalysisAsync(AudioVariant variant, string filePath)
        {
            if (spectralAnalyzer is null || !spectralAnalyzer.AnalyzeCompletedDownloads || !TranscodeDetector.IsLosslessCodec(variant.Codec))
            {
                return;
            }

            try
            {
                var result = await spectralAnalyzer
                    .AnalyzeAsync(filePath, variant.SampleRateHz, variant.DurationMs / 1000.0)
                    .ConfigureAwait(false);
                if (result is null)
                {
                    return;
                }

                result.ApplyTo(variant);
                if (result.Verdict is SpectralVerdict.Lossy or SpectralVerdict.Suspect or SpectralVerdict.Upsampled)
                {
                    log.Information("[HashDb] {Description} for {Filename}", result.Describe(), LoggingSanitizer.SanitizeFilePath(filePath));
                }
            }
            catch (Exception ex)
            {
                log.Warning(ex, "[HashDb] Spectral analysis failed for {Filename}", LoggingSanitizer.SanitizeFilePath(filePath));
            }
        }

        private AudioVariant BuildVariantFromFile(string filePath, string flacKey, long fileSize)
        {
            using var tagFile = TagLib.File.Create(filePath);
            var props = tagFile.Properties;
            var (codec, container) = MapCodecAndContainer(filePath, props);

            var variant = new AudioVariant
            {
                VariantId = flacKey,
                FlacKey = flacKey,
                MusicBrainzRecordingId = string.Empty,  // May be populated later via AcoustID/MB
                Codec = codec,
                Container = container,
                SampleRateHz = props.AudioSampleRate,
                BitDepth = props.BitsPerSample == 0 ? null : props.BitsPerSample,
                Channels = props.AudioChannels,
                DurationMs = (int)props.Duration.TotalMilliseconds,
                BitrateKbps = props.AudioBitrate,
                FileSizeBytes = fileSize,
                FirstSeenAt = DateTimeOffset.UtcNow,
                LastSeenAt = DateTimeOffset.UtcNow,
                SeenCount = 1,
                EncoderSignature = props.Codecs.FirstOrDefault()?.Description ?? string.Empty,
            };

            if (string.Equals(variant.Codec, "FLAC", StringComparison.OrdinalIgnoreCase))
            {
                try
                {
                    var flacResult = flacAnalyzer.Analyze(filePath, variant);

                    // Update core fields from STREAMINFO (more authoritative than tags)
                    if (flacResult.SampleRateHz.HasValue)
                    {
                        variant.SampleRateHz = flacResult.SampleRateHz.Value;
                    }

                    if (flacResult.BitDepth.HasValue)
                    {
                        variant.BitDepth = flacResult.BitDepth;
                    }

                    if (flacResult.Channels.HasValue)
                    {
                        variant.Channels = flacResult.Channels.Value;
                    }

                    variant.FlacStreamInfoHash42 = flacResult.FlacStreamInfoHash42;
                    variant.FlacPcmMd5 = flacResult.FlacPcmMd5;
                    variant.FlacMinBlockSize = flacResult.FlacMinBlockSize;
                    variant.FlacMaxBlockSize = flacResult.FlacMaxBlockSize;
                    variant.FlacMinFrameSize = flacResult.FlacMinFrameSize;
                    variant.FlacMaxFrameSize = flacResult.FlacMaxFrameSize;
                    variant.FlacTotalSamples = flacResult.FlacTotalSamples;
                    variant.AnalyzerVersion = flacResult.AnalyzerVersion;

                    variant.QualityScore = flacResult.QualityScore;
                    variant.TranscodeSuspect = flacResult.TranscodeSuspect;
                    variant.TranscodeReason = flacResult.TranscodeReason;
                }
                catch (Exception ex)
                {
                    log.Warning(ex, "[HashDb] FLAC analysis failed for {File}", LoggingSanitizer.SanitizeFilePath(filePath));
                    variant.QualityScore = qualityScorer.ComputeQualityScore(variant);
                    var (suspect, reason) = transcodeDetector.DetectTranscode(variant);
                    variant.TranscodeSuspect = suspect;
                    variant.TranscodeReason = reason;
                }
            }
            else if (string.Equals(variant.Codec, "MP3", StringComparison.OrdinalIgnoreCase))
            {
                try
                {
                    var mp3Result = mp3Analyzer.Analyze(filePath, variant);

                    variant.Mp3StreamHash = mp3Result.Mp3StreamHash;
                    variant.Mp3Encoder = mp3Result.Mp3Encoder;
                    variant.Mp3EncoderPreset = mp3Result.Mp3EncoderPreset;
                    variant.Mp3FramesAnalyzed = mp3Result.Mp3FramesAnalyzed;
                    variant.EffectiveBandwidthHz = mp3Result.EffectiveBandwidthHz;
                    variant.NominalLowpassHz = mp3Result.NominalLowpassHz;
                    variant.SpectralFlatnessScore = mp3Result.SpectralFlatnessScore;
                    variant.HfEnergyRatio = mp3Result.HfEnergyRatio;
                    variant.AnalyzerVersion = mp3Result.AnalyzerVersion;

                    variant.QualityScore = mp3Result.QualityScore;
                    variant.TranscodeSuspect = mp3Result.TranscodeSuspect;
                    variant.TranscodeReason = mp3Result.TranscodeReason;
                }
                catch (Exception ex)
                {
                    log.Warning(ex, "[HashDb] MP3 analysis failed for {File}", LoggingSanitizer.SanitizeFilePath(filePath));
                    variant.QualityScore = qualityScorer.ComputeQualityScore(variant);
                    var (suspect, reason) = transcodeDetector.DetectTranscode(variant);
                    variant.TranscodeSuspect = suspect;
                    variant.TranscodeReason = reason;
                }
            }
            else if (string.Equals(variant.Codec, "Opus", StringComparison.OrdinalIgnoreCase))
            {
                try
                {
                    var opusResult = opusAnalyzer.Analyze(filePath, variant);

                    variant.OpusStreamHash = opusResult.OpusStreamHash;
                    variant.OpusNominalBitrateKbps = opusResult.OpusNominalBitrateKbps;
                    variant.OpusApplication = opusResult.OpusApplication;
                    variant.OpusBandwidthMode = opusResult.OpusBandwidthMode;
                    variant.EffectiveBandwidthHz = opusResult.EffectiveBandwidthHz;
                    variant.HfEnergyRatio = opusResult.HfEnergyRatio;
                    variant.AnalyzerVersion = opusResult.AnalyzerVersion;

                    variant.QualityScore = opusResult.QualityScore;
                    variant.TranscodeSuspect = opusResult.TranscodeSuspect;
                    variant.TranscodeReason = opusResult.TranscodeReason;
                }
                catch (Exception ex)
                {
                    log.Warning(ex, "[HashDb] Opus analysis failed for {File}", LoggingSanitizer.SanitizeFilePath(filePath));
                    variant.QualityScore = qualityScorer.ComputeQualityScore(variant);
                    var (suspect, reason) = transcodeDetector.DetectTranscode(variant);
                    variant.TranscodeSuspect = suspect;
                    variant.TranscodeReason = reason;
                }
            }
            else if (string.Equals(variant.Codec, "AAC", StringComparison.OrdinalIgnoreCase))
            {
                try
                {
                    var aacResult = aacAnalyzer.Analyze(filePath, variant);

                    variant.AacStreamHash = aacResult.AacStreamHash;
                    variant.AacProfile = aacResult.AacProfile;
                    variant.AacSbrPresent = aacResult.AacSbrPresent;
                    variant.AacPsPresent = aacResult.AacPsPresent;
                    variant.AacNominalBitrateKbps = aacResult.AacNominalBitrateKbps;
                    variant.EffectiveBandwidthHz = aacResult.EffectiveBandwidthHz;
                    variant.HfEnergyRatio = aacResult.HfEnergyRatio;
                    variant.AnalyzerVersion = aacResult.AnalyzerVersion;

                    variant.QualityScore = aacResult.QualityScore;
                    variant.TranscodeSuspect = aacResult.TranscodeSuspect;
                    variant.TranscodeReason = aacResult.TranscodeReason;
                }
                catch (Exception ex)
                {
                    log.Warning(ex, "[HashDb] AAC analysis failed for {File}", LoggingSanitizer.SanitizeFilePath(filePath));
                    variant.QualityScore = qualityScorer.ComputeQualityScore(variant);
                    var (suspect, reason) = transcodeDetector.DetectTranscode(variant);
                    variant.TranscodeSuspect = suspect;
                    variant.TranscodeReason = reason;
                }
            }
            else
            {
                variant.QualityScore = qualityScorer.ComputeQualityScore(variant);
                var (suspect, reason) = transcodeDetector.DetectTranscode(variant);
                variant.TranscodeSuspect = suspect;
                variant.TranscodeReason = reason;
            }

            if (audioSketchService != null && string.IsNullOrWhiteSpace(variant.AudioSketchHash))
            {
                try
                {
                    variant.AudioSketchHash = audioSketchService.ComputeSketchHash(filePath) ?? string.Empty;
                }
                catch (Exception ex)
                {
                    log.Warning(ex, "[HashDb] Audio sketch hash failed for {File}", LoggingSanitizer.SanitizeFilePath(filePath));
                }
            }

            return variant;
        }

        private static bool CodecProfileFromCodec(string codec)
        {
            return codec switch
            {
                "FLAC" => true,
                "ALAC" => true,
                "WAV" => true,
                "AIFF" => true,
                _ => false,
            };
        }

        private static (string Codec, string Container) MapCodecAndContainer(string filePath, TagLib.Properties props)
        {
            var ext = Path.GetExtension(filePath)?.ToLowerInvariant();
            var container = string.IsNullOrWhiteSpace(ext) ? "UNKNOWN" : ext.TrimStart('.').ToUpperInvariant();

            var codec = ext switch
            {
                ".flac" => "FLAC",
                ".alac" => "ALAC",
                ".m4a" => "ALAC",
                ".aac" => "AAC",
                ".mp3" => "MP3",
                ".opus" => "Opus",
                ".ogg" => "Vorbis",
                ".wav" => "WAV",
                _ => props.Codecs.FirstOrDefault()?.Description ?? "Unknown",
            };

            return (codec, container);
        }

        private SqliteConnection GetConnection()
        {
            var conn = new SqliteConnection($"Data Source={dbPath}");
            conn.Open();
            return conn;
        }

        private void InitializeDatabase()
        {
            using var conn = GetConnection();

            // Run versioned migrations
            var migrationsApplied = Migrations.HashDbMigrations.RunMigrations(conn);
            if (migrationsApplied > 0)
            {
                log.Information("[HashDb] Applied {Count} migrations", migrationsApplied);
            }
        }

        private long GetLatestSeqIdSync()
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT COALESCE(MAX(seq_id), 0) FROM HashDb";
            var result = cmd.ExecuteScalar();
            return result == DBNull.Value ? 0 : Convert.ToInt64(result);
        }

        /// <inheritdoc/>
        public HashDbStats GetStats()
        {
            using var conn = GetConnection();
            var stats = new HashDbStats { CurrentSeqId = currentSeqId };

            using var cmd = conn.CreateCommand();
            cmd.CommandText =
                """
                WITH peer_stats AS (
                    SELECT COUNT(*) AS total,
                           COUNT(*) FILTER (WHERE caps > 0) AS slskdn
                    FROM Peers
                ),
                inventory_stats AS (
                    SELECT COUNT(*) AS total,
                           COUNT(*) FILTER (WHERE hash_status = 'known') AS hashed
                    FROM FlacInventory
                ),
                hash_stats AS (
                    SELECT COUNT(*) AS total
                    FROM HashDb
                )
                SELECT peer_stats.total,
                       peer_stats.slskdn,
                       inventory_stats.total,
                       inventory_stats.hashed,
                       hash_stats.total
                FROM peer_stats, inventory_stats, hash_stats
                """;
            using var reader = cmd.ExecuteReader();
            if (reader.Read())
            {
                stats.TotalPeers = reader.GetInt32(0);
                stats.SlskdnPeers = reader.GetInt32(1);
                stats.TotalFlacEntries = reader.GetInt32(2);
                stats.HashedFlacEntries = reader.GetInt32(3);
                stats.TotalHashEntries = reader.GetInt32(4);
            }

            if (System.IO.File.Exists(dbPath))
            {
                stats.DatabaseSizeBytes = new FileInfo(dbPath).Length;
            }

            return stats;
        }

        /// <inheritdoc/>
        public int GetSchemaVersion()
        {
            using var conn = GetConnection();
            return Migrations.HashDbMigrations.GetCurrentVersion(conn);
        }

        /// <inheritdoc/>
        public async Task UpsertAlbumTargetAsync(AlbumTarget target, CancellationToken cancellationToken = default)
        {
            if (target is null)
            {
                throw new ArgumentNullException(nameof(target));
            }

            using var conn = GetConnection();
            using var transaction = conn.BeginTransaction();

            try
            {
                await UpsertAlbumTargetInternalAsync(conn, target, cancellationToken).ConfigureAwait(false);
                transaction.Commit();
            }
            catch
            {
                transaction.Rollback();
                throw;
            }
        }

        /// <inheritdoc/>
        public async Task<AlbumTargetEntry?> GetAlbumTargetAsync(string releaseId, CancellationToken cancellationToken = default)
        {
            releaseId = releaseId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(releaseId))
            {
                return null;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT release_id, discogs_release_id, title, artist, metadata_release_date, metadata_country, metadata_label, metadata_status, created_at
                FROM AlbumTargets
                WHERE release_id = @release_id";
            cmd.Parameters.AddWithValue("@release_id", releaseId);

            await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            if (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                return ReadAlbumTargetEntry(reader);
            }

            return null;
        }

        /// <inheritdoc/>
        public async Task<IEnumerable<AlbumTargetTrackEntry>> GetAlbumTracksAsync(string releaseId, CancellationToken cancellationToken = default)
        {
            var tracks = new List<AlbumTargetTrackEntry>();
            releaseId = releaseId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(releaseId))
            {
                return tracks;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT release_id, track_position, recording_id, title, artist, duration_ms, isrc
                FROM AlbumTargetTracks
                WHERE release_id = @release_id
                ORDER BY track_position ASC";
            cmd.Parameters.AddWithValue("@release_id", releaseId);

            await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                tracks.Add(ReadAlbumTargetTrackEntry(reader));
            }

            return tracks;
        }

        /// <inheritdoc/>
        public async Task<IEnumerable<AlbumTargetTrackEntry>> GetAlbumTracksAsync(
            IEnumerable<string> releaseIds,
            CancellationToken cancellationToken = default)
        {
            var normalized = releaseIds
                .Where(releaseId => !string.IsNullOrWhiteSpace(releaseId))
                .Select(releaseId => releaseId.Trim())
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            var tracks = new List<AlbumTargetTrackEntry>();
            if (normalized.Length == 0)
            {
                return tracks;
            }

            using var conn = GetConnection();
            foreach (var batch in normalized.Chunk(500))
            {
                using var cmd = conn.CreateCommand();
                var parameters = batch.Select((_, index) => $"@release{index}").ToArray();
                cmd.CommandText = $"""
                    SELECT release_id, track_position, recording_id, title, artist, duration_ms, isrc
                    FROM AlbumTargetTracks
                    WHERE release_id IN ({string.Join(", ", parameters)})
                    ORDER BY release_id ASC, track_position ASC
                    """;

                for (var index = 0; index < batch.Length; index++)
                {
                    cmd.Parameters.AddWithValue(parameters[index], batch[index]);
                }

                await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
                while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
                {
                    tracks.Add(ReadAlbumTargetTrackEntry(reader));
                }
            }

            return tracks;
        }

        /// <inheritdoc/>
        public async Task<AlbumTargetTrackEntry?> GetAlbumTrackByRecordingIdAsync(
            string recordingId,
            CancellationToken cancellationToken = default)
        {
            recordingId = recordingId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(recordingId))
            {
                return null;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText =
                """
                SELECT track.release_id, track.track_position, track.recording_id, track.title, track.artist, track.duration_ms, track.isrc
                FROM AlbumTargetTracks AS track
                INNER JOIN AlbumTargets AS album ON album.release_id = track.release_id
                WHERE track.recording_id IS NOT NULL
                  AND track.recording_id <> ''
                  AND track.recording_id = @recording_id COLLATE NOCASE
                ORDER BY album.created_at DESC, track.track_position ASC
                LIMIT 1
                """;
            cmd.Parameters.AddWithValue("@recording_id", recordingId);

            await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            return await reader.ReadAsync(cancellationToken).ConfigureAwait(false)
                ? ReadAlbumTargetTrackEntry(reader)
                : null;
        }

        /// <inheritdoc/>
        public async Task<IEnumerable<AlbumTargetTrackEntry>> GetRecentAlbumTracksAsync(
            int count,
            CancellationToken cancellationToken = default)
        {
            var tracks = new List<AlbumTargetTrackEntry>();
            if (count <= 0)
            {
                return tracks;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText =
                """
                SELECT track.release_id, track.track_position, track.recording_id, track.title, track.artist, track.duration_ms, track.isrc
                FROM AlbumTargets AS album INDEXED BY idx_album_targets_created
                INNER JOIN AlbumTargetTracks AS track ON track.release_id = album.release_id
                ORDER BY album.created_at DESC, track.track_position ASC
                LIMIT @count
                """;
            cmd.Parameters.AddWithValue("@count", count);

            await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                tracks.Add(ReadAlbumTargetTrackEntry(reader));
            }

            return tracks;
        }

        /// <inheritdoc/>
        public async Task<IEnumerable<AlbumTargetEntry>> GetAlbumTargetsAsync(CancellationToken cancellationToken = default)
        {
            var targets = new List<AlbumTargetEntry>();
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT release_id, discogs_release_id, title, artist, metadata_release_date, metadata_country, metadata_label, metadata_status, created_at
                FROM AlbumTargets
                ORDER BY created_at DESC";

            await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                targets.Add(ReadAlbumTargetEntry(reader));
            }

            return targets;
        }

        /// <inheritdoc/>
        public async Task<IEnumerable<AlbumTargetEntry>> GetAlbumTargetsAsync(
            IEnumerable<string> releaseIds,
            CancellationToken cancellationToken = default)
        {
            var normalized = releaseIds
                .Where(releaseId => !string.IsNullOrWhiteSpace(releaseId))
                .Select(releaseId => releaseId.Trim())
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            var targets = new List<AlbumTargetEntry>();
            if (normalized.Length == 0)
            {
                return targets;
            }

            using var conn = GetConnection();
            foreach (var batch in normalized.Chunk(500))
            {
                using var cmd = conn.CreateCommand();
                var parameters = batch.Select((_, index) => $"@release{index}").ToArray();
                cmd.CommandText = $"""
                    SELECT release_id, discogs_release_id, title, artist, metadata_release_date, metadata_country, metadata_label, metadata_status, created_at
                    FROM AlbumTargets
                    WHERE release_id IN ({string.Join(", ", parameters)})
                    """;
                for (var index = 0; index < batch.Length; index++)
                {
                    cmd.Parameters.AddWithValue(parameters[index], batch[index]);
                }

                await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
                while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
                {
                    targets.Add(ReadAlbumTargetEntry(reader));
                }
            }

            return targets;
        }

        /// <inheritdoc/>
        public async Task<IEnumerable<HashDbEntry>> LookupHashesByRecordingIdAsync(string recordingId, CancellationToken cancellationToken = default)
        {
            var matches = new List<HashDbEntry>();
            recordingId = recordingId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(recordingId))
            {
                return matches;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT *
                FROM HashDb
                WHERE musicbrainz_id = @mbid
                ORDER BY last_updated_at DESC";
            cmd.Parameters.AddWithValue("@mbid", recordingId);

            await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                matches.Add(ReadHashEntry(reader));
            }

            return matches;
        }

        /// <inheritdoc/>
        public async Task<IEnumerable<HashDbEntry>> LookupHashesByRecordingIdsAsync(
            IEnumerable<string> recordingIds,
            CancellationToken cancellationToken = default)
        {
            var normalized = recordingIds
                .Where(recordingId => !string.IsNullOrWhiteSpace(recordingId))
                .Select(recordingId => recordingId.Trim())
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            var matches = new List<HashDbEntry>();
            if (normalized.Length == 0)
            {
                return matches;
            }

            using var conn = GetConnection();
            foreach (var batch in normalized.Chunk(500))
            {
                using var cmd = conn.CreateCommand();
                var parameters = batch.Select((_, index) => $"@recording{index}").ToArray();
                cmd.CommandText = $"""
                    SELECT *
                    FROM HashDb
                    WHERE musicbrainz_id IN ({string.Join(", ", parameters)})
                    """;

                for (var index = 0; index < batch.Length; index++)
                {
                    cmd.Parameters.AddWithValue(parameters[index], batch[index]);
                }

                await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
                while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
                {
                    matches.Add(ReadHashEntry(reader));
                }
            }

            return matches;
        }

        /// <inheritdoc/>
        public async Task<HashSet<string>> GetRecordingIdsWithHashesAsync(
            IEnumerable<string> recordingIds,
            CancellationToken cancellationToken = default)
        {
            var normalized = recordingIds
                .Where(recordingId => !string.IsNullOrWhiteSpace(recordingId))
                .Select(recordingId => recordingId.Trim())
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToArray();
            var matches = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            if (normalized.Length == 0)
            {
                return matches;
            }

            using var conn = GetConnection();
            foreach (var batch in normalized.Chunk(500))
            {
                using var cmd = conn.CreateCommand();
                var parameters = batch.Select((_, index) => $"@recording{index}").ToArray();
                cmd.CommandText = $"""
                    SELECT TRIM(musicbrainz_id)
                    FROM HashDb
                    WHERE musicbrainz_id IS NOT NULL
                      AND TRIM(musicbrainz_id) <> ''
                      AND TRIM(musicbrainz_id) COLLATE NOCASE IN ({string.Join(", ", parameters)})
                    """;

                for (var index = 0; index < batch.Length; index++)
                {
                    cmd.Parameters.AddWithValue(parameters[index], batch[index]);
                }

                await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
                while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
                {
                    matches.Add(reader.GetString(0));
                }
            }

            return matches;
        }

        private static AlbumTargetEntry ReadAlbumTargetEntry(SqliteDataReader reader)
        {
            return new AlbumTargetEntry
            {
                ReleaseId = reader.GetString(0).Trim(),
                DiscogsReleaseId = reader.IsDBNull(1) ? string.Empty : reader.GetString(1).Trim(),
                Title = reader.GetString(2).Trim(),
                Artist = reader.GetString(3).Trim(),
                ReleaseDate = reader.IsDBNull(4) ? string.Empty : reader.GetString(4).Trim(),
                Country = reader.IsDBNull(5) ? string.Empty : reader.GetString(5).Trim(),
                Label = reader.IsDBNull(6) ? string.Empty : reader.GetString(6).Trim(),
                Status = reader.IsDBNull(7) ? string.Empty : reader.GetString(7).Trim(),
                CreatedAt = reader.GetInt64(8),
            };
        }

        private static AlbumTargetTrackEntry ReadAlbumTargetTrackEntry(SqliteDataReader reader)
        {
            return new AlbumTargetTrackEntry
            {
                ReleaseId = reader.GetString(0).Trim(),
                Position = reader.GetInt32(1),
                RecordingId = reader.IsDBNull(2) ? string.Empty : reader.GetString(2).Trim(),
                Title = reader.GetString(3).Trim(),
                Artist = reader.GetString(4).Trim(),
                DurationMs = reader.IsDBNull(5) ? null : reader.GetInt32(5),
                Isrc = reader.IsDBNull(6) ? string.Empty : reader.GetString(6).Trim(),
            };
        }

        private async Task UpsertAlbumTargetInternalAsync(SqliteConnection conn, AlbumTarget target, CancellationToken cancellationToken)
        {
            var normalizedMetadata = target.Metadata with
            {
                Country = string.IsNullOrWhiteSpace(target.Metadata.Country) ? null : target.Metadata.Country.Trim(),
                Label = string.IsNullOrWhiteSpace(target.Metadata.Label) ? null : target.Metadata.Label.Trim(),
                Status = string.IsNullOrWhiteSpace(target.Metadata.Status) ? null : target.Metadata.Status.Trim(),
            };

            var normalizedTarget = target with
            {
                MusicBrainzReleaseId = target.MusicBrainzReleaseId?.Trim() ?? string.Empty,
                DiscogsReleaseId = string.IsNullOrWhiteSpace(target.DiscogsReleaseId) ? null : target.DiscogsReleaseId.Trim(),
                Title = target.Title?.Trim() ?? string.Empty,
                Artist = target.Artist?.Trim() ?? string.Empty,
                Metadata = normalizedMetadata,
            };

            using var albumCmd = conn.CreateCommand();
            albumCmd.CommandText = @"
                INSERT INTO AlbumTargets (
                    release_id,
                    discogs_release_id,
                    title,
                    artist,
                    metadata_release_date,
                    metadata_country,
                    metadata_label,
                    metadata_status
                )
                VALUES (
                    @release_id,
                    @discogs_release_id,
                    @title,
                    @artist,
                    @metadata_release_date,
                    @metadata_country,
                    @metadata_label,
                    @metadata_status
                )
                ON CONFLICT(release_id) DO UPDATE SET
                    discogs_release_id = excluded.discogs_release_id,
                    title = excluded.title,
                    artist = excluded.artist,
                    metadata_release_date = excluded.metadata_release_date,
                    metadata_country = excluded.metadata_country,
                    metadata_label = excluded.metadata_label,
                    metadata_status = excluded.metadata_status;
            ";
            albumCmd.Parameters.AddWithValue("@release_id", normalizedTarget.MusicBrainzReleaseId);
            albumCmd.Parameters.AddWithValue("@discogs_release_id", (object?)normalizedTarget.DiscogsReleaseId ?? DBNull.Value);
            albumCmd.Parameters.AddWithValue("@title", normalizedTarget.Title);
            albumCmd.Parameters.AddWithValue("@artist", normalizedTarget.Artist);
            albumCmd.Parameters.AddWithValue("@metadata_release_date", (object?)FormatReleaseDate(normalizedTarget.Metadata.ReleaseDate) ?? DBNull.Value);
            albumCmd.Parameters.AddWithValue("@metadata_country", (object?)normalizedTarget.Metadata.Country ?? DBNull.Value);
            albumCmd.Parameters.AddWithValue("@metadata_label", (object?)normalizedTarget.Metadata.Label ?? DBNull.Value);
            albumCmd.Parameters.AddWithValue("@metadata_status", (object?)normalizedTarget.Metadata.Status ?? DBNull.Value);
            await albumCmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);

            await DeleteAlbumTracksAsync(conn, normalizedTarget.MusicBrainzReleaseId, cancellationToken).ConfigureAwait(false);

            var tracks = normalizedTarget.Tracks ?? Array.Empty<TrackTarget>();
            var normalizedTracks = new List<(TrackTarget Track, int Position)>(tracks.Count);
            for (var i = 0; i < tracks.Count; i++)
            {
                var sourceTrack = tracks[i];
                var normalizedRecordingId = string.IsNullOrWhiteSpace(sourceTrack.MusicBrainzRecordingId) ? string.Empty : sourceTrack.MusicBrainzRecordingId.Trim();
                var normalizedIsrc = string.IsNullOrWhiteSpace(sourceTrack.Isrc) ? null : sourceTrack.Isrc?.Trim();

                var track = sourceTrack with
                {
                    MusicBrainzRecordingId = normalizedRecordingId,
                    Title = sourceTrack.Title?.Trim() ?? string.Empty,
                    Artist = sourceTrack.Artist?.Trim() ?? string.Empty,
                    Isrc = normalizedIsrc,
                };

                normalizedTracks.Add((track, track.Position == 0 ? i + 1 : track.Position));
            }

            foreach (var batch in normalizedTracks.Chunk(AlbumTrackUpsertBatchSize))
            {
                using var trackCmd = conn.CreateCommand();
                var values = batch.Select((_, index) =>
                    $"(@release_id, @track_position{index}, @recording_id{index}, @title{index}, @artist{index}, @duration_ms{index}, @isrc{index})");
                trackCmd.CommandText = $"""
                    INSERT INTO AlbumTargetTracks (
                        release_id,
                        track_position,
                        recording_id,
                        title,
                        artist,
                        duration_ms,
                        isrc
                    )
                    VALUES {string.Join(", ", values)}
                    ON CONFLICT(release_id, track_position) DO UPDATE SET
                        recording_id = excluded.recording_id,
                        title = excluded.title,
                        artist = excluded.artist,
                        duration_ms = excluded.duration_ms,
                        isrc = excluded.isrc
                    """;
                trackCmd.Parameters.AddWithValue("@release_id", normalizedTarget.MusicBrainzReleaseId);
                for (var index = 0; index < batch.Length; index++)
                {
                    var item = batch[index];
                    trackCmd.Parameters.AddWithValue($"@track_position{index}", item.Position);
                    trackCmd.Parameters.AddWithValue($"@recording_id{index}", string.IsNullOrWhiteSpace(item.Track.MusicBrainzRecordingId) ? DBNull.Value : item.Track.MusicBrainzRecordingId);
                    trackCmd.Parameters.AddWithValue($"@title{index}", item.Track.Title);
                    trackCmd.Parameters.AddWithValue($"@artist{index}", item.Track.Artist);
                    trackCmd.Parameters.AddWithValue($"@duration_ms{index}", (object?)DurationToMilliseconds(item.Track.Duration) ?? DBNull.Value);
                    trackCmd.Parameters.AddWithValue($"@isrc{index}", (object?)item.Track.Isrc ?? DBNull.Value);
                }

                await trackCmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
            }
        }

        private static Task DeleteAlbumTracksAsync(SqliteConnection conn, string releaseId, CancellationToken cancellationToken)
        {
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "DELETE FROM AlbumTargetTracks WHERE release_id = @release_id";
            cmd.Parameters.AddWithValue("@release_id", releaseId);
            return cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        private static string? FormatReleaseDate(DateOnly? releaseDate)
        {
            return releaseDate?.ToString("yyyy-MM-dd");
        }

        private static int? DurationToMilliseconds(TimeSpan duration)
        {
            if (duration == TimeSpan.Zero)
            {
                return null;
            }

            var ms = (int)Math.Min(int.MaxValue, Math.Max(0, (int)Math.Round(duration.TotalMilliseconds)));
            return ms == 0 ? (int?)null : ms;
        }

        // ========== Peer Management ==========

        /// <inheritdoc/>
        public async Task<Peer> GetOrCreatePeerAsync(string username, CancellationToken cancellationToken = default)
        {
            username = username?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(username))
            {
                throw new ArgumentException("Peer ID is required", nameof(username));
            }

            using var conn = GetConnection();
            var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();

            // Try to get existing
            using (var cmd = conn.CreateCommand())
            {
                cmd.CommandText = "SELECT * FROM Peers WHERE peer_id = @peer_id";
                cmd.Parameters.AddWithValue("@peer_id", username);

                using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
                if (await reader.ReadAsync(cancellationToken))
                {
                    return ReadPeer(reader);
                }
            }

            // Create new. Peer discovery can report the same username from
            // multiple event paths concurrently, so this must tolerate another
            // connection inserting the row after the read above.
            using (var cmd = conn.CreateCommand())
            {
                cmd.CommandText = @"INSERT OR IGNORE INTO Peers (peer_id, last_seen) VALUES (@peer_id, @last_seen)";
                cmd.Parameters.AddWithValue("@peer_id", username);
                cmd.Parameters.AddWithValue("@last_seen", now);
                await cmd.ExecuteNonQueryAsync(cancellationToken);
            }

            using (var cmd = conn.CreateCommand())
            {
                cmd.CommandText = "SELECT * FROM Peers WHERE peer_id = @peer_id";
                cmd.Parameters.AddWithValue("@peer_id", username);

                using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
                if (await reader.ReadAsync(cancellationToken))
                {
                    return ReadPeer(reader);
                }
            }

            throw new InvalidOperationException($"Failed to create or load peer '{username}'.");
        }

        /// <inheritdoc/>
        public async Task UpdatePeerCapabilitiesAsync(string username, PeerCapabilityFlags caps, string? clientVersion = null, CancellationToken cancellationToken = default)
        {
            username = username?.Trim() ?? string.Empty;
            clientVersion = clientVersion?.Trim();
            if (string.IsNullOrWhiteSpace(username))
            {
                return;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                INSERT INTO Peers (peer_id, caps, client_version, last_cap_check, last_seen)
                VALUES (@peer_id, @caps, @version, @now, @now)
                ON CONFLICT(peer_id) DO UPDATE SET
                    caps = excluded.caps,
                    client_version = COALESCE(excluded.client_version, Peers.client_version),
                    last_cap_check = excluded.last_cap_check,
                    last_seen = excluded.last_seen";
            cmd.Parameters.AddWithValue("@peer_id", username);
            cmd.Parameters.AddWithValue("@caps", (int)caps);
            cmd.Parameters.AddWithValue("@version", clientVersion ?? (object)DBNull.Value);
            cmd.Parameters.AddWithValue("@now", DateTimeOffset.UtcNow.ToUnixTimeSeconds());
            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        /// <inheritdoc/>
        public async Task<IEnumerable<Peer>> GetSlskdnPeersAsync(CancellationToken cancellationToken = default)
        {
            var peers = new List<Peer>();
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT * FROM Peers WHERE caps > 0 ORDER BY last_seen DESC";

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                peers.Add(ReadPeer(reader));
            }

            return peers;
        }

        /// <inheritdoc/>
        public async Task TouchPeerAsync(string username, CancellationToken cancellationToken = default)
        {
            username = username?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(username))
            {
                throw new ArgumentException("Peer ID is required", nameof(username));
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                INSERT INTO Peers (peer_id, last_seen)
                VALUES (@peer_id, @now)
                ON CONFLICT(peer_id) DO UPDATE SET last_seen = excluded.last_seen";
            cmd.Parameters.AddWithValue("@peer_id", username);
            cmd.Parameters.AddWithValue("@now", DateTimeOffset.UtcNow.ToUnixTimeSeconds());
            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        // ========== FLAC Inventory ==========

        /// <inheritdoc/>
        public async Task UpsertFlacEntryAsync(FlacInventoryEntry entry, CancellationToken cancellationToken = default)
        {
            NormalizeFlacEntry(entry);

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                INSERT INTO FlacInventory (file_id, peer_id, path, size, discovered_at, hash_status, hash_value, hash_source, flac_audio_md5, sample_rate, channels, bit_depth, duration_samples)
                VALUES (@file_id, @peer_id, @path, @size, @discovered_at, @hash_status, @hash_value, @hash_source, @flac_audio_md5, @sample_rate, @channels, @bit_depth, @duration_samples)
                ON CONFLICT(file_id) DO UPDATE SET
                    hash_status = COALESCE(@hash_status, hash_status),
                    hash_value = COALESCE(@hash_value, hash_value),
                    hash_source = COALESCE(@hash_source, hash_source),
                    flac_audio_md5 = COALESCE(@flac_audio_md5, flac_audio_md5),
                    sample_rate = COALESCE(@sample_rate, sample_rate),
                    channels = COALESCE(@channels, channels),
                    bit_depth = COALESCE(@bit_depth, bit_depth),
                    duration_samples = COALESCE(@duration_samples, duration_samples)";

            cmd.Parameters.AddWithValue("@file_id", entry.FileId);
            cmd.Parameters.AddWithValue("@peer_id", entry.PeerId);
            cmd.Parameters.AddWithValue("@path", entry.Path);
            cmd.Parameters.AddWithValue("@size", entry.Size);
            cmd.Parameters.AddWithValue("@discovered_at", entry.DiscoveredAt);
            cmd.Parameters.AddWithValue("@hash_status", entry.HashStatusStr ?? "none");
            cmd.Parameters.AddWithValue("@hash_value", entry.HashValue ?? (object)DBNull.Value);
            cmd.Parameters.AddWithValue("@hash_source", entry.HashSourceStr ?? (object)DBNull.Value);
            cmd.Parameters.AddWithValue("@flac_audio_md5", entry.FlacAudioMd5 ?? (object)DBNull.Value);
            cmd.Parameters.AddWithValue("@sample_rate", entry.SampleRate ?? (object)DBNull.Value);
            cmd.Parameters.AddWithValue("@channels", entry.Channels ?? (object)DBNull.Value);
            cmd.Parameters.AddWithValue("@bit_depth", entry.BitDepth ?? (object)DBNull.Value);
            cmd.Parameters.AddWithValue("@duration_samples", entry.DurationSamples ?? (object)DBNull.Value);

            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        internal static async Task<(int AffectedRows, int CommandCount)> UpsertFlacEntriesInBatchesAsync(
            SqliteConnection connection,
            SqliteTransaction transaction,
            IEnumerable<FlacInventoryEntry> entries,
            CancellationToken cancellationToken)
        {
            var batch = new List<FlacInventoryEntry>(FlacInventoryUpsertBatchSize);
            var affectedRows = 0;
            var commandCount = 0;

            foreach (var entry in entries)
            {
                NormalizeFlacEntry(entry);
                batch.Add(entry);
                if (batch.Count < FlacInventoryUpsertBatchSize)
                {
                    continue;
                }

                affectedRows += await ExecuteFlacInventoryUpsertBatchAsync(
                    connection,
                    transaction,
                    batch,
                    cancellationToken).ConfigureAwait(false);
                commandCount++;
                batch.Clear();
            }

            if (batch.Count > 0)
            {
                affectedRows += await ExecuteFlacInventoryUpsertBatchAsync(
                    connection,
                    transaction,
                    batch,
                    cancellationToken).ConfigureAwait(false);
                commandCount++;
            }

            return (affectedRows, commandCount);
        }

        internal static async Task<int> UpsertPeersInBatchesAsync(
            SqliteConnection connection,
            SqliteTransaction transaction,
            IEnumerable<string> peerIds,
            CancellationToken cancellationToken)
        {
            var normalized = peerIds
                .Where(peerId => !string.IsNullOrWhiteSpace(peerId))
                .Select(peerId => peerId.Trim())
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            var commandCount = 0;
            var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();

            foreach (var batch in normalized.Chunk(PeerUpsertBatchSize))
            {
                using var cmd = connection.CreateCommand();
                cmd.Transaction = transaction;
                var values = batch.Select((_, index) => $"(@peer_id{index}, @last_seen)");
                cmd.CommandText = $"""
                    INSERT OR IGNORE INTO Peers (peer_id, last_seen)
                    VALUES {string.Join(", ", values)}
                    """;
                cmd.Parameters.AddWithValue("@last_seen", now);
                for (var index = 0; index < batch.Length; index++)
                {
                    cmd.Parameters.AddWithValue($"@peer_id{index}", batch[index]);
                }

                await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
                commandCount++;
            }

            return commandCount;
        }

        private static async Task<int> ExecuteFlacInventoryUpsertBatchAsync(
            SqliteConnection connection,
            SqliteTransaction transaction,
            IReadOnlyList<FlacInventoryEntry> batch,
            CancellationToken cancellationToken)
        {
            using var cmd = connection.CreateCommand();
            cmd.Transaction = transaction;
            var values = batch.Select((_, index) =>
                $"(@file_id{index}, @peer_id{index}, @path{index}, @size{index}, @discovered_at{index}, @hash_status{index}, @hash_value{index}, @hash_source{index}, @flac_audio_md5{index}, @sample_rate{index}, @channels{index}, @bit_depth{index}, @duration_samples{index})");
            cmd.CommandText = $"""
                INSERT INTO FlacInventory
                    (file_id, peer_id, path, size, discovered_at, hash_status, hash_value, hash_source, flac_audio_md5, sample_rate, channels, bit_depth, duration_samples)
                VALUES {string.Join(", ", values)}
                ON CONFLICT(file_id) DO UPDATE SET
                    hash_status = COALESCE(excluded.hash_status, hash_status),
                    hash_value = COALESCE(excluded.hash_value, hash_value),
                    hash_source = COALESCE(excluded.hash_source, hash_source),
                    flac_audio_md5 = COALESCE(excluded.flac_audio_md5, flac_audio_md5),
                    sample_rate = COALESCE(excluded.sample_rate, sample_rate),
                    channels = COALESCE(excluded.channels, channels),
                    bit_depth = COALESCE(excluded.bit_depth, bit_depth),
                    duration_samples = COALESCE(excluded.duration_samples, duration_samples)
                """;

            for (var index = 0; index < batch.Count; index++)
            {
                var entry = batch[index];
                cmd.Parameters.AddWithValue($"@file_id{index}", entry.FileId);
                cmd.Parameters.AddWithValue($"@peer_id{index}", entry.PeerId);
                cmd.Parameters.AddWithValue($"@path{index}", entry.Path);
                cmd.Parameters.AddWithValue($"@size{index}", entry.Size);
                cmd.Parameters.AddWithValue($"@discovered_at{index}", entry.DiscoveredAt);
                cmd.Parameters.AddWithValue($"@hash_status{index}", entry.HashStatusStr ?? "none");
                cmd.Parameters.AddWithValue($"@hash_value{index}", entry.HashValue ?? (object)DBNull.Value);
                cmd.Parameters.AddWithValue($"@hash_source{index}", entry.HashSourceStr ?? (object)DBNull.Value);
                cmd.Parameters.AddWithValue($"@flac_audio_md5{index}", entry.FlacAudioMd5 ?? (object)DBNull.Value);
                cmd.Parameters.AddWithValue($"@sample_rate{index}", entry.SampleRate ?? (object)DBNull.Value);
                cmd.Parameters.AddWithValue($"@channels{index}", entry.Channels ?? (object)DBNull.Value);
                cmd.Parameters.AddWithValue($"@bit_depth{index}", entry.BitDepth ?? (object)DBNull.Value);
                cmd.Parameters.AddWithValue($"@duration_samples{index}", entry.DurationSamples ?? (object)DBNull.Value);
            }

            return await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
        }

        private static void NormalizeFlacEntry(FlacInventoryEntry entry)
        {
            entry.PeerId = entry.PeerId?.Trim() ?? string.Empty;
            entry.Path = entry.Path?.Trim() ?? string.Empty;
            if (string.IsNullOrEmpty(entry.FileId))
            {
                entry.FileId = FlacInventoryEntry.GenerateFileId(entry.PeerId, entry.Path, entry.Size);
            }

            if (entry.DiscoveredAt == 0)
            {
                entry.DiscoveredAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            }
        }

        /// <inheritdoc/>
        public async Task<FlacInventoryEntry?> GetFlacEntryAsync(string fileId, CancellationToken cancellationToken = default)
        {
            fileId = fileId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(fileId))
            {
                return null;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT * FROM FlacInventory WHERE file_id = @file_id";
            cmd.Parameters.AddWithValue("@file_id", fileId);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            if (await reader.ReadAsync(cancellationToken))
            {
                return ReadFlacEntry(reader);
            }

            return null;
        }

        /// <inheritdoc/>
        public async Task<IEnumerable<FlacInventoryEntry>> GetFlacEntriesBySizeAsync(long size, int limit = 100, CancellationToken cancellationToken = default)
        {
            var entries = new List<FlacInventoryEntry>();
            if (size <= 0 || limit <= 0)
            {
                return entries;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT * FROM FlacInventory WHERE size = @size ORDER BY discovered_at DESC LIMIT @limit";
            cmd.Parameters.AddWithValue("@size", size);
            cmd.Parameters.AddWithValue("@limit", limit);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                entries.Add(ReadFlacEntry(reader));
            }

            return entries;
        }

        /// <inheritdoc/>
        public async Task<IEnumerable<FlacInventoryEntry>> GetUnhashedFlacFilesAsync(int limit = 50, CancellationToken cancellationToken = default)
        {
            var entries = new List<FlacInventoryEntry>();
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT * FROM FlacInventory 
                WHERE hash_status = 'none' OR hash_status = 'pending'
                ORDER BY discovered_at DESC 
                LIMIT @limit";
            cmd.Parameters.AddWithValue("@limit", limit);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                entries.Add(ReadFlacEntry(reader));
            }

            return entries;
        }

        /// <inheritdoc/>
        public async Task UpdateFlacHashAsync(string fileId, string hashValue, HashSource source, CancellationToken cancellationToken = default)
        {
            fileId = fileId?.Trim() ?? string.Empty;
            hashValue = hashValue?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(fileId) || string.IsNullOrWhiteSpace(hashValue))
            {
                return;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                UPDATE FlacInventory 
                SET hash_status = 'known', hash_value = @hash_value, hash_source = @hash_source
                WHERE file_id = @file_id";
            cmd.Parameters.AddWithValue("@file_id", fileId);
            cmd.Parameters.AddWithValue("@hash_value", hashValue);
            cmd.Parameters.AddWithValue("@hash_source", source.ToString().ToLowerInvariant());
            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        /// <inheritdoc/>
        public async Task MarkFlacHashFailedAsync(string fileId, CancellationToken cancellationToken = default)
        {
            fileId = fileId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(fileId))
            {
                return;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "UPDATE FlacInventory SET hash_status = 'failed' WHERE file_id = @file_id";
            cmd.Parameters.AddWithValue("@file_id", fileId);
            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        // ========== Hash Database ==========

        /// <inheritdoc/>
        public async Task<HashDbEntry?> LookupHashAsync(string flacKey, CancellationToken cancellationToken = default)
        {
            flacKey = flacKey?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(flacKey))
            {
                return null;
            }

            using var activity = HashDbActivitySource.Source.StartActivity("hashdb.lookup");
            activity?.SetTag("hashdb.lookup.key", flacKey);

            // Check cache first
            if (hashCache != null && hashCache.TryGetValue($"hashdb:lookup:{flacKey}", out var cachedObj) && cachedObj is HashDbEntry cached)
            {
                activity?.SetTag("hashdb.lookup.cache_hit", true);
                log.Debug("[HashDb] Cache hit for flac_key: {Key}", LoggingSanitizer.SanitizeHash(flacKey));
                return cached;
            }

            activity?.SetTag("hashdb.lookup.cache_hit", false);

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT *
                FROM HashDb
                WHERE flac_key = @lookup_key OR variant_id = @lookup_key
                ORDER BY CASE WHEN flac_key = @lookup_key THEN 0 ELSE 1 END, last_updated_at DESC";
            cmd.Parameters.AddWithValue("@lookup_key", flacKey);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            if (await reader.ReadAsync(cancellationToken))
            {
                var entry = ReadHashEntry(reader);

                // Cache the result (5 minute TTL)
                if (hashCache != null)
                {
                    hashCache.Set($"hashdb:lookup:{flacKey}", entry, new MemoryCacheEntryOptions
                    {
                        AbsoluteExpirationRelativeToNow = TimeSpan.FromMinutes(5)
                    });
                    if (!string.IsNullOrWhiteSpace(entry.VariantId) &&
                        !string.Equals(entry.VariantId, flacKey, StringComparison.Ordinal))
                    {
                        hashCache.Set($"hashdb:lookup:{entry.VariantId}", entry, new MemoryCacheEntryOptions
                        {
                            AbsoluteExpirationRelativeToNow = TimeSpan.FromMinutes(5)
                        });
                    }

                    log.Debug("[HashDb] Cached lookup result for flac_key: {Key}", LoggingSanitizer.SanitizeHash(flacKey));
                }

                activity?.SetTag("hashdb.lookup.found", true);
                return entry;
            }

            activity?.SetTag("hashdb.lookup.found", false);
            return null;
        }

        /// <inheritdoc/>
        public async Task<List<HashDbEntry>> LookupHashesByFlacKeysAsync(
            IEnumerable<string> flacKeys,
            CancellationToken cancellationToken = default)
        {
            var normalized = flacKeys
                .Where(flacKey => !string.IsNullOrWhiteSpace(flacKey))
                .Select(flacKey => flacKey.Trim())
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            var entries = new List<HashDbEntry>();
            if (normalized.Length == 0)
            {
                return entries;
            }

            var missing = new List<string>(normalized.Length);
            foreach (var flacKey in normalized)
            {
                if (hashCache != null &&
                    hashCache.TryGetValue($"hashdb:lookup:{flacKey}", out var cachedObj) &&
                    cachedObj is HashDbEntry cached &&
                    string.Equals(cached.FlacKey, flacKey, StringComparison.Ordinal))
                {
                    entries.Add(cached);
                }
                else
                {
                    missing.Add(flacKey);
                }
            }

            if (missing.Count == 0)
            {
                return entries;
            }

            using var connection = GetConnection();
            foreach (var batch in missing.Chunk(HashLookupBatchSize))
            {
                using var command = connection.CreateCommand();
                var parameters = batch.Select((_, index) => $"@flac_key{index}").ToArray();
                command.CommandText = $"""
                    SELECT *
                    FROM HashDb
                    WHERE flac_key IN ({string.Join(", ", parameters)})
                    """;
                for (var index = 0; index < batch.Length; index++)
                {
                    command.Parameters.AddWithValue(parameters[index], batch[index]);
                }

                using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
                while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
                {
                    var entry = ReadHashEntry(reader);
                    entries.Add(entry);
                    hashCache?.Set($"hashdb:lookup:{entry.FlacKey}", entry, new MemoryCacheEntryOptions
                    {
                        AbsoluteExpirationRelativeToNow = TimeSpan.FromMinutes(5),
                    });
                }
            }

            return entries;
        }

        /// <inheritdoc/>
        public async Task<AudioVariant?> GetAudioVariantByFlacKeyAsync(string flacKey, CancellationToken cancellationToken = default)
        {
            var entry = await LookupHashAsync(flacKey, cancellationToken).ConfigureAwait(false);
            return entry is null ? null : MapEntryToVariant(entry);
        }

        /// <inheritdoc/>
        public async Task<IEnumerable<HashDbEntry>> LookupHashesBySizeAsync(long size, CancellationToken cancellationToken = default)
        {
            var entries = new List<HashDbEntry>();
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT * FROM HashDb WHERE size = @size ORDER BY use_count DESC";
            cmd.Parameters.AddWithValue("@size", size);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                entries.Add(ReadHashEntry(reader));
            }

            return entries;
        }

        /// <inheritdoc/>
        public async Task<IEnumerable<HashDbEntry>> LookupHashesByAudioFingerprintAsync(string fingerprint, CancellationToken cancellationToken = default)
        {
            var entries = new List<HashDbEntry>();
            if (string.IsNullOrWhiteSpace(fingerprint))
            {
                return entries;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT *
                FROM HashDb
                WHERE audio_fingerprint = @fingerprint
                ORDER BY quality_score DESC, last_updated_at DESC";
            cmd.Parameters.AddWithValue("@fingerprint", fingerprint);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                entries.Add(ReadHashEntry(reader));
            }

            return entries;
        }

        /// <inheritdoc/>
        public async Task StoreHashAsync(HashDbEntry entry, CancellationToken cancellationToken = default)
        {
            // Invalidate cache when storing
            if (hashCache != null && !string.IsNullOrEmpty(entry.FlacKey))
            {
                hashCache.Remove($"hashdb:lookup:{entry.FlacKey}");
            }

            var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            var newSeqId = Interlocked.Increment(ref currentSeqId);

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                INSERT INTO HashDb (flac_key, byte_hash, size, meta_flags, first_seen_at, last_updated_at, seq_id, use_count)
                VALUES (@flac_key, @byte_hash, @size, @meta_flags, @now, @now, @seq_id, 1)
                ON CONFLICT(flac_key) DO UPDATE SET
                    byte_hash = @byte_hash,
                    last_updated_at = @now,
                    seq_id = @seq_id,
                    use_count = use_count + 1";

            cmd.Parameters.AddWithValue("@flac_key", entry.FlacKey);
            cmd.Parameters.AddWithValue("@byte_hash", entry.ByteHash);
            cmd.Parameters.AddWithValue("@size", entry.Size);
            cmd.Parameters.AddWithValue("@meta_flags", entry.MetaFlags ?? (object)DBNull.Value);
            cmd.Parameters.AddWithValue("@now", now);
            cmd.Parameters.AddWithValue("@seq_id", newSeqId);

            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        /// <inheritdoc/>
        public async Task StoreHashFromVerificationAsync(string filename, long size, string byteHash, int? sampleRate = null, int? channels = null, int? bitDepth = null, CancellationToken cancellationToken = default)
        {
            var flacKey = HashDbEntry.GenerateFlacKey(filename, size);
            int? metaFlags = null;

            if (sampleRate.HasValue && channels.HasValue && bitDepth.HasValue)
            {
                metaFlags = HashDbEntry.PackMetaFlags(sampleRate.Value, channels.Value, bitDepth.Value);
            }

            await StoreHashAsync(new HashDbEntry
            {
                FlacKey = flacKey,
                ByteHash = byteHash,
                Size = size,
                MetaFlags = metaFlags,
            }, cancellationToken);

            log.Debug("[HashDb] Stored hash {Key} -> {Hash} for {File} ({Size} bytes)",
                LoggingSanitizer.SanitizeHash(flacKey), LoggingSanitizer.SanitizeHash(byteHash),
                LoggingSanitizer.SanitizeFilePath(filename), size);
        }

        /// <inheritdoc/>
        public async Task UpdateHashRecordingIdAsync(string flacKey, string musicBrainzId, CancellationToken cancellationToken = default)
        {
            flacKey = flacKey?.Trim() ?? string.Empty;
            musicBrainzId = musicBrainzId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(flacKey) || string.IsNullOrWhiteSpace(musicBrainzId))
            {
                return;
            }

            // Invalidate cache when updating
            if (hashCache != null)
            {
                hashCache.Remove($"hashdb:lookup:{flacKey}");
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                UPDATE HashDb
                SET musicbrainz_id = @mbid, last_updated_at = @now
                WHERE flac_key = @flac_key";
            cmd.Parameters.AddWithValue("@mbid", musicBrainzId);
            cmd.Parameters.AddWithValue("@now", DateTimeOffset.UtcNow.ToUnixTimeSeconds());
            cmd.Parameters.AddWithValue("@flac_key", flacKey);
            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        // ========== Library Health ==========

        /// <inheritdoc/>
        public async Task UpsertLibraryHealthScanAsync(LibraryHealth.LibraryHealthScan scan, CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                INSERT INTO LibraryHealthScans (
                    scan_id,
                    library_path,
                    started_at,
                    completed_at,
                    status,
                    files_scanned,
                    issues_detected,
                    error_message)
                VALUES (
                    @scan_id,
                    @library_path,
                    @started_at,
                    @completed_at,
                    @status,
                    @files_scanned,
                    @issues_detected,
                    @error_message)
                ON CONFLICT(scan_id) DO UPDATE SET
                    completed_at = excluded.completed_at,
                    status = excluded.status,
                    files_scanned = excluded.files_scanned,
                    issues_detected = excluded.issues_detected,
                    error_message = excluded.error_message";

            cmd.Parameters.AddWithValue("@scan_id", scan.ScanId);
            cmd.Parameters.AddWithValue("@library_path", scan.LibraryPath);
            cmd.Parameters.AddWithValue("@started_at", scan.StartedAt.ToUnixTimeSeconds());
            cmd.Parameters.AddWithValue("@completed_at", scan.CompletedAt?.ToUnixTimeSeconds() ?? (object)DBNull.Value);
            cmd.Parameters.AddWithValue("@status", scan.Status.ToString().ToLowerInvariant());
            cmd.Parameters.AddWithValue("@files_scanned", scan.FilesScanned);
            cmd.Parameters.AddWithValue("@issues_detected", scan.IssuesDetected);
            cmd.Parameters.AddWithValue("@error_message", (object?)scan.ErrorMessage ?? DBNull.Value);

            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        /// <inheritdoc/>
        public async Task<LibraryHealth.LibraryHealthScan?> GetLibraryHealthScanAsync(string scanId, CancellationToken cancellationToken = default)
        {
            scanId = scanId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(scanId))
            {
                return null;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT * FROM LibraryHealthScans WHERE scan_id = @id";
            cmd.Parameters.AddWithValue("@id", scanId);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            if (await reader.ReadAsync(cancellationToken))
            {
                return ReadScan(reader);
            }

            return null;
        }

        /// <inheritdoc/>
        public async Task<List<LibraryHealth.LibraryIssue>> GetLibraryIssuesAsync(LibraryHealth.LibraryHealthIssueFilter filter, CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            return await ReadLibraryIssuesAsync(conn, filter, transaction: null, cancellationToken).ConfigureAwait(false);
        }

        /// <inheritdoc/>
        public async Task<List<LibraryHealth.LibraryIssue>> GetLibraryIssuesByIdsAsync(
            IEnumerable<string> issueIds,
            CancellationToken cancellationToken = default)
        {
            var normalized = issueIds
                .Where(issueId => !string.IsNullOrWhiteSpace(issueId))
                .Select(issueId => issueId.Trim())
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            var issuesById = new Dictionary<string, LibraryHealth.LibraryIssue>(StringComparer.Ordinal);
            if (normalized.Length == 0)
            {
                return new List<LibraryHealth.LibraryIssue>();
            }

            using var conn = GetConnection();
            foreach (var batch in normalized.Chunk(500))
            {
                using var cmd = conn.CreateCommand();
                var parameters = batch.Select((_, index) => $"@issue{index}").ToArray();
                cmd.CommandText = $"SELECT * FROM LibraryHealthIssues WHERE issue_id IN ({string.Join(", ", parameters)})";
                for (var index = 0; index < batch.Length; index++)
                {
                    cmd.Parameters.AddWithValue(parameters[index], batch[index]);
                }

                await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
                while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
                {
                    var issue = ReadIssue(reader);
                    issuesById[issue.IssueId] = issue;
                }
            }

            return normalized
                .Where(issuesById.ContainsKey)
                .Select(issueId => issuesById[issueId])
                .ToList();
        }

        /// <inheritdoc/>
        public async Task<List<LibraryHealth.LibraryIssue>> GetLibraryIssuesByRemediationJobAsync(
            string jobId,
            LibraryHealth.LibraryIssueStatus status,
            CancellationToken cancellationToken = default)
        {
            jobId = jobId?.Trim() ?? string.Empty;
            var issues = new List<LibraryHealth.LibraryIssue>();
            if (string.IsNullOrWhiteSpace(jobId))
            {
                return issues;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText =
                """
                SELECT *
                FROM LibraryHealthIssues
                WHERE remediation_job_id IS NOT NULL
                  AND remediation_job_id <> ''
                  AND remediation_job_id = @job_id
                  AND status = @status
                ORDER BY detected_at DESC
                """;
            cmd.Parameters.AddWithValue("@job_id", jobId);
            cmd.Parameters.AddWithValue("@status", status.ToString().ToLowerInvariant());

            await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                issues.Add(ReadIssue(reader));
            }

            return issues;
        }

        /// <inheritdoc/>
        public async Task<LibraryHealth.LibraryIssuePage> GetLibraryIssuePageAsync(
            LibraryHealth.LibraryHealthIssueFilter filter,
            CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var transaction = conn.BeginTransaction();
            using var cmd = conn.CreateCommand();
            cmd.Transaction = transaction;
            cmd.CommandText = "SELECT COUNT(*) FROM LibraryHealthIssues" + BuildLibraryIssueFilterSql(cmd, filter);
            var totalCount = Convert.ToInt32(await cmd.ExecuteScalarAsync(cancellationToken).ConfigureAwait(false), CultureInfo.InvariantCulture);
            var issues = await ReadLibraryIssuesAsync(conn, filter, transaction, cancellationToken).ConfigureAwait(false);
            transaction.Commit();

            return new LibraryHealth.LibraryIssuePage
            {
                Issues = issues,
                TotalCount = totalCount,
            };
        }

        /// <inheritdoc/>
        public async Task<LibraryHealth.LibraryHealthSummary> GetLibraryHealthSummaryAsync(
            string libraryPath,
            CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            var where = string.Empty;
            if (!string.IsNullOrWhiteSpace(libraryPath))
            {
                where = " WHERE file_path LIKE @path";
                cmd.Parameters.AddWithValue("@path", $"{libraryPath}%");
            }

            cmd.CommandText = $@"
                SELECT
                    COUNT(*),
                    COALESCE(SUM(CASE WHEN status NOT IN ('resolved', 'ignored') THEN 1 ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END), 0)
                FROM LibraryHealthIssues{where}";

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            await reader.ReadAsync(cancellationToken).ConfigureAwait(false);
            return new LibraryHealth.LibraryHealthSummary
            {
                LibraryPath = libraryPath,
                TotalIssues = Convert.ToInt32(reader.GetInt64(0), CultureInfo.InvariantCulture),
                IssuesOpen = Convert.ToInt32(reader.GetInt64(1), CultureInfo.InvariantCulture),
                IssuesResolved = Convert.ToInt32(reader.GetInt64(2), CultureInfo.InvariantCulture),
            };
        }

        /// <inheritdoc/>
        public async Task<List<LibraryHealth.LibraryIssueTypeSummary>> GetLibraryIssueTypeSummariesAsync(
            string libraryPath,
            CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            var where = string.Empty;
            if (!string.IsNullOrWhiteSpace(libraryPath))
            {
                where = " WHERE file_path LIKE @path";
                cmd.Parameters.AddWithValue("@path", $"{libraryPath}%");
            }

            cmd.CommandText = $@"
                SELECT type, severity, COUNT(*)
                FROM LibraryHealthIssues{where}
                GROUP BY type, severity";

            var groups = new Dictionary<LibraryHealth.LibraryIssueType, LibraryHealth.LibraryIssueTypeSummary>();
            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                if (!Enum.TryParse<LibraryHealth.LibraryIssueType>(reader.GetString(0), ignoreCase: true, out var type) ||
                    !Enum.TryParse<LibraryHealth.LibraryIssueSeverity>(reader.GetString(1), ignoreCase: true, out var severity))
                {
                    continue;
                }

                var count = Convert.ToInt32(reader.GetInt64(2), CultureInfo.InvariantCulture);
                if (!groups.TryGetValue(type, out var group))
                {
                    group = new LibraryHealth.LibraryIssueTypeSummary { Type = type };
                    groups[type] = group;
                }

                group.Count += count;
                group.BySeverity[severity] = count;
            }

            return groups.Values
                .OrderByDescending(group => group.Count)
                .ThenBy(group => group.Type)
                .ToList();
        }

        /// <inheritdoc/>
        public async Task<List<LibraryHealth.LibraryIssueArtistSummary>> GetLibraryIssueArtistSummariesAsync(
            string libraryPath,
            int limit,
            CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            var where = "WHERE LENGTH(TRIM(artist)) > 0";
            if (!string.IsNullOrWhiteSpace(libraryPath))
            {
                where += " AND file_path LIKE @path";
                cmd.Parameters.AddWithValue("@path", $"{libraryPath}%");
            }

            cmd.Parameters.AddWithValue("@artistLimit", Math.Clamp(limit, 1, 100));
            cmd.CommandText = BuildLibraryIssueArtistSummarySql(where);
            return await ReadLibraryIssueArtistSummariesAsync(cmd, cancellationToken).ConfigureAwait(false);
        }

        /// <inheritdoc/>
        public async Task<List<LibraryHealth.LibraryIssueReleaseSummary>> GetLibraryIssueReleaseSummariesAsync(
            string libraryPath,
            int limit,
            CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            var where = "WHERE LENGTH(TRIM(album)) > 0";
            if (!string.IsNullOrWhiteSpace(libraryPath))
            {
                where += " AND file_path LIKE @path";
                cmd.Parameters.AddWithValue("@path", $"{libraryPath}%");
            }

            cmd.Parameters.AddWithValue("@releaseLimit", Math.Clamp(limit, 1, 100));
            cmd.CommandText = $@"
                WITH filtered AS MATERIALIZED (
                    SELECT
                        COALESCE(artist, '') AS artist,
                        album,
                        COALESCE(mb_release_id, '') AS release_id,
                        type
                    FROM LibraryHealthIssues
                    {where}
                ),
                type_counts AS (
                    SELECT artist, album, release_id, type, COUNT(*) AS item_count
                    FROM filtered
                    GROUP BY artist, album, release_id, type
                ),
                totals AS (
                    SELECT artist, album, release_id, SUM(item_count) AS total_count
                    FROM type_counts
                    GROUP BY artist, album, release_id
                ),
                top_releases AS (
                    SELECT artist, album, release_id, total_count
                    FROM totals
                    ORDER BY total_count DESC, artist, album, release_id
                    LIMIT @releaseLimit
                )
                SELECT counts.artist, counts.album, counts.release_id, counts.type, counts.item_count, top.total_count
                FROM type_counts AS counts
                INNER JOIN top_releases AS top
                    ON top.artist = counts.artist
                    AND top.album = counts.album
                    AND top.release_id = counts.release_id
                ORDER BY top.total_count DESC, counts.artist, counts.album, counts.release_id, counts.type";

            var groups = new Dictionary<(string Artist, string Album, string ReleaseId), LibraryHealth.LibraryIssueReleaseSummary>();
            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                if (!Enum.TryParse<LibraryHealth.LibraryIssueType>(reader.GetString(3), ignoreCase: true, out var type))
                {
                    continue;
                }

                var key = (reader.GetString(0), reader.GetString(1), reader.GetString(2));
                if (!groups.TryGetValue(key, out var group))
                {
                    group = new LibraryHealth.LibraryIssueReleaseSummary
                    {
                        Artist = key.Item1,
                        Album = key.Item2,
                        MusicBrainzReleaseId = key.Item3,
                        Count = Convert.ToInt32(reader.GetInt64(5), CultureInfo.InvariantCulture),
                    };
                    groups[key] = group;
                }

                group.ByType[type] = Convert.ToInt32(reader.GetInt64(4), CultureInfo.InvariantCulture);
            }

            return groups.Values
                .OrderByDescending(group => group.Count)
                .ThenBy(group => group.Artist, StringComparer.Ordinal)
                .ThenBy(group => group.Album, StringComparer.Ordinal)
                .ThenBy(group => group.MusicBrainzReleaseId, StringComparer.Ordinal)
                .ToList();
        }

        /// <inheritdoc/>
        public async Task<List<LibraryHealth.IssueCodecGroup>> GetLibraryIssueCodecSummariesAsync(
            string libraryPath,
            CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            var where = string.Empty;
            if (!string.IsNullOrWhiteSpace(libraryPath))
            {
                where = "WHERE file_path LIKE @path";
                cmd.Parameters.AddWithValue("@path", $"{libraryPath}%");
            }

            cmd.CommandText = $@"
                WITH normalized AS (
                    SELECT
                        UPPER(COALESCE(
                            NULLIF(CASE WHEN json_valid(metadata) THEN CAST(json_extract(metadata, '$.codec') AS TEXT) END, ''),
                            'UNKNOWN')) AS codec,
                        CASE
                            WHEN type = 'SuspectedTranscode' THEN 1
                            WHEN json_valid(metadata) AND json_extract(metadata, '$.transcode_suspect') = 1 THEN 1
                            ELSE 0
                        END AS transcode_suspect
                    FROM LibraryHealthIssues
                    {where}
                )
                SELECT codec, COUNT(*), SUM(transcode_suspect)
                FROM normalized
                GROUP BY codec
                ORDER BY COUNT(*) DESC, codec";

            var groups = new List<LibraryHealth.IssueCodecGroup>();
            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                groups.Add(new LibraryHealth.IssueCodecGroup
                {
                    Codec = reader.GetString(0),
                    Count = Convert.ToInt32(reader.GetInt64(1), CultureInfo.InvariantCulture),
                    TranscodeSuspect = Convert.ToInt32(reader.GetInt64(2), CultureInfo.InvariantCulture),
                });
            }

            return groups;
        }

        /// <inheritdoc/>
        public async Task<LibraryHealth.LibraryHealthDashboard> GetLibraryHealthDashboardAsync(
            string libraryPath,
            int artistLimit,
            int issueLimit,
            CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var transaction = conn.BeginTransaction();
            using var cmd = conn.CreateCommand();
            cmd.Transaction = transaction;
            var where = string.Empty;
            if (!string.IsNullOrWhiteSpace(libraryPath))
            {
                where = "WHERE file_path LIKE @path";
                cmd.Parameters.AddWithValue("@path", $"{libraryPath}%");
            }

            cmd.Parameters.AddWithValue("@artistLimit", Math.Clamp(artistLimit, 1, 100));
            cmd.CommandText = $@"
                WITH filtered AS MATERIALIZED (
                    SELECT type, severity, status, artist
                    FROM LibraryHealthIssues
                    {where}
                ),
                type_counts AS (
                    SELECT type, severity, COUNT(*) AS item_count
                    FROM filtered
                    GROUP BY type, severity
                ),
                artist_type_counts AS (
                    SELECT artist, type, COUNT(*) AS item_count
                    FROM filtered
                    WHERE LENGTH(TRIM(artist)) > 0
                    GROUP BY artist, type
                ),
                artist_totals AS (
                    SELECT artist, SUM(item_count) AS total_count
                    FROM artist_type_counts
                    GROUP BY artist
                ),
                top_artists AS (
                    SELECT artist, total_count
                    FROM artist_totals
                    ORDER BY total_count DESC, artist
                    LIMIT @artistLimit
                )
                SELECT
                    'summary' AS result_kind,
                    '' AS group_key,
                    '' AS subgroup_key,
                    COUNT(*) AS item_count,
                    0 AS group_total,
                    COALESCE(SUM(CASE WHEN status NOT IN ('resolved', 'ignored') THEN 1 ELSE 0 END), 0) AS open_count,
                    COALESCE(SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END), 0) AS resolved_count
                FROM filtered
                UNION ALL
                SELECT 'type', type, severity, item_count, 0, 0, 0
                FROM type_counts
                UNION ALL
                SELECT 'artist', counts.artist, counts.type, counts.item_count, top.total_count, 0, 0
                FROM artist_type_counts AS counts
                INNER JOIN top_artists AS top ON top.artist = counts.artist";

            var dashboard = new LibraryHealth.LibraryHealthDashboard();
            var typeGroups = new Dictionary<LibraryHealth.LibraryIssueType, LibraryHealth.LibraryIssueTypeSummary>();
            var artistGroups = new Dictionary<string, LibraryHealth.LibraryIssueArtistSummary>(StringComparer.Ordinal);
            using (var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false))
            {
                while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
                {
                    var kind = reader.GetString(0);
                    if (kind == "summary")
                    {
                        dashboard.Summary = new LibraryHealth.LibraryHealthSummary
                        {
                            LibraryPath = libraryPath,
                            TotalIssues = Convert.ToInt32(reader.GetInt64(3), CultureInfo.InvariantCulture),
                            IssuesOpen = Convert.ToInt32(reader.GetInt64(5), CultureInfo.InvariantCulture),
                            IssuesResolved = Convert.ToInt32(reader.GetInt64(6), CultureInfo.InvariantCulture),
                        };
                        dashboard.TotalIssues = dashboard.Summary.TotalIssues;
                    }
                    else if (kind == "type" &&
                        Enum.TryParse<LibraryHealth.LibraryIssueType>(reader.GetString(1), ignoreCase: true, out var type) &&
                        Enum.TryParse<LibraryHealth.LibraryIssueSeverity>(reader.GetString(2), ignoreCase: true, out var severity))
                    {
                        var count = Convert.ToInt32(reader.GetInt64(3), CultureInfo.InvariantCulture);
                        if (!typeGroups.TryGetValue(type, out var group))
                        {
                            group = new LibraryHealth.LibraryIssueTypeSummary { Type = type };
                            typeGroups[type] = group;
                        }

                        group.Count += count;
                        group.BySeverity[severity] = count;
                    }
                    else if (kind == "artist" &&
                        Enum.TryParse<LibraryHealth.LibraryIssueType>(reader.GetString(2), ignoreCase: true, out var artistType))
                    {
                        var artist = reader.GetString(1);
                        if (!artistGroups.TryGetValue(artist, out var group))
                        {
                            group = new LibraryHealth.LibraryIssueArtistSummary
                            {
                                Artist = artist,
                                Count = Convert.ToInt32(reader.GetInt64(4), CultureInfo.InvariantCulture),
                            };
                            artistGroups[artist] = group;
                        }

                        group.ByType[artistType] = Convert.ToInt32(reader.GetInt64(3), CultureInfo.InvariantCulture);
                    }
                }
            }

            dashboard.IssuesByType = typeGroups.Values
                .OrderByDescending(group => group.Count)
                .ThenBy(group => group.Type)
                .ToList();
            dashboard.IssuesByArtist = artistGroups.Values
                .OrderByDescending(group => group.Count)
                .ThenBy(group => group.Artist, StringComparer.Ordinal)
                .ToList();
            dashboard.Issues = await ReadLibraryIssuesAsync(
                conn,
                new LibraryHealth.LibraryHealthIssueFilter
                {
                    LibraryPath = libraryPath,
                    Limit = Math.Clamp(issueLimit, 1, 250),
                },
                transaction,
                cancellationToken).ConfigureAwait(false);
            transaction.Commit();
            return dashboard;
        }

        private static string BuildLibraryIssueArtistSummarySql(string where)
        {
            return $@"
                WITH filtered AS MATERIALIZED (
                    SELECT artist, type
                    FROM LibraryHealthIssues
                    {where}
                ),
                type_counts AS (
                    SELECT artist, type, COUNT(*) AS item_count
                    FROM filtered
                    GROUP BY artist, type
                ),
                totals AS (
                    SELECT artist, SUM(item_count) AS total_count
                    FROM type_counts
                    GROUP BY artist
                ),
                top_artists AS (
                    SELECT artist, total_count
                    FROM totals
                    ORDER BY total_count DESC, artist
                    LIMIT @artistLimit
                )
                SELECT counts.artist, counts.type, counts.item_count, top.total_count
                FROM type_counts AS counts
                INNER JOIN top_artists AS top ON top.artist = counts.artist
                ORDER BY top.total_count DESC, counts.artist, counts.type";
        }

        private static async Task<List<LibraryHealth.LibraryIssueArtistSummary>> ReadLibraryIssueArtistSummariesAsync(
            SqliteCommand cmd,
            CancellationToken cancellationToken)
        {
            var groups = new Dictionary<string, LibraryHealth.LibraryIssueArtistSummary>(StringComparer.Ordinal);
            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                if (!Enum.TryParse<LibraryHealth.LibraryIssueType>(reader.GetString(1), ignoreCase: true, out var type))
                {
                    continue;
                }

                var artist = reader.GetString(0);
                if (!groups.TryGetValue(artist, out var group))
                {
                    group = new LibraryHealth.LibraryIssueArtistSummary
                    {
                        Artist = artist,
                        Count = Convert.ToInt32(reader.GetInt64(3), CultureInfo.InvariantCulture),
                    };
                    groups[artist] = group;
                }

                group.ByType[type] = Convert.ToInt32(reader.GetInt64(2), CultureInfo.InvariantCulture);
            }

            return groups.Values
                .OrderByDescending(group => group.Count)
                .ThenBy(group => group.Artist, StringComparer.Ordinal)
                .ToList();
        }

        private static async Task<List<LibraryHealth.LibraryIssue>> ReadLibraryIssuesAsync(
            SqliteConnection conn,
            LibraryHealth.LibraryHealthIssueFilter filter,
            SqliteTransaction? transaction,
            CancellationToken cancellationToken)
        {
            var issues = new List<LibraryHealth.LibraryIssue>();
            using var cmd = conn.CreateCommand();
            cmd.Transaction = transaction;
            var sql = "SELECT * FROM LibraryHealthIssues" + BuildLibraryIssueFilterSql(cmd, filter);
            sql += " ORDER BY detected_at DESC LIMIT @limit OFFSET @offset";
            cmd.Parameters.AddWithValue("@limit", Math.Clamp(filter.Limit, 1, 250));
            cmd.Parameters.AddWithValue("@offset", Math.Max(0, filter.Offset));
            cmd.CommandText = sql;

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                issues.Add(ReadIssue(reader));
            }

            return issues;
        }

        private static string BuildLibraryIssueFilterSql(
            SqliteCommand cmd,
            LibraryHealth.LibraryHealthIssueFilter filter)
        {
            var conditions = new List<string>();
            if (!string.IsNullOrWhiteSpace(filter.LibraryPath))
            {
                conditions.Add("file_path LIKE @path");
                cmd.Parameters.AddWithValue("@path", $"{filter.LibraryPath}%");
            }

            if (!string.IsNullOrWhiteSpace(filter.MusicBrainzReleaseId))
            {
                conditions.Add("mb_release_id = @rid");
                cmd.Parameters.AddWithValue("@rid", filter.MusicBrainzReleaseId);
            }

            if (filter.Types != null && filter.Types.Count > 0)
            {
                conditions.Add($"type IN ({string.Join(",", filter.Types.Select((_, i) => $"@t{i}"))})");
                for (int i = 0; i < filter.Types.Count; i++)
                {
                    cmd.Parameters.AddWithValue($"@t{i}", filter.Types[i].ToString());
                }
            }

            if (filter.Severities != null && filter.Severities.Count > 0)
            {
                conditions.Add($"severity IN ({string.Join(",", filter.Severities.Select((_, i) => $"@s{i}"))})");
                for (int i = 0; i < filter.Severities.Count; i++)
                {
                    cmd.Parameters.AddWithValue($"@s{i}", filter.Severities[i].ToString());
                }
            }

            if (filter.Statuses != null && filter.Statuses.Count > 0)
            {
                conditions.Add($"status IN ({string.Join(",", filter.Statuses.Select((_, i) => $"@st{i}"))})");
                for (int i = 0; i < filter.Statuses.Count; i++)
                {
                    cmd.Parameters.AddWithValue($"@st{i}", filter.Statuses[i].ToString().ToLowerInvariant());
                }
            }

            return conditions.Count == 0 ? string.Empty : " WHERE " + string.Join(" AND ", conditions);
        }

        /// <inheritdoc/>
        public async Task UpdateLibraryIssueStatusAsync(string issueId, LibraryHealth.LibraryIssueStatus status, CancellationToken cancellationToken = default)
        {
            issueId = issueId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(issueId))
            {
                return;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                UPDATE LibraryHealthIssues
                SET status = @status,
                    resolved_at = CASE WHEN @status IN ('resolved','ignored') THEN strftime('%s','now') ELSE resolved_at END
                WHERE issue_id = @id";
            cmd.Parameters.AddWithValue("@status", status.ToString().ToLowerInvariant());
            cmd.Parameters.AddWithValue("@id", issueId);
            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        /// <inheritdoc/>
        public async Task<int> UpdateLibraryIssueStatusesAsync(
            IEnumerable<string> issueIds,
            LibraryHealth.LibraryIssueStatus status,
            string? remediationJobId = null,
            CancellationToken cancellationToken = default)
        {
            var normalized = issueIds
                .Where(issueId => !string.IsNullOrWhiteSpace(issueId))
                .Select(issueId => issueId.Trim())
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            if (normalized.Length == 0)
            {
                return 0;
            }

            var normalizedJobId = remediationJobId?.Trim();
            var affected = 0;
            using var conn = GetConnection();
            using var transaction = conn.BeginTransaction();
            foreach (var batch in normalized.Chunk(500))
            {
                using var cmd = conn.CreateCommand();
                cmd.Transaction = transaction;
                var parameters = batch.Select((_, index) => $"@issue{index}").ToArray();
                cmd.CommandText = $"""
                    UPDATE LibraryHealthIssues
                    SET status = @status,
                        remediation_job_id = CASE WHEN @set_job_id = 1 THEN @job_id ELSE remediation_job_id END,
                        resolved_at = CASE WHEN @status IN ('resolved', 'ignored') THEN strftime('%s','now') ELSE resolved_at END
                    WHERE issue_id IN ({string.Join(", ", parameters)})
                    """;
                cmd.Parameters.AddWithValue("@status", status.ToString().ToLowerInvariant());
                cmd.Parameters.AddWithValue("@set_job_id", string.IsNullOrWhiteSpace(normalizedJobId) ? 0 : 1);
                cmd.Parameters.AddWithValue("@job_id", (object?)normalizedJobId ?? DBNull.Value);
                for (var index = 0; index < batch.Length; index++)
                {
                    cmd.Parameters.AddWithValue(parameters[index], batch[index]);
                }

                affected += await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
            }

            transaction.Commit();
            return affected;
        }

        /// <inheritdoc/>
        public async Task InsertLibraryIssueAsync(LibraryHealth.LibraryIssue issue, CancellationToken cancellationToken = default)
        {
            issue.IssueId = issue.IssueId?.Trim() ?? string.Empty;
            issue.FilePath = string.IsNullOrWhiteSpace(issue.FilePath) ? string.Empty : issue.FilePath.Trim();
            issue.MusicBrainzRecordingId = string.IsNullOrWhiteSpace(issue.MusicBrainzRecordingId) ? string.Empty : issue.MusicBrainzRecordingId.Trim();
            issue.MusicBrainzReleaseId = string.IsNullOrWhiteSpace(issue.MusicBrainzReleaseId) ? string.Empty : issue.MusicBrainzReleaseId.Trim();
            issue.Artist = string.IsNullOrWhiteSpace(issue.Artist) ? string.Empty : issue.Artist.Trim();
            issue.Album = string.IsNullOrWhiteSpace(issue.Album) ? string.Empty : issue.Album.Trim();
            issue.Title = string.IsNullOrWhiteSpace(issue.Title) ? string.Empty : issue.Title.Trim();
            issue.Reason = string.IsNullOrWhiteSpace(issue.Reason) ? string.Empty : issue.Reason.Trim();
            issue.SuggestedAction = string.IsNullOrWhiteSpace(issue.SuggestedAction) ? string.Empty : issue.SuggestedAction.Trim();
            issue.RemediationJobId = string.IsNullOrWhiteSpace(issue.RemediationJobId) ? string.Empty : issue.RemediationJobId.Trim();
            issue.ResolvedBy = string.IsNullOrWhiteSpace(issue.ResolvedBy) ? string.Empty : issue.ResolvedBy.Trim();
            if (string.IsNullOrWhiteSpace(issue.IssueId))
            {
                return;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                INSERT INTO LibraryHealthIssues (
                    issue_id,
                    type,
                    severity,
                    file_path,
                    mb_recording_id,
                    mb_release_id,
                    artist,
                    album,
                    title,
                    reason,
                    metadata,
                    can_auto_fix,
                    suggested_action,
                    remediation_job_id,
                    status,
                    detected_at,
                    resolved_at,
                    resolved_by)
                VALUES (
                    @issue_id,
                    @type,
                    @severity,
                    @file_path,
                    @mb_recording_id,
                    @mb_release_id,
                    @artist,
                    @album,
                    @title,
                    @reason,
                    @metadata,
                    @can_auto_fix,
                    @suggested_action,
                    @remediation_job_id,
                    @status,
                    @detected_at,
                    @resolved_at,
                    @resolved_by)";

            cmd.Parameters.AddWithValue("@issue_id", issue.IssueId);
            cmd.Parameters.AddWithValue("@type", issue.Type.ToString());
            cmd.Parameters.AddWithValue("@severity", issue.Severity.ToString());
            cmd.Parameters.AddWithValue("@file_path", (object?)issue.FilePath ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@mb_recording_id", (object?)issue.MusicBrainzRecordingId ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@mb_release_id", (object?)issue.MusicBrainzReleaseId ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@artist", (object?)issue.Artist ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@album", (object?)issue.Album ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@title", (object?)issue.Title ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@reason", (object?)issue.Reason ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@metadata", JsonSerializer.Serialize(issue.Metadata ?? new Dictionary<string, object>()));
            cmd.Parameters.AddWithValue("@can_auto_fix", issue.CanAutoFix);
            cmd.Parameters.AddWithValue("@suggested_action", (object?)issue.SuggestedAction ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@remediation_job_id", (object?)issue.RemediationJobId ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@status", issue.Status.ToString().ToLowerInvariant());
            cmd.Parameters.AddWithValue("@detected_at", issue.DetectedAt.ToUnixTimeSeconds());
            cmd.Parameters.AddWithValue("@resolved_at", issue.ResolvedAt?.ToUnixTimeSeconds() ?? (object)DBNull.Value);
            cmd.Parameters.AddWithValue("@resolved_by", (object?)issue.ResolvedBy ?? DBNull.Value);

            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        private async Task TryResolveAcoustIdAsync(string filePath, string flacKey, string fingerprint, CancellationToken cancellationToken = default)
        {
            var filename = Path.GetFileName(filePath);
            var acoustIdStage = BeginMetadataStage(filename, "acoustid");
            filePath = filePath?.Trim() ?? string.Empty;
            flacKey = flacKey?.Trim() ?? string.Empty;
            fingerprint = fingerprint?.Trim() ?? string.Empty;
            if (acoustIdClient == null || optionsMonitor == null || musicBrainzClient == null)
            {
                FinishMetadataStage(acoustIdStage, "skipped", "AcoustID or MusicBrainz is not configured");
                return;
            }

            if (string.IsNullOrWhiteSpace(flacKey) || string.IsNullOrWhiteSpace(fingerprint))
            {
                FinishMetadataStage(acoustIdStage, "skipped", "Fingerprint data is unavailable");
                return;
            }

            MetadataProcessingEvent? musicBrainzStage = null;
            try
            {
                var chromaOptions = optionsMonitor.CurrentValue.Integration.Chromaprint;
                var result = await acoustIdClient.LookupAsync(fingerprint, chromaOptions.SampleRate, chromaOptions.DurationSeconds, cancellationToken).ConfigureAwait(false);

                var recordingId = result?.Recordings?.FirstOrDefault()?.Id;

                if (string.IsNullOrWhiteSpace(recordingId))
                {
                    log.Debug("[HashDb] AcoustID did not resolve a recording for fingerprint {Fingerprint}",
                        LoggingSanitizer.SanitizeHash(fingerprint));
                    FinishMetadataStage(acoustIdStage, "complete", "No recording match");
                    return;
                }

                await UpdateHashRecordingIdAsync(flacKey, recordingId, cancellationToken).ConfigureAwait(false);
                log.Information("[HashDb] Resolved AcoustID fingerprint to recording {RecordingId} for key {FlacKey}",
                    LoggingSanitizer.SanitizeExternalIdentifier(recordingId), LoggingSanitizer.SanitizeHash(flacKey));
                FinishMetadataStage(acoustIdStage, "complete", $"Recording {recordingId}");

                musicBrainzStage = BeginMetadataStage(filename, "musicbrainz");
                var track = await musicBrainzClient.GetRecordingAsync(recordingId, cancellationToken).ConfigureAwait(false);
                FinishMetadataStage(
                    musicBrainzStage,
                    "complete",
                    track is null ? "Recording metadata not found" : "Recording metadata found");

                if (track is not null && autoTaggingService != null && !string.IsNullOrWhiteSpace(filePath))
                {
                    var autoTagStage = BeginMetadataStage(filename, "auto_tagging");
                    try
                    {
                        var tagResult = await autoTaggingService.TagAsync(filePath, track, cancellationToken).ConfigureAwait(false);
                        FinishMetadataStage(autoTagStage, "complete", tagResult?.Updated == true ? "Tags updated" : "No tag changes needed");
                        if (tagResult?.Updated == true)
                        {
                            log.Information("[HashDb] Auto-tagged {File}", LoggingSanitizer.SanitizeFilePath(filePath));
                        }
                    }
                    catch (Exception ex)
                    {
                        FinishMetadataStage(autoTagStage, "failed", $"Auto-tagging failed ({ex.GetType().Name})");
                        log.Warning(ex, "[HashDb] Auto-tagging failed for {File}", LoggingSanitizer.SanitizeFilePath(filePath));
                    }
                }
            }
            catch (Exception ex)
            {
                FinishMetadataStage(
                    musicBrainzStage ?? acoustIdStage,
                    "failed",
                    $"Provider request failed ({ex.GetType().Name})");
                if (musicBrainzStage != null)
                {
                    FinishMetadataStage(acoustIdStage, "complete", "Recording resolved");
                }

                throw;
            }
        }

        /// <inheritdoc/>
        public async Task UpdateHashFingerprintAsync(string flacKey, string fingerprint, CancellationToken cancellationToken = default)
        {
            flacKey = flacKey?.Trim() ?? string.Empty;
            fingerprint = fingerprint?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(flacKey))
            {
                return;
            }

            if (string.IsNullOrWhiteSpace(fingerprint))
            {
                return;
            }

            // Invalidate cache when updating
            if (hashCache != null)
            {
                hashCache.Remove($"hashdb:lookup:{flacKey}");
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                UPDATE HashDb
                SET audio_fingerprint = @fingerprint,
                    last_updated_at = @now
                WHERE flac_key = @flac_key";
            cmd.Parameters.AddWithValue("@fingerprint", fingerprint);
            cmd.Parameters.AddWithValue("@now", DateTimeOffset.UtcNow.ToUnixTimeSeconds());
            cmd.Parameters.AddWithValue("@flac_key", flacKey);
            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        /// <inheritdoc/>
        public async Task UpdateVariantMetadataAsync(string flacKey, AudioVariant variant, CancellationToken cancellationToken = default)
        {
            flacKey = flacKey?.Trim() ?? string.Empty;
            if (variant == null)
            {
                return;
            }

            if (string.IsNullOrWhiteSpace(flacKey))
            {
                return;
            }

            variant.VariantId = string.IsNullOrWhiteSpace(variant.VariantId) ? flacKey : variant.VariantId.Trim();
            variant.Codec = string.IsNullOrWhiteSpace(variant.Codec) ? string.Empty : variant.Codec.Trim();
            variant.Container = string.IsNullOrWhiteSpace(variant.Container) ? string.Empty : variant.Container.Trim();
            variant.FileSha256 = string.IsNullOrWhiteSpace(variant.FileSha256) ? string.Empty : variant.FileSha256.Trim();
            variant.MusicBrainzRecordingId = string.IsNullOrWhiteSpace(variant.MusicBrainzRecordingId) ? string.Empty : variant.MusicBrainzRecordingId.Trim();
            variant.TranscodeReason = string.IsNullOrWhiteSpace(variant.TranscodeReason) ? string.Empty : variant.TranscodeReason.Trim();
            variant.EncoderSignature = string.IsNullOrWhiteSpace(variant.EncoderSignature) ? string.Empty : variant.EncoderSignature.Trim();
            variant.AnalyzerVersion = string.IsNullOrWhiteSpace(variant.AnalyzerVersion) ? string.Empty : variant.AnalyzerVersion.Trim();

            // Invalidate cache when updating metadata
            if (hashCache != null)
            {
                hashCache.Remove($"hashdb:lookup:{flacKey}");
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                UPDATE HashDb
                SET variant_id = @variant_id,
                    codec = @codec,
                    container = @container,
                    sample_rate_hz = @sample_rate_hz,
                    bit_depth = @bit_depth,
                    channels = @channels,
                    duration_ms = @duration_ms,
                    bitrate_kbps = @bitrate_kbps,
                    flac_streaminfo_hash42 = @flac_streaminfo_hash42,
                    flac_pcm_md5 = @flac_pcm_md5,
                    flac_min_block_size = @flac_min_block_size,
                    flac_max_block_size = @flac_max_block_size,
                    flac_min_frame_size = @flac_min_frame_size,
                    flac_max_frame_size = @flac_max_frame_size,
                    flac_total_samples = @flac_total_samples,
                    mp3_stream_hash = @mp3_stream_hash,
                    mp3_encoder = @mp3_encoder,
                    mp3_encoder_preset = @mp3_encoder_preset,
                    mp3_frames_analyzed = @mp3_frames_analyzed,
                    effective_bandwidth_hz = @effective_bandwidth_hz,
                    nominal_lowpass_hz = @nominal_lowpass_hz,
                    spectral_flatness_score = @spectral_flatness_score,
                    hf_energy_ratio = @hf_energy_ratio,
                    opus_stream_hash = @opus_stream_hash,
                    opus_nominal_bitrate_kbps = @opus_nominal_bitrate_kbps,
                    opus_application = @opus_application,
                    opus_bandwidth_mode = @opus_bandwidth_mode,
                    aac_stream_hash = @aac_stream_hash,
                    aac_profile = @aac_profile,
                    aac_sbr_present = @aac_sbr_present,
                    aac_ps_present = @aac_ps_present,
                    aac_nominal_bitrate_kbps = @aac_nominal_bitrate_kbps,
                    audio_sketch_hash = @audio_sketch_hash,
                    quality_score = @quality_score,
                    transcode_suspect = @transcode_suspect,
                    transcode_reason = @transcode_reason,
                    dynamic_range_dr = @dynamic_range_dr,
                    loudness_lufs = @loudness_lufs,
                    has_clipping = @has_clipping,
                    encoder_signature = @encoder_signature,
                    analyzer_version = @analyzer_version,
                    seen_count = COALESCE(seen_count, 1),
                    file_sha256 = @file_sha256,
                    musicbrainz_id = COALESCE(musicbrainz_id, @recording_id),
                    last_updated_at = @now
                WHERE flac_key = @flac_key";

            cmd.Parameters.AddWithValue("@variant_id", variant.VariantId ?? flacKey);
            cmd.Parameters.AddWithValue("@codec", (object?)variant.Codec ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@container", (object?)variant.Container ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@sample_rate_hz", variant.SampleRateHz);
            cmd.Parameters.AddWithValue("@bit_depth", (object?)variant.BitDepth ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@channels", variant.Channels);
            cmd.Parameters.AddWithValue("@duration_ms", variant.DurationMs);
            cmd.Parameters.AddWithValue("@bitrate_kbps", variant.BitrateKbps);
            cmd.Parameters.AddWithValue("@flac_streaminfo_hash42", (object?)variant.FlacStreamInfoHash42 ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@flac_pcm_md5", (object?)variant.FlacPcmMd5 ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@flac_min_block_size", (object?)variant.FlacMinBlockSize ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@flac_max_block_size", (object?)variant.FlacMaxBlockSize ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@flac_min_frame_size", (object?)variant.FlacMinFrameSize ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@flac_max_frame_size", (object?)variant.FlacMaxFrameSize ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@flac_total_samples", (object?)variant.FlacTotalSamples ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@mp3_stream_hash", (object?)variant.Mp3StreamHash ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@mp3_encoder", (object?)variant.Mp3Encoder ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@mp3_encoder_preset", (object?)variant.Mp3EncoderPreset ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@mp3_frames_analyzed", (object?)variant.Mp3FramesAnalyzed ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@effective_bandwidth_hz", (object?)variant.EffectiveBandwidthHz ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@nominal_lowpass_hz", (object?)variant.NominalLowpassHz ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@spectral_flatness_score", (object?)variant.SpectralFlatnessScore ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@hf_energy_ratio", (object?)variant.HfEnergyRatio ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@opus_stream_hash", (object?)variant.OpusStreamHash ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@opus_nominal_bitrate_kbps", (object?)variant.OpusNominalBitrateKbps ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@opus_application", (object?)variant.OpusApplication ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@opus_bandwidth_mode", (object?)variant.OpusBandwidthMode ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@aac_stream_hash", (object?)variant.AacStreamHash ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@aac_profile", (object?)variant.AacProfile ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@aac_sbr_present", (object?)variant.AacSbrPresent ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@aac_ps_present", (object?)variant.AacPsPresent ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@aac_nominal_bitrate_kbps", (object?)variant.AacNominalBitrateKbps ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@audio_sketch_hash", (object?)variant.AudioSketchHash ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@quality_score", variant.QualityScore);
            cmd.Parameters.AddWithValue("@transcode_suspect", variant.TranscodeSuspect);
            cmd.Parameters.AddWithValue("@transcode_reason", (object?)variant.TranscodeReason ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@dynamic_range_dr", (object?)variant.DynamicRangeDR ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@loudness_lufs", (object?)variant.LoudnessLUFS ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@has_clipping", (object?)variant.HasClipping ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@encoder_signature", (object?)variant.EncoderSignature ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@analyzer_version", (object?)variant.AnalyzerVersion ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@file_sha256", (object?)variant.FileSha256 ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@recording_id", (object?)variant.MusicBrainzRecordingId ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@now", DateTimeOffset.UtcNow.ToUnixTimeSeconds());
            cmd.Parameters.AddWithValue("@flac_key", flacKey);

            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        /// <inheritdoc/>
        public async Task UpdateVariantAnalysisAsync(
            IEnumerable<AudioVariant> variants,
            CancellationToken cancellationToken = default)
        {
            var normalized = new Dictionary<string, AudioVariant>(StringComparer.Ordinal);
            foreach (var variant in variants.Where(variant => !string.IsNullOrWhiteSpace(variant.FlacKey)))
            {
                variant.FlacKey = variant.FlacKey.Trim();
                variant.TranscodeReason = string.IsNullOrWhiteSpace(variant.TranscodeReason)
                    ? string.Empty
                    : variant.TranscodeReason.Trim();
                variant.AnalyzerVersion = string.IsNullOrWhiteSpace(variant.AnalyzerVersion)
                    ? string.Empty
                    : variant.AnalyzerVersion.Trim();
                normalized[variant.FlacKey] = variant;
            }

            if (normalized.Count == 0)
            {
                return;
            }

            using var connection = GetConnection();
            using var transaction = connection.BeginTransaction();
            foreach (var batch in normalized.Values.Chunk(VariantAnalysisUpdateBatchSize))
            {
                using var command = connection.CreateCommand();
                command.Transaction = transaction;
                var values = batch.Select((_, index) =>
                    $"(@flac_key{index}, @quality_score{index}, @transcode_suspect{index}, @transcode_reason{index}, @analyzer_version{index}, @last_updated_at)");
                command.CommandText = $"""
                    WITH updates (
                        flac_key,
                        quality_score,
                        transcode_suspect,
                        transcode_reason,
                        analyzer_version,
                        last_updated_at) AS (
                        VALUES {string.Join(", ", values)}
                    )
                    UPDATE HashDb AS target
                    SET quality_score = updates.quality_score,
                        transcode_suspect = updates.transcode_suspect,
                        transcode_reason = updates.transcode_reason,
                        analyzer_version = updates.analyzer_version,
                        last_updated_at = updates.last_updated_at
                    FROM updates
                    WHERE target.flac_key = updates.flac_key
                    """;
                command.Parameters.AddWithValue("@last_updated_at", DateTimeOffset.UtcNow.ToUnixTimeSeconds());
                for (var index = 0; index < batch.Length; index++)
                {
                    var variant = batch[index];
                    command.Parameters.AddWithValue($"@flac_key{index}", variant.FlacKey);
                    command.Parameters.AddWithValue($"@quality_score{index}", variant.QualityScore);
                    command.Parameters.AddWithValue($"@transcode_suspect{index}", variant.TranscodeSuspect);
                    command.Parameters.AddWithValue($"@transcode_reason{index}", variant.TranscodeReason);
                    command.Parameters.AddWithValue($"@analyzer_version{index}", variant.AnalyzerVersion);
                }

                await command.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
            }

            transaction.Commit();
            if (hashCache != null)
            {
                foreach (var flacKey in normalized.Keys)
                {
                    hashCache.Remove($"hashdb:lookup:{flacKey}");
                }
            }
        }

        /// <inheritdoc/>
        public async Task<List<AudioVariant>> GetVariantsByRecordingAsync(string recordingId, CancellationToken cancellationToken = default)
        {
            var list = new List<AudioVariant>();
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = $"""
                WITH source AS (
                    SELECT
                        HashDb.*,
                        CASE
                            WHEN variant_id IS NULL OR TRIM(
                                variant_id,
                                {SqlDotNetWhitespaceCharacterSet}) = ''
                                THEN flac_key
                            ELSE variant_id
                        END AS variant_identity,
                        ROW_NUMBER() OVER (
                            ORDER BY quality_score DESC, last_updated_at DESC) AS source_sequence
                    FROM HashDb
                    WHERE musicbrainz_id = @recordingId
                ),
                ranked AS (
                    SELECT
                        source.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY variant_identity
                            ORDER BY source_sequence) AS variant_rank
                    FROM source
                )
                SELECT *
                FROM ranked
                WHERE variant_rank = 1
                ORDER BY source_sequence
                """;
            cmd.Parameters.AddWithValue("@recordingId", recordingId);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                var entry = ReadHashEntry(reader);
                var variant = MapEntryToVariant(entry);
                if (variant != null)
                {
                    list.Add(variant);
                }
            }

            return list;
        }

        /// <inheritdoc/>
        public async Task<AudioVariant?> GetBestVariantByRecordingAsync(
            string recordingId,
            CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = """
                WITH ranked AS (
                    SELECT
                        HashDb.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY COALESCE(NULLIF(TRIM(variant_id), ''), flac_key)
                            ORDER BY quality_score DESC, last_updated_at DESC
                        ) AS variant_rank
                    FROM HashDb
                    WHERE musicbrainz_id = @recording_id
                )
                SELECT *
                FROM ranked
                WHERE variant_rank = 1
                ORDER BY quality_score DESC, seen_count DESC, last_updated_at DESC
                LIMIT 1
                """;
            cmd.Parameters.AddWithValue("@recording_id", recordingId);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            if (!await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                return null;
            }

            return MapEntryToVariant(ReadHashEntry(reader));
        }

        /// <inheritdoc/>
        public async Task<List<AudioVariant>> GetVariantsByRecordingsAsync(
            IEnumerable<string> recordingIds,
            CancellationToken cancellationToken = default)
        {
            var normalized = recordingIds
                .Where(recordingId => !string.IsNullOrWhiteSpace(recordingId))
                .Select(recordingId => recordingId.Trim())
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            var variants = new List<AudioVariant>();
            if (normalized.Length == 0)
            {
                return variants;
            }

            using var conn = GetConnection();
            foreach (var batch in normalized.Chunk(500))
            {
                using var cmd = conn.CreateCommand();
                var parameters = batch.Select((_, index) => $"@recording{index}").ToArray();
                cmd.CommandText = $"""
                    WITH source AS (
                        SELECT
                            HashDb.*,
                            CASE
                                WHEN variant_id IS NULL OR TRIM(
                                    variant_id,
                                    {SqlDotNetWhitespaceCharacterSet}) = ''
                                    THEN flac_key
                                ELSE variant_id
                            END AS variant_identity,
                            ROW_NUMBER() OVER () AS source_sequence
                        FROM HashDb
                        WHERE musicbrainz_id IN ({string.Join(", ", parameters)})
                    ),
                    ranked AS (
                        SELECT
                            source.*,
                            ROW_NUMBER() OVER (
                                PARTITION BY musicbrainz_id, variant_identity
                                ORDER BY
                                    COALESCE(quality_score, 0) DESC,
                                    last_updated_at DESC,
                                    source_sequence) AS variant_rank,
                            MIN(source_sequence) OVER (
                                PARTITION BY musicbrainz_id, variant_identity) AS group_sequence
                        FROM source
                    )
                    SELECT *
                    FROM ranked
                    WHERE variant_rank = 1
                    ORDER BY group_sequence
                    """;

                for (var index = 0; index < batch.Length; index++)
                {
                    cmd.Parameters.AddWithValue(parameters[index], batch[index]);
                }

                await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
                while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
                {
                    var variant = MapEntryToVariant(ReadHashEntry(reader));
                    if (variant != null)
                    {
                        variants.Add(variant);
                    }
                }
            }

            return variants;
        }

        /// <inheritdoc/>
        public async Task<List<AudioVariant>> GetRecentVariantsAsync(
            int limit,
            CancellationToken cancellationToken = default)
        {
            var variants = new List<AudioVariant>();
            if (limit <= 0)
            {
                return variants;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = """
                WITH exact_recordings AS (
                    SELECT
                        musicbrainz_id,
                        MAX(last_updated_at) AS recording_last_updated
                    FROM HashDb
                    WHERE musicbrainz_id IS NOT NULL
                      AND TRIM(musicbrainz_id) <> ''
                    GROUP BY musicbrainz_id
                ),
                selected_recordings AS (
                    SELECT
                        musicbrainz_id,
                        recording_last_updated,
                        ROW_NUMBER() OVER (
                            PARTITION BY TRIM(musicbrainz_id) COLLATE NOCASE
                            ORDER BY recording_last_updated DESC, musicbrainz_id
                        ) AS recording_rank
                    FROM exact_recordings
                ),
                ranked AS (
                    SELECT
                        HashDb.*,
                        selected_recordings.recording_last_updated,
                        ROW_NUMBER() OVER (
                            PARTITION BY
                                HashDb.musicbrainz_id,
                                COALESCE(NULLIF(TRIM(variant_id), ''), flac_key)
                            ORDER BY quality_score DESC, last_updated_at DESC, flac_key
                        ) AS variant_rank
                    FROM HashDb
                    INNER JOIN selected_recordings
                        ON selected_recordings.musicbrainz_id = HashDb.musicbrainz_id
                       AND selected_recordings.recording_rank = 1
                )
                SELECT *
                FROM ranked
                WHERE variant_rank = 1
                ORDER BY
                    recording_last_updated DESC,
                    musicbrainz_id COLLATE NOCASE,
                    quality_score DESC,
                    last_updated_at DESC,
                    flac_key
                LIMIT @limit
                """;
            cmd.Parameters.AddWithValue("@limit", limit);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                var variant = MapEntryToVariant(ReadHashEntry(reader));
                if (variant != null)
                {
                    variants.Add(variant);
                }
            }

            return variants;
        }

        /// <inheritdoc/>
        public async Task<List<AudioVariant>> GetRecentBestVariantsByRecordingAsync(
            int recordingLimit,
            CancellationToken cancellationToken = default)
        {
            var variants = new List<AudioVariant>();
            if (recordingLimit <= 0)
            {
                return variants;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = """
                WITH exact_recordings AS (
                    SELECT
                        musicbrainz_id,
                        MAX(last_updated_at) AS recording_last_updated
                    FROM HashDb
                    WHERE musicbrainz_id IS NOT NULL
                      AND TRIM(musicbrainz_id) <> ''
                    GROUP BY musicbrainz_id
                ),
                selected_recordings AS (
                    SELECT
                        musicbrainz_id,
                        recording_last_updated,
                        ROW_NUMBER() OVER (
                            PARTITION BY TRIM(musicbrainz_id) COLLATE NOCASE
                            ORDER BY recording_last_updated DESC, musicbrainz_id
                        ) AS recording_rank
                    FROM exact_recordings
                ),
                recent_recordings AS (
                    SELECT musicbrainz_id, recording_last_updated
                    FROM selected_recordings
                    WHERE recording_rank = 1
                    ORDER BY recording_last_updated DESC, musicbrainz_id COLLATE NOCASE
                    LIMIT @recording_limit
                ),
                ranked AS (
                    SELECT
                        HashDb.*,
                        recent_recordings.recording_last_updated,
                        ROW_NUMBER() OVER (
                            PARTITION BY HashDb.musicbrainz_id
                            ORDER BY
                                quality_score DESC,
                                seen_count DESC,
                                last_updated_at DESC,
                                flac_key
                        ) AS variant_rank
                    FROM HashDb
                    INNER JOIN recent_recordings
                        ON recent_recordings.musicbrainz_id = HashDb.musicbrainz_id
                )
                SELECT *
                FROM ranked
                WHERE variant_rank = 1
                ORDER BY recording_last_updated DESC, musicbrainz_id COLLATE NOCASE
                """;
            cmd.Parameters.AddWithValue("@recording_limit", recordingLimit);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                var variant = MapEntryToVariant(ReadHashEntry(reader));
                if (variant != null)
                {
                    variants.Add(variant);
                }
            }

            return variants;
        }

        /// <inheritdoc/>
        public async Task<List<AudioVariant>> GetVariantsByRecordingAndProfileAsync(string recordingId, string codecProfileKey, CancellationToken cancellationToken = default)
        {
            var list = new List<AudioVariant>();
            using var conn = GetConnection();
            conn.CreateFunction<string, int, int?, int, string, bool>(
                "matches_codec_profile",
                CodecProfile.MatchesKey);
            using var cmd = conn.CreateCommand();
            cmd.CommandText = $"""
                WITH matching_profiles AS (
                    SELECT codec, sample_rate_hz, bit_depth, channels
                    FROM HashDb
                    WHERE musicbrainz_id = @recordingId
                    GROUP BY codec, sample_rate_hz, bit_depth, channels
                    HAVING matches_codec_profile(
                        COALESCE(codec, ''),
                        COALESCE(sample_rate_hz, 0),
                        bit_depth,
                        COALESCE(channels, 2),
                        @codecProfileKey)
                ),
                source AS (
                    SELECT
                        HashDb.*,
                        CASE
                            WHEN variant_id IS NULL OR TRIM(
                                variant_id,
                                {SqlDotNetWhitespaceCharacterSet}) = ''
                                THEN flac_key
                            ELSE variant_id
                        END AS variant_identity,
                        ROW_NUMBER() OVER (
                            ORDER BY quality_score DESC, last_updated_at DESC) AS source_sequence
                    FROM HashDb
                    INNER JOIN matching_profiles
                        ON matching_profiles.codec IS HashDb.codec
                       AND matching_profiles.sample_rate_hz IS HashDb.sample_rate_hz
                       AND matching_profiles.bit_depth IS HashDb.bit_depth
                       AND matching_profiles.channels IS HashDb.channels
                    WHERE musicbrainz_id = @recordingId
                ),
                ranked AS (
                    SELECT
                        source.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY variant_identity
                            ORDER BY source_sequence) AS variant_rank
                    FROM source
                )
                SELECT *
                FROM ranked
                WHERE variant_rank = 1
                ORDER BY source_sequence
                """;
            cmd.Parameters.AddWithValue("@recordingId", recordingId);
            cmd.Parameters.AddWithValue("@codecProfileKey", codecProfileKey);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                var variant = MapEntryToVariant(ReadHashEntry(reader));
                if (variant != null)
                {
                    list.Add(variant);
                }
            }

            return list;
        }

        /// <inheritdoc/>
        public async Task UpsertCanonicalStatsAsync(CanonicalStats stats, CancellationToken cancellationToken = default)
        {
            if (!NormalizeCanonicalStats(stats))
            {
                return;
            }

            using var conn = GetConnection();
            await UpsertCanonicalStatsBatchAsync(
                conn,
                transaction: null,
                new[] { stats },
                cancellationToken).ConfigureAwait(false);
        }

        /// <inheritdoc/>
        public async Task UpsertCanonicalStatsAsync(
            IEnumerable<CanonicalStats> stats,
            CancellationToken cancellationToken = default)
        {
            var normalized = stats
                .Where(NormalizeCanonicalStats)
                .ToList();
            if (normalized.Count == 0)
            {
                return;
            }

            using var conn = GetConnection();
            using var transaction = conn.BeginTransaction();
            foreach (var batch in normalized.Chunk(CanonicalStatsUpsertBatchSize))
            {
                await UpsertCanonicalStatsBatchAsync(
                    conn,
                    transaction,
                    batch,
                    cancellationToken).ConfigureAwait(false);
            }

            transaction.Commit();
        }

        private static bool NormalizeCanonicalStats(CanonicalStats stats)
        {
            stats.Id = stats.Id?.Trim() ?? string.Empty;
            stats.MusicBrainzRecordingId = stats.MusicBrainzRecordingId?.Trim() ?? string.Empty;
            stats.CodecProfileKey = stats.CodecProfileKey?.Trim() ?? string.Empty;
            stats.BestVariantId = string.IsNullOrWhiteSpace(stats.BestVariantId) ? string.Empty : stats.BestVariantId.Trim();
            return !string.IsNullOrWhiteSpace(stats.Id) &&
                !string.IsNullOrWhiteSpace(stats.MusicBrainzRecordingId) &&
                !string.IsNullOrWhiteSpace(stats.CodecProfileKey);
        }

        private static async Task UpsertCanonicalStatsBatchAsync(
            SqliteConnection connection,
            SqliteTransaction? transaction,
            IReadOnlyList<CanonicalStats> stats,
            CancellationToken cancellationToken)
        {
            using var cmd = connection.CreateCommand();
            cmd.Transaction = transaction;
            var values = stats.Select((_, index) => $"""
                (@id{index},
                 @recording_id{index},
                 @codec_profile_key{index},
                 @variant_count{index},
                 @total_seen_count{index},
                 @avg_quality_score{index},
                 @max_quality_score{index},
                 @percent_transcode_suspect{index},
                 @codec_distribution{index},
                 @bitrate_distribution{index},
                 @sample_rate_distribution{index},
                 @best_variant_id{index},
                 @canonicality_score{index},
                 @last_updated{index})
                """);
            cmd.CommandText = $"""
                INSERT INTO CanonicalStats (
                    id,
                    musicbrainz_recording_id,
                    codec_profile_key,
                    variant_count,
                    total_seen_count,
                    avg_quality_score,
                    max_quality_score,
                    percent_transcode_suspect,
                    codec_distribution,
                    bitrate_distribution,
                    sample_rate_distribution,
                    best_variant_id,
                    canonicality_score,
                    last_updated)
                VALUES {string.Join(", ", values)}
                ON CONFLICT(id) DO UPDATE SET
                    variant_count = excluded.variant_count,
                    total_seen_count = excluded.total_seen_count,
                    avg_quality_score = excluded.avg_quality_score,
                    max_quality_score = excluded.max_quality_score,
                    percent_transcode_suspect = excluded.percent_transcode_suspect,
                    codec_distribution = excluded.codec_distribution,
                    bitrate_distribution = excluded.bitrate_distribution,
                    sample_rate_distribution = excluded.sample_rate_distribution,
                    best_variant_id = excluded.best_variant_id,
                    canonicality_score = excluded.canonicality_score,
                    last_updated = excluded.last_updated
                """;

            for (var index = 0; index < stats.Count; index++)
            {
                var item = stats[index];
                cmd.Parameters.AddWithValue($"@id{index}", item.Id);
                cmd.Parameters.AddWithValue($"@recording_id{index}", item.MusicBrainzRecordingId);
                cmd.Parameters.AddWithValue($"@codec_profile_key{index}", item.CodecProfileKey);
                cmd.Parameters.AddWithValue($"@variant_count{index}", item.VariantCount);
                cmd.Parameters.AddWithValue($"@total_seen_count{index}", item.TotalSeenCount);
                cmd.Parameters.AddWithValue($"@avg_quality_score{index}", item.AvgQualityScore);
                cmd.Parameters.AddWithValue($"@max_quality_score{index}", item.MaxQualityScore);
                cmd.Parameters.AddWithValue($"@percent_transcode_suspect{index}", item.PercentTranscodeSuspect);
                cmd.Parameters.AddWithValue($"@codec_distribution{index}", JsonSerializer.Serialize(item.CodecDistribution));
                cmd.Parameters.AddWithValue($"@bitrate_distribution{index}", JsonSerializer.Serialize(item.BitrateDistribution));
                cmd.Parameters.AddWithValue($"@sample_rate_distribution{index}", JsonSerializer.Serialize(item.SampleRateDistribution));
                cmd.Parameters.AddWithValue($"@best_variant_id{index}", (object?)item.BestVariantId ?? DBNull.Value);
                cmd.Parameters.AddWithValue($"@canonicality_score{index}", item.CanonicalityScore);
                cmd.Parameters.AddWithValue($"@last_updated{index}", item.LastUpdated.ToUnixTimeSeconds());
            }

            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        /// <inheritdoc/>
        public async Task<CanonicalStats?> GetCanonicalStatsAsync(string recordingId, string codecProfileKey, CancellationToken cancellationToken = default)
        {
            recordingId = recordingId?.Trim() ?? string.Empty;
            codecProfileKey = codecProfileKey?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(recordingId) || string.IsNullOrWhiteSpace(codecProfileKey))
            {
                return null;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT * FROM CanonicalStats WHERE musicbrainz_recording_id = @rec AND codec_profile_key = @key";
            cmd.Parameters.AddWithValue("@rec", recordingId);
            cmd.Parameters.AddWithValue("@key", codecProfileKey);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            if (await reader.ReadAsync(cancellationToken))
            {
                return ReadCanonicalStats(reader);
            }

            return null;
        }

        /// <inheritdoc/>
        public async Task<List<CanonicalStats>> GetCanonicalStatsForRecordingAsync(
            string recordingId,
            CancellationToken cancellationToken = default)
        {
            var stats = new List<CanonicalStats>();
            recordingId = recordingId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(recordingId))
            {
                return stats;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT * FROM CanonicalStats WHERE musicbrainz_recording_id = @rec";
            cmd.Parameters.AddWithValue("@rec", recordingId);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                stats.Add(ReadCanonicalStats(reader));
            }

            return stats;
        }

        /// <inheritdoc/>
        public async Task<List<string>> GetRecordingIdsWithVariantsAsync(CancellationToken cancellationToken = default)
        {
            var list = new List<string>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT musicbrainz_id
                FROM HashDb
                WHERE musicbrainz_id IS NOT NULL AND TRIM(musicbrainz_id) <> ''
                GROUP BY musicbrainz_id
                ORDER BY MAX(last_updated_at) DESC";
            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                var recordingId = reader.GetString(0).Trim();
                if (!string.IsNullOrWhiteSpace(recordingId) && seen.Add(recordingId))
                {
                    list.Add(recordingId);
                }
            }

            return list;
        }

        /// <inheritdoc/>
        public async Task<List<string>> GetRecordingIdsWithVariantsPageAsync(
            string? afterRecordingId,
            int limit,
            CancellationToken cancellationToken = default)
        {
            var list = new List<string>();
            if (limit <= 0)
            {
                return list;
            }

            var cursor = afterRecordingId?.Trim();
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();

            // Keep separate first-page and keyset SQL shapes so SQLite can use an index range search.
            cmd.CommandText = string.IsNullOrWhiteSpace(cursor)
                ? """
                    SELECT DISTINCT TRIM(musicbrainz_id) COLLATE NOCASE AS recording_id
                    FROM HashDb
                    WHERE musicbrainz_id IS NOT NULL AND TRIM(musicbrainz_id) <> ''
                    ORDER BY recording_id COLLATE NOCASE
                    LIMIT @limit
                    """
                : """
                    SELECT DISTINCT TRIM(musicbrainz_id) COLLATE NOCASE AS recording_id
                    FROM HashDb
                    WHERE musicbrainz_id IS NOT NULL AND TRIM(musicbrainz_id) <> ''
                      AND TRIM(musicbrainz_id) COLLATE NOCASE > @after
                    ORDER BY recording_id COLLATE NOCASE
                    LIMIT @limit
                    """;
            cmd.Parameters.AddWithValue("@limit", limit);
            if (!string.IsNullOrWhiteSpace(cursor))
            {
                cmd.Parameters.AddWithValue("@after", cursor);
            }

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                list.Add(reader.GetString(0));
            }

            return list;
        }

        /// <inheritdoc/>
        public async Task<List<string>> GetCodecProfilesForRecordingAsync(string recordingId, CancellationToken cancellationToken = default)
        {
            var list = new List<string>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            recordingId = recordingId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(recordingId))
            {
                return list;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT codec, sample_rate_hz, bit_depth, channels FROM HashDb WHERE musicbrainz_id = @rec";
            cmd.Parameters.AddWithValue("@rec", recordingId);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                var codec = reader.IsDBNull(0) ? "Unknown" : reader.GetString(0).Trim();
                var sampleRate = reader.IsDBNull(1) ? 0 : reader.GetInt32(1);
                var bitDepth = reader.IsDBNull(2) ? (int?)null : reader.GetInt32(2);
                var channels = reader.IsDBNull(3) ? 2 : reader.GetInt32(3);

                var profile = new CodecProfile
                {
                    Codec = codec,
                    IsLossless = CodecProfileFromCodec(codec),
                    SampleRateHz = sampleRate,
                    BitDepth = bitDepth,
                    Channels = channels,
                }.ToKey();

                if (seen.Add(profile))
                {
                    list.Add(profile);
                }
            }

            return list;
        }

        /// <inheritdoc/>
        public async Task<Jobs.DiscographyJob?> GetDiscographyJobAsync(string jobId, CancellationToken cancellationToken = default)
        {
            jobId = jobId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(jobId))
            {
                return null;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT job_id, artist_id, artist_name, profile, target_directory, total_releases, completed_releases, failed_releases, status, created_at, json_data
                FROM DiscographyJobs
                WHERE job_id = @job_id";
            cmd.Parameters.AddWithValue("@job_id", jobId);

            await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            if (!await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                return null;
            }

            var json = reader.IsDBNull(10) ? null : reader.GetString(10);

            try
            {
                if (!string.IsNullOrWhiteSpace(json))
                {
                    var deserialized = JsonSerializer.Deserialize<Jobs.DiscographyJob>(json, CaseInsensitiveJson);
                    if (deserialized != null)
                    {
                        return NormalizeDiscographyJob(deserialized);
                    }
                }
            }
            catch (Exception ex)
            {
                log.Warning(ex, "[HashDb] Failed to deserialize discography job {JobId}",
                    LoggingSanitizer.SanitizeExternalIdentifier(jobId));
            }

            var profileText = reader.IsDBNull(3) ? null : reader.GetString(3);
            var statusText = reader.IsDBNull(8) ? null : reader.GetString(8);
            return NormalizeDiscographyJob(new Jobs.DiscographyJob
            {
                JobId = reader.GetString(0).Trim(),
                ArtistId = reader.IsDBNull(1) ? string.Empty : reader.GetString(1).Trim(),
                ArtistName = reader.IsDBNull(2) ? string.Empty : reader.GetString(2).Trim(),
                Profile = Enum.TryParse<Integrations.MusicBrainz.DiscographyProfile>(profileText, ignoreCase: true, out var profile)
                    ? profile
                    : Integrations.MusicBrainz.DiscographyProfile.CoreDiscography,
                TargetDirectory = reader.IsDBNull(4) ? string.Empty : reader.GetString(4).Trim(),
                TotalReleases = reader.IsDBNull(5) ? 0 : reader.GetInt32(5),
                CompletedReleases = reader.IsDBNull(6) ? 0 : reader.GetInt32(6),
                FailedReleases = reader.IsDBNull(7) ? 0 : reader.GetInt32(7),
                Status = Enum.TryParse<Jobs.JobStatus>(statusText, ignoreCase: true, out var status)
                    ? status
                    : Jobs.JobStatus.Pending,
                CreatedAt = reader.IsDBNull(9) ? DateTimeOffset.UtcNow : DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(9)),
            });
        }

        /// <inheritdoc/>
        public async Task<IReadOnlyList<Jobs.DiscographyJob>> ListDiscographyJobsAsync(CancellationToken cancellationToken = default)
        {
            var results = new List<Jobs.DiscographyJob>();

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT job_id, artist_id, artist_name, profile, target_directory, total_releases, completed_releases, failed_releases, status, created_at, json_data
                FROM DiscographyJobs
                ORDER BY created_at DESC";

            await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                var json = reader.IsDBNull(10) ? null : reader.GetString(10);
                Jobs.DiscographyJob? job = null;

                if (!string.IsNullOrWhiteSpace(json))
                {
                    try
                    {
                        job = JsonSerializer.Deserialize<Jobs.DiscographyJob>(json, CaseInsensitiveJson);
                    }
                    catch (Exception ex)
                    {
                        log.Warning(ex, "[HashDb] Failed to deserialize discography job from list row");
                    }
                }

                if (job == null)
                {
                    var profileText = reader.IsDBNull(3) ? null : reader.GetString(3);
                    var statusText = reader.IsDBNull(8) ? null : reader.GetString(8);
                    job = new Jobs.DiscographyJob
                    {
                        JobId = reader.GetString(0).Trim(),
                        ArtistId = reader.IsDBNull(1) ? string.Empty : reader.GetString(1).Trim(),
                        ArtistName = reader.IsDBNull(2) ? string.Empty : reader.GetString(2).Trim(),
                        Profile = Enum.TryParse<Integrations.MusicBrainz.DiscographyProfile>(profileText, ignoreCase: true, out var profile)
                            ? profile
                            : Integrations.MusicBrainz.DiscographyProfile.CoreDiscography,
                        TargetDirectory = reader.IsDBNull(4) ? string.Empty : reader.GetString(4).Trim(),
                        TotalReleases = reader.IsDBNull(5) ? 0 : reader.GetInt32(5),
                        CompletedReleases = reader.IsDBNull(6) ? 0 : reader.GetInt32(6),
                        FailedReleases = reader.IsDBNull(7) ? 0 : reader.GetInt32(7),
                        Status = Enum.TryParse<Jobs.JobStatus>(statusText, ignoreCase: true, out var status)
                            ? status
                            : Jobs.JobStatus.Pending,
                        CreatedAt = reader.IsDBNull(9) ? DateTimeOffset.UtcNow : DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(9)),
                    };
                }

                results.Add(NormalizeDiscographyJob(job));
            }

            return results;
        }

        /// <inheritdoc/>
        public async Task<Jobs.JobListPage> GetJobListPageAsync(
            string? type,
            string? status,
            int limit,
            int offset,
            string? sortBy,
            bool descending,
            CancellationToken cancellationToken = default)
        {
            var normalizedType = type?.Trim().ToLowerInvariant();
            var normalizedStatus = status?.Trim().ToLowerInvariant();
            var normalizedSort = sortBy?.Trim().ToLowerInvariant();
            var knownStatus = normalizedStatus is "pending" or "running" or "completed" or "failed";
            var selects = new List<string>();
            if (normalizedType == null || normalizedType == "discography")
            {
                selects.Add(BuildJobListSelect(
                    "DiscographyJobs",
                    "discography",
                    sourceOrder: 0,
                    filterStatus: normalizedStatus != null,
                    knownStatus: knownStatus));
            }

            if (normalizedType == null || normalizedType == "label_crate")
            {
                selects.Add(BuildJobListSelect(
                    "LabelCrateJobs",
                    "label_crate",
                    sourceOrder: 1,
                    filterStatus: normalizedStatus != null,
                    knownStatus: knownStatus));
            }

            if (selects.Count == 0 || limit <= 0)
            {
                return new Jobs.JobListPage(Array.Empty<Jobs.JobListItem>(), 0);
            }

            var unionSql = string.Join(" UNION ALL ", selects);
            using var conn = GetConnection();
            using var countCommand = conn.CreateCommand();
            countCommand.CommandText = $"SELECT COUNT(*) FROM ({unionSql})";
            if (knownStatus)
            {
                countCommand.Parameters.AddWithValue("@status", normalizedStatus);
            }

            var total = Convert.ToInt32(await countCommand.ExecuteScalarAsync(cancellationToken).ConfigureAwait(false));
            if (total == 0 || offset >= total)
            {
                return new Jobs.JobListPage(Array.Empty<Jobs.JobListItem>(), total);
            }

            var direction = descending ? "DESC" : "ASC";
            var orderBy = normalizedSort switch
            {
                "status" => $"status_value {direction}, source_order, created_at DESC",
                "created_at" or "created" => $"created_at {direction}, source_order",
                "id" => $"job_id {direction}, source_order, created_at DESC",
                null => "created_at DESC, source_order",
                _ => "source_order, created_at DESC",
            };

            using var pageCommand = conn.CreateCommand();
            pageCommand.CommandText = $"""
                SELECT
                    job_id,
                    job_type,
                    status_value,
                    created_at,
                    total_releases,
                    completed_releases,
                    failed_releases
                FROM ({unionSql})
                ORDER BY {orderBy}
                LIMIT @limit OFFSET @offset
                """;
            pageCommand.Parameters.AddWithValue("@limit", limit);
            pageCommand.Parameters.AddWithValue("@offset", Math.Max(0, offset));
            if (knownStatus)
            {
                pageCommand.Parameters.AddWithValue("@status", normalizedStatus);
            }

            var items = new List<Jobs.JobListItem>();
            await using var reader = await pageCommand.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                items.Add(new Jobs.JobListItem(
                    Id: reader.GetString(0).Trim(),
                    Type: reader.GetString(1),
                    Status: reader.GetString(2),
                    CreatedAt: DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(3)),
                    TotalReleases: reader.GetInt32(4),
                    CompletedReleases: reader.GetInt32(5),
                    FailedReleases: reader.GetInt32(6)));
            }

            return new Jobs.JobListPage(items, total);
        }

        private static string BuildJobListSelect(
            string table,
            string type,
            int sourceOrder,
            bool filterStatus,
            bool knownStatus)
        {
            var statusExpression = """
                CASE LOWER(status)
                    WHEN 'pending' THEN 'pending'
                    WHEN 'running' THEN 'running'
                    WHEN 'completed' THEN 'completed'
                    WHEN 'failed' THEN 'failed'
                    ELSE 'unknown'
                END
                """;
            var where = !filterStatus
                ? string.Empty
                : knownStatus
                    ? "WHERE LOWER(status) = @status"
                    : "WHERE LOWER(status) IS NULL OR LOWER(status) NOT IN ('pending', 'running', 'completed', 'failed')";
            return $"""
                SELECT
                    job_id,
                    '{type}' AS job_type,
                    {statusExpression} AS status_value,
                    created_at,
                    COALESCE(total_releases, 0) AS total_releases,
                    COALESCE(completed_releases, 0) AS completed_releases,
                    COALESCE(failed_releases, 0) AS failed_releases,
                    {sourceOrder} AS source_order
                FROM {table}
                {where}
                """;
        }

        /// <inheritdoc/>
        public async Task UpsertDiscographyJobAsync(Jobs.DiscographyJob job, CancellationToken cancellationToken = default)
        {
            if (job == null || string.IsNullOrWhiteSpace(job.JobId))
            {
                return;
            }

            job.JobId = job.JobId.Trim();
            job.ArtistId = job.ArtistId?.Trim() ?? string.Empty;
            job.ArtistName = job.ArtistName?.Trim() ?? string.Empty;
            job.TargetDirectory = job.TargetDirectory?.Trim() ?? string.Empty;
            job.ReleaseJobIds = job.ReleaseJobIds
                .Where(id => !string.IsNullOrWhiteSpace(id))
                .Select(id => id.Trim())
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToList();
            job.ReleaseIds = job.ReleaseIds
                .Where(id => !string.IsNullOrWhiteSpace(id))
                .Select(id => id.Trim())
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToList();

            var json = JsonSerializer.Serialize(job);

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                INSERT INTO DiscographyJobs (job_id, artist_id, artist_name, profile, target_directory, total_releases, completed_releases, failed_releases, status, created_at, json_data)
                VALUES (@job_id, @artist_id, @artist_name, @profile, @target_directory, @total_releases, @completed_releases, @failed_releases, @status, @created_at, @json_data)
                ON CONFLICT(job_id) DO UPDATE SET
                    artist_id = excluded.artist_id,
                    artist_name = excluded.artist_name,
                    profile = excluded.profile,
                    target_directory = excluded.target_directory,
                    total_releases = excluded.total_releases,
                    completed_releases = excluded.completed_releases,
                    failed_releases = excluded.failed_releases,
                    status = excluded.status,
                    json_data = excluded.json_data";

            cmd.Parameters.AddWithValue("@job_id", job.JobId);
            cmd.Parameters.AddWithValue("@artist_id", job.ArtistId ?? string.Empty);
            cmd.Parameters.AddWithValue("@artist_name", job.ArtistName ?? string.Empty);
            cmd.Parameters.AddWithValue("@profile", job.Profile.ToString());
            cmd.Parameters.AddWithValue("@target_directory", job.TargetDirectory ?? string.Empty);
            cmd.Parameters.AddWithValue("@total_releases", job.TotalReleases);
            cmd.Parameters.AddWithValue("@completed_releases", job.CompletedReleases);
            cmd.Parameters.AddWithValue("@failed_releases", job.FailedReleases);
            cmd.Parameters.AddWithValue("@status", job.Status.ToString());
            cmd.Parameters.AddWithValue("@created_at", job.CreatedAt.ToUnixTimeSeconds());
            cmd.Parameters.AddWithValue("@json_data", json);

            await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
        }

        /// <inheritdoc/>
        public async Task<List<DiscographyReleaseJobStatus>> GetDiscographyReleaseJobsAsync(string jobId, CancellationToken cancellationToken = default)
        {
            var list = new List<DiscographyReleaseJobStatus>();
            jobId = jobId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(jobId))
            {
                return list;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT release_id, status
                FROM DiscographyReleaseJobs
                WHERE discography_job_id = @job_id";
            cmd.Parameters.AddWithValue("@job_id", jobId);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                var releaseId = reader.GetString(0).Trim();
                if (string.IsNullOrWhiteSpace(releaseId))
                {
                    continue;
                }

                var statusText = reader.GetString(1);
                var status = Enum.TryParse<JobStatus>(statusText, ignoreCase: true, out var s) ? s : JobStatus.Pending;
                list.Add(new DiscographyReleaseJobStatus
                {
                    ReleaseId = releaseId,
                    Status = status,
                });
            }

            return list;
        }

        /// <inheritdoc/>
        public async Task UpsertDiscographyReleaseJobsAsync(string jobId, IEnumerable<DiscographyReleaseJobStatus> releases, CancellationToken cancellationToken = default)
        {
            jobId = jobId?.Trim() ?? string.Empty;
            var normalized = NormalizeReleaseJobs(releases);
            if (string.IsNullOrWhiteSpace(jobId) || normalized.Count == 0)
            {
                return;
            }

            using var conn = GetConnection();
            using var tx = conn.BeginTransaction();
            await UpsertReleaseJobsInBatchesAsync(
                conn,
                tx,
                "DiscographyReleaseJobs",
                "discography_job_id",
                jobId,
                normalized,
                cancellationToken).ConfigureAwait(false);
            tx.Commit();
        }

        /// <inheritdoc/>
        public Task SetDiscographyReleaseJobStatusAsync(string jobId, string releaseId, JobStatus status, CancellationToken cancellationToken = default)
        {
            return UpsertDiscographyReleaseJobsAsync(jobId, new[]
            {
                new DiscographyReleaseJobStatus
                {
                    ReleaseId = releaseId,
                    Status = status,
                },
            }, cancellationToken);
        }

        /// <inheritdoc/>
        public async Task<IReadOnlyList<LabelPresence>> GetLabelPresenceAsync(CancellationToken cancellationToken = default)
        {
            var results = new List<LabelPresence>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT TRIM(metadata_label) AS metadata_label, COUNT(*) AS cnt
                FROM AlbumTargets
                WHERE metadata_label IS NOT NULL AND TRIM(metadata_label) <> ''
                GROUP BY TRIM(metadata_label)
                ORDER BY cnt DESC, metadata_label";

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                var label = reader.GetString(0).Trim();
                if (!seen.Add(label))
                {
                    continue;
                }

                results.Add(new LabelPresence
                {
                    Label = label,
                    ReleaseCount = reader.GetInt32(1),
                });
            }

            return results;
        }

        /// <inheritdoc/>
        public async Task<IReadOnlyList<string>> GetReleaseIdsByLabelAsync(string labelNameOrId, int limit, CancellationToken cancellationToken = default)
        {
            var results = new List<string>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            labelNameOrId = labelNameOrId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(labelNameOrId) || limit <= 0)
            {
                return results;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT TRIM(release_id)
                FROM AlbumTargets
                WHERE (TRIM(metadata_label) = @label COLLATE NOCASE OR TRIM(discogs_release_id) = @label COLLATE NOCASE)
                ORDER BY created_at DESC
                LIMIT @limit";
            cmd.Parameters.AddWithValue("@label", labelNameOrId);
            cmd.Parameters.AddWithValue("@limit", limit);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                var releaseId = reader.GetString(0).Trim();
                if (!string.IsNullOrWhiteSpace(releaseId) && seen.Add(releaseId))
                {
                    results.Add(releaseId);
                }
            }

            return results;
        }

        // ========== Traffic Accounting ==========

        /// <inheritdoc/>
        public async Task<Models.TrafficTotals> GetTrafficTotalsAsync(CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT overlay_upload_bytes, overlay_download_bytes, soulseek_upload_bytes, soulseek_download_bytes FROM TrafficStats WHERE key = 'global'";

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            if (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                return new Models.TrafficTotals
                {
                    OverlayUploadBytes = reader.GetInt64(0),
                    OverlayDownloadBytes = reader.GetInt64(1),
                    SoulseekUploadBytes = reader.GetInt64(2),
                    SoulseekDownloadBytes = reader.GetInt64(3),
                };
            }

            return new Models.TrafficTotals();
        }

        /// <inheritdoc/>
        public async Task AddTrafficAsync(long overlayUpload, long overlayDownload, long soulseekUpload, long soulseekDownload, CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                INSERT INTO TrafficStats (key, overlay_upload_bytes, overlay_download_bytes, soulseek_upload_bytes, soulseek_download_bytes, updated_at)
                VALUES ('global', @ou, @od, @su, @sd, @updated)
                ON CONFLICT(key) DO UPDATE SET
                    overlay_upload_bytes = TrafficStats.overlay_upload_bytes + @ou,
                    overlay_download_bytes = TrafficStats.overlay_download_bytes + @od,
                    soulseek_upload_bytes = TrafficStats.soulseek_upload_bytes + @su,
                    soulseek_download_bytes = TrafficStats.soulseek_download_bytes + @sd,
                    updated_at = @updated;
            ";

            var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            cmd.Parameters.AddWithValue("@ou", overlayUpload);
            cmd.Parameters.AddWithValue("@od", overlayDownload);
            cmd.Parameters.AddWithValue("@su", soulseekUpload);
            cmd.Parameters.AddWithValue("@sd", soulseekDownload);
            cmd.Parameters.AddWithValue("@updated", now);

            await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
        }

        // ========== Warm Cache Popularity ==========

        /// <inheritdoc/>
        public Task IncrementPopularityAsync(string contentId, CancellationToken cancellationToken = default)
            => IncrementPopularitiesAsync(new[] { contentId }, cancellationToken);

        /// <inheritdoc/>
        public async Task IncrementPopularitiesAsync(IEnumerable<string> contentIds, CancellationToken cancellationToken = default)
        {
            var normalized = contentIds
                .Where(contentId => !string.IsNullOrWhiteSpace(contentId))
                .Select(contentId => contentId.Trim())
                .ToArray();
            if (normalized.Length == 0)
            {
                return;
            }

            using var conn = GetConnection();
            using var transaction = conn.BeginTransaction();
            await UpsertPopularityInBatchesAsync(conn, transaction, normalized, cancellationToken).ConfigureAwait(false);
            transaction.Commit();
        }

        internal static async Task<int> UpsertPopularityInBatchesAsync(
            SqliteConnection connection,
            SqliteTransaction transaction,
            IEnumerable<string> contentIds,
            CancellationToken cancellationToken)
        {
            var normalized = contentIds
                .Where(contentId => !string.IsNullOrWhiteSpace(contentId))
                .Select(contentId => contentId.Trim())
                .GroupBy(contentId => contentId, StringComparer.Ordinal)
                .Select(group => (ContentId: group.Key, Hits: group.LongCount()))
                .ToArray();
            var commandCount = 0;
            var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();

            foreach (var batch in normalized.Chunk(WarmCachePopularityUpsertBatchSize))
            {
                using var cmd = connection.CreateCommand();
                cmd.Transaction = transaction;
                var values = batch.Select((_, index) => $"(@content_id{index}, @hits{index}, @now)");
                cmd.CommandText = $"""
                    INSERT INTO WarmCachePopularity (content_id, hits, last_updated)
                    VALUES {string.Join(", ", values)}
                    ON CONFLICT(content_id) DO UPDATE SET
                        hits = WarmCachePopularity.hits + excluded.hits,
                        last_updated = excluded.last_updated
                    """;
                cmd.Parameters.AddWithValue("@now", now);
                for (var index = 0; index < batch.Length; index++)
                {
                    cmd.Parameters.AddWithValue($"@content_id{index}", batch[index].ContentId);
                    cmd.Parameters.AddWithValue($"@hits{index}", batch[index].Hits);
                }

                await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
                commandCount++;
            }

            return commandCount;
        }

        /// <inheritdoc/>
        public async Task<IReadOnlyList<(string ContentId, long Hits)>> GetTopPopularAsync(int limit, long minHits = 1, CancellationToken cancellationToken = default)
        {
            var results = new List<(string, long)>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            if (limit <= 0)
            {
                return results;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT content_id, hits
                FROM WarmCachePopularity
                WHERE hits >= @minHits
                ORDER BY hits DESC, last_updated DESC
                LIMIT @limit;
            ";
            cmd.Parameters.AddWithValue("@minHits", minHits);
            cmd.Parameters.AddWithValue("@limit", limit);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                var cid = reader.GetString(0).Trim();
                var hits = reader.GetInt64(1);
                if (!string.IsNullOrWhiteSpace(cid) && seen.Add(cid))
                {
                    results.Add((cid, hits));
                }
            }

            return results;
        }

        // ========== Warm Cache Entries ==========

        /// <inheritdoc/>
        public async Task UpsertWarmCacheEntryAsync(Models.WarmCacheEntry entry, CancellationToken cancellationToken = default)
        {
            if (entry == null || string.IsNullOrWhiteSpace(entry.ContentId))
            {
                return;
            }

            entry.ContentId = entry.ContentId.Trim();
            entry.Path = entry.Path?.Trim() ?? string.Empty;

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                INSERT INTO WarmCacheEntries (content_id, path, size_bytes, pinned, last_accessed)
                VALUES (@cid, @path, @size, @pinned, @accessed)
                ON CONFLICT(content_id) DO UPDATE SET
                    path = excluded.path,
                    size_bytes = excluded.size_bytes,
                    pinned = excluded.pinned,
                    last_accessed = excluded.last_accessed;
            ";
            cmd.Parameters.AddWithValue("@cid", entry.ContentId);
            cmd.Parameters.AddWithValue("@path", entry.Path);
            cmd.Parameters.AddWithValue("@size", entry.SizeBytes);
            cmd.Parameters.AddWithValue("@pinned", entry.Pinned ? 1 : 0);
            cmd.Parameters.AddWithValue("@accessed", entry.LastAccessed > 0 ? entry.LastAccessed : DateTimeOffset.UtcNow.ToUnixTimeSeconds());

            await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
        }

        /// <inheritdoc/>
        public async Task DeleteWarmCacheEntryAsync(string contentId, CancellationToken cancellationToken = default)
        {
            contentId = contentId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(contentId))
            {
                return;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "DELETE FROM WarmCacheEntries WHERE content_id = @cid";
            cmd.Parameters.AddWithValue("@cid", contentId);
            await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
        }

        /// <inheritdoc/>
        public async Task<Models.WarmCacheEntry?> GetWarmCacheEntryAsync(string contentId, CancellationToken cancellationToken = default)
        {
            contentId = contentId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(contentId))
            {
                return null;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT content_id, path, size_bytes, pinned, last_accessed FROM WarmCacheEntries WHERE content_id = @cid";
            cmd.Parameters.AddWithValue("@cid", contentId);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            if (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                return ReadWarmCacheEntry(reader);
            }

            return null;
        }

        /// <inheritdoc/>
        public async Task<bool> TouchWarmCacheEntryAsync(
            string contentId,
            long lastAccessed,
            CancellationToken cancellationToken = default)
        {
            contentId = contentId?.Trim() ?? string.Empty;
            if (contentId.Length == 0)
            {
                return false;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = """
                UPDATE WarmCacheEntries
                SET last_accessed = @last_accessed
                WHERE content_id = @content_id
                """;
            cmd.Parameters.AddWithValue("@last_accessed", lastAccessed);
            cmd.Parameters.AddWithValue("@content_id", contentId);
            return await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false) > 0;
        }

        /// <inheritdoc/>
        public async Task<IReadOnlyList<Models.WarmCacheEntry>> ListWarmCacheEntriesAsync(CancellationToken cancellationToken = default)
        {
            var list = new List<Models.WarmCacheEntry>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT content_id, path, size_bytes, pinned, last_accessed FROM WarmCacheEntries ORDER BY last_accessed DESC";

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                var entry = ReadWarmCacheEntry(reader);
                if (!string.IsNullOrWhiteSpace(entry.ContentId) && seen.Add(entry.ContentId))
                {
                    list.Add(entry);
                }
            }

            return list;
        }

        /// <inheritdoc/>
        public async Task<long> GetWarmCacheTotalSizeAsync(CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT SUM(size_bytes) FROM WarmCacheEntries";

            var result = await cmd.ExecuteScalarAsync(cancellationToken).ConfigureAwait(false);
            if (result == null || result is DBNull)
            {
                return 0;
            }

            return Convert.ToInt64(result);
        }

        /// <inheritdoc/>
        public async Task<int> EvictWarmCacheEntriesAsync(long maxBytes, CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = """
                WITH totals AS (
                    SELECT COALESCE(SUM(size_bytes), 0) AS total_bytes
                    FROM WarmCacheEntries
                ),
                candidates AS (
                    SELECT
                        content_id,
                        COALESCE(SUM(size_bytes) OVER (
                            ORDER BY last_accessed, content_id COLLATE NOCASE
                            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                        ), 0) AS reclaimed_before
                    FROM WarmCacheEntries
                    WHERE pinned = 0
                )
                DELETE FROM WarmCacheEntries
                WHERE content_id IN (
                    SELECT candidates.content_id
                    FROM candidates
                    CROSS JOIN totals
                    WHERE totals.total_bytes > @max_bytes
                      AND candidates.reclaimed_before < totals.total_bytes - @max_bytes
                )
                """;
            cmd.Parameters.AddWithValue("@max_bytes", maxBytes);
            return await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
        }

        private static Models.WarmCacheEntry ReadWarmCacheEntry(SqliteDataReader reader)
        {
            return new Models.WarmCacheEntry
            {
                ContentId = reader.GetString(0).Trim(),
                Path = reader.GetString(1).Trim(),
                SizeBytes = reader.GetInt64(2),
                Pinned = !reader.IsDBNull(3) && reader.GetInt32(3) == 1,
                LastAccessed = reader.GetInt64(4),
            };
        }

        // ========== Label Crate Jobs ==========

        /// <inheritdoc/>
        public async Task<LabelCrateJob?> GetLabelCrateJobAsync(string jobId, CancellationToken cancellationToken = default)
        {
            jobId = jobId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(jobId))
            {
                return null;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT job_id, label_id, label_name, limit_count, total_releases, completed_releases, failed_releases, status, created_at, json_data
                FROM LabelCrateJobs
                WHERE job_id = @job_id";
            cmd.Parameters.AddWithValue("@job_id", jobId);

            await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            if (!await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                return null;
            }

            var json = reader.IsDBNull(9) ? null : reader.GetString(9);

            try
            {
                if (!string.IsNullOrWhiteSpace(json))
                {
                    var deserialized = JsonSerializer.Deserialize<LabelCrateJob>(json, CaseInsensitiveJson);
                    if (deserialized != null)
                    {
                        return NormalizeLabelCrateJob(deserialized);
                    }
                }
            }
            catch (Exception ex)
            {
                log.Warning(ex, "[HashDb] Failed to deserialize label crate job {JobId}",
                    LoggingSanitizer.SanitizeExternalIdentifier(jobId));
            }

            var statusText = reader.IsDBNull(7) ? null : reader.GetString(7);
            return NormalizeLabelCrateJob(new LabelCrateJob
            {
                JobId = reader.GetString(0).Trim(),
                LabelId = reader.IsDBNull(1) ? string.Empty : reader.GetString(1).Trim(),
                LabelName = reader.IsDBNull(2) ? string.Empty : reader.GetString(2).Trim(),
                Limit = reader.IsDBNull(3) ? 0 : reader.GetInt32(3),
                TotalReleases = reader.IsDBNull(4) ? 0 : reader.GetInt32(4),
                CompletedReleases = reader.IsDBNull(5) ? 0 : reader.GetInt32(5),
                FailedReleases = reader.IsDBNull(6) ? 0 : reader.GetInt32(6),
                Status = Enum.TryParse<Jobs.JobStatus>(statusText, ignoreCase: true, out var status)
                    ? status
                    : Jobs.JobStatus.Pending,
                CreatedAt = reader.IsDBNull(8) ? DateTimeOffset.UtcNow : DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(8)),
            });
        }

        /// <inheritdoc/>
        public async Task<IReadOnlyList<LabelCrateJob>> ListLabelCrateJobsAsync(CancellationToken cancellationToken = default)
        {
            var results = new List<LabelCrateJob>();

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT job_id, label_id, label_name, limit_count, total_releases, completed_releases, failed_releases, status, created_at, json_data
                FROM LabelCrateJobs
                ORDER BY created_at DESC";

            await using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                var json = reader.IsDBNull(9) ? null : reader.GetString(9);
                LabelCrateJob? job = null;

                if (!string.IsNullOrWhiteSpace(json))
                {
                    try
                    {
                        job = JsonSerializer.Deserialize<LabelCrateJob>(json, CaseInsensitiveJson);
                    }
                    catch (Exception ex)
                    {
                        log.Warning(ex, "[HashDb] Failed to deserialize label crate job from list row");
                    }
                }

                if (job == null)
                {
                    var statusText = reader.IsDBNull(7) ? null : reader.GetString(7);
                    job = new LabelCrateJob
                    {
                        JobId = reader.GetString(0).Trim(),
                        LabelId = reader.IsDBNull(1) ? string.Empty : reader.GetString(1).Trim(),
                        LabelName = reader.IsDBNull(2) ? string.Empty : reader.GetString(2).Trim(),
                        Limit = reader.IsDBNull(3) ? 0 : reader.GetInt32(3),
                        TotalReleases = reader.IsDBNull(4) ? 0 : reader.GetInt32(4),
                        CompletedReleases = reader.IsDBNull(5) ? 0 : reader.GetInt32(5),
                        FailedReleases = reader.IsDBNull(6) ? 0 : reader.GetInt32(6),
                        Status = Enum.TryParse<Jobs.JobStatus>(statusText, ignoreCase: true, out var status)
                            ? status
                            : Jobs.JobStatus.Pending,
                        CreatedAt = reader.IsDBNull(8) ? DateTimeOffset.UtcNow : DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(8)),
                    };
                }

                results.Add(NormalizeLabelCrateJob(job));
            }

            return results;
        }

        /// <inheritdoc/>
        public async Task UpsertLabelCrateJobAsync(LabelCrateJob job, CancellationToken cancellationToken = default)
        {
            if (job == null || string.IsNullOrWhiteSpace(job.JobId))
            {
                return;
            }

            job.JobId = job.JobId.Trim();
            job.LabelId = job.LabelId?.Trim() ?? string.Empty;
            job.LabelName = job.LabelName?.Trim() ?? string.Empty;
            job.ReleaseIds = job.ReleaseIds
                .Where(id => !string.IsNullOrWhiteSpace(id))
                .Select(id => id.Trim())
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToList();

            var json = JsonSerializer.Serialize(job);

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                INSERT INTO LabelCrateJobs (job_id, label_id, label_name, limit_count, total_releases, completed_releases, failed_releases, status, created_at, json_data)
                VALUES (@job_id, @label_id, @label_name, @limit_count, @total_releases, @completed_releases, @failed_releases, @status, @created_at, @json_data)
                ON CONFLICT(job_id) DO UPDATE SET
                    label_id = excluded.label_id,
                    label_name = excluded.label_name,
                    limit_count = excluded.limit_count,
                    total_releases = excluded.total_releases,
                    completed_releases = excluded.completed_releases,
                    failed_releases = excluded.failed_releases,
                    status = excluded.status,
                    json_data = excluded.json_data";

            cmd.Parameters.AddWithValue("@job_id", job.JobId);
            cmd.Parameters.AddWithValue("@label_id", (object?)job.LabelId ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@label_name", job.LabelName ?? string.Empty);
            cmd.Parameters.AddWithValue("@limit_count", job.Limit);
            cmd.Parameters.AddWithValue("@total_releases", job.TotalReleases);
            cmd.Parameters.AddWithValue("@completed_releases", job.CompletedReleases);
            cmd.Parameters.AddWithValue("@failed_releases", job.FailedReleases);
            cmd.Parameters.AddWithValue("@status", job.Status.ToString());
            cmd.Parameters.AddWithValue("@created_at", job.CreatedAt.ToUnixTimeSeconds());
            cmd.Parameters.AddWithValue("@json_data", json);

            await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
        }

        /// <inheritdoc/>
        public async Task<List<DiscographyReleaseJobStatus>> GetLabelCrateReleaseJobsAsync(string jobId, CancellationToken cancellationToken = default)
        {
            var list = new List<DiscographyReleaseJobStatus>();
            jobId = jobId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(jobId))
            {
                return list;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT release_id, status
                FROM LabelCrateReleaseJobs
                WHERE label_crate_job_id = @job_id";
            cmd.Parameters.AddWithValue("@job_id", jobId);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                var releaseId = reader.GetString(0);
                var statusText = reader.GetString(1);
                var status = Enum.TryParse<JobStatus>(statusText, ignoreCase: true, out var s) ? s : JobStatus.Pending;
                list.Add(new DiscographyReleaseJobStatus
                {
                    ReleaseId = releaseId,
                    Status = status,
                });
            }

            return list;
        }

        /// <inheritdoc/>
        public async Task UpsertLabelCrateReleaseJobsAsync(string jobId, IEnumerable<DiscographyReleaseJobStatus> releases, CancellationToken cancellationToken = default)
        {
            jobId = jobId?.Trim() ?? string.Empty;
            var normalized = NormalizeReleaseJobs(releases);
            if (string.IsNullOrWhiteSpace(jobId) || normalized.Count == 0)
            {
                return;
            }

            using var conn = GetConnection();
            using var tx = conn.BeginTransaction();
            await UpsertReleaseJobsInBatchesAsync(
                conn,
                tx,
                "LabelCrateReleaseJobs",
                "label_crate_job_id",
                jobId,
                normalized,
                cancellationToken).ConfigureAwait(false);
            tx.Commit();
        }

        private static List<DiscographyReleaseJobStatus> NormalizeReleaseJobs(IEnumerable<DiscographyReleaseJobStatus>? releases)
        {
            if (releases == null)
            {
                return new List<DiscographyReleaseJobStatus>();
            }

            return releases
                .Where(release => release != null && !string.IsNullOrWhiteSpace(release.ReleaseId))
                .Select(release => new DiscographyReleaseJobStatus
                {
                    ReleaseId = release.ReleaseId.Trim(),
                    Status = release.Status,
                })
                .ToList();
        }

        private static async Task<int> UpsertReleaseJobsInBatchesAsync(
            SqliteConnection connection,
            SqliteTransaction transaction,
            string tableName,
            string jobIdColumn,
            string jobId,
            IReadOnlyList<DiscographyReleaseJobStatus> releases,
            CancellationToken cancellationToken)
        {
            var commandCount = 0;
            foreach (var batch in releases.Chunk(ReleaseJobUpsertBatchSize))
            {
                using var cmd = connection.CreateCommand();
                cmd.Transaction = transaction;
                var values = batch.Select((_, index) => $"(@job_id, @release_id{index}, @status{index})");
                cmd.CommandText = $"""
                    INSERT INTO {tableName} ({jobIdColumn}, release_id, status)
                    VALUES {string.Join(", ", values)}
                    ON CONFLICT({jobIdColumn}, release_id) DO UPDATE SET
                        status = excluded.status
                    """;
                cmd.Parameters.AddWithValue("@job_id", jobId);
                for (var index = 0; index < batch.Length; index++)
                {
                    cmd.Parameters.AddWithValue($"@release_id{index}", batch[index].ReleaseId);
                    cmd.Parameters.AddWithValue($"@status{index}", batch[index].Status.ToString().ToLowerInvariant());
                }

                await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
                commandCount++;
            }

            return commandCount;
        }

        /// <inheritdoc/>
        public Task SetLabelCrateReleaseJobStatusAsync(string jobId, string releaseId, JobStatus status, CancellationToken cancellationToken = default)
        {
            return UpsertLabelCrateReleaseJobsAsync(jobId, new[]
            {
                new DiscographyReleaseJobStatus
                {
                    ReleaseId = releaseId,
                    Status = status,
                },
            }, cancellationToken);
        }

        /// <inheritdoc/>
        public async Task<ArtistReleaseGraph?> GetArtistReleaseGraphAsync(string artistId, CancellationToken cancellationToken = default)
        {
            artistId = artistId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(artistId))
            {
                return null;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT json_data
                FROM ArtistReleaseGraphs
                WHERE artist_id = @artist_id";
            cmd.Parameters.AddWithValue("@artist_id", artistId);

            var json = await cmd.ExecuteScalarAsync(cancellationToken).ConfigureAwait(false) as string;
            if (string.IsNullOrWhiteSpace(json))
            {
                return null;
            }

            try
            {
                var graph = JsonSerializer.Deserialize<ArtistReleaseGraph>(json, CaseInsensitiveJson);
                if (graph == null || string.IsNullOrWhiteSpace(graph.ArtistId))
                {
                    return null;
                }

                graph.ArtistId = graph.ArtistId.Trim();
                return graph;
            }
            catch (Exception ex)
            {
                log.Warning(ex, "[HashDb] Failed to deserialize release graph for artist {ArtistId}",
                    LoggingSanitizer.SanitizeExternalIdentifier(artistId));
                return null;
            }
        }

        /// <inheritdoc/>
        public async Task UpsertArtistReleaseGraphAsync(ArtistReleaseGraph graph, CancellationToken cancellationToken = default)
        {
            if (graph == null || string.IsNullOrWhiteSpace(graph.ArtistId))
            {
                return;
            }

            graph.ArtistId = graph.ArtistId.Trim();

            var json = JsonSerializer.Serialize(graph);

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                INSERT INTO ArtistReleaseGraphs (artist_id, name, cached_at, expires_at, json_data)
                VALUES (@artist_id, @name, @cached_at, @expires_at, @json_data)
                ON CONFLICT(artist_id) DO UPDATE SET
                    name = excluded.name,
                    cached_at = excluded.cached_at,
                    expires_at = excluded.expires_at,
                    json_data = excluded.json_data";

            cmd.Parameters.AddWithValue("@artist_id", graph.ArtistId);
            cmd.Parameters.AddWithValue("@name", graph.Name ?? string.Empty);
            cmd.Parameters.AddWithValue("@cached_at", graph.CachedAt.ToUnixTimeSeconds());
            cmd.Parameters.AddWithValue("@expires_at", graph.ExpiresAt?.ToUnixTimeSeconds() ?? (object)DBNull.Value);
            cmd.Parameters.AddWithValue("@json_data", json);

            await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
        }

        private static Jobs.DiscographyJob NormalizeDiscographyJob(Jobs.DiscographyJob job)
        {
            job.JobId = job.JobId?.Trim() ?? string.Empty;
            job.ArtistId = job.ArtistId?.Trim() ?? string.Empty;
            job.ArtistName = job.ArtistName?.Trim() ?? string.Empty;
            job.TargetDirectory = job.TargetDirectory?.Trim() ?? string.Empty;
            return job;
        }

        private static LabelCrateJob NormalizeLabelCrateJob(LabelCrateJob job)
        {
            job.JobId = job.JobId?.Trim() ?? string.Empty;
            job.LabelId = job.LabelId?.Trim() ?? string.Empty;
            job.LabelName = job.LabelName?.Trim() ?? string.Empty;
            return job;
        }

        /// <inheritdoc/>
        public async Task IncrementHashUseCountAsync(string flacKey, CancellationToken cancellationToken = default)
        {
            flacKey = flacKey?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(flacKey))
            {
                return;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "UPDATE HashDb SET use_count = use_count + 1, last_updated_at = @now WHERE flac_key = @flac_key";
            cmd.Parameters.AddWithValue("@flac_key", flacKey);
            cmd.Parameters.AddWithValue("@now", DateTimeOffset.UtcNow.ToUnixTimeSeconds());
            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        // ========== Mesh Sync ==========

        /// <inheritdoc/>
        public async Task<long> GetLatestSeqIdAsync(CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT COALESCE(MAX(seq_id), 0) FROM HashDb";
            var result = await cmd.ExecuteScalarAsync(cancellationToken);
            return result == DBNull.Value ? 0 : Convert.ToInt64(result);
        }

        /// <inheritdoc/>
        public async Task<IEnumerable<HashDbEntry>> GetEntriesSinceSeqAsync(long sinceSeq, int limit = 1000, CancellationToken cancellationToken = default)
        {
            var entries = new List<HashDbEntry>();
            if (limit <= 0)
            {
                return entries;
            }

            sinceSeq = Math.Max(0, sinceSeq);

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT * FROM HashDb WHERE seq_id > @since_seq ORDER BY seq_id LIMIT @limit";
            cmd.Parameters.AddWithValue("@since_seq", sinceSeq);
            cmd.Parameters.AddWithValue("@limit", limit);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                entries.Add(ReadHashEntry(reader));
            }

            return entries;
        }

        /// <inheritdoc/>
        public async Task<int> MergeEntriesFromMeshAsync(IEnumerable<HashDbEntry> entries, CancellationToken cancellationToken = default)
        {
            var entriesList = entries
                .Select(entry => (Entry: entry, Key: entry.FlacKey?.Trim() ?? string.Empty))
                .ToList();
            log.Information("[HashDb] Merging {Count} entries from mesh", entriesList.Count);

            var requestedKeys = entriesList
                .Select(item => item.Key)
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            var existingByExactKey = new Dictionary<string, (string ByteHash, int UseCount, long LastUpdatedAt)>(StringComparer.Ordinal);
            var existingByVariantKey = new Dictionary<string, (string ByteHash, int UseCount, long LastUpdatedAt)>(StringComparer.Ordinal);
            var readCommandCount = 0;

            using var conn = GetConnection();
            foreach (var batch in requestedKeys.Chunk(MeshMergeLookupBatchSize))
            {
                using var cmd = conn.CreateCommand();
                var parameters = batch.Select((_, index) => $"@key{index}").ToArray();
                cmd.CommandText = $"""
                    SELECT flac_key, variant_id, byte_hash, use_count, last_updated_at
                    FROM HashDb
                    WHERE flac_key IN ({string.Join(", ", parameters)})
                       OR variant_id IN ({string.Join(", ", parameters)})
                    """;
                for (var index = 0; index < batch.Length; index++)
                {
                    cmd.Parameters.AddWithValue(parameters[index], batch[index]);
                }

                using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
                while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
                {
                    var state = (
                        ByteHash: reader.GetString(2),
                        UseCount: reader.IsDBNull(3) ? 1 : reader.GetInt32(3),
                        LastUpdatedAt: reader.GetInt64(4));
                    existingByExactKey[reader.GetString(0)] = state;
                    if (!reader.IsDBNull(1))
                    {
                        var variantId = reader.GetString(1);
                        if (!string.IsNullOrWhiteSpace(variantId) &&
                            (!existingByVariantKey.TryGetValue(variantId, out var previous) ||
                             state.LastUpdatedAt > previous.LastUpdatedAt))
                        {
                            existingByVariantKey[variantId] = state;
                        }
                    }
                }

                readCommandCount++;
            }

            var existingByLookupKey = new Dictionary<string, (string ByteHash, int UseCount, long LastUpdatedAt)>(StringComparer.Ordinal);
            foreach (var key in requestedKeys)
            {
                if (existingByExactKey.TryGetValue(key, out var exact))
                {
                    existingByLookupKey[key] = exact;
                }
                else if (existingByVariantKey.TryGetValue(key, out var variant))
                {
                    existingByLookupKey[key] = variant;
                }
            }

            var candidates = new List<(HashDbEntry Entry, string Key)>();
            var conflicts = 0;
            var skipped = 0;

            foreach (var item in entriesList)
            {
                if (!existingByLookupKey.TryGetValue(item.Key, out var existing))
                {
                    candidates.Add(item);
                    existingByLookupKey[item.Key] = (item.Entry.ByteHash, 1, 0);
                }
                else if (existing.ByteHash != item.Entry.ByteHash)
                {
                    // Conflict: retain the established local entry.
                    log.Warning("[HashDb] Hash conflict for {Key}: local={Local} (uses:{LocalUse}) vs remote={Remote} (uses:{RemoteUse})",
                        LoggingSanitizer.SanitizeHash(item.Key),
                        LoggingSanitizer.SanitizeHash(existing.ByteHash),
                        existing.UseCount,
                        LoggingSanitizer.SanitizeHash(item.Entry.ByteHash),
                        item.Entry.UseCount);
                    conflicts++;
                }
                else
                {
                    skipped++;
                }
            }

            var merged = 0;
            var writeCommandCount = 0;
            if (candidates.Count > 0)
            {
                var lastSeqId = Interlocked.Add(ref currentSeqId, candidates.Count);
                var firstSeqId = lastSeqId - candidates.Count + 1;
                var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
                using var transaction = conn.BeginTransaction();

                for (var offset = 0; offset < candidates.Count; offset += MeshMergeInsertBatchSize)
                {
                    var batch = candidates.GetRange(
                        offset,
                        Math.Min(MeshMergeInsertBatchSize, candidates.Count - offset));
                    using var cmd = conn.CreateCommand();
                    cmd.Transaction = transaction;
                    var values = batch.Select((_, index) =>
                        $"(@flac_key{index}, @byte_hash{index}, @size{index}, @meta_flags{index}, @now, @now, @seq_id{index}, 1)");
                    cmd.CommandText = $"""
                        INSERT INTO HashDb
                            (flac_key, byte_hash, size, meta_flags, first_seen_at, last_updated_at, seq_id, use_count)
                        VALUES {string.Join(", ", values)}
                        ON CONFLICT(flac_key) DO NOTHING
                        """;
                    cmd.Parameters.AddWithValue("@now", now);
                    for (var index = 0; index < batch.Count; index++)
                    {
                        var item = batch[index];
                        cmd.Parameters.AddWithValue($"@flac_key{index}", item.Key);
                        cmd.Parameters.AddWithValue($"@byte_hash{index}", item.Entry.ByteHash);
                        cmd.Parameters.AddWithValue($"@size{index}", item.Entry.Size);
                        cmd.Parameters.AddWithValue($"@meta_flags{index}", item.Entry.MetaFlags ?? (object)DBNull.Value);
                        cmd.Parameters.AddWithValue($"@seq_id{index}", firstSeqId + offset + index);
                        hashCache?.Remove($"hashdb:lookup:{item.Key}");
                    }

                    merged += await cmd.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
                    writeCommandCount++;
                }

                transaction.Commit();
            }

            log.Information("[HashDb] Mesh merge complete with {CommandCount} database commands: {Merged} new, {Conflicts} conflicts, {Skipped} already known",
                readCommandCount + writeCommandCount, merged, conflicts, skipped);

            return merged;
        }

        /// <inheritdoc/>
        public async Task<long> GetPeerLastSeqSeenAsync(string peerId, CancellationToken cancellationToken = default)
        {
            peerId = peerId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(peerId))
            {
                return 0;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT COALESCE(last_seq_seen, 0) FROM MeshPeerState WHERE peer_id = @peer_id";
            cmd.Parameters.AddWithValue("@peer_id", peerId);
            var result = await cmd.ExecuteScalarAsync(cancellationToken);
            return result == null || result == DBNull.Value ? 0 : Convert.ToInt64(result);
        }

        /// <inheritdoc/>
        public async Task UpdatePeerLastSeqSeenAsync(string peerId, long seqId, CancellationToken cancellationToken = default)
        {
            peerId = peerId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(peerId))
            {
                return;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                INSERT INTO MeshPeerState (peer_id, last_seq_seen, last_sync_time)
                VALUES (@peer_id, @seq_id, @now)
                ON CONFLICT(peer_id) DO UPDATE SET last_seq_seen = @seq_id, last_sync_time = @now";
            cmd.Parameters.AddWithValue("@peer_id", peerId);
            cmd.Parameters.AddWithValue("@seq_id", seqId);
            cmd.Parameters.AddWithValue("@now", DateTimeOffset.UtcNow.ToUnixTimeSeconds());
            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        // ========== Backfill ==========

        /// <inheritdoc/>
        public async Task<IEnumerable<FlacInventoryEntry>> GetBackfillCandidatesAsync(int limit = 10, CancellationToken cancellationToken = default)
        {
            var entries = new List<FlacInventoryEntry>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            if (limit <= 0)
            {
                return entries;
            }

            var today = DateTimeOffset.UtcNow.Date;
            var todayUnix = new DateTimeOffset(today).ToUnixTimeSeconds();

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();

            // Get unhashed files from peers who haven't hit their daily backfill limit
            cmd.CommandText = @"
                SELECT f.* FROM FlacInventory f
                JOIN Peers p ON f.peer_id = p.peer_id
                WHERE f.hash_status = 'none'
                  AND (p.backfill_reset_date IS NULL OR p.backfill_reset_date < @today OR p.backfills_today < 50)
                ORDER BY f.discovered_at DESC
                LIMIT @limit";
            cmd.Parameters.AddWithValue("@today", todayUnix);
            cmd.Parameters.AddWithValue("@limit", limit);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                var entry = ReadFlacEntry(reader);
                if (!string.IsNullOrWhiteSpace(entry.FileId) && seen.Add(entry.FileId))
                {
                    entries.Add(entry);
                }
            }

            return entries;
        }

        /// <inheritdoc/>
        public async Task IncrementPeerBackfillCountAsync(string peerId, CancellationToken cancellationToken = default)
        {
            peerId = peerId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(peerId))
            {
                return;
            }

            var today = new DateTimeOffset(DateTimeOffset.UtcNow.Date).ToUnixTimeSeconds();

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                UPDATE Peers SET 
                    backfills_today = CASE WHEN backfill_reset_date = @today THEN backfills_today + 1 ELSE 1 END,
                    backfill_reset_date = @today
                WHERE peer_id = @peer_id";
            cmd.Parameters.AddWithValue("@peer_id", peerId);
            cmd.Parameters.AddWithValue("@today", today);
            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        /// <inheritdoc/>
        public async Task<int> GetPeerBackfillCountTodayAsync(string peerId, CancellationToken cancellationToken = default)
        {
            peerId = peerId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(peerId))
            {
                return 0;
            }

            var today = new DateTimeOffset(DateTimeOffset.UtcNow.Date).ToUnixTimeSeconds();

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                SELECT CASE WHEN backfill_reset_date = @today THEN backfills_today ELSE 0 END
                FROM Peers WHERE peer_id = @peer_id";
            cmd.Parameters.AddWithValue("@peer_id", peerId);
            cmd.Parameters.AddWithValue("@today", today);

            var result = await cmd.ExecuteScalarAsync(cancellationToken);
            return result == null || result == DBNull.Value ? 0 : Convert.ToInt32(result);
        }

        /// <inheritdoc/>
        public async Task<IReadOnlyDictionary<string, int>> GetPeerBackfillCountsTodayAsync(
            IReadOnlyCollection<string> peerIds,
            CancellationToken cancellationToken = default)
        {
            var normalizedPeerIds = peerIds
                .Where(peerId => !string.IsNullOrWhiteSpace(peerId))
                .Select(peerId => peerId.Trim())
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToArray();
            var counts = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            if (normalizedPeerIds.Length == 0)
            {
                return counts;
            }

            var today = new DateTimeOffset(DateTimeOffset.UtcNow.Date).ToUnixTimeSeconds();
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            var parameters = normalizedPeerIds.Select((_, index) => $"@peer_id_{index}").ToArray();
            cmd.CommandText = $@"
                SELECT peer_id,
                       CASE WHEN backfill_reset_date = @today THEN backfills_today ELSE 0 END
                FROM Peers
                WHERE peer_id COLLATE NOCASE IN ({string.Join(", ", parameters)})";
            cmd.Parameters.AddWithValue("@today", today);
            for (var index = 0; index < normalizedPeerIds.Length; index++)
            {
                cmd.Parameters.AddWithValue(parameters[index], normalizedPeerIds[index]);
            }

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                counts[reader.GetString(0)] = reader.GetInt32(1);
            }

            return counts;
        }

        /// <inheritdoc/>
        public async Task ResetDailyBackfillCountersAsync(CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "UPDATE Peers SET backfills_today = 0";
            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        // ========== History Backfill ==========

        /// <inheritdoc/>
        public async Task<int> BackfillFromSearchResponsesAsync(IEnumerable<Search.Response> responses, int maxFiles = int.MaxValue, CancellationToken cancellationToken = default)
        {
            var flacCount = 0;
            var skippedCount = 0;
            var peerIds = new HashSet<string>(StringComparer.Ordinal);

            IEnumerable<FlacInventoryEntry> EnumerateEntries()
            {
                foreach (var response in responses)
                {
                    if (flacCount >= maxFiles)
                    {
                        yield break;
                    }

                    if (string.IsNullOrEmpty(response.Username))
                    {
                        continue;
                    }

                    peerIds.Add(response.Username);
                    foreach (var file in response.Files)
                    {
                        if (cancellationToken.IsCancellationRequested || flacCount >= maxFiles)
                        {
                            yield break;
                        }

                        // Only interested in FLAC files large enough to hash
                        if (!file.Filename.EndsWith(".flac", StringComparison.OrdinalIgnoreCase))
                        {
                            continue;
                        }

                        if (file.Size < HashChunkSize)
                        {
                            skippedCount++;
                            continue;
                        }

                        flacCount++;
                        yield return new FlacInventoryEntry
                        {
                            PeerId = response.Username,
                            Path = file.Filename,
                            Size = file.Size,
                            HashStatusStr = "none",
                        };
                    }
                }
            }

            using var conn = GetConnection();
            using var transaction = conn.BeginTransaction();
            var ingestion = await UpsertFlacEntriesInBatchesAsync(
                conn,
                transaction,
                EnumerateEntries(),
                cancellationToken).ConfigureAwait(false);
            var peerCommandCount = await UpsertPeersInBatchesAsync(
                conn,
                transaction,
                peerIds,
                cancellationToken).ConfigureAwait(false);
            transaction.Commit();

            if (flacCount > 0 || skippedCount > 0)
            {
                log.Information(
                    "[HashDb] Backfilled {Count} FLAC files from search history with {CommandCount} database commands ({Skipped} too small)",
                    flacCount,
                    ingestion.CommandCount + peerCommandCount,
                    skippedCount);
            }

            return flacCount;
        }

        /// <inheritdoc/>
        public async Task<DateTimeOffset?> GetBackfillProgressAsync(CancellationToken cancellationToken = default)
        {
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT value FROM HashDbState WHERE key = 'backfill_progress'";

            var result = await cmd.ExecuteScalarAsync(cancellationToken);
            if (result == null || result == DBNull.Value)
            {
                return null;
            }

            var text = result.ToString()?.Trim();
            if (long.TryParse(text, out var timestamp))
            {
                return DateTimeOffset.FromUnixTimeSeconds(timestamp);
            }

            if (DateTimeOffset.TryParse(text, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal, out var parsed))
            {
                return parsed;
            }

            return null;
        }

        /// <inheritdoc/>
        public async Task SetBackfillProgressAsync(DateTimeOffset oldestProcessed, CancellationToken cancellationToken = default)
        {
            var timestamp = oldestProcessed.ToUnixTimeSeconds();

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                INSERT INTO HashDbState (key, value) VALUES ('backfill_progress', @value)
                ON CONFLICT(key) DO UPDATE SET value = @value";
            cmd.Parameters.AddWithValue("@value", timestamp.ToString());
            await cmd.ExecuteNonQueryAsync(cancellationToken);
        }

        // ========== Helpers ==========
        private static Peer ReadPeer(SqliteDataReader reader)
        {
            return new Peer
            {
                PeerId = reader.GetString(reader.GetOrdinal("peer_id")).Trim(),
                Caps = reader.GetInt32(reader.GetOrdinal("caps")),
                ClientVersion = reader.IsDBNull(reader.GetOrdinal("client_version")) ? null : reader.GetString(reader.GetOrdinal("client_version")).Trim(),
                LastSeen = reader.GetInt64(reader.GetOrdinal("last_seen")),
                LastCapCheck = reader.IsDBNull(reader.GetOrdinal("last_cap_check")) ? null : reader.GetInt64(reader.GetOrdinal("last_cap_check")),
                BackfillsToday = reader.GetInt32(reader.GetOrdinal("backfills_today")),
                BackfillResetDate = reader.IsDBNull(reader.GetOrdinal("backfill_reset_date")) ? null : reader.GetInt64(reader.GetOrdinal("backfill_reset_date")),
            };
        }

        private static FlacInventoryEntry ReadFlacEntry(SqliteDataReader reader)
        {
            var entry = new FlacInventoryEntry
            {
                FileId = reader.GetString(reader.GetOrdinal("file_id")).Trim(),
                PeerId = reader.GetString(reader.GetOrdinal("peer_id")).Trim(),
                Path = reader.GetString(reader.GetOrdinal("path")).Trim(),
                Size = reader.GetInt64(reader.GetOrdinal("size")),
                DiscoveredAt = reader.GetInt64(reader.GetOrdinal("discovered_at")),
                HashStatusStr = reader.IsDBNull(reader.GetOrdinal("hash_status")) ? "none" : reader.GetString(reader.GetOrdinal("hash_status")).Trim(),
                HashValue = reader.IsDBNull(reader.GetOrdinal("hash_value")) ? null : reader.GetString(reader.GetOrdinal("hash_value")).Trim(),
                HashSourceStr = reader.IsDBNull(reader.GetOrdinal("hash_source")) ? null : reader.GetString(reader.GetOrdinal("hash_source")).Trim(),
                FlacAudioMd5 = reader.IsDBNull(reader.GetOrdinal("flac_audio_md5")) ? null : reader.GetString(reader.GetOrdinal("flac_audio_md5")).Trim(),
                SampleRate = reader.IsDBNull(reader.GetOrdinal("sample_rate")) ? null : reader.GetInt32(reader.GetOrdinal("sample_rate")),
                Channels = reader.IsDBNull(reader.GetOrdinal("channels")) ? null : reader.GetInt32(reader.GetOrdinal("channels")),
                BitDepth = reader.IsDBNull(reader.GetOrdinal("bit_depth")) ? null : reader.GetInt32(reader.GetOrdinal("bit_depth")),
                DurationSamples = reader.IsDBNull(reader.GetOrdinal("duration_samples")) ? null : reader.GetInt64(reader.GetOrdinal("duration_samples")),
            };

            // Read new optional columns (may not exist in older DBs)
            TryReadOptionalString(reader, "full_file_hash", v => entry.FullFileHash = v);
            TryReadOptionalInt(reader, "min_block_size", v => entry.MinBlockSize = v);
            TryReadOptionalInt(reader, "max_block_size", v => entry.MaxBlockSize = v);
            TryReadOptionalString(reader, "encoder_info", v => entry.EncoderInfo = v);
            TryReadOptionalString(reader, "album_hash", v => entry.AlbumHash = v);
            TryReadOptionalInt(reader, "probe_fail_count", v => entry.ProbeFailCount = v ?? 0);
            TryReadOptionalString(reader, "probe_fail_reason", v => entry.ProbeFailReason = v);
            TryReadOptionalLong(reader, "last_probe_at", v => entry.LastProbeAt = v);

            return entry;
        }

        private static void TryReadOptionalString(SqliteDataReader reader, string column, Action<string> setter)
        {
            try
            {
                var ordinal = reader.GetOrdinal(column);
                if (!reader.IsDBNull(ordinal))
                {
                    setter(reader.GetString(ordinal).Trim());
                }
            }
            catch (ArgumentOutOfRangeException)
            {
                // Column doesn't exist in this DB version - ignore
            }
        }

        private static void TryReadOptionalInt(SqliteDataReader reader, string column, Action<int?> setter)
        {
            try
            {
                var ordinal = reader.GetOrdinal(column);
                setter(reader.IsDBNull(ordinal) ? null : reader.GetInt32(ordinal));
            }
            catch (ArgumentOutOfRangeException)
            {
                // Column doesn't exist in this DB version - ignore
            }
        }

        private static void TryReadOptionalLong(SqliteDataReader reader, string column, Action<long?> setter)
        {
            try
            {
                var ordinal = reader.GetOrdinal(column);
                setter(reader.IsDBNull(ordinal) ? null : reader.GetInt64(ordinal));
            }
            catch (ArgumentOutOfRangeException)
            {
                // Column doesn't exist in this DB version - ignore
            }
        }

        private static void TryReadOptionalDouble(SqliteDataReader reader, string column, Action<double?> setter)
        {
            try
            {
                var ordinal = reader.GetOrdinal(column);
                setter(reader.IsDBNull(ordinal) ? null : reader.GetDouble(ordinal));
            }
            catch (ArgumentOutOfRangeException)
            {
                // Column doesn't exist in this DB version - ignore
            }
        }

        private static void TryReadOptionalBool(SqliteDataReader reader, string column, Action<bool?> setter)
        {
            try
            {
                var ordinal = reader.GetOrdinal(column);
                if (reader.IsDBNull(ordinal))
                {
                    setter(null);
                }
                else
                {
                    setter(reader.GetBoolean(ordinal));
                }
            }
            catch (ArgumentOutOfRangeException)
            {
                // Column doesn't exist in this DB version - ignore
            }
        }

        private static HashDbEntry ReadHashEntry(SqliteDataReader reader)
        {
            var entry = new HashDbEntry
            {
                FlacKey = reader.GetString(reader.GetOrdinal("flac_key")),
                ByteHash = reader.GetString(reader.GetOrdinal("byte_hash")),
                Size = reader.GetInt64(reader.GetOrdinal("size")),
                MetaFlags = reader.IsDBNull(reader.GetOrdinal("meta_flags")) ? null : reader.GetInt32(reader.GetOrdinal("meta_flags")),
                FirstSeenAt = reader.GetInt64(reader.GetOrdinal("first_seen_at")),
                LastUpdatedAt = reader.GetInt64(reader.GetOrdinal("last_updated_at")),
                SeqId = reader.IsDBNull(reader.GetOrdinal("seq_id")) ? 0 : reader.GetInt64(reader.GetOrdinal("seq_id")),
                UseCount = reader.GetInt32(reader.GetOrdinal("use_count")),
            };

            TryReadOptionalString(reader, "variant_id", v => entry.VariantId = v);
            TryReadOptionalString(reader, "codec", v => entry.Codec = v);
            TryReadOptionalString(reader, "container", v => entry.Container = v);
            TryReadOptionalInt(reader, "sample_rate_hz", v => entry.SampleRateHz = v);
            TryReadOptionalInt(reader, "bit_depth", v => entry.BitDepth = v);
            TryReadOptionalInt(reader, "channels", v => entry.Channels = v);
            TryReadOptionalInt(reader, "duration_ms", v => entry.DurationMs = v);
            TryReadOptionalInt(reader, "bitrate_kbps", v => entry.BitrateKbps = v);
            TryReadOptionalDouble(reader, "quality_score", v => entry.QualityScore = v);
            TryReadOptionalBool(reader, "transcode_suspect", v => entry.TranscodeSuspect = v);
            TryReadOptionalString(reader, "transcode_reason", v => entry.TranscodeReason = v);
            TryReadOptionalDouble(reader, "dynamic_range_dr", v => entry.DynamicRangeDr = v);
            TryReadOptionalDouble(reader, "loudness_lufs", v => entry.LoudnessLufs = v);
            TryReadOptionalBool(reader, "has_clipping", v => entry.HasClipping = v);
            TryReadOptionalString(reader, "encoder_signature", v => entry.EncoderSignature = v);
            TryReadOptionalInt(reader, "seen_count", v => entry.SeenCount = v);
            TryReadOptionalString(reader, "file_sha256", v => entry.FileSha256 = v);
            TryReadOptionalString(reader, "musicbrainz_id", v => entry.MusicBrainzId = v);
            TryReadOptionalString(reader, "audio_fingerprint", v => entry.AudioFingerprint = v);
            TryReadOptionalString(reader, "audio_sketch_hash", v => entry.AudioSketchHash = v);
            TryReadOptionalString(reader, "analyzer_version", v => entry.AnalyzerVersion = v);

            // FLAC-specific
            TryReadOptionalString(reader, "flac_streaminfo_hash42", v => entry.FlacStreamInfoHash42 = v);
            TryReadOptionalString(reader, "flac_pcm_md5", v => entry.FlacPcmMd5 = v);
            TryReadOptionalInt(reader, "flac_min_block_size", v => entry.FlacMinBlockSize = v);
            TryReadOptionalInt(reader, "flac_max_block_size", v => entry.FlacMaxBlockSize = v);
            TryReadOptionalInt(reader, "flac_min_frame_size", v => entry.FlacMinFrameSize = v);
            TryReadOptionalInt(reader, "flac_max_frame_size", v => entry.FlacMaxFrameSize = v);
            TryReadOptionalLong(reader, "flac_total_samples", v => entry.FlacTotalSamples = v);

            // MP3-specific
            TryReadOptionalString(reader, "mp3_stream_hash", v => entry.Mp3StreamHash = v);
            TryReadOptionalString(reader, "mp3_encoder", v => entry.Mp3Encoder = v);
            TryReadOptionalString(reader, "mp3_encoder_preset", v => entry.Mp3EncoderPreset = v);
            TryReadOptionalInt(reader, "mp3_frames_analyzed", v => entry.Mp3FramesAnalyzed = v);

            // Shared lossy spectral metrics
            TryReadOptionalDouble(reader, "effective_bandwidth_hz", v => entry.EffectiveBandwidthHz = v);
            TryReadOptionalDouble(reader, "nominal_lowpass_hz", v => entry.NominalLowpassHz = v);
            TryReadOptionalDouble(reader, "spectral_flatness_score", v => entry.SpectralFlatnessScore = v);
            TryReadOptionalDouble(reader, "hf_energy_ratio", v => entry.HfEnergyRatio = v);

            // Opus-specific
            TryReadOptionalString(reader, "opus_stream_hash", v => entry.OpusStreamHash = v);
            TryReadOptionalInt(reader, "opus_nominal_bitrate_kbps", v => entry.OpusNominalBitrateKbps = v);
            TryReadOptionalString(reader, "opus_application", v => entry.OpusApplication = v);
            TryReadOptionalString(reader, "opus_bandwidth_mode", v => entry.OpusBandwidthMode = v);

            // AAC-specific
            TryReadOptionalString(reader, "aac_stream_hash", v => entry.AacStreamHash = v);
            TryReadOptionalString(reader, "aac_profile", v => entry.AacProfile = v);
            TryReadOptionalBool(reader, "aac_sbr_present", v => entry.AacSbrPresent = v);
            TryReadOptionalBool(reader, "aac_ps_present", v => entry.AacPsPresent = v);
            TryReadOptionalInt(reader, "aac_nominal_bitrate_kbps", v => entry.AacNominalBitrateKbps = v);

            return entry;
        }

        private static AudioVariant? MapEntryToVariant(HashDbEntry? entry)
        {
            if (entry == null)
            {
                return null;
            }

            return new AudioVariant
            {
                VariantId = entry.VariantId ?? entry.FlacKey,
                MusicBrainzRecordingId = entry.MusicBrainzId,
                FlacKey = entry.FlacKey,
                Codec = entry.Codec,
                Container = entry.Container,
                SampleRateHz = entry.SampleRateHz ?? 0,
                BitDepth = entry.BitDepth,
                Channels = entry.Channels ?? 2,
                DurationMs = entry.DurationMs ?? 0,
                BitrateKbps = entry.BitrateKbps ?? 0,
                FileSizeBytes = entry.Size,
                FileSha256 = entry.FileSha256,
                AudioFingerprint = entry.AudioFingerprint,
                AudioSketchHash = entry.AudioSketchHash,
                AnalyzerVersion = entry.AnalyzerVersion,
                QualityScore = entry.QualityScore ?? 0.0,
                TranscodeSuspect = entry.TranscodeSuspect ?? false,
                TranscodeReason = entry.TranscodeReason,
                DynamicRangeDR = entry.DynamicRangeDr,
                LoudnessLUFS = entry.LoudnessLufs,
                HasClipping = entry.HasClipping,
                EncoderSignature = entry.EncoderSignature,
                FirstSeenAt = DateTimeOffset.FromUnixTimeSeconds(entry.FirstSeenAt),
                LastSeenAt = DateTimeOffset.FromUnixTimeSeconds(entry.LastUpdatedAt),
                SeenCount = entry.SeenCount ?? 1,
                FlacStreamInfoHash42 = entry.FlacStreamInfoHash42,
                FlacPcmMd5 = entry.FlacPcmMd5,
                FlacMinBlockSize = entry.FlacMinBlockSize,
                FlacMaxBlockSize = entry.FlacMaxBlockSize,
                FlacMinFrameSize = entry.FlacMinFrameSize,
                FlacMaxFrameSize = entry.FlacMaxFrameSize,
                FlacTotalSamples = entry.FlacTotalSamples,
                Mp3StreamHash = entry.Mp3StreamHash,
                Mp3Encoder = entry.Mp3Encoder,
                Mp3EncoderPreset = entry.Mp3EncoderPreset,
                Mp3FramesAnalyzed = entry.Mp3FramesAnalyzed,
                EffectiveBandwidthHz = entry.EffectiveBandwidthHz,
                NominalLowpassHz = entry.NominalLowpassHz,
                SpectralFlatnessScore = entry.SpectralFlatnessScore,
                HfEnergyRatio = entry.HfEnergyRatio,
                OpusStreamHash = entry.OpusStreamHash,
                OpusNominalBitrateKbps = entry.OpusNominalBitrateKbps,
                OpusApplication = entry.OpusApplication,
                OpusBandwidthMode = entry.OpusBandwidthMode,
                AacStreamHash = entry.AacStreamHash,
                AacProfile = entry.AacProfile,
                AacSbrPresent = entry.AacSbrPresent,
                AacPsPresent = entry.AacPsPresent,
                AacNominalBitrateKbps = entry.AacNominalBitrateKbps,
            };
        }

        private static CanonicalStats ReadCanonicalStats(SqliteDataReader reader)
        {
            var stats = new CanonicalStats
            {
                Id = reader.GetString(reader.GetOrdinal("id")).Trim(),
                MusicBrainzRecordingId = reader.GetString(reader.GetOrdinal("musicbrainz_recording_id")).Trim(),
                CodecProfileKey = reader.GetString(reader.GetOrdinal("codec_profile_key")).Trim(),
                VariantCount = reader.GetInt32(reader.GetOrdinal("variant_count")),
                TotalSeenCount = reader.GetInt32(reader.GetOrdinal("total_seen_count")),
                AvgQualityScore = reader.GetDouble(reader.GetOrdinal("avg_quality_score")),
                MaxQualityScore = reader.GetDouble(reader.GetOrdinal("max_quality_score")),
                PercentTranscodeSuspect = reader.GetDouble(reader.GetOrdinal("percent_transcode_suspect")),
                BestVariantId = reader.IsDBNull(reader.GetOrdinal("best_variant_id")) ? string.Empty : reader.GetString(reader.GetOrdinal("best_variant_id")).Trim(),
                CanonicalityScore = reader.GetDouble(reader.GetOrdinal("canonicality_score")),
                LastUpdated = DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(reader.GetOrdinal("last_updated"))),
            };

            var codecJson = reader.IsDBNull(reader.GetOrdinal("codec_distribution")) ? "{}" : reader.GetString(reader.GetOrdinal("codec_distribution"));
            var bitrateJson = reader.IsDBNull(reader.GetOrdinal("bitrate_distribution")) ? "{}" : reader.GetString(reader.GetOrdinal("bitrate_distribution"));
            var srJson = reader.IsDBNull(reader.GetOrdinal("sample_rate_distribution")) ? "{}" : reader.GetString(reader.GetOrdinal("sample_rate_distribution"));

            stats.CodecDistribution = JsonSerializer.Deserialize<Dictionary<string, int>>(codecJson) ?? new Dictionary<string, int>();
            stats.BitrateDistribution = JsonSerializer.Deserialize<Dictionary<int, int>>(bitrateJson) ?? new Dictionary<int, int>();
            stats.SampleRateDistribution = JsonSerializer.Deserialize<Dictionary<int, int>>(srJson) ?? new Dictionary<int, int>();

            return stats;
        }

        private static LibraryHealth.LibraryHealthScan ReadScan(SqliteDataReader reader)
        {
            return new LibraryHealth.LibraryHealthScan
            {
                ScanId = reader.GetString(reader.GetOrdinal("scan_id")),
                LibraryPath = reader.GetString(reader.GetOrdinal("library_path")),
                StartedAt = DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(reader.GetOrdinal("started_at"))),
                CompletedAt = reader.IsDBNull(reader.GetOrdinal("completed_at")) ? null : DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(reader.GetOrdinal("completed_at"))),
                Status = Enum.TryParse<LibraryHealth.ScanStatus>(reader.GetString(reader.GetOrdinal("status")), true, out var st) ? st : LibraryHealth.ScanStatus.Running,
                FilesScanned = reader.IsDBNull(reader.GetOrdinal("files_scanned")) ? 0 : reader.GetInt32(reader.GetOrdinal("files_scanned")),
                IssuesDetected = reader.IsDBNull(reader.GetOrdinal("issues_detected")) ? 0 : reader.GetInt32(reader.GetOrdinal("issues_detected")),
                ErrorMessage = reader.IsDBNull(reader.GetOrdinal("error_message")) ? string.Empty : reader.GetString(reader.GetOrdinal("error_message")),
            };
        }

        private static LibraryHealth.LibraryIssue ReadIssue(SqliteDataReader reader)
        {
            var issue = new LibraryHealth.LibraryIssue
            {
                IssueId = reader.GetString(reader.GetOrdinal("issue_id")),
                Type = Enum.TryParse<LibraryHealth.LibraryIssueType>(reader.GetString(reader.GetOrdinal("type")), true, out var t) ? t : LibraryHealth.LibraryIssueType.MissingMetadata,
                Severity = Enum.TryParse<LibraryHealth.LibraryIssueSeverity>(reader.GetString(reader.GetOrdinal("severity")), true, out var sev) ? sev : LibraryHealth.LibraryIssueSeverity.Low,
                FilePath = reader.IsDBNull(reader.GetOrdinal("file_path")) ? string.Empty : reader.GetString(reader.GetOrdinal("file_path")),
                MusicBrainzRecordingId = reader.IsDBNull(reader.GetOrdinal("mb_recording_id")) ? string.Empty : reader.GetString(reader.GetOrdinal("mb_recording_id")),
                MusicBrainzReleaseId = reader.IsDBNull(reader.GetOrdinal("mb_release_id")) ? string.Empty : reader.GetString(reader.GetOrdinal("mb_release_id")),
                Artist = reader.IsDBNull(reader.GetOrdinal("artist")) ? string.Empty : reader.GetString(reader.GetOrdinal("artist")),
                Album = reader.IsDBNull(reader.GetOrdinal("album")) ? string.Empty : reader.GetString(reader.GetOrdinal("album")),
                Title = reader.IsDBNull(reader.GetOrdinal("title")) ? string.Empty : reader.GetString(reader.GetOrdinal("title")),
                Reason = reader.IsDBNull(reader.GetOrdinal("reason")) ? string.Empty : reader.GetString(reader.GetOrdinal("reason")),
                CanAutoFix = !reader.IsDBNull(reader.GetOrdinal("can_auto_fix")) && reader.GetBoolean(reader.GetOrdinal("can_auto_fix")),
                SuggestedAction = reader.IsDBNull(reader.GetOrdinal("suggested_action")) ? string.Empty : reader.GetString(reader.GetOrdinal("suggested_action")),
                RemediationJobId = reader.IsDBNull(reader.GetOrdinal("remediation_job_id")) ? string.Empty : reader.GetString(reader.GetOrdinal("remediation_job_id")),
                Status = Enum.TryParse<LibraryHealth.LibraryIssueStatus>(reader.GetString(reader.GetOrdinal("status")), true, out var st) ? st : LibraryHealth.LibraryIssueStatus.Detected,
                DetectedAt = DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(reader.GetOrdinal("detected_at"))),
                ResolvedAt = reader.IsDBNull(reader.GetOrdinal("resolved_at")) ? null : DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(reader.GetOrdinal("resolved_at"))),
                ResolvedBy = reader.IsDBNull(reader.GetOrdinal("resolved_by")) ? string.Empty : reader.GetString(reader.GetOrdinal("resolved_by")),
            };

            var metaJson = reader.IsDBNull(reader.GetOrdinal("metadata")) ? "{}" : reader.GetString(reader.GetOrdinal("metadata"));
            issue.Metadata = JsonSerializer.Deserialize<Dictionary<string, object>>(metaJson) ?? new Dictionary<string, object>();
            return issue;
        }

        public Task<List<Transfers.MultiSource.Metrics.PeerPerformanceMetrics>> GetAllPeerMetricsAsync(CancellationToken cancellationToken = default)
        {
            var list = new List<Transfers.MultiSource.Metrics.PeerPerformanceMetrics>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT * FROM PeerMetrics";

            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                var metrics = ReadPeerMetrics(reader);
                if (!string.IsNullOrWhiteSpace(metrics.PeerId) && seen.Add(metrics.PeerId))
                {
                    list.Add(metrics);
                }
            }

            return Task.FromResult(list);
        }

        /// <inheritdoc/>
        public async Task<List<Transfers.MultiSource.Metrics.PeerPerformanceMetrics>> GetTopPeerMetricsAsync(int limit, CancellationToken cancellationToken = default)
        {
            var list = new List<Transfers.MultiSource.Metrics.PeerPerformanceMetrics>();
            if (limit <= 0)
            {
                return list;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = """
                WITH first_metrics AS (
                    SELECT MIN(rowid) AS source_rowid
                    FROM PeerMetrics
                    GROUP BY peer_id COLLATE NOCASE
                ), costed_metrics AS (
                    SELECT
                        PeerMetrics.*,
                        PeerMetrics.rowid AS source_rowid,
                        (CASE
                            WHEN COALESCE(throughput_avg_bps, 0) > 0
                                THEN 1.0 / (throughput_avg_bps / (1024.0 * 1024.0))
                            ELSE 1000.0
                        END)
                        + (CASE
                            WHEN COALESCE(chunks_requested, 0) > 0
                                THEN (0.5 * (CAST(COALESCE(chunks_failed, 0) AS REAL) / chunks_requested)) * 10.0
                            ELSE 0.0
                        END)
                        + (CASE
                            WHEN COALESCE(chunks_requested, 0) > 0
                                THEN (0.3 * (CAST(COALESCE(chunks_timedout, 0) AS REAL) / chunks_requested)) * 10.0
                            ELSE 0.0
                        END)
                        + (CASE
                            WHEN COALESCE(rtt_avg_ms, 0) > 0
                                THEN 0.2 * (rtt_avg_ms / 1000.0)
                            ELSE 0.0
                        END)
                        + (CASE
                            WHEN COALESCE(throughput_stddev_bps, 0) > 0
                                AND COALESCE(throughput_avg_bps, 0) > 0
                                THEN 0.1 * (throughput_stddev_bps / throughput_avg_bps)
                            ELSE 0.0
                        END)
                        + (1.0 * (1.0 - MAX(0.0, MIN(1.0, COALESCE(reputation_score, 0.5))))) * 5.0
                        AS peer_cost
                    FROM PeerMetrics
                    INNER JOIN first_metrics ON first_metrics.source_rowid = PeerMetrics.rowid
                )
                SELECT *
                FROM costed_metrics
                ORDER BY peer_cost, source_rowid
                LIMIT @limit
                """;
            cmd.Parameters.AddWithValue("@limit", limit);

            using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                list.Add(ReadPeerMetrics(reader));
            }

            return list;
        }

        /// <inheritdoc/>
        public Task<Transfers.MultiSource.Metrics.PeerPerformanceMetrics?> GetPeerMetricsAsync(string peerId, CancellationToken cancellationToken = default)
        {
            peerId = peerId?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(peerId))
            {
                return Task.FromResult<Transfers.MultiSource.Metrics.PeerPerformanceMetrics?>(null);
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT * FROM PeerMetrics WHERE peer_id = @peer_id";
            cmd.Parameters.AddWithValue("@peer_id", peerId);

            using var reader = cmd.ExecuteReader();
            if (reader.Read())
            {
                return Task.FromResult<Transfers.MultiSource.Metrics.PeerPerformanceMetrics?>(ReadPeerMetrics(reader));
            }

            return Task.FromResult<Transfers.MultiSource.Metrics.PeerPerformanceMetrics?>(null);
        }

        /// <inheritdoc/>
        public async Task<List<Transfers.MultiSource.Metrics.PeerPerformanceMetrics>> GetPeerMetricsAsync(
            IEnumerable<string> peerIds,
            CancellationToken cancellationToken = default)
        {
            var normalized = peerIds
                .Select(peerId => peerId?.Trim() ?? string.Empty)
                .Where(peerId => !string.IsNullOrWhiteSpace(peerId))
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            var metrics = new List<Transfers.MultiSource.Metrics.PeerPerformanceMetrics>();
            if (normalized.Length == 0)
            {
                return metrics;
            }

            using var conn = GetConnection();
            foreach (var batch in normalized.Chunk(500))
            {
                using var cmd = conn.CreateCommand();
                var parameters = batch.Select((_, index) => $"@peer_id{index}").ToArray();
                cmd.CommandText = $"SELECT * FROM PeerMetrics WHERE peer_id IN ({string.Join(", ", parameters)})";
                for (var index = 0; index < batch.Length; index++)
                {
                    cmd.Parameters.AddWithValue(parameters[index], batch[index]);
                }

                using var reader = await cmd.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
                while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
                {
                    metrics.Add(ReadPeerMetrics(reader));
                }
            }

            return metrics;
        }

        /// <inheritdoc/>
        public Task UpsertPeerMetricsAsync(Transfers.MultiSource.Metrics.PeerPerformanceMetrics metrics, CancellationToken cancellationToken = default)
        {
            if (metrics == null || string.IsNullOrWhiteSpace(metrics.PeerId))
            {
                return Task.CompletedTask;
            }

            metrics.PeerId = metrics.PeerId.Trim();
            if (string.IsNullOrWhiteSpace(metrics.PeerId))
            {
                return Task.CompletedTask;
            }

            using var conn = GetConnection();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
                INSERT INTO PeerMetrics (
                    peer_id,
                    source,
                    rtt_avg_ms,
                    rtt_stddev_ms,
                    last_rtt_sample,
                    throughput_avg_bps,
                    throughput_stddev_bps,
                    total_bytes,
                    last_throughput_sample,
                    chunks_requested,
                    chunks_completed,
                    chunks_failed,
                    chunks_timedout,
                    chunks_corrupted,
                    sample_count,
                    first_seen,
                    last_updated,
                    reputation_score,
                    reputation_updated_at
                ) VALUES (
                    @peer_id,
                    @source,
                    @rtt_avg_ms,
                    @rtt_stddev_ms,
                    @last_rtt_sample,
                    @throughput_avg_bps,
                    @throughput_stddev_bps,
                    @total_bytes,
                    @last_throughput_sample,
                    @chunks_requested,
                    @chunks_completed,
                    @chunks_failed,
                    @chunks_timedout,
                    @chunks_corrupted,
                    @sample_count,
                    @first_seen,
                    @last_updated,
                    @reputation_score,
                    @reputation_updated_at
                )
                ON CONFLICT(peer_id) DO UPDATE SET
                    source = excluded.source,
                    rtt_avg_ms = excluded.rtt_avg_ms,
                    rtt_stddev_ms = excluded.rtt_stddev_ms,
                    last_rtt_sample = excluded.last_rtt_sample,
                    throughput_avg_bps = excluded.throughput_avg_bps,
                    throughput_stddev_bps = excluded.throughput_stddev_bps,
                    total_bytes = excluded.total_bytes,
                    last_throughput_sample = excluded.last_throughput_sample,
                    chunks_requested = excluded.chunks_requested,
                    chunks_completed = excluded.chunks_completed,
                    chunks_failed = excluded.chunks_failed,
                    chunks_timedout = excluded.chunks_timedout,
                    chunks_corrupted = excluded.chunks_corrupted,
                    sample_count = excluded.sample_count,
                    first_seen = excluded.first_seen,
                    last_updated = excluded.last_updated,
                    reputation_score = excluded.reputation_score,
                    reputation_updated_at = excluded.reputation_updated_at;
            ";

            cmd.Parameters.AddWithValue("@peer_id", metrics.PeerId);
            cmd.Parameters.AddWithValue("@source", metrics.Source.ToString());
            cmd.Parameters.AddWithValue("@rtt_avg_ms", metrics.RttAvgMs);
            cmd.Parameters.AddWithValue("@rtt_stddev_ms", metrics.RttStdDevMs);
            cmd.Parameters.AddWithValue("@last_rtt_sample", (object?)metrics.LastRttSample?.ToUnixTimeSeconds() ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@throughput_avg_bps", metrics.ThroughputAvgBytesPerSec);
            cmd.Parameters.AddWithValue("@throughput_stddev_bps", metrics.ThroughputStdDevBytesPerSec);
            cmd.Parameters.AddWithValue("@total_bytes", metrics.TotalBytesTransferred);
            cmd.Parameters.AddWithValue("@last_throughput_sample", (object?)metrics.LastThroughputSample?.ToUnixTimeSeconds() ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@chunks_requested", metrics.ChunksRequested);
            cmd.Parameters.AddWithValue("@chunks_completed", metrics.ChunksCompleted);
            cmd.Parameters.AddWithValue("@chunks_failed", metrics.ChunksFailed);
            cmd.Parameters.AddWithValue("@chunks_timedout", metrics.ChunksTimedOut);
            cmd.Parameters.AddWithValue("@chunks_corrupted", metrics.ChunksCorrupted);
            cmd.Parameters.AddWithValue("@sample_count", metrics.SampleCount);
            cmd.Parameters.AddWithValue("@first_seen", metrics.FirstSeen.ToUnixTimeSeconds());
            cmd.Parameters.AddWithValue("@last_updated", metrics.LastUpdated.ToUnixTimeSeconds());
            cmd.Parameters.AddWithValue("@reputation_score", metrics.ReputationScore);
            cmd.Parameters.AddWithValue("@reputation_updated_at", (object?)metrics.ReputationUpdatedAt?.ToUnixTimeSeconds() ?? DBNull.Value);

            cmd.ExecuteNonQuery();
            return Task.CompletedTask;
        }

        private Transfers.MultiSource.Metrics.PeerPerformanceMetrics ReadPeerMetrics(SqliteDataReader reader)
        {
            var metrics = new Transfers.MultiSource.Metrics.PeerPerformanceMetrics
            {
                PeerId = reader.GetString(reader.GetOrdinal("peer_id")).Trim(),
                Source = Enum.TryParse<Transfers.MultiSource.Metrics.PeerSource>(reader.GetString(reader.GetOrdinal("source")), true, out var src) ? src : Transfers.MultiSource.Metrics.PeerSource.Soulseek,
                RttAvgMs = reader.IsDBNull(reader.GetOrdinal("rtt_avg_ms")) ? 0 : reader.GetDouble(reader.GetOrdinal("rtt_avg_ms")),
                RttStdDevMs = reader.IsDBNull(reader.GetOrdinal("rtt_stddev_ms")) ? 0 : reader.GetDouble(reader.GetOrdinal("rtt_stddev_ms")),
                LastRttSample = reader.IsDBNull(reader.GetOrdinal("last_rtt_sample")) ? null : DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(reader.GetOrdinal("last_rtt_sample"))),
                ThroughputAvgBytesPerSec = reader.IsDBNull(reader.GetOrdinal("throughput_avg_bps")) ? 0 : reader.GetDouble(reader.GetOrdinal("throughput_avg_bps")),
                ThroughputStdDevBytesPerSec = reader.IsDBNull(reader.GetOrdinal("throughput_stddev_bps")) ? 0 : reader.GetDouble(reader.GetOrdinal("throughput_stddev_bps")),
                TotalBytesTransferred = reader.IsDBNull(reader.GetOrdinal("total_bytes")) ? 0 : reader.GetInt64(reader.GetOrdinal("total_bytes")),
                LastThroughputSample = reader.IsDBNull(reader.GetOrdinal("last_throughput_sample")) ? null : DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(reader.GetOrdinal("last_throughput_sample"))),
                ChunksRequested = reader.IsDBNull(reader.GetOrdinal("chunks_requested")) ? 0 : reader.GetInt32(reader.GetOrdinal("chunks_requested")),
                ChunksCompleted = reader.IsDBNull(reader.GetOrdinal("chunks_completed")) ? 0 : reader.GetInt32(reader.GetOrdinal("chunks_completed")),
                ChunksFailed = reader.IsDBNull(reader.GetOrdinal("chunks_failed")) ? 0 : reader.GetInt32(reader.GetOrdinal("chunks_failed")),
                ChunksTimedOut = reader.IsDBNull(reader.GetOrdinal("chunks_timedout")) ? 0 : reader.GetInt32(reader.GetOrdinal("chunks_timedout")),
                ChunksCorrupted = reader.IsDBNull(reader.GetOrdinal("chunks_corrupted")) ? 0 : reader.GetInt32(reader.GetOrdinal("chunks_corrupted")),
                SampleCount = reader.IsDBNull(reader.GetOrdinal("sample_count")) ? 0 : reader.GetInt32(reader.GetOrdinal("sample_count")),
                FirstSeen = reader.IsDBNull(reader.GetOrdinal("first_seen")) ? DateTimeOffset.UtcNow : DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(reader.GetOrdinal("first_seen"))),
                LastUpdated = reader.IsDBNull(reader.GetOrdinal("last_updated")) ? DateTimeOffset.UtcNow : DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(reader.GetOrdinal("last_updated"))),
                ReputationScore = reader.IsDBNull(reader.GetOrdinal("reputation_score")) ? 0.5 : reader.GetDouble(reader.GetOrdinal("reputation_score")),
                ReputationUpdatedAt = reader.IsDBNull(reader.GetOrdinal("reputation_updated_at")) ? null : DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64(reader.GetOrdinal("reputation_updated_at"))),
                RecentRttSamples = new Queue<Transfers.MultiSource.Metrics.RttSample>(),
                RecentThroughputSamples = new Queue<Transfers.MultiSource.Metrics.ThroughputSample>(),
            };

            return metrics;
        }
    }
}
