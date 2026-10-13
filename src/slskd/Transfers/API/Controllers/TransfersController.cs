// <copyright file="TransfersController.cs" company="slskd Team">
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

// <copyright file="TransfersController.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;

namespace slskd.Transfers.API
{
    using System;
    using System.Collections.Generic;
    using System.ComponentModel.DataAnnotations;
    using System.Linq;
    using System.Linq.Expressions;
    using System.Net;
    using System.Net.Sockets;
    using System.Threading;
    using System.Threading.Tasks;
    using Asp.Versioning;
    using Microsoft.AspNetCore.Authorization;
    using Microsoft.AspNetCore.Mvc;
    using Microsoft.AspNetCore.SignalR;
    using Serilog;
    using slskd.Common.Security;
    using slskd.Core.Security;
    using slskd.Core.Web;
    using slskd.Transfers.AutoReplace;
    using slskd.Transfers.Downloads;

    /// <summary>
    ///     Transfers.
    /// </summary>
    [ApiController]
    [Route("api/v{version:apiVersion}/[controller]")]
    [ApiVersion("0")]
    [Produces("application/json")]
    [Consumes("application/json")]
    [ValidateCsrfForCookiesOnly] // CSRF protection for cookie-based auth (exempts JWT/API key)
    public class TransfersController : ControllerBase
    {
        /// <summary>
        ///     Initializes a new instance of the <see cref="TransfersController"/> class.
        /// </summary>
        /// <param name="optionsSnapshot"></param>
        /// <param name="stateSnapshot"></param>
        /// <param name="transferService"></param>
        /// <param name="autoReplaceService"></param>
        /// <param name="autoReplaceBackgroundService"></param>
        /// <param name="acceleratedDownloads"></param>
        /// <param name="transfersHub"></param>
        public TransfersController(
            ITransferService transferService,
            IOptionsSnapshot<Options> optionsSnapshot,
            IStateSnapshot<State> stateSnapshot,
            IAutoReplaceService autoReplaceService,
            AutoReplaceBackgroundService autoReplaceBackgroundService,
            IAcceleratedDownloadService acceleratedDownloads,
            IHubContext<TransfersHub> transfersHub)
        {
            Transfers = transferService;
            OptionsSnapshot = optionsSnapshot;
            StateSnapshot = stateSnapshot;
            AutoReplace = autoReplaceService;
            AutoReplaceBackgroundService = autoReplaceBackgroundService;
            AcceleratedDownloads = acceleratedDownloads;
            TransfersHub = transfersHub;
        }

        private static SemaphoreSlim DownloadRequestLimiter { get; } = new SemaphoreSlim(2, 2);
        private static object SpeedsCacheSyncRoot { get; } = new object();
        private static TimeSpan SpeedsCacheDuration { get; } = TimeSpan.FromSeconds(2);
        private static DateTime SpeedsCacheExpiresAt { get; set; } = DateTime.MinValue;
        private static object? SpeedsCacheResponse { get; set; }

        private ITransferService Transfers { get; }
        private IOptionsSnapshot<Options> OptionsSnapshot { get; }
        private IStateSnapshot<State> StateSnapshot { get; }
        private IAutoReplaceService AutoReplace { get; }
        private AutoReplaceBackgroundService AutoReplaceBackgroundService { get; }
        private IAcceleratedDownloadService AcceleratedDownloads { get; }
        private IHubContext<TransfersHub> TransfersHub { get; }
        private ILogger Log { get; set; } = Serilog.Log.ForContext<TransfersController>();

        private void NotifyRemoved(global::slskd.Transfers.Transfer transfer)
        {
            if (transfer == null)
            {
                return;
            }

            _ = TransfersHub.EmitTransferRemovedAsync(new TransferRemoved
            {
                Id = transfer.Id,
                RequestId = transfer.RequestId,
                Direction = transfer.Direction,
                Username = transfer.Username,
                Filename = transfer.Filename,
            });
        }

        private static bool IsSuccessfulTerminalTransfer(Soulseek.TransferStates state)
        {
            return state.HasFlag(Soulseek.TransferStates.Completed) &&
                state.HasFlag(Soulseek.TransferStates.Succeeded);
        }

        private static Expression<Func<global::slskd.Transfers.Transfer, bool>> NotSuccessfulTerminalTransferExpression =>
            transfer =>
                (transfer.State & Soulseek.TransferStates.Completed) != Soulseek.TransferStates.Completed ||
                (transfer.State & Soulseek.TransferStates.Succeeded) != Soulseek.TransferStates.Succeeded;

        /// <summary>
        ///     Gets the accelerated download mode status.
        /// </summary>
        /// <returns>The current accelerated download mode state.</returns>
        [HttpGet("downloads/accelerated")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(AcceleratedDownloadState), 200)]
        public IActionResult GetAcceleratedDownloadMode()
        {
            return Ok(AcceleratedDownloads.GetState());
        }

        /// <summary>
        ///     Enables or disables accelerated download mode.
        /// </summary>
        /// <param name="request">The requested accelerated download mode state.</param>
        /// <returns>The updated accelerated download mode state.</returns>
        [HttpPut("downloads/accelerated")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(typeof(AcceleratedDownloadState), 200)]
        [ProducesResponseType(typeof(string), 400)]
        public IActionResult SetAcceleratedDownloadMode([FromBody, Required] AcceleratedDownloadModeRequest request)
        {
            if (request == null)
            {
                return BadRequest("Request is required");
            }

            return Ok(AcceleratedDownloads.SetEnabled(request.Enabled));
        }

        /// <summary>
        ///     Cancels the specified download.
        /// </summary>
        /// <param name="username">The username of the download source.</param>
        /// <param name="id">The id of the download.</param>
        /// <param name="remove">A value indicating whether the tracked download should be removed after cancellation.</param>
        /// <param name="deleteFile">A value indicating whether the underlying file should also be deleted.</param>
        /// <returns></returns>
        /// <response code="204">The download was cancelled successfully.</response>
        /// <response code="404">The specified download was not found.</response>
        [HttpDelete("downloads/{username}/{id}")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(204)]
        [ProducesResponseType(404)]
        public IActionResult CancelDownloadAsync([FromRoute, Required] string username, [FromRoute, Required] string id, [FromQuery] bool remove = false, [FromQuery] bool deleteFile = false)
        {
            username = username?.Trim() ?? string.Empty;
            id = id?.Trim() ?? string.Empty;

            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (string.IsNullOrWhiteSpace(username) || !Guid.TryParse(id, out var guid))
            {
                return BadRequest();
            }

            try
            {
                var download = Transfers.Downloads.Find(t => t.Id == guid);
                if (download == default || !string.Equals(download.Username, username, StringComparison.Ordinal))
                {
                    return NotFound();
                }

                Transfers.Downloads.TryCancel(guid);

                if (remove)
                {
                    Transfers.Downloads.Remove(guid, deleteFile);
                    NotifyRemoved(download);
                }

                return NoContent();
            }
            catch (NotFoundException)
            {
                return NotFound();
            }
        }

        /// <summary>
        ///     Removes downloads that completed successfully. Failed terminal downloads are intentionally retained so they can be retried.
        /// </summary>
        /// <returns></returns>
        /// <response code="204">The downloads were removed successfully.</response>
        [HttpDelete("downloads/all/completed")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(204)]
        public IActionResult ClearCompletedDownloads()
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            var transfers = Transfers.Downloads.List(
                t => t.State.HasFlag(Soulseek.TransferStates.Completed) &&
                    t.State.HasFlag(Soulseek.TransferStates.Succeeded));

            foreach (var transfer in transfers)
            {
                Transfers.Downloads.Remove(transfer.Id);
                NotifyRemoved(transfer);
            }

            return NoContent();
        }

        /// <summary>
        ///     Cancels the specified upload.
        /// </summary>
        /// <param name="username">The username of the upload destination.</param>
        /// <param name="id">The id of the upload.</param>
        /// <param name="remove">A value indicating whether the tracked upload should be removed after cancellation.</param>
        /// <returns></returns>
        /// <response code="204">The upload was cancelled successfully.</response>
        /// <response code="404">The specified upload was not found.</response>
        [HttpDelete("uploads/{username}/{id}")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(204)]
        [ProducesResponseType(404)]
        public IActionResult CancelUpload([FromRoute, Required] string username, [FromRoute, Required] string id, [FromQuery] bool remove = false)
        {
            username = username?.Trim() ?? string.Empty;
            id = id?.Trim() ?? string.Empty;

            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (string.IsNullOrWhiteSpace(username) || !Guid.TryParse(id, out var guid))
            {
                return BadRequest();
            }

            try
            {
                var upload = Transfers.Uploads.Find(t => t.Id == guid);
                if (upload == default || !string.Equals(upload.Username, username, StringComparison.Ordinal))
                {
                    return NotFound();
                }

                Transfers.Uploads.TryCancel(guid);

                if (remove)
                {
                    Transfers.Uploads.Remove(guid);
                    NotifyRemoved(upload);
                }

                return NoContent();
            }
            catch (NotFoundException)
            {
                return NotFound();
            }
        }

        /// <summary>
        ///     Removes uploads that completed successfully. Failed terminal uploads are intentionally retained for visibility.
        /// </summary>
        /// <returns></returns>
        /// <response code="204">The uploads were removed successfully.</response>
        [HttpDelete("uploads/all/completed")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(204)]
        public IActionResult ClearCompletedUploads()
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            // get all the transfers that aren't removed
            var transfers = Transfers.Uploads
                .List(
                    t => t.State.HasFlag(Soulseek.TransferStates.Completed) &&
                        t.State.HasFlag(Soulseek.TransferStates.Succeeded),
                    includeRemoved: false);

            foreach (var transfer in transfers)
            {
                Transfers.Uploads.Remove(transfer.Id);
                NotifyRemoved(transfer);
            }

            return NoContent();
        }

        /// <summary>
        ///     Gets upload diagnostics for listener, share, and recent upload state.
        /// </summary>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("uploads/diagnostics")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(UploadDiagnosticsResponse), 200)]
        public async Task<IActionResult> GetUploadDiagnostics(CancellationToken cancellationToken = default)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            var options = OptionsSnapshot.Value;
            var state = StateSnapshot.Value;
            var uploads = Transfers.Uploads.List(t => true, includeRemoved: true);
            var recentUploads = uploads
                .OrderByDescending(t => t.EnqueuedAt ?? t.StartedAt ?? t.EndedAt ?? t.RequestedAt)
                .Take(25)
                .Select(t => new UploadDiagnosticsResponse.RecentUpload
                {
                    Id = t.Id,
                    Username = t.Username,
                    Filename = t.Filename,
                    State = t.State.ToString(),
                    RequestedAt = t.RequestedAt,
                    EnqueuedAt = t.EnqueuedAt,
                    StartedAt = t.StartedAt,
                    EndedAt = t.EndedAt,
                    BytesTransferred = t.BytesTransferred,
                    Size = t.Size,
                    Exception = t.Exception,
                    Removed = t.Removed,
                })
                .ToList();

            var listenProbe = await ProbeConfiguredListenPortAsync(
                options.Soulseek.ListenIpAddress,
                options.Soulseek.ListenPort,
                cancellationToken);

            var warnings = new List<string>();

            if (state.Server.IsConnected && state.Server.IsLoggedIn && !listenProbe.Succeeded)
            {
                warnings.Add("Local TCP probe could not connect to the configured Soulseek listener; uploads from remote peers will probably fail until the listener is reachable.");
            }

            if (IPAddress.TryParse(options.Soulseek.ListenIpAddress, out var listenAddress) && IPAddress.IsLoopback(listenAddress))
            {
                warnings.Add("Soulseek listen address is loopback; remote peers cannot connect to 127.0.0.1/::1 from outside this host.");
            }

            if (state.Shares.Files == 0)
            {
                warnings.Add("No shared files are currently indexed; remote requests may be rejected as File not shared.");
            }

            if (state.Shares.ScanPending || state.Shares.Scanning)
            {
                warnings.Add("Share scan is pending or running; upload availability may not match the filesystem until scanning completes.");
            }

            if (uploads.Count == 0)
            {
                warnings.Add("No upload records are present. If a remote user attempted an upload, this usually means the request did not reach slskdN or failed before enqueue.");
            }

            return Ok(new UploadDiagnosticsResponse
            {
                GeneratedAt = DateTime.UtcNow,
                SoulseekState = state.Server.State.ToString(),
                IsConnected = state.Server.IsConnected,
                IsLoggedIn = state.Server.IsLoggedIn,
                ListenIpAddress = options.Soulseek.ListenIpAddress,
                ListenPort = options.Soulseek.ListenPort,
                LocalListenProbe = listenProbe,
                UploadSlots = options.Global.Upload.Slots,
                UploadSpeedLimit = options.Global.Upload.SpeedLimit,
                ShareDirectories = state.Shares.Directories,
                ShareFiles = state.Shares.Files,
                ShareScanPending = state.Shares.ScanPending,
                ShareScanning = state.Shares.Scanning,
                TotalUploadRecords = uploads.Count,
                ActiveUploads = uploads.Count(t => !t.State.HasFlag(Soulseek.TransferStates.Completed)),
                FailedUploads = uploads.Count(t => t.State.HasFlag(Soulseek.TransferStates.Completed) && !t.State.HasFlag(Soulseek.TransferStates.Succeeded)),
                SucceededUploads = uploads.Count(t => t.State.HasFlag(Soulseek.TransferStates.Completed | Soulseek.TransferStates.Succeeded)),
                RecentUploads = recentUploads,
                Warnings = warnings,
            });
        }

        /// <summary>
        ///     Enqueues the specified download.
        /// </summary>
        /// <param name="username">The username of the download source.</param>
        /// <param name="requests">The list of download requests.</param>
        /// <param name="destination">An optional completed-file destination directory.</param>
        /// <returns></returns>
        /// <response code="201">The download was successfully enqueued.</response>
        /// <response code="403">The download was rejected.</response>
        /// <response code="500">An unexpected error was encountered.</response>
        [HttpPost("downloads/{username}")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(201)]
        [ProducesResponseType(typeof(string), 403)]
        [ProducesResponseType(typeof(string), 500)]
        public async Task<IActionResult> EnqueueAsync([FromRoute, Required] string username, [FromBody, Required] IEnumerable<QueueDownloadRequest> requests, [FromQuery] string? destination = null)
        {
            username = username?.Trim() ?? string.Empty;

            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (!ModelState.IsValid)
            {
                return BadRequest(ModelState.GetReadableString());
            }

            var requestList = requests?.ToList();

            if (requestList == null || !requestList.Any())
            {
                return BadRequest("At least one file is required");
            }

            if (requestList.Any(r => r is null))
            {
                return BadRequest("One or more records in the request are null");
            }

            if (string.IsNullOrWhiteSpace(username))
            {
                return BadRequest("Username is required");
            }

            var normalizedRequests = requestList
                .Select(r => new QueueDownloadRequest
                {
                    Filename = r!.Filename?.Trim() ?? string.Empty,
                    Size = r.Size,
                    BatchId = r.BatchId,
                    BatchExternalId = r.BatchExternalId,
                    SearchId = r.SearchId,
                    SearchText = r.SearchText,
                    BitRate = r.BitRate,
                    SampleRate = r.SampleRate,
                    BitDepth = r.BitDepth,
                    Length = r.Length,
                })
                .ToList();

            if (normalizedRequests.Any(r => string.IsNullOrWhiteSpace(r.Filename)))
            {
                return BadRequest("Each file requires a non-empty filename");
            }

            var blockedDownloads = normalizedRequests
                .Select(request => new
                {
                    request.Filename,
                    Exclusion = DownloadFilter.GetMatchingExclusion(
                        request.Filename,
                        OptionsSnapshot.Value.Filters.Download.Exclude),
                })
                .Where(request => request.Exclusion is not null)
                .ToList();

            if (blockedDownloads.Count == normalizedRequests.Count)
            {
                Log.Information(
                    "Rejected download request for {Username}; all {Count} file(s) matched the global download policy",
                    LoggingSanitizer.SanitizeExternalIdentifier(username),
                    blockedDownloads.Count);
                return StatusCode(
                    403,
                    new
                    {
                        type = "download_blocked",
                        title = "Download blocked",
                        detail = "Every requested file matched a configured global download exclusion.",
                        blocked = blockedDownloads,
                    });
            }

            var destinationDirectory = Destinations.DownloadDestinationResolver.NormalizeExplicitPath(OptionsSnapshot.Value, destination);
            if (!string.IsNullOrWhiteSpace(destination) && destinationDirectory == null)
            {
                return BadRequest("Destination must be an absolute path inside the configured downloads directory or a configured destination folder");
            }

            if (!DownloadRequestLimiter.Wait(0))
            {
                return StatusCode(429, "Only one concurrent operation is permitted. Wait until the previous request completes");
            }

            try
            {
                var batchId = normalizedRequests.Count > 1
                    ? normalizedRequests.FirstOrDefault(r => r.BatchId.HasValue)?.BatchId ?? Guid.NewGuid()
                    : normalizedRequests.FirstOrDefault()?.BatchId;

                var (enqueued, failed) = await Transfers.Downloads.EnqueueAsync(
                    username,
                    normalizedRequests.Select(r => new global::slskd.Transfers.Downloads.DownloadEnqueueRequest
                    {
                        Filename = r.Filename,
                        Size = r.Size,
                        BatchId = r.BatchId ?? batchId,
                        BatchExternalId = r.BatchExternalId,
                        DestinationDirectory = destinationDirectory,
                        SearchId = r.SearchId,
                        SearchText = r.SearchText,
                        BitRate = r.BitRate,
                        SampleRate = r.SampleRate,
                        BitDepth = r.BitDepth,
                        Length = r.Length,
                    }));

                return StatusCode(201, new { Enqueued = enqueued, Failed = failed, Blocked = blockedDownloads });
            }
            catch (Exception ex)
            {
                Log.Error("Failed to enqueue {Count} files for {Username}: {Exception}", requestList.Count,
                    LoggingSanitizer.SanitizeExternalIdentifier(username), LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                return StatusCode(500, "Failed to enqueue downloads");
            }
            finally
            {
                DownloadRequestLimiter.Release();
            }
        }

        /// <summary>
        ///     Gets an initial transfer snapshot or only records changed after a cursor.
        /// </summary>
        /// <param name="since">Optional Unix timestamp in milliseconds returned by the prior response for incremental changes.</param>
        /// <param name="includeCompleted">Whether an initial snapshot should include successful terminal transfers.</param>
        /// <param name="limit">Optional page size for a bounded initial snapshot, from 1 through 500.</param>
        /// <param name="direction">Optional direction to page: download or upload.</param>
        /// <param name="asOf">Snapshot watermark returned by the first page, in Unix milliseconds.</param>
        /// <param name="afterRequestedAt">Request time of the last transfer from the previous page.</param>
        /// <param name="afterId">ID of the last transfer from the previous page.</param>
        /// <returns>A server-watermarked transfer change set.</returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="400">The cursor was invalid.</response>
        [HttpGet("changes")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(TransferChangesResponse), 200)]
        [ProducesResponseType(typeof(string), 400)]
        public IActionResult GetTransferChanges(
            [FromQuery] long? since = null,
            [FromQuery] bool includeCompleted = true,
            [FromQuery] int? limit = null,
            [FromQuery] string? direction = null,
            [FromQuery] long? asOf = null,
            [FromQuery] DateTimeOffset? afterRequestedAt = null,
            [FromQuery] Guid? afterId = null)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (limit.HasValue && (limit.Value < 1 || limit.Value > 500))
            {
                return BadRequest("limit must be between 1 and 500");
            }

            if (!limit.HasValue &&
                (!string.IsNullOrWhiteSpace(direction) || asOf.HasValue || afterRequestedAt.HasValue || afterId.HasValue))
            {
                return BadRequest("direction, asOf, and continuation values require limit");
            }

            if (afterRequestedAt.HasValue != afterId.HasValue)
            {
                return BadRequest("afterRequestedAt and afterId must be supplied together");
            }

            if ((afterRequestedAt.HasValue || afterId.HasValue) && !asOf.HasValue)
            {
                return BadRequest("continuation values require asOf");
            }

            if (since.HasValue &&
                (limit.HasValue || asOf.HasValue || afterRequestedAt.HasValue || afterId.HasValue || !string.IsNullOrWhiteSpace(direction)))
            {
                return BadRequest("since cannot be combined with initial snapshot paging");
            }

            Soulseek.TransferDirection? pageDirection = null;
            if (!string.IsNullOrWhiteSpace(direction))
            {
                if (!Enum.TryParse<Soulseek.TransferDirection>(direction.Trim(), ignoreCase: true, out var parsedDirection) ||
                    parsedDirection is not (Soulseek.TransferDirection.Download or Soulseek.TransferDirection.Upload))
                {
                    return BadRequest("direction must be 'download' or 'upload'");
                }

                pageDirection = parsedDirection;
            }

            DateTime? changedSince = null;
            if (since.HasValue)
            {
                if (since.Value < 0)
                {
                    return BadRequest("since must be a non-negative Unix timestamp in milliseconds");
                }

                try
                {
                    changedSince = DateTimeOffset.FromUnixTimeMilliseconds(since.Value).UtcDateTime;
                }
                catch (ArgumentOutOfRangeException)
                {
                    return BadRequest("since is outside the supported Unix timestamp range");
                }
            }

            DateTime snapshotAt;
            if (asOf.HasValue)
            {
                if (asOf.Value < 0)
                {
                    return BadRequest("asOf must be a non-negative Unix timestamp in milliseconds");
                }

                try
                {
                    snapshotAt = DateTimeOffset.FromUnixTimeMilliseconds(asOf.Value).UtcDateTime;
                }
                catch (ArgumentOutOfRangeException)
                {
                    return BadRequest("asOf is outside the supported Unix timestamp range");
                }
            }
            else
            {
                var watermark = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
                snapshotAt = DateTimeOffset.FromUnixTimeMilliseconds(watermark).UtcDateTime;
            }

            Expression<Func<global::slskd.Transfers.Transfer, bool>> filter;
            if (changedSince.HasValue)
            {
                filter = transfer => transfer.UpdatedAt > changedSince.Value && transfer.UpdatedAt <= snapshotAt;
            }
            else if (!includeCompleted)
            {
                filter = transfer =>
                    transfer.UpdatedAt <= snapshotAt &&
                    ((transfer.State & Soulseek.TransferStates.Completed) != Soulseek.TransferStates.Completed ||
                     (transfer.State & Soulseek.TransferStates.Succeeded) != Soulseek.TransferStates.Succeeded);
            }
            else
            {
                filter = transfer => transfer.UpdatedAt <= snapshotAt;
            }

            var includeRemoved = changedSince.HasValue;
            List<global::slskd.Transfers.Transfer> transfers;
            var hasMore = false;
            DateTimeOffset? nextAfterRequestedAt = null;
            Guid? nextAfterId = null;

            if (limit.HasValue)
            {
                var afterTime = afterRequestedAt?.UtcDateTime;
                var fetchLimit = limit.Value + 1;
                var candidates = new List<global::slskd.Transfers.Transfer>();

                if (!pageDirection.HasValue || pageDirection == Soulseek.TransferDirection.Download)
                {
                    candidates.AddRange(Transfers.Downloads.ListPage(
                        filter,
                        includeRemoved: false,
                        afterRequestedAt: afterTime,
                        afterId,
                        limit: fetchLimit));
                }

                if (!pageDirection.HasValue || pageDirection == Soulseek.TransferDirection.Upload)
                {
                    candidates.AddRange(Transfers.Uploads.ListPage(
                        filter,
                        includeRemoved: false,
                        afterRequestedAt: afterTime,
                        afterId,
                        limit: fetchLimit));
                }

                transfers = candidates
                    .OrderByDescending(transfer => transfer.RequestedAt)
                    .ThenByDescending(transfer => transfer.Id)
                    .Take(fetchLimit)
                    .ToList();

                hasMore = transfers.Count > limit.Value;
                if (hasMore)
                {
                    transfers.RemoveAt(transfers.Count - 1);
                    var last = transfers[^1];
                    nextAfterRequestedAt = new DateTimeOffset(DateTime.SpecifyKind(last.RequestedAt, DateTimeKind.Utc));
                    nextAfterId = last.Id;
                }
            }
            else
            {
                transfers = new List<global::slskd.Transfers.Transfer>();
                transfers.AddRange(Transfers.Downloads.List(filter, includeRemoved));
                transfers.AddRange(Transfers.Uploads.List(filter, includeRemoved));
            }

            return Ok(new TransferChangesResponse
            {
                Counts = new TransferCounts
                {
                    Download = Transfers.Downloads.Count(),
                    Upload = Transfers.Uploads.Count(),
                },
                Cursor = new DateTimeOffset(snapshotAt).ToUnixTimeMilliseconds(),
                HasMore = hasMore,
                NextAfterRequestedAt = nextAfterRequestedAt,
                NextAfterId = nextAfterId,
                Transfers = transfers,
            });
        }

        /// <summary>
        ///     Gets a stable page of successful transfer history.
        /// </summary>
        /// <param name="direction">The transfer direction: download or upload.</param>
        /// <param name="asOf">Optional Unix timestamp in milliseconds returned by the first history page.</param>
        /// <param name="offset">The number of successful history records already requested.</param>
        /// <param name="limit">The page size, from 1 through 500.</param>
        /// <returns>A stable page of successful transfer history.</returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="400">A history parameter was invalid.</response>
        [HttpGet("history")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(TransferHistoryResponse), 200)]
        [ProducesResponseType(typeof(string), 400)]
        public IActionResult GetTransferHistory(
            [FromQuery] string direction,
            [FromQuery] long? asOf = null,
            [FromQuery] int offset = 0,
            [FromQuery] int limit = 250)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            direction = direction?.Trim() ?? string.Empty;
            if (!direction.Equals("download", StringComparison.OrdinalIgnoreCase) &&
                !direction.Equals("upload", StringComparison.OrdinalIgnoreCase))
            {
                return BadRequest("direction must be 'download' or 'upload'");
            }

            if (offset < 0)
            {
                return BadRequest("offset must be greater than or equal to zero");
            }

            if (limit < 1 || limit > 500)
            {
                return BadRequest("limit must be between 1 and 500");
            }

            DateTime historyAsOf;
            if (asOf.HasValue)
            {
                if (asOf.Value < 0)
                {
                    return BadRequest("asOf must be a non-negative Unix timestamp in milliseconds");
                }

                try
                {
                    historyAsOf = DateTimeOffset.FromUnixTimeMilliseconds(asOf.Value).UtcDateTime;
                }
                catch (ArgumentOutOfRangeException)
                {
                    return BadRequest("asOf is outside the supported Unix timestamp range");
                }
            }
            else
            {
                var watermark = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
                historyAsOf = DateTimeOffset.FromUnixTimeMilliseconds(watermark).UtcDateTime;
            }

            var page = direction.Equals("download", StringComparison.OrdinalIgnoreCase)
                ? Transfers.Downloads.ListCompleted(historyAsOf, offset, limit + 1)
                : Transfers.Uploads.ListCompleted(historyAsOf, offset, limit + 1);
            var transfers = page.Take(limit).ToList();

            return Ok(new TransferHistoryResponse
            {
                AsOf = new DateTimeOffset(historyAsOf).ToUnixTimeMilliseconds(),
                HasMore = page.Count > limit,
                NextOffset = offset + transfers.Count,
                Transfers = transfers,
            });
        }

        /// <summary>
        ///     Gets a flat list of transfers across both directions.
        /// </summary>
        /// <remarks>
        ///     Unlike <c>downloads</c>/<c>uploads</c> this returns an ungrouped array so the
        ///     client can maintain a stable, id-keyed store and patch rows incrementally.
        /// </remarks>
        /// <param name="direction">Optional direction filter: <c>download</c> or <c>upload</c>. Omit for both.</param>
        /// <param name="includeCompleted">Whether to include successfully completed transfers.</param>
        /// <param name="includeRemoved">Whether to include records flagged as removed.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="400">The direction filter was invalid.</response>
        [HttpGet]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(IEnumerable<global::slskd.Transfers.Transfer>), 200)]
        [ProducesResponseType(typeof(string), 400)]
        public IActionResult GetTransfers([FromQuery] string? direction = null, [FromQuery] bool includeCompleted = true, [FromQuery] bool includeRemoved = false)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            var wantDownloads = true;
            var wantUploads = true;

            if (!string.IsNullOrWhiteSpace(direction))
            {
                if (direction.Equals("download", StringComparison.OrdinalIgnoreCase))
                {
                    wantUploads = false;
                }
                else if (direction.Equals("upload", StringComparison.OrdinalIgnoreCase))
                {
                    wantDownloads = false;
                }
                else
                {
                    return BadRequest("direction must be 'download' or 'upload' when provided");
                }
            }

            var result = new List<global::slskd.Transfers.Transfer>();

            if (wantDownloads)
            {
                result.AddRange(Transfers.Downloads.List(
                    expression: includeCompleted ? null : NotSuccessfulTerminalTransferExpression,
                    includeRemoved: includeRemoved));
            }

            if (wantUploads)
            {
                Expression<Func<global::slskd.Transfers.Transfer, bool>> uploadFilter =
                    includeCompleted ? t => true : NotSuccessfulTerminalTransferExpression;

                result.AddRange(Transfers.Uploads.List(
                    expression: uploadFilter,
                    includeRemoved: includeRemoved));
            }

            return Ok(result);
        }

        /// <summary>
        ///     Gets all downloads.
        /// </summary>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <remarks>
        ///     Deprecated. Prefer <c>GET /api/v0/downloads/requests</c>, which returns one
        ///     row per user-facing request and is stable across source swaps.
        /// </remarks>
        [HttpGet("downloads")]
        [Authorize(Policy = AuthPolicy.Any)]
        [DeprecatedEndpoint(successor: "/api/v0/downloads/requests")]
        [ProducesResponseType(200)]
        public IActionResult GetDownloadsAsync([FromQuery] bool includeRemoved = false, [FromQuery] bool includeCompleted = true)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            var downloads = Transfers.Downloads.List(
                expression: includeCompleted ? null : NotSuccessfulTerminalTransferExpression,
                includeRemoved: includeRemoved);

            var response = downloads.GroupBy(t => t.Username).Select(grouping => new UserResponse()
            {
                Username = grouping.Key,
                Directories = grouping.GroupBy(g => g.Filename.DirectoryName()).Select(d => new DirectoryResponse()
                {
                    Directory = d.Key,
                    FileCount = d.Count(),
                    Files = d.ToList(),
                }),
            });

            return Ok(response);
        }

        /// <summary>
        ///     Gets all downloads for the specified username.
        /// </summary>
        /// <param name="username"></param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("downloads/{username}")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(200)]
        public IActionResult GetDownloadsAsync([FromRoute, Required] string username)
        {
            username = username?.Trim() ?? string.Empty;

            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (string.IsNullOrWhiteSpace(username))
            {
                return BadRequest();
            }

            var downloads = Transfers.Downloads.List(d => d.Username == username);

            if (!downloads.Any())
            {
                return NotFound();
            }

            var response = new UserResponse()
            {
                Username = username,
                Directories = downloads.GroupBy(g => g.Filename.DirectoryName()).Select(d => new DirectoryResponse()
                {
                    Directory = d.Key,
                    FileCount = d.Count(),
                    Files = d.ToList(),
                }),
            };

            return Ok(response);
        }

        /// <summary>
        ///     Gets downloads associated with the specified batch id.
        /// </summary>
        /// <param name="id">The batch id.</param>
        /// <returns>The batch response.</returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="400">The batch id is invalid.</response>
        /// <response code="404">The batch was not found.</response>
        [HttpGet("downloads/batches/{id}")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(DownloadBatchResponse), 200)]
        [ProducesResponseType(400)]
        [ProducesResponseType(404)]
        public IActionResult GetDownloadBatch([FromRoute, Required] string id)
        {
            id = id?.Trim() ?? string.Empty;

            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (!Guid.TryParse(id, out var batchId))
            {
                return BadRequest();
            }

            var downloads = Transfers.Downloads
                .List(t => t.Direction == Soulseek.TransferDirection.Download && t.BatchId == batchId)
                .OrderBy(t => t.RequestedAt)
                .ThenBy(t => t.Filename)
                .ToList();

            if (downloads.Count == 0)
            {
                return NotFound();
            }

            return Ok(new DownloadBatchResponse
            {
                Id = batchId,
                Transfers = downloads,
                TransferCount = downloads.Count,
                CompletedCount = downloads.Count(t => t.State.HasFlag(Soulseek.TransferStates.Completed)),
                SucceededCount = downloads.Count(t => IsSuccessfulTerminalTransfer(t.State)),
                FailedCount = downloads.Count(t =>
                    t.State.HasFlag(Soulseek.TransferStates.Completed) &&
                    !t.State.HasFlag(Soulseek.TransferStates.Succeeded)),
            });
        }

        /// <summary>
        ///     Gets a single download by username and id.
        /// </summary>
        /// <remarks>
        ///     Deprecated. Prefer <c>GET /api/v0/downloads/requests/{requestId}</c> which
        ///     returns the request plus the full attempt history.
        /// </remarks>
        /// <param name="username">The owning user.</param>
        /// <param name="id">The transfer id (Guid).</param>
        [HttpGet("downloads/{username}/{id}")]
        [Authorize(Policy = AuthPolicy.Any)]
        [DeprecatedEndpoint(successor: "/api/v0/downloads/requests/{id}")]
        [ProducesResponseType(typeof(API.Transfer), 200)]
        [ProducesResponseType(404)]
        public IActionResult GetDownload([FromRoute, Required] string username, [FromRoute, Required] string id)
        {
            username = username?.Trim() ?? string.Empty;
            id = id?.Trim() ?? string.Empty;

            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (string.IsNullOrWhiteSpace(username) || !Guid.TryParse(id, out var guid))
            {
                return BadRequest();
            }

            var download = Transfers.Downloads.Find(t => t.Id == guid);

            if (download == default || !string.Equals(download.Username, username, StringComparison.Ordinal))
            {
                return NotFound();
            }

            return Ok(download);
        }

        /// <summary>
        ///     Gets the download for the specified username matching the specified filename, and requests
        ///     the current place in the remote queue of the specified download.
        /// </summary>
        /// <param name="username">The username of the download source.</param>
        /// <param name="id">The id of the download.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="204">The queue position is currently unavailable.</response>
        /// <response code="404">The specified download was not found.</response>
        [HttpGet("downloads/{username}/{id}/position")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(int), 200)]
        [ProducesResponseType(204)]
        [ProducesResponseType(404)]
        public async Task<IActionResult> GetPlaceInQueueAsync([FromRoute, Required] string username, [FromRoute, Required] string id)
        {
            username = username?.Trim() ?? string.Empty;
            id = id?.Trim() ?? string.Empty;

            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (string.IsNullOrWhiteSpace(username) || !Guid.TryParse(id, out var guid))
            {
                return BadRequest();
            }

            try
            {
                var download = Transfers.Downloads.Find(t => t.Id == guid);
                if (download == default || !string.Equals(download.Username, username, StringComparison.Ordinal))
                {
                    return NotFound();
                }

                var place = await Transfers.Downloads.GetPlaceInQueueAsync(guid);
                return Ok(place);
            }
            catch (NotFoundException)
            {
                return NotFound();
            }
            catch (TimeoutException)
            {
                Log.Debug("Timed out getting place in queue for {Username}/{TransferId}", LoggingSanitizer.SanitizeExternalIdentifier(username), guid);
                return NoContent();
            }
            catch (Exception ex)
            {
                Log.Debug("Queue position unavailable for {Username}/{TransferId}: {Exception}",
                    LoggingSanitizer.SanitizeExternalIdentifier(username), guid, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                return NoContent();
            }
        }

        /// <summary>
        ///     Gets real-time transfer speeds (total, soulseek, mesh).
        /// </summary>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("speeds")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(200)]
        public IActionResult GetSpeeds()
        {
            lock (SpeedsCacheSyncRoot)
            {
                if (DateTime.UtcNow < SpeedsCacheExpiresAt && SpeedsCacheResponse != null)
                {
                    return Ok(SpeedsCacheResponse);
                }

                SpeedsCacheResponse = GetSpeedsResponse();
                SpeedsCacheExpiresAt = DateTime.UtcNow.Add(SpeedsCacheDuration);

                return Ok(SpeedsCacheResponse);
            }
        }

        private object GetSpeedsResponse()
        {
            var snapshot = Transfers.GetSpeedSnapshot();
            var totalDownloadSpeed = snapshot.DownloadSpeed;
            var totalUploadSpeed = snapshot.UploadSpeed;
            var totalSpeed = totalDownloadSpeed + totalUploadSpeed;

            // Current transfer service telemetry is Soulseek-based; mesh chunk transfers report separately when enabled.
            var soulseekSpeed = totalSpeed;
            var meshSpeed = 0.0;

            return new
            {
                total = totalSpeed,
                soulseek = soulseekSpeed,
                mesh = meshSpeed,
                download = totalDownloadSpeed,
                upload = totalUploadSpeed,
                sessionBytesDownloaded = snapshot.DownloadedBytes,
                sessionBytesUploaded = snapshot.UploadedBytes,
                sessionBytesTotal = snapshot.DownloadedBytes + snapshot.UploadedBytes,
            };
        }

        /// <summary>
        ///     Gets all uploads.
        /// </summary>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("uploads")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(200)]
        public IActionResult GetUploads([FromQuery] bool includeRemoved = false, [FromQuery] bool includeCompleted = true)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            // todo: refactor this so it doesn't return the world. start and end time params
            // should be required.  consider pagination.
            var uploads = Transfers.Uploads.List(
                expression: includeCompleted ? t => true : NotSuccessfulTerminalTransferExpression,
                includeRemoved: includeRemoved);

            var response = uploads.GroupBy(t => t.Username).Select(grouping => new UserResponse()
            {
                Username = grouping.Key,
                Directories = grouping.GroupBy(g => g.Filename.DirectoryName()).Select(d => new DirectoryResponse()
                {
                    Directory = d.Key,
                    FileCount = d.Count(),
                    Files = d.ToList(),
                }),
            });

            return Ok(response);
        }

        private static async Task<UploadDiagnosticsResponse.ListenProbe> ProbeConfiguredListenPortAsync(
            string listenIpAddress,
            int listenPort,
            CancellationToken cancellationToken)
        {
            var target = ResolveLocalProbeAddress(listenIpAddress);
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(TimeSpan.FromMilliseconds(750));

            try
            {
                using var client = new TcpClient(target.AddressFamily);
                var started = DateTime.UtcNow;
                await client.ConnectAsync(target, listenPort, timeout.Token);

                return new UploadDiagnosticsResponse.ListenProbe
                {
                    TargetIpAddress = target.ToString(),
                    Port = listenPort,
                    Succeeded = true,
                    LatencyMilliseconds = (DateTime.UtcNow - started).TotalMilliseconds,
                };
            }
            catch (Exception ex) when (ex is SocketException || ex is OperationCanceledException || ex is TimeoutException)
            {
                return new UploadDiagnosticsResponse.ListenProbe
                {
                    TargetIpAddress = target.ToString(),
                    Port = listenPort,
                    Succeeded = false,
                    Error = ex.Message,
                };
            }
        }

        private static IPAddress ResolveLocalProbeAddress(string listenIpAddress)
        {
            if (!IPAddress.TryParse(listenIpAddress, out var address))
            {
                return IPAddress.Loopback;
            }

            if (IPAddress.Any.Equals(address))
            {
                return IPAddress.Loopback;
            }

            if (IPAddress.IPv6Any.Equals(address))
            {
                return IPAddress.IPv6Loopback;
            }

            return address;
        }

        /// <summary>
        ///     Gets all uploads for the specified username.
        /// </summary>
        /// <param name="username"></param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("uploads/{username}")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(200)]
        public IActionResult GetUploads([FromRoute, Required] string username)
        {
            username = username?.Trim() ?? string.Empty;

            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (string.IsNullOrWhiteSpace(username))
            {
                return BadRequest();
            }

            var uploads = Transfers.Uploads.List(d => d.Username == username, includeRemoved: false);

            if (!uploads.Any())
            {
                return NotFound();
            }

            var response = new UserResponse()
            {
                Username = username,
                Directories = uploads.GroupBy(g => g.Filename.DirectoryName()).Select(d => new DirectoryResponse()
                {
                    Directory = d.Key,
                    FileCount = d.Count(),
                    Files = d.ToList(),
                }),
            };

            return Ok(response);
        }

        /// <summary>
        ///     Gets the upload for the specified username matching the specified filename.
        /// </summary>
        /// <param name="username">The username of the upload destination.</param>
        /// <param name="id">The id of the upload.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("uploads/{username}/{id}")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(200)]
        public IActionResult GetUploads([FromRoute, Required] string username, [FromRoute, Required] string id)
        {
            username = username?.Trim() ?? string.Empty;
            id = id?.Trim() ?? string.Empty;

            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (string.IsNullOrWhiteSpace(username) || !Guid.TryParse(id, out var guid))
            {
                return BadRequest();
            }

            var upload = Transfers.Uploads.Find(t => t.Id == guid);

            if (upload == default || !string.Equals(upload.Username, username, StringComparison.Ordinal))
            {
                return NotFound();
            }

            return Ok(upload);
        }

        /// <summary>
        ///     Gets all stuck downloads (candidates for auto-replacement).
        /// </summary>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("downloads/stuck")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(200)]
        public IActionResult GetStuckDownloads()
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            var stuckDownloads = AutoReplace.GetStuckDownloads();
            return Ok(stuckDownloads);
        }

        /// <summary>
        ///     Finds alternative sources for a stuck download.
        /// </summary>
        /// <param name="request">The find alternative request.</param>
        /// <param name="cancellationToken">Cancellation token.</param>
        /// <returns></returns>
        /// <response code="200">Alternatives were found successfully.</response>
        [HttpPost("downloads/find-alternative")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(200)]
        public async Task<IActionResult> FindAlternativeAsync(
            [FromBody] FindAlternativeRequest request,
            CancellationToken cancellationToken = default)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (request == null)
            {
                return BadRequest();
            }

            var alternatives = await AutoReplace.FindAlternativesAsync(request, cancellationToken);
            return Ok(alternatives);
        }

        /// <summary>
        ///     Replaces a stuck download with an alternative source.
        /// </summary>
        /// <param name="request">The replace download request.</param>
        /// <param name="cancellationToken">Cancellation token.</param>
        /// <returns></returns>
        /// <response code="200">The download was replaced successfully.</response>
        /// <response code="500">Failed to replace the download.</response>
        [HttpPost("downloads/replace")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(200)]
        [ProducesResponseType(500)]
        public async Task<IActionResult> ReplaceDownloadAsync(
            [FromBody] ReplaceDownloadRequest request,
            CancellationToken cancellationToken = default)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (request == null)
            {
                return BadRequest();
            }

            var success = await AutoReplace.ReplaceDownloadAsync(request, cancellationToken);
            if (success)
            {
                return Ok(new { success = true });
            }

            return StatusCode(500, new { success = false, error = "Failed to replace download" });
        }

        /// <summary>
        ///     Processes all stuck downloads and attempts auto-replacement.
        /// </summary>
        /// <param name="request">The auto-replace request.</param>
        /// <param name="cancellationToken">Cancellation token.</param>
        /// <returns></returns>
        /// <response code="200">The auto-replace process completed.</response>
        [HttpPost("downloads/auto-replace")]
        [Authorize(Policy = AuthPolicy.Any, Roles = AuthRole.ReadWriteOrAdministrator)]
        [ProducesResponseType(typeof(AutoReplaceResult), 200)]
        public async Task<IActionResult> AutoReplaceAsync(
            [FromBody] AutoReplaceRequest request,
            CancellationToken cancellationToken = default)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            if (request == null)
            {
                return BadRequest();
            }

            var result = await AutoReplace.ProcessStuckDownloadsAsync(request, cancellationToken);
            return Ok(result);
        }

        /// <summary>
        ///     Gets the auto-replace status.
        /// </summary>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("downloads/auto-replace/status")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(200)]
        public IActionResult GetAutoReplaceStatus()
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            var stuckCount = AutoReplace.GetStuckDownloads().Count();
            var status = AutoReplaceBackgroundService.GetStatus();
            return Ok(new { stuckCount, enabled = status.Enabled, intervalSeconds = status.IntervalSeconds });
        }

        /// <summary>
        ///     Gets download history statistics grouped by username.
        /// </summary>
        /// <returns>Dictionary of usernames to download statistics.</returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("downloads/user-stats")]
        [Authorize(Policy = AuthPolicy.Any)]
        [ProducesResponseType(typeof(Dictionary<string, UserDownloadStats>), 200)]
        public async Task<IActionResult> GetUserDownloadStats(CancellationToken cancellationToken = default)
        {
            if (Program.IsRelayAgent)
            {
                return Forbid();
            }

            return Ok(await Transfers.GetUserDownloadStatsAsync(cancellationToken));
        }
    }

    public class AcceleratedDownloadModeRequest
    {
        public bool Enabled { get; set; }
    }

    public class UploadDiagnosticsResponse
    {
        public DateTime GeneratedAt { get; set; }
        public string SoulseekState { get; set; } = string.Empty;
        public bool IsConnected { get; set; }
        public bool IsLoggedIn { get; set; }
        public string ListenIpAddress { get; set; } = string.Empty;
        public int ListenPort { get; set; }
        public ListenProbe LocalListenProbe { get; set; } = new();
        public int UploadSlots { get; set; }
        public int UploadSpeedLimit { get; set; }
        public int ShareDirectories { get; set; }
        public int ShareFiles { get; set; }
        public bool ShareScanPending { get; set; }
        public bool ShareScanning { get; set; }
        public int TotalUploadRecords { get; set; }
        public int ActiveUploads { get; set; }
        public int FailedUploads { get; set; }
        public int SucceededUploads { get; set; }
        public IReadOnlyList<RecentUpload> RecentUploads { get; set; } = Array.Empty<RecentUpload>();
        public IReadOnlyList<string> Warnings { get; set; } = Array.Empty<string>();

        public class ListenProbe
        {
            public string TargetIpAddress { get; set; } = string.Empty;
            public int Port { get; set; }
            public bool Succeeded { get; set; }
            public double? LatencyMilliseconds { get; set; }
            public string? Error { get; set; }
        }

        public class RecentUpload
        {
            public Guid Id { get; set; }
            public string Username { get; set; } = string.Empty;
            public string Filename { get; set; } = string.Empty;
            public string State { get; set; } = string.Empty;
            public DateTime? RequestedAt { get; set; }
            public DateTime? EnqueuedAt { get; set; }
            public DateTime? StartedAt { get; set; }
            public DateTime? EndedAt { get; set; }
            public long BytesTransferred { get; set; }
            public long Size { get; set; }
            public string? Exception { get; set; }
            public bool Removed { get; set; }
        }
    }
}
