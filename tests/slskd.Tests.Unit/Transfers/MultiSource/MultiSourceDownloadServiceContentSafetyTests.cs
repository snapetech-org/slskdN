// <copyright file="MultiSourceDownloadServiceContentSafetyTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Transfers.MultiSource;

using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using slskd;
using slskd.Common.Security;
using slskd.Tests.Unit;
using slskd.Transfers.MultiSource;
using Soulseek;
using Xunit;
using Directory = System.IO.Directory;
using File = System.IO.File;

public class MultiSourceDownloadServiceContentSafetyTests
{
    [Fact]
    public async Task DownloadAsync_SequentialFailoverQuarantinesExecutableDisguisedAsMedia()
    {
        var downloadsRoot = Path.Combine(Path.GetTempPath(), $"slskdn-multisource-safety-{Guid.NewGuid():N}");
        Directory.CreateDirectory(downloadsRoot);
        var outputPath = Path.Combine(downloadsRoot, "disguised.mp3");
        var maliciousContent = new byte[] { 0x4D, 0x5A, 0x90, 0x00 };
        var client = new Mock<ISoulseekClient>();
        client
            .Setup(soulseekClient => soulseekClient.DownloadAsync(
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
                TransferOptions transferOptions,
                CancellationToken cancellationToken) =>
            {
                var stream = await outputStreamFactory().ConfigureAwait(false);
                await stream.WriteAsync(maliciousContent, cancellationToken).ConfigureAwait(false);
                return new Transfer(
                    TransferDirection.Download,
                    username,
                    remoteFilename,
                    token ?? 1,
                    TransferStates.Completed | TransferStates.Succeeded,
                    size,
                    startOffset,
                    maliciousContent.Length);
            });

        var options = new Options
        {
            Directories = new Options.DirectoriesOptions { Downloads = downloadsRoot }
        };
        var service = new MultiSourceDownloadService(
            NullLogger<MultiSourceDownloadService>.Instance,
            client.Object,
            Mock.Of<IContentVerificationService>(),
            optionsMonitor: new TestOptionsMonitor<Options>(options));

        try
        {
            var result = await service.DownloadAsync(
                new MultiSourceDownloadRequest
                {
                    Filename = "disguised.mp3",
                    FileSize = maliciousContent.Length,
                    OutputPath = outputPath,
                    Sources =
                    [
                        new VerifiedSource
                        {
                            Username = "source",
                            FullPath = @"Music\disguised.mp3",
                        },
                    ],
                },
                CancellationToken.None);

            Assert.False(result.Success);
            Assert.Contains("Content safety rejected", result.Error, StringComparison.Ordinal);
            Assert.False(File.Exists(outputPath));
            var quarantinedPath = Assert.Single(Directory.GetFiles(Path.Combine(downloadsRoot, ".quarantine")));
            Assert.Equal(maliciousContent, await File.ReadAllBytesAsync(quarantinedPath));
        }
        finally
        {
            Directory.Delete(downloadsRoot, recursive: true);
        }
    }
}
