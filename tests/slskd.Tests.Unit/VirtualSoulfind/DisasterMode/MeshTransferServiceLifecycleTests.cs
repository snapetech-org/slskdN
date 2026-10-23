// <copyright file="MeshTransferServiceLifecycleTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.VirtualSoulfind.DisasterMode;

using System;
using System.Collections.Concurrent;
using System.Reflection;
using System.Reactive.Subjects;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using slskd.VirtualSoulfind.DisasterMode;
using slskd.VirtualSoulfind.ShadowIndex;
using Xunit;

public class MeshTransferServiceLifecycleTests
{
    [Fact]
    public async Task CompletedTransfers_RetireProgressSubjectsAndCancellationSources()
    {
        using var service = CreateService();

        var transferId = await service.StartTransferAsync(
            peerId: "peer-a",
            fileHash: string.Empty,
            fileSize: 1024,
            targetPath: Path.Combine(Path.GetTempPath(), "slskdn-mesh-transfer-lifecycle", $"{Guid.NewGuid():N}.bin"),
            ct: CancellationToken.None);

        var deadline = DateTimeOffset.UtcNow.AddSeconds(30);
        while (DateTimeOffset.UtcNow < deadline)
        {
            var status = await service.GetTransferStatusAsync(transferId, CancellationToken.None);
            var isTerminal = status is { State: MeshTransferState.Completed or MeshTransferState.Failed or MeshTransferState.Cancelled };
            var resourcesRetired = !GetCancellationSources(service).ContainsKey(transferId)
                && !GetProgressSubjects(service).ContainsKey(transferId);
            if (isTerminal && resourcesRetired)
            {
                break;
            }

            await Task.Delay(50);
        }

        Assert.DoesNotContain(transferId, GetCancellationSources(service).Keys);
        Assert.DoesNotContain(transferId, GetProgressSubjects(service).Keys);
    }

    [Fact]
    public void Dispose_CompletesProgressSubjectsAndDisposesTrackedCancellationSources()
    {
        var service = CreateService();
        var transferId = "transfer-1";
        var completed = false;
        using var cts = new CancellationTokenSource();

        service.SubscribeToProgress(transferId).Subscribe(_ => { }, () => completed = true);
        GetCancellationSources(service)[transferId] = cts;

        service.Dispose();

        Assert.True(completed);
        Assert.Empty(GetProgressSubjects(service));
        Assert.Empty(GetCancellationSources(service));
        Assert.True(cts.IsCancellationRequested);
        Assert.Throws<ObjectDisposedException>(() => _ = cts.Token.WaitHandle);
    }

    private static MeshTransferService CreateService()
    {
        var scenePeerDiscovery = new Mock<IScenePeerDiscovery>();
        scenePeerDiscovery
            .Setup(d => d.DiscoverPeersAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(["peer-a"]);

        return new MeshTransferService(
            NullLogger<MeshTransferService>.Instance,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options
            {
                Directories = new slskd.Options.DirectoriesOptions
                {
                    Downloads = Path.GetTempPath(),
                },
            }),
            Mock.Of<IShadowIndexQuery>(),
            scenePeerDiscovery.Object);
    }

    private static ConcurrentDictionary<string, CancellationTokenSource> GetCancellationSources(MeshTransferService service)
    {
        var field = typeof(MeshTransferService).GetField(
            "transferCancellationSources",
            BindingFlags.Instance | BindingFlags.NonPublic);

        return Assert.IsType<ConcurrentDictionary<string, CancellationTokenSource>>(field?.GetValue(service));
    }

    private static ConcurrentDictionary<string, Subject<TransferProgressUpdate>> GetProgressSubjects(MeshTransferService service)
    {
        var field = typeof(MeshTransferService).GetField(
            "progressSubjects",
            BindingFlags.Instance | BindingFlags.NonPublic);

        return Assert.IsType<ConcurrentDictionary<string, Subject<TransferProgressUpdate>>>(field?.GetValue(service));
    }
}
