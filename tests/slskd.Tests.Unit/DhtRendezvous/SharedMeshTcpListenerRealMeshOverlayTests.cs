// <copyright file="SharedMeshTcpListenerRealMeshOverlayTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.DhtRendezvous;

using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography.X509Certificates;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using slskd.PodCore;
using Microsoft.Extensions.Options;
using slskd.DhtRendezvous;
using slskd.DhtRendezvous.Messages;
using slskd.DhtRendezvous.Search;
using slskd.DhtRendezvous.Security;
using slskd.Mesh;
using slskd.Mesh.Messages;
using slskd.SoulseekRuntime;
using Xunit;
using Moq;
using System.Text.Json;
using slskd.ListeningParty;
using slskd.Streaming;
using slskd.Mesh.ServiceFabric;
using slskd.Mesh.ServiceFabric.Services;
using slskd.Mesh.Overlay;

/// <summary>
/// Proves the mesh-overlay half of port sharing end to end using the REAL production classes on
/// both sides -- a real <see cref="MeshOverlayServer"/> (real self-signed certificates, real TLS,
/// real mesh_hello/mesh_hello_ack protocol handling) behind a real <see cref="SharedMeshTcpListener"/>,
/// connected to by the real client-side <see cref="MeshOverlayConnection.ConnectAsync"/> +
/// <see cref="MeshOverlayConnection.PerformClientHandshakeAsync"/> path that a genuine slskdN peer
/// uses. Nothing here is mocked except the few collaborators (outbound reciprocal connector, mesh
/// sync, mesh search RPC) that this specific flow never touches.
/// </summary>
public sealed class SharedMeshTcpListenerRealMeshOverlayTests : IDisposable
{
    private readonly string _serverAppDirectory = Directory.CreateTempSubdirectory("slskdn-mesh-server-").FullName;
    private readonly string _clientAppDirectory = Directory.CreateTempSubdirectory("slskdn-mesh-client-").FullName;

    [Fact]
    public async Task RealClientHandshake_ThroughSharedTcpListener_IsAcceptedByRealMeshOverlayServer()
    {
        var dhtOptions = new DhtRendezvousOptions { Enabled = true };
        var meshOverlayServer = new MeshOverlayServer(
            NullLogger<MeshOverlayServer>.Instance,
            new StaticOptionsMonitor(new slskd.Options { Soulseek = new slskd.Options.SoulseekOptions { Username = "server-peer" } }),
            new CertificateManager(NullLogger<CertificateManager>.Instance, _serverAppDirectory),
            new CertificatePinStore(NullLogger<CertificatePinStore>.Instance, _serverAppDirectory),
            new OverlayRateLimiter(),
            new OverlayBlocklist(NullLogger<OverlayBlocklist>.Instance),
            new MeshNeighborRegistry(NullLogger<MeshNeighborRegistry>.Instance),
            new NoOpMeshOverlayConnector(),
            new NoOpMeshSyncService(),
            new NoOpMeshSearchRpcHandler(),
            new MeshOverlayRequestRouter(),
            dhtOptions);

        var optionsAtStartup = new OptionsAtStartup
        {
            Soulseek = new slskd.Options.SoulseekOptions
            {
                ListenIpAddress = "127.0.0.1",
                ListenPort = 0, // OS-assigned ephemeral port
            },
        };

        var sharedListener = new SharedMeshTcpListener(
            NullLogger<SharedMeshTcpListener>.Instance,
            optionsAtStartup,
            dhtOptions,
            new FedTcpListener(), // unused by this test: only the mesh-overlay TLS path is exercised
            meshOverlayServer);

        await meshOverlayServer.StartAsync();
        await sharedListener.StartAsync(CancellationToken.None);

        try
        {
            var boundEndPoint = await WaitForBoundEndPointAsync(sharedListener);

            var clientCertificateManager = new CertificateManager(NullLogger<CertificateManager>.Instance, _clientAppDirectory);
            var clientCertificate = clientCertificateManager.GetOrCreateServerCertificate();

            await using var connection = await MeshOverlayConnection.ConnectAsync(boundEndPoint, clientCertificate);
            var ack = await connection.PerformClientHandshakeAsync("client-peer", overlayPort: 12345);

            Assert.NotNull(ack);
            Assert.True(connection.IsHandshakeComplete);

            // Real production accounting on the real server, proving the connection was actually
            // accepted and processed -- not just that the TCP connect succeeded.
            await WaitUntilAsync(() => meshOverlayServer.TotalConnectionsAccepted == 1, TimeSpan.FromSeconds(15));
            Assert.Equal(1, meshOverlayServer.TotalConnectionsAccepted);
            Assert.Equal(0, meshOverlayServer.TotalConnectionsRejected);
            Assert.Equal(1, meshOverlayServer.ActiveConnections);
        }
        finally
        {
            await sharedListener.StopAsync(CancellationToken.None);
            await meshOverlayServer.StopAsync();
        }
    }

    [Theory]
    [InlineData(10, true, false)]
    [InlineData(11, false, false)]
    [InlineData(10, true, true)]
    [InlineData(11, false, true)]
    public async Task RealServer_MessageLimitCountsReceivedFramesNotPendingReads(int count, bool allowed, bool serviceFrames)
    {
        var dhtOptions = new DhtRendezvousOptions { Enabled = true };
        var meshOverlayServer = new MeshOverlayServer(
            NullLogger<MeshOverlayServer>.Instance,
            new StaticOptionsMonitor(new slskd.Options { Soulseek = new slskd.Options.SoulseekOptions { Username = "server-peer" } }),
            new CertificateManager(NullLogger<CertificateManager>.Instance, _serverAppDirectory),
            new CertificatePinStore(NullLogger<CertificatePinStore>.Instance, _serverAppDirectory),
            new OverlayRateLimiter(),
            new OverlayBlocklist(NullLogger<OverlayBlocklist>.Instance),
            new MeshNeighborRegistry(NullLogger<MeshNeighborRegistry>.Instance),
            new NoOpMeshOverlayConnector(),
            new NoOpMeshSyncService(),
            new NoOpMeshSearchRpcHandler(),
            new MeshOverlayRequestRouter(),
            dhtOptions);

        var optionsAtStartup = new OptionsAtStartup
        {
            Soulseek = new slskd.Options.SoulseekOptions
            {
                ListenIpAddress = "127.0.0.1",
                ListenPort = 0, // OS-assigned ephemeral port
            },
        };

        var sharedListener = new SharedMeshTcpListener(
            NullLogger<SharedMeshTcpListener>.Instance,
            optionsAtStartup,
            dhtOptions,
            new FedTcpListener(), // unused by this test: only the mesh-overlay TLS path is exercised
            meshOverlayServer);

        await meshOverlayServer.StartAsync();
        await sharedListener.StartAsync(CancellationToken.None);

        try
        {
            var boundEndPoint = await WaitForBoundEndPointAsync(sharedListener);

            var clientCertificateManager = new CertificateManager(NullLogger<CertificateManager>.Instance, _clientAppDirectory);
            var clientCertificate = clientCertificateManager.GetOrCreateServerCertificate();

            await using var connection = await MeshOverlayConnection.ConnectAsync(boundEndPoint, clientCertificate);
            var ack = await connection.PerformClientHandshakeAsync("client-peer", overlayPort: 12345);

            Assert.NotNull(ack);
            Assert.True(connection.IsHandshakeComplete);

            // Real production accounting on the real server, proving the connection was actually
            // accepted and processed -- not just that the TCP connect succeeded.
            await WaitUntilAsync(() => meshOverlayServer.TotalConnectionsAccepted == 1, TimeSpan.FromSeconds(5));
            Assert.Equal(1, meshOverlayServer.TotalConnectionsAccepted);
            Assert.Equal(0, meshOverlayServer.TotalConnectionsRejected);
            Assert.Equal(1, meshOverlayServer.ActiveConnections);
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
            // An adversarial peer bypasses our sender pacing and writes raw
            // authenticated frames. Reply pacing must not delay quota checks.
            using var raw = new SecureMessageFramer((System.Net.Security.SslStream)typeof(MeshOverlayConnection)
                .GetField("_sslStream", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic)!.GetValue(connection)!);
            for (var index = 0; index < count; index++)
            {
                if (serviceFrames)
                {
                    await raw.WriteMessageAsync(new MeshServiceCallMessage { CorrelationId = index.ToString(), ServiceName = "unknown", Method = "Read" }, timeout.Token);
                }
                else
                {
                    await connection.WriteMessageAsync(new PingMessage { Timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() }, timeout.Token);
                }
            }

            if (!serviceFrames || allowed)
            {
                for (var index = 0; index < Math.Min(count, OverlayRateLimiter.MaxMessagesPerSecond); index++)
                {
                    if (serviceFrames) Assert.NotNull(await connection.ReadMessageAsync<MeshServiceReplyMessage>(timeout.Token));
                    else Assert.NotNull(await connection.ReadMessageAsync<PongMessage>(timeout.Token));
                }
            }

            if (allowed)
            {
                await Task.Delay(100, timeout.Token);
                Assert.Equal(1, meshOverlayServer.ActiveConnections);
            }
            else
            {
                await WaitUntilAsync(() => meshOverlayServer.ActiveConnections == 0, TimeSpan.FromSeconds(15));
            }

        }
        finally
        {
            await sharedListener.StopAsync(CancellationToken.None);
            await meshOverlayServer.StopAsync();
        }
    }

    [Theory]
    [InlineData("overflow")]
    [InlineData("failure")]
    [InlineData("resume")]
    [InlineData("active-cancel")]
    public async Task RealConnection_ServiceWriterBoundsCancellationControlAndShutdown(string mode)
    {
        // Cold RSA generation is fixture preparation, outside the protocol deadline.
        var certificates = new CertificateManager(NullLogger<CertificateManager>.Instance, _serverAppDirectory);
        using var serverCertificate = certificates.GetOrCreateServerCertificate();
        using var certificate = new CertificateManager(NullLogger<CertificateManager>.Instance, _clientAppDirectory).GetOrCreateServerCertificate();
        var options = new DhtRendezvousOptions { Enabled = true };
        var server = new MeshOverlayServer(NullLogger<MeshOverlayServer>.Instance,
            new StaticOptionsMonitor(new slskd.Options { Soulseek = new slskd.Options.SoulseekOptions { Username = "server-peer" } }),
            certificates,
            new CertificatePinStore(NullLogger<CertificatePinStore>.Instance, _serverAppDirectory),
            new OverlayRateLimiter(), new OverlayBlocklist(NullLogger<OverlayBlocklist>.Instance),
            new MeshNeighborRegistry(NullLogger<MeshNeighborRegistry>.Instance), new NoOpMeshOverlayConnector(),
            new NoOpMeshSyncService(), new NoOpMeshSearchRpcHandler(), new MeshOverlayRequestRouter(), options);
        var listener = new SharedMeshTcpListener(NullLogger<SharedMeshTcpListener>.Instance,
            new OptionsAtStartup { Soulseek = new slskd.Options.SoulseekOptions { ListenIpAddress = "127.0.0.1", ListenPort = 0 } },
            options, new FedTcpListener(), server);
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(60));
        await server.StartAsync(timeout.Token);
        await listener.StartAsync(timeout.Token);
        try
        {
            await using var connection = await MeshOverlayConnection.ConnectAsync(await WaitForBoundEndPointAsync(listener), certificate, timeout.Token);
            await connection.PerformClientHandshakeAsync("client-peer", overlayPort: 12345, cancellationToken: timeout.Token);
            var entered = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            var release = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            using var activeCancellation = new CancellationTokenSource();
            var exited = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            connection.QueueServiceReply(new MeshServiceReplyMessage { CorrelationId = "held" },
                mode == "active-cancel" ? activeCancellation.Token : timeout.Token, async token =>
            {
                entered.TrySetResult(true);
                try { await release.Task.WaitAsync(token); }
                finally { exited.TrySetResult(true); }
            });
            await entered.Task.WaitAsync(timeout.Token);
            if (mode == "active-cancel")
            {
                activeCancellation.Cancel();
                await Task.WhenAny(exited.Task, Task.Delay(100, timeout.Token));
                Assert.False(exited.Task.IsCompleted);
            }

            // The writer is held outside the framer lock. A control round trip
            // must still progress while service writes remain queued.
            await connection.WriteMessageAsync(new PingMessage { Timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() }, timeout.Token);
            Assert.NotNull(await connection.ReadMessageAsync<PongMessage>(timeout.Token));
            using var canceled = new CancellationTokenSource();
            var canceledWrite = connection.WriteMessageAsync(new MeshServiceCallMessage { CorrelationId = "canceled" }, canceled.Token);
            canceled.Cancel();
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() => canceledWrite);
            if (mode is "resume" or "active-cancel")
            {
                var next = connection.WriteMessageAsync(new MeshServiceCallMessage { CorrelationId = "next" }, timeout.Token);
                release.TrySetResult(true);
                await next;
                var reply = await connection.ReadMessageAsync<MeshServiceReplyMessage>(timeout.Token);
                Assert.Equal("next", reply.CorrelationId);
                Assert.True(connection.IsConnected);
                return;
            }

            var queued = Enumerable.Range(0, 31).Select(index => connection.WriteMessageAsync(
                new MeshServiceCallMessage { CorrelationId = index.ToString() }, timeout.Token)).ToArray();
            Assert.All(queued, pending => Assert.False(pending.IsCompleted));
            if (mode == "failure")
            {
                release.TrySetException(new IOException("Injected post-send failure"));
                foreach (var pending in queued) await Assert.ThrowsAsync<IOException>(() => pending);
            }
            else
            {
                await Assert.ThrowsAsync<IOException>(() => connection.WriteMessageAsync(new MeshServiceCallMessage { CorrelationId = "overflow" }, timeout.Token));
                foreach (var pending in queued) await Assert.ThrowsAnyAsync<OperationCanceledException>(() => pending);
            }

            await connection.DisposeAsync();
            Assert.False(connection.IsConnected);
        }
        finally
        {
            await listener.StopAsync(CancellationToken.None);
            await server.StopAsync();
        }
    }

    [Fact]
    public async Task ListedRadio_RealTlsHostAndClient_ReadBytesAndEnforceRevocation()
    {
        var file = Path.Combine(_serverAppDirectory, "radio.wav");
        var bytes = Enumerable.Range(0, ListedRadioMeshService.MaxChunkBytes + 15).Select(index => (byte)(index % 251)).ToArray();
        await File.WriteAllBytesAsync(file, bytes);
        var state = new ListeningPartyEvent { PartyId = "party", ContentId = "track", Listed = true, AllowMeshStreaming = true };
        var parties = new Mock<IListeningPartyService>();
        parties.Setup(service => service.GetStateByPartyIdAsync("party", It.IsAny<CancellationToken>())).ReturnsAsync(() => state);
        var tickets = new StreamTicketService();
        var capability = tickets.Create("track", "listening-party:party", TimeSpan.FromMinutes(2));
        var locator = new Mock<IContentLocator>();
        locator.Setup(service => service.Resolve("track", It.IsAny<CancellationToken>())).Returns(new ResolvedContent(file, bytes.Length, "audio/wav"));
        var hostOptions = new StaticOptionsMonitor(new slskd.Options
        {
            Feature = new slskd.Options.FeatureOptions { Mesh = true, Streaming = true },
            Soulseek = new slskd.Options.SoulseekOptions { Username = "radio-host" },
        });
        var serviceRouter = new MeshServiceRouter(NullLogger<MeshServiceRouter>.Instance, Microsoft.Extensions.Options.Options.Create(new MeshServiceFabricOptions()));
        serviceRouter.RegisterService(new ListedRadioMeshService(parties.Object, tickets, locator.Object, hostOptions, NullLogger<ListedRadioMeshService>.Instance));
        var dhtOptions = new DhtRendezvousOptions { Enabled = true };
        var hostAccounting = new Mock<slskd.Transfers.MultiSource.Metrics.ITrafficAccountingService>();
        var clientAccounting = new Mock<slskd.Transfers.MultiSource.Metrics.ITrafficAccountingService>();
        var serverRegistry = new MeshNeighborRegistry(NullLogger<MeshNeighborRegistry>.Instance);
        var serverRequests = new MeshOverlayRequestRouter();
        var server = new MeshOverlayServer(
            NullLogger<MeshOverlayServer>.Instance, hostOptions,
            new CertificateManager(NullLogger<CertificateManager>.Instance, _serverAppDirectory),
            new CertificatePinStore(NullLogger<CertificatePinStore>.Instance, _serverAppDirectory),
            new OverlayRateLimiter(), new OverlayBlocklist(NullLogger<OverlayBlocklist>.Instance),
            serverRegistry,
            new NoOpMeshOverlayConnector(), new NoOpMeshSyncService(), new NoOpMeshSearchRpcHandler(),
            serverRequests, dhtOptions, serviceRouter, hostAccounting.Object);
        var listener = new SharedMeshTcpListener(
            NullLogger<SharedMeshTcpListener>.Instance,
            new OptionsAtStartup { Soulseek = new slskd.Options.SoulseekOptions { ListenIpAddress = "127.0.0.1", ListenPort = 0 } },
            dhtOptions, new FedTcpListener(), server);
        var registry = new MeshNeighborRegistry(NullLogger<MeshNeighborRegistry>.Instance);
        var requests = new MeshOverlayRequestRouter();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await server.StartAsync(timeout.Token);
        await listener.StartAsync(timeout.Token);
        try
        {
            var connector = new MeshOverlayConnector(
                NullLogger<MeshOverlayConnector>.Instance,
                new StaticOptionsMonitor(new slskd.Options { Soulseek = new slskd.Options.SoulseekOptions { Username = "radio-listener" } }),
                new CertificateManager(NullLogger<CertificateManager>.Instance, _clientAppDirectory),
                new CertificatePinStore(NullLogger<CertificatePinStore>.Instance, _clientAppDirectory),
                new OverlayRateLimiter(), new OverlayBlocklist(NullLogger<OverlayBlocklist>.Instance),
                registry, new NoOpMeshSyncService(), new NoOpMeshSearchRpcHandler(), requests, serviceRouter, clientAccounting.Object);
            var connection = await connector.ConnectToEndpointAsync(await WaitForBoundEndPointAsync(listener), timeout.Token);
            Assert.NotNull(connection);
            var client = new MeshServiceClient(NullLogger<MeshServiceClient>.Instance, Mock.Of<IMeshServiceDirectory>(), Mock.Of<IControlSigner>(), registry, requests);
            ServiceCall Read(long offset, int length) => new()
            {
                ServiceName = "ListedRadio",
                Method = "Read",
                CorrelationId = Guid.NewGuid().ToString("N"),
                Payload = JsonSerializer.SerializeToUtf8Bytes(new ListedRadioRequest("party", "track", capability, offset, length), new JsonSerializerOptions(JsonSerializerDefaults.Web)),
            };

            var first = await client.CallAsync("radio-host", Read(0, ListedRadioMeshService.MaxChunkBytes), timeout.Token);
            Assert.Equal(ServiceStatusCodes.OK, first.StatusCode);
            Assert.Equal(bytes[..ListedRadioMeshService.MaxChunkBytes], first.Payload);
            var tail = await client.CallAsync("radio-host", Read(ListedRadioMeshService.MaxChunkBytes, 15), timeout.Token);
            Assert.Equal(ServiceStatusCodes.OK, tail.StatusCode);
            Assert.Equal(bytes[ListedRadioMeshService.MaxChunkBytes..], tail.Payload);
            var metadata = await client.CallAsync("radio-host", Read(0, 15) with { Method = "Metadata" }, timeout.Token);
            Assert.Equal(ServiceStatusCodes.OK, metadata.StatusCode);
            var expiredCapability = tickets.Create("track", "listening-party:party", TimeSpan.FromSeconds(-1));
            var expired = await client.CallAsync("radio-host", Read(0, 15) with
            {
                Payload = JsonSerializer.SerializeToUtf8Bytes(new ListedRadioRequest("party", "track", expiredCapability, 0, 15), new JsonSerializerOptions(JsonSerializerDefaults.Web)),
            }, timeout.Token);
            Assert.Equal(403, expired.StatusCode);
            hostAccounting.Verify(service => service.AddOverlayUploadAsync(ListedRadioMeshService.MaxChunkBytes, It.IsAny<CancellationToken>()), Times.Once);
            hostAccounting.Verify(service => service.AddOverlayUploadAsync(15, It.IsAny<CancellationToken>()), Times.Once);
            hostAccounting.VerifyNoOtherCalls();

            // Twenty ordinary sequential calls must survive on the same link;
            // pending-call capacity alone does not pace received frame bursts.
            for (var index = 0; index < 20; index++)
            {
                var burstReply = await client.CallAsync("radio-host", Read(0, 15) with { Method = "Metadata" }, timeout.Token);
                Assert.Equal(ServiceStatusCodes.OK, burstReply.StatusCode);
            }

            // Exercise the connector's inbound RPC handler on the same real TLS link.
            var inbound = Assert.Single(serverRegistry.GetAllConnections());
            Assert.False(inbound.IsOutbound);
            var reverseClient = new MeshServiceClient(NullLogger<MeshServiceClient>.Instance, Mock.Of<IMeshServiceDirectory>(), Mock.Of<IControlSigner>(), serverRegistry, serverRequests);
            var reverseReply = await reverseClient.CallAsync("RADIO-LISTENER", Read(0, 15), timeout.Token);
            Assert.Equal(ServiceStatusCodes.OK, reverseReply.StatusCode);
            Assert.Equal(bytes[..15], reverseReply.Payload);
            var barrier = await reverseClient.CallAsync("radio-listener", Read(0, 15) with { Method = "Metadata" }, timeout.Token);
            Assert.Equal(ServiceStatusCodes.OK, barrier.StatusCode);
            Assert.Single(serverRegistry.GetAllConnections());
            Assert.Single(registry.GetAllConnections());
            var remoteNodeId = Enumerable.Repeat((byte)2, 20).ToArray();
            serviceRouter.RegisterService(new slskd.Mesh.ServiceFabric.Services.DhtMeshService(
                NullLogger<slskd.Mesh.ServiceFabric.Services.DhtMeshService>.Instance,
                new slskd.Mesh.Dht.KademliaRoutingTable(remoteNodeId), Mock.Of<slskd.VirtualSoulfind.ShadowIndex.IDhtClient>(), Mock.Of<slskd.Mesh.IMeshMessageSigner>()));
            var hostRouting = new slskd.Mesh.Dht.KademliaRoutingTable(Enumerable.Repeat((byte)1, 20).ToArray());
            using var dht = new slskd.Mesh.Dht.KademliaRpcClient(
                NullLogger<slskd.Mesh.Dht.KademliaRpcClient>.Instance, reverseClient, hostRouting, Mock.Of<slskd.VirtualSoulfind.ShadowIndex.IDhtClient>(), neighbors: serverRegistry);
            await dht.FindNodeAsync(remoteNodeId, timeout.Token);
            var discovered = Assert.Single(hostRouting.GetAllNodes());
            Assert.Equal(remoteNodeId, discovered.NodeId);
            Assert.Equal("radio-listener", discovered.Address);
            Assert.Single(serverRegistry.GetAllConnections());
            clientAccounting.Verify(service => service.AddOverlayUploadAsync(15, It.IsAny<CancellationToken>()), Times.Once);
            clientAccounting.VerifyNoOtherCalls();

            for (var index = 0; index < 20; index++)
            {
                var burstReply = await reverseClient.CallAsync("radio-listener", Read(0, 15) with { Method = "Metadata" }, timeout.Token);
                Assert.Equal(ServiceStatusCodes.OK, burstReply.StatusCode);
            }

            // Keep the ten-call client quota probe within the real ten-message
            // per-second overlay budget, independently of preceding RPC checks.
            await Task.Delay(TimeSpan.FromMilliseconds(1100), timeout.Token);
            var releaseCalls = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            var heldService = new Mock<IMeshService>();
            heldService.SetupGet(service => service.ServiceName).Returns("held-calls");
            heldService.Setup(service => service.HandleCallAsync(It.IsAny<ServiceCall>(), It.IsAny<MeshServiceContext>(), It.IsAny<CancellationToken>()))
                .Returns(async (ServiceCall call, MeshServiceContext context, CancellationToken cancellation) =>
                {
                    await releaseCalls.Task.WaitAsync(cancellation);
                    return new ServiceReply { CorrelationId = call.CorrelationId, StatusCode = ServiceStatusCodes.OK };
                });
            serviceRouter.RegisterService(heldService.Object);
            var pendingCalls = Enumerable.Range(0, 10).Select(index => reverseClient.CallAsync(
                index % 2 == 0 ? "radio-listener" : "RADIO-LISTENER",
                new ServiceCall { ServiceName = "held-calls", Method = "Wait", CorrelationId = Guid.NewGuid().ToString("N") }, timeout.Token)).ToArray();
            try
            {
                Assert.Equal(10, reverseClient.GetMetrics().TotalPendingCalls);
                Assert.Equal(1, reverseClient.GetMetrics().PeersWithPendingCalls);
                var limited = await reverseClient.CallAsync("Radio-Listener",
                    new ServiceCall { ServiceName = "held-calls", Method = "Wait", CorrelationId = Guid.NewGuid().ToString("N") }, timeout.Token);
                Assert.Equal(ServiceStatusCodes.RateLimited, limited.StatusCode);
            }
            finally
            {
                releaseCalls.TrySetResult(true);
                await Task.WhenAll(pendingCalls);
            }

            Assert.All(pendingCalls, pending => Assert.Equal(ServiceStatusCodes.OK, pending.Result.StatusCode));
            Assert.Equal(0, reverseClient.GetMetrics().TotalPendingCalls);
            Assert.Equal(0, reverseClient.GetMetrics().PeersWithPendingCalls);
            await Task.Delay(TimeSpan.FromMilliseconds(1100), timeout.Token);

            state = state with { AllowMeshStreaming = false };
            var revoked = await client.CallAsync("radio-host", Read(0, 15), timeout.Token);
            Assert.Equal(404, revoked.StatusCode);
            Assert.Empty(revoked.Payload);
            hostAccounting.VerifyNoOtherCalls();
            await connection.DisconnectAsync("Test completed", timeout.Token);
        }
        finally
        {
            await listener.StopAsync(CancellationToken.None);
            await server.StopAsync();
        }
    }

    [Fact]
    public async Task Pods_RealTlsCalls_BindIdentityAndRetainPrivateRoomAndBanBoundaries()
    {
        const string publicId = "pod:00000000000000000000000000000001";
        const string privateId = "pod:00000000000000000000000000000002";
        const string approvalId = "pod:00000000000000000000000000000003";
        var hostPods = new PodService();
        var clientPods = new PodService();
        await hostPods.CreateAsync(new Pod { PodId = publicId, Name = "Public room", IsPublic = true });
        await hostPods.CreateAsync(new Pod { PodId = privateId, Name = "Private room", RequireApproval = true });
        await hostPods.CreateAsync(new Pod { PodId = approvalId, Name = "Approval room", IsPublic = true, RequireApproval = true });
        await clientPods.CreateAsync(new Pod { PodId = privateId, Name = "Other private room" });
        var messaging = new Mock<IPodMessaging>();
        messaging.Setup(service => service.GetMessagesAsync(It.IsAny<string>(), "general", null, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new[] { new PodMessage { PodId = publicId, Body = "Member-only history" } });
        messaging.Setup(service => service.SendAsync(It.IsAny<PodMessage>(), It.IsAny<CancellationToken>())).ReturnsAsync(true);
        var clientMessaging = new Mock<IPodMessaging>();
        using var hostProvider = new ServiceCollection().AddScoped(_ => messaging.Object).BuildServiceProvider();
        using var clientProvider = new ServiceCollection().AddScoped(_ => clientMessaging.Object).BuildServiceProvider();
        var hostRouter = new MeshServiceRouter(NullLogger<MeshServiceRouter>.Instance, Microsoft.Extensions.Options.Options.Create(new MeshServiceFabricOptions()));
        var clientRouter = new MeshServiceRouter(NullLogger<MeshServiceRouter>.Instance, Microsoft.Extensions.Options.Options.Create(new MeshServiceFabricOptions()));
        hostRouter.RegisterService(new PodsMeshService(NullLogger<PodsMeshService>.Instance, hostPods, hostProvider.GetRequiredService<IServiceScopeFactory>()));
        clientRouter.RegisterService(new PodsMeshService(NullLogger<PodsMeshService>.Instance, clientPods, clientProvider.GetRequiredService<IServiceScopeFactory>()));
        var hostRegistry = new MeshNeighborRegistry(NullLogger<MeshNeighborRegistry>.Instance);
        var hostRequests = new MeshOverlayRequestRouter();
        var clientRegistry = new MeshNeighborRegistry(NullLogger<MeshNeighborRegistry>.Instance);
        var clientRequests = new MeshOverlayRequestRouter();
        var dhtOptions = new DhtRendezvousOptions { Enabled = true };
        var server = new MeshOverlayServer(
            NullLogger<MeshOverlayServer>.Instance,
            new StaticOptionsMonitor(new slskd.Options { Soulseek = new slskd.Options.SoulseekOptions { Username = "room-host" } }),
            new CertificateManager(NullLogger<CertificateManager>.Instance, _serverAppDirectory),
            new CertificatePinStore(NullLogger<CertificatePinStore>.Instance, _serverAppDirectory),
            new OverlayRateLimiter(), new OverlayBlocklist(NullLogger<OverlayBlocklist>.Instance), hostRegistry,
            new NoOpMeshOverlayConnector(), new NoOpMeshSyncService(), new NoOpMeshSearchRpcHandler(), hostRequests, dhtOptions, hostRouter);
        var listener = new SharedMeshTcpListener(
            NullLogger<SharedMeshTcpListener>.Instance,
            new OptionsAtStartup { Soulseek = new slskd.Options.SoulseekOptions { ListenIpAddress = "127.0.0.1", ListenPort = 0 } },
            dhtOptions, new FedTcpListener(), server);
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await server.StartAsync(timeout.Token);
        await listener.StartAsync(timeout.Token);
        try
        {
            var connector = new MeshOverlayConnector(
                NullLogger<MeshOverlayConnector>.Instance,
                new StaticOptionsMonitor(new slskd.Options { Soulseek = new slskd.Options.SoulseekOptions { Username = "room-listener" } }),
                new CertificateManager(NullLogger<CertificateManager>.Instance, _clientAppDirectory),
                new CertificatePinStore(NullLogger<CertificatePinStore>.Instance, _clientAppDirectory),
                new OverlayRateLimiter(), new OverlayBlocklist(NullLogger<OverlayBlocklist>.Instance), clientRegistry,
                new NoOpMeshSyncService(), new NoOpMeshSearchRpcHandler(), clientRequests, clientRouter);
            var connection = await connector.ConnectToEndpointAsync(await WaitForBoundEndPointAsync(listener), timeout.Token);
            Assert.NotNull(connection);
            var client = new MeshServiceClient(NullLogger<MeshServiceClient>.Instance, Mock.Of<IMeshServiceDirectory>(), Mock.Of<IControlSigner>(), clientRegistry, clientRequests);
            var reverse = new MeshServiceClient(NullLogger<MeshServiceClient>.Instance, Mock.Of<IMeshServiceDirectory>(), Mock.Of<IControlSigner>(), hostRegistry, hostRequests);
            async Task<ServiceReply> Call(MeshServiceClient caller, string peer, string method, string podId)
            {
                // Stay below the real rolling message quota; permission evidence
                // must not depend on disabling network admission policy.
                await Task.Delay(150, timeout.Token);
                return await caller.CallAsync(peer, new ServiceCall
                {
                    ServiceName = "pods",
                    Method = method,
                    CorrelationId = Guid.NewGuid().ToString("N"),
                    Payload = JsonSerializer.SerializeToUtf8Bytes(new { PodId = podId, ChannelId = "general", Body = "hello", Role = "owner", PeerId = "room-host" }),
                }, timeout.Token);
            }

            Assert.Equal(ServiceStatusCodes.Forbidden, (await Call(client, "room-host", "Get", privateId)).StatusCode);
            Assert.Equal(ServiceStatusCodes.Forbidden, (await Call(client, "room-host", "GetMessages", publicId)).StatusCode);
            Assert.Equal(ServiceStatusCodes.Forbidden, (await Call(client, "room-host", "Join", privateId)).StatusCode);
            Assert.Equal(ServiceStatusCodes.Forbidden, (await Call(client, "room-host", "Join", approvalId)).StatusCode);
            messaging.VerifyNoOtherCalls();
            Assert.Equal(ServiceStatusCodes.OK, (await Call(client, "room-host", "Join", publicId)).StatusCode);
            var joined = Assert.Single(await hostPods.GetMembersAsync(publicId));
            Assert.Equal("room-listener", joined.PeerId);
            Assert.Equal("member", joined.Role);
            var history = await Call(client, "room-host", "GetMessages", publicId);
            Assert.Equal(ServiceStatusCodes.OK, history.StatusCode);
            Assert.Equal("Member-only history", Assert.Single(JsonSerializer.Deserialize<PodMessage[]>(history.Payload)!).Body);
            Assert.Equal(ServiceStatusCodes.OK, (await Call(client, "room-host", "PostMessage", publicId)).StatusCode);
            messaging.Verify(service => service.SendAsync(It.Is<PodMessage>(message => message.SenderPeerId == "room-listener"), It.IsAny<CancellationToken>()), Times.Once);
            Assert.True(await hostPods.JoinAsync(privateId, new PodMember { PeerId = "room-listener", Role = "mod", PublicKey = "approved-key" }));
            Assert.Equal(ServiceStatusCodes.OK, (await Call(client, "room-host", "Join", privateId)).StatusCode);
            var approved = Assert.Single(await hostPods.GetMembersAsync(privateId));
            Assert.Equal("mod", approved.Role);
            Assert.Equal("approved-key", approved.PublicKey);
            Assert.Equal(ServiceStatusCodes.OK, (await Call(client, "room-host", "Get", privateId)).StatusCode);

            Assert.True(await hostPods.BanAsync(publicId, "room-listener"));
            Assert.Equal(ServiceStatusCodes.Forbidden, (await Call(client, "room-host", "GetMessages", publicId)).StatusCode);
            Assert.Equal(ServiceStatusCodes.Forbidden, (await Call(client, "room-host", "Leave", publicId)).StatusCode);
            Assert.Equal(ServiceStatusCodes.Forbidden, (await Call(client, "room-host", "Join", publicId)).StatusCode);
            messaging.Verify(service => service.GetMessagesAsync(publicId, "general", null, It.IsAny<CancellationToken>()), Times.Once);

            Assert.Equal(ServiceStatusCodes.Forbidden, (await Call(reverse, "room-listener", "Get", privateId)).StatusCode);
            Assert.True(await clientPods.JoinAsync(privateId, new PodMember { PeerId = "room-host", Role = "member" }));
            Assert.Equal(ServiceStatusCodes.OK, (await Call(reverse, "room-listener", "Get", privateId)).StatusCode);
            Assert.True(await clientPods.BanAsync(privateId, "room-host"));
            Assert.Equal(ServiceStatusCodes.Forbidden, (await Call(reverse, "room-listener", "Get", privateId)).StatusCode);
            clientMessaging.VerifyNoOtherCalls();
            await connection.DisconnectAsync("Test completed", timeout.Token);
        }
        finally
        {
            await listener.StopAsync(CancellationToken.None);
            await server.StopAsync();
        }
    }

    public void Dispose()
    {
        TryDeleteDirectory(_serverAppDirectory);
        TryDeleteDirectory(_clientAppDirectory);
    }

    private static void TryDeleteDirectory(string path)
    {
        try
        {
            Directory.Delete(path, recursive: true);
        }
        catch
        {
            // Best-effort cleanup only.
        }
    }

    private static async Task<IPEndPoint> WaitForBoundEndPointAsync(SharedMeshTcpListener listener)
    {
        var deadline = DateTimeOffset.UtcNow + TimeSpan.FromSeconds(30);
        while (listener.LocalEndPoint is null)
        {
            if (DateTimeOffset.UtcNow > deadline)
            {
                throw new TimeoutException("Timed out waiting for SharedMeshTcpListener to bind.");
            }

            await Task.Delay(10);
        }

        return listener.LocalEndPoint;
    }

    private static async Task WaitUntilAsync(Func<bool> predicate, TimeSpan timeout)
    {
        var deadline = DateTimeOffset.UtcNow + timeout;
        while (!predicate())
        {
            if (DateTimeOffset.UtcNow > deadline)
            {
                return;
            }

            await Task.Delay(10);
        }
    }

    private sealed class StaticOptionsMonitor : IOptionsMonitor<slskd.Options>
    {
        public StaticOptionsMonitor(slskd.Options value)
        {
            CurrentValue = value;
        }

        public slskd.Options CurrentValue { get; }

        public slskd.Options Get(string? name) => CurrentValue;

        public IDisposable OnChange(Action<slskd.Options, string> listener) => NullDisposable.Instance;

        private sealed class NullDisposable : IDisposable
        {
            public static readonly NullDisposable Instance = new();

            public void Dispose()
            {
            }
        }
    }

    private sealed class NoOpMeshOverlayConnector : IMeshOverlayConnector
    {
        public int PendingConnections => 0;

        public long SuccessfulConnections => 0;

        public long FailedConnections => 0;

        public Task<int> ConnectToCandidatesAsync(System.Collections.Generic.IEnumerable<IPEndPoint> candidates, CancellationToken cancellationToken = default)
            => Task.FromResult(0);

        public Task<MeshOverlayConnection?> ConnectToEndpointAsync(IPEndPoint endpoint, CancellationToken cancellationToken = default)
            => Task.FromResult<MeshOverlayConnection?>(null);

        public MeshOverlayConnectorStats GetStats() => new();
    }

    private sealed class NoOpMeshSearchRpcHandler : IMeshSearchRpcHandler
    {
        public Task<MeshSearchResponseMessage> HandleAsync(MeshSearchRequestMessage request, CancellationToken cancellationToken = default)
            => throw new NotSupportedException("Not exercised by this test.");
    }

    private sealed class NoOpMeshSyncService : IMeshSyncService
    {
        public MeshSyncStats Stats { get; } = new();

        public Task<MeshSyncResult> TrySyncWithPeerAsync(string username, CancellationToken cancellationToken = default)
            => Task.FromResult(new MeshSyncResult { Success = false, PeerUsername = username });

        public Task<MeshMessage?> HandleMessageAsync(string fromUser, MeshMessage message, CancellationToken cancellationToken = default)
            => Task.FromResult<MeshMessage?>(null);

        public Task<MeshHashEntry?> LookupHashAsync(string flacKey, CancellationToken cancellationToken = default)
            => Task.FromResult<MeshHashEntry?>(null);

        public Task PublishHashAsync(string flacKey, string byteHash, long size, int? metaFlags = null, CancellationToken cancellationToken = default)
            => Task.CompletedTask;

        public System.Collections.Generic.IEnumerable<slskd.Mesh.MeshPeerInfo> GetMeshPeers() => System.Array.Empty<slskd.Mesh.MeshPeerInfo>();

        public slskd.Mesh.Messages.MeshHelloMessage GenerateHelloMessage() => new() { ClientId = "server-peer" };

        public Task<MeshPushDeltaMessage> GenerateDeltaResponseAsync(long sinceSeqId, int maxEntries, CancellationToken cancellationToken = default)
            => Task.FromResult(new MeshPushDeltaMessage());

        public Task<int> MergeEntriesAsync(string fromUser, System.Collections.Generic.IEnumerable<MeshHashEntry> entries, CancellationToken cancellationToken = default)
            => Task.FromResult(0);

        public void Dispose()
        {
        }
    }
}
