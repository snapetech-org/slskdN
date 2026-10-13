// <copyright file="DownloadService.cs" company="slskd Team">
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

// <copyright file="DownloadService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;
using Soulseek;
using slskd.Common.CodeQuality;
using slskd.Common.Security;
using slskd.Transfers.MultiSource.Metrics;
using TagLib;

namespace slskd.Transfers.Downloads
{
    using System;
    using System.Collections.Concurrent;
    using System.Collections.Generic;
    using System.Linq;
    using System.Linq.Expressions;
    using System.Net;
    using System.Runtime.CompilerServices;
    using System.Threading;
    using System.Threading.Tasks;
    using Microsoft.EntityFrameworkCore;
    using Serilog;
    using slskd.Events;
    using slskd.Files;
    using slskd.Integrations.FTP;
    using slskd.Relay;
    using slskd.SoulseekExceptions;

    /// <summary>
    ///     Completed download folder layouts.
    /// </summary>
    public enum CompletedDownloadLayout
    {
        BatchId,
        UploaderFolder,
        RemoteFolder,
        Flat,
    }

    /// <summary>
    ///     Manages downloads.
    /// </summary>
    public interface IDownloadService : IDisposable
    {
        /// <summary>
        ///     Adds the specified <paramref name="transfer"/>. Supersedes any existing record for the same file and username.
        /// </summary>
        /// <remarks>This should generally not be called; use EnqueueAsync() instead.</remarks>
        /// <param name="transfer"></param>
        void AddOrSupersede(Transfer transfer);

        /// <summary>
        ///     Enqueues the requested list of <paramref name="files"/>.
        /// </summary>
        /// <remarks>
        ///     If one file in the specified collection fails, the rest will continue. An <see cref="AggregateException"/> will be
        ///     thrown after all files are dispositioned if any throws.
        /// </remarks>
        /// <param name="username">The username of remote user.</param>
        /// <param name="files">The list of files to enqueue.</param>
        /// <param name="cancellationToken">The token to monitor for cancellation.</param>
        /// <returns>The operation context.</returns>
        /// <exception cref="ArgumentException">Thrown when the username is null or an empty string.</exception>
        /// <exception cref="ArgumentException">Thrown when no files are requested.</exception>
        /// <exception cref="AggregateException">Thrown when at least one of the requested files throws.</exception>
        Task<(List<Transfer> Enqueued, List<string> Failed)> EnqueueAsync(string username, IEnumerable<(string Filename, long Size)> files, CancellationToken cancellationToken = default);

        /// <summary>
        ///     Enqueues the requested list of <paramref name="files"/>.
        /// </summary>
        /// <remarks>
        ///     If one file in the specified collection fails, the rest will continue. An <see cref="AggregateException"/> will be
        ///     thrown after all files are dispositioned if any throws.
        /// </remarks>
        /// <param name="username">The username of remote user.</param>
        /// <param name="files">The list of files to enqueue.</param>
        /// <param name="cancellationToken">The token to monitor for cancellation.</param>
        /// <returns>The operation context.</returns>
        /// <exception cref="ArgumentException">Thrown when the username is null or an empty string.</exception>
        /// <exception cref="ArgumentException">Thrown when no files are requested.</exception>
        /// <exception cref="AggregateException">Thrown when at least one of the requested files throws.</exception>
        Task<(List<Transfer> Enqueued, List<string> Failed)> EnqueueAsync(string username, IEnumerable<(string Filename, long Size, Guid? BatchId)> files, CancellationToken cancellationToken = default);

        /// <summary>
        ///     Enqueues the requested list of <paramref name="files"/> with optional completed-file destinations.
        /// </summary>
        /// <param name="username">The username of remote user.</param>
        /// <param name="files">The list of files to enqueue.</param>
        /// <param name="cancellationToken">The token to monitor for cancellation.</param>
        /// <returns>The operation context.</returns>
        Task<(List<Transfer> Enqueued, List<string> Failed)> EnqueueAsync(string username, IEnumerable<(string Filename, long Size, Guid? BatchId, string? DestinationDirectory)> files, CancellationToken cancellationToken = default);

        /// <summary>
        ///     Enqueues the requested list of <paramref name="files"/> with optional metadata.
        ///     Metadata supplied here is seeded onto the Transfer record at request time so
        ///     the row shows audio attributes (bitrate, length, etc.) before the file completes.
        /// </summary>
        /// <param name="username">The username of remote user.</param>
        /// <param name="files">The list of files to enqueue, including optional metadata.</param>
        /// <param name="cancellationToken">The token to monitor for cancellation.</param>
        /// <returns>The operation context.</returns>
        Task<(List<Transfer> Enqueued, List<string> Failed)> EnqueueAsync(string username, IEnumerable<DownloadEnqueueRequest> files, CancellationToken cancellationToken = default);

        /// <summary>
        ///     Finds a single download matching the specified <paramref name="expression"/>.
        /// </summary>
        /// <param name="expression">The expression to use to match downloads.</param>
        /// <returns>The found transfer, or default if not found.</returns>
        Transfer? Find(Expression<Func<Transfer, bool>> expression);

        /// <summary>
        ///     Retrieves the place in the remote queue for the download matching the specified <paramref name="id"/>.
        /// </summary>
        /// <param name="id">The unique identifier for the download.</param>
        /// <returns>The retrieved place in queue.</returns>
        Task<int> GetPlaceInQueueAsync(Guid id);

        /// <summary>
        ///     Returns a list of all downloads matching the optional <paramref name="expression"/>.
        /// </summary>
        /// <param name="expression">An optional expression used to match downloads.</param>
        /// <param name="includeRemoved">Optionally include downloads that have been removed previously.</param>
        /// <returns>The list of downloads matching the specified expression, or all downloads if no expression is specified.</returns>
        List<Transfer> List(Expression<Func<Transfer, bool>>? expression = null, bool includeRemoved = false);

        /// <summary>
        ///     Returns a stable page of downloads ordered by request time, newest first.
        /// </summary>
        /// <param name="expression">The transfer predicate.</param>
        /// <param name="includeRemoved">Whether to include soft-removed records.</param>
        /// <param name="afterRequestedAt">The request time of the previous page's last record.</param>
        /// <param name="afterId">The ID of the previous page's last record.</param>
        /// <param name="limit">The maximum number of records to return.</param>
        /// <returns>The requested page.</returns>
        List<Transfer> ListPage(
            Expression<Func<Transfer, bool>> expression,
            bool includeRemoved,
            DateTime? afterRequestedAt,
            Guid? afterId,
            int limit);

        /// <summary>
        ///     Streams retryable failed downloads in stable oldest-first order.
        /// </summary>
        /// <param name="endedBefore">The exclusive completion-time cutoff.</param>
        /// <param name="cancellationToken">The token to monitor for cancellation.</param>
        /// <returns>An asynchronous sequence containing only the fields required by auto-retry.</returns>
        IAsyncEnumerable<Transfer> StreamAutoRetryCandidatesAsync(
            DateTime endedBefore,
            CancellationToken cancellationToken = default);

        /// <summary>
        ///     Counts downloads, optionally including soft-removed records.
        /// </summary>
        /// <param name="includeRemoved">Whether soft-removed records should be counted.</param>
        /// <returns>The download count.</returns>
        int Count(bool includeRemoved = false);

        /// <summary>
        ///     Returns a stable page of successful downloads completed no later than <paramref name="asOf"/>.
        /// </summary>
        /// <remarks>Soft-removed records remain in the page sequence so offsets stay stable while history is cleared.</remarks>
        /// <param name="asOf">The inclusive completion-time watermark.</param>
        /// <param name="offset">The number of history records to skip.</param>
        /// <param name="limit">The maximum number of records to return.</param>
        /// <returns>The requested successful-download history page.</returns>
        List<Transfer> ListCompleted(DateTime asOf, int offset, int limit);

        /// <summary>
        ///     Removes <see cref="TransferStates.Completed"/> downloads older than the specified <paramref name="age"/>.
        /// </summary>
        /// <param name="age">The age after which downloads are eligible for pruning, in hours.</param>
        /// <param name="stateHasFlag">An optional, additional state by which downloads are filtered for pruning.</param>
        /// <returns>The number of pruned downloads.</returns>
        int Prune(int age, TransferStates stateHasFlag = TransferStates.Completed);

        /// <summary>
        ///     Permanently deletes soft-removed, completed downloads older than the specified <paramref name="age"/>.
        /// </summary>
        /// <param name="age">The time since the last transfer update, in minutes.</param>
        /// <returns>The number of deleted downloads.</returns>
        int PruneRemoved(int age);

        /// <summary>
        ///     Removes the download matching the specified <paramref name="id"/>.
        /// </summary>
        /// <remarks>This is a soft delete; the record is retained for historical retrieval.</remarks>
        /// <param name="id">The unique identifier of the download.</param>
        /// <param name="deleteFile">Optionally delete the file from disk.</param>
        void Remove(Guid id, bool deleteFile = false);

        /// <summary>
        ///     Cancels the download matching the specified <paramref name="id"/>, if it is in progress.
        /// </summary>
        /// <param name="id">The unique identifier for the download.</param>
        /// <returns>A value indicating whether the download was successfully cancelled.</returns>
        bool TryCancel(Guid id);

        /// <summary>
        ///     Fails the download matching the specified <paramref name="id"/> with the specified <paramref name="exception"/>,
        ///     and sets the final state accordingly.
        /// </summary>
        /// <remarks>
        ///     This method is designed to be idempotent, meaning subsequent calls for a given transfer shouldn't change
        ///     the EndedAt or Exception properties if they have already been set. If the transfer State already includes
        ///     the terminal Completed flag, it is unchanged.
        /// </remarks>
        /// <param name="id">The unique identifier for the download.</param>
        /// <param name="exception">The exception that caused the failure.</param>
        /// <returns>A value indicating whether the download was successfully failed.</returns>
        bool TryFail(Guid id, Exception exception);

        /// <summary>
        ///     Updates the specified <paramref name="transfer"/>.
        /// </summary>
        /// <param name="transfer">The transfer to update.</param>
        void Update(Transfer transfer);

        /// <summary>
        ///     Cancels active downloads and waits for in-flight background tasks to unwind.
        /// </summary>
        /// <param name="cancellationToken">A token used to stop waiting for shutdown drain completion.</param>
        /// <returns>A task representing the shutdown drain operation.</returns>
        Task ShutdownAsync(CancellationToken cancellationToken = default);
    }

    /// <summary>
    ///     Manages downloads.
    /// </summary>
    public class DownloadService : IDownloadService
    {
        private readonly EventHandler<ClockEventArgs> _cleanupEnqueueSemaphoresHandler;
        private bool _disposed;

        public DownloadService(
            IOptionsMonitor<Options> optionsMonitor,
            ISoulseekClient soulseekClient,
            IDbContextFactory<TransfersDbContext> contextFactory,
            FileService fileService,
            IRelayService relayService,
            IFTPService ftpClient,
            EventBus eventBus,
            IPeerMetricsService? peerMetricsService = null)
        {
            Client = soulseekClient;
            OptionsMonitor = optionsMonitor;
            ContextFactory = contextFactory;
            Files = fileService;
            FTP = ftpClient;
            Relay = relayService;
            EventBus = eventBus;
            PeerMetrics = peerMetricsService;

            _cleanupEnqueueSemaphoresHandler = (_, _) => _ = ObserveBackgroundTaskAsync(
                Task.Run(() => CleanupEnqueueSemaphoresAsync(), CancellationToken.None),
                "Failed to clean up download enqueue semaphores");
            Clock.EveryMinute += _cleanupEnqueueSemaphoresHandler;
        }

        /// <summary>
        ///     These tokens give users the ability to cancel transfers via the UI (or API).
        ///
        ///     The lifecycle is:
        ///
        ///     1. in EnqueueAsync(), just before transfer records are added to the database, these CTS are created and
        ///        added to the dictionary
        ///     2. in EnqueueAsync(), if there was an error or any condition which caused the transfer to not proceed was met,
        ///        the CTS is removed from the dictionary and disposed
        ///     3. in DownloadAsync(), in the finally block after all post-download logic has been executed, the CTS
        ///        is removed and disposed.
        ///
        ///     The CTS should be in the dictionary the entire time the transfer is "in flight", from the first moment it
        ///     comes into being (via database insert) until the eventual download process has completed or failed.
        ///
        ///     Every cancellable operation in this flow needs to use this CTS token either directly or by linking it with another,
        ///     or we risk transfers getting stuck with no way for users to get rid of them.
        /// </summary>
        private ConcurrentDictionary<Guid, CancellationTokenSource> CancellationTokens { get; } = new ConcurrentDictionary<Guid, CancellationTokenSource>();
        private ConcurrentDictionary<Guid, Task> ActiveDownloadTasks { get; } = new ConcurrentDictionary<Guid, Task>();
        private ConcurrentDictionary<Guid, Task> ActiveEnqueueTasks { get; } = new ConcurrentDictionary<Guid, Task>();
        private ISoulseekClient Client { get; }
        private IDbContextFactory<TransfersDbContext> ContextFactory { get; }
        private IFTPService FTP { get; }
        private FileService Files { get; }
        private IRelayService Relay { get; }
        private ILogger Log { get; } = Serilog.Log.ForContext<DownloadService>();
        private IOptionsMonitor<Options> OptionsMonitor { get; }
        private EventBus EventBus { get; }
        private IPeerMetricsService? PeerMetrics { get; }

        private async Task ObserveBackgroundTaskAsync(Task task, string message)
        {
            try
            {
                await task.ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                Log.Warning("{Message}: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(message),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
            }
        }

        /// <summary>
        ///     Allow only one enqueue operation for a given user at a time. Entries are added on the fly if they
        ///     don't already exist, and a timer asynchronously cleans the dictionary up.
        /// </summary>
        private ConcurrentDictionary<string, SemaphoreSlim> EnqueueSemaphores { get; } = [];

        /// <summary>
        ///     Synchronizes the cleanup process; after gaining exclusive access over the dictionary, checks each entry
        ///     to see if the containing semaphore can be obtained immediately.  If so, it's not in use and is therefore
        ///     removed from the dictionary and discarded.
        /// </summary>
        private SemaphoreSlim EnqueueSemaphoreSyncRoot { get; } = new SemaphoreSlim(initialCount: 1, maxCount: 1);

        /// <summary>
        ///     Disposes this instance.
        /// </summary>
        public void Dispose()
        {
            Dispose(disposing: true);
            GC.SuppressFinalize(this);
        }

        /// <summary>
        ///     Disposes this instance.
        /// </summary>
        /// <param name="disposing">A value indicating whether disposal is in progress.</param>
        protected virtual void Dispose(bool disposing)
        {
            if (_disposed || !disposing)
            {
                return;
            }

            Clock.EveryMinute -= _cleanupEnqueueSemaphoresHandler;

            CancelActiveTransfers();

            EnqueueSemaphores.Clear();
            _disposed = true;
        }

        public async Task ShutdownAsync(CancellationToken cancellationToken = default)
        {
            CancelActiveTransfers();

            var activeTasks = ActiveEnqueueTasks.Values
                .Concat(ActiveDownloadTasks.Values)
                .Distinct()
                .ToArray();

            if (activeTasks.Length == 0)
            {
                return;
            }

            Log.Debug("Waiting for {Count} active download tasks to drain during shutdown", activeTasks.Length);
            await Task.WhenAll(activeTasks).WaitAsync(cancellationToken).ConfigureAwait(false);
        }

        /// <summary>
        ///     Adds the specified <paramref name="transfer"/>. Supersedes any existing record for the same file and username.
        /// </summary>
        /// <remarks>This should generally not be called; use EnqueueAsync() instead.</remarks>
        /// <param name="transfer"></param>
        public void AddOrSupersede(Transfer transfer)
        {
            using var context = ContextFactory.CreateDbContext();

            var existing = context.Transfers
                .Where(t => t.Direction == TransferDirection.Download)
                .Where(t => t.Username == transfer.Username)
                .Where(t => t.Filename == transfer.Filename)
                .Where(t => !t.Removed)
                .FirstOrDefault();

            if (existing != default)
            {
                Log.Debug("Superseding transfer record for {Filename} from {Username}",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username));
                existing.Removed = true;

                // Preserve request continuity across supersede so the UI row stays stable.
                if (!transfer.RequestId.HasValue && existing.RequestId.HasValue)
                {
                    transfer.RequestId = existing.RequestId;
                }
            }

            if (!transfer.RequestId.HasValue && transfer.Direction == TransferDirection.Download)
            {
                var requestId = Guid.NewGuid();
                var defaultName = System.IO.Path.GetFileName(transfer.Filename.Replace('\\', '/').TrimEnd('/'));
                context.Add(new DownloadRequest
                {
                    Id = requestId,
                    Name = string.IsNullOrEmpty(defaultName) ? transfer.Filename : defaultName,
                    OriginalFilename = transfer.Filename,
                    Size = transfer.Size,
                    BatchId = transfer.BatchId,
                    DestinationDirectory = transfer.DestinationDirectory,
                    State = DownloadRequestState.Active,
                    CreatedAt = DateTime.UtcNow,
                    BitRate = transfer.BitRate,
                    SampleRate = transfer.SampleRate,
                    BitDepth = transfer.BitDepth,
                    Length = transfer.Length,
                });
                transfer.RequestId = requestId;
            }

            context.Add(transfer);
            context.SaveChanges();
        }

        /// <summary>
        ///     Enqueues the requested list of <paramref name="files"/>.
        /// </summary>
        /// <param name="username">The username of the remote user.</param>
        /// <param name="files">The list of files to enqueue.</param>
        /// <param name="cancellationToken">The token to monitor for cancellation.</param>
        /// <returns>The operation context.</returns>
        /// <exception cref="ArgumentException">Thrown when the username is null or an empty string.</exception>
        /// <exception cref="ArgumentException">Thrown when no files are requested.</exception>
        /// <exception cref="AggregateException">Thrown when at least one of the requested files throws.</exception>
        public Task<(List<Transfer> Enqueued, List<string> Failed)> EnqueueAsync(string username, IEnumerable<(string Filename, long Size)> files, CancellationToken cancellationToken = default)
            => EnqueueAsync(username, files.Select(f => new DownloadEnqueueRequest { Filename = f.Filename, Size = f.Size }), cancellationToken);

        public Task<(List<Transfer> Enqueued, List<string> Failed)> EnqueueAsync(string username, IEnumerable<(string Filename, long Size, Guid? BatchId)> files, CancellationToken cancellationToken = default)
            => EnqueueAsync(username, files.Select(f => new DownloadEnqueueRequest { Filename = f.Filename, Size = f.Size, BatchId = f.BatchId }), cancellationToken);

        public Task<(List<Transfer> Enqueued, List<string> Failed)> EnqueueAsync(string username, IEnumerable<(string Filename, long Size, Guid? BatchId, string? DestinationDirectory)> files, CancellationToken cancellationToken = default)
            => EnqueueAsync(username, files.Select(f => new DownloadEnqueueRequest { Filename = f.Filename, Size = f.Size, BatchId = f.BatchId, DestinationDirectory = f.DestinationDirectory }), cancellationToken);

        /// <summary>
        ///     Enqueues the requested list of <paramref name="files"/>.
        /// </summary>
        /// <param name="username">The username of the remote user.</param>
        /// <param name="files">The list of files to enqueue.</param>
        /// <param name="cancellationToken">The token to monitor for cancellation.</param>
        /// <returns>The operation context.</returns>
        /// <exception cref="ArgumentException">Thrown when the username is null or an empty string.</exception>
        /// <exception cref="ArgumentException">Thrown when no files are requested.</exception>
        /// <exception cref="AggregateException">Thrown when at least one of the requested files throws.</exception>
        public async Task<(List<Transfer> Enqueued, List<string> Failed)> EnqueueAsync(string username, IEnumerable<DownloadEnqueueRequest> files, CancellationToken cancellationToken = default)
        {
            if (string.IsNullOrEmpty(username))
            {
                throw new ArgumentException("Username is required", nameof(username));
            }

            var fileList = files?.ToList() ?? [];

            if (fileList.Count == 0)
            {
                throw new ArgumentException("At least one file is required", nameof(files));
            }

            if (fileList.Any(f => string.IsNullOrEmpty(f.Filename)))
            {
                throw new ArgumentException("At least one filename is null or empty", nameof(files));
            }

            if (fileList.Count != fileList.Distinct().Count())
            {
                throw new ArgumentException("Two or more files in request are duplicated", nameof(files));
            }

            Log.Information("Requested enqueue of {Count} files from user {Username}",
                fileList.Count, LoggingSanitizer.SanitizeExternalIdentifier(username));

            List<Transfer> enqueued = [];
            List<string> failed = [];

            var policyBlockedFiles = fileList
                .Select(file => new
                {
                    file.Filename,
                    Exclusion = DownloadFilter.GetMatchingExclusion(
                        file.Filename,
                        OptionsMonitor.CurrentValue.Filters.Download.Exclude),
                })
                .Where(file => file.Exclusion is not null)
                .ToList();

            if (policyBlockedFiles.Count > 0)
            {
                foreach (var blockedFile in policyBlockedFiles)
                {
                    failed.Add(blockedFile.Filename);
                    Log.Information(
                        "Blocked download enqueue for {Filename} from {Username} by global exclusion {Exclusion}",
                        LoggingSanitizer.SanitizeFilePath(blockedFile.Filename),
                        LoggingSanitizer.SanitizeExternalIdentifier(username),
                        LoggingSanitizer.SanitizeExternalIdentifier(blockedFile.Exclusion));
                }

                var blockedFilenames = policyBlockedFiles
                    .Select(file => file.Filename)
                    .ToHashSet(StringComparer.Ordinal);
                fileList = fileList
                    .Where(file => !blockedFilenames.Contains(file.Filename))
                    .ToList();

                if (fileList.Count == 0)
                {
                    return (enqueued, failed);
                }
            }

            SemaphoreSlim userSemaphore;
            Task userSemaphoreWaitTask;
            SemaphoreSlim? enqueueSemaphore = null;
            var trackedEnqueueTasks = new List<Task>();

            Log.Debug("Awaiting enqueue semaphore sync root");
            await EnqueueSemaphoreSyncRoot.WaitAsync(cancellationToken);

            try
            {
                Log.Debug("Acquired enqueue semaphore sync root");
                userSemaphore = EnqueueSemaphores.GetOrAdd(username, (username) => new SemaphoreSlim(initialCount: 1, maxCount: 1));
                userSemaphoreWaitTask = userSemaphore.WaitAsync(cancellationToken);
            }
            finally
            {
                EnqueueSemaphoreSyncRoot.Release();
                Log.Debug("Released enqueue semaphore sync root");
            }

            Log.Debug("Awaiting enqueue semaphore for user {Username}", LoggingSanitizer.SanitizeExternalIdentifier(username));
            await userSemaphoreWaitTask;

            try
            {
                Log.Debug("Acquired enqueue semaphore for user {Username}", LoggingSanitizer.SanitizeExternalIdentifier(username));

                using var context = ContextFactory.CreateDbContext();

                /*
                    Get past downloads from this user for only the requested filenames. This list will remain stable
                    throughout this process because we have exclusive access for this user. We'll be adding new records,
                    but we've already deduplicated them so we don't have to worry about duplicate records being created
                    in the critical section.
                */
                var requestedFilenames = fileList
                    .Select(file => file.Filename)
                    .Distinct()
                    .ToArray();
                var existingRecords = context.Transfers
                    .Where(t => t.Direction == TransferDirection.Download)
                    .Where(t => t.Username == username)
                    .Where(t => requestedFilenames.Contains(t.Filename))
                    .AsNoTracking() // note: AI wants to remove this, dont.
                    .ToList();

                var existingRecordsByFilename = new Dictionary<string, List<Transfer>>(StringComparer.Ordinal);
                var existingInProgressRecords = new Dictionary<string, Transfer>(StringComparer.Ordinal);
                foreach (var record in existingRecords)
                {
                    if (!existingRecordsByFilename.TryGetValue(record.Filename, out var records))
                    {
                        records = [];
                        existingRecordsByFilename.Add(record.Filename, records);
                    }

                    records.Add(record);
                    if (record.EndedAt == null || !record.State.HasFlag(TransferStates.Completed))
                    {
                        existingInProgressRecords.Add(record.Filename, record);
                    }
                }

                /*
                    determine how many concurrent enqueue requests we want to send to the remote client.

                    Keep this deliberately low. Some peers reject album-sized
                    enqueue bursts as "Overwhelmed with requests", and the
                    transfer queue can still carry throughput once files are
                    accepted remotely.
                */
                var concurrentEnqueueRequests = Math.Min(fileList.Count, 2);

                var maxTimeToWaitForEnqueueRequestAck = TimeSpan.FromMinutes(3);
#pragma warning disable CA2000 // Ephemeral async throttle; detached enqueue tasks may still touch it after this method returns.
                enqueueSemaphore = new SemaphoreSlim(initialCount: concurrentEnqueueRequests, maxCount: concurrentEnqueueRequests);
#pragma warning restore CA2000
                try
                {
                    /*
                    iterate over each of the files in the request.  each file must be dispositioned as one of the following:

                    1. enqueued: passed duplicate checks and successfully kicked off a Task to enqueue the download
                    2. failed: download is already in progress, or something went wrong kicking off the Task

                    if we fail to enqueue a file, we must call TryFail() to ensure that if a record was inserted, it is
                    given a final disposition that will keep it from getting 'stuck'
                */
                    foreach (var file in fileList)
                    {
                        cancellationToken.ThrowIfCancellationRequested();
                        Guid transferId = Guid.NewGuid();

                        try
                        {
                            Log.Debug("Checking whether download of {Filename} from {Username} is already in progress",
                                LoggingSanitizer.SanitizeFilePath(file.Filename), LoggingSanitizer.SanitizeExternalIdentifier(username));
                            existingRecordsByFilename.TryGetValue(file.Filename, out var existingFilenameRecords);

                            /*
                                if there are any that haven't ended yet (checking a few ways out of paranoia), then there's already
                                an existing transfer record covering this file, and we're already enqueued. nothing more to do!
                            */
                            existingInProgressRecords.TryGetValue(file.Filename, out var existingInProgressRecord);

                            if (existingInProgressRecord is not null)
                            {
                                Log.Debug("Ignoring concurrent download enqueue attempt; transfer for {Filename} from {Username} already in progress (id: {Id})",
                                    LoggingSanitizer.SanitizeFilePath(file.Filename), LoggingSanitizer.SanitizeExternalIdentifier(username), existingInProgressRecord.Id);
                                failed.Add(file.Filename);
                                continue;
                            }

                            /*
                                check the tracked download dictionary in Soulseek.NET to see if it knows about this already
                                it shouldn't, if the slskd database doesn't. but things could get desynced, which is likely a bug
                                and we'd like to know about it
                            */
                            if (IsActiveClientDownload(username, file.Filename))
                            {
                                Log.Warning("Ignoring concurrent download enqueue attempt; transfer for {Filename} from {Username} is tracked by the Soulseek client but not slskd",
                                    LoggingSanitizer.SanitizeFilePath(file.Filename), LoggingSanitizer.SanitizeExternalIdentifier(username));
                                failed.Add(file.Filename);
                                continue;
                            }

                            /*
                                resolve the owning DownloadRequest:
                                1. caller-supplied explicit RequestId wins (used by rescue/auto-replace to swap sources)
                                2. otherwise, inherit from any same-filename record we're about to supersede
                                3. otherwise, create a fresh DownloadRequest so the UI has a stable row identity
                            */
                            Guid resolvedRequestId;
                            DownloadRequest? newRequestEntity = null;

                            if (file.RequestId.HasValue)
                            {
                                resolvedRequestId = file.RequestId.Value;
                            }
                            else
                            {
                                Guid? inheritFrom = null;
                                DateTime? inheritFromRequestedAt = null;
                                if (existingFilenameRecords != null)
                                {
                                    foreach (var record in existingFilenameRecords)
                                    {
                                        if (record.RequestId.HasValue &&
                                            (!inheritFromRequestedAt.HasValue || record.RequestedAt > inheritFromRequestedAt.Value))
                                        {
                                            inheritFrom = record.RequestId;
                                            inheritFromRequestedAt = record.RequestedAt;
                                        }
                                    }
                                }

                                if (inheritFrom.HasValue)
                                {
                                    resolvedRequestId = inheritFrom.Value;
                                }
                                else
                                {
                                    resolvedRequestId = Guid.NewGuid();
                                    var defaultName = System.IO.Path.GetFileName(file.Filename.Replace('\\', '/').TrimEnd('/'));
                                    newRequestEntity = new DownloadRequest
                                    {
                                        Id = resolvedRequestId,
                                        Name = string.IsNullOrEmpty(file.RequestName) ? (string.IsNullOrEmpty(defaultName) ? file.Filename : defaultName) : file.RequestName,
                                        OriginalFilename = file.Filename,
                                        Size = file.Size,
                                        BatchId = file.BatchId,
                                        BatchExternalId = file.BatchExternalId,
                                        DestinationDirectory = file.DestinationDirectory,
                                        State = DownloadRequestState.Active,
                                        CreatedAt = DateTime.UtcNow,
                                        WishlistItemId = file.WishlistItemId,
                                        SearchId = file.SearchId,
                                        SearchText = file.SearchText,
                                        BitRate = file.BitRate,
                                        SampleRate = file.SampleRate,
                                        BitDepth = file.BitDepth,
                                        Length = file.Length,
                                    };
                                    context.Add(newRequestEntity);
                                }
                            }

                            /*
                                add the transfer record to the database in the Queued | Locally state, and set the 'Removed'
                                property of any existing transfer to 'true', allowing the new record to supersede any old record(s)
                                on the UI

                                we have to persist these changes to the database at this time so the record shows up on the UI,
                                otherwise the transfers only show up as they are enqueued.
                            */
                            var transfer = new Transfer()
                            {
                                Id = transferId,
                                RequestId = resolvedRequestId,
                                Username = username,
                                Direction = TransferDirection.Download,
                                Filename = file.Filename, // important! use the remote filename
                                Size = file.Size,
                                BatchId = file.BatchId,
                                DestinationDirectory = file.DestinationDirectory,
                                StartOffset = 0, // todo: maybe implement resumeable downloads?
                                AutoReplaceAttempts = file.AutoReplaceAttempts,
                                RequestedAt = DateTime.UtcNow,
                                State = TransferStates.Queued | TransferStates.Locally,
                                BitRate = file.BitRate,
                                SampleRate = file.SampleRate,
                                BitDepth = file.BitDepth,
                                Length = file.Length,
                            };

                            context.Add(transfer);

                            Log.Debug("Added Transfer record for download of {Filename} from {Username} (id: {Id})",
                                LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username), transfer.Id);

                            if (existingFilenameRecords != null)
                            {
                                foreach (var record in existingFilenameRecords)
                                {
                                    if (record.Removed)
                                    {
                                        continue;
                                    }

                                    record.Removed = true;
                                    context.Update(record);
                                    Log.Debug("Marked existing download record of {Filename} from {Username} removed (id: {Id})",
                                        LoggingSanitizer.SanitizeFilePath(file.Filename), LoggingSanitizer.SanitizeExternalIdentifier(username), record.Id);
                                }
                            }

                            /*
                                create a TaskCompletionSource that we can await for one of the following:

                                1. the transfer enters the Queued | Remotely state
                                2. the transfer enters a state containing Completed
                                3. the linked CancellationTokenSource we add to CancellationTokens is cancelled
                                4. the 'max wait time' CancellationTokenSource is cancelled

                                add this to the dictionary before inserting the record, so we are guaranteed to have it
                                in the right place once the transfer hits the UI
                            */
                            var enqueuedTcs = new TaskCompletionSource<Transfer>(TaskCreationOptions.RunContinuationsAsynchronously);
                            _ = TaskObservation.Observe(
                                enqueuedTcs.Task,
                                ex => Log.Debug(
                                    "Observed terminal download enqueue signal fault for {Filename} from {Username}: {Exception}",
                                    LoggingSanitizer.SanitizeFilePath(file.Filename),
                                    LoggingSanitizer.SanitizeExternalIdentifier(username),
                                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString())));

                            // satisfies condition #3; CancellationTokenSource set cancelled by the user (via API call)
                            var cts = new CancellationTokenSource();
                            CancellationTokens.TryAdd(transfer.Id, cts);
                            cts.Token.Register(() => enqueuedTcs.TrySetCanceled());

                            /*
                                DANGER ZONE! this record is in the database now; we're on the hook for making sure it ends up
                                with a State that includes the Completed flag, else it remain "stuck" on the UI
                            */
                            context.SaveChanges();

                            Log.Debug("Scheduling Task for enqueue of {Filename} from {Username}",
                                LoggingSanitizer.SanitizeFilePath(file.Filename), LoggingSanitizer.SanitizeExternalIdentifier(username));

                            var downloadEnqueueTask = TrackTransferTask(
                                ActiveEnqueueTasks,
                                transferId,
                                ObserveDownloadEnqueueTaskAsync(Task.Run(async () =>
                            {
                                Log.Debug("Awaiting download enqueue semaphore for {Filename} from {Username}",
                                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username));
                                await enqueueSemaphore.WaitAsync(cts.Token);

                                try
                                {
                                    Log.Debug("Acquired download enqueue semaphore for {Filename} from {Username}",
                                        LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username));

                                    List<string> transitions = [];
                                    TransferStates state = TransferStates.None;

                                    // satisfies condition #4; remote user doesn't respond after a really long time
                                    using var timeoutCts = new CancellationTokenSource(maxTimeToWaitForEnqueueRequestAck);
                                    timeoutCts.Token.Register(() =>
                                    {
                                        Log.Information("Download of {Filename} from {Username} did not enqueue remotely within {Duration} seconds. State transition history: {History}",
                                            LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                                            maxTimeToWaitForEnqueueRequestAck.TotalSeconds, string.Join(", ", transitions));
                                        enqueuedTcs.TrySetException(new TimeoutException($"Download failed to enqueue remotely after hard time limit of {maxTimeToWaitForEnqueueRequestAck.TotalSeconds} secs"));
                                        CancelTrackedDownload(transfer.Id, transfer.Filename, username, "remote enqueue acknowledgement timed out");
                                    });

                                    // satisfies conditions #1 and #2
                                    void stateChanged(Transfer transfer)
                                    {
                                        state = transfer.State;
                                        transitions.Add(transfer.State.ToString());

                                        if (transfer.State.HasFlag(TransferStates.Queued) && transfer.State.HasFlag(TransferStates.Remotely))
                                        {
                                            // satisfies condition #1; transfer is now remotely queued
                                            enqueuedTcs.TrySetResult(transfer);
                                        }

                                        // satisfies condition #2; transfer advanced to a terminal state before being enqueued remotely (probably failed)
                                        if (transfer.State.HasFlag(TransferStates.Completed))
                                        {
                                            if (transfer.State.HasFlag(TransferStates.Succeeded))
                                            {
                                                enqueuedTcs.TrySetResult(transfer);
                                            }
                                            else
                                            {
                                                enqueuedTcs.TrySetException(new TransferException(transfer.Exception));
                                            }
                                        }
                                    }

                                    Log.Debug("Scheduling Task for download of {Filename} from {Username}",
                                        LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username));

                                    var downloadTask = TrackTransferTask(
                                        ActiveDownloadTasks,
                                        transferId,
                                        ObserveDownloadTaskAsync(
                                            Task.Run(() => DownloadAsync(transfer, stateChanged, cancellationToken: cts.Token)),
                                            transferId,
                                            file.Filename,
                                            username));

                                    Log.Debug("Download Task status for {Filename} from {Username}: {Status}",
                                        LoggingSanitizer.SanitizeFilePath(file.Filename), LoggingSanitizer.SanitizeExternalIdentifier(username), downloadTask.Status);

                                    Log.Debug("Waiting for download of {Filename} from {Username} to transition into {State}",
                                        LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username), TransferStates.Queued | TransferStates.Remotely);

                                    /*
                                        wait for one of the four conditions to be true:

                                        1. the transfer enters the Queued | Remotely state
                                        2. the transfer enters a state containing Completed
                                        3. the linked CancellationTokenSource we add to CancellationTokens is cancelled
                                        4. the 'max wait time' CancellationTokenSource is cancelled
                                    */
                                    var enqueueAcknowledgementTask = enqueuedTcs.Task;
                                    var completedTask = await Task.WhenAny(enqueueAcknowledgementTask, downloadTask);
                                    if (completedTask == downloadTask && !enqueueAcknowledgementTask.IsCompleted)
                                    {
                                        // A download may terminate before Soulseek reports a remote enqueue
                                        // transition (for example, an expected remote failure). Release the
                                        // enqueue semaphore using the state persisted by the download observer.
                                        enqueuedTcs.TrySetResult(Find(t => t.Id == transfer.Id) ?? transfer);
                                    }

                                    await enqueueAcknowledgementTask;

                                    Log.Debug("Download of {Filename} from {Username} successfully entered state {State}",
                                        LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username), state);
                                }
                                catch (Exception ex) when (IsShutdownCancellation(ex))
                                {
                                    Log.Debug("Download enqueue for {File} from {Username} cancelled during shutdown: {Exception}",
                                        LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                                        LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                                }
                                catch (Exception ex) when (IsCancellationException(ex) || IsDownloadTimeout(ex))
                                {
                                    Log.Information("Download of {File} from {Username} timed out or was cancelled while waiting for remote enqueue: {Exception}",
                                        LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                                        LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                                    CancelTrackedDownload(transfer.Id, transfer.Filename, transfer.Username, "remote enqueue wait ended");
                                    if (!TryFail(transferId, exception: ex))
                                    {
                                        Log.Debug("Transfer {Id} was already cleaned up after timed out or cancelled enqueue", transfer.Id);
                                    }
                                }
                                catch (Exception ex) when (IsExpectedRemoteDownloadFailure(ex))
                                {
                                    Log.Debug("Download of {File} from {Username} failed while waiting for remote enqueue because {Reason}: {Diagnostic}",
                                        LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                                        LoggingSanitizer.SanitizeExternalIdentifier(DescribeExpectedRemoteDownloadFailureReason(ex)),
                                        LoggingSanitizer.SanitizeExternalIdentifier(DescribeRemoteDownloadFailure(ex)));
                                    if (!TryFail(transferId, exception: ex))
                                    {
                                        Log.Debug("Transfer {Id} was already cleaned up after expected remote enqueue failure", transfer.Id);
                                    }
                                }
                                catch (Exception ex)
                                {
                                    Log.Error("Download of {File} from {Username} failed: {Exception}",
                                        LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                                        LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                                    if (!TryFail(transferId, exception: ex))
                                    {
                                        Log.Error("Failed to clean up transfer {Id} after failed execution: {Exception}",
                                            transfer.Id, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                                    }
                                }
                                finally
                                {
                                    ReleaseSemaphore(enqueueSemaphore, "download enqueue", transfer.Filename, transfer.Username);
                                }
                            }, cancellationToken: cts.Token),
                                    transferId,
                                    file.Filename,
                                    username));

                            trackedEnqueueTasks.Add(downloadEnqueueTask);
                            Log.Debug("Download enqueue Task status for {Filename} from {Username}: {Status}",
                                LoggingSanitizer.SanitizeFilePath(file.Filename), LoggingSanitizer.SanitizeExternalIdentifier(username), downloadEnqueueTask.Status);
                            Log.Information("Successfully locally enqueued download of {Filename} from {Username} (id: {Id})",
                                LoggingSanitizer.SanitizeFilePath(file.Filename), LoggingSanitizer.SanitizeExternalIdentifier(username), transferId);
                            enqueued.Add(transfer);
                        }
                        catch (Exception ex) when (IsExpectedRemoteDownloadFailure(ex))
                        {
                            Log.Information("Failed to enqueue download of {Filename} from {Username} because {Reason}: {Diagnostic}",
                                LoggingSanitizer.SanitizeFilePath(file.Filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                                LoggingSanitizer.SanitizeExternalIdentifier(DescribeExpectedRemoteDownloadFailureReason(ex)),
                                LoggingSanitizer.SanitizeExternalIdentifier(DescribeRemoteDownloadFailure(ex)));
                            TryFail(transferId, exception: ex);
                            failed.Add(file.Filename);

                            if (CancellationTokens.TryRemove(transferId, out var cts))
                            {
                                cts?.Dispose();
                            }
                        }
                        catch (Exception ex)
                        {
                            Log.Error("Failed to enqueue download of {Filename} from {Username}: {Exception}",
                                LoggingSanitizer.SanitizeFilePath(file.Filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                                LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                            TryFail(transferId, exception: ex);
                            failed.Add(file.Filename);

                            if (CancellationTokens.TryRemove(transferId, out var cts))
                            {
                                cts.Dispose();
                            }

                            continue;
                        }
                    } // end foreach()

                    Log.Information("Successfully enqueued {Count} files from {Username}", enqueued.Count, LoggingSanitizer.SanitizeExternalIdentifier(username));
                    return (enqueued, failed);
                }
                finally
                {
                    ObserveEnqueueTasksWhenIdle(trackedEnqueueTasks);
                }
            }
            catch (Exception ex)
            {
                Log.Error("Failed to enqueue one or more of {Count} files from {Username}: {Exception}", fileList.Count,
                    LoggingSanitizer.SanitizeExternalIdentifier(username), LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
            finally
            {
                ReleaseSemaphore(userSemaphore, "download enqueue user", null, username);
                Log.Debug("Released enqueue semaphore for user {Username}", LoggingSanitizer.SanitizeExternalIdentifier(username));
            }
        }

        /// <summary>
        ///     Finds a single download matching the specified <paramref name="expression"/>.
        /// </summary>
        /// <param name="expression">The expression to use to match downloads.</param>
        /// <returns>The found transfer, or default if not found.</returns>
        public Transfer? Find(Expression<Func<Transfer, bool>> expression)
        {
            try
            {
                using var context = ContextFactory.CreateDbContext();

                return context.Transfers
                    .AsNoTracking()
                    .Where(t => t.Direction == TransferDirection.Download)
                    .Where(expression).FirstOrDefault();
            }
            catch (Exception ex)
            {
                Log.Error("Failed to find download: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        /// <summary>
        ///     Retrieves the place in the remote queue for the download matching the specified <paramref name="id"/>.
        /// </summary>
        /// <param name="id">The unique identifier for the download.</param>
        /// <returns>The retrieved place in queue.</returns>
        public async Task<int> GetPlaceInQueueAsync(Guid id)
        {
            using var context = ContextFactory.CreateDbContext();

            var transfer = context.Transfers.Find(id);

            if (transfer == default)
            {
                throw new NotFoundException($"No download matching id ${id}");
            }

            var place = await Client.GetDownloadPlaceInQueueAsync(transfer.Username, transfer.Filename);

            transfer.PlaceInQueue = place;
            context.SaveChanges();

            return place;
        }

        /// <summary>
        ///     Returns a list of all downloads matching the optional <paramref name="expression"/>.
        /// </summary>
        /// <param name="expression">An optional expression used to match downloads.</param>
        /// <param name="includeRemoved">Optionally include downloads that have been removed previously.</param>
        /// <returns>The list of downloads matching the specified expression, or all downloads if no expression is specified.</returns>
        public List<Transfer> List(Expression<Func<Transfer, bool>>? expression = null, bool includeRemoved = false)
        {
            expression ??= t => true;

            try
            {
                using var context = ContextFactory.CreateDbContext();

                return context.Transfers
                    .AsNoTracking()
                    .Where(t => t.Direction == TransferDirection.Download)
                    .Where(t => !t.Removed || includeRemoved)
                    .Where(expression)
                    .ToList();
            }
            catch (Exception ex)
            {
                Log.Error("Failed to list downloads: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        public List<Transfer> ListPage(
            Expression<Func<Transfer, bool>> expression,
            bool includeRemoved,
            DateTime? afterRequestedAt,
            Guid? afterId,
            int limit)
        {
            expression ??= t => true;

            try
            {
                using var context = ContextFactory.CreateDbContext();
                var query = context.Transfers
                    .AsNoTracking()
                    .Where(t => t.Direction == TransferDirection.Download)
                    .Where(t => !t.Removed || includeRemoved)
                    .Where(expression);

                if (afterRequestedAt.HasValue && afterId.HasValue)
                {
                    var requestedAt = afterRequestedAt.Value;
                    var id = afterId.Value;
                    query = query.Where(t =>
                        t.RequestedAt < requestedAt ||
                        (t.RequestedAt == requestedAt && t.Id.CompareTo(id) < 0));
                }

                return query
                    .OrderByDescending(t => t.RequestedAt)
                    .ThenByDescending(t => t.Id)
                    .Take(limit)
                    .ToList();
            }
            catch (Exception ex)
            {
                Log.Error("Failed to page downloads: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        public async IAsyncEnumerable<Transfer> StreamAutoRetryCandidatesAsync(
            DateTime endedBefore,
            [EnumeratorCancellation] CancellationToken cancellationToken = default)
        {
            await using var context = ContextFactory.CreateDbContext();

            var query = context.Transfers
                .AsNoTracking()
                .Where(transfer => transfer.Direction == TransferDirection.Download)
                .Where(transfer => !transfer.Removed)
                .Where(transfer =>
                    (transfer.State & TransferStates.Completed) == TransferStates.Completed &&
                    (transfer.State & TransferStates.Succeeded) != TransferStates.Succeeded &&
                    (transfer.State & TransferStates.Cancelled) != TransferStates.Cancelled &&
                    (transfer.State & TransferStates.Rejected) != TransferStates.Rejected)
                .Where(transfer => transfer.EndedAt.HasValue && transfer.EndedAt.Value < endedBefore)
                .OrderBy(transfer => transfer.EndedAt)
                .ThenBy(transfer => transfer.Id)
                .Select(transfer => new Transfer
                {
                    Id = transfer.Id,
                    RequestId = transfer.RequestId,
                    Username = transfer.Username,
                    Direction = transfer.Direction,
                    Filename = transfer.Filename,
                    Size = transfer.Size,
                    State = transfer.State,
                    EndedAt = transfer.EndedAt,
                });

            var maxAttempts = OptionsMonitor.CurrentValue?.Global?.Download?.AutoRetry?.MaxAttempts ?? 0;
            if (maxAttempts > 0)
            {
                query = query.Where(transfer =>
                    !transfer.RequestId.HasValue ||
                    context.Transfers.Count(attempt => attempt.RequestId == transfer.RequestId.Value) <= maxAttempts);
            }

            await foreach (var transfer in query.AsAsyncEnumerable().WithCancellation(cancellationToken))
            {
                if (DownloadFilter.IsExcluded(
                    transfer.Filename,
                    OptionsMonitor.CurrentValue?.Filters.Download.Exclude ?? Array.Empty<string>()))
                {
                    Log.Debug("Skipping auto-retry candidate {Filename}; blocked by global download policy",
                        LoggingSanitizer.SanitizeFilePath(transfer.Filename));
                    continue;
                }

                yield return transfer;
            }
        }

        public int Count(bool includeRemoved = false)
        {
            using var context = ContextFactory.CreateDbContext();
            var query = context.Transfers
                .AsNoTracking()
                .Where(transfer => transfer.Direction == TransferDirection.Download);
            if (!includeRemoved)
            {
                query = query.Where(transfer => !transfer.Removed);
            }

            return query.Count();
        }

        public List<Transfer> ListCompleted(DateTime asOf, int offset, int limit)
        {
            using var context = ContextFactory.CreateDbContext();

            return context.Transfers
                .AsNoTracking()
                .Where(transfer => transfer.Direction == TransferDirection.Download)
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
        }

        /// <summary>
        ///     Removes <see cref="TransferStates.Completed"/> downloads older than the specified <paramref name="age"/>.
        /// </summary>
        /// <param name="age">The age after which downloads are eligible for pruning, in hours.</param>
        /// <param name="stateHasFlag">An optional, additional state by which downloads are filtered for pruning.</param>
        /// <returns>The number of pruned downloads.</returns>
        public int Prune(int age, TransferStates stateHasFlag = TransferStates.Completed)
        {
            if (!stateHasFlag.HasFlag(TransferStates.Completed))
            {
                throw new ArgumentException($"State must include {TransferStates.Completed}", nameof(stateHasFlag));
            }

            try
            {
                using var context = ContextFactory.CreateDbContext();

                var cutoffDateTime = DateTime.UtcNow.AddMinutes(-age);

                var expired = context.Transfers
                    .Where(t => t.Direction == TransferDirection.Download)
                    .Where(t => !t.Removed)
                    .Where(t => t.EndedAt.HasValue && t.EndedAt.Value < cutoffDateTime)
                    .Where(t => t.State == stateHasFlag)
                    .ToList();

                foreach (var tx in expired)
                {
                    tx.Removed = true;
                }

                var pruned = context.SaveChanges();

                if (pruned > 0)
                {
                    Log.Debug("Pruned {Count} expired downloads with state {State}", pruned, stateHasFlag);
                }

                return pruned;
            }
            catch (Exception ex)
            {
                Log.Error("Failed to prune downloads: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        /// <summary>
        ///     Permanently deletes soft-removed, completed downloads older than the specified <paramref name="age"/>.
        /// </summary>
        /// <param name="age">The time since the last transfer update, in minutes.</param>
        /// <returns>The number of deleted downloads.</returns>
        public int PruneRemoved(int age)
        {
            try
            {
                using var context = ContextFactory.CreateDbContext();
                using var transaction = context.Database.BeginTransaction();
                var cutoffDateTime = DateTime.UtcNow.AddMinutes(-age);
                var pruned = context.Transfers
                    .Where(t => t.Direction == TransferDirection.Download)
                    .Where(t => t.Removed)
                    .Where(t => t.EndedAt.HasValue)
                    .Where(t => t.UpdatedAt < cutoffDateTime)
                    .ExecuteDelete();

                var prunedRequests = context.DownloadRequests
                    .Where(request => request.State != DownloadRequestState.Active)
                    .Where(request => (request.CompletedAt ?? request.CreatedAt) < cutoffDateTime)
                    .Where(request => !context.Transfers.Any(transfer =>
                        transfer.Direction == TransferDirection.Download &&
                        transfer.RequestId == request.Id))
                    .ExecuteDelete();

                transaction.Commit();

                if (pruned > 0)
                {
                    Log.Debug("Permanently deleted {Count} removed downloads older than {Age} minutes", pruned, age);
                }

                if (prunedRequests > 0)
                {
                    Log.Debug("Permanently deleted {Count} expired terminal download requests with no remaining transfers", prunedRequests);
                }

                return pruned;
            }
            catch (Exception ex)
            {
                Log.Error("Failed to permanently delete removed downloads: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        /// <summary>
        ///     Removes the download matching the specified <paramref name="id"/>.
        /// </summary>
        /// <remarks>This is a soft delete; the record is retained for historical retrieval.</remarks>
        /// <param name="id">The unique identifier of the download.</param>
        /// <param name="deleteFile">Whether the on-disk file should also be removed.</param>
        public void Remove(Guid id, bool deleteFile = false)
        {
            try
            {
                using var context = ContextFactory.CreateDbContext();

                var transfer = context.Transfers
                    .Where(t => t.Direction == TransferDirection.Download)
                    .Where(t => t.Id == id)
                    .FirstOrDefault();

                if (transfer == default)
                {
                    throw new NotFoundException($"No download matching id ${id}");
                }

                if (!transfer.State.HasFlag(TransferStates.Completed))
                {
                    throw new InvalidOperationException($"Invalid attempt to remove a download before it is complete");
                }

                if (deleteFile)
                {
                    try
                    {
                        var options = OptionsMonitor.CurrentValue;
                        var baseDirectory = transfer.State.HasFlag(TransferStates.Succeeded)
                            ? transfer.DestinationDirectory ?? Destinations.DownloadDestinationResolver.GetDefaultPath(options)
                            : options.Directories.Incomplete;
                        var localFilename = !string.IsNullOrWhiteSpace(transfer.LocalFilename)
                            ? transfer.LocalFilename
                            : GetLocalFilenameForRemoval(transfer, baseDirectory);
                        var allowedRoots = transfer.State.HasFlag(TransferStates.Succeeded)
                            ? Destinations.DownloadDestinationResolver.GetAllowedRoots(options)
                            : new[] { options.Directories.Incomplete, ResolveQuarantineDirectory(options) };
                        var normalizedFilename = PathGuard.NormalizeAbsolutePathWithinRoots(localFilename, allowedRoots);

                        if (normalizedFilename is null)
                        {
                            Log.Warning("Skipped deleting download file {Filename} because it resolves outside configured directories",
                                LoggingSanitizer.SanitizeFilePath(localFilename));
                        }
                        else if (System.IO.File.Exists(normalizedFilename))
                        {
                            System.IO.File.Delete(normalizedFilename);
                            Log.Information("Deleted file {Filename} for removed download {Id}", LoggingSanitizer.SanitizeFilePath(normalizedFilename), id);

                            // Recursively delete empty parent directories up to base directory
                            var directory = System.IO.Path.GetDirectoryName(normalizedFilename);
                            var normalizedBase = System.IO.Path.GetFullPath(baseDirectory);

                            while (!string.IsNullOrEmpty(directory) &&
                                   System.IO.Directory.Exists(directory) &&
                                   !System.IO.Directory.EnumerateFileSystemEntries(directory).Any() &&
                                   System.IO.Path.GetFullPath(directory) != normalizedBase &&
                                   PathGuard.IsContainedIn(System.IO.Path.GetFullPath(directory), normalizedBase))
                            {
                                System.IO.Directory.Delete(directory);
                                Log.Debug("Deleted empty directory {Directory}", LoggingSanitizer.SanitizeFilePath(directory));
                                directory = System.IO.Path.GetDirectoryName(directory);
                            }
                        }
                        else
                        {
                            Log.Warning("File {Filename} not found for deletion", LoggingSanitizer.SanitizeFilePath(localFilename));
                        }
                    }
                    catch (Exception ex)
                    {
                        Log.Error("Failed to delete file for download {Id}: {Exception}", id,
                            LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                    }
                }

                transfer.Removed = true;

                context.SaveChanges();
            }
            catch (Exception ex)
            {
                Log.Error("Failed to remove download {Id}: {Exception}", id, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        private static string GetLocalFilenameForRemoval(Transfer transfer, string baseDirectory)
        {
            if (transfer.State.HasFlag(TransferStates.Succeeded) && transfer.BatchId.HasValue)
            {
                var originalLocalFilename = transfer.Filename.ToLocalFilename(baseDirectory);
                return System.IO.Path.Combine(
                    baseDirectory,
                    transfer.BatchId.Value.ToString(),
                    System.IO.Path.GetFileName(originalLocalFilename));
            }

            return transfer.Filename.ToLocalFilename(baseDirectory);
        }

        /// <summary>
        ///     Cancels the download matching the specified <paramref name="id"/>, if it is in progress.
        /// </summary>
        /// <param name="id">The unique identifier for the download.</param>
        /// <returns>A value indicating whether the download was successfully cancelled.</returns>
        public bool TryCancel(Guid id)
        {
            // if the cancellation token is still in the dictionary, calling Cancel() on it _should_
            // cause the transfer operation to fail with an OperationCancelled exception and set the state
            // of the transfer to Cancelled.  _should_!
            if (CancellationTokens.TryRemove(id, out var cts))
            {
                using (cts)
                {
                    var transfer = Find(t => t.Id == id);
                    if (transfer?.State.HasFlag(TransferStates.Completed) == true)
                    {
                        return false;
                    }

                    cts.Cancel();
                }

                return true;
            }

            /*
                if the cancellation token couldn't be found in the dictionary, either:

                1. the transfer completed already
                2. something went wrong and the record is 'stuck'

                see if we can find the record, and if it's *NOT* completed, cancel it. otherwise,
                leave it alone.
            */
            var t = Find(t => t.Id == id);

            if (t is not null && !t.State.HasFlag(TransferStates.Completed))
            {
                t.EndedAt = DateTime.UtcNow;
                t.State = TransferStates.Completed | TransferStates.Cancelled;
                t.Exception = new OperationCanceledException().Message;
                Update(t);
                return true;
            }

            // this transfer id didn't have a cancellation token registered, and we couldn't find it in the dictionary
            return false;
        }

        /// <summary>
        ///     Fails the download matching the specified <paramref name="id"/> with the specified <paramref name="exception"/>,
        ///     and sets the final state accordingly.
        /// </summary>
        /// <remarks>
        ///     This method is designed to be idempotent, meaning subsequent calls for a given transfer shouldn't change
        ///     the EndedAt or Exception properties if they have already been set. If the transfer State already includes
        ///     the terminal Completed flag, it is unchanged.
        /// </remarks>
        /// <param name="id">The unique identifier for the download.</param>
        /// <param name="exception">The exception that caused the failure.</param>
        /// <returns>A value indicating whether the download was successfully failed.</returns>
        public bool TryFail(Guid id, Exception exception)
        {
            if (Application.IsShuttingDown)
            {
                Log.Debug("Ignoring TryFail for {TransferId} because the application is shutting down", id);
                return false;
            }

            Transfer? t;
            try
            {
                t = Find(t => t.Id == id);
            }
            catch (ObjectDisposedException)
            {
                // Occurs during shutdown when the service provider/db context is already disposed.
                Log.Debug("Ignoring TryFail for {TransferId} because services are disposed during shutdown", id);
                return false;
            }

            if (t is null)
            {
                return false;
            }

            t.EndedAt ??= DateTime.UtcNow;
            t.Exception ??= exception.Message;

            if (!t.State.HasFlag(TransferStates.Completed))
            {
                t.State = TransferStates.Completed | exception switch
                {
                    _ when IsCancellationException(exception) => TransferStates.Cancelled,
                    _ when IsDownloadTimeout(exception) => TransferStates.TimedOut,
                    _ when exception is DownloadBlockedByPolicyException => TransferStates.Rejected,
                    _ => TransferStates.Errored,
                };
            }

            try
            {
                Update(t);

                // Raise failure event for ranking history tracking
                EventBus.Raise(new Events.DownloadFileFailedEvent
                {
                    Timestamp = t.EndedAt.Value,
                    RemoteFilename = t.Filename,
                    Transfer = t,
                    ErrorMessage = exception.Message,
                });

                return true;
            }
            catch (Exception ex)
            {
                Log.Error("Failed to update database: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                return false;
            }
        }

        private bool IsActiveClientDownload(string username, string filename)
            => Client.Downloads?.Any(download =>
                download.Username == username &&
                download.Filename == filename &&
                !download.State.HasFlag(TransferStates.Completed)) ?? false;

        private void CancelTrackedDownload(Guid transferId, string filename, string username, string reason)
        {
            if (!CancellationTokens.TryGetValue(transferId, out var cts))
            {
                return;
            }

            try
            {
                cts.Cancel();
                Log.Debug("Cancelled tracked download token for {Filename} from {Username} because {Reason}",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(reason));
            }
            catch (ObjectDisposedException)
            {
                Log.Debug("Tracked download token for {Filename} from {Username} was already disposed before cancellation after {Reason}",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(reason));
            }
        }

        /// <summary>
        ///     Synchronously updates the specified <paramref name="transfer"/>.
        /// </summary>
        /// <param name="transfer">The transfer to update.</param>
        public void Update(Transfer transfer)
        {
            using var context = ContextFactory.CreateDbContext();

            context.Update(transfer);
            context.SaveChanges();
        }

        /// <summary>
        ///     Downloads the specified enqueued <paramref name="transfer"/> from the remote user.
        /// </summary>
        /// <param name="transfer">The Transfer to download.</param>
        /// <param name="stateChanged">An optional delegate to invoke the transfer state changes.</param>
        /// <param name="cancellationToken">The token to monitor for cancellation.</param>
        /// <returns>The operation context.</returns>
        /// <exception cref="ArgumentNullException">Thrown if the specified Transfer is null.</exception>
        /// <exception cref="TransferNotFoundException">Thrown if the specified Transfer ID can't be found in the database.</exception>
        /// <exception cref="InvalidOperationException">Thrown if the specified Transfer is not in the Queued | Locally state.</exception>
        /// <exception cref="DuplicateTransferException">Thrown if a download matching the username and filename is already tracked by Soulseek.NET.</exception>
        private async Task<Transfer> DownloadAsync(Transfer transfer, Action<Transfer>? stateChanged = null, CancellationToken cancellationToken = default)
        {
            if (transfer is null)
            {
                throw new ArgumentNullException(nameof(transfer), "A valid, enqueued Transfer is required");
            }

            // grab the latest from the database; this may have been sitting behind a semaphore or something
            transfer = Find(t => t.Id == transfer.Id)
                ?? throw new TransferNotFoundException($"Transfer with ID {transfer.Id} not found");

            if (transfer.State != (TransferStates.Queued | TransferStates.Locally))
            {
                throw new InvalidOperationException($"Invalid starting state for download; expected {TransferStates.Queued | TransferStates.Locally}, encountered {transfer.State}");
            }

            if (IsActiveClientDownload(transfer.Username, transfer.Filename))
            {
                throw new DuplicateTransferException("A duplicate download of the same file to the same user is already registered");
            }

            // there _should_ be a cancellation token for this transfer in the dictionary; if so link it with the one we are given
            // (which is probably the same one, harmless if so) to make sure we don't get any wires crossed
            CancellationTokens.TryGetValue(transfer.Id, out var cancellationTokenSource);
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, cancellationTokenSource?.Token ?? CancellationToken.None);
            cancellationToken = cts.Token;

            var updateSyncRoot = new object();
            string? quarantinedFilename = null;
            string? contentSafetyFailureMessage = null;

            var policyExclusion = DownloadFilter.GetMatchingExclusion(
                transfer.Filename,
                OptionsMonitor.CurrentValue.Filters.Download.Exclude);
            if (policyExclusion is not null)
            {
                var policyException = new DownloadBlockedByPolicyException(transfer.Filename, policyExclusion);
                TryFail(transfer.Id, policyException);
                transfer = Find(t => t.Id == transfer.Id) ?? transfer;
                stateChanged?.Invoke(transfer);
                throw policyException;
            }

            // Track bytes for throughput calculation
            long lastBytesTransferred = 0;
            DateTime lastProgressUpdate = DateTime.UtcNow;

            try
            {
                using var rateLimiter = new RateLimiter(250, concurrencyLimit: 1, flushOnDispose: true);

                var topts = new TransferOptions(
                    progressUpdateInterval: 250,
                    progressUpdateMinimumBytes: 1024 * 1024,
                    stateChanged: (args) =>
                    {
                        try
                        {
                            Log.Debug("Download of {Filename} from user {Username} changed state from {Previous} to {New}",
                                LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                                args.PreviousState, args.Transfer.State);

                            // prevent Exceptions thrown during shutdown from updating the transfer record with related Exceptions;
                            // instead, allow these to be left "hanging" so that they are properly cleaned up at the next startup
                            if (Application.IsShuttingDown)
                            {
                                Log.Debug("Download update of {Filename} from {Username} not persisted; app is shutting down",
                                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username));
                                return;
                            }

                            transfer = transfer.WithSoulseekTransfer(args.Transfer);

                            // we don't know when the download is actually enqueued (remotely) until it switches into that state
                            // when it is enqueued locally is irrelevant, due to internal throttling etc
                            if (args.Transfer.State.HasFlag(TransferStates.Queued) && args.Transfer.State.HasFlag(TransferStates.Remotely))
                            {
                                transfer.EnqueuedAt ??= DateTime.UtcNow;
                            }

                            // Keep successful terminal state in memory until the file is verified and moved.
                            // A local post-download failure must still be able to mark the transfer as failed.
                            var completedSuccessfully = args.Transfer.State.HasFlag(TransferStates.Completed | TransferStates.Succeeded);
                            if (!completedSuccessfully)
                            {
                                // todo: broadcast
                                SynchronizedUpdate(transfer, semaphore: updateSyncRoot, cancellationToken: cancellationToken);
                            }
                        }
                        finally
                        {
                            if (stateChanged != null)
                            {
                                try
                                {
                                    stateChanged(transfer);
                                }
                                catch (Exception ex)
                                {
                                    Log.Warning("Download state callback failed for {Filename} from {Username}: {Exception}",
                                        LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                                        LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                                }
                            }
                        }
                    },
                    progressUpdated: (args) => rateLimiter.Invoke(() =>
                    {
                        // don't do anything unless the `transfer` within the outer scope is in the
                        // InProgress state; this will help prevent out-of-band updates that are sometimes
                        // being made after the transfer is completed, causing them to appear 'stuck'
                        if (transfer.State == TransferStates.InProgress)
                        {
                            // don't wait for the semaphore; if a previous progress update is still hanging, don't make
                            // the problem worse. this will result in fewer/jumpy updates on systems with slow filesystems
                            // but the alternative is to continue to stack slow writes on top of one another
                            if (!cancellationToken.IsCancellationRequested && Monitor.TryEnter(updateSyncRoot))
                            {
                                try
                                {
                                    // update only the properties that we expect to change between progress updates
                                    // this helps prevent this update from 'stepping' on other updates
                                    transfer.BytesTransferred = args.Transfer.BytesTransferred;
                                    transfer.AverageSpeed = args.Transfer.AverageSpeed;

                                    // Record throughput sample for peer metrics (Phase 2C - T-409)
                                    if (PeerMetrics != null)
                                    {
                                        var now = DateTime.UtcNow;
                                        var bytesThisUpdate = args.Transfer.BytesTransferred - lastBytesTransferred;
                                        var duration = now - lastProgressUpdate;

                                        if (bytesThisUpdate > 0 && duration.TotalMilliseconds > 0)
                                        {
                                            _ = ObserveBackgroundTaskAsync(
                                                PeerMetrics.RecordThroughputSampleAsync(
                                                    transfer.Username,
                                                    bytesThisUpdate,
                                                    duration,
                                                    cancellationToken),
                                                $"Failed to record throughput sample for {transfer.Username}");

                                            lastBytesTransferred = args.Transfer.BytesTransferred;
                                            lastProgressUpdate = now;
                                        }
                                    }

                                    using var context = ContextFactory.CreateDbContext();

                                    context.Transfers.Where(t => t.Id == transfer.Id).ExecuteUpdate(setter => setter
                                        .SetProperty(t => t.BytesTransferred, transfer.BytesTransferred)
                                        .SetProperty(t => t.AverageSpeed, transfer.AverageSpeed));
                                }
                                finally
                                {
                                    Monitor.Exit(updateSyncRoot);
                                }
                            }
                            else
                            {
                                Log.Debug("Skipped progress update of {Filename} from {Username} {BytesTransferred}/{TotalBytes}; previous update still pending",
                                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                                    args.Transfer.BytesTransferred, args.Transfer.Size);
                            }
                        }
                    }),
                    disposeOutputStreamOnCompletion: true);

                System.IO.UnixFileMode? unixFileMode = !string.IsNullOrEmpty(OptionsMonitor.CurrentValue.Permissions.File.Mode)
                    ? OptionsMonitor.CurrentValue.Permissions.File.Mode.ToUnixFileMode()
                    : null;

                var destinationPermissionsMode = OptionsMonitor.CurrentValue.Global.Download.Destination.Permissions.Mode;
                System.IO.UnixFileMode? completedUnixFileMode = !string.IsNullOrWhiteSpace(destinationPermissionsMode)
                    ? destinationPermissionsMode.ToUnixFileMode()
                    : unixFileMode;

                var retryOptions = OptionsMonitor.CurrentValue.Global.Download.Retry;
                var maxRetryDelay = Math.Max(30_000, retryOptions.MaxDelay);
                var incompleteStrategy = (retryOptions.Partial ?? retryOptions.Incomplete).ToEnum<RetryIncompleteStrategy>();
                var incompleteFilename = GetIncompleteRetryFilename(transfer);

                Log.Debug("Invoking Soulseek DownloadAsync() for {Filename} from {Username}",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username));
                transfer.Attempts = 1;
                SynchronizedUpdate(transfer, semaphore: updateSyncRoot, cancellationToken: CancellationToken.None);

                Task<Soulseek.Transfer> StartDownloadAttempt()
                {
                    transfer.NextAttemptAt = null;
                    SynchronizedUpdate(transfer, semaphore: updateSyncRoot, cancellationToken: CancellationToken.None);

                    var outputPlan = PlanIncompleteOutput(incompleteFilename, incompleteStrategy, transfer);
                    EnsureDirectoryReady(
                        System.IO.Path.GetDirectoryName(incompleteFilename),
                        unixFileMode,
                        incompleteFilename,
                        "Incomplete");

                    return Client.DownloadAsync(
                        username: transfer.Username,
                        remoteFilename: transfer.Filename,
                        outputStreamFactory: () => Task.FromResult(
                            Files.CreateFile(
                                filename: incompleteFilename,
                                options: new CreateFileOptions
                                {
                                    Access = System.IO.FileAccess.Write,
                                    Mode = outputPlan.Mode,
                                    Share = System.IO.FileShare.None, // exclusive access for the duration of the download
                                    UnixCreateMode = unixFileMode,
                                })),
                        size: transfer.Size,
                        startOffset: outputPlan.StartOffset,
                        token: null,
                        cancellationToken: cancellationToken,
                        options: topts);
                }

                void MarkWaitingRetry(int attempt, int delay)
                {
                    transfer.Attempts = attempt;
                    transfer.NextAttemptAt = DateTime.UtcNow.AddMilliseconds(delay);
                    transfer.State = TransferStates.Queued | TransferStates.Locally;
                    SynchronizedUpdate(transfer, semaphore: updateSyncRoot, cancellationToken: CancellationToken.None);
                    Log.Information("Retrying download of {Filename} from {Username}; attempt {Attempt} begins in about {Seconds} second(s)",
                        LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                        attempt, (int)Math.Ceiling(delay / 1000d));
                }

                void MarkFailedAttempt(int attempt, Exception ex)
                {
                    transfer.Attempts = attempt;
                    transfer.Exception = ex.Message;
                    SynchronizedUpdate(transfer, semaphore: updateSyncRoot, cancellationToken: CancellationToken.None);
                    if (IsExpectedRemoteDownloadFailure(ex))
                    {
                        Log.Debug("Attempt {Attempt} to download {Filename} from {Username} failed because {Reason}: {Diagnostic}",
                            attempt, LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                            LoggingSanitizer.SanitizeExternalIdentifier(DescribeExpectedRemoteDownloadFailureReason(ex)),
                            LoggingSanitizer.SanitizeExternalIdentifier(DescribeRemoteDownloadFailure(ex)));
                    }
                    else if (IsCancellationException(ex) || IsDownloadTimeout(ex))
                    {
                        Log.Debug("Attempt {Attempt} to download {Filename} from {Username} ended with expected timeout or cancellation: {Exception}",
                            attempt, LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                            LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                    }
                    else
                    {
                        Log.Warning("Attempt {Attempt} to download {Filename} from {Username} failed: {Exception}",
                            attempt, LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                            LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                    }
                }

                var completedTransfer = await Retry.Do(
                    StartDownloadAttempt,
                    isRetryable: (_, ex) => IsDirectDownloadRetryable(ex),
                    onRetry: MarkWaitingRetry,
                    onFailure: MarkFailedAttempt,
                    maxAttempts: retryOptions.Attempts,
                    baseDelayInMilliseconds: retryOptions.Delay,
                    maxDelayInMilliseconds: maxRetryDelay,
                    cancellationToken: cancellationToken);

                string GetIncompleteRetryFilename(Transfer pendingTransfer)
                {
                    var incompleteRoot = OptionsMonitor.CurrentValue.Directories.Incomplete;
                    var retryDirectory = pendingTransfer.BatchId is Guid batchId
                        ? System.IO.Path.Combine(incompleteRoot, batchId.ToString())
                        : incompleteRoot;

                    var localFilename = pendingTransfer.Filename.ToLocalFilename(baseDirectory: retryDirectory);
                    return PathGuard.NormalizeAbsolutePathWithinRoots(localFilename, new[] { incompleteRoot })
                        ?? throw new System.IO.IOException("Incomplete download path resolves outside its configured directory");
                }

                void EnsureDirectoryReady(
                    string? directory,
                    System.IO.UnixFileMode? createMode,
                    string localFilename,
                    string purpose)
                {
                    if (string.IsNullOrWhiteSpace(directory))
                    {
                        throw new System.IO.IOException($"Failed to determine {purpose.ToLowerInvariant()} directory for file {localFilename}");
                    }

                    if (!System.IO.Directory.Exists(directory))
                    {
                        Files.EnsureDirectory(directory, createMode);
                    }

                    var probeFilename = System.IO.Path.Combine(directory, $".slskdn-write-probe-{Guid.NewGuid():N}.tmp");
                    try
                    {
                        using var probeStream = new System.IO.FileStream(
                            probeFilename,
                            new System.IO.FileStreamOptions
                            {
                                Access = System.IO.FileAccess.Write,
                                Mode = System.IO.FileMode.CreateNew,
                                Share = System.IO.FileShare.None,
                                Options = System.IO.FileOptions.DeleteOnClose,
                            });
                    }
                    catch (Exception ex)
                    {
                        throw new System.IO.IOException($"{purpose} directory '{directory}' is not writable: {ex.Message}", ex);
                    }
                    finally
                    {
                        try
                        {
                            System.IO.File.Delete(probeFilename);
                        }
                        catch
                        {
                            // best-effort cleanup for filesystems that do not honor DeleteOnClose
                        }
                    }
                }

                (System.IO.FileMode Mode, long StartOffset) PlanIncompleteOutput(
                    string localFilename,
                    RetryIncompleteStrategy strategy,
                    Transfer pendingTransfer)
                {
                    var partial = Files.ResolveFileInfo(localFilename);

                    if (!partial.Exists || partial.Length <= 0)
                    {
                        return (System.IO.FileMode.Create, 0);
                    }

                    if (strategy == RetryIncompleteStrategy.Resume)
                    {
                        // Check if the existing file is actually writable by the current process.
                        // If not (e.g. stale file owned by a different user with no group write),
                        // delete it and start fresh instead of crashing with UnauthorizedAccessException.
                        try
                        {
                            using var probe = partial.OpenWrite();
                            Log.Information("Continuing partial download of {Filename} from {Username} at byte {Offset}",
                                LoggingSanitizer.SanitizeFilePath(pendingTransfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(pendingTransfer.Username), partial.Length);
                            return (System.IO.FileMode.Append, partial.Length);
                        }
                        catch (UnauthorizedAccessException)
                        {
                            Log.Warning("Existing incomplete file {Filename} exists but is not writable; deleting and starting fresh",
                                LoggingSanitizer.SanitizeFilePath(localFilename));
                            try
                            {
                                System.IO.File.Delete(localFilename);
                            }
                            catch (Exception deleteEx)
                            {
                                Log.Warning("Failed to delete unwritable incomplete file {Filename}: {Exception}",
                                    LoggingSanitizer.SanitizeFilePath(localFilename), LoggingSanitizer.SanitizeExternalIdentifier(deleteEx.ToString()));
                            }

                            return (System.IO.FileMode.Create, 0);
                        }
                    }

                    Log.Information("Discarding {Bytes} incomplete bytes before retrying {Filename} from {Username}",
                        partial.Length, LoggingSanitizer.SanitizeFilePath(pendingTransfer.Filename),
                        LoggingSanitizer.SanitizeExternalIdentifier(pendingTransfer.Username));
                    return (System.IO.FileMode.Create, 0);
                }

                Log.Debug("Invocation of Soulseek DownloadAsync() for {Filename} from user {Username} completed successfully",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username));

                // Record successful chunk completion for peer metrics (Phase 2C - T-409)
                if (PeerMetrics != null)
                {
                    // CancellationToken.None: download already completed; record success
                    // unconditionally (error paths at nearby catch blocks do the same).
                    _ = ObserveBackgroundTaskAsync(
                        PeerMetrics.RecordChunkCompletionAsync(
                            transfer.Username,
                            ChunkCompletionResult.Success,
                            cancellationToken: CancellationToken.None),
                        $"Failed to record successful chunk completion for {transfer.Username}");
                }

                // explicitly dispose the rate limiter to prevent updates from it beyond this point, and in doing so we
                // flush any pending update, _probably_ pushing the state of the transfer back to InProgress
                rateLimiter.Dispose();

                // copy the completed transfer that was returned from Soulseek.NET in a terminal, fully updated state
                // over the top of the in-memory transfer record. Persist success after verification and final placement.
                transfer = transfer.WithSoulseekTransfer(completedTransfer);

                var options = OptionsMonitor.CurrentValue;
                var safeIncompleteFilename = PathGuard.NormalizeAbsolutePathWithinRoots(
                    incompleteFilename,
                    new[] { options.Directories.Incomplete })
                    ?? throw new System.IO.IOException("Completed download path resolves outside its configured directory");
                var contentSafetyDisposition = await ContentSafety.InspectAndApplyPolicyAsync(
                    safeIncompleteFilename,
                    options.Directories.Incomplete,
                    options.Directories.Downloads,
                    options.Security,
                    cancellationToken);
                cancellationToken.ThrowIfCancellationRequested();
                if (contentSafetyDisposition.Verification is { } contentVerification &&
                    (contentVerification.IsWarning || !contentVerification.IsValid))
                {
                    Log.Warning(
                        "Content verification for {Filename} from {Username} reported {ThreatLevel}: {Message}",
                        LoggingSanitizer.SanitizeFilePath(transfer.Filename),
                        LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                        contentVerification.ThreatLevel,
                        LoggingSanitizer.SanitizeExternalIdentifier(contentVerification.Message));
                }

                if (contentSafetyDisposition.Rejected)
                {
                    contentSafetyFailureMessage = contentSafetyDisposition.Verification?.Message
                        ?? "Content did not pass configured safety checks";
                    quarantinedFilename = contentSafetyDisposition.QuarantinedPath;
                    throw new System.IO.InvalidDataException(
                        $"Content safety rejected '{transfer.Filename}': {contentSafetyFailureMessage}");
                }

                // move the file from incomplete to complete
                DownloadRequest? request = null;
                if (transfer.RequestId.HasValue)
                {
                    using var requestLookupCtx = ContextFactory.CreateDbContext();
                    request = requestLookupCtx.DownloadRequests.AsNoTracking().FirstOrDefault(r => r.Id == transfer.RequestId.Value);
                }

                var destinationDirectory = ResolveCompletedDestinationDirectory(transfer, request);

                EnsureDirectoryReady(
                    destinationDirectory,
                    completedUnixFileMode,
                    transfer.Filename,
                    "Destination");

                cancellationToken.ThrowIfCancellationRequested();
                var finalFilename = Files.MoveFile(
                    sourceFilename: incompleteFilename,
                    destinationDirectory: destinationDirectory,
                    unixFileMode: completedUnixFileMode,
                    overwrite: string.Equals(
                        OptionsMonitor.CurrentValue.Global.Download.Destination.Exists,
                        "overwrite",
                        StringComparison.OrdinalIgnoreCase),
                    deleteSourceDirectoryIfEmptyAfterMove: true,
                    unixDirectoryMode: completedUnixFileMode);

                Log.Debug("Moved file {Filename} to {Destination}",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeFilePath(finalFilename));
                transfer.LocalFilename = finalFilename;

                // Enrich transfer record with audio metadata from the downloaded file
                EnrichTransferMetadata(transfer, finalFilename);
                SynchronizedUpdate(transfer, semaphore: updateSyncRoot, cancellationToken: CancellationToken.None);

                if (OptionsMonitor.CurrentValue.Relay.Enabled)
                {
                    _ = ObserveBackgroundTaskAsync(
                        Relay.NotifyFileDownloadCompleteAsync(finalFilename),
                        $"Failed to notify relay agents of completed download {finalFilename}");
                }

                try
                {
                    // begin post-processing tasks; the file is downloaded, it has been removed from the client's download dictionary,
                    // and the file has been moved from the incomplete directory to the downloads directory
                    Log.Debug("Running post-download logic for {Filename} from {Username}",
                        LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username));

                    EventBus.Raise(new DownloadFileCompleteEvent
                    {
                        Timestamp = transfer.EndedAt ?? DateTime.UtcNow,
                        LocalFilename = finalFilename,
                        RemoteFilename = transfer.Filename,
                        Transfer = transfer,
                    });

                    // try to figure out if this file is the last of a directory, and if so, raise the associated
                    // event. this can be tricky because we want to be sure that this is the last file in this specific
                    // directory, excluding any pending downloads in a subdirectory.
                    var remoteDirectorySeparator = transfer.Filename.GuessDirectorySeparator();
                    var remoteDirectoryName = transfer.Filename.GetDirectoryName(directorySeparator: remoteDirectorySeparator);
                    var pendingDownloadsInDirectory = Client.Downloads
                        .Where(t => t.Username == transfer.Username)
                        .Where(t => t.Filename.GetDirectoryName(directorySeparator: remoteDirectorySeparator) == remoteDirectoryName);

                    if (!pendingDownloadsInDirectory.Any())
                    {
                        EventBus.Raise(new DownloadDirectoryCompleteEvent
                        {
                            Timestamp = transfer.EndedAt?.ToUniversalTime() ?? DateTime.UtcNow,
                            Username = transfer.Username,
                            LocalDirectoryName = destinationDirectory,
                            RemoteDirectoryName = remoteDirectoryName,
                            RequestId = transfer.RequestId,
                        });
                    }

                    if (OptionsMonitor.CurrentValue.Integration.Ftp.Enabled)
                    {
                        _ = ObserveBackgroundTaskAsync(
                            FTP.UploadAsync(finalFilename),
                            $"Failed to start FTP upload for completed download {finalFilename}");
                    }

                    Log.Debug("Completed post-download logic for {Filename} from {Username} successfully",
                        LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username));
                }
                catch (Exception ex)
                {
                    // log, but don't throw. the file ended up in the download folder and is complete; if we throw it looks like it didn't complete
                    // todo: add a visual indicator/new state for Transfers that indicate this state.  or move all of this logic out and handle it via events
                    Log.Error("Failed to run post-download processes for {Filename} from {Username}: {Exception}",
                        LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                        LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                }

                Log.Information("Download of {Filename} from user {Username} completed successfully",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username));

                if (transfer.RequestId.HasValue)
                {
                    try
                    {
                        using var requestCtx = ContextFactory.CreateDbContext();
                        requestCtx.DownloadRequests
                            .Where(r => r.Id == transfer.RequestId.Value)
                            .ExecuteUpdate(setter => setter
                                .SetProperty(r => r.State, DownloadRequestState.Completed)
                                .SetProperty(r => r.CompletedAt, DateTime.UtcNow));
                    }
                    catch (Exception ex)
                    {
                        Log.Debug("Failed to mark DownloadRequest {RequestId} as Completed: {Exception}",
                            transfer.RequestId, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                    }
                }

                return transfer;
            }
            catch (Exception ex) when (IsShutdownCancellation(ex))
            {
                Log.Debug("Download of {Filename} from user {Username} cancelled during shutdown: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
            catch (Exception ex) when (IsCancellationException(ex) || IsDownloadTimeout(ex))
            {
                Log.Information("Download of {Filename} from user {Username} timed out or was cancelled: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                // Record failed/timed out chunk completion for peer metrics (Phase 2C - T-409)
                if (PeerMetrics != null)
                {
                    var result = IsDownloadTimeout(ex) ? ChunkCompletionResult.TimedOut : ChunkCompletionResult.Failed;
                    _ = ObserveBackgroundTaskAsync(
                        PeerMetrics.RecordChunkCompletionAsync(
                            transfer.Username,
                            result,
                            cancellationToken: CancellationToken.None),
                        $"Failed to record {result} chunk completion for {transfer.Username}");
                }

                TryFail(transfer.Id, exception: ex);
                transfer = Find(t => t.Id == transfer.Id) ?? transfer;

                // todo: broadcast
                SynchronizedUpdate(transfer, semaphore: updateSyncRoot, cancellationToken: CancellationToken.None);

                throw;
            }
            catch (Exception ex) when (IsExpectedRemoteDownloadFailure(ex))
            {
                Log.Information("Download of {Filename} from user {Username} failed because {Reason}: {Diagnostic}",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                    LoggingSanitizer.SanitizeExternalIdentifier(DescribeExpectedRemoteDownloadFailureReason(ex)),
                    LoggingSanitizer.SanitizeExternalIdentifier(DescribeRemoteDownloadFailure(ex)));

                if (PeerMetrics != null)
                {
                    _ = ObserveBackgroundTaskAsync(
                        PeerMetrics.RecordChunkCompletionAsync(
                            transfer.Username,
                            ChunkCompletionResult.Failed,
                            cancellationToken: CancellationToken.None),
                        $"Failed to record failed chunk completion for {transfer.Username}");
                }

                TryFail(transfer.Id, exception: ex);
                transfer = Find(t => t.Id == transfer.Id) ?? transfer;

                // todo: broadcast
                SynchronizedUpdate(transfer, semaphore: updateSyncRoot, cancellationToken: CancellationToken.None);

                throw;
            }
            catch (Exception ex)
            {
                Log.Error("Download of {Filename} from user {Username} failed: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                // Record failed chunk completion for peer metrics (Phase 2C - T-409)
                if (PeerMetrics != null)
                {
                    _ = ObserveBackgroundTaskAsync(
                        PeerMetrics.RecordChunkCompletionAsync(
                            transfer.Username,
                            ChunkCompletionResult.Failed,
                            cancellationToken: CancellationToken.None),
                        $"Failed to record failed chunk completion for {transfer.Username}");
                }

                if (contentSafetyFailureMessage is not null && transfer.RequestId.HasValue)
                {
                    using var requestContext = ContextFactory.CreateDbContext();
                    requestContext.DownloadRequests
                        .Where(request => request.Id == transfer.RequestId.Value && request.State == DownloadRequestState.Active)
                        .ExecuteUpdate(setter => setter
                            .SetProperty(request => request.State, DownloadRequestState.Failed)
                            .SetProperty(request => request.CompletedAt, DateTime.UtcNow));
                }

                if (quarantinedFilename is not null)
                {
                    using var transferContext = ContextFactory.CreateDbContext();
                    transferContext.Transfers
                        .Where(record => record.Id == transfer.Id)
                        .ExecuteUpdate(setter => setter.SetProperty(record => record.LocalFilename, quarantinedFilename));
                }

                TryFail(transfer.Id, exception: ex);
                transfer = Find(t => t.Id == transfer.Id) ?? transfer;

                // todo: broadcast
                SynchronizedUpdate(transfer, semaphore: updateSyncRoot, cancellationToken: CancellationToken.None);
                stateChanged?.Invoke(transfer);

                throw;
            }
            finally
            {
                if (CancellationTokens.TryRemove(transfer.Id, out var storedCancellationTokenSource))
                {
                    storedCancellationTokenSource?.Dispose();
                }
            }
        }

        private void SynchronizedUpdate(Transfer transfer, object semaphore, CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            lock (semaphore)
            {
                Update(transfer);
            }
        }

        private async Task ObserveDownloadTaskAsync(Task downloadTask, Guid transferId, string filename, string username)
        {
            try
            {
                await downloadTask.ConfigureAwait(false);
                Log.Information("Task for download of {Filename} from {Username} completed successfully",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username));
            }
            catch (Exception ex) when (IsShutdownCancellation(ex))
            {
                Log.Debug("Task for download of {Filename} from {Username} cancelled during shutdown: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
            }
            catch (Exception ex) when (IsCancellationException(ex) || IsDownloadTimeout(ex))
            {
                Log.Debug("Task for download of {Filename} from {Username} ended with expected timeout or cancellation: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                if (!TryFail(transferId, exception: ex))
                {
                    Log.Debug("Transfer {Id} was already cleaned up after timed out or cancelled download", transferId);
                }
            }
            catch (Exception ex) when (IsExpectedRemoteDownloadFailure(ex))
            {
                Log.Debug("Task for download of {Filename} from {Username} ended with expected remote peer failure: {Diagnostic}",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(DescribeRemoteDownloadFailure(ex)));

                if (!TryFail(transferId, exception: ex))
                {
                    Log.Debug("Transfer {Id} was already cleaned up after expected remote download failure", transferId);
                }
            }
            catch (Exception ex) when (IsLocalFilesystemFailure(ex))
            {
                Log.Debug("Task for download of {Filename} from {Username} ended with observed local filesystem failure: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                if (!TryFail(transferId, exception: ex))
                {
                    Log.Debug("Transfer {Id} was already cleaned up after local filesystem download failure", transferId);
                }
            }
            catch (Exception ex)
            {
                Log.Error("Task for download of {Filename} from {Username} did not complete successfully: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                if (!TryFail(transferId, exception: ex))
                {
                    Log.Error("Failed to clean up transfer {Id} after failed download: {Exception}",
                        transferId, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                }
            }
        }

        private async Task ObserveDownloadEnqueueTaskAsync(Task enqueueTask, Guid transferId, string filename, string username)
        {
            try
            {
                await enqueueTask.ConfigureAwait(false);
                Log.Information("Task for enqueue of {Filename} from {Username} completed successfully",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username));
            }
            catch (Exception ex) when (IsShutdownCancellation(ex))
            {
                Log.Debug("Task for enqueue of {Filename} from {Username} cancelled during shutdown: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
            }
            catch (OperationCanceledException ex)
            {
                Log.Error("Task for enqueue of {Filename} from {Username} did not complete successfully: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                if (!TryFail(transferId, exception: ex))
                {
                    Log.Error("Failed to clean up transfer {Id} after failed enqueue: {Exception}",
                        transferId, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                }
            }
            catch (Exception ex) when (IsExpectedRemoteDownloadFailure(ex))
            {
                Log.Debug("Task for enqueue of {Filename} from {Username} ended with expected remote peer failure: {Diagnostic}",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(DescribeRemoteDownloadFailure(ex)));

                if (!TryFail(transferId, exception: ex))
                {
                    Log.Debug("Transfer {Id} was already cleaned up after expected remote enqueue failure", transferId);
                }
            }
            catch (Exception ex)
            {
                Log.Error("Task for enqueue of {Filename} from {Username} did not complete successfully: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                if (!TryFail(transferId, exception: ex))
                {
                    Log.Error("Failed to clean up transfer {Id} after failed enqueue: {Exception}",
                        transferId, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                }
            }
        }

        private void ReleaseSemaphore(SemaphoreSlim semaphore, string operation, string? filename, string username)
        {
            try
            {
                semaphore.Release();
            }
            catch (ObjectDisposedException ex) when (Application.IsShuttingDown || _disposed)
            {
                Log.Debug("Skipped releasing disposed semaphore for {Operation} of {Filename} from {Username} during shutdown: {Exception}",
                    operation, LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
            }
        }

        private void CancelActiveTransfers()
        {
            foreach (var (transferId, _) in CancellationTokens)
            {
                if (!CancellationTokens.TryRemove(transferId, out var cancellationTokenSource))
                {
                    continue;
                }

                using (cancellationTokenSource)
                {
                    cancellationTokenSource.Cancel();
                }
            }
        }

        private Task TrackTransferTask(ConcurrentDictionary<Guid, Task> taskMap, Guid transferId, Task task)
        {
            taskMap[transferId] = task;
            _ = task.ContinueWith(
                _ =>
                {
                    if (taskMap.TryRemove(transferId, out var removedTask))
                    {
                        _ = removedTask;
                    }
                },
                CancellationToken.None,
                TaskContinuationOptions.ExecuteSynchronously,
                TaskScheduler.Default);
            return task;
        }

        private async Task CleanupEnqueueSemaphoresAsync()
        {
            if (await EnqueueSemaphoreSyncRoot.WaitAsync(0).ConfigureAwait(false))
            {
                try
                {
                    foreach (var kvp in EnqueueSemaphores)
                    {
                        if (await kvp.Value.WaitAsync(0).ConfigureAwait(false))
                        {
                            EnqueueSemaphores.TryRemove(kvp.Key, out var removed);
                            removed?.Dispose();
                            Log.Debug("Cleaned up enqueue semaphore for {Key}", LoggingSanitizer.SanitizeExternalIdentifier(kvp.Key));
                        }
                    }
                }
                finally
                {
                    EnqueueSemaphoreSyncRoot.Release();
                }
            }
        }

        private static void ObserveEnqueueTasksWhenIdle(IReadOnlyCollection<Task> runningTasks)
        {
            if (runningTasks.Count == 0)
            {
                return;
            }

            _ = Task.WhenAll(runningTasks).ContinueWith(
                completedTasks =>
                {
                    if (completedTasks.IsFaulted)
                    {
                        _ = completedTasks.Exception;
                    }
                },
                CancellationToken.None,
                TaskContinuationOptions.ExecuteSynchronously,
                TaskScheduler.Default);
        }

        private static string DescribeRemoteDownloadFailure(Exception exception)
        {
            static IEnumerable<Exception> Walk(Exception current)
            {
                if (current is AggregateException aggregateException)
                {
                    foreach (var inner in aggregateException.Flatten().InnerExceptions.SelectMany(Walk))
                    {
                        yield return inner;
                    }

                    yield break;
                }

                for (var next = current; next is not null; next = next.InnerException)
                {
                    yield return next;
                }
            }

            var chain = string.Join(" -> ", Walk(exception).Select(ex => $"{ex.GetType().Name}: {ex.Message}"));
            var rejection = Walk(exception)
                .Select(ex => ex.Message)
                .FirstOrDefault(message => message.Contains("Transfer rejected:", StringComparison.OrdinalIgnoreCase) ||
                    message.Contains("Download reported as failed by remote client", StringComparison.OrdinalIgnoreCase));

            return rejection is null
                ? chain
                : $"{chain}; remoteReason={rejection}";
        }

        private static string DescribeExpectedRemoteDownloadFailureReason(Exception exception)
        {
            if (ContainsException<UserOfflineException>(exception) ||
                exception.Message.Contains("appears to be offline", StringComparison.OrdinalIgnoreCase))
            {
                return "the remote peer is unavailable";
            }

            if (ContainsException<TransferRejectedException>(exception) ||
                exception.Message.Contains("Transfer rejected:", StringComparison.OrdinalIgnoreCase))
            {
                return "the remote peer rejected the transfer";
            }

            if (ContainsException<TransferReportedFailedException>(exception) ||
                exception.Message.Contains("Download reported as failed by remote client", StringComparison.OrdinalIgnoreCase))
            {
                return "the remote peer reported the transfer as failed";
            }

            if (ContainsException<TransferSizeMismatchException>(exception) ||
                exception.Message.Contains("Transfer aborted: the remote size", StringComparison.OrdinalIgnoreCase))
            {
                return "the remote peer reported a different file size";
            }

            return "the remote peer is unavailable";
        }

        private static bool IsExpectedRemoteDownloadFailure(Exception exception)
        {
            if (exception is AggregateException aggregateException)
            {
                return aggregateException.Flatten().InnerExceptions.Any(IsExpectedRemoteDownloadFailure);
            }

            return exception is UserOfflineException ||
                exception is TransferRejectedException ||
                exception is TransferReportedFailedException ||
                exception is TransferSizeMismatchException ||
                exception.InnerException is UserOfflineException ||
                exception.InnerException is TransferRejectedException ||
                exception.InnerException is TransferReportedFailedException ||
                exception.InnerException is TransferSizeMismatchException ||
                exception is Soulseek.TransferException { InnerException: UserOfflineException } ||
                exception is Soulseek.TransferException { InnerException: TransferRejectedException } ||
                exception is Soulseek.TransferException { InnerException: TransferReportedFailedException } ||
                exception is Soulseek.TransferException { InnerException: TransferSizeMismatchException } ||
                exception.Message.Contains("Download reported as failed by remote client", StringComparison.OrdinalIgnoreCase) ||
                exception.Message.Contains("Transfer rejected:", StringComparison.OrdinalIgnoreCase) ||
                exception.Message.Contains("Transfer aborted: the remote size", StringComparison.OrdinalIgnoreCase) ||
                exception.Message.Contains("appears to be offline", StringComparison.OrdinalIgnoreCase) ||
                exception.Message.Contains("Failed to establish a direct or indirect message connection", StringComparison.OrdinalIgnoreCase) ||
                exception.Message.Contains("Failed to establish a direct or indirect transfer connection", StringComparison.OrdinalIgnoreCase) ||
                exception.Message.Contains("Connection reset by peer", StringComparison.OrdinalIgnoreCase) ||
                exception.Message.Contains("Remote connection closed", StringComparison.OrdinalIgnoreCase) ||
                exception.Message.Contains("Unable to read data from the transport connection", StringComparison.OrdinalIgnoreCase) ||
                SoulseekNetworkExceptionClassifier.IsExpected(exception);
        }

        private static bool IsDownloadTimeout(Exception exception)
        {
            if (exception is AggregateException aggregateException)
            {
                return aggregateException.Flatten().InnerExceptions.Any(IsDownloadTimeout);
            }

            return exception is TimeoutException ||
                (exception is TransferException { Message: var message } && IsTimeoutMessage(message)) ||
                exception.InnerException is TimeoutException;
        }

        private static bool IsTimeoutMessage(string message)
            => message.Contains("timed out", StringComparison.OrdinalIgnoreCase) ||
                message.Contains("timeout", StringComparison.OrdinalIgnoreCase);

        private static bool IsDirectDownloadRetryable(Exception exception)
            => exception is not OperationCanceledException
                && !IsLocalFilesystemFailure(exception)
                && exception is not DownloadBlockedByPolicyException
                && exception is not TransferRejectedException
                && exception is not DuplicateTransferException
                && exception is not TransferSizeMismatchException;

        private static bool IsLocalFilesystemFailure(Exception exception)
            => ContainsException<UnauthorizedAccessException>(exception);

        private static bool ContainsException<TException>(Exception exception)
            where TException : Exception
        {
            if (exception is TException)
            {
                return true;
            }

            if (exception is AggregateException aggregateException)
            {
                return aggregateException.Flatten().InnerExceptions.Any(ContainsException<TException>);
            }

            return exception.InnerException is not null && ContainsException<TException>(exception.InnerException);
        }

        private static bool IsShutdownCancellation(Exception exception)
        {
            if (!Application.IsShuttingDown)
            {
                return false;
            }

            return IsCancellationException(exception);
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

        private void EnrichTransferMetadata(Transfer transfer, string localFilename)
        {
            if (string.IsNullOrWhiteSpace(localFilename) || !System.IO.File.Exists(localFilename))
            {
                return;
            }

            try
            {
                using var tagFile = TagLib.File.Create(localFilename);
                var props = tagFile.Properties;
                if (props != null)
                {
                    if (props.AudioBitrate > 0)
                        transfer.BitRate = props.AudioBitrate;
                    if (props.AudioSampleRate > 0)
                        transfer.SampleRate = props.AudioSampleRate;
                    if (props.BitsPerSample > 0)
                        transfer.BitDepth = props.BitsPerSample;
                    if (props.Duration.TotalSeconds > 0)
                        transfer.Length = (int)Math.Round(props.Duration.TotalSeconds);
                }

                var tag = tagFile.Tag;
                if (tag != null)
                {
                    transfer.Artist = FirstNonEmpty(tag.FirstPerformer, tag.FirstAlbumArtist);
                    transfer.Album = EmptyToNull(tag.Album);
                    transfer.Title = EmptyToNull(tag.Title);
                    transfer.TrackNumber = tag.Track > 0 ? (int)tag.Track : null;
                    transfer.Year = tag.Year > 0 ? (int)tag.Year : null;
                }
            }
            catch (Exception ex)
            {
                Log.Debug("Failed to read audio metadata from {LocalFilename} for transfer enrichment: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(localFilename), LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
            }
        }

        private static string ResolveQuarantineDirectory(Options options)
        {
            var configuredDirectory = options.Security.ContentSafety.QuarantineDirectory;
            var quarantineDirectory = string.IsNullOrWhiteSpace(configuredDirectory)
                ? System.IO.Path.Combine(options.Directories.Downloads, ".quarantine")
                : System.IO.Path.IsPathRooted(configuredDirectory)
                    ? configuredDirectory
                    : System.IO.Path.Combine(options.Directories.Downloads, configuredDirectory);

            return System.IO.Path.GetFullPath(quarantineDirectory);
        }

        private string ResolveCompletedDestinationDirectory(Transfer transfer, DownloadRequest? request = null)
        {
            var options = OptionsMonitor.CurrentValue;
            var completedRoot = !string.IsNullOrWhiteSpace(transfer.DestinationDirectory)
                ? transfer.DestinationDirectory
                : Destinations.DownloadDestinationResolver.GetDefaultPath(options);

            // An explicit destination directory always wins.
            if (!string.IsNullOrWhiteSpace(transfer.DestinationDirectory))
            {
                var explicitDestination = System.IO.Path.GetDirectoryName(transfer.Filename.ToLocalFilename(baseDirectory: completedRoot)) ?? completedRoot;
                return NormalizeCompletedDestination(explicitDestination, options);
            }

            var destinationOptions = options.Global.Download.Destination;
            if (destinationOptions.Subdirectory is not null)
            {
                var subdirectory = DownloadDestinationTemplate.Render(destinationOptions.Subdirectory, transfer, request);
                var configuredDestination = string.IsNullOrEmpty(subdirectory)
                    ? completedRoot
                    : System.IO.Path.Combine(completedRoot, subdirectory);
                return NormalizeCompletedDestination(configuredDestination, options);
            }

            var template = options.Global.Download.CompletedPathTemplate;
            if (!string.IsNullOrWhiteSpace(template))
            {
                return NormalizeCompletedDestination(RenderCompletedPathTemplate(transfer, completedRoot, template, request), options);
            }

            if (string.IsNullOrWhiteSpace(options.Global.Download.CompletedLayout))
            {
                var defaultSubdirectory = DownloadDestinationTemplate.Render("${SOURCE_DIRECTORY}", transfer, request);
                var defaultDestination = string.IsNullOrEmpty(defaultSubdirectory)
                    ? completedRoot
                    : System.IO.Path.Combine(completedRoot, defaultSubdirectory);
                return NormalizeCompletedDestination(defaultDestination, options);
            }

            var layout = ParseCompletedDownloadLayout(options.Global.Download.CompletedLayout);

            var destination = layout switch
            {
                CompletedDownloadLayout.Flat => completedRoot,
                CompletedDownloadLayout.UploaderFolder => System.IO.Path.Combine(
                    completedRoot,
                    transfer.Username.ReplaceInvalidFileNameCharacters(),
                    GetRemoteParentFolderName(transfer.Filename)),
                CompletedDownloadLayout.RemoteFolder => System.IO.Path.GetDirectoryName(transfer.Filename.ToLocalFilename(baseDirectory: completedRoot)) ?? completedRoot,
                _ => transfer.BatchId.HasValue
                    ? System.IO.Path.Combine(completedRoot, transfer.BatchId.Value.ToString())
                    : System.IO.Path.GetDirectoryName(transfer.Filename.ToLocalFilename(baseDirectory: completedRoot)) ?? completedRoot,
            };

            return NormalizeCompletedDestination(destination, options);
        }

        private static string NormalizeCompletedDestination(string destination, Options options)
        {
            return PathGuard.NormalizeAbsolutePathWithinRoots(
                destination,
                Destinations.DownloadDestinationResolver.GetAllowedRoots(options))
                ?? throw new System.IO.IOException("Completed download path resolves outside configured download directories");
        }

        private static string RenderCompletedPathTemplate(Transfer transfer, string completedRoot, string template, DownloadRequest? request = null)
        {
            var rendered = System.Text.RegularExpressions.Regex.Replace(
                template,
                @"\{(?<name>[a-zA-Z_]+)(?::(?<format>[^{}]+))?\}",
                match =>
                {
                    var name = match.Groups["name"].Value.ToLowerInvariant();
                    var format = match.Groups["format"].Success ? match.Groups["format"].Value : null;
                    return RenderTemplateToken(transfer, name, format, request);
                });

            // Split on / and \ so users can write either; sanitize each segment.
            var segments = rendered
                .Split(new[] { '/', '\\' }, StringSplitOptions.None)
                .Select(s => s.Trim())
                .Where(s => !string.IsNullOrEmpty(s) && s != "." && s != "..")
                .Select(s => s.ReplaceInvalidFileNameCharacters())
                .ToArray();

            return segments.Length == 0
                ? completedRoot
                : System.IO.Path.Combine(new[] { completedRoot }.Concat(segments).ToArray());
        }

        private static string RenderTemplateToken(Transfer transfer, string name, string? format, DownloadRequest? request = null)
        {
            return name switch
            {
                "uploader" => Safe(transfer.Username),
                "remote_folder" => Safe(GetRemoteParentFolderName(transfer.Filename), fallback: "_singles"),
                "remote_parent" => Safe(System.IO.Path.GetFileName(GetRemoteParentFolderName(transfer.Filename).TrimEnd('/', '\\')), fallback: "_singles"),
                "remote_filename" => Safe(System.IO.Path.GetFileNameWithoutExtension(transfer.Filename.ToLocalRelativeFilename())),
                "batch_id" => transfer.BatchId?.ToString() ?? "_no-batch",
                "request_name" => Safe(request?.Name ?? string.Empty),
                "search_text" => string.Empty, // reserved
                "date" => transfer.RequestedAt.ToString(string.IsNullOrEmpty(format) ? "yyyy-MM-dd" : format, System.Globalization.CultureInfo.InvariantCulture),
                _ => string.Empty,
            };

            static string Safe(string value, string fallback = "_")
                => string.IsNullOrWhiteSpace(value) ? fallback : value;
        }

        private static string GetRemoteParentFolderName(string remoteFilename)
        {
            var local = remoteFilename.ToLocalRelativeFilename();
            var directory = System.IO.Path.GetDirectoryName(local);
            return string.IsNullOrWhiteSpace(directory) ? "_" : directory;
        }

        private static string? FirstNonEmpty(params string?[] values)
            => values.FirstOrDefault(value => !string.IsNullOrWhiteSpace(value))?.Trim();

        private static string? EmptyToNull(string? value)
            => string.IsNullOrWhiteSpace(value) ? null : value.Trim();

        private static CompletedDownloadLayout ParseCompletedDownloadLayout(string? value)
        {
            var normalized = (value ?? string.Empty).Trim().Replace("-", "_", StringComparison.Ordinal).ToLowerInvariant();
            return normalized switch
            {
                "remote_folder" or "remotefolder" => CompletedDownloadLayout.RemoteFolder,
                "uploader_folder" or "uploaderfolder" => CompletedDownloadLayout.UploaderFolder,
                "batch_id" or "batchid" => CompletedDownloadLayout.BatchId,
                "flat" => CompletedDownloadLayout.Flat,
                _ => CompletedDownloadLayout.RemoteFolder,
            };
        }
    }
}
