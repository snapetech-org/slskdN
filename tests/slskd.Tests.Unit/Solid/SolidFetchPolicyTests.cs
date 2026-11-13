// <copyright file="SolidFetchPolicyTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Solid;

using System;
using System.Net;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Moq;
using slskd;
using slskd.Solid;
using TestOptionsMonitor = slskd.Tests.Unit.TestOptionsMonitor<slskd.Options>;
using Xunit;

public class SolidFetchPolicyTests
{
    private readonly Mock<ILogger<SolidFetchPolicy>> _loggerMock = new();
    private IOptionsMonitor<slskd.Options> _options;

    private SolidFetchPolicy CreatePolicy()
    {
        return new SolidFetchPolicy(
            _options,
            _loggerMock.Object,
            static (_, _) => Task.FromResult(new[] { IPAddress.Parse("93.184.216.34") }));
    }

    [Fact]
    public async Task ValidateAsync_EmptyAllowedHosts_Throws()
    {
        _options = new TestOptionsMonitor(new slskd.Options
        {
            Solid = new slskd.Options.SolidOptions
            {
                AllowedHosts = Array.Empty<string>()
            }
        });
        var policy = CreatePolicy();
        var uri = new Uri("https://example.com/profile");

        await Assert.ThrowsAsync<InvalidOperationException>(() => policy.ValidateAsync(uri, CancellationToken.None));
    }

    [Fact]
    public async Task ValidateAsync_HostNotInAllowedHosts_Throws()
    {
        _options = new TestOptionsMonitor(new slskd.Options
        {
            Solid = new slskd.Options.SolidOptions
            {
                AllowedHosts = new[] { "allowed.example" }
            }
        });
        var policy = CreatePolicy();
        var uri = new Uri("https://notallowed.example/profile");

        var ex = await Assert.ThrowsAsync<InvalidOperationException>(() => policy.ValidateAsync(uri, CancellationToken.None));
        Assert.Contains("not in AllowedHosts", ex.Message);
    }

    [Fact]
    public async Task ValidateAsync_HostInAllowedHosts_Succeeds()
    {
        _options = new TestOptionsMonitor(new slskd.Options
        {
            Solid = new slskd.Options.SolidOptions
            {
                AllowedHosts = new[] { "93.184.216.34" }
            }
        });
        var policy = CreatePolicy();
        var uri = new Uri("https://93.184.216.34/profile");

        await policy.ValidateAsync(uri, CancellationToken.None);
    }

    [Fact]
    public async Task ValidateAsync_HttpWhenAllowInsecureHttpFalse_Throws()
    {
        _options = new TestOptionsMonitor(new slskd.Options
        {
            Solid = new slskd.Options.SolidOptions
            {
                AllowedHosts = new[] { "93.184.216.34" },
                AllowInsecureHttp = false
            }
        });
        var policy = CreatePolicy();
        var uri = new Uri("http://93.184.216.34/profile");

        var ex = await Assert.ThrowsAsync<InvalidOperationException>(() => policy.ValidateAsync(uri, CancellationToken.None));
        Assert.Contains("only https:// allowed", ex.Message);
    }

    [Fact]
    public async Task ValidateAsync_HttpWhenAllowInsecureHttpTrue_Succeeds()
    {
        _options = new TestOptionsMonitor(new slskd.Options
        {
            Solid = new slskd.Options.SolidOptions
            {
                AllowedHosts = new[] { "93.184.216.34" },
                AllowInsecureHttp = true
            }
        });
        var policy = CreatePolicy();
        var uri = new Uri("http://93.184.216.34/profile");

        await policy.ValidateAsync(uri, CancellationToken.None);
    }

    [Fact]
    public async Task ValidateAsync_Localhost_Throws()
    {
        _options = new TestOptionsMonitor(new slskd.Options
        {
            Solid = new slskd.Options.SolidOptions
            {
                AllowedHosts = new[] { "localhost" }
            }
        });
        var policy = CreatePolicy();
        var uri = new Uri("https://localhost/profile");

        var ex = await Assert.ThrowsAsync<InvalidOperationException>(() => policy.ValidateAsync(uri, CancellationToken.None));
        Assert.Contains("localhost/.local not allowed", ex.Message);
    }

    [Fact]
    public async Task ValidateAsync_Localhost_WhenAllowLocalhostForWebIdTrue_Succeeds()
    {
        _options = new TestOptionsMonitor(new slskd.Options
        {
            Solid = new slskd.Options.SolidOptions
            {
                AllowedHosts = new[] { "localhost" },
                AllowLocalhostForWebId = true,
                AllowInsecureHttp = true
            }
        });
        var policy = CreatePolicy();
        var uri = new Uri("http://localhost/profile");

        await policy.ValidateAsync(uri, CancellationToken.None);
    }

    [Fact]
    public async Task ValidateAsync_LoopbackIP_WhenAllowLocalhostForWebIdTrue_Succeeds()
    {
        _options = new TestOptionsMonitor(new slskd.Options
        {
            Solid = new slskd.Options.SolidOptions
            {
                AllowedHosts = new[] { "127.0.0.1" },
                AllowLocalhostForWebId = true,
                AllowInsecureHttp = true
            }
        });
        var policy = CreatePolicy();
        var uri = new Uri("http://127.0.0.1/profile");

        await policy.ValidateAsync(uri, CancellationToken.None);
    }

    [Fact]
    public async Task ValidateAsync_PrivateIPv4_WhenAllowLocalhostForWebIdTrue_StillThrows()
    {
        _options = new TestOptionsMonitor(new slskd.Options
        {
            Solid = new slskd.Options.SolidOptions
            {
                AllowedHosts = new[] { "192.168.1.1" },
                AllowLocalhostForWebId = true
            }
        });
        var policy = CreatePolicy();
        var uri = new Uri("https://192.168.1.1/profile");

        var ex = await Assert.ThrowsAsync<InvalidOperationException>(() => policy.ValidateAsync(uri, CancellationToken.None));
        Assert.Contains("resolves to a private or reserved IP", ex.Message);
    }

    [Fact]
    public async Task ValidateAsync_LocalDomain_Throws()
    {
        _options = new TestOptionsMonitor(new slskd.Options
        {
            Solid = new slskd.Options.SolidOptions
            {
                AllowedHosts = new[] { "test.local" }
            }
        });
        var policy = CreatePolicy();
        var uri = new Uri("https://test.local/profile");

        var ex = await Assert.ThrowsAsync<InvalidOperationException>(() => policy.ValidateAsync(uri, CancellationToken.None));
        Assert.Contains("localhost/.local not allowed", ex.Message);
    }

    [Fact]
    public async Task ValidateAsync_PrivateIPv4_Throws()
    {
        _options = new TestOptionsMonitor(new slskd.Options
        {
            Solid = new slskd.Options.SolidOptions
            {
                AllowedHosts = new[] { "192.168.1.1" }
            }
        });
        var policy = CreatePolicy();
        var uri = new Uri("https://192.168.1.1/profile");

        var ex = await Assert.ThrowsAsync<InvalidOperationException>(() => policy.ValidateAsync(uri, CancellationToken.None));
        Assert.Contains("resolves to a private or reserved IP", ex.Message);
    }

    [Fact]
    public async Task ValidateAsync_LoopbackIP_Throws()
    {
        _options = new TestOptionsMonitor(new slskd.Options
        {
            Solid = new slskd.Options.SolidOptions
            {
                AllowedHosts = new[] { "127.0.0.1" }
            }
        });
        var policy = CreatePolicy();
        var uri = new Uri("https://127.0.0.1/profile");

        var ex = await Assert.ThrowsAsync<InvalidOperationException>(() => policy.ValidateAsync(uri, CancellationToken.None));
        Assert.Contains("resolves to a loopback IP", ex.Message);
    }

    // Note: Empty host URI cannot be constructed with Uri constructor (throws UriFormatException)
    // The validation for empty host happens in SolidFetchPolicy.ValidateAsync, but we cannot
    // create a Uri with empty host to test this path. The validation is still present in the code.

    [Fact]
    public async Task ValidateAsync_CaseInsensitiveHostMatch_Succeeds()
    {
        _options = new TestOptionsMonitor(new slskd.Options
        {
            Solid = new slskd.Options.SolidOptions
            {
                AllowedHosts = new[] { "EXAMPLE.COM" }
            }
        });
        var policy = CreatePolicy();
        var uri = new Uri("https://example.com/profile");

        await policy.ValidateAsync(uri, CancellationToken.None);
    }
}
