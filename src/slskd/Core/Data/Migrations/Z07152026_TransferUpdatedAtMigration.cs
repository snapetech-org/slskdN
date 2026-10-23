// <copyright file="Z07152026_TransferUpdatedAtMigration.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Migrations;

using System;
using System.Collections.Generic;
using Microsoft.Data.Sqlite;
using Serilog;

/// <summary>
///     Adds the transfer mutation cursor and its ordered direction index.
/// </summary>
public class Z07152026_TransferUpdatedAtMigration : IMigration
{
    private const string IndexName = "IDX_Transfers_Direction_UpdatedAt";

    public Z07152026_TransferUpdatedAtMigration(ConnectionStringDictionary connectionStrings)
    {
        ConnectionString = connectionStrings[Database.Transfers];
    }

    private string ConnectionString { get; }
    private ILogger Log { get; } = Serilog.Log.ForContext<Z07152026_TransferUpdatedAtMigration>();

    public bool NeedsToBeApplied()
    {
        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();

        if (!TableExists(connection))
        {
            return false;
        }

        if (!ColumnExists(connection, "UpdatedAt"))
        {
            return true;
        }

        var columns = GetIndexColumns(connection);
        return columns.Count != 2 ||
            !columns[0].Equals("Direction", StringComparison.OrdinalIgnoreCase) ||
            !columns[1].Equals("UpdatedAt", StringComparison.OrdinalIgnoreCase);
    }

    public void Apply()
    {
        if (!NeedsToBeApplied())
        {
            Log.Information("> Migration {Name} is not necessary or has already been applied", nameof(Z07152026_TransferUpdatedAtMigration));
            return;
        }

        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();
        using var transaction = connection.BeginTransaction();

        try
        {
            if (!ColumnExists(connection, "UpdatedAt", transaction))
            {
                using var addColumn = new SqliteCommand(
                    "ALTER TABLE Transfers ADD COLUMN UpdatedAt TEXT NOT NULL DEFAULT '0001-01-01 00:00:00'",
                    connection,
                    transaction);
                addColumn.ExecuteNonQuery();
            }

            using (var backfill = new SqliteCommand(
                """
                UPDATE Transfers
                SET UpdatedAt = COALESCE(EndedAt, StartedAt, EnqueuedAt, RequestedAt, CURRENT_TIMESTAMP)
                WHERE UpdatedAt = '0001-01-01 00:00:00'
                """,
                connection,
                transaction))
            {
                backfill.ExecuteNonQuery();
            }

            using (var dropIndex = new SqliteCommand($"DROP INDEX IF EXISTS {IndexName}", connection, transaction))
            {
                dropIndex.ExecuteNonQuery();
            }

            using (var createIndex = new SqliteCommand(
                $"CREATE INDEX {IndexName} ON Transfers (Direction, UpdatedAt)",
                connection,
                transaction))
            {
                createIndex.ExecuteNonQuery();
            }

            transaction.Commit();
            Log.Information("> Added transfer mutation cursor and timeline index");
        }
        catch (Exception)
        {
            transaction.Rollback();
            throw;
        }
    }

    private static bool TableExists(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT EXISTS (SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'Transfers')";
        return Convert.ToBoolean(command.ExecuteScalar());
    }

    private static bool ColumnExists(SqliteConnection connection, string name, SqliteTransaction? transaction = null)
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = "PRAGMA table_info('Transfers')";
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            if (reader.GetString(reader.GetOrdinal("name")).Equals(name, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        return false;
    }

    private List<string> GetIndexColumns(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();

        // nosemgrep: csharp.lang.security.sqli.csharp-sqli.csharp-sqli -- the index name comes from private migration constants; SQLite PRAGMA identifiers cannot be bound as values.
        command.CommandText = $"PRAGMA index_info('{IndexName}')";
        using var reader = command.ExecuteReader();
        var columns = new List<string>();
        while (reader.Read())
        {
            columns.Add(reader.GetString(reader.GetOrdinal("name")));
        }

        return columns;
    }
}
