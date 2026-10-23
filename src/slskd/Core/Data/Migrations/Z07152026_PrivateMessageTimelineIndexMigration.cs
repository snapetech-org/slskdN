// <copyright file="Z07152026_PrivateMessageTimelineIndexMigration.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Migrations;

using System;
using System.Collections.Generic;
using Microsoft.Data.Sqlite;
using Serilog;

/// <summary>
///     Adds the ordered private-message timeline index used by incremental chat reads.
/// </summary>
public class Z07152026_PrivateMessageTimelineIndexMigration : IMigration
{
    private const string IndexName = "IDX_PrivateMessages_Username_Timestamp";

    public Z07152026_PrivateMessageTimelineIndexMigration(ConnectionStringDictionary connectionStrings)
    {
        ConnectionString = connectionStrings[Database.Messaging];
    }

    private string ConnectionString { get; }
    private ILogger Log { get; } = Serilog.Log.ForContext<Z07152026_PrivateMessageTimelineIndexMigration>();

    public bool NeedsToBeApplied()
    {
        try
        {
            using var connection = new SqliteConnection(ConnectionString);
            connection.Open();

            using (var tableCommand = connection.CreateCommand())
            {
                tableCommand.CommandText = "SELECT EXISTS (SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'PrivateMessages')";
                if (!Convert.ToBoolean(tableCommand.ExecuteScalar()))
                {
                    return false;
                }
            }

            using var indexCommand = connection.CreateCommand();

            // nosemgrep: csharp.lang.security.sqli.csharp-sqli.csharp-sqli -- the index name comes from private migration constants; SQLite PRAGMA identifiers cannot be bound as values.
            indexCommand.CommandText = $"PRAGMA index_info('{IndexName}')";
            using var reader = indexCommand.ExecuteReader();

            var columns = new List<string>();
            while (reader.Read())
            {
                columns.Add(reader.GetString(reader.GetOrdinal("name")));
            }

            return columns.Count != 2 ||
                !columns[0].Equals("Username", StringComparison.OrdinalIgnoreCase) ||
                !columns[1].Equals("Timestamp", StringComparison.OrdinalIgnoreCase);
        }
        catch (Exception ex)
        {
            Log.Debug(ex, "Failed to check if the private-message timeline index migration is needed");
            return false;
        }
    }

    public void Apply()
    {
        if (!NeedsToBeApplied())
        {
            Log.Information("> Migration {Name} is not necessary or has already been applied", nameof(Z07152026_PrivateMessageTimelineIndexMigration));
            return;
        }

        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();

        using var transaction = connection.BeginTransaction();
        try
        {
            Log.Information("> Adding the private-message timeline index...");

            using (var dropCommand = new SqliteCommand($"DROP INDEX IF EXISTS {IndexName}", connection, transaction))
            {
                dropCommand.ExecuteNonQuery();
            }

            using (var createCommand = new SqliteCommand(
                $"CREATE INDEX {IndexName} ON PrivateMessages (Username, Timestamp)",
                connection,
                transaction))
            {
                createCommand.ExecuteNonQuery();
            }

            transaction.Commit();
            Log.Information("> Done!");
        }
        catch (Exception)
        {
            transaction.Rollback();
            throw;
        }
    }
}
