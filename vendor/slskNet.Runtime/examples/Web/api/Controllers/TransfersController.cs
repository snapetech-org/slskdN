namespace WebAPI.Controllers
{
    using Asp.Versioning;
    using Microsoft.AspNetCore.Authorization;
    using Microsoft.AspNetCore.Mvc;
    using Microsoft.Extensions.Configuration;
    using Soulseek;
    using System;
    using System.ComponentModel.DataAnnotations;
    using System.Diagnostics.CodeAnalysis;
    using System.IO;
    using System.Linq;
    using System.Threading;
    using System.Threading.Tasks;
    using WebAPI.DTO;
    using WebAPI.Trackers;

    /// <summary>
    ///     Transfers
    /// </summary>
    [Route("api/v{version:apiVersion}/[controller]")]
    [ApiVersion("1")]
    [ApiController]
    [Produces("application/json")]
    [Consumes("application/json")]
    public class TransfersController : ControllerBase
    {
        /// <summary>
        ///     Initializes a new instance of the <see cref="TransfersController"/> class.
        /// </summary>
        /// <param name="configuration"></param>
        /// <param name="client"></param>
        /// <param name="tracker"></param>
        public TransfersController(IConfiguration configuration, ISoulseekClient client, ITransferTracker tracker)
        {
            OutputDirectory = configuration.GetValue<string>("OUTPUT_DIR");
            Client = client;
            Tracker = tracker;
        }

        private ISoulseekClient Client { get; }
        private string OutputDirectory { get; }
        private ITransferTracker Tracker { get; }

        /// <summary>
        ///     Cancels the specified download.
        /// </summary>
        /// <param name="username">The username of the download source.</param>
        /// <param name="id">The id of the download.</param>
        /// <param name="remove">A value indicating whether the tracked download should be removed after cancellation.</param>
        /// <returns></returns>
        /// <response code="204">The download was cancelled successfully.</response>
        /// <response code="404">The specified download was not found.</response>
        [HttpDelete("downloads/{username}/{id}")]
        [Authorize]
        [ProducesResponseType(204)]
        [ProducesResponseType(404)]
        public IActionResult CancelDownload([FromRoute, Required] string username, [FromRoute, Required] string id, [FromQuery] bool remove = false)
        {
            if (ControllerValidation.IsMissing(username))
            {
                return BadRequest("Username is required");
            }

            if (ControllerValidation.IsMissing(id))
            {
                return BadRequest("Transfer id is required");
            }

            return CancelTransfer(TransferDirection.Download, username, id, remove);
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
        [Authorize]
        [ProducesResponseType(204)]
        [ProducesResponseType(404)]
        public IActionResult CancelUpload([FromRoute, Required] string username, [FromRoute, Required] string id, [FromQuery] bool remove = false)
        {
            if (ControllerValidation.IsMissing(username))
            {
                return BadRequest("Username is required");
            }

            if (ControllerValidation.IsMissing(id))
            {
                return BadRequest("Transfer id is required");
            }

            return CancelTransfer(TransferDirection.Upload, username, id, remove);
        }

        /// <summary>
        ///     Enqueues the specified download.
        /// </summary>
        /// <param name="username">The username of the download source.</param>
        /// <param name="request">The download request.</param>
        /// <returns></returns>
        /// <response code="201">The download was successfully enqueued.</response>
        /// <response code="403">The download was rejected.</response>
        /// <response code="500">An unexpected error was encountered.</response>
        [HttpPost("downloads/{username}")]
        [Authorize]
        [ProducesResponseType(201)]
        [ProducesResponseType(typeof(string), 400)]
        [ProducesResponseType(typeof(string), 403)]
        [ProducesResponseType(typeof(string), 500)]
        [SuppressMessage("Reliability", "CA2000:Dispose objects before losing scope", Justification = "The cancellation token source is owned by the tracker after the first state/progress callback; untracked setup failures are disposed before returning.")]
        public async Task<IActionResult> Enqueue([FromRoute, Required] string username, [FromBody] QueueDownloadRequest request)
        {
            if (ControllerValidation.IsMissing(username))
            {
                return BadRequest("Username is required");
            }

            CancellationTokenSource cts = null;
            var isTracked = 0;

            try
            {
                if (request == null)
                {
                    return BadRequest("Request body is required");
                }

                if (string.IsNullOrWhiteSpace(request.Filename))
                {
                    return BadRequest("Filename is required");
                }

                if (request.Size < 0)
                {
                    return BadRequest("Size must be greater than or equal to zero");
                }

                var waitUntilEnqueue = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);

                cts = new CancellationTokenSource();

                var downloadTask = Client.DownloadAsync(username, request.Filename, () => Task.FromResult((Stream)GetLocalFileStream(request.Filename, OutputDirectory)), request.Size, 0, request.Token, new TransferOptions(disposeOutputStreamOnCompletion: true, stateChanged: (e) =>
                {
                    Tracker.AddOrUpdate(e.Transfer, cts);
                    Interlocked.Exchange(ref isTracked, 1);

                    if (e.Transfer.State.HasFlag(TransferStates.Queued) || e.Transfer.State == TransferStates.Initializing)
                    {
                        waitUntilEnqueue.TrySetResult(true);
                    }
                }, progressUpdated: (e) =>
                {
                    Tracker.AddOrUpdate(e.Transfer, cts);
                    Interlocked.Exchange(ref isTracked, 1);
                }), cts.Token);

                // wait until either the waitUntilEnqueue task completes because the download was successfully queued, or the
                // downloadTask throws due to an error prior to successfully queueing.
                var task = await Task.WhenAny(waitUntilEnqueue.Task, downloadTask);

                if (task == downloadTask && downloadTask.Exception is AggregateException)
                {
                    DisposeUntrackedCancellationTokenSource(cts, isTracked);

                    var rejected = downloadTask.Exception?.InnerExceptions.Where(e => e is TransferRejectedException) ?? Enumerable.Empty<Exception>();

                    if (rejected.Any())
                    {
                        return StatusCode(403, rejected.First().Message);
                    }

                    return StatusCode(500, downloadTask.Exception.Message);
                }

                // if it didn't throw, just return ok. the download will continue waiting in the background.
                return StatusCode(201);
            }
            catch (Exception ex)
            {
                DisposeUntrackedCancellationTokenSource(cts, isTracked);
                Console.WriteLine(ex);
                return StatusCode(500, ex.Message);
            }
        }

        /// <summary>
        ///     Gets all downloads.
        /// </summary>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("downloads")]
        [Authorize]
        [ProducesResponseType(200)]
        public IActionResult GetDownloads()
        {
            return Ok(Tracker.Transfers
                .WithDirection(TransferDirection.Download)
                .ToMap());
        }

        /// <summary>
        ///     Gets all downloads for the specified username.
        /// </summary>
        /// <param name="username"></param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("downloads/{username}")]
        [Authorize]
        [ProducesResponseType(200)]
        public IActionResult GetDownloads([FromRoute, Required] string username)
        {
            if (ControllerValidation.IsMissing(username))
            {
                return BadRequest("Username is required");
            }

            return Ok(Tracker.Transfers
                .WithDirection(TransferDirection.Download)
                .FromUser(username)
                .ToMap());
        }

        /// <summary>
        ///     Gets the downlaod for the specified username matching the specified filename, and requests 
        ///     the current place in the remote queue of the specified download.
        /// </summary>
        /// <param name="username">The username of the download source.</param>
        /// <param name="id">The id of the download.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        /// <response code="404">The specified download was not found.</response>
        [HttpGet("downloads/{username}/{id}")]
        [Authorize]
        [ProducesResponseType(typeof(DTO.Transfer), 200)]
        [ProducesResponseType(404)]
        public async Task<IActionResult> GetPlaceInQueue([FromRoute, Required] string username, [FromRoute, Required] string id)
        {
            if (ControllerValidation.IsMissing(username))
            {
                return BadRequest("Username is required");
            }

            if (ControllerValidation.IsMissing(id))
            {
                return BadRequest("Transfer id is required");
            }

            var record = Tracker.Transfers.WithDirection(TransferDirection.Download).FromUser(username).WithId(id);

            if (record == default)
            {
                return NotFound();
            }

            record.Transfer.PlaceInQueue = await Client.GetDownloadPlaceInQueueAsync(username, record.Transfer.Filename);
            return Ok(record.Transfer);
        }

        /// <summary>
        ///     Gets all uploads.
        /// </summary>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("uploads")]
        [Authorize]
        [ProducesResponseType(200)]
        public IActionResult GetUploads()
        {
            return Ok(Tracker.Transfers
                .WithDirection(TransferDirection.Upload)
                .ToMap());
        }

        /// <summary>
        ///     Gets all uploads for the specified username.
        /// </summary>
        /// <param name="username"></param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("uploads/{username}")]
        [Authorize]
        [ProducesResponseType(200)]
        public IActionResult GetUploads([FromRoute, Required] string username)
        {
            if (ControllerValidation.IsMissing(username))
            {
                return BadRequest("Username is required");
            }

            return Ok(Tracker.Transfers
                .WithDirection(TransferDirection.Upload)
                .FromUser(username)
                .ToMap());
        }

        /// <summary>
        ///     Gets the upload for the specified username matching the specified filename.
        /// </summary>
        /// <param name="username">The username of the upload destination.</param>
        /// <param name="id">The id of the upload.</param>
        /// <returns></returns>
        /// <response code="200">The request completed successfully.</response>
        [HttpGet("uploads/{username}/{id}")]
        [Authorize]
        [ProducesResponseType(200)]
        [ProducesResponseType(404)]
        public IActionResult GetUploads([FromRoute, Required] string username, [FromRoute, Required] string id)
        {
            if (ControllerValidation.IsMissing(username))
            {
                return BadRequest("Username is required");
            }

            if (ControllerValidation.IsMissing(id))
            {
                return BadRequest("Transfer id is required");
            }

            var record = Tracker.Transfers
                .WithDirection(TransferDirection.Upload)
                .FromUser(username)
                .WithId(id);

            if (record == default)
            {
                return NotFound();
            }

            return Ok(record.Transfer);
        }

        [SuppressMessage("Security", "CA3003:Review code for file path injection vulnerabilities", Justification = "The remote file name is normalized to a relative path and confined to the configured output directory by Extensions.GetSafeOutputPath.")]
        private static FileStream GetLocalFileStream(string remoteFilename, string saveDirectory)
        {
            var localFilename = Extensions.GetSafeOutputPath(saveDirectory, remoteFilename);
            var path = Path.GetDirectoryName(localFilename);

            if (!System.IO.Directory.Exists(path))
            {
                System.IO.Directory.CreateDirectory(path);
            }

            return new FileStream(localFilename, FileMode.Create);
        }

        private static void DisposeUntrackedCancellationTokenSource(CancellationTokenSource cts, int isTracked)
        {
            if (cts != null && isTracked == 0)
            {
                cts.Dispose();
            }
        }

        private IActionResult CancelTransfer(TransferDirection direction, string username, string id, bool remove = false)
        {
            if (Tracker.TryGet(direction, username, id, out var transfer))
            {
                transfer.CancellationTokenSource.Cancel();

                if (remove)
                {
                    Tracker.TryRemove(direction, username, id);
                }

                return NoContent();
            }

            return NotFound();
        }
    }
}
