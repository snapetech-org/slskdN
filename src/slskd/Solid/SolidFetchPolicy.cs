// <copyright file="SolidFetchPolicy.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Solid;

using System;
using System.Collections.Concurrent;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

/// <summary>
///     SSRF hardening policy for WebID/Pod fetches.
/// </summary>
public sealed class SolidFetchPolicy : ISolidFetchPolicy
{
    private static readonly TimeSpan DnsCacheTtl = TimeSpan.FromSeconds(30);

    private readonly IOptionsMonitor<slskd.Options> _options;
    private readonly ILogger<SolidFetchPolicy> _logger;
    private readonly Func<string, CancellationToken, Task<IPAddress[]>> _resolveHost;
    private readonly ConcurrentDictionary<string, (DateTime ExpiresUtc, IPAddress[] Addresses)> _dnsCache = new(StringComparer.OrdinalIgnoreCase);

    public SolidFetchPolicy(IOptionsMonitor<slskd.Options> options, ILogger<SolidFetchPolicy> logger)
        : this(options, logger, Dns.GetHostAddressesAsync)
    {
    }

    internal SolidFetchPolicy(
        IOptionsMonitor<slskd.Options> options,
        ILogger<SolidFetchPolicy> logger,
        Func<string, CancellationToken, Task<IPAddress[]>> resolveHost)
    {
        _options = options ?? throw new ArgumentNullException(nameof(options));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        _resolveHost = resolveHost ?? throw new ArgumentNullException(nameof(resolveHost));
    }

    /// <inheritdoc/>
    public async Task ValidateAsync(Uri uri, CancellationToken ct)
    {
        var opts = _options.CurrentValue.Solid;

        if (!opts.AllowInsecureHttp && uri.Scheme != Uri.UriSchemeHttps)
        {
            throw new InvalidOperationException("Solid fetch blocked: only https:// allowed.");
        }

        if (string.IsNullOrWhiteSpace(uri.Host))
        {
            throw new InvalidOperationException("Solid fetch blocked: empty host.");
        }

        // Host allow-list. Empty list => deny all remote fetches.
        if (opts.AllowedHosts == null || opts.AllowedHosts.Length == 0)
        {
            throw new InvalidOperationException("Solid fetch blocked: no AllowedHosts configured.");
        }

        if (!opts.AllowedHosts.Contains(uri.Host, StringComparer.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException($"Solid fetch blocked: host '{uri.Host}' not in AllowedHosts.");
        }

        // E2E/testing: allow only localhost and loopback literals when explicitly enabled.
        if (opts.AllowLocalhostForWebId && IsLoopbackHost(uri.DnsSafeHost))
        {
            return;
        }

        // Block obvious local targets by name before we resolve anything.
        if (uri.Host.Equals("localhost", StringComparison.OrdinalIgnoreCase) || uri.Host.EndsWith(".local", StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException("Solid fetch blocked: localhost/.local not allowed.");
        }

        // Resolve the host and re-check every IP. Prevents the DNS-rebinding-adjacent bypass where
        // an attacker lists a hostname in AllowedHosts that resolves to loopback / RFC1918 / IMDS.
        // If the host is already an IP literal, GetHostAddresses returns it unchanged.
        IPAddress[] addresses;
        try
        {
            addresses = await ResolveWithCacheAsync(uri.Host, ct).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is SocketException or System.Net.Sockets.SocketException)
        {
            throw new InvalidOperationException($"Solid fetch blocked: DNS resolution failed for '{uri.Host}'.", ex);
        }

        if (addresses.Length == 0)
        {
            throw new InvalidOperationException($"Solid fetch blocked: DNS resolution returned no addresses for '{uri.Host}'.");
        }

        foreach (var ip in addresses)
        {
            if (IPAddress.IsLoopback(ip))
            {
                throw new InvalidOperationException($"Solid fetch blocked: host '{uri.Host}' resolves to a loopback IP.");
            }

            if (IsPrivateOrReserved(ip))
            {
                throw new InvalidOperationException($"Solid fetch blocked: host '{uri.Host}' resolves to a private or reserved IP ({ip}).");
            }
        }
    }

    private async Task<IPAddress[]> ResolveWithCacheAsync(string host, CancellationToken ct)
    {
        if (_dnsCache.TryGetValue(host, out var cached) && cached.ExpiresUtc > DateTime.UtcNow)
        {
            return cached.Addresses;
        }

        var resolved = await _resolveHost(host, ct).ConfigureAwait(false);
        _dnsCache[host] = (DateTime.UtcNow.Add(DnsCacheTtl), resolved);
        return resolved;
    }

    internal static bool IsLoopbackHost(string host) =>
        host.Equals("localhost", StringComparison.OrdinalIgnoreCase) ||
        (IPAddress.TryParse(host, out var address) && IPAddress.IsLoopback(address));

    private static bool IsPrivateOrReserved(IPAddress ip)
    {
        // Collapse IPv4-mapped IPv6 (::ffff:a.b.c.d) down to IPv4 before classification so the
        // RFC1918 checks can't be bypassed with a mapped form.
        if (ip.AddressFamily == AddressFamily.InterNetworkV6 && ip.IsIPv4MappedToIPv6)
        {
            ip = ip.MapToIPv4();
        }

        if (ip.AddressFamily == AddressFamily.InterNetwork)
        {
            var b = ip.GetAddressBytes();

            if (b[0] == 10) return true;                                // 10.0.0.0/8
            if (b[0] == 172 && b[1] >= 16 && b[1] <= 31) return true;   // 172.16.0.0/12
            if (b[0] == 192 && b[1] == 168) return true;                // 192.168.0.0/16
            if (b[0] == 169 && b[1] == 254) return true;                // 169.254.0.0/16 (link-local, covers AWS IMDS)
            if (b[0] == 100 && (b[1] & 0xc0) == 0x40) return true;      // 100.64.0.0/10 (CGNAT)
            if (b[0] == 127) return true;                                // 127.0.0.0/8
            if (b[0] == 0) return true;                                  // 0.0.0.0/8
            if (b[0] >= 224) return true;                                // multicast + reserved
        }

        if (ip.AddressFamily == AddressFamily.InterNetworkV6)
        {
            if (ip.IsIPv6LinkLocal || ip.IsIPv6SiteLocal || ip.IsIPv6Multicast) return true;

            var b = ip.GetAddressBytes();
            if ((b[0] & 0xfe) == 0xfc) return true;                      // fc00::/7 ULA
            if (b[0] == 0x00 && b[1] == 0x00)
            {
                // ::1 is handled by IsLoopback at the caller, but guard the unspecified addr here.
                if (ip.Equals(IPAddress.IPv6Any)) return true;
            }
        }

        return false;
    }
}
