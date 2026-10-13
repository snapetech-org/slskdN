// <copyright file="TelemetryControllerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Telemetry;

using System.Collections.Generic;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using slskd;
using slskd.Telemetry;
using Xunit;

public class TelemetryControllerTests
{
    [Fact]
    public async Task Get_WithParameterizedJsonAcceptHeader_ReturnsJson()
    {
        var controller = new TelemetryController(CreateTelemetryService(new StubPrometheusService()));
        controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext(),
        };
        controller.Request.Headers.Accept = "application/json; charset=utf-8";

        var result = await controller.Get(null, null);

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public async Task Get_WithIncludeAndExcludeFilters_ReturnsFilteredTextFamilies()
    {
        var controller = new TelemetryController(CreateTelemetryService(new StubPrometheusService()));
        controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext(),
        };

        var result = await controller.Get(new[] { "^slskd_" }, new[] { "secret$" });

        var content = Assert.IsType<ContentResult>(result);
        Assert.Contains("# HELP slskd_test", content.Content, StringComparison.Ordinal);
        Assert.Contains("slskd_test 1", content.Content, StringComparison.Ordinal);
        Assert.DoesNotContain("slskd_secret", content.Content, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Get_WithIncludeOnlyFilter_ReturnsFilteredJson()
    {
        var controller = new TelemetryController(CreateTelemetryService(new StubPrometheusService()));
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
        var controller = new TelemetryController(CreateTelemetryService(new StubPrometheusService()));
        controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext(),
        };

        var result = await controller.Get(null, new[] { "[" });

        var badRequest = Assert.IsType<BadRequestObjectResult>(result);
        Assert.Contains("not a valid regular expression", Assert.IsType<string>(badRequest.Value), StringComparison.Ordinal);
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
                "slskd_test 1\n" +
                "# HELP slskd_secret Secret metric\n" +
                "# TYPE slskd_secret counter\n" +
                "slskd_secret 9\n");
        }
    }
}
