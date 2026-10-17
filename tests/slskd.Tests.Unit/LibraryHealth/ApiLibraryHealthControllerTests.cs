// <copyright file="ApiLibraryHealthControllerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.LibraryHealth;

using System;
using System.Reflection;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using slskd.LibraryHealth;
using ApiLibraryHealthController = slskd.LibraryHealth.API.LibraryHealthController;
using Xunit;

public class ApiLibraryHealthControllerTests
{
    [Theory]
    [InlineData(nameof(ApiLibraryHealthController.StartScan))]
    [InlineData(nameof(ApiLibraryHealthController.GetScanStatus))]
    [InlineData(nameof(ApiLibraryHealthController.GetSummary))]
    [InlineData(nameof(ApiLibraryHealthController.GetDashboard))]
    [InlineData(nameof(ApiLibraryHealthController.GetIssues))]
    public void PathBearingScanActions_RequireAdministrator(string actionName)
    {
        var action = typeof(ApiLibraryHealthController).GetMethod(actionName)!;
        var authorize = Assert.Single(action.GetCustomAttributes<AuthorizeAttribute>(inherit: true));

        Assert.Equal(AuthPolicy.Any, authorize.Policy);
        Assert.Equal(AuthRole.AdministratorOnly, authorize.Roles);
    }

    [Fact]
    public async Task StartScan_WhenAnotherScanRuns_ReturnsConflict()
    {
        var healthService = new Mock<ILibraryHealthService>();
        healthService.Setup(service => service.StartScanAsync(It.IsAny<LibraryHealthScanRequest>(), default))
            .ThrowsAsync(new LibraryHealthScanAlreadyRunningException("scan-running"));
        var controller = new ApiLibraryHealthController(
            healthService.Object,
            NullLogger<ApiLibraryHealthController>.Instance);

        var result = await controller.StartScan(new LibraryHealthScanRequest(), default);

        var conflict = Assert.IsType<ConflictObjectResult>(result.Result);
        Assert.Contains("already running", conflict.Value?.ToString(), StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task StartScan_WhenSpectralAnalysisIsDisabled_ReturnsBadRequestWithTheSetting()
    {
        var healthService = new Mock<ILibraryHealthService>();
        healthService.Setup(service => service.StartScanAsync(It.IsAny<LibraryHealthScanRequest>(), default))
            .ThrowsAsync(new SpectralAnalysisUnavailableException());
        var controller = new ApiLibraryHealthController(
            healthService.Object,
            NullLogger<ApiLibraryHealthController>.Instance);

        var result = await controller.StartScan(new LibraryHealthScanRequest { IncludeSpectralAnalysis = true }, default);

        var badRequest = Assert.IsType<BadRequestObjectResult>(result.Result);
        Assert.Contains("audio.spectral_analysis.enabled", badRequest.Value?.ToString(), StringComparison.Ordinal);
    }

    [Fact]
    public async Task GetScanStatus_WhenScanMissing_ReturnsSanitizedNotFound()
    {
        var healthService = new Mock<ILibraryHealthService>();
        healthService
            .Setup(service => service.GetScanStatusAsync("scan-123", default))
            .ReturnsAsync((LibraryHealthScan?)null);

        var controller = new ApiLibraryHealthController(
            healthService.Object,
            NullLogger<ApiLibraryHealthController>.Instance);

        var result = await controller.GetScanStatus("scan-123", default);

        var notFound = Assert.IsType<NotFoundObjectResult>(result.Result);
        Assert.Contains("Scan not found", notFound.Value?.ToString() ?? string.Empty);
        Assert.DoesNotContain("scan-123", notFound.Value?.ToString() ?? string.Empty, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task CreateRemediationJob_ReturnsSanitizedSuccessMessage()
    {
        var healthService = new Mock<ILibraryHealthService>();
        healthService
            .Setup(service => service.CreateRemediationJobAsync(It.IsAny<List<string>>(), default))
            .ReturnsAsync("job-123");

        var controller = new ApiLibraryHealthController(
            healthService.Object,
            NullLogger<ApiLibraryHealthController>.Instance);

        var result = await controller.CreateRemediationJob(
            new slskd.LibraryHealth.API.RemediationRequest
            {
                IssueIds = new List<string> { "issue-1", "issue-2" }
            },
            default);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var response = Assert.IsType<slskd.LibraryHealth.API.RemediationResponse>(ok.Value);
        Assert.Equal("job-123", response.JobId);
        Assert.Equal("Remediation job created", response.Message);
    }

    [Theory]
    [InlineData(-1, 0)]
    [InlineData(0, 0)]
    [InlineData(251, 0)]
    [InlineData(25, -1)]
    public async Task GetIssues_RejectsUnboundedPagination(int limit, int offset)
    {
        var healthService = new Mock<ILibraryHealthService>();
        var controller = new ApiLibraryHealthController(
            healthService.Object,
            NullLogger<ApiLibraryHealthController>.Instance);

        var result = await controller.GetIssues(
            new LibraryHealthIssueFilter { Limit = limit, Offset = offset },
            default);

        Assert.IsType<BadRequestObjectResult>(result.Result);
        healthService.Verify(
            service => service.GetIssuePageAsync(It.IsAny<LibraryHealthIssueFilter>(), default),
            Times.Never);
    }

    [Fact]
    public async Task GetIssues_ReturnsAuthoritativeFilteredTotal()
    {
        var healthService = new Mock<ILibraryHealthService>();
        healthService
            .Setup(service => service.GetIssuePageAsync(It.IsAny<LibraryHealthIssueFilter>(), default))
            .ReturnsAsync(new LibraryIssuePage
            {
                Issues = new List<LibraryIssue> { new() { IssueId = "issue-1" } },
                TotalCount = 150,
            });
        var controller = new ApiLibraryHealthController(
            healthService.Object,
            NullLogger<ApiLibraryHealthController>.Instance);

        var result = await controller.GetIssues(new LibraryHealthIssueFilter { Limit = 1 }, default);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var response = Assert.IsType<slskd.LibraryHealth.API.IssuesResponse>(ok.Value);
        Assert.Single(response.Issues);
        Assert.Equal(150, response.TotalCount);
    }

    [Fact]
    public async Task GetDashboard_ReturnsOneBoundedSnapshot()
    {
        var healthService = new Mock<ILibraryHealthService>();
        healthService
            .Setup(service => service.GetDashboardAsync("/music", 10, 100, default))
            .ReturnsAsync(new LibraryHealthDashboard
            {
                Summary = new LibraryHealthSummary { LibraryPath = "/music", TotalIssues = 150 },
                TotalIssues = 150,
            });
        var controller = new ApiLibraryHealthController(
            healthService.Object,
            NullLogger<ApiLibraryHealthController>.Instance);

        var result = await controller.GetDashboard("/music", 10, 100, default);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var dashboard = Assert.IsType<LibraryHealthDashboard>(ok.Value);
        Assert.Equal(150, dashboard.TotalIssues);
        healthService.Verify(
            service => service.GetDashboardAsync("/music", 10, 100, default),
            Times.Once);
    }
}
