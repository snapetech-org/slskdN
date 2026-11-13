// <copyright file="HttpBackendTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

// HTTP Backend tests (SIMPLIFIED FOR SPEED)
namespace slskd.Tests.Unit.VirtualSoulfind.v2.Backends
{
    using System;
    using System.Collections.Generic;
    using System.Net;
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

    public class HttpBackendTests
    {
        [Fact]
        public void HttpBackend_HasCorrectType()
        {
            var (backend, httpClient) = CreateBackend();
            using var _ = httpClient;
            Assert.Equal(ContentBackendType.Http, backend.Type);
            Assert.Null(backend.SupportedDomain);
        }

        [Fact]
        public async Task FindCandidates_NoAllowlist_ReturnsEmpty()
        {
            var options = new HttpBackendOptions { DomainAllowlist = new List<string>() };
            var (backend, httpClient) = CreateBackend(options);
            using var _ = httpClient;
            var itemId = ContentItemId.NewId();

            var candidates = await backend.FindCandidatesAsync(itemId, CancellationToken.None);

            Assert.Empty(candidates);
        }

        [Fact]
        public async Task ValidateCandidate_RejectsNonHttp()
        {
            var (backend, httpClient) = CreateBackend();
            using var _ = httpClient;
            var candidate = new SourceCandidate
            {
                Id = Guid.NewGuid().ToString(),
                ItemId = ContentItemId.NewId(),
                Backend = ContentBackendType.MeshDht,
                BackendRef = "mesh:node123",
                TrustScore = 0.7f,
                ExpectedQuality = 0.8f,
            };

            var result = await backend.ValidateCandidateAsync(candidate, CancellationToken.None);

            Assert.False(result.IsValid);
            Assert.Contains("Not an HTTP", result.InvalidityReason);
        }

        [Fact]
        public async Task ValidateCandidate_RejectsInvalidUrl()
        {
            var (backend, httpClient) = CreateBackend();
            using var _ = httpClient;
            var candidate = new SourceCandidate
            {
                Id = Guid.NewGuid().ToString(),
                ItemId = ContentItemId.NewId(),
                Backend = ContentBackendType.Http,
                BackendRef = "not-a-url",
                TrustScore = 0.7f,
                ExpectedQuality = 0.8f,
            };

            var result = await backend.ValidateCandidateAsync(candidate, CancellationToken.None);

            Assert.False(result.IsValid);
            Assert.Contains("Invalid URL", result.InvalidityReason);
        }

        [Fact]
        public async Task ValidateCandidate_RejectsNonAllowlistedDomain()
        {
            var options = new HttpBackendOptions
            {
                DomainAllowlist = new List<string> { "allowed.com" }
            };
            var (backend, httpClient) = CreateBackend(options);
            using var _ = httpClient;
            var candidate = new SourceCandidate
            {
                Id = Guid.NewGuid().ToString(),
                ItemId = ContentItemId.NewId(),
                Backend = ContentBackendType.Http,
                BackendRef = "https://evil.com/file.flac",
                TrustScore = 0.7f,
                ExpectedQuality = 0.8f,
            };

            var result = await backend.ValidateCandidateAsync(candidate, CancellationToken.None);

            Assert.False(result.IsValid);
            Assert.Contains("not in allowlist", result.InvalidityReason);
        }

        [Fact]
        public async Task ValidateCandidate_WhenHttpClientThrows_ReturnsSanitizedError()
        {
            var handler = new ThrowingHttpMessageHandler(new HttpRequestException("sensitive\r\ndetail"));
            var logger = new CapturingLogger<HttpBackend>();
            var options = new HttpBackendOptions { DomainAllowlist = new List<string> { "93.184.216.34" } };
            var (backend, httpClient) = CreateBackend(options, handler, logger);
            using var _ = httpClient;
            var candidate = new SourceCandidate
            {
                Id = "candidate\r\ninjected: true",
                ItemId = ContentItemId.NewId(),
                Backend = ContentBackendType.Http,
                BackendRef = "https://93.184.216.34/file.flac",
                TrustScore = 0.7f,
                ExpectedQuality = 0.8f,
            };

            var result = await backend.ValidateCandidateAsync(candidate, CancellationToken.None);

            Assert.False(result.IsValid);
            Assert.Equal("HTTP validation failed", result.InvalidityReason);
            Assert.DoesNotContain("sensitive", result.InvalidityReason);
            var entry = Assert.Single(logger.Entries);
            Assert.Contains("candidate\\r\\ninjected: true", entry.Message);
            Assert.Contains("sensitive\\r\\ndetail", entry.Message);
            Assert.Null(entry.Exception);
            Assert.DoesNotContain("\r\n", entry.Message);
        }

        private (HttpBackend Backend, HttpClient HttpClient) CreateBackend(
            HttpBackendOptions options = null,
            HttpMessageHandler handler = null,
            ILogger<HttpBackend> logger = null)
        {
            options ??= new HttpBackendOptions
            {
                DomainAllowlist = new List<string> { "allowed.com" }
            };

            // IHttpClientFactory.CreateClient (and its parameterless extension) must return an HttpClient.
            // Use a test double because Moq cannot setup extension methods.
            var httpClient = handler == null
                ? new HttpClient(new StubHttpMessageHandler())
                : new HttpClient(handler);
            var httpFactory = new TestHttpClientFactory(httpClient);

            var optionsMonitor = new Mock<IOptionsMonitor<HttpBackendOptions>>();
            optionsMonitor.Setup(o => o.CurrentValue).Returns(options);

            var registry = new InMemorySourceRegistry();

            return (new HttpBackend(httpFactory, optionsMonitor.Object, registry, logger), httpClient);
        }
    }

    internal sealed class TestHttpClientFactory : IHttpClientFactory
    {
        private readonly HttpClient _client;
        public TestHttpClientFactory(HttpClient client) => _client = client;
        public HttpClient CreateClient(string name) => _client;
    }

    internal sealed class StubHttpMessageHandler : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new ByteArrayContent(new byte[1024]),
            });
        }
    }

    internal sealed class ThrowingHttpMessageHandler : HttpMessageHandler
    {
        private readonly Exception _exception;

        public ThrowingHttpMessageHandler(Exception exception)
        {
            _exception = exception;
        }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            return Task.FromException<HttpResponseMessage>(_exception);
        }
    }
}
