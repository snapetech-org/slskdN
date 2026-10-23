// <copyright file="Z07162026_DownloadRequestSummaryIndexMigration.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>

namespace slskd.Migrations;

using System;
using System.Collections.Generic;
using Microsoft.Data.Sqlite;
using Serilog;

/// <summary>
///     Adds the covering prefix used to aggregate attempts and select each request's current attempt.
/// </summary>
public class Z07162026_DownloadRequestSummaryIndexMigration : IMigration
{
    private const string IndexName = "IDX_Transfers_RequestId_Current";
    private const string LegacyIndexName = "IDX_Transfers_RequestId";

    public Z07162026_DownloadRequestSummaryIndexMigration(ConnectionStringDictionary connectionStrings)
    {
        ConnectionString = connectionStrings[Database.Transfers];
    }

    private string ConnectionString { get; }
    private ILogger Log { get; } = Serilog.Log.ForContext<Z07162026_DownloadRequestSummaryIndexMigration>();

    public bool NeedsToBeApplied()
    {
        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();

        if (!TableExists(connection))
        {
            return false;
        }

        return IndexExists(connection, LegacyIndexName) ||
            !HasColumns(connection, ["RequestId", "Removed", "RequestedAt"]) ||
            !HasRequestedAtDescending(connection);
    }

    public void Apply()
    {
        if (!NeedsToBeApplied())
        {
            Log.Information("> Migration {Name} is not necessary or has already been applied", nameof(Z07162026_DownloadRequestSummaryIndexMigration));
            return;
        }

        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();
        using var transaction = connection.BeginTransaction();

        try
        {
            Execute(connection, transaction, $"DROP INDEX IF EXISTS {IndexName}");
            Execute(connection, transaction, $"DROP INDEX IF EXISTS {LegacyIndexName}");
            Execute(connection, transaction, $"CREATE INDEX {IndexName} ON Transfers (RequestId, Removed, RequestedAt DESC)");
            transaction.Commit();
            Log.Information("> Added bounded download-request summary index");
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

    private static bool HasRequestedAtDescending(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = $name";
        command.Parameters.AddWithValue("$name", IndexName);
        var sql = command.ExecuteScalar() as string;
        return sql?.Contains("RequestedAt DESC", StringComparison.OrdinalIgnoreCase) == true;
    }
}
