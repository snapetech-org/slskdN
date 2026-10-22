// <copyright file="CapabilityFileServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Capabilities;

using System.Net;
using System.Text;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Moq;
using slskd.Capabilities;
using slskd.Tests.Unit.TestHelpers;
using Soulseek;
using Xunit;

public sealed class CapabilityFileServiceTests
{
    [Fact]
    public async Task RequestCapabilityFileAsync_UsesRuntimeCapabilityRegistryBeforeBrowse()
    {
        var registry = new PeerCapabilityRegistry();
        registry.Update(
            "alice",
            new IPEndPoint(IPAddress.Loopback, 50305),
            new PeerCapabilityEnvelope(
                PeerCapabilityMessageType.Hello,
                new PeerCapabilityDescriptor("peer-id", new[] { "mesh_sync", "swarm_download" }, overlayPort: 50305)));
        var client = new Mock<ISoulseekClient>();
        client.SetupGet(soulseekClient => soulseekClient.PeerCapabilities).Returns(registry);
        var capabilityService = new Mock<ICapabilityService>();
        var service = new CapabilityFileService(
            Mock.Of<ILogger<CapabilityFileService>>(),
            capabilityService.Object,
            client.Object);

        var content = await service.RequestCapabilityFileAsync("alice");

        Assert.NotNull(content);
        Assert.Equal("runtime-capability-v1", content!.Version);
        Assert.True(content.Capabilities.HasFlag(PeerCapabilityFlags.SupportsMeshSync));
        Assert.True(content.Capabilities.HasFlag(PeerCapabilityFlags.SupportsSwarm));
        client.Verify(soulseekClient => soulseekClient.BrowseAsync(
            It.IsAny<string>(),
            It.IsAny<BrowseOptions>(),
            It.IsAny<CancellationToken>()), Times.Never);
        capabilityService.Verify(service => service.SetPeerCapabilities(
            "alice",
            It.Is<PeerCapabilities>(capabilities => capabilities.CanMeshSync && capabilities.CanSwarm)), Times.Once);
    }

    [Fact]
    public void ParseCapabilityFile_AcceptsTrimmedIdentityWithoutFlags()
    {
        var service = new CapabilityFileService(
            Mock.Of<ILogger<CapabilityFileService>>(),
            Mock.Of<ICapabilityService>(),
            Mock.Of<ISoulseekClient>());

        var content = service.ParseCapabilityFile("""
            {
              "client": " slskdn ",
              "version": " 1.2.3 ",
              "protocolVersion": 1,
              "capabilities": 0,
              "features": []
            }
            """u8.ToArray());

        Assert.NotNull(content);
        Assert.Equal("slskdn", content!.Client);
        Assert.Equal("1.2.3", content.Version);
        Assert.Equal(PeerCapabilityFlags.None, content.Capabilities);
    }

    [Fact]
    public void ParseCapabilityFile_DerivesCapabilitiesFromFeatures()
    {
        var service = new CapabilityFileService(
            Mock.Of<ILogger<CapabilityFileService>>(),
            Mock.Of<ICapabilityService>(),
            Mock.Of<ISoulseekClient>());

        var content = service.ParseCapabilityFile("""
            {
              "client": "slskdn",
              "version": "1.2.3",
              "protocolVersion": 1,
              "capabilities": 0,
              "features": ["mesh_sync", "swarm_download", "mesh_sync"]
            }
            """u8.ToArray());

        Assert.NotNull(content);
        Assert.True(content!.Capabilities.HasFlag(PeerCapabilityFlags.SupportsMeshSync));
        Assert.True(content.Capabilities.HasFlag(PeerCapabilityFlags.SupportsSwarm));
    }

    [Fact]
    public void IsCapabilityFileRequest_TrimsAndNormalizesSeparators()
    {
        var service = new CapabilityFileService(
            Mock.Of<ILogger<CapabilityFileService>>(),
            Mock.Of<ICapabilityService>(),
            Mock.Of<ISoulseekClient>());

        Assert.True(service.IsCapabilityFileRequest("  @@slskdn/__caps__.json  "));
    }

    [Fact]
    public async Task RequestCapabilityFileAsync_UsesOriginalRemoteFilenameForDownload()
    {
        var client = new Mock<ISoulseekClient>();
        var capabilityJson = """
            {
              "client": "slskdn",
              "version": "1.2.3",
              "protocolVersion": 1,
              "capabilities": 0,
              "features": []
            }
            """;
        client
            .Setup(soulseekClient => soulseekClient.BrowseAsync("alice", It.IsAny<BrowseOptions>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new BrowseResponse(new[]
            {
                new Directory("@@slskdn", new[]
                {
                    new File(1, "__caps__.json", capabilityJson.Length, "json"),
                }),
            }));

        string? capturedRemoteFilename = null;
        client
            .Setup(soulseekClient => soulseekClient.DownloadAsync(
                "alice",
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (string username, string remoteFilename, Func<Task<Stream>> outputStreamFactory, long size, long startOffset, int? token, TransferOptions options, CancellationToken cancellationToken) =>
            {
                capturedRemoteFilename = remoteFilename;
                await using var stream = await outputStreamFactory();
                var bytes = Encoding.UTF8.GetBytes(capabilityJson);
                await stream.WriteAsync(bytes);
                return (Transfer)null!;
            });

        var service = new CapabilityFileService(
            Mock.Of<ILogger<CapabilityFileService>>(),
            Mock.Of<ICapabilityService>(),
            client.Object);

        var content = await service.RequestCapabilityFileAsync("alice");

        Assert.NotNull(content);
        Assert.Equal("@@slskdn\\__caps__.json", capturedRemoteFilename);
    }

    [Fact]
    public async Task RequestCapabilityFileAsync_EscapesPeerAndCapabilityMetadataOnlyInLogs()
    {
        const string username = "alice\r\nforged peer";
        const string remoteDirectory = "folder\r\nforged\\@@slskdn";
        const string remoteFilename = "folder\r\nforged\\@@slskdn\\__caps__.json";
        const string capabilityJson = """
            {
              "client": "slskdn\r\nforged client",
              "version": "1.2.3\r\nforged version",
              "protocolVersion": 1,
              "capabilities": 0,
              "features": []
            }
            """;

        var client = new Mock<ISoulseekClient>();
        client
            .Setup(soulseekClient => soulseekClient.BrowseAsync(username, It.IsAny<BrowseOptions>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new BrowseResponse(new[]
            {
                new Directory(remoteDirectory, new[]
                {
                    new File(1, "__caps__.json", capabilityJson.Length, "json"),
                }),
            }));

        string? capturedUsername = null;
        string? capturedRemoteFilename = null;
        client
            .Setup(soulseekClient => soulseekClient.DownloadAsync(
                username,
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (string requestedUsername, string requestedFilename, Func<Task<Stream>> outputStreamFactory, long size, long startOffset, int? token, TransferOptions options, CancellationToken cancellationToken) =>
            {
                capturedUsername = requestedUsername;
                capturedRemoteFilename = requestedFilename;
                await using var stream = await outputStreamFactory();
                await stream.WriteAsync(Encoding.UTF8.GetBytes(capabilityJson));
                return (Transfer)null!;
            });

        var fileLogger = new CapturingLogger<CapabilityFileService>();
        var capabilityLogger = new CapturingLogger<CapabilityService>();
        var capabilityService = new CapabilityService(capabilityLogger);
        var service = new CapabilityFileService(fileLogger, capabilityService, client.Object);

        var content = await service.RequestCapabilityFileAsync(username);

        Assert.NotNull(content);
        Assert.Equal("slskdn\r\nforged client", content!.Client);
        Assert.Equal("1.2.3\r\nforged version", content.Version);
        Assert.Equal(username, capturedUsername);
        Assert.Equal(remoteFilename, capturedRemoteFilename);
        Assert.Equal(username, capabilityService.GetPeerCapabilities(username)!.Username);

        var entries = fileLogger.Entries.Concat(capabilityLogger.Entries).ToArray();
        var messages = string.Join(Environment.NewLine, entries.Select(entry => entry.Message));
        Assert.Contains("alice\\r\\nforged peer", messages);
        Assert.Contains("slskdn\\r\\nforged client", messages);
        Assert.Contains("1.2.3\\r\\nforged version", messages);
        Assert.All(entries, entry =>
        {
            Assert.DoesNotContain("\r", entry.Message);
            Assert.DoesNotContain("\n", entry.Message);
            Assert.Null(entry.Exception);
        });
    }

    [Fact]
    public async Task RequestCapabilityFileAsync_EscapesDownloadExceptionDetailsWithoutChangingRequest()
    {
        const string username = "alice\r\nforged peer";
        const string remoteFilename = "@@slskdn\\__caps__.json";
        const string capabilityJson = "{}";
        var client = new Mock<ISoulseekClient>();
        client
            .Setup(soulseekClient => soulseekClient.BrowseAsync(username, It.IsAny<BrowseOptions>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new BrowseResponse(new[]
            {
                new Directory("@@slskdn", new[]
                {
                    new File(1, "__caps__.json", capabilityJson.Length, "json"),
                }),
            }));

        string? capturedUsername = null;
        string? capturedRemoteFilename = null;
        client
            .Setup(soulseekClient => soulseekClient.DownloadAsync(
                username,
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns((string requestedUsername, string requestedFilename, Func<Task<Stream>> outputStreamFactory, long size, long startOffset, int? token, TransferOptions options, CancellationToken cancellationToken) =>
            {
                capturedUsername = requestedUsername;
                capturedRemoteFilename = requestedFilename;
                return Task.FromException<Transfer>(new InvalidOperationException("remote\r\nfailure"));
            });

        var logger = new CapturingLogger<CapabilityFileService>();
        var service = new CapabilityFileService(
            logger,
            Mock.Of<ICapabilityService>(),
            client.Object);

        var content = await service.RequestCapabilityFileAsync(username);

        Assert.Null(content);
        Assert.Equal(username, capturedUsername);
        Assert.Equal(remoteFilename, capturedRemoteFilename);
        Assert.Contains(logger.Entries, entry => entry.Message.Contains("remote\\r\\nfailure", StringComparison.Ordinal));
        Assert.All(logger.Entries, entry =>
        {
            Assert.DoesNotContain("\r", entry.Message);
            Assert.DoesNotContain("\n", entry.Message);
            Assert.Null(entry.Exception);
        });
    }

    [Fact]
    public async Task RequestCapabilityFileAsync_EscapesRemotePathWhenGlobalPolicyBlocksFetch()
    {
        const string username = "alice\r\nforged peer";
        const string remoteDirectory = "folder\r\nforged\\@@slskdn";
        var client = new Mock<ISoulseekClient>();
        client
            .Setup(soulseekClient => soulseekClient.BrowseAsync(username, It.IsAny<BrowseOptions>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new BrowseResponse(new[]
            {
                new Directory(remoteDirectory, new[]
                {
                    new File(1, "__caps__.json", 10, "json"),
                }),
            }));

        var optionsMonitor = new Mock<IOptionsMonitor<slskd.Options>>();
        optionsMonitor.SetupGet(monitor => monitor.CurrentValue).Returns(new slskd.Options
        {
            Filters = new slskd.Options.FiltersOptions
            {
                Download = new slskd.Options.FiltersOptions.DownloadFilterOptions
                {
                    Exclude = new[] { "__caps__" },
                },
            },
        });

        var logger = new CapturingLogger<CapabilityFileService>();
        var service = new CapabilityFileService(
            logger,
            Mock.Of<ICapabilityService>(),
            client.Object,
            optionsMonitor.Object);

        var content = await service.RequestCapabilityFileAsync(username);

        Assert.Null(content);
        var messages = string.Join(Environment.NewLine, logger.Entries.Select(entry => entry.Message));
        Assert.Contains("folder\\r\\nforged", messages);
        Assert.All(logger.Entries, entry =>
        {
            Assert.DoesNotContain("\r", entry.Message);
            Assert.DoesNotContain("\n", entry.Message);
        });
        client.Verify(soulseekClient => soulseekClient.DownloadAsync(
            username,
            It.IsAny<string>(),
            It.IsAny<Func<Task<Stream>>>(),
            It.IsAny<long>(),
            It.IsAny<long>(),
            It.IsAny<int?>(),
            It.IsAny<TransferOptions>(),
            It.IsAny<CancellationToken>()), Times.Never);
    }
}
