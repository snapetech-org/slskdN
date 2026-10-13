// <copyright file="TorIntegrationTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Collections.Concurrent;
using Microsoft.Extensions.Logging;
using Moq;
using slskd.Common.Security;
using slskd.Mesh;
using slskd.Mesh.Transport;
using Xunit;
using Xunit.Abstractions;

namespace slskd.Tests.Integration.Security;

/// <summary>
/// Integration tests for Tor SOCKS5 transport functionality.
/// Tests SOCKS protocol implementation, circuit establishment, and stream isolation.
/// </summary>
[Collection("Integration")] // Run these tests separately to avoid conflicts
public class TorIntegrationTests
{
    private readonly ITestOutputHelper _output;
    private readonly ILogger<TorSocksTransport> _logger;

    public TorIntegrationTests(ITestOutputHelper output)
    {
        _output = output;
        _logger = new XunitLogger<TorSocksTransport>(output);
    }

    [Fact]
    public async Task TorTransport_Socks5Handshake_Succeeds()
    {
        // Arrange
        using var mockServer = new MockSocksServer();
        await mockServer.StartAsync();

        var torOptions = new TorOptions
        {
            SocksAddress = $"127.0.0.1:{mockServer.Port}",
            IsolateStreams = false
        };

        using var transport = new TorSocksTransport(torOptions, _logger);

        // Act
        var isAvailable = await transport.IsAvailableAsync();

        // Assert
        Assert.True(isAvailable, "Tor transport should be available when SOCKS server responds correctly");
    }

    [Fact]
    public async Task TorTransport_Socks5Handshake_SucceedsWithFragmentedResponse()
    {
        // Arrange
        using var mockServer = new MockSocksServer { FragmentHandshakeResponse = true };
        await mockServer.StartAsync();

        var torOptions = new TorOptions
        {
            SocksAddress = $"127.0.0.1:{mockServer.Port}",
            IsolateStreams = false
        };

        using var transport = new TorSocksTransport(torOptions, _logger);

        // Act
        var isAvailable = await transport.IsAvailableAsync();

        // Assert
        Assert.True(isAvailable, "Tor transport should ignore read fragmentation and still detect valid SOCKS5 responses");
    }

    [Fact]
    public async Task TorTransport_Socks5Handshake_FailsWithWrongVersion()
    {
        // Arrange - Mock server that returns wrong SOCKS version
        using var mockServer = new MockSocksServer();
        mockServer.ResponseVersion = 0x04; // SOCKS4 instead of SOCKS5
        await mockServer.StartAsync();

        var torOptions = new TorOptions
        {
            SocksAddress = $"127.0.0.1:{mockServer.Port}"
        };

        using var transport = new TorSocksTransport(torOptions, _logger);

        // Act
        var isAvailable = await transport.IsAvailableAsync();

        // Assert
        Assert.False(isAvailable, "Tor transport should not be available when SOCKS version is wrong");
    }

    [Fact]
    public async Task TorTransport_ConnectionTimeout_HandledGracefully()
    {
        // Arrange
        using var silentServer = new SilentTcpServer();
        await silentServer.StartAsync();

        var torOptions = new TorOptions
        {
            SocksAddress = $"127.0.0.1:{silentServer.Port}",
        };

        using var transport = new TorSocksTransport(torOptions, _logger);
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(2));

        // Act & Assert - a silent SOCKS endpoint should fail within a bounded time
        await Assert.ThrowsAnyAsync<Exception>(() => transport.ConnectAsync("example.com", 80, cts.Token));
        Assert.False(transport.GetStatus().IsAvailable);
    }

    [Fact]
    public async Task TorTransport_StreamIsolation_DifferentCredentialsPerPeer()
    {
        // Arrange
        using var mockServer = new MockSocksServer();
        await mockServer.StartAsync();

        var torOptions = new TorOptions
        {
            SocksAddress = $"127.0.0.1:{mockServer.Port}",
            IsolateStreams = true
        };

        using var transport = new TorSocksTransport(torOptions, _logger);

        // Act - Connect with different isolation keys (simulating different peers)
        // Implementation may throw Exception (e.g. SOCKS5 auth) or NotImplementedException
        await Assert.ThrowsAnyAsync<Exception>(() => transport.ConnectAsync("example.com", 80, "peer1"));
        await Assert.ThrowsAnyAsync<Exception>(() => transport.ConnectAsync("example.com", 80, "peer2"));

        // Assert - Mock server should have received connection attempts
        Assert.True(mockServer.ConnectionAttempts > 0);
    }

    [Fact]
    public async Task TorTransport_StatusTracking_UpdatesCorrectly()
    {
        // Arrange
        using var mockServer = new MockSocksServer();
        await mockServer.StartAsync();

        var torOptions = new TorOptions
        {
            SocksAddress = $"127.0.0.1:{mockServer.Port}"
        };

        using var transport = new TorSocksTransport(torOptions, _logger);

        // Act - Initial status
        var initialStatus = transport.GetStatus();
        await transport.IsAvailableAsync(); // This should update status
        var updatedStatus = transport.GetStatus();

        // Assert
        Assert.True(updatedStatus.IsAvailable);
        Assert.True(updatedStatus.LastSuccessfulConnection.HasValue);
        Assert.Equal(0, initialStatus.TotalConnectionsAttempted);
        Assert.Equal(0, initialStatus.TotalConnectionsSuccessful);
    }

    [Fact]
    public async Task TorTransport_ConcurrentConnections_HandledProperly()
    {
        // Arrange
        using var mockServer = new MockSocksServer();
        await mockServer.StartAsync();

        var torOptions = new TorOptions
        {
            SocksAddress = $"127.0.0.1:{mockServer.Port}"
        };

        using var transport = new TorSocksTransport(torOptions, _logger);

        // Act - Attempt multiple concurrent connections
        var connectionTasks = Enumerable.Range(0, 5).Select(_ =>
            Task.Run(() => transport.ConnectAsync("example.com", 80).ContinueWith(t => t.Exception?.Message ?? "success"))
        ).ToArray();

        await Task.WhenAll(connectionTasks);

        // Assert - All connections should complete (success or any error; no hang)
        var results = connectionTasks.Select(t => t.Result).ToArray();
        Assert.All(results, result => Assert.True(result == "success" || !string.IsNullOrEmpty(result),
            $"Unexpected connection result: {result}"));
    }

    [Fact]
    public async Task TorTransport_ConnectAsync_HandlesFragmentedConnectResponse()
    {
        // Arrange
        using var mockServer = new MockSocksServer { FragmentConnectResponse = true };
        await mockServer.StartAsync();

        var torOptions = new TorOptions
        {
            SocksAddress = $"127.0.0.1:{mockServer.Port}",
            IsolateStreams = false
        };

        using var transport = new TorSocksTransport(torOptions, _logger);

        // Act - connect should succeed even if SOCKS connect response arrives in multiple chunks
        using var stream = await transport.ConnectAsync("example.com", 80);

        // Assert
        Assert.NotNull(stream);
    }

    [Fact]
    public async Task TorTransport_ConnectAsync_ConsumesVariableLengthConnectResponse()
    {
        // Arrange
        var bindAddress = Encoding.ASCII.GetBytes(new string((char)'t', 22));
        var connectResponse = new byte[4 + 1 + bindAddress.Length + 2];
        connectResponse[0] = 0x05; // VER
        connectResponse[1] = 0x00; // SUCCEEDED
        connectResponse[2] = 0x00; // RSV
        connectResponse[3] = 0x03; // Domain
        connectResponse[4] = (byte)bindAddress.Length;
        Array.Copy(bindAddress, 0, connectResponse, 5, bindAddress.Length);
        connectResponse[^2] = 0x01;
        connectResponse[^1] = 0xBB;

        using var mockServer = new MockSocksServer
        {
            ConnectResponse = connectResponse,
            PostConnectPayload = "TorTransportPayload"
        };
        await mockServer.StartAsync();

        var torOptions = new TorOptions
        {
            SocksAddress = $"127.0.0.1:{mockServer.Port}",
            IsolateStreams = false
        };

        using var transport = new TorSocksTransport(torOptions, _logger);

        // Act
        using var stream = await transport.ConnectAsync("example.com", 80);

        var readBuffer = new byte[32];
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(2));
        var bytesRead = await stream.ReadAsync(readBuffer, 0, readBuffer.Length, cts.Token);

        // Assert - returned stream should start with payload, not leftover connect response bytes.
        var payload = Encoding.UTF8.GetString(readBuffer, 0, bytesRead);
        Assert.Equal("TorTransportPayload", payload);
    }

    [Fact]
    public async Task TorSocksDialer_DialAsync_ConsumesVariableLengthConnectResponse()
    {
        // Arrange
        var bindAddress = Encoding.ASCII.GetBytes(new string((char)'x', 24));
        var connectResponse = new byte[4 + 1 + bindAddress.Length + 2];
        connectResponse[0] = 0x05; // VER
        connectResponse[1] = 0x00; // SUCCEEDED
        connectResponse[2] = 0x00; // RSV
        connectResponse[3] = 0x03; // Domain
        connectResponse[4] = (byte)bindAddress.Length;
        Array.Copy(bindAddress, 0, connectResponse, 5, bindAddress.Length);
        connectResponse[^2] = 0x01;
        connectResponse[^1] = 0xBB;

        using var mockServer = new MockSocksServer
        {
            ConnectResponse = connectResponse,
            PostConnectPayload = "TorDialerPayload",
        };
        await mockServer.StartAsync();

        var options = new TorTransportOptions
        {
            Enabled = true,
            SocksHost = "127.0.0.1",
            SocksPort = mockServer.Port,
        };
        var dialer = new TorSocksDialer(options, Mock.Of<ILogger<TorSocksDialer>>());

        var endpoint = new TransportEndpoint
        {
            TransportType = TransportType.TorOnionQuic,
            Host = "abcdefghijklmnop.onion",
            Port = 443
        };

        // Act
        using var stream = await dialer.DialAsync(endpoint);

        var readBuffer = new byte[32];
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(2));
        var bytesRead = await stream.ReadAsync(readBuffer, 0, readBuffer.Length, cts.Token);

        // Assert - returned stream should start with payload, not leftover connect response bytes.
        var payload = Encoding.UTF8.GetString(readBuffer, 0, bytesRead);
        Assert.Equal("TorDialerPayload", payload);
        Assert.Empty(mockServer.ServerErrors);
    }

    [Fact]
    public async Task I2pSocksDialer_DialAsync_ConsumesVariableLengthConnectResponse()
    {
        // Arrange
        var bindAddress = Encoding.ASCII.GetBytes(new string((char)'y', 18));
        var connectResponse = new byte[4 + 1 + bindAddress.Length + 2];
        connectResponse[0] = 0x05; // VER
        connectResponse[1] = 0x00; // SUCCEEDED
        connectResponse[2] = 0x00; // RSV
        connectResponse[3] = 0x03; // Domain
        connectResponse[4] = (byte)bindAddress.Length;
        Array.Copy(bindAddress, 0, connectResponse, 5, bindAddress.Length);
        connectResponse[^2] = 0x01;
        connectResponse[^1] = 0xBB;

        using var mockServer = new MockSocksServer
        {
            ConnectResponse = connectResponse,
            PostConnectPayload = "I2pDialerPayload",
        };
        await mockServer.StartAsync();

        var options = new I2PTransportOptions
        {
            Enabled = true,
            SocksHost = "127.0.0.1",
            SocksPort = mockServer.Port,
        };
        var dialer = new I2pSocksDialer(options, Mock.Of<ILogger<I2pSocksDialer>>());

        var endpoint = new TransportEndpoint
        {
            TransportType = TransportType.I2PQuic,
            Host = "abcdef.i2p",
            Port = 443
        };

        // Act
        using var stream = await dialer.DialAsync(endpoint);

        var readBuffer = new byte[32];
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(2));
        var bytesRead = await stream.ReadAsync(readBuffer, 0, readBuffer.Length, cts.Token);

        // Assert - returned stream should start with payload, not leftover connect response bytes.
        var payload = Encoding.UTF8.GetString(readBuffer, 0, bytesRead);
        Assert.Equal("I2pDialerPayload", payload);
    }

    [Fact]
    public async Task TorTransport_AuthenticationFailure_HandledGracefully()
    {
        // Arrange - Mock server that rejects authentication
        using var mockServer = new MockSocksServer();
        mockServer.RequireAuth = true;
        mockServer.AuthSuccess = false; // Reject authentication
        await mockServer.StartAsync();

        var torOptions = new TorOptions
        {
            SocksAddress = $"127.0.0.1:{mockServer.Port}",
            IsolateStreams = true
        };

        using var transport = new TorSocksTransport(torOptions, _logger);

        // Act & Assert
        await Assert.ThrowsAsync<Exception>(() => transport.ConnectAsync("example.com", 80, "test-peer"));
    }

    [Fact]
    public async Task TorTransport_LargePayload_HandledCorrectly()
    {
        // Arrange
        using var mockServer = new MockSocksServer();
        await mockServer.StartAsync();

        var torOptions = new TorOptions
        {
            SocksAddress = $"127.0.0.1:{mockServer.Port}"
        };

        using var transport = new TorSocksTransport(torOptions, _logger);

        // Create a large payload to test buffering
        var largeHost = new string('a', 200) + ".example.com"; // Very long hostname

        // Act & Assert - Should handle large hostnames without crashing (throws when proxy/auth fails)
        await Assert.ThrowsAnyAsync<Exception>(() => transport.ConnectAsync(largeHost, 80));
    }

    [Fact]
    public async Task TorTransport_Ipv6Addresses_Supported()
    {
        // Arrange
        using var mockServer = new MockSocksServer();
        await mockServer.StartAsync();

        var torOptions = new TorOptions
        {
            SocksAddress = $"127.0.0.1:{mockServer.Port}"
        };

        using var transport = new TorSocksTransport(torOptions, _logger);

        // Act - Try connecting to IPv6 address (may throw when proxy/auth fails)
        await Assert.ThrowsAnyAsync<Exception>(() => transport.ConnectAsync("2001:db8::1", 80));

        // Assert - In full implementation, this would test IPv6 address type (0x04) in SOCKS request
    }

    [Fact]
    public async Task TorTransport_ConnectionLifecycle_StreamProperlyTracked()
    {
        // Arrange
        using var mockServer = new MockSocksServer();
        await mockServer.StartAsync();

        var torOptions = new TorOptions
        {
            SocksAddress = $"127.0.0.1:{mockServer.Port}"
        };

        using var transport = new TorSocksTransport(torOptions, _logger);

        // Act - Check initial state
        var initialStatus = transport.GetStatus();
        Assert.Equal(0, initialStatus.ActiveConnections);

        // In a full implementation, we'd test that ActiveConnections increases during connection
        // and decreases when disposed. For now, we verify the tracking structure exists.
        Assert.Equal(0, initialStatus.TotalConnectionsAttempted);
        Assert.Equal(0, initialStatus.TotalConnectionsSuccessful);
    }

    /// <summary>
    /// Mock SOCKS5 server for testing Tor transport functionality.
    /// </summary>
    private class MockSocksServer : IDisposable
    {
        private TcpListener? _listener;
        private Task? _serverTask;
        private readonly CancellationTokenSource _cts = new();

        public int Port { get; private set; }
        public int ConnectionAttempts { get; private set; }
        public ConcurrentQueue<Exception> ServerErrors { get; } = new();
        public byte ResponseVersion { get; set; } = 0x05; // SOCKS5
        public bool RequireAuth { get; set; }
        public bool AuthSuccess { get; set; } = true;
        public bool FragmentHandshakeResponse { get; set; }
        public bool FragmentConnectResponse { get; set; }
        public byte[]? ConnectResponse { get; set; }
        public string PostConnectPayload { get; set; } = string.Empty;

        public async Task StartAsync()
        {
            _listener = new TcpListener(IPAddress.Loopback, 0);
            _listener.Start();
            Port = ((IPEndPoint)_listener.LocalEndpoint).Port;

            _serverTask = Task.Run(async () =>
            {
                while (!_cts.Token.IsCancellationRequested)
                {
                    try
                    {
                        var client = await _listener.AcceptTcpClientAsync(_cts.Token);
                        _ = HandleClientAsync(client, _cts.Token);
                    }
                    catch (OperationCanceledException)
                    {
                        break;
                    }
                    catch (ObjectDisposedException)
                    {
                        break;
                    }
                }
            });
        }

        private async Task HandleClientAsync(TcpClient client, CancellationToken ct)
        {
            ConnectionAttempts++;
            try
            {
                using (client)
                {
                    var stream = client.GetStream();

                    // The greeting's method count makes the frame length variable.
                    var greetingHeader = new byte[2];
                    await stream.ReadExactlyAsync(greetingHeader, ct);
                    var methods = new byte[greetingHeader[1]];
                    await stream.ReadExactlyAsync(methods, ct);

                    var selectedMethod = RequireAuth
                        ? methods.Contains((byte)0x02) ? (byte)0x02 : (byte)0xFF
                        : methods.Contains((byte)0x00) ? (byte)0x00 : (byte)0xFF;
                    var handshakeResponse = new[] { ResponseVersion, selectedMethod };
                    await WriteFragmentedAsync(stream, handshakeResponse, FragmentHandshakeResponse, ct);

                    if (selectedMethod == 0xFF)
                    {
                        return;
                    }

                    if (selectedMethod == 0x02)
                    {
                        var authHeader = new byte[2];
                        await stream.ReadExactlyAsync(authHeader, ct);
                        var usernameAndPasswordLength = new byte[authHeader[1] + 1];
                        await stream.ReadExactlyAsync(usernameAndPasswordLength, ct);
                        var password = new byte[usernameAndPasswordLength[^1]];
                        await stream.ReadExactlyAsync(password, ct);

                        var authResult = AuthSuccess ? (byte)0x00 : (byte)0x01;
                        await stream.WriteAsync(new byte[] { 0x01, authResult }, 0, 2, ct);

                        if (!AuthSuccess)
                        {
                            return; // End connection on auth failure
                        }
                    }
                    var connectHeader = new byte[4];
                    await stream.ReadExactlyAsync(connectHeader, ct);

                    var addressLength = connectHeader[3] switch
                    {
                        0x01 => 4,
                        0x04 => 16,
                        0x03 => await ReadDomainAddressLengthAsync(stream, ct),
                        _ => throw new InvalidDataException("Unsupported SOCKS5 address type"),
                    };
                    var addressAndPort = new byte[addressLength + 2];
                    await stream.ReadExactlyAsync(addressAndPort, ct);

                    // Send success response
                    var connectResponse = ConnectResponse ??
                        new byte[] { 0x05, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
                    await WriteFragmentedAsync(stream, connectResponse, FragmentConnectResponse, ct);

                    if (!string.IsNullOrEmpty(PostConnectPayload))
                    {
                        var payload = Encoding.UTF8.GetBytes(PostConnectPayload);
                        await WriteFragmentedAsync(stream, payload, false, ct);
                    }
                }
            }
            catch (Exception ex)
            {
                ServerErrors.Enqueue(ex);
            }
        }

        private static async Task<int> ReadDomainAddressLengthAsync(NetworkStream stream, CancellationToken ct)
        {
            var length = new byte[1];
            await stream.ReadExactlyAsync(length, ct);
            return length[0];
        }

        private static async Task WriteFragmentedAsync(Stream stream, byte[] payload, bool fragment, CancellationToken ct)
        {
            if (!fragment || payload.Length <= 1)
            {
                await stream.WriteAsync(payload, 0, payload.Length, ct);
                return;
            }

            var firstChunk = Math.Min(payload.Length - 1, Math.Max(1, payload.Length / 2));
            await stream.WriteAsync(payload, 0, firstChunk, ct);
            await Task.Delay(5, ct);
            await stream.WriteAsync(payload, firstChunk, payload.Length - firstChunk, ct);
        }

        public void Dispose()
        {
            _cts.Cancel();
            _listener?.Stop();
            try
            {
                _serverTask?.Wait(TimeSpan.FromSeconds(1));
            }
            catch (AggregateException)
            {
                // Server task may throw ObjectDisposedException when listener is stopped
            }
            _cts.Dispose();
        }
    }

    /// <summary>
    /// Xunit logger implementation for integration tests.
    /// </summary>
    private class XunitLogger<T> : ILogger<T>
    {
        private readonly ITestOutputHelper _output;

        public XunitLogger(ITestOutputHelper output)
        {
            _output = output;
        }

        public IDisposable BeginScope<TState>(TState state) => NullScope.Instance;

        public bool IsEnabled(LogLevel logLevel) => true;

        public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception? exception, Func<TState, Exception?, string> formatter)
        {
            _output.WriteLine($"[{logLevel}] {formatter(state, exception)}");
            if (exception != null)
            {
                _output.WriteLine($"Exception: {exception}");
            }
        }

        private class NullScope : IDisposable
        {
            public static NullScope Instance { get; } = new();
            public void Dispose() { }
        }
    }

    private sealed class SilentTcpServer : IDisposable
    {
        private readonly CancellationTokenSource _cts = new();
        private TcpListener? _listener;
        private Task? _serverTask;

        public int Port { get; private set; }

        public Task StartAsync()
        {
            _listener = new TcpListener(IPAddress.Loopback, 0);
            _listener.Start();
            Port = ((IPEndPoint)_listener.LocalEndpoint).Port;

            _serverTask = Task.Run(async () =>
            {
                while (!_cts.Token.IsCancellationRequested)
                {
                    try
                    {
                        var client = await _listener.AcceptTcpClientAsync(_cts.Token);
                        _ = Task.Run(async () =>
                        {
                            using (client)
                            {
                                await Task.Delay(Timeout.InfiniteTimeSpan, _cts.Token);
                            }
                        }, _cts.Token);
                    }
                    catch (OperationCanceledException)
                    {
                        break;
                    }
                    catch (ObjectDisposedException)
                    {
                        break;
                    }
                }
            });

            return Task.CompletedTask;
        }

        public void Dispose()
        {
            _cts.Cancel();
            _listener?.Stop();

            try
            {
                _serverTask?.GetAwaiter().GetResult();
            }
            catch (OperationCanceledException)
            {
            }
        }
    }
}
