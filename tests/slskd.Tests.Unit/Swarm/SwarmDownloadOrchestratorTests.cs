// <copyright file="SwarmDownloadOrchestratorTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Swarm;

using System.Collections.Generic;
using System.Reflection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using slskd.Swarm;
using slskd.Transfers.MultiSource.Scheduling;
using Soulseek;
using Xunit;

public sealed class SwarmDownloadOrchestratorTests : IDisposable
{
    private readonly string _tempDirectory = Path.Combine(Path.GetTempPath(), $"slskdn-swarm-tests-{Guid.NewGuid():N}");

    public SwarmDownloadOrchestratorTests()
    {
        System.IO.Directory.CreateDirectory(_tempDirectory);
    }

    public void Dispose()
    {
        if (System.IO.Directory.Exists(_tempDirectory))
        {
            System.IO.Directory.Delete(_tempDirectory, recursive: true);
        }
    }

    [Fact]
    public async Task ProcessJob_EscapesRemoteJobFieldsBeforeLogging()
    {
        var messages = new List<string>();
        using var orchestrator = new SwarmDownloadOrchestrator(
            new CapturingLogger<SwarmDownloadOrchestrator>(messages),
            Mock.Of<IVerificationEngine>(),
            Mock.Of<IChunkScheduler>(),
            Mock.Of<ISoulseekClient>(),
            optionsMonitor: null,
            tempRoot: _tempDirectory);
        var job = new SwarmJob(
            "job\r\ninjected",
            new SwarmFile("content\r\ninjected", "hash", 1024, Filename: "remote\r\nfile.flac"),
            Array.Empty<SwarmSource>());

        await InvokeProcessJobAsync(orchestrator, job, CancellationToken.None);

        var renderedMessages = string.Join("\n", messages);
        Assert.Contains("job\\r\\ninjected", renderedMessages);
        Assert.Contains("content\\r\\ninjected", renderedMessages);
        Assert.DoesNotContain("\r\n", renderedMessages);
        Assert.Equal("job\r\ninjected", job.JobId);
        Assert.Equal("content\r\ninjected", job.File.ContentId);
    }

    [Fact]
    public void Enqueue_WhenBoundedQueueIsFull_ReturnsFalse()
    {
        var orchestrator = CreateOrchestrator();

        for (var index = 0; index < 1024; index++)
        {
            Assert.True(orchestrator.Enqueue(CreateQueueJob(index)));
        }

        Assert.False(orchestrator.Enqueue(CreateQueueJob(1024)));
    }

    [Fact]
    public async Task DownloadChunkAsync_WhenPeerSourceIsMissing_ReturnsSanitizedError()
    {
        var orchestrator = CreateOrchestrator();
        var method = typeof(SwarmDownloadOrchestrator).GetMethod("DownloadChunkAsync", BindingFlags.NonPublic | BindingFlags.Instance);
        Assert.NotNull(method);

        var task = (Task<ChunkResult>)method!.Invoke(
            orchestrator,
            new object[]
            {
                new SwarmJob("job-1", new SwarmFile("content-1", "hash-1", 1024), new List<SwarmSource>()),
                new ChunkInfo { Index = 0, StartOffset = 0, EndOffset = 512 },
                "peer-secret",
                Path.GetTempPath(),
                CancellationToken.None,
            })!;

        var result = await task;

        Assert.False(result.Success);
        Assert.Equal("Chunk source not found", result.Error);
        Assert.DoesNotContain("peer-secret", result.Error, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task DownloadChunkAsync_WhenTransportIsUnsupported_ReturnsSanitizedError()
    {
        var orchestrator = CreateOrchestrator();
        var method = typeof(SwarmDownloadOrchestrator).GetMethod("DownloadChunkAsync", BindingFlags.NonPublic | BindingFlags.Instance);
        Assert.NotNull(method);

        var task = (Task<ChunkResult>)method!.Invoke(
            orchestrator,
            new object[]
            {
                new SwarmJob(
                    "job-1",
                    new SwarmFile("content-1", "hash-1", 1024),
                    new List<SwarmSource> { new("peer-1", "secret-transport") }),
                new ChunkInfo { Index = 0, StartOffset = 0, EndOffset = 512 },
                "peer-1",
                Path.GetTempPath(),
                CancellationToken.None,
            })!;

        var result = await task;

        Assert.False(result.Success);
        Assert.Equal("Unsupported chunk transport", result.Error);
        Assert.DoesNotContain("secret-transport", result.Error, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task DownloadChunkAsync_WhenMeshTransportIsRequested_ReturnsSanitizedError()
    {
        var orchestrator = CreateOrchestrator();
        var method = typeof(SwarmDownloadOrchestrator).GetMethod("DownloadChunkAsync", BindingFlags.NonPublic | BindingFlags.Instance);
        Assert.NotNull(method);

        var task = (Task<ChunkResult>)method!.Invoke(
            orchestrator,
            new object[]
            {
                new SwarmJob(
                    "job-1",
                    new SwarmFile("content-1", "hash-1", 1024),
                    new List<SwarmSource> { new("peer-1", "mesh") }),
                new ChunkInfo { Index = 0, StartOffset = 0, EndOffset = 512 },
                "peer-1",
                Path.GetTempPath(),
                CancellationToken.None,
            })!;

        var result = await task;

        Assert.False(result.Success);
        Assert.Equal("Mesh transport chunk download is unavailable", result.Error);
        Assert.DoesNotContain("not yet implemented", result.Error, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task DownloadChunkAsync_WhenCallerCancels_PropagatesCancellation()
    {
        var username = $"cancel-peer-{Guid.NewGuid():N}";
        var enteredDownload = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (
                string _,
                string _,
                Func<Task<Stream>> _,
                long _,
                long _,
                int? _,
                TransferOptions _,
                CancellationToken token) =>
            {
                enteredDownload.TrySetResult();
                await Task.Delay(Timeout.Infinite, token);
                throw new InvalidOperationException("The canceled chunk unexpectedly completed.");
            });
        var orchestrator = CreateOrchestrator(soulseekClient.Object, tempRoot: _tempDirectory);
        using var cancellation = new CancellationTokenSource();
        var download = InvokeDownloadChunkAsync(
            orchestrator,
            new SwarmJob(
                "job-1",
                new SwarmFile("content-1", "hash-1", 1024, Filename: "song.flac"),
                new List<SwarmSource> { new(username, "soulseek") }),
            new ChunkInfo { Index = 0, StartOffset = 0, EndOffset = 512 },
            username,
            _tempDirectory,
            cancellation.Token);

        await enteredDownload.Task.WaitAsync(TimeSpan.FromSeconds(5));
        cancellation.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => download.WaitAsync(TimeSpan.FromSeconds(5)));
    }

    [Fact]
    public async Task ProcessJob_WhenCompleted_RemovesChunkFilesAndContainsJobPaths()
    {
        var storageRoot = Path.Combine(_tempDirectory, "storage");
        System.IO.Directory.CreateDirectory(storageRoot);
        var escapedName = $"escaped-{Guid.NewGuid():N}";
        var jobId = $"../{escapedName}";
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (
                string username,
                string remoteFilename,
                Func<Task<Stream>> outputStreamFactory,
                long size,
                long startOffset,
                int? token,
                TransferOptions options,
                CancellationToken cancellationToken) =>
            {
                var stream = await outputStreamFactory();
                var chunkLength = (int)Math.Min(512 * 1024, size - startOffset);
                var chunkData = Enumerable.Repeat(startOffset == 0 ? (byte)1 : (byte)2, chunkLength).ToArray();
                await stream.WriteAsync(chunkData, cancellationToken);
                return new Transfer(
                    TransferDirection.Download,
                    username,
                    remoteFilename,
                    token ?? 1,
                    TransferStates.Completed,
                    size,
                    startOffset,
                    startOffset + chunkLength);
            });
        var scheduler = new Mock<IChunkScheduler>();
        scheduler
            .Setup(value => value.AssignChunkAsync(
                It.IsAny<ChunkRequest>(),
                It.IsAny<List<string>>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(new ChunkAssignment { Success = true, AssignedPeer = "peer-1" });
        var verifier = new Mock<IVerificationEngine>();
        verifier
            .Setup(value => value.VerifyChunkAsync(
                It.IsAny<string>(), It.IsAny<int>(), It.IsAny<byte[]>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(true);
        var orchestrator = CreateOrchestrator(soulseekClient.Object, scheduler.Object, verifier.Object, storageRoot);
        var job = new SwarmJob(
            jobId,
            new SwarmFile("Music/song.flac", "hash-1", 512 * 1024 + 256, Filename: "Music/song.flac"),
            new List<SwarmSource> { new("peer-1", "soulseek") });

        var directChunkDirectory = Path.Combine(storageRoot, "direct-chunk");
        System.IO.Directory.CreateDirectory(directChunkDirectory);
        var directChunk = await InvokeDownloadChunkAsync(
            orchestrator,
            job,
            new ChunkInfo { Index = 0, StartOffset = 0, EndOffset = 512 },
            "peer-1",
            directChunkDirectory,
            CancellationToken.None);
        Assert.True(directChunk.Success, directChunk.Error);
        Assert.Equal(512, directChunk.Data!.Length);

        await InvokeProcessJobAsync(orchestrator, job, CancellationToken.None).WaitAsync(TimeSpan.FromSeconds(10));

        var chunksRoot = Path.Combine(storageRoot, "slskdn-swarm");
        Assert.True(System.IO.Directory.Exists(chunksRoot));
        Assert.Empty(System.IO.Directory.EnumerateFileSystemEntries(chunksRoot));
        Assert.False(System.IO.Directory.Exists(Path.Combine(storageRoot, escapedName)));
        Assert.False(System.IO.File.Exists(Path.Combine(storageRoot, $"{escapedName}_song.flac")));
        var outputRoot = Path.Combine(storageRoot, "slskdn-swarm-output");
        Assert.True(System.IO.Directory.Exists(outputRoot));
        var outputFiles = System.IO.Directory.GetFiles(outputRoot);
        var outputFile = Assert.Single(outputFiles);
        Assert.Equal(512 * 1024 + 256, new FileInfo(outputFile).Length);
        Assert.Equal(
            Enumerable.Repeat((byte)1, 512 * 1024).Concat(Enumerable.Repeat((byte)2, 256)),
            await System.IO.File.ReadAllBytesAsync(outputFile));
        Assert.False(System.IO.Directory.Exists(Path.Combine(outputRoot, ".partial")));
        scheduler.Verify(value => value.AssignChunkAsync(
            It.IsAny<ChunkRequest>(),
            It.IsAny<List<string>>(),
            It.IsAny<CancellationToken>()), Times.Exactly(2));
        verifier.Verify(value => value.VerifyChunkAsync(
            "Music/song.flac", 0, It.Is<byte[]>(bytes => bytes.Length == 512 * 1024), It.IsAny<CancellationToken>()), Times.Once);
        verifier.Verify(value => value.VerifyChunkAsync(
            "Music/song.flac", 1, It.Is<byte[]>(bytes => bytes.Length == 256), It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task ProcessJob_WhenPeerAssignmentKeepsFailing_StopsAfterBoundedAttempts()
    {
        var storageRoot = Path.Combine(_tempDirectory, "assignment-failure-storage");
        System.IO.Directory.CreateDirectory(storageRoot);
        var scheduler = new Mock<IChunkScheduler>();
        scheduler
            .Setup(value => value.AssignChunkAsync(
                It.IsAny<ChunkRequest>(),
                It.IsAny<List<string>>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(new ChunkAssignment { Success = false, Reason = "no available peer" });
        var orchestrator = CreateOrchestrator(chunkScheduler: scheduler.Object, tempRoot: storageRoot);
        var job = new SwarmJob(
            $"job-{Guid.NewGuid():N}",
            new SwarmFile("content-1", "hash-1", 512),
            new List<SwarmSource> { new("peer-1", "soulseek") });

        await InvokeProcessJobAsync(orchestrator, job, CancellationToken.None).WaitAsync(TimeSpan.FromSeconds(5));

        scheduler.Verify(value => value.AssignChunkAsync(
            It.IsAny<ChunkRequest>(),
            It.IsAny<List<string>>(),
            It.IsAny<CancellationToken>()), Times.Exactly(3));
        var chunksRoot = Path.Combine(storageRoot, "slskdn-swarm");
        Assert.True(System.IO.Directory.Exists(chunksRoot));
        Assert.Empty(System.IO.Directory.EnumerateFileSystemEntries(chunksRoot));
    }

    [Fact]
    public async Task ProcessJob_WhenChunkDownloadKeepsFailing_StopsAfterBoundedAttempts()
    {
        var storageRoot = Path.Combine(_tempDirectory, "download-failure-storage");
        System.IO.Directory.CreateDirectory(storageRoot);
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(new IOException("peer unavailable"));
        var scheduler = CreateSuccessfulScheduler();
        var verifier = new Mock<IVerificationEngine>();
        var orchestrator = CreateOrchestrator(soulseekClient.Object, scheduler.Object, verifier.Object, storageRoot);
        var job = CreateSmallJob();

        await InvokeProcessJobAsync(orchestrator, job, CancellationToken.None).WaitAsync(TimeSpan.FromSeconds(5));

        VerifyChunkWork(scheduler, soulseekClient, verifier, expectedVerificationCount: 0);
        AssertChunkDirectoryClean(storageRoot);
    }

    [Fact]
    public async Task ProcessJob_WhenChunkVerificationKeepsFailing_StopsAfterBoundedAttempts()
    {
        var storageRoot = Path.Combine(_tempDirectory, "verification-failure-storage");
        System.IO.Directory.CreateDirectory(storageRoot);
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (
                string username,
                string remoteFilename,
                Func<Task<Stream>> outputStreamFactory,
                long size,
                long startOffset,
                int? token,
                TransferOptions options,
                CancellationToken cancellationToken) =>
            {
                var stream = await outputStreamFactory();
                await stream.WriteAsync(new byte[512], cancellationToken);
                return new Transfer(
                    TransferDirection.Download,
                    username,
                    remoteFilename,
                    token ?? 1,
                    TransferStates.Completed,
                    size,
                    startOffset,
                    startOffset + 512);
            });
        var scheduler = CreateSuccessfulScheduler();
        var verifier = new Mock<IVerificationEngine>();
        verifier
            .Setup(value => value.VerifyChunkAsync(
                It.IsAny<string>(), It.IsAny<int>(), It.IsAny<byte[]>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);
        var orchestrator = CreateOrchestrator(soulseekClient.Object, scheduler.Object, verifier.Object, storageRoot);
        var job = CreateSmallJob();

        await InvokeProcessJobAsync(orchestrator, job, CancellationToken.None).WaitAsync(TimeSpan.FromSeconds(5));

        VerifyChunkWork(scheduler, soulseekClient, verifier, expectedVerificationCount: 3);
        AssertChunkDirectoryClean(storageRoot);
    }

    [Fact]
    public async Task ProcessJob_WhenChunkDisappearsBeforeAssembly_LeavesNoPartialOutput()
    {
        var storageRoot = Path.Combine(_tempDirectory, "assembly-failure-storage");
        System.IO.Directory.CreateDirectory(storageRoot);
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (
                string username,
                string remoteFilename,
                Func<Task<Stream>> outputStreamFactory,
                long size,
                long startOffset,
                int? token,
                TransferOptions options,
                CancellationToken cancellationToken) =>
            {
                var stream = await outputStreamFactory();
                await stream.WriteAsync(new byte[512], cancellationToken);
                return new Transfer(
                    TransferDirection.Download,
                    username,
                    remoteFilename,
                    token ?? 1,
                    TransferStates.Completed,
                    size,
                    startOffset,
                    startOffset + 512);
            });
        var verifier = new Mock<IVerificationEngine>();
        verifier
            .Setup(value => value.VerifyChunkAsync(
                It.IsAny<string>(), It.IsAny<int>(), It.IsAny<byte[]>(), It.IsAny<CancellationToken>()))
            .Returns((string _, int _, byte[] _, CancellationToken _) =>
            {
                var chunksRoot = Path.Combine(storageRoot, "slskdn-swarm");
                var jobTempDirectory = Assert.Single(System.IO.Directory.GetDirectories(chunksRoot));
                System.IO.File.Delete(Path.Combine(jobTempDirectory, "chunk_0.tmp"));
                return Task.FromResult(true);
            });
        var orchestrator = CreateOrchestrator(
            soulseekClient.Object,
            CreateSuccessfulScheduler().Object,
            verifier.Object,
            storageRoot);

        await InvokeProcessJobAsync(orchestrator, CreateSmallJob(), CancellationToken.None).WaitAsync(TimeSpan.FromSeconds(5));

        var outputRoot = Path.Combine(storageRoot, "slskdn-swarm-output");
        Assert.True(System.IO.Directory.Exists(outputRoot));
        Assert.Empty(System.IO.Directory.EnumerateFileSystemEntries(outputRoot));
        AssertChunkDirectoryClean(storageRoot);
    }

    [Fact]
    public async Task ProcessJob_WhenNoSoulseekPeerExists_RemovesTemporaryDirectory()
    {
        var storageRoot = Path.Combine(_tempDirectory, "failure-storage");
        System.IO.Directory.CreateDirectory(storageRoot);
        var orchestrator = CreateOrchestrator(tempRoot: storageRoot);
        var job = new SwarmJob(
            $"job-{Guid.NewGuid():N}",
            new SwarmFile("content-1", "hash-1", 1024),
            new List<SwarmSource> { new("mesh-peer", "mesh") });

        await InvokeProcessJobAsync(orchestrator, job, CancellationToken.None).WaitAsync(TimeSpan.FromSeconds(5));

        var chunksRoot = Path.Combine(storageRoot, "slskdn-swarm");
        Assert.True(System.IO.Directory.Exists(chunksRoot));
        Assert.Empty(System.IO.Directory.EnumerateFileSystemEntries(chunksRoot));
    }

    [Fact]
    public async Task ProcessJob_WhenCanceled_DrainsAndRemovesTemporaryDirectory()
    {
        var storageRoot = Path.Combine(_tempDirectory, "cancel-storage");
        System.IO.Directory.CreateDirectory(storageRoot);
        var jobId = $"../escape-{Guid.NewGuid():N}";
        var enteredAssignment = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var scheduler = new Mock<IChunkScheduler>();
        scheduler
            .Setup(value => value.AssignChunkAsync(
                It.IsAny<ChunkRequest>(),
                It.IsAny<List<string>>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (ChunkRequest _, List<string> _, CancellationToken token) =>
            {
                enteredAssignment.TrySetResult();
                await Task.Delay(Timeout.Infinite, token);
                return new ChunkAssignment { Success = false };
            });
        var orchestrator = CreateOrchestrator(chunkScheduler: scheduler.Object, tempRoot: storageRoot);
        using var cancellation = new CancellationTokenSource();
        var job = new SwarmJob(
            jobId,
            new SwarmFile("content-1", "hash-1", 1024),
            new List<SwarmSource> { new("peer-1", "soulseek") });

        var process = InvokeProcessJobAsync(orchestrator, job, cancellation.Token);
        await enteredAssignment.Task.WaitAsync(TimeSpan.FromSeconds(5));
        cancellation.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => process.WaitAsync(TimeSpan.FromSeconds(30)));
        var chunksRoot = Path.Combine(storageRoot, "slskdn-swarm");
        Assert.True(System.IO.Directory.Exists(chunksRoot));
        Assert.Empty(System.IO.Directory.EnumerateFileSystemEntries(chunksRoot));
    }

    private static SwarmDownloadOrchestrator CreateOrchestrator(
        ISoulseekClient? soulseekClient = null,
        IChunkScheduler? chunkScheduler = null,
        IVerificationEngine? verifier = null,
        string? tempRoot = null)
    {
        var logger = NullLogger<SwarmDownloadOrchestrator>.Instance;
        var verificationEngine = verifier ?? Mock.Of<IVerificationEngine>();
        var scheduler = chunkScheduler ?? Mock.Of<IChunkScheduler>();
        var client = soulseekClient ?? Mock.Of<ISoulseekClient>();
        return tempRoot == null
            ? new SwarmDownloadOrchestrator(logger, verificationEngine, scheduler, client)
            : new SwarmDownloadOrchestrator(logger, verificationEngine, scheduler, client, optionsMonitor: null, tempRoot: tempRoot);
    }

    private static Mock<IChunkScheduler> CreateSuccessfulScheduler()
    {
        var scheduler = new Mock<IChunkScheduler>();
        scheduler
            .Setup(value => value.AssignChunkAsync(
                It.IsAny<ChunkRequest>(),
                It.IsAny<List<string>>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(new ChunkAssignment { Success = true, AssignedPeer = "peer-1" });
        return scheduler;
    }

    private static SwarmJob CreateSmallJob()
        => new(
            $"job-{Guid.NewGuid():N}",
            new SwarmFile("content-1", "hash-1", 512),
            new List<SwarmSource> { new("peer-1", "soulseek") });

    private static SwarmJob CreateQueueJob(int index)
        => new(
            $"queue-job-{index}",
            new SwarmFile($"content-{index}", "hash", 0),
            Array.Empty<SwarmSource>());

    private static void VerifyChunkWork(
        Mock<IChunkScheduler> scheduler,
        Mock<ISoulseekClient> soulseekClient,
        Mock<IVerificationEngine> verifier,
        int expectedVerificationCount)
    {
        scheduler.Verify(value => value.AssignChunkAsync(
            It.IsAny<ChunkRequest>(),
            It.IsAny<List<string>>(),
            It.IsAny<CancellationToken>()), Times.Exactly(3));
        soulseekClient.Verify(client => client.DownloadAsync(
            It.IsAny<string>(),
            It.IsAny<string>(),
            It.IsAny<Func<Task<Stream>>>(),
            It.IsAny<long>(),
            It.IsAny<long>(),
            It.IsAny<int?>(),
            It.IsAny<TransferOptions>(),
            It.IsAny<CancellationToken>()), Times.Exactly(expectedVerificationCount == 0 ? 3 : expectedVerificationCount));
        verifier.Verify(value => value.VerifyChunkAsync(
            It.IsAny<string>(), It.IsAny<int>(), It.IsAny<byte[]>(), It.IsAny<CancellationToken>()),
            Times.Exactly(expectedVerificationCount));
    }

    private static void AssertChunkDirectoryClean(string storageRoot)
    {
        var chunksRoot = Path.Combine(storageRoot, "slskdn-swarm");
        Assert.True(System.IO.Directory.Exists(chunksRoot));
        Assert.Empty(System.IO.Directory.EnumerateFileSystemEntries(chunksRoot));
    }

    private static Task InvokeProcessJobAsync(SwarmDownloadOrchestrator orchestrator, SwarmJob job, CancellationToken cancellationToken)
    {
        var method = typeof(SwarmDownloadOrchestrator).GetMethod("ProcessJob", BindingFlags.NonPublic | BindingFlags.Instance);
        Assert.NotNull(method);
        return (Task)method!.Invoke(orchestrator, new object[] { job, cancellationToken })!;
    }

    private static Task<ChunkResult> InvokeDownloadChunkAsync(
        SwarmDownloadOrchestrator orchestrator,
        SwarmJob job,
        ChunkInfo chunk,
        string peerId,
        string tempDirectory,
        CancellationToken cancellationToken)
    {
        var method = typeof(SwarmDownloadOrchestrator).GetMethod("DownloadChunkAsync", BindingFlags.NonPublic | BindingFlags.Instance);
        Assert.NotNull(method);
        return (Task<ChunkResult>)method!.Invoke(
            orchestrator,
            new object[] { job, chunk, peerId, tempDirectory, cancellationToken })!;
    }

    private sealed class CapturingLogger<T> : ILogger<T>
    {
        private readonly ICollection<string> _messages;

        public CapturingLogger(ICollection<string> messages)
        {
            _messages = messages;
        }

        public IDisposable? BeginScope<TState>(TState state)
            where TState : notnull
            => null;

        public bool IsEnabled(LogLevel logLevel) => true;

        public void Log<TState>(
            LogLevel logLevel,
            EventId eventId,
            TState state,
            Exception? exception,
            Func<TState, Exception?, string> formatter)
        {
            _messages.Add(formatter(state, exception));
        }
    }
}
