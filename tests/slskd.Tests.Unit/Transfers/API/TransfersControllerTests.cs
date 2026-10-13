// <copyright file="TransfersControllerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Transfers.API;

using System.Linq;
using System.Linq.Expressions;
using System.IO;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.SignalR;
using Microsoft.Extensions.Options;
using Moq;
using slskd.Transfers;
using slskd.Transfers.API;
using slskd.Transfers.AutoReplace;
using slskd.Transfers.Downloads;
using slskd.Transfers.Uploads;
using Soulseek;
using Xunit;
using SlskdTransfer = slskd.Transfers.Transfer;

public class TransfersControllerTests
{
    [Fact]
    public async Task GetUserDownloadStats_UsesAggregateTransferSnapshot()
    {
        var stats = new Dictionary<string, UserDownloadStats>
        {
            ["alice"] = new() { Username = "alice", SuccessfulDownloads = 3 },
        };
        var transferService = new Mock<ITransferService>();
        transferService
            .Setup(service => service.GetUserDownloadStatsAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(stats);
        var controller = CreateController(transferService: transferService);

        var result = await controller.GetUserDownloadStats();

        var response = Assert.IsType<OkObjectResult>(result);
        Assert.Same(stats, response.Value);
        transferService.Verify(
            service => service.GetUserDownloadStatsAsync(It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task EnqueueAsync_WithWhitespaceFilename_ReturnsBadRequest()
    {
        var downloads = new Mock<IDownloadService>();
        var controller = CreateController(downloads);

        var result = await controller.EnqueueAsync(
            "alice",
            new[] { new QueueDownloadRequest { Filename = "   ", Size = 10 } });

        Assert.IsType<BadRequestObjectResult>(result);
        downloads.Verify(
            service => service.EnqueueAsync(
                It.IsAny<string>(),
                It.IsAny<IEnumerable<DownloadEnqueueRequest>>(),
                It.IsAny<CancellationToken>()),
            Times.Never);
    }

    [Fact]
    public async Task EnqueueAsync_TrimsUsernameAndFilenameBeforeEnqueue()
    {
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.EnqueueAsync(
                It.IsAny<string>(),
                It.IsAny<IEnumerable<DownloadEnqueueRequest>>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync((new List<SlskdTransfer>(), new List<string>()));

        var controller = CreateController(downloads);

        var result = await controller.EnqueueAsync(
            " alice ",
            new[] { new QueueDownloadRequest { Filename = " Music/song.flac ", Size = 10 } });

        var created = Assert.IsType<ObjectResult>(result);
        Assert.Equal(201, created.StatusCode);
        downloads.Verify(
            service => service.EnqueueAsync(
                "alice",
                It.Is<IEnumerable<DownloadEnqueueRequest>>(files =>
                    files.Single().Filename == "Music/song.flac" && files.Single().BatchId == null),
                It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task EnqueueAsync_WithMultipleFiles_AssignsSharedBatchId()
    {
        var downloads = new Mock<IDownloadService>();
        List<DownloadEnqueueRequest> queued = new();
        downloads
            .Setup(service => service.EnqueueAsync(
                It.IsAny<string>(),
                It.IsAny<IEnumerable<DownloadEnqueueRequest>>(),
                It.IsAny<CancellationToken>()))
            .Callback<string, IEnumerable<DownloadEnqueueRequest>, CancellationToken>((_, files, _) => queued = files.ToList())
            .ReturnsAsync((new List<SlskdTransfer>(), new List<string>()));

        var controller = CreateController(downloads);

        var result = await controller.EnqueueAsync(
            "alice",
            new[]
            {
                new QueueDownloadRequest { Filename = "Music/one.flac", Size = 10 },
                new QueueDownloadRequest { Filename = "Music/two.flac", Size = 20 },
            });

        var created = Assert.IsType<ObjectResult>(result);
        Assert.Equal(201, created.StatusCode);
        Assert.Equal(2, queued.Count);
        Assert.NotNull(queued[0].BatchId);
        Assert.Equal(queued[0].BatchId, queued[1].BatchId);
    }

    [Fact]
    public async Task EnqueueAsync_PreservesOptionalBatchAndSearchMetadata()
    {
        var batchId = Guid.NewGuid();
        var searchId = Guid.NewGuid();
        List<DownloadEnqueueRequest> queued = new();
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.EnqueueAsync(
                It.IsAny<string>(),
                It.IsAny<IEnumerable<DownloadEnqueueRequest>>(),
                It.IsAny<CancellationToken>()))
            .Callback<string, IEnumerable<DownloadEnqueueRequest>, CancellationToken>((_, files, _) => queued = files.ToList())
            .ReturnsAsync((new List<SlskdTransfer>(), new List<string>()));

        var controller = CreateController(downloads);
        var result = await controller.EnqueueAsync(
            "alice",
            new[]
            {
                new QueueDownloadRequest
                {
                    Filename = "Music/track.flac",
                    Size = 10,
                    BatchId = batchId,
                    BatchExternalId = "batch-42",
                    SearchId = searchId,
                    SearchText = "artist album",
                },
            });

        Assert.Equal(201, Assert.IsType<ObjectResult>(result).StatusCode);
        var request = Assert.Single(queued);
        Assert.Equal(batchId, request.BatchId);
        Assert.Equal("batch-42", request.BatchExternalId);
        Assert.Equal(searchId, request.SearchId);
        Assert.Equal("artist album", request.SearchText);
    }

    [Fact]
    public async Task EnqueueAsync_WithConfiguredDestination_PassesNormalizedDestination()
    {
        var destination = System.IO.Directory.CreateTempSubdirectory("slskdn-transfer-destination-");
        try
        {
            var downloads = new Mock<IDownloadService>();
            List<DownloadEnqueueRequest> queued = new();
            downloads
                .Setup(service => service.EnqueueAsync(
                    It.IsAny<string>(),
                    It.IsAny<IEnumerable<DownloadEnqueueRequest>>(),
                    It.IsAny<CancellationToken>()))
                .Callback<string, IEnumerable<DownloadEnqueueRequest>, CancellationToken>((_, files, _) => queued = files.ToList())
                .ReturnsAsync((new List<SlskdTransfer>(), new List<string>()));

            var options = new slskd.Options
            {
                Directories = new slskd.Options.DirectoriesOptions { Downloads = destination.FullName },
            };
            var controller = CreateController(downloads, options: options);

            var result = await controller.EnqueueAsync(
                "alice",
                new[] { new QueueDownloadRequest { Filename = "Music/song.flac", Size = 10 } },
                destination.FullName);

            var created = Assert.IsType<ObjectResult>(result);
            Assert.Equal(201, created.StatusCode);
            Assert.Equal(Path.GetFullPath(destination.FullName), queued.Single().DestinationDirectory);
        }
        finally
        {
            destination.Delete(recursive: true);
        }
    }

    [Fact]
    public async Task EnqueueAsync_WithDestinationOutsideAllowedRoots_ReturnsBadRequest()
    {
        var allowed = System.IO.Directory.CreateTempSubdirectory("slskdn-transfer-allowed-");
        var outside = System.IO.Directory.CreateTempSubdirectory("slskdn-transfer-outside-");
        try
        {
            var downloads = new Mock<IDownloadService>();
            var options = new slskd.Options
            {
                Directories = new slskd.Options.DirectoriesOptions { Downloads = allowed.FullName },
            };
            var controller = CreateController(downloads, options: options);

            var result = await controller.EnqueueAsync(
                "alice",
                new[] { new QueueDownloadRequest { Filename = "Music/song.flac", Size = 10 } },
                outside.FullName);

            Assert.IsType<BadRequestObjectResult>(result);
            downloads.Verify(
                service => service.EnqueueAsync(
                    It.IsAny<string>(),
                    It.IsAny<IEnumerable<DownloadEnqueueRequest>>(),
                    It.IsAny<CancellationToken>()),
                Times.Never);
        }
        finally
        {
            allowed.Delete(recursive: true);
            outside.Delete(recursive: true);
        }
    }

    [Fact]
    public void GetDownload_WithMismatchedRouteUsername_ReturnsNotFound()
    {
        var downloads = new Mock<IDownloadService>();
        var transferId = Guid.NewGuid();
        downloads
            .Setup(service => service.Find(It.IsAny<Expression<Func<SlskdTransfer, bool>>>()))
            .Returns(new SlskdTransfer { Id = transferId, Username = "bob" });

        var controller = CreateController(downloads);

        var result = controller.GetDownload("alice", transferId.ToString());

        Assert.IsType<NotFoundResult>(result);
    }

    [Fact]
    public async Task GetPlaceInQueueAsync_WithMismatchedRouteUsername_ReturnsNotFound()
    {
        var downloads = new Mock<IDownloadService>();
        var transferId = Guid.NewGuid();
        downloads
            .Setup(service => service.Find(It.IsAny<Expression<Func<SlskdTransfer, bool>>>()))
            .Returns(new SlskdTransfer { Id = transferId, Username = "bob" });

        var controller = CreateController(downloads);

        var result = await controller.GetPlaceInQueueAsync("alice", transferId.ToString());

        Assert.IsType<NotFoundResult>(result);
        downloads.Verify(service => service.GetPlaceInQueueAsync(It.IsAny<Guid>()), Times.Never);
    }

    [Fact]
    public async Task EnqueueAsync_WhenEnqueueThrows_DoesNotLeakExceptionMessage()
    {
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.EnqueueAsync(
                It.IsAny<string>(),
                It.IsAny<IEnumerable<DownloadEnqueueRequest>>(),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("sensitive detail"));

        var controller = CreateController(downloads);

        var result = await controller.EnqueueAsync(
            "alice",
            new[] { new QueueDownloadRequest { Filename = "Music/song.flac", Size = 10 } });

        var error = Assert.IsType<ObjectResult>(result);
        Assert.Equal(500, error.StatusCode);
        Assert.DoesNotContain("sensitive detail", error.Value?.ToString() ?? string.Empty);
        Assert.Equal("Failed to enqueue downloads", error.Value);
    }

    [Fact]
    public async Task GetPlaceInQueueAsync_WhenQueueLookupThrows_ReturnsNoContent()
    {
        var downloads = new Mock<IDownloadService>();
        var transferId = Guid.NewGuid();
        downloads
            .Setup(service => service.Find(It.IsAny<Expression<Func<SlskdTransfer, bool>>>()))
            .Returns(new SlskdTransfer { Id = transferId, Username = "alice" });
        downloads
            .Setup(service => service.GetPlaceInQueueAsync(transferId))
            .ThrowsAsync(new InvalidOperationException("sensitive detail"));

        var controller = CreateController(downloads);

        var result = await controller.GetPlaceInQueueAsync("alice", transferId.ToString());

        Assert.IsType<NoContentResult>(result);
    }

    [Fact]
    public async Task GetPlaceInQueueAsync_WhenQueueLookupTimesOut_ReturnsNoContent()
    {
        var downloads = new Mock<IDownloadService>();
        var transferId = Guid.NewGuid();
        downloads
            .Setup(service => service.Find(It.IsAny<Expression<Func<SlskdTransfer, bool>>>()))
            .Returns(new SlskdTransfer { Id = transferId, Username = "alice" });
        downloads
            .Setup(service => service.GetPlaceInQueueAsync(transferId))
            .ThrowsAsync(new TimeoutException("sensitive remote detail"));

        var controller = CreateController(downloads);

        var result = await controller.GetPlaceInQueueAsync("alice", transferId.ToString());

        Assert.IsType<NoContentResult>(result);
    }

    [Fact]
    public void GetDownloadBatch_WithInvalidId_ReturnsBadRequest()
    {
        var controller = CreateController();

        var result = controller.GetDownloadBatch("not-a-guid");

        Assert.IsType<BadRequestResult>(result);
    }

    [Fact]
    public void GetDownloadBatch_WithExistingBatch_ReturnsSummary()
    {
        var batchId = Guid.NewGuid();
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Returns<Expression<Func<SlskdTransfer, bool>>?, bool>((expression, _) =>
                new[]
                {
                    new SlskdTransfer
                    {
                        Id = Guid.NewGuid(),
                        BatchId = batchId,
                        Direction = TransferDirection.Download,
                        Filename = "Album\\done.flac",
                        State = TransferStates.Completed | TransferStates.Succeeded,
                    },
                    new SlskdTransfer
                    {
                        Id = Guid.NewGuid(),
                        BatchId = batchId,
                        Direction = TransferDirection.Download,
                        Filename = "Album\\failed.flac",
                        State = TransferStates.Completed | TransferStates.Errored,
                    },
                }.Where(expression!.Compile()).ToList());
        var controller = CreateController(downloads);

        var result = controller.GetDownloadBatch(batchId.ToString());

        var ok = Assert.IsType<OkObjectResult>(result);
        var response = Assert.IsType<DownloadBatchResponse>(ok.Value);
        Assert.Equal(batchId, response.Id);
        Assert.Equal(2, response.TransferCount);
        Assert.Equal(2, response.CompletedCount);
        Assert.Equal(1, response.SucceededCount);
        Assert.Equal(1, response.FailedCount);
    }

    [Fact]
    public void GetDownloadsAsync_WhenCompletedHidden_KeepsFailedTerminalDownloadsVisible()
    {
        var completed = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            Username = "alice",
            Filename = "Album\\done.flac",
            Direction = TransferDirection.Download,
            State = TransferStates.Completed | TransferStates.Succeeded,
        };
        var failed = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            Username = "alice",
            Filename = "Album\\retry.flac",
            Direction = TransferDirection.Download,
            State = TransferStates.Completed | TransferStates.Errored,
        };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Returns<Expression<Func<SlskdTransfer, bool>>?, bool>((expression, _) =>
                new[] { completed, failed }.Where(expression!.Compile()).ToList());

        var controller = CreateController(downloads);

        var result = controller.GetDownloadsAsync(includeCompleted: false);

        var ok = Assert.IsType<OkObjectResult>(result);
        var user = Assert.Single(Assert.IsAssignableFrom<IEnumerable<UserResponse>>(ok.Value));
        var file = Assert.Single(user.Directories.Single().Files);
        Assert.Equal("Album\\retry.flac", file.Filename);
    }

    [Fact]
    public void GetDownloadsAsync_WhenCompletedHidden_UsesTranslatablePredicate()
    {
        Expression<Func<SlskdTransfer, bool>>? capturedExpression = null;
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Callback<Expression<Func<SlskdTransfer, bool>>?, bool>((expression, _) => capturedExpression = expression)
            .Returns(new List<SlskdTransfer>());

        var controller = CreateController(downloads);

        controller.GetDownloadsAsync(includeCompleted: false);

        Assert.NotNull(capturedExpression);
        Assert.False(ContainsMethodCall(capturedExpression!.Body));
    }

    [Fact]
    public void GetUploads_WhenCompletedHidden_UsesTranslatablePredicate()
    {
        Expression<Func<SlskdTransfer, bool>>? capturedExpression = null;
        var uploads = new Mock<IUploadService>();
        uploads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Callback<Expression<Func<SlskdTransfer, bool>>, bool>((expression, _) => capturedExpression = expression)
            .Returns(new List<SlskdTransfer>());

        var controller = CreateController(uploads: uploads);

        controller.GetUploads(includeCompleted: false);

        Assert.NotNull(capturedExpression);
        Assert.False(ContainsMethodCall(capturedExpression!.Body));
    }

    [Fact]
    public void ClearCompletedDownloads_RemovesOnlySuccessfulDownloads()
    {
        var completed = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            Username = "alice",
            Filename = "Album\\done.flac",
            Direction = TransferDirection.Download,
            State = TransferStates.Completed | TransferStates.Succeeded,
        };
        var failed = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            Username = "alice",
            Filename = "Album\\retry.flac",
            Direction = TransferDirection.Download,
            State = TransferStates.Completed | TransferStates.Errored,
        };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Returns<Expression<Func<SlskdTransfer, bool>>?, bool>((expression, _) =>
                new[] { completed, failed }.Where(expression!.Compile()).ToList());

        var controller = CreateController(downloads);

        var result = controller.ClearCompletedDownloads();

        Assert.IsType<NoContentResult>(result);
        downloads.Verify(service => service.Remove(completed.Id, false), Times.Once);
        downloads.Verify(service => service.Remove(failed.Id, false), Times.Never);
    }

    [Fact]
    public void GetAcceleratedDownloadMode_ReturnsCurrentState()
    {
        var accelerated = new Mock<IAcceleratedDownloadService>();
        accelerated
            .Setup(service => service.GetState())
            .Returns(new AcceleratedDownloadState
            {
                Enabled = true,
                UpdatedAt = DateTime.UtcNow,
                Policy = "policy",
            });

        var controller = CreateController(acceleratedDownloads: accelerated);

        var result = controller.GetAcceleratedDownloadMode();

        var ok = Assert.IsType<OkObjectResult>(result);
        var state = Assert.IsType<AcceleratedDownloadState>(ok.Value);
        Assert.True(state.Enabled);
    }

    [Fact]
    public void SetAcceleratedDownloadMode_UpdatesRuntimeState()
    {
        var accelerated = new Mock<IAcceleratedDownloadService>();
        accelerated
            .Setup(service => service.SetEnabled(true))
            .Returns(new AcceleratedDownloadState
            {
                Enabled = true,
                UpdatedAt = DateTime.UtcNow,
                Policy = "policy",
            });

        var controller = CreateController(acceleratedDownloads: accelerated);

        var result = controller.SetAcceleratedDownloadMode(new AcceleratedDownloadModeRequest { Enabled = true });

        var ok = Assert.IsType<OkObjectResult>(result);
        var state = Assert.IsType<AcceleratedDownloadState>(ok.Value);
        Assert.True(state.Enabled);
        accelerated.Verify(service => service.SetEnabled(true), Times.Once);
    }

    [Fact]
    public async Task GetUploadDiagnostics_WhenListenerAndSharesLookBad_ReturnsActionableWarnings()
    {
        var uploads = new Mock<IUploadService>();
        uploads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), true))
            .Returns(new List<SlskdTransfer>
            {
                new()
                {
                    Id = Guid.NewGuid(),
                    Username = "remote-user",
                    Filename = "shared\\file.flac",
                    RequestedAt = DateTime.UtcNow,
                    State = TransferStates.Completed | TransferStates.Errored,
                    Exception = "Connection failed",
                },
            });

        var options = new slskd.Options
        {
            Soulseek = new slskd.Options.SoulseekOptions
            {
                ListenIpAddress = "127.0.0.1",
                ListenPort = 1,
            },
        };

        var state = new slskd.State
        {
            Server = new slskd.ServerState
            {
                State = SoulseekClientStates.Connected | SoulseekClientStates.LoggedIn,
            },
            Shares = new slskd.ShareState
            {
                Files = 0,
                Directories = 0,
            },
        };

        var controller = CreateController(uploads: uploads, options: options, state: state);

        var result = await controller.GetUploadDiagnostics();

        var ok = Assert.IsType<OkObjectResult>(result);
        var response = Assert.IsType<UploadDiagnosticsResponse>(ok.Value);
        Assert.False(response.LocalListenProbe.Succeeded);
        Assert.Equal("127.0.0.1", response.ListenIpAddress);
        Assert.Equal(1, response.TotalUploadRecords);
        Assert.Contains(response.Warnings, warning => warning.Contains("loopback", StringComparison.OrdinalIgnoreCase));
        Assert.Contains(response.Warnings, warning => warning.Contains("No shared files", StringComparison.OrdinalIgnoreCase));
        Assert.Single(response.RecentUploads);
    }

    [Fact]
    public void GetSpeeds_ReturnsAggregateServiceSnapshot()
    {
        var transfers = new Mock<ITransferService>();
        transfers
            .Setup(service => service.GetSpeedSnapshot())
            .Returns((2_000, 3_000, 20_000, 30_000));
        var controller = CreateController(transferService: transfers);

        var result = controller.GetSpeeds();

        var ok = Assert.IsType<OkObjectResult>(result);
        var total = GetDoubleProperty(ok.Value!, "total");
        var download = GetDoubleProperty(ok.Value!, "download");
        var upload = GetDoubleProperty(ok.Value!, "upload");
        var sessionDownloaded = GetInt64Property(ok.Value!, "sessionBytesDownloaded");
        var sessionUploaded = GetInt64Property(ok.Value!, "sessionBytesUploaded");
        var sessionTotal = GetInt64Property(ok.Value!, "sessionBytesTotal");
        Assert.Equal(2_000, download);
        Assert.Equal(3_000, upload);
        Assert.Equal(5_000, total);
        Assert.Equal(20_000, sessionDownloaded);
        Assert.Equal(30_000, sessionUploaded);
        Assert.Equal(50_000, sessionTotal);
        transfers.Verify(service => service.GetSpeedSnapshot(), Times.Once);
    }

    private static double GetDoubleProperty(object source, string propertyName)
    {
        var property = source.GetType().GetProperty(propertyName);
        Assert.NotNull(property);
        return Convert.ToDouble(property.GetValue(source));
    }

    private static long GetInt64Property(object source, string propertyName)
    {
        var property = source.GetType().GetProperty(propertyName);
        Assert.NotNull(property);
        return Convert.ToInt64(property.GetValue(source));
    }

    private static bool ContainsMethodCall(Expression expression)
    {
        return expression switch
        {
            BinaryExpression binary => ContainsMethodCall(binary.Left) || ContainsMethodCall(binary.Right),
            ConditionalExpression conditional => ContainsMethodCall(conditional.Test) ||
                ContainsMethodCall(conditional.IfTrue) ||
                ContainsMethodCall(conditional.IfFalse),
            LambdaExpression lambda => ContainsMethodCall(lambda.Body),
            MemberExpression member => member.Expression != null && ContainsMethodCall(member.Expression),
            MethodCallExpression => true,
            UnaryExpression unary => ContainsMethodCall(unary.Operand),
            _ => false,
        };
    }

    [Fact]
    public void GetTransfers_WithDownloadDirection_ReturnsOnlyDownloads()
    {
        var download = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            Username = "alice",
            Filename = "Album\\song.flac",
            Direction = TransferDirection.Download,
        };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), It.IsAny<bool>()))
            .Returns(new List<SlskdTransfer> { download });
        var uploads = new Mock<IUploadService>();

        var controller = CreateController(downloads: downloads, uploads: uploads);

        var result = controller.GetTransfers(direction: "download");

        var ok = Assert.IsType<OkObjectResult>(result);
        var items = Assert.IsAssignableFrom<IEnumerable<SlskdTransfer>>(ok.Value);
        Assert.Equal(new[] { download }, items);
        uploads.Verify(
            service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), It.IsAny<bool>()),
            Times.Never);
    }

    [Fact]
    public void GetTransfers_WithUploadDirection_ReturnsOnlyUploads()
    {
        var upload = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            Username = "bob",
            Filename = "Shared\\track.mp3",
            Direction = TransferDirection.Upload,
        };
        var downloads = new Mock<IDownloadService>();
        var uploads = new Mock<IUploadService>();
        uploads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), It.IsAny<bool>()))
            .Returns(new List<SlskdTransfer> { upload });

        var controller = CreateController(downloads: downloads, uploads: uploads);

        var result = controller.GetTransfers(direction: "upload");

        var ok = Assert.IsType<OkObjectResult>(result);
        var items = Assert.IsAssignableFrom<IEnumerable<SlskdTransfer>>(ok.Value);
        Assert.Equal(new[] { upload }, items);
        downloads.Verify(
            service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), It.IsAny<bool>()),
            Times.Never);
    }

    [Fact]
    public void GetTransfers_WithNoDirection_ReturnsBothDirections()
    {
        var download = new SlskdTransfer { Id = Guid.NewGuid(), Direction = TransferDirection.Download };
        var upload = new SlskdTransfer { Id = Guid.NewGuid(), Direction = TransferDirection.Upload };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), It.IsAny<bool>()))
            .Returns(new List<SlskdTransfer> { download });
        var uploads = new Mock<IUploadService>();
        uploads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), It.IsAny<bool>()))
            .Returns(new List<SlskdTransfer> { upload });

        var controller = CreateController(downloads: downloads, uploads: uploads);

        var result = controller.GetTransfers();

        var ok = Assert.IsType<OkObjectResult>(result);
        var items = Assert.IsAssignableFrom<IEnumerable<SlskdTransfer>>(ok.Value).ToList();
        Assert.Contains(download, items);
        Assert.Contains(upload, items);
    }

    [Fact]
    public void GetTransfers_WithInvalidDirection_ReturnsBadRequest()
    {
        var controller = CreateController();

        var result = controller.GetTransfers(direction: "sideways");

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public void GetTransfers_WhenCompletedHidden_UsesTranslatablePredicateForBothServices()
    {
        Expression<Func<SlskdTransfer, bool>>? downloadExpression = null;
        Expression<Func<SlskdTransfer, bool>>? uploadExpression = null;

        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), It.IsAny<bool>()))
            .Callback<Expression<Func<SlskdTransfer, bool>>?, bool>((expression, _) => downloadExpression = expression)
            .Returns(new List<SlskdTransfer>());
        var uploads = new Mock<IUploadService>();
        uploads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), It.IsAny<bool>()))
            .Callback<Expression<Func<SlskdTransfer, bool>>, bool>((expression, _) => uploadExpression = expression)
            .Returns(new List<SlskdTransfer>());

        var controller = CreateController(downloads: downloads, uploads: uploads);

        controller.GetTransfers(includeCompleted: false);

        Assert.NotNull(downloadExpression);
        Assert.False(ContainsMethodCall(downloadExpression!.Body));
        Assert.NotNull(uploadExpression);
        Assert.False(ContainsMethodCall(uploadExpression!.Body));
    }

    [Fact]
    public void GetTransferChanges_WithCursor_ReturnsOnlyChangedRowsAndIncludesRemoved()
    {
        var cutoff = new DateTime(2026, 7, 15, 12, 0, 0, DateTimeKind.Utc);
        var old = new SlskdTransfer { Id = Guid.NewGuid(), UpdatedAt = cutoff.AddSeconds(-1) };
        var changed = new SlskdTransfer { Id = Guid.NewGuid(), UpdatedAt = cutoff.AddSeconds(1) };
        var removed = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            Direction = TransferDirection.Upload,
            Removed = true,
            UpdatedAt = cutoff.AddSeconds(1),
        };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), true))
            .Returns<Expression<Func<SlskdTransfer, bool>>?, bool>((expression, _) =>
                new[] { old, changed }.Where(expression!.Compile()).ToList());
        var uploads = new Mock<IUploadService>();
        uploads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), true))
            .Returns<Expression<Func<SlskdTransfer, bool>>, bool>((expression, _) =>
                new[] { removed }.Where(expression.Compile()).ToList());
        var controller = CreateController(downloads: downloads, uploads: uploads);

        var result = controller.GetTransferChanges(new DateTimeOffset(cutoff).ToUnixTimeMilliseconds());

        var ok = Assert.IsType<OkObjectResult>(result);
        var response = Assert.IsType<TransferChangesResponse>(ok.Value);
        Assert.Equal(new[] { changed, removed }, response.Transfers.ToList());
        Assert.True(response.Cursor >= new DateTimeOffset(cutoff).ToUnixTimeMilliseconds());
    }

    [Fact]
    public void GetTransferChanges_InitialSnapshotExcludesRemovedRows()
    {
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Returns(new List<SlskdTransfer>());
        var uploads = new Mock<IUploadService>();
        uploads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Returns(new List<SlskdTransfer>());
        var controller = CreateController(downloads: downloads, uploads: uploads);

        var result = controller.GetTransferChanges();

        Assert.IsType<TransferChangesResponse>(Assert.IsType<OkObjectResult>(result).Value);
        downloads.Verify(
            service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false),
            Times.Once);
        uploads.Verify(
            service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false),
            Times.Once);
    }

    [Fact]
    public void GetTransferChanges_BoundedInitialSnapshotExcludesOnlySuccessfulHistoryAndReturnsTotals()
    {
        var completed = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            State = TransferStates.Completed | TransferStates.Succeeded,
        };
        var failed = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            State = TransferStates.Completed | TransferStates.Errored,
        };
        var active = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            State = TransferStates.InProgress,
        };
        Expression<Func<SlskdTransfer, bool>>? capturedExpression = null;
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Callback<Expression<Func<SlskdTransfer, bool>>?, bool>((expression, _) => capturedExpression = expression)
            .Returns<Expression<Func<SlskdTransfer, bool>>?, bool>((expression, _) =>
                new[] { completed, failed, active }.Where(expression!.Compile()).ToList());
        downloads.Setup(service => service.Count(false)).Returns(17);
        var uploads = new Mock<IUploadService>();
        uploads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Returns(new List<SlskdTransfer>());
        uploads.Setup(service => service.Count(false)).Returns(4);
        var controller = CreateController(downloads: downloads, uploads: uploads);

        var result = controller.GetTransferChanges(includeCompleted: false);

        var response = Assert.IsType<TransferChangesResponse>(Assert.IsType<OkObjectResult>(result).Value);
        Assert.Equal(new[] { failed, active }, response.Transfers);
        Assert.Equal(17, response.Counts.Download);
        Assert.Equal(4, response.Counts.Upload);
        Assert.NotNull(capturedExpression);
        Assert.False(ContainsMethodCall(capturedExpression!.Body));
    }

    [Fact]
    public void GetTransferChanges_ReturnsBoundedContinuationPageForRequestedDirection()
    {
        var requestedAt = new DateTime(2026, 10, 13, 12, 0, 0, DateTimeKind.Utc);
        var first = new SlskdTransfer
        {
            Id = Guid.Parse("ffffffff-ffff-ffff-ffff-ffffffffffff"),
            Direction = TransferDirection.Download,
            RequestedAt = requestedAt,
        };
        var last = new SlskdTransfer
        {
            Id = Guid.Parse("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
            Direction = TransferDirection.Download,
            RequestedAt = requestedAt.AddMinutes(-1),
        };
        var extra = new SlskdTransfer
        {
            Id = Guid.Parse("dddddddd-dddd-dddd-dddd-dddddddddddd"),
            Direction = TransferDirection.Download,
            RequestedAt = requestedAt.AddMinutes(-2),
        };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.ListPage(
                It.IsAny<Expression<Func<SlskdTransfer, bool>>>(),
                false,
                null,
                null,
                3))
            .Returns(new List<SlskdTransfer> { first, last, extra });
        downloads.Setup(service => service.Count(false)).Returns(12);
        var uploads = new Mock<IUploadService>();
        uploads.Setup(service => service.Count(false)).Returns(9);
        var controller = CreateController(downloads: downloads, uploads: uploads);

        var result = controller.GetTransferChanges(
            includeCompleted: false,
            limit: 2,
            direction: " DOWNLOAD ");

        var response = Assert.IsType<TransferChangesResponse>(Assert.IsType<OkObjectResult>(result).Value);
        Assert.Equal(new[] { first, last }, response.Transfers);
        Assert.Equal(12, response.Counts.Download);
        Assert.Equal(9, response.Counts.Upload);
        Assert.True(response.HasMore);
        Assert.Equal(new DateTimeOffset(last.RequestedAt), response.NextAfterRequestedAt);
        Assert.Equal(last.Id, response.NextAfterId);
        downloads.Verify(service => service.ListPage(
            It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false, null, null, 3), Times.Once);
        uploads.Verify(service => service.ListPage(
            It.IsAny<Expression<Func<SlskdTransfer, bool>>>(),
            It.IsAny<bool>(),
            It.IsAny<DateTime?>(),
            It.IsAny<Guid?>(),
            It.IsAny<int>()), Times.Never);
    }

    [Fact]
    public void GetTransferChanges_RejectsInvalidOrMixedPagingArguments()
    {
        var downloads = new Mock<IDownloadService>();
        var uploads = new Mock<IUploadService>();
        var controller = CreateController(downloads: downloads, uploads: uploads);

        Assert.IsType<BadRequestObjectResult>(controller.GetTransferChanges(limit: 501));
        Assert.IsType<BadRequestObjectResult>(controller.GetTransferChanges(direction: "download"));
        Assert.IsType<BadRequestObjectResult>(controller.GetTransferChanges(limit: 10, afterId: Guid.NewGuid()));
        Assert.IsType<BadRequestObjectResult>(controller.GetTransferChanges(
            limit: 10,
            afterRequestedAt: DateTimeOffset.UtcNow,
            afterId: Guid.NewGuid()));
        Assert.IsType<BadRequestObjectResult>(controller.GetTransferChanges(
            since: 1,
            limit: 10));

        downloads.Verify(service => service.ListPage(
            It.IsAny<Expression<Func<SlskdTransfer, bool>>>(),
            It.IsAny<bool>(),
            It.IsAny<DateTime?>(),
            It.IsAny<Guid?>(),
            It.IsAny<int>()), Times.Never);
        uploads.Verify(service => service.ListPage(
            It.IsAny<Expression<Func<SlskdTransfer, bool>>>(),
            It.IsAny<bool>(),
            It.IsAny<DateTime?>(),
            It.IsAny<Guid?>(),
            It.IsAny<int>()), Times.Never);
    }

    [Fact]
    public void GetTransferChanges_UsesSerializedMillisecondWatermarkForInitialPageFilter()
    {
        Expression<Func<SlskdTransfer, bool>>? capturedFilter = null;
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.ListPage(
                It.IsAny<Expression<Func<SlskdTransfer, bool>>>(),
                false,
                null,
                null,
                2))
            .Returns<Expression<Func<SlskdTransfer, bool>>, bool, DateTime?, Guid?, int>(
                (expression, _, _, _, _) =>
                {
                    capturedFilter = expression;
                    return new List<SlskdTransfer>();
                });
        var uploads = new Mock<IUploadService>();
        var controller = CreateController(downloads: downloads, uploads: uploads);

        var result = controller.GetTransferChanges(limit: 1, direction: "download");

        var response = Assert.IsType<TransferChangesResponse>(Assert.IsType<OkObjectResult>(result).Value);
        var serializedWatermark = DateTimeOffset.FromUnixTimeMilliseconds(response.Cursor).UtcDateTime;
        var rowAfterWatermark = new SlskdTransfer { UpdatedAt = serializedWatermark.AddTicks(1) };
        Assert.NotNull(capturedFilter);
        Assert.False(capturedFilter!.Compile()(rowAfterWatermark));
    }

    [Fact]
    public void GetTransferHistory_ReturnsStableBoundedDownloadPage()
    {
        var asOf = new DateTimeOffset(2026, 7, 15, 12, 0, 0, TimeSpan.Zero);
        var first = new SlskdTransfer { Id = Guid.NewGuid() };
        var second = new SlskdTransfer { Id = Guid.NewGuid() };
        var sentinel = new SlskdTransfer { Id = Guid.NewGuid() };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.ListCompleted(asOf.UtcDateTime, 5, 3))
            .Returns([first, second, sentinel]);
        var uploads = new Mock<IUploadService>();
        var controller = CreateController(downloads: downloads, uploads: uploads);

        var result = controller.GetTransferHistory(
            "download",
            asOf.ToUnixTimeMilliseconds(),
            offset: 5,
            limit: 2);

        var response = Assert.IsType<TransferHistoryResponse>(Assert.IsType<OkObjectResult>(result).Value);
        Assert.Equal(asOf.ToUnixTimeMilliseconds(), response.AsOf);
        Assert.True(response.HasMore);
        Assert.Equal(7, response.NextOffset);
        Assert.Equal(new[] { first, second }, response.Transfers);
        uploads.Verify(
            service => service.ListCompleted(It.IsAny<DateTime>(), It.IsAny<int>(), It.IsAny<int>()),
            Times.Never);
    }

    [Fact]
    public void GetTransferHistory_UsesReturnedMillisecondWatermarkForInitialQuery()
    {
        DateTime? queriedAsOf = null;
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.ListCompleted(It.IsAny<DateTime>(), 0, 2))
            .Callback<DateTime, int, int>((asOf, _, _) => queriedAsOf = asOf)
            .Returns([]);
        var controller = CreateController(downloads: downloads);

        var result = controller.GetTransferHistory("download", limit: 1);

        var response = Assert.IsType<TransferHistoryResponse>(Assert.IsType<OkObjectResult>(result).Value);
        var returnedAsOf = DateTimeOffset.FromUnixTimeMilliseconds(response.AsOf).UtcDateTime;
        Assert.Equal(returnedAsOf, queriedAsOf);
        Assert.Equal(0, queriedAsOf!.Value.Ticks % TimeSpan.TicksPerMillisecond);
    }

    [Fact]
    public void GetTransferChanges_MergesDirectionPagesByRequestTime()
    {
        var download = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            Direction = TransferDirection.Download,
            RequestedAt = new DateTime(2026, 10, 13, 11, 0, 0, DateTimeKind.Utc),
        };
        var upload = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            Direction = TransferDirection.Upload,
            RequestedAt = new DateTime(2026, 10, 13, 12, 0, 0, DateTimeKind.Utc),
        };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.ListPage(
                It.IsAny<Expression<Func<SlskdTransfer, bool>>>(),
                false,
                null,
                null,
                2))
            .Returns(new List<SlskdTransfer> { download });
        var uploads = new Mock<IUploadService>();
        uploads
            .Setup(service => service.ListPage(
                It.IsAny<Expression<Func<SlskdTransfer, bool>>>(),
                false,
                null,
                null,
                2))
            .Returns(new List<SlskdTransfer> { upload });
        var controller = CreateController(downloads: downloads, uploads: uploads);

        var result = controller.GetTransferChanges(includeCompleted: false, limit: 1);

        var response = Assert.IsType<TransferChangesResponse>(Assert.IsType<OkObjectResult>(result).Value);
        Assert.Equal(new[] { upload }, response.Transfers);
        Assert.True(response.HasMore);
        Assert.Equal(upload.Id, response.NextAfterId);
        downloads.Verify(service => service.ListPage(
            It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false, null, null, 2), Times.Once);
        uploads.Verify(service => service.ListPage(
            It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false, null, null, 2), Times.Once);
    }

    [Theory]
    [InlineData("sideways", 0, 250)]
    [InlineData("download", -1, 250)]
    [InlineData("download", 0, 0)]
    [InlineData("download", 0, 501)]
    public void GetTransferHistory_WithInvalidPagingInputReturnsBadRequestWithoutQueries(
        string direction,
        int offset,
        int limit)
    {
        var downloads = new Mock<IDownloadService>();
        var uploads = new Mock<IUploadService>();
        var controller = CreateController(downloads: downloads, uploads: uploads);

        var result = controller.GetTransferHistory(direction, offset: offset, limit: limit);

        Assert.IsType<BadRequestObjectResult>(result);
        downloads.Verify(
            service => service.ListCompleted(It.IsAny<DateTime>(), It.IsAny<int>(), It.IsAny<int>()),
            Times.Never);
        uploads.Verify(
            service => service.ListCompleted(It.IsAny<DateTime>(), It.IsAny<int>(), It.IsAny<int>()),
            Times.Never);
    }

    [Fact]
    public void GetTransferHistory_WithNegativeWatermarkReturnsBadRequestWithoutQueries()
    {
        var downloads = new Mock<IDownloadService>();
        var controller = CreateController(downloads: downloads);

        var result = controller.GetTransferHistory("download", asOf: -1);

        Assert.IsType<BadRequestObjectResult>(result);
        downloads.Verify(
            service => service.ListCompleted(It.IsAny<DateTime>(), It.IsAny<int>(), It.IsAny<int>()),
            Times.Never);
    }

    [Fact]
    public void GetTransferChanges_WithNegativeCursorReturnsBadRequestWithoutQueries()
    {
        var downloads = new Mock<IDownloadService>();
        var uploads = new Mock<IUploadService>();
        var controller = CreateController(downloads: downloads, uploads: uploads);

        var result = controller.GetTransferChanges(-1);

        Assert.IsType<BadRequestObjectResult>(result);
        downloads.Verify(
            service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), It.IsAny<bool>()),
            Times.Never);
        uploads.Verify(
            service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), It.IsAny<bool>()),
            Times.Never);
    }

    [Fact]
    public void ClearCompletedDownloads_EmitsRemovedActivityForRemovedTransfers()
    {
        var completed = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            RequestId = Guid.NewGuid(),
            Username = "alice",
            Filename = "Album\\done.flac",
            Direction = TransferDirection.Download,
            State = TransferStates.Completed | TransferStates.Succeeded,
        };
        var downloads = new Mock<IDownloadService>();
        downloads
            .Setup(service => service.List(It.IsAny<Expression<Func<SlskdTransfer, bool>>>(), false))
            .Returns<Expression<Func<SlskdTransfer, bool>>?, bool>((expression, _) =>
                new[] { completed }.Where(expression!.Compile()).ToList());
        var hub = CreateHubMock(out var clientProxy);

        var controller = CreateController(downloads: downloads, transfersHub: hub);

        var result = controller.ClearCompletedDownloads();

        Assert.IsType<NoContentResult>(result);
        clientProxy.Verify(
            proxy => proxy.SendCoreAsync(
                TransferHubMethods.Removed,
                It.Is<object[]>(arguments =>
                    arguments.Length == 1 &&
                    ((TransferRemoved)arguments[0]).RequestId == completed.RequestId),
                It.IsAny<CancellationToken>()),
            Times.Once);
    }

    private static Mock<IHubContext<TransfersHub>> CreateHubMock(out Mock<IClientProxy> clientProxy)
    {
        clientProxy = new Mock<IClientProxy>();
        var clients = new Mock<IHubClients>();
        clients.SetupGet(c => c.All).Returns(clientProxy.Object);

        var hub = new Mock<IHubContext<TransfersHub>>();
        hub.SetupGet(h => h.Clients).Returns(clients.Object);
        return hub;
    }

    private static TransfersController CreateController(
        Mock<IDownloadService>? downloads = null,
        Mock<IUploadService>? uploads = null,
        Mock<IAcceleratedDownloadService>? acceleratedDownloads = null,
        slskd.Options? options = null,
        slskd.State? state = null,
        Mock<IHubContext<TransfersHub>>? transfersHub = null,
        Mock<ITransferService>? transferService = null)
    {
        transferService ??= new Mock<ITransferService>();
        transferService.SetupGet(service => service.Downloads).Returns((downloads ?? new Mock<IDownloadService>()).Object);
        transferService.SetupGet(service => service.Uploads).Returns((uploads ?? new Mock<IUploadService>()).Object);

        var optionsSnapshot = new Mock<IOptionsSnapshot<slskd.Options>>();
        optionsSnapshot.SetupGet(snapshot => snapshot.Value).Returns(options ?? new slskd.Options());

        var stateSnapshot = new Mock<IStateSnapshot<slskd.State>>();
        stateSnapshot.SetupGet(snapshot => snapshot.Value).Returns(state ?? new slskd.State());

        using var autoReplaceBackgroundService = new AutoReplaceBackgroundService(
            Mock.Of<IAutoReplaceService>(),
            Mock.Of<ISoulseekClient>(),
            Mock.Of<IOptionsMonitor<slskd.Options>>(),
            new OptionsAtStartup());

        return new TransfersController(
            transferService.Object,
            optionsSnapshot.Object,
            stateSnapshot.Object,
            Mock.Of<IAutoReplaceService>(),
            autoReplaceBackgroundService,
            (acceleratedDownloads ?? new Mock<IAcceleratedDownloadService>()).Object,
            (transfersHub ?? CreateHubMock(out _)).Object);
    }
}
