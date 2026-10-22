// <copyright file="FedTcpListenerTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.DhtRendezvous;

using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;
using slskd.SoulseekRuntime;
using Xunit;

public class FedTcpListenerTests
{
    [Fact]
    public async Task Feed_MakesConnectionAvailableViaAcceptTcpClientAsync()
    {
        var sut = new FedTcpListener();

        using var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        var acceptTask = listener.AcceptTcpClientAsync();
        using var client = new TcpClient();
        await client.ConnectAsync(IPAddress.Loopback, ((IPEndPoint)listener.LocalEndpoint).Port);
        using var serverClient = await acceptTask.WaitAsync(TimeSpan.FromSeconds(2));

        sut.Feed(serverClient);

        var accepted = await sut.AcceptTcpClientAsync().WaitAsync(TimeSpan.FromSeconds(2));

        Assert.Same(serverClient, accepted);
    }

    [Fact]
    public async Task StartAndStop_AreNoOps_AndDoNotBreakSubsequentFeeds()
    {
        var sut = new FedTcpListener();

        // Mirrors the vendored Listener calling Start()/Stop() on every reconnect/reconfigure
        // around the same long-lived FedTcpListener instance.
        sut.Start();
        sut.Stop();
        sut.Start();

        using var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        var acceptTask = listener.AcceptTcpClientAsync();
        using var client = new TcpClient();
        await client.ConnectAsync(IPAddress.Loopback, ((IPEndPoint)listener.LocalEndpoint).Port);
        using var serverClient = await acceptTask.WaitAsync(TimeSpan.FromSeconds(2));

        sut.Feed(serverClient);

        var accepted = await sut.AcceptTcpClientAsync().WaitAsync(TimeSpan.FromSeconds(2));

        Assert.Same(serverClient, accepted);
    }

    [Fact]
    public async Task Complete_ClosesTheFeed()
    {
        var sut = new FedTcpListener();

        sut.Complete();

        await Assert.ThrowsAsync<ChannelClosedException>(() => sut.AcceptTcpClientAsync());
    }

    [Fact]
    public async Task AcceptTcpClientAsync_CancelsPendingRead()
    {
        var sut = new FedTcpListener();
        using var cancellationTokenSource = new CancellationTokenSource();

        var acceptTask = sut.AcceptTcpClientAsync(cancellationTokenSource.Token);
        cancellationTokenSource.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => acceptTask);
    }
}
