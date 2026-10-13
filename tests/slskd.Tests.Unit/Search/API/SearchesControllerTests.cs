// <copyright file="SearchesControllerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Search.API;

using System.Linq;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using Moq;
using slskd.Search;
using slskd.Search.API;
using Soulseek;
using Xunit;

public class SearchesControllerTests
{
    [Fact]
    public async Task Post_WithNullRequest_ReturnsBadRequest()
    {
        var controller = CreateController();

        var result = await controller.Post(null!);

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task Post_TrimsSearchTextAndProvidersBeforeDispatch()
    {
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<List<string>>()))
            .ReturnsAsync(new slskd.Search.Search { Id = Guid.NewGuid(), SearchText = "hello world" });

        var controller = CreateController(searchService);

        var result = await controller.Post(new SearchRequest
        {
            AcquisitionProfile = " conservative-network ",
            SearchText = "  hello world  ",
            Providers = new List<string> { " pod ", "pod", " scene ", " " }
        });

        Assert.IsType<OkObjectResult>(result);
        searchService.Verify(
            service => service.StartAsync(
                It.IsAny<Guid>(),
                It.Is<SearchQuery>(query => query.Terms.SequenceEqual(new[] { "hello", "world" })),
                It.IsAny<SearchScope>(),
                It.IsAny<SearchOptions>(),
                It.Is<List<string>>(providers => providers.SequenceEqual(new[] { "pod", "scene" }))),
            Times.Once);
    }

    [Fact]
    public async Task Post_WithUnknownAcquisitionProfile_ReturnsBadRequest()
    {
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<List<string>>()))
            .ReturnsAsync(new slskd.Search.Search { Id = Guid.NewGuid(), SearchText = "hello" });

        var controller = CreateController(searchService);

        var result = await controller.Post(new SearchRequest
        {
            AcquisitionProfile = "unknown-profile",
            SearchText = "hello",
        });

        var badRequest = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Contains("AcquisitionProfile", badRequest.Value?.ToString() ?? string.Empty);
        searchService.Verify(
            service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<List<string>>()),
            Times.Never);
    }

    [Fact]
    public async Task Post_ConvertsSearchTimeoutSecondsToSoulseekMilliseconds()
    {
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<List<string>>()))
            .ReturnsAsync(new slskd.Search.Search { Id = Guid.NewGuid(), SearchText = "hello" });

        var controller = CreateController(searchService);

        var result = await controller.Post(new SearchRequest
        {
            SearchText = "hello",
            SearchTimeout = 10,
        });

        Assert.IsType<OkObjectResult>(result);
        searchService.Verify(
            service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.Is<SearchOptions>(options => options.SearchTimeout == 10000),
                It.IsAny<List<string>>()),
            Times.Once);
    }

    [Fact]
    public async Task Post_AppliesAcquisitionProfileDefaultsBeforeDispatch()
    {
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<List<string>>()))
            .ReturnsAsync(new slskd.Search.Search { Id = Guid.NewGuid(), SearchText = "rare track" });

        var controller = CreateController(searchService);

        var result = await controller.Post(new SearchRequest
        {
            AcquisitionProfile = "rare-hunt",
            SearchText = "rare track",
        });

        Assert.IsType<OkObjectResult>(result);
        searchService.Verify(
            service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.Is<SearchOptions>(options =>
                    options.SearchTimeout == 30000 &&
                    options.ResponseLimit == 250 &&
                    options.FileLimit == 25000),
                It.IsAny<List<string>>()),
            Times.Once);
    }

    [Fact]
    public async Task Post_ExplicitSearchOptionsOverrideAcquisitionProfileDefaults()
    {
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<List<string>>()))
            .ReturnsAsync(new slskd.Search.Search { Id = Guid.NewGuid(), SearchText = "quick track" });

        var controller = CreateController(searchService);

        var result = await controller.Post(new SearchRequest
        {
            AcquisitionProfile = "fast-good-enough",
            FileLimit = 8,
            ResponseLimit = 7,
            SearchText = "quick track",
            SearchTimeout = 12,
        });

        Assert.IsType<OkObjectResult>(result);
        searchService.Verify(
            service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.Is<SearchOptions>(options =>
                    options.SearchTimeout == 12000 &&
                    options.ResponseLimit == 7 &&
                    options.FileLimit == 8),
                It.IsAny<List<string>>()),
            Times.Once);
    }

    [Fact]
    public async Task GetAll_WithNegativeLimit_ReturnsBadRequest()
    {
        var controller = CreateController();

        var result = await controller.GetAll(limit: -1, offset: 0);

        Assert.IsType<BadRequestResult>(result);
    }

    [Fact]
    public async Task GetAll_WithIncompleteOrMixedContinuation_ReturnsBadRequest()
    {
        var controller = CreateController();
        var cursorId = Guid.NewGuid();
        var cursorTime = DateTimeOffset.UtcNow;

        Assert.IsType<BadRequestResult>(await controller.GetAll(
            limit: 250,
            afterStartedAt: cursorTime));
        Assert.IsType<BadRequestResult>(await controller.GetAll(
            limit: 250,
            offset: 1,
            afterStartedAt: cursorTime,
            afterId: cursorId));
    }

    [Fact]
    public async Task GetAll_WithDefaultLimit_AppliesConservativeServerCap()
    {
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.ListAsync(null, 500, 0))
            .ReturnsAsync(new List<slskd.Search.Search>());

        var controller = CreateController(searchService);

        var result = await controller.GetAll(limit: 0, offset: 0);

        Assert.IsType<OkObjectResult>(result);
        searchService.Verify(service => service.ListAsync(null, 500, 0), Times.Once);
    }

    [Fact]
    public async Task GetAll_ForwardsSourceAndOffsetForPageRequests()
    {
        var page = new List<slskd.Search.Search>
        {
            new() { Id = Guid.NewGuid(), SearchText = "older search" },
        };
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.ListAsync(null, 250, 500, "wishlist"))
            .ReturnsAsync(page);
        var controller = CreateController(searchService);

        var result = await controller.GetAll(limit: 250, offset: 500, source: "wishlist");

        Assert.Same(page, Assert.IsType<OkObjectResult>(result).Value);
        searchService.Verify(service => service.ListAsync(null, 250, 500, "wishlist"), Times.Once);
    }

    [Fact]
    public async Task GetAll_ForwardsTimestampAndIdForStableContinuation()
    {
        var cursorTime = new DateTime(2026, 8, 20, 12, 0, 0, DateTimeKind.Utc);
        var cursorId = Guid.NewGuid();
        var page = new List<slskd.Search.Search>();
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.ListAsync(null, 250, 0, "wishlist", cursorTime, cursorId))
            .ReturnsAsync(page);
        var controller = CreateController(searchService);

        var result = await controller.GetAll(
            limit: 250,
            source: "wishlist",
            afterStartedAt: new DateTimeOffset(cursorTime),
            afterId: cursorId);

        Assert.Same(page, Assert.IsType<OkObjectResult>(result).Value);
        searchService.Verify(
            service => service.ListAsync(null, 250, 0, "wishlist", cursorTime, cursorId),
            Times.Once);
    }

    [Fact]
    public async Task Post_WhenSearchServiceThrowsArgumentException_DoesNotLeakExceptionMessage()
    {
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<List<string>>()))
            .ThrowsAsync(new ArgumentException("sensitive detail"));

        var controller = CreateController(searchService);

        var result = await controller.Post(new SearchRequest { SearchText = "hello" });

        var badRequest = Assert.IsType<BadRequestObjectResult>(result);
        Assert.DoesNotContain("sensitive detail", badRequest.Value?.ToString() ?? string.Empty);
        Assert.Equal("Invalid search request", badRequest.Value);
    }

    [Fact]
    public async Task Post_WhenSearchServiceThrowsDuplicateToken_DoesNotLeakExceptionMessage()
    {
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<List<string>>()))
            .ThrowsAsync(new DuplicateTokenException("sensitive detail"));

        var controller = CreateController(searchService);

        var result = await controller.Post(new SearchRequest { SearchText = "hello" });

        var conflict = Assert.IsType<ConflictObjectResult>(result);
        Assert.DoesNotContain("sensitive detail", conflict.Value?.ToString() ?? string.Empty);
        Assert.Equal("A search with this ID is already in progress", conflict.Value);
    }

    [Fact]
    public async Task Post_WhenSearchServiceThrowsUnexpectedException_DoesNotLeakExceptionMessage()
    {
        var searchService = new Mock<ISearchService>();
        searchService
            .Setup(service => service.StartAsync(
                It.IsAny<Guid>(),
                It.IsAny<SearchQuery>(),
                It.IsAny<SearchScope>(),
                It.IsAny<SearchOptions>(),
                It.IsAny<List<string>>()))
            .ThrowsAsync(new InvalidOperationException("sensitive detail"));

        var controller = CreateController(searchService);

        var result = await controller.Post(new SearchRequest { SearchText = "hello" });

        var error = Assert.IsType<ConflictObjectResult>(result);
        Assert.DoesNotContain("sensitive detail", error.Value?.ToString() ?? string.Empty);
        Assert.Equal("Search could not be started", error.Value);
    }

    private static SearchesController CreateController(Mock<ISearchService>? searchService = null)
    {
        return new SearchesController(
            (searchService ?? new Mock<ISearchService>()).Object,
            Mock.Of<IOptionsSnapshot<slskd.Options>>());
    }
}
