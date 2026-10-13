// <copyright file="TransfersDbContextTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Transfers;

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using slskd.Migrations;
using slskd.Transfers;
using Soulseek;
using Xunit;
using SlskdTransfer = slskd.Transfers.Transfer;

public sealed class TransfersDbContextTests
{
    [Fact]
    public async Task SaveChanges_Stamps_Transfer_Updates_For_Sync_And_Async_Writes()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite(connection)
            .Options;

        await using var context = new TransfersDbContext(options);
        await context.Database.EnsureCreatedAsync();
        var transfer = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            Direction = TransferDirection.Download,
            Filename = "Music/song.flac",
            RequestedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UnixEpoch,
            Username = "listener",
        };
        context.Transfers.Add(transfer);

        context.SaveChanges();
        Assert.True(transfer.UpdatedAt > DateTime.UnixEpoch);

        transfer.BytesTransferred = 1;
        transfer.UpdatedAt = DateTime.UnixEpoch;
        await context.SaveChangesAsync();
        Assert.True(transfer.UpdatedAt > DateTime.UnixEpoch);
    }

    [Fact]
    public async Task Transfer_Change_Query_Uses_Direction_And_UpdatedAt_Index()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite(connection)
            .Options;
        await using var context = new TransfersDbContext(options);
        await context.Database.EnsureCreatedAsync();

        await using var command = connection.CreateCommand();
        command.CommandText = """
            EXPLAIN QUERY PLAN
            SELECT *
            FROM Transfers
            WHERE Direction = 'Download' AND UpdatedAt > '2026-07-15 12:00:00'
            ORDER BY UpdatedAt
            """;
        await using var reader = await command.ExecuteReaderAsync();
        var details = new List<string>();
        while (await reader.ReadAsync())
        {
            details.Add(reader.GetString(3));
        }

        Assert.True(
            details.Any(detail =>
                detail.Contains("INDEX IDX_Transfers_Direction_UpdatedAt", StringComparison.Ordinal)),
            string.Join(" | ", details));
        Assert.DoesNotContain(details, detail =>
            detail.Contains("TEMP B-TREE", StringComparison.Ordinal));
    }

    [Fact]
    public async Task BoundedTransferQueries_ExecuteAndUseCoveringOrderedIndexes()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite(connection)
            .Options;
        await using var context = new TransfersDbContext(options);
        await context.Database.EnsureCreatedAsync();

        var now = DateTime.UtcNow;
        var completed = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            Direction = TransferDirection.Download,
            EndedAt = now.AddMinutes(-1),
            Filename = "Music/completed.flac",
            RequestedAt = now.AddMinutes(-2),
            State = TransferStates.Completed | TransferStates.Succeeded,
            Username = "listener",
        };
        var failed = new SlskdTransfer
        {
            Id = Guid.NewGuid(),
            Direction = TransferDirection.Download,
            EndedAt = now,
            Filename = "Music/failed.flac",
            RequestedAt = now.AddMinutes(-1),
            State = TransferStates.Completed | TransferStates.Errored,
            Username = "listener",
        };
        context.Transfers.AddRange(completed, failed);
        await context.SaveChangesAsync();

        var actionable = await context.Transfers
            .AsNoTracking()
            .Where(transfer =>
                transfer.Direction == TransferDirection.Download &&
                !transfer.Removed &&
                ((transfer.State & TransferStates.Completed) != TransferStates.Completed ||
                 (transfer.State & TransferStates.Succeeded) != TransferStates.Succeeded))
            .OrderBy(transfer => transfer.UpdatedAt)
            .ToListAsync();
        var history = await context.Transfers
            .AsNoTracking()
            .Where(transfer => transfer.Direction == TransferDirection.Download)
            .Where(transfer =>
                (transfer.State & TransferStates.Completed) == TransferStates.Completed &&
                (transfer.State & TransferStates.Succeeded) == TransferStates.Succeeded)
            .Where(transfer => transfer.EndedAt.HasValue && transfer.EndedAt.Value <= now)
            .OrderByDescending(transfer => transfer.EndedAt)
            .ThenByDescending(transfer => transfer.RequestedAt)
            .ThenByDescending(transfer => transfer.Id)
            .Take(250)
            .ToListAsync();
        var autoRetry = await context.Transfers
            .AsNoTracking()
            .Where(transfer => transfer.Direction == TransferDirection.Download)
            .Where(transfer => !transfer.Removed)
            .Where(transfer =>
                (transfer.State & TransferStates.Completed) == TransferStates.Completed &&
                (transfer.State & TransferStates.Succeeded) != TransferStates.Succeeded &&
                (transfer.State & TransferStates.Cancelled) != TransferStates.Cancelled &&
                (transfer.State & TransferStates.Rejected) != TransferStates.Rejected)
            .Where(transfer => transfer.EndedAt.HasValue && transfer.EndedAt.Value < now.AddMinutes(1))
            .OrderBy(transfer => transfer.EndedAt)
            .ThenBy(transfer => transfer.Id)
            .Take(10)
            .ToListAsync();

        Assert.Equal(failed.Id, Assert.Single(actionable).Id);
        Assert.Equal(completed.Id, Assert.Single(history).Id);
        Assert.Equal(failed.Id, Assert.Single(autoRetry).Id);
        await context.Database.ExecuteSqlRawAsync("ANALYZE");

        var actionablePlan = await ReadQueryPlanAsync(
            connection,
            """
            SELECT * FROM Transfers
            WHERE Direction = 'Download'
              AND Removed = 0
              AND ((State & 16) != 16 OR (State & 32) != 32)
              AND UpdatedAt <= '2026-07-15 12:00:00'
            ORDER BY UpdatedAt
            """);
        var countPlan = await ReadQueryPlanAsync(
            connection,
            "SELECT COUNT(*) FROM Transfers WHERE Direction = 'Download' AND Removed = 0");
        var historyPlan = await ReadQueryPlanAsync(
            connection,
            """
            SELECT * FROM Transfers
            WHERE Direction = 'Download'
              AND EndedAt IS NOT NULL
              AND EndedAt <= '2026-07-15 12:00:00'
              AND (State & 16) = 16
              AND (State & 32) = 32
            ORDER BY EndedAt DESC, RequestedAt DESC, Id DESC
            LIMIT 250
            """);
        var autoRetryPlan = await ReadQueryPlanAsync(
            connection,
            """
            SELECT Id, Username, Direction, Filename, Size, State, EndedAt
            FROM Transfers
            WHERE Direction = 'Download'
              AND Removed = 0
              AND EndedAt IS NOT NULL
              AND EndedAt < '2026-07-15 12:00:00'
              AND (State & 16) = 16
              AND (State & 32) != 32
              AND (State & 64) != 64
              AND (State & 512) != 512
            ORDER BY EndedAt, Id
            LIMIT 10
            """);

        Assert.True(
            actionablePlan.Any(detail =>
                detail.Contains("INDEX IDX_Transfers_Actionable_UpdatedAt", StringComparison.Ordinal) ||
                detail.Contains("INDEX IDX_Transfers_Direction_UpdatedAt", StringComparison.Ordinal)),
            string.Join(" | ", actionablePlan));
        Assert.Contains(countPlan, detail =>
            detail.Contains("COVERING INDEX IDX_Transfers_Removed_Direction", StringComparison.Ordinal));
        Assert.Contains(historyPlan, detail =>
            detail.Contains("INDEX IDX_Transfers_Direction_EndedAt", StringComparison.Ordinal));
        Assert.Contains(autoRetryPlan, detail =>
            detail.Contains("INDEX IDX_Transfers_AutoRetry_EndedAt", StringComparison.Ordinal));
        Assert.DoesNotContain(actionablePlan.Concat(historyPlan).Concat(autoRetryPlan), detail =>
            detail.Contains("TEMP B-TREE", StringComparison.Ordinal));
    }

    [Fact]
    public async Task DownloadRequestSummaryQuery_UsesModelCreatedMixedDirectionIndex()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite(connection)
            .Options;
        await using var context = new TransfersDbContext(options);
        await context.Database.EnsureCreatedAsync();

        await using var sqlCommand = connection.CreateCommand();
        sqlCommand.CommandText =
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'IDX_Transfers_RequestId_Current'";
        var sql = Assert.IsType<string>(await sqlCommand.ExecuteScalarAsync());
        Assert.Contains("\"RequestedAt\" DESC", sql, StringComparison.OrdinalIgnoreCase);

        var plan = await ReadQueryPlanAsync(
            connection,
            """
            SELECT Id
            FROM Transfers
            WHERE RequestId = 'request-1'
            ORDER BY Removed, RequestedAt DESC
            LIMIT 1
            """);
        Assert.Contains(plan, detail =>
            detail.Contains("INDEX IDX_Transfers_RequestId_Current", StringComparison.Ordinal));
        Assert.DoesNotContain(plan, detail =>
            detail.Contains("TEMP B-TREE", StringComparison.Ordinal));
    }

    [Fact]
    public void TransferHistoryIndexesMigration_CreatesExactIdempotentIndexes()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"slskdn-transfer-history-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={databasePath}";

        try
        {
            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText =
                    """
                    CREATE TABLE Transfers (
                        Id TEXT PRIMARY KEY,
                        Direction TEXT NOT NULL,
                        State INTEGER NOT NULL,
                        Removed INTEGER NOT NULL,
                        UpdatedAt TEXT NOT NULL,
                        EndedAt TEXT NULL,
                        RequestedAt TEXT NOT NULL
                    );
                    CREATE INDEX IDX_Transfers_Direction ON Transfers (Direction);
                    """;
                command.ExecuteNonQuery();
            }

            var migration = new Z07152026_TransferHistoryIndexesMigration(
                new ConnectionStringDictionary(new()
                {
                    [Database.Transfers] = connectionString,
                }));

            Assert.True(migration.NeedsToBeApplied());
            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());

            var supersededMigration = new Z07062025_TransferIndexesMigration(
                new ConnectionStringDictionary(new()
                {
                    [Database.Transfers] = connectionString,
                }));
            Assert.True(supersededMigration.NeedsToBeApplied());
            supersededMigration.Apply();
            Assert.False(supersededMigration.NeedsToBeApplied());
            Assert.False(migration.NeedsToBeApplied());

            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                Assert.Equal(
                    ["Direction", "UpdatedAt"],
                    ReadIndexColumns(connection, "IDX_Transfers_Actionable_UpdatedAt"));
                Assert.Equal(
                    ["Removed", "Direction"],
                    ReadIndexColumns(connection, "IDX_Transfers_Removed_Direction"));
                Assert.Equal(
                    ["Direction", "EndedAt", "RequestedAt", "Id"],
                    ReadIndexColumns(connection, "IDX_Transfers_Direction_EndedAt"));
                Assert.Empty(ReadIndexColumns(connection, "IDX_Transfers_Direction"));

                using var sqlCommand = connection.CreateCommand();
                sqlCommand.CommandText =
                    "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'IDX_Transfers_Direction_EndedAt'";
                var sql = Assert.IsType<string>(sqlCommand.ExecuteScalar());
                Assert.Contains("WHERE EndedAt IS NOT NULL", sql, StringComparison.OrdinalIgnoreCase);
                Assert.Contains("State & 16", sql, StringComparison.OrdinalIgnoreCase);
                Assert.Contains("State & 32", sql, StringComparison.OrdinalIgnoreCase);
            }

            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={databasePath}");
            System.IO.File.Delete(databasePath);
        }
    }

    [Fact]
    public void AutoRetryIndexMigration_CreatesExactIdempotentIndex()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"slskdn-auto-retry-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={databasePath}";

        try
        {
            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText =
                    """
                    CREATE TABLE Transfers (
                        Id TEXT PRIMARY KEY,
                        Direction TEXT NOT NULL,
                        State INTEGER NOT NULL,
                        Removed INTEGER NOT NULL,
                        EndedAt TEXT NULL
                    );
                    CREATE INDEX IDX_Transfers_AutoRetry_EndedAt ON Transfers (Direction);
                    """;
                command.ExecuteNonQuery();
            }

            var migration = new Z07162026_AutoRetryIndexMigration(
                new ConnectionStringDictionary(new()
                {
                    [Database.Transfers] = connectionString,
                }));

            Assert.True(migration.NeedsToBeApplied());
            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());

            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                Assert.Equal(
                    ["Direction", "EndedAt", "Id"],
                    ReadIndexColumns(connection, "IDX_Transfers_AutoRetry_EndedAt"));

                using var sqlCommand = connection.CreateCommand();
                sqlCommand.CommandText =
                    "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'IDX_Transfers_AutoRetry_EndedAt'";
                var sql = Assert.IsType<string>(sqlCommand.ExecuteScalar());
                Assert.Contains("WHERE Removed = 0", sql, StringComparison.OrdinalIgnoreCase);
                Assert.Contains("State & 16", sql, StringComparison.OrdinalIgnoreCase);
                Assert.Contains("State & 32", sql, StringComparison.OrdinalIgnoreCase);
                Assert.Contains("State & 64", sql, StringComparison.OrdinalIgnoreCase);
                Assert.Contains("State & 512", sql, StringComparison.OrdinalIgnoreCase);
            }

            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={databasePath}");
            System.IO.File.Delete(databasePath);
        }
    }

    [Fact]
    public async Task TransferLookupIndexesMigration_CreatesPartialIndexesAndUsesThemForHotQueries()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"slskdn-transfer-lookups-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={databasePath}";

        try
        {
            await using (var connection = new SqliteConnection(connectionString))
            {
                await connection.OpenAsync();
                await using var command = connection.CreateCommand();
                command.CommandText =
                    """
                    CREATE TABLE Transfers (
                        Id TEXT PRIMARY KEY,
                        Direction TEXT NOT NULL,
                        BatchId TEXT NULL,
                        Username TEXT NOT NULL,
                        Filename TEXT NOT NULL,
                        Removed INTEGER NOT NULL,
                        UpdatedAt TEXT NOT NULL,
                        EndedAt TEXT NULL
                    );
                    """;
                await command.ExecuteNonQueryAsync();
            }

            var migration = new Z10112026_TransferLookupIndexesMigration(
                new ConnectionStringDictionary(new()
                {
                    [Database.Transfers] = connectionString,
                }));

            Assert.True(migration.NeedsToBeApplied());
            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());

            await using (var connection = new SqliteConnection(connectionString))
            {
                await connection.OpenAsync();
                Assert.Equal(["Direction", "BatchId"], ReadIndexColumns(connection, "IDX_Transfers_Direction_BatchId"));
                Assert.Equal(["Direction", "Username", "Filename"], ReadIndexColumns(connection, "IDX_Transfers_Direction_Username_Filename"));
                Assert.Equal(["Direction", "UpdatedAt"], ReadIndexColumns(connection, "IDX_Transfers_Removed_Direction_UpdatedAt"));

                var batchPlan = await ReadQueryPlanAsync(
                    connection,
                    "SELECT * FROM Transfers WHERE Direction = 'Download' AND BatchId = 'batch' AND Removed = 0");
                Assert.Contains(batchPlan, detail => detail.Contains("IDX_Transfers_Direction_BatchId", StringComparison.OrdinalIgnoreCase));

                var peerFilePlan = await ReadQueryPlanAsync(
                    connection,
                    "SELECT * FROM Transfers WHERE Direction = 'Download' AND Username = 'peer' AND Filename = 'track.flac' AND Removed = 0");
                Assert.Contains(peerFilePlan, detail => detail.Contains("IDX_Transfers_Direction_Username_Filename", StringComparison.OrdinalIgnoreCase));

                var removedPlan = await ReadQueryPlanAsync(
                    connection,
                    "SELECT * FROM Transfers WHERE Direction = 'Download' AND Removed = 1 AND EndedAt IS NOT NULL AND UpdatedAt < '2026-01-01'");
                Assert.Contains(removedPlan, detail => detail.Contains("IDX_Transfers_Removed_Direction_UpdatedAt", StringComparison.OrdinalIgnoreCase));
            }

            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={databasePath}");
            System.IO.File.Delete(databasePath);
        }
    }

    [Fact]
    public void Migrator_RegistersAutoRetryIndexMigration()
    {
        var connectionStrings = new ConnectionStringDictionary(new()
        {
            [Database.Search] = "Data Source=:memory:",
            [Database.Transfers] = "Data Source=:memory:",
            [Database.Messaging] = "Data Source=:memory:",
            [Database.Events] = "Data Source=:memory:",
        });
        var migrator = new Migrator(connectionStrings);
        var migrationsProperty = typeof(Migrator).GetProperty(
            "Migrations",
            System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
        var migrations = Assert.IsType<Dictionary<string, IMigration>>(migrationsProperty!.GetValue(migrator));

        Assert.IsType<Z07162026_AutoRetryIndexMigration>(
            migrations[nameof(Z07162026_AutoRetryIndexMigration)]);
        Assert.IsType<Z07162026_DownloadRequestSummaryIndexMigration>(
            migrations[nameof(Z07162026_DownloadRequestSummaryIndexMigration)]);
        Assert.IsType<Z08032026_AutoReplaceAttemptsMigration>(
            migrations[nameof(Z08032026_AutoReplaceAttemptsMigration)]);
        Assert.IsType<Z10112026_TransferLookupIndexesMigration>(
            migrations[nameof(Z10112026_TransferLookupIndexesMigration)]);
    }

    [Fact]
    public void AutoReplaceAttemptsMigration_AddsIdempotentDefaultedColumn()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"slskdn-auto-replace-attempts-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={databasePath}";

        try
        {
            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText =
                    "CREATE TABLE Transfers (Id TEXT PRIMARY KEY, Filename TEXT NOT NULL)";
                command.ExecuteNonQuery();
            }

            var migration = new Z08032026_AutoReplaceAttemptsMigration(
                new ConnectionStringDictionary(new()
                {
                    [Database.Transfers] = connectionString,
                }));

            Assert.True(migration.NeedsToBeApplied());
            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());

            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText =
                    "INSERT INTO Transfers (Id, Filename) VALUES ('transfer-1', 'track.flac'); " +
                    "SELECT AutoReplaceAttempts FROM Transfers WHERE Id = 'transfer-1';";
                Assert.Equal(0L, command.ExecuteScalar());
            }

            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={databasePath}");
            System.IO.File.Delete(databasePath);
        }
    }

    [Fact]
    public async Task DownloadRequestSummaryIndexMigration_ReplacesLegacyIndexAndSupportsCurrentSelection()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"slskdn-request-summary-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={databasePath}";

        try
        {
            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText =
                    """
                    CREATE TABLE Transfers (
                        Id TEXT PRIMARY KEY,
                        RequestId TEXT NULL,
                        Removed INTEGER NOT NULL,
                        RequestedAt TEXT NOT NULL
                    );
                    CREATE INDEX IDX_Transfers_RequestId ON Transfers (RequestId);
                    """;
                command.ExecuteNonQuery();
            }

            var migration = new Z07162026_DownloadRequestSummaryIndexMigration(
                new ConnectionStringDictionary(new()
                {
                    [Database.Transfers] = connectionString,
                }));

            Assert.True(migration.NeedsToBeApplied());
            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());

            await using (var connection = new SqliteConnection(connectionString))
            {
                await connection.OpenAsync();
                Assert.Equal(
                    ["RequestId", "Removed", "RequestedAt"],
                    ReadIndexColumns(connection, "IDX_Transfers_RequestId_Current"));
                Assert.Empty(ReadIndexColumns(connection, "IDX_Transfers_RequestId"));

                await using var sqlCommand = connection.CreateCommand();
                sqlCommand.CommandText =
                    "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'IDX_Transfers_RequestId_Current'";
                var sql = Assert.IsType<string>(await sqlCommand.ExecuteScalarAsync());
                Assert.Contains("RequestedAt DESC", sql, StringComparison.OrdinalIgnoreCase);

                var plan = await ReadQueryPlanAsync(
                    connection,
                    """
                    SELECT Id
                    FROM Transfers
                    WHERE RequestId = 'request-1'
                    ORDER BY Removed, RequestedAt DESC
                    LIMIT 1
                    """);
                Assert.Contains(plan, detail =>
                    detail.Contains("INDEX IDX_Transfers_RequestId_Current", StringComparison.Ordinal));
                Assert.DoesNotContain(plan, detail =>
                    detail.Contains("TEMP B-TREE", StringComparison.Ordinal));

                await using var replaceCommand = connection.CreateCommand();
                replaceCommand.CommandText =
                    """
                    DROP INDEX IDX_Transfers_RequestId_Current;
                    CREATE INDEX IDX_Transfers_RequestId_Current ON Transfers (RequestId, Removed, RequestedAt);
                    """;
                await replaceCommand.ExecuteNonQueryAsync();
            }

            Assert.True(migration.NeedsToBeApplied());
            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={databasePath}");
            System.IO.File.Delete(databasePath);
        }
    }

    [Fact]
    public void TransferUpdatedAtMigration_Adds_Backfills_And_Reuses_Ordered_Index()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"slskdn-transfers-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={databasePath}";

        try
        {
            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText = """
                    CREATE TABLE Transfers (
                        Id TEXT PRIMARY KEY,
                        Direction TEXT NOT NULL,
                        RequestedAt TEXT NOT NULL,
                        EnqueuedAt TEXT NULL,
                        StartedAt TEXT NULL,
                        EndedAt TEXT NULL
                    );
                    INSERT INTO Transfers (Id, Direction, RequestedAt)
                    VALUES ('transfer-1', 'Download', '2026-07-15 12:00:00');
                    """;
                command.ExecuteNonQuery();
            }

            var migration = new Z07152026_TransferUpdatedAtMigration(
                new ConnectionStringDictionary(new()
                {
                    [Database.Transfers] = connectionString,
                }));

            Assert.True(migration.NeedsToBeApplied());
            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());

            using (var connection = new SqliteConnection(connectionString))
            {
                connection.Open();
                using var timestamp = connection.CreateCommand();
                timestamp.CommandText = "SELECT UpdatedAt FROM Transfers WHERE Id = 'transfer-1'";
                Assert.Equal("2026-07-15 12:00:00", timestamp.ExecuteScalar());

                using var index = connection.CreateCommand();
                index.CommandText = "PRAGMA index_info('IDX_Transfers_Direction_UpdatedAt')";
                using var reader = index.ExecuteReader();
                var columns = new List<string>();
                while (reader.Read())
                {
                    columns.Add(reader.GetString(reader.GetOrdinal("name")));
                }

                Assert.Equal(["Direction", "UpdatedAt"], columns);
            }

            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool($"Data Source={databasePath}");
            System.IO.File.Delete(databasePath);
        }
    }

    [Fact]
    public void Removed_Is_Serialized_Only_For_Removed_Transfer_Deltas()
    {
        var visible = JsonSerializer.Serialize(new SlskdTransfer { Removed = false });
        var removed = JsonSerializer.Serialize(new SlskdTransfer { Removed = true });

        Assert.DoesNotContain("Removed", visible, StringComparison.Ordinal);
        Assert.Contains("\"Removed\":true", removed, StringComparison.Ordinal);
    }

    [Fact]
    public void QueryingLegacyRows_AllowsNullTransferStrings()
    {
        using var connection = new SqliteConnection("Data Source=:memory:");
        connection.Open();

        var options = new DbContextOptionsBuilder<TransfersDbContext>()
            .UseSqlite(connection)
            .Options;

        using (var context = new TransfersDbContext(options))
        {
            context.Database.EnsureCreated();
        }

        using (var command = connection.CreateCommand())
        {
            command.CommandText =
                """
                INSERT INTO Transfers
                (Id, Username, Direction, Filename, Size, StartOffset, State, StateDescription, RequestedAt, EnqueuedAt, StartedAt, EndedAt, BytesTransferred, AverageSpeed, PlaceInQueue, Exception, Removed, Attempts)
                VALUES
                ($id, $username, $direction, $filename, $size, $startOffset, $state, NULL, $requestedAt, NULL, NULL, NULL, $bytesTransferred, $averageSpeed, NULL, NULL, 0, 1)
                """;
            command.Parameters.AddWithValue("$id", Guid.NewGuid());
            command.Parameters.AddWithValue("$username", "legacy-user");
            command.Parameters.AddWithValue("$direction", TransferDirection.Upload.ToString());
            command.Parameters.AddWithValue("$filename", "legacy.flac");
            command.Parameters.AddWithValue("$size", 1024L);
            command.Parameters.AddWithValue("$startOffset", 0L);
            command.Parameters.AddWithValue("$state", TransferStates.None.ToString());
            command.Parameters.AddWithValue("$requestedAt", DateTime.UtcNow);
            command.Parameters.AddWithValue("$bytesTransferred", 0L);
            command.Parameters.AddWithValue("$averageSpeed", 0d);
            command.ExecuteNonQuery();
        }

        using var verificationContext = new TransfersDbContext(options);
        var transfer = verificationContext.Transfers.Single();

        Assert.Equal("legacy-user", transfer.Username);
        Assert.Null(transfer.StateDescription);
        Assert.Null(transfer.Exception);
    }

    private static async Task<List<string>> ReadQueryPlanAsync(SqliteConnection connection, string sql)
    {
        await using var command = connection.CreateCommand();
        command.CommandText = $"EXPLAIN QUERY PLAN {sql}";
        await using var reader = await command.ExecuteReaderAsync();
        var details = new List<string>();
        while (await reader.ReadAsync())
        {
            details.Add(reader.GetString(3));
        }

        return details;
    }

    private static List<string> ReadIndexColumns(SqliteConnection connection, string indexName)
    {
        using var command = connection.CreateCommand();
        command.CommandText = $"PRAGMA index_info('{indexName}')";
        using var reader = command.ExecuteReader();
        var columns = new List<string>();
        while (reader.Read())
        {
            columns.Add(reader.GetString(reader.GetOrdinal("name")));
        }

        return columns;
    }
}
