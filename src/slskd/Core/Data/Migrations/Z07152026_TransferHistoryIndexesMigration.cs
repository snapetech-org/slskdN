// <copyright file="Z07152026_TransferHistoryIndexesMigration.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Migrations;

using System;
using System.Collections.Generic;
using Microsoft.Data.Sqlite;
using Serilog;

/// <summary>
///     Adds indexes for actionable snapshots, direction counts, and completed-history pages.
/// </summary>
public class Z07152026_TransferHistoryIndexesMigration : IMigration
{
    private const string ActionableIndex = "IDX_Transfers_Actionable_UpdatedAt";
    private const string CountIndex = "IDX_Transfers_Removed_Direction";
    private const string HistoryIndex = "IDX_Transfers_Direction_EndedAt";
    private const string LegacyDirectionIndex = "IDX_Transfers_Direction";

    public Z07152026_TransferHistoryIndexesMigration(ConnectionStringDictionary connectionStrings)
    {
        ConnectionString = connectionStrings[Database.Transfers];
    }

    private string ConnectionString { get; }
    private ILogger Log { get; } = Serilog.Log.ForContext<Z07152026_TransferHistoryIndexesMigration>();

    public bool NeedsToBeApplied()
    {
        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();

        if (!TableExists(connection))
        {
            return false;
        }

        return IndexExists(connection, LegacyDirectionIndex) ||
            !HasColumns(connection, ActionableIndex, ["Direction", "UpdatedAt"]) ||
            !HasPartialPredicate(connection, ActionableIndex) ||
            !HasColumns(connection, CountIndex, ["Removed", "Direction"]) ||
            !HasColumns(connection, HistoryIndex, ["Direction", "EndedAt", "RequestedAt", "Id"]) ||
            !HasHistoryPredicate(connection, HistoryIndex);
    }

    public void Apply()
    {
        if (!NeedsToBeApplied())
        {
            Log.Information("> Migration {Name} is not necessary or has already been applied", nameof(Z07152026_TransferHistoryIndexesMigration));
            return;
        }

        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();
        using var transaction = connection.BeginTransaction();

        try
        {
            var actionableIndexSql = $"CREATE INDEX {ActionableIndex} ON Transfers (Direction, UpdatedAt) " +
                "WHERE Removed = 0 AND ((State & 16) != 16 OR (State & 32) != 32)";
            var historyIndexSql = $"CREATE INDEX {HistoryIndex} ON Transfers (Direction, EndedAt DESC, RequestedAt DESC, Id DESC) " +
                "WHERE EndedAt IS NOT NULL AND (State & 16) = 16 AND (State & 32) = 32";
            Execute(connection, transaction, $"DROP INDEX IF EXISTS {ActionableIndex}");
            Execute(connection, transaction, $"DROP INDEX IF EXISTS {CountIndex}");
            Execute(connection, transaction, $"DROP INDEX IF EXISTS {HistoryIndex}");
            Execute(connection, transaction, $"DROP INDEX IF EXISTS {LegacyDirectionIndex}");
            Execute(connection, transaction, actionableIndexSql);
            Execute(connection, transaction, $"CREATE INDEX {CountIndex} ON Transfers (Removed, Direction)");
            Execute(connection, transaction, historyIndexSql);

            transaction.Commit();
            Log.Information("> Added bounded transfer snapshot and history indexes");
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

    private static bool IndexExists(SqliteConnection connection, string indexName)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT EXISTS (SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = $name)";
        command.Parameters.AddWithValue("$name", indexName);
        return Convert.ToBoolean(command.ExecuteScalar());
    }

    private static bool HasColumns(SqliteConnection connection, string indexName, IReadOnlyList<string> expected)
    {
        using var command = connection.CreateCommand();

        // nosemgrep: csharp.lang.security.sqli.csharp-sqli.csharp-sqli -- the index name comes from private migration constants; SQLite PRAGMA identifiers cannot be bound as values.
        command.CommandText = $"PRAGMA index_info('{indexName}')";
        using var reader = command.ExecuteReader();
        var columns = new List<string>();
        while (reader.Read())
        {
            columns.Add(reader.GetString(reader.GetOrdinal("name")));
        }

        if (columns.Count != expected.Count)
        {
            return false;
        }

        for (var index = 0; index < expected.Count; index++)
        {
            if (!columns[index].Equals(expected[index], StringComparison.OrdinalIgnoreCase))
            {
                return false;
            }
        }

        return true;
    }

    private static bool HasPartialPredicate(SqliteConnection connection, string indexName)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = $name";
        command.Parameters.AddWithValue("$name", indexName);
        var sql = command.ExecuteScalar() as string;
        return sql?.Contains("WHERE Removed = 0", StringComparison.OrdinalIgnoreCase) == true &&
            sql.Contains("State & 16", StringComparison.OrdinalIgnoreCase) &&
            sql.Contains("State & 32", StringComparison.OrdinalIgnoreCase);
    }

    private static bool HasHistoryPredicate(SqliteConnection connection, string indexName)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = $name";
        command.Parameters.AddWithValue("$name", indexName);
        var sql = command.ExecuteScalar() as string;
        return sql?.Contains("WHERE EndedAt IS NOT NULL", StringComparison.OrdinalIgnoreCase) == true &&
            sql.Contains("State & 16", StringComparison.OrdinalIgnoreCase) &&
            sql.Contains("State & 32", StringComparison.OrdinalIgnoreCase);
    }
}
