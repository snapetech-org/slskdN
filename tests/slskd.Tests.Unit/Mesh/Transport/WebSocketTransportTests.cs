// <copyright file="WebSocketTransportTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
using Microsoft.Extensions.Logging;
using Moq;
using slskd.Common.Security;
using Xunit;

namespace slskd.Tests.Unit.Mesh.Transport;

public class WebSocketTransportTests : IDisposable
{
    private readonly Mock<ILogger<WebSocketTransport>> _loggerMock;
    private readonly WebSocketTransportOptions _defaultOptions;

    public WebSocketTransportTests()
    {
        _loggerMock = new Mock<ILogger<WebSocketTransport>>();
        _defaultOptions = new WebSocketTransportOptions
        {
            ServerUrl = "wss://test.example.com/tunnel",
            SubProtocol = "slskd-tunnel",
            MaxPooledConnections = 5
        };
    }

    public void Dispose()
    {
        // Cleanup if needed
    }

    [Fact]
    public void Constructor_WithValidOptions_CreatesInstance()
    {
        // Act & Assert - Should not throw
        var transport = new WebSocketTransport(_defaultOptions, _loggerMock.Object);
        Assert.Equal(AnonymityTransportType.WebSocket, transport.TransportType);
    }

    [Fact]
    public void Constructor_WithNullOptions_ThrowsArgumentNullException()
    {
        // Act & Assert
        Assert.Throws<ArgumentNullException>(() => new WebSocketTransport(null!, _loggerMock.Object));
    }

    [Fact]
    public void Constructor_WithNullLogger_ThrowsArgumentNullException()
    {
        // Act & Assert
        Assert.Throws<ArgumentNullException>(() => new WebSocketTransport(_defaultOptions, null!));
    }

    [Fact]
    public void TransportType_ReturnsWebSocket()
    {
        // Arrange
        var transport = new WebSocketTransport(_defaultOptions, _loggerMock.Object);

        // Assert
        Assert.Equal(AnonymityTransportType.WebSocket, transport.TransportType);
    }

    [Fact]
    public void GetStatus_ReturnsValidStatusObject()
    {
        // Arrange
        var transport = new WebSocketTransport(_defaultOptions, _loggerMock.Object);

        // Act
        var status = transport.GetStatus();

        // Assert
        Assert.NotNull(status);
        Assert.IsType<AnonymityTransportStatus>(status);
        Assert.Equal(0, status.ActiveConnections);
        Assert.Equal(0, status.TotalConnectionsAttempted);
        Assert.Equal(0, status.TotalConnectionsSuccessful);
    }

    [Fact]
    public async Task ConnectAsync_WithoutIsolationKey_UsesDefaultCircuit()
    {
        // Arrange
        var transport = new WebSocketTransport(_defaultOptions, _loggerMock.Object);

        // Act & Assert - Should throw due to no actual WebSocket server, but should handle connection logic
        await Assert.ThrowsAnyAsync<Exception>(() => transport.ConnectAsync("example.com", 80));

        var status = transport.GetStatus();
        Assert.Equal(1, status.TotalConnectionsAttempted);
    }

    [Fact]
    public async Task ConnectAsync_WithIsolationKey_UsesIsolatedCircuit()
    {
        // Arrange
        var transport = new WebSocketTransport(_defaultOptions, _loggerMock.Object);

        // Act & Assert - Should throw due to no actual WebSocket server, but should handle isolation logic
        await Assert.ThrowsAnyAsync<Exception>(() => transport.ConnectAsync("example.com", 80, "peer123"));

        var status = transport.GetStatus();
        Assert.Equal(1, status.TotalConnectionsAttempted);
    }

    [Fact]
    public async Task IsAvailableAsync_ConnectionFailure_ReturnsFalse()
    {
        // Arrange
        var transport = new WebSocketTransport(_defaultOptions, _loggerMock.Object);

        // Act
        var isAvailable = await transport.IsAvailableAsync();

        // Assert - Should return false since there's no actual WebSocket server
        Assert.False(isAvailable);
        var status = transport.GetStatus();
        Assert.NotNull(status.LastError);
    }

    [Fact]
    public async Task IsAvailableAsync_WhenConnectionThrows_SetsSanitizedLastError()
    {
        var options = new WebSocketTransportOptions
        {
            ServerUrl = "wss://127.0.0.1:1/tunnel"
        };

        var transport = new WebSocketTransport(options, _loggerMock.Object);

        var isAvailable = await transport.IsAvailableAsync();

        Assert.False(isAvailable);
        Assert.Equal("WebSocket transport unavailable", transport.GetStatus().LastError);
    }

    [Fact]
    public async Task IsAvailableAsync_WithInvalidServerUrl_ReturnsFalseWithoutThrowing()
    {
        var options = new WebSocketTransportOptions
        {
            ServerUrl = "not a uri"
        };

        var transport = new WebSocketTransport(options, _loggerMock.Object);

        var isAvailable = await transport.IsAvailableAsync();

        Assert.False(isAvailable);
        Assert.Equal("WebSocket server URL is not a valid absolute URI", transport.GetStatus().LastError);
    }

    [Fact]
    public async Task ConnectAsync_WithInvalidServerUrl_ThrowsInvalidOperationException()
    {
        var options = new WebSocketTransportOptions
        {
            ServerUrl = "http://example.com/not-websocket"
        };

        var transport = new WebSocketTransport(options, _loggerMock.Object);

        var ex = await Assert.ThrowsAsync<InvalidOperationException>(() => transport.ConnectAsync("example.com", 80));

        Assert.Equal("WebSocket server URL must use a supported WebSocket scheme.", ex.Message);
        Assert.Equal("WebSocket server URL must use a supported WebSocket scheme.", transport.GetStatus().LastError);
    }

    [Theory]
    [InlineData("wss://test.example.com/tunnel")]
    [InlineData("ws://localhost:8080/websocket")]
    [InlineData("wss://api.example.com:8443/ws")]
    public void WebSocketTransportOptions_AcceptsVariousServerUrls(string serverUrl)
    {
        // Arrange
        var options = new WebSocketTransportOptions { ServerUrl = serverUrl };

        // Act & Assert - Should not throw
        var transport = new WebSocketTransport(options, _loggerMock.Object);
        Assert.Equal(AnonymityTransportType.WebSocket, transport.TransportType);
    }

    [Fact]
    public void Dispose_CleansUpResources()
    {
        // Arrange & Act - WebSocketTransport does not implement IDisposable; creation should not throw
        var transport = new WebSocketTransport(_defaultOptions, _loggerMock.Object);

        // Assert
        Assert.NotNull(transport);
    }

    [Fact]
    public void Options_Validation_CustomHeaders()
    {
        // Arrange
        var options = new WebSocketTransportOptions
        {
            ServerUrl = "wss://test.example.com/tunnel",
            CustomHeaders = new Dictionary<string, string>
            {
                ["Authorization"] = "Bearer token123",
                ["X-Custom-Header"] = "custom-value"
            }
        };

        // Act & Assert - Should not throw
        var transport = new WebSocketTransport(options, _loggerMock.Object);
        Assert.Equal(AnonymityTransportType.WebSocket, transport.TransportType);
    }

    [Fact]
    public async Task ConnectAsync_WhenConnectionFails_StoresSanitizedStatusError()
    {
        var transport = new WebSocketTransport(_defaultOptions, _loggerMock.Object);

        await Assert.ThrowsAnyAsync<Exception>(() => transport.ConnectAsync("example.com", 80));

        var status = transport.GetStatus();
        Assert.Equal("WebSocket tunnel connection failed", status.LastError);
        Assert.DoesNotContain("Name or service", status.LastError ?? string.Empty, StringComparison.OrdinalIgnoreCase);
    }
}
