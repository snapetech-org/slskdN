// <copyright file="StubVirtualSoulfindServices.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Integration;

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Soulseek;
using slskd.Common.Moderation;
using slskd.MediaCore;
using slskd.Shares;
using slskd.VirtualSoulfind.v2.Backends;
using slskd.VirtualSoulfind.v2.Catalogue;
using slskd.VirtualSoulfind.v2.Intents;
using slskd.VirtualSoulfind.v2.Planning;
using slskd.VirtualSoulfind.v2.Sources;

/// <summary>
/// Stub <see cref="IDescriptorPublisher"/> for integration tests. No-op publish.
/// </summary>
internal sealed class StubDescriptorPublisher : IDescriptorPublisher
{
    public Task<bool> PublishAsync(ContentDescriptor descriptor, CancellationToken ct = default) =>
        Task.FromResult(true);
}

/// <summary>
/// Stub <see cref="IPeerReputationStore"/> for integration tests. In-memory no-op.
/// </summary>
internal sealed class StubPeerReputationStore : IPeerReputationStore
{
    public Task RecordEventAsync(PeerReputationEvent @event, CancellationToken cancellationToken = default) =>
        Task.CompletedTask;

    public Task<int> GetReputationScoreAsync(string peerId, CancellationToken cancellationToken = default) =>
        Task.FromResult(0);

    public Task<bool> IsPeerBannedAsync(string peerId, CancellationToken cancellationToken = default) =>
        Task.FromResult(false);

    public Task<IEnumerable<PeerReputationEvent>> GetRecentEventsAsync(string peerId, int maxEvents = 50, CancellationToken cancellationToken = default) =>
        Task.FromResult<IEnumerable<PeerReputationEvent>>(Array.Empty<PeerReputationEvent>());

    public Task DecayAndCleanupAsync(CancellationToken cancellationToken = default) =>
        Task.CompletedTask;

    public Task<PeerReputationStats> GetStatsAsync(CancellationToken cancellationToken = default) =>
        Task.FromResult(new PeerReputationStats());
}

/// <summary>
/// Stub <see cref="IShareRepository"/> for integration tests. FindContentItem returns null; other members no-op or default.
/// Supports <see cref="SeedForIsAdvertisableTest"/> to drive ShareRepository_IsAdvertisableFlag_IntegratesWithVirtualSoulfind.
/// </summary>
internal sealed class StubShareRepository : IShareRepository
{
    private readonly Dictionary<string, List<(string ContentId, string Domain, string WorkId, bool IsAdvertisable, string ModerationReason)>> _contentItemsByFile = new();

    public string ConnectionString => ":memory:";

    public (string Domain, string WorkId, string MaskedFilename, bool IsAdvertisable, string ModerationReason, long CheckedAt)? FindContentItem(string contentId) => null;

    public IEnumerable<(string ContentId, string Domain, string WorkId, bool IsAdvertisable, string ModerationReason)> ListContentItemsForFile(string maskedFilename)
    {
        lock (_contentItemsByFile)
        {
            if (_contentItemsByFile.TryGetValue(maskedFilename, out var list))
                return list;
        }
        return Array.Empty<(string, string, string, bool, string)>();
    }

    public IEnumerable<string> ListAdvertisableContentIds()
    {
        lock (_contentItemsByFile)
        {
            return _contentItemsByFile.Values
                .SelectMany(items => items)
                .Where(item => item.IsAdvertisable)
                .Select(item => item.ContentId)
                .ToList();
        }
    }

    /// <summary>
    /// Seeds data so ListFiles and ListContentItemsForFile return items for IsAdvertisable integration tests.
    /// </summary>
    public void SeedForIsAdvertisableTest()
    {
        const string masked = "Music\\Test\\Album\\track.mp3";
        lock (_contentItemsByFile)
        {
            _contentItemsByFile.Clear();
            _contentItemsByFile[masked] = new List<(string, string, string, bool, string)>
            {
                ("content:mb:rec:1", "Music", "work:1", true, ""),
                ("content:mb:rec:2", "Music", "work:1", false, "blocked:test"),
            };
        }
    }

    public int CountAdvertisableItems() => 0;

    public void BackupTo(IShareRepository repository) { }
    public int CountDirectories(string? parentDirectory = null) => 0;
    public int CountFiles(string? parentDirectory = null) => 0;
    public void Create(bool discardExisting = false) { }
    public void DumpTo(string filename) { }
    public void EnableKeepalive(bool enable) { }
    public (string Filename, long Size) FindFileInfo(string maskedFilename) => ("", 0L);
    public Scan FindLatestScan() => default;
    public void FlagLatestScanAsSuspect() { }
    public void FlagScanAsSuspect(long timestamp) { }
    public void InsertDirectory(string name, long timestamp) { }
    public void InsertFile(string maskedFilename, string originalFilename, DateTime touchedAt, File file, long timestamp, bool isBlocked = false, bool isQuarantined = false, string? moderationReason = null) { }
    public void InsertScan(long timestamp, slskd.Options.SharesOptions options) { }
    public IEnumerable<string> ListDirectories(string? parentDirectory = null) => Array.Empty<string>();
    public IEnumerable<string> EnumerateDirectories(string? parentDirectory = null) => ListDirectories(parentDirectory);
    public IEnumerable<File> ListFiles(string? parentDirectory = null, bool includeFullPath = false)
    {
        lock (_contentItemsByFile)
        {
            foreach (var masked in _contentItemsByFile.Keys)
                yield return new File(1, masked, 1024, "mp3");
        }
    }
    public IEnumerable<File> EnumerateFiles(string? parentDirectory = null, bool includeFullPath = false) => ListFiles(parentDirectory, includeFullPath);
    public IEnumerable<(string LocalPath, long Size)> ListLocalPathsAndSizes(string parentDirectory = null) => Array.Empty<(string, long)>();
    public IEnumerable<Scan> ListScans(long startedAtOrAfter = 0) => Array.Empty<Scan>();
    public long PruneDirectories(long olderThanTimestamp) => 0L;
    public long PruneFiles(long olderThanTimestamp) => 0L;
    public void RebuildFilenameIndex() { }
    public void RestoreFrom(IShareRepository repository) { }
    public IEnumerable<File> Search(SearchQuery query, int? limit = null) => Array.Empty<File>();
    public bool TryValidate() => true;
    public bool TryValidate(out IEnumerable<string> problems) { problems = Array.Empty<string>(); return true; }
    public void UpdateScan(long timestamp, long end) { }
    public void Vacuum() { }

    public bool Checkpoint() => true;
    public void UpsertContentItem(string contentId, string domain, string workId, string maskedFilename, bool isAdvertisable, string? moderationReason, long checkedAt) { }

    public void Dispose() { }
}
