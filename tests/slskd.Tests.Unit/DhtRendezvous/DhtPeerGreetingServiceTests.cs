// <copyright file="DhtPeerGreetingServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.DhtRendezvous;

using System.Net;
using System.Reflection;
using System.Runtime.CompilerServices;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using slskd.DhtRendezvous;
using slskd.Tests.Unit.TestHelpers;
using Soulseek;
using Xunit;

public class DhtPeerGreetingServiceTests
{
    [Fact]
    public async Task SendGreetingAsync_WhenRemoteSendFails_LogsEscapedExceptionText()
    {
        await using var registry = new MeshNeighborRegistry(NullLogger<MeshNeighborRegistry>.Instance);
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient.SetupGet(client => client.State).Returns(SoulseekClientStates.Connected);
        soulseekClient
            .Setup(client => client.SendPrivateMessageAsync("peer-1", It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("remote detail\r\nforged log"));
        var logger = new CapturingLogger<DhtPeerGreetingService>();
        var service = new DhtPeerGreetingService(logger, registry, soulseekClient.Object);
        var sendMethod = typeof(DhtPeerGreetingService).GetMethod(
            "SendGreetingAsync",
            BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException("SendGreetingAsync was not found.");

        await (Task)sendMethod.Invoke(service, ["peer-1", false])!;

        var entry = logger.Entries.Find(entry => entry.Level == LogLevel.Warning);
        Assert.NotNull(entry);
        Assert.Null(entry.Exception);
        Assert.Contains("remote detail\\r\\nforged log", entry.Message);
        Assert.DoesNotContain('\r', entry.Message);
        Assert.DoesNotContain('\n', entry.Message);
    }

    [Fact]
    public async Task StartAsync_CalledTwice_DoesNotDuplicateNeighborSubscriptions()
    {
        await using var registry = new MeshNeighborRegistry(NullLogger<MeshNeighborRegistry>.Instance);
        var service = new DhtPeerGreetingService(
            NullLogger<DhtPeerGreetingService>.Instance,
            registry,
            Mock.Of<ISoulseekClient>());

        await service.StartAsync(CancellationToken.None);
        await service.StartAsync(CancellationToken.None);

        Assert.Equal(1, GetEventInvocationCount(registry, "NeighborAdded"));
        Assert.Equal(1, GetEventInvocationCount(registry, "FirstNeighborConnected"));

        await service.StopAsync(CancellationToken.None);
    }

    [Fact]
    public async Task Dispose_DetachesNeighborSubscriptions()
    {
        await using var registry = new MeshNeighborRegistry(NullLogger<MeshNeighborRegistry>.Instance);
        var service = new DhtPeerGreetingService(
            NullLogger<DhtPeerGreetingService>.Instance,
            registry,
            Mock.Of<ISoulseekClient>());

        await service.StartAsync(CancellationToken.None);

        Assert.Equal(1, GetEventInvocationCount(registry, "NeighborAdded"));
        Assert.Equal(1, GetEventInvocationCount(registry, "FirstNeighborConnected"));

        service.Dispose();

        Assert.Equal(0, GetEventInvocationCount(registry, "NeighborAdded"));
        Assert.Equal(0, GetEventInvocationCount(registry, "FirstNeighborConnected"));
    }

    [Fact]
    public async Task OnNeighborAdded_WhenGreetingIsAlreadyInFlight_DoesNotSendDuplicateGreeting()
    {
        await using var registry = new MeshNeighborRegistry(NullLogger<MeshNeighborRegistry>.Instance);
        var soulseekClient = new Mock<ISoulseekClient>();
        var sendCompletion = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        var sendCount = 0;

        soulseekClient.SetupGet(client => client.State).Returns(SoulseekClientStates.Connected);
        soulseekClient
            .Setup(client => client.SendPrivateMessageAsync("peer-1", It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(async () =>
            {
                Interlocked.Increment(ref sendCount);
                await sendCompletion.Task.ConfigureAwait(false);
            });

        var service = new DhtPeerGreetingService(
            NullLogger<DhtPeerGreetingService>.Instance,
            registry,
            soulseekClient.Object);

        var handler = typeof(DhtPeerGreetingService).GetMethod(
            "OnNeighborAdded",
            BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException("OnNeighborAdded was not found.");

        var eventArgs = new MeshNeighborEventArgs(CreateConnection("peer-1", "127.0.0.1", 5100));

        handler.Invoke(service, [null, eventArgs]);
        handler.Invoke(service, [null, eventArgs]);

        await Task.Delay(100);

        Assert.Equal(1, Volatile.Read(ref sendCount));

        sendCompletion.TrySetResult(true);
    }

    private static MeshOverlayConnection CreateConnection(string username, string address, int port)
    {
        var connection = (MeshOverlayConnection)RuntimeHelpers.GetUninitializedObject(typeof(MeshOverlayConnection));

        SetPropertyOrField(connection, "ConnectionId", $"conn-{port}");
        SetPropertyOrField(connection, "RemoteEndPoint", new IPEndPoint(IPAddress.Parse(address), port));
        SetPropertyOrField(connection, "Username", username);

        return connection;
    }

    private static void SetPropertyOrField(object target, string memberName, object? value)
    {
        var property = target.GetType().GetProperty(memberName, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
        if (property?.GetSetMethod(true) is { } setMethod)
        {
            setMethod.Invoke(target, [value]);
            return;
        }

        var field = target.GetType().GetField($"<{memberName}>k__BackingField", BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException($"Member '{memberName}' was not found.");

        field.SetValue(target, value);
    }

    private static int GetEventInvocationCount(object target, string eventName)
    {
        var field = target.GetType().GetField(eventName, BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException($"Event backing field '{eventName}' was not found.");

        return (field.GetValue(target) as MulticastDelegate)?.GetInvocationList().Length ?? 0;
    }
}
