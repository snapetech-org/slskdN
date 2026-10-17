// <copyright file="LibraryHealthService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.LibraryHealth
{
    using System;
    using System.Collections.Concurrent;
    using System.Collections.Generic;
    using System.IO;
    using System.Linq;
    using System.Text.Json;
    using System.Threading;
    using System.Threading.Tasks;
    using Microsoft.Extensions.Logging;
    using Microsoft.Extensions.Options;
    using slskd.Audio;
    using slskd.Common.Security;
    using slskd.HashDb;
    using slskd.Integrations.MetadataFacade;
    using slskd.Integrations.MusicBrainz;
    using slskd.LibraryHealth.Remediation;
    using TagLib;

    /// <summary>
    /// Library Health scanner for detecting quality issues and missing tracks.
    /// Implements deep scanning: transcode detection, canonical variant checking, release completeness.
    /// </summary>
    public class LibraryHealthService : ILibraryHealthService
    {
        private const int ScanProgressCheckpointFiles = 100;

        private readonly IHashDbService hashDb;
        private readonly ILibraryHealthRemediationService remediationService;
        private readonly IMetadataFacade metadataFacade;
        private readonly ICanonicalStatsService canonicalStats;
        private readonly IMusicBrainzClient musicBrainzClient;
        private readonly ILogger<LibraryHealthService> log;
        private readonly IOptionsMonitor<slskd.Options> optionsMonitor;
        private readonly ISpectralAnalyzer? spectralAnalyzer;
        private readonly ConcurrentDictionary<string, LibraryHealthScan> activeScans = new();
        private readonly object scanAdmissionLock = new();
        private string? runningScanId;
        private readonly QualityScorer qualityScorer = new();
        private readonly TranscodeDetector transcodeDetector = new();

        public LibraryHealthService(
            IHashDbService hashDb,
            ILibraryHealthRemediationService remediationService,
            IMetadataFacade metadataFacade,
            ICanonicalStatsService canonicalStats,
            IMusicBrainzClient musicBrainzClient,
            IOptionsMonitor<slskd.Options> optionsMonitor,
            ILogger<LibraryHealthService> log,
            ISpectralAnalyzer? spectralAnalyzer = null)
        {
            this.spectralAnalyzer = spectralAnalyzer;
            this.hashDb = hashDb;
            this.remediationService = remediationService;
            this.metadataFacade = metadataFacade;
            this.canonicalStats = canonicalStats;
            this.musicBrainzClient = musicBrainzClient;
            this.optionsMonitor = optionsMonitor;
            this.log = log;
        }

        public async Task<string> StartScanAsync(LibraryHealthScanRequest request, CancellationToken ct = default)
        {
            request ??= new LibraryHealthScanRequest();

            var requestedExtensions = request.FileExtensions?.Count > 0
                ? request.FileExtensions
                    .Where(ext => !string.IsNullOrWhiteSpace(ext))
                    .Select(ext => ext.Trim())
                    .Select(ext => ext.StartsWith('.') ? ext.ToLowerInvariant() : $".{ext.ToLowerInvariant()}")
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .ToList()
                : new List<string> { ".flac", ".mp3", ".m4a", ".ogg" };

            if (requestedExtensions.Count == 0)
            {
                requestedExtensions = new List<string> { ".flac", ".mp3", ".m4a", ".ogg" };
            }

            var libraryPath = ResolveLibraryPath(request.LibraryPath);
            if (libraryPath == null)
            {
                throw new UnauthorizedException("Library Health scans must target a configured share directory");
            }

            var maxConcurrentFiles = Math.Clamp(request.MaxConcurrentFiles > 0 ? request.MaxConcurrentFiles : 4, 1, 8);

            if (request.IncludeSpectralAnalysis && spectralAnalyzer?.IsEnabled != true)
            {
                throw new SpectralAnalysisUnavailableException();
            }

            var scanId = Guid.NewGuid().ToString();
            lock (scanAdmissionLock)
            {
                if (runningScanId != null)
                {
                    throw new LibraryHealthScanAlreadyRunningException(runningScanId);
                }

                runningScanId = scanId;
            }

            var scan = new LibraryHealthScan
            {
                ScanId = scanId,
                LibraryPath = libraryPath,
                StartedAt = DateTimeOffset.UtcNow,
                Status = ScanStatus.Running,
                FilesScanned = 0,
                IssuesDetected = 0,
            };

            try
            {
                activeScans[scanId] = scan;
                await hashDb.UpsertLibraryHealthScanAsync(scan, ct).ConfigureAwait(false);
            }
            catch
            {
                activeScans.TryRemove(scanId, out _);
                ReleaseScanAdmission(scanId);
                throw;
            }

            var normalizedRequest = new LibraryHealthScanRequest
            {
                LibraryPath = libraryPath,
                IncludeSubdirectories = request.IncludeSubdirectories,
                FileExtensions = requestedExtensions,
                SkipPreviouslyScanned = request.SkipPreviouslyScanned,
                MaxConcurrentFiles = maxConcurrentFiles,
                IncludeSpectralAnalysis = request.IncludeSpectralAnalysis,
            };

            _ = TaskObservation.Observe(
                Task.Run(() => PerformScanAsync(scanId, normalizedRequest, CancellationToken.None), CancellationToken.None),
                ex => log.LogError(ex, "[LibraryHealth] Library health scan task failed to start"));
            return scanId;
        }

        public async Task<LibraryHealthScan?> GetScanStatusAsync(string scanId, CancellationToken ct = default)
        {
            if (activeScans.TryGetValue(scanId, out var active))
            {
                return active;
            }

            return await hashDb.GetLibraryHealthScanAsync(scanId, ct).ConfigureAwait(false);
        }

        public Task<List<LibraryIssue>> GetIssuesAsync(LibraryHealthIssueFilter filter, CancellationToken ct = default)
        {
            return hashDb.GetLibraryIssuesAsync(filter, ct);
        }

        public Task<LibraryIssuePage> GetIssuePageAsync(LibraryHealthIssueFilter filter, CancellationToken ct = default)
        {
            return hashDb.GetLibraryIssuePageAsync(filter, ct);
        }

        public Task<List<LibraryIssueTypeSummary>> GetIssueTypeSummariesAsync(string libraryPath, CancellationToken ct = default)
        {
            return hashDb.GetLibraryIssueTypeSummariesAsync(libraryPath, ct);
        }

        public Task<List<LibraryIssueArtistSummary>> GetIssueArtistSummariesAsync(
            string libraryPath,
            int limit,
            CancellationToken ct = default)
        {
            return hashDb.GetLibraryIssueArtistSummariesAsync(libraryPath, limit, ct);
        }

        public Task<List<LibraryIssueReleaseSummary>> GetIssueReleaseSummariesAsync(
            string libraryPath,
            int limit,
            CancellationToken ct = default)
        {
            return hashDb.GetLibraryIssueReleaseSummariesAsync(libraryPath, limit, ct);
        }

        public Task<List<IssueCodecGroup>> GetIssueCodecSummariesAsync(
            string libraryPath,
            CancellationToken ct = default)
        {
            return hashDb.GetLibraryIssueCodecSummariesAsync(libraryPath, ct);
        }

        public Task<LibraryHealthDashboard> GetDashboardAsync(
            string libraryPath,
            int artistLimit,
            int issueLimit,
            CancellationToken ct = default)
        {
            return hashDb.GetLibraryHealthDashboardAsync(libraryPath, artistLimit, issueLimit, ct);
        }

        public Task UpdateIssueStatusAsync(string issueId, LibraryIssueStatus newStatus, CancellationToken ct = default)
        {
            return hashDb.UpdateLibraryIssueStatusAsync(issueId, newStatus, ct);
        }

        public async Task<string> CreateRemediationJobAsync(List<string> issueIds, CancellationToken ct = default)
        {
            log.LogInformation("[LH] Creating remediation job for {Count} issues", issueIds?.Count ?? 0);
            return await remediationService.CreateRemediationJobAsync(issueIds ?? new List<string>(), ct).ConfigureAwait(false);
        }

        public Task<LibraryHealthSummary> GetSummaryAsync(string libraryPath, CancellationToken ct = default)
        {
            return hashDb.GetLibraryHealthSummaryAsync(libraryPath, ct);
        }

        private async Task PerformScanAsync(string scanId, LibraryHealthScanRequest request, CancellationToken ct)
        {
            if (!activeScans.TryGetValue(scanId, out var scan))
            {
                return;
            }

            try
            {
                if (!Directory.Exists(request.LibraryPath))
                {
                    throw new DirectoryNotFoundException($"Library path not found: {request.LibraryPath}");
                }

                log.LogInformation("[LH] Starting library health scan: {Path}", request.LibraryPath);

                var files = Directory.EnumerateFiles(
                        request.LibraryPath,
                        "*.*",
                        CreateLibraryEnumerationOptions(request.IncludeSubdirectories))
                    .Where(f => request.FileExtensions.Contains(Path.GetExtension(f).ToLowerInvariant()));

                var scanLock = new object();
                var scannedCount = 0;
                var releaseChecks = new ConcurrentDictionary<(string ReleaseId, string Directory), string>();

                await Parallel.ForEachAsync(
                    files,
                    new ParallelOptions
                    {
                        CancellationToken = ct,
                        MaxDegreeOfParallelism = request.MaxConcurrentFiles,
                    },
                    async (file, fileCancellationToken) =>
                    {
                        try
                        {
                            await ScanFileAsync(file, request.IncludeSpectralAnalysis, scan, scanLock, releaseChecks, fileCancellationToken);
                        }
                        catch (Exception ex)
                        {
                            log.LogWarning(ex, "[LH] Failed to scan file: {Path}", file);
                        }

                        var completedFiles = Interlocked.Increment(ref scannedCount);
                        lock (scanLock)
                        {
                            scan.FilesScanned = Math.Max(scan.FilesScanned, completedFiles);
                        }

                        if (completedFiles % ScanProgressCheckpointFiles == 0)
                        {
                            await hashDb.UpsertLibraryHealthScanAsync(scan, fileCancellationToken).ConfigureAwait(false);
                        }
                    }).ConfigureAwait(false);

                await Parallel.ForEachAsync(
                    releaseChecks,
                    new ParallelOptions
                    {
                        CancellationToken = ct,
                        MaxDegreeOfParallelism = request.MaxConcurrentFiles,
                    },
                    async (releaseCheck, releaseCancellationToken) =>
                    {
                        await CheckReleaseCompletenessAsync(
                            releaseCheck.Value,
                            releaseCheck.Key.ReleaseId,
                            scan,
                            scanLock,
                            releaseCancellationToken).ConfigureAwait(false);
                    }).ConfigureAwait(false);

                scan.Status = ScanStatus.Completed;
                scan.CompletedAt = DateTimeOffset.UtcNow;
                await hashDb.UpsertLibraryHealthScanAsync(scan, ct).ConfigureAwait(false);
                activeScans.TryRemove(scanId, out _);

                log.LogInformation("[LH] Scan completed: {Files} files, {Issues} issues", scan.FilesScanned, scan.IssuesDetected);
            }
            catch (Exception ex)
            {
                scan.Status = ScanStatus.Failed;
                scan.ErrorMessage = "Library health scan failed";
                scan.CompletedAt = DateTimeOffset.UtcNow;
                await hashDb.UpsertLibraryHealthScanAsync(scan, ct).ConfigureAwait(false);
                activeScans.TryRemove(scanId, out _);
                log.LogWarning(ex, "[LH] Scan failed for {Path}", request.LibraryPath);
            }
            finally
            {
                ReleaseScanAdmission(scanId);
            }
        }

        private void ReleaseScanAdmission(string scanId)
        {
            lock (scanAdmissionLock)
            {
                if (string.Equals(runningScanId, scanId, StringComparison.Ordinal))
                {
                    runningScanId = null;
                }
            }
        }

        private async Task ScanFileAsync(
            string filePath,
            bool includeSpectralAnalysis,
            LibraryHealthScan scan,
            object scanLock,
            ConcurrentDictionary<(string ReleaseId, string Directory), string> releaseChecks,
            CancellationToken ct)
        {
            try
            {
                // Step 1: Resolve MusicBrainz ID via metadata facade
                var metadata = await metadataFacade.GetByFileAsync(filePath, ct).ConfigureAwait(false);
                var hasRecordingId = metadata != null && !string.IsNullOrWhiteSpace(metadata.MusicBrainzRecordingId);
                if (!hasRecordingId)
                {
                    // Issue: Missing metadata. Transcode checks below still run; they only need the file.
                    await EmitIssueAsync(new LibraryIssue
                    {
                        IssueId = Guid.NewGuid().ToString(),
                        Type = LibraryIssueType.MissingMetadata,
                        Severity = LibraryIssueSeverity.Low,
                        FilePath = filePath,
                        Reason = "Unable to resolve MusicBrainz Recording ID via fingerprint or tags",
                        CanAutoFix = false,
                        Status = LibraryIssueStatus.Detected,
                        DetectedAt = DateTimeOffset.UtcNow,
                    }, scan, scanLock, ct);
                }

                var recordingId = hasRecordingId ? metadata!.MusicBrainzRecordingId : string.Empty;

                // Step 2: Create AudioVariant from file
                AudioVariant variant;
                try
                {
                    using var tagFile = TagLib.File.Create(filePath);
                    var props = tagFile.Properties;
                    var fileInfo = new FileInfo(filePath);

                    variant = new AudioVariant
                    {
                        VariantId = Guid.NewGuid().ToString(),
                        MusicBrainzRecordingId = recordingId,
                        Codec = GetCodecName(props, Path.GetExtension(filePath)),
                        SampleRateHz = props.AudioSampleRate,
                        BitDepth = props.BitsPerSample > 0 ? props.BitsPerSample : null,
                        Channels = props.AudioChannels,
                        DurationMs = (int)props.Duration.TotalMilliseconds,
                        BitrateKbps = (int)(props.AudioBitrate / 1000.0),
                        FileSizeBytes = fileInfo.Length,
                        FirstSeenAt = DateTimeOffset.UtcNow,
                        LastSeenAt = DateTimeOffset.UtcNow,
                        SeenCount = 1,
                    };

                    // Compute quality score
                    variant.QualityScore = qualityScorer.ComputeQualityScore(variant);

                    // Check for transcode
                    var (isSuspect, reason) = transcodeDetector.DetectTranscode(variant);
                    variant.TranscodeSuspect = isSuspect;
                    variant.TranscodeReason = reason;
                }
                catch (Exception)
                {
                    if (!hasRecordingId)
                    {
                        // Already reported as missing metadata; an unreadable file without an ID adds nothing more.
                        return;
                    }

                    // Issue: Corrupted file
                    await EmitIssueAsync(new LibraryIssue
                    {
                        IssueId = Guid.NewGuid().ToString(),
                        Type = LibraryIssueType.CorruptedFile,
                        Severity = LibraryIssueSeverity.Critical,
                        FilePath = filePath,
                        MusicBrainzRecordingId = recordingId,
                        Reason = "File cannot be read",
                        CanAutoFix = true,
                        SuggestedAction = "Re-download from Soulseek or mesh overlay",
                        Status = LibraryIssueStatus.Detected,
                        DetectedAt = DateTimeOffset.UtcNow,
                    }, scan, scanLock, ct);
                    return;
                }

                // Step 2b: Measure the spectral shelf of lossless files when the scan requested it
                SpectralAnalysisResult? spectral = null;
                if (includeSpectralAnalysis && spectralAnalyzer != null && TranscodeDetector.IsLosslessCodec(variant.Codec))
                {
                    try
                    {
                        spectral = await spectralAnalyzer
                            .AnalyzeAsync(filePath, variant.SampleRateHz, variant.DurationMs / 1000.0, ct)
                            .ConfigureAwait(false);
                        spectral?.ApplyTo(variant);
                    }
                    catch (Exception ex) when (ex is not OperationCanceledException)
                    {
                        // The measurement is optional; a decoder failure must not be reported as a corrupted file.
                        log.LogWarning(ex, "[LH] Spectral analysis failed for {Path}", LoggingSanitizer.SanitizeFilePath(filePath));
                    }
                }

                // Step 3: Check for transcodes. A spectral Suspect or Upsampled result is recorded as a low-severity
                // issue: it may be a mastering filter rather than a lossy source.
                var spectralOnlySuspect = !variant.TranscodeSuspect &&
                    spectral?.Verdict is SpectralVerdict.Suspect or SpectralVerdict.Upsampled;
                if (variant.TranscodeSuspect || spectralOnlySuspect)
                {
                    var issueMetadata = new Dictionary<string, object>
                    {
                        ["quality_score"] = variant.QualityScore,
                        ["codec"] = variant.Codec,
                        ["bitrate"] = variant.BitrateKbps,
                    };
                    if (spectral is { Verdict: not SpectralVerdict.Inconclusive })
                    {
                        issueMetadata["spectral_verdict"] = spectral.Verdict.ToString();
                        if (spectral.CutoffHz is double cutoffHz)
                        {
                            issueMetadata["spectral_cutoff_hz"] = Math.Round(cutoffHz);
                        }

                        if (spectral.ShelfDropDb is double dropDb)
                        {
                            issueMetadata["spectral_shelf_drop_db"] = Math.Round(dropDb, 1);
                        }

                        if (!string.IsNullOrEmpty(spectral.EstimatedSource))
                        {
                            issueMetadata["spectral_estimated_source"] = spectral.EstimatedSource;
                        }
                    }

                    await EmitIssueAsync(new LibraryIssue
                    {
                        IssueId = Guid.NewGuid().ToString(),
                        Type = LibraryIssueType.SuspectedTranscode,
                        Severity = variant.TranscodeSuspect ? LibraryIssueSeverity.High : LibraryIssueSeverity.Low,
                        FilePath = filePath,
                        MusicBrainzRecordingId = recordingId,
                        Artist = metadata?.Artist ?? string.Empty,
                        Title = metadata?.Title ?? string.Empty,
                        Reason = variant.TranscodeSuspect ? variant.TranscodeReason : spectral!.Describe(),
                        Metadata = issueMetadata,
                        CanAutoFix = true,
                        SuggestedAction = "Replace with verified lossless variant from canonical sources",
                        Status = LibraryIssueStatus.Detected,
                        DetectedAt = DateTimeOffset.UtcNow,
                    }, scan, scanLock, ct);
                }

                // Steps 4 and 5 compare against MusicBrainz data, so they need a recording ID.
                if (!hasRecordingId)
                {
                    return;
                }

                // Step 4: Check for canonical upgrades
                if (canonicalStats != null)
                {
                    var candidates = await canonicalStats.GetCanonicalVariantCandidatesAsync(recordingId, ct).ConfigureAwait(false);
                    if (candidates != null && candidates.Count > 0)
                    {
                        var bestCanonical = candidates.First();
                        double qualityGap = bestCanonical.QualityScore - variant.QualityScore;

                        // Significant quality gap.
                        if (qualityGap > 0.2)
                        {
                            await EmitIssueAsync(new LibraryIssue
                            {
                                IssueId = Guid.NewGuid().ToString(),
                                Type = LibraryIssueType.NonCanonicalVariant,
                                Severity = qualityGap > 0.4 ? LibraryIssueSeverity.High : LibraryIssueSeverity.Medium,
                                FilePath = filePath,
                                MusicBrainzRecordingId = recordingId,
                                Artist = metadata.Artist ?? string.Empty,
                                Title = metadata.Title ?? string.Empty,
                                Reason = $"Canonical variant available with quality score {bestCanonical.QualityScore:F2} vs current {variant.QualityScore:F2}",
                                Metadata = new Dictionary<string, object>
                                {
                                    ["current_quality"] = variant.QualityScore,
                                    ["canonical_quality"] = bestCanonical.QualityScore,
                                    ["canonical_codec"] = bestCanonical.Codec,
                                    ["canonical_bitrate"] = bestCanonical.BitrateKbps,
                                },
                                CanAutoFix = true,
                                SuggestedAction = "Download canonical variant and replace current file",
                                Status = LibraryIssueStatus.Detected,
                                DetectedAt = DateTimeOffset.UtcNow,
                            }, scan, scanLock, ct);
                        }
                    }
                }

                // Step 5: Check release completeness (if release ID available)
                if (!string.IsNullOrWhiteSpace(metadata.MusicBrainzReleaseId))
                {
                    var releaseId = metadata.MusicBrainzReleaseId.Trim();
                    var directory = Path.GetDirectoryName(filePath) ?? string.Empty;
                    releaseChecks.TryAdd((releaseId, directory), filePath);
                }
            }
            catch (Exception ex)
            {
                log.LogWarning(ex, "[LH] Failed to scan file: {Path}", filePath);

                // Issue: Corrupted file
                await EmitIssueAsync(new LibraryIssue
                {
                    IssueId = Guid.NewGuid().ToString(),
                    Type = LibraryIssueType.CorruptedFile,
                    Severity = LibraryIssueSeverity.Critical,
                    FilePath = filePath,
                    Reason = "File scan failed",
                    CanAutoFix = true,
                    SuggestedAction = "Re-download from Soulseek or mesh overlay",
                    Status = LibraryIssueStatus.Detected,
                    DetectedAt = DateTimeOffset.UtcNow,
                }, scan, scanLock, ct);
            }
        }

        private async Task CheckReleaseCompletenessAsync(string filePath, string releaseId, LibraryHealthScan scan, object scanLock, CancellationToken ct)
        {
            try
            {
                var albumTarget = await hashDb.GetAlbumTargetAsync(releaseId, ct).ConfigureAwait(false);
                if (albumTarget == null)
                {
                    return; // No album target, skip completeness check
                }

                var tracks = (await hashDb.GetAlbumTracksAsync(releaseId, ct).ConfigureAwait(false)).ToList();
                if (tracks.Count == 0)
                {
                    return;
                }

                var libraryPath = Path.GetDirectoryName(filePath);
                var recordingIds = tracks
                    .Where(track => !string.IsNullOrWhiteSpace(track.RecordingId))
                    .Select(track => track.RecordingId)
                    .ToArray();
                var presentRecordingIds = await hashDb
                    .GetRecordingIdsWithHashesAsync(recordingIds, ct)
                    .ConfigureAwait(false);
                var missingTracks = tracks
                    .Where(track =>
                        !string.IsNullOrWhiteSpace(track.RecordingId) &&
                        !presentRecordingIds.Contains(track.RecordingId))
                    .ToList();

                if (missingTracks.Count > 0)
                {
                    await EmitIssueAsync(new LibraryIssue
                    {
                        IssueId = Guid.NewGuid().ToString(),
                        Type = LibraryIssueType.MissingTrackInRelease,
                        Severity = missingTracks.Count > tracks.Count / 2 ? LibraryIssueSeverity.High : LibraryIssueSeverity.Medium,
                        FilePath = libraryPath ?? string.Empty, // Directory, not specific file
                        MusicBrainzReleaseId = releaseId,
                        Artist = albumTarget.Artist,
                        Album = albumTarget.Title,
                        Reason = $"Album incomplete: {missingTracks.Count}/{tracks.Count} tracks missing",
                        Metadata = new Dictionary<string, object>
                        {
                            ["missing_tracks"] = missingTracks.Select(t => new
                            {
                                position = t.Position,
                                title = t.Title,
                                recording_id = t.RecordingId
                            }).ToList(),
                            ["total_tracks"] = tracks.Count,
                        },
                        CanAutoFix = true,
                        SuggestedAction = "Download missing tracks via multi-swarm",
                        Status = LibraryIssueStatus.Detected,
                        DetectedAt = DateTimeOffset.UtcNow,
                    }, scan, scanLock, ct);
                }
            }
            catch (Exception ex)
            {
                log.LogWarning(ex, "[LH] Failed to check release completeness for {ReleaseId}", releaseId);
            }
        }

        internal static EnumerationOptions CreateLibraryEnumerationOptions(bool includeSubdirectories)
        {
            return new EnumerationOptions
            {
                RecurseSubdirectories = includeSubdirectories,
                AttributesToSkip = FileAttributes.Hidden | FileAttributes.System | FileAttributes.ReparsePoint,
            };
        }

        private async Task EmitIssueAsync(LibraryIssue issue, LibraryHealthScan scan, object scanLock, CancellationToken ct)
        {
            try
            {
                await hashDb.InsertLibraryIssueAsync(issue, ct).ConfigureAwait(false);
                lock (scanLock)
                {
                    scan.IssuesDetected++;
                }

                log.LogDebug("[LH] Detected issue: {Type} for {Path}", issue.Type, issue.FilePath);
            }
            catch (Exception ex)
            {
                log.LogWarning(ex, "[LH] Failed to emit issue for {Path}", issue.FilePath);
            }
        }

        private static string GetCodecName(TagLib.Properties props, string extension)
        {
            // Prefer explicit container/extension mapping; fall back to first codec description.
            switch (extension?.ToLowerInvariant())
            {
                case ".flac": return "FLAC";
                case ".alac":
                case ".m4a": return "ALAC";
                case ".aac": return "AAC";
                case ".mp3": return "MP3";
                case ".opus": return "Opus";
                case ".ogg": return "Vorbis";
                case ".wav": return "WAV";
                default:
                    var desc = props.Codecs.FirstOrDefault()?.Description;
                    return string.IsNullOrWhiteSpace(desc) ? "Unknown" : desc;
            }
        }

        private string? ResolveLibraryPath(string requestedPath)
        {
            var shareRoots = optionsMonitor.CurrentValue.Shares.Directories
                .Select(share => new Shares.Share(share).LocalPath)
                .Where(path => !string.IsNullOrWhiteSpace(path))
                .ToList();

            if (!shareRoots.Any())
            {
                return null;
            }

            if (string.IsNullOrWhiteSpace(requestedPath))
            {
                return Path.GetFullPath(shareRoots[0]);
            }

            return PathGuard.NormalizeAbsolutePathWithinRoots(requestedPath, shareRoots);
        }
    }
}
