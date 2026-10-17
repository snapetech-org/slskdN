// <copyright file="LibraryHealthController.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.LibraryHealth.API
{
    using System.Collections.Generic;
    using System.Linq;
    using System.Threading;
    using System.Threading.Tasks;
    using Asp.Versioning;
    using Microsoft.AspNetCore.Authorization;
    using Microsoft.AspNetCore.Mvc;
    using Microsoft.Extensions.Logging;
    using slskd.Core.Security;

    /// <summary>
    /// API controller for Library Health (Collection Doctor).
    /// </summary>
    [ApiController]
    [Route("api/library/health")]
    [Route("api/v{version:apiVersion}/library/health")]
    [ApiVersion("0")]
    [Produces("application/json")]
    [ValidateCsrfForCookiesOnly] // CSRF protection for cookie-based auth (exempts JWT/API key)
    public class LibraryHealthController : ControllerBase
    {
        private readonly ILibraryHealthService libraryHealth;
        private readonly ILogger<LibraryHealthController> log;

        public LibraryHealthController(
            ILibraryHealthService libraryHealth,
            ILogger<LibraryHealthController> log)
        {
            this.libraryHealth = libraryHealth;
            this.log = log;
        }

        /// <summary>
        /// Start a library health scan.
        /// </summary>
        /// <param name="request">Scan request parameters.</param>
        /// <param name="ct">Cancellation token.</param>
        /// <returns>Scan ID.</returns>
        [HttpPost("scans")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.AdministratorOnly)]
        public async Task<ActionResult<StartScanResponse>> StartScan(
            [FromBody] LibraryHealthScanRequest request,
            CancellationToken ct)
        {
            if (request == null)
            {
                return BadRequest(new { message = "request body is required" });
            }

            log.LogInformation("Starting library health scan for path: {Path}", request.LibraryPath);

            string scanId;
            try
            {
                scanId = await libraryHealth.StartScanAsync(request, ct);
            }
            catch (LibraryHealthScanAlreadyRunningException ex)
            {
                return Conflict(new { message = "A library health scan is already running", scan_id = ex.ScanId });
            }
            catch (SpectralAnalysisUnavailableException ex)
            {
                return BadRequest(new { message = ex.Message });
            }

            return Ok(new StartScanResponse
            {
                ScanId = scanId,
                Message = "Scan started successfully",
            });
        }

        /// <summary>
        /// Get the status of a library health scan.
        /// </summary>
        /// <param name="scanId">Scan identifier.</param>
        /// <param name="ct">Cancellation token.</param>
        /// <returns>Scan status.</returns>
        [HttpGet("scans/{scanId}")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.AdministratorOnly)]
        public async Task<ActionResult<LibraryHealthScan>> GetScanStatus(
            string scanId,
            CancellationToken ct)
        {
            var scan = await libraryHealth.GetScanStatusAsync(scanId, ct);

            if (scan == null)
            {
                return NotFound(new { message = "Scan not found" });
            }

            return Ok(scan);
        }

        /// <summary>
        /// Get library health summary for a given path.
        /// </summary>
        /// <param name="libraryPath">Path to scan (query parameter).</param>
        /// <param name="ct">Cancellation token.</param>
        /// <returns>Health summary.</returns>
        [HttpGet("summary")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.AdministratorOnly)]
        public async Task<ActionResult<LibraryHealthSummary>> GetSummary(
            [FromQuery] string libraryPath,
            CancellationToken ct)
        {
            if (string.IsNullOrWhiteSpace(libraryPath))
            {
                return BadRequest(new { message = "libraryPath query parameter is required" });
            }

            log.LogInformation("Getting library health summary for path: {Path}", libraryPath);

            var summary = await libraryHealth.GetSummaryAsync(libraryPath, ct);

            return Ok(summary);
        }

        /// <summary>
        /// Get the bounded Library Health dashboard snapshot for a path.
        /// </summary>
        [HttpGet("dashboard")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.AdministratorOnly)]
        public async Task<ActionResult<LibraryHealthDashboard>> GetDashboard(
            [FromQuery] string libraryPath,
            [FromQuery] int artistLimit = 10,
            [FromQuery] int issueLimit = 100,
            CancellationToken ct = default)
        {
            if (string.IsNullOrWhiteSpace(libraryPath))
            {
                return BadRequest(new { message = "libraryPath query parameter is required" });
            }

            if (artistLimit <= 0 || artistLimit > 100 || issueLimit <= 0 || issueLimit > 250)
            {
                return BadRequest(new { message = "artistLimit must be between 1 and 100 and issueLimit must be between 1 and 250" });
            }

            var dashboard = await libraryHealth.GetDashboardAsync(
                libraryPath,
                artistLimit,
                issueLimit,
                ct);
            return Ok(dashboard);
        }

        /// <summary>
        /// Get library health issues with optional filtering.
        /// </summary>
        /// <param name="filter">Filter parameters (from query string).</param>
        /// <param name="ct">Cancellation token.</param>
        /// <returns>List of issues.</returns>
        [HttpGet("issues")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.AdministratorOnly)]
        public async Task<ActionResult<IssuesResponse>> GetIssues(
            [FromQuery] LibraryHealthIssueFilter filter,
            CancellationToken ct)
        {
            if (filter.Limit <= 0 || filter.Limit > 250 || filter.Offset < 0)
            {
                return BadRequest(new { message = "limit must be between 1 and 250 and offset must be non-negative" });
            }

            log.LogInformation(
                "Getting library health issues: Types={Types}, Severities={Severities}, Statuses={Statuses}, Limit={Limit}",
                filter.Types != null ? string.Join(",", filter.Types) : "all",
                filter.Severities != null ? string.Join(",", filter.Severities) : "all",
                filter.Statuses != null ? string.Join(",", filter.Statuses) : "all",
                filter.Limit);

            var page = await libraryHealth.GetIssuePageAsync(filter, ct);

            return Ok(new IssuesResponse
            {
                Issues = page.Issues,
                TotalCount = page.TotalCount,
                Filter = filter
            });
        }

        /// <summary>
        /// Get issues grouped by type.
        /// </summary>
        /// <param name="libraryPath">Path to filter by (optional).</param>
        /// <param name="ct">Cancellation token.</param>
        /// <returns>Issues grouped by type with counts.</returns>
        [HttpGet("issues/by-type")]
        [Authorize]
        public async Task<ActionResult<IssuesByTypeResponse>> GetIssuesByType(
            [FromQuery] string libraryPath,
            CancellationToken ct)
        {
            var grouped = await libraryHealth.GetIssueTypeSummariesAsync(libraryPath, ct);

            return Ok(new IssuesByTypeResponse
            {
                Groups = grouped,
                TotalIssues = grouped.Sum(group => group.Count),
            });
        }

        /// <summary>
        /// Get issues grouped by artist.
        /// </summary>
        /// <param name="limit">Maximum number of artists to return.</param>
        /// <param name="ct">Cancellation token.</param>
        /// <returns>Issues grouped by artist.</returns>
        [HttpGet("issues/by-artist")]
        [Authorize]
        public async Task<ActionResult<IssuesByArtistResponse>> GetIssuesByArtist(
            [FromQuery] int limit = 20,
            CancellationToken ct = default)
        {
            if (limit <= 0 || limit > 100)
            {
                return BadRequest(new { message = "limit must be between 1 and 100" });
            }

            var grouped = await libraryHealth.GetIssueArtistSummariesAsync(string.Empty, limit, ct);

            return Ok(new IssuesByArtistResponse
            {
                Groups = grouped,
                TotalArtists = grouped.Count,
            });
        }

        /// <summary>
        /// Get issues grouped by release.
        /// </summary>
        /// <param name="limit">Maximum number of releases to return.</param>
        /// <param name="ct">Cancellation token.</param>
        /// <returns>Issues grouped by release.</returns>
        [HttpGet("issues/by-release")]
        [Authorize]
        public async Task<ActionResult<IssuesByReleaseResponse>> GetIssuesByRelease(
            [FromQuery] int limit = 20,
            CancellationToken ct = default)
        {
            if (limit <= 0 || limit > 100)
            {
                return BadRequest(new { message = "limit must be between 1 and 100" });
            }

            var grouped = await libraryHealth.GetIssueReleaseSummariesAsync(string.Empty, limit, ct);

            return Ok(new IssuesByReleaseResponse
            {
                Groups = grouped,
                TotalReleases = grouped.Count,
            });
        }

        /// <summary>
        /// Get issues grouped by codec (using issue metadata when available).
        /// </summary>
        /// <param name="ct">Cancellation token.</param>
        /// <returns>Issues grouped by codec.</returns>
        [HttpGet("issues/by-codec")]
        [Authorize]
        public async Task<ActionResult<object>> GetIssuesByCodec(CancellationToken ct = default)
        {
            var grouped = await libraryHealth.GetIssueCodecSummariesAsync(string.Empty, ct);

            return Ok(new
            {
                Groups = grouped,
                TotalIssues = grouped.Sum(group => group.Count),
            });
        }

        /// <summary>
        /// Update the status of a library health issue.
        /// </summary>
        /// <param name="issueId">Issue identifier.</param>
        /// <param name="request">Status update request.</param>
        /// <param name="ct">Cancellation token.</param>
        /// <returns>No content on success.</returns>
        [HttpPatch("issues/{issueId}")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [Authorize]
        public async Task<IActionResult> UpdateIssueStatus(
            string issueId,
            [FromBody] UpdateIssueStatusRequest request,
            CancellationToken ct)
        {
            log.LogInformation("Updating issue {IssueId} status to {Status}", issueId, request.Status);

            await libraryHealth.UpdateIssueStatusAsync(issueId, request.Status, ct);

            return NoContent();
        }

        /// <summary>
        /// Create a remediation job for one or more issues.
        /// </summary>
        /// <param name="request">Remediation request.</param>
        /// <param name="ct">Cancellation token.</param>
        /// <returns>Job ID.</returns>
        [HttpPost("issues/fix")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [Authorize]
        public async Task<ActionResult<RemediationResponse>> CreateRemediationJob(
            [FromBody] RemediationRequest request,
            CancellationToken ct)
        {
            log.LogInformation("Creating remediation job for {Count} issues", request.IssueIds.Count);

            var jobId = await libraryHealth.CreateRemediationJobAsync(request.IssueIds, ct);

            return Ok(new RemediationResponse
            {
                JobId = jobId,
                Message = "Remediation job created",
            });
        }
    }

    // Response DTOs
    public class StartScanResponse
    {
        public string ScanId { get; set; } = string.Empty;
        public string Message { get; set; } = string.Empty;
    }

    public class IssuesResponse
    {
        public List<LibraryIssue> Issues { get; set; } = new();
        public int TotalCount { get; set; }
        public LibraryHealthIssueFilter Filter { get; set; } = new();
    }

    public class IssuesByTypeResponse
    {
        public List<LibraryIssueTypeSummary> Groups { get; set; } = new();
        public int TotalIssues { get; set; }
    }

    public class IssuesByArtistResponse
    {
        public List<LibraryIssueArtistSummary> Groups { get; set; } = new();
        public int TotalArtists { get; set; }
    }

    public class IssuesByReleaseResponse
    {
        public List<LibraryIssueReleaseSummary> Groups { get; set; } = new();
        public int TotalReleases { get; set; }
    }

    public class UpdateIssueStatusRequest
    {
        public LibraryIssueStatus Status { get; set; }
    }

    public class RemediationRequest
    {
        public List<string> IssueIds { get; set; } = new();
    }

    public class RemediationResponse
    {
        public string JobId { get; set; } = string.Empty;
        public string Message { get; set; } = string.Empty;
    }
}
