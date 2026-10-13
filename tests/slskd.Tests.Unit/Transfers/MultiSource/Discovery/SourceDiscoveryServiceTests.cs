// <copyright file="SourceDiscoveryServiceTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Transfers.MultiSource.Discovery;

using Microsoft.Data.Sqlite;
using Moq;
using slskd.Common.Security;
using slskd.Transfers.MultiSource;
using slskd.Transfers.MultiSource.Discovery;
using Soulseek;
using Xunit;

public class SourceDiscoveryServiceTests
{
    [Fact]
    public void UpsertResponses_BatchesRowsAndPreservesConflictUpdates()
    {
        using var connection = new SqliteConnection("Data Source=:memory:");
        connection.Open();
        using (var schema = connection.CreateCommand())
        {
            schema.CommandText =
                """
                CREATE TABLE DiscoveredFiles (
                    Username TEXT NOT NULL,
                    Filename TEXT NOT NULL,
                    Size INTEGER NOT NULL,
                    UploadSpeed INTEGER DEFAULT 0,
                    FirstSeenUnix INTEGER NOT NULL,
                    LastSeenUnix INTEGER NOT NULL,
                    PRIMARY KEY (Username, Filename, Size)
                )
                """;
            schema.ExecuteNonQuery();
        }

        var files = Enumerable.Range(1, 201)
            .Select(index => new Soulseek.File(
                1,
                $"Music/track-{index}.flac",
                index,
                "flac",
                Array.Empty<FileAttribute>()))
            .ToArray();
        var response = new SearchResponse("listener", 1, true, 128, 0, files, Array.Empty<Soulseek.File>());

        using (var transaction = connection.BeginTransaction())
        {
            var ingestion = SourceDiscoveryService.UpsertResponses(
                connection,
                transaction,
                new[] { response },
                nowUnix: 100,
                CancellationToken.None);

            Assert.Equal(201, ingestion.AffectedRows);
            Assert.Equal(3, ingestion.CommandCount);
            transaction.Commit();
        }

        var updatedResponse = new SearchResponse(
            "listener",
            2,
            true,
            256,
            0,
            new[] { files[0] },
            Array.Empty<Soulseek.File>());
        using (var transaction = connection.BeginTransaction())
        {
            SourceDiscoveryService.UpsertResponses(
                connection,
                transaction,
                new[] { updatedResponse },
                nowUnix: 200,
                CancellationToken.None);
            transaction.Commit();
        }

        using var query = connection.CreateCommand();
        query.CommandText =
            """
            SELECT COUNT(*), MIN(FirstSeenUnix), MAX(LastSeenUnix), MAX(UploadSpeed)
            FROM DiscoveredFiles
            """;
        using var reader = query.ExecuteReader();
        Assert.True(reader.Read());
        Assert.Equal(201, reader.GetInt32(0));
        Assert.Equal(100, reader.GetInt64(1));
        Assert.Equal(200, reader.GetInt64(2));
        Assert.Equal(256, reader.GetInt32(3));
    }

    [Fact]
    public async Task DiscoveryLoop_WhenSafetyLimiterRejects_DoesNotSearchSoulseek()
    {
        var appDirectory = Path.Combine(Path.GetTempPath(), $"slskdn-discovery-test-{Guid.NewGuid():N}");
        System.IO.Directory.CreateDirectory(appDirectory);
        SourceDiscoveryService? service = null;

        try
        {
            var limiterCalled = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            var safetyLimiter = new Mock<ISoulseekSafetyLimiter>();
            safetyLimiter
                .Setup(limiter => limiter.TryConsumeSearch("source-discovery"))
                .Callback(() => limiterCalled.TrySetResult())
                .Returns(false);

            var soulseekClient = new Mock<ISoulseekClient>(MockBehavior.Strict);
            service = new SourceDiscoveryService(
                appDirectory,
                soulseekClient.Object,
                Mock.Of<IContentVerificationService>(),
                safetyLimiter.Object);

            await service.StartDiscoveryAsync("beatles", enableHashVerification: false);
            await limiterCalled.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await service.StopDiscoveryAsync();

            soulseekClient.VerifyNoOtherCalls();
        }
        finally
        {
            if (service is not null)
            {
                await service.StopDiscoveryAsync();
                service.Dispose();
            }

            slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={Path.Combine(appDirectory, "discovery", "discovery.db")}");
            System.IO.Directory.Delete(appDirectory, recursive: true);
        }
    }
}
