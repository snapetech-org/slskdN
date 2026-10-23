// <copyright file="WebSocketTransport.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using System;
using System.IO;
using System.Net.WebSockets;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using System.Text.Json;
using System.Buffers;
using System.Collections.Concurrent;
using WebSocketOptions = slskd.Common.Security.WebSocketTransportOptions;

namespace slskd.Common.Security;

/// <summary>
/// WebSocket transport for DPI circumvention.
/// Routes traffic through WebSocket connections that appear as normal web traffic.
/// </summary>
public sealed class WebSocketTransport : IAnonymityTransport, IDisposable
{
    private readonly WebSocketOptions _options;
    private readonly ILogger<WebSocketTransport> _logger;

    private readonly AnonymityTransportStatus _status = new();
    private readonly object _statusLock = new();

    // Connection pool for reuse
    private readonly ConcurrentDictionary<string, WebSocketConnection> _connectionPool = new();
    private readonly SemaphoreSlim _connectionPoolLock = new(1, 1);

    /// <summary>
    /// Initializes a new instance of the <see cref="WebSocketTransport"/> class.
    /// </summary>
    /// <param name="options">The WebSocket transport options.</param>
    /// <param name="logger">The logger.</param>
    public WebSocketTransport(WebSocketOptions options, ILogger<WebSocketTransport> logger)
    {
        _options = options ?? throw new ArgumentNullException(nameof(options));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));

    }

    /// <summary>
    /// Gets the transport type.
    /// </summary>
    public AnonymityTransportType TransportType => AnonymityTransportType.WebSocket;

    /// <summary>
    /// Checks if WebSocket transport is available.
    /// </summary>
    /// <param name="cancellationToken">The cancellation token.</param>
    /// <returns>True if WebSocket transport is available, false otherwise.</returns>
    public async Task<bool> IsAvailableAsync(CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();

        try
        {
            if (!TryGetServerUri(out var uri, out var validationError))
            {
                lock (_statusLock)
                {
                    _status.IsAvailable = false;
                    _status.LastError = validationError;
                }

                _logger.LogWarning("WebSocket transport not available: {Error}", validationError);
                return false;
            }

            using var client = new ClientWebSocket();
            AddSubProtocolIfConfigured(client);

            using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            cts.CancelAfter(TimeSpan.FromSeconds(5)); // Quick connectivity test

            await client.ConnectAsync(uri, cts.Token);

            lock (_statusLock)
            {
                _status.IsAvailable = true;
                _status.LastError = null;
                _status.LastSuccessfulConnection = DateTimeOffset.UtcNow;
            }

            _logger.LogDebug("WebSocket transport is available at {Url}", _options.ServerUrl);
            return true;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            lock (_statusLock)
            {
                _status.IsAvailable = false;
                _status.LastError = "WebSocket transport unavailable";
            }

            _logger.LogWarning(ex, "WebSocket transport not available at {Url}", _options.ServerUrl);
            return false;
        }
    }

    /// <summary>
    /// Establishes a connection through WebSocket tunnel.
    /// </summary>
    /// <param name="host">The target host.</param>
    /// <param name="port">The target port.</param>
    /// <param name="cancellationToken">The cancellation token.</param>
    /// <returns>A stream for the tunneled connection.</returns>
    public async Task<Stream> ConnectAsync(string host, int port, CancellationToken cancellationToken = default)
    {
        return await ConnectAsync(host, port, null, cancellationToken);
    }

    /// <summary>
    /// Establishes a connection through WebSocket tunnel with stream isolation.
    /// </summary>
    /// <param name="host">The target host.</param>
    /// <param name="port">The target port.</param>
    /// <param name="isolationKey">Optional key for stream isolation.</param>
    /// <param name="cancellationToken">The cancellation token.</param>
    /// <returns>A stream for the tunneled connection.</returns>
    public async Task<Stream> ConnectAsync(string host, int port, string? isolationKey, CancellationToken cancellationToken = default)
    {
        var validationFailure = false;

        lock (_statusLock)
        {
            _status.TotalConnectionsAttempted++;
        }

        try
        {
            if (!TryGetServerUri(out var uri, out var validationError))
            {
                lock (_statusLock)
                {
                    _status.LastError = validationError;
                }

                validationFailure = true;
                throw new InvalidOperationException(validationError);
            }

            // Try to reuse existing connection from pool
            var connectionKey = $"{host}:{port}:{isolationKey ?? "default"}";
            WebSocketConnection? pooledConnection = null;

            await _connectionPoolLock.WaitAsync(cancellationToken);
            try
            {
                if (_connectionPool.TryGetValue(connectionKey, out pooledConnection))
                {
                    _connectionPool.TryRemove(connectionKey, out _);
                }
            }
            finally
            {
                _connectionPoolLock.Release();
            }

            if (pooledConnection != null && pooledConnection.IsUsable())
            {
                _logger.LogDebug("Reusing pooled WebSocket connection for {Host}:{Port}", host, port);
                return new WebSocketStream(pooledConnection.WebSocket, pooledConnection, () => _ = ReturnToPool(connectionKey, pooledConnection));
            }

            // Create new WebSocket connection
            var client = new ClientWebSocket();
            AddSubProtocolIfConfigured(client);

            // Add custom headers to appear as normal web traffic
            if (_options.CustomHeaders != null)
            {
                foreach (var header in _options.CustomHeaders)
                {
                    client.Options.SetRequestHeader(header.Key, header.Value);
                }
            }

            await client.ConnectAsync(uri, cancellationToken);

            // Send tunnel request
            var tunnelRequest = new TunnelRequest
            {
                Host = host,
                Port = port,
                IsolationKey = isolationKey
            };

            var requestJson = JsonSerializer.Serialize(tunnelRequest);
            var requestBytes = System.Text.Encoding.UTF8.GetBytes(requestJson);

            await client.SendAsync(requestBytes, WebSocketMessageType.Text, true, cancellationToken);

            // Wait for tunnel acknowledgment
            var buffer = ArrayPool<byte>.Shared.Rent(1024);
            try
            {
                var result = await client.ReceiveAsync(new ArraySegment<byte>(buffer), cancellationToken);
                var responseJson = System.Text.Encoding.UTF8.GetString(buffer, 0, result.Count);
                var response = JsonSerializer.Deserialize<TunnelResponse>(responseJson);

                if (response?.Success != true)
                {
                    throw new Exception($"Tunnel request failed: {response?.Error ?? "Unknown error"}");
                }
            }
            finally
            {
                ArrayPool<byte>.Shared.Return(buffer);
            }

            var connection = new WebSocketConnection(client, DateTimeOffset.UtcNow);

            lock (_statusLock)
            {
                _status.TotalConnectionsSuccessful++;
                _status.ActiveConnections++;
                _status.LastSuccessfulConnection = DateTimeOffset.UtcNow;
            }

            _logger.LogDebug("Established WebSocket tunnel to {Host}:{Port} via {Url}", host, port, _options.ServerUrl);
            return new WebSocketStream(client, connection, () =>
            {
                lock (_statusLock)
                {
                    _status.ActiveConnections = Math.Max(0, _status.ActiveConnections - 1);
                }

                _ = ReturnToPool(connectionKey, connection);
            });
        }
        catch (Exception ex)
        {
            lock (_statusLock)
            {
                if (!validationFailure)
                {
                    _status.LastError = "WebSocket tunnel connection failed";
                }
            }

            _logger.LogError(ex, "Failed to establish WebSocket tunnel to {Host}:{Port}", host, port);
            throw;
        }
    }

    public void Dispose()
    {
        _connectionPoolLock.Dispose();

        foreach (var connection in _connectionPool.Values)
        {
            connection.Dispose();
        }

        _connectionPool.Clear();
    }

    /// <summary>
    /// Gets the current status of the WebSocket transport.
    /// </summary>
    public AnonymityTransportStatus GetStatus()
    {
        lock (_statusLock)
        {
            return new AnonymityTransportStatus
            {
                IsAvailable = _status.IsAvailable,
                LastError = _status.LastError,
                LastSuccessfulConnection = _status.LastSuccessfulConnection,
                ActiveConnections = _status.ActiveConnections,
                TotalConnectionsAttempted = _status.TotalConnectionsAttempted,
                TotalConnectionsSuccessful = _status.TotalConnectionsSuccessful,
            };
        }
    }

    private async Task ReturnToPool(string key, WebSocketConnection connection)
    {
        if (!connection.IsUsable())
        {
            connection.Dispose();
            return;
        }

        await _connectionPoolLock.WaitAsync();
        try
        {
            // Only keep a limited number of connections in pool
            if (_connectionPool.Count < _options.MaxPooledConnections)
            {
                _connectionPool[key] = connection;
                _logger.LogTrace("Returned WebSocket connection to pool for {Key}", key);
            }
            else
            {
                connection.Dispose();
                _logger.LogTrace("Connection pool full, disposing WebSocket connection for {Key}", key);
            }
        }
        finally
        {
            _connectionPoolLock.Release();
        }
    }

    private void AddSubProtocolIfConfigured(ClientWebSocket client)
    {
        if (!string.IsNullOrWhiteSpace(_options.SubProtocol))
        {
            client.Options.AddSubProtocol(_options.SubProtocol);
        }
    }

    private bool TryGetServerUri(out Uri uri, out string validationError)
    {
        if (!Uri.TryCreate(_options.ServerUrl, UriKind.Absolute, out uri!))
        {
            validationError = "WebSocket server URL is not a valid absolute URI";
            return false;
        }

        if (!string.Equals(uri.Scheme, "ws", StringComparison.OrdinalIgnoreCase) &&
            !string.Equals(uri.Scheme, "wss", StringComparison.OrdinalIgnoreCase))
        {
            validationError = "WebSocket server URL must use a supported WebSocket scheme.";
            return false;
        }

        // Cleartext WebSockets are safe only for same-host local development. Remote
        // tunnels can carry user traffic, so they must use TLS to prevent interception.
        if (string.Equals(uri.Scheme, "ws", StringComparison.OrdinalIgnoreCase) && !uri.IsLoopback)
        {
            validationError = "Unencrypted WebSocket server URLs must target loopback; use wss:// for remote servers";
            return false;
        }

        validationError = string.Empty;
        return true;
    }

    /// <summary>
    /// WebSocket tunnel request message.
    /// </summary>
    private record TunnelRequest
    {
        public string Host { get; init; } = string.Empty;
        public int Port { get; init; }
        public string? IsolationKey { get; init; }
    }

    /// <summary>
    /// WebSocket tunnel response message.
    /// </summary>
    private record TunnelResponse
    {
        public bool Success { get; init; }
        public string? Error { get; init; }
    }

    /// <summary>
    /// Represents a pooled WebSocket connection.
    /// </summary>
    private class WebSocketConnection : IDisposable
    {
        public ClientWebSocket WebSocket { get; }
        public DateTimeOffset CreatedAt { get; }
        private bool _disposed;

        public WebSocketConnection(ClientWebSocket webSocket, DateTimeOffset createdAt)
        {
            WebSocket = webSocket;
            CreatedAt = createdAt;
        }

        public bool IsUsable()
        {
            return !_disposed &&
                   WebSocket.State == WebSocketState.Open &&
                   DateTimeOffset.UtcNow - CreatedAt < TimeSpan.FromMinutes(5); // Max connection age
        }

        public void Dispose()
        {
            if (_disposed) return;
            _disposed = true;

            try
            {
                WebSocket.Dispose();
            }
            catch
            {
                // Ignore disposal errors
            }
        }
    }

    /// <summary>
    /// Stream wrapper for WebSocket connections.
    /// </summary>
    private class WebSocketStream : Stream
    {
        private readonly ClientWebSocket _webSocket;
        private readonly WebSocketConnection _connection;
        private readonly Action _onDispose;
        private bool _disposed;

        public WebSocketStream(ClientWebSocket webSocket, WebSocketConnection connection, Action onDispose)
        {
            _webSocket = webSocket;
            _connection = connection;
            _onDispose = onDispose;
        }

        public override bool CanRead => true;
        public override bool CanWrite => true;
        public override bool CanSeek => false;
        public override long Length => throw new NotSupportedException();
        public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }

        public override async Task<int> ReadAsync(byte[] buffer, int offset, int count, CancellationToken cancellationToken)
        {
            var segment = new ArraySegment<byte>(buffer, offset, count);
            var result = await _webSocket.ReceiveAsync(segment, cancellationToken);

            if (result.MessageType == WebSocketMessageType.Close)
            {
                return 0; // EOF
            }

            return result.Count;
        }

        public override async Task WriteAsync(byte[] buffer, int offset, int count, CancellationToken cancellationToken)
        {
            var segment = new ArraySegment<byte>(buffer, offset, count);
            await _webSocket.SendAsync(segment, WebSocketMessageType.Binary, true, cancellationToken);
        }

        public override void Flush() { }

        public override int Read(byte[] buffer, int offset, int count) =>
            ReadAsync(buffer, offset, count).ConfigureAwait(false).GetAwaiter().GetResult();

        public override void Write(byte[] buffer, int offset, int count) =>
            WriteAsync(buffer, offset, count).ConfigureAwait(false).GetAwaiter().GetResult();

        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();

        protected override void Dispose(bool disposing)
        {
            if (_disposed) return;
            _disposed = true;

            if (disposing)
            {
                try
                {
                    _onDispose();
                }
                catch
                {
                    // noop
                }
            }

            base.Dispose(disposing);
        }
    }
}
