// <copyright file="PrometheusServiceParsingTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Telemetry;

using System;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using slskd.Telemetry;
using Xunit;

public class PrometheusServiceParsingTests
{
    private sealed class StubPrometheusService : PrometheusService
    {
        private readonly string _text;

        public StubPrometheusService(string text) => _text = text;

        public override Task<string> GetMetricsAsString() => Task.FromResult(_text);
    }

    [Fact]
    public async Task GetMetricsAsObject_ParsesWellFormedMetric()
    {
        var text = "# HELP my_metric Some help text\n# TYPE my_metric gauge\nmy_metric 42\n";
        var service = new StubPrometheusService(text);

        var metrics = await service.GetMetricsAsObject();

        Assert.True(metrics.ContainsKey("my_metric"));
        Assert.Equal("gauge", metrics["my_metric"].Type);
        Assert.Equal("Some help text", metrics["my_metric"].Help);
    }

    [Fact]
    public async Task GetMetricsAsObject_AppliesIncludeAndExcludeToMetricFamilies()
    {
        const string text = "# HELP slskd_active Active work\n" +
            "# TYPE slskd_active gauge\n" +
            "slskd_active 2\n" +
            "# HELP slskd_secret Secret work\n" +
            "# TYPE slskd_secret counter\n" +
            "slskd_secret 9\n" +
            "# HELP node_available Node availability\n" +
            "# TYPE node_available gauge\n" +
            "node_available 1\n";
        var service = new StubPrometheusService(text);

        var metrics = await service.GetMetricsAsObject(
            new[] { new Regex("^slskd_", RegexOptions.CultureInvariant) },
            new[] { new Regex("secret$", RegexOptions.CultureInvariant) });

        Assert.Equal("slskd_active", Assert.Single(metrics).Key);
    }

    [Fact]
    public async Task GetMetricsAsString_FiltersWholeMetricFamiliesAndPreservesUnfilteredOutput()
    {
        const string text = "# HELP slskd_active Active work\n" +
            "# TYPE slskd_active gauge\n" +
            "slskd_active 2\n" +
            "# HELP slskd_secret Secret work\n" +
            "# TYPE slskd_secret counter\n" +
            "slskd_secret 9\n";
        var service = new StubPrometheusService(text);

        var unfiltered = await service.GetMetricsAsString();
        var filtered = await service.GetMetricsAsString(
            new[] { new Regex("^slskd_", RegexOptions.CultureInvariant) },
            new[] { new Regex("secret$", RegexOptions.CultureInvariant) });

        Assert.Equal(text, unfiltered);
        Assert.Contains("# HELP slskd_active", filtered, StringComparison.Ordinal);
        Assert.Contains("slskd_active 2", filtered, StringComparison.Ordinal);
        Assert.DoesNotContain("slskd_secret", filtered, StringComparison.Ordinal);
    }

    [Fact]
    public void MetricNameFilter_RejectsInvalidOrOversizedPatterns()
    {
        Assert.Contains(
            "not a valid regular expression",
            Assert.Throws<MetricsFilterValidationException>(
                () => PrometheusMetricFilter.Compile(new[] { "[" }, "include")).Message,
            StringComparison.Ordinal);
        Assert.Contains(
            "at most",
            Assert.Throws<MetricsFilterValidationException>(
                () => PrometheusMetricFilter.Compile(Enumerable.Repeat("x", PrometheusMetricFilter.MaximumPatternCount + 1).ToArray(), "exclude")).Message,
            StringComparison.Ordinal);
        Assert.Contains(
            "characters or fewer",
            Assert.Throws<MetricsFilterValidationException>(
                () => PrometheusMetricFilter.Compile(new[] { new string('x', PrometheusMetricFilter.MaximumPatternLength + 1) }, "include")).Message,
            StringComparison.Ordinal);
        Assert.Contains(
            "empty pattern",
            Assert.Throws<MetricsFilterValidationException>(
                () => PrometheusMetricFilter.Compile(new[] { string.Empty }, "exclude")).Message,
            StringComparison.Ordinal);
    }

    [Fact]
    public void MetricNameFilter_CompilesPatternsWithTheConfiguredTimeout()
    {
        var pattern = Assert.Single(PrometheusMetricFilter.Compile(new[] { "^slskd_" }, "include"));

        Assert.Equal(PrometheusMetricFilter.PatternTimeout, pattern.MatchTimeout);
    }

    [Fact]
    public async Task GetMetricsAsObject_HelpNotFollowedByType_DoesNotThrow()
    {
        // A HELP line followed directly by a short sample line (no TYPE) previously
        // threw ArgumentOutOfRangeException when Substring(7) ran past the line length.
        var text = "# HELP up The scrape target is up\nup 1\n";
        var service = new StubPrometheusService(text);

        var metrics = await service.GetMetricsAsObject();

        Assert.False(metrics.ContainsKey("up"));
    }

    [Theory]
    [InlineData("# HELP\n# TYPE\n")]
    [InlineData("# HELP \n# TYPE \n")]
    [InlineData("# HELP x\nfoo\n")]
    [InlineData("# HELP name help\n# TYP\n")]
    public async Task GetMetricsAsObject_MalformedInput_DoesNotThrow(string text)
    {
        var service = new StubPrometheusService(text);

        var metrics = await service.GetMetricsAsObject();

        Assert.Empty(metrics);
    }
}
