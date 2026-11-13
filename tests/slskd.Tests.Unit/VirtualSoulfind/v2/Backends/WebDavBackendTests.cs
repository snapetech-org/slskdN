// <copyright file="WebDavBackendTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.VirtualSoulfind.v2.Backends;

using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Moq;
using slskd.VirtualSoulfind.Core;
using slskd.VirtualSoulfind.v2.Backends;
using slskd.VirtualSoulfind.v2.Sources;
using Xunit;

public class WebDavBackendTests
{
    [Fact]
    public async Task ValidateCandidate_WhenHttpClientThrows_ReturnsSanitizedError()
    {
        var handler = new ThrowingHttpMessageHandler(new HttpRequestException("sensitive\r\ndetail"));
        var logger = new CapturingLogger<WebDavBackend>();
        var options = new WebDavBackendOptions { Enabled = true, DomainAllowlist = new List<string> { "93.184.216.34" } };
        var (backend, httpClient) = CreateBackend(options: options, handler: handler, logger: logger);
        using var _ = httpClient;
        var candidate = new SourceCandidate
        {
            Id = "candidate\r\ninjected: true",
            ItemId = ContentItemId.NewId(),
            Backend = ContentBackendType.WebDav,
            BackendRef = "https://93.184.216.34/file.flac",
            TrustScore = 0.7f,
            ExpectedQuality = 0.8f,
        };

        var result = await backend.ValidateCandidateAsync(candidate, CancellationToken.None);

        Assert.False(result.IsValid);
        Assert.Equal("WebDAV validation failed", result.InvalidityReason);
        Assert.DoesNotContain("sensitive", result.InvalidityReason);
        var entry = Assert.Single(logger.Entries);
        Assert.Contains("candidate\\r\\ninjected: true", entry.Message);
        Assert.Contains("sensitive\\r\\ndetail", entry.Message);
        Assert.Null(entry.Exception);
        Assert.DoesNotContain("\r\n", entry.Message);
    }

    private static (WebDavBackend Backend, HttpClient HttpClient) CreateBackend(
        WebDavBackendOptions options = null,
        HttpMessageHandler handler = null,
        ILogger<WebDavBackend> logger = null)
    {
        options ??= new WebDavBackendOptions
        {
            Enabled = true,
            DomainAllowlist = new List<string> { "allowed.com" },
        };

        var httpClient = handler == null
            ? new HttpClient(new slskd.Tests.Unit.VirtualSoulfind.v2.Backends.StubHttpMessageHandler())
            : new HttpClient(handler);
        var httpFactory = new slskd.Tests.Unit.VirtualSoulfind.v2.Backends.TestHttpClientFactory(httpClient);
        var optionsMonitor = new Mock<IOptionsMonitor<WebDavBackendOptions>>();
        var sourceRegistry = new Mock<ISourceRegistry>();
        optionsMonitor.Setup(o => o.CurrentValue).Returns(options);

        return (new WebDavBackend(httpFactory, optionsMonitor.Object, sourceRegistry.Object, logger), httpClient);
    }
}
