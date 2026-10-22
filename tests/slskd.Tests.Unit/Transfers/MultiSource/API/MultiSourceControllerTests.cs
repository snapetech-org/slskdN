// <copyright file="MultiSourceControllerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Transfers.MultiSource.API;

using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using slskd.Transfers;
using slskd.Transfers.MultiSource;
using slskd.Transfers.MultiSource.API;
using slskd.Transfers.MultiSource.Discovery;
using Soulseek;
using Xunit;

public class MultiSourceControllerTests
{
    [Fact]
    public async Task GetTopUsers_WhenSearchSafetyBudgetExhausted_DoesNotSearchSoulseek()
    {
        var soulseekClient = new Mock<ISoulseekClient>();
        var safetyLimiter = new Mock<slskd.Common.Security.ISoulseekSafetyLimiter>();
        safetyLimiter
            .Setup(limiter => limiter.TryConsumeSearch("multisource-users"))
            .Returns(false);

        var controller = new MultiSourceController(
            Mock.Of<IMultiSourceDownloadService>(),
            soulseekClient.Object,
            Mock.Of<ITransferService>(),
            Mock.Of<ISourceDiscoveryService>(),
            Mock.Of<IContentVerificationService>(),
            safetyLimiter.Object);

        var result = await controller.GetTopUsers("hello");

        var limited = Assert.IsType<ObjectResult>(result);
        Assert.Equal(StatusCodes.Status429TooManyRequests, limited.StatusCode);
        Assert.Contains("safety budget exhausted", limited.Value?.ToString() ?? string.Empty);
        soulseekClient.Verify(
            client => client.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken>()),
            Times.Never);
    }

    [Fact]
    public async Task GetTopUsers_TrimsSearchTextBeforeDispatch()
    {
        SearchQuery? capturedQuery = null;
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken>()))
            .Callback<SearchQuery, Action<SearchResponse>, SearchScope, int?, SearchOptions, CancellationToken>((query, _, _, _, _, _) => capturedQuery = query)
            .ReturnsAsync((Search)null);

        var controller = new MultiSourceController(
            Mock.Of<IMultiSourceDownloadService>(),
            soulseekClient.Object,
            Mock.Of<ITransferService>(),
            Mock.Of<ISourceDiscoveryService>(),
            Mock.Of<IContentVerificationService>());

        var result = await controller.GetTopUsers(" hello ");

        Assert.IsType<OkObjectResult>(result);
        Assert.NotNull(capturedQuery);
        Assert.Equal("hello", capturedQuery!.SearchText);
    }

    [Fact]
    public async Task GetTopUsers_WhenRequestAborts_PropagatesSearchCancellation()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                cancellation.Token))
            .Returns(Task.FromCanceled<Search>(cancellation.Token));
        var controller = new MultiSourceController(
            Mock.Of<IMultiSourceDownloadService>(),
            soulseekClient.Object,
            Mock.Of<ITransferService>(),
            Mock.Of<ISourceDiscoveryService>(),
            Mock.Of<IContentVerificationService>())
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext { RequestAborted = cancellation.Token },
            },
        };

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => controller.GetTopUsers("hello"));
    }

    [Fact]
    public async Task Search_TrimsSearchTextBeforeDispatch()
    {
        SearchQuery? capturedQuery = null;
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken>()))
            .Callback<SearchQuery, Action<SearchResponse>, SearchScope, int?, SearchOptions, CancellationToken>((query, _, _, _, _, _) => capturedQuery = query)
            .ReturnsAsync((Search)null);

        var controller = new MultiSourceController(
            Mock.Of<IMultiSourceDownloadService>(),
            soulseekClient.Object,
            Mock.Of<ITransferService>(),
            Mock.Of<ISourceDiscoveryService>(),
            Mock.Of<IContentVerificationService>());

        var result = await controller.Search(" hello ");

        Assert.IsType<OkObjectResult>(result);
        Assert.NotNull(capturedQuery);
        Assert.Equal("hello", capturedQuery!.SearchText);
    }

    [Fact]
    public async Task VerifySources_TrimsFilenameAndDeduplicatesUsernamesBeforeDispatch()
    {
        var multiSource = new Mock<IMultiSourceDownloadService>();
        multiSource
            .Setup(service => service.FindVerifiedSourcesAsync(
                "song.flac",
                1234,
                It.IsAny<string?>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(new ContentVerificationResult());

        var controller = new MultiSourceController(
            multiSource.Object,
            Mock.Of<ISoulseekClient>(),
            Mock.Of<ITransferService>(),
            Mock.Of<ISourceDiscoveryService>(),
            Mock.Of<IContentVerificationService>())
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext()
            }
        };

        var result = await controller.VerifySources(new VerifyRequest
        {
            Filename = " song.flac ",
            FileSize = 1234,
            Usernames = new List<string> { " alice ", "alice", " ", "bob " },
        });

        Assert.IsType<OkObjectResult>(result);
        multiSource.Verify(
            service => service.FindVerifiedSourcesAsync("song.flac", 1234, It.IsAny<string?>(), It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task Download_TrimsFilenameAndSourceFieldsBeforeDispatch()
    {
        var multiSource = new Mock<IMultiSourceDownloadService>();
        multiSource
            .Setup(service => service.DownloadAsync(
                It.IsAny<MultiSourceDownloadRequest>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(new MultiSourceDownloadResult { Success = true, Filename = "song.flac" });

        var controller = new MultiSourceController(
            multiSource.Object,
            Mock.Of<ISoulseekClient>(),
            Mock.Of<ITransferService>(),
            Mock.Of<ISourceDiscoveryService>(),
            Mock.Of<IContentVerificationService>())
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext()
            }
        };

        var result = await controller.Download(new DownloadRequest
        {
            Filename = " song.flac ",
            FileSize = 1234,
            ExpectedHash = " hash ",
            Sources = new List<SourceRequest>
            {
                new() { Username = " alice ", FullPath = " Music/song.flac ", ContentHash = " hash ", Method = VerificationMethod.None },
                new() { Username = "bob", FullPath = " ", ContentHash = " ", Method = VerificationMethod.None },
            },
        });

        Assert.IsType<OkObjectResult>(result);
        multiSource.Verify(
            service => service.DownloadAsync(
                It.Is<MultiSourceDownloadRequest>(request =>
                    request.Filename == "song.flac" &&
                    request.ExpectedHash == "hash" &&
                    request.Sources.Count == 2 &&
                    request.Sources[0].Username == "alice" &&
                    request.Sources[0].FullPath == "Music/song.flac" &&
                    request.Sources[0].ContentHash == "hash" &&
                    request.Sources[1].FullPath == "song.flac" &&
                    request.Sources[1].ContentHash == string.Empty),
                It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task GetTopUsers_WhenSearchThrows_DoesNotLeakExceptionMessage()
    {
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("sensitive detail"));

        var controller = new MultiSourceController(
            Mock.Of<IMultiSourceDownloadService>(),
            soulseekClient.Object,
            Mock.Of<ITransferService>(),
            Mock.Of<ISourceDiscoveryService>(),
            Mock.Of<IContentVerificationService>());

        var result = await controller.GetTopUsers("hello");

        var error = Assert.IsType<ObjectResult>(result);
        Assert.Equal(500, error.StatusCode);
        Assert.DoesNotContain("sensitive detail", error.Value?.ToString() ?? string.Empty);
        Assert.Contains("Search failed", error.Value?.ToString() ?? string.Empty);
    }

    [Fact]
    public async Task DownloadFile_WhenSearchThrows_DoesNotLeakExceptionMessage()
    {
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("sensitive detail"));

        var controller = new MultiSourceController(
            Mock.Of<IMultiSourceDownloadService>(),
            soulseekClient.Object,
            Mock.Of<ITransferService>(),
            Mock.Of<ISourceDiscoveryService>(),
            Mock.Of<IContentVerificationService>());

        var result = await controller.DownloadFile(new FileSourceRequest
        {
            Filename = "song.flac",
            Size = 1234,
        });

        var error = Assert.IsType<ObjectResult>(result);
        Assert.Equal(500, error.StatusCode);
        Assert.DoesNotContain("sensitive detail", error.Value?.ToString() ?? string.Empty);
        Assert.Contains("Search failed", error.Value?.ToString() ?? string.Empty);
    }

    [Fact]
    public async Task GetUserFiles_WhenUsernameIsMissingFromLastSearchResults_ReturnsSanitizedNotFound()
    {
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken>()))
            .Callback<SearchQuery, Action<SearchResponse>, SearchScope, int?, SearchOptions, CancellationToken>((_, handler, _, _, _, _) =>
            {
                handler(new SearchResponse(
                    "alice",
                    1000,
                    true,
                    0,
                    0,
                    new[]
                    {
                        new File(1, "Music/song.flac", 1234, string.Empty, Array.Empty<FileAttribute>()),
                    },
                    Array.Empty<File>()));
            })
            .ReturnsAsync((Search)null);

        var controller = new MultiSourceController(
            Mock.Of<IMultiSourceDownloadService>(),
            soulseekClient.Object,
            Mock.Of<ITransferService>(),
            Mock.Of<ISourceDiscoveryService>(),
            Mock.Of<IContentVerificationService>());

        var seedResult = await controller.GetTopUsers("song");
        Assert.IsType<OkObjectResult>(seedResult);

        var result = controller.GetUserFiles(" bob ");

        var notFound = Assert.IsType<NotFoundObjectResult>(result);
        Assert.Equal("User not found in last search results", notFound.Value);
    }

    [Fact]
    public async Task DownloadFile_WhenTooFewSources_ReturnsSanitizedBadRequest()
    {
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.SearchAsync(
                It.IsAny<SearchQuery>(),
                It.IsAny<Action<SearchResponse>>(),
                It.IsAny<SearchScope>(),
                It.IsAny<int?>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<CancellationToken>()))
            .Callback<SearchQuery, Action<SearchResponse>, SearchScope, int?, SearchOptions, CancellationToken>((_, handler, _, _, _, _) =>
            {
                handler(new SearchResponse(
                    "alice",
                    1000,
                    true,
                    0,
                    0,
                    new[]
                    {
                        new File(1, "Music/song.flac", 1234, string.Empty, Array.Empty<FileAttribute>()),
                    },
                    Array.Empty<File>()));
            })
            .ReturnsAsync((Search)null);

        var controller = new MultiSourceController(
            Mock.Of<IMultiSourceDownloadService>(),
            soulseekClient.Object,
            Mock.Of<ITransferService>(),
            Mock.Of<ISourceDiscoveryService>(),
            Mock.Of<IContentVerificationService>())
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext()
            }
        };

        var result = await controller.DownloadFile(new FileSourceRequest
        {
            Filename = "song.flac",
            Size = 1234,
        });

        var badRequest = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Equal("Not enough sources for multi-source download", badRequest.Value);
    }

    [Fact]
    public async Task SwarmDownload_WhenDownloadFails_DoesNotLeakUnderlyingError()
    {
        var multiSource = new Mock<IMultiSourceDownloadService>();
        multiSource
            .Setup(service => service.DownloadAsync(
                It.IsAny<MultiSourceDownloadRequest>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(new MultiSourceDownloadResult
            {
                Success = false,
                Filename = "song.flac",
                Error = "sensitive detail",
                TotalTimeMs = 1000,
                SourcesUsed = 2,
            });

        var discovery = new Mock<ISourceDiscoveryService>();
        discovery
            .Setup(service => service.GetSourcesBySize(1234, 100))
            .Returns(new List<DiscoveredSource>
            {
                new() { Username = "alice", Filename = "Music/song.flac", UploadSpeed = 1000, Size = 1234 },
                new() { Username = "bob", Filename = "Music/song.flac", UploadSpeed = 900, Size = 1234 },
            });

        var controller = new MultiSourceController(
            multiSource.Object,
            Mock.Of<ISoulseekClient>(),
            Mock.Of<ITransferService>(),
            discovery.Object,
            Mock.Of<IContentVerificationService>());

        var result = await controller.SwarmDownload(new SwarmDownloadRequest
        {
            Filename = "song.flac",
            Size = 1234,
            UseDiscoveryDb = true,
            SkipVerification = true,
        });

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = ok.Value?.ToString() ?? string.Empty;
        Assert.DoesNotContain("sensitive detail", payload);
        Assert.Contains("Swarm download failed", payload);
    }

    [Fact]
    public async Task SwarmDownload_WhenTooFewSources_ReturnsSanitizedBadRequest()
    {
        var discovery = new Mock<ISourceDiscoveryService>();
        discovery
            .Setup(service => service.GetSourcesBySize(1234, 100))
            .Returns(new List<DiscoveredSource>
            {
                new() { Username = "alice", Filename = "Music/song.flac", UploadSpeed = 1000, Size = 1234 },
            });

        var controller = new MultiSourceController(
            Mock.Of<IMultiSourceDownloadService>(),
            Mock.Of<ISoulseekClient>(),
            Mock.Of<ITransferService>(),
            discovery.Object,
            Mock.Of<IContentVerificationService>());

        var result = await controller.SwarmDownload(new SwarmDownloadRequest
        {
            Filename = "song.flac",
            Size = 1234,
            UseDiscoveryDb = true,
            SkipVerification = true,
        });

        var badRequest = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Equal("Not enough sources for swarm download", badRequest.Value);
    }
}
