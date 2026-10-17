// <copyright file="LibraryIssueModels.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.LibraryHealth
{
    using System;
    using System.Collections.Generic;

    public enum LibraryIssueType
    {
        SuspectedTranscode,
        NonCanonicalVariant,
        TrackNotInTaggedRelease,
        MissingTrackInRelease,
        CorruptedFile,
        MissingMetadata,
        MultipleVariants,
        WrongDuration,
    }

    public enum LibraryIssueSeverity
    {
        Info,
        Low,
        Medium,
        High,
        Critical,
    }

    public enum LibraryIssueStatus
    {
        Detected,
        Acknowledged,
        Ignored,
        Fixing,
        Resolved,
        Failed,
    }

    public class LibraryIssue
    {
        public string IssueId { get; set; } = string.Empty;
        public LibraryIssueType Type { get; set; }
        public LibraryIssueSeverity Severity { get; set; }

        // Affected entities
        public string FilePath { get; set; } = string.Empty;
        public string MusicBrainzRecordingId { get; set; } = string.Empty;
        public string MusicBrainzReleaseId { get; set; } = string.Empty;
        public string Artist { get; set; } = string.Empty;
        public string Album { get; set; } = string.Empty;
        public string Title { get; set; } = string.Empty;

        // Issue details
        public string Reason { get; set; } = string.Empty;
        public Dictionary<string, object> Metadata { get; set; } = new();

        // Remediation
        public bool CanAutoFix { get; set; }
        public string SuggestedAction { get; set; } = string.Empty;
        public string RemediationJobId { get; set; } = string.Empty;

        // Status
        public LibraryIssueStatus Status { get; set; }
        public DateTimeOffset DetectedAt { get; set; }
        public DateTimeOffset? ResolvedAt { get; set; }
        public string ResolvedBy { get; set; } = string.Empty;
    }

    public class LibraryHealthScan
    {
        public string ScanId { get; set; } = string.Empty;
        public string LibraryPath { get; set; } = string.Empty;
        public DateTimeOffset StartedAt { get; set; }
        public DateTimeOffset? CompletedAt { get; set; }
        public ScanStatus Status { get; set; }
        public int FilesScanned { get; set; }
        public int IssuesDetected { get; set; }
        public string ErrorMessage { get; set; } = string.Empty;
    }

    public enum ScanStatus
    {
        Running,
        Completed,
        Failed,
        Cancelled,
    }

    public class LibraryHealthSummary
    {
        public string LibraryPath { get; set; } = string.Empty;
        public int TotalIssues { get; set; }
        public int IssuesOpen { get; set; }
        public int IssuesResolved { get; set; }
    }

    public class LibraryIssueTypeSummary
    {
        public LibraryIssueType Type { get; set; }

        public int Count { get; set; }

        public Dictionary<LibraryIssueSeverity, int> BySeverity { get; set; } = new();
    }

    public class LibraryIssueArtistSummary
    {
        public string Artist { get; set; } = string.Empty;

        public int Count { get; set; }

        public Dictionary<LibraryIssueType, int> ByType { get; set; } = new();
    }

    public class LibraryIssueReleaseSummary
    {
        public string Artist { get; set; } = string.Empty;

        public string Album { get; set; } = string.Empty;

        public string MusicBrainzReleaseId { get; set; } = string.Empty;

        public int Count { get; set; }

        public Dictionary<LibraryIssueType, int> ByType { get; set; } = new();
    }

    public class LibraryIssuePage
    {
        public List<LibraryIssue> Issues { get; set; } = new();

        public int TotalCount { get; set; }
    }

    public class LibraryHealthDashboard
    {
        public LibraryHealthSummary Summary { get; set; } = new();

        public List<LibraryIssueTypeSummary> IssuesByType { get; set; } = new();

        public List<LibraryIssueArtistSummary> IssuesByArtist { get; set; } = new();

        public List<LibraryIssue> Issues { get; set; } = new();

        public int TotalIssues { get; set; }
    }

    public class IssueCodecGroup
    {
        public string Codec { get; set; } = string.Empty;

        public int Count { get; set; }

        public int TranscodeSuspect { get; set; }
    }

    public class LibraryHealthScanRequest
    {
        public string LibraryPath { get; set; } = string.Empty;
        public bool IncludeSubdirectories { get; set; } = true;
        public List<string> FileExtensions { get; set; } = new() { ".flac", ".mp3", ".m4a", ".ogg" };
        public bool SkipPreviouslyScanned { get; set; } = false;
        public int MaxConcurrentFiles { get; set; } = 4;

        /// <summary>
        ///     Gets or sets a value indicating whether lossless files are decoded with ffmpeg to measure their
        ///     spectral lowpass shelf. Requires audio.spectral_analysis.enabled; slower than a tag-only scan.
        /// </summary>
        public bool IncludeSpectralAnalysis { get; set; } = false;
    }

    public class LibraryHealthIssueFilter
    {
        public string LibraryPath { get; set; } = string.Empty;
        public List<LibraryIssueType> Types { get; set; } = new();
        public List<LibraryIssueSeverity> Severities { get; set; } = new();
        public List<LibraryIssueStatus> Statuses { get; set; } = new();
        public string MusicBrainzReleaseId { get; set; } = string.Empty;
        public int Limit { get; set; } = 100;
        public int Offset { get; set; } = 0;
    }
}
