// <copyright file="MetricsControllerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Telemetry;

using System.Collections.Generic;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using slskd;
using slskd.Telemetry;
using Xunit;

public class MetricsControllerTests
{
    [Fact]
    public async Task Get_WithParameterizedJsonAcceptHeader_ReturnsJson()
    {
        var controller = new MetricsController(CreateTelemetryService(new StubPrometheusService()));
        controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext(),
        };
        controller.Request.Headers.Accept = "application/json; charset=utf-8";

        var result = await controller.Get(null, null);

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public async Task Get_WhenMetricsProviderThrows_ReturnsSanitized500()
    {
        var controller = new MetricsController(CreateTelemetryService(new ThrowingPrometheusService()));
        controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext(),
        };

        var result = await controller.Get(null, null);

        var objectResult = Assert.IsType<ObjectResult>(result);
        Assert.Equal(500, objectResult.StatusCode);
        Assert.Equal("Failed to fetch metrics", objectResult.Value);
    }

    [Fact]
    public async Task Get_WithIncludeAndExcludeFilters_ReturnsFilteredJsonFamilies()
    {
        var controller = new MetricsController(CreateTelemetryService(new FilterablePrometheusService()));
        controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext(),
        };
        controller.Request.Headers.Accept = "application/json";

        var result = await controller.Get(new[] { "^slskd_" }, new[] { "secret$" });

        var objectResult = Assert.IsType<OkObjectResult>(result);
        var metrics = Assert.IsType<Dictionary<string, PrometheusMetric>>(objectResult.Value);
        Assert.Equal("slskd_active", Assert.Single(metrics).Key);
    }

    [Fact]
    public async Task Get_WithIncludeOnlyFilter_DoesNotUseUnfilteredLegacyOverride()
    {
        var controller = new MetricsController(CreateTelemetryService(new StubPrometheusService()));
        controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext(),
        };
        controller.Request.Headers.Accept = "application/json";

        var result = await controller.Get(new[] { "does_not_match" }, null);

        var objectResult = Assert.IsType<OkObjectResult>(result);
        Assert.Empty(Assert.IsType<Dictionary<string, PrometheusMetric>>(objectResult.Value));
    }

    [Fact]
    public async Task Get_WithInvalidFilter_ReturnsClearBadRequest()
    {
        var controller = new MetricsController(CreateTelemetryService(new StubPrometheusService()));
        controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext(),
        };

        var result = await controller.Get(new[] { "[" }, null);

        var badRequest = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Contains("not a valid regular expression", Assert.IsType<string>(badRequest.Value), StringComparison.Ordinal);
    }

    [Fact]
    public async Task Get_WhenFilterTimesOut_ReturnsBadRequest()
    {
        var controller = new MetricsController(CreateTelemetryService(new TimeoutPrometheusService()));
        controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext(),
        };

        var result = await controller.Get(new[] { "^(a|aa)+$" }, null);

        var badRequest = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Contains("evaluation time limit", Assert.IsType<string>(badRequest.Value), StringComparison.Ordinal);
    }

    private static TelemetryService CreateTelemetryService(PrometheusService prometheusService)
    {
        return new TelemetryService(
            prometheusService,
            new ReportsService(new ConnectionStringDictionary(new Dictionary<Database, ConnectionString>())));
    }

    private sealed class StubPrometheusService : PrometheusService
    {
        public override Task<Dictionary<string, PrometheusMetric>> GetMetricsAsObject(IEnumerable<System.Text.RegularExpressions.Regex>? include = null)
        {
            return Task.FromResult(new Dictionary<string, PrometheusMetric> { ["slskd_test"] = new() { Name = "slskd_test" } });
        }

        public override Task<string> GetMetricsAsString()
        {
            return Task.FromResult(
                "# HELP slskd_test Test metric\n" +
                "# TYPE slskd_test gauge\n" +
                "slskd_test 1\n");
        }
    }

    private sealed class FilterablePrometheusService : PrometheusService
    {
        public override Task<string> GetMetricsAsString()
        {
            return Task.FromResult(
                "# HELP slskd_active Active work\n" +
                "# TYPE slskd_active gauge\n" +
                "slskd_active 2\n" +
                "# HELP slskd_secret Secret work\n" +
                "# TYPE slskd_secret counter\n" +
                "slskd_secret 9\n");
        }
    }

    private sealed class TimeoutPrometheusService : PrometheusService
    {
        public override Task<string> GetMetricsAsString()
        {
            var metricName = new string('a', 10000) + "!";
            return Task.FromResult($"# HELP {metricName} Test metric\n# TYPE {metricName} gauge\n{metricName} 1\n");
        }
    }

    private sealed class ThrowingPrometheusService : PrometheusService
    {
        public override Task<string> GetMetricsAsString()
        {
            throw new InvalidOperationException("raw details should not escape");
        }
    }
}
