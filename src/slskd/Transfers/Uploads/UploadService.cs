// <copyright file="UploadService.cs" company="slskd Team">
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

// <copyright file="UploadService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;
using slskd.Common.Security;
using slskd.Files;
using Soulseek;

namespace slskd.Transfers.Uploads
{
    using System;
    using System.Collections.Concurrent;
    using System.Collections.Generic;
    using System.Diagnostics.CodeAnalysis;
    using System.IO;
    using System.Linq;
    using System.Linq.Expressions;
    using System.Threading;
    using System.Threading.Tasks;
    using Microsoft.EntityFrameworkCore;
    using Serilog;
    using slskd.Events;
    using slskd.Relay;
    using slskd.Shares;
    using slskd.SoulseekExceptions;
    using slskd.Transfers.MultiSource.Metrics;
    using slskd.Users;

    /// <summary>
    ///     Manages uploads.
    /// </summary>
    public interface IUploadService : IDisposable
    {
        /// <summary>
        ///     Gets the upload governor.
        /// </summary>
        IUploadGovernor Governor { get; }

        /// <summary>
        ///     Gets the upload queue.
        /// </summary>
        IUploadQueue Queue { get; }

        /// <summary>
        ///     Adds the specified <paramref name="transfer"/>. Supersedes any existing record for the same file and username.
        /// </summary>
        /// <remarks>This should generally not be called; use <see cref="EnqueueAsync(string, string)"/> instead.</remarks>
        /// <param name="transfer"></param>
        void AddOrSupersede(Transfer transfer);

        /// <summary>
        ///     Enqueues the requested file.
        /// </summary>
        /// <param name="username">The username of the requesting user.</param>
        /// <param name="filename">The local filename of the requested file.</param>
        /// <returns>The operation context.</returns>
        Task<Transfer?> EnqueueAsync(string username, string filename);

        /// <summary>
        ///     Uploads the specified enqueued <paramref name="transfer"/> to the requesting user.
        /// </summary>
        /// <param name="transfer">The Transfer to upload.</param>
        /// <returns>The operation context.</returns>
        /// <exception cref="ArgumentNullException">Thrown if the specified Transfer is null.</exception>
        /// <exception cref="TransferNotFoundException">Thrown if the specified Transfer ID can't be found in the database.</exception>
        /// <exception cref="InvalidOperationException">Thrown if the specified Transfer is not in the Queued | Locally state.</exception>
        /// <exception cref="DuplicateTransferException">Thrown if an upload matching the username and filename is already tracked by Soulseek.NET.</exception>
        /// <exception cref="NotFoundException">Thrown if the specified file can't be found on disk.</exception>
        Task<Transfer?> UploadAsync(Transfer transfer);

        /// <summary>
        ///     Finds a single upload matching the specified <paramref name="expression"/>.
        /// </summary>
        /// <param name="expression">The expression to use to match uploads.</param>
        /// <returns>The found transfer, or default if not found.</returns>
        Transfer? Find(Expression<Func<Transfer, bool>> expression);

        /// <summary>
        ///     Returns a summary of the uploads matching the specified <paramref name="expression"/>. This can be expensive;
        ///     consider caching.
        /// </summary>
        /// <param name="expression">The expression used to select uploads for summarization.</param>
        /// <returns>
        ///     The generated summary, including the number of files and total size in bytes.
        /// </returns>
        (int Files, long Bytes) Summarize(Expression<Func<Transfer, bool>> expression);

        /// <summary>
        ///     Returns a list of all uploads matching the optional <paramref name="expression"/>.
        /// </summary>
        /// <param name="expression">An optional expression used to match uploads.</param>
        /// <param name="includeRemoved">A value indicating whether to include uploads that have been removed previously.</param>
        /// <returns>The list of uploads matching the specified expression, or all uploads if no expression is specified.</returns>
        List<Transfer> List(Expression<Func<Transfer, bool>> expression, bool includeRemoved);

        /// <summary>
        ///     Returns a stable page of uploads ordered by request time, newest first.
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
        ///     Counts uploads, optionally including soft-removed records.
        /// </summary>
        /// <param name="includeRemoved">Whether soft-removed records should be counted.</param>
        /// <returns>The upload count.</returns>
        int Count(bool includeRemoved = false);

        /// <summary>
        ///     Returns a stable page of successful uploads completed no later than <paramref name="asOf"/>.
        /// </summary>
        /// <remarks>Soft-removed records remain in the page sequence so offsets stay stable while history is cleared.</remarks>
        /// <param name="asOf">The inclusive completion-time watermark.</param>
        /// <param name="offset">The number of history records to skip.</param>
        /// <param name="limit">The maximum number of records to return.</param>
        /// <returns>The requested successful-upload history page.</returns>
        List<Transfer> ListCompleted(DateTime asOf, int offset, int limit);

        /// <summary>
        ///     Removes <see cref="TransferStates.Completed"/> uploads older than the specified <paramref name="age"/>.
        /// </summary>
        /// <param name="age">The age after which uploads are eligible for pruning, in minutes.</param>
        /// <param name="stateHasFlag">An optional, additional state by which uploads are filtered for pruning.</param>
        /// <returns>The number of pruned uploads.</returns>
        int Prune(int age, TransferStates stateHasFlag = TransferStates.Completed);

        /// <summary>
        ///     Permanently deletes soft-removed, completed uploads older than the specified <paramref name="age"/>.
        /// </summary>
        /// <param name="age">The time since the last transfer update, in minutes.</param>
        /// <returns>The number of deleted uploads.</returns>
        int PruneRemoved(int age);

        /// <summary>
        ///     Removes the upload matching the specified <paramref name="id"/>.
        /// </summary>
        /// <remarks>This is a soft delete; the record is retained for historical retrieval.</remarks>
        /// <param name="id">The unique identifier of the upload.</param>
        void Remove(Guid id);

        /// <summary>
        ///     Cancels the upload matching the specified <paramref name="id"/>, if it is in progress.
        /// </summary>
        /// <param name="id">The unique identifier for the upload.</param>
        /// <returns>A value indicating whether the upload was successfully cancelled.</returns>
        bool TryCancel(Guid id);

        /// <summary>
        ///     Fails the upload matching the specified <paramref name="id"/> with the specified <paramref name="exception"/>,
        ///     and sets the final state accordingly.
        /// </summary>
        /// <remarks>
        ///     This method is designed to be idempotent, meaning subsequent calls for a given transfer shouldn't change
        ///     the EndedAt or Exception properties if they have already been set. If the transfer State already includes
        ///     the terminal Completed flag, it is unchanged.
        /// </remarks>
        /// <param name="id">The unique identifier for the upload.</param>
        /// <param name="exception">The exception that caused the failure.</param>
        /// <returns>A value indicating whether the upload was successfully failed.</returns>
        bool TryFail(Guid id, Exception exception);

        /// <summary>
        ///     Synchronously updates the specified <paramref name="transfer"/>.
        /// </summary>
        /// <param name="transfer">The transfer to update.</param>
        void Update(Transfer transfer);
    }

    /// <summary>
    ///     Manages uploads.
    /// </summary>
    public class UploadService : IUploadService, IDisposable
    {
        private static readonly TimeSpan FailedPeerCooldown = TimeSpan.FromSeconds(30);

        public UploadService(
            FileService fileService,
            IUserService userService,
            ISoulseekClient soulseekClient,
            IOptionsMonitor<Options> optionsMonitor,
            IShareService shareService,
            IRelayService relayService,
            IDbContextFactory<TransfersDbContext> contextFactory,
            EventBus eventBus,
            ITrafficAccountingService trafficAccountingService,
            IScheduledRateLimitService? scheduledRateLimitService = null)
        {
            var log = Serilog.Log.ForContext<UploadService>();
            log.Debug("[UploadService] Constructor called");
            Files = fileService;
            Users = userService;
            Client = soulseekClient;
            Shares = shareService;
            Relay = relayService;
            ContextFactory = contextFactory;
            OptionsMonitor = optionsMonitor;
            EventBus = eventBus;
            _trafficAccountingService = trafficAccountingService;

            log.Debug("[UploadService] Creating UploadGovernor");
            Governor = new UploadGovernor(userService, optionsMonitor, scheduledRateLimitService);
            log.Debug("[UploadService] Creating UploadQueue");
            Queue = new UploadQueue(userService, optionsMonitor);
            FailedPeerCooldownCleanupTimer = new Timer(
                static state => ((UploadService)state!).RemoveExpiredFailedPeerCooldowns(DateTime.UtcNow),
                this,
                FailedPeerCooldown,
                FailedPeerCooldown);
            log.Debug("[UploadService] Constructor completed");
        }

        /// <summary>
        ///     Gets the upload governor.
        /// </summary>
        public IUploadGovernor Governor { get; init; }

        /// <summary>
        ///     Gets the upload queue.
        /// </summary>
        public IUploadQueue Queue { get; init; }

        private FileService Files { get; }
        private ConcurrentDictionary<Guid, CancellationTokenSource> CancellationTokens { get; } = new ConcurrentDictionary<Guid, CancellationTokenSource>();
        private ISoulseekClient Client { get; set; }
        private IDbContextFactory<TransfersDbContext> ContextFactory { get; }
        private ILogger Log { get; } = Serilog.Log.ForContext<UploadService>();
        private IOptionsMonitor<Options> OptionsMonitor { get; }
        private IRelayService Relay { get; }
        private IShareService Shares { get; set; }
        private IUserService Users { get; set; }
        private EventBus EventBus { get; }
        private readonly ITrafficAccountingService _trafficAccountingService;
        private Timer FailedPeerCooldownCleanupTimer { get; }
        private ConcurrentDictionary<string, DateTime> FailedPeerCooldowns { get; } = new(StringComparer.OrdinalIgnoreCase);
        private ConcurrentDictionary<string, bool> Locks { get; } = new();
        private bool Disposed { get; set; }

        /// <summary>
        ///     Disposes this instance.
        /// </summary>
        public void Dispose()
        {
            Dispose(disposing: true);
            GC.SuppressFinalize(this);
        }

        /// <summary>
        ///     Adds the specified <paramref name="transfer"/>. Supersedes any existing record for the same file and username.
        /// </summary>
        /// <remarks>This should generally not be called; use <see cref="EnqueueAsync(string, string)"/> instead.</remarks>
        /// <param name="transfer"></param>
        public void AddOrSupersede(Transfer transfer)
        {
            using var context = ContextFactory.CreateDbContext();

            var existing = context.Transfers
                .Where(t => t.Direction == TransferDirection.Upload)
                .Where(t => t.Username == transfer.Username)
                .Where(t => t.Filename == transfer.Filename)
                .Where(t => !t.Removed)
                .FirstOrDefault();

            if (existing != default)
            {
                Log.Debug("Superseding transfer record for {Filename} from {Username}",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username));
                existing.Removed = true;
            }

            context.Add(transfer);
            context.SaveChanges();
        }

        /// <summary>
        ///     Uploads the specified enqueued <paramref name="transfer"/> to the requesting user.
        /// </summary>
        /// <param name="transfer">The Transfer to upload.</param>
        /// <returns>The operation context.</returns>
        /// <exception cref="ArgumentNullException">Thrown if the specified Transfer is null.</exception>
        /// <exception cref="TransferNotFoundException">Thrown if the specified Transfer ID can't be found in the database.</exception>
        /// <exception cref="InvalidOperationException">Thrown if the specified Transfer is not in the Queued | Locally state.</exception>
        /// <exception cref="DuplicateTransferException">Thrown if an upload matching the username and filename is already tracked by Soulseek.NET.</exception>
        /// <exception cref="NotFoundException">Thrown if the specified file can't be found on disk.</exception>
        [SuppressMessage("Reliability", "CA2000:Dispose objects before losing scope", Justification = "The upload sync semaphore is disposed in the method-level finally block after all callbacks and transfer cleanup complete.")]
        public async Task<Transfer?> UploadAsync(Transfer transfer)
        {
            string? host = null;
            string localFilename = string.Empty;
            long localFileLength = default;
            long soulseekUploadBytesSent = 0;

            var lockName = $"{nameof(UploadAsync)}:{transfer.Username}:{transfer.Filename}";

            if (!Locks.TryAdd(lockName, true))
            {
                Log.Debug("Ignoring concurrent invocation; lock {LockName} already held", LoggingSanitizer.SanitizeExternalIdentifier(lockName));
                return default;
            }

            CancellationTokenSource? cts = null;
            var syncRoot = new object();

            /*
                from this point forward, any exit from this method MUST result in an update to the Transfer record
                in the database that sets EndedAt and ensures that the State property includes the Completed flag

                failure to do so means records will get "stuck" in the database/on the UI

                additionally, any acquired locks/semaphores must be released, including (and most importantly) the queue slot
            */
            try
            {
                cts = new CancellationTokenSource();
                Log.Debug("Acquired lock {LockName}", LoggingSanitizer.SanitizeExternalIdentifier(lockName));

                /*
                    fetch an updated copy of the transfer record from the database; now that we are locked, we *should*
                    have exclusive access to this record

                    we're not using DbContext and tracked changes here because we don't want to hold a connection
                    open for the duration of the upload
                */
                transfer = Find(t => t.Id == transfer.Id)
                    ?? throw new TransferNotFoundException($"Transfer with ID {transfer.Id} not found");

                if (transfer.State != (TransferStates.Queued | TransferStates.Locally))
                {
                    throw new InvalidOperationException($"Invalid starting state for upload; expected {TransferStates.Queued | TransferStates.Locally}, encountered {transfer.State}");
                }

                /*
                    Soulseek.NET keeps an internal dictionary of all transfers for the duration of the transfer logic;
                    check that list to see if there's already an instance of this upload in it, just in case we've gotten
                    out of sync somehow
                */
                if (Client.Uploads.Any(u => u.Username == transfer.Username && u.Filename == transfer.Filename))
                {
                    throw new DuplicateTransferException("A duplicate upload of the same file to the same user is already registered");
                }

                // users with uploads must be watched so that we can keep informed of their online status, privileges, and
                // statistics. this is so that we can accurately determine their effective group.
                try
                {
                    if (!Users.IsWatched(transfer.Username))
                    {
                        await Users.WatchAsync(transfer.Username);
                    }
                }
                catch (Exception ex)
                {
                    Log.Warning("Failed to watch user {Username}: {Exception}",
                        LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username), LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                }

                Log.Information("Initializing upload of {Filename} to {Username}",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username));

                // locate the file on disk. we checked this once already when enqueueing, but it may have moved since
                // can throw NotFoundException
                (host, localFilename, localFileLength) = await ResolveFileInfoAsync(remoteFilename: transfer.Filename);

                using var rateLimiter = new RateLimiter(250, concurrencyLimit: 1, flushOnDispose: true);

                var topts = new TransferOptions(
                    progressUpdateInterval: 250,
                    progressUpdateMinimumBytes: 1024 * 1024,
                    stateChanged: (args) =>
                    {
                        Log.Debug("Upload of {Filename} to user {Username} changed state from {Previous} to {New}",
                            LoggingSanitizer.SanitizeFilePath(localFilename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username), args.PreviousState, args.Transfer.State);

                        // prevent Exceptions thrown during shutdown from updating the transfer record with related Exceptions;
                        // instead, allow these to be left "hanging" so that they are properly cleaned up at the next startup
                        if (Application.IsShuttingDown)
                        {
                            Log.Debug("Upload update of {Filename} to {Username} not persisted; app is shutting down",
                                LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username));
                            return;
                        }

                        transfer = transfer.WithSoulseekTransfer(args.Transfer);

                        // todo: broadcast
                        SynchronizedUpdate(transfer, semaphore: syncRoot, cancellationToken: cts.Token);
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
                            if (!cts.IsCancellationRequested && Monitor.TryEnter(syncRoot))
                            {
                                try
                                {
                                    // update only the properties that we expect to change between progress updates
                                    // this helps prevent this update from 'stepping' on other updates
                                    transfer.BytesTransferred = args.Transfer.BytesTransferred;
                                    transfer.AverageSpeed = args.Transfer.AverageSpeed;

                                    using var context = ContextFactory.CreateDbContext();

                                    context.Transfers.Where(t => t.Id == transfer.Id).ExecuteUpdate(setter => setter
                                        .SetProperty(t => t.BytesTransferred, transfer.BytesTransferred)
                                        .SetProperty(t => t.AverageSpeed, transfer.AverageSpeed));
                                }
                                finally
                                {
                                    Monitor.Exit(syncRoot);
                                }
                            }
                            else
                            {
                                Log.Debug("Skipped progress update of {Filename} to {Username} {BytesTransferred}/{TotalBytes}; previous update still pending",
                                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username), args.Transfer.BytesTransferred, args.Transfer.Size);
                            }
                        }
                    }),
                    seekInputStreamAutomatically: false,
                    disposeInputStreamOnCompletion: true, // note: don't set this to false!
                    governor: (tx, req, ct) => Governor.GetBytesAsync(tx.Username, req, ct),
                    reporter: (tx, att, grant, act) =>
                    {
                        if (act > 0)
                        {
                            Interlocked.Add(ref soulseekUploadBytesSent, act);
                            _trafficAccountingService.RecordSoulseekUploadProgress(act);
                        }

                        Governor.ReturnBytes(tx.Username, att, grant, act);
                    },
                    slotAwaiter: (tx, ct) => Queue.AwaitStartAsync(transfer.Id, ct),
                    slotReleased: (_) => Queue.Complete(transfer.Id));

                // register the cancellation token
                CancellationTokens.TryAdd(transfer.Id, cts);

                // add the transfer to the UploadQueue so that it can become eligible for selection
                Queue.Enqueue(transfer.Id, transfer.Username, transfer.Filename);
                transfer.EnqueuedAt = DateTime.UtcNow;
                SynchronizedUpdate(transfer, semaphore: syncRoot, cancellationToken: cts.Token);

                Soulseek.Transfer completedTransfer;

                if (host == Program.LocalHostName)
                {
                    completedTransfer = await Client.UploadAsync(
                        username: transfer.Username,
                        remoteFilename: transfer.Filename,
                        size: localFileLength,
                        inputStreamFactory: (startOffset) =>
                        {
#pragma warning disable S2930 // "IDisposables" should be disposed
                            // disposeInputStreamOnCompletion takes care of this
                            var stream = new FileStream(localFilename, FileMode.Open, FileAccess.Read);
#pragma warning restore S2930 // "IDisposables" should be disposed

                            stream.Seek(startOffset, SeekOrigin.Begin);
                            return Task.FromResult((Stream)stream);
                        },
                        options: topts,
                        cancellationToken: cts.Token);
                }
                else
                {
                    completedTransfer = await Client.UploadAsync(
                        username: transfer.Username,
                        remoteFilename: transfer.Filename,
                        size: localFileLength,
                        inputStreamFactory: (startOffset) => Relay.GetFileStreamAsync(agentName: host, filename: transfer.Filename, startOffset, id: transfer.Id),
                        options: topts,
                        cancellationToken: cts.Token);

                    Relay.TryCloseFileStream(host, id: transfer.Id);
                }

                // explicitly dispose the rate limiter to prevent updates from it beyond this point, and in doing so we
                // flushe any pending update, _probably_ pushing the state of the transfer back to InProgress
                rateLimiter.Dispose();

                // copy the completed transfer that was returned from Soulseek.NET in a terminal, fully updated state
                // over the top of the transfer record, then persist it
                transfer = transfer.WithSoulseekTransfer(completedTransfer);

                // todo: broadcast
                SynchronizedUpdate(transfer, semaphore: syncRoot, cancellationToken: CancellationToken.None);

                EventBus.Raise(new UploadFileCompleteEvent
                {
                    Timestamp = transfer.EndedAt ?? DateTime.UtcNow,
                    LocalFilename = localFilename,
                    RemoteFilename = transfer.Filename,
                    Transfer = transfer,
                });

                return transfer;
            }
            catch (NotFoundException ex)
            {
                Log.Error("Upload of {Filename} to user {Username} failed: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                TryFail(transfer.Id, "File could not be found", TransferStates.Completed | TransferStates.Aborted);

                throw;
            }
            catch (OperationCanceledException ex)
            {
                Log.Information("Upload of {Filename} to user {Username} was canceled: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                TryFail(transfer.Id, exception: ex);

                throw;
            }
            catch (Exception ex) when (IsExpectedRemoteUploadFailure(ex))
            {
                FailedPeerCooldowns[transfer.Username] = DateTime.UtcNow.Add(FailedPeerCooldown);
                Log.Warning(
                    "Upload of {Filename} to user {Username} failed because of an expected peer/network error; pausing new uploads to this peer for {CooldownSeconds} seconds: {Message}",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename),
                    LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                    FailedPeerCooldown.TotalSeconds,
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                TryFail(transfer.Id, exception: ex);

                throw;
            }
            catch (Exception ex)
            {
                Log.Error("Upload of {Filename} to user {Username} failed: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                TryFail(transfer.Id, exception: ex);

                throw;
            }
            finally
            {
                var bytesSent = Interlocked.Read(ref soulseekUploadBytesSent);
                if (bytesSent > 0)
                {
                    try
                    {
                        await _trafficAccountingService.CommitSoulseekUploadAsync(bytesSent, CancellationToken.None).ConfigureAwait(false);
                    }
                    catch (Exception ex)
                    {
                        Log.Warning("Failed to record {BytesSent} Soulseek upload bytes for {Filename} to {Username}: {Exception}",
                            bytesSent, LoggingSanitizer.SanitizeFilePath(transfer.Filename),
                            LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username), LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                    }
                }

                if (!string.IsNullOrEmpty(host) && host != Program.LocalHostName)
                {
                    try
                    {
                        Relay.TryCloseFileStream(host, id: transfer.Id);
                    }
                    catch
                    {
                        // noop
                    }
                }

                try
                {
                    Locks.TryRemove(lockName, out _);
                    Log.Debug("Released lock {LockName}", LoggingSanitizer.SanitizeExternalIdentifier(lockName));

                    if (CancellationTokens.TryRemove(transfer.Id, out var removedCts))
                    {
                        removedCts.Dispose();
                    }
                    else
                    {
                        cts?.Dispose();
                    }

                    // if for some reason this logic exits without the slotReleased delegate and Complete() being invoked,
                    // the file will get stuck in the queue and prevent any further uploads to the user. be extra cautious
                    // and ensure it gets removed
                    Queue.TryComplete(transfer.Id);
                }
                catch (Exception ex)
                {
                    Log.Error("Failed to finalize upload of {Filename} to {Username}: {Exception}",
                        LoggingSanitizer.SanitizeFilePath(transfer.Filename), LoggingSanitizer.SanitizeExternalIdentifier(transfer.Username),
                        LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                }
            }
        }

        /// <summary>
        ///     Enqueues the requested file.
        /// </summary>
        /// <param name="username">The username of the requesting user.</param>
        /// <param name="filename">The local filename of the requested file.</param>
        /// <returns>The operation context.</returns>
        public async Task<Transfer?> EnqueueAsync(string username, string filename)
        {
            if (string.IsNullOrEmpty(username))
            {
                throw new ArgumentNullException(nameof(username), "Username is required");
            }

            if (string.IsNullOrEmpty(filename))
            {
                throw new ArgumentNullException(nameof(filename), "Filename is required");
            }

            var now = DateTime.UtcNow;
            if (FailedPeerCooldowns.TryGetValue(username, out var retryAfter))
            {
                if (retryAfter > now)
                {
                    var retrySeconds = Math.Max(1, (int)Math.Ceiling((retryAfter - now).TotalSeconds));
                    Log.Warning(
                        "Rejected upload of {Filename} to {Username}; peer is cooling down after a recent connection failure for another {RetrySeconds} seconds",
                        LoggingSanitizer.SanitizeFilePath(filename),
                        LoggingSanitizer.SanitizeExternalIdentifier(username),
                        retrySeconds);
                    throw new DownloadEnqueueException("Recent transfer failed; retry later.");
                }

                FailedPeerCooldowns.TryRemove(username, out _);
            }

            var lockName = $"{nameof(EnqueueAsync)}:{username}:{filename}";

            if (!Locks.TryAdd(lockName, true))
            {
                Log.Debug("Ignoring concurrent upload enqueue attempt; lock {LockName} already held", LoggingSanitizer.SanitizeExternalIdentifier(lockName));
                return default;
            }

            Guid id = Guid.NewGuid();

            try
            {
                Log.Debug("Acquired lock {LockName}", LoggingSanitizer.SanitizeExternalIdentifier(lockName));

                Log.Information("Upload of {Filename} to {Username} requested",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username));

                using var context = ContextFactory.CreateDbContext();

                /*
                    first, get all past uploads to this user for this filename
                */
                var existingRecords = context.Transfers
                    .Where(t => t.Direction == TransferDirection.Upload)
                    .Where(t => t.Username == username)
                    .Where(t => t.Filename == filename)
                    .AsNoTracking()
                    .ToList();

                var existingInProgressRecords = existingRecords
                    .Where(t => t.EndedAt == null || !t.State.HasFlag(TransferStates.Completed))
                    .ToList();

                /*
                    if there are any that haven't ended yet (checking a few ways out of paranoia), then there's already
                    an existing transfer record covering this file, and we're already enqueued. nothing more to do!
                */
                if (existingInProgressRecords.Count != 0)
                {
                    Log.Information("Upload of {Filename} to {Username} is already queued or is in progress (ids: {Ids})",
                        LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                        string.Join(", ", existingInProgressRecords.Select(t => t.Id)));
                    return default;
                }

                /*
                    check the tracked upload dictionary in Soulseek.NET to see if it knows about this already
                    it shouldn't, if the slskd database doesn't. but things could get desynced
                */
                if (Client.Uploads.Any(u => u.Username == username && u.Filename == filename))
                {
                    throw new DuplicateTransferException("A duplicate upload of the same file to the same user is already registered");
                }

                /*
                    no existing transfers. next, check to see if they are requesting a file we are sharing

                    we do this after checking the database because database I/O is "cheaper" than disk and potentially
                    network (if we check a relay)
                */
                string host = string.Empty;
                string localFilename = string.Empty;
                long localFileLength = default;

                try
                {
                    (host, localFilename, localFileLength) = await ResolveFileInfoAsync(remoteFilename: filename);
                }
                catch (NotFoundException)
                {
                    Log.Information("Upload of {Filename} to {Username} {Rejected}: {Message}",
                        LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username), "REJECTED", "File not shared.");
                    throw new DownloadEnqueueException($"File not shared.");
                }

                Log.Debug("Resolved {Remote} to physical file {Physical} on host '{Host}'",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeFilePath(localFilename),
                    LoggingSanitizer.SanitizeExternalIdentifier(host));

                /*
                    we're cleared to enqueue! create a new transfer record, and automatically mark any existing records
                    we found as 'removed' to clean up the UI
                */
                var transfer = new Transfer()
                {
                    Id = id,
                    Username = username,
                    Direction = TransferDirection.Upload,
                    Filename = filename, // important! use the remote filename
                    Size = localFileLength,
                    StartOffset = 0, // potentially updated later during handshaking
                    RequestedAt = DateTime.UtcNow,
                    State = TransferStates.Queued | TransferStates.Locally,
                };

                context.Add(transfer);

                foreach (var record in existingRecords.Where(t => !t.Removed))
                {
                    record.Removed = true;
                    context.Update(record);
                    Log.Debug("Marked existing upload record of {Filename} to {Username} removed (id: {Id})",
                        LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username), record.Id);
                }

                context.SaveChanges();

                Log.Information("Successfully enqueued upload of {Filename} to {Username} (id: {Id})",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username), id);

                // users with uploads must be watched so that we can keep informed of their online status, privileges, and
                // statistics. this is so that we can accurately determine their effective group.
                try
                {
                    if (!Users.IsWatched(username))
                    {
                        await Users.WatchAsync(username);
                    }
                }
                catch (Exception ex)
                {
                    Log.Warning("Failed to watch user {Username}: {Exception}",
                        LoggingSanitizer.SanitizeExternalIdentifier(username), LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                }

                /*
                    schedule the upload immediately

                    Task.Run can fail due to thread pool exhaustion or OOM, and this *SHOULD* throw up the chain and
                    fail the enqueue request
                */
                _ = ObserveUploadTaskAsync(Task.Run(() => UploadAsync(transfer)), id, filename, username);

                return transfer;
            }
            catch (Exception ex)
            {
                Log.Error("Failed to enqueue upload of {Filename} to {Username}: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                if (!TryFail(id, exception: ex))
                {
                    Log.Error("Failed to clean up transfer {Id} after failed enqueue: {Exception}",
                        id, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                    throw;
                }

                throw;
            }
            finally
            {
                if (Locks.TryRemove(lockName, out _))
                {
                    Log.Debug("Released lock {LockName}", LoggingSanitizer.SanitizeExternalIdentifier(lockName));
                }
            }
        }

        private async Task ObserveUploadTaskAsync(Task uploadTask, Guid id, string filename, string username)
        {
            try
            {
                await uploadTask.ConfigureAwait(false);
                Log.Information("Task for upload of {Filename} to {Username} completed successfully",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username));
            }
            catch (Exception ex)
            {
                /*
                    things that can cause us to arrive here:

                    * file not found (moved, deleted somehow)
                    * transfer record deleted somehow
                    * transfer record updated so that it's no longer in Queued | Locally
                    * Soulseek.NET already tracking an identical upload (slskd <> Soulseek.NET desync)
                */
                Log.Debug("Observed failed upload task for {Filename} to {Username}: {Exception}",
                    LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(username),
                    LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));

                if (!TryFail(id, ex))
                {
                    Log.Error("Failed to clean up transfer {Id} after failed execution: {Exception}",
                        id, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                }
            }
        }

        private static bool IsExpectedRemoteUploadFailure(Exception exception)
        {
            var details = exception.ToString();
            var isLocalFileAccessFailure =
                details.Contains("Access to the path", StringComparison.Ordinal) ||
                details.Contains("Failed to create file", StringComparison.Ordinal);

            return !isLocalFileAccessFailure && SoulseekNetworkExceptionClassifier.IsExpected(exception);
        }

        internal int RemoveExpiredFailedPeerCooldowns(DateTime now)
        {
            var removed = 0;
            var cooldowns = (ICollection<KeyValuePair<string, DateTime>>)FailedPeerCooldowns;

            foreach (var cooldown in FailedPeerCooldowns)
            {
                if (cooldown.Value <= now && cooldowns.Remove(cooldown))
                {
                    removed++;
                }
            }

            return removed;
        }

        /// <summary>
        ///     Finds a single upload matching the specified <paramref name="expression"/>.
        /// </summary>
        /// <param name="expression">The expression to use to match uploads.</param>
        /// <returns>The found transfer, or default if not found.</returns>
        public Transfer? Find(Expression<Func<Transfer, bool>> expression)
        {
            try
            {
                using var context = ContextFactory.CreateDbContext();

                return context.Transfers
                    .AsNoTracking()
                    .Where(t => t.Direction == TransferDirection.Upload)
                    .Where(expression).FirstOrDefault();
            }
            catch (Exception ex)
            {
                Log.Error("Failed to find upload: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        /// <summary>
        ///     Returns a summary of the uploads matching the specified <paramref name="expression"/>. This can be expensive;
        ///     consider caching.
        /// </summary>
        /// <param name="expression">The expression used to select uploads for summarization.</param>
        /// <returns>
        ///     The generated summary, including the number of files and total size in bytes.
        /// </returns>
        public (int Files, long Bytes) Summarize(Expression<Func<Transfer, bool>> expression)
        {
            expression ??= t => true;

            try
            {
                using var context = ContextFactory.CreateDbContext();

                var query = context.Transfers
                    .AsNoTracking()
                    .Where(t => t.Direction == TransferDirection.Upload)
                    .Where(expression)
                    .GroupBy(t => true) // https://stackoverflow.com/a/25489456: The GroupBy(x => true) statement places all items into a single group. The Select statement the allows operations against each group.
                    .Select(t => new
                    {
                        Files = t.Count(),
                        Bytes = t.Sum(x => x.Size),
                    });

                Log.Verbose("{Method} SQL: {@Query}", nameof(Summarize), query.ToQueryString());

                var stats = query.FirstOrDefault();

                return (stats?.Files ?? 0, stats?.Bytes ?? 0);
            }
            catch (Exception ex)
            {
                Log.Error("Failed to list uploads: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        /// <summary>
        ///     Returns a list of all uploads matching the optional <paramref name="expression"/>.
        /// </summary>
        /// <param name="expression">An optional expression used to match uploads.</param>
        /// <param name="includeRemoved">A value indicating whether to include uploads that have been removed previously.</param>
        /// <returns>The list of uploads matching the specified expression, or all uploads if no expression is specified.</returns>
        public List<Transfer> List(Expression<Func<Transfer, bool>> expression, bool includeRemoved)
        {
            expression ??= t => true;

            try
            {
                using var context = ContextFactory.CreateDbContext();

                return context.Transfers
                    .AsNoTracking()
                    .Where(t => t.Direction == TransferDirection.Upload)
                    .Where(t => !t.Removed || includeRemoved)
                    .Where(expression)
                    .ToList();
            }
            catch (Exception ex)
            {
                Log.Error("Failed to list uploads: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
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
                    .Where(t => t.Direction == TransferDirection.Upload)
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
                Log.Error("Failed to page uploads: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        public int Count(bool includeRemoved = false)
        {
            using var context = ContextFactory.CreateDbContext();
            var query = context.Transfers
                .AsNoTracking()
                .Where(transfer => transfer.Direction == TransferDirection.Upload);
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
                .Where(transfer => transfer.Direction == TransferDirection.Upload)
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
        ///     Removes <see cref="TransferStates.Completed"/> uploads older than the specified <paramref name="age"/>.
        /// </summary>
        /// <param name="age">The age after which uploads are eligible for pruning, in minutes.</param>
        /// <param name="stateHasFlag">An optional, additional state by which uploads are filtered for pruning.</param>
        /// <returns>The number of pruned uploads.</returns>
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
                    .Where(t => t.Direction == TransferDirection.Upload)
                    .Where(t => !t.Removed)
                    .Where(t => t.EndedAt.HasValue && t.EndedAt.Value < cutoffDateTime)
                    .Where(t => t.State.HasFlag(stateHasFlag))
                    .ToList();

                foreach (var tx in expired)
                {
                    tx.Removed = true;
                }

                var pruned = context.SaveChanges();

                if (pruned > 0)
                {
                    Log.Debug("Pruned {Count} expired uploads with state {State}", pruned, stateHasFlag);
                }

                return pruned;
            }
            catch (Exception ex)
            {
                Log.Error("Failed to prune uploads: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        /// <summary>
        ///     Permanently deletes soft-removed, completed uploads older than the specified <paramref name="age"/>.
        /// </summary>
        /// <param name="age">The time since the last transfer update, in minutes.</param>
        /// <returns>The number of deleted uploads.</returns>
        public int PruneRemoved(int age)
        {
            try
            {
                using var context = ContextFactory.CreateDbContext();
                var cutoffDateTime = DateTime.UtcNow.AddMinutes(-age);
                var pruned = context.Transfers
                    .Where(t => t.Direction == TransferDirection.Upload)
                    .Where(t => t.Removed)
                    .Where(t => t.EndedAt.HasValue)
                    .Where(t => t.UpdatedAt < cutoffDateTime)
                    .ExecuteDelete();

                if (pruned > 0)
                {
                    Log.Debug("Permanently deleted {Count} removed uploads older than {Age} minutes", pruned, age);
                }

                return pruned;
            }
            catch (Exception ex)
            {
                Log.Error("Failed to permanently delete removed uploads: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        /// <summary>
        ///     Removes the upload matching the specified <paramref name="id"/>.
        /// </summary>
        /// <remarks>This is a soft delete; the record is retained for historical retrieval.</remarks>
        /// <param name="id">The unique identifier of the upload.</param>
        public void Remove(Guid id)
        {
            try
            {
                using var context = ContextFactory.CreateDbContext();

                var transfer = context.Transfers
                    .Where(t => t.Direction == TransferDirection.Upload)
                    .Where(t => t.Id == id)
                    .FirstOrDefault();

                if (transfer == default)
                {
                    throw new NotFoundException($"No upload matching id ${id}");
                }

                if (!transfer.State.HasFlag(TransferStates.Completed))
                {
                    throw new InvalidOperationException($"Invalid attempt to remove an upload before it is complete");
                }

                transfer.Removed = true;

                context.SaveChanges();
            }
            catch (Exception ex)
            {
                Log.Error("Failed to remove upload {Id}: {Exception}", id, LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                throw;
            }
        }

        /// <summary>
        ///     Cancels the upload matching the specified <paramref name="id"/>, if it is in progress.
        /// </summary>
        /// <param name="id">The unique identifier for the upload.</param>
        /// <returns>A value indicating whether the upload was successfully cancelled.</returns>
        public bool TryCancel(Guid id)
        {
            if (CancellationTokens.TryRemove(id, out var cts))
            {
                cts.Cancel();
                cts.Dispose();
                return true;
            }

            return false;
        }

        /// <summary>
        ///     Fails the upload matching the specified <paramref name="id"/> with the specified <paramref name="exception"/>,
        ///     and sets the final state accordingly.
        /// </summary>
        /// <remarks>
        ///     This method is designed to be idempotent, meaning subsequent calls for a given transfer shouldn't change
        ///     the EndedAt or Exception properties if they have already been set. If the transfer State already includes
        ///     the terminal Completed flag, it is unchanged.
        /// </remarks>
        /// <param name="id">The unique identifier for the upload.</param>
        /// <param name="exception">The exception that caused the failure.</param>
        /// <returns>A value indicating whether the upload was successfully failed.</returns>
        public bool TryFail(Guid id, Exception exception)
        {
            var state = exception switch
            {
                NotFoundException => TransferStates.Aborted,
                OperationCanceledException => TransferStates.Cancelled,
                TimeoutException => TransferStates.TimedOut,
                _ => TransferStates.Errored,
            };

            return TryFail(id, exception.Message, state);
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

        private bool TryFail(Guid id, string exception, TransferStates state)
        {
            var t = Find(t => t.Id == id);

            if (t is null)
            {
                return false;
            }

            t.EndedAt ??= DateTime.UtcNow;
            t.Exception ??= exception;

            if (!t.State.HasFlag(TransferStates.Completed))
            {
                t.State = TransferStates.Completed | state;
            }

            try
            {
                Update(t);
                return true;
            }
            catch (Exception ex)
            {
                Log.Error("Failed to update database: {Exception}", LoggingSanitizer.SanitizeExternalIdentifier(ex.ToString()));
                return false;
            }
        }

        /// <summary>
        ///     Resolves a remote file's location and size from shares and potentially disk.
        /// </summary>
        /// <param name="remoteFilename">The file to resolve.</param>
        /// <returns>The resolved host, filename (on disk), and length.</returns>
        /// <exception cref="NotFoundException">Thrown if the file can't be located, either in a share or on disk.</exception>
        private async Task<(string Host, string Filename, long Length)> ResolveFileInfoAsync(string remoteFilename)
        {
            string host;
            string filename;
            long length;

            /*
                locate the file and the stored details from shares.
                the size returned here will be the size the remote client is expecting.

                throws NotFoundException
            */
            (host, filename, length) = await Shares.ResolveFileAsync(remoteFilename);

            Log.Debug("Resolved shared file {RemoteFilename} to host {Host} and file {ShareFilename} (length: {ShareLength})",
                LoggingSanitizer.SanitizeFilePath(remoteFilename), LoggingSanitizer.SanitizeExternalIdentifier(host),
                LoggingSanitizer.SanitizeFilePath(filename), length);

            /*
                if the file is hosted locally, do some quick I/O to check to see if the file still exists at the location
                and of the size stored in the scan. the cost is negligible and this will keep transfers that are doomed
                to fail out of our queue.
            */
            if (host == Program.LocalHostName)
            {
                var info = Files.ResolveFileInfo(filename);

                // if the file doesn't exist we can't continue; shares have diverged from disk
                if (!info.Exists)
                {
                    Shares.RequestScan();
                    Log.Warning("The shared file '{File}' could not be located on disk. A share scan should be performed",
                        LoggingSanitizer.SanitizeFilePath(filename));
                    throw new NotFoundException($"The file '{filename}' could not be located on disk. A share scan should be performed.");
                }

                // shares have diverged from disk, but we *MIGHT* be able to upload this file, if the remote client
                // doesn't care that the size is exact.  we definitely need to re-scan though.
                if (info.Length != length)
                {
                    Log.Warning("The length of shared file '{File}' differs between the share ({ShareSize}) and disk ({DiskSize}). A share scan should be performed",
                        LoggingSanitizer.SanitizeFilePath(filename), length, info.Length);
                    Shares.RequestScan();
                }

                length = info.Length;
            }
            else if (!OptionsMonitor.CurrentValue.Flags.OptimisticRelayFileInfo)
            {
                /*
                    if the file is hosted on a relay agent and the user has set the pessimistic flag to true,
                    get the file info from the agent.

                    this was, at one time, the default behavior, but users complained that it caused a lot of timeouts
                    so now it is opt-in.
                */
                var (exists, relayLength) = await Relay.GetFileInfoAsync(agentName: host, remoteFilename);

                if (!exists || relayLength <= 0)
                {
                    // todo: force a remote scan
                    throw new NotFoundException($"The file '{remoteFilename}' could not be located on Agent {host}. A share scan should be performed.");
                }

                if (relayLength != length)
                {
                    // todo: force a remote scan
                    Log.Warning("The length of shared file '{File}' on host {Host} differs between the share ({ShareSize}) and disk ({DiskSize}). A share scan should be performed",
                        LoggingSanitizer.SanitizeFilePath(filename), LoggingSanitizer.SanitizeExternalIdentifier(host), length, relayLength);
                }

                length = relayLength;
            }

            return (host, filename, length);
        }

        private void SynchronizedUpdate(Transfer transfer, object semaphore, CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            lock (semaphore)
            {
                Update(transfer);
            }
        }

        /// <summary>
        ///     Disposes this instance.
        /// </summary>
        /// <param name="disposing">A value indicating whether disposal is in progress.</param>
        protected virtual void Dispose(bool disposing)
        {
            if (!Disposed)
            {
                if (disposing)
                {
                    FailedPeerCooldownCleanupTimer.Dispose();

                    if (Governor is IDisposable disposableGovernor)
                    {
                        disposableGovernor.Dispose();
                    }

                    if (Queue is IDisposable disposableQueue)
                    {
                        disposableQueue.Dispose();
                    }
                }

                Disposed = true;
            }
        }
    }
}
