// <copyright file="DownloadDestinationTemplateTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Tests.Unit.Transfers.Downloads;

using System;
using System.IO;
using System.Linq;
using System.Text;
using slskd.Transfers.Downloads;
using Xunit;
using SlskdTransfer = slskd.Transfers.Transfer;
using TransferDirection = Soulseek.TransferDirection;

public sealed class DownloadDestinationTemplateTests
{
    [Fact]
    public void Render_ExpandsSourceBatchAndSearchContext()
    {
        var batchId = Guid.NewGuid();
        var searchId = Guid.NewGuid();
        var transfer = CreateTransfer(@"Music\Jazz\Track.flac");
        var request = new DownloadRequest
        {
            BatchId = batchId,
            BatchExternalId = "batch/7",
            SearchId = searchId,
            SearchText = "artist/album: Live",
        };

        var path = DownloadDestinationTemplate.Render(
            "${SOURCE_USERNAME}/${SOURCE_PATH}/${SOURCE_DIRECTORY}/${BATCH_ID}/${BATCH_EXTERNAL_ID}/${SEARCH_ID}/${SEARCH_TEXT}",
            transfer,
            request);

        Assert.Equal(
            Path.Combine("alice", "Music", "Jazz", "Jazz", batchId.ToString("D"), "batch_7", searchId.ToString("D"), "artist_album_ Live"),
            path);
    }

    [Fact]
    public void Render_UsesDocumentedFallbacksForMissingOriginMetadata()
    {
        var transfer = CreateTransfer("Track.flac");

        var path = DownloadDestinationTemplate.Render(
            "${SOURCE_DIRECTORY}/${BATCH_ID}/${BATCH_EXTERNAL_ID}/${SEARCH_ID}/${SEARCH_TEXT}",
            transfer,
            request: null);

        Assert.Equal(
            Path.Combine("_singles", "unknown_batch_id", "unknown_batch_external_id", "unknown_search_id", "unknown_search_text"),
            path);
    }

    [Fact]
    public void Render_SanitizesPeerAndSearchTextIntoSinglePathComponents()
    {
        var transfer = CreateTransfer(@"Music\Track.flac", "../../outside");
        var request = new DownloadRequest { SearchText = "../../outside" };

        var path = DownloadDestinationTemplate.Render("${SOURCE_USERNAME}/${SEARCH_TEXT}", transfer, request);

        Assert.Equal(2, path.Split([Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar], StringSplitOptions.RemoveEmptyEntries).Length);
        Assert.DoesNotContain("..", path.Split([Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar], StringSplitOptions.RemoveEmptyEntries));
    }

    [Fact]
    public void Render_SanitizesUrlEncodedTraversalInExternalTokenValues()
    {
        var transfer = CreateTransfer("Music/Track.flac", "%2e%2e");
        var request = new DownloadRequest { SearchText = "%252e%252e" };

        var path = DownloadDestinationTemplate.Render("${SOURCE_USERNAME}/${SEARCH_TEXT}", transfer, request);

        Assert.DoesNotContain("%", path);
        Assert.DoesNotContain("..", path.Split([Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar], StringSplitOptions.RemoveEmptyEntries));
    }

    [Theory]
    [InlineData("../outside")]
    [InlineData("folder/../../outside")]
    [InlineData("/absolute/path")]
    [InlineData("C:\\absolute\\path")]
    [InlineData("folder/%2e%2e/outside")]
    [InlineData("folder/%252e%252e/outside")]
    [InlineData("${UNKNOWN_TOKEN}")]
    [InlineData("${UNFINISHED")]
    public void Validate_RejectsRootedTraversalAndUnknownTokenPaths(string template)
    {
        Assert.Throws<ArgumentException>(() => DownloadDestinationTemplate.Validate(template));
    }

    [Fact]
    public void Render_BoundsLongExternalTextComponentsWithoutLosingUnicodeValidity()
    {
        var request = new DownloadRequest { SearchText = new string('é', 500) };

        var path = DownloadDestinationTemplate.Render("${SEARCH_TEXT}", CreateTransfer("Track.flac"), request);

        Assert.True(Encoding.UTF8.GetByteCount(path) <= 200);
        Assert.True(path.EnumerateRunes().Count() < 500);
    }

    private static SlskdTransfer CreateTransfer(string filename, string username = "alice")
        => new()
        {
            Id = Guid.NewGuid(),
            Username = username,
            Direction = TransferDirection.Download,
            Filename = filename,
            RequestedAt = DateTime.UtcNow,
        };
}
