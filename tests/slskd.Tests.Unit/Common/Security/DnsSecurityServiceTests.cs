// <copyright file="DnsSecurityServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Logging;
using Moq;
using slskd.Common.Security;
using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
using Xunit;

namespace slskd.Tests.Unit.Common.Security;

public class DnsSecurityServiceTests : IDisposable
{
    private readonly Mock<ILogger<DnsSecurityService>> _loggerMock;
    private readonly DnsSecurityService _dnsSecurity;
    private int _dnsResolutionCount;

    public DnsSecurityServiceTests()
    {
        _loggerMock = new Mock<ILogger<DnsSecurityService>>();
        _dnsSecurity = new DnsSecurityService(_loggerMock.Object, ResolveTestHostnameAsync);
    }

    public void Dispose()
    {
        _dnsSecurity.Dispose();
    }

    private Task<IPAddress[]> ResolveTestHostnameAsync(string hostname, CancellationToken cancellationToken)
    {
        if (hostname == "invalid.hostname.that.does.not.exist")
        {
            return Task.FromException<IPAddress[]>(new SocketException((int)SocketError.HostNotFound));
        }

        Interlocked.Increment(ref _dnsResolutionCount);
        return Task.FromResult(new[] { IPAddress.Parse("8.8.8.8") });
    }

    [Fact]
    public async Task ResolveAndValidateAsync_WithValidHostname_ReturnsSuccess()
    {
        // Arrange
        var hostname = "example.com";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(hostname, allowPrivateRanges: false, allowPublicDestinations: true);

        // Assert
        Assert.True(result.IsSuccess);
        Assert.NotEmpty(result.AllowedIPs);
        Assert.Empty(result.ErrorMessage);
    }

    [Fact]
    public async Task ResolveAndValidateAsync_WithIpAddress_ReturnsSuccess()
    {
        // Arrange
        var ipAddress = "8.8.8.8";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(ipAddress, allowPrivateRanges: false, allowPublicDestinations: true);

        // Assert
        Assert.True(result.IsSuccess);
        Assert.Contains(ipAddress, result.AllowedIPs);
    }

    [Fact]
    public async Task ResolveAndValidateAsync_WithPrivateIpAndPrivateNotAllowed_ReturnsFailure()
    {
        // Arrange
        var privateIp = "192.168.1.1";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(privateIp, allowPrivateRanges: false, allowPublicDestinations: true);

        // Assert
        Assert.False(result.IsSuccess);
        Assert.Contains("not allowed", result.ErrorMessage);
    }

    [Fact]
    public async Task ResolveAndValidateAsync_WithPrivateIpAndPrivateAllowed_ReturnsSuccess()
    {
        // Arrange
        var privateIp = "192.168.1.1";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(privateIp, allowPrivateRanges: true, allowPublicDestinations: true);

        // Assert
        Assert.True(result.IsSuccess);
        Assert.Contains(privateIp, result.AllowedIPs);
    }

    [Fact]
    public async Task ResolveAndValidateAsync_WithPublicIpAndPublicNotAllowed_ReturnsFailure()
    {
        // Arrange
        var publicIp = "8.8.8.8";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(publicIp, allowPrivateRanges: true, allowPublicDestinations: false);

        // Assert
        Assert.False(result.IsSuccess);
        Assert.Contains("not allowed", result.ErrorMessage);
    }

    [Fact]
    public async Task ResolveAndValidateAsync_WithBlockedIp_ReturnsFailure()
    {
        // Arrange
        var blockedIp = "127.0.0.1";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(blockedIp, allowPrivateRanges: true, allowPublicDestinations: true);

        // Assert
        Assert.False(result.IsSuccess);
        Assert.Contains("not allowed", result.ErrorMessage, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task ResolveAndValidateAsync_WithInvalidHostname_ReturnsFailure()
    {
        // Arrange
        var invalidHostname = "invalid.hostname.that.does.not.exist";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(invalidHostname, allowPrivateRanges: true, allowPublicDestinations: true);

        // Assert
        Assert.False(result.IsSuccess);
        Assert.Contains("resolve", result.ErrorMessage.ToLowerInvariant());
    }

    [Fact]
    public async Task ResolveAndValidateAsync_WithEmptyHostname_ReturnsFailure()
    {
        // Arrange
        var emptyHostname = "";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(emptyHostname, allowPrivateRanges: true, allowPublicDestinations: true);

        // Assert
        Assert.False(result.IsSuccess);
        Assert.Contains("required", result.ErrorMessage);
    }

    [Fact]
    public async Task ResolveAndValidateAsync_WithNullHostname_ReturnsFailure()
    {
        // Arrange
        string? nullHostname = null;

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(nullHostname!, allowPrivateRanges: true, allowPublicDestinations: true);

        // Assert
        Assert.False(result.IsSuccess);
        Assert.Contains("required", result.ErrorMessage);
    }

    [Fact]
    public void PinTunnelIPs_ValidTunnel_PinsSuccessfully()
    {
        // Arrange
        var tunnelId = "tunnel-123";
        var hostname = "example.com";
        var ips = new List<string> { "1.2.3.4", "5.6.7.8" };

        // Act
        _dnsSecurity.PinTunnelIPs(tunnelId, hostname, ips);

        // Assert - verify pinning works
        Assert.True(_dnsSecurity.ValidateTunnelIP(tunnelId, "1.2.3.4"));
        Assert.True(_dnsSecurity.ValidateTunnelIP(tunnelId, "5.6.7.8"));
        Assert.False(_dnsSecurity.ValidateTunnelIP(tunnelId, "9.9.9.9"));
    }

    [Fact]
    public void PinTunnelIPs_CallerMutatesOriginalList_DoesNotChangePinnedIps()
    {
        var tunnelId = "tunnel-mutable";
        var hostname = "example.com";
        var ips = new List<string> { "1.2.3.4" };

        _dnsSecurity.PinTunnelIPs(tunnelId, hostname, ips);
        ips.Add("9.9.9.9");

        Assert.True(_dnsSecurity.ValidateTunnelIP(tunnelId, "1.2.3.4"));
        Assert.False(_dnsSecurity.ValidateTunnelIP(tunnelId, "9.9.9.9"));
    }

    [Fact]
    public void ValidateTunnelIP_UnknownTunnel_ReturnsFalse()
    {
        // Arrange
        var unknownTunnelId = "unknown-tunnel";

        // Act
        var result = _dnsSecurity.ValidateTunnelIP(unknownTunnelId, "1.2.3.4");

        // Assert
        Assert.False(result);
    }

    [Fact]
    public void ValidateTunnelIP_ValidPinnedIp_ReturnsTrue()
    {
        // Arrange
        var tunnelId = "tunnel-123";
        var hostname = "example.com";
        var ips = new List<string> { "1.2.3.4" };

        _dnsSecurity.PinTunnelIPs(tunnelId, hostname, ips);

        // Act
        var result = _dnsSecurity.ValidateTunnelIP(tunnelId, "1.2.3.4");

        // Assert
        Assert.True(result);
    }

    [Fact]
    public void ValidateTunnelIP_UnpinnedIp_ReturnsFalse()
    {
        // Arrange
        var tunnelId = "tunnel-123";
        var hostname = "example.com";
        var ips = new List<string> { "1.2.3.4" };

        _dnsSecurity.PinTunnelIPs(tunnelId, hostname, ips);

        // Act
        var result = _dnsSecurity.ValidateTunnelIP(tunnelId, "5.6.7.8");

        // Assert
        Assert.False(result);
    }

    [Fact]
    public void ReleaseTunnelPin_ValidTunnel_ReleasesSuccessfully()
    {
        // Arrange
        var tunnelId = "tunnel-123";
        var hostname = "example.com";
        var ips = new List<string> { "1.2.3.4" };

        _dnsSecurity.PinTunnelIPs(tunnelId, hostname, ips);
        Assert.True(_dnsSecurity.ValidateTunnelIP(tunnelId, "1.2.3.4"));

        // Act
        _dnsSecurity.ReleaseTunnelPin(tunnelId);

        // Assert
        Assert.False(_dnsSecurity.ValidateTunnelIP(tunnelId, "1.2.3.4"));
    }

    [Fact]
    public void GetCacheStats_ReturnsValidStats()
    {
        // Act
        var stats = _dnsSecurity.GetCacheStats();

        // Assert
        Assert.True(stats.TotalEntries >= 0);
        Assert.True(stats.ActiveTunnels >= 0);
        Assert.True(stats.ExpiredEntries >= 0);
    }

    [Fact]
    public async Task ResolveAndValidateAsync_CachesResults()
    {
        // Arrange
        var hostname = "google.com";
        var resolutionsBefore = _dnsResolutionCount;

        // First resolution
        var result1 = await _dnsSecurity.ResolveAndValidateAsync(hostname, allowPrivateRanges: true, allowPublicDestinations: true);
        Assert.True(result1.IsSuccess);

        // Second resolution should use cache
        var result2 = await _dnsSecurity.ResolveAndValidateAsync(hostname, allowPrivateRanges: true, allowPublicDestinations: true);
        Assert.True(result2.IsSuccess);

        // Results should be identical
        Assert.Equal(result1.AllowedIPs.Count, result2.AllowedIPs.Count);
        Assert.Equal(resolutionsBefore + 1, _dnsResolutionCount);
    }

    [Fact]
    public async Task ResolveAndValidateAsync_CloudMetadataIp_Blocked()
    {
        // Arrange
        var metadataIp = "169.254.169.254";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(metadataIp, allowPrivateRanges: true, allowPublicDestinations: true);

        // Assert
        Assert.False(result.IsSuccess);
        Assert.Contains("not allowed", result.ErrorMessage, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task ResolveAndValidateAsync_LoopbackIp_Blocked()
    {
        // Arrange
        var loopbackIp = "127.0.0.1";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(loopbackIp, allowPrivateRanges: true, allowPublicDestinations: true);

        // Assert
        Assert.False(result.IsSuccess);
        Assert.Contains("not allowed", result.ErrorMessage, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task ResolveAndValidateAsync_LinkLocalIp_Blocked()
    {
        // Arrange
        var linkLocalIp = "169.254.1.1";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(linkLocalIp, allowPrivateRanges: true, allowPublicDestinations: true);

        // Assert
        Assert.False(result.IsSuccess);
        Assert.Contains("not allowed", result.ErrorMessage, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task ResolveAndValidateAsync_PrivateRangeWithoutPermission_Blocked()
    {
        // Arrange
        var privateIp = "10.0.0.1";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(privateIp, allowPrivateRanges: false, allowPublicDestinations: true);

        // Assert
        Assert.False(result.IsSuccess);
        Assert.Contains("not allowed", result.ErrorMessage.ToLowerInvariant());
    }

    [Fact]
    public async Task ResolveAndValidateAsync_PrivateRangeWithPermission_Allowed()
    {
        // Arrange
        var privateIp = "10.0.0.1";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(privateIp, allowPrivateRanges: true, allowPublicDestinations: false);

        // Assert
        Assert.True(result.IsSuccess);
        Assert.Contains(privateIp, result.AllowedIPs);
    }

    [Fact]
    public async Task ResolveAndValidateAsync_PublicRangeWithoutPermission_Blocked()
    {
        // Arrange
        var publicIp = "8.8.8.8";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(publicIp, allowPrivateRanges: true, allowPublicDestinations: false);

        // Assert
        Assert.False(result.IsSuccess);
        Assert.Contains("not allowed", result.ErrorMessage.ToLowerInvariant());
    }

    [Fact]
    public async Task ResolveAndValidateAsync_PublicRangeWithPermission_Allowed()
    {
        // Arrange
        var publicIp = "8.8.8.8";

        // Act
        var result = await _dnsSecurity.ResolveAndValidateAsync(publicIp, allowPrivateRanges: false, allowPublicDestinations: true);

        // Assert
        Assert.True(result.IsSuccess);
        Assert.Contains(publicIp, result.AllowedIPs);
    }
}
