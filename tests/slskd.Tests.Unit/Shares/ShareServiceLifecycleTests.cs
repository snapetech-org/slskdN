// <copyright file="ShareServiceLifecycleTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Shares;

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Moq;
using slskd;
using slskd.Common.Moderation;
using slskd.Files;
using slskd.Mesh.Dht;
using slskd.Shares;
using Soulseek;
using Xunit;

public class ShareServiceLifecycleTests
{
    [Fact]
    public void ScannerUpdates_DoNotRegressScanProgressOrFiles_WhileScanIsActive()
    {
        var factory = new TestShareRepositoryFactory();
        var service = CreateService(factory, out var scanner, out _);

        scanner.Emit(new SharedFileCacheState
        {
            Filling = true,
            FillProgress = 0.6,
            Files = 120,
        });

        scanner.Emit(new SharedFileCacheState
        {
            Filling = true,
            FillProgress = 0.4,
            Files = 100,
        });

        var current = service.StateMonitor.CurrentValue;

        Assert.Equal(0.6, current.ScanProgress);
        Assert.Equal(120, current.Files);
    }

    [Fact]
    public async Task BrowseAsync_StreamsOrderedRowsAndPreservesDirectoryMergeBehavior()
    {
        var factory = new TestShareRepositoryFactory();
        var service = CreateService(factory, out _, out _);
        var local = factory.Repositories["local"];
        local.DirectoryNames = ["music\\Album", "music\\Empty", "music\\Only\\Sub"];
        local.BrowseFiles =
        [
            new Soulseek.File(1, "music\\Album\\01.mp3", 10, "mp3"),
            new Soulseek.File(2, "music\\Album\\02.mp3", 20, "mp3"),
            new Soulseek.File(3, "music\\Standalone\\track.mp3", 30, "mp3"),
        ];

        service.AddOrUpdateHost(new Host("remote"));
        var remote = factory.Repositories["remote"];
        remote.DirectoryNames = ["music\\Empty", "music\\Other"];
        remote.BrowseFiles =
        [
            new Soulseek.File(4, "music\\Album\\remote.mp3", 40, "mp3"),
            new Soulseek.File(5, "music\\Other\\01.mp3", 50, "mp3"),
        ];

        try
        {
            var browse = await service.BrowseAsync(new Share("[music]/tmp/music"));
            Assert.Equal(0, local.EnumerateDirectoriesCalls);
            Assert.Equal(0, local.EnumerateFilesCalls);

            var entries = browse.ToArray();

            Assert.Equal(
                ["music\\Album", "music\\Empty", "music\\Only\\Sub", "music\\Other", "music\\Standalone"],
                entries.Select(entry => entry.Name));
            Assert.Equal(["remote.mp3"], entries[0].Files.Select(file => file.Filename));
            Assert.Empty(entries[1].Files);
            Assert.Equal(["01.mp3"], entries[3].Files.Select(file => file.Filename));
            Assert.Equal(["track.mp3"], entries[4].Files.Select(file => file.Filename));
        }
        finally
        {
            service.Dispose();
        }
    }

    [Fact]
    public async Task BrowseAsync_ConsumesOnlyRowsNeededForTheRequestedPrefix()
    {
        var factory = new TestShareRepositoryFactory();
        var service = CreateService(factory, out _, out _);
        var repository = factory.Repositories["local"];
        repository.DirectoryNames = Enumerable.Range(0, 1000)
            .Select(index => $"music\\Album {index:D4}")
            .ToArray();
        repository.BrowseFiles = Enumerable.Range(0, 1000)
            .Select(index => new Soulseek.File(index, $"music\\Album {index:D4}\\track.mp3", 10, "mp3"))
            .ToArray();

        try
        {
            var browse = await service.BrowseAsync(new Share("[music]/tmp/music"));
            using var enumerator = browse.GetEnumerator();

            Assert.True(enumerator.MoveNext());
            Assert.Equal("music\\Album 0000", enumerator.Current.Name);
            Assert.True(repository.EnumeratedFileRows < repository.BrowseFiles.Count);
        }
        finally
        {
            service.Dispose();
        }
    }

    [Fact]
    public void TryRemoveHost_DisposesRemovedRepository()
    {
        var factory = new TestShareRepositoryFactory();
        var service = CreateService(factory, out _, out _);

        service.AddOrUpdateHost(new Host("remote"));

        var remoteRepository = factory.Repositories["remote"];
        Assert.False(remoteRepository.Disposed);

        var removed = service.TryRemoveHost("remote");

        Assert.True(removed);
        Assert.True(remoteRepository.Disposed);
    }

    [Fact]
    public void Dispose_UnsubscribesMonitors_AndDisposesOwnedRepositories()
    {
        var factory = new TestShareRepositoryFactory();
        var service = CreateService(factory, out var scanner, out var optionsMonitor);
        service.AddOrUpdateHost(new Host("remote"));

        Assert.Equal(1, scanner.ListenerCount);
        Assert.Equal(1, optionsMonitor.ListenerCount);

        service.Dispose();

        Assert.Equal(0, scanner.ListenerCount);
        Assert.Equal(0, optionsMonitor.ListenerCount);
        Assert.True(factory.Repositories["local"].Disposed);
        Assert.True(factory.Repositories["remote"].Disposed);
    }

    [Fact]
    public async Task ScanAsync_QueuesDirectAdvertisableContentProjection()
    {
        var factory = new TestShareRepositoryFactory();
        var hints = new Mock<IContentPeerHintService>();
        var service = CreateService(factory, out _, out _, hints.Object);
        var repository = factory.Repositories["local"];
        repository.AdvertisableContentIds.AddRange(["content:one", "content:two"]);

        await service.ScanAsync();

        Assert.Equal(1, repository.ListAdvertisableContentIdsCalls);
        Assert.Equal(0, repository.ListFilesCalls);
        Assert.Equal(0, repository.ListContentItemsForFileCalls);
        hints.Verify(hintService => hintService.Enqueue("content:one"), Times.Once);
        hints.Verify(hintService => hintService.Enqueue("content:two"), Times.Once);
    }

    [Fact]
    public async Task ResolveFileAsync_LocalIndexPathThroughOutsideSymlink_IsRejected()
    {
        if (OperatingSystem.IsWindows())
        {
            return;
        }

        var shareRoot = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"slskdn-shared-root-{Guid.NewGuid():N}");
        var outsideRoot = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"slskdn-shared-outside-{Guid.NewGuid():N}");
        var linkedDirectory = System.IO.Path.Combine(shareRoot, "Album");
        var outsideFilename = System.IO.Path.Combine(outsideRoot, "track.flac");
        System.IO.Directory.CreateDirectory(shareRoot);
        System.IO.Directory.CreateDirectory(outsideRoot);
        System.IO.File.WriteAllText(outsideFilename, "outside share content");
        System.IO.Directory.CreateSymbolicLink(linkedDirectory, outsideRoot);

        var factory = new TestShareRepositoryFactory();
        var optionsMonitor = new TestOptionsMonitor<Options>(new Options
        {
            Shares = new Options.SharesOptions { Directories = new[] { shareRoot } },
        });
        var scanner = new TestShareScanner();
        using var service = new ShareService(
            new FileService(optionsMonitor),
            factory,
            optionsMonitor,
            Mock.Of<IModerationProvider>(),
            scanner);
        factory.Repositories["local"].FileInfo = (System.IO.Path.Combine(linkedDirectory, "track.flac"), 21);

        try
        {
            await Assert.ThrowsAsync<NotFoundException>(
                () => service.ResolveFileAsync(@"Music\Album\track.flac"));
        }
        finally
        {
            System.IO.Directory.Delete(linkedDirectory);
            System.IO.Directory.Delete(shareRoot);
            System.IO.Directory.Delete(outsideRoot, recursive: true);
        }
    }

    [Fact]
    public async Task ResolveFileAsync_LocalIndexPathInsideConfiguredShare_IsReturned()
    {
        var shareRoot = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"slskdn-valid-share-{Guid.NewGuid():N}");
        var filename = System.IO.Path.Combine(shareRoot, "track.flac");
        System.IO.Directory.CreateDirectory(shareRoot);
        System.IO.File.WriteAllText(filename, "shared content");

        var factory = new TestShareRepositoryFactory();
        var optionsMonitor = new TestOptionsMonitor<Options>(new Options
        {
            Shares = new Options.SharesOptions { Directories = new[] { shareRoot } },
        });
        var service = new ShareService(
            new FileService(optionsMonitor),
            factory,
            optionsMonitor,
            Mock.Of<IModerationProvider>(),
            new TestShareScanner());
        factory.Repositories["local"].FileInfo = (filename, 14);

        try
        {
            var (host, resolvedFilename, size) = await service.ResolveFileAsync(@"Music\track.flac");

            Assert.Equal(Program.LocalHostName, host);
            Assert.Equal(filename, resolvedFilename);
            Assert.Equal(14, size);
        }
        finally
        {
            service.Dispose();
            System.IO.Directory.Delete(shareRoot, recursive: true);
        }
    }

    private static ShareService CreateService(
        TestShareRepositoryFactory factory,
        out TestShareScanner scanner,
        out TestOptionsMonitor<Options> optionsMonitor,
        IContentPeerHintService? contentPeerHintService = null)
    {
        optionsMonitor = new TestOptionsMonitor<Options>(new Options());
        scanner = new TestShareScanner();

        return new ShareService(
            new FileService(optionsMonitor),
            factory,
            optionsMonitor,
            Mock.Of<IModerationProvider>(),
            scanner,
            contentPeerHintService);
    }

    private sealed class TestShareRepositoryFactory : IShareRepositoryFactory
    {
        public Dictionary<string, TestShareRepository> Repositories { get; } = new(StringComparer.OrdinalIgnoreCase);

        public IShareRepository CreateFromHost(string hostName)
        {
            var repository = new TestShareRepository(hostName);
            Repositories[hostName] = repository;
            return repository;
        }

        public IShareRepository CreateFromHostBackup(string hostName)
        {
            return CreateFromHost($"{hostName}-backup");
        }

        public IShareRepository CreateFromFile(string filename, bool pooling = false)
        {
            return CreateFromHost(filename);
        }
    }

    private sealed class TestShareRepository : IShareRepository
    {
        public TestShareRepository(string name)
        {
            ConnectionString = name;
        }

        public string ConnectionString { get; }
        public bool Disposed { get; private set; }
        public List<string> AdvertisableContentIds { get; } = new();
        public int ListAdvertisableContentIdsCalls { get; private set; }
        public int ListContentItemsForFileCalls { get; private set; }
        public int ListFilesCalls { get; private set; }
        public int EnumerateDirectoriesCalls { get; private set; }
        public int EnumerateFilesCalls { get; private set; }
        public int EnumeratedFileRows { get; private set; }
        public IReadOnlyList<string> DirectoryNames { get; set; } = Array.Empty<string>();
        public IReadOnlyList<Soulseek.File> BrowseFiles { get; set; } = Array.Empty<Soulseek.File>();
        public (string Filename, long Size) FileInfo { get; set; }

        public void BackupTo(IShareRepository repository) { }
        public int CountAdvertisableItems() => 0;
        public int CountDirectories(string? parentDirectory = null) => 0;
        public int CountFiles(string? parentDirectory = null) => 0;
        public void Create(bool discardExisting = false) { }
        public void Dispose() => Disposed = true;
        public void DumpTo(string filename) { }
        public void EnableKeepalive(bool enable) { }
        public (string Filename, long Size) FindFileInfo(string maskedFilename) => FileInfo;
        public Scan? FindLatestScan() => null;
        public (string Domain, string WorkId, string MaskedFilename, bool IsAdvertisable, string ModerationReason, long CheckedAt)? FindContentItem(string contentId) => null;
        public void FlagLatestScanAsSuspect() { }
        public void FlagScanAsSuspect(long timestamp) { }
        public void InsertDirectory(string name, long timestamp) { }
        public void InsertFile(string maskedFilename, string originalFilename, DateTime touchedAt, Soulseek.File file, long timestamp, bool isBlocked = false, bool isQuarantined = false, string? moderationReason = null) { }
        public void InsertScan(long timestamp, Options.SharesOptions options) { }
        public IEnumerable<string> ListDirectories(string? parentDirectory = null) => Array.Empty<string>();
        public IEnumerable<string> EnumerateDirectories(string? parentDirectory = null)
        {
            EnumerateDirectoriesCalls++;
            return EnumerateDirectoryRows(parentDirectory);
        }

        private IEnumerable<string> EnumerateDirectoryRows(string? parentDirectory)
        {
            foreach (var name in DirectoryNames)
            {
                if (parentDirectory is null || name.StartsWith(parentDirectory, StringComparison.Ordinal))
                {
                    yield return name;
                }
            }
        }
        public IEnumerable<(string ContentId, string Domain, string WorkId, bool IsAdvertisable, string ModerationReason)> ListContentItemsForFile(string maskedFilename)
        {
            ListContentItemsForFileCalls++;
            return Array.Empty<(string ContentId, string Domain, string WorkId, bool IsAdvertisable, string ModerationReason)>();
        }
        public IEnumerable<string> ListAdvertisableContentIds()
        {
            ListAdvertisableContentIdsCalls++;
            return AdvertisableContentIds;
        }
        public IEnumerable<Soulseek.File> ListFiles(string? parentDirectory = null, bool includeFullPath = false)
        {
            ListFilesCalls++;
            return Array.Empty<Soulseek.File>();
        }
        public IEnumerable<Soulseek.File> EnumerateFiles(string? parentDirectory = null, bool includeFullPath = false)
        {
            EnumerateFilesCalls++;
            return EnumerateFileRows(parentDirectory, includeFullPath);
        }

        private IEnumerable<Soulseek.File> EnumerateFileRows(string? parentDirectory, bool includeFullPath)
        {
            foreach (var file in BrowseFiles)
            {
                if (parentDirectory is not null && !file.Filename.StartsWith(parentDirectory, StringComparison.Ordinal))
                {
                    continue;
                }

                EnumeratedFileRows++;
                yield return includeFullPath
                    ? file
                    : new Soulseek.File(file.Code, file.Filename.GetNormalizedFileName(), file.Size, file.Extension, file.Attributes);
            }
        }
        public IEnumerable<(string LocalPath, long Size)> ListLocalPathsAndSizes(string? parentDirectory = null) => Array.Empty<(string LocalPath, long Size)>();
        public IEnumerable<Scan> ListScans(long startedAtOrAfter = 0) => Array.Empty<Scan>();
        public long PruneDirectories(long olderThanTimestamp) => 0;
        public long PruneFiles(long olderThanTimestamp) => 0;
        public void RebuildFilenameIndex() { }
        public void RestoreFrom(IShareRepository repository) { }
        public IEnumerable<Soulseek.File> Search(SearchQuery query, int? limit = null) => Array.Empty<Soulseek.File>();
        public bool TryValidate() => true;
        public bool TryValidate(out IEnumerable<string> problems)
        {
            problems = Array.Empty<string>();
            return true;
        }

        public void UpdateScan(long timestamp, long end) { }
        public void UpsertContentItem(string contentId, string domain, string workId, string maskedFilename, bool isAdvertisable, string? moderationReason, long checkedAt) { }
        public void Vacuum() { }

        public bool Checkpoint() => true;
    }

    private sealed class TestShareScanner : IShareScanner
    {
        private readonly ManagedState<SharedFileCacheState> _state = new();

        public int ListenerCount => _listenerCount;

        private int _listenerCount;

        public IStateMonitor<SharedFileCacheState> StateMonitor => new TestStateMonitor(_state, this);

        public Task ScanAsync(IEnumerable<Share> shares, Options.SharesOptions options, IShareRepository repository) => Task.CompletedTask;

        public bool TryCancelScan() => false;

        public void Emit(SharedFileCacheState state)
        {
            _state.SetValue(_ => state);
        }

        private sealed class TestStateMonitor : IStateMonitor<SharedFileCacheState>
        {
            private readonly ManagedState<SharedFileCacheState> _state;
            private readonly TestShareScanner _owner;

            public TestStateMonitor(ManagedState<SharedFileCacheState> state, TestShareScanner owner)
            {
                _state = state;
                _owner = owner;
            }

            public SharedFileCacheState CurrentValue => _state.CurrentValue;

            public IDisposable OnChange(Action<(SharedFileCacheState Previous, SharedFileCacheState Current)> listener)
            {
                Interlocked.Increment(ref _owner._listenerCount);
                var registration = _state.OnChange(listener);
                return new CallbackDisposable(() =>
                {
                    registration.Dispose();
                    Interlocked.Decrement(ref _owner._listenerCount);
                });
            }
        }

        private sealed class CallbackDisposable : IDisposable
        {
            private readonly Action _dispose;
            private int _disposed;

            public CallbackDisposable(Action dispose)
            {
                _dispose = dispose;
            }

            public void Dispose()
            {
                if (Interlocked.Exchange(ref _disposed, 1) == 0)
                {
                    _dispose();
                }
            }
        }
    }
}
