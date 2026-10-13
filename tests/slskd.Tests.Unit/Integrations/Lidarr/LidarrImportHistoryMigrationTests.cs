// <copyright file="LidarrImportHistoryMigrationTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Integrations.Lidarr;

using Microsoft.Data.Sqlite;
using slskd.Migrations;
using Xunit;

public sealed class LidarrImportHistoryMigrationTests
{
    [Fact]
    public void Apply_IsIdempotentAndCreatesHistoryTableAndIndexes()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"lidarr-history-migration-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={databasePath}";
        try
        {
            var migration = new Z08172026_LidarrImportHistoryMigration(connectionString);
            migration.Apply();
            migration.Apply();

            using var connection = new SqliteConnection(connectionString);
            connection.Open();
            using var command = connection.CreateCommand();
            command.CommandText = "PRAGMA table_info(LidarrImportHistory)";
            using var reader = command.ExecuteReader();
            var columns = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            while (reader.Read())
            {
                columns.Add(reader.GetString(1));
            }

            Assert.Contains("SourceDirectory", columns);
            Assert.Contains("Status", columns);
            Assert.Contains("CommandId", columns);
            Assert.Contains("RetryOfId", columns);
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool(connectionString);
            File.Delete(databasePath);
            File.Delete(databasePath + "-shm");
            File.Delete(databasePath + "-wal");
        }
    }
}
