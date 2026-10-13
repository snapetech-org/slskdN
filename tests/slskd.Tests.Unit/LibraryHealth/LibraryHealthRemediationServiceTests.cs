// <copyright file="LibraryHealthRemediationServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.LibraryHealth;

using System.Collections.Concurrent;
using System.Text.Json;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using slskd.HashDb;
using slskd.Integrations.MusicBrainz;
using slskd.Integrations.MusicBrainz.Models;
using slskd.LibraryHealth;
using slskd.LibraryHealth.Remediation;
using slskd.Transfers.MultiSource;
using Xunit;

public class LibraryHealthRemediationServiceTests
{
    [Fact]
    public async Task CreateRemediationJobAsync_AlbumCompletionStartsDownloadsForMissingRecordings()
    {
        var albumDirectory = Path.Combine(Path.GetTempPath(), $"slskdn-library-health-{Guid.NewGuid():N}", "Artist", "Album");
        using var metadata = JsonDocument.Parse("""
            [
              { "recording_id": "rec-1" },
              { "recording_id": "rec-2" }
            ]
            """);

        var issue = new LibraryIssue
        {
            IssueId = "issue-1",
            Type = LibraryIssueType.MissingTrackInRelease,
            FilePath = albumDirectory,
            MusicBrainzReleaseId = "release-1",
            CanAutoFix = true,
            Status = LibraryIssueStatus.Detected,
            Metadata = new Dictionary<string, object>
            {
                ["missing_tracks"] = metadata.RootElement.Clone(),
            },
        };

        var hashDb = new Mock<IHashDbService>();
        hashDb
            .Setup(service => service.GetLibraryIssuesByIdsAsync(It.IsAny<IEnumerable<string>>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new List<LibraryIssue> { issue });
        hashDb
            .Setup(service => service.UpdateLibraryIssueStatusesAsync(
                It.IsAny<IEnumerable<string>>(),
                LibraryIssueStatus.Fixing,
                It.IsAny<string>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(1);

        var musicBrainz = new Mock<IMusicBrainzClient>();
        musicBrainz
            .Setup(service => service.GetRecordingAsync("rec-1", It.IsAny<CancellationToken>()))
            .ReturnsAsync(new TrackTarget { MusicBrainzRecordingId = "rec-1", Artist = "Artist", Title = "Track One" });
        musicBrainz
            .Setup(service => service.GetRecordingAsync("rec-2", It.IsAny<CancellationToken>()))
            .ReturnsAsync(new TrackTarget { MusicBrainzRecordingId = "rec-2", Artist = "Artist", Title = "Track Two" });

        var requests = new ConcurrentBag<MultiSourceDownloadRequest>();
        var allDownloadsQueued = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var queuedDownloadCount = 0;
        var multiSource = new Mock<IMultiSourceDownloadService>();
        multiSource
            .Setup(service => service.FindVerifiedSourcesAsync(It.IsAny<string>(), 0, null, It.IsAny<CancellationToken>()))
            .ReturnsAsync((string filename, long _, string? _, CancellationToken _) => new ContentVerificationResult
            {
                Filename = filename,
                FileSize = 1234,
                BestSemanticKey = "rec/flac",
                SourcesByHash = new Dictionary<string, List<VerifiedSource>>
                {
                    ["hash"] = new()
                    {
                        new VerifiedSource { Username = "peer", FullPath = filename, ContentHash = "hash" },
                    },
                },
                SourcesBySemanticKey = new Dictionary<string, List<VerifiedSource>>
                {
                    ["rec/flac"] = new()
                    {
                        new VerifiedSource { Username = "peer", FullPath = filename, ContentHash = "hash" },
                    },
                },
            });
        multiSource
            .Setup(service => service.SelectCanonicalSourcesAsync(It.IsAny<ContentVerificationResult>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((ContentVerificationResult result, CancellationToken _) => result.BestSources);
        multiSource
            .Setup(service => service.DownloadAsync(It.IsAny<MultiSourceDownloadRequest>(), It.IsAny<CancellationToken>()))
            .Callback<MultiSourceDownloadRequest, CancellationToken>((request, _) =>
            {
                requests.Add(request);
                if (Interlocked.Increment(ref queuedDownloadCount) == 2)
                {
                    allDownloadsQueued.TrySetResult();
                }
            })
            .ReturnsAsync((MultiSourceDownloadRequest request, CancellationToken _) => new MultiSourceDownloadResult
            {
                Id = request.Id,
                Filename = request.Filename,
                OutputPath = request.OutputPath,
                Success = true,
            });

        var service = new LibraryHealthRemediationService(
            Mock.Of<IServiceProvider>(),
            hashDb.Object,
            multiSource.Object,
            musicBrainz.Object,
            NullLogger<LibraryHealthRemediationService>.Instance);

        var jobId = await service.CreateRemediationJobAsync(new List<string> { "issue-1" });

        Assert.True(Guid.TryParse(jobId, out _));
        musicBrainz.Verify(client => client.GetRecordingAsync("rec-1", It.IsAny<CancellationToken>()), Times.Once);
        musicBrainz.Verify(client => client.GetRecordingAsync("rec-2", It.IsAny<CancellationToken>()), Times.Once);
        multiSource.Verify(service => service.FindVerifiedSourcesAsync("Artist - Track One.flac", 0, null, It.IsAny<CancellationToken>()), Times.Once);
        multiSource.Verify(service => service.FindVerifiedSourcesAsync("Artist - Track Two.flac", 0, null, It.IsAny<CancellationToken>()), Times.Once);
        hashDb.Verify(service => service.GetLibraryIssuesByIdsAsync(
            It.Is<IEnumerable<string>>(ids => ids.SequenceEqual(new[] { "issue-1" })),
            It.IsAny<CancellationToken>()), Times.Once);
        hashDb.Verify(service => service.UpdateLibraryIssueStatusesAsync(
            It.Is<IEnumerable<string>>(ids => ids.SequenceEqual(new[] { "issue-1" })),
            LibraryIssueStatus.Fixing,
            It.Is<string>(value => IsGuid(value)),
            It.IsAny<CancellationToken>()), Times.Once);
        hashDb.Verify(service => service.GetLibraryIssuesAsync(
            It.IsAny<LibraryHealthIssueFilter>(),
            It.IsAny<CancellationToken>()), Times.Never);
        hashDb.Verify(service => service.UpdateLibraryIssueStatusAsync(
            It.IsAny<string>(),
            It.IsAny<LibraryIssueStatus>(),
            It.IsAny<CancellationToken>()), Times.Never);

        await allDownloadsQueued.Task.WaitAsync(TimeSpan.FromSeconds(2));
        Assert.Contains(
            requests,
            request => request.TargetMusicBrainzRecordingId == "rec-1" &&
                request.OutputPath == Path.Combine(albumDirectory, "Artist - Track One.flac"));
        Assert.Contains(
            requests,
            request => request.TargetMusicBrainzRecordingId == "rec-2" &&
                request.OutputPath == Path.Combine(albumDirectory, "Artist - Track Two.flac"));
    }

    [Fact]
    public async Task CheckJobStatusAndResolveIssuesAsync_UsesIndexedJobReadAndSetUpdate()
    {
        var jobId = Guid.NewGuid();
        var issues = Enumerable.Range(1, 100)
            .Select(index => new LibraryIssue
            {
                IssueId = $"issue-{index}",
                RemediationJobId = jobId.ToString(),
                Status = LibraryIssueStatus.Fixing,
            })
            .ToList();
        var hashDb = new Mock<IHashDbService>();
        hashDb.Setup(service => service.GetLibraryIssuesByRemediationJobAsync(
                jobId.ToString(),
                LibraryIssueStatus.Fixing,
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(issues);
        hashDb.Setup(service => service.UpdateLibraryIssueStatusesAsync(
                It.IsAny<IEnumerable<string>>(),
                LibraryIssueStatus.Resolved,
                null,
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(100);
        var multiSource = new Mock<IMultiSourceDownloadService>();
        multiSource.Setup(service => service.GetStatus(jobId))
            .Returns(new MultiSourceDownloadStatus { Id = jobId, State = MultiSourceDownloadState.Completed });
        var service = new LibraryHealthRemediationService(
            Mock.Of<IServiceProvider>(),
            hashDb.Object,
            multiSource.Object,
            Mock.Of<IMusicBrainzClient>(),
            NullLogger<LibraryHealthRemediationService>.Instance);

        await service.CheckJobStatusAndResolveIssuesAsync(jobId.ToString());

        hashDb.Verify(value => value.UpdateLibraryIssueStatusesAsync(
            It.Is<IEnumerable<string>>(ids => ids.Count() == 100),
            LibraryIssueStatus.Resolved,
            null,
            It.IsAny<CancellationToken>()), Times.Once);
        hashDb.Verify(value => value.UpdateLibraryIssueStatusAsync(
            It.IsAny<string>(),
            It.IsAny<LibraryIssueStatus>(),
            It.IsAny<CancellationToken>()), Times.Never);
    }

    private static bool IsGuid(string value) => Guid.TryParse(value, out _);
}
