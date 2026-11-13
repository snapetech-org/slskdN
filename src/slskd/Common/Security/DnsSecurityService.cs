// <copyright file="DnsSecurityService.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Logging;
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Threading;
using System.Threading.Tasks;

namespace slskd.Common.Security;

/// <summary>
/// Provides secure DNS resolution with rebinding protection and IP validation for VPN services.
/// </summary>
public sealed class DnsSecurityService : IDnsSecurityService, IDisposable
{
    private readonly ILogger<DnsSecurityService> _logger;
    private readonly Func<string, CancellationToken, Task<IPAddress[]>> _resolveHost;
    private readonly object _dnsCacheLock = new();

    // DNS cache: hostname -> (resolved IPs, expiry time, tunnel IDs using this entry)
    private readonly ConcurrentDictionary<string, (List<string> IPs, DateTimeOffset Expires, HashSet<string> TunnelIds)> _dnsCache = new();

    // Tunnel IP pinning: tunnelId -> (hostname, pinned IPs, pin expiry)
    private readonly ConcurrentDictionary<string, (string Hostname, List<string> PinnedIPs, DateTimeOffset PinExpires)> _tunnelIpPins = new();

    // Background cleanup task
    private readonly Timer _cleanupTimer;

    public DnsSecurityService(ILogger<DnsSecurityService> logger)
        : this(logger, Dns.GetHostAddressesAsync)
    {
    }

    internal DnsSecurityService(
        ILogger<DnsSecurityService> logger,
        Func<string, CancellationToken, Task<IPAddress[]>> resolveHost)
    {
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        _resolveHost = resolveHost ?? throw new ArgumentNullException(nameof(resolveHost));

        // Start cleanup timer (runs every 5 minutes)
        _cleanupTimer = new Timer(CleanupExpiredEntries, null, TimeSpan.FromMinutes(5), TimeSpan.FromMinutes(5));
    }

    public void Dispose()
    {
        Common.TimerDisposer.DisposeWithWait(_cleanupTimer);
        GC.SuppressFinalize(this);
    }

    /// <summary>
    /// Resolves a hostname and validates all IPs against security policies.
    /// </summary>
    /// <param name="hostname">The hostname to resolve.</param>
    /// <param name="allowPrivateRanges">Whether private IP ranges are allowed.</param>
    /// <param name="allowPublicDestinations">Whether public internet destinations are allowed.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>Validated IP addresses safe for tunneling.</returns>
    public async Task<DnsResolutionResult> ResolveAndValidateAsync(
        string hostname,
        bool allowPrivateRanges,
        bool allowPublicDestinations,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(hostname))
            return DnsResolutionResult.Failure("Hostname is required");

        // If it's already an IP address, validate it directly
        if (IPAddress.TryParse(hostname, out var ip))
        {
            var classification = IpRangeClassifier.Classify(ip);
            var isAllowed = IsIpAllowedForTunneling(ip, allowPrivateRanges, allowPublicDestinations);

            if (!isAllowed)
            {
                _logger.LogWarning(
                    "[DnsSecurity] IP address {IP} not allowed for tunneling: {Classification}",
                    hostname, IpRangeClassifier.GetDescription(classification));

                return DnsResolutionResult.Failure($"IP address not allowed: {IpRangeClassifier.GetDescription(classification)}");
            }

            return DnsResolutionResult.Success(new List<string> { hostname });
        }

        // Check cache first
        if (_dnsCache.TryGetValue(hostname, out var cachedEntry) && cachedEntry.Expires > DateTimeOffset.UtcNow)
        {
            // Validate cached IPs are still allowed
            var validCachedIPs = cachedEntry.IPs.Where(ipString =>
                IPAddress.TryParse(ipString, out var ip) &&
                IsIpAllowedForTunneling(ip, allowPrivateRanges, allowPublicDestinations)).ToList();

            if (validCachedIPs.Count != cachedEntry.IPs.Count)
            {
                _logger.LogWarning(
                    "[DnsSecurity] Cached DNS entry for {Hostname} contains disallowed IPs, re-resolving",
                    hostname);
            }
            else
            {
                _logger.LogDebug("[DnsSecurity] Using cached DNS resolution for {Hostname}: {SanitizedIPs}",
                    hostname, string.Join(", ", validCachedIPs.Select(ip => LoggingSanitizer.SanitizeIpAddress(ip))));
                return DnsResolutionResult.Success(validCachedIPs);
            }
        }

        // Resolve hostname
        var resolvedIPs = await ResolveHostnameAsync(hostname, cancellationToken);
        if (!resolvedIPs.Any())
        {
            return DnsResolutionResult.Failure("Failed to resolve hostname");
        }

        // Validate all resolved IPs
        var allowedIPs = new List<string>();
        var blockedIPs = new List<string>();

        foreach (var ipString in resolvedIPs)
        {
            if (IPAddress.TryParse(ipString, out var resolvedIP))
            {
                if (IsIpAllowedForTunneling(resolvedIP, allowPrivateRanges, allowPublicDestinations))
                {
                    allowedIPs.Add(ipString);
                }
                else
                {
                    var classification = IpRangeClassifier.Classify(resolvedIP);
                    blockedIPs.Add($"{ipString} ({IpRangeClassifier.GetDescription(classification)})");
                }
            }
        }

        if (!allowedIPs.Any())
        {
            _logger.LogWarning(
                "[DnsSecurity] All resolved IPs for {Hostname} are blocked: {BlockedIPs}",
                hostname, string.Join(", ", blockedIPs));

            return DnsResolutionResult.Failure("All resolved IP addresses are blocked for security reasons");
        }

        // Cache the result
        _dnsCache[hostname] = (
            new List<string>(allowedIPs),
            DateTimeOffset.UtcNow.AddMinutes(5),
            new HashSet<string>(StringComparer.Ordinal));

        _logger.LogInformation(
            "[DnsSecurity] Resolved and validated {Hostname}: {AllowedCount} allowed, {BlockedCount} blocked",
            hostname, allowedIPs.Count, resolvedIPs.Count - allowedIPs.Count);

        return DnsResolutionResult.Success(allowedIPs);
    }

    /// <summary>
    /// Pins resolved IPs for a tunnel to prevent DNS rebinding attacks.
    /// </summary>
    /// <param name="tunnelId">The tunnel ID.</param>
    /// <param name="hostname">The original hostname.</param>
    /// <param name="resolvedIPs">The resolved and validated IPs.</param>
    public void PinTunnelIPs(string tunnelId, string hostname, List<string> resolvedIPs)
    {
        var pinnedIps = new List<string>(resolvedIPs);

        // Pin the IPs for the tunnel lifetime to prevent rebinding
        _tunnelIpPins[tunnelId] = (hostname, pinnedIps, DateTimeOffset.UtcNow.AddHours(24)); // 24 hour max lifetime

        // Add tunnel ID to DNS cache entry for cleanup tracking
        if (_dnsCache.TryGetValue(hostname, out var cacheEntry))
        {
            lock (_dnsCacheLock)
            {
                cacheEntry.TunnelIds.Add(tunnelId);
            }
        }

        _logger.LogDebug(
            "[DnsSecurity] Pinned IPs for tunnel {TunnelId}: {Hostname} -> {IPs}",
            tunnelId, hostname, string.Join(", ", pinnedIps));
    }

    /// <summary>
    /// Validates that an IP is still allowed for an existing tunnel (rebinding protection).
    /// </summary>
    /// <param name="tunnelId">The tunnel ID.</param>
    /// <param name="ipString">The IP address to validate.</param>
    /// <returns>True if the IP is allowed for this tunnel.</returns>
    public bool ValidateTunnelIP(string tunnelId, string ipString)
    {
        if (!_tunnelIpPins.TryGetValue(tunnelId, out var pinEntry))
        {
            _logger.LogWarning("[DnsSecurity] No IP pin found for tunnel {TunnelId}", tunnelId);
            return false;
        }

        if (pinEntry.PinExpires < DateTimeOffset.UtcNow)
        {
            _logger.LogWarning("[DnsSecurity] IP pin expired for tunnel {TunnelId}", tunnelId);
            return false;
        }

        var isPinned = pinEntry.PinnedIPs.Contains(ipString);
        if (!isPinned)
        {
            _logger.LogWarning(
                "[DnsSecurity] IP {IP} not in pinned IPs for tunnel {TunnelId} (possible DNS rebinding attack)",
                ipString, tunnelId);
        }

        return isPinned;
    }

    /// <summary>
    /// Releases IP pinning for a tunnel.
    /// </summary>
    /// <param name="tunnelId">The tunnel ID.</param>
    public void ReleaseTunnelPin(string tunnelId)
    {
        if (_tunnelIpPins.TryRemove(tunnelId, out var pinEntry))
        {
            _logger.LogDebug("[DnsSecurity] Released IP pin for tunnel {TunnelId}", tunnelId);

            // Remove from DNS cache tracking if present
            if (_dnsCache.TryGetValue(pinEntry.Hostname, out var cacheEntry))
            {
                lock (_dnsCacheLock)
                {
                    cacheEntry.TunnelIds.Remove(tunnelId);
                }
            }
        }
    }

    /// <summary>
    /// Gets DNS cache statistics for monitoring.
    /// </summary>
    public (int TotalEntries, int ActiveTunnels, int ExpiredEntries) GetCacheStats()
    {
        var now = DateTimeOffset.UtcNow;
        var totalEntries = _dnsCache.Count;
        var expiredEntries = _dnsCache.Count(kvp => kvp.Value.Expires < now);
        var activeTunnels = _tunnelIpPins.Count;

        return (totalEntries, activeTunnels, expiredEntries);
    }

    private async Task<List<string>> ResolveHostnameAsync(string hostname, CancellationToken cancellationToken)
    {
        try
        {
            var addresses = await _resolveHost(hostname, cancellationToken).ConfigureAwait(false);
            return addresses.Select(addr => addr.ToString()).ToList();
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "[DnsSecurity] DNS resolution failed for {Hostname}", hostname);
            return new List<string>();
        }
    }

    private bool IsIpAllowedForTunneling(IPAddress ip, bool allowPrivateRanges, bool allowPublicDestinations)
    {
        var classification = IpRangeClassifier.Classify(ip);

        // Always block dangerous addresses
        if (IpRangeClassifier.IsBlocked(ip))
            return false;

        var isPrivate = IpRangeClassifier.IsPrivate(ip);

        // Allow private ranges if policy permits
        if (isPrivate && allowPrivateRanges)
            return true;

        // Allow public ranges if policy permits
        if (!isPrivate && allowPublicDestinations)
            return true;

        return false;
    }

    private void CleanupExpiredEntries(object? state)
    {
        try
        {
            var now = DateTimeOffset.UtcNow;

            // Clean up expired DNS cache entries
            var expiredHosts = _dnsCache.Where(kvp => kvp.Value.Expires < now).Select(kvp => kvp.Key).ToList();
            foreach (var host in expiredHosts)
            {
                _dnsCache.TryRemove(host, out _);
            }

            // Clean up expired tunnel IP pins
            var expiredTunnels = _tunnelIpPins.Where(kvp => kvp.Value.PinExpires < now).Select(kvp => kvp.Key).ToList();
            foreach (var tunnelId in expiredTunnels)
            {
                _tunnelIpPins.TryRemove(tunnelId, out _);
            }

            if (expiredHosts.Any() || expiredTunnels.Any())
            {
                _logger.LogDebug(
                    "[DnsSecurity] Cleaned up {HostCount} expired DNS entries and {TunnelCount} expired tunnel pins",
                    expiredHosts.Count, expiredTunnels.Count);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[DnsSecurity] Error during cleanup");
        }
    }
}

/// <summary>
/// Result of a DNS resolution and validation operation.
/// </summary>
public class DnsResolutionResult
{
    /// <summary>
    /// Whether the resolution was successful.
    /// </summary>
    public bool IsSuccess { get; private set; }

    /// <summary>
    /// The resolved and validated IP addresses.
    /// </summary>
    public List<string> AllowedIPs { get; private set; } = new();

    /// <summary>
    /// Error message if resolution failed.
    /// </summary>
    public string ErrorMessage { get; private set; } = string.Empty;

    /// <summary>
    /// Creates a successful result.
    /// </summary>
    public static DnsResolutionResult Success(List<string> allowedIPs)
    {
        return new DnsResolutionResult
        {
            IsSuccess = true,
            AllowedIPs = allowedIPs
        };
    }

    /// <summary>
    /// Creates a failure result.
    /// </summary>
    public static DnsResolutionResult Failure(string errorMessage)
    {
        return new DnsResolutionResult
        {
            IsSuccess = false,
            ErrorMessage = errorMessage
        };
    }
}
