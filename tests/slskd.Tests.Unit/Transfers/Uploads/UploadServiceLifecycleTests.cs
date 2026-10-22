// <copyright file="UploadServiceLifecycleTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Transfers.Uploads;

using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Moq;
using slskd.Events;
using slskd.Files;
using slskd.Relay;
using slskd.Tests.Unit;
using slskd.Shares;
using slskd.Transfers;
using slskd.Transfers.MultiSource.Metrics;
using slskd.Transfers.Uploads;
using slskd.Users;
using Soulseek;
using Xunit;

public class UploadServiceLifecycleTests
{
    [Fact]
    public async Task PruneRemoved_DeletesOnlyOldCompletedRemovedUploads()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var dbOptions = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite(connection)
            .Options;
        var now = DateTime.UtcNow;
        var expiredId = Guid.NewGuid();
        var recentId = Guid.NewGuid();
        var activeRemovedId = Guid.NewGuid();
        var visibleId = Guid.NewGuid();
        var downloadId = Guid.NewGuid();

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

        await using (var context = new TransfersDbContext(dbOptions))
        {
            await context.Database.EnsureCreatedAsync();
            context.Transfers.AddRange(
                CreateTransfer(expiredId, TransferDirection.Upload, true, now.AddMinutes(-30)),
                CreateTransfer(recentId, TransferDirection.Upload, true, now),
                CreateTransfer(activeRemovedId, TransferDirection.Upload, true, null),
                CreateTransfer(visibleId, TransferDirection.Upload, false, now.AddMinutes(-30)),
                CreateTransfer(downloadId, TransferDirection.Download, true, now.AddMinutes(-30)));
            await context.SaveChangesAsync();

            await context.Database.ExecuteSqlInterpolatedAsync(
                $"UPDATE Transfers SET UpdatedAt = {now.AddMinutes(-30)} WHERE Id IN ({expiredId}, {activeRemovedId}, {visibleId}, {downloadId})");
        }

        var optionsMonitor = new TestOptionsMonitor<Options>(new Options());
        var userService = new Mock<IUserService>();
        var eventService = new EventService(Mock.Of<IDbContextFactory<EventsDbContext>>());
        using var service = new UploadService(
            new FileService(optionsMonitor),
            userService.Object,
            Mock.Of<ISoulseekClient>(),
            optionsMonitor,
            Mock.Of<IShareService>(),
            Mock.Of<IRelayService>(),
            new TestDbContextFactory(dbOptions),
            new EventBus(eventService),
            Mock.Of<ITrafficAccountingService>());

        Assert.Equal(1, service.PruneRemoved(5));

        await using var verificationContext = new TransfersDbContext(dbOptions);
        var remainingIds = await verificationContext.Transfers.Select(transfer => transfer.Id).ToListAsync();
        Assert.DoesNotContain(expiredId, remainingIds);
        Assert.Contains(recentId, remainingIds);
        Assert.Contains(activeRemovedId, remainingIds);
        Assert.Contains(visibleId, remainingIds);
        Assert.Contains(downloadId, remainingIds);
    }

    [Fact]
    public void Dispose_DisposesOwnedGovernorAndQueue()
    {
        var optionsMonitor = new TestOptionsMonitor<Options>(new Options());
        var userService = new Mock<IUserService>();
        userService.Setup(x => x.GetGroup(It.IsAny<string>())).Returns(Application.DefaultGroup);
        var eventService = new EventService(Mock.Of<IDbContextFactory<EventsDbContext>>());
        var service = new UploadService(
            new FileService(optionsMonitor),
            userService.Object,
            Mock.Of<ISoulseekClient>(),
            optionsMonitor,
            Mock.Of<IShareService>(),
            Mock.Of<IRelayService>(),
            Mock.Of<IDbContextFactory<TransfersDbContext>>(),
            new EventBus(eventService),
            Mock.Of<ITrafficAccountingService>());

        Assert.Equal(2, optionsMonitor.ListenerCount);

        service.Dispose();

        Assert.Equal(0, optionsMonitor.ListenerCount);
    }

    [Fact]
    public async Task UploadAsync_WhenSoulseekConnectionIsRefused_MarksUploadFailed()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();

        var dbOptions = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite(connection)
            .Options;

        await using (var context = new TransfersDbContext(dbOptions))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var transfer = new slskd.Transfers.Transfer
        {
            Id = Guid.NewGuid(),
            Username = "alice",
            Direction = TransferDirection.Upload,
            Filename = @"Music\track.flac",
            Size = 4,
            State = TransferStates.Queued | TransferStates.Locally,
            RequestedAt = DateTime.UtcNow,
        };

        await using (var context = new TransfersDbContext(dbOptions))
        {
            context.Transfers.Add(transfer);
            await context.SaveChangesAsync();
        }

        var tempFile = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid():N}.flac");
        await System.IO.File.WriteAllBytesAsync(tempFile, new byte[] { 1, 2, 3, 4 });

        var optionsMonitor = new TestOptionsMonitor<Options>(new Options());
        var userService = new Mock<IUserService>();
        userService.Setup(x => x.GetGroup(It.IsAny<string>())).Returns(Application.DefaultGroup);

        var shareService = new Mock<IShareService>();
        shareService
            .Setup(x => x.ResolveFileAsync(@"Music\track.flac"))
            .ReturnsAsync((Program.LocalHostName, tempFile, 4L));

        var soulseekClient = new Mock<ISoulseekClient>();
        soulseekClient
            .SetupGet(x => x.Uploads)
            .Returns(Array.Empty<Soulseek.Transfer>());
        soulseekClient
            .Setup(x => x.UploadAsync(
                "alice",
                @"Music\track.flac",
                4L,
                It.IsAny<Func<long, Task<Stream>>>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(new IOException("Failed to connect from Soulseek.Network.Tcp.Connection.ConnectAsync: Connection refused"));

        var service = new UploadService(
            new FileService(optionsMonitor),
            userService.Object,
            soulseekClient.Object,
            optionsMonitor,
            shareService.Object,
            Mock.Of<IRelayService>(),
            new TestDbContextFactory(dbOptions),
            new EventBus(new EventService(Mock.Of<IDbContextFactory<EventsDbContext>>())),
            Mock.Of<ITrafficAccountingService>());

        try
        {
            var exception = await Assert.ThrowsAsync<IOException>(() => service.UploadAsync(transfer));

            Assert.Contains("Connection refused", exception.Message, StringComparison.Ordinal);
            var failed = service.Find(t => t.Id == transfer.Id);
            Assert.NotNull(failed);
            Assert.True(failed.State.HasFlag(TransferStates.Completed));
            Assert.True(failed.State.HasFlag(TransferStates.Errored));
            Assert.Contains("Connection refused", failed.Exception, StringComparison.Ordinal);

            var enqueueException = await Assert.ThrowsAsync<DownloadEnqueueException>(
                () => service.EnqueueAsync("alice", @"Music\another-track.flac"));
            Assert.Equal("Recent transfer failed; retry later.", enqueueException.Message);
            Assert.Equal(1, service.RemoveExpiredFailedPeerCooldowns(DateTime.UtcNow.AddMinutes(1)));
            Assert.Equal(0, service.RemoveExpiredFailedPeerCooldowns(DateTime.UtcNow.AddMinutes(1)));
        }
        finally
        {
            service.Dispose();
            System.IO.File.Delete(tempFile);
        }
    }

    [Fact]
    public async Task UploadAsync_AccountsOnlyWrittenPayloadBytes_WhenUploadCompletes()
    {
        var client = new Mock<ISoulseekClient>();
        SetupUploadClient(client, options =>
        {
            options.Reporter!(CreateSoulseekTransfer(1, TransferStates.InProgress), 1, 1, 1);
            options.Reporter!(CreateSoulseekTransfer(1, TransferStates.InProgress), 1, 1, 0);
            options.Reporter!(CreateSoulseekTransfer(4, TransferStates.InProgress), 3, 3, 3);
            return Task.FromResult(CreateSoulseekTransfer(4, TransferStates.Completed | TransferStates.Succeeded));
        });

        var accounting = CreateTrafficAccountingMock();
        await using var fixture = await CreateUploadTestFixtureAsync(client, accounting.Object);

        var result = await fixture.Service.UploadAsync(fixture.Transfer);

        Assert.NotNull(result);
        Assert.True(result.State.HasFlag(TransferStates.Succeeded));
        accounting.Verify(service => service.RecordSoulseekUploadProgress(1), Times.Once);
        accounting.Verify(service => service.RecordSoulseekUploadProgress(3), Times.Once);
        accounting.Verify(service => service.RecordSoulseekUploadProgress(0), Times.Never);
        accounting.Verify(service => service.CommitSoulseekUploadAsync(4, It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task UploadAsync_AccountsPartialPayloadBytes_WhenUploadFails()
    {
        var client = new Mock<ISoulseekClient>();
        SetupUploadClient(client, options =>
        {
            options.Reporter!(CreateSoulseekTransfer(2, TransferStates.InProgress), 2, 2, 2);
            options.Reporter!(CreateSoulseekTransfer(3, TransferStates.InProgress), 2, 2, 1);
            options.Reporter!(CreateSoulseekTransfer(3, TransferStates.InProgress), 1, 1, 0);
            return Task.FromException<Soulseek.Transfer>(new InvalidOperationException("synthetic upload failure"));
        });

        var accounting = CreateTrafficAccountingMock();
        await using var fixture = await CreateUploadTestFixtureAsync(client, accounting.Object);

        await Assert.ThrowsAsync<InvalidOperationException>(() => fixture.Service.UploadAsync(fixture.Transfer));

        accounting.Verify(service => service.RecordSoulseekUploadProgress(2), Times.Once);
        accounting.Verify(service => service.RecordSoulseekUploadProgress(1), Times.Once);
        accounting.Verify(service => service.CommitSoulseekUploadAsync(3, It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task UploadAsync_AccountingFailureDoesNotChangeSuccessfulTransferResult()
    {
        var client = new Mock<ISoulseekClient>();
        SetupUploadClient(client, options =>
        {
            options.Reporter!(CreateSoulseekTransfer(4, TransferStates.InProgress), 4, 4, 4);
            return Task.FromResult(CreateSoulseekTransfer(4, TransferStates.Completed | TransferStates.Succeeded));
        });

        var accounting = CreateTrafficAccountingMock();
        accounting
            .Setup(service => service.CommitSoulseekUploadAsync(It.IsAny<long>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new IOException("synthetic accounting failure"));
        await using var fixture = await CreateUploadTestFixtureAsync(client, accounting.Object);

        var result = await fixture.Service.UploadAsync(fixture.Transfer);

        Assert.NotNull(result);
        Assert.True(result.State.HasFlag(TransferStates.Succeeded));
    }

    private static void SetupUploadClient(Mock<ISoulseekClient> client, Func<TransferOptions, Task<Soulseek.Transfer>> upload)
    {
        client.SetupGet(service => service.Uploads).Returns(Array.Empty<Soulseek.Transfer>());
        client.Setup(service => service.UploadAsync(
                "alice",
                @"Music\track.flac",
                4L,
                It.IsAny<Func<long, Task<Stream>>>(),
                It.IsAny<int?>(),
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns((string username, string remoteFilename, long size, Func<long, Task<Stream>> inputStreamFactory, int? token, TransferOptions options, CancellationToken cancellationToken) => upload(options));
    }

    private static Soulseek.Transfer CreateSoulseekTransfer(long bytesTransferred, TransferStates state) =>
        new(
            TransferDirection.Upload,
            "alice",
            @"Music\track.flac",
            1,
            state,
            4,
            0,
            bytesTransferred);

    private static Mock<ITrafficAccountingService> CreateTrafficAccountingMock()
    {
        var accounting = new Mock<ITrafficAccountingService>();
        accounting
            .Setup(service => service.CommitSoulseekUploadAsync(It.IsAny<long>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        return accounting;
    }

    private static async Task<UploadTestFixture> CreateUploadTestFixtureAsync(
        Mock<ISoulseekClient> client,
        ITrafficAccountingService accounting)
    {
        var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var dbOptions = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite(connection)
            .Options;

        await using (var context = new TransfersDbContext(dbOptions))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var transfer = new slskd.Transfers.Transfer
        {
            Id = Guid.NewGuid(),
            Username = "alice",
            Direction = TransferDirection.Upload,
            Filename = @"Music\track.flac",
            Size = 4,
            State = TransferStates.Queued | TransferStates.Locally,
            RequestedAt = DateTime.UtcNow,
        };

        await using (var context = new TransfersDbContext(dbOptions))
        {
            context.Transfers.Add(transfer);
            await context.SaveChangesAsync();
        }

        var eventConnection = new SqliteConnection("Data Source=:memory:");
        await eventConnection.OpenAsync();
        var eventDbOptions = new DbContextOptionsBuilder<EventsDbContext>()
            .UseSqlite(eventConnection)
            .Options;
        await using (var context = new EventsDbContext(eventDbOptions))
        {
            await context.Database.EnsureCreatedAsync();
        }

        var tempFile = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid():N}.flac");
        await System.IO.File.WriteAllBytesAsync(tempFile, new byte[] { 1, 2, 3, 4 });

        var optionsMonitor = new TestOptionsMonitor<Options>(new Options());
        var userService = new Mock<IUserService>();
        userService.Setup(service => service.GetGroup(It.IsAny<string>())).Returns(Application.DefaultGroup);
        var shareService = new Mock<IShareService>();
        shareService
            .Setup(service => service.ResolveFileAsync(@"Music\track.flac"))
            .ReturnsAsync((Program.LocalHostName, tempFile, 4L));

        var service = new UploadService(
            new FileService(optionsMonitor),
            userService.Object,
            client.Object,
            optionsMonitor,
            shareService.Object,
            Mock.Of<IRelayService>(),
            new TestDbContextFactory(dbOptions),
            new EventBus(new EventService(new TestEventsDbContextFactory(eventDbOptions))),
            accounting);

        return new UploadTestFixture(connection, eventConnection, tempFile, service, transfer);
    }

    private sealed class UploadTestFixture : IAsyncDisposable
    {
        private readonly SqliteConnection _connection;
        private readonly SqliteConnection _eventConnection;
        private readonly string _tempFile;

        public UploadTestFixture(SqliteConnection connection, SqliteConnection eventConnection, string tempFile, UploadService service, slskd.Transfers.Transfer transfer)
        {
            _connection = connection;
            _eventConnection = eventConnection;
            _tempFile = tempFile;
            Service = service;
            Transfer = transfer;
        }

        public UploadService Service { get; }

        public slskd.Transfers.Transfer Transfer { get; }

        public async ValueTask DisposeAsync()
        {
            Service.Dispose();
            System.IO.File.Delete(_tempFile);
            await _connection.DisposeAsync();
            await _eventConnection.DisposeAsync();
        }
    }

    private sealed class TestEventsDbContextFactory : IDbContextFactory<EventsDbContext>
    {
        private readonly DbContextOptions<EventsDbContext> _options;

        public TestEventsDbContextFactory(DbContextOptions<EventsDbContext> options)
        {
            _options = options;
        }

        public EventsDbContext CreateDbContext() => new(_options);
    }

    private sealed class TestDbContextFactory : IDbContextFactory<TransfersDbContext>
    {
        private readonly DbContextOptions<TransfersDbContext> _options;

        public TestDbContextFactory(DbContextOptions<TransfersDbContext> options)
        {
            _options = options;
        }

        public TransfersDbContext CreateDbContext() => new(_options);
    }
}
