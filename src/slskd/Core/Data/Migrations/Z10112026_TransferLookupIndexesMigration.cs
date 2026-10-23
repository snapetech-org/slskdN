// <copyright file="Z10112026_TransferLookupIndexesMigration.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Migrations;

using System;
using System.Collections.Generic;
using Microsoft.Data.Sqlite;
using Serilog;

/// <summary>
///     Adds indexes for frequent transfer lookups and removed-transfer cleanup.
/// </summary>
public class Z10112026_TransferLookupIndexesMigration : IMigration
{
    private const string BatchIndex = "IDX_Transfers_Direction_BatchId";
    private const string PeerFileIndex = "IDX_Transfers_Direction_Username_Filename";
    private const string RemovedIndex = "IDX_Transfers_Removed_Direction_UpdatedAt";

    public Z10112026_TransferLookupIndexesMigration(ConnectionStringDictionary connectionStrings)
    {
        ConnectionString = connectionStrings[Database.Transfers];
    }

    private string ConnectionString { get; }
    private ILogger Log { get; } = Serilog.Log.ForContext<Z10112026_TransferLookupIndexesMigration>();

    public bool NeedsToBeApplied()
    {
        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();

        if (!TableExists(connection))
        {
            return false;
        }

        return !HasDefinition(connection, BatchIndex, ["Direction", "BatchId"], "Removed = 0") ||
            !HasDefinition(connection, PeerFileIndex, ["Direction", "Username", "Filename"], "Removed = 0") ||
            !HasDefinition(connection, RemovedIndex, ["Direction", "UpdatedAt"], "Removed = 1", "EndedAt IS NOT NULL");
    }

    public void Apply()
    {
        if (!NeedsToBeApplied())
        {
            Log.Information("> Migration {Name} is not necessary or has already been applied", nameof(Z10112026_TransferLookupIndexesMigration));
            return;
        }

        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();
        using var transaction = connection.BeginTransaction();

        try
        {
            Execute(connection, transaction, $"DROP INDEX IF EXISTS {BatchIndex}");
            Execute(connection, transaction, $"DROP INDEX IF EXISTS {PeerFileIndex}");
            Execute(connection, transaction, $"DROP INDEX IF EXISTS {RemovedIndex}");
            Execute(connection, transaction,
                $"CREATE INDEX {BatchIndex} ON Transfers (Direction, BatchId) WHERE Removed = 0");
            Execute(connection, transaction,
                $"CREATE INDEX {PeerFileIndex} ON Transfers (Direction, Username, Filename) WHERE Removed = 0");
            var removedIndexSql =
                $"CREATE INDEX {RemovedIndex} ON Transfers (Direction, UpdatedAt) WHERE Removed = 1 AND EndedAt IS NOT NULL";
            Execute(connection, transaction, removedIndexSql);

            transaction.Commit();
            Log.Information("> Added transfer lookup and removed-history cleanup indexes");
        }
        catch (Exception)
        {
            transaction.Rollback();
            throw;
        }
    }

    private static void Execute(SqliteConnection connection, SqliteTransaction transaction, string sql)
    {
        using var command = new SqliteCommand(sql, connection, transaction);
        command.ExecuteNonQuery();
    }

    private static bool TableExists(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT EXISTS (SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'Transfers')";
        return Convert.ToBoolean(command.ExecuteScalar());
    }

    private static bool HasDefinition(
        SqliteConnection connection,
        string indexName,
        IReadOnlyList<string> expectedColumns,
        params string[] expectedPredicates)
    {
        using (var command = connection.CreateCommand())
        {

            // nosemgrep: csharp.lang.security.sqli.csharp-sqli.csharp-sqli -- the index name comes from private migration constants; SQLite PRAGMA identifiers cannot be bound as values.
            command.CommandText = $"PRAGMA index_info('{indexName}')";
            using var reader = command.ExecuteReader();
            var columns = new List<string>();
            while (reader.Read())
            {
                columns.Add(reader.GetString(reader.GetOrdinal("name")));
            }

            if (columns.Count != expectedColumns.Count)
            {
                return false;
            }

            for (var index = 0; index < expectedColumns.Count; index++)
            {
                if (!columns[index].Equals(expectedColumns[index], StringComparison.OrdinalIgnoreCase))
                {
                    return false;
                }
            }
        }

        using var definitionCommand = connection.CreateCommand();
        definitionCommand.CommandText = "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = $name";
        definitionCommand.Parameters.AddWithValue("$name", indexName);
        var definition = definitionCommand.ExecuteScalar() as string;

        return definition != null && Array.TrueForAll(
            expectedPredicates,
            predicate => definition.Contains(predicate, StringComparison.OrdinalIgnoreCase));
    }
}
