// <copyright file="SceneServicesTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
#nullable enable

using System.Collections.Concurrent;
using System.Reflection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Moq;
using slskd.Identity;
using slskd.VirtualSoulfind.Scenes;
using slskd.VirtualSoulfind.ShadowIndex;

namespace slskd.Tests.Unit.VirtualSoulfind;

public class SceneServicesTests
{
    [Fact]
    public async Task SceneModerationService_IsPeerMutedAsync_TreatsPeerIdsCaseInsensitively()
    {
        var service = new SceneModerationService(NullLogger<SceneModerationService>.Instance);

        await service.MutePeerAsync("scene:test", "Peer-One", "test", CancellationToken.None);

        Assert.True(await service.IsPeerMutedAsync("scene:test", "peer-one", CancellationToken.None));
    }

    [Fact]
    public async Task SceneMembershipTracker_GetMembersAsync_ExcludesPeersMarkedInactiveInCache()
    {
        var tracker = new SceneMembershipTracker(
            NullLogger<SceneMembershipTracker>.Instance,
            new StubDhtClient());

        await tracker.TrackJoinAsync("scene:test", "peer-1", CancellationToken.None);
        await tracker.TrackLeaveAsync("scene:test", "peer-1", CancellationToken.None);

        var members = await tracker.GetMembersAsync("scene:test", CancellationToken.None);

        Assert.Empty(members);
    }

    [Fact]
    public async Task SceneMembershipTracker_GetSceneMetadataAsync_PropagatesCancellationBeforeDeserialization()
    {
        using var cancellation = new CancellationTokenSource();
        var metadataBytes = MessagePack.MessagePackSerializer.Serialize(new SceneMetadata { SceneId = "scene:test" });
        var dht = new Mock<IDhtClient>();
        dht
            .Setup(client => client.GetAsync(It.IsAny<byte[]>(), It.IsAny<CancellationToken>()))
            .Returns((byte[] _, CancellationToken _) =>
            {
                cancellation.Cancel();
                return Task.FromResult<byte[]?>(metadataBytes);
            });
        var tracker = new SceneMembershipTracker(NullLogger<SceneMembershipTracker>.Instance, dht.Object);

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            tracker.GetSceneMetadataAsync("scene:test", cancellation.Token));
    }

    [Fact]
    public async Task SceneService_SearchScenesAsync_PropagatesCanceledMetadataLookup()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var membershipTracker = new Mock<ISceneMembershipTracker>();
        membershipTracker
            .Setup(tracker => tracker.GetSceneMetadataAsync("scene:label:search", cancellation.Token))
            .Returns(Task.FromCanceled<SceneMetadata?>(cancellation.Token));
        var service = new SceneService(
            NullLogger<SceneService>.Instance,
            Mock.Of<ISceneAnnouncementService>(),
            membershipTracker.Object,
            CreateOptionsMonitor());

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            service.SearchScenesAsync("search", cancellation.Token));
    }

    [Fact]
    public async Task SceneAnnouncementService_RefreshAnnouncementsAsync_StopsOnCallerCancellation()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var sceneService = new Mock<ISceneService>();
        sceneService
            .Setup(service => service.GetJoinedScenesAsync(cancellation.Token))
            .ReturnsAsync(new List<Scene>
            {
                new() { SceneId = "scene:first" },
                new() { SceneId = "scene:second" },
            });
        var rateLimiter = new Mock<IDhtRateLimiter>();
        rateLimiter
            .Setup(limiter => limiter.TryAcquireAsync(cancellation.Token))
            .Returns(Task.FromCanceled<bool>(cancellation.Token));
        var service = new SceneAnnouncementService(
            NullLogger<SceneAnnouncementService>.Instance,
            Mock.Of<IDhtClient>(),
            rateLimiter.Object,
            Mock.Of<IProfileService>(),
            sceneService.Object);

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            service.RefreshAnnouncementsAsync(cancellation.Token));
        rateLimiter.Verify(limiter => limiter.TryAcquireAsync(cancellation.Token), Times.Once);
    }

    [Fact]
    public async Task SceneChatService_OnPubSubFallbackMessage_PreservesSceneIdFromEnvelope()
    {
        var pubsub = new StubScenePubSubService();
        var profileService = new Mock<IProfileService>();
        profileService
            .Setup(service => service.GetMyProfileAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(new PeerProfile { PeerId = "local-peer" });

        var service = new SceneChatService(
            NullLogger<SceneChatService>.Instance,
            pubsub,
            CreateOptionsMonitor(),
            profileService.Object);

        pubsub.RaiseMessageReceived(new SceneMessageReceivedEventArgs
        {
            SceneId = "scene:test",
            PeerId = "remote-peer",
            Message = System.Text.Encoding.UTF8.GetBytes("plain text fallback"),
            Timestamp = DateTimeOffset.UtcNow,
        });

        var messages = await service.GetMessagesAsync("scene:test", 100, CancellationToken.None);

        var message = Assert.Single(messages);
        Assert.Equal("scene:test", message.SceneId);
        Assert.Equal("remote-peer", message.PeerId);
        Assert.Equal("plain text fallback", message.Content);
    }

    [Fact]
    public void SceneChatService_WhenOneSubscriberThrows_ContinuesInvokingRemainingSubscribers()
    {
        var pubsub = new StubScenePubSubService();
        var profileService = new Mock<IProfileService>();
        profileService
            .Setup(service => service.GetMyProfileAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(new PeerProfile { PeerId = "local-peer" });

        var service = new SceneChatService(
            NullLogger<SceneChatService>.Instance,
            pubsub,
            CreateOptionsMonitor(),
            profileService.Object);

        SceneChatMessage? received = null;
        service.MessageReceived += (_, _) => throw new InvalidOperationException("boom");
        service.MessageReceived += (_, message) => received = message;

        pubsub.RaiseMessageReceived(new SceneMessageReceivedEventArgs
        {
            SceneId = "scene:test",
            PeerId = "remote-peer",
            Message = System.Text.Encoding.UTF8.GetBytes("plain text fallback"),
            Timestamp = DateTimeOffset.UtcNow,
        });

        Assert.NotNull(received);
        Assert.Equal("scene:test", received!.SceneId);
        Assert.Equal("remote-peer", received.PeerId);
    }

    [Fact]
    public async Task ScenePubSubService_PollLoop_DoesNotOverlapWhenPollTakesLongerThanInterval()
    {
        using var dht = new BlockingDhtClient();
        using var service = new ScenePubSubService(
            NullLogger<ScenePubSubService>.Instance,
            dht,
            TimeSpan.FromMilliseconds(10));

        await service.SubscribeAsync("scene:test", CancellationToken.None);

        Assert.True(await dht.FirstCallStarted.Task.WaitAsync(TimeSpan.FromSeconds(30)));

        await Task.Delay(80);

        Assert.Equal(1, dht.MaxConcurrentCalls);

        dht.AllowCallsToComplete.Set();
    }

    [Fact]
    public async Task ScenePubSubService_DisposeTimeout_KeepsCancellationSourceUntilPollLoopCompletes()
    {
        using var dht = new CancellationIgnoringDhtClient();
        using var service = new ScenePubSubService(
            NullLogger<ScenePubSubService>.Instance,
            dht,
            TimeSpan.FromMilliseconds(10),
            TimeSpan.FromMilliseconds(50));

        await service.SubscribeAsync("scene:test", CancellationToken.None);
        await dht.FirstCallStarted.Task.WaitAsync(TimeSpan.FromSeconds(5));

        var cancellationSourceField = typeof(ScenePubSubService).GetField(
            "pollLoopCancellationTokenSource",
            BindingFlags.Instance | BindingFlags.NonPublic);
        var pollLoopTaskField = typeof(ScenePubSubService).GetField(
            "pollLoopTask",
            BindingFlags.Instance | BindingFlags.NonPublic);
        Assert.NotNull(cancellationSourceField);
        Assert.NotNull(pollLoopTaskField);
        var cancellationSource = Assert.IsType<CancellationTokenSource>(
            cancellationSourceField!.GetValue(service));
        var pollLoopTask = Assert.IsAssignableFrom<Task>(pollLoopTaskField!.GetValue(service));

        try
        {
            service.Dispose();

            Assert.True(cancellationSource.IsCancellationRequested);
            Assert.True(cancellationSource.Token.IsCancellationRequested);
        }
        finally
        {
            dht.AllowCallsToComplete.Set();
        }

        await pollLoopTask.WaitAsync(TimeSpan.FromSeconds(5));
        Assert.True(
            SpinWait.SpinUntil(
                () =>
                {
                    try
                    {
                        _ = cancellationSource.Token;
                        return false;
                    }
                    catch (ObjectDisposedException)
                    {
                        return true;
                    }
                },
                TimeSpan.FromSeconds(5)),
            "The poll-loop cancellation source should be disposed after the poll loop completes.");
    }

    [Fact]
    public void ScenePubSubService_WhenOneSubscriberThrows_ContinuesInvokingRemainingSubscribers()
    {
        using var service = new TestScenePubSubService(
            NullLogger<ScenePubSubService>.Instance,
            new StubDhtClient());

        SceneMessageReceivedEventArgs? received = null;
        service.MessageReceived += (_, _) => throw new InvalidOperationException("boom");
        service.MessageReceived += (_, args) => received = args;

        var args = new SceneMessageReceivedEventArgs
        {
            SceneId = "scene:test",
            PeerId = "peer-1",
            Message = [1, 2, 3],
            Timestamp = DateTimeOffset.UtcNow,
        };

        service.Raise(args);

        Assert.Same(args, received);
    }

    private static IOptionsMonitor<slskd.Options> CreateOptionsMonitor()
    {
        var options = new slskd.Options
        {
            VirtualSoulfind = new slskd.Core.VirtualSoulfindOptions
            {
                Scenes = new slskd.Core.ScenesOptions
                {
                    EnableChat = true,
                },
            },
        };

        var monitor = new Mock<IOptionsMonitor<slskd.Options>>();
        monitor.SetupGet(m => m.CurrentValue).Returns(options);
        return monitor.Object;
    }

    private sealed class StubScenePubSubService : IScenePubSubService
    {
        public event EventHandler<SceneMessageReceivedEventArgs>? MessageReceived;

        public void Dispose()
        {
        }

        public Task PublishAsync(string sceneId, byte[] message, CancellationToken ct = default) => Task.CompletedTask;

        public void RaiseMessageReceived(SceneMessageReceivedEventArgs args)
        {
            MessageReceived?.Invoke(this, args);
        }

        public Task SubscribeAsync(string sceneId, CancellationToken ct = default) => Task.CompletedTask;

        public Task UnsubscribeAsync(string sceneId, CancellationToken ct = default) => Task.CompletedTask;
    }

    private sealed class StubDhtClient : IDhtClient
    {
        public Task<byte[]?> GetAsync(byte[] key, CancellationToken ct = default) => Task.FromResult<byte[]?>(null);

        public Task<List<byte[]>> GetMultipleAsync(byte[] key, CancellationToken ct = default) => Task.FromResult(new List<byte[]>());

        public Task PutAsync(byte[] key, byte[] value, int ttlSeconds, CancellationToken ct = default) => Task.CompletedTask;
    }

    private sealed class BlockingDhtClient : IDhtClient, IDisposable
    {
        private int _activeCalls;

        public BlockingDhtClient()
        {
            FirstCallStarted = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        }

        public ManualResetEventSlim AllowCallsToComplete { get; } = new(false);

        public TaskCompletionSource<bool> FirstCallStarted { get; }

        public int MaxConcurrentCalls { get; private set; }

        public Task<byte[]?> GetAsync(byte[] key, CancellationToken ct = default) => Task.FromResult<byte[]?>(null);

        public Task<List<byte[]>> GetMultipleAsync(byte[] key, CancellationToken ct = default)
        {
            var current = Interlocked.Increment(ref _activeCalls);
            MaxConcurrentCalls = Math.Max(MaxConcurrentCalls, current);
            FirstCallStarted.TrySetResult(true);

            try
            {
                AllowCallsToComplete.Wait(ct);
                return Task.FromResult(new List<byte[]>());
            }
            finally
            {
                Interlocked.Decrement(ref _activeCalls);
            }
        }

        public Task PutAsync(byte[] key, byte[] value, int ttlSeconds, CancellationToken ct = default) => Task.CompletedTask;

        public void Dispose()
        {
            AllowCallsToComplete.Set();
            AllowCallsToComplete.Dispose();
        }
    }

    private sealed class CancellationIgnoringDhtClient : IDhtClient, IDisposable
    {
        public ManualResetEventSlim AllowCallsToComplete { get; } = new(false);

        public TaskCompletionSource<bool> FirstCallStarted { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

        public Task<byte[]?> GetAsync(byte[] key, CancellationToken ct = default) => Task.FromResult<byte[]?>(null);

        public Task<List<byte[]>> GetMultipleAsync(byte[] key, CancellationToken ct = default)
        {
            FirstCallStarted.TrySetResult(true);
            AllowCallsToComplete.Wait(CancellationToken.None);
            return Task.FromResult(new List<byte[]>());
        }

        public Task PutAsync(byte[] key, byte[] value, int ttlSeconds, CancellationToken ct = default) => Task.CompletedTask;

        public void Dispose()
        {
            AllowCallsToComplete.Set();
            AllowCallsToComplete.Dispose();
        }
    }

    private sealed class TestScenePubSubService : ScenePubSubService
    {
        public TestScenePubSubService(
            Microsoft.Extensions.Logging.ILogger<ScenePubSubService> logger,
            IDhtClient dht)
            : base(logger, dht, TimeSpan.FromHours(1))
        {
        }

        public void Raise(SceneMessageReceivedEventArgs args)
        {
            OnMessageReceived(args);
        }
    }
}
