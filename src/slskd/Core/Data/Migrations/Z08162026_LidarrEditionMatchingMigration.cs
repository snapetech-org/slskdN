// <copyright file="Z08162026_LidarrEditionMatchingMigration.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Migrations;

using System;
using System.Collections.Generic;
using Microsoft.Data.Sqlite;
using Serilog;

/// <summary>
///     Adds the Lidarr release track count, duration, and disambiguation columns used to
///     validate Soulseek candidates against the album/track Lidarr actually wants.
/// </summary>
public sealed class Z08162026_LidarrEditionMatchingMigration
{
    public Z08162026_LidarrEditionMatchingMigration(string connectionString)
    {
        ConnectionString = connectionString;
    }

    private string ConnectionString { get; }

    private ILogger Log { get; } = Serilog.Log.ForContext<Z08162026_LidarrEditionMatchingMigration>();

    public void Apply()
    {
        using var connection = new SqliteConnection(ConnectionString);
        connection.Open();

        var columns = GetExistingColumns(connection);
        if (columns.Count == 0)
        {
            return;
        }

        using var transaction = connection.BeginTransaction();
        try
        {
            AddColumnIfMissing(connection, transaction, columns, "LidarrTrackCount", "INTEGER");
            AddColumnIfMissing(connection, transaction, columns, "LidarrDurationSeconds", "INTEGER");
            AddColumnIfMissing(connection, transaction, columns, "LidarrReleaseDisambiguation", "TEXT");
            transaction.Commit();
            Log.Information("> Lidarr edition matching columns are ready.");
        }
        catch
        {
            transaction.Rollback();
            throw;
        }
    }

    private static HashSet<string> GetExistingColumns(SqliteConnection connection)
    {
        var columns = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        using var table = connection.CreateCommand();
        table.CommandText = "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'WishlistItems'";
        if (table.ExecuteScalar() is null)
        {
            return columns;
        }

        using var command = connection.CreateCommand();
        command.CommandText = "PRAGMA table_info(WishlistItems)";
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            columns.Add(reader.GetString(1));
        }

        return columns;
    }

    private static void AddColumnIfMissing(
        SqliteConnection connection,
        SqliteTransaction transaction,
        ISet<string> columns,
        string columnName,
        string columnType)
    {
        if (columns.Contains(columnName))
        {
            return;
        }

        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = (columnName, columnType) switch
        {
            ("LidarrTrackCount", "INTEGER") => "ALTER TABLE WishlistItems ADD COLUMN LidarrTrackCount INTEGER",
            ("LidarrDurationSeconds", "INTEGER") => "ALTER TABLE WishlistItems ADD COLUMN LidarrDurationSeconds INTEGER",
            ("LidarrReleaseDisambiguation", "TEXT") => "ALTER TABLE WishlistItems ADD COLUMN LidarrReleaseDisambiguation TEXT",
            _ => throw new ArgumentException("Unsupported WishlistItems column migration."),
        };
        command.ExecuteNonQuery();
        columns.Add(columnName);
    }
}
