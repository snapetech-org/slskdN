// <copyright file="DownloadServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Transfers.Downloads;

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Options;
using Moq;
using Serilog;
using Serilog.Core;
using Serilog.Events;
using slskd.Events;
using slskd.Files;
using slskd.HashDb;
using slskd.HashDb.Models;
using slskd.Integrations.FTP;
using slskd.Relay;
using slskd.Tests.Unit;
using slskd.Transfers;
using slskd.Transfers.AutoReplace;
using slskd.Transfers.Downloads;
using Soulseek;
using Xunit;

[Collection(StaticEventCollection.Name)]
public class DownloadServiceTests
{
    private static readonly string TestDirectoryRoot = System.IO.Path.Combine(
        System.IO.Path.GetTempPath(),
        $"slskdn-download-service-tests-{Guid.NewGuid():N}");

    private static slskd.Options CreateTestOptions()
    {
        return new slskd.Options
        {
            Directories = new slskd.Options.DirectoriesOptions
            {
                Downloads = System.IO.Path.Combine(TestDirectoryRoot, "downloads"),
                Incomplete = System.IO.Path.Combine(TestDirectoryRoot, "incomplete"),
            },
        };
    }

    [Fact]
    public async Task PruneRemoved_DeletesOnlyOldCompletedRemovedDownloads()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;
        var now = DateTime.UtcNow;
        var expiredId = Guid.NewGuid();
        var recentId = Guid.NewGuid();
        var activeRemovedId = Guid.NewGuid();
        var visibleId = Guid.NewGuid();
        var uploadId = Guid.NewGuid();

        slskd.Transfers.Transfer CreateTransfer(Guid id, TransferDirection direction, bool removed, DateTime? endedAt)
            => new()
            {
                Id = id,
                Username = "alice",
                Direction = direction,
                Filename = $"{id:N}.flac",
                RequestedAt = now.AddHours(-1),
                EndedAt = endedAt,
                State = endedAt.HasValue
                    ? TransferStates.Completed | TransferStates.Succeeded
                    : TransferStates.InProgress,
                Removed = removed,
            };

        try
        {
            await using (var context = new TransfersDbContext(options))
            {
                await context.Database.EnsureCreatedAsync();
                context.Transfers.AddRange(
                    CreateTransfer(expiredId, TransferDirection.Download, true, now.AddMinutes(-30)),
                    CreateTransfer(recentId, TransferDirection.Download, true, now),
                    CreateTransfer(activeRemovedId, TransferDirection.Download, true, null),
                    CreateTransfer(visibleId, TransferDirection.Download, false, now.AddMinutes(-30)),
                    CreateTransfer(uploadId, TransferDirection.Upload, true, now.AddMinutes(-30)));
                await context.SaveChangesAsync();

                await context.Database.ExecuteSqlInterpolatedAsync(
                    $"UPDATE Transfers SET UpdatedAt = {now.AddMinutes(-30)} WHERE Id IN ({expiredId}, {activeRemovedId}, {visibleId}, {uploadId})");
            }

            using var service = CreateDownloadService(options, new Mock<ISoulseekClient>());
            Assert.Equal(1, service.PruneRemoved(5));

            await using var verificationContext = new TransfersDbContext(options);
            var remainingIds = await verificationContext.Transfers.Select(transfer => transfer.Id).ToListAsync();
            Assert.DoesNotContain(expiredId, remainingIds);
            Assert.Contains(recentId, remainingIds);
            Assert.Contains(activeRemovedId, remainingIds);
            Assert.Contains(visibleId, remainingIds);
            Assert.Contains(uploadId, remainingIds);
        }
        finally
        {
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public async Task ListPage_UsesRequestedAtAndIdContinuationWithoutRepeatingRows()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;
        var requestedAt = new DateTime(2026, 10, 13, 12, 0, 0, DateTimeKind.Utc);
        var downloadIds = new[]
        {
            Guid.Parse("00000000-0000-0000-0000-000000000001"),
            Guid.Parse("00000000-0000-0000-0000-000000000002"),
            Guid.Parse("00000000-0000-0000-0000-000000000003"),
        };

        slskd.Transfers.Transfer CreateTransfer(Guid id, TransferDirection direction, bool removed = false)
            => new()
            {
                Id = id,
                Username = "alice",
                Direction = direction,
                Filename = $"{id:N}.flac",
                RequestedAt = requestedAt,
                State = TransferStates.InProgress,
                Removed = removed,
            };

        try
        {
            await using (var context = new TransfersDbContext(options))
            {
                await context.Database.EnsureCreatedAsync();
                context.Transfers.AddRange(
                    downloadIds
                        .Select(id => CreateTransfer(id, TransferDirection.Download))
                        .Concat(new[]
                        {
                            CreateTransfer(Guid.NewGuid(), TransferDirection.Download, removed: true),
                            CreateTransfer(Guid.NewGuid(), TransferDirection.Upload),
                        }));
                await context.SaveChangesAsync();
            }

            using var service = CreateDownloadService(options, new Mock<ISoulseekClient>());
            var firstPage = service.ListPage(transfer => true, false, null, null, limit: 2);
            var last = Assert.IsType<slskd.Transfers.Transfer>(firstPage.LastOrDefault());
            var secondPage = service.ListPage(
                transfer => true,
                false,
                last.RequestedAt,
                last.Id,
                limit: 2);

            Assert.Equal(downloadIds.Reverse().Take(2), firstPage.Select(transfer => transfer.Id));
            Assert.Equal(downloadIds.Take(1), secondPage.Select(transfer => transfer.Id));
            Assert.Empty(service.ListPage(
                transfer => true,
                false,
                secondPage.Single().RequestedAt,
                secondPage.Single().Id,
                limit: 2));
        }
        finally
        {
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public async Task PruneRemoved_DeletesOnlyExpiredTerminalRequestsWithoutRemainingDownloads()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;
        var now = DateTime.UtcNow;
        var expiredRequestId = Guid.NewGuid();
        var activeRequestId = Guid.NewGuid();
        var recentRequestId = Guid.NewGuid();
        var visibleRequestId = Guid.NewGuid();
        var recentTransferRequestId = Guid.NewGuid();

        DownloadRequest CreateRequest(Guid id, DownloadRequestState state, DateTime createdAt, DateTime? completedAt)
            => new()
            {
                Id = id,
                Name = id.ToString("N"),
                OriginalFilename = $"{id:N}.flac",
                State = state,
                CreatedAt = createdAt,
                CompletedAt = completedAt,
            };

        slskd.Transfers.Transfer CreateTransfer(Guid requestId, bool removed, DateTime endedAt)
            => new()
            {
                Id = Guid.NewGuid(),
                RequestId = requestId,
                Username = "alice",
                Direction = TransferDirection.Download,
                Filename = $"{Guid.NewGuid():N}.flac",
                RequestedAt = now.AddHours(-1),
                EndedAt = endedAt,
                UpdatedAt = endedAt,
                State = TransferStates.Completed | TransferStates.Succeeded,
                Removed = removed,
            };

        try
        {
            await using (var context = new TransfersDbContext(options))
            {
                await context.Database.EnsureCreatedAsync();
                context.DownloadRequests.AddRange(
                    CreateRequest(expiredRequestId, DownloadRequestState.Completed, now.AddHours(-1), now.AddMinutes(-30)),
                    CreateRequest(activeRequestId, DownloadRequestState.Active, now.AddHours(-1), null),
                    CreateRequest(recentRequestId, DownloadRequestState.Failed, now.AddMinutes(-1), now.AddMinutes(-1)),
                    CreateRequest(visibleRequestId, DownloadRequestState.Completed, now.AddHours(-1), now.AddMinutes(-30)),
                    CreateRequest(recentTransferRequestId, DownloadRequestState.Cancelled, now.AddHours(-1), now.AddMinutes(-30)));
                context.Transfers.AddRange(
                    CreateTransfer(expiredRequestId, true, now.AddMinutes(-30)),
                    CreateTransfer(expiredRequestId, true, now.AddMinutes(-30)),
                    CreateTransfer(visibleRequestId, false, now.AddMinutes(-30)),
                    CreateTransfer(recentTransferRequestId, true, now));
                await context.SaveChangesAsync();
                await context.Database.ExecuteSqlInterpolatedAsync(
                    $"UPDATE Transfers SET UpdatedAt = {now.AddMinutes(-30)} WHERE RequestId = {expiredRequestId}");
            }

            using var service = CreateDownloadService(options, new Mock<ISoulseekClient>());
            Assert.Equal(2, service.PruneRemoved(5));

            await using var verificationContext = new TransfersDbContext(options);
            var remainingRequestIds = await verificationContext.DownloadRequests
                .Select(request => request.Id)
                .ToListAsync();
            Assert.DoesNotContain(expiredRequestId, remainingRequestIds);
            Assert.Contains(activeRequestId, remainingRequestIds);
            Assert.Contains(recentRequestId, remainingRequestIds);
            Assert.Contains(visibleRequestId, remainingRequestIds);
            Assert.Contains(recentTransferRequestId, remainingRequestIds);

            var remainingTransfers = await verificationContext.Transfers.ToListAsync();
            Assert.Equal(2, remainingTransfers.Count);
            Assert.All(remainingTransfers, transfer => Assert.NotEqual(expiredRequestId, transfer.RequestId));
        }
        finally
        {
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public async Task EnqueueAsync_GlobalDownloadExclusionEscapesPeerFieldsInLogsWithoutChangingRequestValues()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var username = "alice\r\ninjected";
        var filename = "Music\\Instrumental\\track\r\ninjected.flac";
        var sink = new CapturingLogSink();
        var originalLogger = Log.Logger;
        using var logger = new LoggerConfiguration()
            .MinimumLevel.Verbose()
            .WriteTo.Sink(sink)
            .CreateLogger();
        Log.Logger = logger;

        DownloadService? service = null;
        try
        {
            var soulseekClient = new Mock<ISoulseekClient>();
            soulseekClient.SetupGet(client => client.Downloads).Returns(Array.Empty<Soulseek.Transfer>());
            var configuredOptions = new slskd.Options
            {
                Filters = new slskd.Options.FiltersOptions
                {
                    Download = new slskd.Options.FiltersOptions.DownloadFilterOptions
                    {
                        Exclude = new[] { "instrumental" },
                    },
                },
            };
            service = CreateDownloadService(options, soulseekClient, configuredOptions);

            var (enqueued, failed) = await service.EnqueueAsync(
                username,
                new[] { (Filename: filename, Size: 1234L) },
                CancellationToken.None);

            Assert.Empty(enqueued);
            Assert.Equal(new[] { filename }, failed);

            var requestMessage = Assert.Single(sink.Events, logEvent => logEvent.RenderMessage().StartsWith("Requested enqueue", StringComparison.Ordinal));
            Assert.Contains("alice\\r\\ninjected", requestMessage.RenderMessage());
            Assert.DoesNotContain("\r\n", requestMessage.RenderMessage());

            var blockedMessage = Assert.Single(sink.Events, logEvent => logEvent.RenderMessage().StartsWith("Blocked download enqueue", StringComparison.Ordinal));
            Assert.Contains("track\\r\\ninjected.flac", blockedMessage.RenderMessage());
            Assert.Contains("alice\\r\\ninjected", blockedMessage.RenderMessage());
            Assert.DoesNotContain("\r\n", blockedMessage.RenderMessage());
        }
        finally
        {
            service?.Dispose();
            Log.Logger = originalLogger;
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public async Task EnqueueAsync_PersistsBatchAndSearchContextForDestinationTemplates()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;
        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var batchId = Guid.NewGuid();
        var searchId = Guid.NewGuid();
        var service = CreateDownloadService(options, CreateHangingSoulseekClient());

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[]
                {
                    new DownloadEnqueueRequest
                    {
                        Filename = @"Music\Jazz\track.flac",
                        Size = 1234,
                        BatchId = batchId,
                        BatchExternalId = "batch-42",
                        SearchId = searchId,
                        SearchText = "artist album",
                    },
                },
                CancellationToken.None);

            Assert.Single(enqueued);
            Assert.Empty(failed);

            await using var verificationContext = new TransfersDbContext(options);
            var transfer = await verificationContext.Transfers.SingleAsync(item => item.Id == enqueued[0].Id);
            var request = await verificationContext.DownloadRequests.SingleAsync(item => item.Id == transfer.RequestId);

            Assert.Equal(batchId, request.BatchId);
            Assert.Equal("batch-42", request.BatchExternalId);
            Assert.Equal(searchId, request.SearchId);
            Assert.Equal("artist album", request.SearchText);
            Assert.True(service.TryCancel(transfer.Id));
            await service.ShutdownAsync().WaitAsync(TimeSpan.FromSeconds(5));
        }
        finally
        {
            service.Dispose();
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public async Task EnqueueAsync_GlobalDownloadExclusionRejectsBeforeCreatingTransfer()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(client => client.Downloads)
            .Returns(Array.Empty<Soulseek.Transfer>());
        var configuredOptions = new slskd.Options
        {
            Filters = new slskd.Options.FiltersOptions
            {
                Download = new slskd.Options.FiltersOptions.DownloadFilterOptions
                {
                    Exclude = new[] { "instrumental" },
                },
            },
        };

        var service = CreateDownloadService(options, soulseekClient, configuredOptions);

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\Instrumental\track.flac", Size: 1234L) },
                CancellationToken.None);

            Assert.Empty(enqueued);
            Assert.Equal(new[] { @"Music\Instrumental\track.flac" }, failed);
            soulseekClient.Verify(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long?>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()), Times.Never);

            await using var context = new TransfersDbContext(options);
            Assert.Empty(context.Transfers);
        }
        finally
        {
            service.Dispose();
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public async Task EnqueueAsync_ExistingInProgressTransfer_IsRejectedWithoutStartingDownload()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
            context.Transfers.Add(new slskd.Transfers.Transfer
            {
                Id = Guid.NewGuid(),
                Username = "alice",
                Direction = TransferDirection.Download,
                Filename = @"Music\track.flac",
                Size = 1234,
                RequestedAt = DateTime.UtcNow.AddMinutes(-1),
                State = TransferStates.InProgress,
            });
            await context.SaveChangesAsync();
        }

        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(client => client.Downloads)
            .Returns(Array.Empty<Soulseek.Transfer>());

        var service = CreateDownloadService(options, soulseekClient);

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\track.flac", Size: 1234L) },
                CancellationToken.None);

            Assert.Empty(enqueued);
            Assert.Equal(new[] { @"Music\track.flac" }, failed);
            soulseekClient.Verify(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long?>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()), Times.Never);
        }
        finally
        {
            service.Dispose();
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public async Task EnqueueAsync_WideUnrelatedHistoryMaterializesOnlyRequestedFilename()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var materialization = new TransferMaterializationInterceptor();
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite(connection)
            .AddInterceptors(materialization)
            .Options;
        var requestedFilename = @"Music\requested.flac";
        var now = DateTime.UtcNow;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
            context.Transfers.AddRange(Enumerable.Range(0, 10_000).Select(index => new slskd.Transfers.Transfer
            {
                Id = Guid.NewGuid(),
                Username = "alice",
                Direction = TransferDirection.Download,
                Filename = $@"History\unrelated-{index:D5}.flac",
                Size = 1_234,
                RequestedAt = now.AddSeconds(-index - 1),
                EndedAt = now,
                State = TransferStates.Completed | TransferStates.Succeeded,
            }));
            context.Transfers.Add(new slskd.Transfers.Transfer
            {
                Id = Guid.NewGuid(),
                Username = "alice",
                Direction = TransferDirection.Download,
                Filename = requestedFilename,
                Size = 1_234,
                RequestedAt = now,
                State = TransferStates.InProgress,
            });
            await context.SaveChangesAsync();
        }

        materialization.TransferCount = 0;
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient.SetupGet(client => client.Downloads).Returns(Array.Empty<Soulseek.Transfer>());
        using var service = CreateDownloadService(options, soulseekClient);
        var allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();

        var (enqueued, failed) = await service.EnqueueAsync(
            "alice",
            new[] { (Filename: requestedFilename, Size: 1_234L) },
            CancellationToken.None);

        stopwatch.Stop();
        var allocatedBytes = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;
        Assert.Empty(enqueued);
        Assert.Equal(new[] { requestedFilename }, failed);
        Assert.True(
            materialization.TransferCount == 1,
            $"Materialized {materialization.TransferCount:N0} transfers in {stopwatch.ElapsedMilliseconds:N0} ms and allocated {allocatedBytes:N0} bytes.");
        Assert.True(
            allocatedBytes < 8_000_000,
            $"Allocated {allocatedBytes:N0} bytes in {stopwatch.ElapsedMilliseconds:N0} ms.");
    }

    [Fact]
    public async Task EnqueueAsync_CompletedSoulseekClientTransfer_DoesNotBlockRetry()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var staleClientTransfer = new Soulseek.Transfer(
            TransferDirection.Download,
            "alice",
            @"Music\track.flac",
            token: 1,
            state: TransferStates.Completed | TransferStates.TimedOut,
            size: 1234,
            startOffset: 0,
            bytesTransferred: 0);
        var downloadStarted = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(client => client.Downloads)
            .Returns(new[] { staleClientTransfer });
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long?>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()))
            .Returns(async (
                string username,
                string remoteFilename,
                Func<Task<Stream>> outputStreamFactory,
                long? size,
                long startOffset,
                int? token,
                TransferOptions transferOptions,
                CancellationToken? cancellationToken) =>
            {
                downloadStarted.TrySetResult();
                await Task.Delay(Timeout.Infinite, cancellationToken ?? CancellationToken.None);
                return null!;
            });

        var service = CreateDownloadService(options, soulseekClient);

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\track.flac", Size: 1234L) },
                CancellationToken.None);

            Assert.Single(enqueued);
            Assert.Empty(failed);

            await downloadStarted.Task.WaitAsync(TimeSpan.FromSeconds(5));
            soulseekClient.Verify(client => client.DownloadAsync(
                "alice",
                @"Music\track.flac",
                It.IsAny<Func<Task<Stream>>>(),
                1234,
                0,
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()), Times.Once);
            Assert.True(service.TryCancel(enqueued.Single().Id));
        }
        finally
        {
            service.Dispose();
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public async Task EnqueueAsync_CompletedExistingTransfer_IsSupersededByNewRecord()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;
        var existingId = Guid.NewGuid();
        var latestExistingId = Guid.NewGuid();
        var unrelatedId = Guid.NewGuid();
        var olderRequestId = Guid.NewGuid();
        var inheritedRequestId = Guid.NewGuid();

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
            context.Transfers.AddRange(
                new slskd.Transfers.Transfer
                {
                    Id = existingId,
                    RequestId = olderRequestId,
                    Username = "alice",
                    Direction = TransferDirection.Download,
                    Filename = @"Music\track.flac",
                    Size = 1234,
                    RequestedAt = DateTime.UtcNow.AddHours(-2),
                    EndedAt = DateTime.UtcNow.AddMinutes(-90),
                    State = TransferStates.Completed | TransferStates.Succeeded,
                },
                new slskd.Transfers.Transfer
                {
                    Id = latestExistingId,
                    RequestId = inheritedRequestId,
                    Username = "alice",
                    Direction = TransferDirection.Download,
                    Filename = @"Music\track.flac",
                    Size = 1234,
                    RequestedAt = DateTime.UtcNow.AddHours(-1),
                    EndedAt = DateTime.UtcNow.AddMinutes(-30),
                    State = TransferStates.Completed | TransferStates.Succeeded,
                },
                new slskd.Transfers.Transfer
                {
                    Id = unrelatedId,
                    Username = "alice",
                    Direction = TransferDirection.Download,
                    Filename = @"Music\unrelated.flac",
                    Size = 1234,
                    RequestedAt = DateTime.UtcNow.AddMinutes(-15),
                    EndedAt = DateTime.UtcNow.AddMinutes(-10),
                    State = TransferStates.Completed | TransferStates.Succeeded,
                });
            await context.SaveChangesAsync();
        }

        var soulseekClient = CreateHangingSoulseekClient();
        var service = CreateDownloadService(options, soulseekClient);

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\track.flac", Size: 1234L) },
                CancellationToken.None);

            Assert.Single(enqueued);
            Assert.Empty(failed);

            await using var context = new TransfersDbContext(options);
            var existing = await context.Transfers.SingleAsync(t => t.Id == existingId);
            var latestExisting = await context.Transfers.SingleAsync(t => t.Id == latestExistingId);
            var unrelated = await context.Transfers.SingleAsync(t => t.Id == unrelatedId);
            var replacement = await context.Transfers.SingleAsync(t => t.Id == enqueued.Single().Id);

            Assert.True(existing.Removed);
            Assert.True(latestExisting.Removed);
            Assert.False(unrelated.Removed);
            Assert.False(replacement.Removed);
            Assert.Equal(inheritedRequestId, replacement.RequestId);
            Assert.Equal(TransferStates.Queued | TransferStates.Locally, replacement.State);

            Assert.True(service.TryCancel(replacement.Id));
        }
        finally
        {
            service.Dispose();
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public async Task EnqueueAsync_BackgroundDownloadStartFailure_MarksTransferTerminalFailed()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(client => client.Downloads)
            .Returns(Array.Empty<Soulseek.Transfer>());
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long?>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()))
            .ThrowsAsync(new InvalidOperationException("synthetic enqueue failure"));

        var service = CreateDownloadService(options, soulseekClient);

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\track.flac", Size: 1234L) },
                CancellationToken.None);

            Assert.Single(enqueued);
            Assert.Empty(failed);

            var failedTransfer = await WaitForTransferAsync(
                () => service.Find(t => t.Id == enqueued.Single().Id && t.State.HasFlag(TransferStates.Completed)),
                TimeSpan.FromSeconds(5));

            Assert.True(failedTransfer.State.HasFlag(TransferStates.Errored));
            Assert.Contains("synthetic enqueue failure", failedTransfer.Exception, StringComparison.Ordinal);
            Assert.False(service.TryCancel(failedTransfer.Id));
        }
        finally
        {
            await ShutdownAndDeleteDatabaseAsync(service, databasePath);
        }
    }

    [Fact]
    public async Task EnqueueAsync_IncompleteSymlinkEscape_DoesNotCreateFileOutsideConfiguredRoot()
    {
        if (OperatingSystem.IsWindows())
        {
            return;
        }

        var workDirectory = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"slskdn-download-path-{Guid.NewGuid():N}");
        var incompleteDirectory = System.IO.Path.Combine(workDirectory, "incomplete");
        var outsideDirectory = System.IO.Path.Combine(workDirectory, "outside");
        var databasePath = System.IO.Path.Combine(workDirectory, "transfers.db");
        var linkDirectory = System.IO.Path.Combine(incompleteDirectory, "Music");
        System.IO.Directory.CreateDirectory(incompleteDirectory);
        System.IO.Directory.CreateDirectory(outsideDirectory);
        System.IO.Directory.CreateSymbolicLink(linkDirectory, outsideDirectory);

        var databaseOptions = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;
        await using (var context = new TransfersDbContext(databaseOptions))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var configuredOptions = new slskd.Options
        {
            Directories = new slskd.Options.DirectoriesOptions
            {
                Downloads = System.IO.Path.Combine(workDirectory, "downloads"),
                Incomplete = incompleteDirectory,
            },
        };
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient.SetupGet(client => client.Downloads).Returns(Array.Empty<Soulseek.Transfer>());
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long?>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()))
            .Returns(async (
                string username,
                string filename,
                Func<Task<Stream>> outputStreamFactory,
                long? size,
                long startOffset,
                int? token,
                TransferOptions transferOptions,
                CancellationToken? cancellationToken) =>
            {
                using var output = await outputStreamFactory();
                output.WriteByte(1);
                throw new TransferRejectedException("Synthetic transfer failure after opening output.");
            });

        using var service = CreateDownloadService(databaseOptions, soulseekClient, configuredOptions);

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\track.flac", Size: 1234L) },
                CancellationToken.None);

            Assert.Single(enqueued);
            Assert.Empty(failed);
            await WaitForTransferAsync(
                () => service.Find(t => t.Id == enqueued.Single().Id && t.State.HasFlag(TransferStates.Completed)),
                TimeSpan.FromSeconds(5));

            Assert.False(System.IO.File.Exists(System.IO.Path.Combine(outsideDirectory, "track.flac")));
        }
        finally
        {
            try
            {
                await service.ShutdownAsync().WaitAsync(TimeSpan.FromSeconds(5));
            }
            finally
            {
                service.Dispose();
                await using (var context = new TransfersDbContext(databaseOptions))
                {
                    await context.Database.CloseConnectionAsync();
                }

                DeleteDatabase(databasePath);
                DeleteDirectory(workDirectory, databasePath);
            }
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task EnqueueAsync_ContentSafetyQuarantinesExecutableAndMismatchedFiles(bool verifyMagicBytes)
    {
        var workDirectory = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"slskdn-download-content-safety-{Guid.NewGuid():N}");
        var downloadsDirectory = System.IO.Path.Combine(workDirectory, "downloads");
        var incompleteDirectory = System.IO.Path.Combine(workDirectory, "incomplete");
        var databasePath = System.IO.Path.Combine(workDirectory, "transfers.db");
        System.IO.Directory.CreateDirectory(workDirectory);

        var databaseOptions = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath};Pooling=False")
            .Options;
        await using (var context = new TransfersDbContext(databaseOptions))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var configuredOptions = new slskd.Options
        {
            Directories = new slskd.Options.DirectoriesOptions
            {
                Downloads = downloadsDirectory,
                Incomplete = incompleteDirectory,
            },
            Security = new slskd.Common.Security.SecurityOptions
            {
                Enabled = true,
                ContentSafety = new slskd.Common.Security.ContentSafetyOptions
                {
                    Enabled = true,
                    VerifyMagicBytes = verifyMagicBytes,
                    QuarantineSuspicious = true,
                    BlockExecutables = true,
                },
            },
        };
        var executableHeader = new byte[] { 0x4D, 0x5A, 0x90, 0x00, 0x03, 0x00 };
        var mismatchedHeader = new byte[] { 0x25, 0x50, 0x44, 0x46, 0x2D, 0x31 };
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient.SetupGet(client => client.Downloads).Returns(Array.Empty<Soulseek.Transfer>());
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long?>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()))
            .Returns(async (
                string username,
                string remoteFilename,
                Func<Task<Stream>> outputStreamFactory,
                long? size,
                long startOffset,
                int? token,
                TransferOptions transferOptions,
                CancellationToken? cancellationToken) =>
            {
                var payload = remoteFilename.EndsWith(".flac", StringComparison.OrdinalIgnoreCase)
                    ? mismatchedHeader
                    : executableHeader;
                await using (var output = await outputStreamFactory())
                {
                    await output.WriteAsync(payload, cancellationToken ?? CancellationToken.None);
                }

                var completed = new Soulseek.Transfer(
                    TransferDirection.Download,
                    username,
                    remoteFilename,
                    token: token ?? 1,
                    state: TransferStates.Completed | TransferStates.Succeeded,
                    size: payload.Length,
                    startOffset: 0,
                    bytesTransferred: payload.Length);
                transferOptions.StateChanged?.Invoke((TransferStates.InProgress, completed));
                return completed;
            });

        var service = CreateDownloadService(databaseOptions, soulseekClient, configuredOptions);

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[]
                {
                    (Filename: @"Music\track.mp3", Size: (long)executableHeader.Length),
                    (Filename: @"Music\mismatched.flac", Size: (long)mismatchedHeader.Length),
                },
                CancellationToken.None);

            Assert.Equal(2, enqueued.Count);
            Assert.Empty(failed);

            var expectedRequestStates = enqueued.ToDictionary(
                item => item.RequestId!.Value,
                item => item.Filename.EndsWith(".mp3", StringComparison.OrdinalIgnoreCase) || verifyMagicBytes
                    ? DownloadRequestState.Failed
                    : DownloadRequestState.Completed);

            await WaitUntilAsync(
                () =>
                {
                    if (!enqueued.All(item => service.Find(t => t.Id == item.Id)?.State.HasFlag(TransferStates.Completed) == true))
                    {
                        return false;
                    }

                    using var requestContext = new TransfersDbContext(databaseOptions);
                    var requestStates = requestContext.DownloadRequests
                        .Where(request => expectedRequestStates.Keys.Contains(request.Id))
                        .ToDictionary(request => request.Id, request => request.State);

                    return expectedRequestStates.Count == requestStates.Count &&
                        expectedRequestStates.All(expected => requestStates.TryGetValue(expected.Key, out var state) && state == expected.Value);
                },
                TimeSpan.FromSeconds(30));

            var rejectedTransfers = enqueued.Select(item => service.Find(t => t.Id == item.Id)).ToArray();
            var executableTransfer = rejectedTransfers.Single(t => t!.Filename.EndsWith(".mp3", StringComparison.OrdinalIgnoreCase))!;
            var mismatchedTransfer = rejectedTransfers.Single(t => t!.Filename.EndsWith(".flac", StringComparison.OrdinalIgnoreCase))!;
            Assert.True(executableTransfer.State.HasFlag(TransferStates.Errored));
            Assert.Contains("Content safety rejected", executableTransfer.Exception, StringComparison.Ordinal);
            Assert.NotNull(executableTransfer.LocalFilename);
            Assert.StartsWith(System.IO.Path.Combine(downloadsDirectory, ".quarantine"), executableTransfer.LocalFilename, StringComparison.Ordinal);
            Assert.True(System.IO.File.Exists(executableTransfer.LocalFilename));

            if (verifyMagicBytes)
            {
                Assert.True(mismatchedTransfer.State.HasFlag(TransferStates.Errored));
                Assert.Contains("Content safety rejected", mismatchedTransfer.Exception, StringComparison.Ordinal);
                Assert.NotNull(mismatchedTransfer.LocalFilename);
                Assert.StartsWith(System.IO.Path.Combine(downloadsDirectory, ".quarantine"), mismatchedTransfer.LocalFilename, StringComparison.Ordinal);
                Assert.True(System.IO.File.Exists(mismatchedTransfer.LocalFilename));
            }
            else
            {
                Assert.True(mismatchedTransfer.State.HasFlag(TransferStates.Succeeded));
                Assert.Equal(System.IO.Path.Combine(downloadsDirectory, "Music", "mismatched.flac"), mismatchedTransfer.LocalFilename);
                Assert.True(System.IO.File.Exists(mismatchedTransfer.LocalFilename));
            }

            Assert.False(System.IO.File.Exists(System.IO.Path.Combine(downloadsDirectory, "Music", "track.mp3")));
            Assert.Equal(verifyMagicBytes, System.IO.File.Exists(System.IO.Path.Combine(downloadsDirectory, ".quarantine", "mismatched.flac")));

            await using (var requestContext = new TransfersDbContext(databaseOptions))
            {
                var requestIds = expectedRequestStates.Keys.ToArray();
                var requests = await requestContext.DownloadRequests.Where(request => requestIds.Contains(request.Id)).ToListAsync();
                Assert.Equal(2, requests.Count);
                Assert.Equal(DownloadRequestState.Failed, requests.Single(r => r.Id == executableTransfer.RequestId).State);
                Assert.Equal(
                    verifyMagicBytes ? DownloadRequestState.Failed : DownloadRequestState.Completed,
                    requests.Single(r => r.Id == mismatchedTransfer.RequestId).State);
            }
            Assert.False(service.TryCancel(executableTransfer.Id));
            Assert.False(service.TryCancel(mismatchedTransfer.Id));
        }
        finally
        {
            try
            {
                await service.ShutdownAsync().WaitAsync(TimeSpan.FromSeconds(5));
            }
            finally
            {
                service.Dispose();
                await using (var context = new TransfersDbContext(databaseOptions))
                {
                    await context.Database.CloseConnectionAsync();
                }

                DeleteDatabase(databasePath);
                System.IO.Directory.Delete(workDirectory, recursive: true);
            }
        }
    }

    [Fact]
    public async Task TryCancel_WhenCompletedTransferRetainsCancellationSource_ReturnsFalseWithoutCancelling()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;
        var transfer = new slskd.Transfers.Transfer
        {
            Id = Guid.NewGuid(),
            Username = "alice",
            Direction = TransferDirection.Download,
            Filename = @"Music\completed.flac",
            Size = 1234,
            RequestedAt = DateTime.UtcNow.AddMinutes(-1),
            EndedAt = DateTime.UtcNow,
            State = TransferStates.Completed | TransferStates.Succeeded,
        };

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
            context.Transfers.Add(transfer);
            await context.SaveChangesAsync();
        }

        var service = CreateDownloadService(options, new Mock<ISoulseekClient>());
        using var cancellationTokenSource = new CancellationTokenSource();
        var token = cancellationTokenSource.Token;
        var cancellationTokens = (ConcurrentDictionary<Guid, CancellationTokenSource>)typeof(DownloadService)
            .GetProperty("CancellationTokens", BindingFlags.Instance | BindingFlags.NonPublic)!
            .GetValue(service)!;
        cancellationTokens[transfer.Id] = cancellationTokenSource;

        try
        {
            Assert.False(service.TryCancel(transfer.Id));
            Assert.False(token.IsCancellationRequested);
            Assert.False(cancellationTokens.ContainsKey(transfer.Id));
        }
        finally
        {
            service.Dispose();
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public async Task Remove_CompletedDownloadWithSymlinkEscape_LeavesOutsideFileIntact()
    {
        if (OperatingSystem.IsWindows())
        {
            return;
        }

        var workDirectory = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"slskdn-remove-path-{Guid.NewGuid():N}");
        var downloadsDirectory = System.IO.Path.Combine(workDirectory, "downloads");
        var outsideDirectory = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"slskdn-remove-target-{Guid.NewGuid():N}");
        var databasePath = System.IO.Path.Combine(workDirectory, "transfers.db");
        var linkDirectory = System.IO.Path.Combine(downloadsDirectory, "Artist");
        var outsideFilename = System.IO.Path.Combine(outsideDirectory, "track.flac");
        System.IO.Directory.CreateDirectory(downloadsDirectory);
        System.IO.Directory.CreateDirectory(outsideDirectory);
        System.IO.File.WriteAllText(outsideFilename, "keep this file");
        System.IO.Directory.CreateSymbolicLink(linkDirectory, outsideDirectory);

        var transferId = Guid.NewGuid();
        var databaseOptions = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;
        await using (var context = new TransfersDbContext(databaseOptions))
        {
            await context.Database.EnsureCreatedAsync();
            context.Transfers.Add(new slskd.Transfers.Transfer
            {
                Id = transferId,
                Username = "alice",
                Direction = TransferDirection.Download,
                Filename = @"Music\Artist\track.flac",
                LocalFilename = System.IO.Path.Combine(linkDirectory, "track.flac"),
                Size = 1234,
                RequestedAt = DateTime.UtcNow.AddMinutes(-1),
                EndedAt = DateTime.UtcNow,
                State = TransferStates.Completed | TransferStates.Succeeded,
            });
            await context.SaveChangesAsync();
        }

        var configuredOptions = new slskd.Options
        {
            Directories = new slskd.Options.DirectoriesOptions
            {
                Downloads = downloadsDirectory,
                Incomplete = System.IO.Path.Combine(workDirectory, "incomplete"),
            },
        };
        using var service = CreateDownloadService(databaseOptions, new Mock<ISoulseekClient>(), configuredOptions);

        try
        {
            service.Remove(transferId, deleteFile: true);

            Assert.True(System.IO.File.Exists(outsideFilename));
        }
        finally
        {
            service.Dispose();
            System.IO.Directory.Delete(linkDirectory);
            System.IO.Directory.Delete(downloadsDirectory);
            System.IO.Directory.Delete(outsideDirectory, recursive: true);
            System.IO.Directory.Delete(workDirectory, recursive: true);
        }
    }

    [Fact]
    public async Task TryFail_AggregateTimeout_MarksTransferTimedOut()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;
        var transferId = Guid.NewGuid();

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
            context.Transfers.Add(new slskd.Transfers.Transfer
            {
                Id = transferId,
                Username = "alice",
                Direction = TransferDirection.Download,
                Filename = @"Music\slow.flac",
                Size = 1234,
                RequestedAt = DateTime.UtcNow,
                State = TransferStates.InProgress,
            });
            await context.SaveChangesAsync();
        }

        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(client => client.Downloads)
            .Returns(Array.Empty<Soulseek.Transfer>());

        var service = CreateDownloadService(options, soulseekClient);

        try
        {
            var exception = new AggregateException(new TimeoutException("The wait timed out after 15000 milliseconds"));

            Assert.True(service.TryFail(transferId, exception));

            await using var context = new TransfersDbContext(options);
            var failedTransfer = await context.Transfers.SingleAsync(t => t.Id == transferId);
            Assert.True(failedTransfer.State.HasFlag(TransferStates.Completed));
            Assert.True(failedTransfer.State.HasFlag(TransferStates.TimedOut));
            Assert.False(failedTransfer.State.HasFlag(TransferStates.Errored));
        }
        finally
        {
            service.Dispose();
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public async Task TryFail_TransferExceptionTimeoutMessage_MarksTransferTimedOut()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;
        var transferId = Guid.NewGuid();

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
            context.Transfers.Add(new slskd.Transfers.Transfer
            {
                Id = transferId,
                Username = "alice",
                Direction = TransferDirection.Download,
                Filename = @"Music\slow.flac",
                Size = 1234,
                RequestedAt = DateTime.UtcNow,
                State = TransferStates.InProgress,
            });
            await context.SaveChangesAsync();
        }

        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(client => client.Downloads)
            .Returns(Array.Empty<Soulseek.Transfer>());

        var service = CreateDownloadService(options, soulseekClient);

        try
        {
            var exception = new TransferException("The wait timed out after 15000 milliseconds");

            Assert.True(service.TryFail(transferId, exception));

            await using var context = new TransfersDbContext(options);
            var failedTransfer = await context.Transfers.SingleAsync(t => t.Id == transferId);
            Assert.True(failedTransfer.State.HasFlag(TransferStates.Completed));
            Assert.True(failedTransfer.State.HasFlag(TransferStates.TimedOut));
            Assert.False(failedTransfer.State.HasFlag(TransferStates.Errored));
        }
        finally
        {
            service.Dispose();
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public async Task EnqueueAsync_BackgroundAggregateTimeout_MarksTransferTimedOut()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(client => client.Downloads)
            .Returns(Array.Empty<Soulseek.Transfer>());
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long?>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()))
            .ThrowsAsync(new AggregateException(new TimeoutException("The wait timed out after 15000 milliseconds")));

        var service = CreateDownloadService(options, soulseekClient);

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\slow.flac", Size: 1234L) },
                CancellationToken.None);

            Assert.Single(enqueued);
            Assert.Empty(failed);

            var failedTransfer = await WaitForTransferAsync(
                () => service.Find(t => t.Id == enqueued.Single().Id && t.State.HasFlag(TransferStates.Completed)),
                TimeSpan.FromSeconds(5));

            Assert.True(failedTransfer.State.HasFlag(TransferStates.TimedOut));
            Assert.False(failedTransfer.State.HasFlag(TransferStates.Errored));
        }
        finally
        {
            service.Dispose();
            DeleteDatabase(databasePath);
        }
    }

    [Theory]
    [InlineData("reported")]
    [InlineData("size")]
    [InlineData("rejected")]
    [InlineData("connection-reset")]
    [InlineData("remote-closed")]
    [InlineData("message-connection")]
    [InlineData("transfer-connection")]
    public async Task EnqueueAsync_BackgroundExpectedRemoteFailure_MarksTransferTerminalFailed(string failureKind)
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath};Pooling=False")
            .Options;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(client => client.Downloads)
            .Returns(Array.Empty<Soulseek.Transfer>());
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long?>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()))
            .ThrowsAsync(new AggregateException(CreateExpectedRemoteFailure(failureKind)));

        var service = CreateDownloadService(options, soulseekClient);

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\remote-failed.flac", Size: 1234L) },
                CancellationToken.None);

            Assert.Single(enqueued);
            Assert.Empty(failed);

            var failedTransfer = await WaitForTransferAsync(
                () => service.Find(t => t.Id == enqueued.Single().Id && t.State.HasFlag(TransferStates.Completed)),
                TimeSpan.FromSeconds(5));

            Assert.True(failedTransfer.State.HasFlag(TransferStates.Errored));
            Assert.False(failedTransfer.State.HasFlag(TransferStates.TimedOut));
        }
        finally
        {
            await ShutdownAndDeleteDatabaseAsync(service, databasePath);
        }
    }

    [Fact]
    public async Task EnqueueAsync_BackgroundExpectedRemoteFailure_DoesNotLeakCleanupAggregateTaskFault()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(client => client.Downloads)
            .Returns(Array.Empty<Soulseek.Transfer>());
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long?>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()))
            .ThrowsAsync(new AggregateException(CreateExpectedRemoteFailure("rejected")));

        var service = CreateDownloadService(options, soulseekClient);
        var unobservedExceptions = new List<Exception>();

        void OnUnobservedTaskException(object? sender, UnobservedTaskExceptionEventArgs args)
        {
            unobservedExceptions.Add(args.Exception);
            args.SetObserved();
        }

        TaskScheduler.UnobservedTaskException += OnUnobservedTaskException;

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\remote-failed.flac", Size: 1234L) },
                CancellationToken.None);

            Assert.Single(enqueued);
            Assert.Empty(failed);

            _ = await WaitForTransferAsync(
                () => service.Find(t => t.Id == enqueued.Single().Id && t.State.HasFlag(TransferStates.Completed)),
                TimeSpan.FromSeconds(5));

            service.Dispose();
            service = null!;

            await ForceTaskFinalizersAsync();

            Assert.DoesNotContain(
                unobservedExceptions,
                exception => exception.ToString().Contains("File not shared", StringComparison.Ordinal));
        }
        finally
        {
            TaskScheduler.UnobservedTaskException -= OnUnobservedTaskException;
            service?.Dispose();
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public void CreateRetryPlan_RespectsGlobalPerPeerAndCooldownBudgets()
    {
        var now = DateTime.UtcNow;
        var opts = new slskd.Options.GlobalOptions.GlobalDownloadOptions.AutoRetryOptions();
        var transfers = new[]
        {
            CreateFailedDownload("alice", "a-1.flac", now.AddMinutes(-40)),
            CreateFailedDownload("alice", "a-2.flac", now.AddMinutes(-39)),
            CreateFailedDownload("bob", "b-1.flac", now.AddMinutes(-38)),
            CreateFailedDownload("carol", "c-1.flac", now.AddMinutes(-37)),
            CreateFailedDownload("dave", "d-1.flac", now.AddMinutes(-36)),
            CreateFailedDownload("erin", "e-1.flac", now.AddMinutes(-35)),
            CreateFailedDownload("frank", "f-1.flac", now.AddMinutes(-34)),
            CreateFailedDownload("grace", "g-1.flac", now.AddMinutes(-33)),
            CreateFailedDownload("heidi", "h-1.flac", now.AddMinutes(-32)),
            CreateFailedDownload("ivan", "i-1.flac", now.AddMinutes(-31)),
            CreateFailedDownload("judy", "j-1.flac", now.AddMinutes(-30)),
            CreateFailedDownload("mallory", "m-1.flac", now.AddMinutes(-29)),
        };

        var plan = DownloadAutoRetryService.CreateRetryPlan(
            transfers,
            new HashSet<Guid>(),
            new System.Collections.Concurrent.ConcurrentDictionary<string, int>(),
            new System.Collections.Concurrent.ConcurrentDictionary<string, DateTime>(
                new[] { new KeyValuePair<string, DateTime>("carol", now.AddMinutes(5)) },
                StringComparer.OrdinalIgnoreCase),
            opts,
            now);

        Assert.Equal(10, plan.Count);
        Assert.DoesNotContain(plan, t => t.Username == "carol");
        Assert.Single(plan, t => t.Username == "alice");
        Assert.All(
            plan.GroupBy(t => t.Username, StringComparer.OrdinalIgnoreCase),
            group => Assert.True(group.Count() <= opts.MaxFilesPerPeerPerCycle));
    }

    [Fact]
    public void CreateRetryPlan_SkipsAlreadyRetriedAndFiniteMaxAttemptFiles()
    {
        var now = DateTime.UtcNow;
        var alreadyRetried = CreateFailedDownload("alice", "old.flac", now.AddMinutes(-40));
        var maxed = CreateFailedDownload("bob", "maxed.flac", now.AddMinutes(-39));
        var eligible = CreateFailedDownload("carol", "ok.flac", now.AddMinutes(-38));
        var retryCounts = new System.Collections.Concurrent.ConcurrentDictionary<string, int>();
        var opts = new slskd.Options.GlobalOptions.GlobalDownloadOptions.AutoRetryOptions { MaxAttempts = 5 };
        retryCounts[$"{maxed.Username}:{maxed.Filename}"] = opts.MaxAttempts;

        var plan = DownloadAutoRetryService.CreateRetryPlan(
            new[] { alreadyRetried, maxed, eligible },
            new HashSet<Guid> { alreadyRetried.Id },
            retryCounts,
            new System.Collections.Concurrent.ConcurrentDictionary<string, DateTime>(),
            opts,
            now);

        Assert.Equal(new[] { eligible.Id }, plan.Select(t => t.Id));
    }

    [Fact]
    public void CreateRetryPlan_DefaultMaxAttemptsStopsAfterBoundedRetries()
    {
        var now = DateTime.UtcNow;
        var retriedManyTimes = CreateFailedDownload("alice", "forever.flac", now.AddMinutes(-40));
        var retryCounts = new System.Collections.Concurrent.ConcurrentDictionary<string, int>();
        retryCounts[$"{retriedManyTimes.Username}:{retriedManyTimes.Filename}"] = 500;

        var plan = DownloadAutoRetryService.CreateRetryPlan(
            new[] { retriedManyTimes },
            new HashSet<Guid>(),
            retryCounts,
            new System.Collections.Concurrent.ConcurrentDictionary<string, DateTime>(),
            new slskd.Options.GlobalOptions.GlobalDownloadOptions.AutoRetryOptions(),
            now);

        Assert.Empty(plan);
    }

    [Fact]
    public void CreateRetryPlan_SkipsNonAudioSidecars()
    {
        var now = DateTime.UtcNow;
        var cover = CreateFailedDownload("alice", @"Album\cover.jpg", now.AddMinutes(-40), size: 1234);
        var log = CreateFailedDownload("bob", @"Album\album.log", now.AddMinutes(-39), size: 2345);
        var track = CreateFailedDownload("carol", @"Album\01 Track.flac", now.AddMinutes(-38), size: 3456);

        var plan = DownloadAutoRetryService.CreateRetryPlan(
            new[] { cover, log, track },
            new HashSet<Guid>(),
            new System.Collections.Concurrent.ConcurrentDictionary<string, int>(),
            new System.Collections.Concurrent.ConcurrentDictionary<string, DateTime>(),
            new slskd.Options.GlobalOptions.GlobalDownloadOptions.AutoRetryOptions(),
            now);

        Assert.Equal(new[] { track.Id }, plan.Select(t => t.Id));
    }

    [Fact]
    public async Task CreateRetryPlanAsync_StopsAfterDefaultPlanIsFinal()
    {
        var now = DateTime.UtcNow;
        var enumerated = 0;
        var transfers = Enumerable.Range(0, 50)
            .Select(index => CreateFailedDownload($"peer-{index}", $"track-{index}.flac", now.AddMinutes(index - 100)))
            .ToList();

        var plan = await DownloadAutoRetryService.CreateRetryPlanAsync(
            ToAsyncSequence(transfers, () => enumerated++),
            new HashSet<Guid>(),
            new System.Collections.Concurrent.ConcurrentDictionary<string, int>(),
            new System.Collections.Concurrent.ConcurrentDictionary<string, DateTime>(),
            new slskd.Options.GlobalOptions.GlobalDownloadOptions.AutoRetryOptions(),
            now,
            CancellationToken.None);

        Assert.Equal(10, plan.Count);
        Assert.Equal(10, enumerated);
        Assert.Equal(transfers.Take(10).Select(transfer => transfer.Id), plan.Select(transfer => transfer.Id));
    }

    [Fact]
    public async Task CreateRetryPlanAsync_WaitsForEarlierUnderfilledPeerGroups()
    {
        var now = DateTime.UtcNow;
        var aliceFirst = CreateFailedDownload("alice", "alice-1.flac", now.AddMinutes(-50));
        var bob = CreateFailedDownload("bob", "bob.flac", now.AddMinutes(-49));
        var carol = CreateFailedDownload("carol", "carol.flac", now.AddMinutes(-48));
        var aliceSecond = CreateFailedDownload("alice", "alice-2.flac", now.AddMinutes(-47));
        var dave = CreateFailedDownload("dave", "dave.flac", now.AddMinutes(-46));
        var ordered = new[] { aliceFirst, bob, carol, aliceSecond, dave };
        var enumerated = 0;
        var opts = new slskd.Options.GlobalOptions.GlobalDownloadOptions.AutoRetryOptions
        {
            MaxFilesPerCycle = 3,
            MaxFilesPerPeerPerCycle = 2,
        };

        var plan = await DownloadAutoRetryService.CreateRetryPlanAsync(
            ToAsyncSequence(ordered, () => enumerated++),
            new HashSet<Guid>(),
            new System.Collections.Concurrent.ConcurrentDictionary<string, int>(),
            new System.Collections.Concurrent.ConcurrentDictionary<string, DateTime>(),
            opts,
            now,
            CancellationToken.None);

        Assert.Equal(new[] { aliceFirst.Id, aliceSecond.Id, bob.Id }, plan.Select(transfer => transfer.Id));
        Assert.Equal(4, enumerated);
    }

    [Fact]
    public async Task StreamAutoRetryCandidatesAsync_FiltersAndOrdersInDatabase()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;
        var now = DateTime.UtcNow;
        var oldest = CreateFailedDownload("alice", "oldest.flac", now.AddHours(-3));
        var newer = CreateFailedDownload("bob", "newer.flac", now.AddHours(-2));
        var removed = CreateFailedDownload("carol", "removed.flac", now.AddHours(-4));
        removed.Removed = true;
        var succeeded = CreateFailedDownload("dave", "succeeded.flac", now.AddHours(-4));
        succeeded.State = TransferStates.Completed | TransferStates.Succeeded;
        var cancelled = CreateFailedDownload("erin", "cancelled.flac", now.AddHours(-4));
        cancelled.State = TransferStates.Completed | TransferStates.Cancelled;
        var rejected = CreateFailedDownload("frank", "rejected.flac", now.AddHours(-4));
        rejected.State = TransferStates.Completed | TransferStates.Rejected;
        var tooRecent = CreateFailedDownload("grace", "recent.flac", now.AddMinutes(-5));
        var upload = CreateFailedDownload("heidi", "upload.flac", now.AddHours(-4));
        upload = new slskd.Transfers.Transfer
        {
            Id = upload.Id,
            Username = upload.Username,
            Direction = TransferDirection.Upload,
            Filename = upload.Filename,
            Size = upload.Size,
            RequestedAt = upload.RequestedAt,
            EndedAt = upload.EndedAt,
            State = upload.State,
        };

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
            context.Transfers.AddRange(oldest, newer, removed, succeeded, cancelled, rejected, tooRecent, upload);
            await context.SaveChangesAsync();
        }

        try
        {
            using var service = CreateDownloadService(options, new Mock<ISoulseekClient>());
            var candidates = new List<slskd.Transfers.Transfer>();
            await foreach (var candidate in service.StreamAutoRetryCandidatesAsync(now.AddHours(-1)))
            {
                candidates.Add(candidate);
            }

            Assert.Equal(new[] { oldest.Id, newer.Id }, candidates.Select(candidate => candidate.Id));
            Assert.All(candidates, candidate => Assert.Null(candidate.RequestId));
        }
        finally
        {
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public async Task StreamAutoRetryCandidatesAsync_ExcludesRequestsAtPersistedRetryLimit()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;
        var now = DateTime.UtcNow;
        var requestId = Guid.NewGuid();
        var first = CreateFailedDownload("alice", "track.flac", now.AddHours(-3));
        first.RequestId = requestId;
        first.Removed = true;
        var second = CreateFailedDownload("alice", "track.flac", now.AddHours(-2));
        second.RequestId = requestId;
        second.Removed = true;
        var current = CreateFailedDownload("alice", "track.flac", now.AddHours(-1));
        current.RequestId = requestId;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
            context.Transfers.AddRange(first, second, current);
            await context.SaveChangesAsync();
        }

        var configuredOptions = new slskd.Options
        {
            Global = new slskd.Options.GlobalOptions
            {
                Download = new slskd.Options.GlobalOptions.GlobalDownloadOptions
                {
                    AutoRetry = new slskd.Options.GlobalOptions.GlobalDownloadOptions.AutoRetryOptions
                    {
                        MaxAttempts = 2,
                    },
                },
            },
        };

        try
        {
            using var service = CreateDownloadService(options, new Mock<ISoulseekClient>(), configuredOptions);
            var candidates = new List<slskd.Transfers.Transfer>();
            await foreach (var candidate in service.StreamAutoRetryCandidatesAsync(now.AddMinutes(-30)))
            {
                candidates.Add(candidate);
            }

            Assert.Empty(candidates);
        }
        finally
        {
            DeleteDatabase(databasePath);
        }
    }

    [Fact]
    public async Task ResolveRetryTargetAsync_PrefersCooledDownHashDbAlternate()
    {
        var now = DateTime.UtcNow;
        var failed = CreateFailedDownload("alice", @"Album\track.flac", now.AddMinutes(-40), size: 1234);
        var hashDb = new Mock<IHashDbService>();
        hashDb.Setup(x => x.GetFlacEntriesBySizeAsync(1234, 50, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new[]
            {
                new FlacInventoryEntry { PeerId = "alice", Path = @"Album\track.flac", Size = 1234 },
                new FlacInventoryEntry { PeerId = "mallory", Path = @"Other\wrong-track.flac", Size = 1234 },
                new FlacInventoryEntry { PeerId = "bob", Path = @"Other\track.flac", Size = 1234 },
            });

        var service = CreateAutoRetryService(hashDb: hashDb.Object);

        var target = await service.ResolveRetryTargetAsync(
            failed,
            new slskd.Options.GlobalOptions.GlobalDownloadOptions.AutoRetryOptions(),
            now,
            allowNetworkSearch: true,
            CancellationToken.None);

        Assert.Equal("bob", target.Username);
        Assert.Equal(@"Other\track.flac", target.Filename);
        Assert.Equal("hashdb", target.SourceKind);
        Assert.False(target.UsedNetworkSearch);
    }

    [Fact]
    public async Task ResolveRetryTargetAsync_IgnoresHashDbAlternatesWithDifferentFilename()
    {
        var now = DateTime.UtcNow;
        var failed = CreateFailedDownload("alice", @"Album\track.flac", now.AddMinutes(-40), size: 1234);
        var hashDb = new Mock<IHashDbService>();
        hashDb.Setup(x => x.GetFlacEntriesBySizeAsync(1234, 50, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new[]
            {
                new FlacInventoryEntry { PeerId = "mallory", Path = @"Other\wrong-track.flac", Size = 1234 },
            });

        var service = CreateAutoRetryService(hashDb: hashDb.Object);

        var target = await service.ResolveRetryTargetAsync(
            failed,
            new slskd.Options.GlobalOptions.GlobalDownloadOptions.AutoRetryOptions(),
            now,
            allowNetworkSearch: false,
            CancellationToken.None);

        Assert.Equal("alice", target.Username);
        Assert.Equal(@"Album\track.flac", target.Filename);
        Assert.Equal("original", target.SourceKind);
    }

    [Fact]
    public async Task ResolveRetryTargetAsync_UsesBoundedSearchWhenLocalCandidateUnavailable()
    {
        var now = DateTime.UtcNow;
        var failed = CreateFailedDownload("alice", @"Album\track.flac", now.AddMinutes(-40), size: 1234);
        var hashDb = new Mock<IHashDbService>();
        hashDb.Setup(x => x.GetFlacEntriesBySizeAsync(1234, 50, It.IsAny<CancellationToken>()))
            .ReturnsAsync(Array.Empty<FlacInventoryEntry>());

        var autoReplace = new Mock<IAutoReplaceService>();
        autoReplace.Setup(x => x.FindAlternativesAsync(
                It.Is<FindAlternativeRequest>(r => r.Username == "alice" && r.Filename == failed.Filename && r.Size == failed.Size),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(new List<AlternativeCandidate>
            {
                new() { Username = "carol", Filename = @"Other\track.flac", Size = 1234 },
            });

        var service = CreateAutoRetryService(hashDb: hashDb.Object, autoReplace: autoReplace.Object);

        var target = await service.ResolveRetryTargetAsync(
            failed,
            new slskd.Options.GlobalOptions.GlobalDownloadOptions.AutoRetryOptions(),
            now,
            allowNetworkSearch: true,
            CancellationToken.None);

        Assert.Equal("carol", target.Username);
        Assert.Equal("search", target.SourceKind);
        Assert.True(target.UsedNetworkSearch);
    }

    [Fact]
    public async Task ResolveRetryTargetAsync_FallsBackToOriginalWhenNetworkSearchBudgetUnavailable()
    {
        var now = DateTime.UtcNow;
        var failed = CreateFailedDownload("alice", @"Album\track.flac", now.AddMinutes(-40), size: 1234);
        var autoReplace = new Mock<IAutoReplaceService>(MockBehavior.Strict);
        var service = CreateAutoRetryService(autoReplace: autoReplace.Object);

        var target = await service.ResolveRetryTargetAsync(
            failed,
            new slskd.Options.GlobalOptions.GlobalDownloadOptions.AutoRetryOptions(),
            now,
            allowNetworkSearch: false,
            CancellationToken.None);

        Assert.Equal("alice", target.Username);
        Assert.Equal(failed.Filename, target.Filename);
        Assert.Equal("original", target.SourceKind);
        Assert.False(target.UsedNetworkSearch);
    }

    [Fact]
    public async Task ResolveRetryTargetAsync_ConsumesNetworkSearchBudgetWhenNoAlternativeFound()
    {
        var now = DateTime.UtcNow;
        var failed = CreateFailedDownload("alice", @"Album\track.flac", now.AddMinutes(-40), size: 1234);
        var autoReplace = new Mock<IAutoReplaceService>();
        autoReplace.Setup(x => x.FindAlternativesAsync(It.IsAny<FindAlternativeRequest>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new List<AlternativeCandidate>());

        var service = CreateAutoRetryService(autoReplace: autoReplace.Object);

        var target = await service.ResolveRetryTargetAsync(
            failed,
            new slskd.Options.GlobalOptions.GlobalDownloadOptions.AutoRetryOptions(),
            now,
            allowNetworkSearch: true,
            CancellationToken.None);

        Assert.Equal("alice", target.Username);
        Assert.Equal("original", target.SourceKind);
        Assert.True(target.UsedNetworkSearch);
    }

    [Fact]
    public async Task EnqueueAsync_SameUserRequests_AreSerializedByUserSemaphore()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var blockingFactory = new BlockingFirstDbContextFactory(options);
        var soulseekClient = CreateHangingSoulseekClient();
        var service = CreateDownloadService(blockingFactory, soulseekClient);

        try
        {
            var first = Task.Run(() => service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\first.flac", Size: 1234L) },
                CancellationToken.None));

            await blockingFactory.FirstCreateStarted.Task.WaitAsync(TimeSpan.FromSeconds(5));

            var second = Task.Run(() => service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\second.flac", Size: 1234L) },
                CancellationToken.None));

            await Task.Delay(200);

            Assert.False(second.IsCompleted);
            Assert.Equal(1, blockingFactory.CreateCount);

            blockingFactory.ReleaseFirstCreate();

            var (firstEnqueued, firstFailed) = await first.WaitAsync(TimeSpan.FromSeconds(5));
            var (secondEnqueued, secondFailed) = await second.WaitAsync(TimeSpan.FromSeconds(5));

            Assert.Single(firstEnqueued);
            Assert.Empty(firstFailed);
            Assert.Single(secondEnqueued);
            Assert.Empty(secondFailed);
            Assert.True(blockingFactory.CreateCount >= 2);

            Assert.True(service.TryCancel(firstEnqueued.Single().Id));
            Assert.True(service.TryCancel(secondEnqueued.Single().Id));
        }
        finally
        {
            blockingFactory.ReleaseFirstCreate();
            await ShutdownAndDeleteDatabaseAsync(service, databasePath);
        }
    }

    [Fact]
    public async Task EnqueueAsync_DifferentUsers_CanEnterCriticalSectionConcurrently()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var blockingFactory = new BlockingFirstDbContextFactory(options);
        var soulseekClient = CreateHangingSoulseekClient();
        var service = CreateDownloadService(blockingFactory, soulseekClient);

        try
        {
            var first = Task.Run(() => service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\first.flac", Size: 1234L) },
                CancellationToken.None));

            await blockingFactory.FirstCreateStarted.Task.WaitAsync(TimeSpan.FromSeconds(5));

            var second = Task.Run(() => service.EnqueueAsync(
                "bob",
                new[] { (Filename: @"Music\second.flac", Size: 1234L) },
                CancellationToken.None));

            await WaitUntilAsync(() => blockingFactory.CreateCount >= 2, TimeSpan.FromSeconds(5));

            blockingFactory.ReleaseFirstCreate();

            var (firstEnqueued, firstFailed) = await first.WaitAsync(TimeSpan.FromSeconds(5));
            var (secondEnqueued, secondFailed) = await second.WaitAsync(TimeSpan.FromSeconds(5));

            Assert.Single(firstEnqueued);
            Assert.Empty(firstFailed);
            Assert.Single(secondEnqueued);
            Assert.Empty(secondFailed);

            Assert.True(service.TryCancel(firstEnqueued.Single().Id));
            Assert.True(service.TryCancel(secondEnqueued.Single().Id));
        }
        finally
        {
            blockingFactory.ReleaseFirstCreate();
            await ShutdownAndDeleteDatabaseAsync(service, databasePath);
        }
    }


    [Fact]
    public async Task EnqueueAsync_DoesNotRequirePeerPreflightConnection()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");

        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(client => client.Downloads)
            .Returns(Array.Empty<Soulseek.Transfer>());
        soulseekClient
            .Setup(client => client.ConnectToUserAsync(
                It.IsAny<string>(),
                It.IsAny<bool>(),
                It.IsAny<CancellationToken?>()))
            .ThrowsAsync(new InvalidOperationException("peer preflight should not run"));
        soulseekClient
            .Setup(client => client.GetUserEndPointAsync(
                It.IsAny<string>(),
                It.IsAny<CancellationToken?>()))
            .ThrowsAsync(new InvalidOperationException("endpoint preflight should not run"));
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long?>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()))
            .Returns(async (
                string username,
                string remoteFilename,
                Func<Task<Stream>> outputStreamFactory,
                long? size,
                long startOffset,
                int? token,
                TransferOptions transferOptions,
                CancellationToken? cancellationToken) =>
            {
                await Task.Delay(Timeout.Infinite, cancellationToken ?? CancellationToken.None);
                return null!;
            });

        var service = new DownloadService(
            new TestOptionsMonitor<slskd.Options>(CreateTestOptions()),
            soulseekClient.Object,
            new TestDbContextFactory(options),
            new FileService(new TestOptionsMonitor<slskd.Options>(CreateTestOptions())),
            Mock.Of<IRelayService>(),
            Mock.Of<IFTPService>(),
            new EventBus(new EventService(Mock.Of<Microsoft.EntityFrameworkCore.IDbContextFactory<EventsDbContext>>())));

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\track.flac", Size: 1234L) },
                CancellationToken.None);

            Assert.Single(enqueued);
            Assert.Empty(failed);

            Assert.True(service.TryCancel(enqueued.Single().Id));

            soulseekClient.Verify(client => client.ConnectToUserAsync(
                It.IsAny<string>(),
                It.IsAny<bool>(),
                It.IsAny<CancellationToken?>()), Times.Never);
            soulseekClient.Verify(client => client.GetUserEndPointAsync(
                It.IsAny<string>(),
                It.IsAny<CancellationToken?>()), Times.Never);
        }
        finally
        {
            await ShutdownAndDeleteDatabaseAsync(service, databasePath);
        }
    }

    [Fact]
    public async Task EnqueueAsync_CancelledTransfer_DoesNotFailFromDisposedBatchSemaphore()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var downloadStarted = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(client => client.Downloads)
            .Returns(Array.Empty<Soulseek.Transfer>());
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long?>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()))
            .Returns(async (
                string username,
                string remoteFilename,
                Func<Task<Stream>> outputStreamFactory,
                long? size,
                long startOffset,
                int? token,
                TransferOptions transferOptions,
                CancellationToken? cancellationToken) =>
            {
                downloadStarted.TrySetResult();
                await Task.Delay(Timeout.Infinite, cancellationToken ?? CancellationToken.None);
                return null!;
            });

        var service = new DownloadService(
            new TestOptionsMonitor<slskd.Options>(CreateTestOptions()),
            soulseekClient.Object,
            new TestDbContextFactory(options),
            new FileService(new TestOptionsMonitor<slskd.Options>(CreateTestOptions())),
            Mock.Of<IRelayService>(),
            Mock.Of<IFTPService>(),
            new EventBus(new EventService(Mock.Of<Microsoft.EntityFrameworkCore.IDbContextFactory<EventsDbContext>>())));

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\track.flac", Size: 1234L) },
                CancellationToken.None);

            Assert.Single(enqueued);
            Assert.Empty(failed);

            var transferId = enqueued.Single().Id;
            await downloadStarted.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await WaitForTransferAsync(
                () => service.Find(t => t.Id == transferId),
                TimeSpan.FromSeconds(5));

            Assert.True(service.TryCancel(transferId));

            var cancelledTransfer = await WaitForTransferAsync(
                () => service.Find(t => t.Id == transferId && t.EndedAt != null),
                TimeSpan.FromSeconds(5));

            Assert.True(cancelledTransfer.State.HasFlag(TransferStates.Completed));
            Assert.DoesNotContain("SemaphoreSlim", cancelledTransfer.Exception ?? string.Empty, StringComparison.Ordinal);
            Assert.DoesNotContain("disposed object", cancelledTransfer.Exception ?? string.Empty, StringComparison.OrdinalIgnoreCase);
            Assert.False(service.TryCancel(transferId));
        }
        finally
        {
            await ShutdownAndDeleteDatabaseAsync(service, databasePath);
        }
    }

    [Fact]
    public async Task Dispose_WhenApplicationIsShuttingDown_DoesNotMarkActiveDownloadFailed()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(client => client.Downloads)
            .Returns(Array.Empty<Soulseek.Transfer>());
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long?>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()))
            .Returns(async (
                string username,
                string remoteFilename,
                Func<Task<Stream>> outputStreamFactory,
                long? size,
                long startOffset,
                int? token,
                TransferOptions transferOptions,
                CancellationToken? cancellationToken) =>
            {
                await Task.Delay(Timeout.Infinite, cancellationToken ?? CancellationToken.None);
                return null!;
            });

        var service = new DownloadService(
            new TestOptionsMonitor<slskd.Options>(CreateTestOptions()),
            soulseekClient.Object,
            new TestDbContextFactory(options),
            new FileService(new TestOptionsMonitor<slskd.Options>(CreateTestOptions())),
            Mock.Of<IRelayService>(),
            Mock.Of<IFTPService>(),
            new EventBus(new EventService(Mock.Of<Microsoft.EntityFrameworkCore.IDbContextFactory<EventsDbContext>>())));

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\track.flac", Size: 1234L) },
                CancellationToken.None);

            Assert.Single(enqueued);
            Assert.Empty(failed);

            SetApplicationShuttingDown(true);
            service.Dispose();
            await Task.Delay(250);

            await using var context = new TransfersDbContext(options);
            var transfer = await context.Transfers.SingleAsync(t => t.Id == enqueued.Single().Id);
            Assert.Null(transfer.EndedAt);
            Assert.False(transfer.State.HasFlag(TransferStates.Completed));
        }
        finally
        {
            SetApplicationShuttingDown(false);
            service.Dispose();

            if (System.IO.File.Exists(databasePath))
            {
                DeleteDatabase(databasePath);
            }
        }
    }

    [Fact]
    public async Task ShutdownAsync_WaitsForCancelledDownloadsToDrain()
    {
        var databasePath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"{Guid.NewGuid():N}.db");
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        await using (var context = new TransfersDbContext(options))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var downloadStarted = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var cancellationObserved = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var allowDrainCompletion = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(client => client.Downloads)
            .Returns(Array.Empty<Soulseek.Transfer>());
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long?>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()))
            .Returns(async (
                string username,
                string remoteFilename,
                Func<Task<Stream>> outputStreamFactory,
                long? size,
                long startOffset,
                int? token,
                TransferOptions transferOptions,
                CancellationToken? cancellationToken) =>
            {
                try
                {
                    downloadStarted.TrySetResult();
                    await Task.Delay(Timeout.Infinite, cancellationToken ?? CancellationToken.None);
                    return null!;
                }
                catch (OperationCanceledException)
                {
                    cancellationObserved.TrySetResult();
                    await allowDrainCompletion.Task;
                    throw;
                }
            });

        var service = new DownloadService(
            new TestOptionsMonitor<slskd.Options>(CreateTestOptions()),
            soulseekClient.Object,
            new TestDbContextFactory(options),
            new FileService(new TestOptionsMonitor<slskd.Options>(CreateTestOptions())),
            Mock.Of<IRelayService>(),
            Mock.Of<IFTPService>(),
            new EventBus(new EventService(Mock.Of<Microsoft.EntityFrameworkCore.IDbContextFactory<EventsDbContext>>())));

        try
        {
            var (enqueued, failed) = await service.EnqueueAsync(
                "alice",
                new[] { (Filename: @"Music\track.flac", Size: 1234L) },
                CancellationToken.None);

            Assert.Single(enqueued);
            Assert.Empty(failed);

            await downloadStarted.Task.WaitAsync(TimeSpan.FromSeconds(5));

            SetApplicationShuttingDown(true);
            var shutdownTask = service.ShutdownAsync(CancellationToken.None);

            await cancellationObserved.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.False(shutdownTask.IsCompleted);

            allowDrainCompletion.TrySetResult();
            await shutdownTask.WaitAsync(TimeSpan.FromSeconds(5));
        }
        finally
        {
            SetApplicationShuttingDown(false);
            service.Dispose();

            if (System.IO.File.Exists(databasePath))
            {
                DeleteDatabase(databasePath);
            }
        }
    }

    [Fact]
    public void Dispose_UnsubscribesClockMinuteHandler()
    {
        var optionsMonitor = new TestOptionsMonitor<slskd.Options>(new slskd.Options());
        var clockEveryMinuteListenersBefore = GetStaticEventInvocationCount(typeof(Clock), "EveryMinute");
        var service = new DownloadService(
            optionsMonitor,
            Mock.Of<ISoulseekClient>(),
            Mock.Of<Microsoft.EntityFrameworkCore.IDbContextFactory<TransfersDbContext>>(),
            new FileService(optionsMonitor),
            Mock.Of<IRelayService>(),
            Mock.Of<IFTPService>(),
            new EventBus(new EventService(Mock.Of<Microsoft.EntityFrameworkCore.IDbContextFactory<EventsDbContext>>())));

        Assert.Equal(clockEveryMinuteListenersBefore + 1, GetStaticEventInvocationCount(typeof(Clock), "EveryMinute"));

        service.Dispose();

        Assert.Equal(clockEveryMinuteListenersBefore, GetStaticEventInvocationCount(typeof(Clock), "EveryMinute"));
    }

    [Fact]
    public void ResolveCompletedDestinationDirectory_Default_UsesRemoteFolder()
    {
        var options = CreateDownloadLayoutOptions();
        var transfer = new slskd.Transfers.Transfer
        {
            Id = Guid.NewGuid(),
            Username = "alice",
            Direction = TransferDirection.Download,
            Filename = @"Root\Artist - Album\01 Song.flac",
            BatchId = Guid.NewGuid(),
            RequestedAt = DateTime.UtcNow,
        };

        using var service = CreateDownloadServiceForLayoutTest(options);
        var destination = ResolveCompletedDestinationDirectory(service, transfer);

        Assert.Equal(
            System.IO.Path.Combine(options.Directories.Downloads, "Artist - Album"),
            destination);
    }

    [Fact]
    public void ResolveCompletedDestinationDirectory_RejectsSymlinkEscapeFromConfiguredRoot()
    {
        if (OperatingSystem.IsWindows())
        {
            return;
        }

        var options = CreateDownloadLayoutOptions();
        var outsideDirectory = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"slskdn-download-destination-{Guid.NewGuid():N}");
        System.IO.Directory.CreateDirectory(options.Directories.Downloads);
        System.IO.Directory.CreateDirectory(outsideDirectory);
        System.IO.Directory.CreateSymbolicLink(
            System.IO.Path.Combine(options.Directories.Downloads, "Artist - Album"),
            outsideDirectory);
        var transfer = new slskd.Transfers.Transfer
        {
            Id = Guid.NewGuid(),
            Username = "alice",
            Direction = TransferDirection.Download,
            Filename = @"Root\Artist - Album\01 Song.flac",
            RequestedAt = DateTime.UtcNow,
        };

        try
        {
            using var service = CreateDownloadServiceForLayoutTest(options);

            var exception = Assert.Throws<TargetInvocationException>(() => ResolveCompletedDestinationDirectory(service, transfer));

            Assert.IsType<System.IO.IOException>(exception.InnerException);
        }
        finally
        {
            System.IO.Directory.Delete(options.Directories.Downloads, recursive: true);
            System.IO.Directory.Delete(outsideDirectory, recursive: true);
        }
    }

    [Fact]
    public void ResolveCompletedDestinationDirectory_ConfiguredDefault_UsesConfiguredRoot()
    {
        var configuredRoot = System.IO.Path.Combine(
            System.IO.Path.GetTempPath(),
            $"slskdn-configured-download-{Guid.NewGuid():N}");
        var options = CreateDownloadLayoutOptions(configuredDefault: configuredRoot);
        var transfer = new slskd.Transfers.Transfer
        {
            Id = Guid.NewGuid(),
            Username = "alice",
            Direction = TransferDirection.Download,
            Filename = @"Root\Artist - Album\01 Song.flac",
            RequestedAt = DateTime.UtcNow,
        };

        using var service = CreateDownloadServiceForLayoutTest(options);
        var destination = ResolveCompletedDestinationDirectory(service, transfer);

        Assert.Equal(
            System.IO.Path.Combine(configuredRoot, "Artist - Album"),
            destination);
    }

    [Fact]
    public void ResolveCompletedDestinationDirectory_BatchId_UsesBatchIdWhenExplicitlyConfigured()
    {
        var options = CreateDownloadLayoutOptions("batch_id");
        var batchId = Guid.NewGuid();
        var transfer = new slskd.Transfers.Transfer
        {
            Id = Guid.NewGuid(),
            Username = "alice",
            Direction = TransferDirection.Download,
            Filename = @"Root\Artist - Album\01 Song.flac",
            BatchId = batchId,
            RequestedAt = DateTime.UtcNow,
        };

        using var service = CreateDownloadServiceForLayoutTest(options);
        var destination = ResolveCompletedDestinationDirectory(service, transfer);

        Assert.Equal(
            System.IO.Path.Combine(options.Directories.Downloads, batchId.ToString()),
            destination);
    }

    [Fact]
    public void ResolveCompletedDestinationDirectory_UploaderFolder_UsesUploaderAndRemoteParentFolder()
    {
        var options = CreateDownloadLayoutOptions("uploader_folder");
        var transfer = new slskd.Transfers.Transfer
        {
            Id = Guid.NewGuid(),
            Username = "alice",
            Direction = TransferDirection.Download,
            Filename = @"Root\Artist - Album\01 Song.flac",
            RequestedAt = DateTime.UtcNow,
        };

        using var service = CreateDownloadServiceForLayoutTest(options);
        var destination = ResolveCompletedDestinationDirectory(service, transfer);

        Assert.Equal(
            System.IO.Path.Combine(options.Directories.Downloads, "alice", "Artist - Album"),
            destination);
    }

    [Fact]
    public void ResolveCompletedDestinationDirectory_TokenTemplate_UsesPersistedRequestMetadata()
    {
        var options = CreateDownloadLayoutOptions(
            completedLayout: "batch_id",
            subdirectory: "${SOURCE_USERNAME}/${SOURCE_PATH}/${SOURCE_DIRECTORY}/${BATCH_EXTERNAL_ID}/${SEARCH_ID}/${SEARCH_TEXT}");
        var batchId = Guid.NewGuid();
        var searchId = Guid.NewGuid();
        var transfer = new slskd.Transfers.Transfer
        {
            Id = Guid.NewGuid(),
            Username = "alice",
            Direction = TransferDirection.Download,
            Filename = @"Music\Jazz\Track.flac",
            BatchId = batchId,
            RequestedAt = DateTime.UtcNow,
        };
        var request = new DownloadRequest
        {
            BatchId = batchId,
            BatchExternalId = "batch-42",
            SearchId = searchId,
            SearchText = "artist album",
        };

        using var service = CreateDownloadServiceForLayoutTest(options);
        var destination = ResolveCompletedDestinationDirectory(service, transfer, request);

        Assert.Equal(
            System.IO.Path.Combine(options.Directories.Downloads, "alice", "Music", "Jazz", "Jazz", "batch-42", searchId.ToString("D"), "artist album"),
            destination);
    }

    private static slskd.Options CreateDownloadLayoutOptions(
        string? completedLayout = null,
        string? configuredDefault = null,
        string? subdirectory = null)
    {
        return new slskd.Options
        {
            Directories = new slskd.Options.DirectoriesOptions
            {
                Downloads = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"slskdn-download-layout-{Guid.NewGuid():N}"),
            },
            Global = new slskd.Options.GlobalOptions
            {
                Download = completedLayout is null
                    ? new slskd.Options.GlobalOptions.GlobalDownloadOptions
                    {
                        Destination = new slskd.Options.GlobalOptions.GlobalDownloadOptions.DownloadDestinationOptions
                        {
                            Subdirectory = subdirectory,
                        },
                    }
                    : new slskd.Options.GlobalOptions.GlobalDownloadOptions
                    {
                        CompletedLayout = completedLayout,
                        Destination = new slskd.Options.GlobalOptions.GlobalDownloadOptions.DownloadDestinationOptions
                        {
                            Subdirectory = subdirectory,
                        },
                    },
            },
            Destinations = new slskd.Options.DestinationsOptions
            {
                Folders = configuredDefault is null
                    ? []
                    :
                    [
                        new slskd.Options.DestinationOption
                        {
                            Name = "Music",
                            Path = configuredDefault,
                            Default = true,
                        },
                    ],
            },
        };
    }

    private static DownloadService CreateDownloadServiceForLayoutTest(slskd.Options options)
    {
        var optionsMonitor = new TestOptionsMonitor<slskd.Options>(options);
        return new DownloadService(
            optionsMonitor,
            Mock.Of<ISoulseekClient>(),
            Mock.Of<Microsoft.EntityFrameworkCore.IDbContextFactory<TransfersDbContext>>(),
            new FileService(optionsMonitor),
            Mock.Of<IRelayService>(),
            Mock.Of<IFTPService>(),
            new EventBus(new EventService(Mock.Of<Microsoft.EntityFrameworkCore.IDbContextFactory<EventsDbContext>>())));
    }

    private static string ResolveCompletedDestinationDirectory(DownloadService service, slskd.Transfers.Transfer transfer, DownloadRequest? request = null)
    {
        var method = typeof(DownloadService).GetMethod("ResolveCompletedDestinationDirectory", BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException("ResolveCompletedDestinationDirectory was not found.");

        return Assert.IsType<string>(method.Invoke(service, [transfer, request]));
    }

    private static async Task<slskd.Transfers.Transfer> WaitForTransferAsync(Func<slskd.Transfers.Transfer?> finder, TimeSpan timeout)
    {
        var startedAt = DateTime.UtcNow;

        while (DateTime.UtcNow - startedAt < timeout)
        {
            var transfer = finder();

            if (transfer is not null)
            {
                return transfer;
            }

            await Task.Delay(50);
        }

        throw new TimeoutException($"Timed out waiting {timeout.TotalSeconds} seconds for transfer state update");
    }

    private static async Task ForceTaskFinalizersAsync()
    {
        for (var i = 0; i < 3; i++)
        {
            GC.Collect();
            GC.WaitForPendingFinalizers();
            GC.Collect();
            await Task.Delay(50);
        }
    }

    private static int GetStaticEventInvocationCount(Type type, string eventName)
    {
        var field = type.GetField(eventName, BindingFlags.Static | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException($"{type.FullName}.{eventName} backing field was not found.");

        return (field.GetValue(null) as MulticastDelegate)?.GetInvocationList().Length ?? 0;
    }

    private static void SetApplicationShuttingDown(bool value)
    {
        var property = typeof(slskd.Application).GetProperty("ShuttingDown", BindingFlags.Static | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException("Application.ShuttingDown property was not found.");

        property.SetValue(null, value);
    }

    private static DownloadService CreateDownloadService(
        DbContextOptions<TransfersDbContext> options,
        Mock<ISoulseekClient> soulseekClient,
        slskd.Options? configuredOptions = null)
    {
        var optionsMonitor = new TestOptionsMonitor<slskd.Options>(configuredOptions ?? CreateTestOptions());
        var eventService = new Mock<EventService>(Mock.Of<Microsoft.EntityFrameworkCore.IDbContextFactory<EventsDbContext>>());
        eventService.Setup(service => service.Add(It.IsAny<EventRecord>()));

        return new DownloadService(
            optionsMonitor,
            soulseekClient.Object,
            new TestDbContextFactory(options),
            new FileService(optionsMonitor),
            Mock.Of<IRelayService>(),
            Mock.Of<IFTPService>(),
            new EventBus(eventService.Object));
    }

    private sealed class TransferMaterializationInterceptor : IMaterializationInterceptor
    {
        public int TransferCount { get; set; }

        public object InitializedInstance(MaterializationInterceptionData materializationData, object entity)
        {
            if (entity is slskd.Transfers.Transfer)
            {
                TransferCount++;
            }

            return entity;
        }
    }

    private static DownloadService CreateDownloadService(
        Microsoft.EntityFrameworkCore.IDbContextFactory<TransfersDbContext> contextFactory,
        Mock<ISoulseekClient> soulseekClient)
    {
        var optionsMonitor = new TestOptionsMonitor<slskd.Options>(CreateTestOptions());
        var eventService = new Mock<EventService>(Mock.Of<Microsoft.EntityFrameworkCore.IDbContextFactory<EventsDbContext>>());
        eventService.Setup(service => service.Add(It.IsAny<EventRecord>()));

        return new DownloadService(
            optionsMonitor,
            soulseekClient.Object,
            contextFactory,
            new FileService(optionsMonitor),
            Mock.Of<IRelayService>(),
            Mock.Of<IFTPService>(),
            new EventBus(eventService.Object));
    }

    private static DownloadAutoRetryService CreateAutoRetryService(
        IHashDbService? hashDb = null,
        IAutoReplaceService? autoReplace = null)
    {
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient.SetupGet(client => client.State).Returns(SoulseekClientStates.Connected);

        return new DownloadAutoRetryService(
            Mock.Of<IDownloadService>(),
            soulseekClient.Object,
            new TestOptionsMonitor<slskd.Options>(new slskd.Options()),
            hashDb,
            autoReplace);
    }

    private static async Task WaitUntilAsync(Func<bool> predicate, TimeSpan timeout)
    {
        var startedAt = DateTime.UtcNow;

        while (DateTime.UtcNow - startedAt < timeout)
        {
            if (predicate())
            {
                return;
            }

            await Task.Delay(25);
        }

        throw new TimeoutException($"Timed out waiting {timeout.TotalSeconds} seconds for predicate");
    }

    private static Exception CreateExpectedRemoteFailure(string failureKind)
        => failureKind switch
        {
            "reported" => new SoulseekClientException(
                "Failed to download file Music\\remote-failed.flac from user alice: Download reported as failed by remote client",
                new TransferReportedFailedException("Download reported as failed by remote client")),
            "size" => new TransferSizeMismatchException("Transfer aborted: the remote size of 2000 does not match expected size 1234", 1234, 2000),
            "rejected" => new TransferRejectedException("Transfer rejected: File not shared."),
            "connection-reset" => new SoulseekClientException(
                "Failed to download file Music\\remote-failed.flac from user alice: Transfer failed: Read error: Unable to read data from the transport connection: Connection reset by peer.",
                new ConnectionException("Transfer failed: Read error: Unable to read data from the transport connection: Connection reset by peer.")),
            "remote-closed" => new SoulseekClientException(
                "Failed to download file Music\\remote-failed.flac from user alice: Transfer failed: Read error: Remote connection closed",
                new ConnectionException("Transfer failed: Read error: Remote connection closed")),
            "message-connection" => new SoulseekClientException(
                "Failed to download file Music\\remote-failed.flac from user alice: Failed to establish a direct or indirect message connection to alice (203.0.113.10:50300)",
                new ConnectionException("Failed to establish a direct or indirect message connection to alice (203.0.113.10:50300)")),
            "transfer-connection" => new SoulseekClientException(
                "Failed to download file Music\\remote-failed.flac from user alice: Failed to establish a direct or indirect transfer connection to alice (203.0.113.10:50300)",
                new ConnectionException("Failed to establish a direct or indirect transfer connection to alice (203.0.113.10:50300)")),
            _ => throw new ArgumentOutOfRangeException(nameof(failureKind)),
        };

    private static slskd.Transfers.Transfer CreateFailedDownload(string username, string filename, DateTime endedAt, long size = 1234)
        => new()
        {
            Id = Guid.NewGuid(),
            Username = username,
            Direction = TransferDirection.Download,
            Filename = filename,
            Size = size,
            RequestedAt = endedAt.AddMinutes(-5),
            EndedAt = endedAt,
            State = TransferStates.Completed | TransferStates.Errored,
        };

    private static async IAsyncEnumerable<slskd.Transfers.Transfer> ToAsyncSequence(
        IEnumerable<slskd.Transfers.Transfer> transfers,
        Action onEnumerated,
        [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        foreach (var transfer in transfers)
        {
            cancellationToken.ThrowIfCancellationRequested();
            onEnumerated();
            yield return transfer;
            await Task.Yield();
        }
    }

    private static Mock<ISoulseekClient> CreateHangingSoulseekClient()
    {
        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(client => client.Downloads)
            .Returns(Array.Empty<Soulseek.Transfer>());
        soulseekClient
            .Setup(client => client.DownloadAsync(
                It.IsAny<string>(),
                It.IsAny<string>(),
                It.IsAny<Func<Task<Stream>>>(),
                It.IsAny<long?>(),
                It.IsAny<long>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken?>()))
            .Returns(async (
                string username,
                string remoteFilename,
                Func<Task<Stream>> outputStreamFactory,
                long? size,
                long startOffset,
                int? token,
                TransferOptions transferOptions,
                CancellationToken? cancellationToken) =>
            {
                await Task.Delay(Timeout.Infinite, cancellationToken ?? CancellationToken.None);
                return null!;
            });

        return soulseekClient;
    }

    private static void DeleteDatabase(string databasePath)
    {
        RetrySqliteCleanup(databasePath, () =>
        {
            if (System.IO.File.Exists(databasePath))
            {
                System.IO.File.Delete(databasePath);
            }
        });
    }

    private static void DeleteDirectory(string directoryPath, string databasePath)
    {
        RetrySqliteCleanup(databasePath, () =>
        {
            if (System.IO.Directory.Exists(directoryPath))
            {
                System.IO.Directory.Delete(directoryPath, recursive: true);
            }
        });
    }

    private static void RetrySqliteCleanup(string databasePath, Action cleanup)
    {
        IOException? lastError = null;
        for (var attempt = 0; attempt < 60; attempt++)
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={databasePath}");
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={databasePath};Pooling=False");

            try
            {
                cleanup();
                return;
            }
            catch (IOException ex) when (attempt < 59)
            {
                lastError = ex;
                System.Threading.Thread.Sleep(TimeSpan.FromMilliseconds(50));
            }
        }

        throw lastError ?? new IOException($"SQLite test database cleanup did not complete for '{databasePath}'.");
    }

    private static async Task ShutdownAndDeleteDatabaseAsync(DownloadService service, string databasePath)
    {
        try
        {
            await service.ShutdownAsync().WaitAsync(TimeSpan.FromSeconds(5));
        }
        finally
        {
            service.Dispose();
            DeleteDatabase(databasePath);
        }
    }

    private sealed class CapturingLogSink : ILogEventSink
    {
        private readonly ConcurrentBag<LogEvent> _events = [];

        public IReadOnlyCollection<LogEvent> Events => _events.ToArray();

        public void Emit(LogEvent logEvent) => _events.Add(logEvent);
    }

    private sealed class TestDbContextFactory : Microsoft.EntityFrameworkCore.IDbContextFactory<TransfersDbContext>
    {
        private readonly DbContextOptions<TransfersDbContext> _options;

        public TestDbContextFactory(DbContextOptions<TransfersDbContext> options)
        {
            _options = options;
        }

        public TransfersDbContext CreateDbContext() => new(_options);
    }

    private sealed class BlockingFirstDbContextFactory : Microsoft.EntityFrameworkCore.IDbContextFactory<TransfersDbContext>
    {
        private readonly DbContextOptions<TransfersDbContext> _options;
        private readonly ManualResetEventSlim _releaseFirstCreate = new(initialState: false);
        private int _createCount;

        public BlockingFirstDbContextFactory(DbContextOptions<TransfersDbContext> options)
        {
            _options = options;
        }

        public TaskCompletionSource FirstCreateStarted { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

        public int CreateCount => Volatile.Read(ref _createCount);

        public TransfersDbContext CreateDbContext()
        {
            var count = Interlocked.Increment(ref _createCount);
            if (count == 1)
            {
                FirstCreateStarted.TrySetResult();
                _releaseFirstCreate.Wait(TimeSpan.FromSeconds(5));
            }

            return new TransfersDbContext(_options);
        }

        public void ReleaseFirstCreate()
        {
            _releaseFirstCreate.Set();
        }
    }
}
