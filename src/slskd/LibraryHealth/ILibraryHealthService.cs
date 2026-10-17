// <copyright file="ILibraryHealthService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.LibraryHealth
{
    using System;
    using System.Collections.Generic;
    using System.Threading;
    using System.Threading.Tasks;

    public interface ILibraryHealthService
    {
        Task<string> StartScanAsync(LibraryHealthScanRequest request, CancellationToken ct = default);

        Task<LibraryHealthScan?> GetScanStatusAsync(string scanId, CancellationToken ct = default);

        Task<List<LibraryIssue>> GetIssuesAsync(LibraryHealthIssueFilter filter, CancellationToken ct = default);

        Task<LibraryIssuePage> GetIssuePageAsync(LibraryHealthIssueFilter filter, CancellationToken ct = default);

        Task<List<LibraryIssueTypeSummary>> GetIssueTypeSummariesAsync(string libraryPath, CancellationToken ct = default);

        Task<List<LibraryIssueArtistSummary>> GetIssueArtistSummariesAsync(string libraryPath, int limit, CancellationToken ct = default);

        Task<List<LibraryIssueReleaseSummary>> GetIssueReleaseSummariesAsync(string libraryPath, int limit, CancellationToken ct = default);

        Task<List<IssueCodecGroup>> GetIssueCodecSummariesAsync(string libraryPath, CancellationToken ct = default);

        Task<LibraryHealthDashboard> GetDashboardAsync(string libraryPath, int artistLimit, int issueLimit, CancellationToken ct = default);

        Task UpdateIssueStatusAsync(string issueId, LibraryIssueStatus newStatus, CancellationToken ct = default);

        Task<string> CreateRemediationJobAsync(List<string> issueIds, CancellationToken ct = default);

        Task<LibraryHealthSummary> GetSummaryAsync(string libraryPath, CancellationToken ct = default);
    }

    public sealed class LibraryHealthScanAlreadyRunningException : InvalidOperationException
    {
        public LibraryHealthScanAlreadyRunningException(string scanId)
            : base("A library health scan is already running")
        {
            ScanId = scanId;
        }

        public string ScanId { get; }
    }

    public sealed class SpectralAnalysisUnavailableException : InvalidOperationException
    {
        public SpectralAnalysisUnavailableException()
            : base("Spectral analysis is disabled. Set audio.spectral_analysis.enabled to true to request it in a scan.")
        {
        }
    }
}
