// <copyright file="ShareService.cs" company="slskd Team">
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

// <copyright file="ShareService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Options;
using slskd.Common.Security;
using slskd.Mesh.Dht;

namespace slskd.Shares
{
    using System;
    using System.Collections.Concurrent;
    using System.Collections.Generic;
    using System.Linq;
    using System.Text;
    using System.Threading;
    using System.Threading.Tasks;
    using Serilog;
    using slskd.Files;
    using slskd.Relay;
    using Soulseek;

    /// <summary>
    ///     Provides control and interactions with configured shares and shared files.
    /// </summary>
    public class ShareService : IShareService
    {
        /// <summary>
        ///     Initializes a new instance of the <see cref="ShareService"/> class.
        /// </summary>
        /// <param name="fileService"></param>
        /// <param name="shareRepositoryFactory"></param>
        /// <param name="optionsMonitor"></param>
        /// <param name="moderationProvider">Moderation provider (T-MCP02).</param>
        /// <param name="scanner"></param>
        /// <param name="contentPeerHintService">Content peer hint service for mesh indexing.</param>
        public ShareService(
            FileService fileService,
            IShareRepositoryFactory shareRepositoryFactory,
            IOptionsMonitor<Options> optionsMonitor,
            Common.Moderation.IModerationProvider moderationProvider,
            IShareScanner? scanner = null,
            IContentPeerHintService? contentPeerHintService = null)
        {
            var options = optionsMonitor.CurrentValue;

            CacheStorageMode = options.Shares.Cache.StorageMode.ToEnum<StorageMode>();

            ShareRepositoryFactory = shareRepositoryFactory;

            var host = new Host(Program.LocalHostName);
            var repository = ShareRepositoryFactory.CreateFromHost(host.Name);

            Local = (host, repository);

            AllRepositories = [repository];

            Scanner = scanner ?? new ShareScanner(
                workerCount: options.Shares.Cache.Workers,
                fileService: fileService,
                moderationProvider: moderationProvider);

            ContentPeerHintService = contentPeerHintService;

            ScannerStateMonitorRegistration = Scanner.StateMonitor.OnChange(cacheState =>
            {
                var (previous, current) = cacheState;

                State.SetValue(state => state with
                {
                    // scan is pending if faulted, or if state DIDN'T just transition from filling to not filling AND a scan was already pending
                    ScanPending = current.Faulted || current.Cancelled || (!(previous.Filling && !current.Filling) && state.ScanPending),
                    Scanning = current.Filling,
                    Faulted = current.Faulted,
                    Cancelled = current.Cancelled,
                    ScanProgress = current.Filling && current.FillProgress < state.ScanProgress ? state.ScanProgress : current.FillProgress,
                    Directories = current.Directories,
                    Files = current.Filling && current.Files < state.Files ? state.Files : current.Files,
                });
            });

            OptionsMonitor = optionsMonitor;
            OptionsMonitorRegistration = OptionsMonitor.OnChange(options => Configure(options));

            StateMonitor = State;

            Configure(OptionsMonitor.CurrentValue);
        }

        /// <summary>
        ///     Gets the list of share hosts.
        /// </summary>
        public IReadOnlyList<Host> Hosts => HostDictionary.Values.Select(v => v.Host).Prepend(Local.Host).ToList().AsReadOnly();

        /// <summary>
        ///     Gets the local share host.
        /// </summary>
        public Host LocalHost => Local.Host;

        /// <summary>
        ///     Gets the state monitor for the service.
        /// </summary>
        public IStateMonitor<ShareState> StateMonitor { get; }

        private IShareRepositoryFactory ShareRepositoryFactory { get; }
        private IShareScanner Scanner { get; }
        private IContentPeerHintService? ContentPeerHintService { get; }
        private bool Disposed { get; set; }
        private IDisposable? ScannerStateMonitorRegistration { get; set; }
        private SemaphoreSlim ScannerSyncRoot { get; } = new SemaphoreSlim(1, 1);
        private string LastOptionsHash { get; set; } = string.Empty;
        private IOptionsMonitor<Options> OptionsMonitor { get; }
        private IDisposable? OptionsMonitorRegistration { get; set; }
        private ConcurrentDictionary<string, (Host Host, IShareRepository Repository)> HostDictionary { get; set; } = new();
        private IManagedState<ShareState> State { get; } = new ManagedState<ShareState>();
        private object SyncRoot { get; } = new object();
        private StorageMode CacheStorageMode { get; }
        private ILogger Log { get; } = Serilog.Log.ForContext<ShareService>();
        private (Host Host, IShareRepository Repository) Local { get; set; }
        private IReadOnlyList<IShareRepository> AllRepositories { get; set; }

        /// <summary>
        ///     Adds a new, or updates an existing, share host.
        /// </summary>
        /// <param name="host">The host to add or update.</param>
        public void AddOrUpdateHost(Host host)
        {
            // we assume that if this method is called that the caller has verified that the
            // file for the host exists and is valid.
            HostDictionary.AddOrUpdate(
                key: host.Name,
                addValueFactory: (key) => (host, ShareRepositoryFactory.CreateFromHost(host.Name)),
                updateValueFactory: (_, existing) => (host, existing.Repository));

            AllRepositories = HostDictionary.Values
                .Select(value => value.Repository)
                .Prepend(Local.Repository)
                .ToList()
                .AsReadOnly();

            State.SetValue(state => state with
            {
                Hosts = Hosts.Select(host => host.Name).ToArray(),
                Directories = Hosts.SelectMany(host => host.Shares).Sum(share => share.Directories ?? 0),
                Files = Hosts.SelectMany(host => host.Shares).Sum(share => share.Files ?? 0),
            });
        }

        /// <inheritdoc />
        public IShareRepository GetLocalRepository() => Local.Repository;

        /// <summary>
        ///     Returns the entire contents of the share.
        /// </summary>
        /// <returns>The entire contents of the share.</returns>
        public Task<IEnumerable<Directory>> BrowseAsync(Share? share = null)
        {
            string? prefix = null;

            if (share != null)
            {
                prefix = share.RemotePath + (share.RemotePath.EndsWith('\\') ? string.Empty : '\\');
            }

            // Keep this snapshot small: directory and file rows stay in ordered database cursors until consumed.
            var repositories = AllRepositories.ToArray();
            return Task.FromResult(EnumerateBrowseDirectories(repositories, prefix));
        }

        private static IEnumerable<Directory> EnumerateBrowseDirectories(IReadOnlyList<IShareRepository> repositories, string? prefix)
        {
            var enumerators = new IEnumerator<Directory>[repositories.Count];
            var queue = new PriorityQueue<int, BrowsePriority>(BrowsePriorityComparer.Instance);

            try
            {
                for (var index = 0; index < repositories.Count; index++)
                {
                    enumerators[index] = EnumerateRepositoryBrowse(repositories[index], prefix).GetEnumerator();
                    if (enumerators[index].MoveNext())
                    {
                        var directory = enumerators[index].Current;
                        queue.Enqueue(index, new BrowsePriority(directory.Name, index));
                    }
                }

                while (queue.TryDequeue(out var index, out var priority))
                {
                    var first = enumerators[index].Current;
                    var selected = first;
                    var firstEmpty = first.Files.Count == 0 ? first : null;
                    var selectedFileRepository = first.Files.Count > 0 ? index : -1;

                    Advance(index);

                    while (queue.TryPeek(out _, out var nextPriority) &&
                           CompareSqliteText(priority.Name, nextPriority.Name) == 0)
                    {
                        queue.TryDequeue(out var duplicateIndex, out _);
                        var duplicate = enumerators[duplicateIndex].Current;

                        if (duplicate.Files.Count > 0 && duplicateIndex > selectedFileRepository)
                        {
                            selected = duplicate;
                            selectedFileRepository = duplicateIndex;
                        }
                        else if (duplicate.Files.Count == 0 && firstEmpty is null)
                        {
                            firstEmpty = duplicate;
                        }

                        Advance(duplicateIndex);
                    }

                    yield return selectedFileRepository >= 0 ? selected : firstEmpty ?? selected;
                }
            }
            finally
            {
                foreach (var enumerator in enumerators)
                {
                    enumerator?.Dispose();
                }
            }

            void Advance(int repositoryIndex)
            {
                if (enumerators[repositoryIndex].MoveNext())
                {
                    var directory = enumerators[repositoryIndex].Current;
                    queue.Enqueue(repositoryIndex, new BrowsePriority(directory.Name, repositoryIndex));
                }
            }
        }

        private static IEnumerable<Directory> EnumerateRepositoryBrowse(IShareRepository repository, string? prefix)
        {
            using var directoryNames = repository.EnumerateDirectories(prefix).GetEnumerator();
            using var fileDirectories = EnumerateFileDirectories(repository, prefix).GetEnumerator();

            var hasDirectory = directoryNames.MoveNext();
            var hasFileDirectory = fileDirectories.MoveNext();

            while (hasDirectory || hasFileDirectory)
            {
                if (!hasFileDirectory ||
                    (hasDirectory && CompareSqliteText(directoryNames.Current, fileDirectories.Current.Name) < 0))
                {
                    yield return new Directory(directoryNames.Current);
                    hasDirectory = directoryNames.MoveNext();
                }
                else if (!hasDirectory || CompareSqliteText(fileDirectories.Current.Name, directoryNames.Current) < 0)
                {
                    yield return fileDirectories.Current;
                    hasFileDirectory = fileDirectories.MoveNext();
                }
                else
                {
                    // The stored directory and its files share one wire entry.
                    yield return fileDirectories.Current;
                    hasDirectory = directoryNames.MoveNext();
                    hasFileDirectory = fileDirectories.MoveNext();
                }
            }
        }

        private static IEnumerable<Directory> EnumerateFileDirectories(IShareRepository repository, string? prefix)
        {
            using var files = repository.EnumerateFiles(prefix, includeFullPath: true).GetEnumerator();
            var hasFile = files.MoveNext();

            while (hasFile)
            {
                var directoryName = files.Current.Filename.GetNormalizedDirectoryName();
                var directoryFiles = new List<File>();

                do
                {
                    var file = files.Current;
                    directoryFiles.Add(new File(
                        file.Code,
                        file.Filename.GetNormalizedFileName(),
                        file.Size,
                        file.Extension,
                        file.Attributes));
                    hasFile = files.MoveNext();
                }
                while (hasFile && string.Equals(
                    directoryName,
                    files.Current.Filename.GetNormalizedDirectoryName(),
                    StringComparison.Ordinal));

                yield return new Directory(directoryName, directoryFiles);
            }
        }

        private static int CompareSqliteText(string left, string right)
        {
            var leftRunes = left.EnumerateRunes().GetEnumerator();
            var rightRunes = right.EnumerateRunes().GetEnumerator();

            while (true)
            {
                var hasLeft = leftRunes.MoveNext();
                var hasRight = rightRunes.MoveNext();

                if (!hasLeft || !hasRight)
                {
                    return hasLeft.CompareTo(hasRight);
                }

                var comparison = leftRunes.Current.Value.CompareTo(rightRunes.Current.Value);
                if (comparison != 0)
                {
                    return comparison;
                }
            }
        }

        private readonly record struct BrowsePriority(string Name, int RepositoryIndex);

        private sealed class BrowsePriorityComparer : IComparer<BrowsePriority>
        {
            public static BrowsePriorityComparer Instance { get; } = new();

            public int Compare(BrowsePriority left, BrowsePriority right)
            {
                var comparison = CompareSqliteText(left.Name, right.Name);
                return comparison != 0 ? comparison : left.RepositoryIndex.CompareTo(right.RepositoryIndex);
            }
        }

        /// <summary>
        ///     Dumps the local share cache to a file.
        /// </summary>
        /// <param name="filename">The destination file.</param>
        /// <returns>The operation context.</returns>
        public Task DumpAsync(string filename)
        {
            Local.Repository.DumpTo(filename);
            return Task.CompletedTask;
        }

        /// <summary>
        ///     Returns the share host with the specified <paramref name="name"/>.
        /// </summary>
        /// <param name="name">The name of the host.</param>
        /// <param name="host">The host, if found.</param>
        /// <returns>A value indicating whether the host was found.</returns>
        public bool TryGetHost(string name, out Host host)
        {
            if (HostDictionary.TryGetValue(name, out var record))
            {
                host = record.Host;
                return true;
            }

            host = null!;
            return false;
        }

        /// <summary>
        ///     Disposes this instance.
        /// </summary>
        public void Dispose()
        {
            Dispose(disposing: true);
            GC.SuppressFinalize(this);
        }

        /// <summary>
        ///     Removes the share host with the specified <paramref name="name"/>.
        /// </summary>
        /// <param name="name">The name of the host.</param>
        /// <returns>A value indicating whether the host was removed.</returns>
        public bool TryRemoveHost(string name)
        {
            var removed = false;

            if (HostDictionary.TryRemove(name, out var removedHost))
            {
                removedHost.Repository.Dispose();
                removed = true;
            }

            AllRepositories = HostDictionary.Values
                .Select(value => value.Repository)
                .Prepend(Local.Repository)
                .ToList()
                .AsReadOnly();

            State.SetValue(state => state with
            {
                Hosts = Hosts.Select(host => host.Name).ToArray(),
                Directories = Hosts.SelectMany(host => host.Shares).Sum(share => share.Directories ?? 0),
                Files = Hosts.SelectMany(host => host.Shares).Sum(share => share.Files ?? 0),
            });

            return removed;
        }

        /// <summary>
        ///     Returns the contents of the specified <paramref name="directory"/>.
        /// </summary>
        /// <param name="directory">The directory for which the contents are to be listed.</param>
        /// <returns>The contents of the directory.</returns>
        public Task<Directory> ListDirectoryAsync(string directory)
        {
            var files = AllRepositories.SelectMany(r => r.ListFiles(directory));

            return Task.FromResult(new Directory(directory, files));
        }

        /// <summary>
        ///     Resolves the local filename of the specified <paramref name="remoteFilename"/>, if the mask is associated with a
        ///     configured share.
        /// </summary>
        /// <param name="remoteFilename">The fully qualified filename to resolve.</param>
        /// <returns>The resolved local filename.</returns>
        /// <exception cref="NotFoundException">
        ///     Thrown when the specified remote filename can not be associated with a configured share.
        /// </exception>
        public Task<(string Host, string Filename, long Size)> ResolveFileAsync(string remoteFilename)
        {
            var (resolvedFilename, size) = Local.Repository.FindFileInfo(remoteFilename);

            // when we're debugging the relay (running as both controller and agent on the same instance)
            // always resolve files from remote hosts, ignoring local. this is a crappy hack, but it is the
            // least crappy way to maintain sanity while trying to debug this feature.
            if (OptionsMonitor.CurrentValue.Relay.Mode.ToEnum<RelayMode>() == RelayMode.Debug)
            {
                Log.Warning("Ignoring resolved local file to facilitate Relay debugging.");
            }
            else if (!string.IsNullOrEmpty(resolvedFilename))
            {
                var allowedFilename = PathGuard.NormalizeAbsolutePathWithinRoots(
                    resolvedFilename,
                    OptionsMonitor.CurrentValue.Shares.Directories);
                if (allowedFilename != null)
                {
                    Log.Debug("Resolved remote file to {ResolvedFilename} on local host", allowedFilename);
                    return Task.FromResult((Program.LocalHostName, allowedFilename, size));
                }

                Log.Warning("Indexed local share path for {RemoteFilename} no longer resolves under a configured share; requesting a scan", remoteFilename);
                RequestScan();
            }
            else
            {
                Log.Debug("Failed to resolve remote file on local host; searching remote hosts: {Hosts}", HostDictionary.Values.Select(h => h.Host.Name));
            }

            // file not found locally.  begin searching other hosts one by one.
            // this is the slow, dumb way to do this, but it's plenty fast in this context.
            foreach (var host in HostDictionary.Values)
            {
                (resolvedFilename, size) = host.Repository.FindFileInfo(remoteFilename);

                if (!string.IsNullOrEmpty(resolvedFilename))
                {
                    Log.Debug("Resolved remote file to {ResolvedFilename} on host {Host}", remoteFilename, host.Host.Name);
                    return Task.FromResult((host.Host.Name, resolvedFilename, size));
                }

                Log.Debug("Failed to resolve remote file on host {Host}", host.Host.Name);
            }

            throw new NotFoundException($"The requested filename '{remoteFilename}' could not be resolved to a physical file");
        }

        /// <summary>
        ///     Returns the list of all <see cref="Scan"/>  started at or after the specified <paramref name="startedAtOrAfter"/>
        ///     unix timestamp.
        /// </summary>
        /// <remarks>
        ///     Note that this returns the scan history for local shares only.
        /// </remarks>
        /// <param name="startedAtOrAfter">A unix timestamp that serves as the lower bound of the time-based listing.</param>
        /// <returns>The operation context, including the list of found scans.</returns>
        public Task<IEnumerable<Scan>> ListScansAsync(long startedAtOrAfter = 0)
            => Task.FromResult(Local.Repository.ListScans(startedAtOrAfter));

        /// <summary>
        ///     Requests that a share scan is performed.
        /// </summary>
        public void RequestScan()
        {
            Local.Repository.FlagLatestScanAsSuspect();
            State.SetValue(state => state with { ScanPending = true });
        }

        /// <summary>
        ///     Searches the cache for the specified <paramref name="query"/> and returns the matching files.
        /// </summary>
        /// <param name="query">The query for which to search.</param>
        /// <param name="limit">An optional row limit.</param>
        /// <returns>The matching files.</returns>
        public Task<IEnumerable<File>> SearchAsync(SearchQuery query, int? limit = null)
        {
            var results = AllRepositories.SelectMany(r => r.Search(query, limit));

            return Task.FromResult(results);
        }

        /// <inheritdoc />
        public Task<IEnumerable<File>> SearchLocalAsync(SearchQuery query)
        {
            var results = Local.Repository.Search(query);
            return Task.FromResult(results);
        }

        /// <summary>
        ///     Scans the configured shares.
        /// </summary>
        /// <returns>The operation context.</returns>
        /// <exception cref="ShareScanInProgressException">Thrown when a scan is already in progress.</exception>
        public async Task ScanAsync()
        {
            // try to obtain the semaphore, or fail if it has already been obtained
            // the scanner has an identical check, but because this method changes state we need it here, too
            if (!await ScannerSyncRoot.WaitAsync(millisecondsTimeout: 0))
            {
                Log.Warning("Shared file scan rejected; scan is already in progress.");
                throw new ShareScanInProgressException("Shared files are already being scanned.");
            }

            try
            {
                State.SetValue(state => state with { Ready = false });

                await Scanner.ScanAsync(Local.Host.Shares, OptionsMonitor.CurrentValue.Shares, Local.Repository);

                Log.Debug("Backing up shared file cache database...");
                Local.Repository.BackupTo(ShareRepositoryFactory.CreateFromHostBackup(Local.Host.Name));
                Log.Debug("Shared file cache database backup complete");

                Log.Debug("Recomputing share statistics...");
                ComputeShareStatistics();
                Log.Debug("Share statistics updated: {Shares}", Local.Host.Shares.ToJson());

                // Publish content-to-peer hints for mesh indexing
                if (ContentPeerHintService != null)
                {
                    await PublishContentPeerHintsAsync();
                }

                State.SetValue(state => state with
                {
                    Directories = Hosts.SelectMany(host => host.Shares).Sum(share => share.Directories ?? 0),
                    Files = Hosts.SelectMany(host => host.Shares).Sum(share => share.Files ?? 0),
                    Ready = true,
                });
            }
            finally
            {
                ScannerSyncRoot.Release();
            }
        }

        /// <summary>
        ///     Cancels the currently running scan, if one is running.
        /// </summary>
        /// <returns>A value indicating whether a scan was cancelled.</returns>
        public bool TryCancelScan()
        {
            return Scanner.TryCancelScan();
        }

        /// <summary>
        /// Publishes content-to-peer hints for all shared content.
        /// </summary>
        private Task PublishContentPeerHintsAsync()
        {
            if (ContentPeerHintService == null)
            {
                return Task.CompletedTask;
            }

            try
            {
                Log.Debug("Publishing content-to-peer hints for mesh indexing...");

                var contentIds = new HashSet<string>();

                // Collect all unique advertisable content IDs directly from repository mappings.
                foreach (var repository in AllRepositories)
                {
                    foreach (var contentId in repository.ListAdvertisableContentIds())
                    {
                        if (!string.IsNullOrEmpty(contentId))
                        {
                            contentIds.Add(contentId);
                        }
                    }
                }

                Log.Debug("Found {Count} unique content IDs to publish peer hints for", contentIds.Count);

                // Enqueue each content ID for background publishing
                foreach (var contentId in contentIds)
                {
                    ContentPeerHintService.Enqueue(contentId);
                }

                Log.Debug("Content-to-peer hint publishing queued for {Count} content items", contentIds.Count);
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Failed to publish content-to-peer hints: {Message}", ex.Message);
            }

            return Task.CompletedTask;
        }

        /// <summary>
        ///     Initializes the service and shares.
        /// </summary>
        /// <param name="forceRescan">A value indicating whether a full re-scan of shares should be performed.</param>
        /// <returns>The operation context.</returns>
        public async Task InitializeAsync(bool forceRescan = false)
        {
            Log.Information("Initializing shares");

            // _probably_ redundant, but to be safe
            State.SetValue(state => state with { Ready = false });

            try
            {
                if (forceRescan)
                {
                    Log.Warning("Performing a forced re-scan of shares");
                    await ScanAsync();
                }
                else if (CacheStorageMode == StorageMode.Memory)
                {
                    Log.Information("Share cache StorageMode is 'Memory'. Attempting to load from backup...");

                    var backupRepository = ShareRepositoryFactory.CreateFromHostBackup(Local.Host.Name);

                    if (backupRepository.TryValidate(out _))
                    {
                        Log.Information("Share cache backup validated. Attempting to restore...");

                        Local.Repository.RestoreFrom(backupRepository);

                        Log.Information("Share cache successfully restored from backup");
                    }
                    else
                    {
                        Log.Information("Share cache backup is missing or out of date on initialization; performing initial share scan instead");
                        await ScanAsync();
                    }
                }
                else if (CacheStorageMode == StorageMode.Disk)
                {
                    Log.Information("Share cache StorageMode is 'Disk'. Attempting to validate...");

                    if (Local.Repository.TryValidate(out _))
                    {
                        // no-op
                    }
                    else
                    {
                        Log.Warning("Share cache is missing, corrupt, or is out of date. Attempting to load from backup...");

                        var backupRepository = ShareRepositoryFactory.CreateFromHostBackup(Local.Host.Name);

                        if (backupRepository.TryValidate(out _))
                        {
                            Log.Information("Share cache backup validated. Attempting to restore...");

                            Local.Repository.RestoreFrom(backupRepository);

                            Log.Information("Share cache successfully restored from backup");
                        }
                        else
                        {
                            Log.Information("Share cache and backup are both missing or out of date on initialization; performing full share scan instead");
                            await ScanAsync();
                        }
                    }
                }

                var options = OptionsMonitor.CurrentValue.Shares;
                var latestScan = Local.Repository.FindLatestScan();
                Log.Debug("Latest scan: {Scan}, current options {@Options}", latestScan, options);

                if (latestScan is null)
                {
                    throw new ShareInitializationException("Shares not yet scanned");
                }

                if (!latestScan.EndedAt.HasValue)
                {
                    throw new ShareInitializationException("Previous share scan did not complete");
                }

                if (latestScan.Suspect)
                {
                    throw new ShareInitializationException("Previous share scan was marked as suspect");
                }

                if (latestScan.OptionsJson != options.ToJson())
                {
                    throw new ShareInitializationException("Share options changed since previous scan");
                }

                Local.Repository.EnableKeepalive(true);

                Log.Debug("Recomputing share statistics...");
                ComputeShareStatistics();
                Log.Debug("Share statistics updated");

                // one of several things happened above before we got here:
                //   this method was called with forceRescan = true
                //   the storage mode is memory, and we loaded the in-memory db from a valid backup
                //   the storage mode is disk, and the file is there and valid
                //   the storage mode is disk but either missing or invalid, and we restored from a valid backup
                //   we failed to load the cache from disk or backup, and performed a full scan successfully
                // at this point there is a valid (existing, schema matching expected schema) database at the primary connection string
                State.SetValue(state => state with
                {
                    Scanning = false,
                    Faulted = false,
                    Ready = true,
                    ScanProgress = 1,
                    Hosts = Hosts.Select(host => host.Name).ToList().AsReadOnly(),
                    Directories = Hosts.SelectMany(host => host.Shares).Sum(share => share.Directories ?? 0),
                    Files = Hosts.SelectMany(host => host.Shares).Sum(share => share.Files ?? 0),
                });
            }
            catch (Exception ex)
            {
                Log.Warning(ex, "Error initializing shares: {Message}", ex.Message);

                if (!forceRescan)
                {
                    Log.Warning("Re-attempting initialization");
                    await InitializeAsync(forceRescan: true);
                }
                else
                {
                    Log.Error("Failed to initialize shares, and an attempt to force a full scan to repair failed");
                    throw;
                }
            }
        }

        private void ComputeShareStatistics()
        {
            foreach (var share in Local.Host.Shares)
            {
                var prefix = share.RemotePath + (share.RemotePath.EndsWith('\\') ? string.Empty : '\\');

                var dirs = Local.Repository.CountDirectories(prefix);
                var files = Local.Repository.CountFiles(prefix);

                share.UpdateStatistics(dirs, files);
            }
        }

        private void Configure(Options options)
        {
            Monitor.Enter(SyncRoot);

            try
            {
                var optionsHash = Compute.Sha1Hash(string.Join(';', options.Shares.Directories));

                if (optionsHash == LastOptionsHash)
                {
                    return;
                }

                var shares = options.Shares.Directories
                    .Select(share => share.TrimEnd('/', '\\'))
                    .ToHashSet() // remove duplicates
                    .Select(share => new Share(share)) // convert to Shares
                    .OrderByDescending(share => share.LocalPath.Length) // process subdirectories first.  this allows them to be aliased separately from their parent
                    .ToList();

                Local = (Local.Host with { Shares = shares }, Local.Repository);

                LastOptionsHash = optionsHash;
            }
            finally
            {
                Monitor.Exit(SyncRoot);
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
                    ScannerStateMonitorRegistration?.Dispose();
                    ScannerStateMonitorRegistration = null;
                    OptionsMonitorRegistration?.Dispose();
                    OptionsMonitorRegistration = null;

                    foreach (var host in HostDictionary.Values)
                    {
                        host.Repository.Dispose();
                    }

                    HostDictionary.Clear();
                    Local.Repository.Dispose();
                    ScannerSyncRoot.Dispose();
                }

                Disposed = true;
            }
        }
    }
}
