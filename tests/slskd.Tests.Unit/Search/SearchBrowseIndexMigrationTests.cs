// <copyright file="SearchBrowseIndexMigrationTests.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Tests.Unit.Search;

using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;
using slskd.Migrations;
using Xunit;

public sealed class SearchBrowseIndexMigrationTests
{
    [Fact]
    public async Task Apply_CreatesStableBrowseIndexAndUsesItForKeysetPages()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"slskdn-search-browse-{Guid.NewGuid():N}.db");
        var connectionString = $"Data Source={databasePath}";

        try
        {
            await using (var connection = new SqliteConnection(connectionString))
            {
                await connection.OpenAsync();
                await using var command = connection.CreateCommand();
                command.CommandText =
                    "CREATE TABLE Searches (Id TEXT PRIMARY KEY, StartedAt TEXT NOT NULL); CREATE INDEX IDX_Searches_StartedAt ON Searches (StartedAt);";
                await command.ExecuteNonQueryAsync();
            }

            var migration = new Z10132026_SearchBrowseIndexMigration(
                new ConnectionStringDictionary(new()
                {
                    [Database.Search] = connectionString,
                }));

            Assert.True(migration.NeedsToBeApplied());
            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());

            await using (var connection = new SqliteConnection(connectionString))
            {
                await connection.OpenAsync();
                await using var indexCommand = connection.CreateCommand();
                indexCommand.CommandText = "PRAGMA index_info('IDX_Searches_StartedAt_Id')";
                await using (var reader = await indexCommand.ExecuteReaderAsync())
                {
                    var columns = new List<string>();
                    while (await reader.ReadAsync())
                    {
                        columns.Add(reader.GetString(reader.GetOrdinal("name")));
                    }

                    Assert.Equal(["StartedAt", "Id"], columns);
                }

                await using var definitionCommand = connection.CreateCommand();
                definitionCommand.CommandText =
                    "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'IDX_Searches_StartedAt_Id'";
                var definition = Assert.IsType<string>(await definitionCommand.ExecuteScalarAsync());
                Assert.Contains("StartedAt DESC", definition, StringComparison.OrdinalIgnoreCase);
                Assert.Contains("Id DESC", definition, StringComparison.OrdinalIgnoreCase);

                await using var planCommand = connection.CreateCommand();
                planCommand.CommandText =
                    "EXPLAIN QUERY PLAN SELECT Id FROM Searches WHERE StartedAt < '2026-10-13T12:00:00Z' OR (StartedAt = '2026-10-13T12:00:00Z' AND Id < 'ffffffff-ffff-ffff-ffff-ffffffffffff') ORDER BY StartedAt DESC, Id DESC LIMIT 251";
                await using var planReader = await planCommand.ExecuteReaderAsync();
                var plan = new List<string>();
                while (await planReader.ReadAsync())
                {
                    plan.Add(planReader.GetString(3));
                }

                Assert.Contains(plan, detail =>
                    detail.Contains("IDX_Searches_StartedAt_Id", StringComparison.OrdinalIgnoreCase));
                Assert.DoesNotContain(plan, detail =>
                    detail.Contains("TEMP B-TREE", StringComparison.OrdinalIgnoreCase));
            }

            migration.Apply();
            Assert.False(migration.NeedsToBeApplied());
        }
        finally
        {
            slskd.Tests.Unit.SqliteTestDatabase.ClearPool(connectionString);
            System.IO.File.Delete(databasePath);
        }
    }
}
