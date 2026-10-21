// <copyright file="OidcBackchannelHandler.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Authentication;

using System;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;

/// <summary>
///     Bounds OIDC discovery, token, user-info, and key-set responses and refuses redirects.
/// </summary>
internal sealed class OidcBackchannelHandler : DelegatingHandler
{
    private const int MaxResponseBytes = 1 << 20;

    public OidcBackchannelHandler(bool allowPrivateNetwork)
        : base(CreateTransport(allowPrivateNetwork))
    {
    }

    private static SocketsHttpHandler CreateTransport(bool allowPrivateNetwork)
    {
        return new SocketsHttpHandler
        {
            ConnectCallback = (context, cancellationToken) => ConnectAsync(context, cancellationToken, allowPrivateNetwork),
            AllowAutoRedirect = false,
            UseProxy = false,
            PooledConnectionLifetime = TimeSpan.FromMinutes(5),
            MaxConnectionsPerServer = 4,
        };
    }

    private static async ValueTask<Stream> ConnectAsync(
        SocketsHttpConnectionContext context,
        CancellationToken cancellationToken,
        bool allowPrivateNetwork)
    {
        var addresses = await Dns.GetHostAddressesAsync(context.DnsEndPoint.Host, cancellationToken).ConfigureAwait(false);
        if (addresses.Length == 0 || (!allowPrivateNetwork && addresses.Any(address => !IsPublicAddress(address))))
        {
            throw new HttpRequestException("OIDC provider resolved to a private or reserved network address.");
        }

        Exception? lastError = null;
        foreach (var address in addresses)
        {
            var socket = new Socket(address.AddressFamily, SocketType.Stream, ProtocolType.Tcp);
            try
            {
                await socket.ConnectAsync(new IPEndPoint(address, context.DnsEndPoint.Port), cancellationToken).ConfigureAwait(false);
                return new NetworkStream(socket, ownsSocket: true);
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
            {
                socket.Dispose();
                throw;
            }
            catch (Exception error)
            {
                socket.Dispose();
                lastError = error;
            }
        }

        throw new HttpRequestException("Unable to connect to the OIDC provider.", lastError);
    }

    private static bool IsPublicAddress(IPAddress address)
    {
        if (address.IsIPv4MappedToIPv6)
        {
            address = address.MapToIPv4();
        }

        if (IPAddress.IsLoopback(address))
        {
            return false;
        }

        var bytes = address.GetAddressBytes();
        if (address.AddressFamily == AddressFamily.InterNetwork)
        {
            var first = bytes[0];
            var second = bytes[1];
            var third = bytes[2];
            return first != 0 && first != 10 && first != 127 && first < 224 &&
                   !(first == 100 && second >= 64 && second <= 127) &&
                   !(first == 169 && second == 254) &&
                   !(first == 172 && second >= 16 && second <= 31) &&
                   !(first == 192 && (second == 0 || second == 168 || (second == 88 && third == 99))) &&
                   !(first == 192 && second == 0 && third == 2) &&
                   !(first == 198 && (second == 18 || second == 19 || (second == 51 && third == 100))) &&
                   !(first == 203 && second == 0 && third == 113);
        }

        if (address.AddressFamily != AddressFamily.InterNetworkV6 ||
            address.Equals(IPAddress.IPv6Any) || address.Equals(IPAddress.IPv6None) || address.IsIPv6LinkLocal ||
            address.IsIPv6SiteLocal || address.IsIPv6Multicast)
        {
            return false;
        }

        // Only globally-routed unicast space (2000::/3) is accepted by default.
        return (bytes[0] & 0xE0) == 0x20 &&
               !(bytes[0] == 0x20 && bytes[1] == 0x01 && bytes[2] == 0x0D && bytes[3] == 0xB8);
    }

    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        var response = await base.SendAsync(request, cancellationToken).ConfigureAwait(false);
        var originalContent = response.Content;
        if (originalContent == null)
        {
            return response;
        }

        if (originalContent.Headers.ContentLength > MaxResponseBytes)
        {
            response.Dispose();
            throw new HttpRequestException("OIDC provider response exceeds the configured size limit.");
        }

        try
        {
            await using var source = await originalContent.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
            using var destination = new MemoryStream();
            var buffer = new byte[8192];
            while (true)
            {
                var read = await source.ReadAsync(buffer.AsMemory(0, buffer.Length), cancellationToken).ConfigureAwait(false);
                if (read == 0)
                {
                    break;
                }

                if (destination.Length + read > MaxResponseBytes)
                {
                    response.Dispose();
                    throw new HttpRequestException("OIDC provider response exceeds the configured size limit.");
                }

                await destination.WriteAsync(buffer.AsMemory(0, read), cancellationToken).ConfigureAwait(false);
            }

            var headers = originalContent.Headers.ToArray();
            var boundedContent = new ByteArrayContent(destination.ToArray());
            foreach (var header in headers)
            {
                boundedContent.Headers.TryAddWithoutValidation(header.Key, header.Value);
            }

            originalContent.Dispose();
            response.Content = boundedContent;
            return response;
        }
        catch
        {
            response.Dispose();
            throw;
        }
    }
}
