// <copyright file="PeerStreamServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Streaming;

using System.Text;
using Microsoft.Extensions.Logging;
using Moq;
using Soulseek;
using slskd.Streaming;
using slskd.Transfers.Downloads;
using Xunit;
using TestOptionsMonitor = slskd.Tests.Unit.TestOptionsMonitor<slskd.Options>;

public class PeerStreamServiceTests
{
    [Fact]
    public async Task OpenAsync_ValidTicket_StreamsSoulseekBytesAndReleasesLimiter()
    {
        var payload = Encoding.UTF8.GetBytes("peer-preview-bytes");
        var tickets = new Mock<IPeerStreamTicketService>();
        var limiter = new Mock<IStreamSessionLimiter>();
        var client = new Mock<ISoulseekClient>();

        tickets.Setup(x => x.Validate("ticket-1"))
            .Returns(new PeerStreamTicket("ticket-1", "remote-user", @"Music\track.flac", payload.Length, "user:alice", DateTimeOffset.UtcNow.AddMinutes(1), "audio/flac"));
        limiter.Setup(x => x.TryAcquire("user:alice", 1)).Returns(true);
        client.Setup(x => x.DownloadAsync(
                "remote-user",
                @"Music\track.flac",
                It.IsAny<Func<Task<Stream>>>(),
                payload.Length,
                0,
                null,
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns(async (
                string _,
                string _,
                Func<Task<Stream>> outputStreamFactory,
                long _,
                long _,
                int? _,
                TransferOptions _,
                CancellationToken cancellationToken) =>
            {
                var output = await outputStreamFactory();
                await output.WriteAsync(payload, cancellationToken);
                await output.FlushAsync(cancellationToken);
                return null!;
            });

        var service = new PeerStreamService(
            tickets.Object,
            limiter.Object,
            client.Object,
            Mock.Of<ILogger<PeerStreamService>>(),
            new TestOptionsMonitor(new slskd.Options()));

        var lease = await service.OpenAsync("ticket-1", CancellationToken.None);

        Assert.NotNull(lease);
        Assert.Equal("audio/flac", lease.ContentType);
        await using (var stream = lease.Stream)
        {
            var actual = await ReadAllAsync(stream);
            Assert.Equal(payload, actual);
        }

        limiter.Verify(x => x.Release("user:alice"), Times.Once);
    }

    [Fact]
    public async Task OpenAsync_UnknownSize_UsesRemoteSizeForTransferValidation()
    {
        var tickets = new Mock<IPeerStreamTicketService>();
        var limiter = new Mock<IStreamSessionLimiter>();
        var client = new Mock<ISoulseekClient>();
        TransferOptions? transferOptions = null;

        tickets.Setup(x => x.Validate("ticket-1"))
            .Returns(new PeerStreamTicket("ticket-1", "remote-user", "track.mp3", null, "user:alice", DateTimeOffset.UtcNow.AddMinutes(1), "audio/mpeg"));
        limiter.Setup(x => x.TryAcquire("user:alice", 1)).Returns(true);
        client.Setup(x => x.DownloadAsync(
                "remote-user",
                "track.mp3",
                It.IsAny<Func<Task<Stream>>>(),
                0,
                0,
                null,
                It.IsAny<TransferOptions>(),
                It.IsAny<CancellationToken>()))
            .Returns((string _, string _, Func<Task<Stream>> _, long _, long _, int? _, TransferOptions options, CancellationToken _) =>
            {
                transferOptions = options;
                return Task.FromResult<Transfer>(null!);
            });

        var service = new PeerStreamService(
            tickets.Object,
            limiter.Object,
            client.Object,
            Mock.Of<ILogger<PeerStreamService>>(),
            new TestOptionsMonitor(new slskd.Options()));

        var lease = await service.OpenAsync("ticket-1", CancellationToken.None);

        Assert.NotNull(lease);
        await using (lease.Stream)
        {
            Assert.Empty(await ReadAllAsync(lease.Stream));
        }

        Assert.NotNull(transferOptions?.SizeMismatchResolver);
        Assert.Equal(123L, transferOptions!.SizeMismatchResolver(null!, 123L));
    }

    [Fact]
    public async Task OpenAsync_LimiterRejects_DoesNotStartSoulseekDownload()
    {
        var tickets = new Mock<IPeerStreamTicketService>();
        var limiter = new Mock<IStreamSessionLimiter>();
        var client = new Mock<ISoulseekClient>();

        tickets.Setup(x => x.Validate("ticket-1"))
            .Returns(new PeerStreamTicket("ticket-1", "remote-user", "track.mp3", 10, "user:alice", DateTimeOffset.UtcNow.AddMinutes(1), "audio/mpeg"));
        limiter.Setup(x => x.TryAcquire("user:alice", 1)).Returns(false);

        var service = new PeerStreamService(
            tickets.Object,
            limiter.Object,
            client.Object,
            Mock.Of<ILogger<PeerStreamService>>(),
            new TestOptionsMonitor(new slskd.Options()));

        await Assert.ThrowsAsync<PeerStreamLimitException>(() => service.OpenAsync("ticket-1", CancellationToken.None));
        client.Verify(x => x.DownloadAsync(
            It.IsAny<string>(),
            It.IsAny<string>(),
            It.IsAny<Func<Task<Stream>>>(),
            It.IsAny<long>(),
            It.IsAny<long>(),
            It.IsAny<int?>(),
            It.IsAny<TransferOptions>(),
            It.IsAny<CancellationToken>()), Times.Never);
    }

    [Fact]
    public async Task OpenAsync_GlobalDownloadExclusion_DoesNotStartSoulseekDownload()
    {
        var tickets = new Mock<IPeerStreamTicketService>();
        var limiter = new Mock<IStreamSessionLimiter>();
        var client = new Mock<ISoulseekClient>();

        tickets.Setup(x => x.Validate("ticket-1"))
            .Returns(new PeerStreamTicket("ticket-1", "remote-user", "Music/instrumental.flac", 10, "user:alice", DateTimeOffset.UtcNow.AddMinutes(1), "audio/flac"));

        var service = new PeerStreamService(
            tickets.Object,
            limiter.Object,
            client.Object,
            Mock.Of<ILogger<PeerStreamService>>(),
            new TestOptionsMonitor(new slskd.Options
            {
                Filters = new slskd.Options.FiltersOptions
                {
                    Download = new slskd.Options.FiltersOptions.DownloadFilterOptions
                    {
                        Exclude = new[] { "instrumental" },
                    },
                },
            }));

        var exception = await Assert.ThrowsAsync<DownloadBlockedByPolicyException>(
            () => service.OpenAsync("ticket-1", CancellationToken.None));

        Assert.Equal("Music/instrumental.flac", exception.Filename);
        limiter.Verify(x => x.TryAcquire(It.IsAny<string>(), It.IsAny<int>()), Times.Never);
        client.Verify(x => x.DownloadAsync(
            It.IsAny<string>(),
            It.IsAny<string>(),
            It.IsAny<Func<Task<Stream>>>(),
            It.IsAny<long>(),
            It.IsAny<long>(),
            It.IsAny<int?>(),
            It.IsAny<TransferOptions>(),
            It.IsAny<CancellationToken>()), Times.Never);
    }

    private static async Task<byte[]> ReadAllAsync(Stream stream)
    {
        using var output = new MemoryStream();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await stream.CopyToAsync(output, timeout.Token);
        return output.ToArray();
    }
}
