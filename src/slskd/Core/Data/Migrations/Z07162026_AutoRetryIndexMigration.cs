// <copyright file="Z07162026_AutoRetryIndexMigration.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Migrations;

using System;
using System.Collections.Generic;
using Microsoft.Data.Sqlite;
using Serilog;

/// <summary>
///     Adds the ordered partial index used by download auto-retry candidate streaming.
/// </summary>
public class Z07162026_AutoRetryIndexMigration : IMigration
{
    private const string IndexName = "IDX_Transfers_AutoRetry_EndedAt";

    public Z07162026_AutoRetryIndexMigration(ConnectionStringDictionary connectionStrings)
    {
        ConnectionString = connectionStrings[Database.Transfers];
    }

    private string ConnectionString { get; }
    private ILogger Log { get; } = Serilog.Log.ForContext<Z07162026_AutoRetryIndexMigration>();

    public bool NeedsToBeApplied()
    {
        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();

        if (!TableExists(connection))
        {
            return false;
        }

        return !HasColumns(connection, ["Direction", "EndedAt", "Id"]) ||
            !HasPredicate(connection);
    }

    public void Apply()
    {
        if (!NeedsToBeApplied())
        {
            Log.Information("> Migration {Name} is not necessary or has already been applied", nameof(Z07162026_AutoRetryIndexMigration));
            return;
        }

        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();
        using var transaction = connection.BeginTransaction();

        try
        {
            var createIndexSql = $"CREATE INDEX {IndexName} ON Transfers (Direction, EndedAt, Id) " +
                "WHERE Removed = 0 AND EndedAt IS NOT NULL " +
                "AND (State & 16) = 16 AND (State & 32) != 32 " +
                "AND (State & 64) != 64 AND (State & 512) != 512";
            Execute(connection, transaction, $"DROP INDEX IF EXISTS {IndexName}");
            Execute(connection, transaction, createIndexSql);
            transaction.Commit();
            Log.Information("> Added ordered download auto-retry candidate index");
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

    private static bool HasColumns(SqliteConnection connection, IReadOnlyList<string> expected)
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

    private static bool HasPredicate(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = $name";
        command.Parameters.AddWithValue("$name", IndexName);
        var sql = command.ExecuteScalar() as string;
        return sql?.Contains("WHERE Removed = 0", StringComparison.OrdinalIgnoreCase) == true &&
            sql.Contains("EndedAt IS NOT NULL", StringComparison.OrdinalIgnoreCase) &&
            sql.Contains("State & 16", StringComparison.OrdinalIgnoreCase) &&
            sql.Contains("State & 32", StringComparison.OrdinalIgnoreCase) &&
            sql.Contains("State & 64", StringComparison.OrdinalIgnoreCase) &&
            sql.Contains("State & 512", StringComparison.OrdinalIgnoreCase);
    }
}
