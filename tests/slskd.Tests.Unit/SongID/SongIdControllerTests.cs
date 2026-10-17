// <copyright file="SongIdControllerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.SongID;

using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Http;
using Moq;
using slskd.SongID;
using slskd.SongID.API;
using Xunit;

public sealed class SongIdControllerTests
{
    [Fact]
    public async Task GetCapabilities_ReturnsReporterPayload()
    {
        var service = new Mock<ISongIdService>(MockBehavior.Strict);
        var capabilityReporter = new Mock<ISongIdCapabilityReporter>();
        capabilityReporter
            .Setup(instance => instance.GetCapabilitiesAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(new[]
            {
                new SongIdCapability
                {
                    Id = "text_query",
                    Label = "Text query analysis",
                    Status = "stable",
                    Available = true,
                    Reason = "available",
                },
                new SongIdCapability
                {
                    Id = "hash_from_audio_file_flag",
                    Label = "HashFromAudioFileEnabled flag",
                    Status = "broken",
                    Available = false,
                    Reason = "unavailable",
                },
            });
        var controller = new SongIdController(service.Object, capabilityReporter.Object);

        var result = await controller.GetCapabilities(CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var capabilities = Assert.IsAssignableFrom<IReadOnlyList<SongIdCapability>>(ok.Value);
        Assert.Equal(2, capabilities.Count);
        Assert.Contains(capabilities, capability => capability.Id == "text_query" && capability.Available);
        Assert.Contains(capabilities, capability => capability.Id == "hash_from_audio_file_flag" && !capability.Available);
    }

    [Fact]
    public async Task CreateRun_WithEmptySource_ReturnsBadRequest()
    {
        var service = new Mock<ISongIdService>(MockBehavior.Strict);
        var controller = CreateController(service.Object);

        var result = await controller.CreateRun(new SongIdRunRequest { Source = " " }, CancellationToken.None);

        var badRequest = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Equal("SongID source is required.", badRequest.Value);
        Assert.Equal("songid.source-required", controller.Response.Headers["X-Slskd-Error-Code"]);
    }

    [Fact]
    public async Task CreateRun_WithValidSource_ReturnsAcceptedRun()
    {
        var expectedRun = new SongIdRun
        {
            Id = Guid.NewGuid(),
            Source = "https://youtu.be/example",
            Status = "queued",
            CurrentStage = "queued",
            PercentComplete = 0.05,
            QueuePosition = 3,
        };
        var service = new Mock<ISongIdService>();
        service
            .Setup(instance => instance.QueueAnalyzeAsync(expectedRun.Source, It.IsAny<CancellationToken>()))
            .ReturnsAsync(expectedRun);

        var controller = CreateController(service.Object);

        var result = await controller.CreateRun(new SongIdRunRequest { Source = expectedRun.Source }, CancellationToken.None);

        var accepted = Assert.IsType<AcceptedResult>(result);
        var run = Assert.IsType<SongIdRun>(accepted.Value);
        Assert.Equal(expectedRun.Id, run.Id);
        Assert.Equal("queued", run.Status);
        Assert.Equal("queued", run.CurrentStage);
        Assert.Equal(0.05, run.PercentComplete);
        Assert.Equal(3, run.QueuePosition);
    }

    [Fact]
    public async Task CreateRun_WhenArgumentExceptionThrown_ReturnsStableError()
    {
        var service = new Mock<ISongIdService>();
        service
            .Setup(instance => instance.QueueAnalyzeAsync("bad-source", It.IsAny<CancellationToken>()))
            .ThrowsAsync(new ArgumentException("sensitive source path /srv/private/file.flac"));

        var controller = CreateController(service.Object);

        var result = await controller.CreateRun(new SongIdRunRequest { Source = "bad-source" }, CancellationToken.None);

        var badRequest = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Equal("SongID request is invalid.", badRequest.Value);
        Assert.Equal("songid.request-invalid", controller.Response.Headers["X-Slskd-Error-Code"]);
    }

    [Fact]
    public async Task CreateRun_WhenInvalidOperationExceptionThrown_ReturnsStableError()
    {
        var service = new Mock<ISongIdService>();
        service
            .Setup(instance => instance.QueueAnalyzeAsync("https://open.spotify.com/track/example", It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("ffmpeg exited with code 1: local stderr detail"));

        var controller = CreateController(service.Object);

        var result = await controller.CreateRun(new SongIdRunRequest { Source = "https://open.spotify.com/track/example" }, CancellationToken.None);

        var badRequest = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Equal("SongID analysis could not be queued.", badRequest.Value);
        Assert.Equal("songid.analysis-queue-failed", controller.Response.Headers["X-Slskd-Error-Code"]);
    }

    [Fact]
    public async Task CreateRun_TrimsSourceBeforeDispatch()
    {
        var expectedRun = new SongIdRun
        {
            Id = Guid.NewGuid(),
            Source = "https://youtu.be/example",
            Status = "queued",
        };
        var service = new Mock<ISongIdService>();
        service
            .Setup(instance => instance.QueueAnalyzeAsync(expectedRun.Source, It.IsAny<CancellationToken>()))
            .ReturnsAsync(expectedRun);

        var controller = CreateController(service.Object);

        await controller.CreateRun(new SongIdRunRequest { Source = " https://youtu.be/example " }, CancellationToken.None);

        service.Verify(instance => instance.QueueAnalyzeAsync(expectedRun.Source, It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public void ListRuns_ReturnsOkWithRequestedLimit()
    {
        var runs = new List<SongIdRun>
        {
            new() { Id = Guid.NewGuid(), Source = "first" },
            new() { Id = Guid.NewGuid(), Source = "second" },
        };
        var service = new Mock<ISongIdService>();
        service.Setup(instance => instance.List(2)).Returns(runs);

        var controller = CreateController(service.Object);

        var result = controller.ListRuns(2);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsAssignableFrom<IReadOnlyList<SongIdRun>>(ok.Value);
        Assert.Equal(2, payload.Count);
    }

    [Fact]
    public void ListRuns_WithNonPositiveLimit_UsesDefault()
    {
        var service = new Mock<ISongIdService>();
        service.Setup(instance => instance.List(10)).Returns(Array.Empty<SongIdRun>());

        var controller = CreateController(service.Object);

        var result = controller.ListRuns(0);

        Assert.IsType<OkObjectResult>(result);
        service.Verify(instance => instance.List(10), Times.Once);
    }

    [Fact]
    public void GetRun_WhenMissing_ReturnsNotFound()
    {
        var id = Guid.NewGuid();
        var service = new Mock<ISongIdService>();
        service.Setup(instance => instance.Get(id)).Returns((SongIdRun?)null);

        var controller = CreateController(service.Object);

        var result = controller.GetRun(id);

        Assert.IsType<NotFoundResult>(result);
    }

    [Fact]
    public void GetRun_WhenFound_ReturnsOk()
    {
        var run = new SongIdRun
        {
            Id = Guid.NewGuid(),
            Source = "/srv/music/example.flac",
            Status = "completed",
        };
        var service = new Mock<ISongIdService>();
        service.Setup(instance => instance.Get(run.Id)).Returns(run);

        var controller = CreateController(service.Object);

        var result = controller.GetRun(run.Id);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<SongIdRun>(ok.Value);
        Assert.Equal(run.Id, payload.Id);
        Assert.Equal("completed", payload.Status);
    }

    [Fact]
    public void GetForensicMatrix_WhenRunOrMatrixMissing_ReturnsNotFound()
    {
        var id = Guid.NewGuid();
        var service = new Mock<ISongIdService>();
        service.Setup(instance => instance.Get(id)).Returns(new SongIdRun
        {
            Id = id,
            Status = "completed",
        });

        var controller = CreateController(service.Object);

        var result = controller.GetForensicMatrix(id);

        Assert.IsType<NotFoundResult>(result);
    }

    [Fact]
    public void GetQueueSummary_ReturnsOkWithRequestedLimit()
    {
        var summary = new SongIdQueueSummary
        {
            QueuedCount = 1,
            MaxConcurrentRuns = 2,
        };
        var service = new Mock<ISongIdService>();
        service.Setup(instance => instance.GetQueueSummary(5)).Returns(summary);
        var controller = CreateController(service.Object);

        var result = controller.GetQueueSummary(5);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<SongIdQueueSummary>(ok.Value);
        Assert.Equal(1, payload.QueuedCount);
    }

    [Fact]
    public void GetEvidencePackage_WhenMissing_ReturnsNotFound()
    {
        var id = Guid.NewGuid();
        var service = new Mock<ISongIdService>();
        service.Setup(instance => instance.GetEvidencePackage(id)).Returns((SongIdRunEvidencePackage?)null);
        var controller = CreateController(service.Object);

        var result = controller.GetEvidencePackage(id);

        Assert.IsType<NotFoundResult>(result);
    }

    [Fact]
    public void GetEvidencePackage_WhenFound_ReturnsPackage()
    {
        var package = new SongIdRunEvidencePackage
        {
            RunId = Guid.NewGuid(),
            Status = "completed",
        };
        var service = new Mock<ISongIdService>();
        service.Setup(instance => instance.GetEvidencePackage(package.RunId)).Returns(package);
        var controller = CreateController(service.Object);

        var result = controller.GetEvidencePackage(package.RunId);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<SongIdRunEvidencePackage>(ok.Value);
        Assert.Equal(package.RunId, payload.RunId);
    }

    [Fact]
    public void GetForensicMatrix_WhenPresent_ReturnsDetailedMatrix()
    {
        var run = new SongIdRun
        {
            Id = Guid.NewGuid(),
            Status = "completed",
            CurrentStage = "completed",
            PercentComplete = 1,
            ForensicMatrix = new SongIdForensicMatrix
            {
                IdentityScore = 91,
                SyntheticScore = 12,
                ConfidenceScore = 88,
                QualityClass = "clean_full_track",
                PerturbationStability = 0.84,
                TopEvidenceFor = new List<string> { "repeated recognizer agreement" },
                Notes = new List<string> { "strong_identity_suppresses_synthetic_overclaim" },
                ConfidenceLane = new SongIdForensicLane
                {
                    Label = "high",
                    Score = 0.88,
                    Confidence = 88,
                    Summary = "stable under perturbation",
                },
            },
        };
        var service = new Mock<ISongIdService>();
        service.Setup(instance => instance.Get(run.Id)).Returns(run);

        var controller = CreateController(service.Object);

        var result = controller.GetForensicMatrix(run.Id);

        var ok = Assert.IsType<OkObjectResult>(result);
        var matrix = Assert.IsType<SongIdForensicMatrix>(ok.Value);
        Assert.Equal(91, matrix.IdentityScore);
        Assert.Equal("clean_full_track", matrix.QualityClass);
        Assert.Equal(0.84, matrix.PerturbationStability);
        Assert.Contains("strong_identity_suppresses_synthetic_overclaim", matrix.Notes);
        Assert.Equal(0.88, matrix.ConfidenceLane.Score);
    }

    private static SongIdController CreateController(ISongIdService service)
    {
        var capabilityReporter = new Mock<ISongIdCapabilityReporter>();
        capabilityReporter
            .Setup(instance => instance.GetCapabilitiesAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(Array.Empty<SongIdCapability>());

        return new SongIdController(service, capabilityReporter.Object)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext(),
            },
        };
    }
}
